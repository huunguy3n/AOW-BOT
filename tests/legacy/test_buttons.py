"""Do nut theo mau + chu (bot/buttons.py): nut Nhan / Den khong can anh mau tung bang."""
import types

import cv2
import numpy as np
import pytest

from bot import buttons
from bot.ctx import Ctx


def canvas(*rects):
    img = np.full((960, 540, 3), 40, np.uint8)
    for (x, y, w, h), hsv in rects:
        bgr = cv2.cvtColor(np.uint8([[hsv]]), cv2.COLOR_HSV2BGR)[0, 0]
        img[y:y + h, x:x + w] = bgr
    return img


def test_find_classifies_claim_and_go_by_hue():
    img = canvas(((380, 350, 90, 36), (86, 252, 110)), ((380, 460, 90, 36), (97, 252, 110)),
                 ((20, 20, 30, 30), (86, 252, 110)))               # o vuong nho: khong phai nut
    got = [(b.kind, b.y) for b in buttons.find(img)]
    assert got == [("claim", 368), ("go", 478)]


@pytest.mark.parametrize("text, ok", [
    ("Nhận", True), ("nhan toan bo", True), ("nhen", True), ("Nhận ngay", True),
    ("Chiêu mộ", False), ("Đóng", False), ("@ 1000", False), ("", False),
    ("Mua nhan", False), ("Huấn luyện ngay", False), ("Tăng tốc", False),
])
def test_claim_text(text, ok):
    assert buttons.is_claim_text(text) is ok


def test_claim_buttons_skips_button_that_does_nothing(monkeypatch):
    b = buttons.Button(270, 855, 200, 40, "claim", 86.7, "nhan")
    frames = iter([np.zeros((10, 10, 3), np.uint8)] * 2 + [np.full((10, 10, 3), 200, np.uint8)] * 10)
    monkeypatch.setattr(buttons, "claims", lambda img, roi=None: [b])
    c = types.SimpleNamespace(shot=lambda: next(frames), dev=types.SimpleNamespace(tap=lambda x, y: None),
                              _exp_begin=lambda *a: None, _after_tap=lambda w: None, wait_scale=1.0,
                              dismiss_reward=lambda: None)
    assert Ctx.claim_buttons(c, max_taps=3) == 0          # man khong doi sau khi cham -> khong bam lai mai
