"""Nhiem vu: nhan thuong nhiem vu da hoan thanh + ruong diem nang dong (hang ngay).

Bot KHONG tu di lam tung nhiem vu; cac buoc khac (thu thap, huan luyen, nghien cuu,
tro giup...) da lam tang tien do. Nen dat 'daily' sau cung trong vong de nhan duoc nhieu nhat.

Anh mau templates/daily/:
  open_1.png ...    icon nhiem vu tren thanh pho (va buoc phu neu co)
  tab_1.png ...     cac tab: vd tab_1_daily.png (hang ngay), tab_2_main.png (chinh/chuong)
  claim_1.png ...   nut "Nhan" tren tung dong nhiem vu (co the nhieu kieu: xanh, vang)
  chest_1.png ...   ruong diem nang dong DA DU DIEM (co tia sang lap lanh), khong cat ruong khoa/da nhan
  btn_chest_claim.png nut "Nhan" trong bang chi tiet hien ra sau khi cham ruong
  chapter_claim.png (tuy chon) nut nhan thuong chuong o dau bang
"""
import logging
import cv2
import numpy as np

log = logging.getLogger("aow")
P = "daily/"


CHEST_BAND = (0, 230, 540, 90)   # hang ruong moc diem (10/30/50/80/120) o tab Nhiem vu hang ngay


def ready_chests(img, band=CHEST_BAND):
    """Ruong moc diem DA DU DIEM = ruong TIM (co tia sang); ruong chua du / da nhan = xam (S <= ~20).
    Anh mau chest_1 chi khop ~0.70 vi tia sang lap lanh (anh chu du an 2026-11-20, ruong moc 10 @~183,288)
    -> nhan theo MAU. -> [(x, y)] tam ruong, trai sang phai."""
    x0, y0, w0, h0 = band
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] >= 120) & (hsv[..., 0] <= 160) & (hsv[..., 1] >= 90) & (hsv[..., 2] >= 90)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    k, _, st, _ = cv2.connectedComponentsWithStats(m)
    out = [(int(x0 + x + w // 2), int(y0 + y + h // 2)) for x, y, w, h, a in st[1:]
           if 20 <= w <= 60 and 18 <= h <= 50 and a >= 200 and x0 + x + w < 515]
    return sorted(out)


def claim_chests(ctx, by_color=False):
    chests = ctx.v.list(P + "chest_")
    n = 0
    for _ in range(6):  # moi lan nhan thi bang ve lai -> chup lai
        img = ctx.shot()
        pts = [p for c in chests for p in ctx.v.find_all(img, c)]
        if not pts and by_color:
            pts = ready_chests(img)
        if not pts:
            break
        pts.sort(key=lambda p: p[0])  # trai sang phai
        ctx.tap(pts[0][0], pts[0][1], wait=1.2)
        # cham ruong -> hien bang chi tiet co nut "Nhan"
        if not ctx.tap_tpl(P + "btn_chest_claim", wait=1.5):
            log.info("Khong thay nut nhan ruong - dong bang")
            ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
            break
        ctx.dismiss_reward()
        n += 1
    return n


def claim_tab(ctx, claims, max_taps, by_color=False):
    got = ctx.claim_buttons(max_taps=max_taps) if hasattr(ctx, "claim_buttons") else 0   # nut Nhan theo mau + chu
    return got + _claim_tab(ctx, claims, max_taps, by_color)


def _claim_tab(ctx, claims, max_taps, by_color=False):
    if not claims:
        return claim_chests(ctx, by_color)
    # P7-5 (chu du an 2026-11-24): KHONG cuon bang nhiem vu - nhiem vu hoan thanh luon nam tren cung (cuon xuong
    # chi lam lech danh sach, ruong diem nang dong bi day khoi man)
    n = ctx.claim_loop([P + "chapter_claim"] + claims if ctx.v.has(P + "chapter_claim") else claims,
                       max_taps, th=0.9)
    return n + claim_chests(ctx, by_color)


def run(ctx):
    dc = ctx.cfg.get("daily", {})
    max_taps = dc.get("max_taps", 40)
    claims = ctx.v.list(P + "claim_")
    if not claims and not ctx.v.list(P + "chest_"):
        log.info("Chua co anh mau daily/claim_*.png hay chest_*.png - bo qua nhiem vu")
        return 0
    ctx.ensure_city()
    if not ctx.open_route(P):
        log.info("Khong mo duoc bang nhiem vu (thieu/khong thay daily/open_1.png)")
        ctx.save_debug("daily_open")
        return 0
    total = 0
    tabs = ctx.v.list(P + "tab_")
    # None = tab dang mo san khi vao bang (Nhiem vu chuong); anh tab cat o trang thai CHUA chon
    for t in [None] + tabs:
        if t and not ctx.tap_tpl(t, wait=1.2):
            continue
        got = claim_tab(ctx, claims, max_taps, by_color=bool(t) and "daily" in t)   # ruong theo mau: chi tab hang ngay
        log.info("Nhiem vu %s: nhan %d", (t or "").split("/")[-1] or "bang chinh", got)
        total += got
    ctx.ensure_city()
    return total
