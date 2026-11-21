"""Use case: dung trang thai tai khoan tai thoi diem `now`, moi du kien gan nhan do tuoi (B2b)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aowbot.application.ports import AccountStateSource, Clock
from aowbot.domain.freshness import Fact, Freshness, FreshnessPolicy, freshness
from aowbot.domain.marches import Availability, availability, lower_quartile

FACT_KEYS = ("hq_level", "builders_busy", "resources", "march_total", "march_used", "world_open")


@dataclass(frozen=True, slots=True)
class Labeled:
    fact: Fact[Any] | None
    freshness: Freshness


@dataclass(frozen=True, slots=True)
class MarchView:
    availability: Availability | None
    freshness: Freshness             # do tuoi cua lan doc 'Hanh quan x/y' lam co so
    unknown_return_s: float


@dataclass(frozen=True, slots=True)
class AccountState:
    account: int
    at: float
    facts: tuple[tuple[str, Labeled], ...]
    marches: MarchView

    def get(self, key: str) -> Labeled:
        return dict(self.facts)[key]


@dataclass(frozen=True, slots=True)
class WorldSettings:
    ttl: FreshnessPolicy
    unknown_return_s: float


def build_account_state(account: int, source: AccountStateSource, clock: Clock,
                        settings: WorldSettings) -> AccountState:
    now = clock.now()
    facts = []
    for key in FACT_KEYS:
        f = source.fact(account, key)
        facts.append((key, Labeled(f, freshness(f, now, settings.ttl.ttl(key)))))
    obs = source.marches(account)
    unk = lower_quartile(source.return_gaps(account), settings.unknown_return_s)
    if obs is None:
        view = MarchView(None, Freshness.UNKNOWN, unk)
    else:
        seen = Fact(obs.used, "march_counter", obs.observed_at) if obs.observed_at is not None else None
        # du lieu x/y da qua TTL: van tinh (uoc luong) nhung gan nhan STALE de lop quyet dinh biet can quan sat lai
        view = MarchView(availability(obs, now, unk), freshness(seen, now, settings.ttl.ttl("march_used")), unk)
    return AccountState(account, now, tuple(facts), view)
