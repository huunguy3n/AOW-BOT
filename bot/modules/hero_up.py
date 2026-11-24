"""P9-8 (chu du an 2026-11-24, anh live2-feedback/tuong_1..5): tang cap tuong.

  * Danh sach Tuong: the co MUI TEN XANH lon (goc phai duoi the, ~18x19 px) = tang cap duoc -> vao the.
    (mui ten nho canh quyen sach = Cau chuyen, do notify.hero_story lo.)
  * Chi tiet tuong: "Tang cap" (notify._hero_levelup khi nut co cham do). Thieu EXP (so EXP trong nut mau DO, anh
    tuong_3 "150.5K/166.8K") -> cham o EXP -> bang "EXP Tuong" -> "Dung" 1 lan cho hien "Dung tat ca" -> "Dung tat
    ca" tung hang -> dong -> quay lai "Tang cap" khi con cham do, lap toi het.
  * KHONG BAO GIO bam hang "Dung dao cu" (nut kim cuong, vd 3 kim cuong, dong cuoi bang EXP Tuong).

Anh chu du an la anh dien thoai (gan 540 rong) - nut trong bang EXP tim theo CHU (bot/buttons.py), khong theo toa do.
"""
import logging
import re

import cv2
import numpy as np

from bot import buttons, ocr

log = logging.getLogger("aow")

ARROW_ROI = (0, 60, 540, 860)
DUNG_RX = r"(?:^|\W)d\w{0,2}ng(?:\W|$)"          # "Dung" (OCR mat dau)
ALL_RX = r"t\w{0,2}t\s*c\w?"                       # "... tat ca"
DAO_CU_RX = re.compile(r"\bd\w{0,2}o\s*c\w{0,2}\b")  # chu "Dung dao cu" (dong kim cuong)


def big_arrows(img, roi=ARROW_ROI):
    """Mui ten xanh LON (tang cap) tren the tuong: H 50-80, S >= 150, V >= 150, 15-24 px, dien tich >= 120.
    Mui ten nho (10-12 px, canh quyen sach) la Cau chuyen -> bo. -> [(x, y)] tren -> duoi, trai -> phai."""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 50) & (hsv[..., 0] <= 80) & (hsv[..., 1] >= 150) & (hsv[..., 2] >= 150)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    out = [(int(x0 + st[i][0] + st[i][2] // 2), int(y0 + st[i][1] + st[i][3] // 2)) for i in range(1, n)
           if 15 <= st[i][2] <= 24 and 15 <= st[i][3] <= 24 and st[i][4] >= 120]
    return sorted(out, key=lambda p: (p[1] // 60, p[0]))


def card_center(arrow):
    """Mui ten o goc phai duoi the -> tam the (tuong_1: mui ten 513,237 -> the ~460,150)."""
    return arrow[0] - 55, arrow[1] - 90


def exp_short(img, btn):
    """So EXP tren nut "Tang cap" mau DO = thieu EXP (anh tuong_3). btn = (x, y) tam nut."""
    x, y = int(btn[0]), int(btn[1])
    box = img[max(0, y + 10):y + 34, max(0, x - 60):x + 20]
    if box.size == 0:
        return False
    hsv = cv2.cvtColor(box, cv2.COLOR_BGR2HSV)
    red = ((hsv[..., 0] <= 8) | (hsv[..., 0] >= 172)) & (hsv[..., 1] >= 120) & (hsv[..., 2] >= 100)
    return int(red.sum()) >= 15


def exp_cell(btn):
    """O EXP (icon EXP trong nut Tang cap, tuong_3: nut 272,812 -> icon 230,834)."""
    return int(btn[0]) - 42, int(btn[1]) + 22


def dao_cu_y(img):
    """y dong "Dung dao cu" (kim cuong) trong bang EXP Tuong | None. Moi nut tu y nay tro xuong KHONG duoc bam."""
    for y in range(500, 900, 20):
        t = buttons._norm(ocr.text(img, (330, y, 200, 30), scale=2, psm=7))
        if DAO_CU_RX.search(t):
            return y
    return None


def plan_exp_taps(btns, cut_y, used_one):
    """Ham thuan. btns: [Button] trong bang EXP Tuong (text da bo dau). -> Button can bam ke tiep | None.
    Uu tien "Dung tat ca"; chua co thi "Dung" (1 lan) de hien "Dung tat ca". Bo moi nut tu dong "Dung dao cu" (cut_y)
    tro xuong va moi nut co dau hieu kim cuong / tra phi."""
    ok = [b for b in btns if (cut_y is None or b.y < cut_y - 10) and not buttons.is_danger(b.text)
          and not re.search(r"\d", b.text)]
    alls = [b for b in ok if re.search(ALL_RX, b.text)]
    if alls:
        return alls[0]
    ones = [b for b in ok if re.search(DUNG_RX, b.text) and not re.search(ALL_RX, b.text)]
    if ones and not used_one:
        return ones[0]
    return None


def use_exp(ctx, max_taps=8):
    """Bang "EXP Tuong" dang mo: "Dung" 1 lan -> "Dung tat ca" tung hang. -> so lan bam. Dong bang khi xong."""
    n, used_one, dead = 0, False, set()
    for _ in range(max_taps):
        img = ctx.shot()
        cut = dao_cu_y(img)
        btns = [b for b in buttons.with_text(img, r"d\w{0,2}ng") if (b.x // 20, b.y // 20) not in dead]
        b = plan_exp_taps(btns, cut, used_one)
        if b is None:
            break
        if re.search(ALL_RX, b.text):
            dead.add((b.x // 20, b.y // 20))           # moi "Dung tat ca" 1 lan (hang da dung het)
        else:
            used_one = True
        ctx.tap(b.x, b.y, wait=1.2)
        n += 1
        log.info("EXP Tuong: bam '%s' @%d,%d", b.text, b.x, b.y)
    ctx.tap_first(["common/btn_close", "common/btn_x"] + list(getattr(ctx, "POPUP_CLOSERS", [])), wait=1.0)
    return n


def refill_and_level(ctx, btn, rounds=2):
    """Nut Tang cap khong co cham do vi THIEU EXP -> mo o EXP, dung EXP, tra ve so lan dung."""
    total = 0
    for _ in range(rounds):
        img = ctx.shot()
        if not exp_short(img, btn):
            break
        ctx.tap(*exp_cell(btn), wait=1.5)
        got = use_exp(ctx)
        total += got
        if not got:
            break
    return total
