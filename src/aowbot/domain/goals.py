"""Muc tieu farm do duoc (B3). Moi goal: trang thai mong muon, dieu kien thoa man, thieu hut 0..1, uu tien.

Thu tu chu du an 2026-11-21: nha chinh < gather_min_hq -> ContinuousConstruction dan dau (farm chua thu thap
duoc); tu cap do tro len -> MarchUtilization / ResourceFarming dan dau. #1 (cap 30) farm ngay.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aowbot.domain.marches import Availability


class Goal(Enum):
    MARCH_UTILIZATION = "march_utilization"
    RESOURCE_FARMING = "resource_farming"
    CONTINUOUS_CONSTRUCTION = "continuous_construction"


@dataclass(frozen=True, slots=True)
class GoalStatus:
    goal: Goal
    priority: float          # 0..1 trong so theo giai doan tai khoan
    deficit: float           # 0 = thoa man, 1 = thieu hoan toan
    satisfied: bool
    reason: str


@dataclass(frozen=True, slots=True)
class AccountFacts:
    hq_level: int | None
    builders_busy: int | None
    max_builders: int
    gather_min_hq: int


def phase_priority(goal: Goal, f: AccountFacts) -> float:
    early = f.hq_level is not None and f.hq_level < f.gather_min_hq
    if goal is Goal.CONTINUOUS_CONSTRUCTION:
        return 1.0 if early else 0.5
    return 0.2 if early else 1.0


def march_utilization(avail: Availability | None, total: int | None, f: AccountFacts) -> GoalStatus:
    """Mong muon: moi doi hanh quan dang lam viec. Thieu hut = so doi ranh / tong."""
    prio = phase_priority(Goal.MARCH_UTILIZATION, f)
    if avail is None or not total:
        return GoalStatus(Goal.MARCH_UTILIZATION, prio, 1.0, False, "chua biet so doi hanh quan")
    deficit = avail.free / total
    return GoalStatus(Goal.MARCH_UTILIZATION, prio, deficit, avail.free == 0, f"{avail.free}/{total} doi ranh")


def continuous_construction(f: AccountFacts) -> GoalStatus:
    """Mong muon: tho xay dung duoc deu dang xay."""
    prio = phase_priority(Goal.CONTINUOUS_CONSTRUCTION, f)
    if f.builders_busy is None:
        return GoalStatus(Goal.CONTINUOUS_CONSTRUCTION, prio, 1.0, False, "chua biet tho xay")
    idle = max(0, f.max_builders - f.builders_busy)
    return GoalStatus(Goal.CONTINUOUS_CONSTRUCTION, prio, idle / max(1, f.max_builders), idle == 0,
                      f"{idle}/{f.max_builders} tho ranh")
