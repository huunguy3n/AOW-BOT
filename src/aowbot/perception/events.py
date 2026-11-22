"""EventGenerator: chuyen CONFIRMED <-> NOT_DETECTED cua lop tinh thanh su kien appeared / disappeared.

UNCERTAIN va UNKNOWN KHONG doi trang thai da chap nhan (tranh nhay nhot khi diem dao dong quanh nguong, va khong coi
thieu bang chung la vang mat). Su kien cua vat theo doi (occluded/reappeared...) do TrackManager phat, khong o day.
"""
from __future__ import annotations

from collections.abc import Sequence

from .contract import FrameId, Outcome, PerceptionEvent, Status


class EventGenerator:
    def __init__(self) -> None:
        self._present: dict[str, bool] = {}

    def update(self, outcomes: Sequence[Outcome], frame_id: FrameId) -> list[PerceptionEvent]:
        out: list[PerceptionEvent] = []
        for o in outcomes:
            if o.status is Status.CONFIRMED and self._present.get(o.cls) is not True:
                out.append(PerceptionEvent("appeared", o.cls, frame_id))     # lan dau thay cung la 'appeared'
                self._present[o.cls] = True
            elif o.status is Status.NOT_DETECTED and self._present.get(o.cls) is True:
                out.append(PerceptionEvent("disappeared", o.cls, frame_id))
                self._present[o.cls] = False
            elif o.status is Status.NOT_DETECTED:
                self._present.setdefault(o.cls, False)
        return out
