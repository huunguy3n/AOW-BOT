"""Luat ve doi hanh quan (quan doan). Mot luat, mot cho: bot/scheduler.py goi lai (A-FIX-1b)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

CONFIDENT = 0.6   # do tin toi thieu cua dong ho doc duoc de coi luc ve la chac chan


@dataclass(frozen=True, slots=True)
class Return:
    at: float
    confident: bool
    estimated: bool


@dataclass(frozen=True, slots=True)
class MarchObservation:
    """Lan doc 'Hanh quan x/y' + dong ho cac doi. used/observed_at None = chua doc duoc x/y."""
    total: int
    used: int | None
    observed_at: float | None
    timers: Sequence[tuple[float, float]]     # (luc ve, do tin) cua cac doi doc duoc dong ho

    def __post_init__(self) -> None:
        if self.total < 0:
            raise ValueError(f"total am: {self.total}")


@dataclass(frozen=True, slots=True)
class Availability:
    free: int
    next_return: Return | None


def availability(obs: MarchObservation, now: float, unknown_return_s: float) -> Availability:
    """So doi ranh luc `now` va lan som nhat co doi ve.

    Doi dang di khong co dong ho KHONG phai doi ranh: uoc luong ve luc observed_at + unknown_return_s.
    Dong ho da qua = doi da ve. Chua co x/y -> moi timer la 1 doi dang di (cach cu, truoc A-FIX-1).
    Ngoai le: dong ho UOC LUONG (do tin < CONFIDENT) da qua TRUOC lan doc x/y ma x/y van bao doi dang di thi
    uoc luong do sai (phat lai #1 2026-11-22: uoc luong cu 7 gio -> agent thay '1 doi ranh' du game bao 5/5,
    lap dispatch_gather -> observe_marches toi het tran 8 hanh dong) -> coi nhu doi 'khong ro gio ve'.
    """
    total, used, observed_at, timers = obs.total, obs.used, obs.observed_at, obs.timers
    if used is None or observed_at is None:
        used, observed_at = len(timers), now
    used = max(0, min(int(used), int(total)))
    known = sorted(timers)[:used]
    unknown = Return(observed_at + unknown_return_s, False, True)
    stale = obs.used is not None
    returns = [unknown if stale and c < CONFIDENT and t <= observed_at else Return(t, c >= CONFIDENT, False)
               for t, c in known]
    returns += [unknown] * (used - len(known))
    free = total - used + sum(1 for r in returns if r.at <= now)
    future = sorted((r for r in returns if r.at > now), key=lambda r: r.at)
    return Availability(free, future[0] if future else None)


def lower_quartile(gaps: Sequence[float], default: float, min_samples: int = 3) -> float:
    """Thoi gian ve dien hinh cho doi khong doc duoc dong ho: phan vi 25 % (ghe som re hon de doi nam khong).
    Phat lai #1 2026-11-21: p25 chan 5/6 lan ghe gui 0 doi; trung vi lam tre 4/9 lan co gui."""
    xs = sorted(g for g in gaps if g > 0)
    return xs[len(xs) // 4] if len(xs) >= min_samples else default


@dataclass(frozen=True, slots=True)
class MarchTimer:
    index: int
    kind: str          # 'march' = luc doi ranh lai, 'arrive' = luc toi mo (doc gio thu thap)
    due_at: float
    source: str        # 'ocr' | 'est'
    confidence: float


def timers_from_rows(rows: Sequence[Mapping[str, Any]]) -> list[MarchTimer]:
    """Dong 'Hanh quan' doc duoc (observe) -> timer. Luat chung cho bot/modules/observe.py va agent.
    Dang toi mo: hen luc toi mo (gio thu thap chi hien khi da toi) + uoc luong ve = toi + thoi gian di (di = ve).
    Dang ve: luc ve (tin 0,9). Dang thu thap da biet luc ve: 0,6. Chi biet luc thu thap xong: 0,4 (som hon thuc te)."""
    out: list[MarchTimer] = []
    for i, m in enumerate(rows):
        state = m.get("state")
        if state == "marching" and m.get("arrive_at"):
            out.append(MarchTimer(i, "arrive", float(m["arrive_at"]), "ocr", 0.9))
            if m.get("travel"):
                out.append(MarchTimer(i, "march", float(m["arrive_at"]) + float(m["travel"]), "est", 0.3))
            continue
        if m.get("return_at"):
            out.append(MarchTimer(i, "march", float(m["return_at"]), "ocr", 0.9 if state == "returning" else 0.6))
        elif m.get("gather_done"):
            out.append(MarchTimer(i, "march", float(m["gather_done"]), "ocr", 0.4))
    return out
