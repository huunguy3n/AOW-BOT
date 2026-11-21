"""Executor (B7): trong 1 phien may da bat - quyet dinh -> chay DUNG 1 hanh dong -> xac minh -> quan sat lai ->
quyet dinh lai (replan). Dung khi khong con viec, het tran so hanh dong, hoac Policy chan."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from aowbot.application.decide import DecideSettings, Decision, decide
from aowbot.application.world_view import AccountState
from aowbot.domain.actions import ActionName, spec
from aowbot.domain.events import Event


class Status(Enum):
    OK = "ok"                    # chay xong VA xac minh dung
    UNVERIFIED = "unverified"    # chay xong nhung khong xac minh duoc hieu ung
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ActionResult:
    status: Status
    detail: str


class ActionRunner(Protocol):
    def run(self, action: ActionName) -> ActionResult: ...


class DecisionLog(Protocol):
    def log_decision(self, d: Decision, dry_run: bool, outcome: str | None = None) -> int: ...

    def set_outcome(self, decision_id: int, outcome: str) -> None: ...


@dataclass(frozen=True, slots=True)
class SessionResult:
    decisions: tuple[Decision, ...]
    results: tuple[ActionResult, ...]
    next_eval_at: float
    stopped: str


@dataclass
class _Attempts:
    counts: dict[ActionName, int] = field(default_factory=dict)

    def bump(self, a: ActionName) -> None:
        self.counts[a] = self.counts.get(a, 0) + 1


@dataclass(frozen=True, slots=True)
class SessionDeps:
    state_fn: Callable[[], AccountState]     # doc LAI trang thai (World Model) moi lan quyet dinh
    runner: ActionRunner
    log: DecisionLog
    settings: DecideSettings
    max_actions: int = 8


def run_session(event: Event, deps: SessionDeps) -> SessionResult:
    """state_fn doc LAI trang thai sau moi hanh dong (khong dung ke hoach cu khi trang thai da doi).
    Hanh dong tac dong xong -> quan sat lai ngay (OBSERVE_MARCHES) de lan quyet dinh sau dung so that.
    So lan thu moi hanh dong dem trong phien: Policy chan khi vuot max_retries (khong thu vo han)."""
    attempts = _Attempts()
    decisions: list[Decision] = []
    results: list[ActionResult] = []
    runner, log = deps.runner, deps.log
    for _ in range(deps.max_actions):
        d = decide(event, deps.state_fn(), deps.settings, attempts.counts)
        decisions.append(d)
        i = log.log_decision(d, dry_run=False)
        if d.action is None:
            log.set_outcome(i, "khong lam gi")
            return SessionResult(tuple(decisions), tuple(results), d.next_eval_at, "het viec")
        r = runner.run(d.action)
        results.append(r)
        log.set_outcome(i, f"{r.status.value}: {r.detail}")
        if r.status is not Status.OK:
            attempts.bump(d.action)
        if spec(d.action).mutates_game:
            results.append(runner.run(ActionName.OBSERVE_MARCHES))
    last = decisions[-1]
    return SessionResult(tuple(decisions), tuple(results), last.next_eval_at, f"het tran {deps.max_actions} hanh dong")
