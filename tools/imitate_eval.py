"""Danh gia OFFLINE bo 'lam theo mau' (bot/imitate.py) tren ban ghi thao tac tay - khong cham game.

Moi lan cham mau = 1 cau hoi: an cac mau trong +-window giay quanh no (khong cho bot "chep chinh no"),
hoi decide() voi anh TRUOC khi cham -> so voi cho chu du an da cham:
  dung  = bot cham trong vong 40 px cho that
  sai   = bot cham cho khac
  bo qua = bot khong du tin (tra None) -> o che do that bot se dung lai, khong doan
Chi so quan trong: do CHINH XAC khi da cham (dung / (dung + sai)) - phai rat cao truoc khi chay that.

  python tools/imitate_eval.py --idx 3 [--since "2026-11-21 15:20"] [--window 60] [--th 0.9 --crop 0.85]
"""
import argparse
import os
import sys
import time

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot import imitate, screens  # noqa: E402
from bot.vision import Vision  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idx", type=int, default=3)
    ap.add_argument("--since", default=None, help='"YYYY-mm-dd HH:MM": chi lay mau tu luc nay')
    ap.add_argument("--window", type=float, default=60)
    ap.add_argument("--th", type=float, default=0.9)
    ap.add_argument("--crop", type=float, default=0.85)
    ap.add_argument("--show", type=int, default=8, help="in N truong hop sai")
    ap.add_argument("--chain", type=int, default=1, help="1 = dung ngu canh chuoi thao tac")
    ap.add_argument("--raw", action="store_true", help="do decide() tho (khong luat theo loai man)")
    a = ap.parse_args()
    since = time.mktime(time.strptime(a.since, "%Y-%m-%d %H:%M")) if a.since else 0.0
    t0 = time.time()
    demos = imitate.load_demos(a.idx, since=since)
    idx = imitate.Index(demos)
    print(f"{len(demos)} mau cham co tac dung cua may #{a.idx} (nap {time.time() - t0:.1f}s)")
    v = Vision(os.path.join(os.path.dirname(imitate.HUMAN), "..", "templates"), 0.82)
    hit = wrong = skip = chain_hit = chain_n = 0
    bad = []
    t1 = time.time()
    for d in demos:
        img = cv2.imread(os.path.join(imitate.HUMAN, d["key"]))
        # ngu canh: gia su bot vua lam dung thao tac TRUOC do cua chu du an (neu cung chuoi)
        scr = screens.identify(img, v)[0]
        kw = {"last": d.get("prev") if a.chain else None, "th_scr": a.th, "th_crop": a.crop,
              "exclude": lambda o, q=d: abs(o["t"] - q["t"]) < a.window}
        # --raw: decide() tho; mac dinh: choose() = luat THAT khi chay (man ban -> can ngu canh chuoi)
        r = imitate.decide(img, idx, **kw) if a.raw else imitate.choose(img, idx, scr, **kw)
        if r is not None:
            chain_n += r["chain"]
        if r is None:
            skip += 1
        elif (abs(r["x"] - d["x"]) <= 40 and abs(r["y"] - d["y"]) <= 40) or scr == "reward":   # thuong: cham dau cung dong
            hit += 1
            chain_hit += r["chain"]
        else:
            wrong += 1
            bad.append((d["key"], (d["x"], d["y"]), (r["x"], r["y"]), r["key"], r["sim"], r["match"], r["chain"]))
    n = len(demos) or 1
    print(f"dung {hit} · sai {wrong} · bo qua {skip}  ->  chinh xac khi cham {hit / max(1, hit + wrong):.1%}, "
          f"bao phu {(hit + wrong) / n:.1%}  ({(time.time() - t1) / n * 1000:.0f} ms/lan)")
    print(f"  trong do co ngu canh chuoi: {chain_n} lan, dung {chain_hit} ({chain_hit / max(1, chain_n):.1%})")
    for b in bad[:a.show]:
        print("  SAI", b)


if __name__ == "__main__":
    main()
