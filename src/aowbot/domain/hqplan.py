"""G1 (docs/strategy/session-drain-proposal.md): trang thai ke hoach nha chinh + luat nhuong tho xay. Ham thuan.

Moi lan buoc 'upgrade' chay xong ghi ket qua vao HqPlan (luu facts 'hq_plan'). Muc dich:
  - nho "nha chinh dang cho gi" + gio thuc day (thay vi khoa mu / tu kham pha lai moi lan ghe);
  - tho xay (farm chi 1 tho) duoc DANH CHO nha chinh: buoc xay khac (quests, construct) nhuong khi `reserve` dung;
  - ket qua 'none' (khong toi duoc man nang cap) lien tiep -> lui lich theo cap so nhan, khong lap vo ich.
Khong goi thiet bi, khong doc dong ho: nhan `now` tu ngoai.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

CHAIN_GRACE_S = 15 * 60        # tho vua ranh: nha chinh duoc chon truoc trong ngan nay
WAIT_RES_S = 60 * 60           # thieu tai nguyen: thu lai sau
RESERVE_RES_S = 2 * 3600       # ...va giu tai nguyen cho nha chinh toi da bay nhieu (tranh deadlock)
NONE_BASE_S = 30 * 60          # 'none' lan 1: 30 phut, nhan doi moi lan, tran 4h
NONE_CAP_S = 4 * 3600
BUSY_DEFAULT_S = 30 * 60       # dang xay ma khong doc duoc thoi gian con lai


class Status(Enum):
    CHAIN = "chain"                    # vua bat dau 1 nut (nha chinh hoac cong trinh dieu kien)
    WAIT_BUILDER = "wait_builder"      # nha chinh/dieu kien dang xay hoac het tho
    WAIT_RESOURCES = "wait_resources"  # thieu tai nguyen / dieu kien chua xu ly duoc
    UNREACHED = "unreached"            # khong toi duoc man nang cap (none)
    MAXED = "maxed"                    # nha chinh da toi gioi han


@dataclass(frozen=True, slots=True)
class HqPlan:
    status: Status
    at: float
    wake_at: float = 0.0               # sau gio nay moi dang thu lai
    reserve_until: float = 0.0         # truoc gio nay cac buoc xay khac nhuong tho
    none_streak: int = 0
    last_level: int | None = None
    last_note: str = ""

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @staticmethod
    def from_json(d: Any) -> HqPlan | None:
        try:
            return HqPlan(status=Status(d["status"]), at=float(d["at"]), wake_at=float(d.get("wake_at", 0)),
                          reserve_until=float(d.get("reserve_until", 0)), none_streak=int(d.get("none_streak", 0)),
                          last_level=d.get("last_level"), last_note=str(d.get("last_note", "")))
        except (KeyError, TypeError, ValueError):
            return None


def record(prev: HqPlan | None, result: str, now: float, level: int | None = None,
           busy_s: float | None = None) -> HqPlan:
    """Cap nhat ke hoach sau mot lan buoc 'upgrade'. result: ket qua cua build.upgrade_here / goto_hq
    ('started' | 'busy' | 'no_builder' | 'blocked' | 'none' | 'hq_cap' | 'maxed' | 'no_hq')."""
    streak = prev.none_streak if prev else 0
    lv = level if level is not None else (prev.last_level if prev else None)
    if result in ("hq_cap", "maxed"):
        return HqPlan(Status.MAXED, now, last_level=lv, last_note=result)
    if result == "started":
        # tho vua nhan viec: nhuong cho nha chinh khi tho ranh lai (khong biet gio -> grace tu bay gio)
        return HqPlan(Status.CHAIN, now, wake_at=now, reserve_until=now + CHAIN_GRACE_S,
                      last_level=lv, last_note=result)
    if result in ("busy", "no_builder"):
        wake = now + (busy_s if busy_s and busy_s > 0 else BUSY_DEFAULT_S)
        return HqPlan(Status.WAIT_BUILDER, now, wake_at=wake, reserve_until=wake + CHAIN_GRACE_S,
                      last_level=lv, last_note=result)
    if result == "blocked":
        return HqPlan(Status.WAIT_RESOURCES, now, wake_at=now + WAIT_RES_S, reserve_until=now + RESERVE_RES_S,
                      last_level=lv, last_note=result)
    # 'none' / 'no_hq' / ket qua la: khong toi duoc man nang cap
    streak += 1
    delay = min(NONE_BASE_S * 2 ** (streak - 1), NONE_CAP_S)
    return HqPlan(Status.UNREACHED, now, wake_at=now + delay, none_streak=streak, last_level=lv, last_note=result)


def should_attempt(plan: HqPlan | None, now: float) -> tuple[bool, str]:
    """Buoc 'upgrade' co nen chay luc nay? Chi chan khi da biet chac chua den luc (UNREACHED dang lui lich)."""
    if plan is None:
        return True, "chua co ke hoach"
    if plan.status is Status.MAXED:
        return False, "nha chinh da toi gioi han"
    if plan.status is Status.UNREACHED and now < plan.wake_at:
        mins = (plan.wake_at - now) / 60
        return False, f"khong toi duoc man nang cap {plan.none_streak} lan, lui lich {mins:.0f} phut"
    return True, plan.status.value


def reserve(plan: HqPlan | None, now: float, builders_max: int) -> tuple[bool, str]:
    """Buoc xay khac (quests, construct) co phai nhuong tho cho nha chinh khong?
    Chi khi farm chi 1 tho (builders_max <= 1) va ke hoach dang giu cho (reserve_until)."""
    if plan is None or builders_max > 1:
        return False, ""
    if plan.status in (Status.MAXED, Status.UNREACHED):
        return False, ""
    if now < plan.reserve_until:
        return True, f"nhuong tho cho nha chinh ({plan.status.value}, con {(plan.reserve_until - now) / 60:.0f} phut)"
    return False, ""


def after_construct(plan: HqPlan, now: float) -> HqPlan:
    """Vua xay cong trinh moi. UNREACHED (nut 'Nhay' dan toi cong trinh chua co) -> het ly do lui lich: thu lai ngay."""
    if plan.status is not Status.UNREACHED:
        return plan
    return HqPlan(Status.CHAIN, now, wake_at=now, none_streak=0, last_level=plan.last_level,
                  last_note="after_construct")


# ---------- P4 (PM 2026-11-23): muc tieu nha chinh cho farm (len 9 roi 15) ----------
DEFAULT_TARGETS = (9, 15)


def next_target(level: int | None, targets: Iterable[Any] | None = DEFAULT_TARGETS) -> int | None:
    """Muc tieu nha chinh ke tiep (> cap hien tai), None neu da qua het muc tieu / chua biet cap."""
    if level is None:
        return None
    for t in sorted(int(x) for x in targets or ()):
        if level < t:
            return t
    return None


def hq_rush(level: int | None, targets: Iterable[Any] | None = DEFAULT_TARGETS) -> bool:
    """Dang 'day nha chinh' (cap < muc tieu cuoi): nhiem vu xay nha chinh duoc lam truoc, cong trinh khac sau."""
    return next_target(level, targets) is not None
