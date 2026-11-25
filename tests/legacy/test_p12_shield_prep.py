"""P12-1 (live-run-4): #0/#2-#6 bam Hiep uoc hoa binh dau luot, trang thai 'chuan bi' 17-28 phut, cuoi luot khien TAT.
Nay: Hiep uoc chuan bi / hoi chieu -> dung vat pham khien ngay; Hiep uoc chi tinh la xong khi khien DANG BAT."""
import time
import types

from bot.modules import defense, shield, warday


class Mem:
    def __init__(self, f=None):
        self.f = dict(f or {})

    def fact(self, i, k):
        return self.f.get(k)

    def set_fact(self, i, k, v):
        self.f[k] = v


def _ctx(monkeypatch, states, results, peace_res="peace", facts=None, war=None):
    """states: danh sach (trang thai, giay con) lan luot cho screen_shield."""
    calls, seq = [], list(states)
    monkeypatch.setattr(warday, "window", lambda *a, **k: war)
    monkeypatch.setattr(warday, "screen_shield", lambda ctx: seq.pop(0) if len(seq) > 1 else seq[0])
    monkeypatch.setattr(defense, "peace", lambda ctx, skip_if_active=False: calls.append(("peace",)) or peace_res)

    def sh(ctx, hours=None, allow_buy=None, src=None, extend=False, **k):
        calls.append(("shield", hours, allow_buy, src, extend))
        return results.get((hours, allow_buy), "no_item")
    monkeypatch.setattr(defense, "shield", sh)
    ctx = types.SimpleNamespace(cfg={"defense": {"gem_cap_daily": 2000}}, mem=Mem(facts),
                                dev=types.SimpleNamespace(idx=0), ensure_city=lambda: None)
    return ctx, calls


def test_label_status():
    assert defense.peace_label_status("Mien phi") == "ready"
    assert defense.peace_label_status("Mi3n phi") == "ready"
    assert defense.peace_label_status("Chuan bi 00:42:10") == "preparing"
    assert defense.peace_label_status("Preparing") == "preparing"
    assert defense.peace_label_status("11:20:05") == "cooldown"
    assert defense.peace_label_status("") == "cooldown"


def test_plan_off_while_preparing_goes():
    now = time.time()
    go, why = shield.plan("off", False, now - 22 * 60, now, 60)
    assert go and "chuan bi" in why.lower()                     # live4 #0 cuoi luot: truoc day 'bo qua'


def test_peace_used_and_on_stops(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None), ("on", 8 * 3600)], {})
    assert shield.run(ctx) == 1 and calls == [("peace",)]


def test_2h_protected_no_stack(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("on", 2 * 3600)], {})
    assert shield.run(ctx) == 0 and calls == []


def test_options_order():
    o = shield.options(False, None, True, 60, True)
    assert all(h != 8 for h, _ in o)
    assert shield.options(False, None, False, 60, True)[0] == (8, False)
    assert all(h != 8 for h, _ in shield.options(True, 30 * 60, False, 60, True))


def test_warday_untouched(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None)], {}, war=object())
    assert shield.run(ctx) == 0 and calls == []


def _nobuy(calls):
    return not any(c[0] == "shield" for c in calls)


def test_p13_preparing_no_item_no_gem(monkeypatch):
    # P13-4: Hiep uoc vua dung (chuan bi) -> KHONG dung vat pham / kim cuong de 'cuu' (ghi de P12-1)
    ctx, calls = _ctx(monkeypatch, [("off", None)], {(1, False): "shielded", (1, True): "shielded"},
                      facts={"peace_at": time.time() - 600})
    assert shield.run(ctx) == 0 and _nobuy(calls) and ("peace",) not in calls


def test_p13_cooldown_no_item_no_gem(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None)], {(1, False): "shielded"}, peace_res="cooldown")
    assert shield.run(ctx) == 0 and _nobuy(calls) and calls == [("peace",)]


def test_p13_free_peace_used(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None)], {}, peace_res="peace")
    assert shield.run(ctx) == 1 and _nobuy(calls) and ctx.mem.f.get("peace_at")


def test_p13_low_shield_not_renewed_with_item(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("on", 45 * 60)], {(1, False): "shielded"})
    assert shield.run(ctx) == 0 and calls == []
