"""Decision engine (B6): su kien + trang thai -> 1 quyet dinh co giai thich (vi sao viec nay, khong phai viec khac)."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass

from aowbot.application.planning import PlanSettings, candidates
from aowbot.application.scoring import Score, Weights, score
from aowbot.application.world_view import AccountState
from aowbot.domain.actions import ActionName
from aowbot.domain.events import Event
from aowbot.domain.policy import SafetyPolicy


@dataclass(frozen=True, slots=True)
class DecideSettings:
    plan: PlanSettings
    weights: Weights
    policy: SafetyPolicy
    idle_recheck_s: float      # khong biet bao gio co viec -> danh gia lai sau N giay


@dataclass(frozen=True, slots=True)
class Option:
    action: str
    goal: str
    goal_reason: str
    feasible: bool
    blocker: str | None
    score: Score | None
    policy: str | None


@dataclass(frozen=True, slots=True)
class Decision:
    event_key: str
    account: int
    at: float
    action: ActionName | None
    expected_effect: str | None
    next_eval_at: float
    options: tuple[Option, ...]
    why: str

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["action"] = self.action.value if self.action else None
        return d


def decide(event: Event, state: AccountState, s: DecideSettings,
           attempts: Mapping[ActionName, int] | None = None) -> Decision:
    attempts = attempts or {}
    options, best = [], None
    for c in candidates(state, s.plan):
        if not c.feasible:
            options.append(Option(c.action.name.value, c.goal.goal.value, c.goal.reason, False, c.blocker, None, None))
            continue
        sc = score(c, s.weights)
        verdict = s.policy.check(c.action, attempts.get(c.action.name, 0), c.confidence)
        options.append(Option(c.action.name.value, c.goal.goal.value, c.goal.reason, True, None, sc, verdict.reason))
        if verdict.allowed and sc.total > 0 and (best is None or sc.total > best[1].total):
            best = (c, sc)
    if best is None:
        nxt = state.marches.availability.next_return if state.marches.availability else None
        at = nxt.at if nxt is not None and nxt.at > state.at else state.at + s.idle_recheck_s
        blockers = "; ".join(f"{o.action}: {o.blocker or o.policy}" for o in options)
        return Decision(event.key, state.account, state.at, None, None, at, tuple(options),
                        f"khong co hanh dong dang lam ({blockers})")
    c, sc = best
    others = ", ".join(f"{o.action} {o.score.total if o.score else o.blocker}" for o in options
                       if o.action != c.action.name.value)
    why = (f"{c.action.name.value}: diem {sc.total} (muc tieu {c.goal.goal.value} {c.goal.reason}, "
           f"thoi gian {sc.time}, rui ro {sc.risk}, do tin {sc.confidence}); khac: {others}")
    return Decision(event.key, state.account, state.at, c.action.name, c.action.expected_effect,
                    state.at + c.action.duration_s, tuple(options), why)
