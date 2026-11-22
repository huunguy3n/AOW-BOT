"""Metrics nhan dien: khop du doan voi nhan theo IoU, P/R/F1 theo lop, FPR tren negative, confusion, do tre.

Thuan. Moi du doan la (lop, bbox, do tin cay); bo nhan dien nao cung quy ve dang nay de so sanh cu vs moi.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from .dataset import Annotation, Box, Sample

BACKGROUND = "<none>"


@dataclass(frozen=True)
class Prediction:
    cls: str
    box: Box
    score: float = 1.0


def iou(a: Box, b: Box) -> float:
    x1, y1 = max(a.x, b.x), max(a.y, b.y)
    x2, y2 = min(a.x + a.w, b.x + b.w), min(a.y + a.h, b.y + b.h)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union else 0.0


@dataclass(frozen=True)
class ClassStats:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    neg_samples: int = 0     # so anh negative cua lop (anh day du nhan, khong co lop)
    neg_fired: int = 0       # trong do co du doan lop nay

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        return None if p is None or r is None or p + r == 0 else 2 * p * r / (p + r)

    @property
    def fpr(self) -> float | None:
        return self.neg_fired / self.neg_samples if self.neg_samples else None


@dataclass(frozen=True)
class Report:
    per_class: Mapping[str, ClassStats]
    confusion: Mapping[str, Mapping[str, int]]   # confusion[nhan][du_doan]; BACKGROUND = khong co
    n_samples: int

    def macro(self, name: str) -> float | None:
        vals = [getattr(s, name) for s in self.per_class.values() if getattr(s, name) is not None]
        return sum(vals) / len(vals) if vals else None


def _match(gts: Sequence[Annotation], ps: Sequence[Prediction], iou_th: float) -> tuple[set[int], list[Prediction]]:
    used: set[int] = set()
    unmatched: list[Prediction] = []
    for p in ps:
        best, bi = 0.0, -1
        for i, g in enumerate(gts):
            if i not in used and g.cls == p.cls:
                v = iou(p.box, g.box)
                if v > best:
                    best, bi = v, i
        if bi >= 0 and best >= iou_th:
            used.add(bi)
        else:
            unmatched.append(p)
    return used, unmatched


@dataclass
class _Tally:
    acc: dict[str, dict[str, int]]
    conf: dict[str, dict[str, int]]


def _eval_sample(s: Sample, ps: Sequence[Prediction], classes: Sequence[str], iou_th: float, t: _Tally) -> None:
    acc, conf = t.acc, t.conf
    gts = [a for a in s.annotations if a.visible]
    ps = sorted(ps, key=lambda p: -p.score)
    used, unmatched = _match(gts, ps, iou_th)
    for i in used:
        acc[gts[i].cls]["tp"] += 1
        conf[gts[i].cls][gts[i].cls] += 1
    for p in unmatched:
        hit = next((g for g in gts if g.cls != p.cls and iou(p.box, g.box) >= iou_th), None)
        if p.cls in acc:
            acc[p.cls]["fp"] += 1
        conf[hit.cls if hit else BACKGROUND][p.cls] += 1
    for i, g in enumerate(gts):
        if i not in used:
            acc[g.cls]["fn"] += 1
            if not any(iou(p.box, g.box) >= iou_th for p in unmatched):
                conf[g.cls][BACKGROUND] += 1
    if s.complete:
        present = {a.cls for a in s.annotations}
        fired = {p.cls for p in ps}
        for c in classes:
            if c not in present:
                acc[c]["neg_samples"] += 1
                acc[c]["neg_fired"] += int(c in fired)


def evaluate(samples: Sequence[Sample], preds: Mapping[str, Sequence[Prediction]], classes: Iterable[str],
             iou_th: float = 0.5) -> Report:
    """preds: id mau -> du doan. Khop tham lam theo diem giam dan, chi cung lop, IoU >= iou_th.
    Du doan thua chong len nhan KHAC lop -> confusion[nhan][du doan]; con lai -> confusion[BACKGROUND][du doan]."""
    cls = tuple(classes)
    t = _Tally({c: defaultdict(int) for c in cls}, defaultdict(lambda: defaultdict(int)))
    for s in samples:
        _eval_sample(s, preds.get(s.id, ()), cls, iou_th, t)
    acc, conf = t.acc, t.conf
    per = {c: ClassStats(acc[c]["tp"], acc[c]["fp"], acc[c]["fn"], acc[c]["neg_samples"], acc[c]["neg_fired"])
           for c in cls}
    return Report(per, {k: dict(v) for k, v in conf.items()}, len(samples))


def percentile(values: Sequence[float], q: float) -> float | None:
    """Nearest-rank (khong noi suy) -> p50/p95 tai lap duoc."""
    if not values:
        return None
    s = sorted(values)
    return s[max(0, min(len(s) - 1, math.ceil(q / 100 * len(s)) - 1))]


def latency(values_ms: Sequence[float]) -> dict[str, float | None]:
    return {"n": float(len(values_ms)), "p50": percentile(values_ms, 50), "p95": percentile(values_ms, 95)}


def compare(old: Report, new: Report) -> dict[str, dict[str, float | None]]:
    """Chenh lech moi - cu theo lop (precision/recall/f1/fpr); None neu mot ben khong do duoc."""
    def d(a: float | None, b: float | None) -> float | None:
        return None if a is None or b is None else b - a
    return {c: {k: d(getattr(old.per_class[c], k), getattr(new.per_class[c], k))
                for k in ("precision", "recall", "f1", "fpr")}
            for c in old.per_class if c in new.per_class}
