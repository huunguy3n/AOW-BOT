"""Loi choi (nut "Loi choi" thanh duoi) - chu du an chi 2026-11-21 tren TK chinh #1 (cf30):

  Mo khoang san: tab "Xe khai thac cua toi" -> cham ruong (bong bong ruong vang tren xe) -> nhan thuong.
  Dau truong  : 3 luot "Khieu chien mien phi" / ngay. CHI danh doi thu co LUC CHIEN MAU DO; nho doi thu da
                THUA (khong danh lai trong arena.lost_days ngay). Khong bam "Lam moi" / mua luot (co the ton kim cuong).
TK farm cap thap chua mo -> khong thay nut "Loi choi" / the -> bo qua.
"""
import json, logging, re, time
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
        if ctx.cfg.get("loot", {}).get("enabled", True):
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


def loot(ctx):
    """Dang o man Mo khoang san. -> so lan cuop da danh (0/1)."""
    lc = ctx.cfg.get("loot", {})
    if not lc.get("enabled", True):
        return 0
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
    rar = tuple(lc.get("rarity", ["SSR", "SR"]))
    cands = []                                          # doc tung xe cam/tim -> chon doi thu YEU NHAT dat nguong
    for col, x, y in loot_trucks(img)[:8]:
        ctx.tap(x, y, wait=1.2)
        p = ctx.shot()
        if not ctx.v.find(p, "play/btn_go_loot", th=0.8):
            ctx.tap(270, 150, wait=0.8)
            continue
        r = popup_rarity(p)
        pw = _digits(p, (155, 634, 120, 24))
        name = (ocr.text(p, (133, 585, 170, 26)) or "").strip()
        ok, why = loot_ok(lm, pw, name, legion, lc.get("margin", 0.97))
        if r not in rar:
            ok, why = False, f"do hiem {r}"
        log.info("Cuop boc: xe %s %s '%s' luc chien %s -> %s", col, r, name, pw, "CHON DUOC" if ok else why)
        if ok:
            cands.append((pw, x, y, name))
        ctx.tap(270, 150, wait=0.8)                     # dong popup (cham ra ngoai)
    if not cands:
        log.info("Cuop boc: khong co xe cam/tim nao trong nguong luc chien")
        return 0
    pw, x, y, name = min(cands)
    ctx.tap(x, y, wait=1.2)
    if not ctx.tap_tpl("play/btn_go_loot", wait=3.0, th=0.8):
        return 0
    if not ctx.wait_for("play/btn_loot", timeout=6):
        ctx.save_debug("loot_no_world_btn")
        ctx.ensure_city()
        return 0
    ctx.tap_tpl("play/btn_loot", wait=2.5, fresh=False)
    if not ctx.wait_for("play/btn_battle", timeout=5):
        ctx.save_debug("loot_no_legion")
        ctx.ensure_city()
        return 0
    lg = _digits(ctx._img, (68, 360, 120, 26))
    if lg:
        lm["legion"] = legion = lg
    ok, why = loot_ok(lm, pw, name, legion, lc.get("margin", 0.97))
    if not ok:
        log.info("Cuop boc: quan doan %s, doi thu %s -> bo (%s)", lg, pw, why)
        _loot_save(ctx, lm)
        ctx.back_out(3)
        ctx.ensure_city()
        return 0
    ctx.tap_tpl("play/btn_arena_recommend", wait=1.5, th=0.85, fresh=False)   # "Doi hinh de xuat" truoc khi danh
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


def arena_eligible(pw, red, own, ratio, only_red=False):
    """Doi thu co duoc danh khong (ham thuan). Luat chu du an 2026-11-21: luc chien MAU DO uu tien, khong can so;
    con lai chi khi luc chien <= luc chien minh x ratio. A-SAFE-3: khong doc duoc luc chien minh (own None/0)
    -> chi doi thu mau do (truoc day moi doi thu deu hop le va max() chon doi thu MANH nhat)."""
    if pw is None or (only_red and not red):
        return False
    if red:
        return True
    return bool(own) and pw <= own * ratio


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
    for _ in range(ac.get("max_fights", 3)):
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
            if not arena_eligible(pw, red, own, ratio, ac.get("only_red_power", False)):
                continue
            cands.append((red, pw, bx, by))
        if not cands:
            log.info("Dau truong: khong co doi thu hop le (luc chien minh %s; mau do / yeu hon / chua thua)", own)
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
