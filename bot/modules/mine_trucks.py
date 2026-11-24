"""P9-6 (chu du an 2026-11-24, anh live2-feedback/xe_mo_*.png, mo_khoang_xe_cua_toi_4_4.png): Mo khoang san >
"Xe khai thac cua toi" - dua xe CUA MINH di khai thac toi het luot "So lan khai thac con lai X/4".

Luong (moi xe trong, dau "+" xanh):
  1. cham "+" -> popup xe (do hiem N/R/SR/SSR, nut lam moi vong vang, banh rang, bat tay, "Xuat phat").
  2. lam moi (vong vang) CHI khi chu duoi nut la "Mien phi" hoac con luot (a/b voi a < b); "1/0" = het luot -> thoi.
  3. xe SR/SSR CO tinh the -> nut bat tay (Ho tro) -> tab "Doi quan ho tro lien minh" -> luot danh sach, chon nguoi luc
     chien > `min_support_power` (400M) -> "Moi xuat phat". Khong ai > 400M -> de xe trong, KHONG xuat phat.
  4. xe thuong -> banh rang -> "Doi hinh de xuat" -> "Luu" -> "Xuat phat".
  5. hop "Chu y" (xe gia tri thap) -> CHI "Xac nhan"; KHONG BAO GIO tick "Hom nay khong hien thi lai".
  6. thanh cong = so luot X/4 giam (xe chay tren duong co dong ho).

CHUA CO anh ADB 540x960 cua popup xe / bang Ho tro: toa do lay tu anh chu du an (gan du man hinh, lech vai px) va moi nut
bam deu tim theo CHU (bot/buttons.py: mau + chu, loc nut tra phi). Khong thay chu -> khong bam.
"""
import logging
import re
import time

import cv2
import numpy as np

from bot import buttons, ocr

log = logging.getLogger("aow")

TAB_MINE = (175, 88)                  # tab "Xe khai thac cua toi" (live2 s110403)
LEFT_ROI = (100, 862, 340, 30)        # "So lan khai thac con lai:4/4"
PLUS_ROI = (60, 400, 420, 170)        # vung 2 xe trong co dau "+" xanh (s110403: 153,478 va 389,478)
REFRESH = (462, 368)                  # nut lam moi vong vang (anh xe_mo_1)
REFRESH_LABEL_ROI = (400, 395, 120, 26)   # chu duoi nut lam moi: "Mien phi" | "1/0"
RARITY_ROI = (55, 360, 70, 65)        # chu N / R / SR / SSR goc trai popup
CARGO_ROI = (150, 450, 260, 80)       # hang vat pham van chuyen (tinh the xanh)
GEAR = (467, 587)                     # banh rang "Doi ho ve" (cai dat quan doan)
HANDSHAKE = (468, 768)                # nut bat tay "Ho tro"
CHECKBOX_ROI = (80, 380, 60, 60)      # o tick "Hom nay khong hien thi lai" trong hop Chu y - KHONG BAO GIO cham
POWER_ROW_X = (370, 520)              # cot luc chien moi dong trong bang Ho tro (x 370-520)
LEFT_RX = re.compile(r"(\d)\s*/\s*(\d)")
SLASH_RX = re.compile(r"(\d+)\s*/\s*(\d+)")


def mcfg(cfg):
    return {"enabled": True, "min_support_power": 400_000_000, "refresh_max": 3, "max_trucks": 4,
            "support_pages": 4, **((cfg or {}).get("mine_trucks") or {})}


# ---------------------------------------------------------------- ham thuan
def parse_left(text):
    """'So lan khai thac con lai:4/4' -> 4 | None."""
    m = LEFT_RX.search(text or "")
    return int(m.group(1)) if m and int(m.group(1)) <= int(m.group(2)) else None


def refresh_allowed(label):
    """Chu duoi nut lam moi: 'Mien phi' -> True; 'a/b' -> con luot khi b > 0 va a < b; '1/0' -> False (het luot).
    Khong doc duoc -> False (khong bam - co the ton phi)."""
    t = buttons._norm(label)
    if re.search(r"mi\w{0,2}n\s*ph", t):
        return True
    m = SLASH_RX.search(t)
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    return b > 0 and a < b


def truck_plan(rarity, crystal):
    """'support' (SR/SSR co tinh the: moi doi ho tro lien minh) | 'normal' (doi hinh de xuat + Luu + Xuat phat)."""
    return "support" if rarity in ("SR", "SSR") and crystal else "normal"


def pick_supporter(rows, min_power):
    """rows: [(luc chien | None, (x, y) nut 'Moi xuat phat')] -> dong DAU TIEN co luc chien > min_power | None.
    Khong doc duoc luc chien -> bo dong do."""
    for pw, btn in rows:
        if pw is not None and pw > min_power and btn:
            return pw, btn
    return None


def safe_tap_point(x, y):
    """Khong bao gio cham o tick 'Hom nay khong hien thi lai'."""
    rx, ry, rw, rh = CHECKBOX_ROI
    return not (rx <= x <= rx + rw and ry <= y <= ry + rh)


def plus_marks(img, roi=PLUS_ROI):
    """Dau "+" xanh la tren xe trong (s110403: 2 dau ~60x45 px, H 55-75, S > 150, V > 150). -> [(x, y)] trai -> phai."""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 45) & (hsv[..., 0] <= 85) & (hsv[..., 1] >= 120) & (hsv[..., 2] >= 150)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))   # noi 2 net cua dau "+"
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    out = [(int(x0 + st[i][0] + st[i][2] // 2), int(y0 + st[i][1] + st[i][3] // 2)) for i in range(1, n)
           if 40 <= st[i][2] <= 90 and 35 <= st[i][3] <= 75 and 300 <= st[i][4] < 0.75 * st[i][2] * st[i][3]]
    return sorted(out)


def rarity_letter(img, roi=RARITY_ROI):
    """Mau chu do hiem: N xanh la, R xanh duong, SR tim, SSR vang/cam."""
    x, y, w, h = roi
    hsv = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2HSV).reshape(-1, 3)
    r = hsv[(hsv[:, 1] > 120) & (hsv[:, 2] > 150)]
    if len(r) < 120:
        return None
    hue = float(np.median(r[:, 0]))
    if 10 <= hue <= 35:
        return "SSR"
    if 120 <= hue <= 165:
        return "SR"
    if 40 <= hue <= 85:
        return "N"
    if 90 <= hue <= 118:
        return "R"
    return None


# ---------------------------------------------------------------- thao tac
def _btn(ctx, pattern, roi=None):
    img = ctx.shot()
    bs = buttons.with_text(img, pattern, roi)
    return (bs[0].x, bs[0].y) if bs else None


def _tap_text(ctx, pattern, roi=None, wait=1.5, why=""):
    p = _btn(ctx, pattern, roi)
    if not p or not safe_tap_point(*p):
        return False
    ctx.tap(p[0], p[1], wait=wait)
    log.info("Xe khai thac: bam '%s' @%d,%d", why or pattern, p[0], p[1])
    return True


def attention_confirm(ctx):
    """Hop "Chu y" (xe gia tri thap): CHI "Xac nhan" (khong tick o 'Hom nay khong hien thi lai')."""
    return _tap_text(ctx, r"x\w{0,2}c nh\w{0,2}n", (250, 430, 290, 120), why="Xac nhan (Chu y)")


def _depart(ctx):
    if not _tap_text(ctx, r"xu\w{0,2}t ph\w{0,2}t", (120, 700, 300, 140), wait=2.0, why="Xuat phat"):
        return False
    attention_confirm(ctx)
    return True


def normal_depart(ctx):
    """Banh rang -> Doi hinh de xuat -> Luu -> Xuat phat (-> Chu y: Xac nhan)."""
    ctx.tap(*GEAR, wait=2.0)
    if not _tap_text(ctx, r"de xu\w{0,2}t", (0, 840, 300, 120), why="Doi hinh de xuat"):
        log.info("Xe khai thac: khong thay 'Doi hinh de xuat' - thoat")
        ctx.back_out(1)
        return False
    if not _tap_text(ctx, r"\blu\w{0,2}\b", (260, 840, 280, 120), wait=2.0, why="Luu"):
        ctx.back_out(1)
        return False
    return _depart(ctx)


def _read_power(img, y):
    d = re.sub(r"\D", "", ocr.text(img, (POWER_ROW_X[0], y, POWER_ROW_X[1] - POWER_ROW_X[0], 30), "0123456789") or "")
    return int(d) if 6 <= len(d) <= 12 else None


def support_rows(img):
    """Bang Ho tro (tab Doi quan ho tro lien minh): moi nut 'Moi xuat phat' + luc chien dong do (~80-110 px phia tren)."""
    rows = []
    for b in buttons.with_text(img, r"m\w{0,2}i xu\w{0,2}t", (330, 180, 210, 700)):
        rows.append((_read_power(img, max(0, b.y - 100)) or _read_power(img, max(0, b.y - 85)), (b.x, b.y)))
    return rows


def support_depart(ctx, min_power, pages=4):
    """Bat tay -> tab "Doi quan ho tro lien minh" -> luot, chon nguoi > min_power -> "Moi xuat phat".
    Khong ai du -> dong bang, KHONG xuat phat (de xe trong). -> True neu da moi."""
    ctx.tap(*HANDSHAKE, wait=2.0)
    _tap_text(ctx, r"li\w{0,2}n\s*minh", (260, 80, 280, 80), why="tab Doi quan ho tro lien minh")
    for page in range(pages):
        got = pick_supporter(support_rows(ctx.shot()), min_power)
        if got:
            pw, (x, y) = got
            ctx.tap(x, y, wait=2.0)
            log.info("Xe khai thac SR/SSR: moi ho tro luc chien %s (> %s)", f"{pw:,}", f"{min_power:,}")
            attention_confirm(ctx)
            return True
        if page + 1 < pages:
            ctx.dev.swipe(270, 700, 270, 330, 600)
    log.info("Xe khai thac SR/SSR: khong ai luc chien > %s - de xe trong, KHONG xuat phat", f"{min_power:,}")
    ctx.back_out(1)
    return False


def run(ctx):
    """Dang o man Mo khoang san. -> so xe da dua di."""
    c = mcfg(ctx.cfg)
    if not c["enabled"]:
        return 0
    from bot.modules import play
    if not back_to_mine(ctx):
        log.info("Xe khai thac cua toi: khong ve duoc man Mo khoang san (popup qua?) - bo, luu anh")
        ctx.save_debug("mine_trucks_no_title")
        return 0
    ctx.tap(*TAB_MINE, wait=1.5)
    sent = 0
    for k in range(c["max_trucks"]):
        img = ctx.shot()
        left = parse_left(ocr.text(img, LEFT_ROI))
        log.info("Xe khai thac cua toi: con %s/4 luot khai thac, %d xe trong (xe %d)", left, len(plus_marks(img)), k + 1)
        if left == 0:
            log.info("Xe khai thac cua toi: het luot (0/4)")
            break
        plus = plus_marks(img)
        if not plus:
            log.info("Xe khai thac cua toi: khong con xe trong (luot %s)", left)
            break
        if not ctx.find("play/mine_title"):              # chi cham "+" o man Mo khoang san
            break
        ctx.tap(plus[0][0], plus[0][1], wait=2.0)
        refreshed = 0
        while True:
            p = ctx.shot()
            rar, crystal = rarity_letter(p), play.crystal_item(p, CARGO_ROI)
            if rar in ("SR", "SSR") or refreshed >= c["refresh_max"]:
                break
            if not refresh_allowed(ocr.text(p, REFRESH_LABEL_ROI)):
                break                                    # "1/0" = het luot lam moi / khong doc duoc -> khong bam
            ctx.tap(*REFRESH, wait=2.0)
            refreshed += 1
            log.info("Xe khai thac: lam moi (%d)", refreshed)
        plan = truck_plan(rar, crystal)
        log.info("Xe khai thac: do hiem %s, tinh the %s -> %s", rar, crystal, plan)
        ok = support_depart(ctx, c["min_support_power"], c["support_pages"]) if plan == "support" else normal_depart(ctx)
        if not ok:
            ctx.back_out(1)
            break                                        # khong xuat phat duoc -> khong lap (cung xe se hien lai)
        after = parse_left(ocr.text(ctx.shot(), LEFT_ROI))
        if left is not None and after is not None and after >= left:
            log.info("Xe khai thac: so luot khong giam (%s -> %s) - dung", left, after)
            break
        sent += 1
        log.info("Xe khai thac: xe %d (%s, %s) da xuat phat - luot %s/4 -> %s/4", k + 1, rar, plan, left, after)
    log.info("Xe khai thac cua toi: dua di %d xe", sent)
    return sent


def back_to_mine(ctx, tries=4):
    """P10-4 (live3 15:38:58): sau khi nhan ruong, bang "Chuc mung nhan duoc" con de len man -> find('play/mine_title')
    hut va run() tra 0 LANG LE (khong mo tab Xe khai thac cua toi). Dong bang qua / cho toi khi thay tieu de."""
    for _ in range(tries):
        if ctx.find("play/mine_title"):
            return True
        ctx.dismiss_reward()
        time.sleep(0.8)
    return bool(ctx.find("play/mine_title"))
