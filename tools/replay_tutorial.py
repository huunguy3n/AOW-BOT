"""Kiem tra offline bot/modules/tutorial.decide() bang ban ghi nguoi choi lam mau.

  python tools/replay_tutorial.py [logs/rec/<thu_muc>]

Voi moi thao tac trong ban ghi: dua anh 'before' cho decide() (idle=2, coi nhu da cho 2 nhip; state giu xuyen suot)
roi so voi thao tac that:
  OK      bot cham trong ban kinh 70 px quanh diem nguoi cham / bot lai tran khi nguoi vuot
  ALT     bot cham cho khac nhung hop le (hoi thoai/canh phim cham dau cung duoc)
  DIFF    khac han -> can xem lai
"""
import glob, json, os, sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)
import cv2
from bot.vision import Vision
from bot.modules import tutorial

ANY_TAP = ("hoi thoai", "man la", "dong popup")   # man hinh cham dau cung qua

d = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("logs/rec/*tan_thu*"))[-1]
v = Vision("templates", 0.82)
ev = [e for e in map(json.loads, open(os.path.join(d, "events.jsonl"), encoding="utf-8"))
      if e.get("type") in ("tap", "swipe", "long_press")]
stat = {"OK": 0, "ALT": 0, "DIFF": 0}
state = {}
for e in ev:
    img = cv2.imread(os.path.join(d, f"{e['i']:04d}_before.png"))
    act, x, y, why = tutorial.decide(v, img, idle=2, state=state)
    user = "swipe" if e["type"] in ("swipe", "long_press") else "tap"
    if act == "steer":
        res = "OK" if user == "swipe" else "DIFF"
    elif act == "tap" and user == "tap":
        dist = ((x - e["x"]) ** 2 + (y - e["y"]) ** 2) ** 0.5
        res = "OK" if dist <= 70 else ("ALT" if why.startswith(ANY_TAP) else "DIFF")
    elif act == "tap" and why.startswith(ANY_TAP):
        res = "ALT"
    else:
        res = "DIFF"
    stat[res] += 1
    print(f"{res:4} #{e['i']:<3} nguoi={e['type']:<10}({e['x']},{e['y']})  bot={act}({x},{y}) {why}")
print(stat, f"-> dung {stat['OK'] + stat['ALT']}/{len(ev)}")
