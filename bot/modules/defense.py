"""Phong thu khi bi tan cong: bat khien (Bao Ho Chien Tranh) va/hoac so tan quan di thu thap.

Kich hoat: (1) anh mau canh bao bi tan cong defense/alert_attack.png xuat hien (CAN CAT khi bi danh that),
           (2) nut "Bat khien" tren web (ep chay ngay cho 1 may).
Khien: dang con bao ho -> khong lam gi. Con vat pham -> dung. Het -> mua bang kim cuong neu cho phep VA
khong vuot tran kim cuong/ngay/tai khoan (dem trong data/state.json). Gia co dinh lay tu config.
Gioi han: bot chay lan luot tung may, may dang tat thi khong phan ung duoc.
"""
import re, time, logging
import cv2
from bot import ocr

log = logging.getLogger("aow")
ROWS = {1: "defense/row_1h", 12: "defense/row_12h", 72: "defense/row_3d"}
PRICE = {1: 500, 12: 4800, 72: 25200}
ACTIVE_ROI = (130, 79, 280, 17)   # "Thoi gian co hieu luc 2d:05:54:58"


def edge_red(img):
    """Ti le diem DO o 2 mep trai/phai (y 150-850) -> (trai, phai)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    def frac(x0, x1):
        r = hsv[150:850, x0:x1]
        return float((((r[..., 0] <= 8) | (r[..., 0] >= 170)) & (r[..., 1] >= 120) & (r[..., 2] >= 110)).mean())
    return frac(0, 10), frac(530, 540)


def red_flash(ctx, img=None):
    """Chu du an 2026-11-21: "man hinh nhay do = can cu dang bi tan cong". Chi tin khi dang o THANH PHO / BAN DO
    (bang TT phuc loi nen do cung lam mep do 49 %) va 2/3 khung lien tiep 2 mep deu >= 60 % do."""
    from bot import screens
    img = img if img is not None else ctx.shot()
    if screens.identify(img, ctx.v)[0] not in ("city", "world"):
        return False
    hits = 0
    for k in range(3):
        f = img if k == 0 else ctx.shot()
        l, r = edge_red(f)
        hits += l >= 0.6 and r >= 0.6
        if k < 2:
            time.sleep(0.35)
    return hits >= 2


def under_attack(ctx, img=None):
    img = img if img is not None else ctx.shot()
    if ctx.v.has("defense/alert_attack") and ctx.v.find(img, "defense/alert_attack"):
        return True
    if ctx.cfg.get("defense", {}).get("red_flash", True):
        l, r = edge_red(img)
        if l >= 0.6 and r >= 0.6 and red_flash(ctx, img):
            log.warning("Man hinh nhay do o 2 mep -> can cu dang bi tan cong")
            if getattr(ctx, "store", None):
                ctx.store.update(ctx.dev.idx, last_attack=time.time())
            return True
    return False


def _spent_today(ctx):
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    return (st.get("gems_spent") or {}).get(time.strftime("%Y-%m-%d"), 0)


def _add_spent(ctx, n):
    if not getattr(ctx, "store", None):
        return
    st = ctx.store.inst(ctx.dev.idx)
    d = dict(st.get("gems_spent") or {})
    day = time.strftime("%Y-%m-%d")
    d = {day: d.get(day, 0) + n}  # chi giu hom nay
    ctx.store.update(ctx.dev.idx, gems_spent=d)


def shield(ctx, force=False):
    d = ctx.cfg.get("defense", {})
    hours = int(d.get("shield_hours", 1))
    ctx.ensure_city()
    gems_before = ocr.topbar(ctx.shot()).get("gems")
    if not ctx.tap_tpl("defense/btn_shield_icon", wait=1.5) or not ctx.wait_for("defense/title", timeout=3):
        log.warning("Khong mo duoc bang Bao Ho Chien Tranh")
        return "error"
    img = ctx.shot()
    digits = re.findall(r"\d", ocr.text(img, ACTIVE_ROI, "0123456789d:"))
    if any(c != "0" for c in digits):  # con thoi gian bao ho (00:00:00 / trong = khong con)
        log.info("Dang con bao ho (%s) - khong can bat khien", ocr.text(img, ACTIVE_ROI))
        ctx.back_out()
        return "active"
    row = ctx.v.find(img, ROWS[hours], th=0.95)
    if not row:
        log.warning("Khong thay dong khien %dh", hours)
        ctx.back_out()
        return "error"
    owned = ocr.text(img, (64, row[1] + 53, 22, 16), "0123456789", psm=8)
    owned = int(owned) if owned.isdigit() else 0
    btn = (469, row[1] + 27)
    if owned <= 0:
        price, cap = PRICE[hours], d.get("gem_cap_daily", 0)
        spent = _spent_today(ctx)
        if not d.get("shield_buy_gems"):
            log.warning("Het vat pham khien %dh va khong cho phep mua bang kim cuong", hours)
            ctx.back_out()
            return "no_item"
        if spent + price > cap or (gems_before is not None and gems_before < price):
            log.warning("Khong mua khien: gia %d, da tieu hom nay %d, tran %d, dang co %s kim cuong",
                        price, spent, cap, gems_before)
            ctx.back_out()
            return "cap"
    ctx.tap(*btn, wait=1.5)
    ctx.tap_tpl("common/btn_confirm", wait=1.5)  # hop thoai xac nhan (neu co)
    ctx.back_out()
    gems_after = ocr.topbar(ctx.shot()).get("gems")
    if owned <= 0 and gems_before is not None and gems_after is not None and gems_after < gems_before:
        _add_spent(ctx, gems_before - gems_after)
    log.info("Da bat khien %dh (%s; kim cuong %s -> %s)", hours,
             "vat pham" if owned > 0 else "mua", gems_before, gems_after)
    return "shielded"


def evacuate(ctx):
    """Gui moi doi hanh quan ranh di thu thap (khong ken mo) de quan khong o trong thanh."""
    from bot.modules import gather
    g = ctx.cfg["gather"]
    saved = dict(g)
    g.update(load_ge_mine=False, only_full=False, min_level=1)
    try:
        return gather.run(ctx)
    finally:
        g.clear(); g.update(saved)


def run(ctx, force=False):
    d = ctx.cfg.get("defense", {})
    if not (force or under_attack(ctx)):
        return None
    log.warning("BI TAN CONG%s - xu ly phong thu", " (bam tay tu web)" if force else "")
    res = shield(ctx, force) if d.get("shield_on_attack", True) else None
    if d.get("evacuate_troops"):
        evacuate(ctx)
    if getattr(ctx, "store", None):
        ctx.store.update(ctx.dev.idx, last_defense={"t": time.time(), "shield": res})
    return res
