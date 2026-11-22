"""P5 muc 1 (PM 2026-11-23): tinh bao (phan loai bang, ly do unknown, thong ke log)."""
import glob
import os
import time
import types

import cv2
import pytest

from bot import intel_rules as IR
from bot.modules import notify, rebels
from bot.vision import Vision


class V:
    def __init__(self, seen=(), have=None, scores=None):
        self.seen = set(seen)
        self.have = set(have) if have is not None else None
        self.scores = scores or {}

    def has(self, name):
        return True if self.have is None else name in self.have

    def find(self, img, name, th=None, roi=None, **k):
        if name in self.scores:
            return (270, 235, self.scores[name]) if self.scores[name] >= (th or 0.82) else None
        return (270, 300, 0.95) if name in self.seen else None

    def find_all(self, img, name, **k):
        return []


# ---------- tinh bao: hop thuan ----------
def test_panel_kind_go_reward_none():
    assert IR.panel_kind("img", V({"intel/btn_go"})) == "go"
    assert IR.panel_kind("img", V(scores={"common/msg_reward": 0.79})) == "reward"   # anh 22/11: 0,79-0,93
    assert IR.panel_kind("img", V(scores={"common/msg_reward": 0.6})) is None
    assert IR.panel_kind("img", V()) is None


def test_unknown_reasons_and_rate():
    assert all(IR.is_unknown(r) for r in IR.UNKNOWNS)
    assert not IR.is_unknown("picked") and not IR.is_unknown(None)
    assert IR.unknown_rate({"picked": 6, "unknown_target": 1, "unknown": 1, "win": 2}) == (2, 10, 20.0)
    assert IR.unknown_rate({}) == (0, 0, None)


def test_parse_log_window_and_ignores_count_line():
    lines = ["2026-11-22 00:09:25 INFO [#3] Tinh bao: unknown",
             "2026-11-22 00:09:54 INFO [#3] Tinh bao: 0 nhiem vu",
             "2026-11-22 01:00:00 INFO [MainThread] Tinh bao: picked",
             "2026-11-22 02:00:00 INFO [#1] Tinh bao: unknown_target",
             "2026-11-22 02:00:01 INFO [#1] Tinh bao: ghim Phan quan Lv.1 - bo (doc cap khong ra / vua du doan thua)"]
    assert IR.parse_log(lines) == {"unknown": 1, "picked": 1, "unknown_target": 1}
    t = time.mktime(time.strptime("2026-11-22 01:30:00", "%Y-%m-%d %H:%M:%S"))
    assert IR.parse_log(lines, t0=t) == {"unknown_target": 1}


def test_marker_roi_excludes_bottom_left_false_hit():
    x, y, w, h = IR.MARKER_ROI
    assert not (x <= 92 <= x + w and y <= 760 <= y + h)      # khop nham 22/11 (cham 97,805 = marker + (5,45))
    assert x <= 263 <= x + w and y <= 363 <= y + h            # ghim that (anh chu du an 2026-11-20)


# ---------- tinh bao: luong intel_mission tren Ctx gia ----------
class Ctx:
    def __init__(self, v, full=False):
        self.POPUP_CLOSERS = ["common/btn_x"]
        self.v, self.taps, self.caps, self.full = v, [], [], full
        self.cfg = {"rebels": {}}
        self.dev = types.SimpleNamespace(idx=1)
        self.mem, self.sent = None, 0

    def shot(self):
        return "img"

    def find(self, name, fresh=True, **k):
        return self.v.find("img", name, **k)

    def wait_for(self, name, **k):
        return self.v.find("img", name)

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def tap_tpl(self, name, **k):
        if self.v.find("img", name):
            self.taps.append(name)
            return True
        return False

    def tap_first(self, names, **k):
        return None

    def back_out(self, n=4):
        self.taps.append("back")

    def dismiss_reward(self):
        self.taps.append("dismiss")

    def march_full(self):
        return self.full

    def march_sent(self):
        self.sent += 1


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(notify.time, "sleep", lambda s: None)
    monkeypatch.setattr(notify, "special_pins", lambda img: [])
    monkeypatch.setattr("bot.build.inv_capture", lambda ctx, tag: ctx.caps.append(tag))


def test_reward_panel_is_picked_not_unknown():
    c = Ctx(V(scores={"common/msg_reward": 0.8}))
    assert notify.intel_mission(c) == "picked"
    assert c.taps == ["dismiss"] and not c.caps


def test_no_panel_is_unknown_panel_with_capture(monkeypatch):
    monkeypatch.setattr(IR, "INTEL_PANEL_WAIT_S", 0)
    monkeypatch.setattr(notify, "wait_panel", lambda ctx, timeout=0, interval=0: IR.panel_kind("img", ctx.v))
    c = Ctx(V())
    assert notify.intel_mission(c) == IR.UNKNOWN_PANEL
    assert c.caps == ["intel_" + IR.UNKNOWN_PANEL]


def test_target_not_found_is_unknown_target():
    c = Ctx(V({"intel/btn_go"}))
    assert notify.intel_mission(c) == IR.UNKNOWN_TARGET
    assert "back" in c.taps and c.caps == ["intel_" + IR.UNKNOWN_TARGET]


def test_legion_screen_marches_only_on_predicted_win(monkeypatch):
    v = V({"intel/btn_go", "intel/btn_attack", "rebels/btn_march_out"})
    monkeypatch.setattr(rebels, "pred_win", lambda img: True)
    c = Ctx(v)
    assert notify.intel_mission(c) == "marched" and c.sent == 1 and "rebels/btn_march_out" in c.taps
    monkeypatch.setattr(rebels, "pred_win", lambda img: False)
    c = Ctx(V(v.seen))
    assert notify.intel_mission(c) == "lose_pred" and c.sent == 0 and "rebels/btn_march_out" not in c.taps
    c = Ctx(V(v.seen), full=True)
    assert notify.intel_mission(c) == "no_march"


def test_attack_without_next_screen_is_unknown_attack():
    c = Ctx(V({"intel/btn_go", "intel/btn_attack"}))
    assert notify.intel_mission(c) == IR.UNKNOWN_AFTER


def test_marker_search_uses_center_roi(monkeypatch):
    calls = []

    class V2(V):
        def find(self, img, name, th=None, roi=None, **k):
            if name == "intel/marker_fight":
                calls.append((th, roi))
            return super().find(img, name, th=th, roi=roi)
    notify.intel_mission(Ctx(V2({"intel/btn_go"})))
    assert calls == [(IR.MARKER_TH, IR.MARKER_ROI)]


# ---------- phat lai offline tren anh that (chi local, anh khong co trong git) ----------
SHOTS = sorted(glob.glob(os.path.join("logs", "shots", "*intel_panel_unknown.png")))


@pytest.mark.skipif(not SHOTS, reason="khong co anh logs/shots/*intel_panel_unknown.png")
def test_replay_intel_panel_unknown_shots_are_reward():
    v = Vision("templates")
    kinds = [IR.panel_kind(cv2.imread(f), v) for f in SHOTS]
    assert kinds.count("reward") == len(SHOTS), kinds
