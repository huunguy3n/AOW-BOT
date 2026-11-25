"""P9-2 (chu du an 2026-11-24, live-run-2): khien som ngay thuong + thu tu buoc (khien, lien minh truoc cham do /
tinh bao; gather cuoi); ngan sach reddots."""
import types

from aowbot.domain import drain
from aowbot.domain import warday as W
from aowbot.domain.policy import ShieldInputs, shield_decision
from bot import runner
from bot.modules import defense, reddots, shield, warday
from web import options


def names():
    return [n for n, _ in runner.ORDER]


def test_order_shield_and_alliance_before_notify_reddots_intel():
    o = names()
    assert o.index("shield") < o.index("notify") and o.index("alliance") < o.index("notify")
    assert o.index("alliance") < o.index("reddots") < o.index("notify")  # P13-3
    assert o.index("alliance") < o.index("intel")
    assert o.index("shield") < o.index("alliance")
    assert o[:2] == ["warday", "tutorial"]
    assert W.early_ok(o)
    assert not W.early_ok(["notify", "shield", "alliance"])


def test_gather_still_last_including_monday():
    o = names()
    assert o[-1] == "gather"
    assert W.gather_last([*o, "observe"])[-2:] == ["gather", "observe"]


def test_idle_first_keeps_shield_at_head():
    out = drain.prioritize(names(), ["build"], dict.fromkeys(names(), True))
    assert out[:3] == ["warday", "tutorial", "shield"]
    assert W.early_ok(out) or out.index("alliance") < out.index("notify")


def test_web_modules_same_order_as_runner():
    web = [k for k, _ in options.MODULES]
    assert [n for n in names() if n in web] == web[:len([n for n in names() if n in web])] or \
        [n for n in web if n in names()] == [n for n in names() if n in web]


def test_daily_shield_options_peace_first_then_items_then_gems():
    opts = W.daily_shield_options(True)
    assert opts[0] == (8, False)                                    # Hiep uoc hoa binh mien phi
    items = [h for h, b in opts[1:] if not b]
    bought = [h for h, b in opts if b]
    assert items and all(not b for _, b in opts[1:1 + len(items)])  # vat pham truoc mua
    assert bought and opts.index((bought[0], True)) > opts.index((items[-1], False))
    assert 72 not in bought                                         # khong bao gio mua 3 ngay
    assert all(not b for _, b in W.daily_shield_options(False))


def test_gem_buy_respects_daily_cap_2000():
    # 1h = 500 kim cuong: da tieu 1600 -> mua nua vuot 2000 -> khong mua
    assert shield_decision(ShieldInputs(0, 5000, 500, 1600, 2000, True))[0] == "cap"
    assert shield_decision(ShieldInputs(0, 5000, 500, 1500, 2000, True))[0] == "buy"
    assert shield_decision(ShieldInputs(0, 5000, 4800, 0, 2000, True))[0] == "cap"   # 12h 4800 > tran
    assert defense.counts_toward_cap(shield.SRC)


def test_plan():
    assert shield.plan("off", False, None, 1000, 60) == (True, "khien dang tat")
    assert not shield.plan("on", False, None, 1000, 60)[0]
    assert not shield.plan("off", True, None, 1000, 60)[0]           # thu 7: warday lo
    assert shield.plan("off", False, 1000 - 600, 1000, 60)[0]        # P12-1: Hiep uoc chuan bi != khien -> van bat
    assert shield.plan("off", False, 1000 - 4000, 1000, 60)[0]
    assert not shield.plan(None, False, None, 1000, 60)[0]


class Mem:
    def __init__(self):
        self.f = {}

    def fact(self, i, k):
        return self.f.get(k)

    def set_fact(self, i, k, v):
        self.f[k] = v


def _ctx(monkeypatch, state="off", war=None, peace="cooldown", shields=None):
    calls = []
    monkeypatch.setattr(warday, "window", lambda *a, **k: war)
    monkeypatch.setattr(warday, "screen_shield", lambda ctx: (state, None))
    monkeypatch.setattr(defense, "peace",
                        lambda ctx, skip_if_active=False: calls.append(("peace", skip_if_active)) or peace)
    res = dict(shields or {})

    def sh(ctx, hours=None, allow_buy=None, src=None, **k):
        calls.append(("shield", hours, allow_buy, src))
        return res.get((hours, allow_buy), "no_item")
    monkeypatch.setattr(defense, "shield", sh)
    ctx = types.SimpleNamespace(cfg={"defense": {"gem_cap_daily": 2000}}, mem=Mem(), dev=types.SimpleNamespace(idx=1),
                                ensure_city=lambda: None)
    return ctx, calls


def test_run_uses_free_peace_first(monkeypatch):
    ctx, calls = _ctx(monkeypatch, peace="peace")
    seq = [("off", None), ("on", 8 * 3600)]     # P12-1: Hiep uoc chi tinh xong khi khien DANG BAT
    monkeypatch.setattr(warday, "screen_shield", lambda ctx: seq.pop(0))
    assert shield.run(ctx) == 1
    assert calls == [("peace", True)]
    assert ctx.mem.f["peace_at"]


def test_run_falls_back_items_then_gems_daily_src(monkeypatch):
    ctx, calls = _ctx(monkeypatch, peace="cooldown", shields={(1, True): "shielded"})
    assert shield.run(ctx) == 1
    kinds = [c for c in calls if c[0] == "shield"]
    first_buy = next(i for i, c in enumerate(kinds) if c[2])
    assert all(not c[2] for c in kinds[:first_buy]) and first_buy >= 1   # vat pham thu truoc
    assert kinds[first_buy][1] == 1 and kinds[first_buy][3] == shield.SRC


def test_run_no_buy_when_disabled(monkeypatch):
    ctx, calls = _ctx(monkeypatch)
    ctx.cfg["shield"] = {"buy_gems": False}
    assert shield.run(ctx) == 0
    assert not any(c[0] == "shield" and c[2] for c in calls)


def test_run_skips_on_war_day_and_when_shield_on(monkeypatch):
    ctx, calls = _ctx(monkeypatch, war=object())
    assert shield.run(ctx) == 0 and calls == []
    ctx, calls = _ctx(monkeypatch, state="on")
    assert shield.run(ctx) == 0 and calls == []


def test_run_stops_when_panel_says_active(monkeypatch):
    ctx, calls = _ctx(monkeypatch, peace="active")
    assert shield.run(ctx) == 0 and calls == [("peace", True)]


def test_reddots_budget_raised():
    assert reddots.rcfg({})["max_s"] >= 180
