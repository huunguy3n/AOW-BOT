"""P2 muc 2 (PM 2026-11-23): construct_no_spot -> nho the hong, sang the/nhom khac, khong mo lai bang vo ich."""
import time
import types

from bot.modules import construct as c

H = 3600.0


def test_card_key_stable_against_small_dot_jitter():
    assert c.card_key((110, 330), 95) == c.card_key((113, 327), 95) == "120,320,95"
    assert c.card_key((110, 330), 95) != c.card_key((110, 330), 250)


def test_note_fail_backoff_doubles_and_caps():
    e = c.note_fail({}, "k", 0, hq=10)
    assert e["k"]["n"] == 1 and e["k"]["until"] == 2 * H
    e = c.note_fail(e, "k", 1, hq=10)
    assert e["k"]["n"] == 2 and e["k"]["until"] == 1 + 4 * H
    for t in range(2, 10):
        e = c.note_fail(e, "k", t, hq=10)
    assert e["k"]["until"] == 9 + 24 * H                       # tran 24 gio


def test_note_fail_blocked_is_short_and_expired_entries_dropped():
    e = c.note_fail({"old": {"until": 5, "n": 1}}, "k", 100, reason="blocked")
    assert "old" not in e and e["k"]["until"] == 100 + 1 * H


def test_skipped_until_expiry_or_hq_change():
    e = c.note_fail({}, "k", 0, hq=10)
    assert c.skipped(e, "k", 10, hq=10)
    assert not c.skipped(e, "k", 3 * H, hq=10)                 # het han
    assert not c.skipped(e, "k", 10, hq=11)                    # nha chinh len cap -> thu lai
    assert not c.skipped(e, "other", 10, hq=10)


def test_block_plan():
    e = c.note_fail({}, "a", 0, hq=5)
    e = c.note_fail(e, "b", 0, hq=5, reason="blocked")
    assert c.block_plan(True, 0, 2, e, 10, 5) == 1 * H         # the som nhat het han
    assert c.block_plan(False, 0, 2, e, 10, 5) is None         # chua xem het nhom -> khong chan
    assert c.block_plan(True, 1, 2, e, 10, 5) is None          # da xay duoc -> khong chan
    assert c.block_plan(True, 0, 0, {}, 10, 5, empty_h=1) == 10 + H   # khong co the mo nao
    assert c.block_plan(True, 0, 1, {}, 10, 5) is None         # the mo chua bi bo qua (khong nen xay ra)


class Mem:
    def __init__(self, facts):
        self.f = dict(facts)

    def fact(self, i, k, default=None):
        return self.f.get(k, default)

    def set_fact(self, i, k, v):
        self.f[k] = v


def ctx_with(facts):
    return types.SimpleNamespace(cfg={}, dev=types.SimpleNamespace(idx=4), mem=Mem(facts))


def test_run_returns_fast_while_blocked(monkeypatch):
    monkeypatch.setattr("bot.hqplan.yield_builder", lambda ctx, step: False)
    ctx = ctx_with({c.BLOCK_FACT: {"until": time.time() + 600, "hq": 7}, "hq_level": 7})
    ctx.ensure_city = lambda: (_ for _ in ()).throw(AssertionError("khong duoc mo thanh pho/bang"))
    seen = []
    monkeypatch.setattr(c, "roads", lambda ctx: seen.append("roads") or 0)   # P12-5: duong khong ton tho
    assert c.run(ctx) == 0 and seen == ["roads"]


def test_block_lifted_when_hq_levels_up():
    ctx = ctx_with({c.BLOCK_FACT: {"until": time.time() + 600, "hq": 7}, "hq_level": 8})
    assert c.block_until(ctx) is None
    ctx.mem.f["hq_level"] = 7
    assert c.block_until(ctx)
    ctx.mem.f[c.BLOCK_FACT] = time.time() + 60                 # dang cu (so) van doc duoc
    assert c.block_until(ctx)


def test_place_cancels_on_failure(monkeypatch):
    calls = []
    monkeypatch.setattr(c, "_place", lambda ctx, x, tries: "no_spot")
    monkeypatch.setattr(c, "cancel_place", lambda ctx: calls.append("cancel"))
    assert c.place(None, 95) == "no_spot" and calls == ["cancel"]
    monkeypatch.setattr(c, "_place", lambda ctx, x, tries: "ok")
    assert c.place(None, 95) == "ok" and calls == ["cancel"]
