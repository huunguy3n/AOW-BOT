"""P13-11: mo rong thanh pho - icon o khoa MO tren vien thanh pho + nhiem vu 'mo rong thanh pho' (thanh / bang)."""
import os
import types

import cv2
import pytest

from bot import quest_rules, runner
from bot.modules import expand
from bot.vision import Vision

OWN = "data/owner-feedback/p13/"


def _img(n):
    if not os.path.exists(OWN + n):
        pytest.skip("thieu anh chu")
    return cv2.imread(OWN + n)


def test_unlock_icon_found_on_owner_image():
    v = Vision("templates")
    img = _img("bien_gioi_icon_mo_khoa.png")
    # anh dien thoai 541x727: dat vao khung 540x960
    canvas = cv2.copyMakeBorder(img, 100, 960 - 727 - 100, 0, 0, cv2.BORDER_CONSTANT)[:, :540]
    p = expand.find_unlock(v, canvas)
    assert p and abs(p[0] - 136) <= 6 and abs(p[1] - 278 - 100) <= 6


def test_no_icon_on_plain_city():
    v = Vision("templates")
    img = _img("bien_gioi_keo_vong.png")                       # man co vien sang nhung CHUA co icon mo khoa
    canvas = cv2.resize(img, (540, 960))
    assert expand.find_unlock(v, canvas) is None


def test_quest_rows_classified_expand():
    assert quest_rules.classify("Mo rong thanh pho lan 3") == ("expand", "expand")
    assert quest_rules.delegated("expand")
    assert not quest_rules.forbidden("expand")


def test_due_rules():
    now = 100_000.0
    assert expand.due(None, None, now, 240)[0]
    assert not expand.due(now - 600, None, now, 240)[0]
    assert expand.due(now - 600, now - 60, now, 240)[0]       # nhiem vu mo rong moi thay -> chay ngay
    assert not expand.due(now - 60, now - 600, now, 240)[0]
    assert expand.due(now - 241 * 60, None, now, 240)[0]


def test_runner_has_expand_step_after_upgrade():
    names = [n for n, _ in runner.ORDER]
    assert names.index("upgrade") < names.index("expand") < names.index("mainquest")


class Mem:
    def __init__(self):
        self.f = {}

    def fact(self, i, k):
        return self.f.get(k)

    def set_fact(self, i, k, v):
        self.f[k] = v


def test_run_taps_only_safe_dialog_button(monkeypatch):
    taps = []
    ctx = types.SimpleNamespace(
        cfg={}, mem=Mem(), dev=types.SimpleNamespace(idx=0), v=None,
        ensure_city=lambda: None, back_out=lambda *a: None,
        tap=lambda x, y, **k: taps.append((x, y)), settle=lambda *a, **k: None)
    monkeypatch.setattr(expand, "sweep", lambda c, ring=True: (130, 280))
    monkeypatch.setattr(expand, "open_plot", lambda c, p: bool(taps.append(p)) or True)
    assert expand.run(ctx) == 1 and taps == [(130, 280)]
    assert expand.run(ctx) == 0                                  # vua quet -> bo qua trong 4 gio
