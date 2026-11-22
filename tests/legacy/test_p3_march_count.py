"""P3-1: doc 'Hanh quan x/y' bang anh chu so templates/mdigits + khung 'Hanh quan' vang mat = 0 doi."""
import os

import cv2
import numpy as np
import pytest

from bot import march_count as mc
from bot.vision import Vision

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
FIX = os.path.join(ROOT, "tests", "fixtures")


def _paint(text, bg=60):
    """Anh 540x960 nen toi, dan anh chu so mdigits vao vi tri that (x ~169, y ~141) theo chuoi 'a/b'."""
    img = np.full((960, 540, 3), bg, np.uint8)
    tpls = mc.glyphs()
    x = 168
    for ch in text:
        t = tpls["/" if ch == "/" else ch][0]
        h, w = t.shape
        img[141:141 + h, x:x + w] = cv2.cvtColor(t, cv2.COLOR_GRAY2BGR)
        x += w - (2 if ch == "/" else 1)
    return img


def test_glyph_templates_exist():
    tpls = mc.glyphs()
    assert set("12345/") <= set(tpls)


@pytest.mark.parametrize("text,want", [("1/1", (1, 1)), ("3/5", (3, 5)), ("4/5", (4, 5)), ("5/5", (5, 5)),
                                       ("2/5", (2, 5)), ("1/5", (1, 5))])
def test_read_synthetic(text, want):
    assert mc.read_glyphs(_paint(text)) == want


def test_blank_is_none():
    assert mc.read_glyphs(np.full((960, 540, 3), 60, np.uint8)) is None


def test_parse_bounds():
    assert mc.parse("5/5") == (5, 5)
    assert mc.parse("6/5") is None
    assert mc.parse("1/0") is None
    assert mc.parse("x") is None


def test_infer_rules():
    assert mc.infer((3, 5), True, 5) == (3, 5)
    assert mc.infer((3, 5), None, None) == (3, 5)
    assert mc.infer(None, False, 5) == (0, 5)          # ban do the gioi, khung an -> 0 doi
    assert mc.infer(None, False, None) is None         # chua biet tong -> khong doan
    assert mc.infer(None, None, 5) is None             # khong chac dang o ban do the gioi
    assert mc.infer((3, 5), False, 5) is None          # mau thuan -> khong tin


class _V:
    def __init__(self, have, seen):
        self.have, self.seen = have, seen

    def has(self, n):
        return n in self.have

    def find(self, img, n, th=None, roi=None):
        return (1, 1, 0.99) if n in self.seen else None


def test_header_state_needs_templates_and_world():
    both = {mc.HEADER, mc.WORLD}
    assert mc.header_state(_V(set(), set()), None) is None              # thieu anh mau -> khong ket luan
    assert mc.header_state(_V(both, {mc.HEADER}), None) is True
    assert mc.header_state(_V(both, {mc.WORLD}), None) is False         # ban do the gioi, khong co khung
    assert mc.header_state(_V(both, set()), None) is None               # thanh pho / bang khac


# anh that (chi co tren may chu du an, tests/fixtures bi gitignore)
REAL = [
    ("march_panel_5_i1.png", (5, 5)),                       # Tesseract: None
    ("screens/world/snap-amt_metal.png", (1, 1)),           # Tesseract: None
    ("gather_p3/march_5-5_tess3-5.png", (5, 5)),            # Tesseract doc SAI thanh 3/5
    ("gather_p3/march_4-5.png", (4, 5)),
    ("gather_p3/march_3-5.png", (3, 5)),
    ("gather_p3/march_2-5.png", (2, 5)),
    ("gather_p3/march_1-5.png", (1, 5)),
    ("gather_p3/march_1-1_i3.png", (1, 1)),
    ("gather_p3/world_no_header_i3.png", None),
    ("city_main_i1.png", None),
]


@pytest.mark.fixtures
@pytest.mark.parametrize("name,want", REAL)
def test_real_frames(name, want):
    img = cv2.imread(os.path.join(FIX, name))
    if img is None:
        pytest.skip("thieu anh fixture")
    assert mc.read_glyphs(img) == want


@pytest.mark.fixtures
def test_real_world_without_header_is_zero():
    img = cv2.imread(os.path.join(FIX, "gather_p3", "world_no_header_i3.png"))
    if img is None:
        pytest.skip("thieu anh fixture")
    v = Vision(os.path.join(ROOT, "templates"))
    assert mc.header_state(v, img) is False
    assert mc.infer(mc.read_glyphs(img), mc.header_state(v, img), 2) == (0, 2)
    snap = cv2.imread(os.path.join(FIX, "screens", "world", "snap-amt_metal.png"))
    if snap is not None:
        assert mc.header_state(v, snap) is True
