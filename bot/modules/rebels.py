"""Tham gia tap ket (rally) danh Phan quan Co giap cua lien minh khi con the luc va con doi hanh quan ranh.

Phan quan Co giap chi danh bang "Tap ket tan cong" (luc chien de xuat rat cao), nen bot chi THAM GIA
tap ket do dong minh mo: Lien minh -> tab "Su vu" -> "Tin van chien tranh".

AN TOAN: chi tham gia dong tap ket co dau hieu Phan quan Co giap (rebels/rally_mech.png). Thieu anh mau
do -> khong tham gia gi (tranh tham gia tap ket danh nguoi choi). Anh mau can cat khi co tap ket that:
  rebels/rally_mech.png  - icon/ten Phan quan Co giap tren dong tap ket
  rebels/btn_join.png    - nut tham gia tren dong do
Chay TRUOC buoc gui quan de doi ranh duoc dung cho tap ket truoc.
"""
import logging, re, time
import cv2, numpy as np
from bot import ocr
from bot.modules import alliance

log = logging.getLogger("aow")


def join(ctx):
    rc = ctx.cfg.get("rebels", {})
    if not rc.get("join_mech_rally", True):
        return 0
    if not (ctx.v.has("rebels/rally_mech") and ctx.v.has("rebels/btn_join")):
        log.info("Chua co anh mau dong tap ket Phan quan Co giap - bo qua (cat khi co tap ket that)")
        return 0
    ctx.ensure_city()
    res = ocr.topbar(ctx.shot())
    if res.get("stamina") is not None and res["stamina"] <= rc.get("min_stamina", 0):
        log.info("The luc %s <= muc giu lai %s - khong tham gia", res["stamina"], rc.get("min_stamina", 0))
        return 0
    if ctx.march_full():
        log.info("Khong con quan doan ranh - khong tham gia tap ket")
        return 0
    if not alliance.open_alliance(ctx) or not ctx.tap_tpl("ally/tab_affairs", wait=1.5):
        return 0
    joined = 0
    img = ctx.shot()
    if ctx.v.find(img, "rebels/war_empty"):
        log.info("Lien minh khong co tap ket nao")
    else:
        for mech in sorted(ctx.v.find_all(img, "rebels/rally_mech"), key=lambda p: p[1]):
            # nut tham gia cung dong (lech doc < 45px) voi dau hieu Co giap
            joins = [j for j in ctx.v.find_all(img, "rebels/btn_join") if abs(j[1] - mech[1]) < 45]
            if not joins:
                continue
            ctx.tap(joins[0][0], joins[0][1], wait=2.0)
            if ctx.wait_for("gather/btn_march", timeout=4):
                ctx.tap_tpl("gather/btn_recommended", wait=1.0)
                ctx.tap_tpl("gather/btn_march", wait=2.0)
                if not ctx.find("gather/btn_march"):
                    joined += 1
                    log.info("Da tham gia tap ket Phan quan Co giap")
                    break
            ctx.back_out()
            break
    ctx.ensure_city()
    return joined


# ---------- TU MO tap ket danh Phan quan (chu du an 2026-11-21, TK chinh #1) ----------
# Ban do the gioi: cham Phan quan Co giap -> popup "Phan quan Co giap Lv.N" (de xuat luc chien) -> "Tap ket tan cong"
# -> "Thoi gian tap ket" (3 phut, mac dinh) -> "Xac nhan" -> "Cai dat Quan doan": chon quan doan -> du doan
# "Thang toan dien" (chu xanh) -> "Xuat chinh". Tri nho: cap cao nhat da xuat chinh voi du doan thang -> lan sau
# thu cap +1; du doan KHONG thang -> nho cap do (khong thu lai trong fail_h gio), lui ve cap da thang.
LEGION_TABS = {"Odin": 125, "Thor": 215, "Loki": 305, "Hawk": 395, "Hulk": 485}   # y 424 (anh #1)


def pred_win(img):
    """Chu xanh "Thang toan dien" tren nut Xuat chinh."""
    hsv = cv2.cvtColor(img[830:900, 290:480], cv2.COLOR_BGR2HSV)    # anh mau cat lech ~16 px -> vung rong
    g = (hsv[..., 0] >= 45) & (hsv[..., 0] <= 75) & (hsv[..., 1] >= 150) & (hsv[..., 2] >= 150)
    return int(g.sum()) >= 150


def popup_level(img, title):
    """"Phan quan Co giap Lv.N" -> N (doc phan ben phai tieu de)."""
    m = re.search(r"[Ll][vV]\.?\s*(\d{1,2})", ocr.text(img, (title[0] + 100, title[1] - 15, 120, 32)) or "")
    return int(m.group(1)) if m else None


def _mem(ctx):
    m = getattr(ctx, "mem", None)
    rec = (m.fact(ctx.dev.idx, "rebels_levels") or {}) if m else {}
    return m, {"best": rec.get("best"), "fail": rec.get("fail", {}), "legion": rec.get("legion")}


def _save(ctx, rec):
    m = getattr(ctx, "mem", None)
    if m:
        m.set_fact(ctx.dev.idx, "rebels_levels", rec)


def target_ok(rec, lv, fail_h=12, now=None):
    """Co nen danh cap lv: <= best + 1 va khong vua du doan thua o cap nay (fail_h gio)."""
    now = now or time.time()
    best = rec.get("best") or 0
    f = rec.get("fail", {}).get(str(lv))
    if f and now - f < fail_h * 3600:
        return False
    return best == 0 or lv <= best + 1


def attack(ctx):
    """Tu mo 1 tap ket danh Phan quan Co giap tren ban do. -> 1 neu da Xuat chinh, 0 neu khong."""
    rc = ctx.cfg.get("rebels", {})
    if not rc.get("attack", True) or not ctx.v.has("rebels/label_mech"):
        return 0
    if ctx.march_full():
        log.info("Phan quan: het quan doan ranh - khong mo tap ket")
        return 0
    m, rec = _mem(ctx)
    ctx.ensure_world()
    time.sleep(1.0)
    img = ctx.shot()
    cands = sorted(ctx.v.find_all(img, "rebels/label_mech", th=0.75, roi=(0, 120, 540, 700)),
                   key=lambda p: abs(p[0] - 270) + abs(p[1] - 480))
    if not cands:
        log.info("Phan quan: khong thay Phan quan Co giap quanh can cu (can anh o tim kiem de tim xa hon)")
        ctx.save_debug("rebels_no_target")
        return 0
    for lx, ly, _ in cands[:4]:
        ctx.tap(lx, ly - 40, wait=1.8)                        # than co giap nam tren nhan ten
        img = ctx.shot()
        title = ctx.v.find(img, "rebels/popup_title", th=0.8)
        if not title:
            ctx.close_popups(1)
            continue
        lv = popup_level(img, title)
        rec_pw = re.sub(r"\D", "", ocr.text(img, (title[0] + 81, title[1] + 387, 95, 22), "0123456789,", scale=4) or "")
        if lv is None or not target_ok(rec, lv, rc.get("fail_h", 12)):
            log.info("Phan quan Lv.%s: bo (cap da thang cao nhat %s)", lv, rec.get("best"))
            ctx.tap_first(["common/btn_close", "common/btn_x"], wait=0.8)
            continue
        if not ctx.tap_tpl("rebels/btn_rally", wait=1.8):
            ctx.close_popups(1)
            continue
        if ctx.wait_for("rebels/rally_time_title", timeout=3):
            ctx.tap_tpl("rebels/btn_rally_confirm", wait=2.0)
        if not ctx.wait_for("rebels/legion_title", timeout=4):
            ctx.save_debug("rebels_no_legion")
            ctx.back_out(3)
            return 0
        legion = rec.get("legion") or rc.get("legion", "Odin")
        tab = ctx.find("rebels/tab_odin", th=0.75)                 # hang tab quan doan (y theo anh mau)
        ty = tab[1] if tab else 424
        ctx.tap(LEGION_TABS.get(legion, 125), ty, wait=1.5)
        img = ctx.shot()
        if not pred_win(img):
            rec["fail"][str(lv)] = time.time()
            _save(ctx, rec)
            log.info("Phan quan Lv.%d: quan doan %s KHONG du doan thang -> bo, nho cap nay", lv, legion)
            ctx.back_out(3)
            ctx.ensure_world()
            continue
        if not ctx.tap_tpl("rebels/btn_march_out", wait=2.0):
            ctx.save_debug("rebels_no_march")
            ctx.back_out(3)
            return 0
        ctx.march_sent()
        rec["best"] = max(rec.get("best") or 0, lv)
        rec["legion"] = legion
        _save(ctx, rec)
        log.info("Phan quan Lv.%d (de xuat %s): tap ket 3 phut, quan doan %s xuat chinh (du doan thang) -> lan sau thu Lv.%d",
                 lv, rec_pw or "?", legion, lv + 1)
        ctx.ensure_world()
        return 1
    return 0


def run(ctx):
    """Tu mo tap ket (TK du manh, chu du an 2026-11-21) roi tham gia tap ket cua lien minh neu con doi."""
    n = 0
    try:
        n += attack(ctx)
    except Exception as e:
        log.warning("Phan quan tu tap ket loi: %s", e)
        ctx.save_debug("rebels_attack_err")
    ctx.ensure_city()
    return n + (join(ctx) or 0)
