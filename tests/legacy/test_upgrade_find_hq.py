import os

import cv2
import numpy as np

from bot.modules import upgrade

TPL = os.path.join(os.path.dirname(__file__), "..", "..", "templates", "build")


def _load(n):
    return cv2.imread(os.path.join(TPL, n + ".png"))


def test_find_hq_tren_khung_co_huy_hieu():
    t = _load("hq_emblem_a")
    rng = np.random.default_rng(1)
    frame = rng.integers(60, 120, (960, 540, 3), dtype=np.uint8)
    frame[300:300 + t.shape[0], 200:200 + t.shape[1]] = t
    hit = upgrade.find_hq(frame, [_load("hq_emblem_a"), _load("hq_emblem_b")])
    assert hit and abs(hit[0] - (200 + t.shape[1] // 2)) <= 2 and abs(hit[1] - (300 + t.shape[0] // 2)) <= 2


def test_find_hq_khong_co_nha_chinh():
    rng = np.random.default_rng(2)
    frame = rng.integers(60, 120, (960, 540, 3), dtype=np.uint8)
    assert upgrade.find_hq(frame, [_load("hq_emblem_a"), _load("hq_emblem_b"), None]) is None
