"""M0 + M1 lo trinh ML (chu du an duyet 2026-11-27, docs/strategy/ml-roadmap.md):
M1-1 doan cham vo ich theo dHash vung cham, M1-2 theo diem khop, tu kiem bo-ra; M1-3 man la -> lam theo mau tay;
M0 bang so do theo ngay. Cham ML chan = KHONG gui, coi nhu da cham (tap_tpl True / tap_first ten mau)."""
import time
import types

import numpy as np

from bot import ctx as ctxmod
from bot import imitate, learn


class FakeMem:
    def __init__(self):
        self.rows = []

    def query(self, *a, **k):
        return []

    def log_exp(self, rows):
        self.rows += rows


def make(**cfg):
    c = {"dead_min": 8, "dead_rate": 0.1, "noop_explore": 0.0}
    c.update(cfg)
    return learn.Learner(FakeMem(), {"learn": c})


TAB_ON, TAB_OFF = "00000000000000ff", "ffffffff00000000"     # dHash vung cham: tab da mo / chua mo


def feed(L, key, n, crop, ch, score=None, x=100, y=200):
    L.record([{"tpl": key, "x": x, "y": y, "crop": crop, "score": score, "changed": ch} for _ in range(n)])


def tab_history(L):
    # xen ke: tab da mo -> cham vo ich; tab chua mo -> cham an. Ti le an chung 50 % -> KHONG phai cho chet.
    for _ in range(20):
        feed(L, "ally/tab_main", 1, TAB_ON, 0)
        feed(L, "ally/tab_main", 1, TAB_OFF, 1)


def test_crop_predicts_noop_only_for_same_look():
    L = make()
    tab_history(L)
    assert L.skip_tap("ally/tab_main", "alliance.show_tab", 100, 200) is None        # khong phai cho chet
    assert L.noop_gate("ally/tab_main", "alliance.show_tab", 100, 200, TAB_ON) == ("skip", "crop")
    assert L.noop_gate("ally/tab_main", "alliance.show_tab", 100, 200, TAB_OFF) is None
    near = "%016x" % (int(TAB_ON, 16) ^ 0b111)                                          # lech 3 bit van giong
    assert L.noop_gate("ally/tab_main", "alliance.show_tab", 100, 200, near) == ("skip", "crop")
    assert L.noop_gate("ally/tab_main", "alliance.show_tab", 400, 800, TAB_ON) is None  # o khac


def test_self_check_blocks_unreliable_keys():
    L = make()
    for i in range(40):                           # cung mot anh, luc an luc truot -> doan khong dang tin
        feed(L, "x/btn", 1, TAB_ON, int(i % 3 == 0))
    assert not L.noop_valid("x/btn")
    assert L.noop_gate("x/btn", "m.f", 100, 200, TAB_ON) is None
    L2 = make()
    feed(L2, "y/btn", 6, TAB_ON, 0)               # qua it mau de tu kiem (va chua du 8 lan -> chua 'chet')
    assert L2.noop_gate("y/btn", "m.f", 100, 200, TAB_ON) is None


def test_score_rule_when_no_crop():
    L = make()
    for _ in range(20):
        feed(L, "tutorial/btn_auto_formation", 1, None, 0, score=0.845)
        feed(L, "tutorial/btn_auto_formation", 1, None, 1, score=0.893)
    assert L.noop_gate("tutorial/btn_auto_formation", "t.r", 100, 200, None, 0.846) == ("skip", "score")
    assert L.noop_gate("tutorial/btn_auto_formation", "t.r", 100, 200, None, 0.893) is None


def test_exempt_and_switch_and_explore():
    L = make()
    for k in ("common/btn_x", "imitate"):
        for _ in range(40):
            feed(L, k, 1, TAB_ON, 0)
        assert L.noop_gate(k, "m.f", 100, 200, TAB_ON) is None
    tab_history(L)
    assert make(skip_noop=False).noop_gate("ally/tab_main", "a.b", 100, 200, TAB_ON) is None
    assert L.noop_gate("ally/tab_main", "a.b", 100, 200, TAB_ON, rng=lambda: 0.0) == ("skip", "crop")
    L.cfg["noop_explore"] = 0.05
    assert L.noop_gate("ally/tab_main", "a.b", 100, 200, TAB_ON, rng=lambda: 0.01) == ("probe", "crop")


def _ctx(L, monkeypatch, img=None):
    taps = []
    c = ctxmod.Ctx.__new__(ctxmod.Ctx)
    c.cfg = {"learn": {}}
    c.dev = types.SimpleNamespace(idx=2, tap=lambda x, y: taps.append((x, y)))
    c.step, c._exp, c._img, c._img_t, c.wait_scale = "alliance", [], img, time.time(), 1.0
    monkeypatch.setattr(ctxmod.Ctx, "learner", property(lambda self: L))
    monkeypatch.setattr(ctxmod.Ctx, "blocked_tap", lambda self, x, y, img=None: False)
    return c, taps


def test_tap_tpl_skipped_counts_as_tapped(monkeypatch):
    L = make()
    tab_history(L)
    img = np.zeros((960, 540, 3), np.uint8)
    c, taps = _ctx(L, monkeypatch, img)
    monkeypatch.setattr(learn, "dhash", lambda im, n=8: TAB_ON)
    monkeypatch.setattr(ctxmod.Ctx, "find", lambda self, name, fresh=True, **kw: (100, 200, 0.994))
    assert c.tap_tpl("ally/tab_main") is True                # coi nhu da cham
    assert taps == []
    r = c._exp[-1]
    assert r["kind"] == "ml_skip" and r["outcome"] == "crop" and r["crop"] == TAB_ON
    monkeypatch.setattr(learn, "dhash", lambda im, n=8: TAB_OFF)
    monkeypatch.setattr(ctxmod.Ctx, "_exp_begin", lambda *a, **k: None)
    monkeypatch.setattr(ctxmod.Ctx, "_after_tap", lambda *a, **k: None)
    assert c.tap_tpl("ally/tab_main") is True
    assert taps == [(100, 200)]                              # tab chua mo -> cham that


def test_unknown_action_uses_demo_and_stop():
    img = np.random.RandomState(1).randint(0, 255, (960, 540, 3)).astype(np.uint8)
    ev = {"x": 270, "y": 480, "at": 1.0}
    d = imitate.make_demo(img, ev, "d/1.png")
    idx = imitate.Index([d])
    r = imitate.unknown_action(img, idx)
    assert r and abs(r["x"] - 270) <= 2 and abs(r["y"] - 480) <= 2
    assert imitate.unknown_action(img, idx, blocked={"d/1.png"}) is None
    assert imitate.unknown_action(img, imitate.Index([d], stop=[learn.feat(img)])) is None
    assert imitate.unknown_action(img, None) is None


def test_imitate_unknown_switch(monkeypatch):
    c, _ = _ctx(make(), monkeypatch)
    c.cfg = {"learn": {"imitate_unknown": False}}
    assert c._imitate_unknown(np.zeros((960, 540, 3), np.uint8)) is None


def test_scoreboard_shape():
    rows = learn.scoreboard(FakeMem(), days=3, now=1_800_000_000)
    assert len(rows) == 3
    assert {"day", "taps", "ok_pct", "skips", "skip_crop", "visits", "machine_h", "hq"} <= set(rows[0])
