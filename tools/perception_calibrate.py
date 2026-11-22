"""Hieu chuan mo hinh hop nhat tu BENCHMARK TONG HOP (neo Phase 2 + bien doi + vung vang mat inpaint).

Sinh config/perception_calibration.json: bo hieu chuan cho template_ms / orb, trong so hop nhat (stacking),
nguong confirm_p / reject_p. Tach train/test THEO MAU (khong theo hang) de do khai quat. KHONG phai nhan nguoi:
file mang source="synthetic-anchors-v1".

  python -u tools/perception_calibrate.py [--out config/perception_calibration.json]
"""
import argparse
import json
import os
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from aowbot.perception.calibration import (  # noqa: E402
    FusionModel,
    expected_calibration_error,
    fit_calibrator,
    fit_fusion,
    logit,
)
from aowbot.perception.contract import FrameId  # noqa: E402
from aowbot.perception.core.frame import ImageFrame  # noqa: E402
from aowbot.perception.detectors.orb import OrbDetector  # noqa: E402
from aowbot.perception.detectors.template import TemplateDetector  # noqa: E402
from aowbot.perception.eval.dataset import Box  # noqa: E402

ANCH = os.path.join(BASE, "data", "perception", "phase2_anchors.json")
WIN = 40
SOURCE = "synthetic-anchors+real-negatives-v2"


def degs():
    def gamma(g):
        return lambda im, b: (255 * (im / 255.0) ** g).astype(np.uint8)

    def occl(frac):
        def f(im, b):
            x, y, w, h = b
            o = im.copy()
            o[y:y + max(1, int(h * frac ** .5)), x:x + max(1, int(w * frac ** .5))] = im.mean((0, 1)).astype(np.uint8)
            return o
        return f
    return {
        "clean": lambda im, b: im, "gamma0.7": gamma(0.7), "occl25": occl(0.25), "occl40": occl(0.40),
        "blur1.2": lambda im, b: cv2.GaussianBlur(im, (0, 0), 1.2),
        "noise8": lambda im, b: np.clip(im + np.random.RandomState(0).normal(0, 8, im.shape), 0, 255).astype(np.uint8),
        "scale0.95": lambda im, b: cv2.resize(im, None, fx=0.95, fy=0.95), "scale1.05": lambda im, b: cv2.resize(im, None, fx=1.05, fy=1.05),
    }


def inpaint(im, box):
    x, y, w, h = box
    m = np.zeros(im.shape[:2], np.uint8)
    m[y:y + h, x:x + w] = 255
    return cv2.inpaint(im, m, 3, cv2.INPAINT_TELEA)


def row_for(a, tpl, frame_img, dfn, present, ms, orb):
    h, w = tpl.shape[:2]
    box = (a["x"], a["y"], w, h)
    img = dfn(frame_img if present else inpaint(frame_img, box), box)
    f = 1.0 if img.shape == frame_img.shape else img.shape[1] / frame_img.shape[1]
    tx, ty = int(a["x"] * f), int(a["y"] * f)
    roi = Box(max(0, tx - WIN), max(0, ty - WIN), min(img.shape[1], tx + int(w * f) + WIN) - max(0, tx - WIN),
              min(img.shape[0], ty + int(h * f) + WIN) - max(0, ty - WIN))
    fr = ImageFrame(img, FrameId(0, 0), 0.0)
    d = ms.detect(fr, a["tpl"], tpl, roi)
    if d is None:
        return None
    near = abs(d.box.x + d.box.w / 2 - tx - w * f / 2) <= 8 and abs(d.box.y + d.box.h / 2 - ty - h * f / 2) <= 8
    row = {"tpl": a["tpl"], "label": int(present and near), "ms": d.evidence[0].raw_score}
    if orb.applicable(a["tpl"], tpl):
        d2 = orb.detect(fr, a["tpl"], tpl, roi)
        if d2 is not None:
            row["orb"] = d2.evidence[0].raw_score
    return row


def build_rows():
    anchors = json.load(open(ANCH, encoding="utf8"))
    tpls = {a["tpl"]: cv2.imread(os.path.join(BASE, "templates", a["tpl"] + ".png")) for a in anchors}
    frames = {a["frame"]: cv2.imread(os.path.join(BASE, a["frame"])) for a in anchors}
    ms, orb = TemplateDetector(), OrbDetector()
    D = degs()

    def work(a):
        out = []
        for dn, dfn in D.items():
            for present in (True, False):
                r = row_for(a, tpls[a["tpl"]], frames[a["frame"]], dfn, present, ms, orb)
                if r:
                    r["deg"], r["present"] = dn, present
                    out.append(r)
        return out
    with ThreadPoolExecutor(4) as ex:
        return [r for rs in ex.map(work, anchors) for r in rs]


def real_negative_rows(n_frames, max_rows):
    """Am tinh THAT: khung chay that (logs/perception_live) x moi mau. Chi nhan 0 khi mau legacy BGR khop < 0,6 (chac chan
    khong co), bo vung xam 0,6-0,9. Day la loai am tinh ma inpaint khong co (nen nhieu co diem 0,4-0,6 tren man that)."""
    import glob
    from bot import screens
    from bot.vision import Vision
    v = Vision(os.path.join(BASE, "templates"), 0.82)
    fs = [f for f in sorted(glob.glob(os.path.join(BASE, "logs", "perception_live", "*", "frames", "*.jpg")))
          if not f.endswith("_p.jpg")]
    fs = fs[::max(1, len(fs) // n_frames)][:n_frames]
    names = [n for g in sorted(os.listdir(os.path.join(BASE, "templates")))
             if os.path.isdir(os.path.join(BASE, "templates", g)) and g != "digits" for n in v.list(g + "/")
             if not n.startswith(g + "/lv/")]
    ms, orb = TemplateDetector(), OrbDetector()

    def work(f):
        img = cv2.imread(f)
        fr = ImageFrame(img, FrameId(0, 0), 0.0)
        out = []
        for n in names:
            t = v.load(n, probe=True)
            r = screens.ROI.get(n)
            b = v.best(img, n, roi=r)
            if t is None or b is None or b[2] >= 0.6:
                continue
            roi = Box(*r) if r else None
            d = ms.detect(fr, n, t, roi)
            if d is None:
                continue
            row = {"tpl": n, "label": 0, "ms": d.evidence[0].raw_score, "deg": "real", "present": False}
            if orb.applicable(n, t):
                d2 = orb.detect(fr, n, t, roi)
                if d2 is not None:
                    row["orb"] = d2.evidence[0].raw_score
            out.append(row)
        return out
    with ThreadPoolExecutor(4) as ex:
        rows = [r for rs in ex.map(work, fs) for r in rs]
    rng = np.random.RandomState(5)
    if len(rows) > max_rows:
        rows = [rows[i] for i in rng.choice(len(rows), max_rows, replace=False)]
    return rows


def is_test(tpl):
    return zlib.crc32(tpl.encode()) % 4 == 0           # ~25 % mau lam tap kiem tra (theo mau, on dinh)


def auc(scores, labels):
    s, y = np.asarray(scores), np.asarray(labels)
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(BASE, "config", "perception_calibration.json"))
    a = ap.parse_args()
    rows = build_rows()
    real = real_negative_rows(40, 2400)
    print(f"am tinh that: {len(real)} hang", flush=True)
    rows += real
    tr = [r for r in rows if not is_test(r["tpl"])]
    te = [r for r in rows if is_test(r["tpl"])]
    print(f"rows {len(rows)} train {len(tr)} test {len(te)}; pos train {sum(r['label'] for r in tr)}", flush=True)
    cal_ms = fit_calibrator("template_ms", [r["ms"] for r in tr], [r["label"] for r in tr], SOURCE)
    orb_tr = [r for r in tr if "orb" in r]
    cal_orb = fit_calibrator("orb", [r["orb"] for r in orb_tr], [r["label"] for r in orb_tr], SOURCE)
    cals = {"template_ms": cal_ms, "orb": cal_orb}

    def probs(r):
        p = {"template_ms": cal_ms.prob(r["ms"])}
        if "orb" in r:
            p["orb"] = cal_orb.prob(r["orb"])
        return p
    w, b = fit_fusion([probs(r) for r in tr], [r["label"] for r in tr], ["template_ms", "orb"], SOURCE)
    model = FusionModel(w, b, SOURCE, sum(r["label"] for r in tr), sum(1 - r["label"] for r in tr), cals)
    fp_tr = np.array([model.fused(probs(r)) for r in tr])
    y_tr = np.array([r["label"] for r in tr])
    # confirm_p: nho nhat sao cho precision >= 0,99 tren train; reject_p: lon nhat sao cho recall cua duong >= 0,99
    grid = np.unique(np.round(fp_tr, 4))
    confirm = next((t for t in grid if (y_tr[fp_tr >= t].mean() if (fp_tr >= t).any() else 0) >= 0.99), 0.99)
    reject = max([t for t in grid if (fp_tr[y_tr == 1] <= t).mean() <= 0.01] or [0.0])
    model = FusionModel(w, b, SOURCE, model.n_pos, model.n_neg, cals, {"confirm_p": float(confirm), "reject_p": float(reject)})
    fp_te = np.array([model.fused(probs(r)) for r in te])
    y_te = np.array([r["label"] for r in te])
    ms_te = np.array([r["ms"] for r in te])
    rep = {
        "rows": {"train": len(tr), "test": len(te), "test_pos": int(y_te.sum())},
        "weights": w, "bias": b, "thresholds": model.thresholds,
        "ece_test": {"ms_only": expected_calibration_error([cal_ms.prob(s) for s in ms_te], y_te),
                     "fused": expected_calibration_error(fp_te, y_te)},
        "auc_test": {"ms_raw": auc(ms_te, y_te), "fused": auc(fp_te, y_te)},
    }
    pm_te = np.array([probs(r)["template_ms"] for r in te])
    conf = (fp_te >= confirm) & (pm_te >= 0.5)         # detector chinh phai ung ho (ConfidenceEvaluator.primary_floor)
    rej = fp_te <= reject
    rep["test_at_thresholds"] = {
        "confirm_precision": float(y_te[conf].mean()) if conf.any() else None, "confirm_recall": float(conf[y_te == 1].mean()),
        "reject_misses_positive": float(rej[y_te == 1].mean()), "reject_catches_negative": float(rej[y_te == 0].mean()),
        "uncertain_rate": float((~conf & ~rej).mean())}
    legacy = ms_te >= 0.82
    rep["legacy_th0.82_on_test"] = {"precision": float(y_te[legacy].mean()) if legacy.any() else None,
                                    "recall": float(legacy[y_te == 1].mean())}
    orb_rows = [r for r in te if "orb" in r]
    if orb_rows:
        yo = np.array([r["label"] for r in orb_rows])
        rep["orb_subset_test"] = {"n": len(orb_rows), "auc_ms": auc([r["ms"] for r in orb_rows], yo),
                                  "auc_fused": auc([model.fused(probs(r)) for r in orb_rows], yo)}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf8").write(model.to_json())
    json.dump(rep, open(os.path.join(BASE, "data", "perception", "calibration_report.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1), flush=True)
    assert logit(0.5) == 0


if __name__ == "__main__":
    main()
