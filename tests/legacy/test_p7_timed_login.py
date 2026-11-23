"""P7-11 (chu du an 2026-11-24): "Dang nhap hen gio" - 5 the luc moi khung; lich hen gio co dinh ghe moi may trong
01:00-02:00 va 15:00-16:00 gio VN (18-19h va 8-9h UTC)."""
import calendar
import time

from aowbot.domain import warday as W
from bot import scheduler, stepgate
from bot.memory import Memory

WIN = ((18, 19), (8, 9))


def utc(s):
    return calendar.timegm(time.strptime(s, "%Y-%m-%d %H:%M"))


def test_login_window():
    assert W.login_window(utc("2026-11-24 18:30"), WIN) == (utc("2026-11-24 18:00"), utc("2026-11-24 19:00"))
    assert W.login_window(utc("2026-11-24 08:00"), WIN)[0] == utc("2026-11-24 08:00")
    assert W.login_window(utc("2026-11-24 09:00"), WIN) is None          # ket thuc khong tinh
    assert W.login_window(utc("2026-11-24 12:00"), WIN) is None
    # khung qua nua dem
    assert W.login_window(utc("2026-11-25 00:30"), ((23, 1),)) == (utc("2026-11-24 23:00"), utc("2026-11-25 01:00"))


def test_due_once_per_window():
    t = utc("2026-11-24 18:05")
    assert W.timed_login_due(t, None, WIN, 2)
    assert not W.timed_login_due(utc("2026-11-24 18:01"), None, WIN, 2)  # con trong delay
    assert not W.timed_login_due(t + 60, t, WIN, 2)                        # da ghe trong khung nay
    assert W.timed_login_due(utc("2026-11-25 08:10"), t, WIN, 2)          # khung sau
    assert not W.timed_login_due(utc("2026-11-24 12:00"), None, WIN, 2)


def test_next_at():
    assert W.timed_login_next_at(utc("2026-11-24 12:00"), None, WIN, 2) == utc("2026-11-24 18:02")
    assert W.timed_login_next_at(utc("2026-11-24 18:01"), None, WIN, 2) == utc("2026-11-24 18:02")
    t = utc("2026-11-24 18:30")
    assert W.timed_login_next_at(t, None, WIN, 2) == t                     # dang den han
    assert W.timed_login_next_at(t, t - 60, WIN, 2) == utc("2026-11-25 08:02")   # da nhan -> khung ke tiep
    assert W.timed_login_next_at(utc("2026-11-24 22:00"), None, WIN, 2) == utc("2026-11-25 08:02")


def test_vn_hours_match_utc_windows():
    c = W.wcfg(None)
    vn = sorted(((a + 7) % 24, (b + 7) % 24) for a, b in c["timed_login_windows_utc"])
    assert vn == [(1, 2), (15, 16)]


def _cfg():
    return {"warday": {"stamina": False}, "schedule": {}}


def test_scheduler_plans_warday_visit_in_window(tmp_path):
    mem = Memory(str(tmp_path / "m.db"))
    sc = scheduler.sched_cfg(_cfg())
    p = scheduler.plan_warday(mem, 3, sc, utc("2026-11-24 12:00"), _cfg())
    assert p is not None and p.at == utc("2026-11-24 18:02") and "dang nhap hen gio" in p.why
    now = utc("2026-11-24 18:10")
    assert scheduler.timed_login_due(mem, 3, _cfg(), now)
    assert scheduler.stamina_due(mem, 3, _cfg(), now)                 # notify / rewards chay kem de nhan
    assert stepgate.precheck(mem, 3, "warday", _cfg(), now).run
    mem.set_fact(3, "timed_login_at", now)
    assert not scheduler.timed_login_due(mem, 3, _cfg(), now + 60)
    p = scheduler.plan_warday(mem, 3, sc, now + 60, _cfg())
    assert p.at == utc("2026-11-25 08:02")


def test_timed_login_off(tmp_path):
    mem = Memory(str(tmp_path / "m.db"))
    cfg = {"warday": {"stamina": False, "timed_login": False}}
    assert not scheduler.timed_login_due(mem, 1, cfg, utc("2026-11-24 18:10"))
