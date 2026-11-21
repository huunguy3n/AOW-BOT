"""F1: hoi quy nhan dien (bao tools/check_screens.py, tools/check_tutorial.py). Anh fixture khong co trong git
(chu du an 2026-11-21) -> tu skip khi thieu; bat buoc chay local truoc commit cham perception."""
import glob
import os
import subprocess
import sys

import cv2
import pytest

from bot.screens import identify
from bot.vision import Vision

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCREENS = sorted(glob.glob(os.path.join(ROOT, "tests", "fixtures", "screens", "*", "*.png")))
TUTORIAL = os.path.join(ROOT, "tests", "fixtures", "tutorial")

pytestmark = pytest.mark.fixtures


@pytest.fixture(scope="module")
def vision():
    return Vision(os.path.join(ROOT, "templates"), 0.82)


@pytest.mark.skipif(not SCREENS, reason="thieu tests/fixtures/screens (chi co tren may local)")
@pytest.mark.parametrize("path", SCREENS, ids=[os.path.relpath(p, ROOT) for p in SCREENS])
def test_identify_screen(vision, path):
    want = os.path.basename(os.path.dirname(path))
    assert identify(cv2.imread(path), vision)[0] == want


@pytest.mark.skipif(not os.path.isdir(TUTORIAL), reason="thieu tests/fixtures/tutorial (chi co tren may local)")
def test_tutorial_decide_cases():
    # script tu chdir + tat logging khi import -> chay rieng tien trinh de khong anh huong test khac
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_tutorial.py")], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, check=False,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stdout[-3000:]
