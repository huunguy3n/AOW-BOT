"""PerceptionService + SceneAnalyzer: dieu phoi detector -> hop nhat -> theo doi -> su kien, ra PerceptionResult.

KHONG chay hanh dong game, KHONG biet module/agent. Detector, bo phan loai man hinh, bo theo doi duoc tiem vao qua
Protocol (SceneClassifier duoc hien thuc boi adapter legacy: khong nhan ban ML/kNN/identify da co).

Quy tac (benchmark Phase 2-4):
- Template da ty le chay truoc (ROI-first). ORB (dat) chi chay khi mau du diem dac trung VA ket qua hop nhat tu template
  chua dat nguong CONFIRMED (detector co dieu kien).
- Chuyen dong chi tinh khi co khung truoc; khong co khung truoc = khong co bang chung (khong phai 'khong chuyen dong').
- Khung hong -> INVALID_FRAME, khong dung vao bo theo doi / bo nho dem.
"""
from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from .contract import Detection, FrameId, Outcome, PerceptionEvent, PerceptionResult, Status
from .core.buffer import FrameBuffer
from .core.frame import ImageFrame, InvalidFrameError
from .eval.dataset import Box
from .events import EventGenerator
from .fusion import CandidateMerger, ConfidenceEvaluator, FeatureFusionEngine
from .tracking.manager import TrackManager


class StaticDetector(Protocol):
    def detect(self, frame: ImageFrame, name: str, tpl: Any, roi: Box | None = None) -> Detection | None: ...


class FeatureDetector(StaticDetector, Protocol):
    def applicable(self, name: str, tpl: Any) -> bool: ...


class MotionLike(Protocol):
    def detect(self, cur: ImageFrame, prev: ImageFrame, roi: Box | None = None, cls: str = "motion",
               history: Sequence[ImageFrame] = ()) -> tuple[list[Detection], Any]: ...


class BadgeLike(Protocol):
    def detect(self, frame: ImageFrame, roi: Box | None = None, cls: str = "reddot") -> list[Detection]: ...


class SceneClassifier(Protocol):
    def classify(self, frame: ImageFrame) -> str | None: ...


@dataclass(frozen=True)
class Query:
    """Hoi: lop `cls` (mau `template`, BGR uint8) co trong `roi` khong?"""

    cls: str
    template: np.ndarray[Any, Any] | None
    roi: Box | None = None


@dataclass(frozen=True)
class ServiceConfig:
    motion_roi: Box | None = None
    motion_cls: str = "motion"
    history: int = 9                     # so khung giu cho nen trung vi cua MotionDetector (>= MotionParams.bg_frames)
    skip_below: float | None = 1.0       # dung lai neu diff TB tren ROI < nguong (Phase 6)


class SceneAnalyzer:
    """Bao bo phan loai man hinh; nho ket qua theo digest khung (khong phan loai lai cung 1 khung)."""

    def __init__(self, classifier: SceneClassifier | None) -> None:
        self._c = classifier
        self._last: tuple[str, str | None] | None = None

    def analyze(self, frame: ImageFrame) -> str | None:
        if self._c is None:
            return None
        if self._last is not None and self._last[0] == frame.digest:
            return self._last[1]
        scene = self._c.classify(frame)
        self._last = (frame.digest, scene)
        return scene


class PerceptionService:
    def __init__(self, template: StaticDetector, fusion: FeatureFusionEngine, evaluator: ConfidenceEvaluator,
                 buffer: FrameBuffer, config: ServiceConfig | None = None) -> None:
        self.template = template
        self.fusion = fusion
        self.evaluator = evaluator
        self.buffer = buffer
        self.cfg = config or ServiceConfig()
        self.merger = CandidateMerger()
        self.events = EventGenerator()
        self.orb: FeatureDetector | None = None
        self.motion: MotionLike | None = None
        self.tracker: TrackManager | None = None
        self.scene = SceneAnalyzer(None)
        self.badges: BadgeLike | None = None
        self._cache: dict[tuple[Any, ...], tuple[np.ndarray[Any, Any], Outcome]] = {}

    def with_orb(self, orb: FeatureDetector) -> PerceptionService:
        self.orb = orb
        return self

    def with_motion(self, motion: MotionLike, tracker: TrackManager) -> PerceptionService:
        self.motion, self.tracker = motion, tracker
        return self

    def with_badges(self, badges: BadgeLike) -> PerceptionService:
        self.badges = badges
        return self

    def with_scene(self, classifier: SceneClassifier) -> PerceptionService:
        self.scene = SceneAnalyzer(classifier)
        return self

    # ------------------------------------------------------------------ vao
    def process_raw(self, bgr: Any, instance: int, seq: int, timestamp: float | None,
                    queries: Sequence[Query]) -> PerceptionResult:
        """Nhan anh tho: khung hong -> ket qua INVALID_FRAME (khong nem loi, khong dung vao trang thai)."""
        fid = FrameId(instance, seq)
        try:
            frame = ImageFrame(bgr, fid, timestamp)
        except InvalidFrameError as e:
            return PerceptionResult(fid, time.time() if timestamp is None else timestamp, False,
                                    stats={"error": 1.0}, outcomes=tuple(
                                        Outcome(q.cls, Status.UNKNOWN, None, f"khung hong: {e}") for q in queries))
        return self.process(frame, queries)

    def process(self, frame: ImageFrame, queries: Sequence[Query]) -> PerceptionResult:
        stats: dict[str, float] = {}
        t0 = time.perf_counter()
        outs: list[Outcome] = []
        for q in queries:
            o = self._reuse(frame, q)
            if o is None:
                o = self._ask(frame, q, stats)
                self._remember(frame, q, o)
            else:
                stats["skipped"] = stats.get("skipped", 0.0) + 1.0
            outs.append(o)
        outcomes = tuple(outs)
        stats["static_ms"] = (time.perf_counter() - t0) * 1000
        events: list[PerceptionEvent] = self.events.update(outcomes, frame.frame_id)
        dets = [o.detection for o in outcomes if o.detection is not None]
        t1 = time.perf_counter()
        tracked, tev = self._motion(frame, stats)
        stats["motion_ms"] = (time.perf_counter() - t1) * 1000
        dots = self.badges.detect(frame) if self.badges is not None else []
        stats["reddots"] = float(len(dots))
        t2 = time.perf_counter()
        scene = self.scene.analyze(frame)
        stats["scene_ms"] = (time.perf_counter() - t2) * 1000
        self.buffer.push(frame)
        return PerceptionResult(frame.frame_id, frame.timestamp, True, scene, (*dets, *dots, *tracked), outcomes,
                                (*events, *tev), frame.digest, stats)

    # ------------------------------------------------------------------ noi bo
    def _ask(self, frame: ImageFrame, q: Query, stats: dict[str, float]) -> Outcome:
        if q.template is None:
            return Outcome(q.cls, Status.UNKNOWN, None, "thieu anh mau")
        d = self.template.detect(frame, q.cls, q.template, q.roi)
        if d is None:
            return Outcome(q.cls, Status.UNKNOWN, None, "vung tim nho hon mau")
        fused = [self.fusion.fuse(c) for c in self.merger.merge([d])]
        if self.orb is not None and self._needs_more(fused) and self.orb.applicable(q.cls, q.template):
            stats["orb_runs"] = stats.get("orb_runs", 0.0) + 1
            d2 = self.orb.detect(frame, q.cls, q.template, q.roi)
            if d2 is not None:
                fused = [self.fusion.fuse(c) for c in self.merger.merge([d, d2])]
        return self.evaluator.judge(q.cls, fused, searched=True)

    @staticmethod
    def _key(q: Query) -> tuple[Any, ...]:
        return (q.cls, q.roi, None if q.template is None else q.template.shape)

    @staticmethod
    def _region(frame: ImageFrame, q: Query) -> np.ndarray[Any, Any]:
        """Vung so sanh de quyet dinh dung lai: ROI cua cau hoi (do phan giai goc) hoac thumb ca khung neu khong co ROI.
        Doi tren ROI (khong phai trung binh toan man): nut/cham nho moi hien khong bi pha loang boi phan con lai."""
        g = frame.gray[q.roi.y:q.roi.y + q.roi.h, q.roi.x:q.roi.x + q.roi.w] if q.roi else frame.thumb()
        return g.astype(np.int16)

    def _reuse(self, frame: ImageFrame, q: Query) -> Outcome | None:
        if self.cfg.skip_below is None:
            return None
        hit = self._cache.get(self._key(q))
        if hit is None or hit[0].shape != self._region(frame, q).shape:
            return None
        diff = float(np.abs(self._region(frame, q) - hit[0]).mean())
        return hit[1] if diff < self.cfg.skip_below else None

    def _remember(self, frame: ImageFrame, q: Query, outcome: Outcome) -> None:
        if self.cfg.skip_below is not None:
            self._cache[self._key(q)] = (self._region(frame, q), outcome)

    def _needs_more(self, fused: Sequence[Detection]) -> bool:
        return not any((x.confidence or 0.0) >= self.evaluator.confirm_p for x in fused)

    def _motion(self, frame: ImageFrame, stats: Mapping[str, float] | dict[str, float]
                ) -> tuple[list[Detection], list[PerceptionEvent]]:
        if self.motion is None or self.tracker is None:
            return [], []
        prev = self.buffer.latest()
        if prev is None or prev.size != frame.size:
            return [], []                        # khong co khung truoc: khong co bang chung, khong cap nhat theo doi
        dets, change = self.motion.detect(frame, prev, self.cfg.motion_roi, self.cfg.motion_cls,
                                          self.buffer.recent(self.cfg.history))
        if isinstance(stats, dict):
            stats["global_shift"] = float(getattr(change, "global_shift", False))
            stats["motion_blobs"] = float(len(dets))
        up = self.tracker.update(dets, frame.timestamp, frame.frame_id)
        return list(up.detections), list(up.events)
