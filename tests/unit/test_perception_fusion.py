"""Phase 5: hieu chuan, hop nhat, danh gia do tin cay, su kien, PerceptionService, cau noi World Model."""
import math
from pathlib import Path

import cv2
import numpy as np
import pytest

from aowbot.domain.freshness import Fact
from aowbot.infrastructure.perception_facts import PerceptionFactSource
from aowbot.perception.calibration import (
    Calibrator,
    FusionModel,
    expected_calibration_error,
    fit_calibrator,
    fit_fusion,
    fit_logistic,
    logit,
    sigmoid,
)
from aowbot.perception.contract import Detection, Evidence, FrameId, Outcome, PerceptionResult, Status
from aowbot.perception.core.buffer import FrameBuffer
from aowbot.perception.core.frame import ImageFrame
from aowbot.perception.detectors.badge import RedDotDetector
from aowbot.perception.detectors.orb import OrbDetector
from aowbot.perception.detectors.template import TemplateDetector
from aowbot.perception.eval.dataset import Box
from aowbot.perception.events import EventGenerator
from aowbot.perception.fusion import CandidateMerger, ConfidenceEvaluator, FeatureFusionEngine
from aowbot.perception.service import PerceptionService, Query, SceneAnalyzer, ServiceConfig

CAL_MS = Calibrator("template_ms", 20.0, -16.0, "test", 10, 10)      # p=0,5 tai diem 0,8
CAL_ORB = Calibrator("orb", 0.5, -4.0, "test", 10, 10)               # p=0,5 tai 8 inlier
MODEL = FusionModel({"template_ms": 1.0, "orb": 1.0}, 0.0, "test", 10, 10, {"template_ms": CAL_MS, "orb": CAL_ORB})


def det(cls: str, box: Box, detector: str, score: float | None) -> Detection:
    return Detection(cls, box, Status.UNCERTAIN, (Evidence(detector, score),))


# ---------------------------------------------------------------- calibration
def test_logistic_fit_recovers_known_curve() -> None:
    rng = np.random.RandomState(0)
    s = rng.uniform(0, 1, 4000)
    y = (rng.uniform(size=4000) < 1 / (1 + np.exp(-(10 * s - 5)))).astype(int)
    c = fit_calibrator("d", s, y, "test")
    assert abs(c.a - 10) < 1.5 and abs(c.b + 5) < 1.0 and c.n_pos + c.n_neg == 4000
    assert expected_calibration_error([c.prob(v) for v in s], y) < 0.03


def test_logistic_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        fit_logistic(np.ones((3, 2)), np.array([1, 1, 1]))
    with pytest.raises(ValueError):
        fit_logistic(np.ones((3, 2)), np.array([1, 0]))
    assert sigmoid(-1000) == 0.0 and sigmoid(1000) == 1.0 and logit(0.5) == 0 and math.isfinite(logit(0))


def test_fit_fusion_missing_detector_is_not_negative_evidence() -> None:
    rng = np.random.RandomState(1)
    rows, ys = [], []
    for _ in range(600):
        y = int(rng.rand() < 0.5)
        row = {"a": float(np.clip(0.75 * y + 0.125 + rng.normal(0, 0.12), 0.01, 0.99))}
        if rng.rand() < 0.4:
            row["b"] = float(np.clip(0.75 * y + 0.125 + rng.normal(0, 0.12), 0.01, 0.99))
        rows.append(row)
        ys.append(y)
    w, bias = fit_fusion(rows, ys, ["a", "b"], "test")
    assert w["a"] > 0 and w["b"] > 0
    m = FusionModel(w, bias, "test", 1, 1)
    assert m.fused({"a": 0.9}) > 0.5 > m.fused({"a": 0.1})            # thieu b khong keo ve 0
    assert m.fused({"a": 0.9, "b": 0.9}) > m.fused({"a": 0.9})        # co b dong y -> tin hon


def test_model_json_roundtrip_and_shipped_config_loads() -> None:
    th = {"confirm_p": 0.9, "reject_p": 0.1}
    m = FusionModel({"template_ms": 1.2}, -0.3, "src", 5, 6, {"template_ms": CAL_MS}, th)
    r = FusionModel.from_json(m.to_json())
    assert r.weights == m.weights and r.calibrators["template_ms"] == CAL_MS and r.thresholds["confirm_p"] == 0.9
    shipped = Path(__file__).resolve().parents[2] / "config" / "perception_calibration.json"
    if shipped.exists():
        s = FusionModel.from_json(shipped.read_text(encoding="utf8"))
        assert s.source.startswith("synthetic") and 0 < s.thresholds["reject_p"] < s.thresholds["confirm_p"] < 1


# ---------------------------------------------------------------- merge + fuse
def test_merger_groups_by_class_and_overlap() -> None:
    a = det("x", Box(100, 100, 40, 40), "template_ms", 0.9)
    b = det("x", Box(105, 102, 40, 40), "orb", 12)
    c = det("x", Box(400, 400, 40, 40), "template_ms", 0.5)
    d = det("y", Box(100, 100, 40, 40), "template_ms", 0.9)
    groups = CandidateMerger().merge([a, b, c, d])
    assert sorted(len(g.members) for g in groups) == [1, 1, 2]


def test_fusion_two_detectors_agree_beats_one_and_keeps_all_evidence() -> None:
    eng = FeatureFusionEngine(MODEL)
    one = eng.fuse(CandidateMerger().merge([det("x", Box(0, 0, 40, 40), "template_ms", 0.85)])[0])
    both = eng.fuse(CandidateMerger().merge(
        [det("x", Box(0, 0, 40, 40), "template_ms", 0.85), det("x", Box(2, 2, 40, 40), "orb", 14)])[0])
    assert both.confidence > one.confidence > 0.5                        # type: ignore[operator]
    assert {e.detector for e in both.evidence} == {"template_ms", "orb", "fusion"}
    assert both.evidence[-1].params["model_source"] == "test"


def test_fusion_without_calibrator_does_not_invent_confidence() -> None:
    eng = FeatureFusionEngine(MODEL)
    d = eng.fuse(CandidateMerger().merge([det("x", Box(0, 0, 9, 9), "mystery", 0.99)])[0])
    assert d.confidence is None and d.status is Status.UNCERTAIN


def test_evaluator_statuses_and_unknown_vs_not_detected() -> None:
    ev = ConfidenceEvaluator(confirm_p=0.9, reject_p=0.1)
    eng = FeatureFusionEngine(MODEL)

    def fused(score: float) -> list[Detection]:
        return [eng.fuse(CandidateMerger().merge([det("x", Box(0, 0, 40, 40), "template_ms", score)])[0])]
    assert ev.judge("x", fused(0.95), True).status is Status.CONFIRMED
    mid = ev.judge("x", fused(0.8), True)
    assert mid.status is Status.UNCERTAIN and mid.detection is not None and mid.p is not None
    low = ev.judge("x", fused(0.5), True)
    assert low.status is Status.NOT_DETECTED and low.detection is None
    assert ev.judge("x", [], True).status is Status.NOT_DETECTED
    assert ev.judge("x", [], False).status is Status.UNKNOWN                 # chua tim du != vang mat
    with pytest.raises(ValueError):
        ConfidenceEvaluator(0.2, 0.5)
    with pytest.raises(ValueError):
        Outcome("x", Status.CONFIRMED, None)


# ---------------------------------------------------------------- events
def test_event_generator_no_flapping_on_uncertain() -> None:
    g = EventGenerator()
    f = lambda i: FrameId(0, i)                                              # noqa: E731
    seq = [Status.NOT_DETECTED, Status.CONFIRMED, Status.UNKNOWN, Status.NOT_DETECTED, Status.NOT_DETECTED]
    det_ = det("x", Box(0, 0, 4, 4), "t", 1.0)
    out = []
    for i, st in enumerate(seq):
        o = Outcome("x", st, det_ if st is Status.CONFIRMED else None)
        out += [e.kind for e in g.update([o], f(i))]
    assert out == ["appeared", "disappeared"]                                # UNKNOWN o giua khong tao su kien


# ---------------------------------------------------------------- service
def scene_img(seed: int = 0) -> np.ndarray:
    rng = np.random.RandomState(seed)
    return cv2.GaussianBlur(cv2.resize(rng.randint(0, 255, (480, 270, 3)).astype(np.uint8), (540, 960)), (0, 0), 0.8)


BOX = Box(200, 400, 60, 50)


def make_service(orb: bool = True, skip: float | None = None) -> PerceptionService:
    svc = PerceptionService(TemplateDetector(), FeatureFusionEngine(MODEL), ConfidenceEvaluator(0.9, 0.1),
                            FrameBuffer(10), ServiceConfig(skip_below=skip))
    return svc.with_orb(OrbDetector()) if orb else svc


def test_service_confirms_present_rejects_absent_and_traces() -> None:
    img = scene_img()
    tpl = img[BOX.y:BOX.y + BOX.h, BOX.x:BOX.x + BOX.w].copy()
    svc = make_service(orb=False)
    roi = Box(150, 350, 160, 150)
    r = svc.process_raw(img, 0, 1, 1.0, [Query("x", tpl, roi)])
    o = r.outcomes[0]
    assert r.frame_valid and o.status is Status.CONFIRMED and o.detection is not None
    assert (o.detection.box.x, o.detection.box.y) == (BOX.x, BOX.y) and r.frame_digest
    assert "fusion" in o.detection.detectors or o.detection.evidence[-1].detector == "fusion"
    assert [e.kind for e in r.events] == ["appeared"]
    other = svc.process_raw(scene_img(7), 0, 2, 2.0, [Query("x", tpl, roi)])
    assert other.outcomes[0].status is Status.NOT_DETECTED and [e.kind for e in other.events] == ["disappeared"]


def test_service_unknown_cases_and_invalid_frame() -> None:
    svc = make_service(orb=False)
    r = svc.process_raw(scene_img(), 0, 1, 1.0, [Query("nomau", None), Query("nho", np.zeros((50, 50, 3), np.uint8),
                                                                              Box(0, 0, 10, 10))])
    assert [o.status for o in r.outcomes] == [Status.UNKNOWN, Status.UNKNOWN]
    bad = svc.process_raw(np.zeros((5, 5), np.uint8), 0, 2, 2.0, [Query("x", None)])
    assert not bad.frame_valid and bad.outcomes[0].status is Status.UNKNOWN
    assert len(svc.buffer) == 1                                              # khung hong khong vao bo nho dem


def test_service_orb_only_when_template_not_confirmed() -> None:
    img = scene_img()
    tpl = img[BOX.y:BOX.y + BOX.h, BOX.x:BOX.x + BOX.w].copy()
    roi = Box(150, 350, 160, 150)
    svc = make_service(orb=True)
    assert "orb_runs" not in svc.process_raw(img, 0, 1, 1.0, [Query("x", tpl, roi)]).stats      # da CONFIRMED -> bo ORB
    occ = img.copy()
    occ[BOX.y:BOX.y + 35, BOX.x:BOX.x + 40] = 128
    r = svc.process_raw(occ, 0, 2, 2.0, [Query("x", tpl, roi)])
    assert r.stats.get("orb_runs") == 1.0


class FakeScene:
    def __init__(self) -> None:
        self.calls = 0

    def classify(self, frame: ImageFrame) -> str | None:
        self.calls += 1
        return "city"


def test_scene_analyzer_caches_by_digest_and_service_uses_it() -> None:
    fs = FakeScene()
    sa = SceneAnalyzer(fs)
    f = ImageFrame(scene_img(), FrameId(0, 1), 0.0)
    assert sa.analyze(f) == "city" and sa.analyze(f) == "city" and fs.calls == 1
    assert SceneAnalyzer(None).analyze(f) is None
    assert make_service(False).with_scene(fs).process(f, []).scene == "city"


# ---------------------------------------------------------------- cau noi World Model
class InnerSource:
    def fact(self, account: int, key: str) -> Fact[object] | None:
        return Fact(7, "legacy", 1.0) if key == "hq_level" else None

    def marches(self, account: int) -> None:
        return None

    def return_gaps(self, account: int) -> list[float]:
        return []


def result(*outs: Outcome, valid: bool = True) -> PerceptionResult:
    return PerceptionResult(FrameId(0, 1), 50.0, valid, outcomes=outs)


def test_fact_source_mapping() -> None:
    d = det("btn", Box(0, 0, 9, 9), "t", 1.0)
    r = result(Outcome("btn", Status.CONFIRMED, d, "", 0.97), Outcome("gone", Status.NOT_DETECTED, None, "", 0.04),
               Outcome("maybe", Status.UNCERTAIN, d, "", 0.5), Outcome("unk", Status.UNKNOWN))
    src = PerceptionFactSource(InnerSource(), lambda acc: r)
    f = src.fact(0, "perception:btn")
    assert f is not None and f.value is True and f.confidence == 0.97 and f.source == "perception"
    assert f.observed_at == 50.0
    g = src.fact(0, "perception:gone")
    assert g is not None and g.value is False and g.confidence == pytest.approx(0.96)
    assert src.fact(0, "perception:maybe") is None   # chua biet != vang mat
    assert src.fact(0, "perception:unk") is None
    assert src.fact(0, "perception:never_asked") is None
    assert src.fact(0, "hq_level").value == 7                                                       # type: ignore[union-attr]
    assert src.marches(0) is None and src.return_gaps(0) == []
    assert PerceptionFactSource(InnerSource(), lambda a: result(valid=False)).fact(0, "perception:btn") is None
    assert PerceptionFactSource(InnerSource(), lambda a: None).fact(0, "perception:btn") is None


def test_adaptive_frequency_skips_identical_frames_only() -> None:
    img = scene_img()
    tpl = img[BOX.y:BOX.y + BOX.h, BOX.x:BOX.x + BOX.w].copy()
    roi = Box(150, 350, 160, 150)
    svc = PerceptionService(TemplateDetector(), FeatureFusionEngine(MODEL), ConfidenceEvaluator(0.9, 0.1),
                            FrameBuffer(10), ServiceConfig(skip_below=1.0))
    q = [Query("x", tpl, roi)]
    r1 = svc.process_raw(img, 0, 1, 1.0, q)
    r2 = svc.process_raw(img.copy(), 0, 2, 2.0, q)
    assert "skipped" not in r1.stats and r2.stats["skipped"] == 1.0 and r2.outcomes == r1.outcomes
    r3 = svc.process_raw(scene_img(9), 0, 3, 3.0, q)                          # khung khac han -> chay lai
    assert "skipped" not in r3.stats and r3.outcomes[0].status is Status.NOT_DETECTED
    r4 = svc.process_raw(scene_img(9), 0, 4, 4.0, [Query("y", tpl, roi)])       # cau hoi doi -> khong dung lai
    assert "skipped" not in r4.stats


def test_adaptive_skip_does_not_hide_small_local_change_inside_roi() -> None:
    img = scene_img()
    tpl = img[BOX.y:BOX.y + BOX.h, BOX.x:BOX.x + BOX.w].copy()
    roi = Box(150, 350, 160, 150)
    svc = make_service(orb=False, skip=1.0)
    svc.process_raw(img, 0, 1, 1.0, [Query("x", tpl, roi)])
    gone = img.copy()
    gone[BOX.y:BOX.y + BOX.h, BOX.x:BOX.x + BOX.w] = 0                      # vat bien mat: chi ~1 % man hinh doi
    r = svc.process_raw(gone, 0, 2, 2.0, [Query("x", tpl, roi)])
    assert "skipped" not in r.stats and r.outcomes[0].status is not Status.CONFIRMED


def test_secondary_detector_cannot_confirm_alone() -> None:
    """Ca that tu shadow: template yeu (0,55) + ORB manh khong duoc thanh CONFIRMED."""
    eng = FeatureFusionEngine(MODEL)
    weak, strong = det("x", Box(0, 0, 40, 40), "template_ms", 0.55), det("x", Box(1, 1, 40, 40), "orb", 30)
    cand = CandidateMerger().merge([weak, strong])[0]
    d = eng.fuse(cand)
    assert d.confidence is not None and d.confidence > 0.9                      # hop nhat bi ORB day cao
    strict = ConfidenceEvaluator(0.9, 0.1).judge("x", [d], True)
    assert strict.status is Status.UNCERTAIN and "chua ung ho" in strict.reason
    assert ConfidenceEvaluator(0.9, 0.1, primary=None).judge("x", [d], True).status is Status.CONFIRMED


def test_service_reports_red_dots_with_geometry() -> None:
    img = np.full((960, 540, 3), 60, np.uint8)
    cv2.circle(img, (100, 200), 9, (30, 30, 235), -1)               # cham do (BGR)
    cv2.circle(img, (100, 200), 3, (255, 255, 255), -1)             # so trang ben trong
    cv2.rectangle(img, (300, 300), (360, 312), (30, 30, 235), -1)   # thanh do dai: khong phai cham
    cv2.circle(img, (400, 500), 40, (30, 30, 235), -1)              # mang do lon: khong phai cham
    r = make_service(False).with_badges(RedDotDetector()).process_raw(img, 2, 1, 1.0, [])
    dots = [d for d in r.detections if d.cls == "reddot"]
    assert r.stats["reddots"] == 1.0 and len(dots) == 1
    x, y = dots[0].position
    assert abs(x - 100) <= 2 and abs(y - 200) <= 2 and dots[0].features["circularity"] > 0.8
    assert dots[0].evidence[0].detector == "badge_color" and dots[0].confidence is None
