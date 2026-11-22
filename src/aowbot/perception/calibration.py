"""Hieu chuan diem tho -> xac suat (hoi quy logistic) va hop nhat nhieu detector (stacking). Thuan numpy.

Nguon hieu chuan hien tai la BENCHMARK TONG HOP (neo that + bien doi + vung vang mat inpaint), khong phai nhan nguoi:
moi he so mang theo `source`, `n_pos`, `n_neg` de nguoi doc biet no do tu dau. Khong du lieu nguoi -> khong tuyen bo
"xac suat that"; chi la thang do so sanh duoc giua detector.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]
_EPS = 1e-6


def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def logit(p: float) -> float:
    p = min(max(p, _EPS), 1 - _EPS)
    return math.log(p / (1 - p))


def fit_logistic(x: F64, y: NDArray[np.int_], l2: float = 1e-3, iters: int = 50) -> tuple[F64, int]:
    """IRLS cho P(y=1|x) = sigmoid(x @ w) (x co cot 1 cho he so chan) -> (w, so vong).
    l2 nho chong phan ky khi du lieu tach tuyen tinh."""
    if x.ndim != 2 or len(x) != len(y):
        raise ValueError("x phai 2 chieu va cung so hang voi y")
    if y.min() == y.max():
        raise ValueError("can ca mau duong va am")
    w = np.zeros(x.shape[1])
    reg = np.eye(x.shape[1]) * l2
    reg[0, 0] = 0.0          # khong phat he so chan
    for it in range(1, iters + 1):
        z = np.clip(x @ w, -30, 30)
        p = 1 / (1 + np.exp(-z))
        g = x.T @ (p - y) + reg @ w
        h = (x * (p * (1 - p))[:, None]).T @ x + reg + np.eye(x.shape[1]) * 1e-9
        step = np.linalg.solve(h, g)
        w = w - step
        if float(np.abs(step).max()) < 1e-8:
            return w, it
    return w, iters


@dataclass(frozen=True)
class Calibrator:
    """p = sigmoid(a * score + b) cho MOT detector."""

    detector: str
    a: float
    b: float
    source: str
    n_pos: int
    n_neg: int

    def prob(self, score: float) -> float:
        return sigmoid(self.a * score + self.b)


def fit_calibrator(detector: str, scores: Sequence[float], labels: Sequence[int], source: str) -> Calibrator:
    s = np.asarray(scores, float)
    y = np.asarray(labels, int)
    # chuan hoa de IRLS on dinh roi quy ve thang goc
    mu, sd = float(s.mean()), float(s.std()) or 1.0
    w, _ = fit_logistic(np.column_stack([np.ones_like(s), (s - mu) / sd]), y)
    a = float(w[1] / sd)
    return Calibrator(detector, a, float(w[0] - a * mu), source, int((y == 1).sum()), int((y == 0).sum()))


@dataclass(frozen=True)
class FusionModel:
    """logit(p_fused) = bias + sum_d weight_d * logit(p_d), chi qua detector CO MAT (thieu = 0, khong am)."""

    weights: Mapping[str, float]
    bias: float
    source: str
    n_pos: int
    n_neg: int
    calibrators: Mapping[str, Calibrator] = field(default_factory=lambda: MappingProxyType({}))
    thresholds: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))   # confirm_p / reject_p

    def fused(self, probs: Mapping[str, float]) -> float:
        z = self.bias + sum(self.weights.get(d, 0.0) * logit(p) for d, p in probs.items())
        return sigmoid(z)

    def to_json(self) -> str:
        return json.dumps({
            "weights": dict(self.weights), "bias": self.bias, "source": self.source,
            "n_pos": self.n_pos, "n_neg": self.n_neg,
            "calibrators": {k: vars(c) for k, c in self.calibrators.items()},
            "thresholds": dict(self.thresholds)}, indent=1)

    @staticmethod
    def from_json(text: str) -> FusionModel:
        d: dict[str, Any] = json.loads(text)
        cals = {k: Calibrator(**v) for k, v in d["calibrators"].items()}
        return FusionModel(d["weights"], d["bias"], d["source"], d["n_pos"], d["n_neg"], cals, d.get("thresholds", {}))


def fit_fusion(rows: Sequence[Mapping[str, float]], labels: Sequence[int], detectors: Sequence[str],
               source: str) -> tuple[Mapping[str, float], float]:
    """rows: moi hang = {detector: p_hieu_chuan} (detector vang mat khong co khoa). -> (trong so, he so chan)."""
    x = np.array([[1.0] + [logit(r[d]) if d in r else 0.0 for d in detectors] for r in rows])
    w, _ = fit_logistic(x, np.asarray(labels, int))
    return {d: float(w[i + 1]) for i, d in enumerate(detectors)}, float(w[0])


def expected_calibration_error(p: Sequence[float], y: Sequence[int], bins: int = 10) -> float:
    pa, ya = np.asarray(p, float), np.asarray(y, float)
    idx = np.minimum((pa * bins).astype(int), bins - 1)
    ece = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            ece += float(m.mean()) * abs(float(pa[m].mean()) - float(ya[m].mean()))
    return ece
