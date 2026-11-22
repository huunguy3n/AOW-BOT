"""Chay tools/perception_bench.py tren dataset tong hop (mau that dan len nen nhieu): kiem duong ong end-to-end."""
import importlib.util
import os

import cv2
import numpy as np
import pytest

from aowbot.perception.eval import dataset as ds

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def bench():
    path = os.path.join(ROOT, "tools", "perception_bench.py")
    spec = importlib.util.spec_from_file_location("perception_bench", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_legacy_bench_on_synthetic_dataset(bench, tmp_path):
    cls = next(c for c in ("common/btn_close", "common/btn_x", "common/btn_back")
               if os.path.exists(os.path.join(ROOT, "templates", c + ".png")))
    tpl = cv2.imread(os.path.join(ROOT, "templates", cls + ".png"))
    th, tw = tpl.shape[:2]
    rng = np.random.default_rng(1)
    pos = rng.integers(0, 40, (540 // 6, 960 // 6, 3), dtype=np.uint8)
    pos = cv2.resize(pos, (540, 960), interpolation=cv2.INTER_NEAREST)
    neg = pos.copy()
    pos[300:300 + th, 200:200 + tw] = tpl
    (tmp_path / "images").mkdir()
    samples = []
    for i, (img, anns) in enumerate([(pos, [ds.Annotation(cls, ds.Box(200, 300, tw, th))]), (neg, [])]):
        p = tmp_path / "images" / f"{i}.png"
        cv2.imwrite(str(p), img)
        samples.append(ds.Sample(f"s{i}", f"images/{i}.png", ds.sha256_file(p), f"sess{i}", 1, "vn-2.5.16", "popup",
                                 "test", "human", True, tuple(anns)))
    data = ds.Dataset("synth", (cls,), tuple(samples))
    ds.save(data, tmp_path / "manifest.json")
    _, covered, rep, lat = bench.run(str(tmp_path / "manifest.json"), "test", 0.82)
    s = rep.per_class[cls]
    assert covered == [cls]
    assert (s.tp, s.fp, s.fn, s.fpr) == (1, 0, 0, 0.0)
    assert lat["p50"] is not None
