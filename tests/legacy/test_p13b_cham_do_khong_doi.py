"""P13b: cham do 'Quan quan tuan' - bam giua-the roi xuong khoang trong duoi nut 'Vao lich thi dau', man khong doi.
Luat: cung diem 2 lan khong doi / moi diem cua cham do khong doi -> danh sach den, khong lap vo han."""
import types

import cv2
import numpy as np

from bot import tapguard
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


def test_points_second_hits_button_not_gap():
    pts = notify.dot_tap_points((346, 862))
    assert pts[0] == (298, 932)          # giua-the cu: khoang trong duoi nut
    assert 190 <= pts[1][0] <= 348 and 860 <= pts[1][1] <= 912   # nut "Vao lich thi dau"


def test_gap_noop_then_button_works():
    base = _base()
    c = FakeCtx(base, lambda x, y: 190 <= x <= 348 and 860 <= y <= 912)
    n = notify.tap_red_dots(c, (0, 800, 540, 100), "card")
    assert n == 1 and len(c.taps) == 2 and c.taps[1][1] < 912


def test_all_noop_blacklists_no_loop():
    base = _base()
    c = FakeCtx(base, lambda x, y: False)
    for _ in range(3):
        notify.tap_red_dots(c, (0, 800, 540, 100), "card")
    assert len(c.taps) == 2                # moi diem 1 lan, lan sau bi chan
    assert c.tap_guard.blocked("card", 346, 862)
