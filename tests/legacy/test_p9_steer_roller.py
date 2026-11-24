"""P9-10 (chu du an 2026-11-24, runner_ne_vat_can.png): trong tran chay duong / chien dich phai NE con lan gai (lua che
mau -> anh mau steer/block_roller*) va NHAT buff "+N" mui ten xanh la; cong do giu luat P7-8 (lat kip -> lao vao)."""
import os

import cv2
import pytest

from bot import steer
from bot.vision import Vision

OWNER = "data/pm-shots/owner-20261124/live2-feedback/runner_ne_vat_can.png"
ADB = "logs/steer/1795203553_024.jpg"


def _img(p):
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    return cv2.resize(cv2.imread(p), (540, 960))


@pytest.fixture(scope="module")
def v():
    vis = Vision("templates", 0.82)
    if not vis.list("steer/block_"):
        pytest.skip("thieu templates/steer/block_*.png")
    return vis


def _det(v, img):
    d = steer.detect(img)
    steer.merge_blocks(d, steer.template_blocks(v, img))
    return d


def test_roller_found_under_fire_owner_frame(v):
    d = _det(v, _img(OWNER))
    assert any(130 <= cx <= 300 and 380 <= cy <= 470 for cx, cy, _ in d["block"])   # con lan 142-290 x 388-465


def test_roller_found_adb_frame(v):
    d = _det(v, _img(ADB))
    assert any(20 <= cx <= 180 and 410 <= cy <= 500 for cx, cy, _ in d["block"])


def test_no_roller_on_plain_frames(v):
    for p in ("logs/steer/000.jpg", "logs/steer/002.jpg"):
        if os.path.exists(p):
            assert steer.template_blocks(v, cv2.imread(p)) == []


def test_owner_frame_moves_out_of_roller_lane(v):
    """Doi quan dang o lan con lan (x ~240) -> KHONG dung im: lan dich nam ngoai than con lan."""
    d = _det(v, _img(OWNER))
    tx, _ = steer.choose(d, 240)
    assert tx >= 216 + steer.ROLLER_W // 2 or tx <= 216 - steer.ROLLER_W // 2
    assert abs(tx - 240) >= 60


def test_green_arrow_soldier_buff_detected():
    d = steer.detect(_img(OWNER))
    assert any(abs(cx - 95) <= 20 and abs(cy - 322) <= 25 for cx, cy, _ in d["buff"])   # "+5" mui ten xanh la


def test_simulated_roller_dodge_both_sides():
    """Mo phong: con lan ngay truoc mat -> ne sang ben rong hon; khong co gi -> dung yen (it di chuyen)."""
    empty = {"buff": [], "nerf": [], "danger": [], "enemy": [], "block": [], "target": []}
    assert steer.choose(empty, 270)[0] == 270
    left = dict(empty, block=[(150, 450, steer.ROLLER_W)])
    assert steer.choose(left, 160)[0] >= 150 + steer.ROLLER_W // 2
    right = dict(empty, block=[(390, 450, steer.ROLLER_W)])
    assert steer.choose(right, 380)[0] <= 390 - steer.ROLLER_W // 2


def test_buff_beside_roller_picked_without_crossing():
    """Buff ben phai con lan (cung do cao) -> nhat buff, khong lao vao con lan."""
    det = {"buff": [(400, 420, 80)], "nerf": [], "danger": [], "enemy": [], "block": [(200, 440, steer.ROLLER_W)],
           "target": []}
    tx, _ = steer.choose(det, 300)
    assert abs(tx - 400) <= 30


def test_gate_rule_kept_flip_or_avoid():
    """P7-8 giu nguyen: cong -3 dang tang 4/s con xa -> lat kip -> lao vao; cong -40 cham -> ne."""
    assert steer.flip_ok(-3, 4.0, 200)
    assert not steer.flip_ok(-40, 1.0, 500)
    det = {"buff": [], "nerf": [], "danger": [], "enemy": [], "block": [], "target": [], "flip": [(400, 400, 120)]}
    assert abs(steer.choose(det, 270)[0] - 400) <= 30
    det = {"buff": [], "nerf": [(270, 520, 120)], "danger": [], "enemy": [], "block": [], "target": []}
    assert abs(steer.choose(det, 270)[0] - 270) >= 60


def test_merge_blocks_dedupes():
    det = {"block": [(100, 400, 150)]}
    steer.merge_blocks(det, [(120, 410, 170), (400, 300, 170)])
    assert det["block"] == [(100, 400, 150), (400, 300, 170)]
