"""P12-3 (t57u, live-run-4): VIP @414,175 'nhan 0' vi mo bang 'Tang cap VIP' ma chi tim nut 'Nhan'. Nay bam 'Dung'
hang vat pham diem VIP da co (100 diem VIP x4), lap toi het; KHONG bao gio 'Mua va dung' / nut kim cuong."""
import os
import types

import cv2
import pytest

from bot import ocr, screens
from bot.modules import rewards
from bot.vision import Vision

LIVE = "tests/fixtures/p12/vip_upgrade_i0.png"            # logs/shots/20261124-181950-i0-vip_dot.png (ADB 540x960)
OTHER = "tests/fixtures/p12/vip_other_i0.png"             # 20261124-181955-i0-vip_dot.png (bang khac)
OWNER = "data/pm-shots/owner-20261124/live4-feedback/vip_tang_cap_dung_100.png"
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"
BUY_Y = (340, 520, 610, 700)                               # nut 'Mua va dung' 20 / 1000 / 2000 / 10000


def _img(p):
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    im = cv2.imread(p)
    return cv2.resize(im, (540, 960)) if im.shape[:2] != (960, 540) else im


V = Vision("templates")


def test_finds_dung_row_100_live():
    assert rewards.vip_point_buttons(_img(LIVE), V) == [(452, 416)]


def test_finds_dung_row_owner_t57u():
    b = rewards.vip_point_buttons(_img(OWNER), V)
    assert len(b) == 1 and abs(b[0][0] - 452) <= 4 and abs(b[0][1] - 416) <= 4


def test_never_returns_buy_rows():
    for p in (LIVE, OWNER):
        for _x, y in rewards.vip_point_buttons(_img(p), V):
            assert all(abs(y - by) > 40 for by in BUY_Y)


def test_other_panel_no_buttons():
    assert rewards.vip_point_buttons(_img(OTHER), V) == []    # khong phai bang Tang cap VIP -> khong bam


def test_safe_vip_use_text():
    assert rewards.safe_vip_use("", "Dung")
    assert not rewards.safe_vip_use("Mua va dung", "20")
    assert not rewards.safe_vip_use("", "1000")
    assert not rewards.safe_vip_use("Mua và dùng", "Dung")


def test_ocr_filter_live():
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    assert rewards.vip_point_buttons(_img(LIVE), V, rewards._vip_use_texts) == [(452, 416)]


def test_loop_until_row_gone(monkeypatch):
    live = _img(LIVE)
    gone = live.copy()
    gone[395:440, 400:500] = (40, 40, 40)                  # het vat pham -> hang khong con nut Dung
    frames = {"left": 3}
    taps = []

    def shot():
        return live if frames["left"] > 0 else gone

    def tap(x, y, wait=1.0):
        taps.append((x, y))
        frames["left"] -= 1
    monkeypatch.setattr(rewards, "_vip_use_texts", lambda img, x, y: ("", "Dung"))
    monkeypatch.setattr(screens, "same", lambda a, b, th=2.0: False)
    ctx = types.SimpleNamespace(shot=shot, tap=tap, v=V, tap_tpl=lambda *a, **k: False, dismiss_reward=lambda: None)
    assert rewards.vip_points(ctx) == 3
    assert taps == [(452, 416)] * 3


def test_loop_stops_when_no_effect(monkeypatch):
    live = _img(LIVE)
    taps = []
    monkeypatch.setattr(rewards, "_vip_use_texts", lambda img, x, y: ("", "Dung"))
    monkeypatch.setattr(screens, "same", lambda a, b, th=2.0: True)
    ctx = types.SimpleNamespace(shot=lambda: live, tap=lambda x, y, wait=1.0: taps.append((x, y)), v=V,
                                tap_tpl=lambda *a, **k: False, dismiss_reward=lambda: None)
    assert rewards.vip_points(ctx) == 0 and len(taps) == 2   # 2 lan khong doi -> danh sach den, dung
