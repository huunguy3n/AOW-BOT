"""M2-3 (lo trinh ML, chu du an 2026-11-28): gia tri moi buoc trong luot ghe tu lich su chay (bang runs).

Ham thuan. Moi buoc: so lan chay, ti le "lam duoc viec" (ret khac 0 / rong), phut trung binh, va gia tri = ti le lam
duoc viec / phut. De xuat thu tu = buoc gia tri cao truoc, NHUNG giu cac buoc bat buoc o vi tri luat cung
(warday / shield dau luot, gather + observe cuoi luot - P7-1, CLAUDE.md).

CHE DO BONG: chi tinh va hien tren web / report de so voi ORDER hien tai; runner KHONG doi thu tu. Bat thu tu dong can
chu du an duyet rieng (docs/strategy/ml-roadmap.md M2-3).
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

FIRST = ("warday", "shield", "tutorial")       # luat cung: dau luot
LAST = ("gather", "observe")                   # luat cung: cuoi luot (gather cuoi moi ngay - P7-1)
MIN_RUNS = 5


@dataclass(frozen=True, slots=True)
class StepValue:
    step: str
    runs: int
    work_rate: float      # 0..1
    mean_min: float
    value: float          # lan lam duoc viec / phut chay

    def as_dict(self) -> dict:
        return {"step": self.step, "runs": self.runs, "work_rate": round(self.work_rate, 3),
                "mean_min": round(self.mean_min, 2), "value": round(self.value, 3)}


def did_work(ret: object) -> bool:
    """ret cua runs: so / chuoi. 0, '0', rong, None, 'skip' -> khong lam duoc viec."""
    if ret is None:
        return False
    s = str(ret).strip().lower()
    if s in ("", "0", "none", "false", "skip", "skipped", "0.0"):
        return False
    try:
        return float(s) > 0
    except ValueError:
        return True


def values(rows: Iterable[tuple[str, float | None, object]], min_runs: int = MIN_RUNS) -> list[StepValue]:
    """rows: (buoc, thoi gian giay, ret). -> StepValue cho buoc co >= min_runs lan, gia tri giam dan."""
    acc: dict[str, list[float]] = {}
    for step, dur, ret in rows:
        if not step or step.startswith("_"):
            continue
        a = acc.setdefault(step, [0, 0, 0.0])
        a[0] += 1
        a[1] += did_work(ret)
        a[2] += max(0.0, float(dur or 0.0))
    out = []
    for step, (n, w, d) in acc.items():
        if n < min_runs:
            continue
        mean_min = d / n / 60.0
        rate = w / n
        out.append(StepValue(step, int(n), rate, mean_min, rate / max(mean_min, 0.05)))
    return sorted(out, key=lambda v: -v.value)


def suggest_order(current: Sequence[str], vals: Sequence[StepValue]) -> list[str]:
    """Thu tu de xuat: FIRST (theo ORDER hien tai) -> cac buoc khac theo gia tri (buoc chua du du lieu giu vi tri tuong
    doi cuoi nhom giua) -> LAST. Chi gom cac buoc co trong `current`."""
    val = {v.step: v.value for v in vals}
    first = [s for s in current if s in FIRST]
    last = [s for s in current if s in LAST]
    mid = [s for s in current if s not in FIRST and s not in LAST]
    known = sorted((s for s in mid if s in val), key=lambda s: -val[s])
    unknown = [s for s in mid if s not in val]
    return first + known + unknown + last
