"""Nang cap cong trinh tu menu cong trinh / man "Tang cap" (dung cho nhiem vu va xay theo nhiem vu).

Man Tang cap (540x960): tieu de + "Cap hien tai N"; dieu kien chua dat co nut "Nhay" -> sang cong trinh do;
nut PHAI "Tang cap" (co dong ho). KHONG BAO GIO bam "Tang cap ngay" (nut trai, ton kim cuong).
"""
import os, time, logging
from bot import ocr

log = logging.getLogger("aow")
LEVEL_ROI = (180, 148, 180, 26)   # "Cap hien tai N"
BUILDER_ROI = (62, 128, 36, 20)   # "x/y" tho xay canh icon bua (goc trai thanh pho)


def builders(ctx, img=None):
    """(dang dung, tong) tho xay; None neu khong doc duoc."""
    import re
    img = img if img is not None else ctx.shot()
    m = re.search(r"(\d)\s*/\s*(\d)", ocr.text(img, BUILDER_ROI, "0123456789/"))
    return (int(m.group(1)), int(m.group(2))) if m else None


def screen_level(img):
    import re
    m = re.search(r"(\d+)", ocr.text(img, LEVEL_ROI, "0123456789"))
    return int(m.group(1)) if m else None


MAX_LEVEL = 30   # cap toi da moi cong trinh (chu du an 2026-11-21)


def menu_level(img, px, py):
    """Nhan "Xuong Tank Lv.30" phia tren menu cong trinh (icon Tang cap o px, py). OCR nhieu khung, lay so hay gap."""
    import re
    votes = {}
    for roi in ((px - 160, py - 208, 240, 30), (px - 130, py - 205, 200, 24), (px - 150, py - 212, 220, 36)):
        for b in (170, None):
            m = re.search(r"L[vVy]\.?\s*(\d{1,2})", ocr.text(img, roi, bright=b) or "")
            if m and 1 <= int(m.group(1)) <= MAX_LEVEL:
                votes[int(m.group(1))] = votes.get(int(m.group(1)), 0) + 1
    return max(votes, key=votes.get) if votes else None


def menu_busy(img, px, py):
    """Cong trinh dang chon co thanh tien do (dang xay) ngay tren? -> giay con lai | 0 (co thanh, khong doc duoc) | None"""
    from bot.modules.observe import progress_bars
    for bx, by, t in progress_bars(img, roi=(max(0, px - 200), max(0, py - 170), 320, 120)):
        return t or 0
    return None


def inv_capture(ctx, tag):
    """A-INV-1: luu anh man hien tai de dieu tra vi sao nhiem vu khong dan toi man nang cap.
    Toi da 1 anh / ngay / tag / may (logs/inv/<tag>/), KHONG qua save_debug -> khong doi ket qua buoc."""
    import cv2
    d = os.path.join("logs", "inv", tag)
    path = os.path.join(d, time.strftime("%Y%m%d") + f"-i{ctx.dev.idx}.png")
    if os.path.exists(path):
        return None
    try:
        os.makedirs(d, exist_ok=True)
        cv2.imwrite(path, ctx.dev.screencap(tries=1))
        log.info("Dieu tra: luu %s", path)
        return path
    except (OSError, RuntimeError) as e:
        log.debug("inv_capture %s: %s", tag, e)
        return None


def upgrade_here(ctx, depth=0, max_depth=4):
    """Dang o menu cong trinh (icon Tang cap) hoac man Tang cap. Tra ve: 'started' | 'hq_cap' |
    'blocked' (thieu dieu kien/tai nguyen/het tho) | 'none' (khong phai man nang cap)."""
    cap = ctx.cfg.get("build", {}).get("hq_max_level", 22)
    ic = ctx.find("build/btn_upgrade_icon")
    if ic:
        # chu du an 2026-11-21: cong trinh DANG XAY -> ghi nhan, khong lam lai toi khi xong; Lv.30 = toi da -> bo
        busy = menu_busy(ctx._img, ic[0], ic[1])
        if busy is not None:
            ctx.last_busy = busy
            log.info("Cong trinh dang xay (con %s) - khong lam lai", f"{busy // 3600}h{busy % 3600 // 60:02d}" if busy else "?")
            ctx.back_out(1)
            return "busy"
        lvm = menu_level(ctx._img, ic[0], ic[1])
        if lvm is not None and lvm >= MAX_LEVEL:
            log.info("Cong trinh Lv.%d = cap toi da - bo qua", lvm)
            ctx.back_out(1)
            return "maxed"
        ctx.tap_tpl("build/btn_upgrade_icon", wait=1.5, fresh=False)
    ctx.skip_dialogs()   # vd "Can thoa man dieu kien tien de moi" che man Tang cap (do #5, 2026-11-18)
    img = ctx.shot()
    if not (ctx.v.find(img, "build/btn_upgrade") or ctx.v.find(img, "build/btn_jump")):
        if depth:      # da 'Nhay' sang cong trinh dieu kien ma khong toi man nang cap (A-INV-1)
            inv_capture(ctx, f"jump_none_d{depth}")
        return "none"
    lv = screen_level(img)
    is_hq = bool(ctx.v.find(img, "build/title_hq"))
    if is_hq and lv is not None and getattr(ctx, "store", None):
        ctx.store.update(ctx.dev.idx, hq_level=lv)  # nho cap nha chinh cho phan huan luyen/web
    if is_hq and lv is not None and lv >= cap:
        log.info("Nha chinh da cap %d >= gioi han %d - khong nang", lv, cap)
        return "hq_cap"
    jump = ctx.v.find(img, "build/btn_jump")
    if jump:
        if depth >= max_depth:
            log.info("Chuoi dieu kien qua dai - dung")
            return "blocked"
        log.info("Thieu dieu kien (cap %s) -> Nhay sang cong trinh can nang truoc", lv)
        ctx.tap(jump[0], jump[1], wait=2.0)
        ctx.skip_dialogs()
        return upgrade_here(ctx, depth + 1, max_depth)
    if not ctx.cfg.get("build", {}).get("follow_quests", True):
        return "blocked"
    ctx.tap_tpl("build/btn_upgrade", wait=2.0, fresh=False)
    ctx.skip_dialogs()   # "Xuong kien truc bat dau tang cap, hay tang toc..." hien SAU khi da bat dau (do #5)
    # Thanh cong: man Tang cap dong lai, ve thanh pho. Con man / hien hop thoai -> thieu tai nguyen hoac
    # het tho -> DONG lai (khong bao gio xac nhan hop thoai co the ton kim cuong).
    img = ctx.shot()
    if ctx.v.find(img, "build/msg_no_builder"):
        # bang "Tao doi ngu": het tho ranh (tho thu 2 la tho thue chua mo). Co nut "Tang toc"/"Dung thu" -> KHONG bam
        log.info("Het tho xay ranh - dong bang, dung xay")
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
        ctx.back_out()
        return "no_builder"
    if ctx.v.find(img, "build/btn_upgrade") or not ctx.is_home():
        log.info("Khong nang cap duoc (thieu tai nguyen / het tho?) - dong")
        ctx.save_debug("build_blocked")
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
        ctx.back_out()
        return "blocked"
    log.info("Da bat dau nang cap cong trinh (cap %s -> %s)", lv, (lv or 0) + 1)
    return "started"
