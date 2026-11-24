"""P10-6 (live-run-3): khong co dong log nao ve Diem Danh 30 Ngay / Qua dang nhap (TT phuc loi chi mo khi icon
co cham do). Moi luot deu kiem + log; da nhan hom nay (reset 0h UTC) -> log 'da nhan'; chua kiem -> mo 1 lan."""
import logging
import types

from bot.modules import notify


def test_plan():
    assert notify.welfare_plan("2026-11-24", None, None, 3)[0] == "claimed"
    assert notify.welfare_plan("2026-11-24", "2026-11-24", None, 0)[0] == "done"
    assert notify.welfare_plan("2026-11-24", None, "2026-11-24", 0)[0] == "done"
    assert notify.welfare_plan("2026-11-24", "2026-11-23", "2026-11-23", 0)[0] == "verify"   # ngay moi -> kiem lai


def test_utc_day_reset_at_0h_utc():
    assert notify.utc_day(1795478400) == "2026-11-24"          # 2026-11-24 00:00 UTC
    assert notify.utc_day(1795478400 - 1) == "2026-11-23"


class Mem:
    def __init__(self, d=None):
        self.d = dict(d or {})

    def fact(self, idx, k, default=None):
        return self.d.get(k, default)

    def set_fact(self, idx, k, v):
        self.d[k] = v


def _ctx(mem, taps):
    return types.SimpleNamespace(mem=mem, dev=types.SimpleNamespace(idx=1), ensure_city=lambda: None,
                                 shot=lambda: None, v=types.SimpleNamespace(find=lambda img, n, **k: (40, 200, 0.9)),
                                 tap=lambda x, y, wait=1.0: taps.append((x, y)))


def test_already_claimed_logs_and_skips(caplog):
    taps = []
    caplog.set_level(logging.INFO, logger="aow")
    ctx = _ctx(Mem({"welfare_claim_day": notify.utc_day()}), taps)
    assert notify.welfare_daily(ctx, {}) == 0
    assert taps == [] and "da nhan hom nay" in caplog.text


def test_verify_opens_once_per_day(monkeypatch, caplog):
    taps = []
    caplog.set_level(logging.INFO, logger="aow")
    monkeypatch.setattr(notify, "claim_glow_tiles", lambda ctx: 1)
    monkeypatch.setattr(notify, "hub", lambda ctx, cards: 0)
    mem = Mem()
    assert notify.welfare_daily(_ctx(mem, taps), {}) == 1
    assert taps == [(40, 200)] and mem.d["welfare_claim_day"] == notify.utc_day()
    taps.clear()
    assert notify.welfare_daily(_ctx(mem, taps), {}) == 0      # lan 2 cung ngay -> khong mo lai
    assert taps == []


def test_claimed_this_visit_recorded():
    mem = Mem()
    assert notify.welfare_daily(_ctx(mem, []), {"welfare": 2}) == 0
    assert mem.d["welfare_claim_day"] == notify.utc_day()


def test_run_always_calls_daily_check(monkeypatch):
    called = []
    monkeypatch.setattr(notify, "badged", lambda ctx: [])
    monkeypatch.setattr(notify, "welfare_daily", lambda ctx, done: called.append(1) or 0)
    monkeypatch.setattr(notify, "events", lambda ctx: 0)
    monkeypatch.setattr(notify, "leave", lambda ctx: None)
    ctx = types.SimpleNamespace(cfg={"notify": {}}, ensure_city=lambda: None)
    notify.run(ctx)
    assert called == [1]


def test_free_column_only():
    assert notify.free_column_tiles([(140, 630), (380, 630)], 480) == [(140, 630)]   # khong cot Su thi
