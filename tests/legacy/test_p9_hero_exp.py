"""P9-8 (chu du an 2026-11-24, anh tuong_1..5): tang cap tuong - the mui ten xanh lon; thieu EXP -> o EXP -> "Dung" 1
lan -> "Dung tat ca" tung hang; KHONG BAO GIO hang "Dung dao cu" (kim cuong); lap toi het cham do."""
import os
import types

import cv2
import pytest

from bot import buttons, ocr
from bot.modules import hero_up as H
from bot.modules import notify

FB = "data/pm-shots/owner-20261124/live2-feedback"
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def _img(name):
    p = f"{FB}/{name}.png"
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    return cv2.imread(p)


def B(x, y, text, kind="claim"):
    return buttons.Button(x, y, 80, 30, kind, 85, text)


def test_big_arrows_only_levelup_not_story():
    pts = H.big_arrows(_img("tuong_1_danh_sach_mui_ten_xanh"))
    assert len(pts) == 4                                   # 4 mui ten lon; mui ten nho canh quyen sach (Cau chuyen) bo
    assert all(abs(x - 513) <= 3 or abs(x - 113) <= 3 for x, _ in pts)


def test_exp_short_red_cost():
    assert H.exp_short(_img("tuong_3_thieu_exp"), (272, 812))


def test_plan_prefers_use_all_and_never_diamond():
    btns = [B(333, 226, "dung tat ca"), B(436, 226, "dung"), B(445, 692, "3", "go")]
    assert H.plan_exp_taps(btns, 640, used_one=False).text == "dung tat ca"
    only = [B(455, 323, "dung"), B(455, 414, "dung")]
    assert H.plan_exp_taps(only, 740, used_one=False).y == 323    # "Dung" 1 lan cho hien "Dung tat ca"
    assert H.plan_exp_taps(only, 740, used_one=True) is None      # khong bam "Dung" lan 2
    below = [B(333, 700, "dung tat ca"), B(455, 760, "dung")]     # duoi dong "Dung dao cu"
    assert H.plan_exp_taps(below, 640, used_one=False) is None
    assert H.plan_exp_taps([B(450, 300, "mua")], None, False) is None


@pytest.mark.parametrize("name,first_y,cut", [("tuong_4_kho_exp_dung", 323, 740), ("tuong_5_dung_tat_ca", 226, 640)])
def test_owner_exp_panels(name, first_y, cut):
    img = _img(name)
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    y = H.dao_cu_y(img)
    assert y is not None and abs(y - cut) <= 40
    b = H.plan_exp_taps(buttons.with_text(img, r"d\w{0,2}ng"), y, used_one=False)
    assert b is not None and abs(b.y - first_y) <= 5 and b.y < y


def test_use_exp_sequence_dung_then_all_rows(monkeypatch):
    """Bang EXP: lan 1 chi co "Dung" -> bam 1 lan; sau do hien "Dung tat ca" 3 hang -> bam tung hang; khong cham dong
    kim cuong (y 760)."""
    screens = [[B(455, 323, "dung"), B(455, 414, "dung")],
               [B(333, 226, "dung tat ca"), B(333, 317, "dung tat ca"), B(333, 408, "dung tat ca"),
                B(436, 226, "dung")]]
    state = {"i": 0}
    monkeypatch.setattr(buttons, "with_text", lambda img, rx, roi=None, kinds=None: screens[min(state["i"], 1)])
    monkeypatch.setattr(H, "dao_cu_y", lambda img: 740)
    taps = []

    def tap(x, y, wait=1.0):
        taps.append((x, y))
        state["i"] += 1
    ctx = types.SimpleNamespace(shot=lambda: None, tap=tap, tap_first=lambda *a, **k: None, POPUP_CLOSERS=[])
    assert H.use_exp(ctx) == 4
    assert taps == [(455, 323), (333, 226), (333, 317), (333, 408)]
    assert all(y < 740 for _, y in taps)


def test_hero_detail_refills_exp_when_no_dot(monkeypatch):
    calls = []
    lv = iter([0, 2, 0, 0])
    monkeypatch.setattr(notify, "_hero_levelup", lambda ctx: calls.append("lv") or next(lv))
    monkeypatch.setattr(notify, "_hero_star", lambda ctx: 0)
    monkeypatch.setattr(notify, "hero_story", lambda ctx: 0)
    exp = iter([3, 0])
    monkeypatch.setattr(notify, "_hero_exp", lambda ctx: calls.append("exp") or next(exp))
    # vong 1: khong cham do -> dung EXP (3); vong 2: Tang cap (2); vong 3: het EXP thieu -> dung
    assert notify.hero_detail(types.SimpleNamespace()) == 5
    assert calls == ["lv", "exp", "lv", "lv", "exp"]


def test_hero_exp_skips_when_button_has_dot(monkeypatch):
    """Nut Tang cap con cham do -> _hero_levelup lo, khong mo bang EXP."""
    monkeypatch.setattr(notify, "_dot_near", lambda img, b: True)
    called = []
    monkeypatch.setattr(H, "refill_and_level", lambda ctx, b: called.append(1) or 1)
    v = types.SimpleNamespace(find=lambda img, n: (272, 812))
    ctx = types.SimpleNamespace(shot=lambda: "img", _img="img", v=v)
    assert notify._hero_exp(ctx) == 0 and not called
