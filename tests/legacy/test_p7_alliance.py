"""P7-2 (chu du an 2026-11-24): Lien minh - Lanh tho > Tranh Doat Cu Diem > Nhan; Qua thuong "Nhan toan bo" lap toi het;
quyen gop "Lien minh vinh cuu" chi bang VANG (nut phai 100), khong kim cuong (40), khong cham nut ngon cai."""
import types

from bot import buttons
from bot.modules import alliance


class V:
    def __init__(self, have=(), seen=None):
        self.have, self.seen = set(have), dict(seen or {})

    def has(self, name):
        return name in self.have

    def find(self, img, name, th=None, roi=None, **k):
        return self.seen.get(name)


class Ctx:
    POPUP_CLOSERS = ("common/btn_x",)

    def __init__(self, v, cfg=None, claim_all=0, cans=()):
        self.v, self.cfg, self.taps, self.tpl_taps = v, cfg or {}, [], []
        self.claim_all, self.cans = claim_all, list(cans)
        self.dev = types.SimpleNamespace(idx=1)
        self.mem = None

    def shot(self):
        return "img"

    def find(self, name, fresh=True, **k):
        return self.v.find("img", name, **k)

    def tap_tpl(self, name, **k):
        if name == "ally/btn_gift_claim_all":
            if self.claim_all <= 0:
                return False
            self.claim_all -= 1
            self.tpl_taps.append(name)
            return True
        if self.v.find("img", name):
            self.tpl_taps.append(name)
            return True
        return False

    def wait_for(self, name, **k):
        return True

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def tap_first(self, names, **k):
        return None

    def dismiss_reward(self):
        pass

    def back_out(self, n=1):
        pass


# ---------- quyen gop ----------
def test_donate_safe_rejects_thumb_gem_and_left_half():
    assert alliance.donate_safe(378, 725)                    # "Quyen gop 100" vang (nua phai, nua duoi)
    assert not alliance.donate_safe(140, 725)                # "Quyen gop 40" kim cuong (nua trai)
    assert not alliance.donate_safe(478, 407)                # nut ngon cai (de xuat) phia tren bang
    assert not alliance.donate_safe(378, 725, buttons.GO)    # nut mau xanh duong (kim cuong) -> khong bam
    assert alliance.donate_safe(378, 725, buttons.CLAIM)


def test_donate_roi_excludes_thumb_area():
    x, y, _w, _h = alliance.DONATE_ROI
    assert x >= 270 and y > 420


# ---------- qua tang lien minh ----------
def test_gift_more_stops_when_empty_or_no_progress():
    assert alliance.gift_more(103, 83, 1, 20)
    assert not alliance.gift_more(103, 0, 1, 20)
    assert not alliance.gift_more(103, 103, 1, 20)          # bam ma so khong giam -> dung
    assert not alliance.gift_more(10, 5, 20, 20)            # du so lan toi da
    assert alliance.gift_more(None, None, 1, 20)            # khong doc duoc so: lap toi khi nut bien mat


def test_gift_panel_repeats_claim_all_until_zero(monkeypatch):
    monkeypatch.setattr(alliance, "lv_chest", lambda ctx: 0)              # P9-3: ruong Lv / tung mon (test rieng P9)
    monkeypatch.setattr(alliance.buttons, "with_text", lambda *a, **k: [])
    cans = [103, 83, 63, 0]
    monkeypatch.setattr(alliance, "gift_can_claim", lambda img: cans.pop(0) if cans else 0)
    monkeypatch.setattr(alliance, "gift_sent", lambda img: None)
    ctx = Ctx(V(), claim_all=10)
    n = alliance.gift_panel(ctx)
    # 1 lan tab dac biet + 3 lan tab thuong (103 -> 83 -> 63 -> 0)
    assert n == 4


def test_gift_panel_skips_normal_when_zero(monkeypatch):
    monkeypatch.setattr(alliance, "lv_chest", lambda ctx: 0)              # P9-3: ruong Lv / tung mon (test rieng P9)
    monkeypatch.setattr(alliance.buttons, "with_text", lambda *a, **k: [])
    monkeypatch.setattr(alliance, "gift_can_claim", lambda img: 0)
    monkeypatch.setattr(alliance, "gift_sent", lambda img: None)
    ctx = Ctx(V(), claim_all=5)
    assert alliance.gift_panel(ctx) == 1                     # chi tab dac biet


# ---------- Lanh tho > Tranh Doat Cu Diem ----------
def test_territory_missing_templates_skips_quietly():
    ctx = Ctx(V(have=()))
    assert alliance.territory_claim(ctx) == 0 and ctx.taps == [] and ctx.tpl_taps == []


def test_territory_claims_with_template():
    have = {"ally/tab_territory", "ally/btn_contest", "ally/btn_contest_claim"}
    seen = {"ally/tab_territory": (278, 80, 0.95), "ally/btn_contest": (415, 928, 0.95),
            "ally/btn_contest_claim": (448, 380, 0.95)}
    ctx = Ctx(V(have, seen))
    assert alliance.territory_claim(ctx) == 1
    assert ctx.tpl_taps == ["ally/tab_territory", "ally/btn_contest"] and ctx.taps == [(448, 380)]


def test_territory_no_profit_button(monkeypatch):
    have = {"ally/tab_territory", "ally/btn_contest"}
    seen = {"ally/tab_territory": (278, 80, 0.95), "ally/btn_contest": (415, 928, 0.95)}
    monkeypatch.setattr(alliance.buttons, "with_text", lambda img, rx, roi=None: [])
    ctx = Ctx(V(have, seen))
    assert alliance.territory_claim(ctx) == 0 and ctx.taps == []


def test_run_wires_territory_and_gifts(monkeypatch):
    calls = []
    monkeypatch.setattr(alliance, "open_alliance", lambda c: True)
    monkeypatch.setattr(alliance, "donate", lambda c, n: 0)
    monkeypatch.setattr(alliance, "help_all", lambda c: None)
    monkeypatch.setattr(alliance, "territory_claim", lambda c: calls.append("territory") or 1)
    monkeypatch.setattr(alliance, "main_tab", lambda c: True)
    monkeypatch.setattr(alliance, "gifts_tile", lambda c: calls.append("gifts") or 2)
    monkeypatch.setattr(alliance, "boss", lambda c: 0)
    monkeypatch.setattr(alliance, "ally_mine", lambda c: 0)
    ctx = types.SimpleNamespace(cfg={"alliance": {}}, ensure_city=lambda: None,
                                help_and_free=lambda **k: None)
    assert alliance.run(ctx) == 3 and calls == ["territory", "gifts"]
