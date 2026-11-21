"""Noi agent vao runner cu (SCH-X). Runner chi thay mot doi tuong 'hooks' (bot/ khong import duoc aowbot.app,
luat D7) - main.py dung va truyen vao. Agent chi tac dong may co schedule.mode = 'agent' (dat theo may tren web /
data/settings.json); mac dinh khong may nao."""
from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from typing import Any

from aowbot.app.config import load_agent_config
from aowbot.application.coordinator import AgentCoordinator
from aowbot.application.execute import SessionDeps, run_session
from aowbot.application.scheduling import TimerRegistry
from aowbot.application.world_view import build_account_state
from aowbot.domain.events import Event
from aowbot.infrastructure.clock import SystemClock
from aowbot.infrastructure.legacy.actions import LegacyActionRunner
from aowbot.infrastructure.locks import AccountLock
from aowbot.infrastructure.sqlite.agent_store import SqliteAgentStore
from aowbot.infrastructure.sqlite.legacy_memory_reader import LegacyMemoryReader

log = logging.getLogger("aow")
AGENT_MODE = "agent"


class AgentHooks:
    def __init__(self, cfg_for: Callable[[int], Mapping[str, Any]], db: str, lock_dir: str) -> None:
        self._cfg_for, self._db, self._lock_dir = cfg_for, db, lock_dir
        self._clock = SystemClock()
        self._store = SqliteAgentStore(db)
        self._coord = AgentCoordinator(TimerRegistry(self._store, self._clock), LegacyMemoryReader(db), self._clock)
        recovered = self._coord.recover()
        if recovered:
            log.info("Agent: tra %d su kien dang do (tien trinh truoc bi ngat) ve cho xu ly", len(recovered))

    def enabled(self, idx: int) -> bool:
        return (self._cfg_for(idx).get("schedule") or {}).get("mode") == AGENT_MODE

    def due_event(self, idx: int) -> Event | None:
        return self._coord.due_event(idx) if self.enabled(idx) else None

    def next_at(self, idx: int) -> float | None:
        return self._coord.next_at(idx) if self.enabled(idx) else None

    def session(self, ctx: Any, idx: int, event: Event) -> str:
        """Goi tu run_account khi may da bat + game da vao (cung vong doi, watchdog, perf, tat may cua runner)."""
        lock = AccountLock(self._lock_dir, idx)
        if not lock.acquire():
            msg = "tien trinh khac dang giu khoa tai khoan nay - bo qua"
            self._coord.finish(event, None, msg)
            return msg
        self._coord.begin(event)
        try:
            cfg = load_agent_config(self._cfg_for(idx))
            reader = LegacyMemoryReader(self._db)
            try:
                deps = SessionDeps(lambda: build_account_state(idx, reader, self._clock, cfg.world),
                                   LegacyActionRunner(ctx), self._store, cfg.decide)
                result = run_session(event, deps)
            finally:
                reader.close()
        except Exception as e:      # ranh gioi adapter: ghi lai, tra su kien ve FAILED, de runner xu ly tiep
            log.exception("Agent #%d: phien loi", idx)
            self._coord.finish(event, None, f"{type(e).__name__}: {e}")
            raise
        finally:
            lock.release()
        self._coord.finish(event, result)
        summary = f"{len(result.decisions)} quyet dinh, {result.stopped}"
        log.info("Agent #%d: %s; danh gia lai sau %.0f phut", idx, summary,
                 (result.next_eval_at - self._clock.now()) / 60)
        return summary


def build_agent_hooks(cfg_for: Callable[[int], Mapping[str, Any]], base_dir: str) -> AgentHooks:
    return AgentHooks(cfg_for, os.path.join(base_dir, "data", "memory.db"), os.path.join(base_dir, "data", "locks"))
