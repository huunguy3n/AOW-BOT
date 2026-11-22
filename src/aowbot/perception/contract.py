"""Hop dong ket qua nhan dien (PerceptionResult). Thuan: khong cv2/numpy/bot.

Nguyen tac:
- `Unknown` (chua du bang chung: thieu mau, khung la) KHAC `NotDetected` (da tim du va vang mat).
- `confidence` chi do bo hieu chuan sinh ra; diem tho cua detector nam trong `Evidence.raw_score`
  va KHONG bao gio duoc ghi thanh xac suat. Chua hieu chuan -> `confidence = None`.
- Nhan dien khong ra lenh hanh dong: ket qua chi mo ta, quyet dinh o module/agent.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from .eval.dataset import Box


class Status(StrEnum):
    CONFIRMED = "confirmed"
    UNCERTAIN = "uncertain"
    UNKNOWN = "unknown"
    NOT_DETECTED = "not_detected"
    INVALID_FRAME = "invalid_frame"


@dataclass(frozen=True)
class FrameId:
    instance: int
    seq: int

    def __str__(self) -> str:
        return f"i{self.instance}#{self.seq}"


@dataclass(frozen=True)
class Evidence:
    """Bang chung cua MOT detector cho MOT ung vien (truy vet ket qua -> detector dong gop)."""

    detector: str
    raw_score: float | None = None
    detail: str = ""
    params: Mapping[str, float | str] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True)
class Detection:
    cls: str
    box: Box
    status: Status
    evidence: tuple[Evidence, ...]
    confidence: float | None = None
    track_id: int | None = None
    velocity: tuple[float, float] | None = None
    features: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence ngoai [0,1]: {self.confidence}")
        if not self.evidence:
            raise ValueError("Detection phai co it nhat 1 Evidence (truy vet detector)")

    @property
    def position(self) -> tuple[int, int]:
        return self.box.x + self.box.w // 2, self.box.y + self.box.h // 2

    @property
    def detectors(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(e.detector for e in self.evidence))


@dataclass(frozen=True)
class PerceptionEvent:
    kind: str            # vd "appeared", "disappeared", "moved"
    cls: str
    frame_id: FrameId
    track_id: int | None = None


@dataclass(frozen=True)
class Outcome:
    """Ket luan cua MOT cau hoi 'lop X co o do khong?'. NOT_DETECTED / UNKNOWN khong co Detection nen can o rieng."""

    cls: str
    status: Status
    detection: Detection | None = None
    reason: str = ""
    p: float | None = None          # xac suat hop nhat cua ung vien tot nhat (ke ca khi bi loai); None = khong co

    def __post_init__(self) -> None:
        has = self.detection is not None
        if has and self.status in (Status.NOT_DETECTED, Status.UNKNOWN, Status.INVALID_FRAME):
            raise ValueError(f"{self.status} khong di kem Detection")
        if not has and self.status in (Status.CONFIRMED, Status.UNCERTAIN):
            raise ValueError(f"{self.status} can Detection")


@dataclass(frozen=True)
class PerceptionResult:
    frame_id: FrameId
    timestamp: float
    frame_valid: bool                   # False = khung hong (khong dung vao theo doi / bo nho dem)
    scene: str | None = None
    detections: tuple[Detection, ...] = ()   # moi vat the dang song (tinh + theo doi)
    outcomes: tuple[Outcome, ...] = ()       # moi cau hoi duoc hoi: CONFIRMED/UNCERTAIN/NOT_DETECTED/UNKNOWN
    events: tuple[PerceptionEvent, ...] = ()
    frame_digest: str = ""
    stats: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))
