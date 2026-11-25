"""P13d-5: Quan quan tuan - chon ben % cao hon, keo het, khong kim cuong."""
from types import SimpleNamespace

import cv2
import numpy as np

from bot.modules import champion as C


def _img():
    return np.full((960, 540, 3), 30, np.uint8)


def _bar(img, left_w, right_w, x=60, y=300):
    cv2.rectangle(img, (x, y), (x + left_w - 1, y + 14), (30, 30, 190), -1)           # do (BGR)
    cv2.rectangle(img, (x + left_w, y), (x + left_w + right_w - 1, y + 14), (200, 100, 20), -1)  # xanh duong
    return img


def test_pick_side():
    assert C.pick_side(99, 1) == "left"
    assert C.pick_side(1, 99) == "right"
    assert C.pick_side(50, 50) is None
    assert C.pick_side(None, 10) is None


def test_bar_split_left_bigger():
    img = _bar(_img(), 396, 4)
    lp, r = C.bar_split(img)
    assert lp >= 98 and r <= 2 and C.pick_side(lp, r) == "left"


def test_bar_split_right_bigger():
    img = _bar(_img(), 20, 300)
    lp, r = C.bar_split(img)
    assert lp < r and C.pick_side(lp, r) == "right"


def test_handle_found_not_wide_button():
    img = _img()
    cv2.rectangle(img, (120, 500), (160, 540), (140, 140, 20), -1)        # nut keo ~40x40 xanh ngoc
    cv2.rectangle(img, (160, 700), (330, 745), (140, 140, 20), -1)        # nut "Dat cuoc" rong - khong phai nut keo
    h = C.handle_center(img)
    assert h and abs(h[0] - 140) <= 3 and abs(h[1] - 520) <= 3


def test_drag_plan_left_right_and_clamped():
    assert C.drag_plan("left", (140, 520)) == (140, 520, 2, 520)
    x2 = C.drag_plan("right", (140, 520))[2]
    assert x2 == 537 and 0 <= x2 <= 539
    assert C.drag_plan(None, (1, 1)) is None


def test_verified_full_to_side():
    assert C.verified("left", [20000, 0], 20000)
    assert not C.verified("left", [10000, 10000], 20000)
    assert C.verified("right", [0, 20000], 20000)
    assert not C.verified("right", [20000, 0], 20000)
    assert not C.verified("left", [20000, 0], None)


def test_gem_buttons_never_bet(monkeypatch):
    img = _img()
    cv2.rectangle(img, (100, 800), (260, 840), (140, 140, 20), -1)
    monkeypatch.setattr(C.ocr, "text", lambda *a, **k: "Mua 500")
    assert C.bet_buttons(img) == []                                   # chu khong phai "Dat cuoc"
    monkeypatch.setattr(C.ocr, "text", lambda *a, **k: "Dat cuoc 500 kim cuong tang toc")
    assert C.bet_buttons(img) == []                                   # co dau hieu tra phi


def test_bet_button_found_when_text_matches(monkeypatch):
    img = _img()
    cv2.rectangle(img, (180, 800), (340, 840), (140, 140, 20), -1)
    monkeypatch.setattr(C.ocr, "text", lambda *a, **k: "Dat cuoc")
    b = C.bet_buttons(img)
    assert b and 800 <= b[0].y <= 840


def test_dialog_flow_drags_to_larger_side_then_bets(monkeypatch):
    calls = []
    img = _bar(_img(), 396, 4)
    cv2.rectangle(img, (120, 500), (160, 540), (140, 140, 20), -1)
    cv2.rectangle(img, (180, 640), (340, 680), (140, 140, 20), -1)
    ctx = SimpleNamespace(shot=lambda: img, save_debug=lambda *a: None,
                          dev=SimpleNamespace(swipe=lambda *a, **k: calls.append(("swipe", a))),
                          tap=lambda x, y, wait=0: calls.append(("tap", x, y)))

    def fake_text(im, roi, whitelist=None, **k):
        if whitelist:
            return "20000 0"
        return "So huu 20000" if roi[3] == 34 else "Dat cuoc"
    monkeypatch.setattr(C.ocr, "text", fake_text)
    monkeypatch.setattr(C.time, "sleep", lambda s: None)
    assert C._bet_dialog(ctx) == 1
    sw = next(c for c in calls if c[0] == "swipe")[1]
    assert sw[2] < sw[0]                                              # keo sang TRAI (ben 99%)
    assert calls[-1][0] == "tap"


def test_no_owned_label_no_bet(monkeypatch):
    img = _bar(_img(), 396, 4)
    cv2.rectangle(img, (120, 500), (160, 540), (140, 140, 20), -1)
    ctx = SimpleNamespace(shot=lambda: img, save_debug=lambda *a: None,
                          dev=SimpleNamespace(swipe=lambda *a, **k: (_ for _ in ()).throw(AssertionError("keo"))),
                          tap=lambda *a, **k: (_ for _ in ()).throw(AssertionError("cham")))
    monkeypatch.setattr(C.ocr, "text", lambda *a, **k: "20000")        # khong co chu "So huu"
    assert C._bet_dialog(ctx) == 0
