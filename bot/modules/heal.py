"""Q5 - BENH VIEN (chu du an 2026-11-21: "neu co thuong binh tien hanh chua tri tai benh vien").

Luong (anh chu du an gui): cong trinh "Benh Vien" tren thanh pho -> cham -> vong menu "Chi tiet / Tang cap / Hoi phuc"
-> "Hoi phuc" (xam khi khong co thuong binh) -> bang chua tri -> nut "Hoi phuc" (TAI NGUYEN). KHONG BAO GIO
"Hoi phuc ngay" / nut co gia kim cuong (ADR-0008) - bot/buttons.py chan chu "... ngay" va gia tien.

Tim benh vien: CHU THAP DO tren mai = khoi do 46x24 px, phu ~46 % khung (hinh chu thap nhin nghieng) - do tren 2 anh
chu du an + anh that #0; cham do / nut do khac co kich thuoc / do phu khac. Ve thanh pho tu the gioi (camera dat nha
chinh giua man); benh vien khong nam trong khung nhin -> bo qua (ghi log), khong keo ban do mo.

P5-3 (PM 2026-11-23): 21-22/11 heal chay 45 lan, ca 45 tra 0 (moi lan mo benh vien ra xem). Dau hieu co thuong binh
= BONG BONG chua tri (build/heal_bubble). Khong thay bong bong va lan ghe nay chua co tran (rebels / phong thu)
-> tra 0 ngay, KHONG cham benh vien (heal.open_without_bubble: false). Thieu anh mau bong bong -> cach cu.
(42 anh heal_no_target KHONG phai cua buoc nay: la su kien "chua thuong" trong notify.heal_event.)
"""
import logging

import cv2
import numpy as np

from bot import build, buttons, tplneed
from bot.stepgate import FIGHT_STEPS
from aowbot.domain import drain
from aowbot.domain.blockers import normalize

log = logging.getLogger("aow")
RING_HEAL = (80, -15)            # icon "Hoi phuc" so voi icon "Tang cap" tren vong menu (anh chu du an)
HEAL_TXT = r"\bh\w{0,2}i ph\w{0,2}c\b"


def crosses(img, roi=(0, 110, 540, 700)):
    """Chu thap do benh vien -> [(x, y)] tam."""
    x0, y0, w0, h0 = roi
    hsv = cv2.cvtColor(img[y0:y0 + h0, x0:x0 + w0], cv2.COLOR_BGR2HSV)
    m = (((hsv[..., 0] <= 8) | (hsv[..., 0] >= 172)) & (hsv[..., 1] >= 150) & (hsv[..., 2] >= 120)).astype(np.uint8)
    n, _, st, cen = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 40 <= w <= 54 and 19 <= h <= 30 and 0.38 <= a / (w * h) <= 0.54:
            out.append((int(x0 + cen[i][0]), int(y0 + cen[i][1])))
    return out


def is_hospital_label(text):
    s = normalize(text)
    return "benh vi" in s or "vien" in s and "benh" in s


def fought(done):
    """Lan ghe nay co tran (phan quan xuat chinh / bi tan cong) -> co the co thuong binh."""
    return any(drain.worked((done or {}).get(s)) for s in FIGHT_STEPS)


def should_open(has_bubble_tpl, bubble, fought_now, open_without_bubble=False):
    """Ham thuan P5-3: co mo benh vien (theo chu thap do) khi KHONG cham duoc bong bong chua tri?
    Chi khi: chua co anh mau bong bong (khong biet) / vua co tran / cau hinh cho phep. Thay bong bong -> luong bong bong."""
    if bubble:
        return True
    return (not has_bubble_tpl) or fought_now or bool(open_without_bubble)


def run(ctx):
    if ctx.world_ready():
        ctx.ensure_world()
    ctx.ensure_city()
    img = ctx.settle()
    # BONG BONG chua tri tren benh vien (icon vang '+', chu du an 2026-11-22: khoanh do) = co thuong binh -> cham thang vao bong
    # bong; khong phu thuoc chu thap do (benh vien dang nang cap khong co chu thap do nhung bong bong van hien)
    bub = ctx.v.find(img, "build/heal_bubble", th=0.8, roi=(0, 110, 540, 700))
    if bub:
        log.info("Benh vien: thay bong bong chua tri @%d,%d - cham", bub[0], bub[1])
        ctx.tap(bub[0], bub[1], wait=1.8)
        img = ctx.settle()
        btns = buttons.with_text(img, HEAL_TXT)
        if btns:
            return press_heal(ctx, btns[-1])
        log.info("Benh vien: cham bong bong khong mo bang chua tri - thu cach cu")
        build.inv_capture(ctx, "heal_bubble_no_panel")
        ctx.back_out()
        ctx.ensure_city()
        img = ctx.settle()
    hc = ctx.cfg.get("heal", {}) or {}
    has_tpl = tplneed.has(ctx.v, "build/heal_bubble", "bong bong chua tri tren benh vien")
    if not should_open(has_tpl, bool(bub), fought(getattr(ctx, "visit_done", None)), hc.get("open_without_bubble", False)):
        log.info("Benh vien: khong thay bong bong chua tri, lan ghe chua co tran -> khong mo benh vien")
        return 0
    cs = crosses(img)
    if not cs:
        log.info("Benh vien: khong thay trong khung nhin thanh pho - bo qua")
        return 0
    x, y = cs[0]
    ctx.tap(x, y + 20, wait=1.5)
    img = ctx.settle()
    up = ctx.v.find(img, "build/btn_upgrade_icon")
    if not up:
        log.info("Benh vien: cham khong mo vong menu")
        build.inv_capture(ctx, "heal_no_menu")
        ctx.back_out()
        return 0
    from bot.modules.upgrade import hq_label
    label = hq_label(img, up[0], up[1])
    if not is_hospital_label(label):
        log.info("Benh vien: cong trinh duoc chon khong phai benh vien (%r)", label[:40])
        ctx.back_out()
        return 0
    ctx.tap(up[0] + RING_HEAL[0], up[1] + RING_HEAL[1], wait=1.5)
    img = ctx.settle()
    btns = buttons.with_text(img, HEAL_TXT)           # 'Hoi phuc ngay' / gia kim cuong bi loai trong buttons
    if not btns:
        log.info("Benh vien: khong co thuong binh (hoac chua nhan ra bang chua tri)")
        build.inv_capture(ctx, "heal_panel")
        ctx.back_out()
        ctx.ensure_city()
        return 0
    return press_heal(ctx, btns[-1])


def press_heal(ctx, b):
    """Bang chua ttri: bam nut "Hoi phuc" (tai nguyen); KHONG BAO GIO "Hoi phuc ngay" (buttons chan, ADR-0008)."""
    ctx.tap(b.x, b.y, wait=1.5, tpl="btn:hoi_phuc")
    if ctx.find("common/msg_insufficient"):
        log.info("Benh vien: thieu tai nguyen de chua")
        ctx.close_popups()
        ctx.back_out()
        return 0
    log.info("Benh vien: chua thuong binh (nut '%s')", b.text)
    ctx.back_out()
    ctx.ensure_city()
    return 1
