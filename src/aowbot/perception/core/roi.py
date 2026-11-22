"""ROI Manager: ten -> vung (x, y, w, h) tren man hinh co dinh; kiem bien 1 lan luc dang ky."""
from __future__ import annotations

from collections.abc import Mapping

from ..eval.dataset import Box
from .frame import U8, ImageFrame


class RoiManager:
    def __init__(self, regions: Mapping[str, Box], size: tuple[int, int] = (540, 960)) -> None:
        self.size = size
        for name, b in regions.items():
            if b.x < 0 or b.y < 0 or b.x + b.w > size[0] or b.y + b.h > size[1]:
                raise ValueError(f"ROI '{name}' {b} ngoai man hinh {size[0]}x{size[1]}")
        self._regions = dict(regions)

    def __contains__(self, name: str) -> bool:
        return name in self._regions

    def box(self, name: str) -> Box:
        return self._regions[name]

    def crop(self, frame: ImageFrame, name: str) -> U8:
        if frame.size != self.size:
            raise ValueError(f"khung {frame.size} khac kich thuoc ROI {self.size}")
        return frame.crop(self._regions[name])
