"""P10-1 (live-run-3 15:39:09): popup cuop SSR THAT bi toast "Da chuyen doi sang sv ServerID #6" de len -> bot phan loai
server_change va bo xe. Phan loai theo nut "Cuop boc"; toast chi tinh khi KHONG co nut. Loc som luc chien: ho ve
108.031.985 >= tong luc chien ta 79.829.544 -> bo (truoc day log "CHON DUOC" vi chua biet luc doi)."""
import os
import types

import cv2
import pytest

from bot import ocr
from bot.modules import play

LIVE3 = "logs/shots/20261124-153909-i1-loot_popup_server_change.png"   # ADB 540x960 live3: popup SSR dung + toast
LIVE2 = "data/pm-shots/owner-20261124/live2/auto/s110411.png"            # ADB: xe N + toast, chi nut "Xem"
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def _img(p):
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    return cv2.imread(p)


def _ocr():
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")


def _ctx():
    return types.SimpleNamespace(v=types.SimpleNamespace(find=lambda *a, **k: None))


def test_live3_popup_with_toast_is_loot():
    img = _img(LIVE3)
    _ocr()
    assert play.server_toast(img)                         # toast co that tren anh
    btn = play.loot_button(_ctx(), img)
    assert btn and btn[0] >= 300 and abs(btn[1] - 575) <= 10
    assert play.world_rarity(img) == "SSR"
    assert play.world_popup_kind(play.world_rarity(img), btn, True) == "loot"


def test_live2_real_server_change_still_closed():
    img = _img(LIVE2)
    _ocr()
    btn = play.loot_button(_ctx(), img)
    assert btn is None
    assert play.world_popup_kind(play.world_rarity(img), btn, play.server_toast(img)) == "server_change"


def test_kind_rules():
    assert play.world_popup_kind("SSR", (347, 574), True) == "loot"
    assert play.world_popup_kind("SSR", None, True) == "server_change"
    assert play.world_popup_kind("N", (347, 574), True) == "wrong_rarity"
    assert play.world_popup_kind("SR", None, False) == "no_loot_btn"


def test_world_popup_waits_for_toast_to_fade(monkeypatch):
    seq = [(None, True), (None, True), ((347, 574), False)]
    state = {}

    def btn(ctx, img):
        state["cur"] = seq.pop(0) if seq else ((347, 574), False)
        return state["cur"][0]
    monkeypatch.setattr(play, "loot_button", btn)
    monkeypatch.setattr(play, "server_toast", lambda img: state["cur"][1])
    monkeypatch.setattr(play, "world_rarity", lambda img: "SSR")
    monkeypatch.setattr(play.time, "sleep", lambda s: None)
    c = types.SimpleNamespace(shot=lambda: None)
    assert play.world_popup(c, ("SSR", "SR"), timeout=5) == ("loot", (347, 574))


def test_pre_check_guard_stronger_than_account():
    ok, why = play.pre_check(108031985, None, 79829544)
    assert not ok and "tong luc chien" in why
    ok, why = play.pre_check(50_000_000, None, 79829544)
    assert ok and why.startswith("tam")                   # chua biet luc doi -> kiem lai o man doi hinh
    assert not play.pre_check(108031985, 90_000_000, 300_000_000)[0]   # luc doi biet -> so voi doi, khong tong
    assert play.pre_check(80_000_000, 90_000_000, 300_000_000)[0]
    assert not play.pre_check(None, 90_000_000)[0]       # OCR hong -> bo an toan


def test_formation_check_uses_legion_not_account():
    assert not play.power_check(108031985, 79_000_000)[0]
    assert not play.power_check(None, 79_000_000)[0]
    assert not play.power_check(100, None)[0]
