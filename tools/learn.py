"""Cong cu hoc may mini (giai doan E+F, docs/bot/05-ke-hoach-hoc-may-mini.md).

  python tools/learn.py report [--hours 24]   # ti le cham an / truot theo buoc, anh mau, cho chet; kNN; bien the
  python tools/learn.py train [--max 4000]    # nap mau kNN tu anh cu (logs/, tests/fixtures/screens) bang identify
  python tools/learn.py eval                  # do chinh xac kNN (bo-1-ra tren fixtures) + du doan cho logs/unknown
  python tools/learn.py cand                  # bien the ung vien dang cho (data/learn/cand)
"""
import argparse, glob, json, os, random, sys, time
import cv2, numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)
from bot.memory import Memory  # noqa: E402
from bot.vision import Vision  # noqa: E402
from bot import learn, screens  # noqa: E402


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def report(a):
    m = Memory()
    since = time.time() - a.hours * 3600
    rows = m.query("SELECT step, kind, tpl, why, x, y, changed, outcome FROM exp WHERE at>?", (since,))
    known = [r for r in rows if r[6] is not None]
    ok = sum(r[6] for r in known)
    print(f"== Kinh nghiem {a.hours} gio qua: {len(rows)} lan cham, biet ket qua {len(known)} ({pct(len(known), len(rows))})")
    print(f"   an (man/vung doi): {ok} = {pct(ok, len(known))}   truot: {len(known) - ok} = {pct(len(known) - ok, len(known))}")
    oc = {}
    for r in known:
        oc[r[7]] = oc.get(r[7], 0) + 1
    print("   ket qua:", ", ".join(f"{k} {v}" for k, v in sorted(oc.items(), key=lambda kv: -kv[1])))

    def table(title, keyf, n=12):
        g = {}
        for r in known:
            s = g.setdefault(keyf(r), [0, 0])
            s[0] += r[6]
            s[1] += 1
        print(f"\n== {title} (truot nhieu nhat)")
        for k, (o, t) in sorted(g.items(), key=lambda kv: -(kv[1][1] - kv[1][0]))[:n]:
            print(f"   {str(k):55s} {t:4d} lan  an {pct(o, t):>4s}  truot {t - o}")
    table("Theo buoc", lambda r: r[0])
    table("Theo ai cham (module.ham / anh mau)", lambda r: r[2] or r[3])
    L = learn.Learner(m, {})
    dead = [(k, v) for k, v in L.stats.items() if v[1] >= 8 and v[0] / v[1] < 0.1]
    print(f"\n== Cho chet (>= 8 lan, an < 10%): {len(dead)}")
    for (tpl, gx, gy), (o, t) in sorted(dead, key=lambda kv: -kv[1][1])[:15]:
        print(f"   {tpl:45s} @~{gx * learn.GRID},{gy * learn.GRID}  {o}/{t}")
    nav = m.query("SELECT action, SUM(changed=0), SUM(changed IS NOT NULL) FROM nav WHERE at>? GROUP BY action", (since,))
    print("\n== goto (nav) truot theo hanh dong:", ", ".join(f"{a_} {pct(b or 0, c or 0)} ({c})" for a_, b, c in nav))
    lab = m.query("SELECT label, COUNT(*) FROM screen_samples GROUP BY label ORDER BY 2 DESC")
    print("== Mau kNN:", ", ".join(f"{k} {v}" for k, v in lab) or "chua co")
    var = glob.glob(os.path.join(learn.TPL, "**", "*@*.png"), recursive=True)
    print(f"== Bien the anh mau da hoc: {len(var)}", *[os.path.relpath(v, BASE) for v in var], sep="\n   ")


def images(maxn):
    fs = glob.glob("tests/fixtures/screens/*/*.png")
    for d in ("logs/shots", "logs/unknown"):
        fs += glob.glob(os.path.join(d, "**", "*.png"), recursive=True)
    random.seed(1)
    random.shuffle(fs)
    return fs[:maxn]


def train(a):
    m = Memory()
    L = learn.Learner(m, {})
    v = Vision("templates", 0.82)
    n = add = 0
    t0 = time.time()
    for f in images(a.max):
        img = cv2.imread(f)
        if img is None or img.shape[:2] != (960, 540):
            continue
        n += 1
        scr, det = screens.identify(img, v)
        if scr == "unknown":
            continue
        tpl, p = (det[0], det[1]) if det else (None, None)
        if L.add_sample(-1, scr, tpl, p[0] if p else None, p[1] if p else None, img):
            add += 1
    print(f"Doc {n} anh, them {add} mau kNN ({time.time() - t0:.0f} s). Tong mau: {len(L.lab)}")


def evaluate(a):
    v = Vision("templates", 0.82)
    fx = sorted(glob.glob("tests/fixtures/screens/*/*.png"))
    feats = [learn.feat(cv2.imread(f)) for f in fx]
    labs = [os.path.basename(os.path.dirname(f)) for f in fx]
    m = Memory()
    L = learn.Learner(m, {})
    good = 0
    for i, f in enumerate(fx):
        pr = L.predict(f=feats[i])
        got = pr[0] if pr else None
        good += got == labs[i]
        print(f"   {'OK ' if got == labs[i] else 'SAI'} {os.path.relpath(f):60s} -> {got} {pr[1]:.2f} sim {pr[2]:.3f}" if pr else f"   ?? {f}")
    print(f"kNN tren fixtures (mau DB): {good}/{len(fx)}")
    unk = sorted(glob.glob("logs/unknown/*.png"))
    conf = 0
    for f in unk:
        img = cv2.imread(f)
        if img is None:
            continue
        scr, _ = screens.identify(img, v)
        pr = L.predict(img)
        near = screens.near_miss(img, v, learn.LEARNABLE)
        sure = pr and pr[1] >= 0.8 and pr[2] >= 0.94
        conf += bool(sure or near)
        print(f"   {os.path.basename(f)[:40]:40s} identify={scr:8s} knn={pr[0] if pr else '-'}"
              f" {pr[1]:.2f}/{pr[2]:.3f}" if pr else "", f" near={near[0]}:{near[1][2]:.2f}" if near else "")
    print(f"Man la co huong xu ly (kNN chac / nut gan khop): {conf}/{len(unk)}")


def cand(a):
    for d in sorted(glob.glob(os.path.join(learn.CAND, "*"))):
        p = os.path.join(d, "meta.json")
        meta = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
        print(os.path.basename(d).replace("__", "/"))
        for h, mm in meta.items():
            st = "DA NHAN" if mm.get("promoted") else "TU CHOI" if mm.get("rejected") else "cho"
            print(f"   {h}  dung {mm['ok']}  sai {mm['fail']}  {st}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["report", "train", "eval", "cand"])
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--max", type=int, default=4000)
    a = ap.parse_args()
    {"report": report, "train": train, "eval": evaluate, "cand": cand}[a.cmd](a)
