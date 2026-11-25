"""Tim cham do thong bao (badge) theo mau: hinh tron do tuoi ~10-20px, co the co so trang ben trong."""
import cv2, numpy as np


def red_dots(img, roi=None, min_r=4, max_r=14, min_v=190):
    """Tra ve [(x, y)] tam cac cham do trong vung roi (x, y, w, h).
    min_v: do sang toi thieu; man bi phu toi (lop huong dan tan thu) cham do chi V ~75 -> goi voi min_v=60."""
    ox, oy = 0, 0
    if roi:
        x, y, w, h = roi
        img, ox, oy = img[y:y + h, x:x + w], x, y
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = (((hsv[..., 0] <= 6) | (hsv[..., 0] >= 172)) & (hsv[..., 1] >= 170) & (hsv[..., 2] >= min_v)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))  # lap lo so trang ben trong
    n, _, stats, cent = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        r = max(w, h) / 2
        if min_r <= r <= max_r and 0.6 <= w / max(h, 1) <= 1.6 and area >= 0.5 * w * h:
            out.append((int(cent[i][0]) + ox, int(cent[i][1]) + oy))
    return out


def glow_tiles(img, roi=(0, 440, 250, 520)):
    """O qua co VIEN XANH NGOC PHAT SANG = nhan duoc bang cach cham vao o (khong co nut "Nhan").
    Gap o cot "Mien phi" cua tab "Qua dang nhap" / "Chuc phuc tan thu" (TT phuc loi). Do 2026-11-18 tren #5:
    vien H 92-94, S ~136, V ~203; o ~71x66-71, mat do vien 0.17-0.30. -> [(x, y)] tren xuong."""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 85) & (hsv[..., 0] <= 100) & (hsv[..., 1] >= 110) & (hsv[..., 2] >= 170)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if 55 <= w <= 100 and 55 <= h <= 100 and a / float(w * h) < 0.6:   # vien rong ruot, khong phai khoi dac
            out.append((int(x0 + x + w // 2), int(y0 + y + h // 2)))
    return sorted(out, key=lambda p: p[1])


def tile_locked(img, x, y):
    """P13-7 (anh duong_tuong_sai.png): o qua co O KHOA trang o goc tren-trai o (than khoa ~14x14 px, trang S<45 V>215)
    la o CHUA mo (moc > cap hien tai) - khong nhan duoc, khong bam. (x, y) = tam o. Ham thuan."""
    if getattr(img, "ndim", 0) != 3:
        return False
    x0, y0 = max(0, x - 46), max(0, y - 40)
    sub = img[y0:y + 6, x0:x - 14]
    if sub.size == 0:
        return False
    hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 1] < 45) & (hsv[..., 2] > 215)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    return any(10 <= st[k][2] <= 22 and 9 <= st[k][3] <= 24 and st[k][4] >= 70 for k in range(1, n))


def nhan_tiles(img, roi=(0, 230, 540, 700)):
    """O qua nhan duoc kieu "Diem danh 30 ngay": chu "Nhan" XANH LA SANG de len o + VIEN VANG NHAT phat sang.
    Do tren anh nguoi dung gui 2026-11-18 (ti le ~0.97): chu H~60 S255 V235, khoi ~44x13; vien H 23-26 S 54-58 V255.
    -> [(x, y)] tam chu (cham vao la nhan)."""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    green = ((H >= 50) & (H <= 75) & (S >= 180) & (V >= 180)).astype(np.uint8)
    frame = ((H >= 18) & (H <= 32) & (S >= 30) & (S <= 100) & (V >= 235)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(green, np.ones((3, 7), np.uint8)))
    out = []
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if 28 <= w <= 70 and 8 <= h <= 22 and a >= 150:
            cx, cy = x + w // 2, y + h // 2
            win = frame[max(0, cy - 70):cy + 70, max(0, cx - 70):cx + 70]
            if int(win.sum()) >= 60:          # co vien vang nhat quanh -> la o qua, khong phai chu xanh khac
                out.append((int(x0 + cx), int(y0 + cy)))
    return sorted(out, key=lambda p: (p[1], p[0]))


def city_bubbles(img, roi=(0, 100, 470, 680)):
    """Bong bong QUA tren cong trinh thanh pho: vong tron vang trong suot + hinh hop qua mau KEM SANG o giua.
    Nen nhin xuyen qua thay doi -> khong dung anh mau. Do #5 2026-11-18: hop qua H 25-30 S 69-84 V 255 (~20x18 px),
    vien vang H 20-24 S 110-180. -> [(x, y)]."""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    cream = ((H >= 22) & (H <= 34) & (S >= 50) & (S <= 105) & (V >= 235)).astype(np.uint8)
    ring = ((H >= 17) & (H <= 26) & (S >= 105) & (V >= 80)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(cream, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)))
    out = []
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if 10 <= w <= 34 and 10 <= h <= 34 and a >= 60:
            cx, cy = x + w // 2, y + h // 2
            r = ring[max(0, cy - 22):cy + 22, max(0, cx - 22):cx + 22]
            # hop qua = khoi kem DAC (do: fill 0.47-0.53, nua duoi 0.58-0.65); bong bong khac cung khung vang
            # (tai lieu, drone) mong hon: fill <= 0.26, nua duoi <= 0.24
            blob = cream[max(0, cy - 20):cy + 20, max(0, cx - 20):cx + 20]
            ys, xs = np.nonzero(blob)
            bw, bh = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
            low = blob[ys.min() + bh // 2:ys.max() + 1, xs.min():xs.max() + 1]
            if blob.sum() / float(bw * bh) < 0.38 or low.mean() < 0.4:
                continue
            # hop qua gan VUONG (do 21-22 x 20-21); tang toc (mui ten doi) det 21x13 - KHONG bam; xe "Thu thap" rong 33
            if not (17 <= bw <= 26 and 17 <= bh <= 26):
                continue
            if int(r.sum()) >= 80:
                p = (int(x0 + cx), int(y0 + cy))
                if all(abs(p[0] - q[0]) > 25 or abs(p[1] - q[1]) > 25 for q in out):
                    out.append(p)
    return out


_FREE_TXT = None


def free_bubbles(img, roi=(0, 90, 540, 760)):
    """Bong bong "Free" XANH LA tron (~35 px) noi tren cong trinh dang xay = hoan thanh mien phi (chu du an 2026-11-20).
    Anh mau ca bong bong khop kem khi nen doi (vang/xanh: 0.47) -> loc MAU (dia xanh dam H 45-64 S ~113 V ~108)
    roi xac nhan bang chu "Free" ben trong (anh mau chi phan chu, >= 0.3; nut tron xanh khac <= 0.26) va so diem
    chu trang 80..180. -> [(x, y)]"""
    global _FREE_TXT
    if _FREE_TXT is None:
        _FREE_TXT = cv2.imread("templates/common/btn_free_text.png")
        if _FREE_TXT is None:
            return []
    x0, y0, w0, h0 = roi
    sub = img[y0:y0 + h0, x0:x0 + w0]
    hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    g = ((H >= 40) & (H <= 80) & (S >= 120) & (V >= 80)).astype(np.uint8)
    white = (S < 120) & (V > 220)
    n, _, st, _ = cv2.connectedComponentsWithStats(g)
    out = []
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if not (26 <= w <= 48 and 26 <= h <= 48 and 0.75 <= w / h <= 1.33 and a >= 0.25 * w * h):
            continue
        cx, cy = x + w // 2, y + h // 2
        nw = int(white[max(0, cy - 18):cy + 18, max(0, cx - 18):cx + 18].sum())
        win = sub[max(0, cy - 22):cy + 22, max(0, cx - 25):cx + 25]
        if not (80 <= nw <= 180) or win.shape[0] < _FREE_TXT.shape[0] or win.shape[1] < _FREE_TXT.shape[1]:
            continue
        if cv2.minMaxLoc(cv2.matchTemplate(win, _FREE_TXT, cv2.TM_CCOEFF_NORMED))[1] >= 0.3:
            out.append((int(x0 + cx), int(y0 + cy)))
    return out
