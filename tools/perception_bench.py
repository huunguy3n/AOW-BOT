"""Benchmark nhan dien: chay Vision (legacy) tren dataset nhan tay, in P/R/F1/FPR theo lop + do tre.

  python tools/perception_bench.py data/perception/v0/manifest.json --split test [--th 0.82] [--json out.json]

Chi doc anh da luu (khong dung may that). Dataset: docs/perception/dataset-schema.md.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402

from aowbot.perception.eval import dataset as ds  # noqa: E402
from aowbot.perception.eval import metrics as m  # noqa: E402
from bot.vision import Vision  # noqa: E402


def legacy_predict(v, img, classes):
    """([Prediction], [do tre ms]). Lop khong co anh mau -> khong du doan (khong tinh la 'khong thay')."""
    out, lat = [], []
    for c in classes:
        t = v.load(c, probe=True)
        if t is None:
            continue
        t0 = time.perf_counter()
        hit = v.find(img, c)
        lat.append((time.perf_counter() - t0) * 1000)
        if hit:
            h, w = t.shape[:2]
            out.append(m.Prediction(c, ds.Box(hit[0] - w // 2, hit[1] - h // 2, w, h), hit[2]))
    return out, lat


def run(manifest, split, th, iou_th=0.5):
    data = ds.load(Path(manifest))
    root = Path(manifest).parent
    errs = ds.validate(data) + ds.verify_files(data, root, data.in_split(split))
    if errs:
        raise SystemExit("dataset loi:\n  " + "\n  ".join(errs[:20]))
    v = Vision(os.path.join(BASE, "templates"), th)
    covered = [c for c in data.classes if v.has(c)]
    samples = data.in_split(split)
    preds, lats = {}, []
    for s in samples:
        img = cv2.imread(str(root / s.path), cv2.IMREAD_COLOR)
        preds[s.id], lat = legacy_predict(v, img, covered)
        lats += lat
    rep = m.evaluate(samples, preds, covered, iou_th)
    return data, covered, rep, m.latency(lats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--split", default="test", choices=ds.SPLITS)
    ap.add_argument("--th", type=float, default=0.82)
    ap.add_argument("--json")
    a = ap.parse_args()
    data, covered, rep, lat = run(a.manifest, a.split, a.th)
    f = lambda x: "  -  " if x is None else f"{x:5.3f}"  # noqa: E731
    print(f"dataset {data.version} split={a.split} mau={rep.n_samples} "
          f"lop co anh mau={len(covered)}/{len(data.classes)}")
    print(f"{'lop':34} {'P':>5} {'R':>5} {'F1':>5} {'FPR':>5}  tp fp fn")
    for c, s in rep.per_class.items():
        print(f"{c:34} {f(s.precision)} {f(s.recall)} {f(s.f1)} {f(s.fpr)}  {s.tp} {s.fp} {s.fn}")
    print(f"macro P={f(rep.macro('precision'))} R={f(rep.macro('recall'))} F1={f(rep.macro('f1'))}")
    print(f"do tre moi lan tim (ms): p50={lat['p50']} p95={lat['p95']} n={int(lat['n'])}")
    if a.json:
        Path(a.json).write_text(json.dumps({
            "dataset": data.version, "split": a.split, "threshold": a.th, "latency_ms": lat,
            "per_class": {c: vars(s) | {"precision": s.precision, "recall": s.recall, "f1": s.f1, "fpr": s.fpr}
                          for c, s in rep.per_class.items()},
            "confusion": rep.confusion}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
