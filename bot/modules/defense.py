"""Phong thu khi bi tan cong: bat khien (Bao Ho Chien Tranh) va/hoac so tan quan di thu thap.

Kich hoat: (1) anh mau canh bao bi tan cong defense/alert_attack.png xuat hien (CAN CAT khi bi danh that),
           (2) nut "Bat khien" tren web (ep chay ngay cho 1 may).
Khien: dang con bao ho -> khong lam gi. Con vat pham -> dung. Het -> mua bang kim cuong neu cho phep VA
khong vuot tran kim cuong/ngay/tai khoan (dem trong data/state.json). Gia co dinh lay tu config.
Gioi han: bot chay lan luot tung may, may dang tat thi khong phan ung duoc.
"""
import re, time, logging
import cv2
from bot import ocr, tplneed
from aowbot.domain import policy
from aowbot.domain import warday as W
from aowbot.domain.policy import SHIELD_TAP as TAP, shield_spend as spent_amount

log = logging.getLogger("aow")
ROWS = {1: "defense/row_1h", 8: "defense/row_8h", 12: "defense/row_12h", 24: "defense/row_24h", 72: "defense/row_3d"}
ROW_STEP = 105             # khoang cach doc giua 2 dong khien (anh bang 28/11/2026: 1h, 12h, 24h, 3d cach ~105 px)
PRICE = dict(W.PRICE)   # 1h 500, 12h 4800, 3d 25200 kim cuong. Dong 8h = Hiep uoc hoa binh (mien phi) -> peace()
PEACE_LABEL_DY = (-15, 24)  # chu "Mien phi" phia tren nut Dung cua dong Hiep uoc (y dong - 15, cao 24)
FREE_RX = re.compile(r"mi\w{0,2}n\s*ph")
_CAP_CFG = object()        # shield(cap=...) mac dinh: lay defense.gem_cap_daily
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
    # P5-4: chua co anh mau canh bao -> chi dua vao mep do nhay (red_flash); log 'thieu anh mau' toi da 1 lan/gio
    if tplneed.has(ctx.v, "defense/alert_attack", "canh bao bi tan cong") and ctx.v.find(img, "defense/alert_attack"):
        return True
    if ctx.cfg.get("defense", {}).get("red_flash", True):
        l, r = edge_red(img)
        if l >= 0.6 and r >= 0.6 and red_flash(ctx, img):
            log.warning("Man hinh nhay do o 2 mep -> can cu dang bi tan cong")
            if getattr(ctx, "store", None):
                ctx.store.update(ctx.dev.idx, last_attack=time.time())
            return True
    return False


def _day(now=None):
    """Ngay tinh tran kim cuong = ngay cua server game (reset 0h UTC), khong theo gio may."""
    return time.strftime("%Y-%m-%d", time.gmtime(now))


def spent_today(gems_spent, now=None):
    """Kim cuong da tieu trong ngay. Lay max voi khoa ngay theo gio may: du lieu ghi truoc 2026-11-21 dung ngay
    dia phuong -> luc chuyen doi khong duoc dem thieu (dem thua thi chi la khong mua, an toan)."""
    d = gems_spent or {}
    return max(d.get(_day(now), 0), d.get(time.strftime("%Y-%m-%d", time.localtime(now)), 0))


def _spent_today(ctx):
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    return spent_today(st.get("gems_spent"))


WAR_SRC = "shield_war"


def counts_toward_cap(src):
    """P7-12 (chu du an 2026-11-24): kim cuong mua khien NGAY CHIEN TRANH khong gioi han va KHONG an vao tran 2000/ngay
    ngoai chien tranh (cua so keo sang 00:30 chu nhat -> truoc day bi bot mat tran cua ngay thuong)."""
    return src != WAR_SRC


def _add_spent(ctx, n, src="shield"):
    """Cong kim cuong da tieu vao tran ngay (state.json) + so kim cuong memory.db (gem_ev, report_ro P6).
    Mua ngay chien tranh (src shield_war): chi ghi gem_ev + gems_spent_war, khong tinh vao tran ngay thuong."""
    log.warning("KIM CUONG: may #%s tieu %d (nguon %s)", ctx.dev.idx, n, src)
    if getattr(ctx, "mem", None):
        ctx.mem.log_gem(ctx.dev.idx, src, n)
    if not getattr(ctx, "store", None):
        return
    st = ctx.store.inst(ctx.dev.idx)
    day = _day()
    if not counts_toward_cap(src):
        w = dict(st.get("gems_spent_war") or {})
        ctx.store.update(ctx.dev.idx, gems_spent_war={day: (w.get(day) or 0) + n})
        return
    d = {day: spent_today(st.get("gems_spent")) + n}  # chi giu hom nay
    ctx.store.update(ctx.dev.idx, gems_spent=d)


def shield_choice(owned, gems, price, spent, cap, allow_buy):
    """Luat o aowbot.domain.policy.shield_decision (POL: mot luat mot cho); giu ten cu cho ma goi hien co."""
    return policy.shield_decision(policy.ShieldInputs(owned, gems, price, spent, cap, allow_buy))


def parse_owned(text):
    """So vat pham khien dang co -> int, hoac None neu OCR khong ra so (KHONG doan la 0)."""
    t = (text or "").strip()
    return int(t) if t.isdigit() else None


def missing_tpls(v, hours):
    """Anh mau can de bat khien `hours` gio ma chua co (moi ten log 'thieu anh mau' qua tplneed, 1 lan/gio)."""
    need = [("defense/btn_shield_icon", "icon khien thanh pho"), ("defense/title", "tieu de Bao Ho Chien Tranh")]
    if hours == 24 and not tplneed.has(v, ROWS[24], "dong khien 24h (tam tim bang OCR duoi dong 12h)"):
        need.append((ROWS[12], "dong khien 12h (moc de tim dong 24h)"))
    else:
        need.append((ROWS[hours], f"dong khien {hours}h trong bang Bao Ho Chien Tranh"))
    return [n for n, why in need if not tplneed.has(v, n, why)]


def row24_y(y12, y3d, title_text):
    """Ham thuan: y dong khien 24h khi chua co anh mau -> giua dong 12h va 3 ngay (hoac 12h + ROW_STEP), chi nhan
    khi chu tieu de doc duoc o do co '24'. title_text(y) -> chu OCR tieu de quanh y. -> y | None."""
    if y12 is None:
        return None
    y = (y12 + y3d) // 2 if y3d is not None and y3d - y12 > ROW_STEP * 1.5 else y12 + ROW_STEP
    return y if re.search(r"24", title_text(y) or "") else None


def find_row(ctx, img, hours):
    """-> (x, y, score) dong khien `hours` | None. Dong 24h chua co anh mau -> tim bang OCR (row24_y)."""
    if hours != 24 or tplneed.has(ctx.v, ROWS[24], ""):
        return ctx.v.find(img, ROWS[hours], th=0.95)
    r12 = ctx.v.find(img, ROWS[12], th=0.9)
    if not r12:
        return None
    r3 = ctx.v.find(img, ROWS[72], th=0.85)
    y = row24_y(r12[1], r3[1] if r3 else None,
                lambda yy: ocr.text(img, (90, max(0, int(yy) - 14), 330, 28)))
    if y is None:
        return None
    log.info("Dong khien 24h tim bang OCR @y=%d (chua co anh mau defense/row_24h)", y)
    return (r12[0], int(y), 0.0)


def shield(ctx, force=False, hours=None, allow_buy=None, extend=False, cap=_CAP_CFG, src="shield"):
    """hours/allow_buy: ghi de cau hinh. extend=True: bat them khi van con khien (gia han truoc khi het) thay vi coi
    la 'active'. cap: tran kim cuong/ngay (mac dinh defense.gem_cap_daily; None = khong gioi han - CHI ngay chien
    tranh, chu du an 2026-11-23). src: nguon ghi so kim cuong (shield | shield_war)."""
    d = ctx.cfg.get("defense", {})
    hours = int(hours if hours is not None else d.get("shield_hours", 1))
    buy = bool(d.get("shield_buy_gems")) if allow_buy is None else bool(allow_buy)
    cap = d.get("gem_cap_daily", 0) if cap is _CAP_CFG else cap
    if hours == 8:
        return peace(ctx)
    if hours not in PRICE and hours not in W.ITEM_ONLY:
        log.error("defense.shield_hours = %s khong hop le (chi %s) - khong bat khien", hours, sorted(ROWS))
        return "error"
    missing = missing_tpls(ctx.v, hours)
    if missing:   # P5-4: thieu anh mau -> KHONG mo bang / khong bam mo (dong khien bam theo toa do cua dong)
        log.warning("Khong bat khien %dh: thieu anh mau %s", hours, ", ".join(missing))
        return "missing_tpl"
    ctx.ensure_city()
    gems_before = ocr.topbar(ctx.shot()).get("gems")
    if not ctx.tap_tpl("defense/btn_shield_icon", wait=1.5) or not ctx.wait_for("defense/title", timeout=3):
        log.warning("Khong mo duoc bang Bao Ho Chien Tranh")
        return "error"
    img = ctx.shot()
    digits = re.findall(r"\d", ocr.text(img, ACTIVE_ROI, "0123456789d:"))
    if not extend and any(c != "0" for c in digits):  # con thoi gian bao ho (00:00:00 / trong = khong con)
        log.info("Dang con bao ho (%s) - khong can bat khien", ocr.text(img, ACTIVE_ROI))
        ctx.back_out()
        return "active"
    row = find_row(ctx, img, hours)
    if not row:
        log.warning("Khong thay dong khien %dh", hours)
        ctx.back_out()
        return "error"
    owned = parse_owned(ocr.text(img, (64, row[1] + 53, 22, 16), "0123456789", psm=8))
    btn = (469, row[1] + 27)
    price = PRICE.get(hours)
    if price is None:               # dong chi co vat pham (24h): khong bao gio mua
        buy = False
        price = 10 ** 9
    act, why = shield_choice(owned, gems_before, price, _spent_today(ctx), cap, buy)
    if act not in TAP:
        log.warning("Khong bat khien %dh: %s", hours, why)
        ctx.back_out()
        return act
    if act == "buy":
        log.warning("MUA khien %dh bang %d kim cuong (nguon %s, kim cuong dang co %s): %s", hours, price, src,
                    gems_before, why)
    else:
        log.info("Bat khien %dh: %s", hours, why)
    ctx.tap(*btn, wait=1.5)
    ctx.tap_tpl("common/btn_confirm", wait=1.5)  # hop thoai xac nhan (neu co)
    ctx.back_out()
    gems_after = ocr.topbar(ctx.shot()).get("gems")
    if act == "buy":
        _add_spent(ctx, spent_amount(gems_before, gems_after, price), src)
    elif gems_before is not None and gems_after is not None and gems_after < gems_before:
        # 'use' nhung kim cuong giam: OCR doc nham so vat pham (vd 0 -> 1) va nut da MUA -> van tinh vao tran
        log.warning("Dung vat pham khien nhung kim cuong giam %d -> %d: tinh vao tran ngay", gems_before, gems_after)
        _add_spent(ctx, gems_before - gems_after, src)
    log.info("Da bat khien %dh (%s; kim cuong %s -> %s)", hours,
             "vat pham" if act == "use" else "mua", gems_before, gems_after)
    return "shielded"


def peace_free(text):
    """Chu OCR phia tren nut dong Hiep uoc co 'Mien phi' (mat dau) -> True. Khong doc duoc -> False (khong bam)."""
    return bool(FREE_RX.search((text or "").lower()))


PREP_RX = re.compile(r"chu\w{0,2}n\s*b|prepar")


def peace_label_status(text):
    """P12-1: chu OCR phia tren nut dong Hiep uoc -> 'ready' (Mien phi) | 'preparing' (Chuan bi / Preparing) |
    'cooldown' (con lai: dong ho hoi chieu / khong doc duoc - an toan: khong bam)."""
    t = (text or "").lower()
    if FREE_RX.search(t):
        return "ready"
    if PREP_RX.search(t):
        return "preparing"
    return "cooldown"


def panel_active(img):
    """Bang Bao Ho Chien Tranh dang mo: dong 'Thoi gian co hieu luc' co so khac 0 -> dang con bao ho."""
    digits = re.findall(r"\d", ocr.text(img, ACTIVE_ROI, "0123456789d:"))
    return any(c != "0" for c in digits)


def peace(ctx, skip_if_active=False):
    """Hiep uoc hoa binh (dong 8h, chu du an 2026-11-23 dong y dung): MIEN PHI, chuan bi 1h roi bao ho 8h, hoi 14h.
    Chi bam 'Dung' khi phia tren nut co chu 'Mien phi' (dang hoi / khong doc duoc -> khong bam). Kiem lai: sau khi
    bam chu 'Mien phi' phai mat. -> 'peace' | 'cooldown' | 'preparing' | 'missing_tpl' | 'error'."""
    missing = missing_tpls(ctx.v, 8)
    if missing:
        log.warning("Khong dung Hiep uoc: thieu anh mau %s", ", ".join(missing))
        return "missing_tpl"
    ctx.ensure_city()
    if not ctx.tap_tpl("defense/btn_shield_icon", wait=1.5) or not ctx.wait_for("defense/title", timeout=3):
        log.warning("Khong mo duoc bang Bao Ho Chien Tranh")
        return "error"

    def label(img, row):
        return ocr.text(img, (400, row[1] + PEACE_LABEL_DY[0], 130, PEACE_LABEL_DY[1]))
    img = ctx.shot()
    if skip_if_active and panel_active(img):   # P9-2 khien som: dang con bao ho -> khong dung Hiep uoc
        log.info("Dang con bao ho (%s) - khong dung Hiep uoc", ocr.text(img, ACTIVE_ROI))
        ctx.back_out()
        return "active"
    row = ctx.v.find(img, ROWS[8], th=0.9)
    if not row:
        log.warning("Khong thay dong Hiep uoc hoa binh")
        ctx.back_out()
        return "error"
    st = peace_label_status(label(img, row))
    if st != "ready":
        log.info("Hiep uoc hoa binh: trang thai %s (khong thay chu 'Mien phi') - khong bam",
                 "CHUAN BI" if st == "preparing" else "HOI CHIEU")
        ctx.back_out()
        return st
    log.info("Dung Hiep uoc hoa binh (mien phi, chuan bi 1h)")
    ctx.tap(469, row[1] + 27, wait=1.5)
    ctx.tap_tpl("common/btn_confirm", wait=1.5)   # hop thoai xac nhan (neu co) - dong mien phi
    img = ctx.shot()
    row2 = ctx.v.find(img, ROWS[8], th=0.9)
    ok = bool(row2) and not peace_free(label(img, row2))
    ctx.back_out()
    if not ok:
        log.warning("Hiep uoc hoa binh: bam 'Dung' nhung chu 'Mien phi' van con / mat bang -> coi nhu chua dung")
        return "error"
    return "peace"


def war_shield(ctx, need_s, buy=True, cap=None):
    """Ngay chien tranh: thu lan luot cac dong khien (W.shield_options: vat pham truoc, roi mua) toi khi bat duoc.
    -> so gio khien da bat | 0. Mua bang kim cuong khong gioi han khi cap None (chu du an 2026-11-23)."""
    for hours, may_buy in W.shield_options(need_s, buy):
        res = shield(ctx, hours=hours, allow_buy=may_buy, extend=True, cap=cap, src=WAR_SRC)
        if res == "shielded":
            return hours
        log.info("Khien %dh (%s): %s -> thu dong khac", hours, "mua" if may_buy else "vat pham", res)
    return 0


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
    res = None
    if d.get("shield_on_attack", True):
        from bot.modules import warday
        c = warday.wcfg(ctx.cfg)
        now = time.time()
        w = warday.window(getattr(ctx, "mem", None), ctx.dev.idx, ctx.cfg, now)
        if w is not None:   # ngay chien tranh: moi loai khien, mua khong gioi han (chu du an 2026-11-23)
            hours = war_shield(ctx, max(w.end - now, 3600), bool(c["buy_gems"]), c["gem_cap"])
            res = "shielded" if hours else "error"
        else:
            # P13-4: ngay thuong chi Hiep uoc 8h MIEN PHI (khong vat pham, khong kim cuong)
            res = peace(ctx)
            log.info("Bi tan cong ngay thuong: chi dung Hiep uoc mien phi -> %s", res)
    if d.get("evacuate_troops"):
        evacuate(ctx)
    if getattr(ctx, "store", None):
        ctx.store.update(ctx.dev.idx, last_defense={"t": time.time(), "shield": res})
    return res
