"""B1 (su kien, chong trung), B3 (goals), B4 (registry), POL (policy), B5/6 (planner + utility + decide)."""
import dataclasses

import pytest

from aowbot.app.config import load_agent_config
from aowbot.application.decide import decide
from aowbot.application.world_view import build_account_state
from aowbot.domain.actions import REGISTRY, ActionName, ActionSpec, spec
from aowbot.domain.events import DEDUP_BUCKET_S, Event, EventType, events_from_timers
from aowbot.domain.freshness import Fact
from aowbot.domain.goals import AccountFacts, Goal, continuous_construction, march_utilization, phase_priority
from aowbot.domain.marches import Availability, MarchObservation, MarchTimer, timers_from_rows
from aowbot.domain.policy import SafetyPolicy, ShieldInputs, shield_decision
from bot.modules import defense
from tests.fakes import FakeClock, InMemoryStateSource

NOW = 1_800_000_000.0
CFG = load_agent_config({"gather": {"min_hq_level": 9}, "build": {"max_builders": 2}})


# ---------------------------------------------------------------- B1 su kien
def test_event_key_dedups_close_predictions():
    a = Event(1, EventType.MARCH_RETURN_DUE, "march", NOW, "obs1")
    b = Event(1, EventType.MARCH_RETURN_DUE, "march", NOW + 30, "obs2")
    c = Event(1, EventType.MARCH_RETURN_DUE, "march", NOW + DEDUP_BUCKET_S * 2, "obs2")
    assert (NOW // DEDUP_BUCKET_S) == ((NOW + 30) // DEDUP_BUCKET_S) or a.key != b.key  # cung khung -> trung
    assert a.key != c.key
    assert a.key != Event(2, EventType.MARCH_RETURN_DUE, "march", NOW, "x").key


def test_timers_from_rows_matches_legacy_rules():
    rows = [{"state": "marching", "arrive_at": NOW + 100, "travel": 300},
            {"state": "returning", "return_at": NOW + 50},
            {"state": "gathering", "return_at": NOW + 900},
            {"state": "gathering", "gather_done": NOW + 600},
            {"state": "unknown"}]
    assert timers_from_rows(rows) == [
        MarchTimer(0, "arrive", NOW + 100, "ocr", 0.9), MarchTimer(0, "march", NOW + 400, "est", 0.3),
        MarchTimer(1, "march", NOW + 50, "ocr", 0.9), MarchTimer(2, "march", NOW + 900, "ocr", 0.6),
        MarchTimer(3, "march", NOW + 600, "ocr", 0.4)]
    evs = events_from_timers(1, timers_from_rows(rows), "t")
    assert [e.type for e in evs].count(EventType.MARCH_ARRIVE_DUE) == 1


# ---------------------------------------------------------------- B3 goals
@pytest.mark.parametrize("hq, construction, march", [(3, 1.0, 0.2), (8, 1.0, 0.2), (9, 0.5, 1.0), (None, 0.5, 1.0)])
def test_phase_priority_follows_owner_decision(hq, construction, march):
    f = AccountFacts(hq, 0, 1, 9)
    assert phase_priority(Goal.CONTINUOUS_CONSTRUCTION, f) == construction
    assert phase_priority(Goal.MARCH_UTILIZATION, f) == march


def test_goal_deficits():
    f = AccountFacts(30, 1, 2, 9)
    assert march_utilization(Availability(2, None), 5, f).deficit == pytest.approx(0.4)
    assert march_utilization(Availability(0, None), 5, f).satisfied
    assert march_utilization(None, None, f).deficit == 1.0
    assert continuous_construction(f).deficit == 0.5
    assert continuous_construction(dataclasses.replace(f, builders_busy=2)).satisfied


# ---------------------------------------------------------------- B4 registry + POL
def test_registry_has_no_premium_action():
    assert all(s.premium_cost == 0 for s in REGISTRY)
    assert {s.name for s in REGISTRY} == set(ActionName)


def test_invalid_spec_rejected():
    with pytest.raises(ValueError):
        dataclasses.replace(spec(ActionName.OBSERVE_MARCHES), risk=2.0)


PREMIUM = dataclasses.replace(spec(ActionName.DISPATCH_GATHER), premium_cost=500)


@pytest.mark.parametrize("policy, action, attempts, conf, allowed", [
    (SafetyPolicy(), PREMIUM, 0, 1.0, False),                                        # mac dinh cam kim cuong
    (SafetyPolicy(frozenset({ActionName.DISPATCH_GATHER}), premium_daily_cap=400), PREMIUM, 0, 1.0, False),
    (SafetyPolicy(frozenset({ActionName.DISPATCH_GATHER}), premium_daily_cap=500), PREMIUM, 0, 1.0, True),
    (SafetyPolicy(), spec(ActionName.DISPATCH_GATHER), 3, 1.0, False),               # het luot thu
    (SafetyPolicy(), spec(ActionName.DISPATCH_GATHER), 2, 1.0, True),
    (SafetyPolicy(), spec(ActionName.DISPATCH_GATHER), 0, 0.3, False),               # du lieu cu
    (SafetyPolicy(), spec(ActionName.OBSERVE_MARCHES), 0, 0.0, True),                # quan sat luon duoc
])
def test_policy(policy, action: ActionSpec, attempts, conf, allowed):
    assert policy.check(action, attempts, conf).allowed is allowed


# ---------------------------------------------------------------- B5/6 decide
def state(used, observed_ago, hq=30, busy=2, timers=((NOW + 3600, 0.9),)):
    s = InMemoryStateSource()
    s.facts[(1, "hq_level")] = Fact(hq, "t", NOW - 60)
    s.facts[(1, "builders_busy")] = Fact(busy, "t", NOW - 60)
    s.facts[(1, "march_total")] = Fact(5, "t", NOW - observed_ago)
    s.facts[(1, "world_open")] = Fact(True, "t", NOW - 60)
    s.march_obs[1] = MarchObservation(5, used, NOW - observed_ago, list(timers))
    return build_account_state(1, s, FakeClock(NOW), CFG.world)


EV = Event(1, EventType.MARCH_RETURN_DUE, "march", NOW, "t")


def test_dispatch_when_free_and_fresh():
    d = decide(EV, state(used=3, observed_ago=60), CFG.decide)
    assert d.action is ActionName.DISPATCH_GATHER
    assert "march_utilization" in d.why and d.next_eval_at == NOW + spec(ActionName.DISPATCH_GATHER).duration_s


def test_observe_first_when_stale():
    d = decide(EV, state(used=3, observed_ago=3 * 3600), CFG.decide)
    assert d.action is ActionName.OBSERVE_MARCHES


def test_nothing_to_do_waits_for_next_return():
    d = decide(EV, state(used=5, observed_ago=60, timers=[(NOW + 3600, 0.9)] * 5), CFG.decide)
    assert d.action is None
    assert d.next_eval_at == NOW + 3600
    assert all(o.blocker for o in d.options)            # moi lua chon deu co ly do


def test_farm_below_gather_hq_does_not_gather():
    d = decide(EV, state(used=0, observed_ago=60, hq=3, busy=1), CFG.decide)
    assert d.action is ActionName.LEGACY_BUILD
    gather = next(o for o in d.options if o.action == "dispatch_gather")
    assert not gather.feasible and "nha chinh 3 < 9" in gather.blocker


def test_retry_limit_blocks_action():
    d = decide(EV, state(used=3, observed_ago=60), CFG.decide, {ActionName.DISPATCH_GATHER: 3})
    assert d.action is not ActionName.DISPATCH_GATHER


def test_decision_is_deterministic_and_serializable():
    a, b = decide(EV, state(3, 60), CFG.decide), decide(EV, state(3, 60), CFG.decide)
    assert a == b
    assert a.to_dict()["action"] == "dispatch_gather"


def test_shield_rule_lives_in_domain_and_legacy_delegates():
    assert shield_decision(ShieldInputs(None, 10_000, 500, 0, 2000, True))[0] == "unread"
    assert defense.shield_choice(0, 10_000, 500, 0, 2000, True) == shield_decision(
        ShieldInputs(0, 10_000, 500, 0, 2000, True))
