"""P1: dieu kien truoc khi chay + gian chu ky khi tra 0 (bot/stepgate.py) va lich khong keo may cho buoc bi bo."""
import calendar
import time

from bot import scheduler, stepgate


class Mem:
    def __init__(self):
        self.f = {}
        self.runs = []          # (step, started, result, ret)

    def fact(self, idx, key, default=None):
        v = self.f.get((idx, key))
        return default if v is None else v

    def set_fact(self, idx, key, value):
        self.f[(idx, key)] = value

    def query(self, sql, args=()):
        if "FROM runs" in sql and "step=?" in sql and "started" in sql.split("FROM")[0]:
            step = args[1]
            rows = sorted((r for r in self.runs if r[0] == step), key=lambda r: -r[1])
            return [(r[1],) for r in rows[:1]]
        return []


NOON = calendar.timegm((2026, 11, 24, 10, 30, 0))     # thu 3, 10:30 UTC: khong phai moc the luc (0/8/15h)
CFG = {"stepgate": {}, "warday": {"dates": []}}


def test_warday_only_at_stamina_mark_or_war_window():
    m = Mem()
    m.set_fact(0, "stamina_claim_at", NOON - 600)                     # da nhan moc 8h
    g = stepgate.check(m, 0, "warday", CFG, NOON)
    assert not g.run and "moc the luc" in g.why
    m.set_fact(0, "stamina_claim_at", NOON - 6 * 3600)               # chua nhan moc 8h UTC
    g = stepgate.check(m, 0, "warday", CFG, NOON)
    assert g.run and g.must


def test_warday_due_ignores_idle_backoff():
    m = Mem()
    m.set_fact(0, "idle:warday", {"zeros": 5, "until": NOON + 3600})
    assert stepgate.check(m, 0, "warday", CFG, NOON).run             # stamina_claim_at None -> toi han


def test_idle_backoff_after_two_zeros_and_reset_on_work():
    m = Mem()
    assert stepgate.record(m, 0, "heal", "ok", 0, CFG, NOON) == 0     # 1 lan: chua gian
    u = stepgate.record(m, 0, "heal", "ok", 0, CFG, NOON)
    assert u == NOON + 3600                                           # 2 lan: base_min 60
    assert stepgate.record(m, 0, "heal", "ok", 0, CFG, NOON) == NOON + 7200
    g = stepgate.check(m, 0, "heal", CFG, NOON + 10)
    assert not g.run and "tra 0 3 lan" in g.why
    assert stepgate.snapshot(m, 0, CFG, NOON)["heal"]["zeros"] == 3
    stepgate.record(m, 0, "heal", "ok", 1, CFG, NOON)                 # lam duoc viec -> xoa
    assert stepgate.idle_until(m, 0, "heal") == 0


def test_idle_backoff_capped_and_errors_ignored():
    m = Mem()
    for _ in range(12):
        u = stepgate.record(m, 0, "campaign", "ok", 0, CFG, NOON)
    assert u == NOON + 8 * 3600
    assert stepgate.record(m, 0, "campaign", "err", None, CFG, NOON) == 0     # loi -> runner._backoff lo
    assert stepgate.record(m, 0, "gather", "ok", 0, CFG, NOON) == 0           # khong trong steps


def test_heal_needs_bubble_or_fight():
    m = Mem()
    assert stepgate.check(m, 0, "heal", CFG, NOON).run                # chua biet -> chay
    m.set_fact(0, "heal_bubble", False)
    m.runs.append(("heal", NOON - 600, "ok", 0))
    assert not stepgate.check(m, 0, "heal", CFG, NOON).run
    g = stepgate.check(m, 0, "heal", CFG, NOON, done={"rebels": 1})
    assert g.run and g.must                                           # vua danh phan quan
    m.set_fact(0, "heal_bubble", True)
    assert stepgate.check(m, 0, "heal", CFG, NOON).must
    m.set_fact(0, "heal_bubble", False)
    m.runs[:] = [("heal", NOON - 7 * 3600, "ok", 0)]
    assert stepgate.check(m, 0, "heal", CFG, NOON).run                # qua max_skip_h -> kiem tra 1 lan


def test_mainquest_and_campaign_wait_for_power():
    m = Mem()
    m.set_fact(0, "resources", {"power": 1000})
    m.runs += [("mainquest", NOON - 60, "ok", 0), ("campaign", NOON - 60, "ok", 0)]
    m.set_fact(0, "mainquest_need_power", 1050)
    assert not stepgate.check(m, 0, "mainquest", CFG, NOON).run
    m.set_fact(0, "resources", {"power": 1100})
    assert stepgate.check(m, 0, "mainquest", CFG, NOON).run
    m.set_fact(0, "mainquest_busy_until", NOON + 600)
    assert not stepgate.check(m, 0, "mainquest", CFG, NOON).run
    m.set_fact(0, "campaign_need_power", 1200)
    m.set_fact(0, "campaign_idle_at", NOON - 3600)
    assert not stepgate.check(m, 0, "campaign", CFG, NOON).run
    m.set_fact(0, "campaign_idle_at", NOON - 9 * 3600)
    assert stepgate.check(m, 0, "campaign", CFG, NOON).must           # toi han nhan treo may


def test_disabled_passes_everything():
    m = Mem()
    m.set_fact(0, "idle:heal", {"zeros": 9, "until": NOON + 999})
    assert stepgate.check(m, 0, "heal", {"stepgate": {"enabled": False}}, NOON).run


def test_planned_skip_never_for_heal():
    m = Mem()
    m.set_fact(0, "idle:heal", {"zeros": 9, "until": NOON + 999})
    m.set_fact(0, "idle:campaign", {"zeros": 9, "until": NOON + 999})
    assert not stepgate.planned_skip(m, 0, "heal", CFG, NOON)
    assert stepgate.planned_skip(m, 0, "campaign", CFG, NOON)


class SchedMem(Mem):
    """Mem cho scheduler.decide_one: khong co runs/visits/timers."""

    def backoff_until(self, idx, step):
        return 0

    def timers(self, idx, prefix):
        return []


def test_scheduler_does_not_pull_visit_for_gated_mainquest():
    m = SchedMem()
    m.set_fact(0, "builders_busy", 0)                                 # tho ranh -> plan_build ready
    m.set_fact(0, "mainquest_busy_until", time.time() + 3600)
    cfg = {"schedule": {}, "stepgate": {}, "warday": {"enabled": False}}
    v = scheduler.decide_one(m, 0, ["mainquest", "campaign"], {"mainquest": True, "campaign": True}, cfg, time.time())
    assert "mainquest" not in v.steps
    assert "mainquest" not in v.why
