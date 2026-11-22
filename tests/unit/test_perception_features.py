"""Phase 2: dac trung do sang / tuong phan tren anh tong hop co dap an biet truoc."""
import cv2
import numpy as np
import pytest

from aowbot.perception.features import brightness as br
from aowbot.perception.features import contrast as ct


def textured(seed: int = 0, h: int = 96, w: int = 54) -> np.ndarray:
    rng = np.random.RandomState(seed)
    base = cv2_blur(rng.randint(40, 200, (h, w)).astype(np.uint8))
    return base


def cv2_blur(a: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(a, (0, 0), 1.5)


def test_stats_known_values() -> None:
    g = np.full((10, 10), 100, np.uint8)
    s = br.stats(g)
    assert (s.mean, s.std, s.p5, s.p50, s.p95) == (100, 0, 100, 100, 100)
    with pytest.raises(ValueError):
        br.stats(np.zeros((0, 3), np.uint8))


def test_grid_means_locates_bright_cell() -> None:
    g = np.zeros((40, 40), np.uint8)
    g[0:20, 20:40] = 200
    m = br.grid_means(g, 2, 2)
    assert m.shape == (2, 2) and m[0, 1] == 200 and m[1, 0] == 0


def test_identical_frames_no_change() -> None:
    g = textured()
    c = br.detect_change(g, g.copy())
    assert (c.direction, c.global_shift, c.local) == ("none", False, False) and c.local_fraction == 0


def test_global_brightening_and_darkening() -> None:
    g = textured()
    up = np.clip(g.astype(np.int16) + 20, 0, 255).astype(np.uint8)
    c = br.detect_change(up, g)
    assert c.direction == "brighter" and c.global_shift and not c.local
    assert br.detect_change(g, up).direction == "darker"


def test_global_gain_is_not_local_change() -> None:
    g = textured()
    dim = (g.astype(np.float32) * 0.8).astype(np.uint8)
    c = br.detect_change(dim, g)
    assert c.global_shift and c.direction == "darker" and not c.local
    assert abs(c.gain - 0.8) < 0.03


def test_local_change_not_flagged_as_global() -> None:
    g = textured()
    cur = g.copy()
    cur[20:50, 10:40] = np.clip(cur[20:50, 10:40].astype(np.int16) + 80, 0, 255).astype(np.uint8)  # ~17% dien tich
    c = br.detect_change(cur, g)
    assert c.local and not c.global_shift and c.direction == "none"
    assert 0.10 < c.local_fraction < 0.25


def test_sub_quantization_noise_is_not_change() -> None:
    # sigma=1 (duoi san luong tu hoa). Nhieu lon hon: ti le bao nham phu thuoc k/min_area -> do bang benchmark Phase 2
    g = textured()
    rng = np.random.RandomState(1)
    noisy = np.clip(g.astype(np.float32) + rng.normal(0, 1, g.shape), 0, 255).astype(np.uint8)
    c = br.detect_change(noisy, g)
    assert not c.local and not c.global_shift
    assert c.noise >= br.QUANT_FLOOR


def test_adaptive_noise_floor_grows_with_noise() -> None:
    g = textured()
    rng = np.random.RandomState(2)
    lo = np.clip(g + rng.normal(0, 1, g.shape), 0, 255).astype(np.uint8)
    hi = np.clip(g + rng.normal(0, 6, g.shape), 0, 255).astype(np.uint8)
    assert br.detect_change(hi, g).noise > br.detect_change(lo, g).noise


def test_detect_change_validates_input() -> None:
    g = textured()
    with pytest.raises(ValueError):
        br.detect_change(g, g[:10])
    with pytest.raises(ValueError):
        br.detect_change(g, g, k=0)
    with pytest.raises(ValueError):
        br.detect_change(g, g, min_area=1.5)


def test_contrast_flat_vs_edge() -> None:
    flat = np.full((40, 40), 90, np.uint8)
    step = flat.copy()
    step[:, 20:] = 200
    assert ct.local_std(flat, 9).max() < 1e-3 and ct.local_std(step, 9)[20, 20] > 40
    assert ct.edge_density(flat, 80, 160) == 0 and ct.edge_density(step, 80, 160) > 0
    assert ct.sobel_magnitude(flat).max() == 0 and ct.sobel_magnitude(step).max() > 0


def test_contrast_validates_params() -> None:
    g = np.zeros((10, 10), np.uint8)
    for bad in (lambda: ct.local_std(g, 4), lambda: ct.canny_edges(g, 100, 50), lambda: ct.edge_density(g[:0], 1, 2)):
        with pytest.raises(ValueError):
            bad()


def test_contrast_summary_keys() -> None:
    s = ct.contrast_summary(textured(), 9, 80, 160)
    assert set(s) == {"local_std_mean", "sobel_mean", "edge_density", "rms_contrast"} and s["rms_contrast"] > 0
