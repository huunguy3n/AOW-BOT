"""Xu ly cac vung co cham do thong bao tren thanh pho.

Tim cham do bang mau (bot/badges.py) -> gan voi icon gan nhat -> xu ly:
  welfare/bubble (TT phuc loi) : vao tung tab co cham do, bam nut "Nhan" XANH (bo nut xam), cham the qua co
                                 cham do (Thuong online). KHONG bam: "Tiep tuc nhan"/"Mo khoa"/"Cap mua"/nap.
  activity (Hoat dong tro choi): tab co cham do -> nut "Nhan" xanh; "Dang nhap hen gio" -> mo ruong khi het dem nguoc.
  intel (Tinh bao)             : danh nhiem vu (dung nang luong tinh bao), chi khi du doan thang.
  recruit (Chieu mo)           : chi luot MIEN PHI; dung phieu chieu mo neu bat recruit.use_tickets.
  hero (Tuong)                 : tang cap tuong co mui ten xanh bang EXP khi nut con cham do.
Bo qua: chat, co lien minh (chi R4). Thu/chien dich/lien minh do cac buoc rieng xu ly.
"""
import time, logging
import cv2
import numpy as np
from bot import intel_rules as IR, ocr, screens
from bot.badges import red_dots, glow_tiles, nhan_tiles, tile_locked
from bot.modules import campaign

log = logging.getLogger("aow")
ICONS = {  # ten -> anh mau icon tren thanh pho
    "welfare": "badge/welfare", "activity": "badge/activity", "bubble": "badge/bubble",
    "intel": "badge/intel", "recruit": "badge/recruit", "hero": "badge/hero",
}
TAB_STRIP = (0, 55, 540, 140)    # hang tab trong cac trung tam (TT phuc loi / Hoat dong)
CONTENT = (0, 200, 540, 700)
CLAIM = ["daily/claim_1",         # nut "Nhan" xanh ngoc (cung kieu nhiem vu)
         "notify/btn_claim_card"]  # nut "Nhan" lon tren the (Hoat dong > Moc cay so, Ruong ngay VIP...) - 2026-11-20


# Icon co hoat anh (Tinh bao, bong bong Nhan) khong khop anh mau on dinh -> suy vi tri tu icon ben canh
ANCHORED = {"intel": ("campaign/btn_open", -2, -56), "bubble": ("badge/recruit", 103, -8)}


def badged(ctx):
    img = ctx.shot()
    dots = red_dots(img)
    out = []
    for name, tpl in ICONS.items():
        if name in ANCHORED:
            a, dx, dy = ANCHORED[name]
            q = ctx.v.find(img, a)
            p = (q[0] + dx, q[1] + dy, q[2]) if q else None
        else:
            p = ctx.v.find(img, tpl)
        if p and any(-10 < d[0] - p[0] < 60 and -60 < d[1] - p[1] < 25 for d in dots):
            out.append((name, p))
    return out


def leave(ctx):
    for _ in range(4):
        if ctx.is_home():
            return
        if not ctx.tap_first(["campaign/btn_done", "campaign/btn_done_lose", "common/btn_back2", "common/btn_back"] + ctx.POPUP_CLOSERS, wait=1.0):
            ctx.back_out(1)


# ---------- trung tam phuc loi / hoat dong ----------
def claim_scroll(ctx, pages=6):
    """Nhan het nut "Nhan" trong danh sach DAI (vd tab "Moc cay so": nhieu the, chu du an 2026-11-20 "vuot len con nua"):
    nhan trang hien tai -> vuot len -> nhan tiep, dung khi vuot khong doi man (het danh sach)."""
    from bot import screens
    n = 0
    for page in range(pages):
        n += ctx.claim_loop(CLAIM, max_taps=15, th=0.9)
        before = ctx.shot()
        ctx.dev.swipe(270, 800, 270, 360, 600)
        time.sleep(1.0)
        if screens.same(before, ctx.shot()):
            break
    return n


EPIC_SPLIT_X = 245            # TT phuc loi > Qua dang nhap: cot "Mien phi" x < 245, cot "Su thi" (tra phi) ben phai
EPIC_Y_RANGE = (360, 900)    # vung tim dau 2 cot (Mien phi tim / Su thi vang dat)


def _frac(hsv, x0, x1, y, hlo, hhi, smin, vmin):
    row = hsv[y, x0:x1]
    m = (row[:, 0] >= hlo) & (row[:, 0] <= hhi) & (row[:, 1] >= smin) & (row[:, 2] >= vmin)
    return float(m.mean())


def epic_header(img, run=60):
    """P9-3: tab Qua dang nhap co cot "Su thi" (goi tra phi ₫25000)? Nhan theo MAU (OCR khong doc duoc chu mo "Su thi"
    tren nen vang dat): cot phai vang dat (H 15-28) + cot trai tim (H 120-145) lien tuc >= `run` dong.
    -> y dong dau tien cua 2 cot | None. Ham thuan."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    y0, y1 = EPIC_Y_RANGE
    start, count = None, 0
    for y in range(y0, min(y1, img.shape[0])):
        ok = (_frac(hsv, 270, 520, y, 15, 28, 100, 90) > 0.5 and _frac(hsv, 40, 220, y, 118, 145, 80, 90) > 0.5)
        if ok:
            start = y if start is None else start
            count += 1
            if count >= run:
                return start
        else:
            start, count = None, 0
    return None


def free_column_tiles(tiles, epic_y):
    """P9-3 (chu du an 2026-11-24, anh qua_dang_nhap_mien_phi_chua_bam): co cot "Su thi" -> CHI o phat sang o cot
    "Mien phi" (x < EPIC_SPLIT_X) va duoi dau cot (khong cham banner / nut ₫25000). Khong co cot Su thi -> giu nguyen."""
    if epic_y is None:
        return list(tiles)
    return [t for t in tiles if t[0] < EPIC_SPLIT_X and t[1] > epic_y]


def claim_glow_tiles(ctx, max_taps=6):
    """O qua phat sang khong co nut "Nhan" rieng (tab "Qua dang nhap", "Chuc phuc tan thu", "Diem danh 30 ngay"):
    cham thang vao o. P9-3: chay TRUOC khi luot danh sach (Diem danh 30 ngay: bam o hao quang, KHONG luot)."""
    from bot import tapguard
    g = tapguard.of(ctx)
    n, seen = 0, set()
    for _ in range(max_taps):
        img = ctx.shot()
        # glow_tiles: vien xanh ngoc (Qua dang nhap); nhan_tiles: chu "Nhan" xanh la + vien vang (Diem danh 30 ngay)
        tiles = [t for t in glow_tiles(img) + nhan_tiles(img) if (t[0] // 30, t[1] // 30) not in seen]
        tiles = g.keep("glow", free_column_tiles(tiles, epic_header(img)))   # P12-2: o bam 2 lan van sang -> bo
        tiles = [t for t in tiles if not tile_locked(img, t[0], t[1])]       # P13-7: o co O KHOA (moc > cap) -> khong bam
        if not tiles:
            break
        x, y = tiles[0]
        seen.add((x // 30, y // 30))
        log.info("Phuc loi: o qua phat sang @%d,%d", x, y)
        ctx.tap(x, y, wait=1.2)
        # Diem danh 30 ngay: hien bang "Phan Thuong Hang Ngay" -> CHI bam "Nhan Phan Thuong Co Ban" (mien phi),
        # KHONG BAO GIO "Nang cap VIP"
        if ctx.tap_tpl("welfare/btn_basic_reward", wait=1.2, th=0.9):
            log.info("Diem danh: nhan phan thuong co ban")
        ctx.dismiss_reward()
        n += 1
        after = ctx.shot()   # o van phat sang cung cho -> cham khong co hieu ung (live4 @139,530 bam 4-5 lan)
        still = any(abs(t[0] - x) <= 15 and abs(t[1] - y) <= 15 for t in glow_tiles(after) + nhan_tiles(after))
        g.record("glow", x, y, not still, "o van phat sang")
    return n


def owner_box(img, dot):
    """P13c: tim NUT/THE that so huu cham do (cham o goc tren-phai vat do): contour canh quanh cham, lay khung NHO NHAT
    co mep phai ~ x cham, mep tren ~ y cham. -> (x, y, w, h) hoac None. Khong offset mu (live6b: (x-48,y+70) roi
    xuong khoang trong duoi nut thap 'Vao lich thi dau', thau y=964 ngoai man)."""
    import cv2
    import numpy as np
    x, y = dot
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(0, x - 340), max(0, y - 60), min(W, x + 30), min(H, y + 440)
    if x1 - x0 < 40 or y1 - y0 < 30:
        return None
    g = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    e = cv2.dilate(cv2.Canny(g, 40, 120), np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(e, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for c in cs:
        bx, by, bw, bh = cv2.boundingRect(c)
        bx, by = bx + x0, by + y0
        if bw < 36 or bh < 24 or bw > 340 or bh > 440:
            continue
        if abs(bx + bw - x) > 22 or abs(by - y) > 22:
            continue
        if best is None or bw * bh < best[2] * best[3]:
            best = (bx, by, bw, bh)
    return best


def dot_tap_points(img, dot):
    """Ham thuan P13c: diem cham cho 1 cham do = TAM vat so huu that (owner_box), da kep vao 0..539 x 0..959 va nam
    TRONG khung. Khong tim duoc vat -> [] (khong doan offset; cham do bi bo qua/danh sach den)."""
    box = owner_box(img, dot)
    if box is None:
        return []
    bx, by, bw, bh = box
    cx, cy = bx + bw // 2, by + bh // 2
    return [(min(max(cx, 0), 539), min(max(cy, 0), 959))]


def tap_red_dots(ctx, roi, scope, max_n=6):
    """Cham lan luot cac cham do trong roi. Luat chung P13b: cham 1 diem ma man khong doi (screens.same) -> thu diem
    ke tiep cua cham do do; het diem van khong doi -> DANH SACH DEN o cham do (TapGuard, het lan ghe), sang cham khac.
    Cung diem cham 2 lan khong doi cung vao danh sach den. Khong bao gio lap vo han. -> so cham do co hieu ung."""
    from bot import tapguard
    g = tapguard.of(ctx)
    n, done = 0, set()
    for _ in range(max_n):
        dots = [d for d in g.keep(scope, red_dots(ctx.shot(), roi)) if (d[0] // 30, d[1] // 30) not in done]
        if not dots:
            break
        d = dots[0]
        done.add((d[0] // 30, d[1] // 30))
        moved = False
        shot0 = ctx.shot()
        for (x, y) in dot_tap_points(shot0, d):
            if g.blocked("tap", x, y):
                continue
            before = shot0
            ctx.tap(x, y, wait=1.2)
            if not screens.same(before, ctx.shot()):
                g.record("tap", x, y, True)
                moved = True
                break
            g.record("tap", x, y, False, "cham man khong doi")
        if not moved:
            g.black[g.key(scope, d[0], d[1])] = "cham do: khong tim thay nut that hoac cham khong doi man"
            log.info("Cham do @%d,%d: cham khong doi man -> danh sach den, sang cho khac", d[0], d[1])
            continue
        ctx.dismiss_reward()
        n += 1
    return n


def claim_content(ctx, cards=False, gift=True):
    n = claim_glow_tiles(ctx)          # P9-3: o phat sang truoc (khong luot), roi moi nut Nhan + luot danh sach
    n += claim_scroll(ctx)
    if cards:  # the qua co cham do (vd Thuong online 100/120 phut): cham giua the
        n += tap_red_dots(ctx, CONTENT, "card", max_n=6)
    if ctx.find("event/timed_login"):
        # "Dang nhap hen gio": "Dem nguoc nhan" = thoi gian CON LAI de nhan (khung 8-9h, 18-19h UTC).
        # Tab chi duoc vao khi co cham do (= dang nhan duoc) -> cham vao ruong.
        ctx.tap(285, 500, wait=1.5)
        ctx.dismiss_reward()
        n += 1
    if gift:   # tab 'Chieu mo han gio': icon "Qua Chieu Mo" (cot phai) co cham do (chu du an 2026-11-22: 'bam vao day')
        n += recruit_gift(ctx, ctx.shot())
    return n


def in_alliance(ctx, img=None):
    """Dang trong bang Lien minh (tieu de "Lien minh")? Chu du an 2026-11-21: tab Lanh tho co nut "Den" mang cham do
    (TT Thu Thanh, Co lien minh) -> KHONG duoc cham (di chuyen quan / bay toi cho khac)."""
    img = ctx.shot() if img is None else img
    return bool(ctx.v.find(img, "ally/title", th=0.75, roi=(80, 0, 200, 70)))


def hub(ctx, cards):
    total = 0
    if in_alliance(ctx):
        log.info("Bang Lien minh: khong quet cham do kieu trung tam (tab Lanh tho co nut Den) - de buoc alliance lam")
        return 0
    # icon LICH (goc phai tren, Hoat dong tro choi) co cham do = co muc moi -> mo 1 lan cho het cham, dong lai
    img = ctx.shot()
    cal = ctx.v.find(img, "common/btn_calendar", th=0.9)
    if cal and _dot_near(img, cal, dx=18, dy=-13, tol=(10, 10)):
        ctx.tap(cal[0], cal[1], wait=1.5)
        ctx.tap_first(["common/btn_close", "common/btn_x"], wait=1.0)
        log.info("Hoat dong: xem lich tuan (xoa cham do)")
    for page in range(3):
        visits = {}
        for _ in range(12):
            # P9-3: tab con cham do sau khi nhan (con muc khac) -> vao LAI (toi da TAB_REVISIT lan, chi khi lan truoc
            # nhan duoc gi); truoc day moi tab chi vao 1 lan ("chi bam 1 cham do roi bo di", live-run-2)
            dots = [d for d in red_dots(ctx.shot(), TAB_STRIP) if tab_open_again(visits.get(d[0] // 40))]
            if not dots:
                break
            x, y = dots[0]
            ctx.tap(x - 30, y + 40, wait=1.5)   # cham icon tab (cham do o goc tren-phai)
            got = claim_content(ctx, cards)
            if not cards:                       # Hoat dong: o/the co cham do trong tab -> chi nhan bang "Nhan"
                got += event_tiles(ctx, max_taps=8)
            k = x // 40
            visits[k] = (visits.get(k, (0, 0))[0] + 1, got)
            total += got
        ctx.dev.swipe(460, 120, 120, 120, 500)  # cuon hang tab sang phai
        time.sleep(1.0)
    return total


TAB_REVISIT = 3


def tab_open_again(visit):
    """visit = (so lan da vao, so nhan duoc lan cuoi) | None. Chua vao -> vao; lan truoc nhan duoc va chua qua
    TAB_REVISIT lan -> vao lai; lan truoc 0 -> thoi (cham do khong xu ly an toan duoc)."""
    if visit is None:
        return True
    n, last = visit
    return last > 0 and n < TAB_REVISIT


TIMED_CHEST = (285, 500)   # ruong "Dang nhap hen gio" giua tab (giong claim_content)


def timed_login_chest(ctx, pages=3):
    """P8-3: luot ghe trong khung "Dang nhap hen gio" -> nhan ruong 5 the luc DAU TIEN (truoc moi buoc khac).
    Thanh pho -> icon Hoat dong tro choi (badge/activity) -> chi cham cac tab CO CHAM DO, tab nao hien ruong
    (event/timed_login) thi cham ruong + dong thuong, KHONG nhan cac tab khac (de notify lam sau neu con thoi gian).
    -> 1 da nhan | 0 khong thay (chua toi gio / da nhan / thieu anh mau)."""
    if not (ctx.v.has("badge/activity") and ctx.v.has("event/timed_login")):
        log.info("Dang nhap hen gio: thieu anh mau badge/activity hoac event/timed_login - de notify lam")
        return 0
    ctx.ensure_city()
    p = ctx.find("badge/activity")
    if not p:
        log.info("Dang nhap hen gio: khong thay icon Hoat dong")
        return 0
    ctx.tap(p[0], p[1], wait=2.5)
    try:
        for page in range(pages):
            tried = set()
            for _ in range(8):
                if ctx.find("event/timed_login"):
                    ctx.tap(TIMED_CHEST[0], TIMED_CHEST[1], wait=1.5)
                    ctx.dismiss_reward()
                    log.info("Dang nhap hen gio: da nhan ruong the luc")
                    return 1
                dots = [d for d in red_dots(ctx.shot(), TAB_STRIP) if (d[0] // 40) not in tried]
                if not dots:
                    break
                x, y = dots[0]
                tried.add(x // 40)
                ctx.tap(x - 30, y + 40, wait=1.5)
            if page + 1 < pages:
                ctx.dev.swipe(460, 120, 120, 120, 500)   # cuon hang tab sang phai
                time.sleep(1.0)
        log.info("Dang nhap hen gio: khong thay ruong (chua toi gio / da nhan)")
        return 0
    finally:
        leave(ctx)


# ---------- tinh bao ----------
ENERGY_ROI =(440, 22, 52, 22)   # nang luong tinh bao (goc phai tren man Tinh bao)
INTEL_COST = 5


def energy(ctx):
    t = ocr.text(ctx.shot(), ENERGY_ROI, "0123456789")
    return int(t) if t.isdigit() else None


def refill_energy(ctx, need=INTEL_COST, force=False):
    """Thieu nang luong tinh bao -> dung Thuoc The Luc TUNG VIEN (nut 'Dung') toi khi du `need`.
    KHONG BAO GIO bam 'Mua' (kim cuong). Tran: notify.intel_max_potions vien / luot (dem trong ctx).
    force=True: doc khong ra nang luong ma nhiem vu vua that bai -> van thu 1 vien."""
    nc = ctx.cfg.get("notify", {})
    if not nc.get("intel_use_potions", True):
        return False
    cap = nc.get("intel_max_potions", 20)
    e = energy(ctx)
    if e is not None and e >= need:
        return True
    if e is None and not force:
        return False
    used = 0
    while getattr(ctx, "_potions", 0) < cap:
        if not ctx.tap_tpl("intel/btn_energy_plus", wait=1.5) or not ctx.wait_for("intel/potion_title", timeout=3):
            break
        if not use_potion10(ctx):
            log.info("Het thuoc the luc")
            ctx.tap_first(ctx.POPUP_CLOSERS, wait=1.0)
            break
        ctx._potions = getattr(ctx, "_potions", 0) + 1
        used += 1
        ctx.dismiss_reward()
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=1.0)      # dong bang thuoc de doc lai nang luong
        e2 = energy(ctx)
        if (e2 is not None and e2 >= need) or (e2 is None and force):
            break
    log.info("Dung %d thuoc the luc (luot nay %d/%d), nang luong %s -> %s", used, getattr(ctx, "_potions", 0), cap, e, energy(ctx))
    return used > 0


def use_potion10(ctx):
    """P7-4: bang "Thuoc The Luc" -> nut "Dung" o hang binh 10 diem (intel/potion_10). KHONG BAO GIO bam "Mua"
    (nut Dung khop trung vi tri nut Mua intel/btn_buy_potion bi loai). Thieu anh binh 10 -> nut Dung tren cung (cu)."""
    from bot import tplneed
    img = ctx.shot()
    uses = ctx.v.find_all(img, "intel/btn_use_potion")
    buys = ctx.v.find_all(img, "intel/btn_buy_potion") if tplneed.has(ctx.v, "intel/btn_buy_potion", "nut Mua bang thuoc") else []
    row = ctx.v.find(img, "intel/potion_10") if tplneed.has(ctx.v, "intel/potion_10", "binh the luc 10 diem") else None
    p = IR.pick_use_button(uses, row, buys)
    if not p:
        return False
    ctx.tap(p[0], p[1], wait=1.2)
    return True


def done_ticks(img, roi=(0, 90, 540, 770)):
    """Dau tick XANH LA SANG tren ghim tinh bao = nhiem vu da xong, cho nhan. Do 2026-11-20 (anh chu du an):
    H 67-70, S ~207, V ~222, net dai ~25x22 px dien tich ~150; nen ban do xanh toi (S 84-124). -> [(x, y)] tam."""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 60) & (hsv[..., 0] <= 78) & (hsv[..., 1] >= 170) & (hsv[..., 2] >= 190)).astype("uint8")
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    small = [st[k] for k in range(1, n) if 4 <= st[k][2] <= 14 and 4 <= st[k][3] <= 12 and 20 <= st[k][4] <= 70]
    out = []
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if 18 <= w <= 35 and 15 <= h <= 30 and 100 <= a <= 260:
            # hinh dau tick: net NGAN ben trai-duoi net dai (vd net dai 257,306 / net ngan 249,314)
            if any(x - 14 <= sx <= x and y + 2 <= sy <= y + 16 for sx, sy, _, _, _ in small):
                out.append((int(x0 + x + w // 2), int(y0 + y + h // 2)))
    return sorted(out, key=lambda p: p[1])


def crate_pin(ctx, img, p):
    """Ghim HOP TIEP TE (xanh, icon hop): mau intel/crate_pin (cat tu anh chu du an 2026-11-22) nam tren vong pin_base. #1 chi lam
    ghim vang/tim nen ghim hop xanh bi bo ('chua lam xong cac muc do')."""
    x, y = int(p[0]), int(p[1])
    for n in ("intel/crate_pin", "intel/crate_pin_world"):
        b = ctx.v.best(img, n, roi=(max(0, x - 40), max(0, y - 90), 80, 90))
        if b and b[2] >= 0.7:
            return True
    return False


def pin_gold(img, x, y):
    """Ghim tinh bao DAC BIET (VANG hoac TIM dau lau) hay XANH thuong: mau trung vi dau ghim (tren vong pin_base
    25-60 px). Do #1 2026-11-21: vang H ~20, tim H ~137, xanh H ~103."""
    hsv = cv2.cvtColor(img[max(0, y - 60):max(1, y - 25), max(0, x - 14):x + 14], cv2.COLOR_BGR2HSV).reshape(-1, 3)
    hsv = hsv[hsv[:, 1] > 90]
    if len(hsv) < 50:
        return False
    h = float(np.median(hsv[:, 0]))
    return 8 <= h <= 35 or 125 <= h <= 155


def special_pins(img, roi=(0, 90, 540, 760)):
    """Dau ghim VANG / TIM (giot nuoc co icon trang) theo mau - khong can vong pin_base (bi linh/xe che, anh #1
    2026-11-21 ghim tim dau lau). Ghim ~43-67 x 55-70 px. Ruong lua mi vang (khong icon trang) bi loai. -> [(x, y)]"""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = ((((H >= 10) & (H <= 30)) | ((H >= 125) & (H <= 155))) & (S >= 120) & (V >= 110)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    white = (S < 70) & (V > 200)
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if (32 <= w <= 80 and 32 <= h <= 95 and 0.6 <= w / h <= 1.3 and a >= 0.35 * w * h
                and white[y:y + h, x:x + w].sum() >= 100):
            out.append((int(x + w // 2) + x0, int(y + h // 2) + y0))
    return out


def _pickups(ctx):
    """P7-4: hop qua tinh bao dang nhat (toi da 2 cung luc) - song qua 1 lan ghe (ctx)."""
    pk = getattr(ctx, "_intel_pickups", None)
    if pk is None:
        nc = ctx.cfg.get("notify", {})
        pk = ctx._intel_pickups = IR.Pickups(nc.get("intel_pickup_max", IR.PICKUP_MAX), nc.get("intel_pickup_s", IR.PICKUP_S))
    return pk


def open_intel(ctx, allow_city=True):
    """P9-9 (anh tinh_bao_tu_world_map): icon Tinh bao (ngay tren icon Chien dich) co ca tren BAN DO THE GIOI -> bam
    tu man hien tai (thanh pho hoac the gioi), chi ve thanh pho khi khong thay. -> True neu da bam.
    P13-5: allow_city False -> khong ve thanh pho (chi dong popup roi tim lai icon) - tranh ra/vao thanh pho lap lai."""
    q = ctx.find("campaign/btn_open")
    if not q and not allow_city:
        ctx.close_popups()
        q = ctx.find("campaign/btn_open")
    elif not q:
        ctx.ensure_city()
        q = ctx.find("campaign/btn_open")
    if not q:
        return False
    ctx.tap(q[0] - 2, q[1] - 56, wait=2.0)
    return True


def intel(ctx, max_n):
    nc = ctx.cfg.get("notify", {})
    only_gold = nc.get("intel_only_gold", False)   # #1 (TK chinh): chi lam ghim vang
    done = 0
    tried = set()
    done_keys = set()           # P7-4: ghim lam xong (tran thang / nhat) -> o quet lai co the la diem MOI
    rescans, done_scan = 0, 0
    city_trips = 0              # P13-5: ve thanh pho TOI DA 1 lan trong buoc (khi khong con cach nao thay icon Tinh bao)
    for _ in range(max_n):
        if not ctx.find("intel/title"):
            if not ctx.find("campaign/btn_open"):
                city_trips += 1         # icon khong thay tren man nay -> open_intel co the phai ve thanh pho (lan thu may)
            if not open_intel(ctx, allow_city=city_trips <= 1):
                break
        # nhiem vu da xong (dau tick xanh tren ghim) -> cham ghim de nhan thuong. Nhan theo MAU (anh mau cu chi khop
        # 0.61, chu du an 2026-11-20 "nhan het cac hop qua co tick v"); chup lai sau moi lan nhan (ghim bien mat)
        claimed = set()
        for _ in range(12):
            ticks = [t for t in done_ticks(ctx.shot()) if (t[0] // 25, t[1] // 25) not in claimed]
            if not ticks:
                break
            x, y = ticks[0]
            claimed.add((x // 25, y // 25))
            ctx.tap(x - 20, y + 18, wait=1.5)       # than ghim nam duoi-trai dau tick
            ctx.dismiss_reward()
            done += 1
            done_scan += 1
            freed = _pickups(ctx).done((x, y))      # P9-9: chi giai phong hop nhat tai ghim nay
            log.info("Tinh bao: nhan hop qua da xong @%d,%d%s", x, y, " (giai phong 1 cho nhat hop)" if freed else "")
        img = ctx.shot()
        pins = [p for p in ctx.v.find_all(img, "intel/pin_base", th=0.6, min_dist=15)  # vong mo, chong nhau
                if (p[0] // 20, p[1] // 20) not in tried]
        if only_gold:   # chu du an 2026-11-21: "#1 chi lam mau vang" + "nhan them mau tim dau lau"
            pins = [p for p in pins if pin_gold(img, p[0], p[1]) or crate_pin(ctx, img, p)]   # + ghim hop tiep te (xanh)
            for sx, sy in special_pins(img):            # ghim mat vong (bi che) -> them theo mau dau ghim
                if all(abs(sx - p[0]) > 30 or abs(sy + 35 - p[1]) > 40 for p in pins)                         and (sx // 20, (sy + 35) // 20) not in tried:
                    pins.append((sx, sy + 35, 1.0))     # quy uoc ghim = vong, cham tai y - 35 = dau ghim
        if not pins:
            # P7-4: hoan thanh tinh bao co the sinh diem moi -> quet lai (cho diem hien) toi khi khong con diem
            if IR.should_rescan(done_scan, rescans, nc.get("intel_rescans", 3)):
                rescans, done_scan = rescans + 1, 0
                tried -= done_keys
                done_keys.clear()
                log.info("Tinh bao: quet lai ban do lan %d (vua lam xong nhiem vu, co the co diem moi)", rescans)
                time.sleep(nc.get("intel_rescan_wait_s", 3))
                continue
            break
        e = energy(ctx)
        if e is not None and e < INTEL_COST and not refill_energy(ctx):
            log.info("Het nang luong tinh bao (%s) va khong con thuoc", e)
            break
        x, y, _ = pins[0]
        tried.add((x // 20, y // 20))
        ctx._intel_pin = (x, y - 35)               # P9-9: pickup() nho vi tri ghim hop
        ctx.tap(x, y - 35, wait=1.5)               # ghim (hinh giot nuoc) nam tren vong tron
        r = intel_mission(ctx)
        log.info("Tinh bao: %s", r)
        if r in IR.DONE:
            done += 1
            done_scan += 1
            if r != "marched":          # quan doan dang di -> ghim con tren ban do toi khi xong
                done_keys.add((x // 20, y // 20))
        if r in IR.STOP:
            break
        if r in IR.SKIP:
            if not ctx.find("intel/title"):
                ctx.close_popups()      # P13-5: o lai ban do, vong sau mo lai bang tinh bao (khong ensure_city)
            continue
        # P5-1: chi khi BANG NHIEM VU khong hien (co the la bang thieu nang luong) moi thu 1 vien thuoc; truoc day moi
        # 'unknown' (ke ca nhan nham muc tieu tren ban do) deu ep dung thuoc
        if r == IR.UNKNOWN_PANEL and energy(ctx) is None and not refill_energy(ctx, force=True):
            break       # co the thieu nang luong ma khong doc duoc so -> thu 1 vien, het thuoc thi dung
        if not ctx.find("intel/title"):
            ctx.close_popups()          # P13-5: khong ensure_city o giua buoc
    return done


def rebels_pin(ctx):
    """Ghim tinh bao Phan quan Co giap: popup "Tap ket tan cong" -> quan doan xuat chinh (cung luong voi buoc phan quan, khong ghi
    cap 'best'). Het quan doan / thua du doan -> bo ghim nay."""
    from bot.modules import rebels
    if ctx.march_full():
        log.info("Tinh bao: het quan doan ranh -> khong tap ket phan quan")
        ctx.back_out()
        return "no_march"
    rc = ctx.cfg.get("rebels", {})
    if not rebels.intel_rally_ok(getattr(ctx, "mem", None), ctx.dev.idx, rc):
        log.info("Tinh bao: ghim Phan quan - nha chinh < rebels.intel_rally_min_hq (%s) -> bo", rc.get("intel_rally_min_hq"))
        ctx.back_out()
        return "skipped"
    img = ctx.shot()
    title = ctx.v.find(img, "rebels/popup_title", th=0.8)
    lv = rebels.popup_level(img, title) if title else None
    _, rec = rebels._mem(ctx)
    if lv is None or not rebels.target_ok({"fail": rec.get("fail", {})}, lv, rc.get("fail_h", 12)):
        log.info("Tinh bao: ghim Phan quan Lv.%s - bo (doc cap khong ra / vua du doan thua)", lv)
        ctx.back_out()
        return "skipped"
    r = rebels.launch_rally(ctx, rc, rec, lv, record=False)
    return "marched" if r == 1 else "skipped"


def _intel_unknown(ctx, why):
    """P5-1: 'unknown' co ly do + 1 anh/ngay/may (logs/inv/intel_<ly do>/) - khong qua save_debug (khong doi ket qua
    buoc, khong lam ngap logs/shots)."""
    from bot import build
    build.inv_capture(ctx, "intel_" + why)
    return why


def wait_panel(ctx, timeout=IR.INTEL_PANEL_WAIT_S, interval=0.5):
    """Cho bang sau khi cham ghim: 'go' | 'reward' | None (het gio). Bang qua hien kem hieu ung -> 1 khung la khong du."""
    t0 = time.time()
    while True:
        k = IR.panel_kind(ctx.shot(), ctx.v)
        if k or time.time() - t0 >= timeout:
            return k
        time.sleep(interval)


def legion_march(ctx):
    """P5-1: man "Cai dat Quan doan" kieu moi (nut Xuat chinh co dong ho, rebels/btn_march_out - may #1) sau "Tan cong".
    Chi Xuat chinh khi du doan "Thang toan dien" (chu xanh, rebels.pred_win) - cung luat phan quan; khong thi bo ghim."""
    from bot.modules import rebels
    if ctx.march_full():
        log.info("Tinh bao: het quan doan ranh -> khong hanh quan")
        ctx.back_out()
        return "no_march"
    if not rebels.pred_win(ctx.shot()):
        log.info("Tinh bao: man quan doan khong du doan thang -> bo ghim")
        ctx.back_out()
        return "lose_pred"
    if not ctx.find("rebels/btn_march_out"):
        ctx.back_out()
        return _intel_unknown(ctx, IR.UNKNOWN_AFTER)
    return confirm_departure(ctx, "rebels/btn_march_out")


def _marches(ctx):
    try:
        return ctx.read_marches()
    except Exception:
        return None


def confirm_departure(ctx, btn, tries=2, ok="marched"):
    """P7-4 (live #1: quan doan khong di chuyen): bam nut xuat phat roi KIEM quan doan that su di - nut da bien mat
    va (neu doc duoc) 'Hanh quan x/y' tang. Khong di -> bam lai 1 lan; van khong -> log loi + anh, 'not_departed'."""
    before = _marches(ctx)
    for k in range(tries):
        if not ctx.tap_tpl(btn, wait=2.0):
            if k == 0:
                ctx.back_out()
                return _intel_unknown(ctx, IR.UNKNOWN_AFTER)
        gone = not ctx.find(btn)
        if IR.departed(before, _marches(ctx) if gone else None, gone):
            if ok == "marched":
                ctx.march_sent()
            return ok
        log.info("Tinh bao: bam %s nhung quan doan chua di (lan %d/%d)", btn.split("/")[-1], k + 1, tries)
    log.warning("Tinh bao: quan doan KHONG xuat phat sau %d lan bam %s", tries, btn)
    ctx.back_out()
    return _intel_unknown(ctx, IR.NOT_DEPARTED)


def pickup(ctx):
    """P7-4: hop qua / tiep te tinh bao (moi mau): toi da intel_pickup_max hop dang nhat; day -> cho toi da
    intel_pickup_wait_max_s giay roi moi nhat tiep, van day -> bo ghim (lan sau). Kiem don vi that su di."""
    pk = _pickups(ctx)
    w = pk.wait_s(time.time())
    if w > 0:
        cap = ctx.cfg.get("notify", {}).get("intel_pickup_wait_max_s", 120)
        if w > cap:
            log.info("Tinh bao: dang nhat %d hop (toi da) - con %.0f s, bo ghim nay", len(pk.until), w)
            ctx.back_out()
            return IR.PICKUP_BUSY
        log.info("Tinh bao: dang nhat %d hop (toi da) - cho %.0f s", len(pk.until), w)
        time.sleep(w)
    r = confirm_departure(ctx, "intel/btn_pickup", ok="picked")
    if r == "picked":
        pk.add(time.time(), getattr(ctx, "_intel_pin", None))
    return r


def intel_mission(ctx):
    """Dang mo bang nhiem vu tinh bao -> 'win'|'lose'|'marched'|'picked'|'no_march'|'skipped'|'lose_pred'|'unknown_*'."""
    kind = wait_panel(ctx)
    if kind == "reward":
        # ghim HOP QUA: cham la hien ngay bang "Chuc mung nhan duoc" (khong co nut "Di"). P5-1: 11/11 anh
        # intel_panel_unknown 22/11 la bang nay - truoc day chi xet 1 khung luc bang con dang hien -> 'unknown'
        ctx.dismiss_reward()
        return "picked"
    if kind != "go" or not ctx.tap_tpl("intel/btn_go", wait=3.0):
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
        return _intel_unknown(ctx, IR.UNKNOWN_PANEL)
    if not (ctx.wait_for("intel/btn_attack", timeout=2) or ctx.find("intel/btn_pickup", fresh=False)
            or ctx.find("rebels/btn_rally", fresh=False)):
        # muc tieu tren ban do the gioi: ghim xanh (dau sung cheo) giua man, muc tieu ngay duoi ghim.
        # Anh chu du an 2026-11-20: ghim ~263,363 (truoc do do ~267,388). P5-1: chi tim ghim GIUA MAN (MARKER_ROI) -
        # tim ca man voi nguong 0,55 khop nham goc trai duoi (cham 97,805, nhat ky cham 22/11)
        time.sleep(1.5)                                   # ban do con dang truot toi muc tieu
        img = ctx.shot()
        m = ctx.v.find(img, "intel/marker_fight", th=IR.MARKER_TH, roi=IR.MARKER_ROI)
        # ghim tim/vang dau lau tren ban do (#1 2026-11-21) -> muc tieu ngay duoi ghim; lay ghim gan giua man nhat
        sp = sorted(special_pins(img), key=lambda p: abs(p[0] - 270) + abs(p[1] - 400))[:1]
        spots = ([(m[0] + 5, m[1] + 45), (m[0], m[1])] if m else []) + [(x, y + 45) for x, y in sp]             + [(268, 405), (268, 438), (265, 365)]
        for x, y in spots:
            ctx.tap(x, y, wait=1.5)
            img = ctx.shot()
            if any(ctx.v.find(img, n) for n in ("intel/btn_attack", "intel/btn_pickup", "rebels/btn_rally")):
                break
    if ctx.find("intel/btn_pickup"):     # Tiep te vat tu / hop qua: don vi tinh bao rieng, khong ton doi (P7-4: toi da 2)
        return pickup(ctx)
    if not ctx.tap_tpl("intel/btn_attack", wait=2.5):
        if ctx.find("rebels/btn_rally", fresh=False):   # ghim Phan quan Co giap: chi co "Tap ket tan cong" (chu du an 2026-11-22)
            return rebels_pin(ctx)
        ctx.back_out()
        return _intel_unknown(ctx, IR.UNKNOWN_TARGET)
    # man doi hinh / bang hanh quan len cham: #0 2026-11-22 (anh 0015 -> 0016) mat ~4 s sau khi bam "Tan cong"; wait_scale 0,55
    # rut cho con ~1,4 s -> khong thay nut Chien dau -> back_out -> 'unknown' (moi ghim kiem deu 'unknown')
    for _ in range(14):
        img = ctx.shot()
        if any(ctx.v.find(img, n) for n in ("campaign/btn_fight", "gather/btn_march", "rebels/btn_march_out")):
            break
        time.sleep(0.7)
    if ctx.find("campaign/btn_fight", fresh=False):  # Chien dich Tuong: tran tu danh
        return campaign.battle(ctx)
    if ctx.find("gather/btn_march", fresh=False):   # Quet sach phan quan: hanh quan that tren ban do
        if ctx.march_full():
            log.info("Tinh bao: het quan doan ranh -> khong hanh quan")
            ctx.back_out()
            return "no_march"
        ctx.tap_tpl("gather/btn_recommended", wait=1.0)
        return confirm_departure(ctx, "gather/btn_march")
    if ctx.find("rebels/btn_march_out", fresh=False):   # P5-1: man quan doan kieu moi (#1)
        return legion_march(ctx)
    ctx.back_out()
    return _intel_unknown(ctx, IR.UNKNOWN_AFTER)


# ---------- chieu mo ----------
def recruit_choice(free_ok, ten_dot, one_free, free_wait, use_tickets):
    """Chon nut chieu mo (ham thuan). -> 'free' | 'ten' | 'one_free' | 'one_ticket' | None.
    A-SAFE-4: nut '1 lan' chi coi la mien phi khi co BANG CHUNG (cham do o goc nut, nhu nut 'Mien phi');
    truoc day chi can KHONG thay dong ho 'free_wait' la bam -> mau khop truot thi co the tieu phieu."""
    if free_ok:
        return "free"
    if ten_dot:
        return "ten"            # chu du an 2026-11-18: cham do o '10 lan' = du phieu -> duoc dung phieu
    if one_free and not free_wait:
        return "one_free"
    if use_tickets:
        return "one_ticket"
    return None


def _gift_free(ctx, max_taps=4):
    """Bang 'Qua chieu mo han gio': nut 'Mien phi' (cham do o goc tren-phai nut, anh #4 2026-11-22) -> bam. Goi co gia kim
    cuong KHONG co cham do va khong bam; them kiem chu 'Mien phi' bang OCR cho chac (ADR-0008)."""
    from bot import buttons
    n, seen = 0, set()
    for _ in range(max_taps):
        img = ctx.shot()
        dots = [d for d in red_dots(img, (300, 60, 240, 840)) if (d[0] // 30, d[1] // 30) not in seen]
        log.info("Qua chieu mo: %d cham do", len(dots))
        if not dots:
            break
        d = dots[0]
        seen.add((d[0] // 30, d[1] // 30))
        t = buttons._norm(ocr.text(img, (max(0, d[0] - 105), d[1] - 5, 125, 45), scale=3, psm=7, bright=170))
        log.info("Qua chieu mo: cham do @%d,%d chu %r", d[0], d[1], t)
        if "phi" not in t or "mi" not in t:
            continue
        ctx.tap(d[0] - 47, d[1] + 18, wait=1.5)
        ctx.dismiss_reward()
        n += 1
        log.info("Qua chieu mo: nhan 'Mien phi' @%d,%d", d[0], d[1])
    return n


def recruit_gift(ctx, img):
    """Icon "Qua Chieu Mo" (cot phai man Tuyen dung han che, ~495,380) co cham do -> bam, nhan qua (chu du an
    2026-11-22: 'bam vao day'). Qua mien phi, khong tieu kim cuong. -> so lan nhan."""
    dots = [d for d in red_dots(img) if 450 < d[0] < 535 and 330 < d[1] < 410]
    if not dots:
        return 0
    # cham do o goc TREN-PHAI icon (anh #4 2026-11-22: cham do 510,370, icon 470-518) -> tam icon o trai-duoi.
    # Truoc day +15 chạm ra ngoai mep phai icon nen bang qua khong bao gio mo (nhan 0).
    ctx.tap(dots[0][0] - 17, dots[0][1] + 15, wait=2.0)
    ctx.save_debug("recruit_gift")          # anh bang qua de doi chieu / cat mau nut Nhan neu can
    got = _gift_free(ctx)   # truoc: claim_content cuon danh sach nen nut 'Mien phi' o dau danh sach bi troi mat
    got += (claim_content(ctx, gift=False) or 0) + ctx.claim_buttons()   # claim_buttons: nut "Mien phi" xanh (khong bam nut co gia kim cuong)
    log.info("Chieu mo: Qua Chieu Mo - nhan %s", got)
    for _ in range(3):                      # ve man Tuyen dung
        if ctx.find("recruit/title"):
            break
        ctx.back_out(1)
    return got


RECRUIT_LABEL = {"free": "1 lan (mien phi)", "ten": "10 lan (phieu)", "one_free": "1 lan (mien phi, cham do)",
                 "one_ticket": "1 lan (phieu)"}


RECRUIT_TABS = ("recruit/tab_premium", "recruit/tab_normal")
RECRUIT_TAB_DOT = (87, -84)        # cham do goc tren-phai the tab (live3 recruit_dot_left: tab thuong 385,927 -> 472,843)
FREE_BTN_ROI = (60, 690, 200, 70)  # nut trai "Mien phi" (teal, live3 recruit_dot_left 78-236 x 698-748)


def recruit_tab_dot(img, tab_pos, dots):
    """Ham thuan: the tab o `tab_pos` co cham do goc tren-phai? tab_pos None -> None (khong biet)."""
    if not tab_pos:
        return None
    dx, dy = RECRUIT_TAB_DOT
    return any(abs(d[0] - tab_pos[0] - dx) < 35 and abs(d[1] - tab_pos[1] - dy) < 30 for d in dots)


def _free_by_text(img):
    """P10-2: du phong khi anh mau recruit/btn_free khong khop - nut teal co chu 'Mien phi' o vung nut trai. -> (x, y)."""
    from bot import buttons
    for b in buttons.with_text(img, r"mi\w{0,2}n\s*ph", FREE_BTN_ROI):
        return b.x, b.y
    return None


def _recruit_once(ctx, tab, use_tickets):
    """1 lan bam o tab dang mo (cham do: Mien phi / 10 lan co cham do / Qua Chieu Mo). -> 1 neu bam duoc, 0 neu het."""
    # doi the chieu mo truot xong: chup khi chua yen thi nut chua khop -> bo qua luot mien phi
    # (#0 2026-11-20: nut "Mien phi" co cham do o tab Chieu mo thuong ma bot nhan 0)
    for _ in range(6):                  # P10-2: the truot sau khi doi tab -> cho yen (6 lan) roi moi quyet dinh
        img = ctx.shot()
        ten = ctx.v.find(img, "recruit/btn_ten")
        free = ctx.v.find(img, "recruit/btn_free", th=0.85)
        if (ten or free) and screens.same(img, ctx.shot()):
            break
        time.sleep(1.0)
    if not free:
        ft = _free_by_text(img)
        free = (ft[0], ft[1], 1.0) if ft else None       # tam nut theo chu (tap = free.y)
    if recruit_gift(ctx, img):
        return 1
    # nut "Mien phi" (luot mien phi trong ngay, nut trai) -> uu tien (do #5 2026-11-18: truoc day bi bo sot);
    # nut co cham do goc tren-phai (~+80,-23) cung tinh la mien phi du mau nut lech
    one = ctx.v.find(img, "recruit/btn_one")
    pick = recruit_choice(
        free_ok=bool(free and (ctx.is_colored(img, free[0], free[1]) or _dot_near(img, free, dx=80, dy=-23))),
        # "Chieu mo 10 lan" co cham do = du >= 10 phieu -> bam (dung phieu, khong phai kim cuong)
        ten_dot=bool(ten and any(ten[0] < d[0] < ten[0] + 110 and ten[1] - 25 < d[1] < ten[1] + 15
                                 for d in red_dots(img))),
        one_free=bool(one and _dot_near(img, one, dx=80, dy=-23)),
        free_wait=bool(ctx.v.find(img, "recruit/free_wait")),
        use_tickets=use_tickets)
    btn = {"free": free and (free[0], free[1] - 9), "ten": ten}.get(pick, one) if pick else None
    if not btn:
        return 0
    ctx.tap(btn[0], btn[1] + 9, wait=4.0)
    log.info("Chieu mo %s: %s", tab.split("_")[-1], RECRUIT_LABEL[pick])
    # man ket qua co nut "Chieu mo X1/X10" (KHONG bam lai - het phieu se hoi mua bang kim cuong) -> dong X
    for _ in range(4):
        if ctx.find("recruit/title"):
            break
        if ctx.tap_first(["common/btn_close"] + ctx.POPUP_CLOSERS, wait=1.5) is None:
            ctx.back_out(1)
    return 1


def recruit(ctx):
    """P9-3 (chu du an 2026-11-24): bam HET cham do o tab hien tai roi moi chuyen giua Chieu mo cao cap / thuong; lap toi
    khi ca vong khong con gi (live-run-2: moi tab bam 1 lan roi bo di)."""
    from bot import claimloop
    use_tickets = ctx.cfg.get("recruit", {}).get("use_tickets", False)
    rc = ctx.cfg.get("recruit", {})
    def has_dot(tab):
        img = ctx.shot()
        p = ctx.v.find(img, tab, th=0.85)
        return recruit_tab_dot(img, p, red_dots(img))

    # P10-2: tab HIEN TAI truoc (live3: mo san tab thuong co "Mien phi" ma bot sang cao cap truoc), roi tab con cham do
    n, book = claimloop.current_then_tabs(
        RECRUIT_TABS, lambda tab: ctx.tap_tpl(tab, wait=2.0), lambda tab: _recruit_once(ctx, tab, use_tickets),
        has_dot, max_per_tab=rc.get("max_per_tab", 6), max_rounds=rc.get("max_rounds", 3))
    if n:
        log.info("Chieu mo: %d lan (%s)", n, ", ".join(f"{t.split('_')[-1]} {k}" for t, k in book if k))
    if not n and ctx.find("recruit/title"):
        ctx.save_debug("recruit_dot_left")     # vao chieu mo vi cham do ma khong bam duoc gi -> luu anh de doi chieu
        log.info("Chieu mo: co cham do nhung khong thay luot mien phi / 10 lan (luu anh)")
    return n


# ---------- tuong ----------
def _dot_near(img, p, dx=70, dy=-10, tol=(30, 25)):
    """Co cham do o vi tri (p + (dx, dy)) - cham do goc tren-phai nut."""
    return any(abs(d[0] - p[0] - dx) < tol[0] and abs(d[1] - p[1] - dy) < tol[1] for d in red_dots(img))


def hero_detail(ctx, max_rounds=6):
    """Man chi tiet 1 tuong: 'Tang cap' khi nut co cham do (du EXP/vang), 'Tang sao' khi nut sao co cham do (du manh),
    sach Cau chuyen co cham do. Khong bao gio bam nut khong co cham do. -> so lan bam.
    LAP toi khi 1 vong khong lam them duoc gi: tang sao xong thi gioi han cap tang -> nut 'Tang cap' MOI hien cham do
    (#4 2026-11-21 17:48: tang sao 2 lan roi bo di, nut Tang cap con cham do)."""
    n = 0
    for _ in range(max_rounds):
        got = _hero_levelup(ctx) + _hero_star(ctx) + hero_story(ctx)
        if not got:
            got = _hero_exp(ctx)          # P9-8: Tang cap het cham do vi THIEU EXP -> dung EXP roi tang cap tiep
        n += got
        if not got:
            break
    return n


def _hero_exp(ctx):
    """P9-8: nut Tang cap co so EXP mau do (thieu EXP) -> o EXP -> bang EXP Tuong -> Dung / Dung tat ca (khong bao gio
    'Dung dao cu' kim cuong) -> neu nut Tang cap co cham do lai thi _hero_levelup lam tiep. -> so lan bam."""
    from bot.modules import hero_up
    b = ctx.v.find(ctx.shot(), "hero/btn_levelup")
    if not b or _dot_near(ctx._img, b):
        return 0
    used = hero_up.refill_and_level(ctx, b)
    return used + (_hero_levelup(ctx) if used else 0)


def _hero_levelup(ctx):
    n = 0
    for _ in range(30):
        img = ctx.shot()
        b = ctx.v.find(img, "hero/btn_levelup")
        if not b or not _dot_near(img, b):
            break
        ctx.tap(b[0], b[1], wait=0.8)
        n += 1
    if n:
        log.info("Tuong: tang cap %d lan", n)
        m = getattr(ctx, "mem", None)
        if m:   # tuong len cap -> tai trong doi co the tang -> gather do lai mo tu cap cao nhat (gather.sync_memory)
            m.set_fact(ctx.dev.idx, "hero_ups", (m.fact(ctx.dev.idx, "hero_ups", 0) or 0) + n)
    return n


def _hero_star(ctx):
    n = 0
    for _ in range(5):          # nang sao (manh tuong) - do #5 2026-11-18
        img = ctx.shot()
        st = ctx.v.find(img, "hero/btn_star", th=0.9)
        if not st or not _dot_near(img, st, dx=19, dy=-14, tol=(14, 14)):
            break
        ctx.tap(st[0], st[1], wait=1.5)
        up = ctx.v.find(ctx.shot(), "hero/btn_star_up", th=0.9)
        if not up or not _dot_near(ctx._img, up, dx=80, dy=-26, tol=(20, 16)):
            ctx.tap_first(["common/btn_back"], wait=1.2)
            break
        ctx.tap(up[0], up[1], wait=2.5)
        log.info("Tuong: tang sao")
        n += 1
        ctx.tap(270, 900, wait=1.5)                   # dong man "Tang sao thanh cong"
        ctx.tap_first(["common/btn_back"], wait=1.2)  # man tang sao -> chi tiet tuong
    return n


STORY_TABS = (40, 690, 460, 40)   # hang tab I..IV duoi bang Cau chuyen


def hero_story(ctx):
    """Icon SACH (goc phai) co cham do -> bang "Cau chuyen": tab co cham do -> cham HOP VANG o goc tranh
    -> nhan thuong (vd 20 kim cuong). Chu du an chi 2026-11-18 (#5)."""
    img = ctx.shot()
    bk = ctx.v.find(img, "hero/btn_book", th=0.85)   # 0,87 tren man chu du an gui 2026-11-21; van can cham do
    if not bk or not _dot_near(img, bk, dx=16, dy=-18, tol=(12, 12)):
        return 0
    ctx.tap(bk[0], bk[1], wait=1.5)
    n, done = 0, set()
    for _ in range(4):
        img = ctx.shot()
        dots = [d for d in red_dots(img, STORY_TABS) if d[0] // 60 not in done]
        if dots:
            x, y = dots[0]
            done.add(x // 60)
            ctx.tap(x - 50, y + 21, wait=1.2)       # cham do o goc tren-phai tab
        elif n or done:
            break
        c = ctx.v.find(ctx.shot(), "hero/story_chest", th=0.85)
        if not c:
            break
        ctx.tap(c[0], c[1], wait=1.5)
        ctx.dismiss_reward()
        log.info("Tuong: nhan thuong cau chuyen")
        n += 1
    ctx.tap_first(["common/btn_x", "common/btn_close"], wait=1.0)   # dong bang Cau chuyen
    return n


def full_shard_cards(img, roi=(0, 55, 540, 900)):
    """The tuong "Co the doi": thanh manh XANH LA DAY (10/10) o day the (tuong chua co, du manh de mo khoa).
    The chua du manh co thanh toi (0/10). Do tren anh chu du an gui 2026-11-20: thanh y~262, chu "10/10" chia doi
    thanh thanh 2 khoi xanh H~60, cao ~12. -> [(x, y)] giua the (cham vao de mo), tren xuong."""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 40) & (hsv[..., 0] <= 80) & (hsv[..., 1] >= 150) & (hsv[..., 2] >= 150)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 31), np.uint8))   # noi 2 nua thanh bi chu "10/10" chia
    k, _, st, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, k):
        x, y, w, h, a = st[i]
        if 60 <= w <= 125 and 6 <= h <= 18 and a >= 0.5 * w * h:
            out.append((int(x0 + x + w // 2), int(y0 + y + h // 2) - 90))
    return sorted(out, key=lambda p: (p[1] // 60, p[0]))


def unlock_heroes(ctx, max_cards=3):
    """Mo khoa tuong moi bang manh (MIEN PHI, chu du an 2026-11-20 "khi co hinh nay thi click vao mo khoa tuong moi"):
    cham the "Co the doi" -> bam nut doi/mo khoa (anh mau hero/btn_exchange) -> dong man thuong.
    Chua co anh mau nut -> chi luu anh man sau khi cham the de bo sung, khong bam gi khac."""
    n, seen = 0, set()
    for _ in range(max_cards):
        img = ctx.shot()
        if not ctx.v.find(img, "hero/title"):
            break
        cards = [c for c in full_shard_cards(img) if (c[0] // 60, c[1] // 60) not in seen]
        if not cards:
            break
        x, y = cards[0]
        seen.add((x // 60, y // 60))
        ctx.tap(x, y, wait=2.0)
        if ctx.tap_tpl("hero/btn_exchange", wait=3.0, th=0.85):
            n += 1
            log.info("Tuong: mo khoa tuong moi bang manh @%d,%d", x, y)
            for _ in range(4):                 # hoat anh nhan tuong -> "Xac nhan" / dong
                if ctx.find("hero/title"):
                    break
                ctx.dismiss_reward()
                if not ctx.find("hero/title") and ctx.tap_first(["common/btn_confirm_hero", "common/btn_back"]
                                                                 + ctx.POPUP_CLOSERS, wait=1.5) is None:
                    ctx.back_out(1)
        else:
            ctx.save_debug("hero_unlock")      # chua co anh mau nut doi -> anh de cat hero/btn_exchange
            log.info("Tuong: the 'Co the doi' @%d,%d - chua co anh mau nut doi (luu anh)", x, y)
            if not ctx.find("hero/title"):
                ctx.tap_first(["common/btn_back"] + ctx.POPUP_CLOSERS, wait=1.5)
    return n


def heroes(ctx, max_heroes=6):
    """Danh sach Tuong: mo khoa tuong du manh truoc, roi vao lan luot the co CHAM DO (goc tren-phai the),
    lam viec trong chi tiet, quay lai."""
    n, done = unlock_heroes(ctx), set()
    for _ in range(max_heroes):
        img = ctx.shot()
        if not ctx.v.find(img, "hero/title"):
            break
        from bot.modules import hero_up
        # cham do goc tren-phai the -> tam the (x-55, y+90); P9-8: mui ten xanh LON goc phai duoi the -> tam the
        cards = [(d[0] - 55, d[1] + 90) for d in red_dots(img, (0, 55, 540, 800))]
        cards += [hero_up.card_center(a) for a in hero_up.big_arrows(img)]
        cards = [c for c in cards if (c[0] // 90, c[1] // 110) not in done]
        if not cards:
            break
        x, y = min(cards, key=lambda c: (c[1] // 110, c[0]))
        done.add((x // 90, y // 110))
        ctx.tap(x, y, wait=2.0)                    # giua the tuong
        n += hero_detail(ctx)
        ctx.tap_first(["common/btn_back"], wait=1.5)
    return n


# ---------- su kien cot phai (vd "Su menh" - bang ghep hinh nhiem vu) ----------
EVENT_COL = (480, 340, 60, 200)    # cot icon su kien ben phai thanh pho, duoi Phuc loi (do #5 2026-11-18)
EVENT_BODY = (0, 180, 540, 720)


ZONE_TITLE_ROI = (20, 225, 500, 50)     # tieu de banner tab "Chien Khu manh nhat" (Hoat dong tro choi)
ZONE_CHESTS = (0, 560, 540, 300)        # 2 hang ruong: Tich diem ca nhan + Diem lien minh (duoi hang "Muc tieu giai doan")


def is_zone_title(text):
    """Ham thuan P13-9: tieu de banner OCR (mat dau, rat nhieu) co phai tab 'Chien Khu manh nhat'? Khop long 'khu'."""
    from aowbot.domain.blockers import normalize
    t = normalize(text or "")
    return "khu" in t and ("chien" in t or "manh" in t or "mah" in t or "nhat" in t)


def zone_chest_points(img):
    """Ham thuan P13-9 (chu du an, anh chien_khu_manh_nhat_ruong.png): CHI ruong co CHAM DO (da du moc) trong 2 hang ruong
    -> diem cham (giua ruong, thap-trai cham do). Ruong xam khong cham do (chua du diem) va cham do tab / tab con
    'Muc tieu giai doan' (ngoai hang ruong) bi bo."""
    dots = sorted(red_dots(img, ZONE_CHESTS), key=lambda d: (d[1] // 40, d[0]))
    return [(d[0] - 14, d[1] + 26) for d in dots]


def zone_chests(ctx, max_taps=6):
    """Tab Chien Khu manh nhat: nhan ruong co cham do. Khong bam mua / mo khoa. -> so ruong nhan."""
    if not is_zone_title(ocr.text(ctx.shot(), ZONE_TITLE_ROI)):
        return 0
    n, seen = 0, set()
    for _ in range(max_taps):
        pts = [p for p in zone_chest_points(ctx.shot()) if (p[0] // 40, p[1] // 40) not in seen]
        if not pts:
            break
        x, y = pts[0]
        seen.add((x // 40, y // 40))
        ctx.tap(x, y, wait=1.5)
        ctx.tap_tpl("event/btn_popup_claim", wait=1.2, th=0.9)
        ctx.dismiss_reward()
        n += 1
        log.info("Chien Khu manh nhat: nhan ruong @%d,%d", x, y)
    return n


def event_tiles(ctx, max_taps=12):
    """Trong 1 man su kien: cham lan luot o/vat co CHAM DO -> neu hien bang co nut "Nhan" (event/btn_popup_claim)
    thi nhan, dong bang (X). Khong bam gi khac. -> so lan nhan."""
    n, seen = 0, set()
    n += zone_chests(ctx)                   # P13-9: tab Chien Khu manh nhat - ruong co cham do
    if not ctx.find("recruit/title"):       # trang 'Chieu mo han gio' (Hoat dong) co icon "Qua Chieu Mo" ben phai
        n += 1 if recruit_gift(ctx, ctx.shot()) else 0
    for _ in range(max_taps):
        dots = [d for d in red_dots(ctx.shot(), EVENT_BODY) if (d[0] // 40, d[1] // 40) not in seen]
        if not dots:
            break
        x, y = dots[0]
        seen.add((x // 40, y // 40))
        ctx.tap(x - 35, y + 20, wait=1.5)          # giua o (cham do o goc tren-phai)
        if ctx.tap_tpl("event/btn_popup_claim", wait=1.5, th=0.9):
            ctx.dismiss_reward()
            n += 1
            log.info("Su kien: nhan thuong o @%d,%d", x, y)
        elif ctx.wait_for("common/btn_confirm_hero", timeout=4, th=0.9) or ctx.find("common/msg_reward", th=0.65):
            # o nhan ngay khi cham (vd Diem danh 7 ngay); thuong la TUONG -> hoat anh mo khoa ~3 s roi "Xac nhan"
            ctx.dismiss_reward()
            n += 1
            log.info("Su kien: nhan thuong o @%d,%d (cham truc tiep)", x, y)
        ctx.tap_first(["common/btn_close"], wait=1.0)   # dong bang nhiem vu (neu con)
    return n


def events(ctx):
    """Icon su kien cot phai co cham do -> vao, nhan cac o co cham do."""
    total = 0
    for _ in range(3):
        ctx.ensure_city()
        img = ctx.shot()
        dots = [d for d in red_dots(img, EVENT_COL)]
        if not dots:
            break
        x, y = dots.pop(0)
        ctx.tap(x - 16, y + 17, wait=2.5)
        got = event_tiles(ctx)
        total += got
        leave(ctx)
        if not got:
            break        # vao roi ma khong nhan duoc gi -> khong lap lai (tranh vong vo han voi cham "moi")
    return total


def run(ctx):
    nc = ctx.cfg.get("notify", {})
    ctx.ensure_city()
    done = {}
    for name, p in badged(ctx):
        if not nc.get(name, True):
            continue
        if name == "intel" and ctx.cfg.get("modules", {}).get("intel"):
            continue        # buoc 'intel' rieng lo
        ctx.ensure_city()
        log.info("Cham do: %s", name)
        try:
            if name == "intel":
                ctx.tap(p[0], p[1], wait=2.0)
                done[name] = intel(ctx, nc.get("intel_max", 20))
            else:
                ctx.tap(p[0], p[1], wait=2.5)
                if name in ("welfare", "bubble", "activity"):
                    done[name] = hub(ctx, cards=name != "activity")
                elif name == "recruit":
                    done[name] = recruit(ctx)
                elif name == "hero":
                    done[name] = heroes(ctx)
        finally:
            leave(ctx)
            ctx.ensure_city()
    if nc.get("welfare", True) and nc.get("welfare_daily_check", True):
        try:
            done["welfare_daily"] = welfare_daily(ctx, done)
        finally:
            leave(ctx)
            ctx.ensure_city()
    if nc.get("events", True):
        try:
            done["events"] = events(ctx)
        finally:
            leave(ctx)
            ctx.ensure_city()
    log.info("Thong bao da xu ly: %s", done)
    return done


# ---------- P10-6 Diem Danh 30 Ngay / Qua dang nhap: kiem MOI luot ----------
def utc_day(now=None):
    return time.strftime("%Y-%m-%d", time.gmtime(now if now is not None else time.time()))


def welfare_plan(today, claim_day, check_day, handled):
    """Ham thuan (P10-6, live3: khong co dong log nao ve Diem Danh / Qua dang nhap - TT phuc loi chi vao khi icon co cham
    do va chi tab co cham do, nhan xong tu live2 10:56 nen live3 im lang). -> (hanh dong, ly do):
      'claimed'  - luot nay TT phuc loi vua nhan duoc qua (handled > 0) -> ghi nhan hom nay
      'done'     - hom nay da nhan / da kiem (reset 0h UTC) -> log 'da nhan', bo qua nhanh
      'verify'   - chua nhan / chua kiem hom nay ma icon KHONG co cham do -> mo TT phuc loi 1 lan de kiem (o phat sang /
                   tab cham do), khong luot"""
    if handled:
        return "claimed", f"TT phuc loi vua nhan {handled}"
    if claim_day == today:
        return "done", f"da nhan hom nay ({today} UTC)"
    if check_day == today:
        return "done", f"da kiem hom nay ({today} UTC), khong con qua"
    return "verify", "chua kiem hom nay - mo TT phuc loi"


def welfare_daily(ctx, done):
    """Moi luot: ghi ro trang thai Diem Danh 30 Ngay / Qua dang nhap (TT phuc loi). Luat giu nguyen: o hao quang khong
    luot (claim_glow_tiles), Qua dang nhap chi cot Mien phi (free_column_tiles), khong goi ₫. -> so lan nhan them."""
    m, idx, today = getattr(ctx, "mem", None), ctx.dev.idx, utc_day()
    claim_day = m.fact(idx, "welfare_claim_day") if m else None
    check_day = m.fact(idx, "welfare_check_day") if m else None
    act, why = welfare_plan(today, claim_day, check_day, done.get("welfare") or 0)
    if act == "claimed":
        if m:
            m.set_fact(idx, "welfare_claim_day", today)
        log.info("Diem Danh 30 Ngay / Qua dang nhap: %s -> da nhan hom nay", why)
        return 0
    if act == "done":
        log.info("Diem Danh 30 Ngay / Qua dang nhap: %s - bo qua", why)
        return 0
    ctx.ensure_city()
    p = ctx.v.find(ctx.shot(), ICONS["welfare"])
    if not p:
        log.info("Diem Danh 30 Ngay / Qua dang nhap: khong thay icon TT phuc loi - de lan sau")
        return 0
    ctx.tap(p[0], p[1], wait=2.5)
    n = claim_glow_tiles(ctx) + hub(ctx, cards=True)     # o phat sang tab dang mo + moi tab con cham do
    if m:
        m.set_fact(idx, "welfare_check_day", today)
        if n:
            m.set_fact(idx, "welfare_claim_day", today)
    log.info("Diem Danh 30 Ngay / Qua dang nhap: %s -> nhan %d%s", why, n, "" if n else " (da nhan truoc do)")
    return n


# ---------- su kien "chua thuong" (hop cuu thuong -> cham vong vang) ----------
HEAL_BTN_ROI, HEAL_CNT_ROI = (380, 800, 160, 160), (400, 770, 90, 40)


def _ring_candidates(img, smin, vmin, fill, box, zone=None):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 12) & (hsv[..., 0] <= 35) & (hsv[..., 1] >= smin) & (hsv[..., 2] >= vmin)).astype(np.uint8)
    m[760:] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, _, st, c = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        w, h, a = st[i][2], st[i][3], st[i][4]
        if box[0] <= w <= box[1] and box[0] <= h <= box[1] and 0.8 <= w / h <= 1.25 and a >= fill * w * h:
            x, y = int(c[i][0]), int(c[i][1])
            if zone is None or (zone[0] <= x <= zone[2] and zone[1] <= y <= zone[3]):
                out.append((x, y))
    return out


def heal_targets(img):
    """Vong tron VANG (tam do) hien tren nguoi sau khi dung hop cuu thuong. Do #2 2026-11-21 (chu du an cham tay):
    vong ~49x48 px, H 12-35, S >= 110, V >= 150. Bo vung nut duoi (y >= 760). -> [(x, y)]
    Du phong (chu du an 2026-11-22: 'chua bam duoc vao day', #4): vong mo tren anh nguoi sang mau, S chi ~90-110 ->
    noi nguong S >= 70 nhung chi trong vung giua man (tranh HUD / thanh pho)."""
    out = _ring_candidates(img, 110, 150, 0.45, (26, 70))
    return out or _ring_candidates(img, 70, 150, 0.15, (36, 75), zone=(90, 120, 450, 700))


def heal_event(ctx, max_uses=10):
    """Su kien chua thuong (chu du an lam mau 2026-11-21 #2): con hop cuu thuong (so != 0) -> cham nut hop
    -> cham vong vang tren nguoi -> tien do tang. Het hop (so 0) thi dung. KHONG BAO GIO cham nut '+' (mua them).
    -> so lan dung."""
    n = 0
    for _ in range(max_uses):
        img = ctx.shot()
        btn = ctx.v.find(img, "event/heal_btn", th=0.85, roi=HEAL_BTN_ROI)
        if not btn:
            return n
        if ctx.v.find(img, "event/heal_cnt0", th=0.85, roi=HEAL_CNT_ROI):
            if n == 0:
                log.info("Su kien chua thuong: het hop cuu thuong")
            return n
        ctx.tap(btn[0], btn[1], wait=1.2)
        tg = heal_targets(ctx.shot())
        for _ in range(5):            # vong vang hien tre sau hoat anh canh (chu du an 2026-11-22 #4: chup som thi khong thay)
            if tg:
                break
            time.sleep(1.0)
            tg = heal_targets(ctx.shot())
        if not tg:
            log.info("Su kien chua thuong: dung hop nhung khong thay vong vang - dung")
            ctx.save_debug("heal_no_target")
            return n
        ctx.tap(tg[0][0], tg[0][1], wait=2.0)
        n += 1
        log.info("Su kien chua thuong: dung hop cuu thuong, cham vong @%d,%d", *tg[0])
    return n
