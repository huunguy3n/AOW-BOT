"""Bat thao tac TAY cua chu du an trong luc bot dang chay (chu du an 2026-11-20: "moi khi co su kien toi click,
keo tha la bot dang chua hoan thien, can chup hinh ngay luc toi thao tac").

Moi may dang duoc bot ghe co 1 luong doc `adb shell getevent -lt` (CHI DOC, khong gui gi vao game):
  - ngon tay cham (BTN_TOUCH DOWN) -> chup man hinh NGAY (anh 'truoc')
  - nhac tay (UP) -> phan loai tap / long_press / swipe (keo tha), chup anh 'sau' ~1,2 s sau
  - phim Back / Home cua LDPlayer -> cung ghi
Luu vao logs/human/<ngay>/<gio>-i<idx>-<buoc>-<n>_{before,after,mark}.png + events.jsonl;
anh 'mark' = anh truoc co ve vong tron (cham) / mui ten (keo) de doc nhanh.
Ghi bang exp (kind='human', ket qua do bang learn.outcome) va them anh mark vao ctx.debug_shots -> buoc dang chay
hien 'co anh loi' tren web: noi nao chu du an phai ra tay = noi bot con thieu.

Loc thao tac CUA BOT: tren LDPlayer `input tap/swipe/keyevent` cua bot CUNG hien tren /dev/input (do 2026-11-21) ->
Device ghi moi lan cham/keo/Back truoc khi gui lenh, su kien trung cho (+-25 px, trong 8 s) bi bo (Device.is_mine);
lai quan (steer, sendevent vao event2) -> bo qua khi steer dang lai tren may nay (steer.active_serials).
"""
import datetime, json, logging, os, re, subprocess, threading, time
import cv2

from bot import perf

log = logging.getLogger("aow")
TOUCH_DEV = "/dev/input/event2"
SX, SY = 540 / 960, 960 / 540          # raw touch -> toa do man hinh (bot/touch.py)
TAP_MAX_MOVE, LONG_PRESS_S, AFTER_DELAY = 12, 0.6, 1.2
KEYS = {"KEY_BACK": "back", "KEY_HOMEPAGE": "home", "KEY_APPSELECT": "recent"}
LINE = re.compile(r"\]\s+(/dev/input/event\d+):\s+(\S+)\s+(\S+)\s+(\S+)")


class HumanWatch:
    def __init__(self, ctx, adb):
        self.ctx, self.adb = ctx, adb
        self.dev = ctx.dev
        self.n = 0
        self.proc = None
        self.stop_ev = threading.Event()
        self.th = threading.Thread(target=self._loop, name=f"#{self.dev.idx}-tay", daemon=True)

    # ----- vong doi -----
    def start(self):
        self.th.start()
        return self

    def stop(self):
        self.stop_ev.set()
        try:
            if self.proc:
                self.proc.kill()
        except Exception:
            pass

    # ----- tien ich -----
    def _shot(self):
        try:
            with perf.as_src("human"):      # A-MEAS-1: tach chi phi anh chup cua HumanWatch
                return self.dev.screencap(tries=2)
        except Exception:
            return getattr(self.ctx, "_img", None)

    def _steering(self):
        from bot import steer
        return self.dev.serial in getattr(steer, "active_serials", set())

    def _loop(self):
        while not self.stop_ev.is_set():
            try:
                self._read()
            except Exception as e:
                log.debug("HumanWatch #%d: %s", self.dev.idx, e)
            if not self.stop_ev.wait(5):
                continue

    def _read(self):
        self.proc = subprocess.Popen([self.adb, "-s", self.dev.serial, "shell", "-tt", "getevent", "-lt"],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1,
                                     errors="ignore")
        down, rx, ry = None, None, None
        for line in self.proc.stdout:
            if self.stop_ev.is_set():
                break
            m = LINE.search(line)
            if not m:
                continue
            dev, typ, code, val = m.groups()
            if dev != TOUCH_DEV:
                if typ == "EV_KEY" and code in KEYS and val == "DOWN":
                    if code == "KEY_BACK" and getattr(self.dev, "backs", 0) > 0                             and time.time() - getattr(self.dev, "back_t", 0) < 8:
                        self.dev.backs -= 1          # phim Back do bot gui
                        continue
                    hp = getattr(self.ctx, "human_pause", None)
                    if hp is not None:
                        hp.note()
                    before = self._shot()
                    self._finish({"type": "key", "key": KEYS[code]}, before)
                continue
            if self._steering():
                down = None
                continue
            if code == "ABS_MT_POSITION_X":
                rx = int(val, 16)
            elif code == "ABS_MT_POSITION_Y":
                ry = int(val, 16)
            elif code == "BTN_TOUCH" and val == "DOWN":
                down = {"ts": time.time(), "pts": [], "before": None, "step": self.ctx.step}
                threading.Thread(target=lambda d=down: d.__setitem__("before", self._shot()), daemon=True).start()
            elif code == "BTN_TOUCH" and val == "UP" and down:
                pts = down["pts"] or [(0, 0)]
                (x1, y1), (x2, y2) = pts[0], pts[-1]
                # 'input tap/swipe' cua chinh bot cung hien o day (LDPlayer) -> bo neu trung luc + cho bot vua cham.
                # Lenh adb tra ve SAU khi su kien da phat -> doi 0,3 s cho bot ghi xong roi moi so.
                if self._bot_touch(down["ts"], x1, y1):
                    if self.dev.perf is not None:   # moi lan = 1 anh "truoc" da chup thua (A-OPT-5)
                        self.dev.perf.add("bot_touch_seen", 0.0, "human")
                    down = None
                    continue
                hp = getattr(self.ctx, "human_pause", None)
                if hp is not None:            # P9-1: dem thao tac tay -> ctx.tap / runner tam dung khi chu dang choi
                    hp.note(down["ts"])
                dur = round(time.time() - down["ts"], 2)
                moved = max(abs(x2 - x1), abs(y2 - y1))
                kind = ("tap" if dur < LONG_PRESS_S else "long_press") if moved <= TAP_MAX_MOVE else "swipe"
                ev = {"type": kind, "x": x1, "y": y1, "dur": dur, "step": down["step"]}
                if kind == "swipe":
                    k = max(1, len(pts) // 12)
                    ev.update({"x2": x2, "y2": y2, "path": pts[::k] + [pts[-1]]})
                d = down
                threading.Thread(target=self._finish_touch, args=(ev, d), daemon=True).start()
                down = None
            elif code == "SYN_REPORT" and down is not None and rx is not None and ry is not None:
                pt = (round(rx * SX), round(ry * SY))
                if not down["pts"] or down["pts"][-1] != pt:
                    down["pts"].append(pt)

    def _bot_touch(self, t, x, y):
        t_end = time.time() + 0.3
        while True:
            if self.dev.is_mine(t, x, y):
                return True
            if time.time() > t_end:
                return False
            time.sleep(0.05)

    def _finish_touch(self, ev, d):
        t0 = time.time()
        while d["before"] is None and time.time() - t0 < 3:
            time.sleep(0.05)
        self._finish(ev, d["before"])

    def _finish(self, ev, before):
        """Cho ~1,2 s -> anh sau; luu 3 anh + jsonl; ghi exp; danh dau buoc co 'anh loi'."""
        time.sleep(AFTER_DELAY)
        after = self._shot()
        self.n += 1
        ctx, idx = self.ctx, self.dev.idx
        step = ev.get("step") or ctx.step or "ngoai_buoc"
        day = datetime.datetime.now().strftime("%Y%m%d")
        out = os.path.join("logs", "human", day)
        os.makedirs(out, exist_ok=True)
        base = os.path.join(out, f"{datetime.datetime.now().strftime('%H%M%S')}-i{idx}-{step}-{self.n:03d}")
        ev.update({"idx": idx, "at": time.time(), "clock": datetime.datetime.now().strftime("%H:%M:%S"),
                   "bot_step": ctx.step})
        try:
            if before is not None:
                cv2.imwrite(base + "_before.png", before)
                cv2.imwrite(base + "_mark.png", mark(before, ev))
                ev["before"] = os.path.basename(base) + "_before.png"
            if after is not None:
                cv2.imwrite(base + "_after.png", after)
                ev["after"] = os.path.basename(base) + "_after.png"
        except Exception as e:
            log.debug("HumanWatch luu anh: %s", e)
        res = {}
        if before is not None and after is not None:
            try:
                from bot import learn
                res = learn.outcome(before, after, ev.get("x"), ev.get("y"), ctx.v)
            except Exception:
                res = {}
        ev.update({k: res.get(k) for k in ("changed", "outcome")})
        with open(os.path.join(out, "events.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        desc = (f"keo {ev['x']},{ev['y']} -> {ev['x2']},{ev['y2']}" if ev["type"] == "swipe"
                else f"phim {ev['key']}" if ev["type"] == "key" else f"{ev['type']} @{ev['x']},{ev['y']}")
        log.warning("NGUOI THAO TAC TAY (%s) o buoc %s -> bot con thieu o day. Anh: %s_mark.png", desc, step, base)
        if before is not None:
            ctx.debug_shots.append(base + "_mark.png")      # buoc dang chay -> 'co anh loi' tren web
        L = ctx.learner
        if L:
            L.record([{"visit": getattr(ctx, "visit", None), "inst": idx, "step": step, "at": ev["at"],
                       "kind": "human", "tpl": None, "why": ev["type"], "x": ev.get("x"), "y": ev.get("y"),
                       "score": None, "scr": None, "changed": res.get("changed"), "diff": res.get("diff"),
                       "local": res.get("local"), "outcome": res.get("outcome"), "lat": None,
                       "crop": L.save_crop(before, ev["x"], ev["y"]) if before is not None and ev.get("x") is not None else None}])


def mark(img, ev):
    """Anh truoc + vong tron diem cham / mui ten keo tha + nhan."""
    m = img.copy()
    col = (0, 0, 255)
    if ev["type"] == "swipe":
        pts = ev.get("path") or [(ev["x"], ev["y"]), (ev["x2"], ev["y2"])]
        for a, b in zip(pts, pts[1:]):
            cv2.line(m, tuple(map(int, a)), tuple(map(int, b)), col, 3)
        cv2.arrowedLine(m, tuple(map(int, pts[-2] if len(pts) > 1 else pts[0])), (int(ev["x2"]), int(ev["y2"])), col, 4,
                        tipLength=0.4)
        cv2.circle(m, (int(ev["x"]), int(ev["y"])), 10, col, 3)
    elif ev.get("x") is not None:
        cv2.circle(m, (int(ev["x"]), int(ev["y"])), 26, col, 3)
        cv2.circle(m, (int(ev["x"]), int(ev["y"])), 4, col, -1)
    label = f"TAY: {ev['type']} {ev.get('key', '')} buoc={ev.get('step') or '-'}"
    cv2.rectangle(m, (0, 0), (540, 26), (0, 0, 0), -1)
    cv2.putText(m, label, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return m
