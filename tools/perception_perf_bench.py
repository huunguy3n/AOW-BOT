"""Benchmark hieu nang + shadow offline (Phase 5/6). CHI DOC anh da luu, khong dung may that, khong ghi memory.db.

A) Do tre / CPU / bo nho tren khung that: legacy Vision.find (ROI nhu screens.py) vs PerceptionService
   (template da ty le ROI-first; + ORB co dieu kien). Do ca toan man (khong ROI) de thay chi phi da ty le.
B) Shadow offline: legacy 'tim thay >= 0,82' so voi Outcome moi tren CUNG khung/lop -> ma tran dong y/lech + vi du lech
   (ghi data/perception/shadow.jsonl). KHONG co nhan nguoi: lech != sai, chi la cho can nguoi xem.
C) Tan suat thich nghi: tren cap khung before/after cua nguoi choi (logs/human): ti le cap 'gan giong' (diff thumb < th)
   ma ket qua cau hoi LAI KHAC nhau -> chon nguong an toan.

  python -u tools/perception_perf_bench.py [--frames 40] [--prefix common/] [--pairs 150]
"""
import argparse
import ctypes
import glob
import json
import os
import sys
import time
import tracemalloc
from ctypes import wintypes

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from aowbot.perception.calibration import FusionModel  # noqa: E402
from aowbot.perception.contract import FrameId, Status  # noqa: E402
from aowbot.perception.core.buffer import FrameBuffer  # noqa: E402
from aowbot.perception.core.frame import ImageFrame  # noqa: E402
from aowbot.perception.detectors.orb import OrbDetector  # noqa: E402
from aowbot.perception.detectors.template import TemplateDetector  # noqa: E402
from aowbot.perception.eval.dataset import Box  # noqa: E402
from aowbot.perception.fusion import ConfidenceEvaluator, FeatureFusionEngine  # noqa: E402
from aowbot.perception.service import PerceptionService, Query, ServiceConfig  # noqa: E402
from bot import screens  # noqa: E402
from bot.vision import Vision  # noqa: E402

CONF = os.path.join(BASE, "config", "perception_calibration.json")


def rss_mb():
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    h = ctypes.windll.kernel32.GetCurrentProcess()
    ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
    return pmc.WorkingSetSize / 1e6, pmc.PeakWorkingSetSize / 1e6


def frames_of(n):
    fs = sorted(glob.glob(os.path.join(BASE, "tests", "fixtures", "**", "*.png"), recursive=True))
    out = []
    for f in fs:
        im = cv2.imread(f, cv2.IMREAD_COLOR)
        if im is not None and im.shape[:2] == (960, 540):
            out.append(im)
    return out[:n]


def make_service(orb, skip=None):
    model = FusionModel.from_json(open(CONF, encoding="utf8").read())
    ev = ConfidenceEvaluator(model.thresholds["confirm_p"], model.thresholds["reject_p"])
    svc = PerceptionService(TemplateDetector(), FeatureFusionEngine(model), ev, FrameBuffer(10), ServiceConfig(skip_below=skip))
    return svc.with_orb(OrbDetector()) if orb else svc


def measure(label, fn, frames):
    """fn(frame_index, bgr). -> p50/p95 ms, cpu ms/khung, RSS tang (MB), dinh bo nho python (MB)."""
    tracemalloc.start()
    r0, _ = rss_mb()
    lat = []
    c0 = time.process_time()
    for i, im in enumerate(frames):
        t = time.perf_counter()
        fn(i, im)
        lat.append((time.perf_counter() - t) * 1000)
    cpu = (time.process_time() - c0) * 1000 / len(frames)
    r1, peak = rss_mb()
    _, py_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    out = {"label": label, "p50_ms": float(np.percentile(lat, 50)), "p95_ms": float(np.percentile(lat, 95)),
           "cpu_ms_per_frame": cpu, "rss_delta_mb": r1 - r0, "py_peak_mb": py_peak / 1e6}
    print(json.dumps({k: (round(v, 1) if isinstance(v, float) else v) for k, v in out.items()}), flush=True)
    return out


def part_a(args):
    v = Vision(os.path.join(BASE, "templates"), 0.82)
    names = v.list(args.prefix)
    tpls = {n: v.load(n, probe=True) for n in names}
    frames = frames_of(args.frames)
    print(f"A) {len(frames)} khung x {len(names)} lop ({args.prefix}*)", flush=True)
    rois = {n: screens.ROI.get(n) for n in names}
    q_roi = [Query(n, tpls[n], Box(*r) if r else None) for n, r in rois.items()]
    q_full = [Query(n, tpls[n], None) for n in names]
    res = []
    res.append(measure("legacy ROI(screens.py)", lambda i, im: [v.find(im, n, roi=rois[n]) for n in names], frames))
    res.append(measure("legacy toan man", lambda i, im: [v.find(im, n) for n in names], frames))
    s1, s2, s3 = make_service(False), make_service(True), make_service(True, skip=1.0)
    res.append(measure("service ms ROI", lambda i, im: s1.process_raw(im, 0, i, float(i), q_roi), frames))
    res.append(measure("service ms+orb ROI", lambda i, im: s2.process_raw(im, 0, i, float(i), q_roi), frames))
    res.append(measure("service ms toan man", lambda i, im: make_service(False).process_raw(im, 0, i, float(i), q_full), frames[:max(5, len(frames) // 4)]))
    res.append(measure("service ms+orb ROI + skip 1.0 (khung lap)", lambda i, im: s3.process_raw(im, 0, i, float(i // 2), q_roi),
                       [f for f in frames for _ in (0, 1)]))
    return res


def part_b(args):
    v = Vision(os.path.join(BASE, "templates"), 0.82)
    names = v.list(args.prefix)
    svc = make_service(True)
    frames = frames_of(args.frames)
    mat, ex = {}, []
    path = os.path.join(BASE, "data", "perception", "shadow.jsonl")
    with open(path, "w", encoding="utf8") as fh:
        for i, im in enumerate(frames):
            qs = [Query(n, v.load(n, probe=True), Box(*screens.ROI[n]) if n in screens.ROI else None) for n in names]
            r = svc.process_raw(im, 0, i, float(i), qs)
            for q, o in zip(qs, r.outcomes, strict=True):
                old = v.find(im, q.cls, roi=screens.ROI.get(q.cls)) is not None
                key = f"legacy={'found' if old else 'absent'} | new={o.status.value}"
                mat[key] = mat.get(key, 0) + 1
                disagree = (old and o.status is Status.NOT_DETECTED) or (not old and o.status is Status.CONFIRMED)
                if disagree:
                    row = {"frame": r.frame_digest, "cls": q.cls, "legacy": old, "new": o.status.value, "p": o.p, "reason": o.reason}
                    fh.write(json.dumps(row) + "\n")
                    ex.append(row)
    print("B)", json.dumps(mat, indent=1), f"\n  lech cho nguoi xem: {len(ex)} -> {path}", flush=True)
    return {"matrix": mat, "disagreements": len(ex)}


def part_c(args):
    v = Vision(os.path.join(BASE, "templates"), 0.82)
    names = v.list(args.prefix)[:12]
    svc = make_service(False)
    pairs = sorted(glob.glob(os.path.join(BASE, "logs", "human", "*", "*_before.png")))[::7][:args.pairs]
    rows = []
    for b in pairs:
        a = b.replace("_before", "_after")
        if not os.path.exists(a):
            continue
        ib, ia = cv2.imread(b), cv2.imread(a)
        if ib is None or ia is None or ib.shape != (960, 540, 3) or ia.shape != (960, 540, 3):
            continue
        qs = [Query(n, v.load(n, probe=True), Box(*screens.ROI[n]) if n in screens.ROI else None) for n in names]
        ob = [o.status for o in svc.process_raw(ib, 0, 0, 0.0, qs).outcomes]
        oa = [o.status for o in svc.process_raw(ia, 0, 1, 1.0, qs).outcomes]
        d = float(np.abs(ImageFrame(ib, FrameId(0, 0)).thumb().astype(np.int16) - ImageFrame(ia, FrameId(0, 1)).thumb()).mean())
        rows.append((d, ob != oa))
    out = {}
    for th in (0.25, 0.5, 1.0, 2.0):
        sk = [(d, ch) for d, ch in rows if d < th]
        out[str(th)] = {"pairs_skipped": len(sk), "of": len(rows), "outcomes_changed_when_skipped": sum(ch for _, ch in sk)}
    print("C)", json.dumps(out), flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--prefix", default="common/")
    ap.add_argument("--pairs", type=int, default=150)
    ap.add_argument("--part", default="abc")
    ap.add_argument("--out", default=os.path.join(BASE, "data", "perception", "perf_results.json"))
    a = ap.parse_args()
    res = {}
    if "a" in a.part:
        res["A"] = part_a(a)
    if "b" in a.part:
        res["B"] = part_b(a)
    if "c" in a.part:
        res["C"] = part_c(a)
    json.dump(res, open(a.out, "w", encoding="utf8"), indent=1)
    print("ghi", a.out)


if __name__ == "__main__":
    main()
