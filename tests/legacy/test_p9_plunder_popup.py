"""P9-5 (chu du an 2026-11-24, live-run-2 11:04): sau "Toi cuop boc" XAC NHAN dung popup cuop tren ban do (SR/SSR + nut
"Cuop boc" ben phai); popup "Da chuyen doi sang sv ServerID #28" / xe N chi co "Xem" -> dong, bo xe, chon xe khac.
Khong bao gio bam "Xem"."""
import os
import types

import cv2
import pytest

from bot import buttons, ocr
from bot.modules import play


@pytest.fixture(autouse=True)
def _full_robbed(monkeypatch):
    """P13-6: xe luon 2/2 trong cac test cu (doc 'So lan bi cuop' co test rieng o test_p13_loot_robbed)."""
    monkeypatch.setattr(play, "robbed_left", lambda img: (2, 2))

LIVE2 = "data/pm-shots/owner-20261124/live2/auto/s110411.png"           # ADB 540x960: xe N + thong bao doi server
GOOD = "data/pm-shots/owner-20261124/plunder_1_ssr_truck_cuop_boc.png"  # anh chu du an (535x955): popup SSR dung
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def _img(p):
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    img = cv2.imread(p)
    return img if img.shape[:2] == (960, 540) else cv2.resize(img, (540, 960))


def _ocr():
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")


def test_kind_pure():
    assert play.world_popup_kind("SSR", (346, 575), False) == "loot"
    assert play.world_popup_kind("SR", (346, 575), False) == "loot"
    assert play.world_popup_kind("N", None, True) == "server_change"
    assert play.world_popup_kind("SSR", (346, 575), True) == "loot"   # P10-1: co nut Cuop boc -> bo qua toast
    assert play.world_popup_kind("SSR", None, False) == "no_loot_btn"
    assert play.world_popup_kind("N", (346, 575), False) == "wrong_rarity"


def test_live2_server_change_popup_recognised():
    img = _img(LIVE2)
    _ocr()
    assert play.world_rarity(img) == "N"
    assert play.server_toast(img)
    v = types.SimpleNamespace(v=types.SimpleNamespace(find=lambda *a, **k: None))
    assert play.loot_button(v, img) is None                      # chi co nut "Xem" (276,574) -> khong tra
    assert play.world_popup_kind(play.world_rarity(img), None, True) == "server_change"


def test_correct_popup_recognised_and_xem_never_returned():
    img = _img(GOOD)
    _ocr()
    assert play.world_rarity(img) == "SSR"
    assert not play.server_toast(img)
    ctx = types.SimpleNamespace(v=types.SimpleNamespace(find=lambda *a, **k: None))
    btn = play.loot_button(ctx, img)
    assert btn and btn[0] >= 300 and abs(btn[1] - 575) <= 10      # "Cuop boc" ben phai, khong phai "Xem" (~201)
    assert play.world_popup_kind(play.world_rarity(img), btn, False) == "loot"


def test_template_match_left_side_ignored(monkeypatch):
    """Anh mau btn_loot khop nham o ben trai (nut Xem) -> khong bam."""
    ctx = types.SimpleNamespace(v=types.SimpleNamespace(find=lambda *a, **k: (201, 575, 0.9)))
    monkeypatch.setattr(buttons, "with_text", lambda *a, **k: [])
    assert play.loot_button(ctx, None) is None


class Ctx:
    def __init__(self):
        self.cfg = {"loot": {"crystal_only": True, "refresh_max": 0, "max_attempts": 2}}
        self.v = types.SimpleNamespace(find=lambda img, name, **k: (300, 300, 0.95)
                                       if name in ("play/tab_others", "play/btn_go_loot") else None,
                                       has=lambda n: True)
        self.mem = types.SimpleNamespace(d={}, fact=lambda i, k: self.mem.d.get(k),
                                         set_fact=lambda i, k, v: self.mem.d.__setitem__(k, v))
        self.dev = types.SimpleNamespace(idx=1)
        self.taps, self.debug = [], []

    def shot(self):
        return None

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def tap_tpl(self, name, **k):
        self.taps.append(name)
        return True

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


def test_flow_server_change_skips_truck_and_tries_another(monkeypatch):
    kinds = [("server_change", None), ("loot", (346, 575))]
    guards = [98565656, 98000000]
    monkeypatch.setattr(play, "loot_left", lambda img: 3)
    monkeypatch.setattr(play, "loot_trucks", lambda img: [("purple", 300, 400)])
    monkeypatch.setattr(play, "is_burning", lambda img, x, y: False)
    monkeypatch.setattr(play, "popup_rarity", lambda img: "SR")
    monkeypatch.setattr(play, "has_crystal", lambda ctx, img: True)
    monkeypatch.setattr(play, "guard_power", lambda img: guards[0])
    monkeypatch.setattr(play, "own_power", lambda img: 222749681)
    monkeypatch.setattr(play, "open_menu", lambda ctx: True)
    monkeypatch.setattr(play, "_loot_result", lambda ctx: "win")
    monkeypatch.setattr(play, "world_popup", lambda ctx, rar, timeout=6.0: kinds.pop(0))
    names = iter(["(BoS)blackmam!", "(X)Other"] * 4)
    monkeypatch.setattr(ocr, "text", lambda *a, **k: next(names))
    c = Ctx()

    def mark(lm, name, pw, now=None):
        guards.pop(0)                                 # xe vua bo -> lan sau doc xe khac
        lm.setdefault("skip", []).append({"name": name, "power": pw, "at": 0})
    monkeypatch.setattr(play, "_mark_skip", mark)
    assert play.loot(c) == 1
    assert "loot_popup_server_change" in c.debug
    assert c.taps.count("play/btn_battle") == 1 and (346, 575) in c.taps
    assert "play/btn_loot" not in c.taps              # bam toa do nut "Cuop boc" da xac nhan
