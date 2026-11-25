"""P8-2 (chu du an 2026-11-24): truoc khi cuop xe so luc chien ho ve (popup xe) voi luc chien doi hinh ta (man
"Chien dau", sau "Doi hinh de xuat"). Lan thua that: ho ve 243.560.931 > ta 222.749.681. Ho ve >= ta -> KHONG bam
Chien dau, thoat, danh dau xe da bo, thu xe khac. Khong doc duoc so -> bo xe."""
import logging
import os
import types

import cv2
import pytest

from bot import ocr
from bot.modules import play


@pytest.fixture(autouse=True)
def _full_robbed(monkeypatch):
    """P13-6: xe luon 2/2 trong cac test cu (doc 'So lan bi cuop' co test rieng o test_p13_loot_robbed)."""
    monkeypatch.setattr(play, "robbed_left", lambda img: (2, 2))

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


@pytest.mark.parametrize(("guard", "ours", "margin", "ok"), [
    (243560931, 222749681, 0.0, False),     # lan thua that (anh plunder2) -> bo
    (98565656, 222749681, 0.0, True),       # xe SR anh ADB truck1 -> danh
    (222749681, 222749681, 0.0, False),     # bang nhau -> bo
    (210000000, 222749681, 0.1, False),     # margin 10 %: ta < ho ve x 1,1 -> bo
    (200000000, 222749681, 0.1, True),
    (None, 222749681, 0.0, False),          # khong doc duoc ho ve -> bo
    (98565656, None, 0.0, False),           # khong doc duoc ta -> bo
    (0, 222749681, 0.0, False),
])
def test_power_check(guard, ours, margin, ok):
    assert play.power_check(guard, ours, margin)[0] is ok


def test_power_check_reason_text():
    ok, why = play.power_check(243560931, 222749681)
    assert not ok and why == "ho ve 243,560,931 >= ta 222,749,681"


def test_skip_memory_expires():
    lm = {}
    play._mark_skip(lm, "(JED)Abc", 243560931, now=1000.0)
    assert play._skipped(lm, "(JED)Abc", None, now=2000.0)
    assert play._skipped(lm, "", 243000000, now=2000.0)              # luc chien +-1 %
    assert not play._skipped(lm, "Other", 100000000, now=2000.0)
    assert not play._skipped(lm, "(JED)Abc", 243560931, now=1000.0 + play.SKIP_H * 3600 + 1)


# ---------------------------------------------------------------- luong (gia lap man hinh)
class Mem:
    def __init__(self):
        self.d = {}

    def fact(self, idx, k):
        return self.d.get(k)

    def set_fact(self, idx, k, v):
        self.d[k] = v


class V:
    SEEN = frozenset({"play/tab_others", "play/btn_go_loot"})

    def find(self, img, name, **k):
        return (300, 300, 0.95) if name in self.SEEN else None

    def has(self, name):
        return True


class Ctx:
    def __init__(self, reopen=True):
        self.cfg = {"loot": {"crystal_only": True, "refresh_max": 0, "max_attempts": 2}}
        self.v, self.mem, self.dev = V(), Mem(), types.SimpleNamespace(idx=1)
        self.taps, self.debug, self.reopen = [], [], reopen

    def shot(self):
        return None

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def tap_tpl(self, name, **k):
        self.taps.append(name)
        return name != "play/card_mine" or self.reopen

    def wait_for(self, name, **k):
        return True

    def march_full(self):
        return False

    def back_out(self, n=1):
        self.taps.append("back")

    def ensure_city(self):
        self.taps.append("city")

    def save_debug(self, tag):
        self.debug.append(tag)

    def tap_first(self, *a, **k):
        pass


@pytest.fixture
def scene(monkeypatch):
    s = types.SimpleNamespace(guards=[243560931], own=222749681, result="win")
    monkeypatch.setattr(play, "loot_left", lambda img: 2)
    monkeypatch.setattr(play, "loot_trucks", lambda img: [("purple", 300, 400)])
    monkeypatch.setattr(play, "is_burning", lambda img, x, y: False)
    monkeypatch.setattr(play, "popup_rarity", lambda img: "SR")
    monkeypatch.setattr(play, "has_crystal", lambda ctx, img: True)
    monkeypatch.setattr(play, "guard_power", lambda img: s.guards[0] if len(s.guards) == 1 else s.guards.pop(0))
    monkeypatch.setattr(play, "own_power", lambda img: s.own)
    monkeypatch.setattr(play, "open_menu", lambda ctx: True)
    monkeypatch.setattr(play, "_loot_result", lambda ctx: s.result)
    monkeypatch.setattr(play, "world_popup", lambda ctx, rar, timeout=6.0: ("loot", (346, 575)))   # P9-5
    monkeypatch.setattr(ocr, "text", lambda *a, **k: "(JED)Guard")
    return s


def test_stronger_guard_never_battles(scene, caplog):
    caplog.set_level(logging.INFO, logger="aow")
    c = Ctx()
    assert play.loot(c) == 0
    assert "play/btn_battle" not in c.taps                         # KHONG bao gio bam Chien dau
    assert "play/btn_arena_recommend" in c.taps                    # doi hinh de xuat truoc khi doc luc chien ta
    assert "back" in c.taps
    assert "Cuop boc: ho ve 243,560,931 > ta 222,749,681 -> bo" in caplog.text
    lm = c.mem.d["loot_mem"]
    assert lm["legion"] == 222749681 and lm["skip"][0]["power"] == 243560931
    # lan 2 (mo lai Mo khoang san): xe da bo bi loc ngay o popup (biet luc chien ta) -> khong mo man doi hinh nua
    assert c.taps.count("play/btn_go_loot") == 1


def test_weaker_guard_battles(scene, caplog):
    caplog.set_level(logging.INFO, logger="aow")
    scene.guards = [98565656]
    c = Ctx()
    assert play.loot(c) == 1
    i_rec, i_bat = c.taps.index("play/btn_arena_recommend"), c.taps.index("play/btn_battle")
    assert i_rec < i_bat
    assert c.mem.d["loot_mem"]["win_max"] == 98565656


def test_unreadable_own_power_skips(scene):
    scene.own = None
    c = Ctx(reopen=False)
    assert play.loot(c) == 0
    assert "play/btn_battle" not in c.taps and "loot_own_power" in c.debug


def test_skip_then_try_other_truck(scene, monkeypatch):
    """Xe 1 ho ve manh hon -> bo -> mo lai Mo khoang san -> xe 2 (yeu hon) -> danh."""
    trucks = iter([[("purple", 300, 400)], [("purple", 300, 400)], [("orange", 200, 500)], [("orange", 200, 500)]])
    last = [[("purple", 300, 400)]]

    def lt(img):
        last[0] = next(trucks, last[0])
        return last[0]

    monkeypatch.setattr(play, "loot_trucks", lt)
    names = iter(["(JED)Strong"])
    monkeypatch.setattr(ocr, "text", lambda *a, **k: next(names, "(ABC)Weak"))
    scene.guards = [243560931, 98565656]
    c = Ctx()
    assert play.loot(c) == 1
    assert c.taps.count("play/btn_battle") == 1 and "play/card_mine" in c.taps


def test_old_rules_kept(scene, monkeypatch):
    """Luat cu van giu: khong pha le -> bo; do hiem R -> bo; X/4 = 0 -> khong lam gi."""
    monkeypatch.setattr(play, "has_crystal", lambda ctx, img: False)
    c = Ctx()
    assert play.loot(c) == 0 and "play/btn_go_loot" not in c.taps
    monkeypatch.setattr(play, "has_crystal", lambda ctx, img: True)
    monkeypatch.setattr(play, "popup_rarity", lambda img: "R")
    c = Ctx()
    assert play.loot(c) == 0 and "play/btn_go_loot" not in c.taps
    monkeypatch.setattr(play, "loot_left", lambda img: 0)
    c = Ctx()
    assert play.loot(c) == 0 and c.taps.count((300, 400)) == 0


# ---------------------------------------------------------------- OCR tren anh that
@pytest.mark.fixtures
@pytest.mark.ocr
def test_ocr_guard_and_own_power_real_shots():
    t = cv2.imread(os.path.join(ROOT, "data", "pm-shots", "owner-20261124", "p8-adb", "truck1.png"))
    f = cv2.imread(os.path.join(ROOT, "tests", "fixtures", "loot_legion_i1.png"))
    if t is None or f is None or not ocr.init(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytest.skip("thieu anh hoac Tesseract")
    assert play.guard_power(t) == 98565656
    assert play.own_power(f) == 220020045
    assert play.power_check(play.guard_power(t), play.own_power(f))[0]
