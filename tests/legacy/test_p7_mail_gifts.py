"""P7-3 (chu du an 2026-11-24): icon thu (so 1) + icon qua lien minh (so 6) goc phai duoi -> nhan het, lap toi het;
thu nhan o tab DAU TIEN; cham do uu tien so do co the nhan, chat khong uu tien (cuoi)."""
import types

from bot.modules import alliance, reddots, rewards


def test_pick_prefers_claimable_over_top_left_order():
    kinded = [((60, 120), "generic"), ((515, 800), "mail"), ((20, 40), "vip"), ((455, 860), "ally_gift")]
    assert reddots.pick(kinded)[1] in ("mail", "ally_gift")
    assert reddots.pick(kinded)[0] == (515, 800)                 # cung muc 0 -> hang tren truoc
    assert reddots.pick([((60, 120), "generic"), ((20, 40), "vip")])[1] == "vip"
    assert reddots.pick([]) is None


def test_chat_badge_not_a_hud_dot_and_lowest_priority():
    assert not reddots.is_hud_dot((49, 327))                    # huy hieu chat khong tinh
    assert reddots.KIND_PRIO["mail"] < reddots.KIND_PRIO["generic"]


def test_repeat_more():
    assert rewards.repeat_more(1, 1, (515, 820), 4)
    assert not rewards.repeat_more(1, 1, None, 4)               # het so do
    assert not rewards.repeat_more(1, 0, (515, 820), 4)         # khong nhan them duoc -> dung
    assert not rewards.repeat_more(4, 2, (515, 820), 4)


class V:
    def __init__(self, routes):
        self.routes = routes

    def has(self, name):
        return True

    def list(self, prefix):
        return self.routes.get(prefix, [])

    def find(self, img, name, roi=None, **k):
        return (515, 820, 0.95)


class Ctx:
    def __init__(self, claims_per_tab):
        self.v = V({"rewards/mail/claim_": ["rewards/mail/claim_1"], "rewards/mail/open_": ["rewards/mail/open_1"],
                    "rewards/mail/once_": []})
        self.cfg = {"rewards": {"require_dot": False, "dot_tabs": {"mail": [0, 58, 540, 50]}}}
        self.claims = list(claims_per_tab)
        self.loops = 0

    def ensure_city(self):
        pass

    def shot(self):
        return "img"

    def open_route(self, prefix):
        return True

    def claim_loop(self, names, max_taps):
        self.loops += 1
        return self.claims.pop(0) if self.claims else 0

    def tap(self, *a, **k):
        pass


def test_mail_claims_first_tab_even_without_tab_dots(monkeypatch):
    monkeypatch.setattr(rewards, "red_dots", lambda img, roi=None: [])
    ctx = Ctx([3])
    assert rewards.run_route(ctx, "rewards/mail/", 30) == 3 and ctx.loops == 1


def test_mail_repeats_until_badge_clear(monkeypatch):
    monkeypatch.setattr(rewards, "red_dots", lambda img, roi=None: [])
    badges = [(515, 820, 0.9), (515, 820, 0.9), None]
    monkeypatch.setattr(rewards, "icon_badged", lambda ctx, img, tpl, roi=None: badges.pop(0))
    ctx = Ctx([2, 1, 1, 0])
    assert rewards.run_until_clear(ctx, "mail", 30, 4) == 4      # 3 vong toi khi het so do


def test_ally_gift_until_clear_stops_when_nothing_claimed(monkeypatch):
    got = [2, 1, 0]
    monkeypatch.setattr(rewards, "icon_badged", lambda ctx, img, tpl, roi=None: (440, 880))
    monkeypatch.setattr(alliance, "gifts", lambda ctx, x, y: got.pop(0))
    ctx = types.SimpleNamespace(ensure_city=lambda: None, shot=lambda: "img")
    assert rewards.ally_gift_until_clear(ctx, 6) == 3 and got == []


def test_icon_badged_requires_dot_near_icon(monkeypatch):
    ctx = types.SimpleNamespace(v=V({}))
    monkeypatch.setattr(rewards, "red_dots", lambda img, roi=None: [(536, 800)])
    assert rewards.icon_badged(ctx, "img", "rewards/mail/open_1")
    monkeypatch.setattr(rewards, "red_dots", lambda img, roi=None: [(100, 100)])
    assert rewards.icon_badged(ctx, "img", "rewards/mail/open_1") is None
