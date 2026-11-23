from types import SimpleNamespace

from bot.modules import gather, warday


class Mem:
    def __init__(self, done=0):
        self.f = {}
        self.done = done

    def fact(self, idx, key, default=None):
        return self.f.get((idx, key), default)

    def set_fact(self, idx, key, value):
        self.f[(idx, key)] = value

    def query(self, sql, args=()):
        if "FROM runs" in sql:
            return [(str(self.done),)] if self.done else []
        return []


def ctx(hq=30, done=0, cfg=None):
    c = {"rebels": {"min_hq_level": 15, "daily_target": 5}, "modules": {"rebels": True}, "schedule": {}}
    c.update(cfg or {})
    m = Mem(done)
    m.set_fact(1, "hq_level", hq)
    return SimpleNamespace(cfg=c, mem=m, dev=SimpleNamespace(idx=1))


def test_reserve_when_rebels_due(monkeypatch):
    monkeypatch.setattr(warday, "gather_day", lambda cfg, now=None: False)   # khong phu thuoc hom nay co la thu 2
    c = ctx()
    assert gather.rebels_reserve(c) == 1 and c.mem.fact(1, "rebels_reserve") == 1


def test_no_reserve_when_low_hq_done_or_disabled():
    assert gather.rebels_reserve(ctx(hq=7)) == 0                       # nha chinh < 15
    assert gather.rebels_reserve(ctx(done=5)) == 0                     # du 5 luot hom nay
    assert gather.rebels_reserve(ctx(cfg={"rebels": {"reserve_legion": False}})) == 0
    assert gather.rebels_reserve(ctx(cfg={"modules": {"rebels": False}})) == 0
