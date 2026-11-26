"""P13l (chu du an t99u): thieu tai nguyen -> "Dung dao cu" -> goi nho nhat -> "Dung" -> quay lai -> lam lai.
Anh: tests/fixtures/p13l/res_*.png (4 anh chu du an, anh cat nen kich thuoc khac 540x960)."""
import types

import cv2
import numpy as np

from bot import ctx as ctxmod
from bot import resources as R
from bot.vision import Vision

D = "tests/fixtures/p13l/"
V = Vision("templates", 0.82)
GEM_BTN = (370, 398)          # nut phai "Huan luyen" + 46 kim cuong tren res_1
USE_BTN = (145, 398)          # nut trai "Dung dao cu"
POPUP_X = (495, 163)


def _img(name):
    img = cv2.imread(D + name + ".png")
    assert img is not None, name
    return img


POPUP = "res_1_thieu_dung_dao_cu"
LIST0 = "res_2_bo_sung_list"
DIALOG = "res_3_dung_slider"
LIST1 = "res_4_back"


def _near(p, q, tol=15):
    return abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol


def test_popup_offers_only_the_free_left_button():
    pop = R.find_popup(_img(POPUP), V)
    assert pop and _near(pop.use, USE_BTN) and pop.use[0] < R.LEFT_X


def test_gem_button_is_forbidden_everything_else_is_not():
    img = _img(POPUP)
    for p in (GEM_BTN, (370, 412), (290, 385), (460, 420)):
        assert R.forbidden(img, V, *p), p
    for p in (USE_BTN, POPUP_X, (60, 398)):
        assert not R.forbidden(img, V, *p), p


def test_list_offers_smallest_free_pack_first_and_never_gem_rows():
    for name, gem_rows in ((LIST0, (727,)), (LIST1, (726, 827))):
        img = _img(name)
        rows = R.find_list(img, V)
        assert len(rows) == 5 and rows[0][1] < rows[1][1] and abs(rows[0][1] - 223) < 10, rows
        assert all(y < 660 for _, y in rows)
        for y in gem_rows:
            assert R.forbidden(img, V, rows[0][0], y), (name, y)
        for p in [*rows, (40, 30)]:                       # nut "Dung" va mui ten quay lai: duoc bam
            assert not R.forbidden(img, V, *p), (name, p)


def test_quantity_dialog_confirm_button():
    assert _near(R.find_dialog(_img(DIALOG), V), (263, 361))
    assert R.find_list(_img(DIALOG), V) is None
    for name in (POPUP, LIST0, LIST1):
        assert R.find_dialog(_img(name), V) is None, name


def test_storage_check():
    assert R.parse_storage("Luu tru kim loai 30.1K") == 30100 and R.parse_storage("Luu tru kim loai 53") == 53
    before, after = R.read_storage(_img(LIST0), V), R.read_storage(_img(LIST1), V)
    assert R.storage_up(before, after)                       # khong OCR: o luu tru doi hinh
    assert not R.storage_up(before, before)
    assert R.storage_up((53, None), (30100, None)) and not R.storage_up((30100, None), (30100, None))


class Flow:
    """May gia theo dung 4 anh: popup -> "Dung dao cu" -> danh sach -> "Dung" -> bang so luong -> "Dung" -> danh sach
    (luu tru tang) -> quay lai -> man huan luyen; redo bam Huan luyen."""

    def __init__(self, packs=True, still_short=0):
        self.v, self.cfg = V, {}
        self.dev = types.SimpleNamespace(idx=0)
        self.cur, self.taps, self.packs, self.still_short = "popup", [], packs, still_short

    def frame(self):
        if self.cur == "train":
            return np.zeros((960, 540, 3), np.uint8)
        if self.cur == "list" and not self.packs:
            img = _img(LIST1).copy()
            img[180:660, 390:] = (40, 36, 34)                  # het goi: chi con 2 hang kim cuong
            return img
        return _img({"popup": POPUP, "list": LIST0, "dialog": DIALOG, "used": LIST1}[self.cur])

    def shot(self):
        return self.frame()

    def tap(self, x, y, wait=0, tpl=None):
        img = self.frame()
        assert not R.forbidden(img, V, x, y), ("bam nut kim cuong", self.cur, x, y)
        self.taps.append((self.cur, x, y))
        if self.cur == "popup" and _near((x, y), USE_BTN):
            self.cur = "list"
        elif self.cur == "list" and abs(y - 223) < 10:
            self.cur = "dialog"
        elif self.cur == "dialog" and _near((x, y), (263, 361)):
            self.cur = "used"

    def tap_first(self, names, wait=0, img=None, roi=None):
        img = self.frame() if img is None else img
        for n in names:
            p = V.find(img, n, roi=roi)
            if p:
                self.taps.append((self.cur, p[0], p[1]))
                self.cur = "train"
                return n
        return None

    def press_back(self, *a, **k):
        self.cur = "train"

    def dismiss_reward(self, *a, **k):
        pass

    def save_debug(self, tag):
        pass


def _sleepless(monkeypatch):
    monkeypatch.setattr(R.time, "sleep", lambda s: None)


def test_refill_uses_smallest_pack_then_returns(monkeypatch):
    _sleepless(monkeypatch)
    c = Flow()
    assert R.refill(c) == R.REFILLED
    assert [s for s, _, _ in c.taps] == ["popup", "list", "dialog", "used"]      # cuoi: mui ten quay lai
    assert c.taps[-1][1] < 130 and c.taps[-1][2] < 80
    assert c.cur == "train" and c._refills == 1


def test_retry_redoes_the_action_and_stops_at_the_limit(monkeypatch):
    _sleepless(monkeypatch)
    c, redos = Flow(), []
    assert R.retry(c, lambda: redos.append(1) or True) == R.REFILLED and len(redos) == 1

    c = Flow()

    def short_again():
        c.cur = "popup"                      # lam lai van thieu -> popup hien lai
        return True
    assert R.retry(c, short_again) == R.NO_FREE
    assert c._refills == R.DEFAULTS["max_per_action"] and c.cur == "train"       # co gioi han, dong bang X


def test_no_free_pack_closes_without_buying(monkeypatch):
    _sleepless(monkeypatch)
    c = Flow(packs=False)
    assert R.refill(c) == R.NO_FREE and c.cur == "train"
    assert [s for s, _, _ in c.taps] == ["popup", "list"]      # "Dung dao cu" roi chi mui ten quay lai
    for _ in range(R.EMPTY_MAX):
        c.cur = "popup"
        R.refill(c)
    c.cur, n = "popup", len(c.taps)
    assert R.refill(c) == R.NO_FREE and c.taps[n:][0][1] > 450       # thoi mo danh sach: chi bam X


def test_disabled_only_closes_popup(monkeypatch):
    _sleepless(monkeypatch)
    c = Flow()
    c.cfg = {"resources": {"refill": False}}
    assert R.refill(c) == R.NO_FREE
    assert len(c.taps) == 1 and _near(c.taps[0][1:], POPUP_X)


def test_no_popup_does_nothing():
    c = Flow()
    c.cur = "train"
    assert R.retry(c, lambda: 1 / 0) == R.NONE and c.taps == []


def test_ctx_never_taps_the_gem_button():
    img = _img(POPUP)
    sent = []
    dev = types.SimpleNamespace(idx=0, act_seq=0, screencap=lambda tries=None: img,
                                tap=lambda x, y: sent.append((x, y)))
    c = ctxmod.Ctx(dev, V, {"screen": {"width": 540, "height": 960}, "speed": {"wait_scale": 0}})
    c.shot()
    c.tap(*GEM_BTN, wait=0)
    assert sent == []
    c.tap(*USE_BTN, wait=0)
    assert sent == [USE_BTN]
