from datetime import UTC, datetime

from aowbot.domain import warday as W
from bot import scheduler


def ts(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=UTC).timestamp()


# 2026-11-28 la thu 7
SAT = ts(2026, 11, 28)


def test_stamina_marks():
    assert W.last_stamina_mark(ts(2026, 11, 21, 9)) == ts(2026, 11, 21, 8)
    assert W.last_stamina_mark(ts(2026, 11, 21, 3)) == ts(2026, 11, 21, 0)
    assert W.last_stamina_mark(ts(2026, 11, 21, 23)) == ts(2026, 11, 21, 15)
    assert W.next_stamina_mark(ts(2026, 11, 21, 15)) == ts(2026, 11, 22, 0)


def test_stamina_due_and_next():
    now = ts(2026, 11, 21, 8, 5)
    assert W.stamina_due(now, ts(2026, 11, 21, 0, 30))
    assert not W.stamina_due(now, ts(2026, 11, 21, 8, 2))
    assert W.stamina_next_at(now, ts(2026, 11, 21, 8, 2)) == ts(2026, 11, 21, 15, 1)


def test_war_saturday():
    assert W.war_saturday(ts(2026, 11, 23, 5)) == SAT        # thu 2
    assert W.war_saturday(SAT + 3600) == SAT                  # chinh thu 7
    assert W.war_saturday(ts(2026, 11, 29, 1)) is None        # chu nhat


def test_shield_plan_timeline():
    days = [SAT]
    fri22 = SAT - 2 * 3600
    assert W.shield_plan(fri22 - 3600, days, None).hours is None
    assert W.shield_plan(fri22 - 3600, days, None).at == fri22
    p = W.shield_plan(fri22 + 60, days, None)
    assert p.hours == 8
    # khien 8h dang chay -> hen luc sap het
    p = W.shield_plan(fri22 + 3600, days, fri22 + 8 * 3600)
    assert p.hours is None and p.at == fri22 + 8 * 3600 - 20 * 60
    # sap het 8h (sang thu 7) -> 12h
    p = W.shield_plan(fri22 + 8 * 3600 - 600, days, fri22 + 8 * 3600)
    assert p.hours == 12
    # sap het 12h, chua qua ngay -> 12h tiep
    p = W.shield_plan(SAT + 18 * 3600 - 600, days, SAT + 18 * 3600)
    assert p.hours == 12
    # qua ngay chien tranh -> khong bat nua
    assert W.shield_plan(SAT + 86400 + 60, days, None).hours is None


def test_blocks_step():
    days = [SAT]
    assert W.blocks_step("gather", SAT - 3600, days)
    assert not W.blocks_step("rebels", SAT + 5 * 3600, days)
    assert not W.blocks_step("gather", SAT + 86400, days)
    assert not W.blocks_step("train", SAT + 3600, days)
    assert not W.blocks_step("gather", SAT - 3 * 3600, days)


def test_scheduler_blocks_gather(monkeypatch):
    class Mem:
        def fact(self, idx, key, default=None):
            return {"war_notice_seen": ts(2026, 11, 25, 3)}.get(key, default)
    cfg = {"warday": {}}
    assert scheduler.war_blocks(Mem(), 0, "gather", cfg, SAT + 3600)
    assert not scheduler.war_blocks(Mem(), 0, "gather", cfg, SAT + 86400 + 1)
    p = scheduler.plan_step(Mem(), 0, "gather", scheduler.sched_cfg(cfg), SAT + 3600, {}, cfg)
    assert not p.ready and "chien tranh" in p.why
