"""J1 (chu du an 2026-11-27): bo hoc biet cho chet nhung truoc day chi goto dung -> module van cham
(vd gather/btn_recommended an 1/514). Gio MOI lan cham qua Ctx hoi Learner.skip_tap."""
import types

from bot import ctx as ctxmod
from bot import learn


class FakeMem:
    def __init__(self):
        self.rows = []

    def query(self, *a, **k):
        return []

    def log_exp(self, rows):
        self.rows += rows


def make(**cfg):
    c = {"dead_min": 8, "dead_rate": 0.1, "probe_min": 60, "probe_cap_h": 24}
    c.update(cfg)
    return learn.Learner(FakeMem(), {"learn": c})


def fail(L, tpl, x, y, n):
    L.record([{"tpl": tpl, "x": x, "y": y, "changed": 0} for _ in range(n)])


def test_not_dead_until_enough_fails():
    L = make()
    fail(L, "gather/btn_recommended", 144, 888, 7)
    assert L.skip_tap("gather/btn_recommended", "gather.run", 144, 888, now=0) is None
    fail(L, "gather/btn_recommended", 144, 888, 1)
    assert L.skip_tap("gather/btn_recommended", "gather.run", 144, 888, now=0) == "skip"
    assert L.skip_tap("gather/btn_recommended", "gather.run", 300, 500, now=0) is None   # o khac


def test_probe_schedule_doubles_and_success_revives():
    L = make()
    fail(L, "notify.heroes", 384, 240, 10)
    t = 1000.0
    assert L.skip_tap(None, "notify.heroes", 384, 240, now=t) == "skip"
    assert L.skip_tap(None, "notify.heroes", 384, 240, now=t + 59 * 60) == "skip"
    assert L.skip_tap(None, "notify.heroes", 384, 240, now=t + 61 * 60) == "probe"       # sau 60 phut
    assert L.skip_tap(None, "notify.heroes", 384, 240, now=t + 61 * 60 + 90 * 60) == "skip"
    assert L.skip_tap(None, "notify.heroes", 384, 240, now=t + 61 * 60 + 121 * 60) == "probe"   # gap doi 120
    L.record([{"why": "notify.heroes", "x": 384, "y": 240, "changed": 1}])                # thu lai an
    assert L.skip_tap(None, "notify.heroes", 384, 240, now=t + 10 ** 5) is None
    fail(L, "notify.heroes", 384, 240, 7)                                                   # chua du 8 lan lien tiep
    assert L.skip_tap(None, "notify.heroes", 384, 240, now=t + 10 ** 5) is None


def test_close_back_buttons_and_exempt_never_skipped():
    L = make(skip_exempt=["tutorial"])
    for tpl in ("common/btn_back", "common/btn_x", "tutorial/btn_auto_formation"):
        fail(L, tpl, 480, 912, 30)
        assert L.skip_tap(tpl, "x.y", 480, 912, now=0) is None
    fail(L, None, 100, 100, 30)
    L.record([{"why": "tutorial.run", "x": 100, "y": 100, "changed": 0} for _ in range(30)])
    assert L.skip_tap(None, "tutorial.run", 100, 100, now=0) is None


def test_switch_off():
    L = make(skip_dead=False)
    fail(L, "gather/btn_recommended", 144, 888, 30)
    assert L.skip_tap("gather/btn_recommended", "gather.run", 144, 888, now=0) is None


def test_ctx_tap_skips_and_logs_exp(monkeypatch):
    L = make()
    fail(L, "gather/btn_recommended", 144, 888, 20)
    taps = []
    c = ctxmod.Ctx.__new__(ctxmod.Ctx)
    c.cfg = {"learn": {}}
    c.dev = types.SimpleNamespace(idx=3, tap=lambda x, y: taps.append((x, y)))
    c.step, c._exp, c._img = "gather", [], None
    monkeypatch.setattr(ctxmod.Ctx, "learner", property(lambda self: L))
    monkeypatch.setattr(ctxmod.Ctx, "blocked_tap", lambda self, x, y, img=None: False)
    monkeypatch.setattr(ctxmod.Ctx, "human_gate", lambda self, why="": 0)
    c.tap(144, 888, tpl="gather/btn_recommended")
    assert taps == []
    assert c._exp and c._exp[0]["kind"] == "ml_skip" and c._exp[0]["tpl"] == "gather/btn_recommended"
    assert L.skips == 1


def test_skip_rows_do_not_count_as_taps():
    L = make()
    L.record([{"kind": "ml_skip", "tpl": "a/b", "x": 1, "y": 1}])
    assert L.spot("a/b", 1, 1) == (0, 0)
