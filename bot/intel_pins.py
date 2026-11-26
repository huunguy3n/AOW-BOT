"""P13l (chu du an t103u, anh tests/fixtures/p13l/intel_icons_types.png): phan loai ghim Tinh bao = BIEU TUONG + MAU.

Thua 1 tran Tinh bao -> nho dung LOP ghim do (vd "guns-purple") theo tung may, bo qua lop do, van danh cac lop khac;
chi thu lai khi luc chien tang du (intel_rules.lost_gate).

Bieu tuong: so khop mat na diem TRANG (S thap, V cao) voi templates/intel/pin_icon_<ten>[@bien the].png (36x36, tam
anh = tam dau ghim). Mau: trung vi hue cua vong than ghim (ban kinh 17-21 px quanh tam). Do tren 2 anh that: tim H 137,
lam 104, luc 80, vang/cam 20 (S >= 150), ghim da xong xam S ~78. Diem khop dung 0,82-1,0; sai cao nhat 0,72.
Cap tren ghim khong co so -> lop chi gom bieu tuong + mau (huy hieu vang vach cap la bieu tuong rieng 'badge').

Moi ham la ham thuan (anh -> ket qua).
"""
from typing import NamedTuple

import cv2
import numpy as np

ICONS = {"guns": ("guns",), "skull": ("skull",), "crate": ("crate", "crate@done"), "badge": ("badge",)}
ICON_TH = 0.75
HALF = 18                   # mau bieu tuong 36x36
BASE_DY = 39                # vong chan ghim (intel/pin_base) nam duoi tam dau ghim ~38-40 px
MIN_DIST = 24               # 2 ghim che nhau: tam dau cach nhau it nhat chung nay
RING = (17, 21)
RING_SAT = 55               # vong than ghim phai co mau (ghim mo S ~29)
GREY_SAT = 115              # duoi muc nay = xam (ghim da xong)
HUES = (("gold", 10, 35), ("green", 65, 94), ("blue", 95, 120), ("purple", 125, 160))


class Pin(NamedTuple):
    x: int                  # tam DAU ghim (cho cham)
    y: int
    icon: str
    color: str
    score: float

    @property
    def cls(self):
        return f"{self.icon}-{self.color}"


def white_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return (((hsv[..., 1] < 110) & (hsv[..., 2] > 170)).astype(np.uint8)) * 255


def head_color(img, x, y):
    """Mau than ghim quanh tam dau (x, y) -> 'gold' | 'green' | 'blue' | 'purple' | 'grey' | None (khong ro)."""
    r = RING[1]
    if not (r <= x < img.shape[1] - r and r <= y < img.shape[0] - r):
        return None
    hsv = cv2.cvtColor(img[y - r:y + r + 1, x - r:x + r + 1], cv2.COLOR_BGR2HSV).astype(int)
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.hypot(xx, yy)
    ring = (d >= RING[0]) & (d <= r) & ~((hsv[..., 1] < 110) & (hsv[..., 2] > 170))
    px = hsv[ring]
    if len(px) < 100:
        return None
    sat = float(np.median(px[:, 1]))
    if sat < RING_SAT:
        return None
    if sat < GREY_SAT:
        return "grey"
    hue = float(np.median(px[px[:, 1] >= RING_SAT][:, 0]))
    for name, lo, hi in HUES:
        if lo <= hue <= hi:
            return name
    return None


def find_pins(img, v, th=ICON_TH):
    """Moi ghim nhin thay bieu tuong (ke ca ghim bi che mat vong chan) -> [Pin] tu tren xuong. Thieu mau -> []."""
    load = getattr(v, "load", None)
    if not isinstance(img, np.ndarray) or load is None or min(img.shape[:2]) <= 2 * HALF:
        return []
    mask = cv2.GaussianBlur(white_mask(img), (3, 3), 0)
    hits = []
    for icon, variants in ICONS.items():
        for name in variants:
            t = load(f"intel/pin_icon_{name}")
            if t is None:
                continue
            t = cv2.GaussianBlur(t[..., 0] if t.ndim == 3 else t, (3, 3), 0)
            res = cv2.matchTemplate(mask, t, cv2.TM_CCOEFF_NORMED)
            res[~np.isfinite(res)] = 0
            for y, x in zip(*np.nonzero(res >= th)):
                hits.append((float(res[y, x]), int(x) + HALF, int(y) + HALF, icon))
    out = []
    for score, x, y, icon in sorted(hits, reverse=True):
        if any(abs(x - p.x) < MIN_DIST and abs(y - p.y) < MIN_DIST for p in out):
            continue
        color = head_color(img, x, y)
        if color:
            out.append(Pin(x, y, icon, color, round(score, 3)))
    return sorted(out, key=lambda p: (p.y, p.x))


def class_at(pins, bx, by, dx=16, dy=16):
    """Lop cua ghim co vong chan tai (bx, by) (toa do intel/pin_base) -> 'bieu_tuong-mau' | None."""
    near = [p for p in pins if abs(p.x - bx) <= dx and abs(p.y + BASE_DY - by) <= dy]
    if not near:
        return None
    return min(near, key=lambda p: abs(p.x - bx) + abs(p.y + BASE_DY - by)).cls
