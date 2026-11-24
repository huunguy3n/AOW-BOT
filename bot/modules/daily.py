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


# P9-4 (chu du an 2026-11-24, anh nhiem_vu_hang_ngay_ruong_50_phat_sang: 55 diem, ruong 50 sang): moc diem
MILESTONES = (10, 30, 50, 80, 120)
MILESTONE_X = (180, 249, 319, 388, 458)   # tam ruong moc tren thanh tien do (do tren anh chu du an)
SCORE_ROI = (70, 295, 45, 30)            # so diem nang dong duoi huy hieu (anh chu du an: "55")


def read_score(img, roi=SCORE_ROI):
    from bot import ocr
    t = ocr.text(img, roi, "0123456789")
    return int(t) if t.isdigit() and int(t) <= 300 else None


def milestone_of(x, xs=MILESTONE_X, ms=MILESTONES, tol=30):
    """Moc diem cua ruong o hoanh do x | None."""
    best = min(range(len(xs)), key=lambda i: abs(xs[i] - x))
    return ms[best] if abs(xs[best] - x) <= tol else None


def sparkle(img, p, r=22):
    """So diem anh vang sang (tia lap lanh) quanh ruong - ruong 'phat sang' co ~25+, ruong thuong ~4."""
    x, y = int(p[0]), int(p[1])
    hsv = cv2.cvtColor(img[max(0, y - r - 10):y + r - 10, max(0, x - r):x + r], cv2.COLOR_BGR2HSV)
    return int(((hsv[..., 0] >= 18) & (hsv[..., 0] <= 35) & (hsv[..., 1] >= 80) & (hsv[..., 2] >= 200)).sum())


def milestone_targets(pts, score, img=None):
    """P9-4: ruong can bam = ruong mau (du diem) co moc <= diem (diem None -> moi ruong mau). Ruong phat sang truoc,
    roi trai -> phai. Ham thuan."""
    out = []
    for p in pts:
        m = milestone_of(p[0])
        if m is not None and score is not None and m > score:
            continue
        out.append(p)
    glow = (lambda p: sparkle(img, p)) if isinstance(img, np.ndarray) else (lambda p: 0)
    return sorted(out, key=lambda p: (-(glow(p) >= 12), p[0]))


def claim_chests(ctx, by_color=False, tap=None):
    """Ruong moc diem: bam LAN LUOT moi ruong du diem toi khi het ruong sang (P9-4: truoc day ruong dau khong co nut
    nhan (da nhan) -> break, ruong 50 dang sang bi bo). tap(x, y): ham cham (Su menh truyen ham co vung cho phep)."""
    chests = ctx.v.list(P + "chest_")
    n, tried = 0, set()
    tap = tap or (lambda x, y: ctx.tap(x, y, wait=1.2) or True)
    for _ in range(8):  # moi lan nhan thi bang ve lai -> chup lai
        img = ctx.shot()
        pts = [p[:2] for c in chests for p in ctx.v.find_all(img, c)]
        if not pts and by_color:
            pts = ready_chests(img)
        pts = [p for p in milestone_targets(pts, read_score(img) if by_color else None, img)
               if (p[0] // 30) not in tried]
        if not pts:
            break
        x, y = pts[0]
        tried.add(x // 30)
        if not tap(x, y):
            continue
        from bot import screens
        if isinstance(img, np.ndarray) and screens.same(img, ctx.shot()):
            continue                     # cham khong mo bang nao (ruong da nhan) -> KHONG bam nut dong (dong ca bang)
        # cham ruong -> hien bang chi tiet co nut "Nhan"
        if ctx.tap_tpl(P + "btn_chest_claim", wait=1.5) or ctx.claim_buttons(max_taps=1):
            ctx.dismiss_reward()
            n += 1
            log.info("Ruong moc %s diem: nhan", milestone_of(x))
            continue
        log.info("Ruong @%d,%d: khong co nut nhan (da nhan / chua du) - dong, thu ruong ke", x, y)
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
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
