"""Xay cong trinh MOI theo bang "Xay dung" (icon bua goc phai duoi thanh pho, cham do = so cong trinh xay duoc).
Chu du an 2026-11-21 (#6: "Xay dung dang co 5 cong trinh can xay").

Luong (do tay tren #6 2026-11-21):
  icon bua (build/icon_hammer) -> bang "Xay dung" (build/title_construct): 11 nhom (Tai nguyen, Kho, ...),
  nhom co cham do = co cong trinh xay duoc -> cham nhom -> thanh the cong trinh o day man
  (the bi khoa co o khoa build/card_lock; "x/y" = da xay/toi da) -> KEO the len ban do -> o dat 2x2:
  DO = cho khong hop le, XANH = dat duoc -> nut tick (build/btn_place_ok) -> man "Cap hien tai 0":
  nut PHAI "Xay dung" (build/btn_construct). KHONG BAO GIO bam nut trai "Xay dung ngay" (ke ca khi ghi "Mien phi").
Bo nhom "Con duong" (xay duong khong co ich).
"""
import re, time, logging
import cv2, numpy as np
from bot import ocr
from bot.badges import red_dots

log = logging.getLogger("aow")
HAMMER_ROI = (440, 760, 100, 110)
PANEL_ROI = (60, 250, 420, 470)                  # vung 11 icon nhom trong bang Xay dung
BADGE_OFF = (36, -33)                            # cham do lech so voi tam icon nhom
SKIP_GROUPS = [(110, 650)]                       # "Con duong" (hang Khac, cot 1)
CARD_X = (95, 250, 395)                          # 3 the o thanh day man (cuon ngang neu nhieu hon)
CARD_Y = 862
# diem du phong (giua man; keo sat mep man -> camera troi ra ngoai thanh pho)
TARGETS = [(150, 450), (390, 450), (270, 560), (150, 330), (390, 330), (270, 380)]
SPOT_ZONE = (110, 200, 430, 700)                 # x1, y1, x2, y2: chi chon dich trong vung nay


def footprint(img):
    """O dat cong trinh dang keo: -> ('ok'|'bad', cx, cy, (x, y, w, h)) | None. Xanh la sang = dat duoc, do = khong."""
    hsv = cv2.cvtColor(img[:820], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    for kind, m, need in (("ok", (H >= 45) & (H <= 75) & (S >= 170) & (V >= 200), 700),
                          ("bad", ((H <= 8) | (H >= 172)) & (S >= 150) & (V >= 200), 1800)):
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        n, _, st, c = cv2.connectedComponentsWithStats(m)
        if n > 1:
            i = 1 + int(np.argmax(st[1:, 4]))
            if st[i][4] >= need and st[i][2] >= 120:
                return kind, int(c[i][0]), int(c[i][1]), tuple(int(v) for v in st[i][:4])
    return None


def free_spot(img, box, avoid=()):
    """Cho co trong (o luoi co xanh, khong duong/nha) du lon cho o dat kich thuoc box -> (x, y) | None (ham thuan)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    g = ((H >= 29) & (H <= 40) & (S >= 130) & (S <= 200) & (V >= 85) & (V <= 140)).astype(np.uint8)
    g = cv2.morphologyEx(g, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))   # lap vach ke luoi
    g[820:], g[:110] = 0, 0
    x, y, w, h = box
    g[max(0, y - 10):y + h + 10, max(0, x - 10):x + w + 10] = 0             # cho cong trinh dang keo
    kw, kh = max(60, int(w * 0.9)), max(36, int(h * 0.9))
    k = np.zeros((kh, kw), np.uint8)
    cv2.fillConvexPoly(k, np.array([[kw // 2, 0], [kw - 1, kh // 2], [kw // 2, kh - 1], [0, kh // 2]]), 1)
    d = cv2.distanceTransform(cv2.erode(g, k), cv2.DIST_L2, 3)
    z = np.zeros_like(d)
    z[SPOT_ZONE[1]:SPOT_ZONE[3], SPOT_ZONE[0]:SPOT_ZONE[2]] = 1
    d *= z
    for ax, ay in avoid:
        cv2.circle(d, (ax, ay), 50, 0, -1)
    if d.max() <= 0:
        return None
    yy, xx = np.unravel_index(int(np.argmax(d)), d.shape)
    return int(xx), int(yy)


CAND_ZONE = (80, 190, 460, 740)                  # vung ung vien (sat mep hon -> camera troi)


def spot_candidates(img, box, avoid=(), n=12, min_cover=0.5):
    """Ung vien cho dat xep theo do phu co (ham thuan): kernel hinh thoi cung co o dat, do phu = ti le diem
    'co' duoi no. Chat hon free_spot khong bat buoc phu kin 100% (nen can cu chat: #5 2026-11-22, ban chat, free_spot
    tra None) - game tu bao do/xanh sau moi lan keo nen cho nhieu ung vien tot hon la bo cuoc.
    -> [(x, y, do_phu)] giam dan, cach nhau >= 45px va cach 'avoid' >= 45px."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    g = ((H >= 29) & (H <= 40) & (S >= 130) & (S <= 200) & (V >= 85) & (V <= 140)).astype(np.uint8)
    g = cv2.morphologyEx(g, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    g[820:], g[:110] = 0, 0
    x, y, w, h = box
    g[max(0, y - 10):y + h + 10, max(0, x - 10):x + w + 10] = 0
    kw, kh = max(60, int(w * 0.8)), max(36, int(h * 0.8))
    k = np.zeros((kh, kw), np.float32)
    cv2.fillConvexPoly(k, np.array([[kw // 2, 0], [kw - 1, kh // 2], [kw // 2, kh - 1], [0, kh // 2]]), 1)
    cover = cv2.filter2D(g.astype(np.float32), -1, k / max(1.0, float(k.sum())))
    z = np.zeros_like(cover)
    z[CAND_ZONE[1]:CAND_ZONE[3], CAND_ZONE[0]:CAND_ZONE[2]] = 1
    cover *= z
    for ax, ay in avoid:
        cv2.circle(cover, (ax, ay), 45, 0, -1)
    out = []
    while len(out) < n:
        _, m, _, loc = cv2.minMaxLoc(cover)
        if m < min_cover:
            break
        out.append((int(loc[0]), int(loc[1]), float(m)))
        cv2.circle(cover, loc, 45, 0, -1)
    return out


def card_info(ctx, img, x):
    """The cong trinh o cot x: -> (khoa, da_xay, toi_da) | None (khong co the)."""
    roi = img[CARD_Y - 30:CARD_Y + 45, x - 75:x + 75]
    if float(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY).mean()) < 45:
        return None
    locked = bool(ctx.v.find(img, "build/card_lock", th=0.85, roi=(x - 75, CARD_Y - 40, 150, 60)))
    m = re.search(r"(\d)\s*/\s*(\d)", ocr.text(img, (x + 25, CARD_Y - 18, 50, 22), "0123456789/", scale=4) or "")
    return locked, (int(m.group(1)) if m else None), (int(m.group(2)) if m else None)


BAR_CLOSE_ROI = (430, 820, 110, 110)            # nut X do goc phai duoi thanh dat cong trinh (build/btn_bar_close)


def cancel_place(ctx):
    """Huy dat cong trinh dang keo (khong de cong trinh treo tren ban do): nut X do thanh duoi, roi back_out."""
    if ctx.v.has("build/btn_bar_close"):
        ctx.tap_tpl("build/btn_bar_close", wait=1.0, th=0.8, roi=BAR_CLOSE_ROI)


# ---- P2 muc 2 (PM 2026-11-23): nho the khong dat duoc (construct_no_spot) -> khong lap vo ich, sang the/nhom khac
SKIP_FACT = "construct_skip"           # {khoa the: {"until": epoch, "n": so lan hong, "hq": cap nha chinh luc hong}}
BLOCK_FACT = "construct_block_until"   # moi the co cham do deu dang bi bo qua -> khong mo bang Xay dung toi moc nay
FAIL_REASONS = ("no_spot", "nofp", "no_tick", "no_confirm", "blocked")


def card_key(g, x):
    """Khoa on dinh cho 1 the: vi tri nhom (lam tron 20px, cham do lech vai px giua cac lan) + cot the."""
    return f"{int(round(g[0] / 20.0)) * 20},{int(round(g[1] / 20.0)) * 20},{int(x)}"


def skipped(entries, key, now, hq=None):
    """The dang bi bo qua? (ham thuan) Het han hoac nha chinh da doi cap (thanh pho co the rong them) -> khong."""
    e = (entries or {}).get(key)
    if not e:
        return False
    if hq is not None and e.get("hq") is not None and hq != e.get("hq"):
        return False
    return now < float(e.get("until") or 0)


def note_fail(entries, key, now, hq=None, reason="no_spot", base_h=2.0, cap_h=24.0):
    """Ghi 1 lan dat that bai (ham thuan) -> entries moi. Bo qua base_h * 2^(n-1) gio, toi da cap_h.
    Thieu tai nguyen/tho ('blocked') chi bo 1 gio: het nhanh hon cho trong."""
    out = {k: dict(v) for k, v in (entries or {}).items() if now < float(v.get("until") or 0)}
    n = int((out.get(key) or {}).get("n") or 0) + 1
    hours = 1.0 if reason == "blocked" else min(cap_h, base_h * 2 ** (n - 1))
    out[key] = {"until": now + hours * 3600, "n": n, "hq": hq, "why": reason}
    return out


def block_plan(exhausted, built, eligible, entries, now, hq=None, empty_h=1.0):
    """Sau 1 luot (ham thuan): khong mo lai bang Xay dung toi epoch nao? -> epoch | None.
    Chi khi da xem HET nhom co cham do (exhausted) ma khong xay duoc gi:
      - con the mo nhung deu dang bi bo qua -> toi khi the som nhat het han;
      - khong co the nao mo (cham do cua thu khac / the khoa) -> empty_h gio."""
    if not exhausted or built:
        return None
    if eligible:
        act = [float(v["until"]) for k, v in (entries or {}).items() if skipped(entries, k, now, hq)]
        return min(act) if act else None
    return now + empty_h * 3600


def block_until(ctx):
    """Dang tam bo xay moi (fact BLOCK_FACT {"until", "hq"}) -> epoch | None. Nha chinh doi cap -> het bo."""
    m = getattr(ctx, "mem", None)
    v = m.fact(ctx.dev.idx, BLOCK_FACT) if m else None
    if isinstance(v, dict):
        if v.get("hq") is not None and _hq(ctx) is not None and _hq(ctx) != v.get("hq"):
            return None
        v = v.get("until")
    try:
        t = float(v) if v is not None else None
    except (TypeError, ValueError):
        t = None
    return t if t and t > time.time() else None


def _hq(ctx):
    m = getattr(ctx, "mem", None)
    try:
        return m.fact(ctx.dev.idx, "hq_level") if m else None
    except Exception:
        return None


def place(ctx, x, tries=12):
    """Keo the o cot x len ban do, tim cho xanh, bam tick + "Xay dung".
    -> 'ok' | 'no_spot' | 'nofp' | 'no_tick' | 'no_confirm' | 'blocked' (that bai thi da huy dat)."""
    res = _place(ctx, x, tries)
    if res != "ok":
        cancel_place(ctx)
    return res


def _place(ctx, x, tries):
    ctx.dev.swipe(x, CARD_Y - 30, 270, 450, 1500)
    time.sleep(1.5)
    tried, spare = [], list(TARGETS)
    for _ in range(tries + 1):
        img = ctx.shot()
        fp = footprint(img)
        if not fp:
            ctx.save_debug("construct_nofp")
            return "nofp"
        kind, cx, cy, box = fp
        if kind == "ok":
            ok = ctx.v.find(img, "build/btn_place_ok", th=0.8, roi=(0, min(cy + 40, 760), 540, 200))
            if not ok:
                ctx.save_debug("construct_no_tick")
                return "no_tick"
            ctx.tap(ok[0], ok[1], wait=2.0)
            if not ctx.wait_for("build/btn_construct", timeout=5, th=0.85, roi=(280, 870, 200, 90)):
                ctx.save_debug("construct_no_confirm")
                return "no_confirm"
            from bot import build
            bp = ctx.find("build/btn_construct", th=0.85, roi=(280, 870, 200, 90))
            ctx.last_build_s = build.read_build_time(ctx.shot(), bp[:2]) if bp else None
            ctx.tap_tpl("build/btn_construct", wait=2.5, th=0.85, roi=(280, 870, 200, 90))   # nut PHAI, khong phai "ngay"
            if ctx.find("build/btn_construct", th=0.85, roi=(280, 870, 200, 90)):
                log.info("Xay moi: bam 'Xay dung' nhung van o man xac nhan (thieu tai nguyen/tho?) - bo")
                ctx.save_debug("construct_blocked")
                return "blocked"
            return "ok"
        t = free_spot(img, box, tried)
        if t is None:
            c = spot_candidates(img, box, tried, n=1)
            t = c[0][:2] if c else None
        if t is None:
            if not spare:
                break
            t = spare.pop(0)
        tried.append(t)
        ctx.dev.swipe(cx, cy, t[0], t[1], 1200)
        time.sleep(1.2)
    log.info("Xay moi: khong tim duoc cho trong de dat")
    ctx.save_debug("construct_no_spot")
    return "no_spot"


# ---------- P12-5 (t56u): xay DUONG cho cong trinh thieu duong ----------
ROAD_ICON = "build/road_icon"          # icon vien gach tron vang canh cong trinh thieu duong (vd Cho den)
ROAD_CONFIRM = "build/road_confirm"    # nut "Xac nhan" hop xay duong (chi phi 20 thoi vang)
ROAD_CANCEL = "build/road_cancel"      # nut "Huy" ben trai
ROAD_ZONE = (0, 130, 540, 680)         # vung thanh pho (bo HUD tren / thanh duoi)


def gold_cost(img, btn):
    """Ham thuan P12-5: icon chi phi duoi chu 'Xac nhan' la THOI VANG (mau vang cam, H 10-30) -> True. Kim cuong
    (xanh) / khong chac -> False (KHONG bam Xac nhan). Vung: nua duoi nut, ben trai so."""
    x, y = int(btn[0]), int(btn[1])
    roi = img[max(0, y + 8):y + 34, max(0, x - 40):x]
    if roi.size == 0:
        return False
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    gold = (hsv[..., 0] >= 10) & (hsv[..., 0] <= 30) & (hsv[..., 1] >= 100) & (hsv[..., 2] >= 150)
    return int(gold.sum()) >= 40


def confirm_dialog(img, v):
    """Ham thuan P12-5: hop xay duong = nut 'Xac nhan' (th 0.93) + nut 'Huy' ben trai cung hang -> toa do Xac nhan |
    None (s192252: mot nut xanh khac khop 0.88 nhung khong co 'Huy')."""
    b = v.find(img, ROAD_CONFIRM, th=0.93)
    c = v.find(img, ROAD_CANCEL, th=0.9) if b else None
    return b if b and c and c[0] < b[0] and abs(c[1] - b[1]) < 40 else None


def road_icon(img, v):
    """Ham thuan P12-5: icon vien gach (thieu duong) trong vung thanh pho -> (x, y) | None."""
    x1, y1, x2, y2 = ROAD_ZONE
    p = v.find(img, ROAD_ICON, th=0.85, roi=(x1, y1, x2 - x1, y2 - y1))
    return (int(p[0]), int(p[1])) if p else None


def roads(ctx, max_n=3):
    """P12-5 (chu du an t56u): cong trinh thieu duong co icon vien gach -> bam icon -> hop 'Xac nhan' 20 thoi vang ->
    bam Xac nhan. Chi phi kim cuong / khong nhan ra -> Huy, log ro. Thieu anh mau -> bo qua em. -> so duong da xay."""
    from bot import tplneed
    if not (ctx.cfg.get("construct", {}) or {}).get("roads", True):
        return 0
    if not (tplneed.has(ctx.v, ROAD_ICON, "icon xay duong (vien gach) canh cong trinh")
            and tplneed.has(ctx.v, ROAD_CONFIRM, "nut Xac nhan hop xay duong")):
        return 0
    n = 0
    for _ in range(max_n):
        ctx.ensure_city()
        img = ctx.shot()
        p = road_icon(img, ctx.v)
        if not p:
            break
        log.info("Xay duong: icon thieu duong @%d,%d -> bam", p[0], p[1])
        ctx.tap(p[0], p[1], wait=1.8)
        img = ctx.shot()
        b = confirm_dialog(img, ctx.v)
        if not b:
            log.info("Xay duong: khong thay hop Xac nhan - bo")
            ctx.save_debug("road_no_confirm")
            ctx.tap_first([ROAD_CANCEL, "common/btn_x", "common/btn_close"], wait=1.0)
            break
        if not gold_cost(img, b):
            log.warning("Xay duong: chi phi KHONG phai thoi vang (kim cuong / khong nhan ra) - HUY, khong bam Xac nhan")
            ctx.save_debug("road_gem_cost")
            if not ctx.tap_first([ROAD_CANCEL, "common/btn_x", "common/btn_close"], wait=1.0):
                ctx.press_back()
            break
        ctx.tap(b[0], b[1], wait=2.0)
        n += 1
        log.info("Xay duong: Xac nhan (20 thoi vang) -> da xay duong lan %d", n)
    ctx.ensure_city()
    return n


def run(ctx):
    bc = ctx.cfg.get("construct", {})
    try:
        nr = roads(ctx)                 # P12-5: duong truoc (khong ton tho xay)
    except Exception as e:              # noqa: BLE001 - khong de xay duong lam hong buoc xay moi
        log.warning("Xay duong: loi %s", e)
        nr = 0
        ctx.ensure_city()
    from bot import hqplan
    if hqplan.yield_builder(ctx, "construct"):   # G1: tho ranh dang danh cho nha chinh
        return nr
    bu = block_until(ctx)
    if bu:
        log.info("Xay moi: moi the co cham do deu khong dat duoc (het cho/thieu tai nguyen) - bo toi %s, tho danh cho"
                 " nang cap", time.strftime("%H:%M", time.localtime(bu)))
        return nr
    m = getattr(ctx, "mem", None)
    skips = (m.fact(ctx.dev.idx, SKIP_FACT) if m else None) or {}
    hq = _hq(ctx)
    built, tried, fails, eligible, exhausted = 0, set(), 0, 0, False
    for _ in range(bc.get("max_per_run", 6)):
        if fails >= bc.get("max_fail_per_run", 2):
            log.info("Xay moi: %d lan dat that bai trong luot - dung, de tho cho nang cap", fails)
            break
        ctx.skip_dialogs()            # xay xong hay mo khoa tinh nang -> hoi thoai huong dan (vd "mo khoa lien minh")
        ctx.ensure_city()
        img = ctx.shot()
        h = ctx.v.find(img, "build/icon_hammer", th=0.85, roi=HAMMER_ROI)
        if not h:
            log.info("Xay moi: khong thay icon bua")
            break
        if not red_dots(img, (h[0], h[1] - 50, 60, 50)):
            log.info("Xay moi: icon bua khong co cham do - khong co cong trinh moi")
            break
        ctx.tap(h[0], h[1], wait=1.8)
        img = ctx.shot()
        if not ctx.v.find(img, "build/title_construct", th=0.85):
            ctx.save_debug("construct_panel")
            break
        groups = [(bx - BADGE_OFF[0], by - BADGE_OFF[1]) for bx, by in red_dots(img, PANEL_ROI)]
        groups = [g for g in groups if g not in tried
                  and not any(abs(g[0] - sx) < 40 and abs(g[1] - sy) < 40 for sx, sy in SKIP_GROUPS)]
        if not groups:
            log.info("Xay moi: khong con nhom nao co cham do (hoac da thu)")
            exhausted = True
            break
        g = groups[0]
        tried.add(g)
        ctx.tap(g[0], g[1], wait=2.0)
        img = ctx.shot()
        done = attempted = False
        for x in CARD_X:
            ci = card_info(ctx, img, x)
            if not ci:
                continue
            locked, a, b = ci
            log.info("Xay moi: nhom @%d,%d the cot %d: %s %s/%s", g[0], g[1], x, "KHOA" if locked else "mo", a, b)
            if locked or (a is not None and b is not None and a >= b):
                continue
            key = card_key(g, x)
            eligible += 1
            if skipped(skips, key, time.time(), hq):
                log.info("Xay moi: the %s vua dat that bai (%s) - bo qua, thu the/nhom khac", key,
                         skips[key].get("why"))
                continue
            attempted = True
            res = place(ctx, x)
            if res == "ok":
                built += 1
                done = True
                skips.pop(key, None)
                from bot import build
                build.quick_wait(ctx)     # xay nhanh -> cho xong, vong sau xay tiep (chu du an 2026-11-22)
                log.info("Xay moi: da xay 1 cong trinh (nhom @%d,%d)", g[0], g[1])
            else:
                fails += 1
                skips = note_fail(skips, key, time.time(), hq, res, bc.get("nospot_backoff_h", 2),
                                  bc.get("nospot_cap_h", 24))
                log.info("Xay moi: the %s that bai (%s) -> bo qua %.1f gio, chon the/nhom khac", key, res,
                         (skips[key]["until"] - time.time()) / 3600)
            break                     # da keo 1 the: man da doi (dat xong / huy) -> mo lai bang tu dau
        if not done:
            ctx.back_out(2)
        if done or attempted:
            tried.discard(g)          # nhom con the khac/cung loai (vd 0/3 -> 1/3; the hong da bi bo qua) -> mo lai
    if m:
        m.set_fact(ctx.dev.idx, SKIP_FACT, skips)
        until = block_plan(exhausted, built, eligible, skips, time.time(), hq, bc.get("empty_recheck_h", 1))
        m.set_fact(ctx.dev.idx, BLOCK_FACT, {"until": until, "hq": hq} if until else None)
        if until:
            log.info("Xay moi: khong con the hop le - tho danh cho nang cap (upgrade/quests) toi %s",
                     time.strftime("%H:%M", time.localtime(until)))
    ctx.ensure_city()
    if built:
        if hqplan.after_construct(ctx):   # G1: vua xay cong trinh moi (co the la dieu kien cua nha chinh) -> thu lai ngay
            from bot.modules import upgrade
            upgrade.run(ctx)
    return built + nr
