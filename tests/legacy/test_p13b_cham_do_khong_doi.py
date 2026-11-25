"""P13b: cham do 'Quan quan tuan' - bam giua-the roi xuong khoang trong duoi nut 'Vao lich thi dau', man khong doi.
Luat: cung diem 2 lan khong doi / moi diem cua cham do khong doi -> danh sach den, khong lap vo han."""
import types

import cv2
import numpy as np

from bot import device, tapguard
from bot.device import clamp_xy
from bot.modules import notify

IMG = "data/owner-feedback/p13/quan_quan_tuan_bam_sai.png"


class FakeCtx:
    def __init__(self, base, react):
        self.base, self.react, self.taps, self.tap_guard = base, react, [], tapguard.TapGuard()
        self.cur = base
        self.v = types.SimpleNamespace()

    def shot(self):
        return self.cur.copy()

    def tap(self, x, y, wait=0):
        self.taps.append((x, y))
        if self.react(x, y):
            self.cur = np.full_like(self.base, 200)

    def dismiss_reward(self):
        self.cur = self.base


def _base():
    img = cv2.imread(IMG)
    if img is None:
        img = np.zeros((960, 540, 3), np.uint8)
        cv2.circle(img, (346, 862), 8, (0, 0, 230), -1)
    return img


def test_point_hits_button_body_not_gap():
    base = _base()
    pts = notify.dot_tap_points(base, (346, 862))
    assert len(pts) == 1
    x, y = pts[0]
    assert 190 <= x <= 348 and 860 <= y <= 912     # than nut, khong phai khoang trong (298,932)
    assert (x, y) != (298, 932)


def test_gap_noop_then_button_works():
    base = _base()
    c = FakeCtx(base, lambda x, y: 190 <= x <= 348 and 860 <= y <= 912)
    n = notify.tap_red_dots(c, (0, 800, 540, 100), "card")
    assert n == 1 and len(c.taps) == 1 and c.taps[0][1] < 912


def test_no_object_no_blind_offset():
    img = np.zeros((960, 540, 3), np.uint8)
    assert notify.dot_tap_points(img, (346, 862)) == []


def _box_img(top):
    img = np.zeros((960, 540, 3), np.uint8)
    cv2.rectangle(img, (190, top), (348, top + 45), (200, 180, 40), 3)
    return img


def test_points_always_inside_screen_near_bottom():
    for top in (890, 900, 915):
        img = _box_img(top)
        for dot in ((346, top + 2), (346, 940), (346, 958), (539, 959)):
            for x, y in notify.dot_tap_points(img, dot):
                assert 0 <= x <= 539 and 0 <= y <= 959


def test_clamp_xy():
    assert clamp_xy(161, 964) == (161, 959)
    assert clamp_xy(-5, 2000) == (0, 959)
    assert clamp_xy(600, -1) == (539, 0)
    assert clamp_xy(100, 100) == (100, 100)


def test_device_tap_clamps():
    d = device.Device.__new__(device.Device)
    sent = []
    d._cmd = lambda *a: sent.append(a)
    d._mine = lambda *a: None
    d.tap(161, 964)
    d.swipe(10, 970, 600, 5)
    assert sent[0][-2:] == (161, 959)
    assert sent[1][3:7] == (10, 959, 539, 5)


def test_all_noop_blacklists_no_loop():
    base = _base()
    c = FakeCtx(base, lambda x, y: False)
    for _ in range(3):
        notify.tap_red_dots(c, (0, 800, 540, 100), "card")
    assert len(c.taps) == 1                # 1 diem, lan sau bi chan, lan sau bi chan
    assert c.tap_guard.blocked("card", 346, 862)
