"""Cham/keo cap thap bang sendevent (giu ngon tay suot tran va truot ngang - kieu nguoi choi lai doi quan).

LDPlayer: thiet bi /dev/input/event2, truc KHONG xoay ma co ti le: X_touch = x * 960/540, Y_touch = y * 540/960
(do tu ban ghi thao tac that). 'input swipe' khong dung duoc: game chi di chuyen khi ngon tay giu lien tuc.
P13g-2: may chay do phan giai khac (Device.scale != 1) -> nhan them scale (gia dinh truc cham ti le theo do phan
giai - CHUA do tren may that).
"""
import subprocess

DEV = "/dev/input/event2"
SX, SY = 960 / 540, 540 / 960


class Finger:
    """Moi thao tac = 1 lenh 'adb shell' rieng (shell giu san qua stdin bi adb tren Windows dem lai,
    chi chay khi dong -> giu/keo bien thanh 1 cu cham). Trang thai cham giu nguyen tren thiet bi giua cac lenh."""

    def __init__(self, adb, serial, dev=DEV, scale=1.0):
        self.dev, self.adb, self.serial = dev, adb, serial
        self.sx, self.sy = SX * scale, SY * scale
        self.down_ = False
        self.x = self.y = None
        self.tid = 300

    def _send(self, *events):
        cmd = "; ".join(f"sendevent {self.dev} {t} {c} {v}" for t, c, v in events)
        subprocess.run([self.adb, "-s", self.serial, "shell", cmd],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)

    def down(self, x, y):
        self.tid += 1
        self.x, self.y = x, y
        self._send((3, 57, self.tid), (1, 330, 1), (3, 53, int(x * self.sx)), (3, 54, int(y * self.sy)), (0, 0, 0))
        self.down_ = True

    def move(self, x, y=None, step=6):
        """Truot tu vi tri hien tai toi x (nhieu buoc nho nhu ngon tay that)."""
        if not self.down_:
            return
        y = self.y if y is None else y
        n = max(1, int(abs(x - self.x) / step))
        evs = []
        for i in range(1, n + 1):
            xi = self.x + (x - self.x) * i / n
            evs += [(3, 53, int(xi * self.sx)), (3, 54, int(y * self.sy)), (0, 0, 0)]
        self._send(*evs)
        self.x, self.y = x, y

    def drag_by(self, dx, step=12, dt=0.02, y=None):
        """Keo ngang dx px THEO THOI GIAN (moi buoc <= step px, cach nhau dt giay) trong 1 lenh adb.
        Do tren tran tan thu 2026-11-18: game BO QUA cu nhay lon trong 1 khung (gui +200 px 1 lan -> linh dung yen);
        keo cham 15 px/80 ms -> linh di theo voi he so ~0.4. Gui het cac buoc 6 px trong 1 lan (nhu move()) cung bi bo qua."""
        if not self.down_ or dx == 0:
            return
        y = self.y if y is None else y
        n = max(1, int(abs(dx) / step))
        parts = []
        for i in range(1, n + 1):
            xi = self.x + dx * i / n
            parts.append(f"sendevent {self.dev} 3 53 {int(xi * self.sx)}; sendevent {self.dev} 3 54 {int(y * self.sy)}; "
                         f"sendevent {self.dev} 0 0 0")
        cmd = f"; sleep {dt}; ".join(parts)
        subprocess.run([self.adb, "-s", self.serial, "shell", cmd],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        self.x, self.y = self.x + dx, y

    def drag_to(self, x, y, step=10, dt=0.02):
        """Keo 2 chieu toi (x, y) theo thoi gian (moi buoc <= step px, cach dt giay) - dung keo cong trinh vao o xay."""
        if not self.down_:
            return
        dist = max(abs(x - self.x), abs(y - self.y))
        n = max(1, int(dist / step))
        parts = []
        for i in range(1, n + 1):
            xi = self.x + (x - self.x) * i / n
            yi = self.y + (y - self.y) * i / n
            parts.append(f"sendevent {self.dev} 3 53 {int(xi * self.sx)}; sendevent {self.dev} 3 54 {int(yi * self.sy)}; "
                         f"sendevent {self.dev} 0 0 0")
        subprocess.run([self.adb, "-s", self.serial, "shell", f"; sleep {dt}; ".join(parts)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        self.x, self.y = x, y

    def up(self):
        if self.down_:
            self._send((3, 57, 4294967295), (1, 330, 0), (0, 0, 0))
            self.down_ = False

    def close(self):
        try:
            self.up()
        except Exception:
            pass
