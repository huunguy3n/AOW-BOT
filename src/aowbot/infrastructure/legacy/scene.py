"""Adapter: bo phan loai man hinh CU (bot.screens.identify) -> cong SceneClassifier cua perception.

Khong viet lai / nhan ban phan loai man hinh (template+ROI, kNN, screen_types): chi goi lai ham co san.
"""
from __future__ import annotations

from typing import Any

from aowbot.perception.core.frame import ImageFrame
from bot import screens


class LegacySceneClassifier:
    def __init__(self, vision: Any) -> None:
        self._v = vision

    def classify(self, frame: ImageFrame) -> str | None:
        name, _detail = screens.identify(frame.bgr, self._v)
        return str(name) if name else None
