import cv2
import numpy as np

from bot.modules import research


def test_pick_recommended_prefers_glowing_node():
    img = np.full((960, 540, 3), 40, np.uint8)
    cx, cy = 385 - 55, 185 - 45                  # tam node theo quy uoc badge (x-55, y-45)
    cv2.circle(img, (cx - 20, cy - 25), 6, (255, 255, 235), -1)     # vet sang xanh-trang tren vanh node
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hsv[cy - 31:cy - 19, cx - 26:cx - 14] = (104, 60, 255)
    img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    cands = [(120, 200, 2, 3), (385, 185, 0, 3), (385, 400, 0, 3)]
    assert research.pick_recommended(img, cands) == (385, 185, 0, 3)
    assert research.pick_recommended(np.full((960, 540, 3), 40, np.uint8), cands) is None
