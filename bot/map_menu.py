"""P13l (chu du an t104u/t105u, anh world_tap_player_city.png + arrow_miss_world.png): menu vong tron tren ban do.

  'city' : menu CAN CU NGUOI CHOI (Trinh sat / Tap ket / Tin tuc / Tan cong) - bam "Tan cong" la KHAI CHIEN. Nhan ra
           la DONG NGAY, khong bao gio bam nut nao tren menu nay.
  'land' : menu o dat trong (Chuyen thanh / Chiem linh) = cham hut -> dong (khong doi thanh pho, khong chiem dat).
Dong bang phim Back (ban do: menu mo thi Back chi dong menu), toa do vua cham vao danh sach den (tapguard 'world').
Ngoai le "Thu thap" (menu mo cua minh co nut gather/btn_gather): khong phai 2 menu tren. Cuop xe tinh the (play.py)
khong dung menu nay. "Tan cong" o bang phien quan / tinh bao / chien dich la nut chu nhat, khong khop mau vong tron.

classify() / find_buttons() la ham thuan (anh -> ket qua); dismiss() thao tac qua Ctx.
Mau: templates/map/menu_*.png (tam bieu tuong 32x32). Do: khop dung 1,0; anh khac cao nhat 0,66.
"""
import logging
import time

import cv2
import numpy as np

from bot import tapguard

log = logging.getLogger("aow")

PLAYER_BUTTONS = ("menu_scout", "menu_rally", "menu_news", "menu_attack")
LAND_BUTTONS = ("menu_relocate", "menu_occupy")
GATHER = "gather/btn_gather"
TH = 0.8
COARSE_TH = 0.65            # vong tho tren anh xam thu nho 1/2
SPAN = 320                  # cac nut cung 1 menu cach nhau toi da chung nay (do: 190 x 85)
SCOPE = "world"             # pham vi danh sach den toa do tren ban do
LOG_CITY = "tap trung can cu nguoi choi -> dong"
LOG_LAND = "tap o dat trong (menu Chuyen thanh / Chiem linh) -> dong"
CLOSE_TRIES = 3
TAP_MEMORY_S = 20           # lan cham gan nhat trong chung nay giay -> toa do do mo menu


def _gray_half(a):
    g = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY) if a.ndim == 3 else a
    return cv2.resize(g, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)


def _find(small, img, v, name):
    """Tim nhanh: tho tren anh 1/2 roi xac nhan bang so khop day du quanh diem do -> (x, y) | None."""
    tpl = v.load(f"map/{name}")
    if tpl is None:
        return None
    t = _gray_half(tpl)
    if small.shape[0] < t.shape[0] or small.shape[1] < t.shape[1]:
        return None
    res = cv2.matchTemplate(small, t, cv2.TM_CCOEFF_NORMED)
    res[~np.isfinite(res)] = 0
    _, score, _, loc = cv2.minMaxLoc(res)
    if score < COARSE_TH:
        return None
    h, w = tpl.shape[:2]
    cx, cy = loc[0] * 2 + w // 2, loc[1] * 2 + h // 2
    x0, y0 = max(0, cx - w // 2 - 6), max(0, cy - h // 2 - 6)
    p = v.find(img, f"map/{name}", th=TH, roi=(x0, y0, w + 12, h + 12))
    return (int(p[0]), int(p[1])) if p else None


def find_buttons(img, v, names=PLAYER_BUTTONS + LAND_BUTTONS):
    """-> {ten nut: (x, y)} cac nut vong tron nhin thay. Vision gia / thieu mau -> {}."""
    if not isinstance(img, np.ndarray) or img.ndim != 3 or not hasattr(v, "load"):
        return {}
    small = _gray_half(img)
    out = {}
    for n in names:
        p = _find(small, img, v, n)
        if p:
            out[n] = p
    return out


def _compact(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return max(xs) - min(xs) <= SPAN and max(ys) - min(ys) <= SPAN


def classify(img, v):
    """-> 'city' (menu can cu nguoi choi) | 'land' (menu o dat trong) | None."""
    hit = find_buttons(img, v)
    if not hit or v.find(img, GATHER):
        return None
    if "menu_relocate" in hit:
        # "Chiem linh" cung bieu tuong kiem cheo voi "Tan cong" (khop 0,86) -> nhan theo nut "Chuyen thanh"
        pair = [hit[n] for n in ("menu_relocate", "menu_occupy", "menu_attack") if n in hit]
        if len(pair) >= 2 and _compact(pair):
            return "land"
    found = {n: hit[n] for n in PLAYER_BUTTONS if n in hit}
    if "menu_attack" not in found and "menu_occupy" in hit:
        found["menu_attack"] = hit["menu_occupy"]
    # >= 2 nut, co it nhat 1 nut khong phai kiem cheo, nam gon trong 1 menu
    if len(found) >= 2 and set(found) - {"menu_attack"} and _compact(list(found.values())):
        return "city"
    return None


def blocked(ctx, x, y):
    """Toa do ban do da tung mo menu can cu / dat trong trong luot ghe nay?"""
    return tapguard.of(ctx).blocked(SCOPE, x, y)


def _close(ctx, img):
    """Dong menu: Back (toi da 2 lan, huy hop thoai thoat neu hien); van con -> nut "Thanh pho" (roi ban do)."""
    for k in range(CLOSE_TRIES):
        if k < CLOSE_TRIES - 1:
            ctx.dev.back()
        else:
            p = ctx.v.find(img, "common/btn_to_city")
            if not p:
                break
            ctx.dev.tap(p[0], p[1])
        time.sleep(0.8)
        img = ctx.shot()
        q = ctx.v.find(img, "common/btn_cancel_exit")
        if q:                       # Back mo "Roi tro choi?" = menu da dong tu truoc -> Huy
            ctx.dev.tap(q[0], q[1])
            time.sleep(0.6)
            img = ctx.shot()
        if not classify(img, ctx.v):
            return True
    log.warning("Menu ban do khong dong duoc sau %d lan - khong bam gi tren menu", CLOSE_TRIES)
    return False


def dismiss_if_open(ctx, img):
    """Nhu dismiss(img) nhung khong chup them khi anh khong co menu (goi o moi lan cham / vai khung sau cham)."""
    if img is None or not classify(img, ctx.v):
        return None
    return dismiss(ctx, img)


def dismiss(ctx, img=None):
    """Menu can cu nguoi choi / o dat trong dang mo -> dong, danh sach den diem vua cham. -> 'city' | 'land' | None."""
    ctx._menu_watch = 0                      # chan de quy: shot() trong luc dong khong goi lai dismiss
    img = img if img is not None else ctx.shot()
    kind = classify(img, ctx.v)
    if not kind:
        return None
    if kind == "city":
        log.warning(LOG_CITY)
    else:
        log.info(LOG_LAND)
    last = getattr(ctx, "_last_tap", None)
    if last and time.time() - last[2] <= TAP_MEMORY_S:
        tapguard.of(ctx).ban(SCOPE, last[0], last[1], "mo menu " + kind)
    ctx._last_tap = None
    ctx._menu_closed = getattr(ctx, "_menu_closed", 0) + 1
    ctx.last_menu = kind
    _close(ctx, img)
    ctx._menu_watch = 0
    ctx._menu_closed_seq = getattr(ctx.dev, "act_seq", None)
    return kind
