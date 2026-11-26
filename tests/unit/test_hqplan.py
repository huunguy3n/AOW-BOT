"""aowbot.domain.hqplan (G1): ke hoach nha chinh + luat nhuong tho."""
from aowbot.domain import hqplan
from aowbot.domain.hqplan import (
    CHAIN_GRACE_S,
    NONE_CAP_S,
    HqPlan,
    Status,
    after_construct,
    record,
    reserve,
    should_attempt,
)

NOW = 1_800_000_000.0
H = 3600.0


def test_started_reserves_only_while_builder_busy():
    p = record(None, "started", NOW)
    assert p.status is Status.CHAIN and p.none_streak == 0
    assert reserve(p, NOW + 60, 0)[0]
    assert not reserve(p, NOW + 60, 1)[0]          # P13f-2: tho RANH -> khong nhuong
    assert not reserve(p, NOW + 60, None)[0]       # khong doc duoc -> khong nhuong
    assert not reserve(p, NOW + CHAIN_GRACE_S + 1, 0)[0]


def test_idle_builder_never_reserved():
    for r in ("started", "busy", "no_builder", "blocked", "none", "hq_cap"):
        p = record(None, r, NOW, busy_s=H)
        assert not any(reserve(p, NOW + dt, 1)[0] for dt in (0, 60, H, 3 * H))


def test_busy_uses_remaining_time_and_reserves_past_it():
    p = record(None, "busy", NOW, busy_s=2 * H)
    assert p.status is Status.WAIT_BUILDER and p.wake_at == NOW + 2 * H
    assert reserve(p, NOW + 2 * H + 60, 0)[0]


def test_none_backs_off_and_does_not_reserve():
    p = None
    waits = []
    for _ in range(6):
        p = record(p, "none", NOW)
        waits.append(p.wake_at - NOW)
        assert not reserve(p, NOW, 0)[0]
    assert waits[:4] == [300, 600, 1200, 2400] and waits[-1] == NONE_CAP_S
    assert p.none_streak == 6


def test_should_attempt_blocks_only_while_backing_off():
    p = record(None, "none", NOW)
    assert not should_attempt(p, NOW + 60)[0]
    assert should_attempt(p, NOW + 31 * 60)[0]
    assert should_attempt(None, NOW)[0]


def test_started_resets_none_streak():
    p = record(record(None, "none", NOW), "started", NOW + 1)
    assert p.none_streak == 0 and p.status is Status.CHAIN


def test_resources_block_does_not_reserve():
    p = record(None, "blocked", NOW)
    assert p.status is Status.WAIT_RESOURCES
    assert not reserve(p, NOW + H, 0)[0]          # P13f-2: tho khong lam nha chinh -> khong co gi de nhuong


def test_maxed_stops_everything():
    for r in ("hq_cap", "maxed"):
        p = record(None, r, NOW)
        assert not should_attempt(p, NOW)[0] and not reserve(p, NOW, 0)[0]


def test_json_roundtrip_and_garbage():
    p = record(None, "busy", NOW, level=7, busy_s=600)
    assert HqPlan.from_json(p.to_json()) == p
    assert HqPlan.from_json({"status": "xxx"}) is None


def test_after_construct_clears_none_backoff_only():
    p = record(record(None, "none", NOW), "none", NOW)
    q = after_construct(p, NOW + 5)
    assert should_attempt(q, NOW + 5)[0] and q.none_streak == 0
    busy = record(None, "busy", NOW, busy_s=H)
    assert after_construct(busy, NOW) is busy


def test_next_target_and_rush():
    assert hqplan.DEFAULT_TARGETS == (9, 15)
    assert hqplan.next_target(4) == 9
    assert hqplan.next_target(9) == 15
    assert hqplan.next_target(15) is None
    assert hqplan.next_target(None) is None
    assert hqplan.next_target(3, [15, 9]) == 9
    assert hqplan.hq_rush(7) and not hqplan.hq_rush(20) and not hqplan.hq_rush(None)


def test_wait_builder_does_not_reserve_idle_builder():
    """P13d-3 / P13f-2: cho nha chinh (wait_builder) -> tho ranh luon duoc dung cho cong trinh khac."""
    p = record(None, "no_builder", NOW)
    assert p.status is Status.WAIT_BUILDER
    assert not reserve(p, NOW + 60, 1)[0] and not reserve(p, p.wake_at + 60, 1)[0]
    assert reserve(p, p.wake_at + 60, 0)[0]
