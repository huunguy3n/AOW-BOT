"""Phase 1 perception: contract, ImageFrame, FrameBuffer, RoiManager."""
import threading

import numpy as np
import pytest

from aowbot.perception.contract import Detection, Evidence, FrameId, PerceptionResult, Status
from aowbot.perception.core.buffer import FrameBuffer
from aowbot.perception.core.frame import ImageFrame, InvalidFrameError
from aowbot.perception.core.roi import RoiManager
from aowbot.perception.eval.dataset import Box


def frame(seq: int = 0, h: int = 960, w: int = 540, fill: int = 10) -> ImageFrame:
    return ImageFrame(np.full((h, w, 3), fill, np.uint8), FrameId(0, seq), 1.0)


def test_invalid_frames_rejected() -> None:
    for bad in (np.zeros((10, 10), np.uint8), np.zeros((10, 10, 3), np.float32), np.zeros((0, 10, 3), np.uint8)):
        with pytest.raises(InvalidFrameError):
            ImageFrame(bad, FrameId(0, 0))


def test_conversions_computed_once() -> None:
    f = frame()
    for _ in range(3):
        _ = f.gray, f.hsv, f.lab, f.clahe(), f.clahe()
    assert dict(f.conversions) == {"gray": 1, "hsv": 1, "lab": 1, "clahe:2.0:8": 1}


def test_clahe_params_are_distinct_cache_keys() -> None:
    f = frame()
    f.clahe(2.0, 8)
    f.clahe(4.0, 8)
    assert f.conversions["clahe:2.0:8"] == 1 and f.conversions["clahe:4.0:8"] == 1


def test_digest_tracks_pixels() -> None:
    a, b = frame(fill=10), frame(fill=11)
    assert a.digest == frame(fill=10).digest != b.digest


def test_crop_is_view_and_bounds_checked() -> None:
    f = frame()
    c = f.crop(Box(10, 20, 30, 40))
    assert c.shape == (40, 30, 3) and np.shares_memory(c, f.bgr)
    with pytest.raises(ValueError, match="ngoai khung"):
        f.crop(Box(530, 0, 20, 20))


def test_buffer_bounded_and_counts_drops() -> None:
    b = FrameBuffer(3)
    for i in range(5):
        b.push(frame(i, 10, 10))
    assert len(b) == 3 and b.dropped == 2
    assert b.latest().frame_id.seq == 4 and b.previous().frame_id.seq == 3  # type: ignore[union-attr]
    assert b.get(FrameId(0, 0)) is None and b.get(FrameId(0, 2)) is not None
    with pytest.raises(ValueError, match="maxlen"):
        FrameBuffer(0)


def test_buffer_thread_safe_under_contention() -> None:
    b = FrameBuffer(8)
    fr = frame(0, 4, 4)

    def work() -> None:
        for _ in range(500):
            b.push(fr)
            b.latest()
    ts = [threading.Thread(target=work) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(b) == 8 and b.dropped == 4 * 500 - 8


def test_roi_validated_at_registration_and_crop() -> None:
    with pytest.raises(ValueError, match="ngoai man hinh"):
        RoiManager({"bad": Box(500, 0, 100, 10)})
    r = RoiManager({"top": Box(0, 0, 540, 30)})
    assert "top" in r and "x" not in r
    assert r.crop(frame(), "top").shape == (30, 540, 3)
    with pytest.raises(ValueError, match="khac kich thuoc"):
        r.crop(frame(h=100, w=100), "top")


def test_detection_contract() -> None:
    ev = (Evidence("a", 0.9), Evidence("b", None), Evidence("a", 0.8))
    d = Detection("x", Box(10, 10, 20, 40), Status.UNCERTAIN, ev)
    assert d.position == (20, 30) and d.detectors == ("a", "b") and d.confidence is None
    with pytest.raises(ValueError, match="Evidence"):
        Detection("x", Box(0, 0, 1, 1), Status.UNKNOWN, ())
    with pytest.raises(ValueError, match="confidence"):
        Detection("x", Box(0, 0, 1, 1), Status.CONFIRMED, ev, confidence=1.5)


def test_unknown_is_not_not_detected() -> None:
    assert Status.UNKNOWN != Status.NOT_DETECTED
    r = PerceptionResult(FrameId(1, 2), 0.0, True)
    assert r.detections == () and str(r.frame_id) == "i1#2"
