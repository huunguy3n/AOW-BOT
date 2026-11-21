"""Huan luyen linh qua bang "Doi ngu huan luyen" (khong can tim nha linh tren ban do).

Luong (giao dien that, man 540x960):
  icon train/queue_icon (goc trai, "0/1") -> bang liet ke nha linh; nha nao NHAN ROI co nut "Den"
  -> cham "Den" -> vao thang man huan luyen -> chon cap linh cao nhat da mo khoa (the cap I..IV
  o vi tri co dinh) -> thanh so luong mac dinh da toi da -> bam "Huan luyen" (nut PHAI).

KHONG BAO GIO bam "Huan luyen ngay" (nut trai, ton kim cuong).
Cap bi khoa: man hinh hien "Khi Xuong ... dat cap N se mo khoa" va KHONG co nut Huan luyen
-> bot thu cap thap hon.
"""
import time, logging
from bot import ocr

log = logging.getLogger("aow")


def open_queue(ctx):
    ctx.ensure_city()
    if not ctx.tap_tpl("train/queue_icon", wait=1.5):
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
    if tc.get("use_max_button") and ctx.v.has("train/btn_max"):
        ctx.tap_tpl("train/btn_max", wait=0.6)
    ctx.tap_tpl("train/btn_train", wait=1.5)
    if ctx.find("common/msg_insufficient"):
        log.info("Thieu tai nguyen huan luyen T%d", tier)
        ctx.close_popups()
        return False
    if tier < tc.get("tier", 3):
        log.info("Da huan luyen T%d (T%d chua mo khoa)", tier, tc.get("tier", 3))
    else:
        log.info("Da huan luyen T%d", tier)
    return True


def run(ctx):
    tc = ctx.cfg["train"]
    ctx.cfg["_use_help"], ctx.cfg["_use_free"] = tc.get("use_help", True), tc.get("use_free_speedup", True)
    n = 0
    for _ in range(tc.get("max_queues", 4)):  # moi lan 1 nha linh; het nha ranh thi dung
        try:
            ok = train_once(ctx, tc)
        finally:
            ctx.back_out()
        if not ok:
            break
        n += 1
    ctx.ensure_city()
    ctx.help_and_free()
    return n
