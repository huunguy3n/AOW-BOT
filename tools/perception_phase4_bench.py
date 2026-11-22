"""Benchmark Phase 4 (theo doi): chi so MOTA / IDF1 / ID switch / RMSE tren chuoi tong hop co dap an (GT).

A) Tracker thuan: GT -> phat hien nhieu/rot/che/FP (moi canh bao co chu thich) -> so sanh
   baseline (gan gan nhat theo vi tri CU, khong mo hinh chuyen dong, bo track ngay khi mat) voi Kalman+Hungarian,
   quet (accel_sigma, gate_px, max_misses). 30 hat giong ngau nhien moi kich ban.
B) Dau-cuoi: sprite thuc di chuyen tren nen la khung fixtures that -> MotionDetector -> TrackManager,
   co/khong nhap nhay sang toan man (D8), vat tinh gay nhieu; do RMSE, ID switch, do tre.

  python -u tools/perception_phase4_bench.py [--seeds 30] [--out data/perception/phase4_results.json]
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

from aowbot.perception.contract import Detection, Evidence, FrameId, Status  # noqa: E402
from aowbot.perception.core.frame import ImageFrame  # noqa: E402
from aowbot.perception.detectors.motion import MotionDetector, MotionParams  # noqa: E402
from aowbot.perception.eval.dataset import Box  # noqa: E402
from aowbot.perception.eval.tracking_metrics import score  # noqa: E402
from aowbot.perception.tracking.assign import assign  # noqa: E402
from aowbot.perception.tracking.kalman import KalmanParams  # noqa: E402
from aowbot.perception.tracking.manager import TrackerParams, TrackManager  # noqa: E402

W, H, SZ = 540, 960, 40
DT = 0.2        # ~ chu ky screencap raw tren ADB (0,4-0,5 s) nhanh hon khi dung FrameStream


# ------------------------------------------------------------------ A) sinh chuoi
def gen_gt(rng, n, frames, crossing=False):
    """Quy dao van toc ~ khong doi + nhieu gia toc nho, bat khi cham bien. -> [n][frames] (cx, cy)."""
    out = []
    for k in range(n):
        if crossing:
            p = np.array([60.0, 300.0 + 80 * k]); v = np.array([90.0, 45.0 if k == 0 else -45.0])
        else:
            p = rng.uniform([60, 100], [W - 60, H - 100]); v = rng.uniform(-110, 110, 2)
        tr = []
        for _ in range(frames):
            v = v + rng.normal(0, 8, 2)
            p = p + v * DT
            for ax, lim in ((0, W), (1, H)):
                if not 30 < p[ax] < lim - 30:
                    v[ax] = -v[ax]
                    p[ax] = np.clip(p[ax], 30, lim - 30)
            tr.append((float(p[0]), float(p[1])))
        out.append(tr)
    return out


def box_at(c):
    return Box(int(c[0] - SZ / 2), int(c[1] - SZ / 2), SZ, SZ)


def observe(rng, gt, sm, miss, fp, occ=None):
    """Phat hien moi khung: GT + nhieu, rot p=miss, vung che `occ`=(x0,y0,x1,y1,f0,f1), FP Poisson(fp)."""
    frames = len(gt[0])
    obs = []
    for f in range(frames):
        ds = []
        for tr in gt:
            c = tr[f]
            hidden = occ and occ[4] <= f < occ[5] and occ[0] <= c[0] <= occ[2] and occ[1] <= c[1] <= occ[3]
            if hidden or rng.rand() < miss:
                continue
            ds.append(det_of((c[0] + rng.normal(0, sm), c[1] + rng.normal(0, sm))))
        for _ in range(rng.poisson(fp)):
            ds.append(det_of((rng.uniform(40, W - 40), rng.uniform(40, H - 40))))
        obs.append(ds)
    return obs


def det_of(c):
    return Detection("unit", box_at(c), Status.UNCERTAIN, (Evidence("synthetic"),))


class NearestBaseline:
    """Baseline: moi phat hien gan track GAN NHAT theo vi tri cuoi (Hungarian), khong du doan, bo track ngay khi mat,
    xac nhan ngay (mo phong cach nhin tung khung doc lap cua legacy)."""

    def __init__(self, gate):
        self.gate, self.tracks, self.nid = gate, {}, 1

    def update(self, dets):
        ids = list(self.tracks)
        cost = [[np.hypot(d.box.x + SZ / 2 - self.tracks[i][0], d.box.y + SZ / 2 - self.tracks[i][1]) for d in dets] for i in ids]
        pairs = assign(cost, self.gate) if ids and dets else []
        new, used = {}, set()
        out = []
        for ti, dj in pairs:
            c = (dets[dj].box.x + SZ / 2, dets[dj].box.y + SZ / 2)
            new[ids[ti]] = c
            used.add(dj)
            out.append((ids[ti], dets[dj].box))
        for j, d in enumerate(dets):
            if j not in used:
                new[self.nid] = (d.box.x + SZ / 2, d.box.y + SZ / 2)
                out.append((self.nid, d.box))
                self.nid += 1
        self.tracks = new
        return out


def run_kalman(obs, tp, kp):
    tm = TrackManager(tp, kp)
    hyp = []
    for i, ds in enumerate(obs):
        u = tm.update(ds, i * DT, FrameId(0, i))
        hyp.append([(d.track_id, d.box) for d in u.detections])
    return hyp


def run_baseline(obs, gate):
    nb = NearestBaseline(gate)
    return [nb.update(ds) for ds in obs]


SCEN = {
    "S1_clean": dict(n=1, sm=3, miss=0.0, fp=0.0),
    "S2_noisy_dropout": dict(n=3, sm=6, miss=0.2, fp=0.0),
    "S3_crossing": dict(n=2, sm=4, miss=0.1, fp=0.0, crossing=True),
    "S4_occlusion": dict(n=2, sm=4, miss=0.0, fp=0.0, occ=(0, 200, W, H - 200, 20, 26)),
    "S5_dense_fp": dict(n=8, sm=5, miss=0.15, fp=0.3),
}


def part_a(seeds):
    grid = [(a, g, m) for a in (20, 60, 200, 600) for g in (40, 80) for m in (3, 6)]
    names = ["baseline"] + [f"kf a={a} g={g} m={m}" for a, g, m in grid]
    res = {sc: {n: [] for n in names} for sc in SCEN}
    for sc, cfg in SCEN.items():
        for s in range(seeds):
            rng = np.random.RandomState(1000 + s)
            gt = gen_gt(rng, cfg["n"], 60, cfg.get("crossing", False))
            gtf = [[(k, box_at(tr[f])) for k, tr in enumerate(gt)] for f in range(60)]
            obs = observe(rng, gt, cfg["sm"], cfg["miss"], cfg["fp"], cfg.get("occ"))
            res[sc]["baseline"].append(score(gtf, run_baseline(obs, 80)))
            for (a, g, m), n in zip(grid, names[1:], strict=True):
                hyp = run_kalman(obs, TrackerParams(gate_px=g, confirm_hits=2, max_misses=m), KalmanParams(accel_sigma=a, meas_sigma=max(cfg["sm"], 2)))
                res[sc][n].append(score(gtf, hyp))
    table = {}
    for sc, d in res.items():
        table[sc] = {n: {"mota": float(np.mean([x.mota for x in v])), "idf1": float(np.mean([x.idf1 for x in v])),
                         "idsw": float(np.mean([x.id_switches for x in v])), "rmse": float(np.mean([x.rmse for x in v]))}
                     for n, v in d.items()}
    return table


# ------------------------------------------------------------------ B) dau-cuoi
def backgrounds():
    fs = sorted(glob.glob(os.path.join(BASE, "tests", "fixtures", "**", "*.png"), recursive=True))
    out = []
    for f in fs:
        im = cv2.imread(f, cv2.IMREAD_COLOR)
        if im is not None and im.shape[:2] == (H, W):
            out.append(im)
    return out


def render(bg, centers, rng, flicker, distractor):
    img = bg.copy()
    if distractor is not None:
        cv2.circle(img, distractor, 14, (0, 0, 255), -1)
    for c in centers:
        b = box_at(c)
        img[b.y:b.y + SZ, b.x:b.x + SZ] = (40, 200, 240)
        cv2.rectangle(img, (b.x, b.y), (b.x + SZ, b.y + SZ), (255, 255, 255), 2)
    if flicker:
        img = np.clip(img.astype(np.float32) * rng.uniform(0.85, 1.15) + rng.uniform(-15, 15), 0, 255).astype(np.uint8)
    return img


def part_b(seeds, bg_frames, min_area=40):
    bgs = backgrounds()
    md = MotionDetector(MotionParams(bg_frames=bg_frames, min_area=min_area))
    out = {}
    for name, flicker, distract in (("clean", False, False), ("flicker", True, False), ("flicker+distractor", True, True)):
        scs, lat = [], []
        for s in range(seeds):
            rng = np.random.RandomState(2000 + s)
            bg = bgs[s % len(bgs)]
            gt = gen_gt(rng, 2, 40, crossing=True)
            tm = TrackManager(TrackerParams(gate_px=80, confirm_hits=2, max_misses=4), KalmanParams(accel_sigma=200, meas_sigma=8))
            dpos = (int(rng.uniform(60, 480)), int(rng.uniform(100, 860))) if distract else None
            prev = None
            hist = []
            gtf, hyp = [], []
            for f in range(40):
                img = render(bg, [tr[f] for tr in gt], rng, flicker, dpos)
                fr = ImageFrame(img, FrameId(0, f), f * DT)
                dets = []
                if prev is not None:
                    t0 = time.perf_counter()
                    dets, _ = md.detect(fr, prev, cls="unit", history=hist)
                    lat.append((time.perf_counter() - t0) * 1000)
                u = tm.update(dets, f * DT, fr.frame_id)
                gtf.append([(k, box_at(tr[f])) for k, tr in enumerate(gt)])
                hyp.append([(d.track_id, d.box) for d in u.detections])
                prev = fr
                hist.append(fr)
            scs.append(score(gtf[3:], hyp[3:]))                    # bo 3 khung xac nhan dau
        out[name] = {"mota": float(np.mean([x.mota for x in scs])), "idf1": float(np.mean([x.idf1 for x in scs])),
                     "idsw": float(np.mean([x.id_switches for x in scs])), "rmse": float(np.mean([x.rmse for x in scs])),
                     "recall": float(np.mean([x.tp / max(x.gt, 1) for x in scs])), "motion_ms_p50": float(np.percentile(lat, 50)),
                     "motion_ms_p95": float(np.percentile(lat, 95))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--out", default=os.path.join(BASE, "data", "perception", "phase4_results.json"))
    ap.add_argument("--part", default="ab")
    ap.add_argument("--bg", type=int, default=9)
    ap.add_argument("--min-area", type=int, default=40)
    a = ap.parse_args()
    res = {}
    if "a" in a.part:
        res["A"] = part_a(a.seeds)
        print("A) xong", flush=True)
    if "b" in a.part:
        res["B"] = part_b(min(a.seeds, 12), a.bg, a.min_area)
        print("B) xong", flush=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w", encoding="utf8"), indent=1)
    print("ghi", a.out, flush=True)


if __name__ == "__main__":
    main()
