"""P13g-3 (chu du an t92u 26/11/2026): "lay metal mo 7, bam Tim van ra metal 7 cu" - khong bao gio gui 2 quan doan
toi cung 1 mo; moi loai do 8 -> 7 -> 6; trung mo cua minh -> ha cap roi chuyen loai uu tien ke tiep.
Goc loi tren may #1 (log 26/11 07:28-07:31, 09:40-09:43): buoc nhay 5 cap cua o "Cap" Co giap (buoc phan quan) dinh
vao ctx -> thu thap doi cap 3 / 2 / 1 thanh 5 -> tim ra dung 1 mo."""
import os
import time
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from bot import gather_rules as gr
from bot import ocr as real_ocr
from bot.modules import gather

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
FIX = os.path.join(ROOT, "tests", "fixtures", "p13g")
NOW = 1_795_700_000.0


# ---------- luat thuan ----------
@pytest.mark.parametrize("text,xy", [
    ("# 32X: 234Y: 326", (234, 326)), ("#32X:234Y:326 )", (234, 326)), ("# 32X: 220-Y: 334", (220, 334)),
    ("# 32 X: 218Y: 506", (218, 506)), ("#32X:55Y:335", (55, 335)), ("Xuong Luyen Kim", None), ("", None),
])
def test_parse_xy(text, xy):
    assert gr.parse_xy(text) == xy


def test_same_mine_by_tile_any_level_and_after_arrival():
    d = [{"type": "metal", "level": 7, "travel": 400, "t": NOW, "xy": [234, 326]}]
    assert gr.same_mine(d, (234, 326), NOW + 30) is d[0]            # dang hanh quan
    assert gr.same_mine(d, (234, 326), NOW + 3 * 3600) is d[0]      # da toi mo, dang thu thap
    assert gr.same_mine(d, (234, 327), NOW + 30) is None
    assert gr.same_mine(d, None, NOW + 30) is None                  # khong doc duoc toa do
    assert gr.same_mine(d, (234, 326), NOW + 481 * 60) is None      # qua cua so chan


def test_own_target_ignores_other_tile():
    d = [{"type": "metal", "level": 7, "travel": 400, "t": NOW, "xy": [234, 326]}]
    assert gr.own_target(d, "metal", 7, NOW + 30, travel=400, xy=(100, 100)) is None   # cung thoi gian, khac o
    assert gr.own_target(d, "metal", 7, NOW + 30, travel=400, xy=(234, 326)) is d[0]
    assert gr.own_target(d, "metal", 7, NOW + 30, travel=400) is d[0]                  # khong biet toa do


def test_bigger_mine_catches_level5_read_when_searching_low_level():
    assert gr.bigger_mine([560000], None, "food", 3) == 560000      # log 07:30:36 'doc 560000 khong hop ly'
    assert gr.bigger_mine([560000], None, "metal", 2) == 560000
    assert gr.bigger_mine([40000], None, "metal", 7) is None        # rot chu so dau: khong phai mo lon hon
    assert gr.bigger_mine([160000], None, "metal", 3) is None       # dung cap
    assert gr.bigger_mine([606, 999999], None, "metal", 2) is None  # so la
    assert gr.bigger_mine([], None, "metal", 2) is None


# ---------- o "Cap": buoc cua Co giap khong dinh sang tab mo ----------
class LevelCtx:
    """O tim kiem gia: nut -/+ doi `level` tung `jump` don vi."""

    def __init__(self, level, jump=1):
        self.level, self.jump = level, jump
        self.cfg = {"gather": {}}
        self.dev = SimpleNamespace(tap=self._tap, idx=1, swipe=lambda *a: None)
        self.W = 540

    def _tap(self, x, y):
        self.level += self.jump if x > 200 else -self.jump

    def find(self, name, fresh=True, th=None):
        if name == "gather/btn_level_minus":
            return (68, 758, 1)
        if name == "gather/btn_level_plus":
            return (476, 758, 1)
        return (100, 640, 1)                                       # tab

    def tap(self, x, y, wait=0):
        pass


def test_rebel_step_does_not_leak_into_resource_tabs(monkeypatch):
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    c = LevelCtx(5)
    c.level_step = 5                                              # hoc o buoc phan quan cung luot ghe
    monkeypatch.setattr(gather, "read_level", lambda ctx: ctx.level)
    assert gather.select_tab(c, "metal")
    assert gather.step_of(c) == 1
    assert gather.set_level(c, 2) and c.level == 2                # truoc P13g: "buoc 5 -> dung cap 5 thay cho 2"
    assert gather.select_tab(c, "mech", name="rebels/tab_mech")
    assert gather.step_of(c) == 5                                 # Co giap van giu buoc 5
    c.jump = 5
    c.level = 10
    assert gather.set_level(c, 7) and c.level == 5


def test_resource_tab_never_learns_a_step_from_a_misread(monkeypatch):
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    reads = iter([8, 4, 4, 4])
    monkeypatch.setattr(gather, "read_level", lambda ctx: next(reads, 4))
    c = LevelCtx(8)
    gather.select_tab(c, "food")
    assert gather.set_level(c, 4)
    assert getattr(c, "level_step", None) is None


# ---------- luong that run() + try_dispatch tren "the gioi" gia ----------
SCREENS = {
    "world": {"gather/btn_search"},
    "search": {"gather/btn_search_go", "gather/chk_full_off"},
    "map": set(),
    "mine": {"gather/btn_gather"},
    "own_mine": set(),                                            # bang mo cua minh: khong co nut Thu thap
    "march": {"gather/btn_march", "gather/btn_recommended"},
}


class Mem:
    def __init__(self):
        self.f, self.ev = {}, []

    def fact(self, idx, key, default=None):
        return self.f.get((idx, key), default)

    def set_fact(self, idx, key, value):
        self.f[(idx, key)] = value

    def log_gather(self, inst, kind, rtype=None, level=None, note=None):
        self.ev.append((kind, rtype, level))


class Store:
    def __init__(self):
        self.d = {"hq_level": 30}

    def inst(self, idx):
        return self.d

    def update(self, idx, **kw):
        self.d.update(kw)


class World:
    """mines[(loai, cap)] = toa do mo ma "Tim kiem" tra ve (khong co = khong tim thay)."""
    W = 540
    POPUP_CLOSERS = ()

    def __init__(self, mines, slots=5, priority=("metal", "food", "alloy"), own_popup=False, read_level=True):
        self.mines, self.slots, self.own_popup, self.level_readable = mines, slots, own_popup, read_level
        self.scr, self.tab, self.level, self.found = "world", None, None, None
        self.searches, self.sent, self.marches_taps = [], [], 0
        self.mem, self.store = Mem(), Store()
        self.dev = SimpleNamespace(idx=1, swipe=lambda *a: None, back=lambda: None, tap=lambda *a: None)
        self.v = SimpleNamespace(has=lambda n: True, find=lambda img, n, **k: self._find(n))
        self.cfg = {"gather": {"priority": list(priority), "max_level": 8, "min_level": 1, "min_hq_level": 9,
                               "only_full": True, "load_ge_mine": True, "node_xy": [270, 452],
                               "same_mine_type_limit": 2},
                    "rebels": {"reserve_legion": False}, "modules": {"rebels": False}}
        self._img = np.zeros((960, 540, 3), np.uint8)
        self.last_dispatch = None

    def _find(self, n):
        return (100, 100, 0.99) if n in SCREENS[self.scr] else None

    def shot(self):
        return self._img

    def find(self, n, fresh=True, th=None):
        return self._find(n)

    def tap_tpl(self, n, wait=0, fresh=True):
        if not self._find(n):
            return False
        if n == "gather/btn_search":
            self.scr = "search"
        elif n == "gather/btn_search_go":
            self.searches.append((self.tab, self.level))
            self.found = self.mines.get((self.tab, self.level))
            self.scr = "map" if self.found else "search"
        elif n == "gather/btn_gather":
            self.scr = "march"
        elif n == "gather/btn_march":
            self.sent.append((self.tab, self.level, self.found))
            self.scr = "world"
        return True

    def tap(self, x, y, wait=0):
        if self.scr == "map":
            taken = self.found in [s[2] for s in self.sent]
            self.scr = "own_mine" if taken and not self.own_popup else "mine"

    def wait_for(self, n, timeout=0):
        return self._find(n)

    def read_marches(self):
        return len(self.sent), self.slots

    def ensure_world(self):
        self.scr = "world"

    def ensure_city(self):
        self.scr = "world"

    def back_out(self):
        self.scr = "world"

    def save_debug(self, name):
        pass

    def close_popups(self):
        pass

    def tap_first(self, *a, **k):
        return False

    def _exp_begin(self, *a):
        pass


@pytest.fixture
def world_ocr(monkeypatch):
    """Cac phep doc man hinh tro vao trang thai World."""
    cur = {}

    def attach(c, load=10_000_000, travel=None):
        cur["c"] = c

        def select_tab(ctx, rtype, name=None):
            ctx.tab = rtype
            return True

        def set_level(ctx, level, misses=2):
            ctx.level = level
            return True

        def text(img, roi, *a, **k):
            if tuple(roi) in [r for r, _ in gather.XY_ROIS]:
                return f"# 32X: {c.found[0]}Y: {c.found[1]}" if c.found else ""
            if tuple(roi[:2]) == (300, 843):
                return str(load)
            if tuple(roi[:2]) == (350, 905):
                return str(travel(c.found) if travel else 400 + (c.found or (0, 0))[0])
            return ""

        monkeypatch.setattr(gather, "select_tab", select_tab)
        monkeypatch.setattr(gather, "set_level", set_level)
        monkeypatch.setattr(gather, "read_level", lambda ctx: ctx.level if ctx.level_readable else None)
        monkeypatch.setattr(gather, "ocr", SimpleNamespace(
            text=text, label_number=lambda img, roi: None,
            amount=lambda s: int(s) if s and s.isdigit() else None,
            seconds=lambda s: int(s) if s and s.isdigit() else None))
        monkeypatch.setattr(gather.screens, "same", lambda a, b, th=2.0: True)
        monkeypatch.setattr(gather.time, "sleep", lambda s: None)
        monkeypatch.setattr(gather, "_ev", lambda *a, **k: None)
        return c

    return attach


M7 = (234, 326)


@pytest.mark.parametrize("own_popup", [False, True])
def test_same_tile_after_taking_metal7_is_never_dispatched_twice(world_ocr, own_popup):
    """'Tim' metal 7/6/5 deu tra lai dung o metal 7 vua gui -> bo, sau 2 lan chuyen sang food tu cap 8 ha dan."""
    mines = {("metal", lv): M7 for lv in range(1, 8)}             # khong co metal 8
    mines.update({("food", 7): (220, 334), ("alloy", 8): (300, 354)})
    c = world_ocr(World(mines, slots=3, own_popup=own_popup))
    # travel khac nhau moi lan tim -> chi toa do moi nhan ra "cung o"
    n = iter(range(100, 10_000, 97))
    world_ocr(c, travel=lambda found: next(n))
    c.mem.set_fact(1, "gather_sig", [30, 0])
    # bo qua luat "cung loai/cap con dang di" de chac chan phai nhan ra bang toa do
    assert gather.run(c) == 3
    tiles = [s[2] for s in c.sent]
    assert len(tiles) == len(set(tiles)) == 3
    assert [s[:2] for s in c.sent] == [("metal", 7), ("food", 7), ("alloy", 8)]
    assert c.searches[:2] == [("metal", 8), ("metal", 7)]
    after = c.searches[2:]
    assert after.index(("food", 8)) < after.index(("food", 7))
    assert ("metal", 4) not in c.searches                         # 2 lan trung -> thoi tim metal


def test_each_type_searches_8_then_7_then_6_ignoring_old_gather_top(world_ocr):
    c = world_ocr(World({("food", 6): (1, 2)}, slots=1, priority=("metal", "food")))
    c.mem.set_fact(1, "gather_top:metal", 2)                      # tri nho cu (truoc P13g) khong con tac dung
    c.mem.set_fact(1, "gather_top:food", 3)
    c.mem.set_fact(1, "gather_sig", [30, 0])
    assert gather.run(c) == 1
    assert c.searches == [("metal", lv) for lv in range(8, 0, -1)] + [("food", 8), ("food", 7), ("food", 6)]


def test_second_visit_remembers_tile_even_if_dispatch_list_rolled(world_ocr):
    c = world_ocr(World({("metal", 8): M7}, slots=5, priority=("metal",)))
    c.mem.set_fact(1, gather.TILES_KEY, [[*M7, round(time.time() - 3600)]])
    assert gather.try_dispatch(c, "metal", 8, 8) == gather.OWN and not c.sent


def test_successful_dispatch_records_tile(world_ocr):
    c = world_ocr(World({("metal", 8): M7}, priority=("metal",)))
    assert gather.try_dispatch(c, "metal", 8, 8) == gather.OK
    assert c.last_dispatch["xy"] == list(M7)
    assert c.mem.fact(1, gather.TILES_KEY)[0][:2] == list(M7)
    assert c.store.d["dispatches"][-1]["xy"] == list(M7)


def test_wrong_level_in_box_is_not_searched(world_ocr, monkeypatch):
    c = world_ocr(World({("metal", 5): M7}, priority=("metal",)))
    monkeypatch.setattr(gather, "read_level", lambda ctx: 5)
    assert gather.try_dispatch(c, "metal", 2, 8) == gather.BADLEVEL
    assert c.searches == [] and c.sent == []


def test_unreadable_level_never_trusts_capacity_table(world_ocr):
    """Khong doc duoc o 'Cap' + khong doc duoc tru luong -> khong gui (truoc: dung dung tich cap muon tim)."""
    c = world_ocr(World({("metal", 2): M7}, priority=("metal",), read_level=False))
    assert gather.try_dispatch(c, "metal", 2, 8) == gather.UNREAD
    assert c.sent == [] and c.mem.fact(1, "mine_cap:metal:2") is None


def test_bigger_amount_on_screen_overrides_table(world_ocr, monkeypatch):
    c = world_ocr(World({("metal", 2): M7}, priority=("metal",)), load=80692)
    monkeypatch.setattr(gather.ocr, "label_number", lambda img, roi: 560000)
    assert gather.try_dispatch(c, "metal", 2, 8) == gather.TOO_BIG
    assert c.sent == [] and c.mem.fact(1, "mine_cap:metal:2") is None


# ---------- anh that (chi co tren may chu du an) ----------
@pytest.mark.fixtures
@pytest.mark.ocr
@pytest.mark.parametrize("name,xy", [
    ("mine_menu_234_326.png", (234, 326)), ("empty_302_354.png", (302, 354)),
    ("busy_bar_55_335.png", (55, 335)), ("popup_274_334.png", (274, 334)),
])
def test_read_mine_xy_real(name, xy):
    img = cv2.imread(os.path.join(FIX, name))
    if img is None or not real_ocr.init(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytest.skip("thieu anh fixture hoac Tesseract")
    assert gather.read_mine_xy(img) == xy
