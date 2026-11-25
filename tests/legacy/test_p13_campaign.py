"""P13-10: Chien dich - nut thoat/bo qua tran, man Thang loi -> 'Tiep tuc Chien dich' (khong 'Tro lai'); cong do -N ban
den khi duong roi lao vao (anh runner_cong_do / runner_ban_cong_do_tang_quan)."""
import os

import cv2
import numpy as np
import pytest

from bot import steer
from bot.modules import campaign
from bot.vision import Vision

OWN = "data/owner-feedback/p13/"


def _vision():
    return Vision("templates")


def _img(name):
    p = OWN + name
    if not os.path.exists(p):
        pytest.skip("thieu anh chu")
    return cv2.imread(p)


def _canvas(src, x, y):
    """Dat anh dien thoai len khung 540x960 (goc tren-trai) de khop mau."""
    c = np.zeros((960, 540, 3), np.uint8)
    h, w = min(src.shape[0], 960 - y), min(src.shape[1], 540 - x)
    c[y:y + h, x:x + w] = src[:h, :w]
    return c


def test_victory_screen_continue_found_back_not_tapped():
    v = _vision()
    img = _img("chien_dich_tiep_tuc.png")
    canvas = _canvas(img, 0, 330)                     # man Thang loi nam giua man 540x960
    b = v.best(canvas, "campaign/btn_continue")
    assert b and b[2] >= 0.9 and b[0] > 270            # nut phai (Tiep tuc), khong phai 'Tro lai' ben trai
    bb = v.best(canvas, "campaign/btn_back_victory")
    assert bb and bb[0] < 270
    assert steer.result_of(v, canvas) == "win"


def test_skip_button_found_bottom_right():
    v = _vision()
    img = _img("chien_dich_nut_bo_qua.png")
    canvas = _canvas(img, 0, 0)
    b = v.best(canvas, "campaign/btn_skip_battle", roi=campaign.SKIP_ROI)
    assert b and b[2] >= 0.9 and b[0] > 430 and b[1] > 720


class V2:
    def __init__(self, found):
        self.found = found

    def has(self, n):
        return True

    def find(self, img, name, **k):
        return (500, 790) if name in self.found else None


class Ctx:
    def __init__(self, found):
        self.v, self.taps, self.cfg = V2(found), [], {}

    def shot(self):
        return None

    def tap_tpl(self, name, **k):
        self.taps.append(name)
        return True


def test_skip_taps_button_when_present():
    c = Ctx({"campaign/btn_skip_battle"})
    assert campaign.skip_turn_battle(c, wait_s=1) is True and c.taps == ["campaign/btn_skip_battle"]
    c2 = Ctx(set())
    assert campaign.skip_turn_battle(c2, wait_s=0.6) is False and c2.taps == []


def test_close_result_prefers_continue_never_back():
    c = Ctx({"campaign/btn_continue"})
    campaign.close_result(c)
    assert c.taps == ["campaign/btn_continue"]


def test_red_gate_minus2_shoot_then_dash_in():
    # -2 con xa (cach doi quan > ~4 s): ban den duong roi lao vao; gan hon: ne; so lon: khong
    far_cy = steer.SQUAD_Y - 6 * steer.VY_S
    near_cy = steer.SQUAD_Y - 1 * steer.VY_S
    assert steer.flip_ok(-2, None, far_cy)
    assert not steer.flip_ok(-2, None, near_cy)
    assert not steer.flip_ok(-30, None, steer.SQUAD_Y - 6 * steer.VY_S)
    assert not steer.flip_ok(-5, None, 200)                  # cong lon chua do toc do -> giu luat P7-8
    assert steer.flip_ok(3, None, near_cy)                   # da duong ("+2") -> lao vao nhu buff
    assert not steer.flip_ok(-2, -1.0, far_cy)               # do duoc: dang giam (khong bi ban) -> ne
    assert steer.flip_ok(-2, 2.0, steer.SQUAD_Y - 2 * steer.VY_S)    # ban nhanh 2/giay -> kip
