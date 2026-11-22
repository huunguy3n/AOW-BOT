import cv2
import numpy as np

from bot.modules import construct


def _frame(grass_box):
    """Khung gia: nen toi, 1 mang co (mau cua o luoi) -> spot_candidates phai chon trong mang do."""
    img = np.full((960, 540, 3), 20, np.uint8)
    hsv = np.full((960, 540, 3), (35, 160, 110), np.uint8)
    x1, y1, x2, y2 = grass_box
    img[y1:y2, x1:x2] = cv2.cvtColor(hsv[y1:y2, x1:x2], cv2.COLOR_HSV2BGR)
    return img


def test_spot_candidates_chon_trong_mang_co():
    img = _frame((90, 400, 330, 600))
    c = construct.spot_candidates(img, (300, 100, 200, 100), n=3)
    assert c and 90 <= c[0][0] <= 330 and 400 <= c[0][1] <= 600


def test_spot_candidates_tranh_diem_da_thu_va_het_co():
    img = _frame((90, 400, 330, 600))
    a = construct.spot_candidates(img, (300, 100, 200, 100), n=1)[0]
    b = construct.spot_candidates(img, (300, 100, 200, 100), avoid=[a[:2]], n=1)
    assert not b or abs(b[0][0] - a[0]) + abs(b[0][1] - a[1]) >= 45
    assert construct.spot_candidates(np.full((960, 540, 3), 20, np.uint8), (300, 100, 200, 100)) == []
