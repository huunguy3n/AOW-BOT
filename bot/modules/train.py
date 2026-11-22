"""Huan luyen linh qua bang "Doi ngu huan luyen" (khong can tim nha linh tren ban do).

Luong (giao dien that, man 540x960):
  icon train/queue_icon (goc trai, "0/1") -> bang liet ke nha linh; nha nao NHAN ROI co nut "Den"
  -> cham "Den" -> vao thang man huan luyen -> chon cap linh cao nhat da mo khoa (the cap I..IV
  o vi tri co dinh) -> thanh so luong mac dinh da toi da -> bam "Huan luyen" (nut PHAI).

KHONG BAO GIO bam "Huan luyen ngay" (nut trai, ton kim cuong).
Cap bi khoa: man hinh hien "Khi Xuong ... dat cap N se mo khoa" va KHONG co nut Huan luyen
-> bot thu cap thap hon.
"""
import logging
import time

from bot import ocr, queues, tplneed

log = logging.getLogger("aow")
TPL_MAX = "train/btn_max"          # nut "Toi da" canh thanh so luong (chu du an chup tren #1 - P2)
MAX_ROI = (0, 560, 540, 330)       # vung tim nut toi da (nua duoi man huan luyen)
NORES_FACT = "train_nores"         # {"until": epoch, "n": k}: lan truoc thieu tai nguyen -> khong mo lai toi moc


def open_queue(ctx):
    ctx.ensure_city()
    # th 0,7: so "0/3" doi thanh "1/3" sau khi luyen -> diem khop tut 0,89 -> 0,82 (sat nguong, #0 2026-11-22) nen lan 2/3 'khong thay';
    # cho khac < 0,45 nen nguong thap an toan
    if not ctx.tap_tpl("train/queue_icon", wait=1.5, th=0.7, roi=(0, 90, 120, 320)):
        log.info("Khong thay icon doi ngu huan luyen")
        return False
    return True


OWNED_ROI = (104, 226, 80, 24)  # "So huu: 1,180" cua cap dang chon


def limits(ctx, tc):
    """(cap thap nhat duoc luyen, so T3 muc tieu hoac None)."""
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    low = tc.get("min_tier", 1)
    hq, cap = st.get("hq_level"), ctx.cfg.get("build", {}).get("hq_max_level", 22)
    if hq and hq >= cap:
        low = max(low, tc.get("tier", 3))  # nha chinh da toi gioi han -> chi luyen cap muc tieu (T3)
    target = None
    if tc.get("only_for_gather"):
        marches = st.get("march_total") or 1
        target = marches * tc.get("troops_per_march", 1200)
    return low, target


def pick_tier(ctx, tc, low):
    """Cham the cap tu cao xuong thap, tra ve cap dau tien co nut Huan luyen."""
    xs = tc.get("card_x", [100, 205, 308, 410])
    y = tc.get("card_y", 695)
    top = min(tc.get("tier", 3), len(xs))
    for tier in range(top, low - 1, -1):
        ctx.tap(xs[tier - 1], y, wait=1.0)
        if ctx.find("train/btn_train"):
            return tier
    return None


def train_once(ctx, tc):
    """Huan luyen o 1 nha linh dang ranh. Tra ve True neu da bam Huan luyen."""
    if not open_queue(ctx):
        return False
    if not ctx.tap_tpl("train/btn_goto", wait=2.0):
        log.info("Khong con nha linh nao nhan roi")
        ctx.close_popups(2)
        return False
    if not ctx.wait_for("common/btn_back", timeout=4):
        log.info("Khong vao duoc man huan luyen")
        ctx.save_debug("train_no_panel")
        return False
    low, target = limits(ctx, tc)
    tier = pick_tier(ctx, tc, low)
    if not tier:
        log.warning("Khong co cap linh nao mo khoa trong khoang T%d..T%d", low, tc.get("tier", 3))
        return False
    if target and tier == tc.get("tier", 3):
        owned = ocr.amount(ocr.text(ctx._img, OWNED_ROI, "0123456789,"))
        if owned is not None and owned >= target:
            log.info("Da du T%d: co %d >= %d (doi x linh moi doi) - khong luyen them", tier, owned, target)
            return False
    use_max(ctx, tc)
    ctx.tap_tpl("train/btn_train", wait=1.5)
    if not started(ctx):
        log.info("Thieu tai nguyen huan luyen T%d (nut Huan luyen van con / hop thoai thieu)", tier)
        ctx.close_popups(2)          # chi nut X/Dong - KHONG bam 'Dung vat pham' / mua bang kim cuong
        note_nores(ctx, tc)
        return "no_res"
    if tier < tc.get("tier", 3):
        log.info("Da huan luyen T%d (T%d chua mo khoa)", tier, tc.get("tier", 3))
    else:
        log.info("Da huan luyen T%d", tier)
    return True


def use_max(ctx, tc):
    """P2: bam nut 'Toi da' (train/btn_max) truoc khi Huan luyen. Thieu anh mau -> log 'thieu anh mau train/btn_max',
    giu so luong mac dinh (game dat san toi da theo tai nguyen) - khong bam mo vao thanh truot."""
    if not tc.get("use_max_button", True):
        return False
    if not tplneed.has(ctx.v, TPL_MAX, "giu so luong mac dinh"):
        return False
    if ctx.tap_tpl(TPL_MAX, wait=0.6, th=0.85, roi=MAX_ROI):
        return True
    log.info("Huan luyen: co anh mau %s nhung khong thay nut tren man - giu so luong mac dinh", TPL_MAX)
    return False


def started(ctx):
    """Sau khi bam 'Huan luyen': da bat dau? Hop thoai thieu tai nguyen (neu co anh mau) hoac nut 'Huan luyen' van con
    -> chua bat dau."""
    for i in range(2):                   # nut con thi nhin lai 1 lan (man co the dang chuyen)
        img = ctx.shot()
        if ctx.v.has("common/msg_insufficient") and ctx.v.find(img, "common/msg_insufficient", th=0.8):
            return False
        if not ctx.v.find(img, "train/btn_train"):          # cung cach tim nhu luc bam
            return True
        if not i:
            time.sleep(1.2)
    return False


def nores_until(ctx):
    m = getattr(ctx, "mem", None)
    v = m.fact(ctx.dev.idx, NORES_FACT) if m else None
    try:
        t = float((v or {}).get("until") or 0)
    except (TypeError, ValueError, AttributeError):
        return None
    return t if t > time.time() else None


def note_nores(ctx, tc):
    m = getattr(ctx, "mem", None)
    if not m:
        return
    from bot.modules import research
    e = research.note_nores(m.fact(ctx.dev.idx, NORES_FACT), time.time(), tc.get("nores_backoff_min", 30),
                            tc.get("nores_cap_h", 4))
    m.set_fact(ctx.dev.idx, NORES_FACT, e)


def queue_full(ctx):
    """Doc nhanh icon huan luyen cot trai (anh chu so, ~ms): 'x/y' voi x >= y -> moi nha linh dang luyen. None = khong
    doc duoc (van mo bang nhu cu)."""
    try:
        img = ctx.shot()
        p = ctx.v.find(img, "train/queue_icon", th=0.7, roi=queues.COLUMN)
        if not p:
            return None
        q = queues.resolve(queues.read_glyphs(img, p[0], p[1]), queues.has_dot(img, p[0], p[1]))
        return None if not q else q[0] >= q[1]
    except Exception as e:      # doc hang cho khong duoc lam hong buoc
        log.debug("train queue_full: %s", e)
        return None


def run(ctx):
    tc = ctx.cfg["train"]
    n = 0
    nr = nores_until(ctx)
    if nr:
        log.info("Huan luyen: lan truoc thieu tai nguyen - bo toi %s", time.strftime("%H:%M", time.localtime(nr)))
        return 0
    ctx.ensure_city()
    if queue_full(ctx):
        log.info("Huan luyen: moi nha linh dang luyen (icon cot trai x/x) - bo qua")
        return 0
    for _ in range(tc.get("max_queues", 4)):  # moi lan 1 nha linh; het nha ranh thi dung
        try:
            ok = train_once(ctx, tc)
        finally:
            ctx.back_out()
        if ok is not True:
            break
        n += 1
    if n:
        m = getattr(ctx, "mem", None)
        if m and m.fact(ctx.dev.idx, NORES_FACT):
            m.set_fact(ctx.dev.idx, NORES_FACT, None)
    ctx.ensure_city()
    ctx.help_and_free(use_help=tc.get("use_help", True), use_free=tc.get("use_free_speedup", True))
    return n
