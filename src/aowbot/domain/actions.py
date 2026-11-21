"""Dang ky hanh dong (B4): tien dieu kien, hieu ung ky vong, thoi luong, chi phi, rui ro, xac minh, retry."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aowbot.domain.goals import Goal


class ActionName(Enum):
    OBSERVE_MARCHES = "observe_marches"
    DISPATCH_GATHER = "dispatch_gather"
    LEGACY_BUILD = "legacy_build"


@dataclass(frozen=True, slots=True)
class ActionSpec:
    name: ActionName
    goal: Goal
    expected_effect: str
    duration_s: float        # uoc luong ban dau (B8 se hoc tu bang runs/perf)
    risk: float              # 0..1: kha nang de lai man hinh/trang thai xau
    premium_cost: int        # kim cuong; > 0 chi duoc phep neu Policy cho (ADR-0008)
    verification: str
    max_retries: int
    idempotency: str
    mutates_game: bool       # False = chi quan sat

    def __post_init__(self) -> None:
        if not 0.0 <= self.risk <= 1.0 or self.duration_s <= 0 or self.max_retries < 0 or self.premium_cost < 0:
            raise ValueError(f"ActionSpec khong hop le: {self.name}")


REGISTRY: tuple[ActionSpec, ...] = (
    ActionSpec(ActionName.OBSERVE_MARCHES, Goal.MARCH_UTILIZATION,
               "doc lai 'Hanh quan x/y' + dong ho cac doi", 20.0, 0.02, 0,
               "doc duoc so x/y", 2, "chi doc - lap lai an toan", mutates_game=False),
    # gather.run(limit=1): bot cu chon mo theo uu tien/tai trong (gather.try_dispatch); 36-413 s, trung vi ~110 s
    ActionSpec(ActionName.DISPATCH_GATHER, Goal.MARCH_UTILIZATION,
               "1 doi ranh di thu thap", 110.0, 0.1, 0,
               "so doi dang di (x) tang 1", 2,
               "doc lai x/y truoc khi gui: x da tang thi khong gui lai", mutates_game=True),
    ActionSpec(ActionName.LEGACY_BUILD, Goal.CONTINUOUS_CONSTRUCTION,
               "bat dau 1 nang cap (buoc mainquest/quests cu)", 180.0, 0.2, 0,
               "so tho dang xay tang", 1, "doc lai tho xay truoc khi chay", mutates_game=True),
)


def spec(name: ActionName) -> ActionSpec:
    for s in REGISTRY:
        if s.name is name:
            return s
    raise KeyError(name)
