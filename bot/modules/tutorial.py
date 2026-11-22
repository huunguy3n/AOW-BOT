"""Qua phan tan thu (dung theo ban ghi mau logs/rec/20261117_232742_khoi_tao_tan_thu, docs/bot/01-tan-thu-phan-tich.md).

Moi vong: chup man hinh -> decide() chon 1 hanh dong theo thu tu uu tien -> thuc hien.
decide() la ham thuan (chi doc anh) de kiem tra offline bang ban ghi: python tools/replay_tutorial.py
"""
import time, logging
import cv2
import numpy as np

from bot import quest_rules

log = logging.getLogger("aow")

V_DY = 51          # cham tam vong tron duoi chu V (do tren 14 khung: 37..61)
HAND_DY = 100      # cham dong do nat duoi ban tay xanh (do: 90..113)
CENTER = (270, 600)
QUEST_TAPS = [(30, 818), (150, 818)]   # icon nhiem vu goc trai duoi (ban ghi #46) / dong chu nhiem vu
PAD = 40

FIGHT_XY = (270, 921)    # nut Chien dau o man doi hinh (chu phu "The luc can bang" lam lech anh mau)

# Nguong do tren ban ghi: battle_top trong tran >=0.68, ngoai tran <=0.52; battle_flag ngoai tran <=0.34
TH = {
    "tutorial/marker_v": 0.68, "tutorial/hand_green": 0.85, "tutorial/hand_green2": 0.85, "tutorial/battle_top2": 0.8, "tutorial/dialog_next": 0.9,
    "tutorial/btn_start_game": 0.85, "tutorial/btn_attack_red": 0.9,
    "tutorial/battle_top": 0.62, "tutorial/battle_flag": 0.6,
    "tutorial/btn_auto_formation": 0.8,
    "tutorial/icon_unlock": 0.85,     # bong bong o khoa: khop nham tren ban ghi toi da 0.74
    "tutorial/icon_explore": 0.75,    # nhap nhay: diem khop 0.64..1.0; kinh lup co dinh o mep phai da bi ROI loai
    "tutorial/supply_box": 0.9,
    "tutorial/icon_repair": 0.85,     # bong bong co le "Sua chua" tren cong trinh (khong khop nham tren ban ghi)
}
ROI = {"tutorial/battle_top": (200, 20, 140, 110), "tutorial/battle_top2": (200, 20, 140, 110), "tutorial/battle_flag": (480, 150, 60, 120),
       "tutorial/btn_auto_formation": (440, 860, 100, 100),
       "tutorial/icon_explore": (0, 100, 440, 760),     # bo nut kinh lup co dinh cua thanh pho o mep phai
       "common/btn_close@top": (420, 0, 120, 90)}


def _f(v, img, name, roi=None):
    return v.find(img, name, th=TH.get(name), roi=roi or ROI.get(name))


def _formation_btn(v, img):
    """Nut xep doi hinh tu dong: 'Doi hinh tu dong' (tran tan thu) hoac 'Doi hinh de xuat' (xuat quan tu ban do,
    chu du an 2026-11-22 gui anh: man Phien quan)."""
    return _f(v, img, "tutorial/btn_auto_formation") or v.find(img, "tutorial/btn_suggest_formation", th=0.85)


def find_green_chevron(img):
    """Mui ten XANH chi xuong (dau V kep, ~22x31 px) tren ban do the gioi: huong dan game chi vao quan Phien quan o
    ngay duoi no (anh chu du an 2026-11-22: mui ten y~96, quan y~200). -> (x, y_cham) | None. Ham thuan."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 50) & (hsv[..., 0] <= 80) & (hsv[..., 1] >= 120) & (hsv[..., 2] >= 170)).astype("uint8")
    m[:110], m[800:] = 0, 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, _, st, c = cv2.connectedComponentsWithStats(m)
    best = None
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 16 <= w <= 36 and 22 <= h <= 46 and 1.0 <= h / w <= 1.8 and a >= 0.4 * w * h and (best is None or a > best[2]):
            best = (int(c[i][0]), int(y + h + 95), a)
    return best[:2] if best else None


BEAM_DY = 35       # cham duoi chan cot sang cam (linh dung tren o do) - do khung 021/025: chan cot ~445, linh ~465..480


def _wide_band_center(mask, frac=0.7, bin_=6):
    """Tam DAI RONG NHAT cua vung do: cac hang co be ngang >= frac x be ngang lon nhat. O hinh thoi (vien) -> dai o
    2 goc trai/phai = tam o; o chu nhat dac -> ca vung; vet cheo / dau lau hep bi loai. -> (x, y, span) hoac None."""
    ys, xs = np.nonzero(mask)
    if len(xs) < 20:
        return None
    rows = {}
    for y, x in zip(ys // bin_, xs):
        lo, hi = rows.get(y, (x, x))
        rows[y] = (min(lo, x), max(hi, x))
    mx = max(hi - lo for lo, hi in rows.values())
    band = [(y, lo, hi) for y, (lo, hi) in rows.items() if hi - lo >= frac * mx]
    ty = int(np.mean([y for y, _, _ in band]) * bin_ + bin_ // 2)
    tx = int(np.mean([(lo + hi) / 2 for _, lo, hi in band]))
    return tx, ty, int(mx)


def _beam_tile(tile, x0, y0, cx, tol=45):
    """O do duoi chan cot sang: tam vung do RONG nhat (>= 100 px) thang hang voi cot (|tx - cx| <= tol). -> (x, y)"""
    nn, lab, st2, _ = cv2.connectedComponentsWithStats(cv2.dilate(tile.astype(np.uint8), np.ones((31, 31), np.uint8)))
    wide = sorted((j for j in range(1, nn) if st2[j][2] >= 100), key=lambda j: -st2[j][4])
    for sel in [(lab == j) & tile for j in wide] + [tile]:
        c_ = _wide_band_center(sel)
        if c_ is None:
            continue
        tx, ty, span = c_[0] + x0, c_[1] + y0, c_[2]
        if span < 100:
            ys, xs = np.nonzero(sel)
            il, ir = int(np.argmin(xs)), int(np.argmax(xs))
            tx, ty = int((xs[il] + xs[ir]) / 2) + x0, int((ys[il] + ys[ir]) / 2) + y0
            span = int(xs[ir] - xs[il])
        if abs(tx - cx) <= tol and span >= 100:
            return tx, ty
    return None


def find_beam(img):
    """Muc tieu 'linh tren o do + kiem cheo hong': COT SANG CAM thang dung chieu xuong muc tieu.
    Kiem cheo nhap nhay (tach/chum) va giong mau toc/da nhan vat -> khong dung duoc; cot sang on dinh khi ban do cuon.
    Do 2026-11-18: H 10-15, S 130-212, V 121-253, cao 80-95 px, rong < 24 px. -> (x, y_chan_cot) hoac None."""
    hsv = cv2.cvtColor(img[100:700], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = ((H >= 5) & (H <= 20) & (S >= 120) & (V >= 150)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 3), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    full = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    red = (((full[..., 0] <= 8) | (full[..., 0] >= 170)) & (full[..., 1] >= 150) & (full[..., 2] >= 200))
    best = None
    for k in range(1, n):
        x, y, w, h, a = st[k]
        # cot co the bi che / ngan (khi dot: 43 px, xe tang + dau lau: 30 px) -> chap nhan >= 25 px, bat buoc co o do ben duoi
        if h >= 25 and w <= 24 and h / w >= 3 and a / float(w * h) > 0.35:
            cx, bot = int(x + w // 2), int(y + h + 100)
            if cx > 430:          # cot icon giao dien ben phai (ban ghi #83 bat nham o x=477)
                continue
            # xac nhan: vien O DO sang ngay duoi chan cot (bo cac vat cam manh khac)
            x0, y0 = max(0, cx - 110), bot
            # cua so 160 px; khong co o thang hang -> 300 px nhung doi thang hang chat hon (cot bi xe/dau lau che
            # giua chung, #2 2026-11-21: chan cot y 188, o do 343-447). 220 px tung bat nham thung hang (2026-11-20)
            for depth, tol in ((160, 45), (300, 25)):
                tile = red[y0:min(960, bot + depth), x0:cx + 110]
                hit = _beam_tile(tile, x0, y0, cx, tol) if tile.size and tile.sum() >= 60 else None
                if hit:
                    break
            if hit and (not best or h > best[2]):
                best = (hit[0], hit[1], int(h))
    return best[:2] if best else None


MEDKIT_COUNT_ROI = (415, 778, 75, 28)   # o so luong tui cuu thuong (giua icon tui nho va nut "+")
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def read_count(img, roi):
    """Doc so nguyen trong o (x, y, w, h) bang Tesseract. -> int hoac None (khong doc duoc)."""
    try:
        import os, re
        import pytesseract
        if os.path.exists(TESSERACT):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT
        x, y, w, h = roi
        g = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        t = pytesseract.image_to_string(b, config="--psm 7 -c tessedit_char_whitelist=0123456789")
        m = re.search(r"\d+", t or "")
        return int(m.group()) if m else None
    except Exception as e:
        log.debug("OCR loi: %s", e)
        return None


def find_ring(img):
    """Vong tron vang phat sang RONG RUOT (cham vao vet thuong o man chua tri sau khi dung tui cuu thuong).
    Do 2026-11-18: rong 54..78 px (co gian theo nhip), do dac ~0.44. -> (cx, cy) hoac None."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 15) & (hsv[..., 0] <= 40) & (hsv[..., 1] >= 50) & (hsv[..., 2] >= 170)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if 45 <= w <= 180 and 45 <= h <= 180 and 0.75 <= w / h <= 1.33 and 0.2 <= a / float(w * h) <= 0.6:
            inner = m[y + h // 3:y + 2 * h // 3, x + w // 3:x + 2 * w // 3]
            if inner.size and inner.mean() < 0.35:          # giua rong -> la vong, khong phai khoi vang dac
                return int(x + w // 2), int(y + h // 2)
    return None


def _green_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return ((hsv[..., 0] >= 40) & (hsv[..., 0] <= 85) & (hsv[..., 1] >= 120) & (hsv[..., 2] >= 130)).astype(np.uint8)


def build_targets(img):
    """Che do xay (do 2026-11-18, man 'Mo quang'): the cong trinh = vien xanh trong dai duoi (y 820-930, ~138x67);
    o xay = khoi xanh lon tren ban do (~256x128, dien tich ~16000). -> ((the_x, the_y) | None, (o_x, o_y) | None)"""
    g = _green_mask(img)
    n, _, st, cen = cv2.connectedComponentsWithStats(g)
    card = zone = None
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if y >= 800 and 80 <= w <= 220 and 40 <= h <= 110 and a >= 300:
            card = (int(x + w // 2), int(y + h // 2))
        elif y + h < 800 and a >= 4000 and (not zone or a > zone[2]):
            zone = (int(cen[k][0]), int(cen[k][1]), int(a))
    return card, (zone[:2] if zone else None)


def free_slots(img, w=256, h=128, th=0.85):
    """Tim cho trong 2x2 o luoi (hinh thoi ~256x128) phu kin CO (khong duong / cong trinh / tai nguyen).
    Dung khi xay ma game KHONG hien o xanh goi y (vd 'Kho'). Diem cao truoc. Do 2026-11-18: co H 32-34, S 150-160."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    grass = ((H >= 25) & (H <= 45) & (S >= 90) & (V >= 70) & (V <= 210)).astype(np.uint8)
    grass = cv2.morphologyEx(grass, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    grass[:120] = 0
    grass[790:] = 0
    f = 4
    g = cv2.resize(grass.astype(np.float32), None, fx=1 / f, fy=1 / f, interpolation=cv2.INTER_AREA)
    kw, kh = w // f, h // f
    k = np.zeros((kh, kw), np.float32)
    cv2.fillPoly(k, [np.array([[0, kh // 2], [kw // 2, 0], [kw - 1, kh // 2], [kw // 2, kh - 1]])], 1)
    k /= k.sum()
    sc = cv2.filter2D(g, -1, k, anchor=(kw // 2, kh // 2), borderType=cv2.BORDER_CONSTANT)
    ys, xs = np.where(sc >= th)
    out = []
    for s_, x, y in sorted(zip(sc[ys, xs], xs * f, ys * f), reverse=True):
        if all(abs(x - a) > 90 or abs(y - b) > 45 for a, b in out):
            out.append((int(x), int(y)))
    return out


_HAND_ROT = {}


def find_hand_rot(img, th=0.8, angles=(-50, -35, -20, 20, 35, 50)):
    """Ban tay xanh NGHIENG (chi xeo vao thung/cong trinh, #5 2026-11-20: mau dung thang khong khop -> bot bam
    nham bong bong o khoa). Xoay mau hand_green2 + mat na (bo goc den) -> (x, y, goc) hoac None.
    goc > 0 = xoay nguoc chieu kim dong ho -> ngon tay chi xuong-phai."""
    if not _HAND_ROT:
        t = cv2.imread("templates/tutorial/hand_green2.png")
        if t is None:
            return None
        h, w = t.shape[:2]
        n = int((h * h + w * w) ** 0.5) + 2
        big = cv2.copyMakeBorder(t, (n - h) // 2, n - h - (n - h) // 2, (n - w) // 2, n - w - (n - w) // 2,
                                 cv2.BORDER_CONSTANT)
        msk = cv2.copyMakeBorder(np.full((h, w), 255, np.uint8), (n - h) // 2, n - h - (n - h) // 2,
                                 (n - w) // 2, n - w - (n - w) // 2, cv2.BORDER_CONSTANT)
        for a in angles:
            M = cv2.getRotationMatrix2D((n / 2, n / 2), a, 1.0)
            rt = cv2.warpAffine(big, M, (n, n))
            rm = cv2.warpAffine(msk, M, (n, n), flags=cv2.INTER_NEAREST)
            _HAND_ROT[a] = (rt, cv2.merge([rm, rm, rm]))
    # loc truoc theo mau (so khop co mat na ~1 s/khung neu quet ca man): mang TRANG lon co than ban tay
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    wm = ((hsv[..., 1] < 60) & (hsv[..., 2] > 215)).astype(np.uint8)
    n_, _, st, _ = cv2.connectedComponentsWithStats(wm)
    n = next(iter(_HAND_ROT.values()))[0].shape[0]
    best = None
    for k in range(1, n_):
        x, y, w, h, area = st[k]
        if not (250 <= area <= 1600 and 15 <= w <= 60 and 15 <= h <= 60):
            continue
        cx, cy = x + w // 2, y + h // 2
        x0, y0 = max(0, cx - n), max(0, cy - n)
        win = img[y0:cy + n, x0:cx + n]
        if win.shape[0] < n or win.shape[1] < n:
            continue
        for a, (rt, rm) in _HAND_ROT.items():
            r = cv2.matchTemplate(win, rt, cv2.TM_CCOEFF_NORMED, mask=rm)
            r[~np.isfinite(r)] = 0
            _, m, _, loc = cv2.minMaxLoc(r)
            if m >= th and (best is None or m > best[0]):
                best = (m, x0 + loc[0] + n // 2, y0 + loc[1] + n // 2, a)
    return best[1:] if best else None


def find_hand_beam(img, min_green=40):
    """Ban tay xanh (moi kieu xoay/co) = mang TRANG co ban tay + COT SANG XANH LA chieu thang xuong muc tieu.
    Mau anh khop kem khi ban tay nghieng/phong to (#4 2026-11-20: tank, ~0.6) -> nhan theo mau. -> (x, y) tam ban tay."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    wm = ((S < 60) & (V > 215)).astype(np.uint8)
    green = (H >= 30) & (H <= 85) & (S >= 150) & (V >= 170)   # cot sang xanh nga vang H 33..45 (do #4)
    n_, _, st, _ = cv2.connectedComponentsWithStats(wm)
    best = None
    for k in range(1, n_):
        x, y, w, h, area = st[k]
        # ban tay to (#2 2026-11-21 thung hang: 96x71, 2656 px) -> nhan toi 110 px / 3600 px
        if not (250 <= area <= 3600 and 15 <= w <= 110 and 15 <= h <= 110) or y < 90 or y + h > 840:
            continue
        if area < 0.3 * w * h:          # ban tay = khoi trang dac (khong phai chu/vien mong)
            continue
        cx = x + w // 2
        if cx < 60 or cx + 60 > img.shape[1]:
            continue
        # cot sang: vet xanh HEP, LIEN MACH theo chieu doc DUOI ban tay, hoac TREN ban tay khi phia duoi bi bong
        # bong icon che (#4 thung tiep te 2026-11-20); hai ben cot khong xanh
        for y0, y1 in ((y + h, min(img.shape[0], y + h + 80)), (max(0, y - 80), y)):
            if y1 - y0 < 20:
                continue
            col = green[y0:y1, cx - 20:cx + 20]   # ban tay ve lech cot ~15 px (#4 thung tiep te)
            rows = int((col.sum(axis=1) >= 2).sum())
            side = green[y0:y1, cx - 60:cx - 35].mean() + green[y0:y1, cx + 35:cx + 60].mean()
            g = int(col.sum())
            if g >= min_green and rows >= 0.45 * (y1 - y0) and side < 0.4 and (best is None or g > best[0]):
                best = (g, cx, y + h // 2, y + h)
        # cot sang bi bong bong icon che (thung tiep te, #4 2026-11-20): O XANH thang hang ngay duoi cung la dau hieu
        if best is None and area >= 1000 and h >= 40:   # ban tay cao, dac; manh trang det (chu, nut) bo
            t_ = find_tile_below(img, cx, y + h, depth=200, green_only=True)
            if t_ and abs(t_[0] - cx) <= 30:
                best = (1, cx, y + h // 2, y + h)
    return best[1:3] if best else None


def find_tile_below(img, cx, y_from, depth=260, half=130, green_only=False):
    """O XANH LA / DO (vien hinh thoi) duoi ban tay = vung muc tieu: chu du an 2026-11-20 "uu tien nhan biet vung o
    duoi mau xanh la, do". Tam = giua goc trai/phai cua manh vien rong (>= 100 px) gan nhat. -> (x, y) hoac None."""
    y0, y1 = max(0, y_from), min(img.shape[0] - 120, y_from + depth)
    x0, x1 = max(0, cx - half), min(img.shape[1], cx + half)
    if y1 - y0 < 30:
        return None
    hsv = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    masks = (((H >= 35) & (H <= 85) & (S >= 150) & (V >= 200)),                         # vien xanh la
             (((H <= 8) | (H >= 170)) & (S >= 150) & (V >= 200)))                        # vien do
    masks = masks[:1] if green_only else masks
    best = None
    for m in masks:
        m = m.copy()
        m[:, max(0, cx - x0 - 12):cx - x0 + 12] = False   # bo cot sang xanh (noi vien o len tren -> lech tam)
        ys, xs = np.nonzero(m)
        if len(xs) >= 30:
            c_ = _wide_band_center(m)          # vung rong nhat (o dac / dai 2 goc o vien)
            if c_ and c_[2] >= 100 and abs(c_[0] + x0 - cx) <= 60:
                best = (c_[0] + x0, c_[1] + y0)
            else:
                # vien o dut thanh nhieu manh -> lay 2 GOC trai/phai (diem xa nhat), phai ngang hang va cach >= 100 px
                il, ir = int(np.argmin(xs)), int(np.argmax(xs))
                tx, ty = int((xs[il] + xs[ir]) / 2) + x0, int((ys[il] + ys[ir]) / 2) + y0
                if xs[ir] - xs[il] >= 100 and abs(int(ys[il]) - int(ys[ir])) <= 40 and abs(tx - cx) <= 60:
                    best = (tx, ty)
        if best:
            return best      # uu tien o XANH; vien do chi khi khong co o xanh (thung hang cam do bi bat nham)
    return best


def find_footprint_red(img):
    """Dau chan cong trinh mau DO (dat sai cho) - hinh thoi lon ~(120..300)x(60..160) tren ban do. -> tam hoac None."""
    hsv = cv2.cvtColor(img[:800], cv2.COLOR_BGR2HSV)
    m = (((hsv[..., 0] <= 8) | (hsv[..., 0] >= 170)) & (hsv[..., 1] >= 120) & (hsv[..., 2] >= 130)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    best = None
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if 120 <= w <= 320 and 60 <= h <= 180 and a >= 2500 and (not best or a > best[2]):
            best = (int(x + w // 2), int(y + h // 2), int(a))
    return best[:2] if best else None


def zone_all_green(img, zone, r=70):
    """O xay hien TOAN XANH (khong lan do) quanh tam o -> xay duoc."""
    x, y = zone
    hsv = cv2.cvtColor(img[max(0, y - r // 2):y + r // 2, max(0, x - r):x + r], cv2.COLOR_BGR2HSV)
    red = (((hsv[..., 0] <= 8) | (hsv[..., 0] >= 170)) & (hsv[..., 1] >= 120) & (hsv[..., 2] >= 130)).mean()
    green = ((hsv[..., 0] >= 40) & (hsv[..., 0] <= 85) & (hsv[..., 1] >= 120) & (hsv[..., 2] >= 130)).mean()
    return red < 0.03 and green > 0.08     # cong trinh che giua dau chan -> phan xanh lo ra chi ~0.16


def _colored(img, x, y, min_sat=80):
    """Nut bam duoc co mau (sat 165-215); nut chua du dieu kien mau xam (sat ~0) - do 2026-11-18."""
    hsv = cv2.cvtColor(img[max(0, y - 10):y + 10, max(0, x - 35):x + 35], cv2.COLOR_BGR2HSV)
    return float(hsv[..., 1].mean()) >= min_sat


def is_battle(v, img):
    """Tran chay duong tan thu: bieu tuong do tren dinh (tran thuong) hoac co tren thanh tien do ben phai (boss/robot).
    -> True | False (khong thay dau hieu tran) | None (CHAC CHAN khong phai tran: man bat dau / ket qua -> thoat ngay).
    Nut 'Bat dau tro choi' nhap nhay -> nguong thap 0.7 (diem khop dao dong 0.8..0.98)."""
    if (v.find(img, "tutorial/btn_start_game", th=0.7) or v.find(img, "campaign/res_win")
            or v.find(img, "campaign/res_lose")):
        return None
    # battle_top2: bieu tuong phe dich khac (tran cua #5 2026-11-20 20:31, mau cu chi khop 0.55 -> cham giua man)
    return bool(_f(v, img, "tutorial/battle_top") or _f(v, img, "tutorial/battle_top2")
                or _f(v, img, "tutorial/battle_flag"))


def decide(v, img, idle=0, state=None):
    """-> (action, x, y, reason). action: tap | steer | wait
    state: dict giu giua cac vong (vd da bam tu xep doi hinh chua)."""
    state = {} if state is None else state
    # 0. hop thoai "Roi tro choi?" (do phim Back) -> LUON bam Huy, khong bao gio Xac nhan
    p = v.find(img, "common/btn_cancel_exit", th=0.9)
    if p:
        return ("tap", p[0], p[1], "huy thoat game")
    # 0a. CHE DO follow (sau tan thu): KHONG lam gi o man Chieu mo (ke ca khi chu V chi vao "Chieu mo 10 lan")
    #     -> quay ra. Chieu mo chi do buoc 'notify' quyet dinh theo tuy chon (do #5 2026-11-18: V dan vao Chieu mo
    #     cao cap, bot bam "10 lan" -> tieu 10 phieu).
    if state.get("follow") and (v.find(img, "recruit/tab_premium", th=0.9) or v.find(img, "recruit/title", th=0.9)):
        # NGOAI LE (chu du an 2026-11-20, anh khoanh "Chieu mo 10 lan"): chu V chi vao nut 10 lan VA nut co cham do
        # (= du >= 10 PHIEU, cung quy tac buoc notify) -> bam 1 lan / luot. Khong cham do = phai tra kim cuong -> quay ra.
        pv = v.find(img, "tutorial/marker_v", th=TH["tutorial/marker_v"], roi=(290, 560, 220, 170))
        if pv and not state.get("recruit_taps"):
            from bot.badges import red_dots
            tx, ty = pv[0], pv[1] + V_DY
            if red_dots(img, (tx + 40, ty - 45, 70, 50), min_v=60):
                state["recruit_taps"] = 1
                return ("tap", tx, ty, "V chi Chieu mo 10 lan co cham do (dung phieu)")
        return ("back", 0, 0, "man chieu mo -> khong lam, quay ra")
    # 0b. can cu bi danh khi offline: "Do ben Xuong kien truc giam xuong 0" -> nut duy nhat "Xay dung lai" (mien phi)
    p = v.find(img, "common/btn_rebuild", th=0.9)
    if p:
        return ("tap", p[0], p[1], "xay dung lai can cu (bi danh)")
    # 1. man ket qua tran
    if v.find(img, "campaign/res_lose"):
        # man thua co chu V chi "Hoan thanh nhiem vu de nhan thuong" -> nut Dong/Bat dau lai bi khoa, phai theo V
        pv = v.find(img, "tutorial/marker_v", th=TH["tutorial/marker_v"])
        if pv:
            return ("tap", pv[0], min(950, pv[1] + V_DY), "thua -> theo mui ten V")
        p = v.find(img, "campaign/btn_retry", th=0.75) or v.find(img, "campaign/btn_done_lose", th=0.75)
        return ("tap", p[0] if p else 270, p[1] if p else 748, "thua -> bat dau lai")
    if v.find(img, "campaign/res_win"):
        p = v.find(img, "campaign/btn_done")
        if p:
            return ("tap", p[0], p[1], "thang -> dong")
    # 2. bat dau / dang trong tran
    p = v.find(img, "tutorial/btn_start_game", th=0.7)
    if p:
        return ("tap", p[0], p[1], "bat dau tro choi")
    if is_battle(v, img):
        return ("steer", 0, 0, "tran chay duong")
    # 2b. popup goi TRA PHI (vd "Gift bag of first purchase" d7500) -> CHI bam X tim ben phai, khong bao gio bam nut gia
    p = v.find(img, "common/btn_x_offer", th=0.85)
    if p:
        return ("tap", p[0], p[1], "dong popup goi tra phi (X)")
    # 3. popup "Chuc mung nhan duoc" -> cham lop phu ben duoi khung qua
    #    Tooltip vat pham co the che tieu de -> nguong thap 0.65. Cham ~310 px duoi tieu de = vung trong duoi khung
    #    (ban ghi: nguoi choi cham 311..583 px duoi tieu de; cham co dinh y=595 tung trung vat pham khi popup o cao)
    p = v.find(img, "common/msg_reward", th=0.65) or v.find(img, "tutorial/msg_reward_left", th=0.65)
    if p:
        return ("tap", CENTER[0], min(900, p[1] + 310), "dong popup thuong")
    # 3b. man chua tri Tong thu ky: bam tui cuu thuong CHI KHI so luong > 0 (doc OCR). Khong doc duoc -> khong bam.
    #     KHONG BAO GIO bam nut "+" ben canh (mua them) tru khi chu V cua game chi vao (da xu ly o buoc V).
    state["heal"] = max(0, state.get("heal", 0) - 1)
    p = v.find(img, "tutorial/btn_medkit", th=0.9, roi=(380, 800, 160, 160))
    if p:
        state["heal"] = 15          # cho phep tim vong vang trong 15 buoc tiep theo
        n = read_count(img, MEDKIT_COUNT_ROI)
        if n is not None and n > 0:
            return ("tap", p[0], p[1], f"tui cuu thuong (con {n})")
    # 3c. vong tron vang tren nguoi nhan vat (sau khi dung tui cuu thuong) -> cham tam. Chi ngoai thanh pho
    #     (o thanh pho, vong vang = vong cua chu V da xu ly rieng)
    if state.get("heal", 0) > 0 and not v.find(img, "common/btn_to_world"):   # chi ngay sau man chua tri
        p = find_ring(img)
        if p:
            return ("tap", p[0], p[1], "vong tron vang -> cham tam")
    # 4. hoi thoai nhan vat (khung duoi co dau tam giac)
    if _f(v, img, "tutorial/dialog_next"):
        return ("tap", CENTER[0], 560, "hoi thoai")
    # 5a. man xay / nang cap: nut "... ngay" ghi "Mien phi" -> BAM MIEN PHI (uu tien hon chu V, theo nguoi choi).
    #     Nut "... ngay" ghi so kim cuong -> KHONG bam (khong tieu kim cuong); dung nut "Xay dung" thuong ben duoi.
    #     Ngoai le: lop phu huong dan toi man hinh + chu V chi nut KHAC (vd "Tang cap" ben phai) -> nut Mien phi
    #     bi khoa duoi lop phu, bam mai khong an (#4, #2 2026-11-19: 40 lan cham (157,914) -> dat gioi han buoc).
    p = v.find(img, "tutorial/label_free", th=0.9, roi=(40, 860, 260, 100))
    if p:
        pv = v.find(img, "tutorial/marker_v", th=TH["tutorial/marker_v"], roi=(0, 700, 540, 260))
        if pv and abs(pv[0] - p[0]) > 80:
            return ("tap", pv[0], min(950, pv[1] + V_DY), "mui ten V (Mien phi bi khoa)")
        return ("tap", p[0], p[1] - 14, "xay/nang cap ngay (Mien phi)")
    # 5b3. CHE DO XAY (thanh duoi co nut X do): KHONG bam X.
    #   a) cong trinh da dat nhung DAU CHAN DO (sai cho) -> nhan giu dau chan, keo ve tam o xanh da nho
    #   b) con the cong trinh o thanh duoi -> nhan giu the, keo vao o xanh (nho vi tri o)
    #   c) dau chan da xanh -> de buoc chu V ben duoi bam nut V (dau tick)
    bx = v.find(img, "common/btn_close", th=0.9, roi=(440, 820, 100, 110))
    if not bx and state.get("in_build"):        # vua thoat che do xay -> xoa trang thai cho cong trinh sau
        for k_ in ("in_build", "zone", "drags", "slots_mode", "slots_tried", "confirms", "drag_from", "ok_taps",
                   "build_waits"):
            state.pop(k_, None)
    if bx:
        state["in_build"] = True
        card, zone = build_targets(img)
        if zone:
            state["zone"] = zone
        fp = find_footprint_red(img)
        if fp and state.get("drags", 0) < 8:
            # o goi y da nho (game co hien o xanh) -> keo ve do; khong co -> thu lan luot cac cho trong tu do
            target = state.get("zone") if not state.get("slots_mode") else None
            if target is None:
                slots = [c for c in free_slots(img) if c not in state.setdefault("slots_tried", [])
                         and abs(c[0] - fp[0]) + abs(c[1] - fp[1]) > 40]
                if slots:
                    target = slots[0]
                    state["slots_tried"].append(target)
            if target:
                state["drags"] = state.get("drags", 0) + 1
                state["drag_from"] = fp
                return ("drag", target[0], target[1], "keo dau chan do toi cho trong")
        # nut XAC NHAN (dau tick xanh) dang hien va KHONG con dau chan do -> bam thang (chu du an 2026-11-20 "bam vao
        # day"; truoc chi doan vi tri tu o xanh da nho +52/+134 va toi da 3 lan). Nut xam (dau chan do) -> khong bam.
        ok = v.find(img, "tutorial/btn_build_ok", th=0.88, roi=(0, 150, 540, 650))
        if ok and not fp and _colored(img, ok[0], ok[1], min_sat=40) and state.get("ok_taps", 0) < 4:   # xanh 77 / xam 11
            state["ok_taps"] = state.get("ok_taps", 0) + 1
            return ("tap", ok[0], ok[1], "xac nhan xay (nut tick)")
        if card and state.get("drags", 0) < 8:
            target = zone
            if not target:                       # game khong hien o xanh -> tu tim cho trong 2x2
                state["slots_mode"] = True
                slots = free_slots(img)
                target = slots[0] if slots else None
                if target:
                    state.setdefault("slots_tried", []).append(target)
            if target:
                state["drags"] = state.get("drags", 0) + 1
                state["drag_from"] = card
                return ("drag", target[0], target[1], "keo the cong trinh vao o " + ("xanh" if zone else "trong tu do"))
        # dau chan da XANH (khong con do, khong con the) -> bam dau tick: luon o tam dau chan + (52, ~135)
        # (do b3/b5: dau chan (206,397)->tick (258,535); (270,439)->(322,572)); nut X do ben trai KHONG bam
        if zone and not card and zone_all_green(img, zone) and state.get("confirms", 0) < 3:
            state["confirms"] = state.get("confirms", 0) + 1
            return ("tap", zone[0] + 52, min(950, zone[1] + 134), "xac nhan xay (dau tick)")
        # P4: follow het keo (56/78 anh follow_maxsteps 18-22/11 ket o day toi het 40 buoc) -> HUY bang nut X do
        # (giong buoc construct: construct_no_spot -> X), de buoc construct dat lai voi luat tim o co trong cua no
        if state.get("follow"):
            state["build_waits"] = state.get("build_waits", 0) + 1
            if quest_rules.build_give_up(state):
                return ("build_fail", bx[0], bx[1], "che do xay: khong dat duoc -> huy (X)")
        return ("wait", 0, 0, "che do xay: cho")        # che do xay -> KHONG BAO GIO roi xuong luat bam X
    # 4b. bong bong "Free" tren cong trinh dang xay = hoan thanh mien phi (chu du an 2026-11-20). Khong ton kim cuong.
    from bot.badges import free_bubbles
    fb = free_bubbles(img)
    if fb:
        return ("tap", fb[0][0], fb[0][1], "Free: hoan thanh xay mien phi")
    # 5. muc tieu do game chi. Dem vien 40 px: chu V chi vao icon nhiem vu sat mep trai bi cat mat 1 phan
    #    (lan chay 2026-11-18 #49-#51: khong khop -> dung yen)
    pad = cv2.copyMakeBorder(img, 0, 0, PAD, PAD, cv2.BORDER_REPLICATE)
    p = v.find(pad, "tutorial/marker_v", th=TH["tutorial/marker_v"])
    if p:
        x = max(12, min(528, p[0] - PAD))
        return ("tap", x, min(950, p[1] + V_DY), "mui ten V")
    # chu V nam NGANG (vd chi vao nut "Xay dung" o man nang cap): xoay mau, cham lech V_DY theo huong mui ten.
    # Khop nham tren ban ghi: phai <=0.65, trai <=0.60 -> nguong 0.72. (Huong len khop nham 0.84 -> khong dung)
    for name, dx in (("tutorial/marker_v_right", V_DY), ("tutorial/marker_v_left", -V_DY)):
        p = v.find(pad, name, th=0.72)
        if p:
            x = max(12, min(528, p[0] - PAD + dx))
            return ("tap", x, p[1], "mui ten V ngang")
    # 2 pha nhap nhay cua ban tay (hand_green2 cat tu man mo thung tiep te, chu du an gui 2026-11-19: mau cu chi khop 0.79)
    p = _f(v, img, "tutorial/hand_green") or _f(v, img, "tutorial/hand_green2")
    if p:
        t_ = find_tile_below(img, p[0], p[1] + 20)
        if t_:
            return ("tap", t_[0], t_[1], "ban tay xanh -> o duoi")
        return ("tap", p[0], min(950, p[1] + HAND_DY), "ban tay xanh")
    p = find_hand_rot(img)
    if p:
        import math
        a = math.radians(p[2])
        x, y = p[0] + HAND_DY * math.sin(a), p[1] + HAND_DY * math.cos(a)
        return ("tap", int(max(12, min(528, x))), int(min(950, y)), f"ban tay xanh nghieng {p[2]}")
    p = find_hand_beam(img)
    if p:
        t_ = find_tile_below(img, p[0], p[1] + 20)
        if t_:
            return ("tap", t_[0], t_[1], "ban tay xanh (cot sang) -> o duoi")
        return ("tap", p[0], min(950, p[1] + HAND_DY), "ban tay xanh (cot sang)")
    # 5a2. HET TAN THU: menu cong trinh (Chi tiet / Tang cap) o thanh pho ma KHONG co chu V chi duong
    #      -> game da tha cho nguoi choi tu lam (do 2026-11-18, Chuong 5: bot lap "Den" -> menu -> cho, khong co V).
    #      Can 2 khung lien tiep (chu V nhap nhay co the lot 1 khung). Viec xay tiep do mainquest/quests lam.
    if v.find(img, "build/btn_upgrade_icon", th=0.85) and v.find(img, "common/btn_to_world"):
        state["menu_nov"] = state.get("menu_nov", 0) + 1
        if state["menu_nov"] >= 2:
            return ("done", 0, 0, "menu cong trinh khong co chu V -> het tan thu")
        return ("wait", 0, 0, "menu cong trinh: cho chu V")
    state["menu_nov"] = 0
    # 5b. bang "Chuong N" (uu tien theo nguoi choi): 1) "Nhan toan bo" thuong chuong khi nut SANG (xam = chua du)
    #     2) "Nhan" tung dong  3) het thi "Den" dong tren cung chua xong (1 dong bam >3 lan van quay lai -> dong ke)
    if v.find(img, "common/btn_close", th=0.85, roi=(440, 150, 100, 80)):
        p = v.find(img, "tutorial/btn_claim_all", th=0.85)
        if p and _colored(img, p[0], p[1]):
            return ("tap", p[0], p[1], "bang chuong -> Nhan toan bo")
        claims = [c for c in v.find_all(img, "tutorial/btn_claim", th=0.9, roi=(380, 230, 160, 420))
                  if _colored(img, c[0], c[1])]
        if claims:
            c = min(claims, key=lambda c: c[1])
            return ("tap", c[0], c[1], f"bang chuong -> Nhan (dong y={c[1]})")
        gos = sorted(v.find_all(img, "quest/btn_go", th=0.85), key=lambda p: p[1])
        if gos:
            tried = state.setdefault("go_tries", {})
            for gx, gy, _ in gos:
                key = gy // 20
                if tried.get(key, 0) < 3:
                    tried[key] = tried.get(key, 0) + 1
                    return ("tap", gx, gy, f"bang chuong -> Den (dong y={gy})")
    # 5b2. man Tuong: chi tiet -> "Tang cap" (toi da 5 lan / lan vao); danh sach -> tuong co mui ten xanh; het -> quay lai
    p = v.find(img, "hero/btn_levelup", th=0.85)
    if p and state.get("hero_lv", 0) < 5:
        state["hero_lv"] = state.get("hero_lv", 0) + 1
        return ("tap", p[0], p[1], "tuong -> tang cap")
    if v.find(img, "hero/title", th=0.9):
        p = v.find(img, "hero/arrow_up", th=0.85)
        if p and state.get("hero_open", 0) < 3:
            state["hero_open"] = state.get("hero_open", 0) + 1
            state["hero_lv"] = 0
            return ("tap", p[0], p[1], "danh sach tuong -> mo tuong nang duoc")
        b = v.find(img, "common/btn_back", th=0.9)
        if b:
            return ("tap", b[0], b[1], "man tuong xong -> quay lai")
    if p:   # da tang cap du 5 lan o man chi tiet -> quay lai
        b = v.find(img, "common/btn_back", th=0.9)
        if b:
            return ("tap", b[0], b[1], "tuong da tang cap -> quay lai")
    if not p and state.get("hero_lv", 0) > 0:
        # vua tang cap tuong, nut "Tang cap" bien mat (het EXP / can nha chinh cao hon, vd "Dieu kien: Xuong kien
        # truc dat cap 4") -> quay lai (do #5 2026-11-18: dung 5 vong o man chi tiet tuong)
        b = v.find(img, "common/btn_back", th=0.9)
        if b:
            state["hero_lv"] = 0
            return ("tap", b[0], b[1], "tuong het tang cap duoc -> quay lai")
    # 5c. popup co nut X (vd "Ruong Kho Bau" sau khi cham thung) -> dong
    p = v.find(img, "common/btn_close", th=0.9)
    if p:
        return ("tap", p[0], p[1], "dong popup (X)")
    # 5d. linh tren o do (kiem cheo hong phia tren) -> cot sang cam chieu xuong -> cham chan cot
    p = find_beam(img)
    if p:
        # cung 1 o do cham hoai khong an (muc tieu dau lau, #0 2026-11-20: 30 lan (276,386) -> het 40 buoc) -> bo qua o nay
        bt = state.setdefault("beam_taps", {})
        key = (p[0] // 30, p[1] // 30)
        bt[key] = bt.get(key, 0) + 1
        if bt[key] <= 6:
            return ("tap", p[0], p[1], "o do duoi chan muc tieu")
    # 6. nut quen thuoc
    p = _f(v, img, "tutorial/btn_attack_red")
    if p:
        return ("tap", p[0], p[1], "tan cong")
    # 6a. CHE DO follow: man doi hinh ma KHONG du doan "Thang toan dien" -> khong danh (giong mainquest/campaign)
    #     Kiem tra SAU khi da bam "tu xep doi hinh" (du doan tinh theo doi hinh dang xep).
    if state.get("follow") and state.get("formation") and _formation_btn(v, img) and not _pred_win(v, img):
        return ("weak", 0, 0, "doi hinh khong du doan thang -> khong danh")
    if _formation_btn(v, img):          # man doi hinh: tu xep 1 lan roi Chien dau
        if not state.get("formation"):
            state["formation"] = True
            p = _formation_btn(v, img)
            return ("tap", p[0], p[1], "tu xep doi hinh")
        state["formation"] = False
        p = v.find(img, "campaign/btn_fight", th=0.8)
        return ("tap", p[0] if p else FIGHT_XY[0], p[1] if p else FIGHT_XY[1], "chien dau")
    state["formation"] = False
    p = _f(v, img, "tutorial/icon_explore")
    if p:
        return ("tap", p[0], p[1], "kinh lup kham pha")
    p = v.find(img, "tutorial/btn_build", th=0.9, roi=(260, 860, 280, 100))   # khong mien phi -> xay thuong
    if p:
        return ("tap", p[0], p[1] + 8, "xay dung (thuong)")
    p = _f(v, img, "tutorial/icon_repair")
    if p:
        return ("tap", p[0], p[1], "sua chua cong trinh (co le)")
    p = _f(v, img, "tutorial/icon_unlock")          # bong bong o khoa mo: "Mo rong lanh tho" (khop nham max 0.74)
    if p:
        return ("tap", p[0], p[1], "mo khoa lanh tho")
    p = _f(v, img, "tutorial/supply_box")
    if p:
        boxes = state.setdefault("box_taps", {})
        key = (p[0] // 30, p[1] // 30)
        if boxes.get(key, 0) < 2:          # cham thung -> popup Ruong; khong lap vo han cung 1 thung
            boxes[key] = boxes.get(key, 0) + 1
            return ("tap", p[0], p[1], "thung tiep te")
    p = v.find(img, "common/btn_close", roi=ROI["common/btn_close@top"])
    if p:
        return ("tap", p[0], p[1], "dong the CONGRATULATIONS")
    # 6b. bang nhiem vu dang o tab Chinh/Chuong, tab "Nhiem vu hang ngay" co CHAM DO -> game huong dan bam tab do
    #     (anh chu du an 2026-11-22). Toi da 2 lan / phien (cham do khong mat khi chua nhan het).
    t3 = v.find(img, "daily/tab_3_daily", th=0.85)
    if t3 and v.find(img, "daily/tab_2_main", th=0.85) and state.get("daily_tab", 0) < 2:
        from bot.badges import red_dots
        if red_dots(img, (t3[0] + 40, t3[1] - 50, 60, 50)):
            state["daily_tab"] = state.get("daily_tab", 0) + 1
            return ("tap", t3[0], t3[1], "tab Nhiem vu hang ngay (cham do)")
    # 6c. mui ten XANH chi xuong tren ban do -> cham quan/muc tieu ngay duoi (toi da 3 lan moi vi tri)
    g = find_green_chevron(img)
    if g:
        key = (g[0] // 40, g[1] // 40)
        seen = state.setdefault("chevron_taps", {})
        if seen.get(key, 0) < 3:
            seen[key] = seen.get(key, 0) + 1
            return ("tap", g[0], g[1], "mui ten xanh chi xuong -> cham muc tieu")
    # 6d. P4 - CHE DO follow, man khong co huong dan cua game nhung biet chac (129 anh follow_stuck 18-22/11):
    #     bang nhiem vu kieu moi (X do goc tren-phai) -> Nhan toan bo / Nhan / dong; ban do the gioi / Tinh bao -> ra
    #     (viec do cua buoc rebels/intel/gather; KHONG cham giua ban do: chon o dat "Chuyen thanh / Chiem linh").
    if state.get("follow"):
        r = _follow_known(v, img, state, idle)
        if r:
            return r
    # 7. khong nhan ra
    home = v.find(img, "common/btn_to_world")
    if not home and idle >= 5:     # cham giua 3 lan khong qua -> phim Back (dong popup la an toan hon cham mu)
        return ("back", 0, 0, "man la -> phim Back")
    if not home and idle >= 2:     # cho 2 nhip truoc: chu V / ban tay nhap nhay co the hien o khung sau
        return ("tap", CENTER[0], CENTER[1], "man la (canh phim / mo khoa) -> cham giua")
    if home and idle >= 3:
        k = state.get("quest_alt", 0)
        state["quest_alt"] = k + 1
        qx, qy = QUEST_TAPS[k % len(QUEST_TAPS)]       # luan phien: icon nhiem vu (nguoi choi cham) / dong chu
        return ("tap", qx, qy, "dung yen -> cham thanh nhiem vu")
    return ("wait", 0, 0, "cho")


def _follow_known(v, img, state, idle=0):
    """Follow: man biet chac (quest_rules.follow_screen) -> hanh dong, hoac None (de luat 'khong nhan ra').
    Nhan thuong lam ngay; ra / quay lai chi sau 1 nhip cho (idle >= 1): chu V / ban tay nhap nhay co the hien sau."""
    kind = quest_rules.follow_screen(v, img)
    if kind == "quest_board":
        p = v.find(img, "tutorial/btn_claim_all", th=0.85)
        if p and _colored(img, p[0], p[1]) and state.get("board_claims", 0) < 6:
            state["board_claims"] = state.get("board_claims", 0) + 1
            return ("tap", p[0], p[1], "bang nhiem vu -> Nhan toan bo")
        claims = [c for c in v.find_all(img, "tutorial/btn_claim", th=0.9, roi=(380, 180, 160, 700))
                  if _colored(img, c[0], c[1])]
        if claims and state.get("board_claims", 0) < 6:
            state["board_claims"] = state.get("board_claims", 0) + 1
            c = min(claims, key=lambda c: c[1])
            return ("tap", c[0], c[1], "bang nhiem vu -> Nhan")
        if idle < 1:
            return ("wait", 0, 0, "bang nhiem vu: cho huong dan")
        x = quest_rules.board_close(v, img)
        if x:
            return ("exit", x[0], x[1], "bang nhiem vu: het viec -> dong (X)")
        return ("exit", 0, 0, "bang nhiem vu: het viec")
    if idle < 1:
        return None
    if kind == "intel":
        b = v.find(img, "common/btn_back", th=0.85)
        return ("exit", b[0] if b else 0, b[1] if b else 0, "ban do Tinh bao -> ra (viec cua buoc intel)")
    if kind == "world":
        return ("exit", 0, 0, "ban do the gioi khong co huong dan -> ra (viec cua rebels/gather)")
    if not v.find(img, "common/btn_to_world"):
        b = v.find(img, "common/btn_back", th=0.9)
        if b:
            return ("tap", b[0], b[1], "bang co nut quay lai -> quay lai")
        for n, roi in quest_rules.BOARD_CLOSE:   # vd "Gia nhap lien minh!" (X 0,84) - KHONG bam "Gia nhap"/"Tao moi"
            p = v.find(img, n, th=0.82, roi=roi)
            if p:
                return ("tap", p[0], p[1], "popup X goc tren -> dong")
    return None


def finish(ctx, step, why):
    """Het tan thu: ghi trang thai + TAT buoc tutorial cho may nay (lan sau mainquest/quests lam tiep)."""
    log.info("Het huong dan tan thu sau %d buoc (%s) -> tat buoc tan thu, chuyen sang nhiem vu chinh", step, why)
    st = getattr(ctx, "store", None)
    if st:
        st.update(ctx.dev.idx, tutorial_done=time.time())
        st.set_settings(ctx.dev.idx, {"modules": {"tutorial": False}})
    ctx.back_out()
    return True


def _pred_win(v, img):
    from bot.modules.campaign import predicted_win
    return predicted_win(v, img)


GUIDE_WHY = ("ban tay", "mui ten V", "o do duoi", "V chi")


def guide_visible(v, img):
    """Man dang co huong dan cua game (ban tay xanh, mui ten V, o do duoi muc tieu) -> ly do, hoac None.
    Chu du an 2026-11-21: huong dan hien ra GIUA cac buoc khac (quet cham do, quan sat) va phai cham tay
    (logs/human/20261121 anh 9-12) -> runner kiem tra sau moi buoc va lam theo."""
    try:
        act, _, _, why = decide(v, img, state={"follow": True})
    except Exception:
        return None
    return why if act == "tap" and any(k in why for k in GUIDE_WHY) else None


def follow(ctx, max_steps=40, no_battle=False):
    """Lam theo huong dan cua game SAU tan thu (vd sau nut "Den" cua bang Chuong: tang cap tuong, don phe tich,
    xay cong trinh moi...) bang chinh decide() cua tan thu. Dung khi ve thanh pho dung yen.
    -> 'idle' | 'build_<ket qua upgrade_here>' | 'weak' (khong du doan thang) | 'stuck' | 'lose' | 'max'"""
    return run(ctx, max_steps=max_steps, idle_limit=4, max_retry=0, follow=True, no_battle=no_battle)


def _power(ctx):
    from bot import ocr
    try:
        return ocr.topbar(ctx.shot()).get("power")
    except Exception:
        return None


def weak_wait(ctx):
    """Tran tan thu thua lien tiep (vd "That bai nang ne" khi danh muc tieu, #4 2026-11-19) -> danh lai vo ich.
    Tam dung tan thu toi khi luc chien tang power_gain_pct% (giong mainquest) hoac qua weak_retry_h gio
    (khong doc duoc luc chien). -> True = bo qua lan nay."""
    st = getattr(ctx, "store", None)
    if not st:
        return False
    s = st.inst(ctx.dev.idx)
    need, until = s.get("tutorial_need_power"), s.get("tutorial_wait_until")
    if not need and not until:
        return False
    p = _power(ctx)
    if (need and p and p >= need) or (until and time.time() >= until):
        log.info("Tan thu: luc chien %s (can %s) -> danh lai", p, need)
        st.update(ctx.dev.idx, tutorial_need_power=None, tutorial_wait_until=None)
        return False
    log.info("Tan thu tam dung: luc chien %s < %s (cho tang suc manh)", p, need)
    return True


def _block_weak(ctx):
    st = getattr(ctx, "store", None)
    if not st:
        return
    tc = ctx.cfg.get("tutorial", {})
    pct = tc.get("power_gain_pct", ctx.cfg.get("mainquest", {}).get("power_gain_pct", 5))
    try:
        ctx.ensure_city()   # doc luc chien o man thanh pho (doc ngay sau man thua ra 71352 thay vi 43552, #4 2026-11-19)
    except Exception:
        pass
    p = _power(ctx)
    need = int(p * (1 + pct / 100)) if p else None
    st.update(ctx.dev.idx, tutorial_need_power=need,
              tutorial_wait_until=time.time() + tc.get("weak_retry_h", 6) * 3600)
    log.info("Tan thu: thua lien -> tam dung, danh lai khi luc chien >= %s hoac sau %s gio",
             need, tc.get("weak_retry_h", 6))


def run(ctx, max_steps=600, idle_limit=10, max_retry=5, follow=False, no_battle=False):
    """follow=False: qua tan thu (True = xong, False = dung giua chung). follow=True: xem follow()."""
    from bot import steer
    if not follow and weak_wait(ctx):
        return "weak_wait"
    tag = "follow" if follow else "tutorial"
    idle = quest_taps = retries = 0
    state = {"follow": follow, "no_battle": no_battle}
    trace = ctx.cfg.get("tutorial", {}).get("trace_dir")   # luu anh + quyet dinh tung buoc de xem lai
    for step in range(max_steps):
        img = ctx.shot()
        act, x, y, why = decide(ctx.v, img, idle, state)
        log.info("tan thu #%d: %s (%d,%d) %s", step, act, x, y, why)
        if act == "done":
            if follow:      # menu cong trinh -> nang cap nhu nhiem vu xay
                from bot import build
                return "build_" + build.upgrade_here(ctx)
            return finish(ctx, step, why)
        if trace:
            import cv2
            dbg = img.copy()
            if act == "tap":
                cv2.circle(dbg, (int(x), int(y)), 20, (0, 0, 255), 4)
            cv2.rectangle(dbg, (0, 0), (540, 24), (0, 0, 0), -1)
            cv2.putText(dbg, f"#{step} {act} {why}", (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.imwrite(f"{trace}/{step:03d}.jpg", dbg, [cv2.IMWRITE_JPEG_QUALITY, 75])
        # follow sau khi da thua (quests 2026-11-20: #5 thua dong 3 roi lai danh dong 4) -> khong vao tran nua
        if follow and state.get("no_battle") and (act == "steer" or why in ("bat dau tro choi", "chien dau",
                                                                             "tu xep doi hinh")):
            log.info("Follow: dang cho tang luc chien - khong vao tran")
            act = "weak"
        if act == "exit":   # P4 follow: man biet chac, het viec cua follow -> ra thanh pho, ket qua 'idle'
            if x or y:
                ctx.tap(x, y, wait=1.0)
            ctx.ensure_city()
            return "idle" if follow else False
        if act == "build_fail":   # P4 follow: che do xay khong dat duoc -> huy bang X, de buoc construct lam
            ctx.tap(x, y, wait=1.0)
            ctx.ensure_city()
            return "build_no_spot"
        if act == "weak":   # chi follow: de mainquest ghi nhan va doi luc chien tang
            ctx.back_out()
            return "weak"
        if act == "steer":
            r = steer.run_battle(ctx.dev.adb, ctx.dev.serial, ctx.v, is_battle=is_battle,
                                 debug_dir=ctx.cfg.get("battle", {}).get("debug_dir"))
            log.info("Tan thu - tran: %s", r)
            idle = 0
            continue
        if act == "drag":
            from bot.touch import Finger
            fx, fy = state.get("drag_from", (240, 870))
            fg = Finger(ctx.dev.adb, ctx.dev.serial)
            try:
                fg.down(fx, fy)
                time.sleep(0.4)                       # nhan giu the cong trinh
                fg.drag_to(x, y)                      # keo cham vao tam o xanh
                time.sleep(0.6)
                ok = zone_all_green(ctx.shot(), (x, y))
                log.info("Tan thu - keo cong trinh toi (%d,%d): o %s", x, y, "TOAN XANH" if ok else "chua xanh het")
                time.sleep(0.2)
            finally:
                fg.close()                            # tha tay
            time.sleep(1.5)
            idle = 0
            continue
        if act == "back":
            backs = state.get("backs", 0) + 1
            state["backs"] = backs
            if backs > 4:
                ctx.save_debug(f"{tag}_stuck")
                log.warning("Tan thu: man la, Back %d lan van khong qua - dung", backs - 1)
                return "stuck" if follow else False
            # man 'Tro giup lien minh' khong dong bang phim Back (i0/i2 2026-11-22 follow_stuck): thu nut "<" truoc,
            # tu lan 2 tro di cham mui ten goc tren-trai (chi khi khong o thanh pho/ban do)
            if not ctx.tap_first(["common/btn_back", "common/btn_back2"], wait=0.8):
                if backs >= 2 and not ctx.is_home():
                    ctx.tap(50, 26, wait=1.0)
                else:
                    ctx.safe_back()   # o thanh pho khong bam Back (chi hien "Roi tro choi?")
            idle = 2
            continue
        if act == "tap":
            if not why.startswith(("man la", "dung yen")):
                state["backs"] = 0
            if why == "thua -> bat dau lai" and not state.get("last_lose"):   # dem 1 lan / tran thua, khong dem moi lan bam
                retries += 1
                if retries > max_retry:
                    ctx.save_debug(f"{tag}_lose")
                    log.warning("Tan thu: thua %d lan lien - dung", retries - 1)
                    if not follow:
                        ctx.back_out()
                        _block_weak(ctx)
                    return "lose" if follow else False
            elif why.startswith("thang"):
                retries = 0
            if why.startswith("dung yen"):
                if follow:      # ve thanh pho, game khong chi gi them -> xong
                    return "idle"
                quest_taps += 1
                if quest_taps > 3:
                    return finish(ctx, step, "dung yen, cham thanh nhiem vu khong co huong dan")
            else:
                quest_taps = 0
            # chong lap: cham CUNG 1 cho 3 lan lien (vd cot sang bat nham tren popup) -> phim Back thay vi cham tiep
            lt = state.get("last_tap")
            same = lt and abs(lt[0] - x) <= 12 and abs(lt[1] - y) <= 12 and not why.startswith(("thua", "tuong ->"))
            state["same_taps"] = state.get("same_taps", 0) + 1 if same else 0
            state["last_tap"] = (x, y)
            if state["same_taps"] >= 3:
                log.info("Tan thu: cham (%d,%d) %d lan khong doi man hinh -> phim Back", x, y, state["same_taps"])
                state["same_taps"] = 0
                ctx.safe_back()
                continue
            ctx.tap(x, y, wait=1.2)
            state["last_lose"] = why.startswith("thua")
            idle = 0 if not why.startswith(("man la", "dung yen")) else idle + 1
            if idle > idle_limit:
                ctx.save_debug(f"{tag}_stuck")
                log.warning("Tan thu: khong nhan ra man hinh %d lan - dung", idle)
                return "stuck" if follow else False
            continue
        idle += 1
        time.sleep(1.5)
    log.warning("Tan thu: dat gioi han buoc")
    ctx.save_debug(f"{tag}_maxsteps")
    return "max" if follow else False
