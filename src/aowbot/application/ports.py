"""Port ma application can (hien thuc o infrastructure)."""
from __future__ import annotations

from collections.abc import Sequence
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
