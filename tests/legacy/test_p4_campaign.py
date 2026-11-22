"""P4 muc 4 (PM 2026-11-23): Chien dich - man "Cai dat quan doan" kieu moi + nhan treo may tinh la lam duoc viec."""
import logging
import types

import pytest

import bot.steer
from bot import tplneed
from bot.modules import campaign


class V:
    def __init__(self, seen=(), have=None):
        self.seen = set(seen)
        self.have = set(have) if have is not None else None

    def has(self, name):
        return True if self.have is None else name in self.have

    def find(self, img, name, **k):
        return (300, 900, 0.95) if name in self.seen else None

    def best(self, img, name, **k):
        return None


class Ctx:
    def __init__(self, v):
        self.POPUP_CLOSERS = ["common/btn_x"]
        self.v, self.taps, self._img = v, [], "img"
        self.cfg = {"battle": {"steer": False}}
        self.dev = types.SimpleNamespace(idx=3)
        self.saved, self.backs = [], 0

    def shot(self):
        return "img"

    def find(self, name, fresh=True, **k):
        return self.v.find("img", name)

    def tap_tpl(self, name, **k):
        if self.v.find("img", name):
            self.taps.append(name)
            if name in (campaign.LEGION_FIGHT, "campaign/btn_fight"):
                self.v.seen = {"campaign/btn_done", "campaign/res_win"}   # tran xong -> man thang
            return True
        return False

    def tap_first(self, names, **k):
        for n in names:
            if self.v.find("img", n):
                self.taps.append(n)
                self.v.seen.discard(n)
                return n
        return None

    def wait_for(self, name, **k):
        return self.v.find("img", name)

    def back_out(self, n=4):
        self.backs += n

    def dismiss_reward(self):
        pass

    def save_debug(self, tag):
        self.saved.append(tag)


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(campaign.time, "sleep", lambda s: None)
    monkeypatch.setattr(bot.steer, "result_of", lambda v, img: "win", raising=False)


def test_legion_screen_pure():
    assert campaign.legion_screen(V({campaign.LEGION_FIGHT}), "img")
    assert not campaign.legion_screen(V(), "img")


def test_battle_on_legion_screen_recommend_then_fight_when_prechecked():
    c = Ctx(V({campaign.LEGION_FIGHT, campaign.LEGION_RECOMMEND}))
    assert campaign.battle(c, pre_checked=True) == "win"
    assert c.taps[:2] == [campaign.LEGION_RECOMMEND, campaign.LEGION_FIGHT]
    assert "campaign_no_fight" not in c.saved


def test_battle_on_legion_screen_without_prediction_does_not_fight():
    c = Ctx(V({campaign.LEGION_FIGHT, campaign.LEGION_RECOMMEND}))
    assert campaign.battle(c, only_win=True, pre_checked=False) == "skip"
    assert campaign.LEGION_FIGHT not in c.taps


def test_legion_missing_template_skips_fast(caplog):
    caplog.set_level(logging.INFO, logger="aow")
    tplneed._last.clear()
    c = Ctx(V(set(), have=set()))
    assert campaign.legion_fight(c) is False
    assert c.taps == []
    assert any("thieu anh mau play/btn_arena_fight" in r.getMessage() for r in caplog.records)


def test_claim_idle_counts_as_work():
    c = Ctx(V({"campaign/btn_idle_claim", "campaign/btn_idle_get"}))
    assert campaign.claim_idle(c) is True
    c2 = Ctx(V())
    assert campaign.claim_idle(c2) is False
