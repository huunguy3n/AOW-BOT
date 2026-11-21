"""Gia lap dung chung cho test (khong can may ao / DB that)."""
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from aowbot.domain.freshness import Fact
from aowbot.domain.marches import MarchObservation


@dataclass
class FakeClock:
    at: float

    def now(self) -> float:
        return self.at

    def advance(self, seconds: float) -> None:
        self.at += seconds


@dataclass
class InMemoryStateSource:
    facts: dict[tuple[int, str], Fact[Any]] = field(default_factory=dict)
    march_obs: dict[int, MarchObservation] = field(default_factory=dict)
    gaps: dict[int, list[float]] = field(default_factory=dict)

    def fact(self, account: int, key: str) -> Fact[Any] | None:
        return self.facts.get((account, key))

    def marches(self, account: int) -> MarchObservation | None:
        return self.march_obs.get(account)

    def return_gaps(self, account: int) -> Sequence[float]:
        return self.gaps.get(account, [])
