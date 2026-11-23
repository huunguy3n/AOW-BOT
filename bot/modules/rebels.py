"""Phan quan Co giap: TU MO tap ket tren ban do (attack, chu du an 2026-11-21) + tham gia tap ket lien minh (join).

attack: nhan "Co giap" quanh can cu, khong co thi o tim kiem theo cap; P5-2 (PM 2026-11-23): 1 luot thu toi
rebels.search_tries cap (cap ke tiep roi ha dan) - truoc day du doan thua 1 cap la ca luot tra 0.
join: MAC DINH TAT (rebels.join_mech_rally: false, chu du an chua quyet). AN TOAN: chi tham gia dong tap ket co
dau hieu Phan quan Co giap (rebels/rally_mech.png) - tranh tham gia tap ket danh nguoi choi. Thieu anh mau -> bo
qua ngay + log 'thieu anh mau' (bot/tplneed.py). Anh mau can cat khi co tap ket that (Lien minh > Su vu):
  rebels/rally_mech.png  - icon/ten Phan quan Co giap tren dong tap ket
  rebels/btn_join.png    - nut tham gia tren dong do
"""
import logging, re, time
import cv2
from bot import ocr, tplneed
from bot.modules import alliance

log = logging.getLogger("aow")


JOIN_TH = 0.9                   # btn_join khop 0,75 voi nut '+' benh vien / bang tim kiem (#1 2026-11-23)
JOIN_ROI = (200, 220, 300, 680)  # o '+' tren the tap ket (Lien minh > Su vu, y~327); bo dai tren cung (y < 220)


def join(ctx):
    """Tham gia tap ket Phan quan Co giap cua lien minh. MAC DINH TAT (rebels.join_mech_rally: false - chu du an chua
    quyet, PM 2026-11-23). Thieu anh mau rally_mech / btn_join -> bo qua ngay, khong mo bang lien minh."""
    rc = ctx.cfg.get("rebels", {})
    if not rc.get("join_mech_rally", False):
        return 0
    if not (tplneed.has(ctx.v, "rebels/rally_mech", "dong tap ket Phan quan Co giap - Lien minh > Su vu")
            and tplneed.has(ctx.v, "rebels/btn_join", "nut tham gia tren dong tap ket")):
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
            joins = [j for j in ctx.v.find_all(img, "rebels/btn_join", th=JOIN_TH, roi=JOIN_ROI)
                     if abs(j[1] - mech[1]) < 45]
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


def intel_rally_ok(mem, idx, rc):
    """P5-2: ghim tinh bao Phan quan Co giap (tu mo tap ket) tren may nha chinh thap. rebels.intel_rally_min_hq = 0 ->
    moi cap (hanh vi tu 2026-11-22, chu du an chua quyet lai); > 0 -> chi khi biet nha chinh >= gia tri do."""
    need = int(rc.get("intel_rally_min_hq", 0) or 0)
    if need <= 0:
        return True
    hq = mem.fact(idx, "hq_level") if mem is not None else None
    return isinstance(hq, (int, float)) and hq >= need


def pick_level(rec, start=10, fail_h=12, now=None):
    """Q6: cap de tim qua o tim kiem: da thang cap N -> N+1; chua co -> start; cap do vua du doan thua -> lui dan."""
    best = rec.get("best") or 0
    lv = best + 1 if best else start
    while lv > 1 and not target_ok(rec, lv, fail_h, now):
        lv -= 1
    return lv


def search_target(ctx, level):
    """Q6: O tim kiem ban do (kinh lup, dung chung voi thu thap) -> tab Co giap -> cap -> Di toi. Camera dat muc tieu
    giua man -> tra diem cham (truoc day chi tim quanh can cu: 5/7 lan 'khong thay', 2026-11-21).
    -> (x, y) | None (cap nay khong co muc tieu) | False (o tim kiem hong: khong nut / khong tab Co giap - dung thu cap khac)."""
    from bot.modules import gather
    if not ctx.tap_tpl("gather/btn_search", wait=1.5):
        return False
    if not ctx.wait_for("gather/btn_search_go", timeout=3):
        ctx.back_out()
        return False
    if not gather.select_tab(ctx, "mech", name="rebels/tab_mech"):
        log.info("Phan quan: o tim kiem khong co tab Co giap")
        ctx.back_out()
        return False
    if not gather.set_level(ctx, level):
        log.info("Phan quan: khong dat duoc cap %d trong o tim kiem", level)
    ctx.tap_tpl("gather/btn_search_go", wait=3.0)
    if ctx.find("gather/msg_not_found") or ctx.find("gather/btn_search_go"):
        log.info("Phan quan: khong tim thay Co giap cap %d", level)
        ctx.back_out()
        return None
    cx, cy = ctx.cfg["gather"].get("node_xy", [ctx.W // 2, 452])
    return cx, cy


def launch_rally(ctx, rc, rec, lv, rec_pw="", record=True):
    """Dang o popup "Phan quan Co giap Lv.N": Tap ket tan cong -> thoi gian -> quan doan -> (du doan thang) -> Xuat chinh.
    -> 1 da xuat chinh | 0 bo han (loi man hinh) | -1 thu muc tieu khac (khong du doan thang / khong co nut).
    record=False (tinh bao): khong ghi cap 'best' / quan doan, de khong lam lech tien do cap cua buoc phan quan."""
    if not ctx.tap_tpl("rebels/btn_rally", wait=1.8):
        ctx.close_popups(1)
        return -1
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
        rec.setdefault("fail", {})[str(lv)] = time.time()
        _save(ctx, rec)
        log.info("Phan quan Lv.%d: quan doan %s KHONG du doan thang -> bo, nho cap nay", lv, legion)
        ctx.back_out(3)
        ctx.ensure_world()
        return -1
    if not ctx.tap_tpl("rebels/btn_march_out", wait=2.0):
        ctx.save_debug("rebels_no_march")
        ctx.back_out(3)
        return 0
    ctx.march_sent()
    if record:
        rec["best"] = max(rec.get("best") or 0, lv)
        rec["legion"] = legion
        _save(ctx, rec)
    log.info("Phan quan Lv.%d (de xuat %s): tap ket 3 phut, quan doan %s xuat chinh (du doan thang)%s",
             lv, rec_pw or "?", legion, f" -> lan sau thu Lv.{lv + 1}" if record else " [tinh bao]")
    ctx.ensure_world()
    return 1


def search_levels(rec, start=10, fail_h=12, tries=3, now=None):
    """P5-2: cac cap thu lan luot trong 1 luot: cap pick_level roi ha dan (bo cap vua du doan thua). Truoc day moi
    luot chi thu 1 cap -> du doan thua Lv.10 la ca luot tra 0 (4/4 lan 21-22/11). -> [cap...] (<= tries phan tu)."""
    lv = pick_level(rec, start, fail_h, now)
    out = []
    while lv >= 1 and len(out) < max(1, tries):
        if target_ok(rec, lv, fail_h, now):
            out.append(lv)
        lv -= 1
    return out


def attack(ctx):
    """Tu mo 1 tap ket danh Phan quan Co giap tren ban do. -> 1 neu da Xuat chinh, 0 neu khong."""
    rc = ctx.cfg.get("rebels", {})
    if not rc.get("attack", True) or not tplneed.has(ctx.v, "rebels/label_mech", "nhan ten Co giap tren ban do"):
        return 0
    if ctx.march_full():
        log.info("Phan quan: het quan doan ranh - khong mo tap ket")
        return 0
    m, rec = _mem(ctx)
    ctx.ensure_world()
    time.sleep(1.0)
    img = ctx.shot()
    near = sorted(ctx.v.find_all(img, "rebels/label_mech", th=0.75, roi=(0, 120, 540, 700)),
                  key=lambda p: abs(p[0] - 270) + abs(p[1] - 480))
    for lx, ly, _ in near[:4]:
        r = try_target(ctx, rc, rec, (lx, ly - 40))           # than co giap nam tren nhan ten
        if r >= 0:
            return r
    levels = search_levels(rec, rc.get("start_level", 10), rc.get("fail_h", 12), rc.get("search_tries", 3))
    for lv in levels:
        p = search_target(ctx, lv)
        if p is False:                                  # o tim kiem hong -> cap khac cung vay
            break
        if not p:
            log.info("Phan quan: tim kiem cap %d khong ra muc tieu", lv)
            continue
        log.info("Phan quan: tim kiem cap %d -> toi muc tieu", lv)
        for tap in (p, (p[0], p[1] + 12), (p[0], p[1] - 12)):
            r = try_target(ctx, rc, rec, tap, want=lv)
            if r >= 0:
                return r
            if r == -1:          # popup mo duoc nhung bo (du doan thua / cap khac) -> sang cap thap hon
                break
    if not near and not levels:
        log.info("Phan quan: khong con cap nao de thu (cap vua du doan thua dang cho %s gio)", rc.get("fail_h", 12))
    return 0


def try_target(ctx, rc, rec, tap, want=None):
    """Cham 1 muc tieu -> 1 xuat chinh | 0 dung han (loi man hinh) | -1 popup mo nhung bo | -2 khong mo duoc popup."""
    ctx.tap(tap[0], tap[1], wait=1.8)
    img = ctx.shot()
    title = ctx.v.find(img, "rebels/popup_title", th=0.8)
    if not title:
        ctx.close_popups(1)
        return -2
    lv = popup_level(img, title)
    rec_pw = re.sub(r"\D", "", ocr.text(img, (title[0] + 81, title[1] + 387, 95, 22), "0123456789,", scale=4) or "")
    if lv is None or not target_ok(rec, lv, rc.get("fail_h", 12)):
        log.info("Phan quan Lv.%s: bo (cap da thang cao nhat %s)", lv, rec.get("best"))
        ctx.tap_first(["common/btn_close", "common/btn_x"], wait=0.8)
        return -1
    r = launch_rally(ctx, rc, rec, lv, rec_pw)
    return r if r in (0, 1) else -1


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
