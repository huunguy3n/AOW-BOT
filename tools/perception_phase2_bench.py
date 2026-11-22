"""Benchmark Phase 2 (chi doc anh da luu; khong dung may that).

A) Bien the khop mau: bgr (legacy) | gray | clahe | grad (Sobel) | ms (bgr da ty le) tren moi neo that.
   Neo = (mau, khung, vi tri) co diem legacy >= 0,95 tren tests/fixtures (mau cat tu chinh khung -> LAC QUAN,
   chi do do ben voi bien doi, KHONG phai do chinh xac). Voi moi bien doi do:
     retention = ty le neo con diem >= th TAI DUNG cho (cua so +-40 px)
     rank_ok   = ty le neo ma diem tai cho dung > diem cao nhat o VUNG VANG MAT (khung da inpaint mau) -
                 khong phu thuoc nguong => so sanh cong bang giua cac bien the.
B) detect_change (do sang) tren cap khung tong hop: nhieu / toan cuc / cuc bo / chuyen dong,
   quet luoi (k, min_area) de chon gia tri mac dinh BANG SO DO.

  python -u tools/perception_phase2_bench.py [--n-neg 40] [--out data/perception/phase2_results.json]
"""
import argparse
import glob
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from aowbot.perception.features.brightness import detect_change  # noqa: E402

TH = 0.82
WIN = 40
TPL_DIR = os.path.join(BASE, "templates")
CACHE = os.path.join(BASE, "data", "perception", "phase2_anchors.json")


# ------------------------------------------------------------------ anchors
def load_templates():
    out = {}
    for f in glob.glob(os.path.join(TPL_DIR, "**", "*.png"), recursive=True):
        if "@" in os.path.basename(f):
            continue
        out[os.path.relpath(f, TPL_DIR)[:-4].replace("\\", "/")] = cv2.imread(f, cv2.IMREAD_COLOR)
    return out


def load_frames():
    fs = sorted(glob.glob(os.path.join(BASE, "tests", "fixtures", "**", "*.png"), recursive=True))
    out = []
    for f in fs:
        im = cv2.imread(f, cv2.IMREAD_COLOR)
        if im is not None and im.shape[:2] == (960, 540):
            out.append((os.path.relpath(f, BASE).replace("\\", "/"), im))
    return out


def find_anchor(name, tpl, frames):
    for fn, im in frames:
        r = cv2.matchTemplate(im, tpl, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        if mx >= 0.95:
            return {"tpl": name, "frame": fn, "x": loc[0], "y": loc[1], "score": float(mx)}
    return None


def anchors(tpls, frames):
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf8"))
    t0 = time.time()
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda kv: find_anchor(kv[0], kv[1], frames), tpls.items()))
    a = [r for r in res if r]
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(a, open(CACHE, "w", encoding="utf8"))
    print(f"neo: {len(a)}/{len(tpls)} mau co neo >=0,95 ({time.time() - t0:.0f}s)", flush=True)
    return a


# ------------------------------------------------------------------ bien doi
def deg_scale(f):
    return lambda im, box: (cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_LINEAR), f)


def deg_blur(s):
    return lambda im, box: (cv2.GaussianBlur(im, (0, 0), s), 1.0)


def deg_gamma(g):
    return lambda im, box: ((255 * (im / 255.0) ** g).astype(np.uint8), 1.0)


def deg_noise(s):
    return lambda im, box: (np.clip(im + np.random.RandomState(0).normal(0, s, im.shape), 0, 255).astype(np.uint8), 1.0)


def deg_glow(amp):
    """Anh sang CUC BO quanh mau (hieu ung phat sang/nhap nhay): cong them mot vet gauss tam o mau."""
    def f(im, box):
        x, y, w, h = box
        yy, xx = np.mgrid[:im.shape[0], :im.shape[1]]
        g = np.exp(-(((xx - (x + w / 2)) ** 2 + (yy - (y + h / 2)) ** 2) / (2 * (max(w, h) * 0.8) ** 2)))
        return np.clip(im.astype(np.float32) + amp * g[..., None], 0, 255).astype(np.uint8), 1.0
    return f


def deg_occlude(frac):
    """Che mot goc mau (chu nhat phu `frac` dien tich, mau trung binh anh)."""
    def f(im, box):
        x, y, w, h = box
        out = im.copy()
        ww = max(1, int(w * frac ** 0.5))
        hh = max(1, int(h * frac ** 0.5))
        out[y:y + hh, x:x + ww] = im.mean((0, 1)).astype(np.uint8)
        return out, 1.0
    return f


DEGS = {
    "clean": lambda im, box: (im, 1.0),
    "gamma0.7": deg_gamma(0.7), "gamma1.5": deg_gamma(1.5), "noise8": deg_noise(8),
    "blur1.2": deg_blur(1.2), "blur2.0": deg_blur(2.0),
    "scale0.90": deg_scale(0.90), "scale0.95": deg_scale(0.95), "scale1.05": deg_scale(1.05), "scale1.10": deg_scale(1.10),
    "glow+60": deg_glow(60), "glow+120": deg_glow(120), "occlude25%": deg_occlude(0.25),
}


# ------------------------------------------------------------------ bien the khop
def _norm_grad(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def prep(variant, img):
    if variant == "bgr" or variant == "ms":
        return img
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if variant == "gray":
        return g
    if variant == "clahe":
        return cv2.createCLAHE(2.0, (8, 8)).apply(g)
    if variant == "grad":
        return _norm_grad(img)
    raise ValueError(variant)


VARIANTS = ("bgr", "gray", "clahe", "grad", "ms")
MS_SCALES = (0.90, 0.925, 0.95, 0.975, 1.0, 1.025, 1.05, 1.075, 1.10)


def match(variant, img, tpl, roi=None):
    """-> (score, (x, y)) tot nhat trong roi (x0, y0, x1, y1) hoac toan anh."""
    if roi:
        x0, y0, x1, y1 = roi
        img = img[y0:y1, x0:x1]
    else:
        x0 = y0 = 0
    best = (-1.0, (0, 0))
    scales = MS_SCALES if variant == "ms" else (1.0,)
    for s in scales:
        t = tpl if s == 1.0 else cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
        if img.shape[0] < t.shape[0] or img.shape[1] < t.shape[1]:
            continue
        a, b = prep(variant, img), prep(variant, t)
        _, mx, _, loc = cv2.minMaxLoc(cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED))
        if mx > best[0]:
            best = (float(mx), (loc[0] + x0, loc[1] + y0))
    return best


def run_anchor(a, tpls, frames, n_neg_ok):
    tpl = tpls[a["tpl"]]
    im = frames[a["frame"]]
    h, w = tpl.shape[:2]
    box = (a["x"], a["y"], w, h)
    hole = cv2.inpaint(im, np.pad(np.zeros((h, w), np.uint8) + 255, ((a["y"], 960 - a["y"] - h), (a["x"], 540 - a["x"] - w))),
                       3, cv2.INPAINT_TELEA)
    res = {}
    for dn, dfn in DEGS.items():
        d, f = dfn(im, box)
        dh = dfn(hole, box)[0] if n_neg_ok else None
        tx, ty = int(a["x"] * f), int(a["y"] * f)
        roi = (max(0, tx - WIN), max(0, ty - WIN), min(d.shape[1], tx + int(w * f) + WIN), min(d.shape[0], ty + int(h * f) + WIN))
        for v in VARIANTS:
            sc, loc = match(v, d, tpl, roi)
            ok_loc = abs(loc[0] - tx) <= 8 and abs(loc[1] - ty) <= 8
            neg = match(v, dh, tpl)[0] if dh is not None else None
            res[f"{v}|{dn}"] = (sc, ok_loc, neg)
    return res


def part_a(args):
    tpls, fr = load_templates(), load_frames()
    frames = dict(fr)
    anc = anchors(tpls, fr)
    print(f"A) {len(anc)} neo, {len(DEGS)} bien doi x {len(VARIANTS)} bien the; am tinh tren {args.n_neg} neo", flush=True)
    t0 = time.time()
    flags = [i < args.n_neg for i in range(len(anc))]
    with ThreadPoolExecutor(4) as ex:
        allr = list(ex.map(lambda p: run_anchor(p[0], tpls, frames, p[1]), zip(anc, flags, strict=True)))
    table = {}
    for key in allr[0]:
        sc = np.array([r[key][0] for r in allr])
        okl = np.array([r[key][1] for r in allr])
        negs = [(r[key][0], r[key][2]) for r in allr if r[key][2] is not None]
        table[key] = {
            "retention": float(((sc >= TH) & okl).mean()),
            "rank_ok": float(np.mean([p > n for p, n in negs])),
            "neg_fp@0.82": float(np.mean([n >= TH for _, n in negs])),
            "median_score": float(np.median(sc)),
        }
    print(f"A) xong {time.time() - t0:.0f}s", flush=True)
    return {"n_anchors": len(anc), "n_neg": args.n_neg, "table": table}


# ------------------------------------------------------------------ B) do sang
def make_pairs(frames, rng):
    """(nhan, cur, prev): static_s{0,1,2,4,8} | global_gain | global_bias | local_patch | motion."""
    out = []
    for _, im in frames:
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        gf = g.astype(np.float32)
        for s in (0, 1, 2, 4, 8):
            cur = np.clip(gf + rng.normal(0, s, g.shape), 0, 255).astype(np.uint8) if s else g.copy()
            out.append((f"static_s{s}", cur, g))
        out.append(("global_gain0.9", np.clip(gf * 0.9, 0, 255).astype(np.uint8), g))
        out.append(("global_gain1.1", np.clip(gf * 1.1, 0, 255).astype(np.uint8), g))
        out.append(("global_bias+12", np.clip(gf + 12, 0, 255).astype(np.uint8), g))
        out.append(("global_bias-12", np.clip(gf - 12, 0, 255).astype(np.uint8), g))
        y, x = int(rng.randint(50, 800)), int(rng.randint(20, 400))
        c = g.copy()
        c[y:y + 80, x:x + 80] = np.clip(c[y:y + 80, x:x + 80].astype(np.int16) + 70, 0, 255).astype(np.uint8)
        out.append(("local_patch80", c, g))
        m = g.copy()
        m[y:y + 80, x:x + 80] = np.roll(g[y:y + 80, x:x + 80], 10, axis=1)
        out.append(("motion_shift10", m, g))
    return out


def part_b(frames):
    rng = np.random.RandomState(7)
    pairs = make_pairs(frames, rng)
    classes = sorted({p[0] for p in pairs})
    grid = {}
    for k in (2, 3, 4, 5, 6):
        for ma in (0.005, 0.01, 0.02, 0.05):
            cell = {}
            for c in classes:
                rs = [detect_change(cur, prev, k, ma) for n, cur, prev in pairs if n == c]
                cell[c] = {"global": float(np.mean([r.global_shift for r in rs])), "local": float(np.mean([r.local for r in rs]))}
            grid[f"k={k},min_area={ma}"] = cell
    return {"n_pairs": len(pairs), "grid": grid}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-neg", type=int, default=40)
    ap.add_argument("--out", default=os.path.join(BASE, "data", "perception", "phase2_results.json"))
    ap.add_argument("--part", default="ab")
    a = ap.parse_args()
    res = {}
    if "b" in a.part:
        res["B"] = part_b(load_frames()[::3])
        print("B) xong", flush=True)
    if "a" in a.part:
        res["A"] = part_a(a)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w", encoding="utf8"), indent=1)
    print("ghi", a.out, flush=True)


if __name__ == "__main__":
    main()
