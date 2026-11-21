"""A-SAFE-1: quyet dinh bat/mua khien phai dong khi loi (ADR-0008)."""
import time

import pytest

from bot.modules import defense
from bot.modules.defense import parse_owned, shield_choice, spent_amount, spent_today

PRICE = 500
CAP = 2000


@pytest.mark.parametrize("text, expected", [("3", 3), ("0", 0), (" 12 ", 12), ("", None), ("l", None), (None, None)])
def test_parse_owned_never_guesses_zero(text, expected):
    assert parse_owned(text) == expected


@pytest.mark.parametrize("gems", [None, 0, 10_000])
@pytest.mark.parametrize("allow_buy", [True, False])
def test_unreadable_item_count_never_taps(gems, allow_buy):
    act, _ = shield_choice(None, gems, PRICE, 0, CAP, allow_buy)
    assert act == "unread"


def test_unreadable_gems_never_buys():
    act, _ = shield_choice(0, None, PRICE, 0, CAP, True)
    assert act == "unread"


def test_owned_item_is_used_without_gem_checks():
    assert shield_choice(2, None, PRICE, CAP, CAP, False)[0] == "use"


def test_no_item_and_buying_disabled():
    assert shield_choice(0, 10_000, PRICE, 0, CAP, False)[0] == "no_item"


def test_not_enough_gems():
    assert shield_choice(0, PRICE - 1, PRICE, 0, CAP, True)[0] == "no_gems"


@pytest.mark.parametrize("spent, expected", [(CAP - PRICE, "buy"), (CAP - PRICE + 1, "cap"), (CAP, "cap")])
def test_daily_cap_is_inclusive(spent, expected):
    assert shield_choice(0, 10_000, PRICE, spent, CAP, True)[0] == expected


def test_zero_cap_never_buys():
    assert shield_choice(0, 10_000, PRICE, 0, 0, True)[0] == "cap"


@pytest.mark.parametrize("before, after, expected", [
    (3000, 2500, 500),    # doc dung
    (3000, None, 500),    # doc sau mua hong -> tinh bang gia
    (None, 2500, 500),
    (3000, 3000, 500),    # OCR lam tron K/M, so khong giam -> van tinh gia
    (3000, 2000, 1000),   # game tru nhieu hon gia (vd gia doi) -> tinh so that
    (3000, 2900, 500),    # tru it hon gia (lam tron) -> khong dem thieu
])
def test_spent_amount_never_undercounts(before, after, expected):
    assert spent_amount(before, after, PRICE) == expected


def test_spent_today_uses_utc_day_and_legacy_local_key():
    now = time.time()
    utc_day = time.strftime("%Y-%m-%d", time.gmtime(now))
    local_day = time.strftime("%Y-%m-%d", time.localtime(now))
    assert spent_today({utc_day: 700}, now) == 700
    assert spent_today({local_day: 900}, now) == 900          # du lieu ghi theo ngay dia phuong truoc ban sua
    assert spent_today({utc_day: 300, local_day: 900}, now) == 900   # lay so lon hon (cung ngay thi dict giu 900)
    assert spent_today({"2000-01-01": 5000}, now) == 0
    assert spent_today(None, now) == 0


def test_invalid_shield_hours_is_rejected_before_any_action():
    class Ctx:
        def __init__(self):
            self.cfg = {"defense": {"shield_hours": 3}}

        def __getattr__(self, name):
            raise AssertionError(f"khong duoc thao tac ({name}) khi cau hinh sai")

    assert defense.shield(Ctx()) == "error"
