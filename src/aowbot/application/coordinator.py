"""Dieu phoi agent theo su kien (B9 + SCH-X): may nao can thuc day, luc nao; sau phien hen lan danh gia ke.
Khong mo game chi de kiem tra viec chac chan chua toi han: chi thuc day khi co su kien den han."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from aowbot.application.execute import SessionResult
from aowbot.application.ports import Clock
from aowbot.application.scheduling import TimerRegistry
from aowbot.domain.events import Event, EventType, events_from_timers
from aowbot.domain.marches import MarchTimer


class MarchTimerSource(Protocol):
    def march_timers(self, account: int) -> Sequence[MarchTimer]: ...


class AgentCoordinator:
    def __init__(self, registry: TimerRegistry, timers: MarchTimerSource, clock: Clock) -> None:
        self._registry, self._timers, self._clock = registry, timers, clock

    def sync(self, account: int) -> int:
        """Timer hanh quan moi nhat (bot cu / agent quan sat ghi vao memory.db) -> su kien (trung khoa bo qua)."""
        return self._registry.schedule(events_from_timers(account, list(self._timers.march_timers(account)),
                                                          "timers"))

    def due_event(self, account: int) -> Event | None:
        self.sync(account)
        # timer chi co doi DOC DUOC dong ho; doi khong ro gio do quyet dinh cua agent hen (OBSERVE_DUE). Chua co hen
        # nao cua agent (lan dau bat / vua khoi phuc) -> quan sat ngay de co quyet dinh dau tien
        if not any(e.type is EventType.OBSERVE_DUE for e in self._registry.pending(account)):
            self._registry.schedule([Event(account, EventType.OBSERVE_DUE, "bootstrap", self._clock.now(), "agent")])
        due = [e for e in self._registry.due(200) if e.account == account]
        return due[0] if due else None

    def begin(self, event: Event) -> None:
        self._registry.claim(event)

    def finish(self, event: Event, result: SessionResult | None, error: str | None = None) -> None:
        """Xong phien: su kien nay DONE/FAILED, cac su kien cung may da den han coi nhu da xu ly (1 lan ghe lam
        het viec), hen OBSERVE_DUE luc danh gia lai ma quyet dinh cuoi da tinh."""
        ok = result is not None and error is None
        self._registry.complete(event, ok, error or (result.stopped if result else ""))
        others = [e for e in self._registry.due(200) if e.account == event.account]
        self._registry.supersede(others, f"xu ly cung lan ghe voi {event.key}")
        when = result.next_eval_at if result else self._clock.now() + 1800
        self._registry.schedule([Event(event.account, EventType.OBSERVE_DUE, "agent", when, "agent")])

    def next_at(self, account: int) -> float | None:
        e = self._registry.next_for(account)
        return e.due_at if e else None

    def recover(self) -> list[Event]:
        return self._registry.recover()
