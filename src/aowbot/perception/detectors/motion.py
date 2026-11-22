"""MotionDetector: chenh lech khung (da bu sang toan cuc) -> hinh thai hoc -> blob -> van toc quang hoc (Farneback).

- Chuyen dong = doi CUC BO so voi mo hinh sang toan cuc, nen nhap nhay anh sang toan man khong tao "chuyen dong".
- ROI-first: co `roi` thi chi xu ly vung do. Optical flow chay tren ban thu nho (`flow_scale`) de re.
- Tham so Farneback la bo gia tri mac dinh cua tai lieu OpenCV (chua hieu chuan cho game nay); ghi vao Evidence.
- Chi bao "co vung doi" + van toc (features vx, vy theo px/khung); khong biet doi tuong la gi (lop = `cls`).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np

from ..contract import Detection, Evidence, Status
from ..core.frame import ImageFrame
from ..eval.dataset import Box
from ..features.brightness import BrightnessChange, change_mask
from .shape import ShapeParams, blobs, clean

DETECTOR = "motion"


@dataclass(frozen=True)
class MotionParams:
    k: float = 4.0                  # nguong lech (so lan san nhieu) - gia tri do o Phase 2
    close_k: int = 7                # lap lo trong vat the di chuyen
    open_k: int = 3                 # khu diem le
    min_area: int = 400             # blob nho hon (px) bi bo (do Phase 4: 40 -> 400 tang MOTA 0,17 -> 0,64 khi sach)
    flow: bool = True
    flow_scale: float = 0.5
    bg_frames: int = 9              # nen = trung vi N khung truoc (bo bong ma); 1 = chi khung truoc


class MotionDetector:
    def __init__(self, p: MotionParams | None = None) -> None:
        self.p = p or MotionParams()

    def _ref(self, prev: ImageFrame, history: Sequence[ImageFrame], roi: Box | None) -> np.ndarray:
        """Anh nen so sanh: trung vi cua `bg_frames` khung gan nhat (neu du >= 3), khong thi khung truoc."""
        frames = [*history][-self.p.bg_frames:] if self.p.bg_frames > 1 else []
        if len(frames) < 3:
            frames = [prev]
        gs = [f.gray[roi.y:roi.y + roi.h, roi.x:roi.x + roi.w] if roi else f.gray for f in frames]
        return gs[0] if len(gs) == 1 else np.median(np.stack(gs), axis=0).astype(np.uint8)

    def detect(self, cur: ImageFrame, prev: ImageFrame, roi: Box | None = None, cls: str = "motion",
               history: Sequence[ImageFrame] = ()) -> tuple[list[Detection], BrightnessChange]:
        if cur.size != prev.size:
            raise ValueError("2 khung khac kich thuoc")
        ox, oy = (roi.x, roi.y) if roi else (0, 0)
        g1 = cur.gray[roi.y:roi.y + roi.h, roi.x:roi.x + roi.w] if roi else cur.gray
        g0 = prev.gray[roi.y:roi.y + roi.h, roi.x:roi.x + roi.w] if roi else prev.gray
        mask, change = change_mask(g1, self._ref(prev, history, roi), self.p.k)
        sp = ShapeParams("fixed", fixed=1, open_k=self.p.open_k, close_k=self.p.close_k, min_area=self.p.min_area)
        flow = self._flow(g0, g1) if self.p.flow and mask.any() else None
        out = []
        for b in blobs(clean(mask.astype(np.uint8) * 255, sp), sp):
            feats = {"area": float(b.area), "fill": b.fill}
            if flow is not None:
                feats.update(self._blob_flow(flow, b.box))
            ev = Evidence(DETECTOR, None, "frame diff (sang toan cuc da bu)",
                          {"k": self.p.k, "noise": change.noise, "frame": str(cur.frame_id),
                           "prev": str(prev.frame_id)})
            out.append(Detection(cls, Box(ox + b.box.x, oy + b.box.y, b.box.w, b.box.h), Status.UNCERTAIN, (ev,),
                                 features=feats))
        return out, change

    def _flow(self, g0: np.ndarray, g1: np.ndarray) -> np.ndarray:
        s = self.p.flow_scale
        a = cv2.resize(g0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        b = cv2.resize(g1, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        f = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)   # type: ignore[call-overload]
        return np.asarray(f) / s                                                    # px o do phan giai goc

    def _blob_flow(self, flow: np.ndarray, box: Box) -> dict[str, float]:
        s = self.p.flow_scale
        x0, y0 = int(box.x * s), int(box.y * s)
        x1, y1 = max(x0 + 1, int((box.x + box.w) * s)), max(y0 + 1, int((box.y + box.h) * s))
        v = flow[y0:y1, x0:x1].reshape(-1, 2).mean(0)
        return {"vx": float(v[0]), "vy": float(v[1])}
