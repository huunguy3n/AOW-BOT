"""P13i (chu du an t96u 26/11/2026): bong bong tron vang CO LE noi tren cong trinh = "cong trinh nay nang duoc ngay".

Nhan dien (ham thuan, test offline). Bong bong CO HOAT ANH: co le lac nghieng, camera phong to / thu nho, ben trong
trong mo (thay nen phia sau) - nen khong tin rieng diem khop anh mau. Ung vien phai qua CA BON lop:
  1. hinh: vung mau kem cua bieu tuong giong co le trong anh mau o mot trong cac goc nghieng (bong bong THU TAI NGUYEN
     hinh ban tay / canh cung mau cung vong nhung hinh khac);
  2. vong vang quanh bieu tuong;
  3. long dia toi mo, khong choi (loai the vang, tia dan tren nen cat);
  4. khop anh mau templates/build/wrench_bubble.png da xoay dung goc, o ti le gan co bieu tuong.
Nguong do tren ~30.000 khung 540x960 da luu 17-26/11 (docs/strategy/p13i-report.md).
"""
import cv2
import numpy as np

TPL = "build/wrench_bubble"
ANGLES = (0, -5, -10, -15, -20, -25, -30, 5)       # do xoay so voi anh mau (do that: -25..0)
SCALES = (0.8, 0.88, 0.95, 1.0, 1.06, 1.12, 1.2, 1.27, 1.34, 1.42)
ICON_LO, ICON_HI = (18, 30, 220), (36, 145, 255)    # HSV mau kem bieu tuong (do: H 21-30, S 66-132, V >= 236)
GOLD_LO, GOLD_HI = (12, 100, 90), (34, 255, 255)    # HSV vong vang
SOFT_TH = 0.82      # giong hinh co le (that >= 0.84; khop nham tot nhat 0.81)
RING_TH = 0.45      # ti le diem vang tren vong tron tot nhat
DIM_TH = 0.70       # ti le diem toi mo (V 35-180) trong long dia, ngoai bieu tuong
MATCH_TH = 0.46     # diem khop anh mau da xoay (that >= 0.51)
# vung HUD khong bao gio cham (x, y, w, h): thanh tai nguyen, cot tho/may bay trai tren, thanh duoi, bua goc phai duoi
BLOCK = ((0, 0, 540, 100), (0, 100, 75, 140), (0, 875, 540, 85), (440, 760, 100, 115))


def _icon_mask(bgr):
    return cv2.inRange(cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV), ICON_LO, ICON_HI)


def _largest(mask):
    """Manh lon nhat cua mat na -> (anh nhi phan cat sat, (w, h)) | None."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
    if n < 2:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = (int(v) for v in st[i][:4])
    return (lab[y:y + h, x:x + w] == i).astype(np.uint8), (w, h)


def _norm(shape):
    small = cv2.resize(shape.astype(np.float32), (24, 24), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(small, (3, 3), 0)


def _references(tpl):
    """-> [(anh mau da xoay, hinh chuan hoa, w, h bieu tuong)] cho tung goc."""
    h, w = tpl.shape[:2]
    out = []
    for a in ANGLES:
        m = cv2.getRotationMatrix2D(((w - 1) / 2, (h - 1) / 2), a, 1.0)
        rot = cv2.warpAffine(tpl, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        icon = _largest(_icon_mask(rot))
        if icon:
            out.append((rot, _norm(icon[0]), icon[1][0], icon[1][1]))
    return out


def _shape(comp, refs):
    """Goc giong nhat: -> (diem, ti le co, anh mau da xoay) | None. Ti le khung (cao/rong) lech xa -> bo goc do."""
    h, w = comp.shape
    cur = _norm(comp)
    best = None
    for rot, ref, rw, rh in refs:
        if abs(np.log((h / w) / (rh / rw))) > 0.28:
            continue
        s = float(cv2.matchTemplate(cur, ref, cv2.TM_CCOEFF_NORMED)[0, 0])
        if best is None or s > best[0]:
            best = (s, (w / rw + h / rh) / 2.0, rot)
    return best


def _ring(gold, cx, cy, radius):
    """Ti le diem vang tren vong tron tot nhat quanh (cx, cy), ban kinh 0.82..1.08 * radius."""
    ang = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    best = 0.0
    for r in np.arange(radius * 0.82, radius * 1.09, 1.0):
        xs = np.clip(np.round(cx + r * np.cos(ang)).astype(int), 0, gold.shape[1] - 1)
        ys = np.clip(np.round(cy + r * np.sin(ang)).astype(int), 0, gold.shape[0] - 1)
        best = max(best, float((gold[ys, xs] > 0).mean()))
    return best


def _dim(hsv, icon, cx, cy, r):
    """Ti le diem toi mo trong dia ban kinh r quanh (cx, cy), bo vien quanh bieu tuong."""
    x0, y0 = max(0, cx - r), max(0, cy - r)
    sub = hsv[y0:cy + r + 1, x0:cx + r + 1]
    yy, xx = np.mgrid[:sub.shape[0], :sub.shape[1]]
    near = cv2.dilate(icon[y0:cy + r + 1, x0:cx + r + 1], np.ones((5, 5), np.uint8)) > 0
    px = sub[((xx - (cx - x0)) ** 2 + (yy - (cy - y0)) ** 2 <= r * r) & ~near]
    return float(((px[:, 2] >= 35) & (px[:, 2] <= 180)).mean()) if len(px) else 0.0


def _match(img, tpl, cx, cy, scale):
    """Diem khop anh mau tot nhat trong cua so nho quanh (cx, cy), thu cac ti le gan `scale`."""
    best = 0.0
    for s in SCALES:
        if abs(s - scale) > 0.12:
            continue
        t = tpl if s == 1.0 else cv2.resize(tpl, None, fx=s, fy=s,
                                            interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
        th, tw = t.shape[:2]
        x0, y0 = max(0, cx - tw // 2 - 6), max(0, cy - th // 2 - 6)
        area = img[y0:y0 + th + 12, x0:x0 + tw + 12]
        if area.shape[0] < th or area.shape[1] < tw:
            continue
        best = max(best, float(cv2.minMaxLoc(cv2.matchTemplate(area, t, cv2.TM_CCOEFF_NORMED))[1]))
    return best


def _blocked(x, y, block):
    return any(bx <= x < bx + w and by <= y < by + h for bx, by, w, h in block)


def find_bubbles(img, tpl, block=BLOCK):
    """Ham thuan: -> [(x, y, diem)] tam cac bong bong CO LE tren anh thanh pho (diem = khop anh mau), diem giam dan.
    tpl: anh mau bong bong cat sat vong tron (None -> [])."""
    if tpl is None:
        return []
    refs = _references(tpl)
    if not refs:
        return []
    radius = tpl.shape[1] / 2.0
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, ICON_LO, ICON_HI)
    gold = cv2.inRange(hsv, GOLD_LO, GOLD_HI)
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
    out = []
    for i in range(1, n):
        x, y, w, h, area = (int(v) for v in st[i])
        if not (10 <= w <= 40 and 10 <= h <= 40 and 35 <= area <= 330):
            continue
        cx, cy = x + w // 2, y + h // 2
        if _blocked(cx, cy, block):
            continue
        best = _shape((lab[y:y + h, x:x + w] == i).astype(np.uint8), refs)
        if best is None or best[0] < SOFT_TH:
            continue
        _, scale, rot = best
        if not SCALES[0] * 0.85 <= scale <= SCALES[-1] * 1.03:
            continue
        if _ring(gold, cx, cy, radius * scale) < RING_TH:
            continue
        if _dim(hsv, mask, cx, cy, int(round(radius * 0.72 * scale))) < DIM_TH:
            continue
        score = _match(img, rot, cx, cy, scale)
        if score >= MATCH_TH:
            out.append((cx, cy, score))
    return sorted(out, key=lambda p: -p[2])


def above_hq(bubble, hq):
    """Ham thuan: bong bong (x, y, ..) noi ngay PHIA TREN nha chinh co huy hieu / tam tai hq (x, y, ..)?"""
    if not hq:
        return False
    return abs(bubble[0] - hq[0]) <= 100 and -10 <= hq[1] - bubble[1] <= 180


def ordered(bubbles, hq):
    """Ham thuan: bong bong tren nha chinh len dau, con lai theo diem. -> [(x, y, diem, la_nha_chinh)]."""
    tagged = [(b[0], b[1], b[2], above_hq(b, hq)) for b in bubbles]
    return sorted(tagged, key=lambda b: (not b[3], -b[2]))
