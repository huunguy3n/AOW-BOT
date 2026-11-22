"""Xoa huy hieu tin nhan chat chua doc (chu du an 2026-11-22: "bam vao va thoat ra la mat chat").

CHI MO de doc roi thoat: bam icon chat (goc trai thanh pho) -> bang "Tro chuyen" -> bam tung cuoc tro chuyen co so chua doc
(huy hieu tron xanh, ben phai) -> thoat. KHONG go, KHONG gui, KHONG bam duong dan trong tin nhan (chi bam anh dai dien
cuoc tro chuyen o trai). Tat bang reddots.chat_clear: false.
"""
import logging

import cv2
import numpy as np

from bot.badges import red_dots

log = logging.getLogger("aow")

ICON_ROI = (25, 300, 60, 50)        # huy hieu do (so tin nhan) tren icon chat o thanh pho
AVATAR_X = 62                       # anh dai dien cuoc tro chuyen (cot trai cua moi dong)
MAX_ROWS = 6


def unread_rows(img):
    """Huy hieu tron XANH (so chua doc) cua bang Tro chuyen -> [(x, y)] tren xuong. H 100-112, S>=130, V>=190,
    duong kinh 24-40 px, tron (dien tich >= 0,6 khung). Do tren anh bang that cua chu du an 2026-11-22 (badge 31 px)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 100) & (hsv[..., 0] <= 112) & (hsv[..., 1] >= 130) & (hsv[..., 2] >= 190)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, _, st, cen = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, a = (int(v) for v in st[i])
        if 24 <= w <= 40 and 24 <= h <= 40 and 0.8 <= w / h <= 1.25 and a >= 0.6 * w * h and cen[i][0] > 380:
            out.append((int(cen[i][0]), int(cen[i][1])))
    return sorted(out, key=lambda p: p[1])


def clear(ctx):
    """Icon chat co huy hieu -> mo, doc het cuoc tro chuyen chua doc, thoat. -> so cuoc tro chuyen da mo."""
    if not (ctx.cfg.get("reddots", {}) or {}).get("chat_clear", True):
        return 0
    ctx.ensure_city()
    dots = red_dots(ctx.shot(), ICON_ROI)
    if not dots:
        return 0
    x, y = dots[0]
    ctx.tap(x - 14, y + 18, wait=2.0)
    if ctx.is_home():
        log.info("Chat: cham icon khong mo bang Tro chuyen - bo qua")
        return 0
    opened = 0
    for _ in range(MAX_ROWS):
        rows = unread_rows(ctx.shot())
        if not rows:
            break
        bx, by = rows[0]
        ctx.tap(AVATAR_X, by - 30, wait=1.5)       # vao cuoc tro chuyen (chi doc)
        opened += 1
        ctx.back_out(1)                            # ve lai bang Tro chuyen
    log.info("Chat: da mo %d cuoc tro chuyen chua doc", opened)
    ctx.back_out(3)
    ctx.ensure_city()
    return opened
