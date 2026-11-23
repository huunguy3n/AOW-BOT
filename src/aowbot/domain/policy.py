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


# ---------- khien (POL: luat cua A-SAFE-1, bot/modules/defense.py goi lai) ----------
SHIELD_TAP = ("use", "buy")   # cac ket qua cua shield_choice dan toi bam nut


@dataclass(frozen=True, slots=True)
class ShieldInputs:
    owned: int | None        # so vat pham khien (None = OCR khong doc duoc)
    gems: int | None         # kim cuong dang co (None = khong doc duoc)
    price: int
    spent_today: int
    daily_cap: int | None    # None = khong gioi han (CHI ngay chien tranh, chu du an 2026-11-23)
    allow_buy: bool


def shield_decision(i: ShieldInputs) -> tuple[str, str]:
    """Quyet dinh o dong khien (ADR-0008). -> (ket qua, ly do).
    Ket qua: 'use' / 'buy' (bam nut) hoac ly do khong bam: 'unread' / 'no_item' / 'no_gems' / 'cap'.
    Cung 1 nut: con vat pham thi dung vat pham, het thi MUA bang kim cuong -> moi so khong doc duoc deu
    dan toi KHONG bam (dong khi loi): khong chac con vat pham thi khong bam, khong biet so du thi khong mua.
    Thu tu kiem tra co y nghia (kiem tra dau tien dung thi tra ve)."""
    checks = (
        (i.owned is None, "unread", "khong doc duoc so vat pham khien"),
        (i.owned is not None and i.owned > 0, "use", f"con {i.owned} vat pham"),
        (not i.allow_buy, "no_item", "het vat pham, khong cho phep mua bang kim cuong"),
        (i.gems is None, "unread", "khong doc duoc so kim cuong"),
        (i.gems is not None and i.gems < i.price, "no_gems", f"khong du kim cuong ({i.gems} < {i.price})"),
        (i.daily_cap is not None and i.spent_today + i.price > i.daily_cap, "cap",
         f"vuot tran ngay ({i.spent_today} + {i.price} > {i.daily_cap})"),
    )
    for hit, code, why in checks:
        if hit:
            return code, why
    cap = "khong gioi han - ngay chien tranh" if i.daily_cap is None else i.daily_cap
    return "buy", f"mua {i.price} kim cuong (da tieu {i.spent_today}/{cap})"


def shield_spend(gems_before: int | None, gems_after: int | None, price: int) -> int:
    """Kim cuong tinh vao tran sau khi mua. Khong doc duoc / so khong giam (OCR lam tron K/M) -> tinh bang gia:
    dem thua chi lam bot mua it hon, dem thieu thi vuot tran."""
    if gems_before is not None and gems_after is not None and gems_after < gems_before:
        return max(gems_before - gems_after, price)
    return price
