"""Do tuoi cua du kien quan sat duoc: observed / inferred / stale / unknown."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Freshness(Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Fact[T]:
    value: T
    source: str
    observed_at: float
    confidence: float = 1.0
    inferred: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence ngoai [0, 1]: {self.confidence}")


def freshness[T](fact: Fact[T] | None, now: float, ttl_s: float) -> Freshness:
    """Qua TTL thi STALE (gia tri cu khong duoc coi la trang thai hien tai). Moc tuong lai (dong ho lech) = vua thay."""
    if fact is None or fact.value is None:
        return Freshness.UNKNOWN
    if now - fact.observed_at > ttl_s:
        return Freshness.STALE
    return Freshness.INFERRED if fact.inferred else Freshness.OBSERVED


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """TTL (giay) theo khoa du kien; khoa khong khai bao dung default_s."""
    default_s: float
    per_key: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if self.default_s <= 0 or any(v <= 0 for _, v in self.per_key):
            raise ValueError("TTL phai > 0")

    def ttl(self, key: str) -> float:
        return dict(self.per_key).get(key, self.default_s)
