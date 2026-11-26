"""Phim Back khong duoc bam khi dang o thanh pho / ban do (hop thoai 'Roi tro choi?' ~130 lan/ngay, 2026-11-21)."""
import types

import numpy as np

from bot import ctx as ctx_mod
from bot.ctx import Ctx
from bot.modules import gather


def fake(home_seq, cancel=False):
    calls = []
    home = iter(home_seq)
    c = types.SimpleNamespace(step="t", calls=calls)
    c.is_home = lambda: next(home)
    c.dev = types.SimpleNamespace(back=lambda: calls.append("back"))
    c._exp_begin = lambda *a: calls.append(("exp", *a))
    c.tap_tpl = lambda name, **k: calls.append(("tap", name)) or cancel
    c.wait_change = lambda before, cap: None
    return c


def test_no_back_at_home(monkeypatch):
    monkeypatch.setattr(ctx_mod.time, "sleep", lambda s: None)
    c = fake([True])
    assert Ctx.press_back(c, "x") is False and "back" not in c.calls


def test_recheck_catches_map_still_moving(monkeypatch):
    monkeypatch.setattr(ctx_mod.time, "sleep", lambda s: None)
    c = fake([False, True])            # lan 1 ban do dang truot -> doc truot, lan 2 thay nut ban do
    assert Ctx.press_back(c, "x") is False and "back" not in c.calls


def test_back_when_in_panel_and_logged(monkeypatch):
    monkeypatch.setattr(ctx_mod.time, "sleep", lambda s: None)
    c = fake([False, False])
    assert Ctx.press_back(c, "back_out") is True
    assert ("exp", "back", None, None, "back_out") in c.calls and "back" in c.calls


def test_close_map_menu_skips_back_when_nothing_opened(monkeypatch):
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    img = np.zeros((960, 540, 3), np.uint8)
    c = fake([])
    c.shot = img.copy
    gather.close_map_menu(c, img)
    assert "back" not in c.calls
    c.shot = lambda: np.full((960, 540, 3), 200, np.uint8)      # menu da mo -> man doi -> Back
    gather.close_map_menu(c, img)
    assert "back" in c.calls
