"""Phase 1 perception: Vision Inspector tren anh tong hop co dap an biet truoc."""
import json
from pathlib import Path

import numpy as np

from aowbot.perception.contract import Detection, Evidence, FrameId, Status
from aowbot.perception.core.frame import ImageFrame
from aowbot.perception.diagnostics.inspector import (
    InspectorParams,
    brightness_diff,
    contact_sheet,
    render_views,
    save_inspection,
)
from aowbot.perception.eval.dataset import Box
from aowbot.perception.features.contrast import local_std as local_contrast

VIEWS = ["original", "gray", "hsv", "lab", "brightness", "local_contrast", "clahe", "sobel", "canny", "detections"]


def square_frame(seq: int = 0, level: int = 200) -> ImageFrame:
    img = np.full((96, 54, 3), 40, np.uint8)
    img[30:60, 15:40] = level
    return ImageFrame(img, FrameId(3, seq), 5.0)


def test_local_contrast_zero_on_flat_high_on_edge() -> None:
    flat = np.full((40, 40), 90, np.uint8)
    assert local_contrast(flat, 9).max() < 1e-3
    step = flat.copy()
    step[:, 20:] = 190
    c = local_contrast(step, 9)
    assert c[20, 20] > 40 and c[20, 2] < 1e-3          # cao sat bien, 0 o vung phang


def test_brightness_diff_sign_and_size_check() -> None:
    a, b = np.full((4, 4), 100, np.uint8), np.full((4, 4), 130, np.uint8)
    assert brightness_diff(b, a).min() == 30 and brightness_diff(a, b).max() == -30
    try:
        brightness_diff(a, np.zeros((5, 5), np.uint8))
    except ValueError:
        return
    raise AssertionError("phai bao loi khi khac kich thuoc")


def test_views_complete_same_size_and_diff_optional() -> None:
    f = square_frame()
    v = render_views(f)
    assert list(v) == VIEWS
    assert all(img.shape == f.bgr.shape and img.dtype == np.uint8 for img in v.values())
    v2 = render_views(f, prev=square_frame(1, 100))
    assert "brightness_diff" in v2
    # vung vuong sang hon khung truoc -> kenh xanh la (index 1) > 0, kenh do = 0
    d = v2["brightness_diff"][45, 25]
    assert d[1] > 0 and d[2] == 0


def test_views_reuse_frame_cache() -> None:
    f = square_frame()
    render_views(f)
    render_views(f)
    assert f.conversions["gray"] == 1 and f.conversions["hsv"] == 1 and f.conversions["lab"] == 1


def test_sobel_and_canny_fire_on_edges_only() -> None:
    v = render_views(square_frame(), p=InspectorParams())
    assert v["sobel"][45, 27].max() == 0 and v["canny"][45, 27].max() == 0        # trong vung phang
    assert v["sobel"][30, 27].max() > 0
    assert v["canny"][28:32, 27].max() > 0


def test_detection_overlay_changes_pixels_and_sheet_layout() -> None:
    f = square_frame()
    ev = (Evidence("legacy_template", 0.9),)
    det = Detection("common/btn_x", Box(10, 25, 35, 40), Status.UNCERTAIN, ev, track_id=7)
    v = render_views(f, detections=[det])
    assert (v["detections"] != f.bgr).any() and (v["original"] == f.bgr).all()
    sheet = contact_sheet(v, cols=4, scale=0.5)
    assert sheet.shape == (3 * 48, 4 * 27, 3)           # 10 o -> 3 hang x 4 cot (thieu o duoc dem den)


def test_save_inspection_writes_traceable_report(tmp_path: Path) -> None:
    f = square_frame(9)
    det = Detection("a/b", Box(1, 2, 3, 4), Status.UNCERTAIN, (Evidence("legacy_template", 0.91, "x", {"th": 0.82}),))
    png = save_inspection(f, tmp_path, detections=[det])
    rep = json.loads((tmp_path / "i3_9.json").read_text(encoding="utf-8"))
    assert png.exists() and rep["frame_id"] == "i3#9" and rep["digest"] == f.digest
    assert rep["detections"][0]["detectors"] == ["legacy_template"]
    assert rep["detections"][0]["evidence"][0]["raw_score"] == 0.91 and rep["detections"][0]["confidence"] is None
    assert "CHUA hieu chuan" in rep["display_params_note"]
