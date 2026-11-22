"""RedDotDetector: cham do thong bao (badge) theo mau + hinh, cong tuong duong `bot.badges.red_dots` (bot/ khong duoc
import tu perception) nhung tra ve Detection co bbox, dac trung va tham so de truy vet.

Luat (giong ban cu, do tren man 540x960): mau do tuoi (H<=6 hoac >=172, S>=170, V>=min_v), lap lo so trang ben trong
(dong 3x3), thanh phan lien thong co ban kinh 4-14 px, ti le khung 0,6-1,6, dien tich >= 0,5 khung.
Chi phat hien HINH/MAU; viec cham dau do la quyet dinh cua module game, khong o day.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..contract import Detection, Evidence, Status
from ..core.frame import ImageFrame, as_u8
from ..eval.dataset import Box

DETECTOR = "badge_color"


@dataclass(frozen=True)
class BadgeParams:
    min_r: int = 4
    max_r: int = 14
    min_v: int = 190            # man phu toi (tan thu) can ha xuong ~60
    min_s: int = 170
    hue_lo: int = 6
    hue_hi: int = 172
    close_k: int = 3
    aspect_lo: float = 0.6
    aspect_hi: float = 1.6
    min_fill: float = 0.5


class RedDotDetector:
    def __init__(self, p: BadgeParams | None = None) -> None:
        self.p = p or BadgeParams()

    def detect(self, frame: ImageFrame, roi: Box | None = None, cls: str = "reddot") -> list[Detection]:
        p = self.p
        ox, oy = (roi.x, roi.y) if roi else (0, 0)
        hsv = frame.hsv[roi.y:roi.y + roi.h, roi.x:roi.x + roi.w] if roi else frame.hsv
        h = hsv[..., 0]
        m = (((h <= p.hue_lo) | (h >= p.hue_hi)) & (hsv[..., 1] >= p.min_s) & (hsv[..., 2] >= p.min_v)).astype(np.uint8)
        m = as_u8(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((p.close_k, p.close_k), np.uint8)))
        n, labels, st, _ = cv2.connectedComponentsWithStats(m)
        out: list[Detection] = []
        for i in range(1, n):
            x, y, w, hh, area = (int(v) for v in st[i])
            r = max(w, hh) / 2
            if not (p.min_r <= r <= p.max_r and p.aspect_lo <= w / max(hh, 1) <= p.aspect_hi
                    and area >= p.min_fill * w * hh):
                continue
            cnts, _ = cv2.findContours((labels[y:y + hh, x:x + w] == i).astype(np.uint8), cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
            per = max((cv2.arcLength(c, True) for c in cnts), default=0.0)
            circ = min(1.0, 4 * np.pi * area / (per * per)) if per > 0 else 0.0
            ev = Evidence(DETECTOR, None, "mau do + hinh tron (luat cu)",
                          {"min_v": float(p.min_v), "min_s": float(p.min_s), "frame": str(frame.frame_id)})
            out.append(Detection(cls, Box(ox + x, oy + y, w, hh), Status.UNCERTAIN, (ev,),
                                 features={"area": float(area), "fill": area / (w * hh), "circularity": float(circ),
                                           "radius": float(r)}))
        return out
