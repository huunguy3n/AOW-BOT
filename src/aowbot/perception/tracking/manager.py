"""TrackManager + ObjectLifecycle: gan phat hien <-> track (Hungarian, cong theo khoang cach toi vi tri DU DOAN),
vong doi TENTATIVE -> CONFIRMED -> OCCLUDED -> (mat), sinh PerceptionEvent.

Nguyen tac:
- Thieu phep do KHONG phai bang chung vang mat: track CONFIRMED mat phep do chuyen OCCLUDED, tiep tuc du doan
  toi `max_misses` buoc moi bo (xu ly che khuat). Chi bo khi qua han.
- Track chi co lop; khong co quyet dinh game. Moi track xuat ra Detection UNCERTAIN, bang chung ghi 'predicted_only'.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from ..contract import Detection, Evidence, FrameId, PerceptionEvent, Status
from ..eval.dataset import Box
from .assign import assign
from .kalman import KalmanCV, KalmanParams

DETECTOR = "kalman_track"
_CROSS_CLASS = 1e9


class TrackState(StrEnum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    OCCLUDED = "occluded"


@dataclass(frozen=True)
class TrackerParams:
    gate_px: float = 80.0       # khoang cach toi da (px) giua vi tri du doan va phat hien (do Phase 4)
    confirm_hits: int = 3       # so lan trung lien tiep de xac nhan
    max_misses: int = 6         # so buoc lien tiep mat phep do truoc khi bo track da xac nhan (do Phase 4)


@dataclass
class Track:
    id: int
    cls: str
    kf: KalmanCV
    w: float
    h: float
    state: TrackState = TrackState.TENTATIVE
    hits: int = 1
    misses: int = 0
    last_t: float = 0.0


@dataclass(frozen=True)
class TrackUpdate:
    frame_id: FrameId
    detections: tuple[Detection, ...]     # moi track dang song (TENTATIVE khong xuat)
    events: tuple[PerceptionEvent, ...]


def _center(b: Box) -> tuple[float, float]:
    return b.x + b.w / 2, b.y + b.h / 2


class TrackManager:
    def __init__(self, tp: TrackerParams | None = None, kp: KalmanParams | None = None) -> None:
        self.tp = tp or TrackerParams()
        self.kp = kp or KalmanParams()
        self._tracks: list[Track] = []
        self._next_id = 1
        self._t: float | None = None

    @property
    def tracks(self) -> tuple[Track, ...]:
        return tuple(self._tracks)

    def _cost(self, dets: Sequence[Detection]) -> list[list[float]]:
        out = []
        for tr in self._tracks:
            px, py = tr.kf.position
            row = []
            for d in dets:
                cx, cy = _center(d.box)
                row.append(_CROSS_CLASS if d.cls != tr.cls else ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5)
            out.append(row)
        return out

    def update(self, dets: Sequence[Detection], t: float, frame_id: FrameId) -> TrackUpdate:
        dt = 0.0 if self._t is None else max(0.0, t - self._t)
        self._t = t
        for tr in self._tracks:
            tr.kf.predict(dt)
        pairs = assign(self._cost(dets), self.tp.gate_px) if self._tracks and dets else []
        matched_t = {i for i, _ in pairs}
        matched_d = {j for _, j in pairs}
        events: list[PerceptionEvent] = []
        for i, j in pairs:
            self._hit(self._tracks[i], dets[j], t, frame_id, events)
        for i, tr in enumerate(self._tracks):
            if i not in matched_t:
                self._miss(tr, frame_id, events)
        self._tracks = [tr for tr in self._tracks if not self._expired(tr, frame_id, events)]
        for j, d in enumerate(dets):
            if j not in matched_d:
                self._spawn(d, t, frame_id, events)
        return TrackUpdate(frame_id, self._snapshot(frame_id), tuple(events))

    def _hit(self, tr: Track, d: Detection, t: float, fid: FrameId, ev: list[PerceptionEvent]) -> None:
        tr.kf.update(_center(d.box))
        tr.w, tr.h = 0.7 * tr.w + 0.3 * d.box.w, 0.7 * tr.h + 0.3 * d.box.h
        tr.hits += 1
        tr.misses = 0
        tr.last_t = t
        if tr.state is TrackState.OCCLUDED:
            tr.state = TrackState.CONFIRMED
            ev.append(PerceptionEvent("reappeared", tr.cls, fid, tr.id))
        elif tr.state is TrackState.TENTATIVE and tr.hits >= self.tp.confirm_hits:
            tr.state = TrackState.CONFIRMED
            ev.append(PerceptionEvent("appeared", tr.cls, fid, tr.id))

    def _miss(self, tr: Track, fid: FrameId, ev: list[PerceptionEvent]) -> None:
        tr.misses += 1
        if tr.state is TrackState.CONFIRMED:
            tr.state = TrackState.OCCLUDED
            ev.append(PerceptionEvent("occluded", tr.cls, fid, tr.id))

    def _expired(self, tr: Track, fid: FrameId, ev: list[PerceptionEvent]) -> bool:
        if tr.state is TrackState.TENTATIVE:
            return tr.misses > 0          # chua xac nhan ma mat -> bo, khong sinh su kien
        if tr.misses > self.tp.max_misses:
            ev.append(PerceptionEvent("disappeared", tr.cls, fid, tr.id))
            return True
        return False

    def _spawn(self, d: Detection, t: float, fid: FrameId, ev: list[PerceptionEvent]) -> None:
        cx, cy = _center(d.box)
        tr = Track(self._next_id, d.cls, KalmanCV(cx, cy, self.kp), float(d.box.w), float(d.box.h), last_t=t)
        self._next_id += 1
        if self.tp.confirm_hits <= 1:
            tr.state = TrackState.CONFIRMED
            ev.append(PerceptionEvent("appeared", tr.cls, fid, tr.id))
        self._tracks.append(tr)

    def _snapshot(self, fid: FrameId) -> tuple[Detection, ...]:
        out = []
        for tr in self._tracks:
            if tr.state is TrackState.TENTATIVE:
                continue
            x, y = tr.kf.position
            w, h = max(1, round(tr.w)), max(1, round(tr.h))
            box = Box(round(x - w / 2), round(y - h / 2), w, h)
            ev = Evidence(DETECTOR, None, tr.state.value,
                          {"predicted_only": float(tr.misses > 0), "misses": float(tr.misses),
                           "pos_sigma": tr.kf.position_sigma, "frame": str(fid)})
            out.append(Detection(tr.cls, box, Status.UNCERTAIN, (ev,), track_id=tr.id, velocity=tr.kf.velocity))
        return tuple(out)
