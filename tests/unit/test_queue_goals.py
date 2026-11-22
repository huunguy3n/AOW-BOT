"""Q4: agent giu hang cho huan luyen / nghien cuu luon chay (thu thap van dan dau khi co doi ranh)."""
from aowbot.app.config import load_agent_config
from aowbot.application.decide import decide
from aowbot.application.world_view import build_account_state
from aowbot.domain.actions import ActionName
from aowbot.domain.events import Event, EventType
from aowbot.domain.freshness import Fact
from aowbot.domain.goals import Goal, queue_busy
from aowbot.domain.marches import MarchObservation
from tests.fakes import FakeClock, InMemoryStateSource

NOW = 1_800_000_000.0
CFG = load_agent_config({})
EV = Event(1, EventType.OBSERVE_DUE, "bootstrap", NOW, "t")


def state(used=5, train=(3, 3), research=(1, 1), wait_hq=None, age=60):
    s = InMemoryStateSource()
    for k, v in (("hq_level", 30), ("builders_busy", 2), ("march_total", 5), ("world_open", True)):
        s.facts[(1, k)] = Fact(v, "t", NOW - 60)
    if train:
        s.facts[(1, "queue_train")] = Fact(list(train), "t", NOW - age)
    if research:
        s.facts[(1, "queue_research")] = Fact(list(research), "t", NOW - age)
    if wait_hq is not None:
        s.facts[(1, "research_wait_hq")] = Fact(wait_hq, "t", NOW - 60)
    s.march_obs[1] = MarchObservation(5, used, NOW - 60, [(NOW + 3600, 0.9)] * used)
    return build_account_state(1, s, FakeClock(NOW), CFG.world)


def test_queue_goal_deficit():
    g = queue_busy(Goal.TRAINING, (1, 3), 0.6)
    assert g.deficit == 2 / 3 and not g.satisfied
    assert queue_busy(Goal.TRAINING, (3, 3), 0.6).satisfied
    assert queue_busy(Goal.TRAINING, None, 0.6).deficit == 1.0


def test_idle_barracks_get_training():
    assert decide(EV, state(train=(0, 3)), CFG.decide).action is ActionName.LEGACY_TRAIN


def test_idle_research_queue_gets_research():
    assert decide(EV, state(research=(0, 1)), CFG.decide).action is ActionName.LEGACY_RESEARCH


def test_research_waits_for_hq():
    d = decide(EV, state(research=(0, 1), wait_hq=30), CFG.decide)
    assert d.action is not ActionName.LEGACY_RESEARCH
    r = next(o for o in d.options if o.action == "legacy_research")
    assert "nha chinh" in r.blocker


def test_gather_first_when_marches_free():
    assert decide(EV, state(used=2, train=(0, 3)), CFG.decide).action is ActionName.DISPATCH_GATHER


def test_unknown_or_stale_queue_is_not_acted_on():
    d = decide(EV, state(train=None, research=(0, 1), age=10 * 3600), CFG.decide)
    assert d.action not in (ActionName.LEGACY_TRAIN, ActionName.LEGACY_RESEARCH)
