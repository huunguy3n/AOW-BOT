"""P13d-3: khong dung cho cong trinh ngan khi con viec khac / tho khac ranh; chi bam 'Mien phi', khong nut kim cuong."""
from types import SimpleNamespace

import cv2
import numpy as np

from bot import build, ocr
from bot.modules import observe


def test_no_wait_when_other_steps_pending():
    ok, why = build.should_quick_wait({"upgrade", "gather", "research", "observe"}, (2, 2), 2)
    assert not ok and "gather" in why


def test_no_wait_when_other_builder_idle():
    ok, _ = build.should_quick_wait(set(), (0, 2), 2)
    assert not ok


def test_wait_only_when_nothing_else_to_do():
    ok, _ = build.should_quick_wait({"observe", "reddots", "upgrade"}, (1, 1), 1)
    assert ok
    assert build.should_quick_wait(None, None, 1)[0]


def _btn_img():
    img = np.full((960, 540, 3), 30, np.uint8)
    cv2.rectangle(img, (180, 600), (340, 645), (140, 140, 20), -1)       # nut xanh ngoc
    return img


def test_free_speedup_only_free_text(monkeypatch):
    img = _btn_img()
    monkeypatch.setattr(ocr, "text", lambda *a, **k: "Mien phi")
    assert build.free_speedup_button(img) is not None
    for t in ("Tang toc", "500 kim cuong", "Mien phi 300", "Dung", "Mua"):
        monkeypatch.setattr(ocr, "text", lambda *a, _t=t, **k: _t)
        assert build.free_speedup_button(img) is None, t


def test_free_speedup_taps_only_free(monkeypatch):
    taps = []
    img = _btn_img()
    ctx = SimpleNamespace(shot=lambda: img, tap=lambda x, y, wait=0: taps.append((x, y)),
                          ensure_city=lambda: None, back_out=lambda n=1: None, skip_dialogs=lambda: None)
    monkeypatch.setattr(observe, "progress_bars", lambda im: [(100, 300, 120)])
    monkeypatch.setattr(ocr, "text", lambda *a, **k: "Tang toc")      # chi nut tra phi
    assert build.free_speedup(ctx) == 0 and len(taps) == 1            # chi cham thanh tien do, khong cham nut
    taps.clear()
    monkeypatch.setattr(ocr, "text", lambda *a, **k: "Mien phi")
    assert build.free_speedup(ctx) == 1 and len(taps) == 2
