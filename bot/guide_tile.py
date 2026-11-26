"""P13j (chu du an 26/11/2026, 2 anh tests/fixtures/p13j/): huong dan XANH trong thanh pho sau "Di" cua Tinh bao.

Cai cu bam hut: sau "Di" khong thay "Tan cong" / "Tiep te" thi dung logic ghim BAN DO THE GIOI (intel/marker_fight,
toa do cung 268,405 ...). Trong thanh pho cac diem do roi vao LINH cua minh (o xanh lam) chu khong vao muc tieu.

Huong dan that cua game:
  * muc tieu dung trong O SANG XANH LA hinh thoi, co COT SANG XANH LA thang dung phia tren -> bam tam o;
  * co khi them BAN TAY TRANG chi xuong, giua tay va vat la bong bong tron -> bam VAT duoi dau ngon (tam o),
    khong bam bong bong, khong bam tay;
  * o xanh LAM la linh cua minh: H ngoai dai GREEN_H nen khong bao gio thanh muc tieu.

find() / find_tile() / find_hand() la ham thuan (anh -> ket qua). tap_and_check() cham 1 lan, kiem man doi; khong doi
-> danh sach den toa do (tapguard) den het luot ghe.
"""
import logging
import time
from typing import NamedTuple

import cv2
import numpy as np

from bot import tapguard

log = logging.getLogger("aow")

GREEN_H, GREEN_S, GREEN_V = (33, 85), 120, 150   # vien o + cot sang (o linh xanh lam H 94-116)
PLAY_Y = (90, 870)              # bo thanh tai nguyen / thanh nut duoi
TAP_X = (60, 480)               # bo cot icon HUD ben phai (co goi tra phi)
TILE_W = range(110, 211, 8)     # be ngang o (px) - nhieu ti le zoom thanh pho
TILE_RATIO = 0.52               # cao / ngang cua hinh thoi
TILE_TH = 0.45                  # ti le vien phu xanh cua NUA YEU HON (trai / phai) -> mot cum xanh le khong du
TAP_DY = -6                     # vat dung tren o nen than vat cao hon tam o mot chut
BEAM_MIN = 50                   # so hang co cot sang HEP ngay tren o (che do xay vien xanh: toi da 47)
HAND = "intel/point_hand"
HAND_TH = 0.8
HAND_SCALES = (0.8, 0.9, 1.0, 1.1, 1.2)
HAND_TIP = (0.60, 0.96)         # dau ngon chi xuong, theo ti le (ngang, cao) cua anh mau
HAND_DROP = 85                  # dau ngon -> tam vat khi khong thay o (anh chu du an: 215,161 -> 216,246)
BUILD_X_ROI = (440, 820, 100, 110)   # nut X cua che do xay (vien o cong trinh cung mau xanh)
WHY = "o xanh huong dan"        # tien to ly do trong tutorial.decide (GUIDE_WHY)
CITY = "common/btn_to_world"
# P13l: muc tieu DICH trong thanh = o DO + cot sang CAM (kiem cheo phia tren), linh minh dung o XANH LAM ben canh
RED_H = (172, 6)                # vong qua 180
ORANGE_H = (7, 25)
BLUE_H = (94, 116)
PAIR_PX = 220                   # o xanh lam (linh minh) cach o do toi da

# man / nut hien ra sau khi cham dung vat
OPENED = ("intel/btn_attack", "intel/btn_pickup", "rebels/btn_rally", "campaign/btn_fight", "gather/btn_march",
          "rebels/btn_march_out")
STEPS = 4                       # chuoi huong dan trong 1 nhiem vu (xe tang -> hom ...) toi da
LOOKS = 3                       # so khung cho huong dan hien ra (ban do dang truot)
CHECKS = 5                      # so khung kiem sau khi cham
NEAR = 40                       # huong dan dich qua nguong nay = da doi


class Guide(NamedTuple):
    x: int
    y: int
    kind: str                   # 'hand' | 'beam' | 'enemy'


def green_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= GREEN_H[0]) & (hsv[..., 0] <= GREEN_H[1]) & (hsv[..., 1] >= GREEN_S)
         & (hsv[..., 2] >= GREEN_V)).astype(np.uint8)
    m[:PLAY_Y[0]] = 0
    m[PLAY_Y[1]:] = 0
    return m


def colour_mask(img, h, s=150, v=170):
    """Mat na mau theo dai H (h[0] > h[1] = vong qua 180), bo thanh tai nguyen / thanh nut duoi."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hue = hsv[..., 0]
    inside = (hue >= h[0]) & (hue <= h[1]) if h[0] <= h[1] else (hue >= h[0]) | (hue <= h[1])
    m = (inside & (hsv[..., 1] >= s) & (hsv[..., 2] >= v)).astype(np.uint8)
    m[:PLAY_Y[0]] = 0
    m[PLAY_Y[1]:] = 0
    return m


def find_enemy(img, blocked=None):
    """P13l (log 26/11 #6, intel_unknown_target): o DO co cot sang CAM phia tren va o XANH LAM (linh minh) ben canh
    -> Guide(diem cham tren dich, 'enemy') | None."""
    red = colour_mask(img, RED_H)
    tiles = find_tiles(red)
    if not tiles:
        return None
    beam = red | colour_mask(img, ORANGE_H)
    blue = find_tiles(colour_mask(img, BLUE_H))
    for _, cx, cy, w in tiles:
        near = any(abs(bx - cx) <= PAIR_PX and abs(by - cy) <= PAIR_PX // 2 for _, bx, by, _ in blue)
        if near and _ok(cx, cy + TAP_DY, blocked) and beam_rows(beam, cx, cy, w) >= BEAM_MIN:
            return Guide(cx, cy + TAP_DY, "enemy")
    return None


def _diamond(w):
    """-> (nua trai, nua phai) cua vien hinh thoi be ngang w (da chuan hoa tong = 1)."""
    h, t = int(round(w * TILE_RATIO)), 2
    k = np.zeros((h + 2 * t, w + 2 * t), np.float32)
    cx, cy = (w + 2 * t) // 2, (h + 2 * t) // 2
    pts = np.array([[cx - w // 2, cy], [cx, cy - h // 2], [cx + w // 2, cy], [cx, cy + h // 2]])
    cv2.polylines(k, [pts], True, 1.0, 1)
    left, right = k.copy(), k.copy()
    left[:, cx:] = 0
    right[:, :cx] = 0
    return left / left.sum(), right / right.sum()


def find_tiles(mask, top=5):
    """O hinh thoi vien xanh (khop vien nhieu ti le tren mat na mau, thu nho 1/2) -> [(diem, cx, cy, w)] giam dan."""
    if int(mask.sum()) < 150:
        return []
    d = cv2.dilate(mask, np.ones((7, 7), np.uint8))
    half = (cv2.resize(d.astype(np.float32), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA) > 0.25)
    half = half.astype(np.float32)
    cands = []
    for w in TILE_W:
        left, right = _diamond(w // 2)
        s = np.minimum(cv2.filter2D(half, -1, left, borderType=cv2.BORDER_CONSTANT),
                       cv2.filter2D(half, -1, right, borderType=cv2.BORDER_CONSTANT))
        ys, xs = np.nonzero((s >= TILE_TH) & (s >= cv2.dilate(s, np.ones((5, 5), np.uint8))))
        cands += [(float(s[y, x]), int(x) * 2, int(y) * 2, w) for x, y in zip(xs, ys)]
    out = []
    for c in sorted(cands, reverse=True):
        if all(abs(c[1] - o[1]) > 50 or abs(c[2] - o[2]) > 35 for o in out):
            out.append(c)
        if len(out) >= top:
            break
    return out


def beam_rows(mask, cx, cy, w):
    """So hang co cot sang HEP (xanh o giua, hai ben khong xanh) ngay phia tren o (cx, cy). Cot bi tay / bong bong che
    van cong don duoc cac doan lo ra."""
    y0, y1 = max(0, cy - 190), max(0, cy - int(w * 0.3))
    if y1 - y0 < 20:
        return 0
    best = 0
    for bx in range(max(45, cx - 30), min(mask.shape[1] - 45, cx + 31), 2):
        mid = mask[y0:y1, bx - 7:bx + 8].sum(axis=1) >= 2
        left = mask[y0:y1, bx - 40:bx - 22].sum(axis=1) <= 2
        right = mask[y0:y1, bx + 22:bx + 41].sum(axis=1) <= 2
        best = max(best, int((mid & left & right).sum()))
    return best


def find_hand(v, img):
    """Ban tay TRANG chi xuong (anh mau intel/point_hand, nhieu ti le, chi so phan tay + vien) -> (x, y dau ngon, ti
    le) | None. Loc truoc theo mang trang de khong quet ca man."""
    has = getattr(v, "has", None)           # Vision gia (test luat cu) khong co anh mau
    tpl = v.load(HAND) if has and has(HAND) else None
    if tpl is None:
        return None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    white = ((hsv[..., 1] < 60) & (hsv[..., 2] > 200)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(white)
    scaled = []
    for s in HAND_SCALES:
        t = cv2.resize(tpl, None, fx=s, fy=s)
        th = cv2.cvtColor(t, cv2.COLOR_BGR2HSV)
        m = ((th[..., 1] < 60) & (th[..., 2] > 200)).astype(np.uint8) * 255
        m = cv2.dilate(m, np.ones((5, 5), np.uint8))
        scaled.append((s, t, cv2.merge([m, m, m])))
    best = None
    for k in range(1, n):
        x, y, w, h, area = st[k]
        if not (700 <= area <= 7000 and 30 <= w <= 130 and 25 <= h <= 100 and PLAY_Y[0] <= y <= PLAY_Y[1]):
            continue
        x0, y0 = max(0, x - 40), max(0, y - 40)
        win = img[y0:y + h + 40, x0:x + w + 40]
        for s, t, m in scaled:
            if win.shape[0] < t.shape[0] or win.shape[1] < t.shape[1]:
                continue
            r = cv2.matchTemplate(win, t, cv2.TM_CCOEFF_NORMED, mask=m)
            r[~np.isfinite(r)] = 0
            _, score, _, loc = cv2.minMaxLoc(r)
            if HAND_TH <= score <= 1.001 and (best is None or score > best[0]):
                tip = (x0 + loc[0] + int(t.shape[1] * HAND_TIP[0]), y0 + loc[1] + int(t.shape[0] * HAND_TIP[1]))
                best = (score, int(tip[0]), int(tip[1]), s)
    return best[1:] if best else None


def _ok(x, y, blocked):
    return TAP_X[0] <= x <= TAP_X[1] and PLAY_Y[0] <= y <= PLAY_Y[1] and not (blocked and blocked(x, y))


def find(v, img, blocked=None, enemy=False):
    """Huong dan xanh dang hien -> Guide(diem CHAM, loai) | None. blocked(x, y) -> True: toa do da danh sach den.
      1. co ban tay -> vat duoi dau ngon: tam o xanh ngay duoi tay (on dinh khi tay nhap nho), khong thay o thi
         dau ngon + HAND_DROP;
      2. khong co tay -> o xanh co cot sang phia tren, CHI khi dang o thanh pho (cong buff tran chay duong cung la
         khoi xanh co cot: 3 khung taught/battle);
      3. enemy=True (chi duong Tinh bao sau "Di"): o DO + cot cam trong thanh (find_enemy); tutorial.decide da co
         find_beam rieng cho o do."""
    if not isinstance(img, np.ndarray) or v.find(img, "common/btn_close", th=0.9, roi=BUILD_X_ROI):
        return None
    mask = green_mask(img)
    tiles = find_tiles(mask)
    hand = find_hand(v, img)
    if hand:
        tx, ty, s = hand
        under = [t for t in tiles if abs(t[1] - tx) <= 70 and 30 <= t[2] - ty <= 170]
        if under:
            _, cx, cy, _ = max(under)
            x, y = cx, cy + TAP_DY
        else:
            x, y = tx, ty + int(HAND_DROP * s)
        return Guide(x, y, "hand") if _ok(x, y, blocked) else None
    if not v.find(img, CITY):
        return None
    for _, cx, cy, w in tiles:
        if _ok(cx, cy + TAP_DY, blocked) and beam_rows(mask, cx, cy, w) >= BEAM_MIN:
            return Guide(cx, cy + TAP_DY, "beam")
    return find_enemy(img, blocked) if enemy else None


# ---------- thao tac ----------
def blocked_by(ctx):
    """Ham blocked(x, y) theo danh sach den cua luot ghe."""
    g = tapguard.of(ctx)
    return lambda x, y: g.blocked("guide", x, y)


def opened(v, img):
    """Cham dung vat: hien nut Tan cong / Tiep te / Tap ket / man doi hinh / bang nhan thuong."""
    return any(v.find(img, n) for n in OPENED) or bool(v.find(img, "common/msg_reward", th=0.75))


def repeated(history, hit):
    """Huong dan hien lai dung cho da cham 2 lan lien (history: diem da cham trong chuoi, moi nhat cuoi)."""
    last = history[-2:]
    return len(last) == 2 and all(abs(x - hit.x) <= NEAR and abs(y - hit.y) <= NEAR for x, y in last)


def tap_and_check(ctx, hit):
    """Cham huong dan 1 lan -> 'panel' (nut / bang hien ra) | 'changed' (huong dan mat / chuyen cho 2 khung lien, vd hom
    da nhat) | 'nochange' (van y nguyen -> danh sach den toa do, khong cham lai trong luot ghe)."""
    log.info("Huong dan xanh (%s): cham vat @%d,%d", hit.kind, hit.x, hit.y)
    ctx.tap(hit.x, hit.y, wait=1.5)
    moved = 0
    for k in range(CHECKS):
        img = ctx.shot()
        if opened(ctx.v, img):
            return "panel"
        now = find(ctx.v, img, enemy=hit.kind == "enemy")
        gone = now is None or abs(now.x - hit.x) > NEAR or abs(now.y - hit.y) > NEAR
        moved = moved + 1 if gone else 0
        if moved >= 2:
            return "changed"
        if k + 1 < CHECKS:
            time.sleep(0.8)
    tapguard.of(ctx).ban("guide", hit.x, hit.y, "cham huong dan khong doi man")
    return "nochange"


def follow_city(ctx):
    """Sau "Di": lam theo huong dan xanh (va o do dich, P13l) trong thanh pho (toi da STEPS cham).
      None      : khong co huong dan va KHONG o thanh pho -> ben goi dung logic ghim ban do the gioi;
      'panel'   : nut / bang da hien;
      'changed' : da cham, huong dan het ma khong co bang nao;
      'miss'    : o thanh pho nhung khong thay huong dan / cham khong an -> KHONG dung toa do ban do the gioi."""
    blocked, acted, history = blocked_by(ctx), False, []
    for _ in range(STEPS):
        hit, city = None, False
        for look in range(LOOKS):
            img = ctx.shot()
            if acted and opened(ctx.v, img):
                return "panel"
            hit = find(ctx.v, img, blocked, enemy=True)
            city = bool(ctx.v.find(img, CITY))
            if hit or not city:
                break
            if look + 1 < LOOKS:
                time.sleep(0.8)
        if hit is None:
            if acted:
                return "changed"
            return "miss" if city else None
        if repeated(history, hit):      # 'doi' roi lai hien dung cho (nhap nhay) -> coi nhu khong an
            tapguard.of(ctx).ban("guide", hit.x, hit.y, "cham 2 lan huong dan van hien lai")
            return "miss"
        history.append((hit.x, hit.y))
        r = tap_and_check(ctx, hit)
        if r == "panel":
            return r
        if r == "nochange":
            return "miss"
        acted = True
    return "changed"
