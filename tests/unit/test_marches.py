"""aowbot.domain.marches + freshness: bang chan tri dung chung voi bot/scheduler.py (A-FIX-1a/1b)."""
import pytest

from aowbot.domain.freshness import Fact, Freshness, freshness
from aowbot.domain.marches import MarchObservation, Return, availability, lower_quartile
from bot import scheduler

NOW = 1_800_000_000.0
H = 3600.0

# total, used, observed_at, timers, unknown_return_s, free, next (at, confident, estimated) | None
TRUTH = [
    ("B11: 5/5 dang di, 1 dong ho", 5, 5, NOW - 60, [(NOW + 2 * H, 0.6)], H, 0, (NOW - 60 + H, False, True)),
    ("uoc luong da qua", 5, 5, NOW - 2 * H, [(NOW + H, 0.9)], H, 4, (NOW + H, True, False)),
    ("dong ho da qua = ranh", 2, 2, NOW, [(NOW - 5, 0.9), (NOW + 100, 0.9)], H, 1, (NOW + 100, True, False)),
    ("dung 3/5", 5, 3, NOW, [(NOW + 100, 0.9)], H, 2, (NOW + 100, True, False)),
    ("chua co x/y -> cach cu", 5, None, None, [(NOW + 100, 0.9)], H, 4, (NOW + 100, True, False)),
    ("thua timer -> giu som nhat", 3, 1, NOW, [(NOW + 300, 0.9), (NOW + 100, 0.9)], H, 2, (NOW + 100, True, False)),
    ("dong ho do tin thap", 1, 1, NOW, [(NOW + 50, 0.3)], H, 0, (NOW + 50, False, False)),
    ("tat ca ranh", 4, 0, NOW, [], H, 4, None),
    ("used > total bi kep", 2, 9, NOW, [], H, 0, (NOW + H, False, True)),
    # phat lai #1 2026-11-22: 5/5 vua doc, uoc luong cu 7 gio (do tin 0,3) khong duoc tinh la 'da ve'
    ("uoc luong cu truoc lan doc x/y bi mau thuan", 5, 5, NOW - 60, [(NOW - 7 * H, 0.3), (NOW + 23 * 60, 0.3)], H, 0,
     (NOW + 23 * 60, False, False)),
    ("dong ho chac chan da qua van = ranh", 5, 5, NOW - 60, [(NOW - 7 * H, 0.9)], H, 1, (NOW - 60 + H, False, True)),
    ("uoc luong da qua SAU lan doc = ranh", 5, 5, NOW - 120, [(NOW - 30, 0.3)], H, 1, (NOW - 120 + H, False, True)),
]


@pytest.mark.parametrize("name, total, used, obs, timers, unk, free, nxt", TRUTH, ids=[t[0] for t in TRUTH])
def test_availability_truth_table(name, total, used, obs, timers, unk, free, nxt):
    a = availability(MarchObservation(total, used, obs, timers), NOW, unk)
    assert a.free == free
    assert a.next_return == (Return(*nxt) if nxt else None)


def test_negative_total_rejected():
    with pytest.raises(ValueError):
        MarchObservation(-1, 0, NOW, [])


def test_scheduler_uses_same_rule():
    for name, total, used, obs, timers, unk, free, nxt in TRUTH:
        got_free, got_next = scheduler.march_slots(total, used, obs, timers, NOW, unk)
        assert got_free == free, name
        assert (got_next[0] if got_next else None) == (nxt[0] if nxt else None), name


@pytest.mark.parametrize("gaps, expected", [
    ([600, 1200, 1800, 2400, 3000, 3600, 4200, 4800], 1800),
    ([100, 200], 999),          # chua du mau
    ([-5, 0, 100, 200], 999),   # bo gia tri <= 0
])
def test_lower_quartile(gaps, expected):
    assert lower_quartile(gaps, 999) == expected


@pytest.mark.parametrize("fact, now, ttl, expected", [
    (None, NOW, 60, Freshness.UNKNOWN),
    (Fact(None, "ocr", NOW), NOW, 60, Freshness.UNKNOWN),
    (Fact(5, "ocr", NOW - 30), NOW, 60, Freshness.OBSERVED),
    (Fact(5, "ocr", NOW - 60), NOW, 60, Freshness.OBSERVED),
    (Fact(5, "ocr", NOW - 61), NOW, 60, Freshness.STALE),
    (Fact(5, "est", NOW - 30, 0.3, inferred=True), NOW, 60, Freshness.INFERRED),
    (Fact(5, "ocr", NOW + 10), NOW, 60, Freshness.OBSERVED),
])
def test_freshness(fact, now, ttl, expected):
    assert freshness(fact, now, ttl) is expected


def test_confidence_validated():
    with pytest.raises(ValueError):
        Fact(1, "x", NOW, confidence=1.5)
