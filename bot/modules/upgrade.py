"""Q2 - XAY THEO NHA CHINH (chu du an 2026-11-21): "tho ranh thi cu bam vao nha chinh, nha chinh thieu dieu kien gi
thi xay them can cu do". Moi may, moi cap; nha chinh da toi build.hq_max_level (30 = toi da) -> bo muc tieu xay.

Tim nha chinh: tu ban do the gioi bam ve thanh pho -> camera dat NHA CHINH (Xuong kien truc) giua man (~270,440;
kiem tren anh thao tac tay #1/#3 2026-11-21). Cham -> vong menu cong trinh -> kiem nhan "Xuong kien truc" -> nang cap
bang build.upgrade_here: thieu dieu kien -> nut "Nhay" sang cong trinh dieu kien (chuoi toi build max_depth), het tai
nguyen / het tho -> dong. KHONG BAO GIO bam "Tang cap ngay" (kim cuong, ADR-0008) - build.upgrade_here giu luat do.
Nha chinh dang xay (tho thu 2 con ranh, #1) -> de buoc 'quests' dung tho con lai.
"""
import logging

from bot import build, hqplan, ocr
from aowbot.domain.blockers import normalize

log = logging.getLogger("aow")
HQ_TAP = (270, 440)
LABEL_OFF = (-170, -215, 260, 44)   # nhan "Xuong kien truc Lv.N" tren vong menu (tinh tu icon Tang cap)


def is_hq_label(text):
    s = normalize(text)
    return "kien truc" in s or "kien tr" in s or "xuong kien" in s


def hq_label(img, px, py):
    dx, dy, w, h = LABEL_OFF
    x, y = max(0, px + dx), max(0, py + dy)
    return " ".join(ocr.text(img, (x, y, w, h), bright=b, psm=6) or "" for b in (170, None))


def builder_idle(ctx):
    """Con tho dung duoc dang ranh? So tho = build.max_builders cua may (P13f-1: farm 1/2 = day, khong thue tho)."""
    b = build.builders(ctx)
    if b is None:
        return True, "khong doc duoc so tho - van thu"
    maxb = build.max_builders(ctx, b[1])
    return b[0] < min(maxb, b[1]), f"tho {b[0]}/{b[1]} (dung toi da {maxb})"


# ---- tim nha chinh bang anh mau (chu du an 2026-11-21: luot qua lai trong thanh pho tim match nha chinh) ----
# Nha chinh co huy hieu canh tren mai o moi cap (templates/build/hq_emblem_*.png, cat tu anh #2/#3); them kieu moi: tha
# templates/build/hq_emblem_<ten>.png. Camera khong luon dat nha chinh giua man -> luot theo vong tron toi khi thay.
HQ_MATCH_TH = 0.68                   # anh khac #2/#3: huy hieu cung 0.72-0.90, nen khac khong qua 0.56
HQ_TPLS = ("build/hq_emblem_a", "build/hq_emblem_b")
# P9-9 nha chinh DA SKIN: skin bi ngo Halloween (#1, live2/00-before.png 200,420,340,490 = san tron tim duoi qua bi ngo;
# bi ngo co hoat anh nen khong cat). Mau khong nam tren mai -> lech diem cham: tam mau + TAP_DY[ten] (truoc khi _try_open
# cong +35). Khop that 0.76-1.0 tren 22 khung thanh pho live2, nen <= 0.66.
TAP_DY = {"build/hq_emblem_halloween": -45}
SAFE = (60, 190, 400, 840)           # vung khong bi bang/menu che (x1, y1, x2, y2)
CENTER = (270, 450)
PAN_DX, PAN_DY = 200, 300            # moi buoc luot (ngon tay keo noi dung theo)
PAN_RING = ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))


def find_hq(img, tpls, th=HQ_MATCH_TH, dys=None):
    """-> (x, y, diem) tam huy hieu nha chinh tot nhat >= th, hoac None. Ham thuan (test offline).
    dys: lech y theo tung mau (P9-9 skin: mau khong phai huy hieu tren mai) - y tra ve da cong lech."""
    import cv2
    best = None
    for i, t in enumerate(tpls):
        if t is None:
            continue
        _, m, _, loc = cv2.minMaxLoc(cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED))
        if m >= th and (best is None or m > best[2]):
            dy = dys[i] if dys else 0
            best = (loc[0] + t.shape[1] // 2, loc[1] + t.shape[0] // 2 + dy, float(m))
    return best


def _names(ctx):
    import glob
    import os
    names = list(HQ_TPLS)
    for f in sorted(glob.glob(os.path.join(ctx.v.dir, "build", "hq_emblem_*.png"))):
        n = "build/" + os.path.basename(f)[:-4]
        if n not in names:
            names.append(n)
    return names


def _templates(ctx):
    return [ctx.v.load(n, probe=True) for n in _names(ctx)]


def _drag(ctx, dx, dy):
    """Keo noi dung (dx, dy) tu giua man; xong cho camera dung yen."""
    cx, cy = 270, 480
    ctx.dev.swipe(cx, cy, cx + dx, cy + dy, 600)
    return ctx.settle()


def _try_open(ctx, hit):
    """Chạm nha chinh tai hit; -> icon Tang cap neu mo dung menu 'Xuong kien truc', nguoc lai None."""
    ctx.tap(hit[0], hit[1] + 35, wait=1.5)
    img = ctx.settle()
    ic = ctx.v.find(img, "build/btn_upgrade_icon")
    if not ic:
        build.inv_capture(ctx, "upgrade_no_menu")
        return None
    label = hq_label(img, ic[0], ic[1])
    if is_hq_label(label):
        return ic
    log.info("Xay theo nha chinh: cong trinh khong phai nha chinh (%r)", label[:40])
    build.inv_capture(ctx, "upgrade_not_hq")
    ctx.back_out(1)
    return None


def recenter_hq(ctx):
    """P13-1 (chu du an t71u): muon nha chinh nam GIUA man -> ra ban do the gioi roi vao lai thanh pho (camera ve nha
    chinh). Lam TRUOC khi cham nha chinh, thay cho luot quanh thanh pho. Nha chinh < cap mo the gioi (world_ready
    false, vd #3-#6 cap 4-5): van thu 1 lan nhe (goto toi da 3 vong); khong ra duoc the gioi -> nho 6 gio khong thu
    lai (fact recenter_fail), chi ve thanh pho. -> True neu da di 'the gioi -> thanh pho'."""
    import time
    if not ctx.cfg.get("build", {}).get("recenter_world", True):
        ctx.ensure_city()
        return False
    m = getattr(ctx, "mem", None)
    idx = ctx.dev.idx
    if ctx.world_ready():
        ctx.ensure_world()
        ctx.ensure_city()
        return True
    last = m.fact(idx, "recenter_fail") if m else None
    if last and time.time() - float(last) < 6 * 3600:
        ctx.ensure_city()
        return False
    ctx.ensure_city()
    if ctx.goto("world", rounds=3):
        ctx.ensure_city()
        return True
    if m:
        m.set_fact(idx, "recenter_fail", time.time())
    log.info("Xay theo nha chinh: nha chinh thap, khong ra duoc the gioi de can giua - bo qua 6 gio")
    ctx.ensure_city()
    return False


def goto_hq(ctx):
    """-> toa do icon Tang cap tren vong menu nha chinh, hoac None."""
    recentered = recenter_hq(ctx)   # the gioi -> thanh pho: camera ve gan nha chinh
    img = ctx.settle()
    names = _names(ctx)
    tpls = _templates(ctx)
    dys = [TAP_DY.get(n, 0) for n in names]
    if not any(t is not None for t in tpls):
        log.warning("Thieu anh mau nha chinh: templates/build/hq_emblem_*.png")
        return None
    pos = (0, 0)                # tong dich chuyen noi dung so voi luc vao thanh pho
    for step in range(len(PAN_RING) + 1):
        hit = find_hq(img, tpls, dys=dys)
        if hit is None and step == 0 and not recentered:
            log.info("Xay theo nha chinh: khong thay nha chinh - ra the gioi vao lai de can giua")
            recentered = recenter_hq(ctx)
            img = ctx.settle()
            hit = find_hq(img, tpls, dys=dys)
        if hit is None and step == 0:
            # P9-9 skin moi chua co mau: ve thanh pho -> camera dat nha chinh giua man; cham VI TRI + kiem NHAN ten
            # ("Xuong kien truc") -> khong phu thuoc skin. Sai cong trinh -> _try_open tu thoat.
            log.info("Xay theo nha chinh: khong khop mau skin nao -> thu vi tri giua man %s + nhan ten", HQ_TAP)
            ic = _try_open(ctx, (HQ_TAP[0], HQ_TAP[1] - 35, 0.0))
            if ic:
                return ic
            ctx.ensure_city()
            img = ctx.settle()
        if hit:
            x, y, sc = hit
            log.info("Xay theo nha chinh: thay nha chinh @%d,%d (%.2f) sau %d buoc luot", x, y, sc, step)
            if not (SAFE[0] <= x <= SAFE[2] and SAFE[1] <= y <= SAFE[3]):
                # sat mep / duoi bang che -> dua vao giua man roi tim lai
                img = _drag(ctx, max(-PAN_DX, min(PAN_DX, CENTER[0] - x)), max(-PAN_DY, min(PAN_DY, CENTER[1] - y)))
                hit = find_hq(img, tpls, dys=dys) or hit
            ic = _try_open(ctx, hit)
            if ic:
                return ic
            ctx.ensure_city()
            img = ctx.settle()
            pos = (0, 0)               # camera ve cho cu -> vong luot tinh lai tu goc
        if step >= len(PAN_RING):
            break
        nx, ny = PAN_RING[step]
        img = _drag(ctx, (nx - pos[0]) * PAN_DX, (ny - pos[1]) * PAN_DY)
        pos = (nx, ny)
    log.info("Xay theo nha chinh: khong thay nha chinh sau khi luot quanh thanh pho")
    build.inv_capture(ctx, "upgrade_no_menu")
    return None


def run(ctx):
    cap = ctx.cfg.get("build", {}).get("hq_max_level", 30)
    m = getattr(ctx, "mem", None)
    hq = m.fact(ctx.dev.idx, "hq_level") if m else None
    if hq is not None and hq >= cap:
        log.info("Nha chinh cap %d >= %d - bo muc tieu xay", hq, cap)
        return 0
    go, why = hqplan.should_attempt(ctx)
    if not go:
        log.info("Xay theo nha chinh: bo (%s)", why)
        return 0
    ctx.ensure_city()
    ok, why = builder_idle(ctx)
    if not ok:
        log.info("Xay theo nha chinh: khong co tho ranh (%s)", why)
        hqplan.save(ctx, "no_builder")
        return 0
    if not goto_hq(ctx):
        ctx.back_out()
        ctx.ensure_city()
        hqplan.save(ctx, "none")
        return 0
    ctx.last_busy = None
    res = build.upgrade_here(ctx)
    log.info("Xay theo nha chinh -> %s", res)
    hqplan.save(ctx, res, busy_s=getattr(ctx, "last_busy", None))
    if res == "none" and ctx.cfg.get("build", {}).get("probe_plot_lock", True):
        build.probe_plot_lock(ctx)   # nut Nhay dan toi lo dat khoa? mo hop thoai o khoa de ghi chi phi (chua xac nhan)
    if res == "hq_cap" and m:
        m.set_fact(ctx.dev.idx, "hq_level", cap)
    ctx.back_out()
    ctx.ensure_city()
    if res == "started":
        build.quick_wait(ctx)      # xay nhanh -> cho xong; buoc xa viec (drain) chay lai 'upgrade' de xay tiep
    return 1 if res == "started" else 0
