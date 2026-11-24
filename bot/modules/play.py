"""Loi choi (nut "Loi choi" thanh duoi) - chu du an chi 2026-11-21 tren TK chinh #1 (cf30):

  Mo khoang san: tab "Xe khai thac cua toi" -> cham ruong (bong bong ruong vang tren xe) -> nhan thuong.
  Dau truong  : 3 luot "Khieu chien mien phi" / ngay. CHI danh doi thu co LUC CHIEN MAU DO; nho doi thu da
                THUA (khong danh lai trong arena.lost_days ngay). Khong bam "Lam moi" / mua luot (co the ton kim cuong).
TK farm cap thap chua mo -> khong thay nut "Loi choi" / the -> bo qua.
"""
import logging, re, time
import cv2, numpy as np
from bot import ocr
from bot.modules import campaign

log = logging.getLogger("aow")


def open_menu(ctx):
    ctx.ensure_city()
    if not ctx.tap_tpl("play/btn_open", wait=2.0, th=0.85, roi=(330, 860, 160, 100)):
        return False
    return bool(ctx.wait_for("play/card_mine", timeout=3, th=0.85) or ctx.find("play/card_arena", th=0.85))


# ---------- mo khoang san ----------
def mine(ctx):
    if not ctx.tap_tpl("play/card_mine", wait=2.5, th=0.85):
        return 0
    n = 0
    if ctx.wait_for("play/mine_title", timeout=3):
        for _ in range(6):
            p = ctx.find("play/mine_chest", th=0.8)
            if not p:
                break
            ctx.tap(p[0], p[1], wait=1.5)
            ctx.dismiss_reward()
            n += 1
            log.info("Mo khoang san: nhan ruong xe khai thac @%d,%d", p[0], p[1])
        from bot.modules import mine_trucks            # P9-6: xe khai thac CUA TOI truoc khi cuop xe nguoi khac
        try:
            n += mine_trucks.run(ctx)
        except Exception as e:                           # loi xe cua toi khong lam hong cuop xe / dau truong
            log.warning("Xe khai thac cua toi: loi %s", e)
            ctx.save_debug("mine_trucks")
        if not ctx.find("play/mine_title"):
            ctx.back_out(1)
        if ctx.cfg.get("loot", {}).get("enabled", True) and ctx.find("play/mine_title"):
            n += loot(ctx)
            if not ctx.find("play/mine_title"):
                return n                                # da di cuop (ve thanh pho) -> khong back_out them
    else:
        log.info("Mo khoang san: khong thay man Mo khoang san")
        ctx.save_debug("mine_open")
    ctx.back_out(1)
    return n


# ---------- cuop boc xe khai thac (chu du an lam mau 2026-11-21 01:11 tren #1) ----------
# Mo khoang san -> tab "Xe khai thac cua nguoi khac" -> cham xe CAM (SSR) / TIM (SR) -> popup (ten, luc chien)
# -> "Toi cuop boc" -> ban do: "Cuop boc" -> Cai dat quan doan (luc chien quan doan minh) -> "Chien dau" -> ket qua.
# 4 luot / ngay, reset 4h UTC (game hien "So lan cuop boc con lai: N/4"). Nho: nguoi cuop THUA (khong danh lai),
# nguong luc chien: ti le (doi thu / quan doan minh) da thang cao nhat, da thua thap nhat.
def loot_trucks(img):
    """Xe khai thac CAM (SSR) / TIM (SR) tren duong (bo xe xanh la / xanh duong). -> [(mau, x, y)]"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    out = []
    for name, m in (("purple", (H >= 120) & (H <= 170) & (S >= 50) & (V >= 50)),
                    ("orange", ((H <= 12) | (H >= 172)) & (S >= 110) & (V >= 70))):
        m = m.astype(np.uint8)
        m[:240], m[760:], m[:, :50], m[:, 490:] = 0, 0, 0, 0
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
        n, _, st, c = cv2.connectedComponentsWithStats(m)
        out += [(name, int(c[i][0]), int(c[i][1])) for i in range(1, n)
                if st[i][4] >= 250 and 20 <= st[i][2] <= 90 and 30 <= st[i][3] <= 120]
    return out


def is_burning(img, x, y, half=(38, 48)):
    """P7-6: xe DANG CHAY / da bi nguoi khac cuop (dau X do + lua, anh chu du an plunder_0) -> KHONG BAO GIO danh.
    Dau X = net do manh, mong: thanh phan do lon (>= 25x25) nhung lap day thap (< 0,35); than xe cam (SSR) lap day cao."""
    hw, hh = half
    x0, y0 = max(0, x - hw), max(0, y - hh)
    box = img[y0:y + hh, x0:x + hw]
    if box.size == 0:
        return False
    hsv = cv2.cvtColor(box, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (((H <= 8) | (H >= 172)) & (S >= 150) & (V >= 140)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    return any(st[i][2] >= 25 and st[i][3] >= 25 and st[i][4] < 0.35 * st[i][2] * st[i][3] for i in range(1, n))


CRYSTAL_ROI = (40, 650, 200, 80)   # hang vat pham van chuyen tren popup xe (duoi dong luc chien y~634)


def crystal_item(img, roi=CRYSTAL_ROI, min_px=120):
    """P7-6: xe chu du an cho cuop = xe CHO VAT PHAM PHA LE XANH (anh plunder_5: o vat pham dau). Pha le xanh nhat:
    H 85-110, S 60-210, V >= 170 (nen popup tim H~130, hop qua vang/xam, tang toc vang -> khong khop)."""
    x, y, w, h = roi
    hsv = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    return int(((H >= 85) & (H <= 110) & (S >= 60) & (S <= 210) & (V >= 170)).sum()) >= min_px


def has_crystal(ctx, img):
    """Anh mau play/item_crystal (neu da cat) truoc, khong co thi theo mau."""
    from bot import tplneed
    if tplneed.has(ctx.v, "play/item_crystal", "vat pham pha le xanh tren popup xe"):
        return bool(ctx.v.find(img, "play/item_crystal", th=0.8, roi=CRYSTAL_ROI))
    return crystal_item(img)


def refresh_trucks(ctx, lc):
    """P7-6: nut lam moi (mui ten tron, play/btn_refresh) de tim xe SR/SSR. Toi da loot.refresh_max lan / luot.
    Sau khi bam: bang khac hien (hop thoai ton phi / xac nhan) -> dong, KHONG xac nhan, dung lam moi."""
    from bot import tplneed
    cap = lc.get("refresh_max", 3)
    if not tplneed.has(ctx.v, "play/btn_refresh", "nut lam moi xe khai thac") or getattr(ctx, "_loot_refresh", 0) >= cap:
        return False
    if not ctx.tap_tpl("play/btn_refresh", wait=2.0, th=0.85):
        return False
    ctx._loot_refresh = getattr(ctx, "_loot_refresh", 0) + 1
    if not ctx.find("play/tab_others", th=0.8):
        log.info("Cuop boc: bam lam moi hien bang khac (co the ton phi) -> dong, khong lam moi nua")
        ctx.save_debug("loot_refresh_popup")
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=1.0)
        ctx._loot_refresh = cap
        return False
    log.info("Cuop boc: lam moi danh sach xe (%d/%d)", ctx._loot_refresh, cap)
    return True


def popup_rarity(img):
    """Chu SSR (vang H~21) / SR (tim H~135) o goc trai tren popup xe."""
    hsv = cv2.cvtColor(img[520:560, 65:165], cv2.COLOR_BGR2HSV).reshape(-1, 3)
    r = hsv[(hsv[:, 1] > 120) & (hsv[:, 2] > 150)]
    if len(r) < 200:
        return None
    h = float(np.median(r[:, 0]))
    return "SSR" if 10 <= h <= 35 else "SR" if 120 <= h <= 165 else None


def _digits(img, roi):
    d = re.sub(r"\D", "", ocr.text(img, roi, "0123456789", scale=4) or "")
    return int(d) if 5 <= len(d) <= 11 else None


def loot_left(img):
    """'So lan cuop boc con lai: N/4' -> N | None."""
    m = re.search(r"(\d)\s*/\s*(\d)", ocr.text(img, (160, 866, 250, 24)) or "")
    return int(m.group(1)) if m else None


def _loot_mem(ctx):
    m = getattr(ctx, "mem", None)
    return (m.fact(ctx.dev.idx, "loot_mem") or {}) if m else {}


def _loot_save(ctx, d):
    m = getattr(ctx, "mem", None)
    if m:
        m.set_fact(ctx.dev.idx, "loot_mem", d)


def loot_ok(lm, power, name=None, legion=None, margin=0.97, now=None):
    """Co nen cuop doi thu luc chien 'power' khong (ham thuan). -> (True|False, ly do)
    - da THUA nguoi nay (ten hoac luc chien +-3 %) trong 14 ngay -> khong
    - luc chien >= nguong da thua thap nhat x margin -> khong
    - biet luc chien quan doan minh: ti le doi thu/minh >= ti le da thua -> khong; > max(1, ti le da thang x 1,15) -> khong
      (chua thang lan nao: chi danh doi thu YEU hon quan doan minh)."""
    now = now or time.time()
    if power is None:
        return False, "khong doc duoc luc chien"
    for x in lm.get("lost", []):
        if now - x.get("at", 0) > 14 * 86400:
            continue
        if (name and x.get("name") and name == x["name"]) or abs(power - x.get("power", 0)) <= 0.03 * power:
            return False, f"da thua {x.get('name') or ''} truoc day"
    if lm.get("lose_min") and power >= lm["lose_min"] * margin:
        return False, f"luc chien >= nguong da thua {lm['lose_min']:,}"
    if legion:
        r = power / legion
        if lm.get("ratio_bad") and r >= lm["ratio_bad"] * margin:
            return False, f"ti le {r:.2f} >= ti le da thua {lm['ratio_bad']:.2f}"
        cap = max(1.0, (lm.get("ratio_ok") or 0) * 1.15)
        if r > cap:
            return False, f"ti le {r:.2f} > nguong thang {cap:.2f}"
    return True, "ok"


def _loot_result(ctx, timeout=120):
    """Sau 'Chien dau': 'lose' (man That bai) | 'win' (man thang / thuong) | 'unknown'."""
    from bot.steer import result_of
    t0 = time.time()
    while time.time() - t0 < timeout:
        img = ctx.shot()
        if ctx.v.find(img, "play/res_fail", th=0.8):
            ctx.save_debug("loot_lose")
            ctx.tap(270, 703, wait=1.5)                 # nut "Dong" cua man That bai
            return "lose"
        if ctx.v.has("play/res_loot_win") and ctx.v.find(img, "play/res_loot_win", th=0.8):
            ctx.save_debug("loot_win")                  # P7-6: man "Thang loi" -> "Dong" (anh plunder_4)
            if not ctx.tap_tpl("play/btn_result_close", wait=2.0, th=0.8, fresh=False):
                ctx.tap(270, 703, wait=2.0)
            return "win"
        if ctx.v.find(img, "play/res_arena_win", th=0.8):   # man thang giong dau truong (doan, chua thay that)
            ctx.save_debug("loot_win")
            if not ctx.tap_tpl("play/btn_result_close", wait=2.0, th=0.8, fresh=False):
                ctx.tap(270, 799, wait=2.0)
            return "win"
        if (ctx.v.find(img, "campaign/res_win") or ctx.v.find(img, "common/msg_reward", th=0.75)
                or (ctx.v.find(img, "campaign/btn_done") and result_of(ctx.v, img) == "win")):
            ctx.save_debug("loot_win")
            ctx.dismiss_reward()
            ctx.close_popups(2)
            return "win"
        time.sleep(2.0)
    ctx.save_debug("loot_unknown")
    return "unknown"


GUARD_ROI = (155, 634, 120, 24)    # luc chien ho ve canh icon kiem duoi ten nguoi choi (popup xe; anh ADB truck1 98565656)
LEGION_ROI = (68, 360, 120, 26)    # luc chien quan doan minh tren man doi hinh "Chien dau" (fixture loot_legion_i1 220020045)
LEGION_BAND = (60, 330, 220, 140)  # vung do du phong khi LEGION_ROI khong doc duoc (doi hinh lech vai px)
SKIP_H = 12                        # xe da bo vi ho ve manh hon: khong xet lai trong N gio


def _n(v):
    return f"{v:,}" if v else str(v)


def guard_power(img):
    """Luc chien ho ve xe (popup xe "Toi cuop boc") | None."""
    return _digits(img, GUARD_ROI)


def own_power(img):
    """Luc chien doi hinh cua ta tren man "Chien dau" (sau "Doi hinh de xuat") | None. Vung co dinh truoc, khong doc
    duoc thi quet cac dong trong LEGION_BAND (so 8-11 chu so dau tien tu tren xuong)."""
    v = _digits(img, LEGION_ROI)
    if v:
        return v
    x, y0, w, h = LEGION_BAND
    for y in range(y0, y0 + h - 24, 12):
        d = re.sub(r"\D", "", ocr.text(img, (x, y, w, 26), "0123456789", scale=4) or "")
        if 8 <= len(d) <= 11:
            return int(d)
    return None


def power_check(guard, ours, margin=0.0):
    """P8-2 (chu du an 2026-11-24, lan cuop xe SR thua: ho ve 243.560.931 > ta 222.749.681). Ham thuan -> (ok, ly do).
    Chi danh khi DOC DUOC ca hai so, ho ve < ta va ta >= ho ve x (1 + margin). Khong doc duoc -> khong danh mo."""
    if not guard:
        return False, "khong doc duoc luc chien ho ve"
    if not ours:
        return False, "khong doc duoc luc chien ta"
    if guard >= ours:
        return False, f"ho ve {guard:,} >= ta {ours:,}"
    if ours < guard * (1 + (margin or 0.0)):
        return False, f"ta {ours:,} < ho ve {guard:,} x {1 + margin:.2f}"
    return True, "ok"


def _skipped(lm, name, power, now=None):
    """Xe (ten / luc chien +-1 %) da bo vi ho ve manh hon trong SKIP_H gio."""
    now = now or time.time()
    for x in lm.get("skip", []):
        if now - x.get("at", 0) > SKIP_H * 3600:
            continue
        if (name and x.get("name") == name) or (power and x.get("power") and abs(power - x["power"]) <= 0.01 * power):
            return True
    return False


def _mark_skip(lm, name, power, now=None):
    now = now or time.time()
    lm["skip"] = [x for x in lm.get("skip", []) if now - x.get("at", 0) <= SKIP_H * 3600][-30:]
    lm["skip"].append({"name": name, "power": power, "at": now})


# ---------- P9-5 (live-run-2 11:04: popup "Da chuyen doi sang sv ServerID #28" + xe N chi co nut "Xem") ----------
WORLD_HDR = (140, 212, 100, 50)          # chu do hiem SSR/SR/N goc trai tren popup xe tren BAN DO
WORLD_BTN_ROI = (130, 540, 290, 70)      # hang nut "Xem" (trai) | "Cuop boc" (phai) day popup
TOAST_ROI = (0, 295, 540, 60)            # dai thong bao "Da chuyen doi sang sv ServerID #.."
SERVER_RX = re.compile(r"chuy\w{0,2}n\s*d\w{0,2}i|server\s*id|sang\s*sv")
LOOT_RX = r"cu\w{0,2}p\s*b"              # chu "Cuop boc" (OCR mat dau)


def world_rarity(img):
    """Do hiem tren popup xe o ban do: SSR (vang H~20), SR (tim H 120-165), N (xanh la H 40-85) | None."""
    x, y, w, h = WORLD_HDR
    hsv = cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2HSV).reshape(-1, 3)
    r = hsv[(hsv[:, 1] > 120) & (hsv[:, 2] > 150)]
    if len(r) < 200:
        return None
    hue = float(np.median(r[:, 0]))
    return "SSR" if 10 <= hue <= 35 else "SR" if 120 <= hue <= 165 else "N" if 40 <= hue <= 85 else None


def server_toast(img):
    from bot import buttons
    return bool(SERVER_RX.search(buttons._norm(ocr.text(img, TOAST_ROI, scale=2, psm=6))))


def loot_button(ctx, img):
    """Nut "Cuop boc" (BEN PHAI, chu 'cuop boc') -> (x, y) | None. KHONG BAO GIO tra nut "Xem"."""
    from bot import buttons
    for b in buttons.with_text(img, LOOT_RX, WORLD_BTN_ROI):
        if "xem" not in b.text and b.x >= 300:
            return b.x, b.y
    p = ctx.v.find(img, "play/btn_loot", th=0.8, roi=WORLD_BTN_ROI)
    return (p[0], p[1]) if p and p[0] >= 300 else None


def world_popup_kind(rarity, btn, toast, rar=("SSR", "SR")):
    """Ham thuan: popup tren ban do sau "Toi cuop boc" -> 'loot' (dung popup: SR/SSR + nut Cuop boc) |
    'server_change' (thong bao doi server / xe khac) | 'no_loot_btn' (chi co "Xem") | 'wrong_rarity'."""
    if btn and rarity in rar and not toast:
        return "loot"
    if toast:
        return "server_change"
    if not btn:
        return "no_loot_btn"
    return "wrong_rarity"


def world_popup(ctx, rar, timeout=6.0):
    """Cho popup xe tren ban do (toi `timeout` s). -> (loai, toa do nut Cuop boc | None)."""
    t0, kind, btn = time.time(), "no_loot_btn", None
    while time.time() - t0 < timeout:
        img = ctx.shot()
        btn = loot_button(ctx, img)
        kind = world_popup_kind(world_rarity(img), btn, server_toast(img), rar)
        if kind in ("loot", "server_change"):
            break
        time.sleep(0.6)
    return kind, btn


def _reopen_mine(ctx):
    """Sau khi bo xe o man doi hinh (dang o ban do) -> ve Loi choi > Mo khoang san de thu xe khac."""
    ctx.ensure_city()
    if not open_menu(ctx) or not ctx.tap_tpl("play/card_mine", wait=2.5, th=0.85):
        return False
    return bool(ctx.wait_for("play/mine_title", timeout=3))


def loot(ctx):
    """Dang o man Mo khoang san. -> so lan cuop da danh (0/1).
    P7-6 (chu du an 2026-11-24): doc "So lan cuop boc con lai X/4" (0 -> bo); KHONG BAO GIO danh xe dang chay; chi xe
    SR/SSR cho vat pham PHA LE XANH (loot.crystal_only); chua co -> nut lam moi (toi da loot.refresh_max).
    P8-2: so luc chien ho ve (popup) voi luc chien ta (man doi hinh, sau "Doi hinh de xuat"); ho ve >= ta -> KHONG bam
    "Chien dau", thoat, danh dau xe da bo, thu xe khac (toi da loot.max_attempts lan mo man doi hinh).
    Luong: popup xe "Toi cuop boc" -> ban do "Cuop boc" -> doi hinh "Chien dau" -> "Thang loi"/"That bai" -> "Dong"."""
    lc = ctx.cfg.get("loot", {})
    if not lc.get("enabled", True):
        return 0
    tries = max(1, lc.get("max_attempts", 2))
    for k in range(tries):
        r = _loot_once(ctx, lc)
        if r != "retry":
            return r
        if k + 1 >= tries or not _reopen_mine(ctx):
            break
    ctx.ensure_city()
    return 0


def _loot_once(ctx, lc):
    """1 lan chon xe + mo man doi hinh. -> 0 | 1 | "retry" (bo xe o man doi hinh vi ho ve manh hon -> thu xe khac)."""
    # anh mau tab cat luc DANG CHON (nen xanh); chua chon nen toi -> khong khop (2026-11-21: bot lang le bo qua) -> cham toa do
    if not ctx.tap_tpl("play/tab_others", wait=2.0, th=0.85):
        ctx.tap(365, 90, wait=2.0)
    img = ctx.shot()
    if not ctx.v.find(img, "play/tab_others", th=0.8):
        log.info("Cuop boc: khong mo duoc tab 'Xe khai thac cua nguoi khac'")
        ctx.save_debug("loot_tab")
        return 0
    left = loot_left(img)
    log.info("Cuop boc: con %s/4 luot, %d xe cam/tim tren duong", left, len(loot_trucks(img)))
    if left == 0:
        log.info("Cuop boc: het luot hom nay (reset %dh UTC)", lc.get("reset_utc", 4))
        return 0
    if ctx.march_full():
        log.info("Cuop boc: het quan doan ranh (hanh quan day) - de lan sau")
        return 0
    lm = _loot_mem(ctx)
    legion = lm.get("legion")
    pmargin = lc.get("power_margin", 0.0)
    rar = tuple(lc.get("rarity", ["SSR", "SR"]))
    crystal_only = lc.get("crystal_only", True)
    cands = []                                          # doc tung xe cam/tim -> chon doi thu YEU NHAT dat nguong
    for _round in range(1 + lc.get("refresh_max", 3)):
        for col, x, y in loot_trucks(img)[:8]:
            if is_burning(img, x, y):                   # P7-6: xe dang chay (da bi cuop) -> KHONG BAO GIO danh
                log.info("Cuop boc: xe %s @%d,%d dang chay (da bi cuop) - bo", col, x, y)
                continue
            ctx.tap(x, y, wait=1.2)
            p = ctx.shot()
            if not ctx.v.find(p, "play/btn_go_loot", th=0.8):
                ctx.tap(270, 150, wait=0.8)
                continue
            r = popup_rarity(p)
            pw = guard_power(p)
            name = (ocr.text(p, (133, 585, 170, 26)) or "").strip()
            ok, why = loot_ok(lm, pw, name, legion, lc.get("margin", 0.97))
            if r not in rar:
                ok, why = False, f"do hiem {r}"
            elif crystal_only and not has_crystal(ctx, p):
                ok, why = False, "khong cho pha le xanh"
            elif _skipped(lm, name, pw):
                ok, why = False, f"da bo trong {SKIP_H}h (ho ve manh hon)"
            elif ok and legion:                         # P8-2 loc som theo luc chien ta doc o man doi hinh lan truoc
                ok, why = power_check(pw, legion, pmargin)
            log.info("Cuop boc: xe %s %s '%s' luc chien %s -> %s", col, r, name, pw, "CHON DUOC" if ok else why)
            if ok:
                cands.append((pw, x, y, name))
            ctx.tap(270, 150, wait=0.8)                 # dong popup (cham ra ngoai)
        if cands or not refresh_trucks(ctx, lc):        # P7-6: chua co xe SR/SSR pha le -> lam moi
            break
        img = ctx.shot()
    if not cands:
        log.info("Cuop boc: khong co xe SR/SSR cho pha le nao trong nguong luc chien")
        return 0
    pw, x, y, name = min(cands)
    if is_burning(ctx.shot(), x, y):                    # xe vua bi nguoi khac cuop trong luc doc
        log.info("Cuop boc: xe '%s' vua bi cuop (dang chay) - bo", name)
        return 0
    ctx.tap(x, y, wait=1.2)
    if not ctx.tap_tpl("play/btn_go_loot", wait=3.0, th=0.8):
        return 0
    # P9-5: XAC NHAN dung popup cuop (SR/SSR + nut "Cuop boc"); popup doi server / xe N chi co "Xem" -> dong, bo xe
    kind, btn = world_popup(ctx, rar)
    if kind != "loot":
        ctx.save_debug(f"loot_popup_{kind}")
        log.info("Cuop boc: popup ban do sai (%s) - dong, bo xe '%s', chon xe khac", kind, name)
        _mark_skip(lm, name, pw)
        _loot_save(ctx, lm)
        ctx.back_out(1)                                 # dong popup / thong bao (KHONG bam "Xem")
        return "retry"
    ctx.tap(btn[0], btn[1], wait=2.5)                   # nut "Cuop boc" (ben phai) - khong bao gio "Xem"
    if not ctx.wait_for("play/btn_battle", timeout=5):
        ctx.save_debug("loot_no_legion")
        ctx.ensure_city()
        return 0
    # P8-2: "Doi hinh de xuat" TRUOC roi moi doc luc chien ta (doi hinh de xuat doi luc chien); CHUA bam Chien dau
    ctx.tap_tpl("play/btn_arena_recommend", wait=1.5, th=0.85, fresh=False)
    lg = own_power(ctx.shot())
    if lg:
        lm["legion"] = legion = lg
    ok, why = power_check(pw, lg, lc.get("power_margin", 0.0))
    if ok:
        ok, why = loot_ok(lm, pw, name, legion, lc.get("margin", 0.97))
    if not ok:
        if not lg:
            ctx.save_debug("loot_own_power")
        log.info("Cuop boc: ho ve %s > ta %s -> bo ('%s': %s)", _n(pw), _n(lg), name, why)
        _mark_skip(lm, name, pw)
        _loot_save(ctx, lm)
        ctx.back_out(3)                                 # thoat man doi hinh, KHONG bam Chien dau
        return "retry"
    ctx.tap_tpl("play/btn_battle", wait=3.0)
    r = _loot_result(ctx)
    ratio = pw / legion if legion else None
    if r == "lose":
        lm.setdefault("lost", []).append({"name": name, "power": pw, "at": time.time()})
        lm["lost"] = lm["lost"][-60:]
        lm["lose_min"] = min(lm.get("lose_min") or pw, pw)
        if ratio:
            lm["ratio_bad"] = min(lm.get("ratio_bad") or ratio, ratio)
    elif r == "win":
        lm["win_max"] = max(lm.get("win_max") or 0, pw)
        if ratio:
            lm["ratio_ok"] = max(lm.get("ratio_ok") or 0, ratio)
    _loot_save(ctx, lm)
    log.info("Cuop boc '%s' luc chien %s (quan doan %s) -> %s", name, pw, legion, r)
    ctx.ensure_city()
    return 1


# ---------- dau truong ----------
def power_red(img, by):
    """Luc chien doi thu (cung hang voi nut Khieu chien, x 290-380) mau DO? Chu trang binh thuong: H~110 S~35."""
    hsv = cv2.cvtColor(img[by + 2:by + 20, 290:385], cv2.COLOR_BGR2HSV).reshape(-1, 3)
    txt = hsv[hsv[:, 2] >= 140]
    if len(txt) < 30:
        return False
    red = ((txt[:, 0] <= 8) | (txt[:, 0] >= 170)) & (txt[:, 1] >= 110)
    return red.mean() >= 0.4


def read_power(img, by):
    d = re.sub(r"\D", "", ocr.text(img, (298, by + 1, 85, 20), "0123456789", scale=4) or "")
    return int(d) if 4 <= len(d) <= 11 else None


def _lost(ctx):
    m = getattr(ctx, "mem", None)
    days = ctx.cfg.get("arena", {}).get("lost_days", 7)
    lst = (m.fact(ctx.dev.idx, "arena_lost") or []) if m else []
    return [x for x in lst if time.time() - x.get("at", 0) < days * 86400]


def _is_lost(lost, power):
    return power is not None and any(abs(power - x["power"]) <= 0.03 * x["power"] for x in lost if x.get("power"))


def _remember_lost(ctx, power):
    m = getattr(ctx, "mem", None)
    if m and power:
        lst = _lost(ctx) + [{"power": power, "at": time.time()}]
        m.set_fact(ctx.dev.idx, "arena_lost", lst[-50:])


def fight(ctx):
    """Da bam Khieu chien -> (doi hinh: tu xep) -> Chien dau -> cho ket qua. -> 'win' | 'lose' | 'unknown'"""
    # man Cai dat quan doan (giong cuop boc): "Doi hinh de xuat" + "Chien dau" do (anh #1 2026-11-21 05:24)
    if ctx.wait_for("play/btn_arena_fight", timeout=6, th=0.85):
        ctx.tap_tpl("play/btn_arena_recommend", wait=1.5, th=0.85, fresh=False)   # luon xep doi hinh toi uu
        if not ctx.tap_tpl("play/btn_arena_fight", wait=2.5, th=0.85):
            ctx.save_debug("arena_no_fight")
            ctx.back_out(2)
            return "unknown"
    elif ctx.find("tutorial/btn_auto_formation", th=0.8, roi=(440, 860, 100, 100)) or ctx.find("campaign/btn_fight", fresh=False):
        ctx.tap_tpl("tutorial/btn_auto_formation", wait=1.5, th=0.8, roi=(440, 860, 100, 100), fresh=False)
        if not ctx.tap_tpl("campaign/btn_fight", wait=2.0):
            ctx.save_debug("arena_no_fight")
            ctx.back_out(2)
            return "unknown"
    from bot.steer import result_of
    t0 = time.time()
    while time.time() - t0 < 150:
        img = ctx.shot()
        if (ctx.v.find(img, "campaign/btn_done") or ctx.v.find(img, "campaign/btn_done_lose")
                or ctx.v.find(img, "campaign/res_win") or ctx.v.find(img, "campaign/res_lose")):
            r = result_of(ctx.v, img)
            if r == "lose":
                ctx.save_debug("arena_lose")
            campaign.close_result(ctx)
            return r
        if ctx.v.find(img, "play/res_arena_win", th=0.8):   # "Thang toan dien" + Nhan thuong + nut Dong (#1 05:37)
            if not ctx.tap_tpl("play/btn_result_close", wait=2.0, th=0.8, fresh=False):
                ctx.tap(270, 799, wait=2.0)
            return "win"
        if ctx.v.find(img, "play/res_fail", th=0.8):    # man "That bai" kieu cuop boc (nut Dong)
            ctx.save_debug("arena_lose")
            ctx.tap(270, 703, wait=1.5)
            return "lose"
        if ctx.v.find(img, "play/arena_title"):         # tran xong nhanh / tu ve bang dau truong
            return "unknown"
        time.sleep(2.0)
    ctx.save_debug("arena_timeout")
    ctx.back_out(2)
    return "unknown"


def arena_eligible(pw, red, own, ratio, only_red=False, weaker_only=False):
    """Doi thu co duoc danh khong (ham thuan). Luat chu du an 2026-11-21: luc chien MAU DO uu tien, khong can so;
    con lai chi khi luc chien <= luc chien minh x ratio. A-SAFE-3: khong doc duoc luc chien minh (own None/0)
    -> chi doi thu mau do (truoc day moi doi thu deu hop le va max() chon doi thu MANH nhat).
    P7-10 (chu du an 2026-11-24) weaker_only: CHI doi thu luc chien YEU HON minh (< own x ratio), mau do khong mien;
    khong biet luc chien minh -> khong danh."""
    if pw is None or (only_red and not red):
        return False
    if weaker_only:
        return bool(own) and pw < own * ratio
    if red:
        return True
    return bool(own) and pw <= own * ratio


def arena_refresh(ctx, ac):
    """P7-10: nut "Lam moi" danh sach doi thu (play/btn_arena_refresh), toi da arena.refresh_max lan / luot. Chu tren
    nut co dau hieu tra phi (kim cuong / gia) -> khong bam; bam xong hien hop thoai khac -> dong, khong xac nhan, dung."""
    from bot import buttons, tplneed
    cap = ac.get("refresh_max", 3)
    if not tplneed.has(ctx.v, "play/btn_arena_refresh", "nut Lam moi dau truong") or getattr(ctx, "_arena_refresh", 0) >= cap:
        return False
    img = ctx.shot()
    p = ctx.v.find(img, "play/btn_arena_refresh", th=0.85)
    if not p:
        return False
    txt = ocr.text(img, (max(0, p[0] - 70), max(0, p[1] - 22), 140, 44)) or ""
    if buttons.is_danger(txt) or re.search(r"\d", txt):
        log.info("Dau truong: nut Lam moi co dau hieu ton phi (%r) - khong bam", txt[:20])
        ctx._arena_refresh = cap
        return False
    ctx.tap(p[0], p[1], wait=2.0)
    ctx._arena_refresh = getattr(ctx, "_arena_refresh", 0) + 1
    if not ctx.wait_for("play/arena_title", timeout=3):
        log.info("Dau truong: bam Lam moi hien bang khac (co the ton phi) -> dong, dung")
        ctx.save_debug("arena_refresh_popup")
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=1.0)
        ctx._arena_refresh = cap
        return False
    log.info("Dau truong: Lam moi danh sach doi thu (%d/%d)", ctx._arena_refresh, cap)
    return True


def arena(ctx):
    ac = ctx.cfg.get("arena", {})
    if not ac.get("enabled", True) or not ctx.tap_tpl("play/card_arena", wait=2.5, th=0.85):
        return 0
    if not ctx.wait_for("play/arena_title", timeout=3):
        ctx.back_out(1)
        return 0
    done, skip = 0, set()
    lost = _lost(ctx)
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    own = (st.get("resources") or {}).get("power")
    ratio = ac.get("max_ratio", 1.0)
    for _ in range(ac.get("max_fights", 3) + ac.get("refresh_max", 3)):   # P7-10: lan Lam moi khong tinh luot danh
        if done >= ac.get("max_fights", 3):
            break
        img = ctx.shot()
        # anh mau = chu "Khieu chien mien phi" (cu: "(3/3)" -> sau tran dau thanh 2/3 khong khop, 2026-11-21);
        # +14 = tam cu (dong so luot) de giu toa do doc luc chien / cham nut
        rows = sorted(((x, y + 14, s_) for x, y, s_ in ctx.v.find_all(img, "play/arena_free", th=0.8)), key=lambda p: p[1])
        if not rows:
            log.info("Dau truong: het luot mien phi")
            break
        # Chu du an 2026-11-21: "luc chien mau do" = o luc chien khoanh do trong anh (chu trang) -> chon doi thu
        # luc chien <= luc chien minh x max_ratio, chua thua, MANH nhat trong so do (diem cao hon); mau do (neu co) uu tien
        cands = []
        for bx, by, _ in rows:
            if by // 30 in skip:
                continue
            pw = read_power(img, by)
            if _is_lost(lost, pw):
                log.info("Dau truong: bo doi thu luc chien %s (da thua truoc day)", pw)
                skip.add(by // 30)
                continue
            red = power_red(img, by)
            if not arena_eligible(pw, red, own, ratio, ac.get("only_red_power", False), ac.get("weaker_only", True)):
                continue
            cands.append((red, pw, bx, by))
        if not cands:
            log.info("Dau truong: khong co doi thu hop le (luc chien minh %s; yeu hon / chua thua)", own)
            if own and arena_refresh(ctx, ac):         # P7-10: khong co doi thu yeu hon -> "Lam moi"
                skip.clear()
                continue
            break
        red, pw, bx, by = max(cands)
        skip.add(by // 30)
        ctx.tap(bx, by + 10, wait=1.0)
        r = fight(ctx)
        log.info("Dau truong: danh doi thu luc chien %s -> %s", pw, r)
        if r == "lose":
            _remember_lost(ctx, pw)
            lost = _lost(ctx)
        if r in ("win", "lose"):
            done += 1
        if not ctx.wait_for("play/arena_title", timeout=4):
            break
    ctx.back_out(1)
    return done


def run(ctx):
    if not open_menu(ctx):
        log.info("Khong thay nut/bang Loi choi (chua mo khoa?) - bo qua")
        return 0
    n = 0
    try:
        n += mine(ctx)
        if not ctx.find("play/card_arena", th=0.85):
            open_menu(ctx)
        n += arena(ctx)
    finally:
        ctx.ensure_city()
    return n
