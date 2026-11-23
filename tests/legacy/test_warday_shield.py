"""Chu du an 2026-11-23: Hiep uoc chi bam khi co chu 'Mien phi'; ngay chien tranh thu moi dong khien, mua khong gioi
han (src shield_war, ghi so); ngoai ngay chien tranh van tran gem_cap_daily; thu 2 gather len dau, khong giu quan."""
import types
from datetime import UTC, datetime

import pytest

from aowbot.domain import warday as W
from bot.modules import defense, gather
from bot.modules import warday as WM
from web import options, server

SAT = datetime(2026, 11, 28, tzinfo=UTC).timestamp()
MON = datetime(2026, 11, 23, 5, tzinfo=UTC).timestamp()


class V:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [(184, 191)]

    def has(self, name):
        return True

    def find(self, img, name, th=None, roi=None):
        return self.rows.pop(0) if name == "defense/row_8h" and self.rows else None


class Ctx:
    def __init__(self, labels, rows=None, cfg=None):
        self.v, self.labels, self.taps = V(rows), list(labels), []
        self.cfg = cfg or {}
        self.dev = types.SimpleNamespace(idx=1)

    def ensure_city(self):
        pass

    def tap_tpl(self, name, **kw):
        return True

    def wait_for(self, name, **kw):
        return True

    def shot(self):
        return "img"

    def tap(self, x, y, **kw):
        self.taps.append((x, y))

    def back_out(self):
        pass


@pytest.fixture
def label_ocr(monkeypatch):
    def use(ctx):
        monkeypatch.setattr(defense.ocr, "text", lambda img, roi, *a, **k: ctx.labels.pop(0) if ctx.labels else "")
    return use


def test_peace_taps_only_when_free(label_ocr):
    ctx = Ctx(["Mien phi", ""], rows=[(184, 191), (184, 191)])
    label_ocr(ctx)
    assert defense.peace(ctx) == "peace" and ctx.taps == [(469, 218)]


def test_peace_cooldown_never_taps(label_ocr):
    ctx = Ctx(["13:59:00"])
    label_ocr(ctx)
    assert defense.peace(ctx) == "cooldown" and ctx.taps == []


def test_peace_unverified_is_error(label_ocr):
    ctx = Ctx(["Mien phi", "Mien phi"], rows=[(184, 191), (184, 191)])
    label_ocr(ctx)
    assert defense.peace(ctx) == "error"


def test_shield_hours_8_goes_to_peace(monkeypatch):
    monkeypatch.setattr(defense, "peace", lambda ctx: "peace")
    assert defense.shield(Ctx([]), hours=8) == "peace"


def test_war_shield_tries_options_in_order(monkeypatch):
    calls = []

    def fake(ctx, hours=None, allow_buy=None, extend=False, cap="cfg", src="shield"):
        calls.append((hours, allow_buy, cap, src))
        return "shielded" if (hours, allow_buy) == (1, True) else "no_item"
    monkeypatch.setattr(defense, "shield", fake)
    assert defense.war_shield(Ctx([]), 3 * 3600, buy=True, cap=None) == 1
    war = [(12, False, None, "shield_war"), (72, False, None, "shield_war"), (1, False, None, "shield_war")]
    assert calls[:3] == war
    assert calls[-1] == (1, True, None, "shield_war")


def test_war_shield_no_buy_when_disabled(monkeypatch):
    calls = []
    monkeypatch.setattr(defense, "shield", lambda ctx, **kw: calls.append(kw["allow_buy"]) or "no_item")
    assert defense.war_shield(Ctx([]), 3600, buy=False) == 0
    assert not any(calls)


def test_attack_in_war_window_uses_unlimited(monkeypatch):
    got = {}
    monkeypatch.setattr(defense, "under_attack", lambda ctx: True)
    monkeypatch.setattr(defense, "war_shield",
                        lambda ctx, need, buy, cap: got.update(need=need, buy=buy, cap=cap) or 12)
    monkeypatch.setattr(defense.time, "time", lambda: SAT + 3600)
    ctx = Ctx([], cfg={"defense": {"shield_on_attack": True, "gem_cap_daily": 2000}})
    assert defense.run(ctx) == "shielded"
    assert got["cap"] is None and got["buy"] is True and got["need"] > 20 * 3600


def test_attack_outside_war_keeps_daily_cap(monkeypatch):
    got = {}
    monkeypatch.setattr(defense, "under_attack", lambda ctx: True)
    monkeypatch.setattr(defense, "shield", lambda ctx, force=False, **kw: got.update(kw) or "shielded")
    monkeypatch.setattr(defense.time, "time", lambda: SAT - 3 * 86400)
    ctx = Ctx([], cfg={"defense": {"shield_on_attack": True}, "warday": {}})
    assert defense.run(ctx) == "shielded" and got == {}          # duong thuong: cap = defense.gem_cap_daily


def test_known_until():
    assert WM.known_until("off", None, 9999, 100) is None           # man hinh bao chua bao ho -> bat lai
    assert WM.known_until("on", 50, None, 100) == 150
    assert WM.known_until("on", None, 400, 100) == 400
    assert WM.known_until(None, None, 50, 100) is None


class Mem:
    def __init__(self, **f):
        self.f = dict(f)

    def fact(self, idx, key, default=None):
        return self.f.get(key, default)

    def set_fact(self, idx, key, value):
        self.f[key] = value


def test_ensure_records_shield(monkeypatch):
    mem = Mem(peace_at=SAT - 20 * 3600)
    ctx = Ctx([], cfg={})
    ctx.mem = mem
    monkeypatch.setattr(WM, "screen_shield", lambda ctx: ("off", None))
    monkeypatch.setattr(defense, "war_shield", lambda ctx, need, buy, cap: 12)
    assert WM.ensure(ctx, W.wcfg(None), [SAT], SAT + 3600) == 1
    assert mem.f["war_shield_until"] > SAT + 12 * 3600


def test_ensure_peace_before_war(monkeypatch):
    mem = Mem()
    ctx = Ctx([], cfg={})
    ctx.mem = mem
    monkeypatch.setattr(WM, "screen_shield", lambda ctx: ("off", None))
    monkeypatch.setattr(defense, "peace", lambda ctx: "peace")
    assert WM.ensure(ctx, W.wcfg(None), [SAT], SAT - 2 * 3600 + 60) == 1
    assert mem.f["peace_at"] == SAT - 2 * 3600 + 60


def test_gather_first_and_monday_reserve(monkeypatch):
    assert W.gather_first(["warday", "tutorial", "notify", "play", "gather", "train"]) == \
        ["warday", "tutorial", "gather", "notify", "play", "train"]
    assert W.gather_first(["notify"]) == ["notify"]
    monkeypatch.setattr(WM.time, "time", lambda: MON)
    assert WM.gather_day({})
    ctx = types.SimpleNamespace(cfg={"rebels": {}, "modules": {"rebels": True}}, dev=types.SimpleNamespace(idx=0),
                                mem=Mem())
    monkeypatch.setattr(gather, "_mem", lambda c: c.mem)
    assert gather.rebels_reserve(ctx) == 0 and ctx.mem.f["rebels_reserve"] == 0


def test_web_week_info_and_switch_option():
    assert server.week_info(Mem(), 0, {"warday": {}}, SAT + 3600) == "war"
    assert server.week_info(Mem(), 0, {"warday": {"mode": "off"}}, SAT + 3600) is None
    assert server.week_info(Mem(), 0, {"warday": {}}, MON) == "gather"
    keys = {o["key"] for _, items in options.GROUPS for o in items}
    assert {"warday.mode", "warday.reset_hour_utc", "warday.buy_gems", "warday.peace"} <= keys
