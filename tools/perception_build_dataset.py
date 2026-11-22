"""P1b: dung dataset v0 tu thao tac TAY da ghi (logs/human) + do "do phu muc tieu nguoi chon" cua Vision cu.

Y tuong: moi lan nguoi cham = bang chung DOC LAP rang (x, y) la muc tieu bam duoc. Hoi: Vision cu co anh mau khop
(>= th) ngay do khong? Ti le khong khop = can duoi cua recall (nguoi cham nhung bot khong co/khong nhan ra mau).
Nhan lop tu khop cu la 'bootstrap' (khong duoc vao test). Test chi co sau khi nguoi duyet bang review.csv.

  python tools/perception_build_dataset.py --n 300 [--day 20261121] [--th 0.82] [--out data/perception/v0]
Ra: <out>/manifest.json, images/, review/*.png + review.csv (cham chua co mau -> dien cot 'class'), coverage.json
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402

from aowbot.perception.eval import dataset as ds  # noqa: E402
from bot.vision import Vision  # noqa: E402

HUMAN = os.path.join(BASE, "logs", "human")
TPL = os.path.join(BASE, "templates")
SKIP_GROUPS = {"digits"}      # chu so rieng le: khong phai muc tieu cham


def template_classes(v):
    groups = sorted(d for d in os.listdir(TPL) if os.path.isdir(os.path.join(TPL, d)) and d not in SKIP_GROUPS)
    out = []
    for g in groups:
        out += [c for c in v.list(g + "/") if not c.startswith(g + "/lv/")]
    return out


def load_taps(day):
    root = os.path.join(HUMAN, day)
    taps = []
    with open(os.path.join(root, "events.jsonl"), encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "tap" and e.get("before") and os.path.exists(os.path.join(root, e["before"])):
                taps.append(e)
    return root, taps


def pick(taps, n, day):
    """Chon xac dinh theo bam id (tai lap, khong phu thuoc thu tu)."""
    key = lambda e: hashlib.sha256(f"{day}:{e['before']}".encode()).hexdigest()  # noqa: E731
    return sorted(taps, key=key)[:n]


def hit_near(v, img, classes, xy, th, pad=12):  # noqa: PLR0913, PLR0917
    """[(lop, diem, bbox)] cac anh mau khop co bbox chua diem cham (nong pad px)."""
    x, y = xy
    out = []
    for c in classes:
        t = v.load(c, probe=True)
        if t is None:
            continue
        h, w = t.shape[:2]
        # chi xet cua so quanh diem cham (diem khop tai moi vi tri nhu nhau, nhanh hon ca man ~100 lan)
        x0, y0 = max(0, x - w - pad), max(0, y - h - pad)
        roi = (x0, y0, min(img.shape[1], x + w + pad) - x0, min(img.shape[0], y + h + pad) - y0)
        for cx, cy, sc in v.find_all(img, c, th=th, roi=roi, min_dist=8):
            if abs(cx - x) <= w // 2 + pad and abs(cy - y) <= h // 2 + pad:
                out.append((c, float(sc), ds.Box(int(cx) - w // 2, int(cy) - h // 2, w, h)))
    return sorted(out, key=lambda r: -r[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default="20261121")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--th", type=float, default=0.82)
    ap.add_argument("--out", default=os.path.join(BASE, "data", "perception", "v0"))
    a = ap.parse_args()
    out = Path(a.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "review").mkdir(exist_ok=True)
    root, taps = load_taps(a.day)
    chosen = pick(taps, a.n, a.day)
    v = Vision(TPL, a.th)
    classes = template_classes(v)
    sessions = {}
    rows, cov = [], defaultdict(lambda: [0, 0])
    review = []
    for i, e in enumerate(chosen):
        img = cv2.imread(os.path.join(root, e["before"]), cv2.IMREAD_COLOR)
        if img is None or img.shape[:2] != (960, 540):
            continue
        sid = f"h{a.day}-i{e['idx']}-{i:04d}"
        sess = f"{a.day}-i{e['idx']}-h{str(e['clock'])[:2]}"
        dst = out / "images" / f"{sid}.png"
        shutil.copyfile(os.path.join(root, e["before"]), dst)
        hits = hit_near(v, img, classes, (e["x"], e["y"]), a.th)
        cov[e["idx"]][0] += 1
        cov[e["idx"]][1] += int(bool(hits))
        anns = (ds.Annotation(hits[0][0], hits[0][2]),) if hits else ()
        rows.append((sid, sess, e["idx"], anns, bool(hits)))
        sessions[sess] = None
        if not hits:   # muc tieu nguoi cham ma mau cu khong thay -> can nguoi dat ten lop
            x0, y0 = max(0, e["x"] - 60), max(0, e["y"] - 60)
            crop = img[y0:y0 + 120, x0:x0 + 120]
            cv2.imwrite(str(out / "review" / f"{sid}.png"), crop)
            review.append((sid, e["x"], e["y"], e.get("changed"), e.get("outcome")))
    split = ds.assign_splits(sessions, {"train": 0.7, "val": 0.3, "test": 0.0})   # test chi tu nhan nguoi duyet
    samples = tuple(ds.Sample(sid, f"images/{sid}.png", ds.sha256_file(out / "images" / f"{sid}.png"), sess, idx,
                              "unknown", "unknown", split[sess], "bootstrap", False, anns)
                    for sid, sess, idx, anns, _ in rows)
    data = ds.Dataset("v0", tuple(classes), samples)
    ds.save(data, out / "manifest.json")
    with (out / "review.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "tap_x", "tap_y", "changed", "outcome", "class", "w", "h"])
        w.writerows((*r, "", "", "") for r in review)
    tot = sum(c[0] for c in cov.values())
    hit = sum(c[1] for c in cov.values())
    summary = {"day": a.day, "threshold": a.th, "taps_total": len(taps), "taps_sampled": tot, "covered": hit,
               "coverage": round(hit / tot, 3) if tot else None, "templates": len(classes),
               "by_instance": {str(k): {"n": c[0], "covered": c[1], "coverage": round(c[1] / c[0], 3)}
                               for k, c in sorted(cov.items())}}
    (out / "coverage.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print(f"manifest: {out / 'manifest.json'} ({len(samples)} mau, nhan bootstrap) | can duyet: {len(review)} cham")


if __name__ == "__main__":
    main()
