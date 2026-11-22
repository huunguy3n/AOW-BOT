"""ORBDetector: dac trung cuc bo (ORB + ty le Lowe + RANSAC affine tu dong dang) cho vat bi che / lech ty le.

Chi hop voi mau co du diem dac trung: `applicable(tpl)` False (it diem) -> KHONG chay, khong tra loi "khong thay".
Diem tho = so inlier RANSAC. Tham so (ratio, min_inliers) do bang benchmark Phase 3, khong dat tuy y.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..contract import Detection, Evidence, Status
from ..core.frame import ImageFrame
from ..eval.dataset import Box

DETECTOR = "orb"


@dataclass(frozen=True)
class OrbParams:
    nfeatures: int = 2000        # 500 (OpenCV) bo sot vat ro tren ca khung (do 2026-11-22)
    edge_threshold: int = 15     # mac dinh OpenCV la 31: loat het diem cua mau <60 px (66 % mau cua bot nho hon 40 px)
    patch_size: int = 15
    ratio: float = 0.75          # ty le Lowe (gia tri kinh dien cua tai lieu SIFT; kiem lai o benchmark)
    min_keypoints: int = 12      # mau it diem hon -> khong ap dung
    min_inliers: int = 6         # do Phase 3: 6 cho retention cao nhat, vang mat 0/32 bao nham (mau nho, can kiem lai)


class OrbDetector:
    def __init__(self, p: OrbParams | None = None) -> None:
        self.p = p or OrbParams()
        p = self.p
        self._orb = cv2.ORB_create(  # type: ignore[attr-defined]
            nfeatures=p.nfeatures, edgeThreshold=p.edge_threshold, patchSize=p.patch_size)
        self._bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        self._cache: dict[str, tuple[list[cv2.KeyPoint], np.ndarray | None]] = {}

    def _features(self, name: str, gray: np.ndarray) -> tuple[list[cv2.KeyPoint], np.ndarray | None]:
        if name not in self._cache:
            kp, des = self._orb.detectAndCompute(gray, None)
            self._cache[name] = (list(kp), des)
        return self._cache[name]

    def applicable(self, name: str, tpl: np.ndarray) -> bool:
        kp, des = self._features(name, cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY))
        return des is not None and len(kp) >= self.p.min_keypoints

    def detect(self, frame: ImageFrame, name: str, tpl: np.ndarray, roi: Box | None = None) -> Detection | None:
        tk, td = self._features(name, cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY))
        if td is None or len(tk) < self.p.min_keypoints:
            return None
        ox, oy = (roi.x, roi.y) if roi else (0, 0)
        gray = frame.gray[roi.y:roi.y + roi.h, roi.x:roi.x + roi.w] if roi else frame.gray
        fk, fd = self._orb.detectAndCompute(gray, None)
        if fd is None or len(fk) < 4:
            return None
        pairs = self._bf.knnMatch(td, fd, k=2)
        good = [m[0] for m in pairs if len(m) == 2 and m[0].distance < self.p.ratio * m[1].distance]
        if len(good) < 4:
            return None
        src = np.array([tk[m.queryIdx].pt for m in good], np.float32).reshape(-1, 1, 2)
        dst = np.array([fk[m.trainIdx].pt for m in good], np.float32).reshape(-1, 1, 2)
        mat, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0)
        n = 0 if mat is None or inl is None else int(inl.sum())
        if mat is None or n < self.p.min_inliers:
            return None
        h, w = tpl.shape[:2]
        corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32).reshape(-1, 1, 2)
        pts = cv2.transform(corners, mat).reshape(-1, 2)
        x0, y0 = pts.min(0)
        x1, y1 = pts.max(0)
        box = Box(int(ox + x0), int(oy + y0), max(1, int(x1 - x0)), max(1, int(y1 - y0)))
        ev = Evidence(DETECTOR, float(n), "inliers RANSAC affine",
                      {"matches": len(good), "ratio": self.p.ratio, "frame": str(frame.frame_id)})
        return Detection(name, box, Status.UNCERTAIN, (ev,))
