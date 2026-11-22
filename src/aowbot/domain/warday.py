"""Luat thuan: moc nhan the luc (0h/8h/15h UTC) va NGAY CHIEN TRANH cua su kien SVS (thu 7, tinh theo UTC).

Chu du an 2026-11-21:
- The luc: phai dang nhap DUNG moc reset 0h, 8h, 15h UTC de nhan.
- Ngay chien tranh = thu 7 cua su kien SVS; nhan biet bang bang thong bao "phoi hop chien tranh".
- Bat khien 8h luc 22h UTC thu 6; het 8h thi bat 12h; sap het 12h ma chua qua ngay thi bat tiep 12h.
- Trong ngay chien tranh cam thu thap .
Khong doc game, khong doc dong ho: moi ham nhan `now` (epoch giay) -> test offline duoc.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass

DAY = 86400
STAMINA_MARKS_UTC = (0, 8, 15)
SATURDAY = 5                          # datetime.weekday(): thu 2 = 0 ... thu 7 = 5
BLOCK_STEPS = ("gather",)            # buoc cam trong cua so chien tranh (chu du an 2026-11-21: phan quan duoc phep)


def _utc_midnight(now: float) -> float:
    return (now // DAY) * DAY


def weekday_utc(now: float) -> int:
    """0 = thu 2 ... 5 = thu 7, 6 = chu nhat (1/1/1970 la thu 5)."""
    return int(now // DAY + 3) % 7


# ---------- moc the luc ----------
def last_stamina_mark(now: float, marks=STAMINA_MARKS_UTC) -> float:
    base = _utc_midnight(now)
    cands = [base + h * 3600 for h in marks] + [base - DAY + max(marks) * 3600]
    return max(t for t in cands if t <= now)


def next_stamina_mark(now: float, marks=STAMINA_MARKS_UTC) -> float:
    base = _utc_midnight(now)
    cands = [base + h * 3600 for h in marks] + [base + DAY + min(marks) * 3600]
    return min(t for t in cands if t > now)


def stamina_due(now: float, last_claim: float | None, delay_min: float = 1, marks=STAMINA_MARKS_UTC) -> bool:
    """Da qua moc (them delay) ma chua nhan ke tu moc do. last_claim = lan ghe nhan the luc gan nhat."""
    mark = last_stamina_mark(now, marks)
    return now >= mark + delay_min * 60 and (last_claim is None or last_claim < mark)


def stamina_next_at(now: float, last_claim: float | None, delay_min: float = 1, marks=STAMINA_MARKS_UTC) -> float:
    """Luc som nhat can ghe de nhan the luc: ngay bay gio neu da den han, khong thi moc ke tiep."""
    if stamina_due(now, last_claim, delay_min, marks):
        return now
    mark = last_stamina_mark(now, marks)
    if last_claim is None or last_claim < mark:      # dang trong delay cua moc hien tai
        return mark + delay_min * 60
    return next_stamina_mark(now, marks) + delay_min * 60


# ---------- ngay chien tranh ----------
def war_saturday(seen_at: float) -> float | None:
    """Thu 7 (0h UTC) cua tuan SVS suy ra tu luc thay bang thong bao: thu 7 dau tien trong hoac sau ngay thay.
    Chu nhat -> None (bang con sot sau tran, khong suy ra tuan toi)."""
    wd = weekday_utc(seen_at)
    if wd == 6:
        return None
    return _utc_midnight(seen_at) + ((SATURDAY - wd) % 7) * DAY


def parse_dates(dates) -> list[float]:
    """Danh sach 'YYYY-MM-DD' (cau hinh warday.dates, chu du an tu khai) -> epoch 0h UTC cua ngay do."""
    out = []
    for d in dates or []:
        try:
            y, m, dd = (int(x) for x in str(d).split("-"))
            out.append(float(calendar.timegm((y, m, dd, 0, 0, 0))))
        except (ValueError, OverflowError):
            continue
    return out


def war_days(seen_at: float | None, dates=None, now: float | None = None) -> list[float]:
    """Cac ngay chien tranh (0h UTC) dang co hieu luc/sap toi: ngay khai thu cong + ngay suy ra tu bang thong bao."""
    out = parse_dates(dates)
    if seen_at:
        s = war_saturday(seen_at)
        if s is not None:
            out.append(s)
    return sorted(set(out))


@dataclass(frozen=True, slots=True)
class WarWindow:
    day: float            # 0h UTC cua ngay chien tranh
    start: float          # luc bat dau (thu 6 22h UTC: bat khien som)
    end: float            # het ngay chien tranh (0h UTC hom sau)


def window_for(day: float, lead_h: float = 2) -> WarWindow:
    return WarWindow(day, day - lead_h * 3600, day + DAY)


def active_window(now: float, days: list[float], lead_h: float = 2) -> WarWindow | None:
    for d in days:
        w = window_for(d, lead_h)
        if w.start <= now < w.end:
            return w
    return None


def next_window(now: float, days: list[float], lead_h: float = 2) -> WarWindow | None:
    fut = [window_for(d, lead_h) for d in days if window_for(d, lead_h).start > now]
    return min(fut, key=lambda w: w.start) if fut else None


def blocks_step(step: str, now: float, days: list[float], lead_h: float = 2) -> bool:
    return step in BLOCK_STEPS and active_window(now, days, lead_h) is not None


# ---------- khien ngay chien tranh ----------
@dataclass(frozen=True, slots=True)
class ShieldPlan:
    hours: int | None      # None = chua can bat
    at: float | None       # luc can ghe (None = khong con viec)
    why: str


def shield_plan(now: float, days: list[float], shield_until: float | None, lead_h: float = 2,
                renew_before_min: float = 20) -> ShieldPlan:
    """Khien can bat luc nao / bao nhieu gio.
    Trong cua so [thu 6 22h UTC, het thu 7]: chua co khien (hoac con <= renew_before_min phut) thi bat:
    8h neu chua toi thu 7 (22h thu 6), 12h tu thu 7 tro di. Khien con lau (vd dung the 3 ngay) -> khong bat, hen
    luc sap het. Het ngay chien tranh -> khong bat tiep (khien 12h cuoi tran qua dem la du)."""
    w = active_window(now, days, lead_h)
    if w is None:
        nw = next_window(now, days, lead_h)
        why = "chua toi ngay chien tranh" if nw else "khong co ngay chien tranh"
        return ShieldPlan(None, nw.start if nw else None, why)
    margin = renew_before_min * 60
    if shield_until is not None and shield_until - now > margin:
        nxt = shield_until - margin
        hh, mm = int(shield_until % DAY // 3600), int(shield_until % 3600 // 60)
        return ShieldPlan(None, nxt if nxt < w.end else None, f"khien con den {hh:02d}:{mm:02d} UTC")
    hours = 8 if now < w.day else 12
    return ShieldPlan(hours, now, f"ngay chien tranh: bat khien {hours}h")
