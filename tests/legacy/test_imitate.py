"""Lam theo mau (#3, 2026-11-21): chi cham khi man + manh anh con khop; chan nut ton tien; dung khi het viec."""
import types

import cv2
import numpy as np
import pytest

from bot import imitate


def screen(seed=1, icon=True):
    rng = np.random.default_rng(seed)
    img = (rng.random((960, 540, 3)) * 60).astype(np.uint8)
    img = cv2.GaussianBlur(img, (0, 0), 6)
    if icon:                                         # 'bieu tuong co cham do' chu du an bam
        cv2.rectangle(img, (240, 400), (300, 460), (40, 200, 240), -1)
        cv2.circle(img, (295, 405), 9, (0, 0, 255), -1)
        cv2.putText(img, "A", (255, 445), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
    return img


def index_of(img, x=270, y=430):
    return imitate.Index([imitate.make_demo(img, {"x": x, "y": y, "at": 1.0, "outcome": "changed"}, "k1")])


def test_taps_where_owner_tapped_when_icon_still_there():
    r = imitate.decide(screen(), index_of(screen()))
    assert r and abs(r["x"] - 270) <= 3 and abs(r["y"] - 430) <= 3


def test_no_tap_when_icon_gone_or_screen_differs():
    idx = index_of(screen())
    assert imitate.decide(screen(icon=False), idx) is None          # viec da lam xong (icon / cham do mat)
    other = screen()
    cv2.rectangle(other, (0, 0), (540, 380), (230, 230, 230), -1)   # man khac han (vd bang trang mo ra)
    cv2.rectangle(other, (30, 520), (510, 900), (90, 20, 20), -1)
    assert imitate.decide(other, idx) is None
    assert imitate.decide(screen(), idx, blocked={"k1"}) is None


def test_busy_screens_need_chain_context():
    idx = index_of(screen())
    assert imitate.choose(screen(), idx, "popup")                    # popup: tin hang xom
    assert imitate.choose(screen(), idx, "panel") is None            # bang chuc nang: phai co ngu canh chuoi


@pytest.mark.parametrize(("text", "bad"), [
    ("Mua", True), ("Nạp thẻ", True), ("Tăng tốc ngay", True), ("Huấn luyện ngay", True), ("Mở khóa", True),
    ("99.000 VND", True), ("$4.99", True),
    ("Xây dựng ngay", True), ("Tăng cấp ngay", True), ("Xây dựng ngay\n@ 200", True),
    ("Xây dựng ngay\n@ Miễn phí", False), ("tang cap ngay @ mien phi", False),   # moc mien phi = 0 kim cuong
    ("Nhận ngay", False), ("Nhiệm vụ hằng ngày", False), ("Nhận", False), ("Đóng", False), ("Xác nhận", False),
    ("Huấn luyện", False)])
def test_danger_words(text, bad):
    assert imitate.is_danger(text) is bad


def test_follow_stops_and_blocks_danger(monkeypatch):
    img = screen()
    idx = index_of(img)
    taps = []
    ctx = types.SimpleNamespace(v=None, shot=lambda: img, tap=lambda x, y, **k: taps.append((x, y)),
                                ensure_city=lambda: None)
    monkeypatch.setattr(imitate, "text_near", lambda *a: "Tăng tốc ngay")
    monkeypatch.setattr("bot.screens.identify", lambda im, v: ("popup", None))
    monkeypatch.setattr("bot.screens.same", lambda a, b: True)
    calls = {"n": 0}

    def check():
        calls["n"] += 1
        if calls["n"] > 5:
            raise RuntimeError("vong lap khong dung")
    monkeypatch.setattr("bot.screens.identify", lambda im, v: ("city", None) if calls["n"] > 1 else ("popup", None))
    res = imitate.follow(ctx, idx, {}, check)
    assert taps == [] and res["danger"] == 1          # nut ton tien: khong cham, chan roi dung o thanh pho
