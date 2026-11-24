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


def test_peace_used_but_preparing_then_item(monkeypatch):
    # live4: bam Hiep uoc xong, man hinh van 'off' (chuan bi) -> dung vat pham 1h ngay trong luot
    ctx, calls = _ctx(monkeypatch, [("off", None), ("off", None)], {(1, False): "shielded"})
    assert shield.run(ctx) == 1
    assert calls[0] == ("peace",)
    sh = [c for c in calls if c[0] == "shield"]
    assert sh[-1][1] == 1 and sh[-1][2] is False
    assert ctx.mem.f.get("peace_at")                            # van ghi luc dung Hiep uoc


def test_peace_used_and_on_stops(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None), ("on", 8 * 3600)], {})
    assert shield.run(ctx) == 1 and calls == [("peace",)]


def test_peace_preparing_from_memory_skips_peace_uses_item(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None)], {(1, False): "shielded"}, facts={"peace_at": time.time() - 20 * 60})
    assert shield.run(ctx) == 1
    assert ("peace",) not in calls
    assert [c for c in calls if c[0] == "shield"][-1][1:3] == (1, False)


def test_peace_cooldown_uses_item(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None)], {(1, False): "shielded"}, peace_res="cooldown")
    assert shield.run(ctx) == 1 and calls[0] == ("peace",)
    assert calls[-1][1:3] == (1, False)


def test_peace_label_preparing_uses_item(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None)], {(1, False): "shielded"}, peace_res="preparing")
    assert shield.run(ctx) == 1 and calls[-1][1:3] == (1, False)


def test_end_of_visit_045_renews_with_item(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("on", 45 * 60)], {(1, False): "shielded"})
    assert shield.run(ctx) == 1
    assert ("peace",) not in calls and all(c[4] for c in calls)      # extend


def test_2h_protected_no_stack(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("on", 2 * 3600)], {})
    assert shield.run(ctx) == 0 and calls == []


def test_gems_last_within_cap_src(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None)], {(1, True): "shielded"}, peace_res="cooldown")
    assert shield.run(ctx) == 1
    sh = [c for c in calls if c[0] == "shield"]
    first_buy = next(i for i, c in enumerate(sh) if c[2])
    assert all(not c[2] for c in sh[:first_buy]) and sh[first_buy][3] == shield.SRC
    assert defense.counts_toward_cap(shield.SRC)                    # tinh vao tran 2000/ngay


def test_options_order():
    o = shield.options(False, None, True, 60, True)
    assert all(h != 8 for h, _ in o)
    assert shield.options(False, None, False, 60, True)[0] == (8, False)
    assert all(h != 8 for h, _ in shield.options(True, 30 * 60, False, 60, True))


def test_warday_untouched(monkeypatch):
    ctx, calls = _ctx(monkeypatch, [("off", None)], {}, war=object())
    assert shield.run(ctx) == 0 and calls == []
