"""P13l (chu du an t99u, 4 anh tests/fixtures/p13l/res_*.png): bo sung tai nguyen khi thieu - CHI goi trong tui.

Popup "Thieu tai nguyen:" (luyen / xay / nang nha chinh / nghien cuu):
  nut TRAI xanh dam "Dung dao cu"  -> DUOC bam (chi mo man do mien phi, khong tieu gi);
  nut PHAI teal + icon kim cuong   -> KHONG BAO GIO bam.
-> man "Bo sung tai nguyen" (tab tai nguyen thieu da chon san) -> goi NHO NHAT con hang = nut "Dung" xanh dam tren cung
   (hang het hang X0 chi co nut teal + gia kim cuong: bo) -> bang so luong (giu so game dien san, khong keo thanh)
-> "Dung" -> kiem "Luu tru" tang -> mui ten quay lai goc tren trai -> ve man cu, ben goi THAO TAC LAI; con thieu thi
   popup hien lai -> lap, toi da resources.max_per_action lan / thao tac, max_per_visit goi / luot ghe.
Khong con goi mien phi -> dong, bo qua. forbidden() chan moi lan cham cua Ctx vao nut kim cuong cua 2 man nay.

find_popup / find_list / find_dialog / forbidden / storage_up la ham thuan (anh -> ket qua).
"""
import logging
import time
from typing import NamedTuple

import cv2
import numpy as np

from bot import ocr

log = logging.getLogger("aow")

MSG = "common/msg_insufficient"        # chu do "Thieu tai nguyen:"
USE_ITEMS = "common/btn_use_items"     # nut trai "Dung dao cu"
X_RES = "common/btn_x_res"             # X do cua popup
TITLE = "common/res_title"             # "Bo sung tai nguyen"
USE = "common/btn_res_use"             # "Dung" tung hang
USE_BIG = "common/btn_res_use_big"     # "Dung" cua bang so luong
PLUS = "common/res_plus"               # nut "+" thanh so luong
GEM = "common/res_gem"                 # icon kim cuong tren nut
BACK = ("common/btn_back", "common/btn_back2")
CLOSE = (X_RES, "common/btn_close", "common/btn_x", "common/btn_x_small")

MSG_ROI = (0, 100, 420, 700)           # (x, y, w, h) chu do: nua trai, giua man (kiem moi lan cham -> hep)
MSG_TH = 0.8
BTN_TH = 0.85
GEM_TH = 0.8
BLUE_H = (92, 115)                     # nut "Dung" / "Dung dao cu" H ~97; nut kim cuong (teal) H ~87
TEAL_H = (70, 91)
LEFT_X = 270                           # nut mien phi cua popup nam nua trai, nut kim cuong nua phai
BTN_BELOW_MSG = (60, 220)              # nut cach chu "Thieu tai nguyen" ve phia duoi (do 125)
TITLE_ROI = (0, 0, 540, 90)
LIST_ROI = (300, 130, 240, 830)
BACK_ROI = (0, 0, 130, 80)
STORAGE_ROI = (-100, 88, 270, 48)      # (dx, dy, w, h) tinh tu tam tieu de: o "Luu tru ... N"
CHANGED_TH = 3.0                       # khong doc duoc so: o luu tru doi it nhat chung nay (lech trung binh 0-255)
LOOKS = 5
EMPTY_MAX = 3        # mo man bo sung ma khong con goi mien phi qua chung nay lan / luot ghe -> thoi mo

NONE, REFILLED, NO_FREE, FAIL = "none", "refilled", "no_free", "fail"
DEFAULTS = {"refill": True, "max_per_action": 4, "max_per_visit": 20}


class Popup(NamedTuple):
    msg: tuple                         # (x, y) chu "Thieu tai nguyen"
    use: tuple | None                  # (x, y) nut "Dung dao cu" (None = khong co nut mien phi)


def rcfg(cfg):
    return {**DEFAULTS, **((cfg or {}).get("resources") or {})}


def _hue(img, x, y, half=(35, 12)):
    patch = img[max(0, y - half[1]):y + half[1], max(0, x - half[0]):x + half[0]]
    if not patch.size:
        return None, 0.0
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    return float(np.median(hsv[:, 0])), float(np.median(hsv[:, 1]))


def is_blue(img, x, y):
    h, s = _hue(img, x, y)
    return h is not None and s > 150 and BLUE_H[0] <= h <= BLUE_H[1]


def is_teal(img, x, y):
    h, s = _hue(img, x, y)
    return h is not None and s > 150 and TEAL_H[0] <= h <= TEAL_H[1]


def has_gem(img, v, x, y):
    """Co icon kim cuong tren / quanh nut tam (x, y)?"""
    return bool(v.find(img, GEM, th=GEM_TH, roi=(max(0, x - 75), max(0, y - 30), 150, 70)))


def find_popup(img, v):
    """Popup "Thieu tai nguyen:" -> Popup | None. Nut mien phi phai: khop mau "Dung dao cu", nua TRAI, ngay duoi chu,
    mau xanh dam, khong co icon kim cuong."""
    if not isinstance(img, np.ndarray):
        return None
    m = v.find(img, MSG, th=MSG_TH, roi=MSG_ROI)
    if not m:
        return None
    y0 = int(m[1]) + BTN_BELOW_MSG[0]
    p = v.find(img, USE_ITEMS, th=BTN_TH, roi=(0, max(0, y0 - 25), LEFT_X, BTN_BELOW_MSG[1] - BTN_BELOW_MSG[0] + 50))
    use = None
    if p and p[0] < LEFT_X and p[1] > m[1] and is_blue(img, p[0], p[1]) and not has_gem(img, v, p[0], p[1]):
        use = (int(p[0]), int(p[1]))
    return Popup((int(m[0]), int(m[1])), use)


def find_list(img, v):
    """Man "Bo sung tai nguyen" -> [(x, y)] nut "Dung" MIEN PHI tren -> duoi (goi nho nhat o tren cung); [] = chi con
    hang kim cuong; None = khong phai man nay. Bang so luong dang mo -> None."""
    if not isinstance(img, np.ndarray) or find_dialog(img, v):
        return None
    if not v.find(img, TITLE, th=BTN_TH, roi=TITLE_ROI):
        return None
    rows = [(int(x), int(y)) for x, y, _ in v.find_all(img, USE, th=BTN_TH, roi=LIST_ROI)]
    return sorted((p for p in rows if is_blue(img, *p) and not has_gem(img, v, *p)), key=lambda p: p[1])


def find_dialog(img, v):
    """Bang so luong ("10K kim loai", thanh truot) -> (x, y) nut "Dung" lon | None. Bat buoc co ca nut "+" phia tren."""
    if not isinstance(img, np.ndarray):
        return None
    plus = v.find(img, PLUS, th=BTN_TH)
    if not plus:
        return None
    p = v.find(img, USE_BIG, th=BTN_TH)
    if not p or p[1] <= plus[1] or not is_blue(img, p[0], p[1]) or has_gem(img, v, p[0], p[1]):
        return None
    return int(p[0]), int(p[1])


def forbidden(img, v, x, y):
    """(x, y) roi vao nut kim cuong cua popup thieu tai nguyen (nua phai, hang nut) hoac nut teal gia kim cuong cua man
    bo sung? Ham thuan."""
    if (not isinstance(img, np.ndarray) or img.ndim != 3 or getattr(v, "load", None) is None
            or not (0 <= x < img.shape[1] and 0 <= y < img.shape[0])):
        return False
    if x >= LEFT_X - 10:
        pop = find_popup(img, v)
        if pop:
            lo, hi = ((pop.use[1] - 50, pop.use[1] + 50) if pop.use
                      else (pop.msg[1] + BTN_BELOW_MSG[0], pop.msg[1] + BTN_BELOW_MSG[1]))
            if lo <= y <= hi:
                return True
    if is_teal(img, x, y) and v.find(img, TITLE, th=BTN_TH, roi=TITLE_ROI):
        return True
    return False


# ---------- "Luu tru N" ----------
def _storage_patch(img, v):
    t = v.find(img, TITLE, th=BTN_TH, roi=TITLE_ROI)
    if not t:
        return None
    dx, dy, w, h = STORAGE_ROI
    x, y = max(0, int(t[0]) + dx), max(0, int(t[1]) + dy)
    return (x, y, w, h), img[y:y + h, x:x + w]


def parse_storage(text):
    """"Luu tru kim loai 30.1K" -> 30100; lay SO CUOI cung. None neu khong co so."""
    import re
    found = re.findall(r"\d[\d.,]*\s*[KMB]?(?![A-Za-z])", text or "")
    return ocr.amount(found[-1]) if found else None


def read_storage(img, v):
    """-> (so | None, anh o luu tru | None)."""
    got = _storage_patch(img, v)
    if not got:
        return None, None
    roi, patch = got
    return parse_storage(ocr.text(img, roi, scale=3, psm=7)), patch.copy()


def storage_up(before, after):
    """So luu tru co tang khong? before / after = read_storage(). Doc duoc ca 2 so -> so sanh; khong thi o luu tru phai
    doi hinh."""
    (n0, p0), (n1, p1) = before, after
    if n0 is not None and n1 is not None:
        return n1 > n0
    if p0 is None or p1 is None or p0.shape != p1.shape:
        return False
    return float(cv2.absdiff(p0, p1).mean()) >= CHANGED_TH


# ---------- thao tac ----------
def _wait(ctx, fn, looks=LOOKS, gap=0.7):
    """Chup toi `looks` khung cho toi khi fn(img, v) khac None -> (ket qua, khung)."""
    img = None
    for k in range(looks):
        img = ctx.shot()
        r = fn(img, ctx.v)
        if r is not None:
            return r, img
        if k + 1 < looks:
            time.sleep(gap)
    return None, img


def close_popup(ctx, img=None):
    """Popup thieu tai nguyen dang hien -> bam X (KHONG BAO GIO nut kim cuong). -> True neu popup nay dang hien."""
    img = img if img is not None else ctx.shot()
    if find_popup(img, ctx.v) is None:
        return False
    if not ctx.tap_first(list(CLOSE), wait=0.8, img=img):
        ctx.press_back("thieu tai nguyen", checked=False)
    return True


def _leave_list(ctx):
    """Man bo sung -> mui ten quay lai goc tren trai (bang so luong con mo thi dong X truoc)."""
    for _ in range(3):
        img = ctx.shot()
        if find_dialog(img, ctx.v):
            ctx.tap_first(["common/btn_close", "common/btn_x"], wait=0.8, img=img)
            continue
        if not ctx.v.find(img, TITLE, th=BTN_TH, roi=TITLE_ROI):
            return
        if not ctx.tap_first(list(BACK), wait=1.0, img=img, roi=BACK_ROI):
            ctx.press_back("bo sung tai nguyen", checked=False)


def _use_one(ctx, row, list_img):
    """Dung 1 goi o hang `row` -> True neu "Luu tru" tang."""
    before = read_storage(list_img, ctx.v)
    ctx.tap(row[0], row[1], wait=1.2, tpl=USE)
    big, _ = _wait(ctx, find_dialog, looks=3)
    if big:                          # giu nguyen so luong game dien san - khong keo thanh, khong bam "+"
        ctx.tap(big[0], big[1], wait=1.5, tpl=USE_BIG)
    img = None
    for k in range(LOOKS):
        ctx.dismiss_reward(1)
        img = ctx.shot()
        if find_list(img, ctx.v) is not None and storage_up(before, read_storage(img, ctx.v)):
            return True
        if k + 1 < LOOKS:
            time.sleep(0.7)
    return False


def refill(ctx, img=None):
    """Popup thieu tai nguyen dang hien -> dung 1 goi mien phi nho nhat roi ve man cu.
    -> NONE (khong co popup) | REFILLED (ben goi lam lai thao tac) | NO_FREE (het goi mien phi / tat / het tran:
    popup da dong) | FAIL (khong mo duoc man / luu tru khong tang)."""
    if img is None:
        shot = getattr(ctx, "shot", None)
        img = shot() if shot else None
    pop = find_popup(img, ctx.v) if img is not None else None
    if pop is None:
        return NONE
    rc = rcfg(ctx.cfg)
    used = getattr(ctx, "_refills", 0)
    if not rc["refill"] or used >= rc["max_per_visit"] or pop.use is None or getattr(ctx, "_refill_empty", 0) >= EMPTY_MAX:
        why = ("tat resources.refill" if not rc["refill"] else "khong co nut 'Dung dao cu'" if pop.use is None
               else "het tran goi / luot ghe" if used >= rc["max_per_visit"] else "da het goi mien phi")
        log.info("Thieu tai nguyen: %s -> dong popup, bo qua (khong dung kim cuong)", why)
        close_popup(ctx, img)
        return NO_FREE
    log.info("Thieu tai nguyen -> 'Dung dao cu' @%d,%d (khong bam nut kim cuong)", *pop.use)
    ctx.tap(pop.use[0], pop.use[1], wait=1.5, tpl=USE_ITEMS)
    rows, list_img = _wait(ctx, find_list)
    if rows is None:
        log.warning("Bo sung tai nguyen: khong mo duoc man danh sach")
        ctx.save_debug("refill_no_list")
        close_popup(ctx)
        return FAIL
    if not rows:
        log.info("Bo sung tai nguyen: khong con goi mien phi (chi con hang kim cuong) -> quay lai, khong mua")
        ctx._refill_empty = getattr(ctx, "_refill_empty", 0) + 1     # loai khac co the con goi -> van mo vai lan
        _leave_list(ctx)
        close_popup(ctx)
        return NO_FREE
    ok = _use_one(ctx, rows[0], list_img)
    if ok:
        ctx._refills = used + 1
        log.info("Bo sung tai nguyen: da dung goi nho nhat @%d,%d (goi thu %d trong luot ghe)", *rows[0], used + 1)
    else:
        log.warning("Bo sung tai nguyen: bam 'Dung' @%d,%d ma luu tru khong tang -> dung", *rows[0])
        ctx.save_debug("refill_no_change")
    _leave_list(ctx)
    close_popup(ctx)                  # popup cu co the con nguyen sau khi quay lai
    return REFILLED if ok else FAIL


def retry(ctx, redo):
    """Ngay sau 1 thao tac (huan luyen / nang cap / xay / nghien cuu): popup thieu tai nguyen -> bo sung roi `redo()`
    (bam lai thao tac; tra False = khong bam duoc), lap toi khi het popup, toi da resources.max_per_action lan.
    Con popup sau lan cuoi -> dong. -> NONE (khong thieu) | REFILLED (da bo sung va lam lai, het popup) | NO_FREE |
    FAIL."""
    r = refill(ctx)
    if r != REFILLED:
        return r
    for k in range(rcfg(ctx.cfg)["max_per_action"]):
        if not redo():
            return FAIL
        img = ctx.shot()
        if find_popup(img, ctx.v) is None:
            return REFILLED
        if k + 1 >= rcfg(ctx.cfg)["max_per_action"]:
            break
        r = refill(ctx, img)
        if r != REFILLED:
            return r
    log.info("Thieu tai nguyen: van thieu sau %d goi -> dong popup, bo qua", rcfg(ctx.cfg)["max_per_action"])
    close_popup(ctx)
    return NO_FREE
