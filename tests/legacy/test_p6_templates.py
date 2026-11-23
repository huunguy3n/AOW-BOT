"""Anh mau moi tu #1 (2026-11-23): btn_research o giua man, nguong node_panel / btn_join 0,9, Hiep uoc row_8h,
msg_not_found; hop thoai 'Roi tro choi?' luon Huy. Anh goc data/pm-shots/adb (khong co trong git -> bo qua)."""
import os
import types

import cv2
import pytest

from bot import tplcheck
from bot.ctx import Ctx
from bot.modules import rebels, research
from bot.vision import Vision

SHOTS = os.path.join("data", "pm-shots", "adb")


def shot(name):
    p = os.path.join(SHOTS, name)
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p} (chi co tren may chu du an)")
    return cv2.imread(p)


@pytest.fixture(scope="module")
def v():
    return Vision("templates")


def test_btn_roi_follows_panel():
    assert research.btn_roi(None) == research.BTN_ROI
    x, y, _w, h = research.btn_roi((489, 282, 1.0))
    assert y <= 491 - 12 and y + h == 960 and x <= 385 - 54
    x, y, _w, h = research.BTN_ROI
    assert y <= 491 - 12 and y + h <= 960            # khong thay khung: 2/3 duoi van chua nut o y491


def test_research_button_found_mid_screen(v):
    img = shot("14_node_panel_unfinished.png")
    ctx = types.SimpleNamespace(v=v)
    got = research.start_buttons(ctx, img)
    assert got and abs(got[0][0] - 385) <= 3 and abs(got[0][1] - 491) <= 3


@pytest.mark.parametrize("name, panel", [("11_node_done_panel.png", True), ("14_node_panel_unfinished.png", True),
                                         ("15_research_tap_msg.png", False), ("16_research_tap_msg_b.png", False)])
def test_node_panel_threshold(v, name, panel):
    assert bool(v.find(shot(name), research.TPL_PANEL, th=research.PANEL_TH)) is panel


def test_no_research_button_on_queue_full_dialog(v):
    ctx = types.SimpleNamespace(v=v)
    assert research.start_buttons(ctx, shot("15_research_tap_msg.png")) == []


@pytest.mark.parametrize("name, n", [("20_alliance_suvu.png", 2), ("23_search_panel.png", 0),
                                     ("24_search_food_max.png", 0), ("saved_hospital_wounded_i0_20261122.png", 0)])
def test_join_button_only_on_rally_card(v, name, n):
    hits = v.find_all(shot(name), "rebels/btn_join", th=rebels.JOIN_TH, roi=rebels.JOIN_ROI)
    assert len(hits) >= n if n else hits == []


def test_peace_row_and_not_found_msg(v):
    p = v.find(shot("18_shield_panel.png"), "defense/row_8h", th=0.9)
    assert p and abs(p[1] - 191) <= 2
    assert v.find(shot("30_search_alloy8full_2.png"), "gather/msg_not_found")
    assert not v.find(shot("30_search_alloy8full_1.png"), "gather/msg_not_found")


class FakeV:
    def __init__(self, exit_at=None):
        self.exit_at = exit_at

    def find(self, img, name, th=None, roi=None):
        if name == "common/btn_cancel_exit" and self.exit_at:
            p, self.exit_at = self.exit_at, None
            return p
        return None

    def has(self, name):
        return True


def test_exit_dialog_always_cancelled_before_confirm():
    """dismiss_reward co 'Xac nhan' trong REWARD_CLOSERS: tren hop thoai thoat phai bam Huy, khong phai Xac nhan."""
    c = Ctx.__new__(Ctx)
    c.v, c.taps = FakeV((300, 600, 0.95)), []
    c.shot = lambda: "img"
    c.tap = lambda x, y, wait=1.0, tpl=None: c.taps.append((x, y, tpl))
    c.dev = types.SimpleNamespace(idx=1)
    c.W, c.H = 540, 960
    c.dismiss_reward(rounds=2)
    assert c.taps == [(300, 600, "common/btn_cancel_exit")]
    assert c.cancel_exit("img") is False                 # het hop thoai -> khong bam gi them


def test_train_max_template_not_required_by_default():
    assert "train/btn_max" not in tplcheck.needed({"train": {}})
    assert "train/btn_max" in tplcheck.needed({"train": {"use_max_button": True}})
