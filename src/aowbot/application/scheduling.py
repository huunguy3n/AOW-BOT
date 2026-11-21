"""TimerRegistry (B1): hen su kien, chong trung, lay su kien den han, khoi phuc sau khi tien trinh chet."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from aowbot.application.ports import Clock
from aowbot.domain.events import Event, EventStatus


class EventStore(Protocol):
    def add(self, event: Event, now: float) -> bool: ...          # False = da co (trung khoa)

    def due(self, now: float, limit: int) -> list[Event]: ...     # PENDING va den han, som truoc

    def set_status(self, key: str, status: EventStatus, now: float, note: str = "") -> None: ...

    def claimed_before(self, t: float) -> list[Event]: ...

    def pending_for(self, account: int) -> list[Event]: ...


class TimerRegistry:
    def __init__(self, store: EventStore, clock: Clock, claim_timeout_s: float = 1800.0) -> None:
        self._store, self._clock, self._claim_timeout_s = store, clock, claim_timeout_s

    def schedule(self, events: Sequence[Event]) -> int:
        """-> so su kien MOI (trung khoa bi bo qua: cung luc ve doc lai o lan quan sat sau)."""
        now = self._clock.now()
        return sum(self._store.add(e, now) for e in events)

    def due(self, limit: int = 20) -> list[Event]:
        return self._store.due(self._clock.now(), limit)

    def next_for(self, account: int) -> Event | None:
        pend = sorted(self._store.pending_for(account), key=lambda e: e.due_at)
        return pend[0] if pend else None

    def claim(self, event: Event) -> None:
        self._store.set_status(event.key, EventStatus.CLAIMED, self._clock.now())

    def complete(self, event: Event, ok: bool, note: str = "") -> None:
        self._store.set_status(event.key, EventStatus.DONE if ok else EventStatus.FAILED, self._clock.now(), note)

    def supersede(self, events: Sequence[Event], note: str) -> None:
        """Mot lan danh thuc da xu ly tai khoan -> cac su kien khac cung tai khoan da den han coi nhu xong."""
        now = self._clock.now()
        for e in events:
            self._store.set_status(e.key, EventStatus.SUPERSEDED, now, note)

    def recover(self) -> list[Event]:
        """Su kien CLAIMED qua lau (tien trinh chet giua chung) -> tra ve PENDING. Hanh dong tac dong phai tu kiem
        idempotent (vd doc lai x/y truoc khi gui quan) - xem ActionSpec.idempotency."""
        stale = self._store.claimed_before(self._clock.now() - self._claim_timeout_s)
        for e in stale:
            self._store.set_status(e.key, EventStatus.PENDING, self._clock.now(), "khoi phuc sau khi bi ngat")
        return stale
