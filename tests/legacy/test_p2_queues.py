"""P2 muc 1 (PM 2026-11-23): doc hang cho "1/1" / "0/1" bang anh chu so (templates/qdigits) + cham do."""
import types

import cv2
import numpy as np
import pytest

from bot import queues
from bot.modules import observe


def paint(text, x=33, y=208, bg=60):
    """Anh 960x540 nen toi, dat cac anh chu so (templates/qdigits) canh nhau ben phai icon tam (x, y)."""
    g = queues.glyphs()
    img = np.full((960, 540, 3), bg, np.uint8)
    cx = x + 35
    for ch in text:
        t = g[ch][0]
        h, w = t.shape
        img[y - 8:y - 8 + h, cx:cx + w] = cv2.cvtColor(t, cv2.COLOR_GRAY2BGR)
        cx += w - 1
    return img


def test_glyph_templates_present():
    g = queues.glyphs()
    assert "/" in g and {"0", "1", "2", "3"} <= set(g)


@pytest.mark.parametrize("text, want", [("1/1", (1, 1)), ("0/1", (0, 1)), ("0/2", (0, 2)), ("1/2", (1, 2)),
                                        ("3/3", (3, 3)), ("0/3", (0, 3)), ("2/2", (2, 2))])
def test_read_glyphs_synthetic(text, want):
    assert queues.read_glyphs(paint(text), 33, 208) == want


def test_read_glyphs_blank_is_none():
    assert queues.read_glyphs(np.full((960, 540, 3), 60, np.uint8), 33, 208) is None


def test_read_glyphs_without_templates_is_none():
    assert queues.read_glyphs(paint("1/1"), 33, 208, tpls={}) is None


def test_read_glyphs_rejects_invalid_value():
    assert queues.read_glyphs(paint("3/2"), 33, 208) is None          # dang chay > tong -> loai


@pytest.mark.parametrize("val, dot, total, want", [
    ((1, 1), False, None, (1, 1)),
    ((0, 1), True, None, (0, 1)),
    ((1, 1), True, None, None),          # doc 'day' ma co cham do (con cho ranh) -> mau thuan, khong tin
    (None, True, 1, (0, 1)),             # nghien cuu: khong doc duoc so + cham do -> ranh
    (None, True, 2, (1, 2)),             # biet tong 2 -> it nhat 1 cho ranh
    (None, True, None, None),            # khong biet tong -> khong doan
    (None, False, 1, None),              # khong cham do -> KHONG ket luan (farm cap thap co luc khong hien cham)
])
def test_resolve(val, dot, total, want):
    assert queues.resolve(val, dot, total) == want


def test_read_uses_dot_and_known_totals(monkeypatch):
    class V:
        def find(self, img, name, **k):
            return (33, 208, 0.95) if name == "research/icon_queue" else (33, 142, 0.95) if "builder" in name else None

    monkeypatch.setattr(queues, "read_count", lambda img, x, y: None)
    monkeypatch.setattr(queues, "has_dot", lambda img, x, y: True)
    out = queues.read(V(), None, {"build": 2})
    assert out == {"research": (0, 1), "build": (1, 2)}


def test_known_totals_from_facts():
    facts = {"queue_build": [1, 2], "queue_train": [0, 3], "queue_research": None}
    ctx = types.SimpleNamespace(dev=types.SimpleNamespace(idx=1),
                                mem=types.SimpleNamespace(fact=lambda i, k: facts.get(k)))
    assert observe.known_totals(ctx) == {"build": 2, "train": 3}
    assert observe.known_totals(types.SimpleNamespace(dev=None)) == {}
