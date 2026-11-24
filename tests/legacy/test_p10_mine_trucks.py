"""P10-4 (live-run-3 15:38:58): sau "nhan ruong xe khai thac" bang "Chuc mung nhan duoc" (s153857) con de len man ->
mine_trucks.run() khong thay tieu de Mo khoang san va tra 0 LANG LE: khong mo tab "Xe khai thac cua toi", khong doc X/4.
Nay: dong bang qua / cho tieu de roi moi chay luong P9-6, log X/4 va ket qua tung xe."""
import logging
import types

import numpy as np

from bot import buttons, ocr
from bot.modules import mine_trucks as M
from bot.modules import play


class Ctx:
    def __init__(self, title_after=2):
        self.cfg = {}
        self.taps, self.debug, self.dismiss = [], [], 0
        self.title_after = title_after
        self.dev = types.SimpleNamespace(swipe=lambda *a, **k: self.taps.append("swipe"))

    def shot(self):
        return np.zeros((960, 540, 3), np.uint8)

    def find(self, name, **k):
        if name == "play/mine_title":
            return (270, 20, 1.0) if self.dismiss >= self.title_after else None
        return None

    def dismiss_reward(self):
        self.dismiss += 1

    def tap(self, x, y, wait=1.0):
        assert M.safe_tap_point(x, y)
        self.taps.append((x, y))

    def back_out(self, n=1):
        self.taps.append("back")

    def save_debug(self, tag):
        self.debug.append(tag)


def test_reward_popup_closed_then_my_trucks_tab_opened(monkeypatch, caplog):
    monkeypatch.setattr(M.time, "sleep", lambda s: None)
    monkeypatch.setattr(ocr, "text", lambda *a, **k: "So lan khai thac con lai:0/4")
    c = Ctx(title_after=1)
    caplog.set_level(logging.INFO, logger="aow")
    assert M.run(c) == 0
    assert c.dismiss == 1 and M.TAB_MINE in c.taps                 # dong bang qua roi mo tab Xe khai thac cua toi
    assert "con 0/4" in caplog.text and "het luot" in caplog.text


def test_no_title_logs_and_saves(monkeypatch, caplog):
    monkeypatch.setattr(M.time, "sleep", lambda s: None)
    c = Ctx(title_after=99)
    caplog.set_level(logging.INFO, logger="aow")
    assert M.run(c) == 0
    assert "mine_trucks_no_title" in c.debug and "khong ve duoc man Mo khoang san" in caplog.text
    assert M.TAB_MINE not in c.taps


def test_normal_truck_departs_and_logs_result(monkeypatch, caplog):
    monkeypatch.setattr(M.time, "sleep", lambda s: None)
    lefts = iter(["4/4", "Mien phi", "3/4", "3/4", "3/4"])
    monkeypatch.setattr(ocr, "text", lambda *a, **k: next(lefts, "3/4"))
    plus = [[(153, 478)], []]
    monkeypatch.setattr(M, "plus_marks", lambda img: plus[0] if plus else [])
    monkeypatch.setattr(M, "rarity_letter", lambda img: "N")
    monkeypatch.setattr(play, "crystal_item", lambda img, roi: False)

    def depart(ctx):
        plus.pop(0)
        return True
    monkeypatch.setattr(M, "normal_depart", depart)
    monkeypatch.setattr(M, "refresh_allowed", lambda label: False)
    c = Ctx(title_after=0)
    caplog.set_level(logging.INFO, logger="aow")
    assert M.run(c) == 1
    assert "luot 4/4 -> 3/4" in caplog.text and "dua di 1 xe" in caplog.text


def test_mine_calls_my_trucks_after_chest(monkeypatch):
    """play.mine: ruong -> mine_trucks.run duoc goi (truoc khi cuop xe)."""
    order = []

    class C(Ctx):
        def tap_tpl(self, name, **k):
            return name == "play/card_mine"

        def wait_for(self, name, **k):
            return True

        def find(self, name, **k):
            if name == "play/mine_chest":
                order.append("chest")
                return (161, 354, 0.9) if order.count("chest") == 1 else None
            return None

        def tap(self, x, y, wait=1.0):
            pass
    monkeypatch.setattr(M, "run", lambda ctx: order.append("my_trucks") or 0)
    c = C()
    c.cfg = {"loot": {"enabled": False}}
    play.mine(c)
    assert order.index("my_trucks") > order.index("chest")


def test_attention_never_ticks_checkbox(monkeypatch):
    monkeypatch.setattr(buttons, "with_text", lambda *a, **k: [buttons.Button(105, 408, 40, 40, "claim", 85, "x")])
    c = Ctx(0)
    assert M.attention_confirm(c) is False and c.taps == []      # nut trung o tick -> KHONG cham
