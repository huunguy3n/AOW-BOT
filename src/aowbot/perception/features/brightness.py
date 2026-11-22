"""Dac trung do sang: thong ke xam, luoi cuc bo, thay doi giua 2 khung (toan cuc hay cuc bo).

`detect_change` phan biet 3 nguyen nhan khien 2 khung khac nhau:
  - doi anh sang TOAN CUC (trung vi chenh lech lech khoi 0): khong co vat the nao doi.
  - doi CUC BO (ti le diem lech khoi nen > min_area): vat the/hieu ung/hoat anh.
  - chi nhieu (ca hai deu khong).
Nguong thich nghi: nguong cuc bo = k * san_nhieu; san_nhieu = do lech chuan ben vung cua phan du sau khi bu
mo hinh sang toan cuc cur ~ a*prev + b (gain + bias), san toi thieu = 1 muc xam (luong tu hoa anh 8-bit).
k va min_area la tham so cua nguoi goi; gia tri dung duoc kiem bang benchmark (tools/perception_phase2_bench.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

import cv2
import numpy as np
from numpy.typing import NDArray

from ..core.frame import U8

F32 = NDArray[np.float32]
QUANT_FLOOR = 1.0       # 1 muc xam: nho hon khong the phan biet trong anh uint8
SAT_HI, SAT_LO = 254.0, 1.0   # diem bao hoa cua anh 8-bit
GAIN_TOL = 0.03         # |gain - 1| nho hon: coi nhu khong doi ty le
P90_SPAN = 3.29         # (p95 - p5) / sigma cua phan phoi chuan


@dataclass(frozen=True)
class BrightnessStats:
    mean: float
    std: float
    p5: float
    p50: float
    p95: float


def stats(gray: U8) -> BrightnessStats:
    if gray.size == 0:
        raise ValueError("vung rong")
    p5, p50, p95 = np.percentile(gray, [5, 50, 95])
    return BrightnessStats(float(gray.mean()), float(gray.std()), float(p5), float(p50), float(p95))


def grid_means(gray: U8, rows: int, cols: int) -> F32:
    """Do sang trung binh moi o luoi rows x cols (thong ke cuc bo re, khong cua so truot)."""
    if rows < 1 or cols < 1:
        raise ValueError("rows/cols >= 1")
    return np.asarray(cv2.resize(gray.astype(np.float32), (cols, rows), interpolation=cv2.INTER_AREA), np.float32)


@dataclass(frozen=True)
class BrightnessChange:
    direction: Literal["brighter", "darker", "none"]   # theo dich chuyen toan cuc (trung vi chenh lech)
    global_shift: bool
    shift: float             # trung vi chenh lech (muc xam, co dau)
    gain: float              # he so a trong cur ~ a*prev + b (1.0 = khong doi ty le)
    bias: float              # b
    noise: float             # san nhieu cua phan du sau khi bu doi sang toan cuc (muc xam)
    local_fraction: float    # ti le diem lech khoi mo hinh toan cuc > k * noise
    local: bool


IQR_SPAN = 1.349        # IQR / sigma cua phan phoi chuan (chiu duoc toi 25 % diem lech)


def _sigma_iqr(r: F32) -> float:
    q1, q3 = np.percentile(r, [25, 75])
    return float(q3 - q1) / IQR_SPAN


def _sigma(r: F32) -> float:
    """Do lech chuan ben vung tu (p95 - p5) / 3,29. Khong dung MAD: tren so nguyen trung vi |chenh lech| bi lam
    tron xuong -> danh gia thap nhieu (do 2026-11-22: nhieu sigma=2 -> MAD cho 1,48)."""
    p5, p95 = np.percentile(r, [5, 95])
    return float(p95 - p5) / P90_SPAN


def _fit_affine(cur: F32, prev: F32, iters: int = 3, step: int = 4) -> tuple[float, float]:
    """Hoi quy ben vung cur ~ a*prev + b. Khoi dau a=1, b=trung vi chenh lech (khong dung binh phuong toi thieu
    tren tat ca: vung doi lon se keo mo hinh); sigma khoi dau bang IQR; moi vong bo diem lech > 3 sigma roi khop lai."""
    x, y = prev[::step, ::step].ravel(), cur[::step, ::step].ravel()
    a, b = 1.0, float(np.median(y - x))
    sig = max(_sigma_iqr(y - (a * x + b)), QUANT_FLOOR)
    for _ in range(iters):
        keep = np.abs(y - (a * x + b)) <= 3 * sig
        if keep.sum() < 2 or np.ptp(x[keep]) == 0:
            break
        a, b = (float(v) for v in np.polyfit(x[keep], y[keep], 1))
        sig = max(_sigma(y[keep] - (a * x[keep] + b)), QUANT_FLOOR)
    return a, b


def _transfer(cur: F32, prev: F32, bins: int = 32, step: int = 2, min_px: int = 50) -> F32:
    """Ham chuyen cuong do sang cur ~ f(prev) = prev + d(prev), d = trung vi cua (cur - prev) trong moi nhom cuong do
    cua prev, noi suy tuyen tinh (noi suy do lech d thay vi f: chinh xac tuyet doi voi bias, gan dung voi gain).
    Bu duoc gain, bias, gamma VA bao hoa 0/255 (mo hinh affine khong bu duoc bao hoa: do 2026-11-22); trung vi
    ben vung voi vung doi cuc bo < 50 % moi nhom."""
    x, y = prev[::step, ::step].ravel(), cur[::step, ::step].ravel()
    idx = np.minimum((x * (bins / 256.0)).astype(np.int32), bins - 1)
    xs, ys = [], []
    for b in range(bins):
        m = idx == b
        if int(m.sum()) >= min_px:
            xs.append(float(x[m].mean()))
            ys.append(float(np.median(y[m] - x[m])))
    if len(xs) < 2:
        return cast(F32, prev + float(np.median(y - x)))
    return cast(F32, (prev + np.interp(prev, xs, ys)).astype(np.float32))


def change_mask(
    cur: U8, prev: U8, k: float = 4.0, min_area: float = 0.01,
) -> tuple[NDArray[np.bool_], BrightnessChange]:
    """Mat na diem thay doi CUC BO (sau khi bu sang toan cuc) + tom tat. Dung cho phat hien chuyen dong."""
    if cur.shape != prev.shape or cur.ndim != 2:
        raise ValueError("can 2 anh xam cung kich thuoc")
    if k <= 0 or not 0 < min_area < 1:
        raise ValueError("k > 0 va 0 < min_area < 1")
    c, p = cur.astype(np.float32), prev.astype(np.float32)
    shift = float(np.median(c - p))
    a, b = _fit_affine(c, p)            # chi de BAO CAO gain/bias; phan du tinh bang ham chuyen cuong do
    resid = c - _transfer(c, p)
    dev = np.abs(resid - np.median(resid))
    inl = dev <= 3 * max(_sigma_iqr(resid), QUANT_FLOOR)   # san nhieu chi tu diem khop mo hinh
    noise = max(_sigma(resid[inl]), QUANT_FLOOR)
    mask = dev > k * noise
    g = abs(shift) > QUANT_FLOOR
    if g or abs(a - 1.0) > GAIN_TOL:
        # co doi sang toan cuc: diem bao hoa (0/255) o 1 trong 2 khung khong the quy doi -> mo ho, bo khoi mat na
        mask &= ~((p >= SAT_HI) | (c >= SAT_HI) | (p <= SAT_LO) | (c <= SAT_LO))
    frac = float(mask.mean())
    direction: Literal["brighter", "darker", "none"] = "none"
    if g:
        direction = "brighter" if shift > 0 else "darker"
    return mask, BrightnessChange(direction, g, shift, a, b, noise, frac, frac >= min_area)


def detect_change(cur: U8, prev: U8, k: float = 4.0, min_area: float = 0.01) -> BrightnessChange:
    return change_mask(cur, prev, k, min_area)[1]
