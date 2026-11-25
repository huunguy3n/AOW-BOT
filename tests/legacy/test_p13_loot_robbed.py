"""P13-6: chi cuop xe khi 'So lan co the bi cuop boc' con 2/2 (anh cuop_xe_chi_2_2.png: 0/2 -> khong cuop)."""
import inspect
import os

import cv2
import pytest

from bot import ocr
from bot.modules import play

TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
FIX = "tests/fixtures/loot_world_i1.png"


def test_robbed_ok_rules():
    assert play.robbed_ok((2, 2))[0]
    assert not play.robbed_ok((1, 2))[0]
    assert not play.robbed_ok((0, 2))[0]            # anh chu: xe (Chg)vippro/fam 0/2
    assert not play.robbed_ok(None)[0]               # khong doc duoc -> bo (an toan)


def test_fixture_two_of_two():
    if not os.path.exists(FIX) or not ocr.init(TESS):
        pytest.skip("thieu fixture / Tesseract")
    assert play.robbed_left(cv2.imread(FIX)) == (2, 2)


def test_loot_checks_robbed_before_pressing_loot():
    src = inspect.getsource(play._loot_once)
    assert src.index("robbed_ok") < src.index('ctx.tap(btn[0], btn[1], wait=2.5)')
