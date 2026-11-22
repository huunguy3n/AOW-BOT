"""FrameBuffer: hang doi khung co gioi han (khong tang bo nho), an toan khi 2 luong (2 may chay song song)."""
from __future__ import annotations

import threading
from collections import deque

from ..contract import FrameId
from .frame import ImageFrame


class FrameBuffer:
    def __init__(self, maxlen: int) -> None:
        if maxlen < 1:
            raise ValueError("maxlen phai >= 1")
        self._q: deque[ImageFrame] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self.dropped = 0

    def push(self, frame: ImageFrame) -> None:
        with self._lock:
            if len(self._q) == self._q.maxlen:
                self.dropped += 1
            self._q.append(frame)

    def __len__(self) -> int:
        with self._lock:
            return len(self._q)

    def latest(self) -> ImageFrame | None:
        with self._lock:
            return self._q[-1] if self._q else None

    def recent(self, n: int) -> list[ImageFrame]:
        """n khung moi nhat, cu -> moi."""
        with self._lock:
            return list(self._q)[-n:] if n > 0 else []

    def previous(self) -> ImageFrame | None:
        with self._lock:
            return self._q[-2] if len(self._q) >= 2 else None

    def get(self, frame_id: FrameId) -> ImageFrame | None:
        with self._lock:
            return next((f for f in self._q if f.frame_id == frame_id), None)
