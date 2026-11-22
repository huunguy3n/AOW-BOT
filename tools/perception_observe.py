"""Quan sat CHI-DOC mot may LDPlayer dang chay: chup khung lien tuc (adb screencap), chay PerceptionService (khong cham,
khong gui phim, khong ghi memory.db), luu khung khi man hinh doi + ban ve ket qua + dong thoi gian JSON.

  python tools/perception_observe.py --idx 2 --out logs/perception_live/<ten> [--until-pid PID] [--max-frames 160]

Dung ADB giong bot (exec-out screencap) nen khong can quyen them. Khong bat/tat may, khong mo game.
"""
import argparse
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

from aowbot.infrastructure.legacy.scene import LegacySceneClassifier  # noqa: E402
from aowbot.perception.calibration import FusionModel  # noqa: E402
from aowbot.perception.contract import Status  # noqa: E402
from aowbot.perception.core.buffer import FrameBuffer  # noqa: E402
from aowbot.perception.detectors.orb import OrbDetector  # noqa: E402
from aowbot.perception.detectors.template import TemplateDetector  # noqa: E402
from aowbot.perception.eval.dataset import Box  # noqa: E402
from aowbot.perception.fusion import ConfidenceEvaluator, FeatureFusionEngine  # noqa: E402
from aowbot.perception.service import PerceptionService, Query, ServiceConfig  # noqa: E402
from bot import screens  # noqa: E402
from bot.device import Device  # noqa: E402
from bot.vision import Vision  # noqa: E402

COLORS = {Status.CONFIRMED: (0, 200, 0), Status.UNCERTAIN: (0, 200, 255)}


def pid_alive(pid):
    if not pid:
        return True
    import subprocess
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True).stdout
    return str(pid) in out


def draw(img, result):
    out = img.copy()
    for o in result.outcomes:
        d = o.detection
        if d is None:
            continue
        b = d.box
        c = COLORS.get(o.status, (0, 0, 255))
        cv2.rectangle(out, (b.x, b.y), (b.x + b.w, b.y + b.h), c, 2)
        cv2.putText(out, f"{o.cls.split('/')[-1]} {o.p:.2f}" if o.p is not None else o.cls, (b.x, max(12, b.y - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1, cv2.LINE_AA)
    cv2.putText(out, f"{result.scene or '?'}", (6, 950), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2, cv2.LINE_AA)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idx", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--until-pid", type=int, default=0)
    ap.add_argument("--max-frames", type=int, default=160)
    ap.add_argument("--poll", type=float, default=0.8)
    ap.add_argument("--diff", type=float, default=1.5)
    ap.add_argument("--heartbeat", type=float, default=20.0)
    ap.add_argument("--max-seconds", type=float, default=7200)
    ap.add_argument("--prefix", default="common/")
    ap.add_argument("--png", action="store_true", help="luu PNG goc (cat anh mau); mac dinh JPEG q72")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(os.path.join(BASE, "config.yaml"), encoding="utf8"))
    dev = Device(cfg["ldplayer"]["adb"], a.idx)
    v = Vision(os.path.join(BASE, "templates"), 0.82)
    names = v.list(a.prefix)
    model = FusionModel.from_json(open(os.path.join(BASE, "config", "perception_calibration.json"), encoding="utf8").read())
    svc = PerceptionService(TemplateDetector(), FeatureFusionEngine(model),
                            ConfidenceEvaluator(model.thresholds["confirm_p"], model.thresholds["reject_p"]),
                            FrameBuffer(10), ServiceConfig(skip_below=None))
    svc.with_orb(OrbDetector()).with_scene(LegacySceneClassifier(v))
    os.makedirs(os.path.join(a.out, "frames"), exist_ok=True)
    tl = open(os.path.join(a.out, "timeline.jsonl"), "a", encoding="utf8")
    last_thumb, last_save, seq, saved, t_start = None, 0.0, 0, 0, time.time()
    gone = 0
    print(f"quan sat #{a.idx}: {len(names)} lop {a.prefix}*; ghi {a.out}", flush=True)
    while time.time() - t_start < a.max_seconds and saved < a.max_frames:
        if a.until_pid and not pid_alive(a.until_pid):
            gone += 1
            if gone > 3:
                break
        try:
            img = dev.screencap(tries=1, _reconnect=False)
        except Exception:
            time.sleep(2.0)
            continue
        seq += 1
        thumb = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (54, 96), interpolation=cv2.INTER_AREA).astype(np.int16)
        diff = 99.0 if last_thumb is None else float(np.abs(thumb - last_thumb).mean())
        now = time.time()
        if diff >= a.diff or now - last_save >= a.heartbeat:
            queries = [Query(n, v.load(n, probe=True), Box(*screens.ROI[n]) if n in screens.ROI else None) for n in names]
            t0 = time.perf_counter()
            r = svc.process_raw(img, a.idx, seq, now, queries)
            lat = (time.perf_counter() - t0) * 1000
            t1 = time.perf_counter()
            legacy = {n: v.find(img, n, roi=screens.ROI.get(n)) is not None for n in names}
            lat_legacy = (time.perf_counter() - t1) * 1000
            name = f"{saved:04d}_{time.strftime('%H%M%S', time.localtime(now))}"
            cv2.imwrite(os.path.join(a.out, "frames", name + (".png" if a.png else ".jpg")), img, [cv2.IMWRITE_JPEG_QUALITY, 72])
            cv2.imwrite(os.path.join(a.out, "frames", name + "_p.jpg"), draw(img, r), [cv2.IMWRITE_JPEG_QUALITY, 72])
            row = {"n": saved, "t": now, "clock": time.strftime("%H:%M:%S", time.localtime(now)), "file": name,
                   "diff": round(diff, 2), "scene": r.scene, "digest": r.frame_digest,
                   "new": {o.cls: {"status": o.status.value, "p": None if o.p is None else round(o.p, 3)}
                           for o in r.outcomes if o.status in (Status.CONFIRMED, Status.UNCERTAIN)},
                   "legacy_found": [n for n, f in legacy.items() if f],
                   "ms_new": round(lat, 1), "ms_legacy": round(lat_legacy, 1), "events": [e.kind + ":" + e.cls for e in r.events]}
            tl.write(json.dumps(row, ensure_ascii=False) + "\n")
            tl.flush()
            saved += 1
            last_thumb, last_save = thumb, now
            if saved % 10 == 0:
                print(f"  {saved} khung, scene={r.scene}", flush=True)
        time.sleep(a.poll)
    print(f"xong: {saved} khung luu, {seq} lan chup, {time.time() - t_start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
