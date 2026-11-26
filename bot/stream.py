"""Luong anh nhanh tu 1 ket noi adb (screencap raw lien tuc) + dieu khien cham/keo qua 1 shell giu san.

Dung cho tran danh can lai (nhat buff, ne nerf, ne tan cong) - can nhieu khung hinh/giay.
"""
import subprocess, threading, time
import numpy as np

from bot.device import normalize_frame


class FrameStream:
    def __init__(self, adb, serial, w=540, h=960):
        self.adb, self.serial = adb, serial
        self.w, self.h = w, h
        self.size = w * h * 4
        self.frame, self.t, self.count = None, 0, 0
        self.restarts = 0
        self.proc = None
        self._start()

    def _start(self):
        """P13d-2: (khoi dong lai) luong screencap lien tuc. Dem khung / thoi gian de biet fps that."""
        self.proc = subprocess.Popen(
            [self.adb, "-s", self.serial, "exec-out", "while true; do screencap; done"],
            stdout=subprocess.PIPE, bufsize=0)
        self.started_at, self.count_at_start = time.time(), self.count
        self._stop = False
        threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()

    def fps(self):
        """Khung / giay tu lan (khoi dong lai) gan nhat."""
        dt = time.time() - self.started_at
        return (self.count - self.count_at_start) / dt if dt > 0.5 else 0.0

    def restart(self):
        """Dong bang hinh (reader chet / adb treo): giet tien trinh cu, mo luong moi."""
        try:
            self.proc.kill()
        except Exception:
            pass
        self.restarts += 1
        self._start()

    def _read(self, n, proc):
        buf = bytearray()
        while len(buf) < n:
            chunk = proc.stdout.read(n - len(buf))
            if not chunk:
                raise EOFError
            buf += chunk
        return bytes(buf)

    def _reader(self, proc):
        try:
            while not self._stop and proc is self.proc:
                hdr = self._read(16, proc)  # w, h, format, colorspace (Android 9+)
                w, h = np.frombuffer(hdr[:8], np.uint32)
                data = self._read(int(w) * int(h) * 4, proc)
                rgba = np.frombuffer(data, np.uint8).reshape(int(h), int(w), 4)
                self.frame = normalize_frame(rgba[..., [2, 1, 0]].copy())[0]  # BGR cho OpenCV, he 540x960
                self.t = time.time()
                self.count += 1
        except Exception:
            pass

    def latest(self, newer_than=0, timeout=2.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.frame is not None and self.t > newer_than:
                return self.frame, self.t
            time.sleep(0.01)
        return self.frame, self.t

    def close(self):
        self._stop = True
        try:
            self.proc.kill()
        except Exception:
            pass
