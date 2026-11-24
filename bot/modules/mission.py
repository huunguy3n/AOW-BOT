"""Su kien "Su menh" (P7-7, chu du an 2026-11-24; anh data/pm-shots/owner-20261124/su_menh_*.png).

Mo tu icon ben phai man thanh pho (mission/icon, cot icon phai ~512,305, co so do).
  * CHI tab "Nhiem vu hang ngay" (goc phai hang tab) -> nhan thuong (nut "Nhan" xanh theo mau + chu, bot/buttons.py loc
    nut tra phi).
  * "Qua ky dieu" (icon hop qua tren cung): ruong nho goc tren-trai (co dong ho) nhan MIEN PHI khi co cham do.
  * KHONG BAO GIO cham: tab "The thong hanh" (d250000), tab / ban xuc xac "San kho bau", cac goi tra phi
    (d250000, d500000, d1250000). Moi lan cham deu qua tap_ok() (vung cho phep theo man) + loc chu tra phi.
Thieu anh mau -> bo qua em (log "thieu anh mau", bot/tplneed.py).
"""
import logging
import re

import cv2
import numpy as np

from bot import buttons, tplneed
from bot.badges import red_dots

log = logging.getLogger("aow")

ICON_ROI = (440, 90, 100, 420)        # cot icon phai man thanh pho (Qua, Hoat dong, Phuc loi, Su menh...)
TAB_ROI = (0, 180, 540, 70)           # hang tab: San kho bau | The thong hanh | Nhiem vu hang ngay
DAILY_ROI = (0, 245, 540, 715)        # noi dung tab Nhiem vu hang ngay (nut Nhan)
GIFT_ROI = (0, 60, 540, 140)          # hang icon su kien tren cung (San kho bau tren chien truong | Qua ky dieu)
FREE_CHEST_ROI = (0, 200, 280, 260)   # man Qua ky dieu: ruong nho goc tren-trai (co dong ho)

# vung cho phep cham theo man (x, y, w, h). Ngoai vung -> KHONG cham (The thong hanh x 180-350, San kho bau x < 180
# o hang tab; ban xuc xac / nut "+" xuc xac / goi gia tien nam ngoai cac vung nay)
CART_ROI = (460, 265, 80, 75)         # P9-4: icon xe day (cua hang xuc xac) goc phai tren tab San kho bau
SHOP_ROI = (0, 90, 540, 870)          # noi dung "Cua hang xuc xac dieu khien tu xa"
ALLOW = {
    "main": [(355, 185, 185, 60),       # tab "Nhiem vu hang ngay"
             (140, 70, 110, 120)],      # icon "Qua ky dieu"
    "hunt_nav": [(20, 70, 115, 115)],   # P9-4: icon su kien "San kho bau tren chien truong" - CHI hunt_shop dung
    "daily": [DAILY_ROI],               # nut Nhan / ruong moc trong tab Nhiem vu hang ngay
    "gift": [FREE_CHEST_ROI],           # ruong mien phi goc tren-trai
    "hunt": [CART_ROI],                 # P9-4: CHI icon xe day - khong bao gio ban xuc xac / nut "+" xuc xac / tab
    "shop": [SHOP_ROI],                 # P9-4: trong cua hang: chi nut "Mien phi" CO cham do (free_with_dot)
}
FREE_RX = r"mi\w{0,2}n ph"
PAID = re.compile(r"₫|\bd\s?\d{3}|\d{3}[.,]?\d{3}\s*(d|vnd)|250\s?000|500\s?000|1\s?250\s?000|\bmua\b|the thong hanh|san kho bau")


def tap_ok(screen, x, y):
    """Ham thuan: toa do (x, y) co nam trong vung cho phep cua man `screen` khong."""
    return any(rx <= x <= rx + rw and ry <= y <= ry + rh for rx, ry, rw, rh in ALLOW.get(screen, ()))


def paid_text(text):
    """Chu co dau hieu tra phi / vung cam (gia d250000..., 'Mua', 'The thong hanh', 'San kho bau') -> True."""
    t = buttons._norm(text)
    return bool(PAID.search(t) or PAID.search(text or "") or buttons.is_danger(t))


def _tap(ctx, screen, p, wait=1.5):
    x, y = int(p[0]), int(p[1])
    if not tap_ok(screen, x, y):
        log.warning("Su menh: cham @%d,%d ngoai vung cho phep (%s) - KHONG cham", x, y, screen)
        return False
    ctx.tap(x, y, wait=wait)
    return True


def claim_safe(ctx, screen, roi, max_taps=10):
    """Nut "Nhan" xanh (buttons.claims da loc nut tra phi) trong roi, moi nut kiem lai vung cho phep + chu."""
    n, dead = 0, set()
    for _ in range(max_taps):
        todo = [b for b in buttons.claims(ctx.shot(), roi)
                if (b.x // 20, b.y // 20) not in dead and tap_ok(screen, b.x, b.y) and not paid_text(b.text)]
        if not todo:
            break
        b = todo[0]
        dead.add((b.x // 20, b.y // 20))
        if _tap(ctx, screen, (b.x, b.y), wait=1.2):
            n += 1
            ctx.dismiss_reward()
    return n


def chest_dot(img, c):
    """P8-1: cham do cua ruong mien phi Qua ky dieu (goc tren-phai ruong). Do tren anh ADB #1 (mis2, 2026-11-24): tam
    ~81,285 khi ruong ~43,311, 17x17 px, H ~8, S 255, V 130-170 -> TOI va CAM hon cham thong bao thuong (red_dots
    H <= 6, V >= 190 khong thay). Chi xet hop canh ruong (x c..c+65, y c-50..c) de khong lay mau do cua anh nen."""
    near = any(abs(dx - c[0]) <= 60 and abs(dy - c[1]) <= 60 for dx, dy in red_dots(img, FREE_CHEST_ROI))
    if near or not isinstance(img, np.ndarray):
        return near
    x0, y0 = max(0, int(c[0])), max(0, int(c[1]) - 50)
    box = img[y0:int(c[1]), x0:x0 + 65]
    if box.size == 0:
        return False
    hsv = cv2.cvtColor(box, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (((H <= 10) | (H >= 172)) & (S >= 170) & (V >= 110)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    return any(10 <= st[k][2] <= 26 and 10 <= st[k][3] <= 26 and st[k][4] >= 0.6 * st[k][2] * st[k][3] for k in range(1, n))


def free_chest(ctx):
    """Qua ky dieu: ruong goc tren-trai co CHAM DO -> cham (mien phi) -> nhan."""
    if not tplneed.has(ctx.v, "mission/free_chest", "ruong mien phi Qua ky dieu (goc tren-trai, co dong ho)"):
        return 0
    img = ctx.shot()
    c = ctx.v.find(img, "mission/free_chest", roi=FREE_CHEST_ROI)
    if not c:
        return 0
    if not chest_dot(img, c):
        log.info("Su menh: ruong Qua ky dieu chua co cham do (chua toi gio mien phi)")
        return 0
    if not _tap(ctx, "gift", c):
        return 0
    n = claim_safe(ctx, "gift", FREE_CHEST_ROI, 2) or 1     # cham ruong thuong nhan ngay (bang thuong)
    ctx.dismiss_reward()
    log.info("Su menh: nhan ruong mien phi Qua ky dieu")
    return n


def free_with_dot(btns, dots, tol=24):
    """P9-4 (anh cua_hang_xuc_xac_mien_phi): nut "Mien phi" CO cham do o goc tren-phai (gioi han 1/1) -> duoc bam.
    Khong cham do (da nhan / het luot) -> khong bam. Ham thuan."""
    out = []
    for b in btns:
        cx, cy = b.x + b.w // 2, b.y - b.h // 2
        if any(abs(d[0] - cx) <= tol and abs(d[1] - cy) <= tol for d in dots) and not paid_text(b.text):
            out.append(b)
    return out


def dice_shop_free(ctx, max_taps=3):
    """"Cua hang xuc xac dieu khien tu xa": CHI bam nut "Mien phi" dang co cham do. Khong mua gi tra phi."""
    n = 0
    for _ in range(max_taps):
        img = ctx.shot()
        todo = free_with_dot(buttons.with_text(img, FREE_RX, SHOP_ROI), red_dots(img, SHOP_ROI))
        if not todo:
            break
        b = todo[0]
        if not _tap(ctx, "shop", (b.x, b.y), wait=1.5):
            break
        ctx.dismiss_reward()
        n += 1
        log.info("Su menh: cua hang xuc xac - nhan 'Mien phi' @%d,%d", b.x, b.y)
    return n


def cart_dot(img, c):
    """Cham do goc tren-phai icon xe day (mis1: xe 501,311 -> cham 522,288)."""
    return any(5 <= d[0] - c[0] <= 35 and -40 <= d[1] - c[1] <= -8 for d in red_dots(img, CART_ROI))


def hunt_shop(ctx):
    """P9-4 (chu du an 2026-11-24): San kho bau -> icon xe day co cham do -> cua hang xuc xac -> nut Mien phi co cham
    do. KHONG choi ban xuc xac, khong The thong hanh, khong goi tra phi."""
    if not tplneed.has(ctx.v, "mission/cart", "icon xe day cua hang xuc xac (tab San kho bau)"):
        return 0
    c = ctx.find("mission/cart", roi=CART_ROI)
    if not c:
        _tap(ctx, "hunt_nav", (75, 125), wait=2.0)      # icon su kien San kho bau (mac dinh mo tab San kho bau)
        c = ctx.find("mission/cart", roi=CART_ROI)
    if not c:
        return 0
    if not cart_dot(ctx._img if isinstance(ctx._img, np.ndarray) else ctx.shot(), c):
        log.info("Su menh: xe day cua hang xuc xac khong co cham do - bo qua")
        return 0
    if not _tap(ctx, "hunt", c, wait=2.0):
        return 0
    n = dice_shop_free(ctx)
    ctx.back_out(1)
    return n


def daily_chests(ctx):
    """P9-4: ruong moc diem (10/30/50/80/120) trong tab Nhiem vu hang ngay: bam ruong sang khi diem >= moc, lap toi het.
    Moi lan cham qua vung cho phep 'daily'."""
    from bot.modules import daily
    return daily.claim_chests(ctx, by_color=True, tap=lambda x, y: _tap(ctx, "daily", (x, y), wait=1.2))


def run(ctx):
    mc = ctx.cfg.get("mission", {})
    if not tplneed.has(ctx.v, "mission/icon", "icon Su menh ben phai man thanh pho"):
        return 0
    ctx.ensure_city()
    p = ctx.find("mission/icon", roi=ICON_ROI)
    if not p:
        log.info("Su menh: khong thay icon (su kien chua mo / da het) - bo qua")
        return 0
    ctx.tap(p[0], p[1], wait=2.0)
    n = 0
    try:
        if tplneed.has(ctx.v, "mission/title", "tieu de man Su menh") and not ctx.wait_for("mission/title", timeout=3):
            log.info("Su menh: khong mo duoc man Su menh")
            return 0
        if tplneed.has(ctx.v, "mission/tab_daily", "tab Nhiem vu hang ngay"):
            t = ctx.find("mission/tab_daily", roi=TAB_ROI)
            if t and _tap(ctx, "main", t):
                got = claim_safe(ctx, "daily", DAILY_ROI, mc.get("max_claims", 12))
                got += daily_chests(ctx)
                log.info("Su menh: tab Nhiem vu hang ngay -> nhan %d", got)
                n += got
        if mc.get("free_gift", True) and tplneed.has(ctx.v, "mission/gift_icon", "icon Qua ky dieu"):
            g = ctx.find("mission/gift_icon", roi=GIFT_ROI)
            if g and _tap(ctx, "main", g, wait=2.0):
                n += free_chest(ctx)
        if mc.get("dice_shop", True):
            n += hunt_shop(ctx)
    finally:
        ctx.back_out()
        ctx.ensure_city()
    return n
