"""Cong cu cat anh mau nhanh (chay tu thu muc goc bot).

  python tools/snap.py shot NAME                 # chup instance 0 -> logs/snap-NAME.png
  python tools/snap.py tap X Y [NAME]            # cham (X,Y) roi chup
  python tools/snap.py tpl TEMPLATE [NAME]       # cham theo anh mau roi chup
  python tools/snap.py back [NAME]               # phim Back roi chup
  python tools/snap.py cut SRC NAME x1 y1 x2 y2  # cat logs/snap-SRC.png -> templates/NAME.png, bao so diem khop
  python tools/snap.py find SRC NAME             # tim anh mau NAME tren logs/snap-SRC.png
  python tools/snap.py todo [NHOM]               # anh mau con thieu (vd: todo research) + lenh cat goi y
  python tools/snap.py grid SRC                  # logs/grid-SRC.png: anh x2 co luoi toa do de doc x1 y1 x2 y2
  python tools/snap.py cutmany SRC NAME=x1,y1,x2,y2 [NAME2=...]   # cat nhieu anh mau tu 1 anh chup
Bien moi truong AOW_IDX=<so> de chon instance khac.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, yaml
from bot.device import Device
from bot.vision import Vision

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
IDX = int(os.environ.get("AOW_IDX", 0))


def dev():
    return Device(cfg["ldplayer"]["adb"], IDX)


def save(name, wait=2.0):
    time.sleep(wait)
    p = f"logs/snap-{name}.png"
    cv2.imwrite(p, dev().screencap())
    print("saved", p)


def cut(src, im, name, x1, y1, x2, y2):
    os.makedirs(os.path.dirname(f"templates/{name}.png"), exist_ok=True)
    cv2.imwrite(f"templates/{name}.png", im[y1:y2, x1:x2])
    cv2.imwrite(f"logs/zoom-{name.replace('/', '_')}.png",
                cv2.resize(im[y1:y2, x1:x2], None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST))
    hits = Vision("templates").find_all(im, name)
    note = "" if len(hits) == 1 else ("  <- KHONG khop lai!" if not hits else "  <- khop nhieu cho, nen cat rong hon")
    print(f"{name}: {x2 - x1}x{y2 - y1}, khop {[(int(x), int(y), round(sc, 3)) for x, y, sc in hits[:5]]}{note}")


def grid(src, step=20):
    im = cv2.imread(f"logs/snap-{src}.png")
    big = cv2.resize(im, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    h, w = im.shape[:2]
    for v in range(0, max(w, h), step):
        major = v % 100 == 0
        col, th = ((0, 255, 255), 1) if major else ((90, 90, 90), 1)
        if v < w:
            cv2.line(big, (2 * v, 0), (2 * v, 2 * h), col, th)
            if major:
                cv2.putText(big, str(v), (2 * v + 3, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
        if v < h:
            cv2.line(big, (0, 2 * v), (2 * w, 2 * v), col, th)
            if major:
                cv2.putText(big, str(v), (3, 2 * v - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
    p = f"logs/grid-{src}.png"
    cv2.imwrite(p, big)
    print("saved", p, "(toa do ghi tren luoi la toa do 540x960 that)")


def main(a):
    cmd = a[0]
    if cmd == "boot":  # bat instance + mo game + dong popup
        from bot.device import LDConsole
        from bot.ctx import Ctx
        ld = LDConsole(cfg["ldplayer"])
        ld.launch(IDX)
        d = dev()
        d.wait_ready()
        ld.runapp(IDX, cfg["ldplayer"]["game_package"])
        time.sleep(cfg["ldplayer"].get("launch_wait", 45))
        Ctx(d, Vision("templates"), cfg).close_popups(rounds=10, settle=3)
        save(a[1] if len(a) > 1 else "boot")
    elif cmd == "swipe":  # swipe x1 y1 x2 y2 [ten]
        dev().swipe(*map(int, a[1:5]), 600)
        save(a[5] if len(a) > 5 else "last")
    elif cmd == "shot":
        save(a[1], 0)
    elif cmd == "tap":  # tap X Y [ten] - dat AOW_REPEAT=n de cham n lan
        for _ in range(int(os.environ.get("AOW_REPEAT", 1))):
            dev().tap(int(a[1]), int(a[2]))
            time.sleep(0.3)
        save(a[3] if len(a) > 3 else "last")
    elif cmd == "tpl":
        p = Vision("templates").find(dev().screencap(), a[1])
        print("found", p)
        if p:
            dev().tap(p[0], p[1])
        save(a[2] if len(a) > 2 else "last")
    elif cmd == "back":
        dev().back()
        save(a[1] if len(a) > 1 else "last")
    elif cmd == "cut":
        im = cv2.imread(f"logs/snap-{a[1]}.png")
        cut(a[1], im, a[2], *map(int, a[3:7]))
    elif cmd == "cutmany":
        im = cv2.imread(f"logs/snap-{a[1]}.png")
        if im is None:
            sys.exit(f"Khong co logs/snap-{a[1]}.png")
        for spec in a[2:]:
            name, box = spec.split("=")
            cut(a[1], im, name, *map(int, box.split(",")))
    elif cmd == "grid":
        grid(a[1])
    elif cmd == "todo":
        from bot.tplcheck import missing
        total, miss = missing(cfg, a[1] if len(a) > 1 else None)
        print(f"Thieu {len(miss)}/{total} anh mau{' nhom ' + a[1] if len(a) > 1 else ''}:")
        for n in miss:
            print("  " + n)
        if miss:
            print("Khi tinh huong hien tren man hinh:\n  python tools/snap.py shot X\n  python tools/snap.py grid X\n"
                  "  python tools/snap.py cutmany X " + " ".join(f"{n}=x1,y1,x2,y2" for n in miss[:3]))
    elif cmd == "find":
        v = Vision("templates")
        print(v.find_all(cv2.imread(f"logs/snap-{a[1]}.png"), a[2]))


if __name__ == "__main__":
    main(sys.argv[1:])
