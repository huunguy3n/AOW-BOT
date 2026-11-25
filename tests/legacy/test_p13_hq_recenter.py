"""P13-1: truoc khi cham nha chinh -> ra the gioi roi vao lai thanh pho (can giua); khong tu ve 'hen lai sau' lau."""
import types

from aowbot.domain import hqplan as d
from bot.modules import upgrade


class Mem:
    def __init__(self):
        self.f = {}

    def fact(self, i, k):
        return self.f.get(k)

    def set_fact(self, i, k, v):
        self.f[k] = v


def _ctx(ready, goto_ok=True, cfg=None):
    log = []
    c = types.SimpleNamespace(
        cfg=cfg if cfg is not None else {"build": {}}, mem=Mem(), dev=types.SimpleNamespace(idx=3),
        world_ready=lambda: ready,
        ensure_world=lambda: log.append("world"),
        ensure_city=lambda: log.append("city"),
        goto=lambda t, rounds=10: log.append("goto_" + t) or goto_ok)
    return c, log


def test_world_ready_goes_world_then_city():
    c, log = _ctx(True)
    assert upgrade.recenter_hq(c) is True
    assert log == ["world", "city"]


def test_low_hq_tries_world_once_then_remembers_failure():
    c, log = _ctx(False, goto_ok=False)
    assert upgrade.recenter_hq(c) is False
    assert "goto_world" in log and c.mem.f.get("recenter_fail")
    log.clear()
    assert upgrade.recenter_hq(c) is False       # 6 gio khong thu lai
    assert "goto_world" not in log


def test_low_hq_world_reachable():
    c, log = _ctx(False, goto_ok=True)
    assert upgrade.recenter_hq(c) is True
    assert log == ["city", "goto_world", "city"]


def test_switch_off():
    c, log = _ctx(True, cfg={"build": {"recenter_world": False}})
    assert upgrade.recenter_hq(c) is False
    assert log == ["city"]


def test_none_backoff_short():
    p = d.record(None, "none", 1000.0)
    assert p.wake_at - 1000.0 == 300
    assert d.NONE_CAP_S <= 3600
