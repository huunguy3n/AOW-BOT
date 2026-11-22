import os

import cv2
import pytest

from bot.modules import reddots
from bot.vision import Vision

SHOT = os.path.join(os.path.dirname(__file__), "..", "fixtures", "reddots_left_i1.png")
TPL = os.path.join(os.path.dirname(__file__), "..", "..", "templates")


@pytest.mark.fixtures
def test_gift_badge_included_and_roofs_still_excluded():
    img = cv2.imread(SHOT)
    if img is None:
        pytest.skip("thieu anh fixture")
    v = Vision(TPL, 0.82)
    dots = reddots._left(img, v)
    assert (456, 797) in dots                                    # so 60 tren icon qua lien minh (anh #1 2026-11-22)
    assert (406, 740) not in dots and (304, 791) not in dots      # mai do cong trinh khong phai cham do
    assert (456, 797) not in reddots._left(img)                   # khong co Vision -> hanh vi cu
