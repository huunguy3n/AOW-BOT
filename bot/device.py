"""Dieu khien LDPlayer (ldconsole) va ADB."""
import subprocess, time, logging, threading
import cv2, numpy as np

from aowbot.domain import rollout
from bot import hang

log = logging.getLogger("aow")


class ScreencapError(RuntimeError):
    """Khong chup duoc man hinh. Thong diep luon chua 'Khong chup duoc man hinh' (runner dem buoc 'mu')."""


class LDConsole:
    _slot = threading.Lock()   # 2 luong cung bat may: kiem tra so may + launch phai nguyen tu (khong vuot max_running)

    def __init__(self, cfg):
        self.exe = cfg["ldconsole"]
        self.boot_timeout = cfg.get("boot_timeout", 120)
        self.max_running = rollout.max_running(cfg.get("max_running", 2))   # P6: tran cung 2 may
        self.wait_slot = cfg.get("wait_slot_min", 60) * 60

    def run(self, *args, timeout=60):
        r = subprocess.run([self.exe, *map(str, args)], capture_output=True,
                           text=True, timeout=timeout, errors="ignore")
        return (r.stdout or "").strip()

    def is_running(self, idx):
        return "running" in self.run("isrunning", "--index", idx).lower()

    def running(self):
        """ID cac instance dang chay (list2: cot 5 = 1 khi dang chay)."""
        out = []
        for line in self.run("list2").splitlines():
            p = line.split(",")
            if len(p) > 4 and p[0].isdigit() and p[4].strip() == "1":
                out.append(int(p[0]))
        return out

    def launch(self, idx):
        if self.is_running(idx):
            return True
        # gioi han so may chay cung luc (chu du an: toi da 2) - tinh ca may do tien trinh/nguoi khac bat
        t0 = time.time()
        while True:
            with LDConsole._slot:
                run = self.running()
                if len(run) < self.max_running:
                    self.run("launch", "--index", idx)
                    t1 = time.time()   # giu khoa toi khi may moi hien 'dang chay' -> luong kia dem dung
                    while time.time() - t1 < 30 and idx not in self.running():
                        time.sleep(1)
                    break
            if time.time() - t0 > self.wait_slot:
                log.warning("Da co %d may dang chay (toi da %d) - khong bat #%d", len(run), self.max_running, idx)
                return False
            log.info("Dang co %s chay (toi da %d) - cho truoc khi bat #%d", run, self.max_running, idx)
            time.sleep(30)
        t0 = time.time()
        while time.time() - t0 < self.boot_timeout:
            if self.is_running(idx):
                return True
            time.sleep(3)
        return False

    def quit(self, idx, wait=25):
        """Tat may va KIEM TRA da tat (2026-11-21: may con bat sau luot -> chiem cho, may khac phai cho).
        Lan 1 khong tat -> goi quit lan 2. -> True neu da tat."""
        for _ in range(2):
            self.run("quit", "--index", idx)
            t0 = time.time()
            while time.time() - t0 < wait:
                if idx not in self.running():
                    return True
                time.sleep(2)
            log.warning("[#%s] ldconsole quit chua tat may sau %d s -> thu lai", idx, wait)
        log.error("[#%s] Khong tat duoc may", idx)
        return False

    def runapp(self, idx, pkg):
        self.run("runapp", "--index", idx, "--packagename", pkg)


SCREEN_W, SCREEN_H = 540, 960


def clamp_xy(x, y, who=""):
    """P13c: kep toa do cham vao khung 540x960 (0..539 x 0..959). Live6b: offset mu day diem cham ra y=964 (ngoai man).
    Phai kep -> ghi log. Tra (x, y) int."""
    cx = min(max(int(x), 0), SCREEN_W - 1)
    cy = min(max(int(y), 0), SCREEN_H - 1)
    if (cx, cy) != (int(x), int(y)):
        logging.getLogger("aow").warning("Kep toa do cham %s (%d,%d) -> (%d,%d): ngoai man 540x960", who, int(x), int(y), cx, cy)
    return cx, cy


def frame_scale(w, h):
    """P13g-2: khung DOC dung ti le 540:960 -> he so toa do may / 540 (1.0 = dung chuan); ti le khac (man ngang
    luc mo may...) -> None. Ham thuan."""
    if h <= w or abs(w * SCREEN_H - h * SCREEN_W) > h * 2:
        return None
    return w / SCREEN_W


def normalize_frame(img):
    """-> (khung 540x960, he so) | (khung goc, None). May bi doi do phan giai (#0 26/11/2026: 720x1280) -> thu nho
    ve he toa do chuan (ADR-0003) de anh mau / ROI / toa do cu van dung."""
    h, w = img.shape[:2]
    s = frame_scale(w, h)
    if s is None or (w, h) == (SCREEN_W, SCREEN_H):
        return img, s
    return cv2.resize(img, (SCREEN_W, SCREEN_H), interpolation=cv2.INTER_AREA), s


class Device:
    """Mot instance LDPlayer qua ADB. Instance N -> emulator-(5554+2N)."""

    def __init__(self, adb, idx, serial=None):
        self.adb = adb
        self.idx = idx
        self.serial = serial or f"emulator-{5554 + 2 * idx}"

    perf = None   # bot.perf.Perf cua lan ghe (runner gan) - A-MEAS-1
    scale = 1.0       # P13g-2: toa do may = toa do 540x960 x scale (theo khung doc gan nhat)
    odd_size = None   # (w, h) cua khung khong dung ti le da canh bao

    def _normalize(self, img):
        out, s = normalize_frame(img)
        size = (img.shape[1], img.shape[0])
        if s is None:
            if size != self.odd_size:
                self.odd_size = size
                log.warning("[#%s] Khung chup %dx%d khong dung ti le man doc 540x960 - de nguyen", self.idx, *size)
            return img
        if s != self.scale:
            if s != 1.0:
                log.warning("[#%s] Man hinh may la %dx%d, khac 540x960 -> thu nho anh va nhan toa do cham x%.3f. "
                            "Nen dat lai do phan giai may #%s trong LDPlayer: 540x960, DPI 240", self.idx, *size, s,
                            self.idx)
            else:
                log.info("[#%s] Man hinh ve lai 540x960", self.idx)
            self.scale = s
        return out

    def _dev_xy(self, x, y):
        """Toa do 540x960 -> toa do may."""
        return int(round(x * self.scale)), int(round(y * self.scale))

    @staticmethod
    def _kind(args):
        """Loai lenh adb de dem hieu nang: tap / swipe / key / screencap_raw / screencap_png / pidof / ..."""
        a = [str(x) for x in args]
        if a[:2] == ["shell", "input"] and len(a) > 2:
            return {"keyevent": "key"}.get(a[2], a[2])
        if a and a[0] == "exec-out":
            return "screencap_png" if "-p" in a else "screencap_raw"
        if a and a[0] == "shell" and len(a) > 1:
            return a[1]
        return a[0] if a else "?"

    def _cmd(self, *args, timeout=30, binary=False):
        t0 = time.perf_counter()
        try:
            r = subprocess.run([self.adb, "-s", self.serial, *map(str, args)],
                               capture_output=True, timeout=timeout)
        finally:
            if self.perf is not None:
                self.perf.add("adb_" + self._kind(args), time.perf_counter() - t0)
        return r.stdout if binary else r.stdout.decode("utf-8", "ignore")

    def wait_ready(self, timeout=120):
        t0 = time.time()
        while time.time() - t0 < timeout:
            # thu ca 2 dia chi: emulator-55xx va 127.0.0.1:55xx (#0 sau khi cau hinh lai 2026-11-20 khong tra loi
            # qua emulator-5554: "ADB khong ket noi duoc" 3 lan) -> dia chi nao tra loi thi dung tiep
            for ser in dict.fromkeys([self.serial, f"emulator-{5554 + 2 * self.idx}", f"127.0.0.1:{5555 + 2 * self.idx}"]):
                try:
                    r = subprocess.run([self.adb, "-s", ser, "shell", "getprop", "sys.boot_completed"],
                                       capture_output=True, timeout=min(10, max(3, timeout / 3)))
                    if r.stdout.decode("utf-8", "ignore").strip() == "1":
                        if ser != self.serial:
                            log.info("ADB #%d: dung dia chi %s (thay %s)", self.idx, ser, self.serial)
                            self.serial = ser
                        return True
                except Exception:
                    pass
            # LDPlayer doi khi can 'adb connect'; luc may dang khoi dong lenh nay co the treo -> bo qua
            try:
                subprocess.run([self.adb, "connect", f"127.0.0.1:{5555 + 2 * self.idx}"],
                               capture_output=True, timeout=min(10, max(3, timeout / 3)))
            except subprocess.TimeoutExpired:
                pass
            time.sleep(3)
        return False

    # A-OPT-3 (P1, 2026-11-23): truoc day 1 lan chup hong treo toi ~190 s (4 lan x (raw 20 s + PNG 20 s) + nghi
    # + do lai dia chi 30 s + 4 lan nua), roi save_debug chup them lan nua. Nay: timeout ngan, ngan sach tong,
    # 2 lan timeout lien tiep = may treo (khong thu PNG sau khi raw timeout), do lai dia chi 1 lan ngan; khong cuu
    # duoc -> dead = True: moi lan chup sau nem loi NGAY de runner bo may sang may ke tiep. Tham so: ldplayer.screencap.
    # P9-1 (live-run-2 treo 11:11): rut ngan 8/30/15 -> 5/15/10 (bot.hang) - may treo phat hien sau <= ~30 s
    shot_timeout = hang.SHOT_TIMEOUT_S      # giay / 1 lenh screencap (binh thuong ~0,4-0,6 s)
    shot_tries = 3           # so lan thu mac dinh
    shot_budget = hang.SHOT_BUDGET_S        # tong thoi gian toi da 1 lan screencap() (ke ca thu lai)
    shot_max_timeouts = 2    # timeout lien tiep -> coi nhu may treo, thoi thu
    reconnect_wait = hang.RECONNECT_WAIT_S  # wait_ready khi het luot (doi dia chi adb)
    dead = False             # may khong phan hoi: moi lan chup sau nem ScreencapError ngay

    def configure(self, lc):
        """Doc ldplayer.screencap (config.yaml) - thieu khoa thi giu mac dinh tren."""
        sc = (lc or {}).get("screencap") or {}
        self.shot_timeout = float(sc.get("timeout_s", self.shot_timeout))
        self.shot_tries = int(sc.get("tries", self.shot_tries))
        self.shot_budget = float(sc.get("budget_s", self.shot_budget))
        self.shot_max_timeouts = int(sc.get("max_timeouts", self.shot_max_timeouts))
        self.reconnect_wait = float(sc.get("reconnect_wait_s", self.reconnect_wait))
        return self

    def screencap(self, tries=None, _reconnect=True):
        """Chup man hinh; adb doi khi tra ve rong (may vua khoi dong / dang ban) -> thu lai.
        Het luot ma van hong: dia chi adb co the da doi (emulator-55xx <-> 127.0.0.1:55xx, #6/#3 2026-11-21
        'error: device not found' ngay sau khi mo game) -> wait_ready do lai dia chi roi chup them 1 lan.
        Khong cuu duoc -> dead = True (runner bo may nay)."""
        if self.dead:
            raise ScreencapError("Khong chup duoc man hinh (may khong phan hoi)")
        tries = self.shot_tries if tries is None else tries
        t0 = time.perf_counter()
        ok = False
        try:
            try:
                img = self._screencap(tries)
            except ScreencapError as e:
                if not _reconnect or tries < 3:
                    raise
                log.warning("ADB #%d: khong chup duoc qua %s (%s) -> do lai dia chi", self.idx, self.serial, e)
                if not self.wait_ready(self.reconnect_wait):
                    self.dead = True
                    raise ScreencapError("Khong chup duoc man hinh (ADB khong tra loi sau do lai dia chi)") from e
                # P13-13 (live5 #1 buoc tinh bao: 3 doi dang chay, ADB nghen tam thoi): sau khi do lai dia chi thu 1 lan voi
                # timeout GAP DOI (toi da 12 s) truoc khi coi may la treo; chi dung 1 lan, khong lap
                old_timeout = self.shot_timeout
                self.shot_timeout = min(old_timeout * 2, 12.0)
                try:
                    img = self._screencap(min(tries, 2))
                except ScreencapError:
                    self.dead = True
                    raise
                finally:
                    self.shot_timeout = old_timeout
            ok = True
            return img
        finally:
            if self.perf is not None:   # tong thoi gian 1 lan chup, ke ca thu lai (do 'duoi dai' khi may treo)
                self.perf.add("screencap" if ok else "screencap_fail", time.perf_counter() - t0)

    def _screencap(self, tries):
        t0 = time.monotonic()
        timeouts = 0
        for k in range(tries):
            img, timed_out = None, False
            try:
                img = self._raw_shot() if self.raw else None
                if img is None:
                    data = self._cmd("exec-out", "screencap", "-p", binary=True, timeout=self.shot_timeout)
                    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR) if data else None
            except subprocess.TimeoutExpired:
                timed_out = True
            except cv2.error:
                img = None
            if img is not None:
                return self._normalize(img)
            timeouts = timeouts + 1 if timed_out else 0
            if timeouts >= self.shot_max_timeouts:
                raise ScreencapError(f"Khong chup duoc man hinh ({timeouts} lan timeout {self.shot_timeout:.0f} s)")
            if k + 1 >= tries or time.monotonic() - t0 >= self.shot_budget:
                break
            time.sleep(min(1.0 * (k + 1), max(0.0, self.shot_budget - (time.monotonic() - t0))))
        raise ScreencapError("Khong chup duoc man hinh")

    raw = True   # screencap tho (khong nen PNG tren may): ~400 ms thay vi ~600 ms (do #4 2026-11-20)

    def _raw_shot(self):
        """screencap khong -p: header (w, h, format[, colorspace]) + RGBA. Sai dinh dang -> None (dung PNG).
        Timeout -> nem TimeoutExpired (khong thu PNG: may treo thi PNG cung treo)."""
        data = self._cmd("exec-out", "screencap", binary=True, timeout=self.shot_timeout)
        if not data or len(data) < 16:
            return None
        w, h, fmt = np.frombuffer(data[:12], "<u4")
        hdr = len(data) - int(w) * int(h) * 4
        if fmt != 1 or hdr not in (12, 16) or not (100 < w < 4000 and 100 < h < 4000):
            return None
        rgba = np.frombuffer(data, np.uint8, offset=hdr).reshape(int(h), int(w), 4)
        return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)

    def _mine(self, x, y, t0):
        """Ghi lai thao tac CUA BOT: tren LDPlayer 'input tap/swipe' cung di qua /dev/input/event2 nen bot/human.py
        thay ca cham cua bot (lan dau 2026-11-21: moi cham cua bot bi ghi la 'nguoi thao tac tay')."""
        if not hasattr(self, "recent"):
            import collections
            self.recent = collections.deque(maxlen=50)
        self.recent.append([t0, t0, int(x), int(y), False])

    def is_mine(self, t, x, y, back=8.0, dist=25):
        """Su kien cham nhan luc t tai (x, y) co phai do bot gui khong. getevent qua adb ve TRE vai giay (do
        2026-11-21) -> khong so sat thoi gian: lay lan cham cua bot CU NHAT chua khop, trong 'back' giay truoc t,
        cung cho (+-dist px); khop roi thi danh dau (moi lan cham cua bot chi tru 1 su kien)."""
        for e in list(getattr(self, "recent", ())):
            t0, t1, bx, by, used = e
            if not used and t - back <= t0 <= t + 0.5 and abs(bx - x) <= dist and abs(by - y) <= dist:
                e[4] = True
                return True
        return False

    # ghi TRUOC khi gui lenh: 'input tap' tren LDPlayer mat ~1 s moi tra ve, su kien cham da toi bot/human.py truoc do
    def tap(self, x, y):
        x, y = clamp_xy(x, y, "tap")
        self.act_seq = getattr(self, "act_seq", 0) + 1     # G3: ctx.ensure_city biet co thao tac nao tu lan kiem truoc
        self._mine(x, y, time.time())
        self._cmd("shell", "input", "tap", *self._dev_xy(x, y))

    def swipe(self, x1, y1, x2, y2, ms=300):
        x1, y1 = clamp_xy(x1, y1, "swipe")
        x2, y2 = clamp_xy(x2, y2, "swipe")
        self.act_seq = getattr(self, "act_seq", 0) + 1
        self._mine(x1, y1, time.time())
        self._cmd("shell", "input", "swipe", *self._dev_xy(x1, y1), *self._dev_xy(x2, y2), int(ms))

    def type_digits(self, s, clear=4, enter=False):
        """P7-10/P10-3: go SO vao o nhap dang co tieu diem (o "Cap" tim kiem). Chi chu so (khong bao gio go chu tu do).
        Live3 15:43 (s154328/s154354): o con "1" sau khi go 9/8 - DEL gui don dap bi mat, so go khong vao -> nay:
        MOVE_END, xoa `clear` ky tu cu TUNG phim mot (co nghi), 'input text', khong Enter (nguoi goi bam "OK" ban phim)."""
        s = str(s)
        if not s.isdigit():
            raise ValueError("type_digits: chi nhan chu so")
        self.act_seq = getattr(self, "act_seq", 0) + 1
        self._cmd("shell", "input", "keyevent", "123")         # KEYCODE_MOVE_END: con tro cuoi o
        for _ in range(clear):
            self._cmd("shell", "input", "keyevent", "67")      # KEYCODE_DEL
            time.sleep(0.12)
        self._cmd("shell", "input", "text", s)
        if enter:
            self._cmd("shell", "input", "keyevent", "66")

    def back(self):
        self.act_seq = getattr(self, "act_seq", 0) + 1
        self.backs = getattr(self, "backs", 0) + 1       # bot/human.py: phim Back cua bot, khong phai cua nguoi
        self.back_t = time.time()
        self._cmd("shell", "input", "keyevent", "4")

    def find_package(self, keyword="warpath"):
        out = self._cmd("shell", "pm", "list", "packages")
        for line in out.splitlines():
            if keyword in line.lower():
                return line.split(":", 1)[-1].strip()
        return None

    def app_alive(self, pkg):
        """Game con tien trinh khong (pidof). Loi adb -> coi nhu con (khong khoi dong lai vo co)."""
        try:
            return bool(self._cmd("shell", "pidof", pkg, timeout=10).strip())
        except Exception:
            return True

    def force_stop(self, pkg):
        """Dung game (KHONG xoa du lieu - khac 'pm clear')."""
        self._cmd("shell", "am", "force-stop", pkg)

    def start_app(self, pkg):
        self._cmd("shell", "monkey", "-p", pkg, "-c",
                  "android.intent.category.LAUNCHER", "1")
