"""P10-2 (live-run-3 15:31:17): man Chieu mo mo san tab THUONG co nut teal "Mien phi" + cham do,
bot bao "khong thay luot mien phi". Bam HET o tab hien tai truoc roi moi chuyen tab con cham do; nut Mien phi nhan bang
anh mau hoac chu; khong bao gio nut kim cuong."""
import os
import types

import cv2
import pytest

from bot import claimloop, ocr
from bot.badges import red_dots
from bot.modules import notify
from bot.vision import Vision

SHOT = "logs/shots/20261124-153117-i1-recruit_dot_left.png"   # ADB 540x960 live3 (= live3/auto s153117)
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def _img():
    if not os.path.exists(SHOT):
        pytest.skip("thieu anh live3 recruit_dot_left")
    return cv2.imread(SHOT)


def test_free_found_by_text_and_tab_dot():
    img = _img()
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    x, y = notify._free_by_text(img)
    assert 90 < x < 230 and 700 < y < 745
    dots = red_dots(img)
    assert notify.recruit_tab_dot(img, (385, 927), dots) is True        # tab thuong con cham do
    assert notify.recruit_tab_dot(img, (157, 927), dots) is False       # tab cao cap khong
    assert notify.recruit_tab_dot(img, None, dots) is None


def test_recruit_once_taps_free_on_live3_frame():
    img = _img()
    v = Vision("templates")
    taps = []
    ctx = types.SimpleNamespace(v=v, _img=img, shot=lambda *a, **k: img, tap=lambda x, y, **k: taps.append((x, y)),
                                find=lambda n, **k: v.find(img, n), save_debug=lambda t: None,
                                tap_first=lambda *a, **k: None, back_out=lambda n=1: None, cfg={},
                                POPUP_CLOSERS=[], is_colored=lambda *a: False)
    assert notify._recruit_once(ctx, "current", False) == 1
    assert taps and 90 < taps[0][0] < 230 and 700 < taps[0][1] < 750      # nut "Mien phi", khong phai "10 lan"


def test_current_tab_first_then_tabs_with_dots():
    left = {"current": 2, "premium": 1, "normal": 0}
    seq = []

    def once(t):
        if left[t] <= 0:
            return 0
        left[t] -= 1
        seq.append(t)
        return 1
    total, book = claimloop.current_then_tabs(["premium", "normal"], lambda t: seq.append(("enter", t)), once,
                                             lambda t: left[t] > 0)
    assert total == 3
    assert seq[:2] == ["current", "current"]                   # tab hien tai HET truoc khi chuyen
    assert ("enter", "normal") not in seq                       # tab khong cham do -> khong vao
    assert book[0] == ("current", 2)


def test_stops_when_no_dots_or_no_progress():
    calls = []
    total, _ = claimloop.current_then_tabs(["a", "b"], calls.append, lambda t: 0, lambda t: False)
    assert total == 0 and calls == []
    total, _ = claimloop.current_then_tabs(["a"], calls.append, lambda t: 0, lambda t: None,
                                          max_rounds=5)
    assert calls == ["a"]                                        # vong khong nhan them -> dung, khong lap vo han


def test_recruit_choice_never_gems():
    assert notify.recruit_choice(False, False, False, False, False) is None
    assert notify.recruit_choice(True, False, False, False, False) == "free"
