"""Benchmark Phase 3 (chi doc anh da luu). Dung neo cua Phase 2 (data/perception/phase2_anchors.json).

A) Pham vi ap dung cua ORB: bao nhieu mau co du diem dac trung (edgeThreshold 31 mac dinh vs 15).
B) Che khuat / mo / nhieu / vang mat: template_ms vs ORB (quet min_inliers), ROI-first (+-40 px quanh cho dung).
   retention = phat hien dung cho (tam lech <= 8 px) va (ms: diem >= 0,82 | orb: inlier >= min_inliers)
   FP = tren khung da inpaint mau (vang mat), ROI = cung cua so quanh cho cu: co phat hien khong.
C) shape: tong hop co dap an (IoU >= 0,5) + doi chieu cham do that voi bot.badges.red_dots tren fixtures.

  python -u tools/perception_phase3_bench.py [--part abc] [--out data/perception/phase3_results.json]
"""
import argparse
import glob
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from aowbot.perception.contract import FrameId  # noqa: E402
from aowbot.perception.core.frame import ImageFrame  # noqa: E402
from aowbot.perception.detectors.orb import OrbDetector, OrbParams  # noqa: E402
from aowbot.perception.detectors.shape import ShapeParams, binarize, blobs, clean  # noqa: E402
from aowbot.perception.detectors.template import TemplateDetector  # noqa: E402
from aowbot.perception.eval.dataset import Box  # noqa: E402
from aowbot.perception.eval.metrics import iou  # noqa: E402

ANCH = os.path.join(BASE, "data", "perception", "phase2_anchors.json")
WIN = 40
INL_GRID = (6, 8, 10, 12, 15)


def load():
    anchors = json.load(open(ANCH, encoding="utf8"))
    tpls = {a["tpl"]: cv2.imread(os.path.join(BASE, "templates", a["tpl"] + ".png"), cv2.IMREAD_COLOR) for a in anchors}
    frames = {a["frame"]: cv2.imread(os.path.join(BASE, a["frame"]), cv2.IMREAD_COLOR) for a in anchors}
    return anchors, tpls, frames


def occlude(frac):
    def f(im, box):
        x, y, w, h = box
        out = im.copy()
        ww, hh = max(1, int(w * frac ** 0.5)), max(1, int(h * frac ** 0.5))
        out[y:y + hh, x:x + ww] = im.mean((0, 1)).astype(np.uint8)
        return out
    return f


DEGS = {
    "clean": lambda im, b: im,
    "occlude25": occlude(0.25), "occlude40": occlude(0.40), "occlude60": occlude(0.60),
    "blur1.2": lambda im, b: cv2.GaussianBlur(im, (0, 0), 1.2),
    "blur2.0": lambda im, b: cv2.GaussianBlur(im, (0, 0), 2.0),
    "noise8": lambda im, b: np.clip(im + np.random.RandomState(0).normal(0, 8, im.shape), 0, 255).astype(np.uint8),
}


def inpaint(im, box):
    x, y, w, h = box
    m = np.zeros(im.shape[:2], np.uint8)
    m[y:y + h, x:x + w] = 255
    return cv2.inpaint(im, m, 3, cv2.INPAINT_TELEA)


def roi_of(box, shape):
    x, y, w, h = box
    x0, y0 = max(0, x - WIN), max(0, y - WIN)
    return Box(x0, y0, min(shape[1], x + w + WIN) - x0, min(shape[0], y + h + WIN) - y0)


def near(b, box):
    return abs((b.x + b.w / 2) - (box[0] + box[2] / 2)) <= 8 and abs((b.y + b.h / 2) - (box[1] + box[3] / 2)) <= 8


def part_a(tpls):
    out = {}
    for et in (31, 15):
        o = OrbDetector(OrbParams(edge_threshold=et, patch_size=et))
        v = np.array([len(o._features(n, cv2.cvtColor(t, cv2.COLOR_BGR2GRAY))[0]) for n, t in tpls.items()])
        out[f"edge{et}"] = {"templates": len(v), "median_kp": float(np.median(v)),
                            "applicable_ge12": int((v >= 12).sum()), "applicable_ge20": int((v >= 20).sum())}
    return out


def part_b(anchors, tpls, frames):
    ms = TemplateDetector()
    orbs = {m: OrbDetector(OrbParams(min_inliers=m)) for m in INL_GRID}
    sub = [a for a in anchors if orbs[8].applicable(a["tpl"], tpls[a["tpl"]])]
    print(f"B) neo {len(anchors)}, ORB ap dung {len(sub)}", flush=True)
    keys = ["ms"] + [f"orb{m}" for m in INL_GRID]
    res = {}
    t0 = time.time()
    for dn, dfn in DEGS.items():
        cnt = dict.fromkeys(keys, 0)
        for a in sub:
            t = tpls[a["tpl"]]
            box = (a["x"], a["y"], t.shape[1], t.shape[0])
            im = dfn(frames[a["frame"]], box)
            f = ImageFrame(im, FrameId(0, 0), 0.0)
            roi = roi_of(box, im.shape)
            d = ms.detect(f, a["tpl"], t, roi)
            cnt["ms"] += bool(d and d.evidence[0].raw_score >= 0.82 and near(d.box, box))
            for m in INL_GRID:
                d = orbs[m].detect(f, a["tpl"], t, roi)
                cnt[f"orb{m}"] += bool(d and near(d.box, box))
        res[dn] = {k: v / len(sub) for k, v in cnt.items()}
    fp = dict.fromkeys(keys, 0)
    for a in sub:
        t = tpls[a["tpl"]]
        box = (a["x"], a["y"], t.shape[1], t.shape[0])
        f = ImageFrame(inpaint(frames[a["frame"]], box), FrameId(0, 0), 0.0)
        roi = roi_of(box, f.bgr.shape)
        d = ms.detect(f, a["tpl"], t, roi)
        fp["ms"] += bool(d and d.evidence[0].raw_score >= 0.82)
        for m in INL_GRID:
            fp[f"orb{m}"] += bool(orbs[m].detect(f, a["tpl"], t, roi))
    res["absent_FP"] = {k: v / len(sub) for k, v in fp.items()}
    print(f"B) xong {time.time() - t0:.0f}s", flush=True)
    return {"n_applicable": len(sub), "n_anchors": len(anchors), "table": res}


def synth_scene(rng):
    h, w = 240, 320
    bg = cv2.GaussianBlur(rng.randint(30, 90, (h // 8, w // 8)).astype(np.uint8), (0, 0), 1)
    img = cv2.resize(bg, (w, h), interpolation=cv2.INTER_CUBIC)
    truth = []
    for _ in range(rng.randint(2, 6)):
        bw, bh = rng.randint(20, 50), rng.randint(20, 50)
        x, y = rng.randint(0, w - bw), rng.randint(0, h - bh)
        if any(iou(Box(x, y, bw, bh), t) > 0 for t in truth):
            continue
        img[y:y + bh, x:x + bw] = rng.randint(170, 240)
        truth.append(Box(x, y, bw, bh))
    return img, truth


def score_cfg(scenes, p, gain, bias):
    tp = fp = fn = 0
    noise = np.random.RandomState(1)
    for img, truth in scenes:
        g = np.clip(img.astype(np.float32) * gain + bias + noise.normal(0, 4, img.shape), 0, 255).astype(np.uint8)
        found = [b.box for b in blobs(clean(binarize(g, p), p), p)]
        used = set()
        for t in truth:
            best = max(((iou(t, f), i) for i, f in enumerate(found) if i not in used), default=(0, -1))
            if best[0] >= 0.5:
                tp += 1
                used.add(best[1])
            else:
                fn += 1
        fp += len(found) - len(used)
    return {"P": tp / max(tp + fp, 1), "R": tp / max(tp + fn, 1)}


def part_c_synth(n=200):
    rng = np.random.RandomState(3)
    cfgs = {"otsu": ShapeParams("otsu", min_area=80), "otsu+open3": ShapeParams("otsu", open_k=3, min_area=80),
            "adaptive": ShapeParams("adaptive", min_area=80), "fixed128": ShapeParams("fixed", fixed=128, min_area=80)}
    scenes = [synth_scene(rng) for _ in range(n)]
    return {f"{light}|{name}": score_cfg(scenes, p, gain, bias)
            for light, gain, bias in (("normal", 1.0, 0), ("dark", 0.5, 0), ("bright", 1.0, 40))
            for name, p in cfgs.items()}


def part_c_real():
    from bot.badges import red_dots
    fs = [cv2.imread(f) for f in glob.glob(os.path.join(BASE, "tests", "fixtures", "**", "*.png"), recursive=True)]
    fs = [f for f in fs if f is not None and f.shape[:2] == (960, 540)]
    agree = n_legacy = n_new = 0
    p = ShapeParams("fixed", fixed=1, min_area=16)
    for im in fs:
        legacy = red_dots(im)
        hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
        m = ((hsv[..., 0] <= 6) | (hsv[..., 0] >= 172)) & (hsv[..., 1] >= 170) & (hsv[..., 2] >= 190)
        found = [b for b in blobs(clean(m.astype(np.uint8) * 255, p), p)
                 if 4 <= b.box.w <= 28 and 4 <= b.box.h <= 28 and b.fill >= 0.5]
        n_legacy += len(legacy)
        n_new += len(found)
        for d in legacy:
            agree += any(abs(b.box.x + b.box.w / 2 - d[0]) <= 6 and abs(b.box.y + b.box.h / 2 - d[1]) <= 6 for b in found)
    return {"frames": len(fs), "legacy_dots": n_legacy, "cc_blobs": n_new, "legacy_found_by_cc": agree}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(BASE, "data", "perception", "phase3_results.json"))
    ap.add_argument("--part", default="abc")
    a = ap.parse_args()
    res = {}
    if "c" in a.part:
        res["C_synth"] = part_c_synth()
        res["C_real"] = part_c_real()
        print("C) xong", flush=True)
    anchors, tpls, frames = load()
    if "a" in a.part:
        res["A"] = part_a(tpls)
    if "b" in a.part:
        res["B"] = part_b(anchors, tpls, frames)
    json.dump(res, open(a.out, "w", encoding="utf8"), indent=1)
    print("ghi", a.out, flush=True)


if __name__ == "__main__":
    main()
