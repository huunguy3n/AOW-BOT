"""P13m t108u: bang "het giai doan tan thu" khi nang nha chinh 7 -> 8 -> chi "Xac nhan" roi bam "Tang cap" tiep.

Chua co anh that: anh gia (dan anh mau nut vao khung 540x960) + chu OCR gia.
"""
import logging
import types

import numpy as np
import pytest

from bot import build, ocr, resources
from bot import novice_popup as N
from bot.vision import Vision

TEXT = "Thong bao | Ban sap het giai doan tan thu, bao ve tan thu se ket thuc"
UP, GEM_BTN, OK, CANCEL, X = (390, 800), (150, 800), (380, 620), (160, 620), (500, 140)
V = Vision("templates", 0.85)


@pytest.fixture(autouse=True)
def _no_frames(monkeypatch):
    monkeypatch.setattr(N, "keep_frame", lambda *a: None)


# ---------- chu ----------
@pytest.mark.parametrize("text", [
    TEXT, "hết giai đoạn tân thủ", "HET GIAI DOAN TAN THU", "bao ve tanthu ket thuc", "het giai doan tan\nthu.",
    "het giai doan tan thii", "giai doan t4n thu", "giai doan tan tnu", "Bảo vệ Tân Thú đã hết"])
def test_novice_text(text):
    assert N.is_novice_text(text)


@pytest.mark.parametrize("text", [
    "", None, "Roi tro choi?", "Ban co muon roi tro choi? tan thu", "lan thu 2 trong ngay", "tang thuong tan thuong",
    "Mo khoa Binh chung nay", "tan the gioi", "Thieu tai nguyen", "ban thu cong trinh"])
def test_not_novice_text(text):
    assert not N.is_novice_text(text)


# ---------- nhan dien tren anh gia ----------
def paste(*items):
    """items = (ten anh mau, (x, y) tam) -> khung 540x960 nen toi."""
    img = np.full((960, 540, 3), 30, np.uint8)
    for name, (x, y) in items:
        t = V.load(name)
        h, w = t.shape[:2]
        img[y - h // 2:y - h // 2 + h, x - w // 2:x - w // 2 + w] = t[..., :3]
    return img


@pytest.mark.parametrize("tpl", N.CONFIRM_TPLS)
def test_find_popup_each_confirm_style(tpl):
    p = N.find(paste((tpl, OK)), V, text=TEXT)
    assert p and abs(p[0] - OK[0]) <= 4 and abs(p[1] - OK[1]) <= 4


def test_find_reads_text_above_button_by_ocr(monkeypatch):
    rois = []
    monkeypatch.setattr(ocr, "text", lambda img, roi, *a, **k: rois.append(roi) or "het giai doan tan thu")
    p = N.find(paste(("common/btn_confirm", OK)), V)
    assert p and rois
    _x, y, _w, h = rois[-1]
    assert y + h < p[1]                                     # chi doc noi dung phia tren nut


def test_find_needs_both_button_and_text(monkeypatch):
    monkeypatch.setattr(ocr, "text", lambda *a, **k: "")
    assert N.find(paste(("common/btn_confirm", OK)), V) is None                 # "Xac nhan" cua hop thoai khac
    assert N.find(paste(("common/btn_confirm", OK)), V, text="Nhan duoc phan thuong") is None
    assert N.find(paste(), V, text=TEXT) is None                                # co chu, khong co nut


def test_exit_dialog_never_matches():
    # 28/11/2026 anh that: bang het tan thu CUNG co nut Huy trung anh mau hop thoai thoat -> phan biet bang CHU
    img = paste(("common/btn_confirm", OK), ("common/btn_cancel_exit", CANCEL))
    assert N.find(img, V, text="Roi tro choi? Ban co chac muon thoat") is None
    assert N.find(img, V, text=TEXT) == OK


def test_confirm_button_with_gem_never_matches():
    img = paste(("common/btn_confirm", OK), ("common/res_gem", (OK[0] - 60, OK[1])))
    assert resources.has_gem(img, V, *OK)
    assert N.find(img, V, text=TEXT) is None


# ---------- luong nang nha chinh ----------
class Screens:
    """Vision gia: moi man = {ten anh mau: toa do}. Anh = mang mang ma man o diem (0, 0)."""

    def __init__(self, **screens):
        self.names, self.maps = list(screens), list(screens.values())

    def img(self, name):
        a = np.zeros((960, 540, 3), np.uint8)
        a[0, 0, 0] = self.names.index(name)
        return a

    def find(self, img, n, **k):
        p = self.maps[int(img[0, 0, 0])].get(n)
        return (p[0], p[1], 1.0) if p else None


S = dict(
    upgrade={"build/btn_upgrade": UP, "build/title_hq": (270, 60), "common/btn_x": X},
    popup={"common/btn_confirm": OK, "common/btn_x": X},
    city={"common/btn_to_world": (500, 920)},
    exit={"common/btn_confirm": OK, "common/btn_cancel_exit": CANCEL},
    gem={"build/btn_upgrade": GEM_BTN},
)


class Ctx:
    """flow: {(man, diem cham): man ke tiep}; diem khong co trong flow -> man giu nguyen."""

    POPUP_CLOSERS = ("common/btn_x",)

    def __init__(self, start, flow):
        self.v, self.screen, self.flow = Screens(**S), start, flow
        self.taps, self.closed, self.debug = [], [], []
        self.cfg = {"build": {"hq_max_level": 30, "follow_quests": True}}
        self.dev = types.SimpleNamespace(idx=2)
        self.mem = self.store = None

    def shot(self):
        self._img = self.v.img(self.screen)
        return self._img

    def settle(self, *a, **k):
        return self.shot()

    def find(self, n, **k):
        return self.v.find(self.shot(), n)

    def tap(self, x, y, **k):
        self.taps.append((x, y))
        self.screen = self.flow.get((self.screen, (x, y)), self.screen)

    def tap_tpl(self, n, **k):
        p = self.find(n)
        if p:
            self.tap(p[0], p[1])
        return bool(p)

    def tap_first(self, names, **k):
        self.closed.append(names)

    def cancel_exit(self, img=None, why=""):
        p = self.v.find(img, "common/btn_cancel_exit")
        if p:
            self.tap(p[0], p[1])
        return bool(p)

    def skip_dialogs(self, *a):
        return 0

    def back_out(self, *a):
        self.closed.append("back")

    def is_home(self, img=None):
        return self.screen == "city"

    def save_debug(self, tag):
        self.debug.append(tag)


@pytest.fixture
def env(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="aow")
    monkeypatch.setattr(N, "read_text", lambda img, p: TEXT)
    monkeypatch.setattr(N.buttons, "with_text", lambda *a, **k: [])
    monkeypatch.setattr(resources, "has_gem", lambda img, v, x, y: (x, y) == GEM_BTN)
    monkeypatch.setattr(resources, "retry", lambda c, redo: resources.NONE)
    monkeypatch.setattr(build, "screen_level", lambda img: 7)
    monkeypatch.setattr(build, "upgraded_ok", lambda img: False)
    monkeypatch.setattr(build, "free_instant_button", lambda img, up: None)
    monkeypatch.setattr(build.hqlevel, "record", lambda *a, **k: None)
    return caplog


def _logged(caplog):
    return [r.getMessage() for r in caplog.records].count("het tan thu -> xac nhan, nang nha chinh")


def test_popup_after_upgrade_tap_confirm_then_upgrade_again(env):
    class Flow(Ctx):
        def tap(self, x, y, **k):
            first = not self.taps
            super().tap(x, y, **k)
            if (x, y) == UP:
                self.screen = "popup" if first else "city"      # lan 1: bang tan thu; lan 2: bat dau xay

    c = Flow("upgrade", {("popup", OK): "upgrade"})
    assert build.upgrade_here(c) == "started"
    assert c.taps == [UP, OK, UP]
    assert not c.closed and c.builds_started == 1 and _logged(env) == 1


def test_popup_confirm_starts_upgrade_by_itself(env):
    c = Ctx("upgrade", {("upgrade", UP): "popup", ("popup", OK): "city"})
    assert build.upgrade_here(c) == "started"
    assert c.taps == [UP, OK] and not c.closed


def test_popup_already_open_confirm_first_and_never_free_instant(env, monkeypatch):
    monkeypatch.setattr(build, "free_instant_button", lambda img, up: pytest.fail("khong duoc xet 'Tang cap ngay'"))
    c = Ctx("popup", {("popup", OK): "upgrade", ("upgrade", UP): "city"})
    assert build.upgrade_here(c) == "started"
    assert c.taps == [OK, UP] and not c.closed and _logged(env) == 1


def test_stuck_popup_is_not_closed_with_x(env):
    c = Ctx("upgrade", {("upgrade", UP): "popup"})
    assert build.upgrade_here(c) == "blocked"
    assert c.taps == [UP, OK, OK]                           # 2 lan khong dong -> danh sach den
    assert not c.closed and c.debug == ["novice_popup_stuck"]


def test_popup_that_keeps_returning_is_bounded(env):
    c = Ctx("upgrade", {("upgrade", UP): "popup", ("popup", OK): "upgrade"})
    assert build.upgrade_here(c) == "blocked"
    assert c.taps == [UP, OK] * (build.NOVICE_ROUNDS + 1)
    assert not c.closed


def test_after_confirm_diamond_button_never_tapped(env):
    c = Ctx("upgrade", {("upgrade", UP): "popup", ("popup", OK): "gem"})
    build.upgrade_here(c)
    assert c.taps == [UP, OK]


def test_after_confirm_next_level_screen_not_tapped_again(env, monkeypatch):
    c = Ctx("upgrade", {("upgrade", UP): "popup", ("popup", OK): "upgrade"})
    monkeypatch.setattr(build, "screen_level", lambda img: 8 if OK in c.taps else 7)
    assert build.upgrade_here(c) == "started"
    assert c.taps == [UP, OK]


def test_exit_dialog_in_upgrade_flow_cancelled_never_confirmed(env, monkeypatch):
    monkeypatch.setattr(N, "read_text", lambda img, p: "Roi tro choi? Ban co chac muon thoat")
    c = Ctx("upgrade", {("upgrade", UP): "exit", ("exit", CANCEL): "city"})
    build.upgrade_here(c)
    assert c.taps == [UP, CANCEL] and _logged(env) == 0


def test_other_confirm_dialog_not_confirmed(env, monkeypatch):
    monkeypatch.setattr(N, "read_text", lambda img, p: "Ban co chac muon dung kim cuong?")
    c = Ctx("upgrade", {("upgrade", UP): "popup"})
    build.upgrade_here(c)
    assert OK not in c.taps and _logged(env) == 0


# ---------- anh that 28/11/2026: nut "Huy" cua bang trung anh mau Huy cua hop thoai thoat ----------
import os as _os  # noqa: E402

import cv2 as _cv2  # noqa: E402
import pytest as _pytest  # noqa: E402

_REAL = _os.path.join("tests", "fixtures", "novice_popup", "hq7to8_confirm.png")
_EXIT = _os.path.join("tests", "fixtures", "screens", "exit_dialog")


def _vision():
    from bot import ocr
    from bot.vision import Vision
    if not _os.path.exists(ocr.DEFAULT_CMD if hasattr(ocr, "DEFAULT_CMD") else "C:/Program Files/Tesseract-OCR/tesseract.exe"):
        _pytest.skip("thieu Tesseract")
    ocr.init("C:/Program Files/Tesseract-OCR/tesseract.exe")
    return Vision("templates", 0.82)


@_pytest.mark.skipif(not _os.path.exists(_REAL), reason="thieu anh fixture")
def test_real_novice_popup_is_confirm_not_exit_dialog():
    from bot import novice_popup, screens
    v = _vision()
    img = _cv2.imread(_REAL)
    assert v.find(img, "common/btn_cancel_exit")             # dung la nut Huy trung anh mau hop thoai thoat
    p = novice_popup.find(img, v)
    assert p and abs(p[0] - 387) <= 10 and abs(p[1] - 631) <= 10    # nut "Xac nhan" ben phai
    scr, det = screens.identify(img, v)
    assert scr == "popup" and det[0] == "common/btn_confirm"


@_pytest.mark.skipif(not _os.path.isdir(_EXIT), reason="thieu anh fixture")
def test_real_exit_dialogs_still_exit():
    from bot import screens
    v = _vision()
    files = [f for f in _os.listdir(_EXIT) if f.endswith(".png")]
    for f in files:
        assert screens.identify(_cv2.imread(_os.path.join(_EXIT, f)), v)[0] == "exit_dialog", f
