"""Luat thuan: moc nhan the luc (0h/8h/15h UTC), NGAY CHIEN TRANH (SVS) va NGAY THU THAP trong lich tuan su kien.

Chu du an 2026-11-21:
- The luc: phai dang nhap DUNG moc reset 0h, 8h, 15h UTC de nhan.
- Trong ngay chien tranh cam thu thap (phan quan duoc phep).
Chu du an 2026-11-23 (lich tuan su kien, THAY luat khien 8h/12h cu):
- Thu 7 = ngay chien tranh: giu khien LIEN TUC du 24h, can cu khong bao gio bi tan cong. Dung moi loai khien
  (Hiep uoc hoa binh mien phi, vat pham 1h/12h/3d) va DUOC mua bang kim cuong KHONG GIOI HAN trong ngay chien
  tranh. Ngoai ngay chien tranh van giu tran defense.gem_cap_daily.
- Phat hien: lich (thu trong tuan + gio reset server cau hinh duoc) + cong tac tay (auto/on/off, config + web)
  + bang thong bao / banner 'Giai doan N' (tuy chon). Khong chac -> an toan: giu khien (cua so co le truoc/sau,
  dau hieu chi THEM ngay chien tranh, khong bao gio bot).
- Gia han khien truoc khi het it nhat vai phut (renew_before_min).
- Thu 2 = ngay thu thap: gui TAT CA doi di thu thap (P7-1 2026-11-24: van chay CUOI luot, xem gather_last).
Khong doc game, khong doc dong ho: moi ham nhan `now` (epoch giay) -> test offline duoc.
"""
from __future__ import annotations

import calendar
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

DAY = 86400
STAMINA_MARKS_UTC = (0, 8, 15)
SATURDAY = 5                          # datetime.weekday(): thu 2 = 0 ... thu 7 = 5
MONDAY = 0
BLOCK_STEPS = ("gather",)            # buoc cam trong cua so chien tranh (chu du an 2026-11-21: phan quan duoc phep)


def _utc_midnight(now: float) -> float:
    return (now // DAY) * DAY


def weekday_utc(now: float) -> int:
    """0 = thu 2 ... 5 = thu 7, 6 = chu nhat (1/1/1970 la thu 5)."""
    return int(now // DAY + 3) % 7


# ---------- moc the luc ----------
def last_stamina_mark(now: float, marks: tuple[int, ...] = STAMINA_MARKS_UTC) -> float:
    base = _utc_midnight(now)
    cands = [base + h * 3600 for h in marks] + [base - DAY + max(marks) * 3600]
    return max(t for t in cands if t <= now)


def next_stamina_mark(now: float, marks: tuple[int, ...] = STAMINA_MARKS_UTC) -> float:
    base = _utc_midnight(now)
    cands = [base + h * 3600 for h in marks] + [base + DAY + min(marks) * 3600]
    return min(t for t in cands if t > now)


def stamina_due(now: float, last_claim: float | None, delay_min: float = 1,
                marks: tuple[int, ...] = STAMINA_MARKS_UTC) -> bool:
    """Da qua moc (them delay) ma chua nhan ke tu moc do. last_claim = lan ghe nhan the luc gan nhat."""
    mark = last_stamina_mark(now, marks)
    return now >= mark + delay_min * 60 and (last_claim is None or last_claim < mark)


def stamina_next_at(now: float, last_claim: float | None, delay_min: float = 1,
                    marks: tuple[int, ...] = STAMINA_MARKS_UTC) -> float:
    """Luc som nhat can ghe de nhan the luc: ngay bay gio neu da den han, khong thi moc ke tiep."""
    if stamina_due(now, last_claim, delay_min, marks):
        return now
    mark = last_stamina_mark(now, marks)
    if last_claim is None or last_claim < mark:      # dang trong delay cua moc hien tai
        return mark + delay_min * 60
    return next_stamina_mark(now, marks) + delay_min * 60


# ---------- P7-11: "Dang nhap hen gio" (khung gio co dinh, UTC) ----------
def _windows(windows: Iterable[Iterable[float]]) -> list[tuple[float, float]]:
    out = []
    for w in windows or ():
        a, b = (float(x) for x in w)
        out.append((a % 24, b % 24 if b % 24 != a % 24 else (a % 24) + 24))
    return out


def _spans(now: float, windows: Iterable[Iterable[float]]) -> list[tuple[float, float]]:
    """Khung [bat dau, ket thuc) epoch cua hom qua / hom nay / ngay mai (khung qua nua dem: ket thuc < bat dau)."""
    out = []
    base = _utc_midnight(now)
    for a, b in _windows(windows):
        dur = ((b - a) % 24 or 24) * 3600
        for d in (-DAY, 0, DAY):
            s = base + d + a * 3600
            out.append((s, s + dur))
    return sorted(out)


def login_window(now: float, windows: Iterable[Iterable[float]]) -> tuple[float, float] | None:
    """Khung dang nhap hen gio dang mo luc `now` -> (bat dau, ket thuc) | None."""
    for s, e in _spans(now, windows):
        if s <= now < e:
            return s, e
    return None


def timed_login_due(now: float, last: float | None, windows: Iterable[Iterable[float]], delay_min: float = 2) -> bool:
    """Dang trong khung (qua `delay_min` phut dau) ma chua ghe nhan tu dau khung nay."""
    w = login_window(now, windows)
    if w is None:
        return False
    return now >= w[0] + delay_min * 60 and (last is None or last < w[0])


def timed_login_next_at(now: float, last: float | None, windows: Iterable[Iterable[float]],
                        delay_min: float = 2) -> float | None:
    """Luc som nhat can ghe: ngay neu den han; dang o dau khung (delay) -> het delay; khong thi khung ke tiep."""
    if timed_login_due(now, last, windows, delay_min):
        return now
    for s, e in _spans(now, windows):
        t = s + delay_min * 60
        if e <= now or t >= e or (last is not None and last >= s):
            continue
        return max(t, now) if s <= now else t
    return None


# ---------- P8-3: du 7 may trong khung 1 gio (chu du an 2026-11-24) ----------
# Khung 1 gio la DU cho ca 7 may: luot ghe trong khung la luot NGAN (mo game -> ruong "Dang nhap hen gio" DAU TIEN ->
# notify/rewards ngan neu con thoi gian -> tat may), <= ~12 phut / may; 7 may / 2 luong = 4 dot trong 60 phut.
def timed_login_pending(now: float, lasts: Mapping[int, float | None], windows: Iterable[Iterable[float]]) -> list[int]:
    """Khung dang mo: cac may CHUA nhan tu dau khung (bat may NGAY dau khung, khong cho delay - khoi dong da > delay).
    lasts: idx -> luc nhan gan nhat (fact timed_login_at) | None. Sap theo idx (thu tu on dinh, de doan truoc)."""
    w = login_window(now, windows)
    if w is None:
        return []
    return sorted(i for i, t in lasts.items() if t is None or t < w[0])


def timed_login_missed(start: float, lasts: Mapping[int, float | None]) -> list[int]:
    """Het khung bat dau luc `start`: may nao chua nhan trong khung do (de log canh bao)."""
    return sorted(i for i, t in lasts.items() if t is None or t < start)


def last_closed_window(now: float, windows: Iterable[Iterable[float]]) -> tuple[float, float] | None:
    """Khung gan nhat DA dong (ket thuc <= now)."""
    done = [(s, e) for s, e in _spans(now, windows) if e <= now]
    return max(done) if done else None


def next_window_start(now: float, windows: Iterable[Iterable[float]]) -> float | None:
    """Dau khung ke tiep (> now)."""
    nxt = [s for s, _ in _spans(now, windows) if s > now]
    return min(nxt) if nxt else None


def simulate_waves(insts: Iterable[int], start: float, parallel: int, visit_s: float,
                   free_at: Iterable[float] = ()) -> list[tuple[int, float, float]]:
    """Xep tham lam: moi may vao luong ranh som nhat -> [(idx, bat dau, ket thuc)].
    free_at: luc cac luong dang ban se ranh (may dang chay luot dai); thieu thi luong ranh tu `start`."""
    slots = sorted([max(start, float(t)) for t in free_at][:parallel])
    slots += [start] * (max(1, parallel) - len(slots))
    out = []
    for i in insts:
        k = min(range(len(slots)), key=lambda j: slots[j])
        b = slots[k]
        slots[k] = b + visit_s
        out.append((i, b, b + visit_s))
    return out


def waves_fit(insts: Iterable[int], window: tuple[float, float], parallel: int, visit_s: float,
              free_at: Iterable[float] = ()) -> bool:
    """Moi may nhan ruong TRONG khung? (ruong nhan dau luot ghe -> du khi bat dau + thoi gian toi ruong < ket thuc;
    o day doi hoi CA luot ghe xong trong khung cho chac)."""
    return all(e <= window[1] for _, _, e in simulate_waves(insts, window[0], parallel, visit_s, free_at))


def timed_login_yield(now: float, windows: Iterable[Iterable[float]], others_pending: int) -> bool:
    """May dang chay luot DAI trong khung: da nhan ruong cua minh ma con may khac cho nhan -> ket thuc luot som
    (nhuong luong). Ngoai khung / khong ai cho -> chay tiep binh thuong."""
    return others_pending > 0 and login_window(now, windows) is not None


# ---------- cau hinh (mot cho cho runner / lich / stepgate / module) ----------
MODES = ("auto", "on", "off")
DEFAULTS: Mapping[str, Any] = MappingProxyType({
    "enabled": True, "stamina": True, "stamina_delay_min": 1,
    "mode": "auto",              # auto = lich + dau hieu; on = HOM NAY la ngay chien tranh; off = khong co
    "weekdays": (SATURDAY,),      # ngay chien tranh trong tuan (0 = thu 2 ... 5 = thu 7)
    "reset_hour_utc": 0,         # gio reset server (UTC): ngay chien tranh = [reset thu 7, reset chu nhat)
    "lead_h": 2,                 # mo cua so (bat khien) truoc gio bat dau N gio
    "tail_min": 30,              # giu cua so them N phut sau khi het ngay (dong ho lech -> giu khien)
    "renew_before_min": 20,      # khien con <= N phut thi gia han
    "buy_gems": True,            # het vat pham thi mua bang kim cuong (chu du an 2026-11-23)
    "gem_cap": None,             # tran kim cuong / ngay chien tranh: None = khong gioi han (chu du an 2026-11-23)
    "peace": True,               # Hiep uoc hoa binh (mien phi, chuan bi 1h, 8h, hoi 14h) dung truoc gio chien tranh
    "peace_prep_min": 60, "peace_hours": 8, "peace_cooldown_h": 14,
    "banner_ocr": False,         # doc banner 'Giai doan N' tren ban do the gioi (vung chua kiem tren may 540x960)
    "dates": (),                 # ngay chien tranh khai tay 'YYYY-MM-DD'
    "gather_weekdays": (MONDAY,),  # ngay thu thap: uu tien gui moi doi di thu thap
    # P7-11 (chu du an 2026-11-24): su kien "Dang nhap hen gio" - 5 the luc moi khung; ghe moi may trong
    # 01:00-02:00 va 15:00-16:00 gio VN = 18-19h va 8-9h UTC
    "timed_login": True, "timed_login_windows_utc": ((18, 19), (8, 9)), "timed_login_delay_min": 2,
    # P8-3: luot NGAN trong khung (moi may <= visit_max_min), cac buoc chay sau ruong neu con thoi gian; may dang chay
    # luot dai trong khung -> nhan ruong o buoc ke tiep roi nhuong luong neu may khac con cho (yield)
    "timed_login_visit_max_min": 12, "timed_login_steps": ("warday", "notify", "rewards"), "timed_login_yield": True,
})


def wcfg(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """cfg['warday'] (co the thieu / None) -> dict day du. mode la -> 'auto' (khong bao gio tu tat)."""
    c = {**DEFAULTS, **(raw or {})}
    if c.get("mode") not in MODES:
        c["mode"] = "auto"
    return c


def reset_s(c: Mapping[str, Any]) -> float:
    try:
        return float(c.get("reset_hour_utc") or 0) % 24 * 3600
    except (TypeError, ValueError):
        return 0.0


def day_start(now: float, reset: float = 0.0) -> float:
    """Luc reset server gan nhat <= now (dau 'ngay game')."""
    return _utc_midnight(now - reset) + reset


def game_weekday(now: float, reset: float = 0.0) -> int:
    return weekday_utc(now - reset)


def _wdays(v: Any) -> set[int]:
    out = set()
    for w in v or []:
        try:
            out.add(int(w) % 7)
        except (TypeError, ValueError):
            continue
    return out


def schedule_days(now: float, weekdays: Iterable[int], reset: float = 0.0) -> list[float]:
    """Ngay chien tranh theo lich tuan quanh now (-7 .. +8 ngay) -> dau ngay game (epoch)."""
    wd = _wdays(weekdays)
    base = day_start(now, reset)
    return [base + k * DAY for k in range(-7, 9) if game_weekday(base + k * DAY, reset) in wd]


def war_saturday(seen_at: float) -> float | None:
    """Thu 7 (0h UTC) cua tuan SVS suy ra tu luc thay bang thong bao: thu 7 dau tien trong hoac sau ngay thay.
    Chu nhat -> None (bang con sot sau tran, khong suy ra tuan toi)."""
    wd = weekday_utc(seen_at)
    if wd == 6:
        return None
    return _utc_midnight(seen_at) + ((SATURDAY - wd) % 7) * DAY


def parse_dates(dates: Iterable[Any] | None) -> list[float]:
    """Danh sach 'YYYY-MM-DD' (cau hinh warday.dates, chu du an tu khai) -> epoch 0h UTC cua ngay do."""
    out = []
    for d in dates or []:
        try:
            y, m, dd = (int(x) for x in str(d).split("-"))
            out.append(float(calendar.timegm((y, m, dd, 0, 0, 0))))
        except (ValueError, OverflowError):
            continue
    return out


def war_days(seen_at: float | None, dates: Iterable[Any] | None = None, now: float | None = None) -> list[float]:
    """(Cu, chi dau hieu) ngay khai tay + ngay suy ra tu bang thong bao. Ma moi dung resolve_days."""
    out = parse_dates(dates)
    if seen_at:
        s = war_saturday(seen_at)
        if s is not None:
            out.append(s)
    return sorted(set(out))


def resolve_days(c: Mapping[str, Any], notice_seen: float | None, now: float,
                 banner_seen: float | None = None) -> list[float]:
    """Ngay chien tranh (dau ngay game) theo cong tac + lich + bang thong bao + banner + ngay khai tay.
    mode 'off' -> [] (chu du an tu tat); 'on' -> them HOM NAY; 'auto' -> lich + dau hieu. Dau hieu chi THEM ngay,
    khong bao gio bot ngay cua lich (khong chac -> giu khien)."""
    if not c.get("enabled", True) or c.get("mode") == "off":
        return []
    r = reset_s(c)
    out = set(schedule_days(now, c.get("weekdays") or [], r))
    out.update(d + r for d in parse_dates(c.get("dates")))
    for seen in (notice_seen, banner_seen):
        if seen:
            s = war_saturday(seen)
            if s is not None:
                out.add(s + r)
    if c.get("mode") == "on":
        out.add(day_start(now, r))
    return sorted(out)


def is_gather_day(c: Mapping[str, Any], now: float) -> bool:
    """Thu 2 (mac dinh) = ngay thu thap (chu du an 2026-11-23)."""
    return bool(c.get("enabled", True)) and game_weekday(now, reset_s(c)) in _wdays(c.get("gather_weekdays"))


BANNER_RX = re.compile(r"gia\w{0,2}\s*\w{0,2}o\w{0,2}n\s*\d")


def banner_is_war(text: str | None) -> bool:
    """Chu OCR (tieng Viet mat dau) cua banner ban do the gioi 'Giai doan N: ...' -> dang tuan su kien SVS."""
    return bool(BANNER_RX.search((text or "").lower()))


@dataclass(frozen=True, slots=True)
class WarWindow:
    day: float            # dau ngay chien tranh (reset server)
    start: float          # luc mo cua so (bat khien som lead_h)
    end: float            # het cua so (het ngay + tail)


def window_for(day: float, lead_h: float = 2, tail_min: float = 0) -> WarWindow:
    return WarWindow(day, day - lead_h * 3600, day + DAY + tail_min * 60)


def active_window(now: float, days: list[float], lead_h: float = 2, tail_min: float = 0) -> WarWindow | None:
    """Cua so chua now; 2 ngay sat nhau (vd mode 'on' + lich) gop thanh 1 cua so (khong ho khien giua)."""
    ws = sorted((window_for(d, lead_h, tail_min) for d in set(days)), key=lambda w: w.start)
    hit = [w for w in ws if w.start <= now < w.end]
    if not hit:
        return None
    end = max(w.end for w in hit)
    for w in ws:
        if w.start <= end < w.end:
            end = w.end
    return WarWindow(hit[0].day, hit[0].start, end)


def next_window(now: float, days: list[float], lead_h: float = 2, tail_min: float = 0) -> WarWindow | None:
    fut = [window_for(d, lead_h, tail_min) for d in days if window_for(d, lead_h, tail_min).start > now]
    return min(fut, key=lambda w: w.start) if fut else None


def blocks_step(step: str, now: float, days: list[float], lead_h: float = 2, tail_min: float = 0) -> bool:
    return step in BLOCK_STEPS and active_window(now, days, lead_h, tail_min) is not None


def window_now(c: Mapping[str, Any], notice_seen: float | None, now: float,
               banner_seen: float | None = None) -> WarWindow | None:
    """Cua so chien tranh dang mo theo cau hinh day du (wcfg) - dung chung cho lich / stepgate / module."""
    days = resolve_days(c, notice_seen, now, banner_seen)
    return active_window(now, days, float(c["lead_h"]), float(c["tail_min"]))


# ---------- khien ngay chien tranh ----------
# gia mua bang kim cuong (bang Bao Ho Chien Tranh tren #1, 2026-11-23)
PRICE: Mapping[int, int] = MappingProxyType({1: 500, 12: 4800, 72: 25200})


@dataclass(frozen=True, slots=True)
class ShieldPlan:
    action: str | None     # 'peace' (Hiep uoc) | 'shield' (khien tuc thi) | None (chua can)
    at: float | None       # luc can ghe (None = khong con viec)
    why: str
    need_s: float = 0.0    # 'shield': so giay con phai che (toi het cua so)


def peace_cover(c: Mapping[str, Any], peace_at: float | None, day: float) -> float | None:
    """Hiep uoc kich hoat luc peace_at -> het han (epoch); chi tinh khi chuan bi xong TRUOC gio chien tranh."""
    if not peace_at:
        return None
    ready = peace_at + float(c["peace_prep_min"]) * 60
    return ready + float(c["peace_hours"]) * 3600 if ready <= day else None


def peace_available(c: Mapping[str, Any], peace_at: float | None, now: float) -> bool:
    return bool(c.get("peace")) and (not peace_at or now - peace_at >= float(c["peace_cooldown_h"]) * 3600)


def shield_plan(now: float, days: list[float], shield_until: float | None, c: Mapping[str, Any] | None = None,
                peace_at: float | None = None) -> ShieldPlan:
    """Khien ngay chien tranh. shield_until = han khien da biet (doc man hinh / ghi luc bat), None = khong co.
    - Ngoai cua so: hen luc mo cua so.
    - Trong cua so, khien (hoac Hiep uoc chuan bi xong truoc gio G) con > renew_before_min: hen luc sap het.
    - Chua che: truoc gio G du thoi gian chuan bi -> Hiep uoc (mien phi); khong thi khien tuc thi (vat pham, het thi
      mua). Truoc gio G ma khong dung duoc Hiep uoc -> cho sat gio G (truoc renew_before_min) moi bat khien tuc thi."""
    c = wcfg(c)
    lead, tail, margin = float(c["lead_h"]), float(c["tail_min"]), float(c["renew_before_min"]) * 60
    w = active_window(now, days, lead, tail)
    if w is None:
        nw = next_window(now, days, lead, tail)
        return ShieldPlan(None, nw.start if nw else None,
                          "chua toi ngay chien tranh" if nw else "khong co ngay chien tranh")
    cover = max([x for x in (shield_until, peace_cover(c, peace_at, w.day)) if x is not None] or [0.0])
    if cover - now > margin:
        nxt = cover - margin
        hh, mm = int(cover % DAY // 3600), int(cover % 3600 // 60)
        return ShieldPlan(None, nxt if nxt < w.end else None, f"khien con den {hh:02d}:{mm:02d} UTC")
    prep = float(c["peace_prep_min"]) * 60
    if now < w.day:
        if peace_available(c, peace_at, now) and now + prep + margin <= w.day:
            return ShieldPlan("peace", now, "truoc gio chien tranh: dung Hiep uoc hoa binh (mien phi)")
        if now < w.day - margin:
            return ShieldPlan(None, w.day - margin, "cho sat gio chien tranh moi bat khien tuc thi")
    return ShieldPlan("shield", now, "ngay chien tranh: bat khien tuc thi", w.end - now)


def shield_options(need_s: float, buy: bool) -> list[tuple[int, bool]]:
    """Thu tu thu cac dong khien (gio, duoc mua?) de che need_s giay. Vat pham (khong ton kim cuong) truoc: dong nho
    nhat du che, roi dong lon hon, roi dong nho hon; sau do mua (neu cho): re hon trong 1h / 12h truoc. Khong mua 3d."""
    need_h = max(need_s, 1.0) / 3600
    rows = sorted(PRICE)
    fit = [h for h in rows if h >= need_h]
    small = [h for h in reversed(rows) if h < need_h]
    out = [(h, False) for h in fit + small]
    if buy:
        first = 1 if math.ceil(need_h) * PRICE[1] < PRICE[12] else 12
        out += [(first, True), (13 - first, True)]
    return out


TAIL_STEP = "gather"


def gather_last(order: list[str]) -> list[str]:
    """P7-1 (chu du an 2026-11-24, live #1): thu thap LUON chay CUOI luot (truoc 'observe') moi ngay - gather chay som
    chiem 5/5 quan doan -> cuop xe, phan quan, mo lien minh, tinh bao bi bo. Cac buoc can quan doan chay truoc.
    Thu 2 (ngay thu thap) cung cuoi luot nhung gui HET quan doan con lai (khong giu cho phan quan)."""
    if TAIL_STEP not in order:
        return list(order)
    rest = [n for n in order if n != TAIL_STEP]
    if "observe" in rest:
        i = rest.index("observe")
        return [*rest[:i], TAIL_STEP, *rest[i:]]
    return [*rest, TAIL_STEP]
