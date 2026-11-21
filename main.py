"""Age of Warpath farm bot - chay luan phien cac instance LDPlayer.

  python main.py                      # chay vong lap theo config.yaml
  python main.py --once --only 0      # chay 1 luot cho instance 0
  python main.py --modules gather     # chi chay buoc gui quan
  python main.py --capture 0          # chup man hinh instance 0 -> logs/capture-*.png (de cat anh mau)
  python main.py --check              # liet ke anh mau con thieu
  python main.py --web                # giao dien quan ly: http://localhost:8080
"""
import argparse, logging, os, sys, time, traceback
import cv2, yaml

from bot.device import LDConsole, Device
from bot.vision import Vision
from bot.state import Store
from bot.runner import Runner, RingLog, ORDER

BASE = os.path.dirname(os.path.abspath(__file__))
log = logging.getLogger("aow")
RING = RingLog()


def setup_log():
    os.makedirs(os.path.join(BASE, "logs"), exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(threadName)s] %(message)s", "%H:%M:%S")
    log.setLevel(logging.INFO)
    for h in (logging.StreamHandler(sys.stdout),
              logging.FileHandler(os.path.join(BASE, "logs", time.strftime("bot-%Y%m%d.log")), encoding="utf-8")):
        h.setFormatter(fmt)
        log.addHandler(h)
    log.addHandler(RING)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(BASE, "config.yaml"))
    ap.add_argument("--only", help="danh sach ID instance, vd 0,3,5")
    ap.add_argument("--modules", help="ghi de buoc chay, vd research,train,gather")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--capture", type=int, metavar="ID")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--web", action="store_true", help="mo giao dien quan ly http://localhost:8080")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    with open(a.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    setup_log()
    vision = Vision(os.path.join(BASE, "templates"), cfg.get("match_threshold", 0.82))

    if a.check:
        from bot.tplcheck import missing
        total, miss = missing(cfg)
        print(f"Thieu {len(miss)}/{total} anh mau:")
        for n in miss:
            print("  templates/" + n + ".png")
        for folder in ("rewards", "daily"):  # bao anh mau theo tuyen da co (claim_2, tab_*...)
            d = os.path.join(BASE, "templates", folder)
            if os.path.isdir(d):
                for root, _, files in os.walk(d):
                    for fn in sorted(files):
                        if fn.endswith(".png"):
                            print("  co: " + os.path.relpath(os.path.join(root, fn), os.path.join(BASE, "templates")).replace("\\", "/"))
        return

    ld = LDConsole(cfg["ldplayer"])
    if a.capture is not None:
        ld.launch(a.capture)
        dev = Device(cfg["ldplayer"]["adb"], a.capture)
        dev.wait_ready()
        path = os.path.join(BASE, "logs", time.strftime(f"capture-i{a.capture}-%H%M%S.png"))
        cv2.imwrite(path, dev.screencap())
        print("Da luu", path)
        return

    store = Store()
    runner = Runner(cfg, store, vision)
    if a.web:
        from web.server import serve
        serve(runner, store, RING, a.port)
        return
    modules = set(a.modules.split(",")) if a.modules else None
    ids = [int(x) for x in a.only.split(",")] if a.only else cfg["instances"]
    while True:
        t0 = time.time()
        for idx in ids:
            runner.run_account(idx, modules)
        log.info("Xong 1 vong %d tai khoan trong %.1f phut", len(ids), (time.time() - t0) / 60)
        if a.once or not cfg["cycle"].get("loop_forever", True):
            break
        time.sleep(cfg["cycle"].get("pause_between_cycles_min", 30) * 60)


if __name__ == "__main__":
    main()
