"""P13-4: icon huy hieu 'can khien' canh dong ho khien = tin hieu warday; khong co -> khong bat khien kieu warday."""
import os
import types

import cv2
import numpy as np
import pytest

from bot.modules import warday

OWNER = "data/owner-feedback/p13/warday_icon_can_khien.png"


def _canvas(with_badge):
    img = np.full((960, 540, 3), (40, 90, 60), np.uint8)       # nen thanh pho xanh
    if with_badge:
        src = cv2.imread(OWNER)
        crop = cv2.resize(src[308:365, 440:495], (26, 26), interpolation=cv2.INTER_AREA)   # anh dien thoai -> ~ADB
        img[64:90, 201:227] = crop
    return img


def test_badge_detected_on_owner_image():
    if not os.path.exists(OWNER):
        pytest.skip("thieu anh chu")
    assert warday.badge_visible(_canvas(True))


def test_no_badge():
    assert not warday.badge_visible(_canvas(False))


class Ctx:
    def __init__(self, img, mode="auto"):
        self.img = img
        self.cfg = {"warday": {"mode": mode, "weekdays": [0, 1, 2, 3, 4, 5, 6]}}
        self.mem = None
        self.dev = types.SimpleNamespace(idx=0)

    def ensure_city(self):
        pass

    def shot(self):
        return self.img


def test_run_skips_shield_without_badge(monkeypatch):
    called = []
    monkeypatch.setattr(warday, "ensure", lambda *a, **k: called.append(1) or 1)
    monkeypatch.setattr(warday, "sniff", lambda ctx, img=None: False)
    monkeypatch.setattr(warday.W, "active_window", lambda *a, **k: object())
    assert warday.run(Ctx(_canvas(False))) == 0 and not called
    warday.run(Ctx(_canvas(False), mode="on"))          # cong tac tay: bat
    assert called
    called.clear()
    if os.path.exists(OWNER):
        warday.run(Ctx(_canvas(True)))
        assert called
