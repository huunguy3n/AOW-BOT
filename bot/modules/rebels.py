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
    if not join_hq_ok(getattr(ctx, "mem", None), ctx.dev.idx, rc):   # P7-10: farm < 15 khong bao gio tham gia
        log.info("Tap ket Co giap: nha chinh < %s -> khong tham gia (farm)", rc.get("min_hq_level", 15))
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


def target_why(rec, lv, fail_h=12, want=None, now=None):
    """Ly do bo muc tieu Lv.lv (ham thuan, de log dung)."""
    now = now or time.time()
    if lv is None:
        return "khong doc duoc cap tren popup"
    parts = []
    if want is not None and lv != want:
        parts.append(f"muon cap {want} nhung popup Lv.{lv} - o Cap khong doi")
    f = rec.get("fail", {}).get(str(lv))
    if f and now - f < fail_h * 3600:
        parts.append(f"Lv.{lv} vua du doan thua (cho {fail_h} gio)")
    best = rec.get("best") or 0
    if best and lv > best + 1:
        parts.append(f"cao hon cap da thang {best} + 1")
    return "; ".join(parts) or "khong dat dieu kien"


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
    setter = gather.type_level if ctx.cfg.get("rebels", {}).get("type_level", True) else gather.set_level
    if not setter(ctx, level):          # P7-10: go so truc tiep vao o "Cap"
        log.info("Phan quan: khong dat duoc cap %d trong o tim kiem - khong tim (tranh ra lai cap cu)", level)
        ctx.back_out()
        return None
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
        rally_ticks(ctx)
        ctx.tap_tpl("rebels/btn_rally_confirm", wait=2.0)
    if not ctx.wait_for("rebels/legion_title", timeout=4):
        ctx.save_debug("rebels_no_legion")
        ctx.back_out(3)
        return 0
    legion = rec.get("legion") or rc.get("legion", "Odin")
    tab = ctx.find("rebels/tab_odin", th=0.75)                 # hang tab quan doan (y theo anh mau)
    ty = tab[1] if tab else 424
    ctx.tap(LEGION_TABS.get(legion, 125), ty, wait=1.5)
    recommend(ctx)                                             # P9-7: "Doi hinh de xuat" TRUOC "Xuat chinh"
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
    ctx.ensure_world()
    if not rally_started(ctx):
        log.info("Phan quan Lv.%d: chua thay 'Dang tap ket' tren khung Hanh quan (co the da di / khung an)", lv)
    if record:
        rec["best"] = max(rec.get("best") or 0, lv)
        rec["legion"] = legion
        _save(ctx, rec)
    log.info("Phan quan Lv.%d (de xuat %s): tap ket 3 phut, quan doan %s xuat chinh (du doan thang)%s",
             lv, rec_pw or "?", legion, f" -> lan sau thu Lv.{lv + 1}" if record else " [tinh bao]")
    ctx.ensure_world()
    return 1


RECOMMEND_ROI = (0, 840, 300, 120)      # nut "Doi hinh de xuat" goc trai duoi man "Cai dat Quan doan" (anh rally_*)
MARCH_PANEL_ROI = (0, 120, 260, 160)    # khung "Hanh quan x/y" ben trai ban do (dong "Dang tap ket")


def recommend(ctx):
    """P9-7 (chu du an 2026-11-24, anh rally_doi_hinh_de_xuat_xuat_chinh): man "Cai dat Quan doan" -> bam "Doi hinh de
    xuat" (anh mau dung chung voi dau truong / cuop xe; khong co thi tim theo chu) roi moi "Xuat chinh"."""
    if ctx.tap_tpl("play/btn_arena_recommend", wait=1.5, th=0.85, roi=RECOMMEND_ROI):
        return True
    from bot import buttons
    bs = buttons.with_text(ctx.shot(), r"de\s*xu\w{0,2}t", RECOMMEND_ROI)
    if bs:
        ctx.tap(bs[0].x, bs[0].y, wait=1.5)
        return True
    log.info("Tap ket: khong thay 'Doi hinh de xuat' - giu doi hinh hien tai")
    return False


def rally_started_text(text):
    """Chu khung Hanh quan co 'Dang tap ket' (OCR mat dau) -> True. Ham thuan."""
    from bot import buttons
    t = buttons._norm(text)
    return bool(re.search(r"t\w{0,2}p\s*k\w{0,2}t", t))


def rally_started(ctx):
    """P9-7 (anh rally_dang_tap_ket): sau Xuat chinh, khung Hanh quan hien dong "Dang tap ket" = tap ket da xuat phat."""
    try:
        return rally_started_text(ocr.text(ctx.shot(), MARCH_PANEL_ROI, psm=6))
    except Exception:   # noqa: BLE001 - chi de log
        return False


RALLY_TICKS = (("rebels/chk_3min_off", "o tick 3Phut chua chon"),
               ("rebels/chk_full_start_off", "o tick Du thanh vien se xuat phat chua chon"))


def rally_ticks(ctx):
    """P7-10: bang "Thoi gian tap ket": tick "3Phut" + "Du thanh vien se xuat phat" (anh mau o tick CHUA chon) truoc
    "Xac nhan". Da chon (khong khop mau chua chon) -> khong cham (cham lai se bo chon). Thieu mau -> bo qua em.
    -> so o vua tick."""
    n = 0
    for name, why in RALLY_TICKS:
        if not tplneed.has(ctx.v, name, why):
            continue
        p = ctx.find(name, th=0.85)
        if p:
            ctx.tap(p[0], p[1], wait=0.8)
            n += 1
            if ctx.find(name, th=0.85):
                log.info("Tap ket: tick %s khong an", name.split("/")[-1])
    return n


def join_hq_ok(mem, idx, rc):
    """P7-10: nha chinh < rebels.min_hq_level (15) -> KHONG BAO GIO tham gia tap ket Phan quan Co giap (ke ca khi bat
    join_mech_rally). Khong biet cap nha chinh -> khong."""
    hq = mem.fact(idx, "hq_level") if mem is not None else None
    return isinstance(hq, (int, float)) and hq >= int(rc.get("min_hq_level", 15))


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


def snap_levels(levels, step):
    """Ham thuan P12-4: cap muon tim -> cap o 'Cap' nhan duoc (boi so cua step, giu thu tu, bo trung)."""
    from bot.modules.gather import snap_level
    out = []
    for lv in levels:
        s_ = snap_level(lv, step)
        if s_ not in out:
            out.append(s_)
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
    step = rec.get("step") or 1
    if step > 1 and not getattr(ctx, "level_step", None):
        ctx.level_step = step
    tried = set()
    for lv in levels:
        snapped = snap_levels([lv], getattr(ctx, "level_step", 1) or 1)[0]
        if snapped in tried:       # P12-4: buoc 5 -> cap 9/8/7 deu la 5 -> khong tim lai cung cap
            log.info("Phan quan: cap %d = cap %d (buoc %s) da thu - bo", lv, snapped, ctx.level_step)
            continue
        tried.add(snapped)
        p = search_target(ctx, lv)
        if (getattr(ctx, "level_step", 1) or 1) > 1 and rec.get("step") != ctx.level_step:
            rec["step"] = ctx.level_step               # nho buoc o Cap Co giap cho lan sau
            _save(ctx, rec)
        tried.add(snap_levels([lv], getattr(ctx, "level_step", 1) or 1)[0])
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
        # P10-3: ly do THAT (live3 log "cap da thang cao nhat None" gay hieu nham: thuc ra o Cap khong doi -> lai ra
        # Lv.10 vua du doan thua). Ha cap KHONG doi hoi lich su thang (target_ok: best None -> moi cap duoc).
        log.info("Phan quan Lv.%s: bo (%s)", lv, target_why(rec, lv, rc.get("fail_h", 12), want))
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
