"""A-FIX-1a (doi khong co dong ho khong phai doi ranh), A-FIX-2 (khong lam tuoi du kien cu), A-FIX-3 (gian chu ky
tho ranh khi lan truoc khong xay duoc)."""
import json

import pytest

from bot import scheduler
from bot.memory import Memory
from bot.runner import Runner

NOW = 1_800_000_000.0
H = 3600


# ---------------------------------------------------------------- A-FIX-1a march_slots
def test_unknown_marches_are_not_free():
    # ca B11 (#1 2026-11-21): 5/5 dang di, chi 1 doi doc duoc dong ho -> cach cu ra '4 doi ranh'
    free, nxt = scheduler.march_slots(5, 5, NOW - 60, [(NOW + 2 * H, 0.6)], NOW, 1 * H)
    assert free == 0
    assert nxt[0] == NOW - 60 + 1 * H            # doi khong ro gio: uoc luong, ve som nhat
    assert nxt[2] is False                       # uoc luong -> khong chac chan


def test_estimated_return_passed_counts_as_free():
    free, nxt = scheduler.march_slots(5, 5, NOW - 2 * H, [(NOW + H, 0.9)], NOW, 1 * H)
    assert free == 4                             # 4 doi uoc luong da ve
    assert nxt == (NOW + H, nxt[1], True)


def test_past_due_timer_is_free():
    free, nxt = scheduler.march_slots(2, 2, NOW - 10, [(NOW - 5, 0.9), (NOW + 100, 0.9)], NOW, H)
    assert free == 1 and nxt[0] == NOW + 100


def test_partially_used():
    free, _ = scheduler.march_slots(5, 3, NOW - 10, [(NOW + 100, 0.9)], NOW, H)
    assert free == 2


@pytest.mark.parametrize("used, observed_at", [(None, NOW - 10), (5, None)])
def test_without_counter_falls_back_to_timer_count(used, observed_at):
    free, _ = scheduler.march_slots(5, used, observed_at, [(NOW + 100, 0.9)], NOW, H)
    assert free == 4                             # hanh vi cu khi chua co 'Hanh quan x/y'


def test_more_timers_than_used_keeps_earliest():
    free, nxt = scheduler.march_slots(3, 1, NOW, [(NOW + 300, 0.9), (NOW + 100, 0.9)], NOW, H)
    assert free == 2 and nxt[0] == NOW + 100


@pytest.fixture
def mem(tmp_path):
    return Memory(str(tmp_path / "m.db"))


def test_typical_return_uses_lower_quartile(mem):
    for k, gap in enumerate([600, 1200, 1800, 2400, 3000, 3600, 4200, 4800]):
        mem._exec("INSERT INTO observations(inst, at, marches) VALUES (1, ?, ?)",
                  (NOW + k, json.dumps([{"state": "gathering", "return_at": NOW + k + gap}])))
    assert scheduler.typical_return_s(mem, 1, 999) == 1800
    assert scheduler.typical_return_s(mem, 2, 999) == 999


def test_plan_gather_no_visit_when_all_marching(mem):
    cfg = {"gather": {"min_hq_level": 9}, "world": {"min_hq_level": 6}}
    sc = scheduler.sched_cfg({"schedule": {"gather_retry_min": 10}})
    for k, v in {"hq_level": 30, "march_total": 5, "march_used": 5, "observed_at": NOW - 60}.items():
        mem.set_fact(1, k, v)
    mem.set_timer(1, "march:0", NOW + 2 * H, conf=0.6)
    mem.log_run(None, 1, "gather", NOW - 600, 30, "ok", ret=2)
    p = scheduler.plan_gather(mem, 1, sc, NOW, cfg)
    assert not p.ready
    assert "doi ranh" not in p.why


# ---------------------------------------------------------------- A-FIX-2 facts_to_copy
def test_unchanged_facts_are_not_rewritten():
    st = {"hq_level": 5, "name": "MF001", "status": "idle"}
    known = {"hq_level": 5, "name": "MF001"}
    assert Runner.facts_to_copy(st, known, Runner.FACT_KEYS) == {}


def test_changed_or_new_facts_are_copied():
    st = {"hq_level": 6, "mainquest_need_power": 933040, "tutorial_done": None}
    known = {"hq_level": 5}
    assert Runner.facts_to_copy(st, known, Runner.FACT_KEYS) == {
        "hq_level": 6, "mainquest_need_power": 933040, "tutorial_done": None}


def test_seen_at_kept_when_value_same(mem):
    mem.set_fact(0, "hq_level", 5)
    seen = mem.query("SELECT seen_at FROM facts WHERE inst=0 AND key='hq_level'")[0][0]
    for k, v in Runner.facts_to_copy({"hq_level": 5}, mem.facts(0), Runner.FACT_KEYS).items():
        mem.set_fact(0, k, v)
    assert mem.query("SELECT seen_at FROM facts WHERE inst=0 AND key='hq_level'")[0][0] == seen


# ---------------------------------------------------------------- A-FIX-3 build backoff
def rows(*visits):
    """visits: list ret theo lan ghe, moi nhat truoc -> [(visit, started, ret)]"""
    out, t = [], NOW
    for v, rets in enumerate(visits):
        for r in rets:
            t -= 60
            out.append((100 - v, t, r))
    return out


def test_streak_counts_visits_not_runs():
    assert scheduler.build_streak(rows(["0", "0"], ["0", None], ["0", "0"])) == 3


def test_streak_stops_at_success_regardless_of_result():
    assert scheduler.build_streak(rows(["0", "0"], ["1", "0"], ["0", "0"])) == 1


def test_streak_resets_after_state_change():
    r = rows(["0"], ["0"], ["0"], ["0"])
    assert scheduler.build_streak(r, since=r[1][1]) == 2


@pytest.mark.parametrize("streak, minutes", [(0, 10), (1, 10), (2, 20), (4, 40), (6, 80), (8, 120), (20, 120)])
def test_gap_doubles_every_two_and_is_capped(streak, minutes):
    sc = scheduler.sched_cfg({"schedule": {"min_gap_min": 10, "build_every_min": 120}})
    assert scheduler.build_gap_s(streak, sc) == minutes * 60


def test_plan_build_backs_off_and_can_be_disabled(mem):
    for v in range(4):
        mem.log_run(v, 0, "mainquest", NOW - 3000 + v * 600, 30, "ok", ret=0)
    mem.set_fact(0, "builders_busy", 0)
    on = scheduler.plan_build(mem, 0, scheduler.sched_cfg({"schedule": {"min_gap_min": 10}}), NOW, "mainquest")
    off = scheduler.plan_build(mem, 0, scheduler.sched_cfg({"schedule": {"min_gap_min": 10, "build_backoff": False}}),
                               NOW, "mainquest")
    last = NOW - 3000 + 3 * 600
    assert on.at == last + 40 * 60 and not on.ready
    assert off.at == max(last + 10 * 60, NOW - 1) and off.ready
