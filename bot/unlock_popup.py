"""P13k (chu du an 26/11/2026): popup "Mo khoa Binh chung nay" phu len thanh pho -> bam "Xac nhan" (mien phi, chi
xac nhan da mo). KHONG BAO GIO bam "Den" (nut trai).

Popup khong co nut X va thanh nut duoi cua game van lo ra (is_home van True) nen moi noi don popup phai hoi rieng.
Nhan bang CA HAI: tieu de (mat na chu vang - nen sau chu la thanh pho dang song nen khong so anh mau thuong) va nut
"Xac nhan" nua phai. Chi co nut "Xac nhan" (hop thoai khac) -> khong phai popup nay.
find() / in_go_zone() la ham thuan; dismiss() bam qua Ctx, gioi han lan thu + danh sach den toa do (bot/tapguard.py).
"""
import logging

import cv2
import numpy as np

from bot import tapguard

log = logging.getLogger("aow")

TITLE = "common/unlock_troop_title"          # mat na (trang/den) cua chu tieu de
BTN = "common/btn_confirm_unlock"
EXIT = "common/btn_cancel_exit"
TITLE_ROI = (0, 95, 540, 125)                # (x, y, w, h)
BTN_ROI = (270, 660, 270, 200)               # chi nua PHAI: nut "Den" nam ngoai vung tim
GO_ZONE = (40, 690, 265, 815)                # (x0, y0, x1, y1) quanh nut "Den" - cam cham khi popup dang hien
TITLE_TH = 0.7
BTN_TH = 0.85
SCOPE = "unlock_troop"                       # pham vi danh sach den toa do
WHY = "popup mo khoa binh chung -> Xac nhan"


def gold_mask(bgr):
    """Diem anh mau chu tieu de (vang nhat, sang) -> anh 0/255."""
    return cv2.inRange(cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV), (10, 30, 170), (35, 210, 255))


def title_score(img, v):
    """Do khop tieu de "Mo khoa Binh chung nay" (0..1); thieu anh mau -> 0."""
    load = getattr(v, "load", None)
    tpl = load(TITLE) if load else None
    if tpl is None:
        return 0.0
    x, y, w, h = TITLE_ROI
    area = img[y:y + h, x:x + w]
    if area.shape[0] < tpl.shape[0] or area.shape[1] < tpl.shape[1]:
        return 0.0
    return float(cv2.matchTemplate(gold_mask(area), tpl[..., 0], cv2.TM_CCOEFF_NORMED).max())


def find(img, v):
    """-> (x, y, diem) cua nut "Xac nhan" neu anh la popup mo khoa binh chung, nguoc lai None.
    Hop thoai "Roi tro choi?" dang hien -> None (Ctx.cancel_exit bam Huy truoc)."""
    if not isinstance(img, np.ndarray) or img.ndim != 3:
        return None
    p = v.find(img, BTN, th=BTN_TH, roi=BTN_ROI)
    if not p or title_score(img, v) < TITLE_TH or v.find(img, EXIT):
        return None
    return p


def in_go_zone(x, y):
    x0, y0, x1, y1 = GO_ZONE
    return x0 <= x <= x1 and y0 <= y <= y1


def dismiss(ctx, img=None):
    """Popup dang hien -> bam "Xac nhan" roi kiem da dong; chua dong thi bam lai toi khi TapGuard dua toa do vao danh
    sach den (2 lan khong dong). -> None: khong phai popup nay | True: da dong | False: van con (khong bam nua)."""
    img = img if img is not None else ctx.shot()
    hit = find(img, ctx.v)
    if hit is None:
        return None
    guard = tapguard.of(ctx)
    spot = hit[:2]                     # dem theo 1 diem: nhan dien lech 1 px khong thanh "toa do moi"
    while hit is not None:
        if guard.blocked(SCOPE, *spot):
            return False
        if ctx.cancel_exit(img, SCOPE):          # luon kiem hop thoai thoat truoc moi lan bam "Xac nhan"
            img = ctx.shot()
        else:
            log.info("Popup 'Mo khoa Binh chung nay' (buoc %s) -> bam 'Xac nhan' @%d,%d (khong bam 'Den')",
                     getattr(ctx, "step", None), hit[0], hit[1])
            ctx.tap(hit[0], hit[1], wait=1.2, tpl=BTN)
            img = ctx.shot()
            if guard.record(SCOPE, *spot, find(img, ctx.v) is None, "bam 'Xac nhan' ma popup khong dong"):
                guard.ban(SCOPE, *spot, "popup mo khoa binh chung khong dong")
                ctx.save_debug("unlock_troop_stuck")
        hit = find(img, ctx.v)
    log.info("Popup 'Mo khoa Binh chung nay' da dong")
    return True
