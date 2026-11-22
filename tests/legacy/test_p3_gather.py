"""P3-2/3/4: hop thoai 'Chi huy truong khac', mo cua chinh minh, mo bi chiem / thong bao msg_*, dung tich mo day."""
import os
import time
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from bot import gather_rules as gr
from bot import ocr as real_ocr
from bot import tplneed
from bot.modules import gather
from bot.vision import Vision

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
FIX = os.path.join(ROOT, "tests", "fixtures", "gather_p3")
NOW = 1_795_340_000.0


# ---------- luat thuan ----------
def test_table_cap_defaults_and_unknown():
    assert gr.table_cap(None, "metal", 7) == 1040000
    assert gr.table_cap(None, "alloy", 8) == 82500
    assert gr.table_cap(None, "alloy", 1) is None             # hop kim thap nhat cap 3
    assert gr.table_cap(None, "oil", 5) is None               # chua do
    assert gr.table_cap({"metal": [1, 2]}, "metal", 2) == 2   # config de len mac dinh
    assert gr.table_cap(None, "gems", 1) is None


def test_choose_amount_uses_cap_when_ocr_bad():
    assert gr.choose_amount(None, 1320000) == (1320000, "bang")      # 111 lan gather_unread
    assert gr.choose_amount(40000, 1040000) == (1040000, "bang")     # OCR rot '10' -> khong gui doi nho vao mo lon
    assert gr.choose_amount(800000, 800000) == (800000, "ocr")
    assert gr.choose_amount(13200000, 1320000) == (1320000, "bang")  # thua chu so
    assert gr.choose_amount(None, None) == (None, None)               # khong biet -> UNREAD nhu cu
    assert gr.choose_amount(35000, 1320000, only_full=False) == (35000, "ocr")


def test_choose_amount_never_below_cap_for_full_mines():
    for cap in (10000, 62500, 1320000):
        for read in (None, 1, cap // 2, cap * 0.95, cap, cap * 1.2, cap * 3):
            amt, _ = gr.choose_amount(read, cap)
            assert amt >= cap * 0.9


def test_own_target_matches_log_22_11():
    """#1 22/11: 16:44:47 gui metal cap 1 (di 1008 s); 16:45:38 tim lai metal cap 1 -> cung 1008 s = cung mo."""
    d = [{"type": "metal", "level": 1, "travel": 1008, "t": NOW},
         {"type": "food", "level": 1, "travel": 1009, "t": NOW + 68}]
    assert gr.own_target(d, "metal", 1, NOW + 51, travel=1008) is d[0]
    assert gr.own_target(d, "metal", 1, NOW + 51) is d[0]               # kiem truoc khi tim
    assert gr.own_target(d, "metal", 1, NOW + 51, travel=600) is None   # mo khac (xa/gan hon)
    assert gr.own_target(d, "metal", 2, NOW + 51) is None
    assert gr.own_target(d, "metal", 1, NOW + 1008 + 61) is None        # doi da toi mo -> mo het day
    assert gr.own_target(d, "food", 1, NOW + 120, travel=1009) is d[1]
    assert gr.own_target([{"type": "metal", "level": 1, "travel": None, "t": NOW}], "metal", 1, NOW + 5) is None


@pytest.mark.parametrize("text,kind", [
    ("Chu y! Co Chi huy truong khac dang hanh quan den diem tai nguyen nay, neu ban tiep tuc hanh quan, co the "
     "se xay ra chien tranh! muon tiep tuc xuat chinh?", "contested"),
    ("Chú ý! Có Chỉ huy trưởng khác đang hành quân đến điểm", "contested"),
    ("Chi huy trudng khac dang hanh quan", "contested"),               # OCR 'eng' sai chu
    ("So doi hanh quan da dat toi da", "march_full"),
    ("Khong du binh linh", "no_troops"),
    ("Diem tai nguyen da bi chiem", "occupied"),
    ("Khong tim thay diem tai nguyen phu hop", "not_found"),
    ("Ban chua dat cap 10, tam thoi khong the thu thap", "locked"),
    ("Radar mo khoa cap 1", None),
    ("", None),
])
def test_classify_msg(text, kind):
    assert gr.classify_msg(text) == kind


def test_skip_until():
    cfg = {"contested_skip_min": 20}
    assert gr.skip_until("contested", NOW, cfg) == NOW + 1200
    assert gr.skip_until("occupied", NOW, {}) == NOW + 1800
    assert gr.skip_until("toobig", NOW, cfg) is None


# ---------- luong try_dispatch voi man hinh gia ----------
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
    def __init__(self, dispatches=None):
        self.d = {"dispatches": list(dispatches or [])}

    def inst(self, idx):
        return self.d

    def update(self, idx, **kw):
        self.d.update(kw)


SCREENS = {
    "world": {"gather/btn_search"},
    "search": {"gather/btn_search_go", "gather/tab_metal", "gather/chk_full_off"},
    "map": set(),
    "mine": {"gather/btn_gather"},
    "mine_taken": {"gather/mine_occupied"},
    "march": {"gather/btn_march", "gather/btn_recommended"},
    "dialog": {"common/btn_cancel_exit", "gather/dlg_contested"},
    "dialog_other": {"common/btn_cancel_exit"},
}
NEXT = {("world", "gather/btn_search"): "search", ("search", "gather/btn_search_go"): "map",
        ("mine", "gather/btn_gather"): "march", ("dialog", "common/btn_cancel_exit"): "march",
        ("dialog_other", "common/btn_cancel_exit"): "march"}


class V:
    def __init__(self, c, missing=()):
        self.c, self.missing = c, set(missing)

    def has(self, n):
        return n not in self.missing

    def find(self, img, n, th=None, roi=None):
        return (100, 100, 0.99) if n in SCREENS[self.c.scr] and n not in self.missing else None


class Ctx:
    W = 540
    POPUP_CLOSERS = ()

    def __init__(self, mine="mine", after_march="world", dispatches=None, missing=()):
        self.scr, self.taps = "world", []
        self.mine, self.after_march = mine, after_march
        self.v = V(self, missing)
        self.mem, self.store = Mem(), Store(dispatches)
        self.dev = SimpleNamespace(idx=1, swipe=lambda *a: None, back=lambda: None, tap=lambda *a: None)
        self.cfg = {"gather": {"node_xy": [270, 452], "only_full": True, "load_ge_mine": True, "priority": ["metal"],
                               "max_level": 8, "min_level": 1}}
        self._img = np.zeros((960, 540, 3), np.uint8)
        self.last_dispatch = None

    def shot(self):
        return self._img

    def find(self, n, fresh=True, th=None):
        return self.v.find(None, n)

    def tap_tpl(self, n, wait=0, fresh=True):
        if not self.v.find(None, n):
            return False
        self.taps.append(n)
        if n == "gather/btn_march":
            self.scr = self.after_march
        else:
            self.scr = NEXT.get((self.scr, n), self.scr)
        return True

    def tap(self, x, y, wait=0):
        self.taps.append(("xy", x, y))
        if self.scr == "map":
            self.scr = self.mine

    def wait_for(self, n, timeout=0):
        return self.v.find(None, n)

    def ensure_world(self):
        self.scr = "world"

    def back_out(self):
        self.scr = "world"

    def save_debug(self, name):
        self.taps.append(("debug", name))

    def close_popups(self):
        pass

    def tap_first(self, *a, **k):
        return False

    def _exp_begin(self, *a):
        pass


@pytest.fixture
def fake_ocr(monkeypatch):
    texts = {"load": "517590", "travel": "00:16:48", "msg": ""}

    def text(img, roi, *a, **k):
        if tuple(roi[:2]) == (300, 843):
            return texts["load"]
        if tuple(roi[:2]) == (350, 905):
            return texts["travel"]
        return texts["msg"]

    ns = SimpleNamespace(text=text, label_number=lambda img, roi: None,
                         amount=lambda s: int(s) if s and s.isdigit() else None,
                         seconds=lambda s: 1008 if s == "00:16:48" else None)
    monkeypatch.setattr(gather, "ocr", ns)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    return texts


def test_unread_amount_uses_mine_cap_and_dispatches(fake_ocr):
    c = Ctx()
    assert gather.try_dispatch(c, "metal", 1, 8) == gather.OK
    assert c.last_dispatch["amount"] == 40000 and c.last_dispatch["travel"] == 1008
    assert ("cap_table", "metal", 1) in c.mem.ev
    assert "gather/btn_march" in c.taps


def test_own_mine_is_not_dispatched(fake_ocr):
    """Doi minh vua gui toi metal cap 1 (di 1008 s): khong bam Xuat chinh -> khong co hop thoai -> khong Huy oan."""
    c = Ctx(dispatches=[{"type": "metal", "level": 1, "travel": 1008, "t": time.time() - 51}], after_march="dialog")
    assert gather.try_dispatch(c, "metal", 1, 8) == gather.OWN
    assert "gather/btn_march" not in c.taps and "common/btn_cancel_exit" not in c.taps


def test_skip_reason_before_search_for_own_mine():
    c = Ctx(dispatches=[{"type": "metal", "level": 1, "travel": 1008, "t": time.time() - 51}])
    assert "doi minh" in gather.skip_reason(c, "metal", 1)
    assert gather.skip_reason(c, "metal", 2) is None
    assert ("own_skip", "metal", 1) in c.mem.ev


def test_contested_dialog_cancels_never_continues(fake_ocr):
    c = Ctx(after_march="dialog")
    assert gather.try_dispatch(c, "metal", 1, 8) == gather.CONTESTED
    assert "common/btn_cancel_exit" in c.taps
    assert not any("continue" in str(t) or "tiep" in str(t) for t in c.taps)
    assert ("contested", "metal", 1) in c.mem.ev
    assert c.last_dispatch is None                       # khong ghi doi ao


def test_contested_dialog_without_template_uses_ocr(fake_ocr):
    fake_ocr["msg"] = "Chu y! Co Chi huy truong khac dang hanh quan den diem tai nguyen nay"
    c = Ctx(after_march="dialog", missing={"gather/dlg_contested"})
    assert gather.try_dispatch(c, "metal", 1, 8) == gather.CONTESTED


def test_unknown_dialog_is_error_and_counted(fake_ocr):
    c = Ctx(after_march="dialog_other")
    assert gather.try_dispatch(c, "metal", 1, 8) == gather.ERROR
    assert ("dialog_unknown", "metal", 1) in c.mem.ev


def test_occupied_mine_returns_and_never_taps_popup(fake_ocr):
    c = Ctx(mine="mine_taken")
    assert gather.try_dispatch(c, "metal", 1, 8) == gather.OCCUPIED
    assert "gather/btn_gather" not in c.taps


def test_missing_message_templates_do_not_crash(fake_ocr, caplog):
    """Thieu msg_* / mine_occupied: bo qua nhanh, log 'thieu anh mau <ten>', van gui duoc."""
    tplneed._last.clear()
    miss = {"gather/msg_not_found", "gather/msg_march_full", "gather/msg_no_troops", "gather/mine_occupied"}
    c = Ctx(missing=miss)
    with caplog.at_level("INFO", logger="aow"):
        assert gather.try_dispatch(c, "metal", 1, 8) == gather.OK
    assert "thieu anh mau gather/msg_not_found" in caplog.text
    assert "thieu anh mau gather/msg_march_full" in caplog.text


def test_hold_then_skip_reason():
    c = Ctx()
    gather.hold(c, "alloy", 8, gather.NOT_FOUND)
    assert "tam bo (not_found)" in gather.skip_reason(c, "alloy", 8)
    gather.hold(c, "alloy", 7, gather.TOO_BIG)              # khong phai ly do tam bo qua lan ghe
    assert gather.skip_reason(c, "alloy", 7) is None


# ---------- anh that (chi co tren may chu du an) ----------
@pytest.mark.fixtures
def test_contested_template_matches_real_dialog():
    img = cv2.imread(os.path.join(FIX, "march_confirm_own_i1.png"))
    if img is None:
        pytest.skip("thieu anh fixture")
    v = Vision(os.path.join(ROOT, "templates"))
    assert v.find(img, "gather/dlg_contested")
    assert v.find(img, "common/btn_cancel_exit")
    world = cv2.imread(os.path.join(FIX, "march_4-5.png"))
    assert not v.find(world, "gather/dlg_contested")


@pytest.mark.fixtures
@pytest.mark.ocr
def test_contested_dialog_ocr_real():
    img = cv2.imread(os.path.join(FIX, "march_confirm_own_i1.png"))
    if img is None or not real_ocr.init(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytest.skip("thieu anh fixture hoac Tesseract")
    assert gr.classify_msg(real_ocr.text(img, gather.DLG_BAND, scale=2, psm=6)) == "contested"
