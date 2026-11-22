"""G3: ctx.ensure_city bo qua lan kiem lai thua (khong co thao tac o giua, trong cua so skip_recheck_s)."""
import time
from types import SimpleNamespace

from bot.ctx import Ctx


def make(win=3.0):
    c = Ctx.__new__(Ctx)
    c.cfg = {"nav": {"skip_recheck_s": win}}
    c.dev = SimpleNamespace(act_seq=0)
    c.nav = []
    c.calls = 0

    def fake():
        c.calls += 1
        return True
    c._ensure_city = fake
    return c


def test_second_call_without_action_is_skipped_and_recorded():
    c = make()
    c.ensure_city()
    c.ensure_city()
    assert c.calls == 1 and c.nav == [("city", "done", None)]


def test_action_in_between_forces_recheck():
    c = make()
    c.ensure_city()
    c.dev.act_seq += 1
    c.ensure_city()
    assert c.calls == 2


def test_window_expiry_and_disabled():
    c = make()
    c.ensure_city()
    c._city_ok = (c.dev.act_seq, time.time() - 10)
    c.ensure_city()
    assert c.calls == 2
    d = make(win=0)
    d.ensure_city()
    d.ensure_city()
    assert d.calls == 2


def test_unverified_city_is_not_remembered():
    c = make()
    c._ensure_city = lambda: (setattr(c, "calls", c.calls + 1), False)[1]
    c.ensure_city()
    c.ensure_city()
    assert c.calls == 2
