"""P13-11 (chu du an, anh bien_gioi_keo_vong / bien_gioi_icon_mo_khoa, t74u): MO RONG THANH PHO.

Quanh thanh pho co vien sang (ranh gioi lo dat chua mo). Moi lan dang nhap: keo camera doc vien sang (luot vong quanh
thanh pho nhu tim nha chinh); thay icon O KHOA MO (templates/build/plot_unlock.png) -> bam de lam nhiem vu mo rong.
Ngoai ra hang nhiem vu "mo rong thanh pho" tren thanh nhiem vu / bang nhiem vu (quest_rules 'expand') danh dau
`expand_pending` -> buoc nay chay ngay cung lan ghe, khong cho het khoang `expand.min_interval_min`.
An toan: hop thoai sau khi bam icon CHI bam nut co chu Den / Nhay / Mo rong / Xay dung (buttons.with_text da loc Mua / Nap /
Mo khoa tra phi / kim cuong / tang toc); khong tim thay -> luu anh logs/inv/plot_unlock_dialog va dong. Khong bao gio bam
nut co gia / kim cuong. Chua kiem tren may that (khong co khung ADB hop thoai).
"""
import logging
import os
import time

import cv2

from bot import build, buttons

log = logging.getLogger("aow")
UNLOCK_TPL = "build/plot_unlock"
ROI = (30, 130, 480, 760)               # vung thanh pho khong bi HUD che
ACT_RX = r"\b(den|nhay|mo rong|xay dung)\b"
DIALOG_ROI = (0, 150, 540, 800)


def scfg(cfg):
    return {"enabled": True, "min_interval_min": 240, "ring": True, **((cfg or {}).get("expand") or {})}


def due(last_at, pending_at, now, interval_min):
    """Ham thuan: co chay buoc mo rong thanh pho khong. -> (bool, ly do)."""
    if pending_at and (not last_at or pending_at > last_at):
        return True, "co nhiem vu mo rong thanh pho (thanh / bang nhiem vu)"
    if not last_at or now - last_at >= interval_min * 60:
        return True, "quet vien thanh pho dinh ky"
    return False, f"vua quet {(now - last_at) / 60:.0f} phut truoc"


def find_unlock(v, img):
    """Ham thuan: icon o khoa MO tren thanh pho -> (x, y) | None."""
    p = v.find(img, UNLOCK_TPL, th=0.8, roi=ROI)
    return (p[0], p[1]) if p else None


def sweep(ctx, ring=True):
    """Xem man hien tai, roi luot camera quanh thanh pho (vong 8 huong) toi khi thay icon o khoa mo. -> (x, y) | None."""
    img = ctx.settle()
    pos = (0, 0)
    steps = len(build.PAN_RING) if ring else 0
    for step in range(steps + 1):
        p = find_unlock(ctx.v, img)
        if p:
            return p
        if step >= steps:
            break
        nx, ny = build.PAN_RING[step]
        ctx.dev.swipe(270, 480, 270 + (nx - pos[0]) * 200, 480 + (ny - pos[1]) * 300, 600)
        pos = (nx, ny)
        img = ctx.settle()
    return None


def open_plot(ctx, p):
    """Bam icon o khoa mo -> hop thoai; chi bam nut Den / Nhay / Mo rong / Xay dung (khong gia, khong kim cuong). -> bool."""
    ctx.tap(p[0], p[1], wait=1.8)
    img = ctx.settle()
    d = os.path.join("logs", "inv", "plot_unlock_dialog")
    os.makedirs(d, exist_ok=True)
    cv2.imwrite(os.path.join(d, time.strftime("%Y%m%d-%H%M%S") + f"-i{ctx.dev.idx}.png"), img)
    for b in buttons.with_text(img, ACT_RX, DIALOG_ROI):
        log.info("Mo rong thanh pho: bam '%s' @%d,%d", b.text[:20], b.x, b.y)
        ctx.tap(b.x, b.y, wait=2.0)
        return True
    log.info("Mo rong thanh pho: hop thoai khong co nut an toan (Den / Nhay / Mo rong / Xay dung) - dong, luu anh")
    ctx.back_out(1)
    return False


def run(ctx):
    c = scfg(ctx.cfg)
    if not c["enabled"]:
        return 0
    m, idx, now = getattr(ctx, "mem", None), ctx.dev.idx, time.time()
    last = m.fact(idx, "expand_last") if m else None
    pend = m.fact(idx, "expand_pending") if m else None
    go, why = due(last, pend, now, c["min_interval_min"])
    if not go:
        log.info("Mo rong thanh pho: bo qua (%s)", why)
        return 0
    ctx.ensure_city()
    log.info("Mo rong thanh pho: %s", why)
    p = sweep(ctx, c["ring"])
    if m:
        m.set_fact(idx, "expand_last", now)
    if not p:
        log.info("Mo rong thanh pho: khong thay icon o khoa mo tren vien thanh pho")
        ctx.back_out()
        ctx.ensure_city()
        return 0
    log.info("Mo rong thanh pho: thay icon o khoa mo @%d,%d", p[0], p[1])
    n = 1 if open_plot(ctx, p) else 0
    ctx.back_out()
    ctx.ensure_city()
    return n
