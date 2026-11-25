"""P13b (chu du an t77u/t78u): mo lien minh chi gui SOM khi >= 2 quan doan ranh; con 1 -> hoan cuoi luot cung gather."""
import time
from types import SimpleNamespace

import pytest
import yaml

from bot.ctx import Ctx
from bot.modules import alliance, gather


@pytest.fixture(autouse=True)
def _hq12(monkeypatch):
    monkeypatch.setattr(alliance, "_hq", lambda ctx: 12)


def test_mine_decision():
    assert alliance.mine_decision(3) == "early"
    assert alliance.mine_decision(2) == "early"
    assert alliance.mine_decision(1) == "defer"
    assert alliance.mine_decision(0) == "full"


class FakeCtx:
    """Chi du phan ally_mine dung."""

    def __init__(self, free, full=False):
        self.free, self.full = free, full
        self.ally_mine = None
        self.sent = 0
        self.cfg = {"alliance": {"mine": True}, "quests": {"alliance": True}}

    def march_full(self):
        return self.full

    def march_free(self):
        return self.free

    def tap_tpl(self, name, **kw):
        return True

    def wait_for(self, name, **kw):
        return (1, 1)

    def find(self, name, **kw):
        return None

    def march_sent(self):
        self.sent += 1

    def save_debug(self, *a):
        pass

    def ensure_city(self):
        pass


def test_free_two_sends_early():
    c = FakeCtx(2)
    assert alliance.ally_mine(c) == 1
    assert c.sent == 1 and c.ally_mine == "sent"


def test_free_one_defers_not_sent():
    c = FakeCtx(1)
    assert alliance.ally_mine(c) == 0
    assert c.sent == 0 and c.ally_mine == "deferred"


def test_free_zero_or_full_does_nothing():
    c = FakeCtx(0)
    assert alliance.ally_mine(c) == 0 and c.sent == 0 and c.ally_mine is None
    c = FakeCtx(3, full=True)
    assert alliance.ally_mine(c) == 0 and c.sent == 0 and c.ally_mine is None


def test_sent_early_not_resent_at_end():
    c = FakeCtx(3)
    alliance.ally_mine(c)
    assert alliance.ally_mine_end(c) == 0
    assert c.sent == 1


def test_deferred_then_end_sends(monkeypatch):
    monkeypatch.setattr(alliance, "open_alliance", lambda ctx: True)
    monkeypatch.setattr(alliance, "main_tab", lambda ctx: True)
    c = FakeCtx(1)
    alliance.ally_mine(c)
    c.free = 1                                  # cuoi luot van con 1 doi ranh
    assert alliance.ally_mine_end(c) == 1
    assert c.sent == 1
    assert alliance.ally_mine_end(c) == 0       # khong gui lan 2
    assert c.sent == 1


def test_deferred_but_full_at_end_skips(monkeypatch):
    monkeypatch.setattr(alliance, "open_alliance", lambda ctx: True)
    monkeypatch.setattr(alliance, "main_tab", lambda ctx: True)
    c = FakeCtx(1)
    alliance.ally_mine(c)
    c.full = True                               # tinh bao / phan quan da dung quan doan
    assert alliance.ally_mine_end(c) == 0
    assert c.sent == 0


def test_end_without_deferral_noop():
    c = FakeCtx(1)
    assert alliance.ally_mine_end(c) == 0 and c.sent == 0


def _bare_ctx(read, march=None, state=None):
    c = Ctx.__new__(Ctx)
    c.read_marches = lambda: read
    c._march = march
    c.dev = SimpleNamespace(idx=0)
    c.store = SimpleNamespace(inst=lambda i: state or {})
    return c


def test_march_free_counts_from_reading():
    assert _bare_ctx((1, 5)).march_free() == 4
    assert _bare_ctx((4, 5)).march_free() == 1
    assert _bare_ctx((5, 5)).march_free() == 0
    assert _bare_ctx((1, 1)).march_free() == 0


def test_march_free_cache_and_state():
    assert _bare_ctx(None, march=(3, 5, time.time())).march_free() == 2
    st = {"march_used": 2, "march_total": 5, "resources_at": time.time()}
    assert _bare_ctx(None, state=st).march_free() == 3


def test_march_free_unreadable_is_one():
    assert _bare_ctx(None).march_free() == 1
    old = {"march_used": 0, "march_total": 5, "resources_at": time.time() - 5000}
    assert _bare_ctx(None, march=(0, 5, time.time() - 5000), state=old).march_free() == 1


def test_gather_run_calls_end(monkeypatch):
    called = []
    monkeypatch.setattr(alliance, "ally_mine_end", lambda ctx: called.append(1))
    ctx = SimpleNamespace(cfg={"gather": {"max_level": 8, "min_level": 1, "min_hq_level": 9, "load_ge_mine": True}})
    monkeypatch.setattr(gather, "hq_level", lambda c: 3)       # HQ thap -> gather thoat sau khi goi mo lien minh
    assert gather.run(ctx) == 0
    assert called == [1]
    gather.run(ctx, limit=1)                                    # agent (limit) khong goi
    assert called == [1]


def _open(monkeypatch):
    monkeypatch.setattr(alliance, "open_alliance", lambda ctx: True)
    monkeypatch.setattr(alliance, "main_tab", lambda ctx: True)


@pytest.mark.parametrize("hq", [5, 11, None])
def test_low_or_unknown_hq_never_sends(monkeypatch, hq):
    _open(monkeypatch)
    monkeypatch.setattr(alliance, "_hq", lambda ctx: hq)
    c = FakeCtx(3)
    assert alliance.ally_mine(c) == 0 and c.sent == 0 and c.ally_mine is None
    c = FakeCtx(1)
    c.ally_mine = "deferred"                        # cuoi luot cung bi chan
    assert alliance.ally_mine_end(c) == 0 and c.sent == 0
    c = FakeCtx(1)
    assert alliance.ally_mine(c, late=True) == 0 and c.sent == 0


@pytest.mark.parametrize("hq", [12, 13])
def test_hq_12_plus_free_two_sends_early(monkeypatch, hq):
    monkeypatch.setattr(alliance, "_hq", lambda ctx: hq)
    c = FakeCtx(2)
    assert alliance.ally_mine(c) == 1 and c.sent == 1


def test_hq_12_free_one_defers_then_end_sends(monkeypatch):
    _open(monkeypatch)
    c = FakeCtx(1)
    assert alliance.ally_mine(c) == 0 and c.ally_mine == "deferred"
    assert alliance.ally_mine_end(c) == 1 and c.sent == 1


def test_min_hq_from_config(monkeypatch):
    monkeypatch.setattr(alliance, "_hq", lambda ctx: 14)
    c = FakeCtx(3)
    c.cfg["alliance"]["mine_min_hq"] = 15
    assert alliance.ally_mine(c) == 0 and c.sent == 0
    c.cfg["alliance"]["mine_min_hq"] = 14
    assert alliance.ally_mine(c) == 1
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["alliance"]["mine_min_hq"] == 12
