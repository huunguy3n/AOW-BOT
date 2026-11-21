"""Xay cong trinh MOI theo bang "Xay dung" (icon bua goc phai duoi thanh pho, cham do = so cong trinh xay duoc).
Chu du an 2026-11-21 (#6: "Xay dung dang co 5 cong trinh can xay").

Luong (do tay tren #6 2026-11-21):
  icon bua (build/icon_hammer) -> bang "Xay dung" (build/title_construct): 11 nhom (Tai nguyen, Kho, ...),
  nhom co cham do = co cong trinh xay duoc -> cham nhom -> thanh the cong trinh o day man
  (the bi khoa co o khoa build/card_lock; "x/y" = da xay/toi da) -> KEO the len ban do -> o dat 2x2:
  DO = cho khong hop le, XANH = dat duoc -> nut tick (build/btn_place_ok) -> man "Cap hien tai 0":
  nut PHAI "Xay dung" (build/btn_construct). KHONG BAO GIO bam nut trai "Xay dung ngay" (ke ca khi ghi "Mien phi").
Bo nhom "Con duong" (xay duong khong co ich).
"""
import re, time, logging
import cv2, numpy as np
from bot import ocr
from bot.badges import red_dots

log = logging.getLogger("aow")
HAMMER_ROI = (440, 760, 100, 110)
PANEL_ROI = (60, 250, 420, 470)                  # vung 11 icon nhom trong bang Xay dung
BADGE_OFF = (36, -33)                            # cham do lech so voi tam icon nhom
SKIP_GROUPS = [(110, 650)]                       # "Con duong" (hang Khac, cot 1)
CARD_X = (95, 250, 395)                          # 3 the o thanh day man (cuon ngang neu nhieu hon)
CARD_Y = 862
# diem du phong (giua man; keo sat mep man -> camera troi ra ngoai thanh pho)
TARGETS = [(150, 450), (390, 450), (270, 560), (150, 330), (390, 330), (270, 380)]
SPOT_ZONE = (110, 200, 430, 700)                 # x1, y1, x2, y2: chi chon dich trong vung nay


def footprint(img):
    """O dat cong trinh dang keo: -> ('ok'|'bad', cx, cy, (x, y, w, h)) | None. Xanh la sang = dat duoc, do = khong."""
    hsv = cv2.cvtColor(img[:820], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    for kind, m, need in (("ok", (H >= 45) & (H <= 75) & (S >= 170) & (V >= 200), 700),
                          ("bad", ((H <= 8) | (H >= 172)) & (S >= 150) & (V >= 200), 1800)):
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        n, _, st, c = cv2.connectedComponentsWithStats(m)
        if n > 1:
            i = 1 + int(np.argmax(st[1:, 4]))
            if st[i][4] >= need and st[i][2] >= 120:
                return kind, int(c[i][0]), int(c[i][1]), tuple(int(v) for v in st[i][:4])
    return None


def free_spot(img, box, avoid=()):
    """Cho co trong (o luoi co xanh, khong duong/nha) du lon cho o dat kich thuoc box -> (x, y) | None (ham thuan)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    g = ((H >= 29) & (H <= 40) & (S >= 130) & (S <= 200) & (V >= 85) & (V <= 140)).astype(np.uint8)
    g = cv2.morphologyEx(g, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))   # lap vach ke luoi
    g[820:], g[:110] = 0, 0
    x, y, w, h = box
    g[max(0, y - 10):y + h + 10, max(0, x - 10):x + w + 10] = 0             # cho cong trinh dang keo
    kw, kh = max(60, int(w * 0.9)), max(36, int(h * 0.9))
    k = np.zeros((kh, kw), np.uint8)
    cv2.fillConvexPoly(k, np.array([[kw // 2, 0], [kw - 1, kh // 2], [kw // 2, kh - 1], [0, kh // 2]]), 1)
    d = cv2.distanceTransform(cv2.erode(g, k), cv2.DIST_L2, 3)
    z = np.zeros_like(d)
    z[SPOT_ZONE[1]:SPOT_ZONE[3], SPOT_ZONE[0]:SPOT_ZONE[2]] = 1
    d *= z
    for ax, ay in avoid:
        cv2.circle(d, (ax, ay), 50, 0, -1)
    if d.max() <= 0:
        return None
    yy, xx = np.unravel_index(int(np.argmax(d)), d.shape)
    return int(xx), int(yy)


def card_info(ctx, img, x):
    """The cong trinh o cot x: -> (khoa, da_xay, toi_da) | None (khong co the)."""
    roi = img[CARD_Y - 30:CARD_Y + 45, x - 75:x + 75]
    if float(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).mean()) < 45:
        return None
    locked = bool(ctx.v.find(img, "build/card_lock", th=0.85, roi=(x - 75, CARD_Y - 40, 150, 60)))
    m = re.search(r"(\d)\s*/\s*(\d)", ocr.text(img, (x + 25, CARD_Y - 18, 50, 22), "0123456789/", scale=4) or "")
    return locked, (int(m.group(1)) if m else None), (int(m.group(2)) if m else None)


def place(ctx, x, tries=8):
    """Keo the o cot x len ban do, tim cho xanh, bam tick + "Xay dung". -> True neu da xay."""
    ctx.dev.swipe(x, CARD_Y - 30, 270, 450, 1500)
    time.sleep(1.5)
    tried, spare = [], list(TARGETS)
    for _ in range(tries + 1):
        img = ctx.shot()
        fp = footprint(img)
        if not fp:
            ctx.save_debug("construct_nofp")
            return False
        kind, cx, cy, box = fp
        if kind == "ok":
            ok = ctx.v.find(img, "build/btn_place_ok", th=0.8, roi=(0, min(cy + 40, 760), 540, 200))
            if not ok:
                ctx.save_debug("construct_no_tick")
                return False
            ctx.tap(ok[0], ok[1], wait=2.0)
            if not ctx.wait_for("build/btn_construct", timeout=5, th=0.85, roi=(280, 870, 200, 90)):
                ctx.save_debug("construct_no_confirm")
                return False
            ctx.tap_tpl("build/btn_construct", wait=2.5, th=0.85, roi=(280, 870, 200, 90))   # nut PHAI, khong phai "ngay"
            if ctx.find("build/btn_construct", th=0.85, roi=(280, 870, 200, 90)):
                log.info("Xay moi: bam 'Xay dung' nhung van o man xac nhan (thieu tai nguyen/tho?) - bo")
                ctx.save_debug("construct_blocked")
                return False
            return True
        t = free_spot(img, box, tried)
        if t is None:
            if not spare:
                break
            t = spare.pop(0)
        tried.append(t)
        ctx.dev.swipe(cx, cy, t[0], t[1], 1200)
        time.sleep(1.2)
    log.info("Xay moi: khong tim duoc cho trong de dat")
    ctx.save_debug("construct_no_spot")
    return False


def run(ctx):
    bc = ctx.cfg.get("construct", {})
    built, tried = 0, set()
    for _ in range(bc.get("max_per_run", 6)):
        ctx.skip_dialogs()            # xay xong hay mo khoa tinh nang -> hoi thoai huong dan (vd "mo khoa lien minh")
        ctx.ensure_city()
        img = ctx.shot()
        h = ctx.v.find(img, "build/icon_hammer", th=0.85, roi=HAMMER_ROI)
        if not h:
            log.info("Xay moi: khong thay icon bua")
            break
        if not red_dots(img, (h[0], h[1] - 50, 60, 50)):
            log.info("Xay moi: icon bua khong co cham do - khong co cong trinh moi")
            break
        ctx.tap(h[0], h[1], wait=1.8)
        img = ctx.shot()
        if not ctx.v.find(img, "build/title_construct", th=0.85):
            ctx.save_debug("construct_panel")
            break
        groups = [(bx - BADGE_OFF[0], by - BADGE_OFF[1]) for bx, by in red_dots(img, PANEL_ROI)]
        groups = [g for g in groups if g not in tried
                  and not any(abs(g[0] - sx) < 40 and abs(g[1] - sy) < 40 for sx, sy in SKIP_GROUPS)]
        if not groups:
            log.info("Xay moi: khong con nhom nao co cham do (hoac da thu)")
            break
        g = groups[0]
        tried.add(g)
        ctx.tap(g[0], g[1], wait=2.0)
        img = ctx.shot()
        done = False
        for x in CARD_X:
            ci = card_info(ctx, img, x)
            if not ci:
                continue
            locked, a, b = ci
            log.info("Xay moi: nhom @%d,%d the cot %d: %s %s/%s", g[0], g[1], x, "KHOA" if locked else "mo", a, b)
            if locked or (a is not None and b is not None and a >= b):
                continue
            if place(ctx, x):
                built += 1
                done = True
                log.info("Xay moi: da xay 1 cong trinh (nhom @%d,%d)", g[0], g[1])
            break
        if not done:
            ctx.back_out(2)
        else:
            tried.discard(g)          # nhom con the khac/cung loai (vd 0/3 -> 1/3) -> lan sau thu lai
    ctx.ensure_city()
    return built
