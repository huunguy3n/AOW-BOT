"""Port ma application can (hien thuc o infrastructure)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from aowbot.domain.freshness import Fact
from aowbot.domain.marches import MarchObservation


class Clock(Protocol):
    def now(self) -> float: ...


class AccountStateSource(Protocol):
    """Quan sat da ghi lai cua 1 tai khoan (hien: memory.db cua bot cu, chi doc)."""

    def fact(self, account: int, key: str) -> Fact[Any] | None: ...

    def marches(self, account: int) -> MarchObservation | None: ...

    def return_gaps(self, account: int) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class ObservationRecord:
    at: float
    used: int | None
    total: int | None
    rows: Sequence[Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class VisitRecord:
    started: float
    why: str
    gather_sent: int | None      # None = lan ghe khong chay gather


class HistorySource(Protocol):
    def observations(self, account: int, since: float, until: float) -> list[ObservationRecord]: ...

    def visits(self, account: int, since: float, until: float) -> list[VisitRecord]: ...

    def fact(self, account: int, key: str) -> Fact[Any] | None: ...
