"""P7-12 (chu du an 2026-11-24): kiem lai luat khien P6.
- Thu 7 (ngay chien tranh): moi loai khien ke ca Hiep uoc hoa binh (row_8h, mien phi, chuan bi 1h, hoi 14h); giu khien
  LIEN TUC ca 24h; mua kim cuong KHONG gioi han trong cua so.
- Ngoai ngay chien tranh: tran 2000 kim cuong/ngay cho khien; mua ngay chien tranh khong an vao tran nay."""
import types
from datetime import UTC, datetime

import yaml

from aowbot.domain import policy
from aowbot.domain import warday as W
from bot.modules import defense

SAT = datetime(2026, 11, 28, tzinfo=UTC).timestamp()      # thu 7
HOUR, DAY = 3600, 86400


def test_war_day_shield_continuous_24h():
    """Tu 3h truoc gio G toi het ngay: Hiep uoc truoc gio G, roi khien tuc thi gia han truoc khi het -> khong ho."""
    c = W.wcfg(None)
    days = [SAT]
    t, shield_until, peace_at, gaps = SAT - 3 * HOUR, None, None, []
    events = []
    while t < SAT + DAY:
        cover = max([x for x in (shield_until, W.peace_cover(c, peace_at, SAT)) if x] or [0])
        p = W.shield_plan(t, days, shield_until if shield_until and shield_until > t else None, c, peace_at)
        if p.action == "peace":
            peace_at = t
            events.append(("peace", t))
        elif p.action == "shield":
            hours, _ = next(o for o in W.shield_options(p.need_s, True) if o[1])   # het vat pham -> mua
            shield_until = max(cover, t) + hours * HOUR
            events.append(("shield", t, hours))
        nxt = p.at if p.at is not None and p.at > t else t + 60
        nt = min(nxt + 300, SAT + DAY)                           # ghe tre 5 phut
        # trong ngay chien tranh, moi thoi diem tu t toi nt phai duoc che
        cov = max([x for x in (shield_until, W.peace_cover(c, peace_at, SAT)) if x] or [0])
        lo, hi = max(t, SAT), min(nt, SAT + DAY)
        if hi > lo and cov < hi:
            gaps.append((max(lo, cov), hi))
        t = nt
    assert gaps == [], gaps
    assert events[0][0] == "peace" and events[0][1] < SAT - HOUR          # Hiep uoc (row_8h) truoc gio G
    assert any(e[0] == "shield" for e in events)


def test_peace_is_part_of_war_plan_and_row_8h():
    assert defense.ROWS[8] == "defense/row_8h"
    c = W.wcfg(None)
    assert c["peace"] and c["peace_prep_min"] == 60 and c["peace_cooldown_h"] == 14
    p = W.shield_plan(SAT - 2 * HOUR, [SAT], None, c, None)
    assert p.action == "peace"
    # da dung Hiep uoc 10 gio truoc (con hoi 14h) -> khong dung lai, cho sat gio G bat khien tuc thi
    p = W.shield_plan(SAT - 2 * HOUR, [SAT], None, c, SAT - 12 * HOUR)
    assert p.action is None and p.at == SAT - c["renew_before_min"] * 60


def test_war_day_unlimited_gems():
    c = W.wcfg(None)
    assert c["gem_cap"] is None and c["buy_gems"]
    act, _ = policy.shield_decision(policy.ShieldInputs(0, 50_000, 4800, 1_000_000, None, True))
    assert act == "buy"


def test_outside_war_daily_cap_2000():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["defense"]["gem_cap_daily"] == 2000
    assert policy.shield_decision(policy.ShieldInputs(0, 50_000, 500, 1500, 2000, True))[0] == "buy"
    assert policy.shield_decision(policy.ShieldInputs(0, 50_000, 500, 1600, 2000, True))[0] == "cap"


class Store:
    def __init__(self):
        self.st = {}

    def inst(self, idx):
        return self.st

    def update(self, idx, **kw):
        self.st.update(kw)


def test_war_spend_not_counted_toward_daily_cap():
    gems = []
    ctx = types.SimpleNamespace(dev=types.SimpleNamespace(idx=1), store=Store(),
                                mem=types.SimpleNamespace(log_gem=lambda i, s, n: gems.append((s, n))))
    defense._add_spent(ctx, 4800, defense.WAR_SRC)
    assert defense.spent_today(ctx.store.st.get("gems_spent")) == 0      # tran ngay thuong con nguyen
    assert sum(ctx.store.st["gems_spent_war"].values()) == 4800 and gems == [("shield_war", 4800)]
    defense._add_spent(ctx, 500, "shield")
    assert defense.spent_today(ctx.store.st.get("gems_spent")) == 500
    assert defense.counts_toward_cap("shield") and not defense.counts_toward_cap("shield_war")
