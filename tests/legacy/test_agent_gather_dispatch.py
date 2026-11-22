"""Hoi quy: agent dispatch_gather -> gather.run(limit=1) tung loi
"'tuple' object has no attribute 'fact'" (#1, 21-22/11): bien tri nho `m` bi ghi de boi read_marches() (tuple x/y).
Kiem: bo nho (ctx.mem) va x/y (tuple) khong lan nhau."""
from types import SimpleNamespace

from aowbot.application.execute import Status
from aowbot.domain.actions import ActionName
from aowbot.infrastructure.legacy.actions import LegacyActionRunner
from bot.modules import gather


class Mem:
    def __init__(self):
        self.f = {}

    def fact(self, idx, key, default=None):
        return self.f.get((idx, key), default)

    def set_fact(self, idx, key, value):
        self.f[(idx, key)] = value

    def query(self, sql, args=()):
        return []


class Store:
    def __init__(self, data):
        self.data = data

    def inst(self, idx):
        return self.data


class Ctx:
    def __init__(self, marches):
        self.cfg = {"gather": {"max_level": 8, "min_level": 1, "priority": ["alloy", "metal"], "min_hq_level": 9,
                               "load_ge_mine": True},
                    "rebels": {"reserve_legion": False}, "modules": {"rebels": False}}
        self.mem = Mem()
        self.mem.set_fact(1, "hq_level", 30)
        self.mem.set_fact(1, "gather_fix_v2", True)
        self.mem.set_fact(1, "gather_sig", [30, 0])              # chu ky khong doi -> sync_memory giu tri nho
        self.mem.set_fact(1, "gather_locked:alloy", True)     # loai bi khoa -> nhanh `mem.fact(...gather_locked...)`
        self.store = Store({"hq_level": 30, "march_total": 5})
        self.dev = SimpleNamespace(idx=1)
        self._marches = list(marches)
        self.calls = []

    def ensure_world(self):
        return True

    def ensure_city(self):
        return True

    def read_marches(self):
        return self._marches.pop(0) if self._marches else None


def test_gather_run_tuple_marches_and_memory(monkeypatch):
    c = Ctx([(3, 5), (4, 5)])
    tried = []

    def fake_try(ctx, rtype, lv, max_lv):
        tried.append((rtype, lv))
        return gather.OK

    monkeypatch.setattr(gather, "try_dispatch", fake_try)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.run(c, limit=1) == 1
    assert tried == [("metal", 8)]                             # alloy bi khoa (doc tu mem), khong loi tuple


def test_agent_dispatch_verifies_one_more_march(monkeypatch):
    c = Ctx([(3, 5), (3, 5), (4, 5)])                          # truoc (runner) -> trong gather.run -> sau (runner)
    monkeypatch.setattr(gather, "try_dispatch", lambda *a: gather.OK)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    r = LegacyActionRunner(c).run(ActionName.DISPATCH_GATHER)
    assert r.status is Status.OK, r.detail


def test_agent_dispatch_hidden_counter_uses_known_total(monkeypatch):
    c = Ctx([None, None, (1, 5)])                              # khung x/y an = 0 doi dang di
    monkeypatch.setattr(gather, "try_dispatch", lambda *a: gather.OK)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    r = LegacyActionRunner(c).run(ActionName.DISPATCH_GATHER)
    assert r.status is Status.OK, r.detail
