"""Planner (B5): tu trang thai tai khoan -> ung vien hanh dong kha thi + blocker (vi sao khong lam duoc)."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from aowbot.application.world_view import AccountState
from aowbot.domain.actions import ActionName, ActionSpec, spec
from aowbot.domain.freshness import Freshness
from aowbot.domain.goals import AccountFacts, GoalStatus, continuous_construction, march_utilization

CONFIDENCE = MappingProxyType({Freshness.OBSERVED: 1.0, Freshness.INFERRED: 0.7, Freshness.STALE: 0.3,
                               Freshness.UNKNOWN: 0.0})


@dataclass(frozen=True, slots=True)
class PlanSettings:
    gather_min_hq: int
    max_builders: int


@dataclass(frozen=True, slots=True)
class Candidate:
    action: ActionSpec
    goal: GoalStatus
    feasible: bool
    blocker: str | None
    confidence: float          # do tin cua du kien lam co so cho hanh dong


def _value(state: AccountState, key: str) -> object:
    lab = state.get(key)
    return None if lab.fact is None or lab.freshness in (Freshness.UNKNOWN,) else lab.fact.value


def account_facts(state: AccountState, s: PlanSettings) -> AccountFacts:
    hq, busy = _value(state, "hq_level"), _value(state, "builders_busy")
    return AccountFacts(hq if isinstance(hq, int) else None, busy if isinstance(busy, int) else None,
                        s.max_builders, s.gather_min_hq)


def candidates(state: AccountState, s: PlanSettings) -> list[Candidate]:
    f = account_facts(state, s)
    m = state.marches
    total = _value(state, "march_total")
    mg = march_utilization(m.availability, total if isinstance(total, int) else None, f)
    out = []

    march_block = None
    if f.hq_level is not None and f.hq_level < s.gather_min_hq:
        march_block = f"nha chinh {f.hq_level} < {s.gather_min_hq}: chua thu thap"
    elif _value(state, "world_open") is False:
        march_block = "ban do the gioi chua mo"

    stale = m.freshness in (Freshness.STALE, Freshness.UNKNOWN)
    out.append(Candidate(spec(ActionName.OBSERVE_MARCHES), mg, march_block is None and stale,
                         march_block or (None if stale else "du lieu hanh quan con moi"), 1.0))
    if march_block:
        dispatch_block: str | None = march_block
    elif stale:
        dispatch_block = f"du lieu hanh quan {m.freshness.value} - quan sat lai truoc"
    elif m.availability is None or m.availability.free == 0:
        dispatch_block = "khong co doi ranh"
    else:
        dispatch_block = None
    out.append(Candidate(spec(ActionName.DISPATCH_GATHER), mg, dispatch_block is None, dispatch_block,
                         CONFIDENCE[m.freshness]))

    cg = continuous_construction(f)
    busy_lab = state.get("builders_busy")
    if f.builders_busy is None or busy_lab.freshness is not Freshness.OBSERVED:
        build_block: str | None = f"so tho xay {busy_lab.freshness.value}"
    elif cg.satisfied:
        build_block = "moi tho dang xay"
    else:
        build_block = None
    out.append(Candidate(spec(ActionName.LEGACY_BUILD), cg, build_block is None, build_block,
                         CONFIDENCE[busy_lab.freshness]))
    return out
