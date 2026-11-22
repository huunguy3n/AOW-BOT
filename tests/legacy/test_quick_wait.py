from types import SimpleNamespace

from bot import build
from bot.modules import observe


class FakeCtx:
    def __init__(self, cfg=None):
        self.cfg = {"build": {"quick_s": 60, "quick_total_s": 200, "max_builders": 1, **(cfg or {})}}
        self.step_limit = 900

    def ensure_city(self):
        pass

    def shot(self):
        return None

    def wd_reset(self, limit=None):
        self.step_limit = limit


def _patch(mp, bars, busy_seq):
    mp.setattr(observe, "progress_bars", lambda img: [(0, 0, t) for t in bars])
    seq = iter(busy_seq)
    mp.setattr(build, "builders", lambda ctx, img=None: next(seq, (0, 1)))
    mp.setattr(build.time, "sleep", lambda s: None)


def test_waits_for_quick_build(monkeypatch):
    ctx = FakeCtx()
    _patch(monkeypatch, [30], [(1, 1), (0, 1)])
    assert build.quick_wait(ctx) is True
    assert ctx.step_limit == 900            # giu gioi han buoc


def test_long_build_not_waited(monkeypatch):
    ctx = FakeCtx()
    _patch(monkeypatch, [3600], [(1, 1)])
    assert build.quick_wait(ctx) is False


def test_unreadable_time_not_waited(monkeypatch):
    ctx = FakeCtx()
    _patch(monkeypatch, [], [(1, 1)])
    assert build.quick_wait(ctx) is False


def test_disabled_and_cap(monkeypatch):
    ctx = FakeCtx({"quick_s": 0})
    _patch(monkeypatch, [10], [])
    assert build.quick_wait(ctx) is False
    ctx2 = FakeCtx()
    ctx2._quick_waited = 500.0
    assert build.quick_wait(ctx2) is False
