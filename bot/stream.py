"""Luong anh nhanh tu 1 ket noi adb (screencap raw lien tuc) + dieu khien cham/keo qua 1 shell giu san.

Dung cho tran danh can lai (nhat buff, ne nerf, ne tan cong) - can nhieu khung hinh/giay.
"""
import subprocess, threading, time
import numpy as np


class FrameStream:
    def __init__(self, adb, serial, w=540, h=960):
        self.w, self.h = w, h
        self.size = w * h * 4
        self.proc = subprocess.Popen(
            [adb, "-s", serial, "exec-out", "while true; do screencap; done"],
            stdout=subprocess.PIPE, bufsize=0)
        self.frame, self.t, self.count = None, 0, 0
        self._stop = False
        threading.Thread(target=self._reader, daemon=True).start()

    def _read(self, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = self.proc.stdout.read(n - len(buf))
            if not chunk:
                raise EOFError
            buf += chunk
        return bytes(buf)

    def _reader(self):
        try:
            while not self._stop:
                hdr = self._read(16)  # w, h, format, colorspace (Android 9+)
                w, h = np.frombuffer(hdr[:8], np.uint32)
                data = self._read(int(w) * int(h) * 4)
                rgba = np.frombuffer(data, np.uint8).reshape(int(h), int(w), 4)
                self.frame = rgba[..., [2, 1, 0]].copy()  # -> BGR cho OpenCV
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


class Shell:
    """Shell adb giu san: gui 'input ...' khong ton thoi gian mo ket noi moi."""

    def __init__(self, adb, serial):
        self.p = subprocess.Popen([adb, "-s", serial, "shell"], stdin=subprocess.PIPE,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, bufsize=0)

    def send(self, cmd):
        self.p.stdin.write((cmd + "\n").encode())

    def swipe(self, x1, y1, x2, y2, ms=120):
        self.send(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(ms)} &")

    def tap(self, x, y):
        self.send(f"input tap {int(x)} {int(y)} &")

    def close(self):
        try:
            self.p.stdin.close(); self.p.kill()
        except Exception:
            pass
