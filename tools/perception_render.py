"""Dung lai anh phu ket qua (offline, tu khung da luu boi perception_observe.py) bang bo nhan dien HIEN TAI:
mau `common/` (hop nhat) + cham do (RedDotDetector) + man hinh (identify cu). Ghi <run>/render/*.jpg + render.json.

  python tools/perception_render.py logs/perception_live/i2_20261122
"""
import glob
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402

from aowbot.infrastructure.legacy.scene import LegacySceneClassifier  # noqa: E402
from aowbot.perception.calibration import FusionModel  # noqa: E402
from aowbot.perception.contract import Status  # noqa: E402
from aowbot.perception.core.buffer import FrameBuffer  # noqa: E402
from aowbot.perception.detectors.badge import RedDotDetector  # noqa: E402
from aowbot.perception.detectors.orb import OrbDetector  # noqa: E402
from aowbot.perception.detectors.template import TemplateDetector  # noqa: E402
from aowbot.perception.eval.dataset import Box  # noqa: E402
from aowbot.perception.fusion import ConfidenceEvaluator, FeatureFusionEngine  # noqa: E402
from aowbot.perception.service import PerceptionService, Query, ServiceConfig  # noqa: E402
from bot import screens  # noqa: E402
from bot.badges import red_dots  # noqa: E402
from bot.vision import Vision  # noqa: E402

SHOW_UNCERTAIN_P = 0.5       # chi VE o UNCERTAIN co p >= nguong nay (de doc); moi o van nam trong render.json


def make_service(v):
    model = FusionModel.from_json(open(os.path.join(BASE, "config", "perception_calibration.json"), encoding="utf8").read())
    svc = PerceptionService(TemplateDetector(), FeatureFusionEngine(model),
                            ConfidenceEvaluator(model.thresholds["confirm_p"], model.thresholds["reject_p"]),
                            FrameBuffer(10), ServiceConfig(skip_below=None))
    return svc.with_orb(OrbDetector()).with_badges(RedDotDetector()).with_scene(LegacySceneClassifier(v))


def draw(img, r, legacy_dots):
    out = img.copy()
    for o in r.outcomes:
        d = o.detection
        if d is None or (o.status is Status.UNCERTAIN and (o.p or 0) < SHOW_UNCERTAIN_P):
            continue
        b = d.box
        c = (0, 200, 0) if o.status is Status.CONFIRMED else (0, 200, 255)
        cv2.rectangle(out, (b.x, b.y), (b.x + b.w, b.y + b.h), c, 2)
        cv2.putText(out, f"{o.cls.split('/')[-1]} {o.p:.2f}", (b.x, max(12, b.y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1,
                    cv2.LINE_AA)
    for d in r.detections:
        if d.cls == "reddot":
            cx, cy = d.position
            cv2.circle(out, (cx, cy), 17, (255, 0, 255), 2)
    for (x, y) in legacy_dots:
        cv2.drawMarker(out, (x, y), (255, 255, 0), cv2.MARKER_CROSS, 8, 1)
    cv2.rectangle(out, (0, 930), (540, 960), (0, 0, 0), -1)
    n = sum(1 for d in r.detections if d.cls == "reddot")
    cv2.putText(out, f"scene={r.scene} reddot={n} (cu={len(legacy_dots)})", (6, 951), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 1, cv2.LINE_AA)
    return out


def main():
    run = sys.argv[1]
    v = Vision(os.path.join(BASE, "templates"), 0.82)
    names = v.list("common/")
    svc = make_service(v)
    os.makedirs(os.path.join(run, "render"), exist_ok=True)
    rows = []
    files = [f for f in sorted(glob.glob(os.path.join(run, "frames", "*.jpg"))) if not f.endswith("_p.jpg")]
    for i, f in enumerate(files):
        img = cv2.imread(f)
        qs = [Query(n, v.load(n, probe=True), Box(*screens.ROI[n]) if n in screens.ROI else None) for n in names]
        t0 = time.perf_counter()
        r = svc.process_raw(img, 2, i, float(i), qs)
        ms = (time.perf_counter() - t0) * 1000
        legacy = red_dots(img)
        name = os.path.basename(f)[:-4]
        cv2.imwrite(os.path.join(run, "render", name + ".jpg"), draw(img, r, legacy), [cv2.IMWRITE_JPEG_QUALITY, 80])
        dots = [d.position for d in r.detections if d.cls == "reddot"]
        rows.append({"file": name, "scene": r.scene, "ms": round(ms, 1), "reddots": len(dots), "reddots_legacy": len(legacy),
                     "reddot_xy": dots,
                     "confirmed": [o.cls for o in r.outcomes if o.status is Status.CONFIRMED],
                     "uncertain": {o.cls: round(o.p, 2) for o in r.outcomes if o.status is Status.UNCERTAIN and o.p}})
    json.dump(rows, open(os.path.join(run, "render.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} khung; reddot moi={sum(r['reddots'] for r in rows)} cu={sum(r['reddots_legacy'] for r in rows)}")


if __name__ == "__main__":
    main()
