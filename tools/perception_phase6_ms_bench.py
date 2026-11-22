"""Phase 6: chon tuy chon tang toc cho TemplateDetector bang so do (cung neo/bien doi/vung vang mat nhu Phase 2-3).

Bien the: bgr9 (hien tai) | gray9 | gray5 | gray9+early | gray9+coarse2 | gray5+early+coarse2.
Chi so: retention (dung cho + diem >= 0,82 hoac >= nguong), rank_ok (diem dung > diem cao nhat khi vang mat),
FP (vang mat bao >= 0,82), do tre ms/lan (toan man va ROI +-40 px).

  python -u tools/perception_phase6_ms_bench.py [--n 80] [--out data/perception/phase6_ms.json]
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from aowbot.perception.contract import FrameId  # noqa: E402
from aowbot.perception.core.frame import ImageFrame  # noqa: E402
from aowbot.perception.detectors.template import SCALES_5, SCALES_9, TemplateDetector, TemplateParams  # noqa: E402
from aowbot.perception.eval.dataset import Box  # noqa: E402

ANCH = os.path.join(BASE, "data", "perception", "phase2_anchors.json")
VARIANTS = {
    "bgr9": TemplateParams(SCALES_9),
    "gray9": TemplateParams(SCALES_9, gray=True),
    "gray5": TemplateParams(SCALES_5, gray=True),
    "gray9+early.95": TemplateParams(SCALES_9, gray=True, early_exit=0.95),
    "gray9+coarse2": TemplateParams(SCALES_9, gray=True, coarse=2),
    "gray5+early+coarse2": TemplateParams(SCALES_5, gray=True, early_exit=0.95, coarse=2),
}
DEGS = {
    "clean": lambda im, b: im,
    "blur1.2": lambda im, b: cv2.GaussianBlur(im, (0, 0), 1.2),
    "noise8": lambda im, b: np.clip(im + np.random.RandomState(0).normal(0, 8, im.shape), 0, 255).astype(np.uint8),
    "scale0.95": lambda im, b: cv2.resize(im, None, fx=0.95, fy=0.95),
    "scale1.05": lambda im, b: cv2.resize(im, None, fx=1.05, fy=1.05),
    "scale0.90": lambda im, b: cv2.resize(im, None, fx=0.90, fy=0.90),
    "scale1.10": lambda im, b: cv2.resize(im, None, fx=1.10, fy=1.10),
}
WIN = 40


def inpaint(im, box):
    x, y, w, h = box
    m = np.zeros(im.shape[:2], np.uint8)
    m[y:y + h, x:x + w] = 255
    return cv2.inpaint(im, m, 3, cv2.INPAINT_TELEA)


def one(a, tpl, img, variants):
    h, w = tpl.shape[:2]
    box = (a["x"], a["y"], w, h)
    hole = inpaint(img, box)
    out = {}
    for dn, dfn in DEGS.items():
        d, dh = dfn(img, box), dfn(hole, box)
        f = d.shape[1] / img.shape[1]
        tx, ty = int(a["x"] * f), int(a["y"] * f)
        roi = Box(max(0, tx - WIN), max(0, ty - WIN), min(d.shape[1], tx + int(w * f) + WIN) - max(0, tx - WIN),
                  min(d.shape[0], ty + int(h * f) + WIN) - max(0, ty - WIN))
        fp_, fh = ImageFrame(d, FrameId(0, 0), 0.0), ImageFrame(dh, FrameId(0, 1), 0.0)
        for vn, det in variants.items():
            p = det.detect(fp_, a["tpl"], tpl, roi)
            n = det.detect(fh, a["tpl"], tpl, roi)
            ok = bool(p and abs(p.box.x + p.box.w / 2 - tx - w * f / 2) <= 8 and abs(p.box.y + p.box.h / 2 - ty - h * f / 2) <= 8)
            ps = p.evidence[0].raw_score if p else -1.0
            ns = n.evidence[0].raw_score if n else -1.0
            out[(vn, dn)] = (ok and ps >= 0.82, ps > ns, ns >= 0.82)
    return out


def latency(anchors, tpls, frames, variants, n):
    res = {}
    for vn, det in variants.items():
        full, roi_t = [], []
        for a in anchors[:n]:
            tpl = tpls[a["tpl"]]
            fr = ImageFrame(frames[a["frame"]], FrameId(0, 0), 0.0)
            t = time.perf_counter()
            det.detect(fr, a["tpl"], tpl, None)
            full.append((time.perf_counter() - t) * 1000)
            h, w = tpl.shape[:2]
            roi = Box(max(0, a["x"] - WIN), max(0, a["y"] - WIN), min(540 - max(0, a["x"] - WIN), w + 2 * WIN),
                      min(960 - max(0, a["y"] - WIN), h + 2 * WIN))
            t = time.perf_counter()
            det.detect(fr, a["tpl"], tpl, roi)
            roi_t.append((time.perf_counter() - t) * 1000)
        res[vn] = {"full_p50": float(np.percentile(full, 50)), "full_p95": float(np.percentile(full, 95)),
                   "roi_p50": float(np.percentile(roi_t, 50))}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--out", default=os.path.join(BASE, "data", "perception", "phase6_ms.json"))
    a = ap.parse_args()
    anchors = json.load(open(ANCH, encoding="utf8"))
    tpls = {x["tpl"]: cv2.imread(os.path.join(BASE, "templates", x["tpl"] + ".png")) for x in anchors}
    frames = {x["frame"]: cv2.imread(os.path.join(BASE, x["frame"])) for x in anchors}
    variants = {k: TemplateDetector(params=p) for k, p in VARIANTS.items()}
    sub = anchors[:a.n]
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(lambda x: one(x, tpls[x["tpl"]], frames[x["frame"]], variants), sub))
    table = {}
    for key in rows[0]:
        arr = np.array([[r[key][0], r[key][1], r[key][2]] for r in rows], float)
        table[f"{key[0]}|{key[1]}"] = {"retention": arr[:, 0].mean(), "rank_ok": arr[:, 1].mean(), "fp": arr[:, 2].mean()}
    lat = latency(anchors, tpls, frames, variants, 30)
    json.dump({"n": len(sub), "table": table, "latency": lat}, open(a.out, "w", encoding="utf8"), indent=1)
    print("ghi", a.out, flush=True)


if __name__ == "__main__":
    main()
