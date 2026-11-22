"""Phase 3: detector (template da ty le, ORB, shape) tren anh tong hop co dap an biet truoc."""
import cv2
import numpy as np
import pytest

from aowbot.perception.contract import FrameId, Status
from aowbot.perception.core.frame import ImageFrame
from aowbot.perception.detectors.orb import OrbDetector, OrbParams
from aowbot.perception.detectors.shape import ShapeParams, binarize, blobs, clean, detect_shapes
from aowbot.perception.detectors.template import TemplateDetector, TemplateParams
from aowbot.perception.eval.dataset import Box


def scene(seed: int = 0) -> np.ndarray:
    rng = np.random.RandomState(seed)
    base = rng.randint(0, 255, (960 // 2, 540 // 2, 3)).astype(np.uint8)
    img = cv2.resize(base, (540, 960), interpolation=cv2.INTER_CUBIC)
    return cv2.GaussianBlur(img, (0, 0), 0.8)


def frame_of(img: np.ndarray) -> ImageFrame:
    return ImageFrame(img, FrameId(0, 1), 1.0)


BOX = Box(200, 400, 60, 50)


def tpl_of(img: np.ndarray) -> np.ndarray:
    return img[BOX.y:BOX.y + BOX.h, BOX.x:BOX.x + BOX.w].copy()


def center(b: Box) -> tuple[float, float]:
    return b.x + b.w / 2, b.y + b.h / 2


# ---------------------------------------------------------------- template
def test_template_exact_match_and_trace() -> None:
    img = scene()
    d = TemplateDetector().detect(frame_of(img), "x", tpl_of(img))
    assert d is not None and (d.box.x, d.box.y) == (BOX.x, BOX.y)
    ev = d.evidence[0]
    assert ev.raw_score is not None and ev.raw_score > 0.99 and ev.params["scale"] == 1.0
    assert d.status is Status.UNCERTAIN and d.confidence is None and d.detectors == ("template_ms",)


def test_template_multiscale_finds_resized_object_where_single_scale_fails() -> None:
    img = scene()
    t = tpl_of(img)
    big = cv2.resize(img, None, fx=1.075, fy=1.075)[:960, :540]
    f = frame_of(big)
    ms = TemplateDetector().detect(f, "x", t)
    one = TemplateDetector((1.0,)).detect(f, "x", t)
    assert ms is not None and one is not None
    assert ms.evidence[0].raw_score > 0.9 and one.evidence[0].raw_score < 0.7             # type: ignore[operator]
    assert abs(center(ms.box)[0] - 1.075 * center(BOX)[0]) < 6


def test_template_roi_offset_and_too_small_roi() -> None:
    img = scene()
    f, t = frame_of(img), tpl_of(img)
    d = TemplateDetector().detect(f, "x", t, Box(150, 350, 160, 150))
    assert d is not None and (d.box.x, d.box.y) == (BOX.x, BOX.y)
    assert TemplateDetector().detect(f, "x", t, Box(0, 0, 20, 20)) is None
    with pytest.raises(ValueError):
        TemplateDetector(())
    with pytest.raises(ValueError):
        TemplateDetector().detect(f, "x", t[..., 0])


# ---------------------------------------------------------------- ORB
def test_orb_finds_partially_occluded_object() -> None:
    img = scene()
    t = tpl_of(img)
    occ = img.copy()
    occ[BOX.y:BOX.y + 25, BOX.x:BOX.x + 30] = 128            # che ~25 % goc tren-trai
    orb = OrbDetector(OrbParams(min_inliers=6))
    assert orb.applicable("x", t)
    d = orb.detect(frame_of(occ), "x", t, Box(150, 350, 160, 150))               # ROI-first
    assert d is not None
    assert abs(center(d.box)[0] - center(BOX)[0]) < 8 and abs(center(d.box)[1] - center(BOX)[1]) < 8
    assert d.evidence[0].detector == "orb" and d.evidence[0].raw_score >= 6      # type: ignore[operator]


def test_orb_not_applicable_on_flat_template_and_absent_object() -> None:
    orb = OrbDetector()
    flat = np.full((40, 40, 3), 90, np.uint8)
    assert not orb.applicable("flat", flat) and orb.detect(frame_of(scene()), "flat", flat) is None
    t = tpl_of(scene(0))
    assert OrbDetector().detect(frame_of(scene(5)), "x", t, Box(150, 350, 160, 150)) is None   # vang mat


# ---------------------------------------------------------------- shape
def synthetic_shapes() -> tuple[np.ndarray, list[Box]]:
    g = np.full((200, 300), 30, np.uint8)
    truth = []
    for (x, y, w, h) in [(20, 20, 60, 40), (120, 50, 30, 80), (220, 120, 50, 50)]:
        g[y:y + h, x:x + w] = 220
        truth.append(Box(x, y, w, h))
    return g, truth


def test_blobs_recover_known_rectangles_exactly() -> None:
    g, truth = synthetic_shapes()
    p = ShapeParams(method="otsu", min_area=100)
    found = blobs(clean(binarize(g, p), p), p)
    assert sorted((b.box.x, b.box.y, b.box.w, b.box.h) for b in found) == sorted((t.x, t.y, t.w, t.h) for t in truth)
    assert all(b.fill == 1.0 for b in found)


def test_circularity_distinguishes_circle_from_bar() -> None:
    g = np.zeros((120, 200), np.uint8)
    cv2.circle(g, (50, 60), 30, 255, -1)
    cv2.rectangle(g, (110, 55), (190, 65), 255, -1)
    p = ShapeParams(method="fixed", min_area=50)
    by_w = {b.box.w: b for b in blobs(binarize(g, p), p)}
    circle, bar = by_w[61], by_w[81]
    assert circle.circularity > 0.8 > bar.circularity + 0.3


def test_morphology_open_removes_speckle_close_fills_gap() -> None:
    g = np.zeros((60, 60), np.uint8)
    g[10:30, 10:30] = 255
    g[50, 50] = 255
    p0 = ShapeParams(method="fixed", min_area=1)
    assert len(blobs(binarize(g, p0), p0)) == 2
    p1 = ShapeParams(method="fixed", min_area=1, open_k=3)
    assert len(blobs(clean(binarize(g, p1), p1), p1)) == 1
    h = np.zeros((20, 40), np.uint8)
    h[:, :15] = 255
    h[:, 17:] = 255
    p2 = ShapeParams(method="fixed", min_area=1, close_k=5)
    assert len(blobs(binarize(h, ShapeParams(method="fixed", min_area=1)), p0)) == 2
    assert len(blobs(clean(binarize(h, p2), p2), p2)) == 1


def test_area_filters_and_detections_carry_params() -> None:
    g, _ = synthetic_shapes()
    dets = detect_shapes(g, "obj", ShapeParams(min_area=100, max_area=2450))
    assert len(dets) == 2                                            # bo hinh 50x50=2500; giu 60x40 va 30x80 (=2400)
    assert all(d.evidence[0].params["method"] == "otsu" and "circularity" in d.features for d in dets)


def test_color_variant_is_not_a_match_even_though_gray_is_identical() -> None:
    """Hard negative (D6) co that tu shadow 2026-11-22: X xanh vs X do cung hinh, khac mau -> xam ~giong nhau."""
    base = np.full((200, 200, 3), 40, np.uint8)
    tpl = base[:60, :60].copy()
    cv2.line(tpl, (10, 10), (50, 50), (255, 80, 80), 8)            # X "xanh" (BGR: xanh duong sang)
    cv2.line(tpl, (50, 10), (10, 50), (255, 80, 80), 8)
    scene = base.copy()
    red = tpl.copy()
    red[..., 0], red[..., 2] = tpl[..., 2], tpl[..., 0]             # hoan doi kenh: cung do sang, khac mau
    scene[70:130, 70:130] = red
    fr = frame_of(np.pad(scene, ((0, 760), (0, 340), (0, 0))))
    bgr_score = TemplateDetector(params=TemplateParams(gray=False)).detect(fr, "x", tpl)
    gray_only = cv2.matchTemplate(fr.gray, cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY), cv2.TM_CCOEFF_NORMED).max()
    d = TemplateDetector().detect(fr, "x", tpl)
    assert gray_only > 0.8 > bgr_score.evidence[0].raw_score                       # type: ignore[union-attr, operator]
    assert d is not None and d.evidence[0].raw_score < 0.8                          # xac minh mau chan duoc
    same = TemplateDetector().detect(fr, "x", red)
    assert same is not None and same.evidence[0].raw_score > 0.95
