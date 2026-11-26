"""P13i: con tho ranh thi VIEC DAU TIEN la bong bong tron vang co le noi tren cong trinh (bot/wrench.py) - uu tien nha
chinh, khong co thi nha khac; sau do moi toi:

Q2 - XAY THEO NHA CHINH (chu du an 2026-11-21): "tho ranh thi cu bam vao nha chinh, nha chinh thieu dieu kien gi
thi xay them can cu do". Moi may, moi cap; nha chinh da toi build.hq_max_level (30 = toi da) -> bo muc tieu xay.

Tim nha chinh: tu ban do the gioi bam ve thanh pho -> camera dat NHA CHINH (Xuong kien truc) giua man (~270,440;
kiem tren anh thao tac tay #1/#3 2026-11-21). Cham -> vong menu cong trinh -> kiem nhan "Xuong kien truc" -> nang cap
bang build.upgrade_here: thieu dieu kien -> nut "Nhay" sang cong trinh dieu kien (chuoi toi build max_depth), het tai
nguyen / het tho -> dong. KHONG BAO GIO bam "Tang cap ngay" (kim cuong, ADR-0008) - build.upgrade_here giu luat do.
Nha chinh / tien quyet dang xay ma con tho ranh, hoac thieu dieu kien -> nang nha khac (other_buildings, P13f-2).
"""
import logging
import time

from bot import build, hqplan, ocr, tapguard, tplneed, wrench
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


def hq_centered(hit, tol=(90, 120)):
    """Ham thuan: nha chinh (x, y, diem) dang nam giua man (quanh CENTER)?"""
    return bool(hit) and abs(hit[0] - CENTER[0]) <= tol[0] and abs(hit[1] - CENTER[1]) <= tol[1]


def goto_hq(ctx, again=False):
    """-> toa do icon Tang cap tren vong menu nha chinh, hoac None. again: lan cham nha chinh KE TIEP trong cung chuoi -
    camera con thay nha chinh giua man (anh mau) thi khong ra the gioi lai (P13f-3)."""
    names = _names(ctx)
    tpls = _templates(ctx)
    dys = [TAP_DY.get(n, 0) for n in names]
    img, recentered, move = None, False, True
    if again and any(t is not None for t in tpls):
        ctx.ensure_city()
        img = ctx.settle()
        move = not hq_centered(find_hq(img, tpls, dys=dys))
    if move:
        recentered = recenter_hq(ctx)   # the gioi -> thanh pho: camera ve gan nha chinh
        img = ctx.settle()
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


# ---- P13i: bong bong CO LE tren cong trinh = nang duoc ngay -> lua chon DAU TIEN khi con tho ranh ----
WRENCH_SCOPE = "wrench"     # pham vi danh sach den toa do (bot/tapguard.py)
WRENCH_MISSES = 3           # so bong bong bam ma khong bat dau duoc gi toi da moi lan goi


def _wrench_tpl(ctx):
    if not ctx.cfg.get("build", {}).get("wrench", True):
        return None
    load = getattr(getattr(ctx, "v", None), "load", None)
    if load is None:
        return None
    tpl = load(wrench.TPL, probe=True)
    if tpl is None:
        tplneed.has(ctx.v, wrench.TPL, "bong bong co le tren cong trinh")
    return tpl


def _hq_hit(ctx, img):
    """Huy hieu nha chinh dang thay tren man (anh mau) -> (x, y, diem) | None."""
    return find_hq(img, _templates(ctx), dys=[TAP_DY.get(n, 0) for n in _names(ctx)])


def wrench_candidates(ctx, img, hq=None):
    """-> [(x, y, diem, tren_nha_chinh)] bong bong co le tren anh, nha chinh truoc, bo toa do trong danh sach den."""
    tpl = _wrench_tpl(ctx)
    if tpl is None:
        return []
    found = wrench.find_bubbles(img, tpl)
    if not found:
        return []
    guard = tapguard.of(ctx)
    ranked = wrench.ordered(found, hq or _hq_hit(ctx, img))
    return [b for b in ranked if not guard.blocked(WRENCH_SCOPE, b[0], b[1])]


def tap_wrench(ctx, bubble):
    """Bam 1 bong bong co le roi nang bang build.upgrade_here (chi 'Tang cap' / 'Nhay' / 'Mien phi', khong kim cuong,
    khong mua / thue tho). -> ket qua cua upgrade_here."""
    x, y, score, on_hq = bubble
    log.info("Bong bong co le @%d,%d (khop %.2f) - %s -> bam", x, y, score,
             "tren NHA CHINH (uu tien)" if on_hq else "nha khac")
    ctx.last_is_hq = False
    ctx.tap(x, y, wait=1.5)
    res = build.upgrade_here(ctx)
    hq_screen = bool(getattr(ctx, "last_is_hq", False))
    log.info("Bong bong co le @%d,%d: sau khi bam -> %s%s", x, y, res, " (man nang cap nha chinh)" if hq_screen else "")
    guard = tapguard.of(ctx)
    ok = res in ("started", "no_builder")
    # 'none' = bam ma khong ra menu / man nang cap (man khong doi, cham sai cho) -> vao danh sach den ngay
    for _ in range(guard.limit if res == "none" else 1):
        guard.record(WRENCH_SCOPE, x, y, ok, f"bong bong co le -> {res}")
    if res == "started" and (on_hq or hq_screen):
        hqplan.save(ctx, res)
    ctx.back_out()
    ctx.ensure_city()
    return res


def wrench_upgrades(ctx, recenter=False):
    """Con tho ranh -> bam lan luot cac bong bong co le (nha chinh truoc, khong co thi nha khac). recenter: man hien
    tai khong thay nha chinh -> dua camera ve nha chinh 1 lan roi moi chon.
    -> (so cong trinh bat dau, ket qua lan bam cuoi | None)."""
    if _wrench_tpl(ctx) is None:
        return 0, None
    cap = ctx.cfg.get("build", {}).get("chain_max", 6)
    built, misses, res, tried = 0, 0, None, []
    while built < cap and misses < WRENCH_MISSES:
        if build.builder_state(ctx)[0] == 0:          # moi tho dung duoc dang ban (farm 1/2 = day)
            break
        ctx.ensure_city()
        img = ctx.settle()
        hq = _hq_hit(ctx, img)
        if hq is None and recenter:
            recenter = False
            if recenter_hq(ctx):                      # camera ve nha chinh: giua man la nha chinh du chua co anh mau
                img = ctx.settle()
                hq = _hq_hit(ctx, img) or (*CENTER, 0.0)
            else:
                img = ctx.settle()
        todo = [b for b in wrench_candidates(ctx, img, hq)
                if all(abs(b[0] - x) > 25 or abs(b[1] - y) > 25 for x, y in tried)]
        if not todo:
            if res is None:
                log.info("Bong bong co le: khong thay tren man")
            break
        res = tap_wrench(ctx, todo[0])
        if res == "no_builder":
            break
        if res == "started":
            built += 1
            tried = []                                # man da doi: bong bong khac co the troi toi cho cu
            if not build.quick_wait(ctx):
                break
        else:
            misses += 1
            tried.append(todo[0][:2])
    return built, res


# ---- P13f-2: nha chinh khong lam duoc ngay -> nang cong trinh huu ich khac (nha tai nguyen) cho tho khong ngoi khong
# templates/build/res_*.png cat tu anh ADB (Xuong Thuc Pham, thap tai nguyen den xanh); them kieu moi: tha them res_*.png.
RES_TH = 0.66                          # 253 anh da luu 24-26/11: dung nha >= 0.69, cho khac <= 0.59
# vung HUD / nut noi tren man thanh pho (x, y, w, h) - khong bao gio cham ("Cong nhan" thue tho, "Qua", goi tra phi...)
RES_BLOCK = ((0, 0, 540, 190), (0, 780, 540, 180), (0, 190, 70, 590), (0, 560, 160, 220), (400, 100, 140, 460),
             (470, 560, 70, 220))


def res_candidates(img, tpls, th=RES_TH, block=RES_BLOCK):
    """Ham thuan: -> [(x, y, diem)] tam cac nha tai nguyen tren anh thanh pho, diem giam dan, bo vung HUD."""
    import cv2
    import numpy as np
    hits = []
    for t in tpls:
        if t is None:
            continue
        r = cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED)
        for y, x in zip(*np.where(r >= th)):
            hits.append((float(r[y, x]), int(x) + t.shape[1] // 2, int(y) + t.shape[0] // 2))
    out = []
    for s, x, y in sorted(hits, reverse=True):
        if any(bx <= x < bx + w and by <= y < by + h for bx, by, w, h in block):
            continue
        if all(abs(x - ox) >= 70 or abs(y - oy) >= 70 for ox, oy, _ in out):
            out.append((x, y, s))
    return out


def _res_templates(ctx):
    import glob
    import os
    names = sorted("build/" + os.path.basename(f)[:-4] for f in glob.glob(os.path.join(ctx.v.dir, "build", "res_*.png")))
    return [ctx.v.load(n, probe=True) for n in names]


def upgrade_resource(ctx, tries=3, pans=4):
    """Cham nha tai nguyen thay tren man (luot toi da `pans` huong) -> build.upgrade_here. Chi bam nut Tang cap / Nhay /
    'Mien phi' nhu moi nang cap khac; khong kim cuong. -> 'started' | 'no_builder' | None."""
    tpls = _res_templates(ctx)
    if not any(t is not None for t in tpls):
        log.warning("Thieu anh mau nha tai nguyen: templates/build/res_*.png")
        return None
    ctx.ensure_city()
    img = ctx.settle()
    pos, done = (0, 0), 0
    for step in range(pans + 1):
        bubbles = wrench_candidates(ctx, img)         # P13i: thanh da luot -> bong bong co le truoc nha tai nguyen
        if bubbles:
            res = tap_wrench(ctx, bubbles[0])
            if res in ("started", "no_builder"):
                return res
            img = ctx.settle()
        found = res_candidates(img, tpls)
        if found:
            x, y, score = found[0]
            done += 1
            ctx.tap(x, y, wait=1.5)
            res = build.upgrade_here(ctx, max_depth=2)
            log.info("Nang nha khac: nha tai nguyen @%d,%d (%.2f) -> %s", x, y, score, res)
            ctx.back_out()
            ctx.ensure_city()
            if res in ("started", "no_builder"):
                return res
            if done >= tries:
                break
        if step >= pans:
            break
        nx, ny = PAN_RING[step]
        img = _drag(ctx, (nx - pos[0]) * PAN_DX, (ny - pos[1]) * PAN_DY)
        pos = (nx, ny)
    return None


def other_buildings(ctx):
    """Tho con ranh ma nha chinh khong lam duoc ngay -> nang nha khac toi khi het tho / het viec. -> so cong trinh."""
    bc = ctx.cfg.get("build", {})
    if not bc.get("other_when_blocked", True):
        return 0
    m = getattr(ctx, "mem", None)
    until = m.fact(ctx.dev.idx, "other_build_hold") if m else None
    if until and float(until) > time.time():
        log.info("Nang nha khac: lan truoc khong nang duoc gi - thu lai sau %.0f phut", (float(until) - time.time()) / 60)
        return 0
    built = 0
    for _ in range(bc.get("chain_max", 6)):
        if not build.builder_state(ctx)[0]:       # het tho ranh (hoac khong doc duoc: khong cham mo)
            break
        res = upgrade_resource(ctx)
        if res != "started":
            if res is None and not built and m:
                m.set_fact(ctx.dev.idx, "other_build_hold", time.time() + bc.get("other_retry_min", 30) * 60)
            break
        built += 1
        if not build.quick_wait(ctx):
            break
    return built


def hq_chain(ctx):
    """Nang theo nha chinh lien tiep chung nao tho con ranh. -> (so cong trinh bat dau, ket qua cuoi).
    Cap nha chinh chi duoc ghi trong build.upgrade_here (qua bot.hqlevel); 'hq_cap' khong ghi de them o day (P13i)."""
    built, res = 0, "none"
    for _ in range(ctx.cfg.get("build", {}).get("chain_max", 6)):
        if built:                                     # P13i: con tho -> bong bong co le truoc khi tim nha chinh tiep
            n, wres = wrench_upgrades(ctx)
            built += n
            if wres == "no_builder" or (n and build.builder_state(ctx)[0] == 0):
                return built, "started" if n else "no_builder"
        ic = goto_hq(ctx, again=True) if built else goto_hq(ctx)
        if not ic:
            ctx.back_out()
            ctx.ensure_city()
            hqplan.save(ctx, "none")
            return built, "none"
        ctx.last_busy = None
        res = build.upgrade_here(ctx)
        log.info("Xay theo nha chinh -> %s", res)
        hqplan.save(ctx, res, busy_s=getattr(ctx, "last_busy", None))
        if res == "none" and ctx.cfg.get("build", {}).get("probe_plot_lock", True):
            build.probe_plot_lock(ctx)   # nut Nhay dan toi lo dat khoa? mo hop thoai o khoa de ghi chi phi (chua xac nhan)
        ctx.back_out()
        ctx.ensure_city()
        if res != "started":
            break
        built += 1
        if not build.quick_wait(ctx):    # moi tho da ban -> roi buoc; con ranh / xay nhanh xong -> xay tiep ngay
            break
    return built, res


def run(ctx):
    cap = ctx.cfg.get("build", {}).get("hq_max_level", 30)
    m = getattr(ctx, "mem", None)
    hq = m.fact(ctx.dev.idx, "hq_level") if m else None
    ctx.ensure_city()
    ok, why = builder_idle(ctx)
    if not ok:
        log.info("Xay theo nha chinh: khong co tho ranh (%s)", why)
        hqplan.save(ctx, "no_builder")
        return 0
    # P13i: bong bong co le TRUOC (nang duoc ngay); khong co / tho van ranh moi toi logic tim nha chinh
    wbuilt, wres = wrench_upgrades(ctx, recenter=hq is None or hq < cap)
    if wres == "no_builder" or (wbuilt and build.builder_state(ctx)[0] == 0):
        return wbuilt
    built, res = 0, "none"
    if hq is not None and hq >= cap:
        log.info("Nha chinh cap %d >= %d - bo muc tieu xay nha chinh", hq, cap)
    else:
        go, why = hqplan.should_attempt(ctx)
        if go:
            built, res = hq_chain(ctx)
        else:
            log.info("Xay theo nha chinh: bo (%s)", why)
    if res not in ("started", "no_builder"):   # het viec / thieu dieu kien -> tho ranh lam nha khac
        built += other_buildings(ctx)
    return wbuilt + built
