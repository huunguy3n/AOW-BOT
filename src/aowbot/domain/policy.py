"""Chinh sach an toan (POL) dung TRUOC Executor; hoc may / diem utility khong vuot qua duoc (ADR-0008)."""
from __future__ import annotations

from dataclasses import dataclass

from aowbot.domain.actions import ActionName, ActionSpec


@dataclass(frozen=True, slots=True)
class PolicyVerdict:
    allowed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class SafetyPolicy:
    premium_whitelist: frozenset[ActionName] = frozenset()   # mac dinh: khong hanh dong nao duoc tieu kim cuong
    min_state_confidence: float = 0.5                        # du kien lam co so cho hanh dong tac dong
    premium_daily_cap: int = 0

    def check(self, action: ActionSpec, attempts: int, state_confidence: float, premium_spent_today: int = 0) \
            -> PolicyVerdict:
        if action.premium_cost > 0:
            if action.name not in self.premium_whitelist:
                return PolicyVerdict(False, f"{action.name.value} ton {action.premium_cost} kim cuong: khong cho phep")
            if premium_spent_today + action.premium_cost > self.premium_daily_cap:
                return PolicyVerdict(False, "vuot tran kim cuong ngay")
        if attempts >= action.max_retries + 1:
            return PolicyVerdict(False, f"da thu {attempts} lan (toi da {action.max_retries + 1})")
        if action.mutates_game and state_confidence < self.min_state_confidence:
            return PolicyVerdict(False, f"do tin trang thai {state_confidence:.2f} < {self.min_state_confidence}")
        return PolicyVerdict(True, "ok")
