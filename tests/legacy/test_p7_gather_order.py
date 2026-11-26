"""P7-1 (chu du an 2026-11-24, live #1): gather CUOI luot moi ngay; thu 2 gui het quan doan; mo cap 1 'toobig'.
P13g: tri nho gather_top (bat dau thap hon cap 8) da bo - xem tests/legacy/test_p13g_gather_same_mine.py."""
from types import SimpleNamespace

from aowbot.domain import drain
from aowbot.domain import warday as W
from bot import gather_rules as GR
from bot import runner
from bot.modules import gather
from bot.modules import warday as WM

CAPS = {"metal": [40000, 80000, 160000, 320000, 560000, 800000, 1040000, 1320000],
        "alloy": [None, None, 10000, 20000, 35000, 50000, 62500, 82500]}


def test_order_gather_is_last_and_world_steps_before_it():
    names = [n for n, _ in runner.ORDER]
    assert names[-1] == "gather"
    for step in ("intel", "rebels", "play", "alliance", "campaign"):    # can quan doan -> chay truoc
        assert names.index(step) < names.index("gather")
    assert runner.DRAIN_AT[0] == "gather"                                 # xa viec chay lai truoc gather


def test_gather_last_keeps_observe_after_and_other_order():
    q = ["warday", "gather", "notify", "intel", "observe"]
    assert W.gather_last(q) == ["warday", "notify", "intel", "gather", "observe"]
    assert W.gather_last(["gather", "notify"]) == ["notify", "gather"]
    assert not hasattr(W, "gather_first")             # quyet dinh P6 'thu 2 gather len dau' da bo


def test_drain_prioritize_then_gather_last_still_last():
    names = [n for n, _ in runner.ORDER]
    pr = drain.prioritize(names, ["build", "train"], dict.fromkeys(names, True))
    assert W.gather_last([*pr, "observe"])[-2:] == ["gather", "observe"]


def test_too_big_levels_skips_remaining_levels_by_table():
    assert GR.too_big_levels(CAPS, "metal", 100000, 5, 1) == [4, 3]
    assert GR.too_big_levels(CAPS, "metal", 8795, 2, 1) == [1]
    assert GR.too_big_levels(CAPS, "metal", None, 5, 1) == []


class Mem:
    def __init__(self, facts=None):
        self.f = dict(facts or {})

    def fact(self, idx, key, default=None):
        return self.f.get((idx, key), default)

    def set_fact(self, idx, key, value):
        self.f[(idx, key)] = value


def test_monday_gather_sends_all_no_rebel_reserve(monkeypatch):
    monkeypatch.setattr(WM, "gather_day", lambda cfg, now=None: True)
    ctx = SimpleNamespace(cfg={"rebels": {}, "modules": {"rebels": True}}, dev=SimpleNamespace(idx=0), mem=Mem())
    assert gather.rebels_reserve(ctx) == 0
