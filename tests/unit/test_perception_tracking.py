"""Phase 4: gan toi uu, Kalman, TrackManager (vong doi, che khuat), chi so theo doi, MotionDetector."""
import itertools

import cv2
import numpy as np
import pytest

from aowbot.perception.contract import Detection, Evidence, FrameId, Status
from aowbot.perception.core.frame import ImageFrame
from aowbot.perception.detectors.motion import MotionDetector, MotionParams
from aowbot.perception.eval.dataset import Box
from aowbot.perception.eval.tracking_metrics import score
from aowbot.perception.tracking.assign import assign
from aowbot.perception.tracking.kalman import KalmanCV, KalmanParams
from aowbot.perception.tracking.manager import TrackerParams, TrackManager, TrackState


# ---------------------------------------------------------------- assign
def brute(cost: list[list[float]], gate: float) -> float:
    n, m = len(cost), len(cost[0])
    k = min(n, m)
    best = float("inf")
    for rows in itertools.permutations(range(n), k):
        for cols in itertools.permutations(range(m), k):
            ok = all(cost[r][c] <= gate for r, c in zip(rows, cols, strict=True))
            if ok:
                best = min(best, sum(cost[r][c] for r, c in zip(rows, cols, strict=True)))
    return best


def test_assign_is_optimal_vs_bruteforce() -> None:
    rng = np.random.RandomState(0)
    for n, m in [(3, 3), (2, 4), (4, 2), (4, 4), (1, 3)]:
        for _ in range(25):
            c = rng.randint(0, 20, (n, m)).astype(float).tolist()
            pairs = assign(c, gate=1e9)
            assert len(pairs) == min(n, m)
            assert sum(c[i][j] for i, j in pairs) == brute(c, 1e9)


def test_assign_gate_and_empty() -> None:
    assert assign([], 5) == [] and assign([[]], 5) == []
    assert assign([[10.0]], 5) == []
    assert assign([[1.0, 9.0], [9.0, 2.0]], 5) == [(0, 0), (1, 1)]


# ---------------------------------------------------------------- Kalman
def test_kalman_learns_velocity_and_smooths() -> None:
    rng = np.random.RandomState(1)
    kp = KalmanParams(accel_sigma=20, meas_sigma=4)
    kf = KalmanCV(0, 0, kp)
    err_meas, err_kf = [], []
    for i in range(1, 60):
        true = 100.0 * i * 0.1
        z = true + rng.normal(0, 4)
        kf.predict(0.1)
        kf.update((z, 50 + rng.normal(0, 4) * 0))
        if i > 20:
            err_meas.append(abs(z - true))
            err_kf.append(abs(kf.position[0] - true))
    assert abs(kf.velocity[0] - 100) < 15
    assert np.mean(err_kf) < np.mean(err_meas)


def test_kalman_predict_only_extrapolates_and_uncertainty_grows() -> None:
    kf = KalmanCV(0, 0, KalmanParams(accel_sigma=20, meas_sigma=2))
    for i in range(1, 30):
        kf.predict(0.1)
        kf.update((10.0 * i, 0.0))
    s0, x0 = kf.position_sigma, kf.position[0]
    for _ in range(5):
        kf.predict(0.1)
    assert kf.position[0] > x0 + 3 and kf.position_sigma > s0
    with pytest.raises(ValueError):
        kf.predict(-1)


# ---------------------------------------------------------------- TrackManager
def det(cx: float, cy: float, cls: str = "unit") -> Detection:
    return Detection(cls, Box(int(cx - 10), int(cy - 10), 20, 20), Status.UNCERTAIN, (Evidence("t"),))


def run(tm: TrackManager, seq: list[list[Detection]], dt: float = 0.1):
    out = []
    for i, ds in enumerate(seq):
        out.append(tm.update(ds, i * dt, FrameId(0, i)))
    return out


def test_lifecycle_confirm_occlude_reappear_disappear() -> None:
    tm = TrackManager(TrackerParams(gate_px=40, confirm_hits=3, max_misses=3),
                      KalmanParams(accel_sigma=50, meas_sigma=3))
    moving = [[det(100 + 10 * i, 200)] for i in range(6)]
    gap = [[] for _ in range(2)]
    back = [[det(100 + 10 * i, 200)] for i in range(8, 11)]
    gone = [[] for _ in range(5)]
    ups = run(tm, moving + gap + back + gone)
    kinds = [(i, e.kind) for i, u in enumerate(ups) for e in u.events]
    assert kinds == [(2, "appeared"), (6, "occluded"), (8, "reappeared"), (11, "occluded"), (14, "disappeared")]
    assert len({e.track_id for u in ups for e in u.events}) == 1          # cung MOT danh tinh qua che khuat
    occ = ups[6].detections[0]
    assert occ.evidence[0].params["predicted_only"] == 1.0 and occ.velocity is not None and occ.velocity[0] > 50


def test_missing_measurement_is_not_absence_until_expired() -> None:
    tm = TrackManager(TrackerParams(gate_px=40, confirm_hits=2, max_misses=4))
    ups = run(tm, [[det(50, 50)]] * 3 + [[]] * 3)
    assert all(len(u.detections) == 1 for u in ups[2:])          # van con track khi moi mat 1-3 buoc
    assert tm.tracks[0].state is TrackState.OCCLUDED


def test_tentative_noise_dies_silently_and_class_isolated() -> None:
    tm = TrackManager(TrackerParams(gate_px=40, confirm_hits=3))
    ups = run(tm, [[det(10, 10)], [], [det(300, 300)], []])
    assert all(not u.events and not u.detections for u in ups) and not tm.tracks
    tm = TrackManager(TrackerParams(gate_px=100, confirm_hits=1))
    ups = run(tm, [[det(100, 100, "a")], [det(102, 100, "b")]])
    assert len({d.track_id for u in ups for d in u.detections}) == 2        # khac lop khong gop


def test_crossing_objects_keep_identity_with_motion_model() -> None:
    tm = TrackManager(TrackerParams(gate_px=60, confirm_hits=2, max_misses=3),
                      KalmanParams(accel_sigma=30, meas_sigma=2))
    seq = [[det(40 + 14 * i, 300 + 4 * i), det(40 + 14 * i, 380 - 4 * i)] for i in range(20)]     # cat nhau o i=10
    ups = run(tm, seq)
    assert len({d.track_id for u in ups for d in u.detections}) == 2          # khong sinh them track
    early = min(ups[4].detections, key=lambda d: d.box.y).track_id            # vat dang di XUONG (y tang)
    late = max(ups[-1].detections, key=lambda d: d.box.y).track_id
    assert early == late


# ---------------------------------------------------------------- chi so
def bx(x: float, y: float = 0.0) -> Box:
    return Box(int(x), int(y), 20, 20)


def test_metrics_perfect_and_id_switch() -> None:
    gt = [[(1, bx(10 * i))] for i in range(10)]
    s = score(gt, [[(7, bx(10 * i))] for i in range(10)])
    assert (s.id_switches, s.fp, s.fn) == (0, 0, 0) and s.mota == 1.0 and s.idf1 == 1.0 and s.rmse == 0
    hyp = [[(7 if i < 5 else 8, bx(10 * i))] for i in range(10)]
    w = score(gt, hyp)
    assert w.id_switches == 1 and w.mota == pytest.approx(0.9) and w.idf1 == pytest.approx(0.5)


def test_metrics_misses_false_positives_and_length_check() -> None:
    gt = [[(1, bx(0))], [(1, bx(0))], [(1, bx(0))], [(1, bx(0))]]
    hyp = [[(1, bx(0))], [], [(1, bx(0)), (2, bx(400))], [(1, bx(0))]]
    s = score(gt, hyp)
    assert (s.tp, s.fn, s.fp) == (3, 1, 1) and s.mota == pytest.approx(0.5)
    with pytest.raises(ValueError):
        score(gt, hyp[:2])


# ---------------------------------------------------------------- MotionDetector
def textured(seed: int = 0) -> np.ndarray:
    rng = np.random.RandomState(seed)
    return cv2.resize(rng.randint(30, 220, (120, 68, 3)).astype(np.uint8), (270, 480), interpolation=cv2.INTER_CUBIC)


def frame(img: np.ndarray, seq: int) -> ImageFrame:
    return ImageFrame(img, FrameId(0, seq), float(seq))


def sprite(bg: np.ndarray, x: int, y: int) -> np.ndarray:
    out = bg.copy()
    out[y:y + 30, x:x + 30] = 250
    return out


def test_motion_finds_moved_sprite_with_correct_velocity() -> None:
    bg = textured()
    md = MotionDetector(MotionParams(min_area=100))
    dets, ch = md.detect(frame(sprite(bg, 108, 200), 1), frame(sprite(bg, 100, 200), 0))
    assert not ch.global_shift and len(dets) >= 1
    big = max(dets, key=lambda d: d.features["area"])
    assert big.evidence[0].detector == "motion" and big.evidence[0].params["prev"] == "i0#0"
    assert 92 <= big.box.x <= 112 and 190 <= big.box.y <= 210
    assert big.features["vx"] > 0 and abs(big.features["vy"]) < abs(big.features["vx"])


def test_motion_ignores_global_lighting_change_and_static_scene() -> None:
    bg = textured()
    md = MotionDetector()
    assert md.detect(frame(bg, 1), frame(bg, 0))[0] == []
    bright = np.clip(bg.astype(np.int16) + 25, 0, 255).astype(np.uint8)
    dets, ch = md.detect(frame(bright, 1), frame(bg, 0))
    assert dets == [] and ch.global_shift and ch.direction == "brighter"
    with pytest.raises(ValueError):
        md.detect(frame(bg, 1), frame(bg[:100], 0))
