"""A-OPT-1 (PM 2026-11-23): reddots gioi han tan suat / thoi gian, nho icon vo ich lau dan."""
import time
from types import SimpleNamespace

from bot.modules import reddots

NOW = 1_800_000_000.0


class Mem:
    def __init__(self):
        self.f = {}

    def fact(self, idx, key, default=None):
        v = self.f.get((idx, key))
        return default if v is None else v

    def set_fact(self, idx, key, value):
        self.f[(idx, key)] = value

    def query(self, sql, args=()):
        return []


def test_due_rules():
    assert reddots.due(None, NOW, 30, False, [])[0]                          # chua quet bao gio
    assert reddots.due(NOW - 31 * 60, NOW, 30, False, [])[0]                 # qua 30 phut
    assert not reddots.due(NOW - 10 * 60, NOW, 30, False, [])[0]             # vua quet, khong co gi moi
    assert reddots.due(NOW - 10 * 60, NOW, 30, True, [])[0]                  # notify vua nhan duoc qua
    assert reddots.due(NOW - 10 * 60, NOW, 30, False, [(500, 300)])[0]       # cham do moi


def test_dead_until_doubles_and_caps():
    assert reddots.dead_until(1, NOW, 2, 24) == NOW + 2 * 3600
    assert reddots.dead_until(2, NOW, 2, 24) == NOW + 4 * 3600
    assert reddots.dead_until(9, NOW, 2, 24) == NOW + 24 * 3600


def test_remember_escalates_useless_and_resets_worked():
    m = Mem()
    rc = reddots.rcfg({})
    dead_n = {"5,5": 2, "7,7": 3}
    keep = reddots.remember(m, 0, rc, {}, dead_n, {(5, 5), (6, 6), (7, 7)}, {(5, 5)}, {(7, 7)}, NOW)
    assert keep["5,5"] == NOW + 8 * 3600              # lan vo ich thu 3 -> 2 x 2^2
    assert keep["6,6"] == NOW + 2 * 3600              # dead vi da xu ly du lan (khong phai vo ich)
    assert m.fact(0, "reddots_dead_n") == {"5,5": 3}  # (7,7) vua lam duoc viec -> xoa dem
    assert m.fact(0, "reddots_last_at") == NOW


class Ctx:
    def __init__(self, mem, done=None):
        self.cfg = {"reddots": {"min_interval_min": 30}}
        self.mem, self.dev, self.v = mem, SimpleNamespace(idx=0), None
        self.visit_done = done or {}
        self.shots = 0

    def ensure_city(self):
        return True

    def shot(self):
        self.shots += 1
        return "img"


def test_run_skips_when_recent_and_nothing_new(monkeypatch):
    m = Mem()
    m.set_fact(0, "reddots_last_at", time.time() - 300)
    m.set_fact(0, "reddots_seen", ["12,7"])
    monkeypatch.setattr(reddots, "_left", lambda img, v=None: [(500, 300)])    # _key -> (12, 7): da thay lan truoc
    monkeypatch.setattr(reddots.chat, "clear", lambda ctx: (_ for _ in ()).throw(AssertionError("khong duoc quet")))
    c = Ctx(m)
    assert reddots.run(c) == 0
    assert c.shots == 1                               # chi 1 anh de so cham do moi
