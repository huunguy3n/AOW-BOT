"""P10-7 (live-run-3): khien tat luc dau luot -> bat 1h bang vat pham; cuoi luot 'CO con 0h35' -> se tat truoc lan ghe
sau. Dau + cuoi luot: tat hoac con < 1h -> gia han (Hiep uoc mien phi neu khong ho > vat pham > kim cuong trong tran
2000/ngay); con >= 1h -> khong bat chong; thu 7 warday lo."""
import inspect
import types

from aowbot.domain.policy import ShieldInputs, shield_decision
from bot import runner
from bot.modules import defense, shield, warday


def test_plan_renew_thresholds():
    assert shield.plan("on", False, None, 10_000, 60, left=35 * 60)[0]               # con 0h35 -> gia han
    assert not shield.plan("on", False, None, 10_000, 60, left=2 * 3600)[0]          # con 2h -> khong
    assert not shield.plan("on", False, None, 10_000, 60, left=3600)[0]              # dung 1h -> khong chong
    assert not shield.plan("on", False, None, 10_000, 60, left=None)[0]              # khong doc duoc gio
    assert not shield.plan("on", True, None, 10_000, 60, left=60)[0]                 # thu 7: warday
    assert shield.plan("off", False, None, 10_000, 60)[0]


def test_peace_only_if_no_gap():
    assert not shield.peace_ok_for_renew(35 * 60, 60)
    assert shield.peace_ok_for_renew(70 * 60, 60)
    assert not shield.peace_ok_for_renew(None, 60)


class Mem:
    def __init__(self):
        self.f = {}

    def fact(self, i, k):
        return self.f.get(k)

    def set_fact(self, i, k, v):
        self.f[k] = v


def _ctx(monkeypatch, state, left, results, war=None):
    calls = []
    monkeypatch.setattr(warday, "window", lambda *a, **k: war)
    monkeypatch.setattr(warday, "screen_shield", lambda ctx: (state, left))
    monkeypatch.setattr(defense, "peace", lambda ctx, skip_if_active=False: calls.append(("peace",)) or "peace")

    def sh(ctx, hours=None, allow_buy=None, src=None, extend=False, **k):
        calls.append(("shield", hours, allow_buy, src, extend))
        return results.get((hours, allow_buy), "no_item")
    monkeypatch.setattr(defense, "shield", sh)
    ctx = types.SimpleNamespace(cfg={"defense": {"gem_cap_daily": 2000}}, mem=Mem(), dev=types.SimpleNamespace(idx=1),
                                ensure_city=lambda: None)
    return ctx, calls


def test_renew_035_skips_peace_uses_item_extend(monkeypatch):
    ctx, calls = _ctx(monkeypatch, "on", 35 * 60, {(1, False): "shielded"})
    assert shield.run(ctx) == 1
    assert ("peace",) not in calls                               # Hiep uoc chuan bi 1h > 35 phut -> ho
    sh = [c for c in calls if c[0] == "shield"]
    assert all(c[4] for c in sh) and all(c[3] == shield.SRC for c in sh)   # extend, nguon tran ngay thuong
    first_buy = next((i for i, c in enumerate(sh) if c[2]), len(sh))
    assert sh[-1][1] == 1 and not sh[-1][2] and first_buy == len(sh)      # vat pham, chua mua


def test_renew_gems_only_after_items_within_cap_src(monkeypatch):
    ctx, calls = _ctx(monkeypatch, "on", 20 * 60, {(1, True): "shielded"})
    assert shield.run(ctx) == 1
    sh = [c for c in calls if c[0] == "shield"]
    first_buy = next(i for i, c in enumerate(sh) if c[2])
    assert first_buy >= 1 and sh[first_buy][3] == shield.SRC     # kim cuong sau vat pham, ghi gem_ev trong tran


def test_no_renew_with_2h(monkeypatch):
    ctx, calls = _ctx(monkeypatch, "on", 2 * 3600, {})
    assert shield.run(ctx) == 0 and calls == []


def test_war_day_untouched(monkeypatch):
    ctx, calls = _ctx(monkeypatch, "on", 60, {}, war=object())
    assert shield.run(ctx) == 0 and calls == []


def test_daily_cap_2000_in_decision():
    assert shield_decision(ShieldInputs(0, 5000, 500, 1600, 2000, True))[0] == "cap"   # da tieu 1600 + 500 > 2000
    assert shield_decision(ShieldInputs(0, 5000, 500, 1500, 2000, True))[0] == "buy"


def test_runner_checks_shield_at_end_of_visit():
    src = inspect.getsource(runner)
    i = src.index("P10-7: khien CUOI luot")
    assert "shield.run(ctx)" in src[i:i + 300]
    assert src.index('("shield", shield)') < src.index('("notify", notify)')    # dau luot van som
