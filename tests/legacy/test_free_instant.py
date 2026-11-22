import os

import cv2
import pytest

from bot import build, ocr

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "upgrade_free_instant_i0.png")


def test_free_label_rule_is_strict():
    assert build.is_free_instant("tang cap ngay", "fy mien phi")
    assert not build.is_free_instant("tang cap ngay", "120")                # co gia kim cuong
    assert not build.is_free_instant("tang cap ngay", "mien phi 120")       # co so -> khong tin
    assert not build.is_free_instant("tang cap", "mien phi")                # khong phai nut 'ngay'
    assert not build.is_free_instant("huan luyen ngay", "")


@pytest.mark.fixtures
@pytest.mark.ocr
def test_free_instant_button_found_on_real_screen():
    img = cv2.imread(FIX)
    if img is None or not ocr.init(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytest.skip("thieu anh fixture hoac Tesseract")
    assert build.free_instant_button(img, (376, 337)) == (151, 349)         # nut trai 'Tang cap ngay / Mien phi'
    assert build.free_instant_button(img, (151, 349)) is None               # tam sai (khong co nut ben trai)
