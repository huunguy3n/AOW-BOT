"""P13d-5 (t87u) Quan quan tuan - DAT CUOC bang thanh/bar su kien ("So huu 20000"), KHONG kim cuong.

Luong (anh data/owner-feedback/p13/cuoc_1..3):
  1. popup "Cuoc cua toi" ("Chua dat cuoc"): bam "Dat cuoc" duoi "Goi y cuoc"
  2. man tran ("Giai doan cuoc", Phe Cong / Phe thu, thanh % 99% vs 1%): bam "Dat cuoc"
  3. hop "Cuoc va dat cuoc": doc % hai ben (thanh do-xanh), KEO thanh truot HET ve ben % CAO HON (trai lon -> keo trai,
     phai lon -> keo phai), doc lai so tien ben do == "So huu", roi bam "Dat cuoc".
An toan: chi nut co chu "Dat cuoc" (khong co dau hieu tra phi - buttons.is_danger); khong thay chu "So huu" (tien su kien)
thi KHONG dat; khong bao gio nut kim cuong / mua them. Ham quyet dinh la ham thuan (test offline), phan chay thiet bi mong.
Vao man cuoc: bot/modules/reddots.py (_open_dot) goi handle() khi icon vua mo ra la man cuoc; chua co duong vao rieng.
"""
import logging
import re
import time

import cv2
import numpy as np

from bot import buttons, ocr

log = logging.getLogger("aow")

BET_RX = r"\bd[aeo]t cu[oa]c\b"            # "Dat cuoc" (OCR 'eng' mat dau)
TITLE_MY = (140, 105, 260, 55)             # "Cuoc cua toi"
TITLE_STAGE = (100, 125, 340, 40)          # "Giai doan cuoc  hh:mm:ss"
MAX_DRAGS = 3


# ---------------- ham thuan ----------------
def _norm(s):
    return buttons._norm(s)


def pick_side(left_pct, right_pct):
    """% hai ben -> 'left' | 'right' | None (khong doc duoc / bang nhau -> khong dat)."""
    if left_pct is None or right_pct is None or left_pct == right_pct:
        return None
    return "left" if left_pct > right_pct else "right"


def bar_split(img, roi=None):
    """Thanh ty le cuoc (do ben trai, xanh duong ben phai): do rong doan do / (do + xanh) -> (left%, right%) | None."""
    ox, oy = 0, 0
    if roi:
        x, y, w, h = roi
        img, ox, oy = img[y:y + h, x:x + w], x, y
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    red = (((H <= 6) | (H >= 172)) & (S >= 150) & (V >= 90))
    blue = ((H >= 100) & (H <= 125) & (S >= 150) & (V >= 90))
    both = (red | blue).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(both, cv2.MORPH_CLOSE, np.ones((3, 9), np.uint8)))
    best = None
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if w >= 100 and 6 <= h <= 30 and w / h >= 8 and a >= 0.7 * w * h and (best is None or w > best[2]):
            best = (x, y, w, h)
    if best is None:
        return None
    x, y, w, h = best
    rc = int((red[y:y + h, x:x + w].sum(axis=0) >= h // 2).sum())     # so cot "do" / "xanh" trong thanh
    bc = int((blue[y:y + h, x:x + w].sum(axis=0) >= h // 2).sum())
    if rc + bc < 0.9 * w or rc + bc == 0:
        return None
    left = round(100.0 * rc / (rc + bc))
    return left, 100 - left


def handle_center(img, roi=None):
    """Nut keo hinh luc giac xanh ngoc cua thanh truot ('Dat cuoc' nho): khoi ~40 px gan vuong (nut 'Dat cuoc' rong >> 60,
    nut '+' < 32). -> (x, y) | None."""
    ox, oy = 0, 0
    if roi:
        x, y, w, h = roi
        img, ox, oy = img[y:y + h, x:x + w], x, y
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 80) & (hsv[..., 0] <= 100) & (hsv[..., 1] >= 110) & (hsv[..., 2] >= 110)).astype(np.uint8)
    n, _, st, cent = cv2.connectedComponentsWithStats(cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 34 <= w <= 60 and 34 <= h <= 60 and 0.75 <= w / h <= 1.35 and a >= 0.4 * w * h:
            return int(cent[i][0]) + ox, int(cent[i][1]) + oy
    return None


def drag_plan(side, handle, width=540):
    """Keo nut truot HET ve phia `side` (tha ngoai mep: thanh truot kep ve cuc). -> (x1, y1, x2, y2) | None.
    Toa do kep 0..width-1 (device.clamp_xy cung kep)."""
    if side not in ("left", "right") or not handle:
        return None
    x, y = handle
    return x, y, (2 if side == "left" else width - 3), y


def parse_amounts(text):
    """'20000 0' -> [20000, 0] (so tien hai dau thanh truot)."""
    return [int(t) for t in re.findall(r"\d+", text or "")]


def verified(side, amounts, owned):
    """Sau khi keo: so tien ben `side` == So huu (het), ben kia == 0."""
    if side not in ("left", "right") or owned is None or len(amounts) < 2:
        return False
    mine, other = (amounts[0], amounts[-1]) if side == "left" else (amounts[-1], amounts[0])
    return mine == owned and other == 0


def bet_buttons(img, roi=None):
    """Nut co chu 'Dat cuoc' (khong dau hieu tra phi), duoi len tren: nut LOW NHAT = nut dat cuoc chinh cua man."""
    out = buttons.with_text(img, BET_RX, roi=roi)
    return sorted(out, key=lambda b: -b.y)


def has_owned_label(text):
    return "huu" in _norm(text)


# ---------------- thiet bi ----------------
def _txt(ctx, img, roi):
    return _norm(ocr.text(img, roi, scale=3, psm=7))


def screen_of(ctx, img):
    """'my_bets' (Cuoc cua toi) | 'stage' (man tran) | 'dialog' (Cuoc va dat cuoc) | None."""
    if "cuoc cua" in _txt(ctx, img, TITLE_MY):
        return "my_bets"
    if "giai doan cuoc" in _txt(ctx, img, TITLE_STAGE) or "doan cuoc" in _txt(ctx, img, TITLE_STAGE):
        return "stage"
    if handle_center(img) and bar_split(img) and bet_buttons(img):
        return "dialog"
    return None


def owned_amount(ctx, img, handle_y):
    """'So huu N' nam duoi thanh truot ~ +85 px."""
    roi = (150, min(900, handle_y + 68), 240, 34)
    t = ocr.text(img, roi, scale=3, psm=7)
    n = parse_amounts(t)
    return n[-1] if n and has_owned_label(t) else None     # khong thay chu "So huu" -> khong dat (khong biet loai tien)


def _bet_dialog(ctx):
    img = ctx.shot()
    pct = bar_split(img)
    h = handle_center(img)
    side = pick_side(*pct) if pct else None
    if side is None or h is None:
        log.info("Quan quan: khong doc duoc ty le cuoc (%s) / nut keo (%s) - khong dat", pct, h)
        ctx.save_debug("champion_dialog")
        return 0
    owned = owned_amount(ctx, img, h[1])
    if owned is None or owned <= 0:
        log.info("Quan quan: khong doc duoc 'So huu' - khong dat (khong dung kim cuong)")
        return 0
    ok = False
    for k in range(MAX_DRAGS):
        x1, y1, x2, y2 = drag_plan(side, h)
        ctx.dev.swipe(x1, y1, x2, y2, ms=700)
        time.sleep(0.8)
        img = ctx.shot()
        amounts = parse_amounts(ocr.text(img, (0, max(0, h[1] - 16), 540, 32), "0123456789", scale=3, psm=7))
        if verified(side, amounts, owned):
            ok = True
            break
        log.info("Quan quan: keo lan %d chua het (so tien %s, so huu %s)", k + 1, amounts, owned)
        h = handle_center(img) or h
    if not ok:
        log.info("Quan quan: keo khong het ve ben %s - huy, khong dat", side)
        ctx.save_debug("champion_drag")
        return 0
    btns = bet_buttons(img)
    if not btns:
        return 0
    b = btns[0]
    ctx.tap(b.x, b.y, wait=2.0)
    log.info("Quan quan: dat cuoc %d (so huu, het) ben %s (%s%%)", owned, side, pct[0] if side == "left" else pct[1])
    return 1


def handle(ctx, rounds=4):
    """Dang o 1 trong 3 man cuoc -> lam tiep toi khi dat xong. -> 1 neu da dat cuoc, 0 neu khong."""
    done = 0
    for _ in range(rounds):
        img = ctx.shot()
        scr = screen_of(ctx, img)
        if scr == "my_bets":
            if "chua dat" not in _txt(ctx, img, (100, 380, 340, 120)):
                log.info("Quan quan: da dat cuoc roi - bo qua")
                return done
            if not has_owned_label(_txt(ctx, img, (150, 160, 240, 34))):
                return done
            btns = bet_buttons(img)
            if not btns:
                return done
            ctx.tap(btns[0].x, btns[0].y, wait=2.0)
        elif scr == "stage":
            btns = bet_buttons(img)
            if not btns:
                return done
            ctx.tap(btns[0].x, btns[0].y, wait=2.0)
        elif scr == "dialog":
            done = _bet_dialog(ctx)
            return done
        else:
            return done
    return done
