"""P10-3 (live-run-3 15:43): o "Cap" con "1" sau khi go 9/8 (s154328, s154354: ban phim ao "1|  OK"), +/- khong toi,
log "bo (cap da thang cao nhat None)". Xoa sach o -> go -> OK ban phim -> OCR xac nhan -> sai thi +/- co doc lai;
ha cap khong doi hoi lich su thang."""
import os
import types

import cv2
import numpy as np
import pytest

from bot import ocr
from bot.modules import gather, rebels
from bot.vision import Vision

AUTO = "data/pm-shots/owner-20261124/live3/auto"
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def _img(name):
    p = f"{AUTO}/{name}.png"
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    return cv2.imread(p)


def test_keyboard_bar_detected_on_live3():
    assert gather.keyboard_bar(_img("s154354")) == gather.KB_OK
    assert gather.keyboard_bar(_img("s154337")) is None
    assert gather.keyboard_bar(None) is None


@pytest.mark.parametrize("name,lv", [("s154328", 1), ("s154337", 10), ("s154411", 5)])
def test_read_level_live3(name, lv):
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    img = _img(name)
    ctx = types.SimpleNamespace(cfg={"gather": {}}, v=Vision("templates", 0.85), shot=lambda: img)
    assert gather.read_level(ctx) == lv


class Ctx:
    """O Cap dang co so cu 10; go so co the khong an (stuck) -> doc lai."""
    def __init__(self, reads, kb=True):
        self.reads, self.taps, self.typed = list(reads), [], []
        self.cfg = {"gather": {}}
        self.kb = kb
        self.dev = types.SimpleNamespace(type_digits=lambda s: self.typed.append(int(s)),
                                         tap=lambda x, y: self.taps.append(("dev", x, y)))

    def find(self, name, **k):
        return {"gather/btn_level_minus": (68, 758, 1.0), "gather/btn_level_plus": (476, 758, 1.0)}.get(name)

    def tap(self, x, y, wait=1.0):
        self.taps.append((x, y))

    def shot(self):
        img = np.zeros((960, 540, 3), np.uint8)
        if self.kb:
            img[870:950] = 255
        return img


def test_type_over_old_value_presses_keyboard_ok_and_verifies(monkeypatch):
    c = Ctx([9])
    monkeypatch.setattr(gather, "read_level", lambda ctx: c.reads.pop(0) if c.reads else 9)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.type_level(c, 9)
    assert c.typed == [9] and gather.KB_OK in c.taps


def test_wrong_value_fixed_with_plus_minus_and_reread(monkeypatch):
    state = {"v": 1}                                         # live3: o con "1" sau khi go 9

    def tap(x, y):
        state["v"] += 1 if x > 300 else -1
    c = Ctx([])
    c.dev.tap = tap
    monkeypatch.setattr(gather, "read_level", lambda ctx: state["v"])
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.type_level(c, 9) and state["v"] == 9


def test_set_level_tolerates_one_lost_tap(monkeypatch):
    state = {"v": 10, "n": 0}

    def tap(x, y):
        state["n"] += 1
        if state["n"] > 1:                                   # lan cham dau chi dong ban phim
            state["v"] -= 1
    c = Ctx([])
    c.dev.tap = tap
    monkeypatch.setattr(gather, "read_level", lambda ctx: state["v"])
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.set_level(c, 8) and state["v"] == 8


def test_set_level_gives_up_at_floor(monkeypatch):
    c = Ctx([])
    c.dev.tap = lambda x, y: None
    monkeypatch.setattr(gather, "read_level", lambda ctx: 3)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.set_level(c, 1) is False


def test_plus_minus_plan():
    assert gather.plus_minus_plan(10, 8) == ("-", 2)
    assert gather.plus_minus_plan(1, 9) == ("+", 8)
    assert gather.plus_minus_plan(9, 9) is None and gather.plus_minus_plan(None, 9) is None


def test_lower_levels_without_win_history():
    rec = {"best": None, "fail": {"10": 1_000_000}, "legion": None}
    assert rebels.search_levels(rec, start=10, now=1_000_100) == [9, 8, 7]
    assert rebels.target_ok(rec, 9, now=1_000_100) and rebels.target_ok(rec, 8, now=1_000_100)
    why = rebels.target_why(rec, 10, want=9, now=1_000_100)
    assert "o Cap khong doi" in why and "du doan thua" in why and "None" not in why


def test_search_target_stops_when_level_not_set(monkeypatch):
    calls = []

    class C:
        def __init__(self):
            self.cfg = {"rebels": {"type_level": True}, "gather": {}}

        def tap_tpl(self, name, **k):
            calls.append(name)
            return True

        def wait_for(self, *a, **k):
            return True

        def back_out(self, *a):
            calls.append("back")
    monkeypatch.setattr(gather, "select_tab", lambda *a, **k: True)
    monkeypatch.setattr(gather, "type_level", lambda ctx, lv: False)
    assert rebels.search_target(C(), 9) is None
    assert calls.count("gather/btn_search_go") == 0 and "back" in calls   # khong bam Tim kiem voi cap sai
