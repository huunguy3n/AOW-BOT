"""P13m t108u (chu du an 27/11/2026): bat dau nang nha chinh 7 -> 8 game hien bang bao HET GIAI DOAN TAN THU (het bao
ve tan thu) -> bam "Xac nhan" roi NANG TIEP (bot/build.py upgrade_here). Khong phai vat can, khong dong X.

common/btn_confirm co y KHONG nam trong Ctx.POPUP_CLOSERS (hop thoai "Roi tro choi?" cung co "Xac nhan") -> bang nay
nhan rieng bang CHU, nhu P13k nhan theo tieu de: PHAI co CA HAI nut "Xac nhan" va chu "tan thu" phia tren nut.
Hop thoai thoat dang mo, hoac nut co icon kim cuong -> khong phai bang nay, khong bam.

Chua co anh that: is_novice_text() / find() la ham thuan (anh, chu OCR) -> test offline bang chu gia.
"""
import logging
import os
import re
import time

import cv2
import numpy as np

from aowbot.domain.blockers import normalize
from bot import buttons, ocr, resources, tapguard

log = logging.getLogger("aow")

LOG = "het tan thu -> xac nhan, nang nha chinh"
EXIT = "common/btn_cancel_exit"
CONFIRM_TPLS = ("common/btn_confirm", "common/btn_confirm_unlock", "common/btn_confirm_hero")
CONFIRM_TH = 0.85
CONFIRM_RX = r"\bx\w{1,2}c ?nh\w{1,2}n\b"       # "Xac nhan" (OCR eng mat dau / lech nhe)
BTN_ROI = (0, 250, 540, 660)                    # (x, y, w, h) vung tim nut theo mau + chu
TEXT_X = (20, 500)                              # (x, be ngang) vung doc noi dung bang
TEXT_TOP, TEXT_SPAN, TEXT_GAP = 90, 520, 22     # doc tu tren nut toi sat mep tren nut
# "tan thu" cho phep thieu dau / lech nhe (tanthu, tan thii, tan tnu); khong khop "lan thu", "tang thuong", "tan the"
NOVICE_RX = re.compile(r"(?<![a-z])t[a4]n\W{0,2}t[hn](?:u|ii|v)(?![a-z])")
EXIT_RX = re.compile(r"roi tro choi")
SCOPE = "novice_end"                            # pham vi danh sach den toa do


def is_novice_text(text):
    """Doan chu OCR la bang "het giai doan tan thu"? Ham thuan."""
    s = normalize(text or "")
    return bool(NOVICE_RX.search(s)) and not EXIT_RX.search(s)


def find_confirm(img, v):
    """-> (x, y) nut "Xac nhan" | None: anh mau co san, khong co thi nut mau + chu OCR."""
    for name in CONFIRM_TPLS:
        p = v.find(img, name, th=CONFIRM_TH)
        if p:
            return int(p[0]), int(p[1])
    for b in buttons.with_text(img, CONFIRM_RX, roi=BTN_ROI):
        return b.x, b.y
    return None


def read_text(img, btn):
    """Noi dung bang phia tren nut `btn` (2 kieu nhi phan hoa, noi lai)."""
    y0 = max(TEXT_TOP, btn[1] - TEXT_SPAN)
    h = btn[1] - TEXT_GAP - y0
    if h <= 0:
        return ""
    roi = (TEXT_X[0], y0, TEXT_X[1], h)
    out = []
    for bright in (None, 170):
        out.append(ocr.text(img, roi, scale=2, psm=6, bright=bright) or "")
        if is_novice_text(out[-1]):
            break
    return " ".join(out)


def find(img, v, text=None):
    """-> (x, y) nut "Xac nhan" cua bang het tan thu | None. text=None: tu OCR; truyen text: ham thuan."""
    if not isinstance(img, np.ndarray) or img.ndim != 3 or v.find(img, EXIT):
        return None
    p = find_confirm(img, v)
    if p is None or resources.has_gem(img, v, *p):
        return None
    return p if is_novice_text(read_text(img, p) if text is None else text) else None


def keep_frame(ctx, img):
    """Chua co anh that cua bang nay -> luu khung lan gap vao logs/inv/novice_popup/ (khong tinh la anh loi)."""
    d = os.path.join("logs", "inv", "novice_popup")
    try:
        os.makedirs(d, exist_ok=True)
        idx = getattr(getattr(ctx, "dev", None), "idx", "x")
        cv2.imwrite(os.path.join(d, f"{time.strftime('%Y%m%d-%H%M%S')}-i{idx}.png"), img)
    except (OSError, cv2.error) as e:
        log.debug("novice_popup: khong luu duoc anh: %s", e)


def _frame(ctx, img):
    """Hop thoai thoat game dang mo -> Huy TRUOC (Ctx.cancel_exit) roi chup lai."""
    if isinstance(img, np.ndarray) and ctx.v.find(img, EXIT) and ctx.cancel_exit(img, SCOPE):
        return ctx.shot()
    return img


def confirm(ctx, img=None):
    """Bang het tan thu dang hien -> bam "Xac nhan" roi kiem da dong; khong dong 2 lan -> danh sach den het luot ghe.
    -> None: khong phai bang nay | True: da xac nhan, bang da dong | False: van con (khong bam nua, khong dong X)."""
    img = _frame(ctx, img if img is not None else ctx.settle(max_s=2.0))
    hit = find(img, ctx.v)
    if hit is None:
        return None
    guard = tapguard.of(ctx)
    spot = hit
    keep_frame(ctx, img)
    while hit is not None:
        if guard.blocked(SCOPE, *spot):
            return False
        log.info(LOG)
        ctx.tap(hit[0], hit[1], wait=1.5, tpl="common/btn_confirm")
        hit = find(_frame(ctx, ctx.settle(max_s=2.0)), ctx.v)
        if guard.record(SCOPE, *spot, hit is None, "bam 'Xac nhan' ma bang tan thu khong dong"):
            guard.ban(SCOPE, *spot, "bang het tan thu khong dong")
            ctx.save_debug("novice_popup_stuck")
    return True
