"""ImageFrame: 1 khung hinh BGR 8-bit + dinh danh + chuyen doi mau luoi (tinh 1 lan, nho lai).

Moi chuyen doi (gray/hsv/lab/clahe) chi chay 1 lan tren moi khung; `conversions` dem de test xac nhan.
"""
from __future__ import annotations

import hashlib
import time
from collections import Counter
from collections.abc import Callable
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray

from ..contract import FrameId
from ..eval.dataset import Box

U8 = NDArray[np.uint8]


def as_u8(a: Any) -> U8:
    """Ep kieu ket qua cv2 (stub tra ve dtype rong) ve uint8: moi ham o day deu sinh anh 8-bit."""
    return cast(U8, a)


class InvalidFrameError(ValueError):
    """Khung khong hop le (khong phai uint8 HxWx3, hoac rong)."""


class ImageFrame:
    def __init__(self, bgr: U8, frame_id: FrameId, timestamp: float | None = None) -> None:
        if not isinstance(bgr, np.ndarray) or bgr.dtype != np.uint8 or bgr.ndim != 3 or bgr.shape[2] != 3:
            raise InvalidFrameError("can anh uint8 HxWx3 (BGR)")
        if bgr.shape[0] == 0 or bgr.shape[1] == 0:
            raise InvalidFrameError("anh rong")
        self.bgr: U8 = bgr
        self.frame_id = frame_id
        self.timestamp = time.time() if timestamp is None else timestamp
        self.conversions: Counter[str] = Counter()
        self._memo: dict[str, U8] = {}
        self._digest: str | None = None

    @property
    def size(self) -> tuple[int, int]:
        """(rong, cao)."""
        return self.bgr.shape[1], self.bgr.shape[0]

    @property
    def digest(self) -> str:
        """SHA-256 rut gon cua diem anh: gan ket qua nhan dien voi dung khung dau vao."""
        if self._digest is None:
            self._digest = hashlib.sha256(self.bgr.tobytes()).hexdigest()[:16]
        return self._digest

    def _get(self, key: str, make: Callable[[], U8]) -> U8:
        if key not in self._memo:
            self._memo[key] = make()
            self.conversions[key] += 1
        return self._memo[key]

    @property
    def gray(self) -> U8:
        return self._get("gray", lambda: as_u8(cv2.cvtColor(self.bgr, cv2.COLOR_BGR2GRAY)))

    @property
    def hsv(self) -> U8:
        return self._get("hsv", lambda: as_u8(cv2.cvtColor(self.bgr, cv2.COLOR_BGR2HSV)))

    @property
    def lab(self) -> U8:
        return self._get("lab", lambda: as_u8(cv2.cvtColor(self.bgr, cv2.COLOR_BGR2LAB)))

    def thumb(self) -> U8:
        """Anh xam 54x96 (INTER_AREA): so sanh re giua 2 khung (cung kich thuoc voi watchdog/learn cua bot)."""
        return self._get("thumb", lambda: as_u8(cv2.resize(self.gray, (54, 96), interpolation=cv2.INTER_AREA)))

    def clahe(self, clip: float = 2.0, tile: int = 8) -> U8:
        """CLAHE tren do sang. Tham so la cua nguoi goi (chua hieu chuan), nen nam trong khoa nho."""
        def make() -> U8:
            return as_u8(cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile)).apply(self.gray))
        return self._get(f"clahe:{clip}:{tile}", make)

    def crop(self, box: Box) -> U8:
        """Vung cat (view, khong sao chep). Ngoai khung -> ValueError (khong am tham cat bot)."""
        w, h = self.size
        if box.x < 0 or box.y < 0 or box.x + box.w > w or box.y + box.h > h:
            raise ValueError(f"vung {box} ngoai khung {w}x{h}")
        return as_u8(self.bgr[box.y:box.y + box.h, box.x:box.x + box.w])
