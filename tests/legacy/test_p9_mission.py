"""P9-4 (chu du an 2026-11-24, live-run-2): Su menh - chan follower chiem man Su menh / cua hang xuc xac; ruong moc
diem lap toi het; cua hang xuc xac chi nut "Mien phi" co cham do; khong ban xuc xac / goi ₫."""
import os
import types

import cv2
import numpy as np
import pytest

from bot import buttons, ocr, screens
from bot.badges import red_dots
from bot.modules import daily, mission, tutorial
from bot.vision import Vision

AUTO = "data/pm-shots/owner-20261124/live2/auto"
FB = "data/pm-shots/owner-20261124/live2-feedback"
ADB = "data/pm-shots/owner-20261124/p8-adb"
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def _img(path):
    if not os.path.exists(path):
        pytest.skip(f"thieu anh {path}")
    return cv2.imread(path)


@pytest.fixture(scope="module")
def v():
    return Vision("templates", 0.85)


# ---------- follower khong chiem man Su menh ----------
@pytest.mark.parametrize("f,tpl", [("s110312", "mission/title"), ("s110320", "mission/title"),
                                   ("s110328", "mission/shop_title")])
def test_no_follow_on_mission_screens(v, f, tpl):
    img = _img(f"{AUTO}/{f}.png")
    assert tutorial.no_follow_screen(v, img) == tpl
    assert tutorial.guide_visible(v, img) is None


def test_follow_still_allowed_on_city(v):
    img = _img(f"{AUTO}/s110303.png")
    assert tutorial.no_follow_screen(v, img) is None


def test_follow_loop_stops_on_mission(monkeypatch, v):
    img = _img(f"{AUTO}/s110328.png")
    called = []
    monkeypatch.setattr(tutorial, "decide", lambda *a, **k: called.append(1) or ("tap", 163, 589, "x"))
    ctx = types.SimpleNamespace(v=v, shot=lambda: img, cfg={}, store=None, tap=lambda *a, **k: called.append("tap"))
    assert tutorial.run(ctx, max_steps=3, follow=True) == "idle"
    assert called == []                          # khong goi decide, khong cham (163,589) canh goi ₫125000


# ---------- cua hang xuc xac ----------
def test_dice_shop_only_free_button_with_dot():
    img = _img(f"{AUTO}/s110328.png")
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    bs = buttons.with_text(img, mission.FREE_RX, mission.SHOP_ROI)
    got = mission.free_with_dot(bs, red_dots(img, mission.SHOP_ROI))
    assert [(b.x, b.y) for b in got] == [(440, 271)]
    assert mission.free_with_dot(bs, []) == []                  # khong cham do (1/1 da nhan) -> khong bam
    for b in buttons.find(img, mission.SHOP_ROI):
        if b.y > 400:                                           # nut ₫125000 / ₫250000 / ₫500000
            assert b not in got


def test_dice_shop_free_taps_only_allowed(monkeypatch):
    taps = []
    B = buttons.Button(440, 271, 84, 32, "claim", 85, "mien phi")
    state = {"left": 1}
    monkeypatch.setattr(buttons, "with_text", lambda img, rx, roi=None, kinds=None: [B] if state["left"] else [])
    monkeypatch.setattr(mission, "red_dots", lambda img, roi=None: [(482, 258)])

    def tap(x, y, wait=1.0):
        taps.append((x, y))
        state["left"] = 0
    ctx = types.SimpleNamespace(shot=lambda: None, tap=tap, dismiss_reward=lambda: None)
    assert mission.dice_shop_free(ctx) == 1 and taps == [(440, 271)]


def test_hunt_allow_zone_excludes_dice_board():
    assert mission.tap_ok("hunt", 501, 311)                    # icon xe day
    for p in ((270, 640), (500, 912), (190, 912), (95, 210), (270, 210), (270, 735)):
        assert not mission.tap_ok("hunt", *p), p               # ban xuc xac, nut +, tab San kho bau / The thong hanh
    assert not mission.tap_ok("main", 270, 210)                # tab The thong hanh
    assert mission.tap_ok("hunt_nav", 75, 125) and not mission.tap_ok("hunt_nav", 270, 640)


def test_cart_dot_on_adb(v):
    img = _img(f"{ADB}/mis1.png")
    c = v.find(img, "mission/cart", roi=mission.CART_ROI)
    assert c and abs(c[0] - 501) <= 3 and abs(c[1] - 311) <= 3
    assert mission.cart_dot(img, c)
    blank = img.copy()
    cv2.circle(blank, (522, 288), 9, (40, 30, 30), -1)
    assert not mission.cart_dot(blank, c)


# ---------- ruong moc diem ----------
def _owner_board():
    img = _img(f"{FB}/nhiem_vu_hang_ngay_ruong_50_phat_sang.png")
    pad = np.zeros((960, 540, 3), np.uint8)
    pad[:img.shape[0], :img.shape[1]] = img
    return pad


def test_milestone_targets_owner_image():
    img = _owner_board()
    pts = daily.ready_chests(img)
    assert len(pts) == 3
    t = daily.milestone_targets(pts, 55, img)
    assert daily.milestone_of(t[0][0]) == 50                   # ruong 50 dang sang -> truoc
    assert {daily.milestone_of(p[0]) for p in t} == {10, 30, 50}
    assert [daily.milestone_of(p[0]) for p in daily.milestone_targets(pts, 25, img)] == [10]
    assert daily.milestone_of(388) == 80 and daily.milestone_of(600) is None


def test_claim_chests_continues_after_claimed_chest(monkeypatch):
    """Ruong 10 da nhan (khong co nut) -> KHONG dung, thu tiep 30, 50 (truoc P9 break o ruong dau)."""
    pts = [(181, 290), (251, 290), (321, 286)]
    claimable = {321}
    last = {"x": None}
    monkeypatch.setattr(daily, "read_score", lambda img: 55)
    monkeypatch.setattr(daily, "ready_chests", lambda img: list(pts))
    monkeypatch.setattr(screens, "same", lambda a, b: False)

    def tap(x, y):
        last["x"] = x
        return True
    ctx = types.SimpleNamespace(
        v=types.SimpleNamespace(list=lambda p: [], find_all=lambda img, c: []),
        shot=lambda: np.zeros((960, 540, 3), np.uint8),
        tap_tpl=lambda name, **k: last["x"] in claimable,
        claim_buttons=lambda max_taps=1: 0, dismiss_reward=lambda: None,
        tap_first=lambda *a, **k: None, POPUP_CLOSERS=[])
    assert daily.claim_chests(ctx, by_color=True, tap=tap) == 1
