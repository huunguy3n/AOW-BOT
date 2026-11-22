"""TemplateDetector: khop mau TM_CCOEFF_NORMED da ty le, ROI-first, co cac tuy chon tang toc DO BANG BENCHMARK.

Do Phase 2 (docs/perception/PHASE2_RESULTS.md): da ty le 0,90-1,10 giu retention 1,00 khi anh lech ty le +-10 %
(legacy 0,17-0,47); CLAHE/Sobel lam te hon -> KHONG tien xu ly do sang/tuong phan. Phase 6 (PHASE6_RESULTS.md):
tuy chon tang toc (xam, it ty le, tho->min, thoat som) duoc chon theo retention/FP/do tre.

Detector chi bao CUNG co/khong va diem tho (Evidence). Status luon UNCERTAIN, confidence None: ket luan
(Confirmed / NotDetected) thuoc ve tang hop nhat + hieu chuan, khong thuoc detector.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import cv2
import numpy as np

from ..contract import Detection, Evidence, Status
from ..core.frame import ImageFrame
from ..eval.dataset import Box

DETECTOR = "template_ms"
SCALES_9 = (0.90, 0.925, 0.95, 0.975, 1.0, 1.025, 1.05, 1.075, 1.10)    # do o Phase 2
SCALES_5 = (0.90, 0.95, 1.0, 1.05, 1.10)
DEFAULT_SCALES = SCALES_9


@dataclass(frozen=True)
class TemplateParams:
    scales: tuple[float, ...] = DEFAULT_SCALES
    gray: bool = True               # tim tren anh xam (~3 lan re) roi XAC MINH MAU bang BGR tai cho tim thay
    verify_tol: float = 0.10        # BGR thap hon xam qua muc nay (khac mau) -> tim lai bang BGR day du
    early_exit: float | None = 0.95   # diem o ty le 1,0 >= nguong thi bo qua ty le khac (Phase 6: 310 -> 11 ms)
    coarse: int = 1                 # >1: tim thuc o do phan giai giam `coarse` lan roi tinh chinh o do phan giai goc
    coarse_min_side: int = 40       # chi ap dung coarse khi canh nho cua mau >= gia tri nay


class TemplateDetector:
    def __init__(self, scales: tuple[float, ...] | None = None, params: TemplateParams | None = None) -> None:
        self.p = params or TemplateParams()
        if scales is not None:
            self.p = replace(self.p, scales=scales)
        if not self.p.scales or min(self.p.scales) <= 0 or self.p.coarse < 1:
            raise ValueError("scales phai khong rong va > 0; coarse >= 1")
        self.scales = self.p.scales
        self._bgr = self if not self.p.gray else TemplateDetector(params=replace(self.p, gray=False))

    def _gray_then_verify(self, frame: ImageFrame, name: str, tpl: np.ndarray, roi: Box | None) -> Detection | None:
        """Tim nhanh tren anh xam, roi tinh diem BGR TAI CHO do. Xam bo qua mau nen nut khac mau (X xanh vs X do,
        mui ten kem vs xam) khop xam ~0,93 ma BGR ~0,72 (shadow offline 2026-11-22). BGR thap hon xam > verify_tol
        -> khong tin cho xam, tim lai BGR day du trong ROI."""
        ox, oy = (roi.x, roi.y) if roi else (0, 0)
        area = frame.gray[roi.y:roi.y + roi.h, roi.x:roi.x + roi.w] if roi else frame.gray
        best = self._search(area, cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY))
        if best is None:
            return None
        g_score, (lx, ly), (w, h), s = best
        bgr_area = frame.crop(roi) if roi else frame.bgr
        x0, y0 = max(0, lx - 2), max(0, ly - 2)
        win = bgr_area[y0:ly + h + 2, x0:lx + w + 2]
        t = self._resize(tpl, s)
        if win.shape[0] >= t.shape[0] and win.shape[1] >= t.shape[1]:
            b_score, (fx, fy) = self._match(win, t)
            if b_score >= g_score - self.p.verify_tol:
                ev = Evidence(DETECTOR, b_score, "TM_CCOEFF_NORMED BGR (tim xam, xac minh mau)",
                              {"scale": s, "gray_score": g_score, "frame": str(frame.frame_id)})
                return Detection(name, Box(ox + x0 + fx, oy + y0 + fy, w, h), Status.UNCERTAIN, (ev,))
        return self._bgr.detect(frame, name, tpl, roi)

    @staticmethod
    def _resize(a: np.ndarray, s: float) -> np.ndarray:
        return a if s == 1.0 else cv2.resize(a, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)

    def _match(self, area: np.ndarray, t: np.ndarray) -> tuple[float, tuple[int, int]]:
        _, mx, _, loc = cv2.minMaxLoc(cv2.matchTemplate(area, t, cv2.TM_CCOEFF_NORMED))
        return float(mx), (int(loc[0]), int(loc[1]))

    def detect(self, frame: ImageFrame, name: str, tpl: np.ndarray, roi: Box | None = None) -> Detection | None:
        """Khop tot nhat trong roi (hoac ca khung). None = khong khop duoc o ty le nao (mau lon hon vung tim)."""
        if tpl.dtype != np.uint8 or tpl.ndim != 3:
            raise ValueError("mau phai la uint8 HxWx3 (BGR)")
        ox, oy = (roi.x, roi.y) if roi else (0, 0)
        if self.p.gray:
            return self._gray_then_verify(frame, name, tpl, roi)
        area = frame.crop(roi) if roi else frame.bgr
        best = self._search(area, tpl)
        if best is None:
            return None
        score, loc, (w, h), s = best
        ev = Evidence(DETECTOR, score, "TM_CCOEFF_NORMED " + ("xam" if self.p.gray else "BGR"),
                      {"scale": s, "frame": str(frame.frame_id), "coarse": float(self.p.coarse)})
        return Detection(name, Box(ox + loc[0], oy + loc[1], w, h), Status.UNCERTAIN, (ev,))

    def _search(
        self, area: np.ndarray, tpl: np.ndarray,
    ) -> tuple[float, tuple[int, int], tuple[int, int], float] | None:
        c = self.p.coarse if min(tpl.shape[:2]) >= self.p.coarse_min_side else 1
        if c > 1:
            return self._coarse_to_fine(area, tpl, c)
        order = sorted(self.scales, key=lambda s: abs(s - 1.0))        # thu ty le 1,0 truoc de thoat som
        best: tuple[float, tuple[int, int], tuple[int, int], float] | None = None
        for s in order:
            t = self._resize(tpl, s)
            if area.shape[0] < t.shape[0] or area.shape[1] < t.shape[1]:
                continue
            mx, loc = self._match(area, t)
            if best is None or mx > best[0]:
                best = (mx, loc, (t.shape[1], t.shape[0]), s)
            if self.p.early_exit is not None and s == 1.0 and mx >= self.p.early_exit:
                break
        return best

    def _coarse_to_fine(self, area: np.ndarray, tpl: np.ndarray, c: int
                        ) -> tuple[float, tuple[int, int], tuple[int, int], float] | None:
        """Tim tren anh/mau thu nho c lan (moi ty le), roi tinh chinh o do phan giai goc quanh dinh tot nhat."""
        small = cv2.resize(area, None, fx=1.0 / c, fy=1.0 / c, interpolation=cv2.INTER_AREA)
        best_s: tuple[float, tuple[int, int], float] | None = None
        for s in sorted(self.scales, key=lambda v: abs(v - 1.0)):
            t = cv2.resize(tpl, None, fx=s / c, fy=s / c, interpolation=cv2.INTER_AREA)
            if small.shape[0] < t.shape[0] or small.shape[1] < t.shape[1] or min(t.shape[:2]) < 4:
                continue
            mx, loc = self._match(small, t)
            if best_s is None or mx > best_s[0]:
                best_s = (mx, loc, s)
        if best_s is None:
            return None
        _, (lx, ly), s = best_s
        t = self._resize(tpl, s)
        x0, y0 = max(0, lx * c - 2 * c), max(0, ly * c - 2 * c)
        win = area[y0:y0 + t.shape[0] + 4 * c, x0:x0 + t.shape[1] + 4 * c]
        if win.shape[0] < t.shape[0] or win.shape[1] < t.shape[1]:
            return None
        mx, (fx, fy) = self._match(win, t)
        return mx, (x0 + fx, y0 + fy), (t.shape[1], t.shape[0]), s
