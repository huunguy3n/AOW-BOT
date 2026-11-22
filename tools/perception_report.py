"""Dung bao cao danh gia tu cac lan chay quan sat: ve lai moi khung bang bo nhan dien HIEN TAI (moi lop mau, cham do, man hinh),
gan dong log bot theo thoi gian, xuat thu muc <out>/ gom index.html + img/*.jpg (san sang xuat ban).

  python tools/perception_report.py --runs logs/perception_live/i2_20261122 logs/perception_live/i2_20261122b \
        --botlog logs/perception_live/i2_20261122/bot_stdout.txt --out logs/perception_live/report
"""
import argparse
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src"), os.path.join(BASE, "tools")]

_S = {}


def _init():
    import cv2
    cv2.setNumThreads(1)          # 1 luong OpenCV moi tien trinh: tranh tranh chap CPU khi chay nhieu tien trinh
    import perception_render as pr
    from bot.vision import Vision
    v = Vision(os.path.join(BASE, "templates"), 0.82)
    names = [n for g in sorted(os.listdir(os.path.join(BASE, "templates")))
             if os.path.isdir(os.path.join(BASE, "templates", g)) and g != "digits" for n in v.list(g + "/")
             if not n.startswith(g + "/lv/")]
    _S.update(v=v, names=names, svc=pr.make_service(v), pr=pr)


def _work(job):
    import cv2
    from aowbot.perception.contract import Status
    from aowbot.perception.eval.dataset import Box
    from aowbot.perception.eval.names import display
    from aowbot.perception.service import Query
    from bot import screens
    from bot.badges import red_dots
    i, path, out = job
    v, names, svc, pr = _S["v"], _S["names"], _S["svc"], _S["pr"]
    img = cv2.imread(path)
    qs = [Query(n, v.load(n, probe=True), Box(*screens.ROI[n]) if n in screens.ROI else None) for n in names]
    svc._cache.clear()
    t0 = time.perf_counter()
    r = svc.process_raw(img, 2, i, float(i), qs)
    ms = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter()
    legacy_found = [n for n in names if v.find(img, n, roi=screens.ROI.get(n)) is not None]
    ms_legacy = (time.perf_counter() - t1) * 1000
    legacy_dots = red_dots(img)
    cv2.imwrite(os.path.join(out, "img", f"{i:03d}.jpg"), pr.draw(img, r, legacy_dots), [cv2.IMWRITE_JPEG_QUALITY, 72])
    dots = [d.position for d in r.detections if d.cls == "reddot"]
    conf = {o.cls: round(o.p, 3) for o in r.outcomes if o.status is Status.CONFIRMED and o.p is not None}
    unc = {o.cls: round(o.p, 2) for o in r.outcomes if o.status is Status.UNCERTAIN and o.p}
    return {"i": i, "file": os.path.basename(path), "scene": r.scene, "ms": round(ms), "ms_legacy": round(ms_legacy),
            "reddots": len(dots), "reddots_legacy": len(legacy_dots),
            "confirmed": {display(k): p for k, p in conf.items()},
            "uncertain": {display(k): p for k, p in unc.items() if p >= pr.SHOW_UNCERTAIN_P},
            "uncertain_all": len(unc), "legacy_found": [display(n) for n in legacy_found], "events": [e.kind for e in r.events],
            "stats": {k: round(float(x), 1) for k, x in r.stats.items() if k in ("orb_runs", "reddots")}}


def parse_botlog(path):
    rows = []
    if not path or not os.path.exists(path):
        return rows
    day = time.strftime("%Y-%m-%d")
    for ln in open(path, encoding="utf8", errors="replace"):
        if len(ln) > 9 and ln[2] == ":" and ln[5] == ":":
            t = time.mktime(time.strptime(day + " " + ln[:8], "%Y-%m-%d %H:%M:%S"))
            rows.append((t, ln[9:].rstrip()))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--botlog")
    ap.add_argument("--out", required=True)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "img"), exist_ok=True)
    frames = []
    for run in a.runs:
        tl = {r["file"]: r for r in map(json.loads, open(os.path.join(run, "timeline.jsonl"), encoding="utf8"))}
        for p in sorted(glob.glob(os.path.join(run, "frames", "*.jpg"))):
            nm = os.path.basename(p)[:-4]
            if not nm.endswith("_p") and nm in tl:
                frames.append((p, tl[nm]))
    if a.limit:
        frames = frames[:a.limit]
    jobs = [(i, p, a.out) for i, (p, _) in enumerate(frames)]
    t0 = time.time()
    with Pool(a.procs, initializer=_init) as pool:
        res = []
        for k, r in enumerate(pool.imap(_work, jobs)):
            res.append(r)
            if k % 10 == 0:
                print(f"  {k + 1}/{len(jobs)} ({time.time() - t0:.0f}s)", flush=True)
    log = parse_botlog(a.botlog)
    for r, (_, tl) in zip(res, frames, strict=True):
        r["t"], r["clock"] = tl["t"], tl["clock"]
    prev = 0.0
    for r in res:
        r["bot"] = [m for t, m in log if prev < t <= r["t"] + 1][-4:]
        prev = r["t"] + 1
    json.dump(res, open(os.path.join(a.out, "data.json"), "w", encoding="utf8"), ensure_ascii=False)
    print(f"xong {len(res)} khung trong {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
