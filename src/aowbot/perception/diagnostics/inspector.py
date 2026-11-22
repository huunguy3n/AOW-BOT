"""Vision Inspector: ve cac "lat cat" cua 1 khung de nguoi doc xem bo nhan dien nhin thay gi.

CHI de chan doan: cac tham so (Canny, CLAHE, cua so tuong phan) la tham so HIEN THI, chua hieu chuan, va
duoc ghi vao bao cao (`params`) de khong ai nham chung la nguong nhan dien. Khong co duong chay vao hanh dong.
Truy vet: moi bao cao ghi frame_id + digest + detector dong gop cua tung Detection.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from ..contract import Detection
from ..core.frame import U8, ImageFrame, as_u8
from ..features.contrast import local_std, sobel_magnitude


@dataclass(frozen=True)
class InspectorParams:
    clahe_clip: float = 2.0
    clahe_tile: int = 8
    contrast_window: int = 9        # cua so do lech chuan cuc bo (le)
    canny_low: int = 80
    canny_high: int = 160
    diff_gain: float = 4.0          # khuech dai ban do chenh lech sang de nhin

    def as_dict(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.__dict__.items()}


def _norm_u8(a: np.ndarray[Any, Any]) -> U8:
    """Dua ban do thuc ve 0..255 theo min-max cua CHINH no (chi de hien thi)."""
    lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        return np.zeros(a.shape, np.uint8)
    return ((a - lo) * (255.0 / (hi - lo))).astype(np.uint8)


def _heat(g: U8) -> U8:
    return as_u8(cv2.applyColorMap(g, cv2.COLORMAP_JET))


def brightness_diff(cur: U8, prev: U8) -> np.ndarray[Any, Any]:
    """Chenh lech do sang co dau (float32): duong = sang len, am = toi di. Hai khung phai cung kich thuoc."""
    if cur.shape != prev.shape:
        raise ValueError(f"khac kich thuoc: {cur.shape} vs {prev.shape}")
    return cur.astype(np.float32) - prev.astype(np.float32)


def _diff_view(d: np.ndarray[Any, Any], gain: float) -> U8:
    """Xanh la = sang len, do = toi di, den = khong doi."""
    out = np.zeros((*d.shape, 3), np.uint8)
    pos = np.clip(d * gain, 0, 255).astype(np.uint8)
    neg = np.clip(-d * gain, 0, 255).astype(np.uint8)
    out[..., 1] = pos
    out[..., 2] = neg
    return out


def _sobel(gray: U8) -> U8:
    return _norm_u8(sobel_magnitude(gray))


def _gray3(g: U8) -> U8:
    return as_u8(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))


def draw_detections(img: U8, dets: Sequence[Detection]) -> U8:
    out = img.copy()
    for d in dets:
        b = d.box
        color = {"confirmed": (0, 200, 0), "uncertain": (0, 200, 255)}.get(d.status.value, (0, 0, 255))
        cv2.rectangle(out, (b.x, b.y), (b.x + b.w, b.y + b.h), color, 1)
        tid = "" if d.track_id is None else f" T{d.track_id}"
        cv2.putText(out, f"{d.cls.split('/')[-1]}{tid}", (b.x, max(10, b.y - 3)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)
    return out


def render_views(frame: ImageFrame, prev: ImageFrame | None = None,
                 detections: Sequence[Detection] = (), p: InspectorParams | None = None) -> dict[str, U8]:
    """Ten lat cat -> anh BGR cung kich thuoc khung. Dung bo nho dem cua frame (khong doi mau lap)."""
    p = p or InspectorParams()
    gray = frame.gray
    views: dict[str, U8] = {
        "original": frame.bgr,
        "gray": _gray3(gray),
        "hsv": frame.hsv,
        "lab": frame.lab,
        "brightness": _heat(gray),
        "local_contrast": _heat(_norm_u8(local_std(gray, p.contrast_window))),
        "clahe": _gray3(frame.clahe(p.clahe_clip, p.clahe_tile)),
        "sobel": _gray3(_sobel(gray)),
        "canny": _gray3(as_u8(cv2.Canny(gray, p.canny_low, p.canny_high))),
    }
    if prev is not None:
        views["brightness_diff"] = _diff_view(brightness_diff(gray, prev.gray), p.diff_gain)
    views["detections"] = draw_detections(frame.bgr, detections)
    return views


def contact_sheet(views: Mapping[str, U8], cols: int = 4, scale: float = 0.5) -> U8:
    """Ghep luoi co nhan ten tung o."""
    tiles = []
    for name, img in views.items():
        t = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        cv2.putText(t, name, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(t, name, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        tiles.append(t)
    h, w = tiles[0].shape[:2]
    while len(tiles) % cols:
        tiles.append(np.zeros((h, w, 3), np.uint8))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    return np.vstack(rows)


def feature_report(frame: ImageFrame, detections: Sequence[Detection], p: InspectorParams) -> dict[str, Any]:
    """Bao cao JSON truy vet: khung nao, tham so hien thi nao, moi ket qua do detector nao dong gop."""
    return {
        "frame_id": str(frame.frame_id),
        "digest": frame.digest,
        "timestamp": frame.timestamp,
        "size": list(frame.size),
        "display_params": p.as_dict(),
        "display_params_note": "tham so hien thi, CHUA hieu chuan, khong phai nguong nhan dien",
        "detections": [
            {
                "cls": d.cls, "box": [d.box.x, d.box.y, d.box.w, d.box.h], "status": d.status.value,
                "confidence": d.confidence, "track_id": d.track_id, "detectors": list(d.detectors),
                "evidence": [{"detector": e.detector, "raw_score": e.raw_score, "detail": e.detail,
                              "params": dict(e.params)} for e in d.evidence],
            }
            for d in detections
        ],
    }


def save_inspection(frame: ImageFrame, out_dir: Path, prev: ImageFrame | None = None,
                    detections: Sequence[Detection] = (), p: InspectorParams | None = None) -> Path:
    """Ghi <out_dir>/<frame_id>.png (luoi lat cat) + .json (bao cao). Tra ve duong dan anh."""
    p = p or InspectorParams()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = str(frame.frame_id).replace("#", "_")
    png = out_dir / f"{stem}.png"
    cv2.imwrite(str(png), contact_sheet(render_views(frame, prev, detections, p)))
    (out_dir / f"{stem}.json").write_text(
        json.dumps(feature_report(frame, detections, p), ensure_ascii=False, indent=2), encoding="utf-8")
    return png
