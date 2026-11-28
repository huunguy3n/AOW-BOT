"""Lich tuan su kien (chu du an 2026-11-23): thu 7 chien tranh (khien lien tuc, kim cuong khong gioi han),
thu 2 thu thap, cong tac tay auto/on/off, gio reset server, Hiep uoc hoa binh, thu tu dong khien."""
from datetime import UTC, datetime

import pytest

from aowbot.domain import policy
from aowbot.domain import warday as W


def ts(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=UTC).timestamp()


SAT = ts(2026, 11, 28)          # thu 7
MON = ts(2026, 11, 23)          # thu 2
TUE = ts(2026, 11, 24, 10)


def test_defaults_saturday_by_schedule_without_any_sign():
    c = W.wcfg(None)
    assert c["mode"] == "auto" and tuple(c["weekdays"]) == (5,) and c["gem_cap"] is None and c["buy_gems"] is True
    assert SAT in W.resolve_days(c, None, TUE)
    w = W.window_now(c, None, SAT + 3600)
    assert w is not None and w.day == SAT and w.start == SAT - 2 * 3600 and w.end == SAT + 86400 + 1800
    assert W.window_now(c, None, TUE) is None


def test_reset_hour_shifts_war_day():
    c = W.wcfg({"reset_hour_utc": 17})
    days = W.resolve_days(c, None, TUE)
    assert SAT + 17 * 3600 in days and SAT not in days
    assert W.window_now(c, None, SAT + 10 * 3600) is None          # thu 7 10h UTC chua toi reset 17h
    assert W.window_now(c, None, SAT + 86400 + 10 * 3600) is not None   # chu nhat 10h UTC = van ngay game thu 7


@pytest.mark.parametrize("mode, want_today", [("on", True), ("off", False), ("auto", False), ("xyz", False)])
def test_manual_switch(mode, want_today):
    c = W.wcfg({"mode": mode})
    assert (W.window_now(c, None, TUE) is not None) is want_today
    assert (W.window_now(c, None, SAT + 3600) is not None) is (mode != "off")


def test_signs_only_add_days():
    c = W.wcfg({"weekdays": []})                     # khong lich
    assert W.resolve_days(c, None, TUE) == []
    assert W.resolve_days(c, ts(2026, 11, 25), TUE) == [SAT]          # bang thong bao
    assert W.resolve_days(c, None, TUE, banner_seen=ts(2026, 11, 26)) == [SAT]
    assert W.resolve_days(W.wcfg({"dates": ["2026-12-01"]}), None, TUE)[-2:] != []


def test_adjacent_days_merge_into_one_window():
    w = W.active_window(SAT + 3600, [SAT, SAT + 86400], 2, 30)
    assert w.end == SAT + 2 * 86400 + 1800


def test_gather_day_monday():
    c = W.wcfg(None)
    assert W.is_gather_day(c, MON + 3600) and not W.is_gather_day(c, TUE)
    assert not W.is_gather_day(W.wcfg({"enabled": False}), MON)
    assert W.is_gather_day(W.wcfg({"gather_weekdays": [1]}), TUE)


@pytest.mark.parametrize("text, want", [("Giai doan 1:Tiep te hau can", True), ("Giai đoạn 2: x", True),
                                        ("Gial doan 3", True), ("Chua bao ho", False), ("", False), (None, False)])
def test_banner(text, want):
    assert W.banner_is_war(text) is want


def test_peace_rules():
    c = W.wcfg(None)
    fri22 = SAT - 2 * 3600
    assert W.peace_available(c, None, fri22)
    assert not W.peace_available(c, fri22 - 13 * 3600, fri22)          # dang hoi 14h
    assert W.peace_available(c, fri22 - 15 * 3600, fri22)
    assert not W.peace_available(W.wcfg({"peace": False}), None, fri22)
    assert W.peace_cover(c, fri22, SAT) == fri22 + 9 * 3600
    assert W.peace_cover(c, SAT - 1800, SAT) is None                   # chuan bi lan sang gio G -> khong tinh


def test_plan_no_peace_waits_until_just_before_g():
    c = W.wcfg({"peace": False})
    p = W.shield_plan(SAT - 2 * 3600 + 60, [SAT], None, c)
    assert p.action is None and p.at == SAT - 20 * 60
    assert W.shield_plan(SAT - 10 * 60, [SAT], None, c).action == "shield"


def test_plan_late_bot_uses_instant_shield_not_peace():
    # bot ghe luc 23:30 thu 6: khong du 1h chuan bi Hiep uoc -> khong dung Hiep uoc; hen 23:40, luc do khien tuc thi
    p = W.shield_plan(SAT - 30 * 60, [SAT], None)
    assert p.action is None and p.at == SAT - 20 * 60
    assert W.shield_plan(SAT - 20 * 60, [SAT], None).action == "shield"


def test_plan_never_unshielded_through_the_day():
    """Mo phong: moi lan ghe bat khien theo ke hoach -> khong co khoang trong nao tu gio G toi het ngay."""
    c = W.wcfg(None)
    now, until, peace_at, gaps = SAT - 2 * 3600, None, None, 0
    covered_to = None
    while now < SAT + 86400:
        p = W.shield_plan(now, [SAT], until, c, peace_at)
        if p.action == "peace":
            peace_at = now
            until = W.peace_cover(c, peace_at, SAT)
        elif p.action == "shield":
            hours = W.shield_options(p.need_s, True)[0][0]
            until = now + hours * 3600
        if now >= SAT and (until is None or until <= now):
            gaps += 1
        covered_to = until
        now = p.at if p.at and p.at > now else now + 600
    assert gaps == 0 and covered_to >= SAT + 86400


def test_shield_options_items_first_then_buy():
    # 28/11/2026: dong vat pham 24h (khong mua duoc) nam trong thu tu vat pham
    assert W.shield_options(3 * 3600, False) == [(12, False), (24, False), (72, False), (1, False)]
    assert W.shield_options(30 * 60, False) == [(1, False), (12, False), (24, False), (72, False)]
    assert W.shield_options(20 * 3600, False) == [(24, False), (72, False), (12, False), (1, False)]
    assert all(h != 24 for h, b in W.shield_options(20 * 3600, True) if b)   # 24h chi vat pham, khong mua
    o = W.shield_options(3 * 3600, True)
    assert o[-2:] == [(1, True), (12, True)]                          # 3 x 500 < 4800
    assert W.shield_options(20 * 3600, True)[-2:] == [(12, True), (1, True)]
    assert all(h != 72 for h, b in W.shield_options(80 * 3600, True) if b)   # khong mua 3 ngay


def test_policy_unlimited_only_when_cap_none():
    big = policy.ShieldInputs(owned=0, gems=100_000, price=4800, spent_today=50_000, daily_cap=None, allow_buy=True)
    assert policy.shield_decision(big)[0] == "buy"
    capped = policy.ShieldInputs(owned=0, gems=100_000, price=4800, spent_today=0, daily_cap=2000, allow_buy=True)
    assert policy.shield_decision(capped)[0] == "cap"
    unread = policy.ShieldInputs(owned=0, gems=None, price=4800, spent_today=0, daily_cap=None, allow_buy=True)
    assert policy.shield_decision(unread)[0] == "unread"               # khong gioi han van dong khi loi
    poor = policy.ShieldInputs(owned=0, gems=100, price=4800, spent_today=0, daily_cap=None, allow_buy=True)
    assert policy.shield_decision(poor)[0] == "no_gems"
