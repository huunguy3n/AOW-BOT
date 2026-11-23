"""P7-1 (chu du an 2026-11-24, live #1): gather CUOI luot moi ngay; thu 2 gui het quan doan; mo cap 1 'toobig'."""
import time
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


def test_fit_and_start_level_lift_poisoned_top():
    # live #1: gather_top:metal = 1 (ghi tu quan doan 8795) nhung quan doan lon (154397) cho het cap 2 (80000)
    assert GR.fit_level(CAPS, "metal", 154397, 1, 8) == 2
    assert GR.start_level(1, GR.fit_level(CAPS, "metal", 154397, 1, 8), 8) == 2
    assert GR.start_level(1, GR.fit_level(CAPS, "metal", 517590, 1, 8), 8) == 4
    assert GR.start_level(None, None, 8) == 8                 # chua biet gi -> do tu cap 8
    assert GR.start_level(6, 3, 8) == 6                       # tri nho cao hon -> giu
    assert GR.fit_level(CAPS, "metal", 8795, 1, 8) is None    # quan doan qua nho cho moi cap
    assert GR.fit_level(CAPS, "alloy", 15000, 1, 8) == 3      # cap 1-2 alloy khong co trong bang -> bo


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


def test_too_big_at_min_level_does_not_write_gather_top():
    c = SimpleNamespace(mem=Mem(), dev=SimpleNamespace(idx=1))
    gather.note_load(c, 8795)                           # cua so het han -> max = quan doan nho
    gather.remember_too_big(c, "metal", 1, 8795, 1)
    assert c.mem.fact(1, "gather_top:metal") is None    # truoc P7-1: ghi 1 -> chi thu cap 1 mai mai
    c.mem.f[(1, "march_load_max")] = [517590, time.time()]
    gather.remember_too_big(c, "metal", 8, 517590, 1)
    assert c.mem.fact(1, "gather_top:metal") == 7


def test_monday_gather_sends_all_no_rebel_reserve(monkeypatch):
    monkeypatch.setattr(WM, "gather_day", lambda cfg, now=None: True)
    ctx = SimpleNamespace(cfg={"rebels": {}, "modules": {"rebels": True}}, dev=SimpleNamespace(idx=0), mem=Mem())
    assert gather.rebels_reserve(ctx) == 0
