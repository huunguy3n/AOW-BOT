"""Dac trung tuong phan: do lech chuan cuc bo, mat do bien (Canny), nang luong Sobel.

Tham so (cua so, nguong Canny) do nguoi goi truyen vao; chua co gia tri nao duoc hieu chuan bang benchmark,
nen khong co mac dinh nao duoc dung de RA QUYET DINH nhan dien.
"""
from __future__ import annotations

from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray

from ..core.frame import U8, as_u8

F32 = NDArray[np.float32]


def local_std(gray: U8, window: int) -> F32:
    """Do lech chuan cuc bo = sqrt(E[x^2] - E[x]^2) tren cua so vuong `window` x `window`."""
    if window < 3 or window % 2 == 0:
        raise ValueError("window phai le va >= 3")
    g = gray.astype(np.float32)
    k = (window, window)
    mean = cv2.blur(g, k)
    var = cv2.blur(g * g, k) - mean * mean
    return cast(F32, np.sqrt(np.maximum(var, 0.0)))


def sobel_magnitude(gray: U8) -> F32:
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return cast(F32, cv2.magnitude(gx, gy))


def canny_edges(gray: U8, low: int, high: int) -> U8:
    if not 0 <= low < high <= 255:
        raise ValueError("can 0 <= low < high <= 255")
    return as_u8(cv2.Canny(gray, low, high))


def edge_density(gray: U8, low: int, high: int) -> float:
    """Ti le diem bien Canny trong vung (0..1)."""
    if gray.size == 0:
        raise ValueError("vung rong")
    return float(np.count_nonzero(canny_edges(gray, low, high))) / gray.size


def contrast_summary(gray: U8, window: int, low: int, high: int) -> dict[str, float]:
    """Tom tat 1 vung: de ghi vao Detection.features (diem dac trung, khong phai diem nhan dien)."""
    ls: Any = local_std(gray, window)
    return {
        "local_std_mean": float(ls.mean()),
        "sobel_mean": float(sobel_magnitude(gray).mean()),
        "edge_density": edge_density(gray, low, high),
        "rms_contrast": float(gray.std()),
    }
