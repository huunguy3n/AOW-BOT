"""P13l (chu du an t100u-t102u, t104u; anh arrow_miss_world.png): mui ten XANH chi xuong tren ban do the gioi ->
cham dung VAT THE ngay duoi no (phien quan / mo), khong bao gio dung offset co dinh, khong bao gio cham can cu nguoi
choi.

Thu tu ung vien (trong cua so duoi mui ten):
  1. nhan "Phien quan" / "Phien quan Co giap" -> than quan ngay tren nhan;
  2. thanh mau do (don vi dang duoc chon) -> than quan ngay tren thanh mau;
  3. vat the khac nen co (mo tai nguyen / quan khong nhan) - khoi gan mui ten nhat.
Loai: can cu nguoi choi (co quoc gia canh bien ten, mai khien, the lien minh "(XXX)"), toa do da danh sach den.

Moi ham la ham thuan (anh -> ket qua); thao tac o bot/modules/arrow.py.
"""
import re
from typing import NamedTuple

import cv2
import numpy as np

from bot import ocr

TOP = 60                    # bo thanh tai nguyen tren cung (cu: 110 - mat mui ten o y ~100 tren anh chu)
BOTTOM = 800
REACH_X = 110               # vat the lech ngang mui ten toi da
REACH_Y = 230               # va nam duoi chan mui ten toi da
LABELS = (("map/label_rebel", 30), ("rebels/label_mech", 40))     # (mau, than quan cach nhan ve phia tren)
LABEL_TH = 0.75
BAR_UP = 60                 # than quan cach thanh mau ve phia tren (do: thanh y 261, than co giap y 165-225)
BAR_MIN_W, BAR_H = 60, (4, 18)
BLOB_MIN = 700              # dien tich toi thieu cua vat the khac nen co
BLOB_REACH_Y = 180
# the lien minh "(LSB)Ten": OCR hay rot dau "(" -> nhan ca "LSB)Ten"
TAG_RX = re.compile(r"[(\[{]\s?[A-Za-z0-9]{2,5}\s?[)\]}]|\b[A-Z]{3}\)\s?\w")


class Target(NamedTuple):
    x: int
    y: int
    kind: str               # 'rebel' | 'unit' | 'object'


def find_green_chevron(img):
    """Mui ten XANH chi xuong (dau V kep, ~22x31 px) -> (x tam, y chan mui ten) | None."""
    if not isinstance(img, np.ndarray):
        return None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 50) & (hsv[..., 0] <= 80) & (hsv[..., 1] >= 120) & (hsv[..., 2] >= 170)).astype("uint8")
    m[:TOP], m[BOTTOM:] = 0, 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, _, st, c = cv2.connectedComponentsWithStats(m)
    best = None
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 16 <= w <= 36 and 22 <= h <= 46 and 1.15 <= h / w <= 1.8 and a >= 0.4 * w * h and (best is None
                                                                                              or a > best[2]):
            best = (int(c[i][0]), int(y + h), a)
    return best[:2] if best else None


# ---------- can cu nguoi choi ----------
def flags(img):
    """Co quoc gia (hinh chu nhat do ~27x18 co sao vang) canh bien ten can cu nguoi choi -> [(x, y)] tam co."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    red = (((h <= 6) | (h >= 174)) & (s >= 180) & (v >= 150)).astype(np.uint8)
    red = cv2.morphologyEx(red, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(red)
    out = []
    for i in range(1, n):
        x, y, w, ht, a = st[i]
        if not (18 <= w <= 34 and 13 <= ht <= 24 and a >= 0.7 * w * ht):
            continue
        box = hsv[y:y + ht, x:x + w]
        yellow = (box[..., 0] >= 18) & (box[..., 0] <= 35) & (box[..., 1] >= 150) & (box[..., 2] >= 180)
        if int(yellow.sum()) >= 20:
            out.append((int(x + w // 2), int(y + ht // 2)))
    return out


def dome_share(img, x, y):
    """Ti le diem mau xanh lo sang (mai khien) trong o 100x80 quanh (x, y)."""
    box = img[max(0, y - 40):y + 40, max(0, x - 50):x + 50]
    if not box.size:
        return 0.0
    hsv = cv2.cvtColor(box, cv2.COLOR_BGR2HSV)
    m = (hsv[..., 0] >= 85) & (hsv[..., 0] <= 102) & (hsv[..., 1] >= 40) & (hsv[..., 1] <= 200) & (hsv[..., 2] >= 175)
    return float(m.mean())


def has_tag(img, x, y):
    """Bien ten co the lien minh "(LSB)" ngay duoi (x, y)? (OCR)"""
    x0, y0 = max(0, x - 90), max(0, y)
    w, h = min(200, img.shape[1] - x0), min(90, img.shape[0] - y0)
    if w < 40 or h < 20:
        return False
    for bright in (None, 170):
        try:
            text = ocr.text(img, (x0, y0, w, h), scale=3, psm=11, bright=bright) or ""
        except Exception:       # noqa: BLE001 - OCR hong khong duoc lam hong thao tac (con co map_menu chan menu)
            return False
        if TAG_RX.search(text):
            return True
    return False


def city_near(img, x, y, wide=False, seen=None):
    """(x, y) la can cu nguoi choi? Hep: co quoc gia ngay tai diem cham / mai khien. wide=True (vat the khong co nhan
    "Phien quan"): them co o vung bien ten ben duoi va the lien minh "(XXX)"."""
    if not isinstance(img, np.ndarray):
        return False
    seen = flags(img) if seen is None else seen
    if any(abs(fx - x) <= 45 and abs(fy - y) <= 30 for fx, fy in seen):
        return True
    if dome_share(img, x, y) >= 0.3:
        return True
    if not wide:
        return False
    if any(abs(fx - x) <= 140 and -30 <= fy - y <= 90 for fx, fy in seen):
        return True
    return has_tag(img, x, y)


def blind_tap_ok(img, v, x, y):
    """Cham "mu" theo toa do co dinh (muc tieu giua man): tren ban do the gioi chi khi quanh do khong co dau hieu can
    cu nguoi choi (log 26/11 #1: diem co dinh cua Tinh bao trung can cu "(LSS)MF006"). Man khac: duoc."""
    if not isinstance(img, np.ndarray) or not v.find(img, "common/btn_to_city"):
        return True
    return not city_near(img, x, y, wide=True)


def rebel_near(img, v, x, y, radius, blocked=None):
    """P13m: ban do the gioi KHONG co mui ten (sau khi cham thanh nhiem vu) -> than phien quan CO NHAN "Phien quan"
    gan (x, y) nhat trong ban kinh `radius` -> Target | None. Vat that, khong phai diem co dinh; loai can cu."""
    if not isinstance(img, np.ndarray) or v.find(img, "common/btn_to_world"):
        return None
    name, up = LABELS[0]
    if not getattr(v, "has", lambda n: False)(name):
        return None
    seen = flags(img)
    found = [Target(int(lx), int(ly) - up, "rebel") for lx, ly, _ in v.find_all(img, name, th=LABEL_TH)]
    for t in sorted(found, key=lambda t: abs(t.x - x) + abs(t.y - y)):
        if (abs(t.x - x) <= radius and abs(t.y - y) <= radius and not (blocked and blocked(t.x, t.y))
                and not city_near(img, t.x, t.y, seen=seen)):
            return t
    return None


# ---------- vat the duoi mui ten ----------
def _labels(img, v, arrow):
    ax, ay = arrow
    out = []
    for name, up in LABELS:
        if not getattr(v, "has", lambda n: False)(name):
            continue
        for lx, ly, _ in v.find_all(img, name, th=LABEL_TH):
            x, y = int(lx), int(ly) - up
            if abs(x - ax) <= REACH_X and 0 < ly - ay <= REACH_Y and y > ay:
                out.append(Target(x, y, "rebel"))
    return out


def hp_bars(img):
    """Thanh mau do nam ngang cua don vi -> [(x tam, y tam, rong)]."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    red = (((h <= 6) | (h >= 174)) & (s >= 180) & (v >= 60)).astype(np.uint8)
    red = cv2.morphologyEx(red, cv2.MORPH_OPEN, np.ones((3, 15), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(red)
    out = []
    for i in range(1, n):
        x, y, w, ht, a = st[i]
        if w >= BAR_MIN_W and BAR_H[0] <= ht <= BAR_H[1] and a >= 0.75 * w * ht:
            out.append((int(x + w // 2), int(y + ht // 2), int(w)))
    return out


def _bars(img, arrow):
    ax, ay = arrow
    out = []
    for bx, by, _ in hp_bars(img):
        y = by - BAR_UP
        if abs(bx - ax) <= REACH_X and 0 < by - ay <= REACH_Y and y > ay:
            out.append(Target(bx, y, "unit"))
    return out


def objects(img, arrow):
    """Khoi KHAC NEN CO (cat / co dat) ngay duoi mui ten -> [Target 'object'] gan mui ten truoc."""
    ax, ay = arrow
    x0, y0 = max(0, ax - REACH_X), min(img.shape[0], ay + 5)
    box = img[y0:min(img.shape[0], ay + BLOB_REACH_Y), x0:ax + REACH_X]
    if box.shape[0] < 20 or box.shape[1] < 20:
        return []
    hsv = cv2.cvtColor(box, cv2.COLOR_BGR2HSV)
    # nen = mau chiem da so cua cua so (co / cat); vat the = lech han ve hue hoac do bao hoa / do sang
    base = np.median(hsv.reshape(-1, 3), axis=0)
    dh = np.abs(hsv[..., 0].astype(int) - base[0])
    ds = np.abs(hsv[..., 1].astype(int) - base[1])
    dv = np.abs(hsv[..., 2].astype(int) - base[2])
    m = ((dh > 14) | (ds > 70) | (dv > 60)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, _, st, c = cv2.connectedComponentsWithStats(m)
    found = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < BLOB_MIN or w < 25 or h < 25 or w > 1.9 * REACH_X:
            continue
        cx, cy = int(c[i][0]) + x0, int(c[i][1]) + y0
        found.append((abs(cx - ax) + abs(cy - ay), Target(cx, cy, "object")))
    return [t for _, t in sorted(found)]


def pick(img, v, arrow=None, blocked=None, reach_x=REACH_X):
    """Muc tieu duoi mui ten xanh -> Target | None (khong thay vat the an toan -> KHONG cham). Trong thanh pho (nut
    ban do) -> None. Vat the khong nhan / khong thanh mau chi duoc chon khi chac chan o ban do the gioi.
    blocked(x, y) -> True: toa do da danh sach den. reach_x: lech ngang mui ten toi da (P13m: sau "Tim kiem" phien
    quan dung gia tri hep de khong cham con cap khac ben canh)."""
    if not isinstance(img, np.ndarray) or v.find(img, "common/btn_to_world"):
        return None
    arrow = arrow or find_green_chevron(img)
    if not arrow:
        return None
    seen = flags(img)

    def near_arrow(t):
        return abs(t.x - arrow[0]) + abs(t.y - arrow[1])

    def blobs():
        return objects(img, arrow) if v.find(img, "common/btn_to_city") else []

    for group, wide in ((lambda: _labels(img, v, arrow), False), (lambda: _bars(img, arrow), True), (blobs, True)):
        for t in sorted(group(), key=near_arrow):
            if abs(t.x - arrow[0]) > reach_x or (blocked and blocked(t.x, t.y)):
                continue
            if city_near(img, t.x, t.y, wide=wide, seen=seen):
                continue
            return t
    return None
