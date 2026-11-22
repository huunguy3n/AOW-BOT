"""Phat hien hinh: nhi phan -> hinh thai hoc -> thanh phan lien thong / contour -> bbox.

Dung cho vat the dac trung bang mau/hinh khoi (cham do, bong bong, vong tron), khong can mau anh.
Moi tham so nam trong ShapeParams va duoc ghi vao Evidence; khong co gia tri nao duoc hieu chuan tu dau.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

from ..contract import Detection, Evidence, Status
from ..core.frame import U8, as_u8
from ..eval.dataset import Box

DETECTOR = "shape"


@dataclass(frozen=True)
class ShapeParams:
    method: Literal["otsu", "adaptive", "fixed"] = "otsu"
    fixed: int = 128                 # chi dung khi method = "fixed"
    block: int = 31                  # cua so adaptive (le)
    offset: int = 5                  # hang so tru cua adaptive
    open_k: int = 0                  # nhan mo (khu nhieu), 0 = bo qua
    close_k: int = 0                 # nhan dong (lap lo), 0 = bo qua
    min_area: int = 16
    max_area: int = 0                # 0 = khong gioi han


@dataclass(frozen=True)
class Blob:
    box: Box
    area: int
    fill: float                      # dien tich / dien tich bbox
    circularity: float               # 4*pi*A / P^2 (1 = tron)


def binarize(gray: U8, p: ShapeParams) -> U8:
    if p.method == "otsu":
        return as_u8(cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1])
    if p.method == "adaptive":
        return as_u8(cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
                                           p.block, p.offset))
    return as_u8(cv2.threshold(gray, p.fixed, 255, cv2.THRESH_BINARY)[1])


def clean(mask: U8, p: ShapeParams) -> U8:
    out = mask
    if p.open_k:
        out = as_u8(cv2.morphologyEx(out, cv2.MORPH_OPEN, np.ones((p.open_k, p.open_k), np.uint8)))
    if p.close_k:
        out = as_u8(cv2.morphologyEx(out, cv2.MORPH_CLOSE, np.ones((p.close_k, p.close_k), np.uint8)))
    return out


def blobs(mask: U8, p: ShapeParams) -> list[Blob]:
    """Thanh phan lien thong 8-lang gieng cua mask (>0) + dac trung hinh dang qua contour ngoai."""
    n, labels, st, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), connectivity=8)
    out: list[Blob] = []
    for i in range(1, n):
        x, y, w, h, a = (int(v) for v in st[i])
        if a < p.min_area or (p.max_area and a > p.max_area):
            continue
        crop = (labels[y:y + h, x:x + w] == i).astype(np.uint8)
        cnts, _ = cv2.findContours(crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        per = max((cv2.arcLength(c, True) for c in cnts), default=0.0)
        circ = float(4 * np.pi * a / (per * per)) if per > 0 else 0.0
        out.append(Blob(Box(x, y, w, h), a, a / (w * h), min(circ, 1.0)))
    return out


def detect_shapes(gray: U8, cls: str, p: ShapeParams, instance: str = "") -> list[Detection]:
    """Moi blob -> Detection UNCERTAIN, dac trung (area/fill/circularity) trong features, tham so trong Evidence."""
    ev_params = {"method": p.method, "min_area": float(p.min_area),
                 "open_k": float(p.open_k), "close_k": float(p.close_k)}
    out = []
    for b in blobs(clean(binarize(gray, p), p), p):
        ev = Evidence(DETECTOR, None, "connected components", {**ev_params, "src": instance})
        out.append(Detection(cls, b.box, Status.UNCERTAIN, (ev,),
                             features={"area": float(b.area), "fill": b.fill, "circularity": b.circularity}))
    return out
