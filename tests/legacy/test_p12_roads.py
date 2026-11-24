"""P12-5 (t56u, live-run-4): cong trinh thieu duong (icon vien gach) -> bam icon -> 'Xac nhan' 20 thoi vang.
Chi phi kim cuong / khong nhan ra -> Huy, khong bam Xac nhan."""
import os
import types

import cv2
import pytest

from bot.modules import construct
from bot.vision import Vision

V = Vision("templates")
F = "tests/fixtures/p12"


def _img(name):
    p = name if "/" in name else f"{F}/{name}.png"
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    return cv2.imread(p)


def test_icon_live_i0_i3():
    p = construct.road_icon(_img("road_icon_i0"), V)          # live4/#0/auto/s181238 (canh nha dang xay)
    assert p and abs(p[0] - 163) <= 4 and abs(p[1] - 168) <= 4
    p = construct.road_icon(_img("road_icon_i3"), V)          # live4/#3/auto/s191903
    assert p and abs(p[0] - 104) <= 4 and abs(p[1] - 308) <= 4


def test_no_icon_on_dialog_frame():
    assert construct.road_icon(_img("road_confirm_i3"), V) is None


def test_confirm_dialog_gold_live():
    img = _img("road_confirm_i3")                              # live4/#3/auto/s193839: 'Xac nhan' thoi vang 20
    b = construct.confirm_dialog(img, V)
    assert b and abs(b[0] - 361) <= 4
    assert construct.gold_cost(img, b)


def test_confirm_owner_t56u():
    own = _img("data/pm-shots/owner-20261124/live4-feedback/xay_duong_xac_nhan_20.png")
    b = V.find(own, construct.ROAD_CONFIRM, th=0.93)
    assert b and construct.gold_cost(own, b)


def test_false_positive_without_cancel():
    assert construct.confirm_dialog(_img("road_falsepos_i3"), V) is None


def _gem(img, b):
    g = img.copy()
    x, y = b[0], b[1]
    g[y + 14:y + 34, x - 40:x] = (230, 200, 60)                # icon kim cuong xanh thay thoi vang
    return g


def test_gem_cost_not_gold():
    img = _img("road_confirm_i3")
    b = construct.confirm_dialog(img, V)
    assert not construct.gold_cost(_gem(img, b), b)


class _Ctx:
    def __init__(self, frames):
        self.frames, self.taps, self.v = list(frames), [], V
        self.cfg = {"construct": {"roads": True}}
        self.debug = []

    def shot(self):
        return self.frames[0] if len(self.frames) == 1 else self.frames.pop(0)

    def ensure_city(self):
        return True

    def tap(self, x, y, wait=1.0):
        self.taps.append((x, y))

    def tap_first(self, names, wait=1.0):
        self.taps.append(names[0])
        return True

    def save_debug(self, n):
        self.debug.append(n)

    def press_back(self):
        self.taps.append("back")


def test_roads_taps_icon_then_confirm():
    icon, dlg = _img("road_icon_i0"), _img("road_confirm_i3")
    blank = icon.copy()
    blank[130:680] = 60
    ctx = _Ctx([icon, dlg, blank])
    assert construct.roads(ctx) == 1
    assert ctx.taps[0] == (163, 168) and ctx.taps[1] == (361, 681)


def test_roads_gem_cancels():
    icon, dlg = _img("road_icon_i0"), _img("road_confirm_i3")
    b = construct.confirm_dialog(dlg, V)
    ctx = _Ctx([icon, _gem(dlg, b), icon])
    assert construct.roads(ctx) == 0
    assert (361, 681) not in ctx.taps and construct.ROAD_CANCEL in ctx.taps and "road_gem_cost" in ctx.debug


def test_roads_off():
    ctx = types.SimpleNamespace(cfg={"construct": {"roads": False}})
    assert construct.roads(ctx) == 0
