"""Ghi lai thao tac nguoi choi lam mau tren 1 instance -> du lieu de xay buoc tu dong cho bot.

  python tools/record.py [--idx 6] [--name khoi_tao] [--note]

Ghi vao logs/rec/<ngay_gio>_<name>/:
  events.jsonl  - moi dong 1 thao tac: tap / swipe / long_press / key (toa do man hinh 540x960),
                  thoi gian, activity dang mo, ten anh truoc/sau
  NNNN_before.png - man hinh luc ngon tay vua cham (truoc khi game phan ung)
  NNNN_after.png  - man hinh ~1.5 s sau khi nhac tay (ket qua thao tac)
  notes.txt     - ghi chu nhap tu ban phim (--note): go 1 dong + Enter de danh dau buoc, vd "bat dau xay"
Dung: Ctrl+C.
Chi DOC: getevent + screencap, khong gui thao tac nao vao game.
"""
import argparse, datetime, json, os, re, subprocess, sys, threading, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
import yaml

cfg = yaml.safe_load(open(os.path.join(BASE, "config.yaml"), encoding="utf-8"))
ADB = cfg["ldplayer"]["adb"]
TOUCH_DEV = "/dev/input/event2"
SX, SY = 540 / 960, 960 / 540          # raw touch -> toa do man hinh (xem bot/touch.py)
TAP_MAX_MOVE, LONG_PRESS_S = 12, 0.6
AFTER_DELAY = 1.5
KEYS = {"KEY_BACK": "back", "KEY_HOMEPAGE": "home", "KEY_APPSELECT": "recent"}


def adb(serial, *a, **kw):
    return subprocess.run([ADB, "-s", serial, *a], capture_output=True, timeout=kw.get("timeout", 15))


class Recorder:
    def __init__(self, serial, outdir):
        self.serial, self.out = serial, outdir
        self.n = 0
        self.lock = threading.Lock()
        self.f = open(os.path.join(outdir, "events.jsonl"), "a", encoding="utf-8")
        self.t0 = time.time()

    def shot(self, name):
        try:
            png = adb(self.serial, "exec-out", "screencap", "-p", timeout=10).stdout
            if png[:4] == b"\x89PNG":
                open(os.path.join(self.out, name), "wb").write(png)
                return name
        except Exception:
            pass
        return None

    def activity(self):
        try:
            s = adb(self.serial, "shell", "dumpsys activity activities | grep -m1 mResumedActivity").stdout.decode(errors="ignore")
            m = re.search(r"\s(\S+/\S+)\s", s)
            return m.group(1) if m else ""
        except Exception:
            return ""

    def write(self, ev):
        ev["t"] = round(time.time() - self.t0, 2)
        ev["clock"] = datetime.datetime.now().strftime("%H:%M:%S")
        with self.lock:
            self.f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            self.f.flush()
        print(f"[{ev['clock']}] #{ev.get('i', '-'):>4} {ev['type']:<10} "
              + " ".join(f"{k}={v}" for k, v in ev.items() if k in ("x", "y", "x2", "y2", "dur", "key", "text")))

    def note(self, text):
        self.write({"type": "note", "text": text})
        self.shot(f"note_{int(time.time())}.png")


def run(serial, rec):
    p = subprocess.Popen([ADB, "-s", serial, "shell", "-tt", "getevent", "-lt"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
    down = None          # dict khi ngon tay dang cham
    rx = ry = None
    pending = {}         # i -> thread chup 'before'
    line_re = re.compile(r"\]\s+(/dev/input/event\d+):\s+(\S+)\s+(\S+)\s+(\S+)")
    for line in p.stdout:
        m = line_re.search(line)
        if not m:
            continue
        dev, typ, code, val = m.groups()
        if dev != TOUCH_DEV:
            if typ == "EV_KEY" and code in KEYS and val == "DOWN":
                rec.n += 1
                i = rec.n
                rec.write({"i": i, "type": "key", "key": KEYS[code], "activity": rec.activity(),
                           "before": rec.shot(f"{i:04d}_before.png")})
                threading.Timer(AFTER_DELAY, rec.shot, args=(f"{i:04d}_after.png",)).start()
            continue
        if code == "ABS_MT_POSITION_X":
            rx = int(val, 16)
        elif code == "ABS_MT_POSITION_Y":
            ry = int(val, 16)
        elif code == "BTN_TOUCH" and val == "DOWN":
            rec.n += 1
            i = rec.n
            down = {"i": i, "ts": time.time(), "pts": []}
            th = threading.Thread(target=rec.shot, args=(f"{i:04d}_before.png",))
            th.start()
            pending[i] = th
        elif code == "BTN_TOUCH" and val == "UP" and down:
            pts = down["pts"] or [(0, 0)]
            (x1, y1), (x2, y2) = pts[0], pts[-1]
            dur = round(time.time() - down["ts"], 2)
            moved = max(abs(x2 - x1), abs(y2 - y1))
            kind = "tap" if moved <= TAP_MAX_MOVE and dur < LONG_PRESS_S else \
                   "long_press" if moved <= TAP_MAX_MOVE else "swipe"
            i = down["i"]
            ev = {"i": i, "type": kind, "x": x1, "y": y1, "dur": dur, "before": f"{i:04d}_before.png",
                  "after": f"{i:04d}_after.png"}
            if kind == "swipe":
                step = max(1, len(pts) // 12)
                ev.update({"x2": x2, "y2": y2, "path": pts[::step] + [pts[-1]]})

            def finish(ev=ev, i=i):
                th = pending.pop(i, None)
                if th:
                    th.join(5)          # cho anh 'before' xong truoc khi ghi
                ev["activity"] = rec.activity()
                rec.write(ev)
            threading.Thread(target=finish).start()
            threading.Timer(AFTER_DELAY, rec.shot, args=(ev["after"],)).start()
            down = None
        elif code == "SYN_REPORT" and down is not None and rx is not None and ry is not None:
            pt = (round(rx * SX), round(ry * SY))
            if not down["pts"] or down["pts"][-1] != pt:
                down["pts"].append(pt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idx", type=int, default=6, help="ID instance LDPlayer (MFarm06 = 6)")
    ap.add_argument("--name", default="demo")
    ap.add_argument("--note", action="store_true", help="cho phep go ghi chu buoc tu ban phim")
    a = ap.parse_args()
    serial = f"emulator-{5554 + 2 * a.idx}"
    if b"device" not in adb(serial, "get-state").stdout:
        sys.exit(f"{serial} chua san sang - bat instance {a.idx} truoc")
    out = os.path.join(BASE, "logs", "rec", datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + a.name)
    os.makedirs(out)
    rec = Recorder(serial, out)
    pkg = adb(serial, "shell", "pm list packages | grep -i warpath").stdout.decode().strip().replace("package:", "")
    rec.write({"type": "session", "serial": serial, "idx": a.idx, "packages": pkg.split(), "activity": rec.activity(),
               "before": rec.shot("0000_start.png")})
    print(f"Dang ghi {serial} -> {out}\nThao tac tren LDPlayer nhu binh thuong. Ctrl+C de dung.")
    if a.note:
        def notes():
            for ln in sys.stdin:
                if ln.strip():
                    rec.note(ln.strip())
                    open(os.path.join(out, "notes.txt"), "a", encoding="utf-8").write(
                        f"{datetime.datetime.now():%H:%M:%S} {ln.strip()}\n")
        threading.Thread(target=notes, daemon=True).start()
    try:
        run(serial, rec)
    except KeyboardInterrupt:
        pass
    rec.write({"type": "end", "before": rec.shot("9999_end.png")})
    print("Da luu:", out)


if __name__ == "__main__":
    main()
