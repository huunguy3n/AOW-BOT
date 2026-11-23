"""P7-6 (chu du an 2026-11-24): cuop xe Mo khoang san - khong bao gio danh xe dang chay, chi xe cho pha le xanh,
nut lam moi co gioi han + dong hop thoai la, doc 'So lan cuop boc con lai X/4' (0 -> bo). Anh tong hop."""
import types

import cv2
import numpy as np

from bot.modules import play


def _bg():
    img = np.zeros((960, 540, 3), np.uint8)
    img[:] = (60, 110, 150)            # dat nau (BGR)
    return img


def test_burning_truck_red_x_detected():
    img = _bg()
    cv2.rectangle(img, (280, 300), (330, 380), (70, 70, 70), -1)        # than xe xam
    cv2.line(img, (285, 310), (325, 375), (0, 0, 255), 3)                 # dau X do (anh plunder_0)
    cv2.line(img, (325, 310), (285, 375), (0, 0, 255), 3)
    assert play.is_burning(img, 305, 342)


def test_orange_ssr_truck_body_not_burning():
    img = _bg()
    cv2.rectangle(img, (280, 300), (330, 380), (20, 60, 230), -1)       # than xe cam/do dac (SSR) - lap day cao
    assert not play.is_burning(img, 305, 342)
    assert not play.is_burning(_bg(), 305, 342)


def test_crystal_item_by_color():
    img = np.zeros((960, 540, 3), np.uint8)
    img[:] = (140, 60, 90)                                                # nen popup tim
    assert not play.crystal_item(img)
    x, y, _, _ = play.CRYSTAL_ROI
    cv2.rectangle(img, (x + 10, y + 10), (x + 40, y + 50), (255, 230, 150), -1)   # pha le xanh nhat (BGR)
    assert play.crystal_item(img)
    img2 = np.zeros((960, 540, 3), np.uint8)
    cv2.rectangle(img2, (x + 10, y + 10), (x + 40, y + 50), (40, 200, 240), -1)   # hop qua vang
    assert not play.crystal_item(img2)


class V:
    def __init__(self, have=(), seen=()):
        self.have, self.seen = set(have), set(seen)

    def has(self, name):
        return name in self.have

    def find(self, img, name, **k):
        return (489, 203, 0.9) if name in self.seen else None


class Ctx:
    POPUP_CLOSERS = ("common/btn_x",)

    def __init__(self, v, tab_after=True):
        self.v, self.taps, self.debug, self.tab_after = v, [], [], tab_after

    def tap_tpl(self, name, **k):
        if name in self.v.seen:
            self.taps.append(name)
            if name == "play/btn_refresh" and not self.tab_after:
                self.v.seen.discard("play/tab_others")
            return True
        return False

    def find(self, name, **k):
        return self.v.find(None, name)

    def tap_first(self, names, **k):
        self.taps.append("close")

    def save_debug(self, tag):
        self.debug.append(tag)


def test_refresh_missing_template_skips():
    c = Ctx(V())
    assert not play.refresh_trucks(c, {"refresh_max": 3}) and c.taps == []


def test_refresh_capped():
    c = Ctx(V({"play/btn_refresh"}, {"play/btn_refresh", "play/tab_others"}))
    assert [play.refresh_trucks(c, {"refresh_max": 2}) for _ in range(3)] == [True, True, False]


def test_refresh_unexpected_popup_closes_and_stops():
    c = Ctx(V({"play/btn_refresh"}, {"play/btn_refresh", "play/tab_others"}), tab_after=False)
    assert not play.refresh_trucks(c, {"refresh_max": 3})
    assert c.taps == ["play/btn_refresh", "close"] and c.debug == ["loot_refresh_popup"]
    assert not play.refresh_trucks(c, {"refresh_max": 3})              # khong lam moi nua trong luot nay


def test_loot_counter_zero_skips(monkeypatch):
    c = types.SimpleNamespace(cfg={"loot": {}}, v=V(seen={"play/tab_others"}), shot=lambda: None,
                              tap_tpl=lambda *a, **k: True, tap=lambda *a, **k: None,
                              march_full=lambda: (_ for _ in ()).throw(AssertionError("khong toi day")))
    monkeypatch.setattr(play, "loot_left", lambda img: 0)
    monkeypatch.setattr(play, "loot_trucks", lambda img: [])
    assert play.loot(c) == 0
