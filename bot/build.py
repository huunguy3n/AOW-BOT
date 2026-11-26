"""Nang cap cong trinh tu menu cong trinh / man "Tang cap" (dung cho nhiem vu va xay theo nhiem vu).

Man Tang cap (540x960): tieu de + "Cap hien tai N"; dieu kien chua dat co nut "Nhay" -> sang cong trinh do;
nut PHAI "Tang cap" (co dong ho). KHONG BAO GIO bam "Tang cap ngay" (nut trai, ton kim cuong) TRU khi dong duoi ghi
"Mien phi" va khong co so (chu du an 2026-11-22; free_instant_button).
"""
import os, re, time, logging
from bot import ocr

log = logging.getLogger("aow")
LEVEL_ROI = (180, 148, 180, 26)   # "Cap hien tai N"
BUILDER_ROI = (62, 128, 36, 20)   # "x/y" tho xay canh icon bua (goc trai thanh pho)


def builders(ctx, img=None):
    """(dang dung, tong) tho xay; None neu khong doc duoc."""
    import re
    img = img if img is not None else ctx.shot()
    v = getattr(ctx, "v", None)
    if v is not None:       # P13f-2: anh chu so quanh icon bua (doc duoc "1/1" ma OCR vung co dinh hay hut)
        from bot import queues
        p = v.find(img, queues.ICONS["build"], th=0.8, roi=queues.COLUMN)
        got = queues.read_count(img, p[0], p[1]) if p else None
        if got:
            return got
    m = re.search(r"(\d)\s*/\s*(\d)", ocr.text(img, BUILDER_ROI, "0123456789/"))
    return (int(m.group(1)), int(m.group(2))) if m else None


def max_builders(ctx, total=None):
    """P13f-1: so tho xay dung duoc = build.max_builders cua may (farm 1, #1 = 2), kep xuong theo y game bao neu it hon.
    KHONG lay y lam so tho (farm game bao 1/2 nhung o thu 2 chua mua). Khong bao gio thue / mua tho."""
    from aowbot.domain import builders as dom
    if total is None:
        m = getattr(ctx, "mem", None)
        try:
            total = m.fact(ctx.dev.idx, "builders_total") if m else None
        except Exception:  # noqa: BLE001
            total = None
    return dom.effective_max(ctx.cfg.get("build", {}).get("max_builders", 1), total)


def builder_state(ctx, img=None):
    """-> (so tho dung duoc dang RANH, (dang xay, tong)) hoac (None, None) neu khong doc duoc."""
    from aowbot.domain import builders as dom
    b = builders(ctx, img) if img is not None else builders(ctx)
    if b is None:
        return None, None
    return dom.idle_count(b[0], min(max_builders(ctx, b[1]), b[1])), b


def note_started(ctx):
    """Dem cong trinh da bat dau trong luot ghe (runner: lan thu xay co tien trien khong) -> 'started'."""
    ctx.builds_started = getattr(ctx, "builds_started", 0) + 1
    return "started"


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


PAN_RING = ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))


def find_plot_lock(ctx, dx=200, dy=300):
    """Tim bieu tuong o khoa lo dat: xem man hien tai roi luot camera theo vong quanh (nhu tim nha chinh)."""
    roi = (40, 150, 460, 700)
    img = ctx.settle()
    pos = (0, 0)
    for step in range(len(PAN_RING) + 1):
        p = ctx.v.find(img, "build/plot_lock", th=0.75, roi=roi)
        if p:
            return p
        if step >= len(PAN_RING):
            break
        nx, ny = PAN_RING[step]
        ctx.dev.swipe(270, 480, 270 + (nx - pos[0]) * dx, 480 + (ny - pos[1]) * dy, 600)
        pos = (nx, ny)
        img = ctx.settle()
    return None


def probe_plot_lock(ctx):
    """Giai doan 1 (chu du an cho phep 2026-11-22: mo lo dat khi KHONG ton kim cuong): camera dang o lo dat khoa ->
    cham o khoa, chup hop thoai + doc chu de biet chi phi. KHONG xac nhan. Tra ve chuoi OCR hop thoai hoac None."""
    p = find_plot_lock(ctx)
    if not p:
        log.info("O khoa lo dat: khong thay bieu tuong tren man")
        inv_capture(ctx, "plot_lock_missing")
        return None
    log.info("O khoa lo dat @%d,%d (%.2f) - mo hop thoai de doc chi phi", p[0], p[1], p[2])
    ctx.tap(p[0], p[1], wait=1.8)
    img = ctx.settle()
    import cv2
    d = os.path.join("logs", "inv", "plot_lock_dialog")
    os.makedirs(d, exist_ok=True)
    cv2.imwrite(os.path.join(d, time.strftime("%Y%m%d-%H%M%S") + f"-i{ctx.dev.idx}.png"), img)
    from bot import ocr
    txt = " | ".join(ocr.text(img, roi, psm=6) or "" for roi in ((0, 150, 540, 400), (0, 400, 540, 400), (0, 760, 540, 200)))
    log.info("O khoa lo dat - hop thoai: %r", txt[:200])
    ctx.back_out(1)
    return txt


FREE_RX = re.compile(r"\bmi\w{1,2}n ph\w{0,2}\b")


def is_free_instant(top, bottom):
    """Nut "Tang cap ngay" CHI duoc bam khi dong duoi ghi "Mien phi" va KHONG co so (gia kim cuong) - chu du an 2026-11-21/22:
    'Tang cap ngay - Mien phi' (0 kim cuong, moc nang cap ngan) thi bam. Ham thuan (text da bo dau, chu thuong)."""
    return "ngay" in top and bool(FREE_RX.search(bottom)) and not re.search(r"\d", bottom)


def free_instant_button(img, up):
    """Nut trai "Tang cap ngay / Mien phi" canh nut "Tang cap" (up = tam nut Tang cap) -> (x, y) | None."""
    from bot import buttons, ocr
    for b in buttons.find(img):
        if abs(b.y - up[1]) > 14 or not 150 < up[0] - b.x < 320:
            continue
        top = buttons._norm(ocr.text(img, (b.x - 70, b.y - 22, 140, 22), scale=3, psm=7, bright=170))
        bottom = buttons._norm(ocr.text(img, (b.x - 60, b.y, 120, 24), scale=3, psm=7, bright=170))
        if is_free_instant(top, bottom):
            return b.x, b.y
    return None


def read_build_time(img, btn):
    """Thoi gian xay ghi duoi nut 'Tang cap' / 'Xay dung' (icon dong ho + 00:00:30) -> giay | None. btn = tam nut.
    Doc 3 lan (Otsu + 2 nguong sang), chi tin khi >= 2 lan cung ra 1 gia tri (icon dong ho hay bi doc thanh so)."""
    from collections import Counter
    x, y = btn[0], btn[1]
    votes = Counter()
    for b in (None, 150, 170):
        t = ocr.seconds(ocr.text(img, (x - 24, y + 7, 74, 26), "0123456789:", scale=4, psm=7, bright=b) or "")
        if t is not None:
            votes[t] += 1
    for v, n in votes.most_common(1):
        if n >= 2:
            return v
    return None


QUICK_IGNORE = frozenset({"observe", "reddots", "upgrade", "construct", "quests", "mainquest"})


def should_quick_wait(pending, busy_total, maxb):
    """(ham thuan) Vua bat dau xay - co DUNG CHO cong trinh ngan xong khong? -> (cho?, ly do).
    P13f-2: con tho dung duoc RANH (busy_total = (dang xay, tong)) -> khong cho, ben goi XAY TIEP NGAY. Moi tho da ban
    va con buoc khac trong luot (pending) -> lam buoc do; runner doc lai tho sau moi buoc, ranh la xay tiep ngay.
    Het tho va khong con viec gi khac -> cho (khong chan ai)."""
    if busy_total is not None and busy_total[0] < min(maxb, busy_total[1]):
        return False, "con tho ranh - xay tiep ngay"
    others = sorted(n for n in (pending or ()) if n not in QUICK_IGNORE)
    if others:
        return False, f"tho dang ban het - lam viec khac ({','.join(others[:4])}), tho ranh la xay tiep"
    return True, ""


SPEEDUP_FREE_RX = r"\bmi\w{1,2}n ph\w{1,2}\b"      # "Mien phi" (OCR eng mat dau)


def free_speedup_button(img, roi=None):
    """Nut 'Mien phi' (0 kim cuong) tren bang Tang toc: nut xanh co chu Mien phi, KHONG co chu so/gia/chu tra phi.
    Ham thuan. -> (x, y) | None. Nut co gia kim cuong / 'Dung' vat pham / 'Tang toc' khong bao gio khop."""
    from bot import buttons
    for b in buttons.with_text(img, SPEEDUP_FREE_RX, roi=roi):
        if not any(ch.isdigit() for ch in b.text):
            return b.x, b.y
    return None


def free_speedup(ctx):
    """Cong trinh dang xay co the co moc 'Tang toc - Mien phi': cham thanh tien do tren thanh pho, neu bang Tang toc co nut
    'Mien phi' thi bam. Khong co -> dong. KHONG bam nut kim cuong / 'Dung' vat pham. -> so lan bam."""
    from bot.modules.observe import progress_bars
    ctx.ensure_city()
    bars = progress_bars(ctx.shot())
    if not bars:
        return 0
    n = 0
    for bx, by, _t in bars[:2]:
        ctx.tap(bx + 10, by - 12, wait=1.5)
        btn = free_speedup_button(ctx.shot())
        if btn:
            ctx.tap(btn[0], btn[1], wait=2.0)
            ctx.skip_dialogs()
            n += 1
            log.info("Tang toc xay: bam nut MIEN PHI (0 kim cuong)")
        ctx.back_out(2)
        ctx.ensure_city()
    return n


def quick_wait(ctx):
    """Goi sau khi bat dau 1 cong trinh. -> True khi tho RANH (ben goi xay tiep ngay): con ranh san (nang cap tuc thi /
    tho thu 2 cua #1), vua bam 'Mien phi' xong, hoac vua cho xong cong trinh ngan (chu du an 2026-11-22: 'xay nhanh thi
    xay lien tuc'; thanh tien do <= build.quick_s giay, tran build.quick_total_s giay / luot). False = moi tho da ban."""
    from bot.modules.observe import progress_bars
    bc = ctx.cfg.get("build", {})
    quick, total_cap = bc.get("quick_s", 180), bc.get("quick_total_s", 600)

    def free_now():
        idle, b = builder_state(ctx)
        if idle:
            ctx.last_build_s = None
            log.info("Xay: con tho ranh (%d/%d, dung toi da %d) - xay tiep ngay", b[0], b[1], max_builders(ctx, b[1]))
        return bool(idle), b

    ctx.ensure_city()
    free, b = free_now()
    if free:
        return True
    pressed = 0
    try:
        pressed = free_speedup(ctx)   # P13d-3: co moc 'Mien phi' thi bam (0 kim cuong), roi moi tinh co cho khong
    except Exception as e:            # noqa: BLE001 - loi o day khong duoc lam hong buoc xay
        log.warning("Tang toc mien phi: loi %s", e)
        ctx.ensure_city()
    ctx.ensure_city()
    if pressed:
        free, b = free_now()
        if free:
            return True
    ok_wait, why_wait = should_quick_wait(getattr(ctx, "visit_pending", None), b, max_builders(ctx, b[1] if b else None))
    if not ok_wait:
        log.info("Xay: %s", why_wait)
        return False
    used = getattr(ctx, "_quick_waited", 0.0)
    if quick <= 0 or used >= total_cap:
        return False
    known = getattr(ctx, "last_build_s", None)      # thoi gian xay doc duoc tren man Tang cap / Xay dung truoc khi bam
    ctx.last_build_s = None
    ts = [known] if known else sorted(t for _, _, t in progress_bars(ctx.shot()) if t)
    if not ts or ts[0] > quick or ts[0] + used > total_cap:
        log.info("Xay: %s - khong cho xay lien tuc", f"con {ts[0]} s > {quick} s" if ts else "khong doc duoc thoi gian xay")
        return False
    t0 = time.time()
    deadline = t0 + ts[0] + 6
    log.info("Xay nhanh (con %d s <= %d s) - cho xong de xay tiep", ts[0], quick)
    while time.time() < deadline:
        time.sleep(4)
        ctx.wd_reset(getattr(ctx, "step_limit", None))   # dang cho co chu dich: dem lai watchdog, giu gioi han buoc
        if builder_state(ctx)[0]:
            break
    ctx._quick_waited = used + (time.time() - t0)
    ctx.ensure_city()
    return True


SUCCESS_ROI = (120, 300, 300, 44)   # chu "Tang cap thanh cong!" giua man Tang cap (anh build_blocked #2/#4 22/11)


def upgraded_ok(img):
    """Man Tang cap dang hien "Tang cap thanh cong!"? (OCR, chu trang tren nen mo). Ham thuan tren anh."""
    from aowbot.domain.blockers import normalize
    for b in (200, None):
        s = normalize(ocr.text(img, SUCCESS_ROI, bright=b, psm=7) or "")
        if "thanh cong" in s or ("tang cap" in s and "thanh c" in s):
            return True
    return False


def upgrade_here(ctx, depth=0, max_depth=4, late=False):
    """Dang o menu cong trinh (icon Tang cap) hoac man Tang cap. Tra ve: 'started' | 'hq_cap' |
    'blocked' (thieu dieu kien/tai nguyen/het tho) | 'none' (khong phai man nang cap)."""
    cap = ctx.cfg.get("build", {}).get("hq_max_level", 22)
    ctx.settle()   # S1: camera con truot sau 'Den'/'Nhay' -> doc man khi da dung yen (A-INV-1: nut hien ngay sau do)
    ic = ctx.find("build/btn_upgrade_icon", fresh=False)
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
        if not ic and not late:   # chua thay gi: cho them 1 nhip on dinh roi doc lai (man nang cap / menu hien tre)
            img = ctx.settle(max_s=4.0)
            if any(ctx.v.find(img, n) for n in ("build/btn_upgrade_icon", "build/btn_upgrade", "build/btn_jump")):
                log.info("Man nang cap hien tre - doc lai")
                return upgrade_here(ctx, depth, max_depth, late=True)
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
    up = ctx.v.find(img, "build/btn_upgrade")
    ctx.last_build_s = read_build_time(img, up) if up else None
    free = free_instant_button(img, up) if up else None
    if free:
        log.info("Tang cap ngay MIEN PHI (0 kim cuong) - bam")
        ctx.tap(free[0], free[1], wait=2.0, tpl="btn:tang_cap_ngay_mien_phi")
    else:
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
    lv2 = screen_level(img)
    if lv is not None and lv2 is not None and lv2 == lv + 1:
        # nang cap xong NGAY (vd 'Tang cap ngay - Mien phi'): man van o trang nang cap cua cap ke tiep, cap hien tai
        # da tang -> la thanh cong, khong phai 'blocked' (do #4 2026-11-22: Radar 1 -> 2 'Tang cap thanh cong!')
        log.info("Da nang cap xong ngay (cap %s -> %s)", lv, lv2)
        ctx.back_out()
        return note_started(ctx)
    if upgraded_ok(img):
        # P4: "Tang cap thanh cong!" (nang ngay mien phi / cong trinh nho) - man van mo trang cap ke tiep nen nut Tang cap
        # con -> truoc bi tinh 'blocked' (7/7 anh build_blocked 22/11) -> ke hoach nha chinh lui 1 gio vo ly
        log.info("Tang cap thanh cong (cap %s -> %s)", lv, lv2 if lv2 is not None else "?")
        ctx.back_out()
        return note_started(ctx)
    if ctx.v.find(img, "build/btn_upgrade") or not ctx.is_home():
        log.info("Khong nang cap duoc (thieu tai nguyen / het tho?) - dong")
        ctx.save_debug("build_blocked")
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
        ctx.back_out()
        return "blocked"
    log.info("Da bat dau nang cap cong trinh (cap %s -> %s)", lv, (lv or 0) + 1)
    return note_started(ctx)
