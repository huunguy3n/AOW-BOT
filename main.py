"""Age of Warpath farm bot - chay luan phien cac instance LDPlayer.

  python main.py                      # chay vong lap theo config.yaml
  python main.py --once --only 0      # chay 1 luot cho instance 0
  python main.py --modules gather     # chi chay buoc gui quan
  python main.py --capture 0          # chup man hinh instance 0 -> logs/capture-*.png (de cat anh mau)
  python main.py --check              # liet ke anh mau con thieu
  python main.py --web                # giao dien quan ly: http://localhost:8080
"""
import argparse, logging, os, sys, time
import cv2, yaml

from bot.device import LDConsole, Device
from bot.vision import Vision
from bot.state import Store
from bot.runner import Runner, RingLog


def _port_busy(port, host="127.0.0.1"):
    """Da co tien trinh nghe cong nay chua (thu ket noi that, vi bind tren Windows khong bao trung)."""
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

BASE = os.path.dirname(os.path.abspath(__file__))
log = logging.getLogger("aow")
RING = RingLog()


class DailyFileHandler(logging.FileHandler):
    """Ghi logs/bot-YYYYMMDD.log theo NGAY CUA DONG LOG (A-REL-1): truoc day ten file chon 1 lan luc khoi dong
    nen chay qua dem van ghi vao file ngay dau. Giu nguyen mau ten file de cong cu/thoi quen cu khong doi."""

    def __init__(self, folder):
        self.folder = folder
        self.day = time.strftime("%Y%m%d")
        super().__init__(self._path(), encoding="utf-8", delay=True)

    def _path(self):
        return os.path.join(self.folder, f"bot-{self.day}.log")

    def emit(self, record):
        day = time.strftime("%Y%m%d", time.localtime(record.created))
        if day != self.day:
            self.acquire()
            try:
                self.close()
                self.day = day
                self.baseFilename = os.path.abspath(self._path())
            finally:
                self.release()
        super().emit(record)


def setup_log():
    os.makedirs(os.path.join(BASE, "logs"), exist_ok=True)
    log.setLevel(logging.INFO)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(threadName)s] %(message)s", "%H:%M:%S"))
    # file co NGAY trong moi dong: do dac tu log (vd thoi gian khoi dong) can moc thoi gian tuyet doi
    daily = DailyFileHandler(os.path.join(BASE, "logs"))
    daily.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(threadName)s] %(message)s",
                                         "%Y-%m-%d %H:%M:%S"))
    log.addHandler(console)
    log.addHandler(daily)
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
    setup_log()          # truoc khi doc YAML: loi cu phap config cung duoc ghi vao log
    try:
        with open(a.config, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        log.exception("Khong doc duoc cau hinh %s", a.config)
        raise
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

    if a.web and _port_busy(a.port):
        # Windows: werkzeug bat SO_REUSEADDR -> web thu 2 van "chay" cung cong nhung request roi vao ban CU
        # (2 runner song song, giao dien cu). Dung ngay thay vi am tham chay chong.
        print(f"Cong {a.port} dang co web khac chay (ban cu?). Tat no truoc, hoac dung --port khac.")
        sys.exit(1)
    store = Store()
    from aowbot.app.agent import build_agent_hooks  # lazy: chi khi chay runner (khong can cho --check/--capture)
    runner = Runner(cfg, store, vision, agent=build_agent_hooks(lambda i: store.cfg_for(cfg, i), BASE))
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
