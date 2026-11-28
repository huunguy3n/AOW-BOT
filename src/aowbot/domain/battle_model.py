"""M2-2 (lo trinh ML, chu du an 2026-11-28 "tich hop M2"): xac suat thang tran theo ti le luc chien, tung loai tran.

Ham thuan, khong numpy (domain). Hoi quy logistic 1 bien x = ln(ta / dich) cho moi loai tran (campaign, intel, arena,
loot...) tu bang battle_ev (chi dong co ket qua win/lose VA biet ca hai luc chien). Chua du mau -> None.

CHE DO BONG: xac suat chi duoc GHI kem quyet dinh (cot p_win) va hien tren web de do do chuan; KHONG doi quyet
dinh danh / bo cua bot. Bat dung de quyet dinh can chu du an duyet rieng khi du du lieu (docs/strategy/ml-roadmap.md).
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

MIN_N = 20          # can >= N tran co ket qua + hai luc chien moi fit
MIN_EACH = 3        # ... va >= N tran thang, >= N tran thua (khong thi he so tien ra vo cung)


@dataclass(frozen=True, slots=True)
class Model:
    kind: str
    a: float          # chan
    b: float          # he so cua ln(ta/dich)
    n: int
    wins: int

    def p_win(self, ours: float | None, enemy: float | None) -> float | None:
        x = log_ratio(ours, enemy)
        if x is None:
            return None
        z = self.a + self.b * x
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))

    def ratio_for(self, p: float) -> float | None:
        """Ti le ta/dich can de dat xac suat thang p (dung tren web: 'can manh hon dich bao nhieu')."""
        if self.b <= 1e-9 or not 0.0 < p < 1.0:
            return None
        return math.exp((math.log(p / (1.0 - p)) - self.a) / self.b)


def log_ratio(ours: float | None, enemy: float | None) -> float | None:
    if not ours or not enemy or ours <= 0 or enemy <= 0:
        return None
    return math.log(ours / enemy)


def fit_one(kind: str, xs: list[float], ys: list[int], l2: float = 0.1, iters: int = 50) -> Model | None:
    """Newton cho logistic 1 bien co phat L2 nho (on dinh khi du lieu tach roi)."""
    n, wins = len(xs), sum(ys)
    if n < MIN_N or wins < MIN_EACH or n - wins < MIN_EACH:
        return None
    a = b = 0.0
    for _ in range(iters):
        ga, gb = -l2 * a, -l2 * b
        haa, hab, hbb = l2, 0.0, l2
        for x, y in zip(xs, ys, strict=True):
            p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, a + b * x))))
            w = p * (1.0 - p)
            ga += y - p
            gb += (y - p) * x
            haa += w
            hab += w * x
            hbb += w * x * x
        det = haa * hbb - hab * hab
        if abs(det) < 1e-12:
            break
        da, db = (hbb * ga - hab * gb) / det, (haa * gb - hab * ga) / det
        a, b = a + da, b + db
        if abs(da) + abs(db) < 1e-8:
            break
    return Model(kind, a, b, n, wins)


def fit(rows: Iterable[Mapping]) -> dict[str, Model]:
    """rows: dict co kind, ours, enemy, result ('win' | 'lose' | khac). -> {loai: Model} cho loai du mau."""
    data: dict[str, tuple[list[float], list[int]]] = {}
    for r in rows:
        if r.get("result") not in ("win", "lose"):
            continue
        x = log_ratio(r.get("ours"), r.get("enemy"))
        if x is None:
            continue
        xs, ys = data.setdefault(str(r.get("kind")), ([], []))
        xs.append(x)
        ys.append(1 if r["result"] == "win" else 0)
    out = {}
    for k, (xs, ys) in data.items():
        m = fit_one(k, xs, ys)
        if m:
            out[k] = m
    return out


def calibration(rows: Iterable[Mapping], bins: int = 5) -> list[dict]:
    """Do chuan cua p_win da ghi (che do bong): chia theo p, so ti le thang that. -> [{lo, hi, n, p_mean, win_rate}]."""
    b: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for r in rows:
        p = r.get("p_win")
        if p is None or r.get("result") not in ("win", "lose"):
            continue
        b[min(bins - 1, int(float(p) * bins))].append((float(p), 1 if r["result"] == "win" else 0))
    out = []
    for i, cell in enumerate(b):
        if cell:
            out.append({"lo": i / bins, "hi": (i + 1) / bins, "n": len(cell),
                        "p_mean": round(sum(p for p, _ in cell) / len(cell), 3),
                        "win_rate": round(sum(y for _, y in cell) / len(cell), 3)})
    return out
