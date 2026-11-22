"""Khung 'Hanh quan' 5 doi cua #1 (2026-11-22, anh chu du an): doc dung gio cac dong doc duoc, khong doan sai."""
import os

import cv2
import pytest

from bot import ocr

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "march_panel_5_i1.png")


def test_row_pitch_matches_measured_panel():
    assert ocr.MARCH_ROW_H == 44


@pytest.mark.fixtures
@pytest.mark.ocr
def test_five_marches_read_only_confident_times():
    img = cv2.imread(FIX)
    if img is None or not ocr.init(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytest.skip("thieu anh fixture hoac Tesseract")
    rows = ocr.marches(img, 5)
    truth = [866, 3083, 2571, 415, 485]
    for r, t in zip(rows, truth, strict=True):
        assert r["remaining"] in (None, t)                 # khong bao gio doc sai gio
    assert rows[0]["remaining"] == 866 and rows[3]["remaining"] == 415
