"""Utility (B6): diem = (dong gop muc tieu - chi phi thoi gian - rui ro) x do tin, moi thanh phan ghi lai."""
from __future__ import annotations

from dataclasses import dataclass

from aowbot.application.planning import Candidate


@dataclass(frozen=True, slots=True)
class Weights:
    goal: float = 1.0          # x uu tien giai doan x thieu hut
    time: float = 0.5          # moi gio thao tac
    risk: float = 0.5

    def __post_init__(self) -> None:
        if min(self.goal, self.time, self.risk) < 0:
            raise ValueError("trong so phai >= 0")


@dataclass(frozen=True, slots=True)
class Score:
    total: float
    goal: float
    time: float
    risk: float
    confidence: float


def score(c: Candidate, w: Weights) -> Score:
    goal = w.goal * c.goal.priority * c.goal.deficit
    time_cost = w.time * c.action.duration_s / 3600
    risk = w.risk * c.action.risk
    return Score(round((goal - time_cost - risk) * c.confidence, 4), round(goal, 4), round(-time_cost, 4),
                 round(-risk, 4), c.confidence)
