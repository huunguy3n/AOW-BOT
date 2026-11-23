"""Gui quan di mo cho den khi MOI doi hanh quan deu da di (Hanh quan x/y voi x == y).

Thu tu: alloy > metal > food (config). Moi loai tim tu cap CAO NHAT (8) ha dan xuong, cap nao thoa
(tai trong doi >= tru luong mo) thi xuat chinh. Cap (loai, cap) tim that bai bi bo qua trong luot nay.

Tri nho (chu du an 2026-11-21): cap cao nhat con thoa cua tung loai (gather_top:<loai>) va loai bi khoa theo cap
nha chinh (gather_locked:<loai>) duoc NHO lai, lan sau bat dau thang tu do. Chi do lai tu cap 8 khi doi "chu ky"
(gather_sig) = [cap nha chinh, so lan tuong tang cap] thay doi (nha chinh len cap / tuong trong quan doan len cap).
"""
import time, logging
from bot import gather_rules, ocr, screens, tplneed

log = logging.getLogger("aow")

OK, NOT_FOUND, FULL, NO_TROOPS, ERROR, NO_SEARCH = "ok", "notfound", "full", "notroops", "error", "nosearch"
UNREAD = "unread"  # khong doc duoc tru luong mo / tai trong -> khong ket luan duoc mo to hay nho (khong nho lai)
LOCKED = "locked"  # "Ban chua dat cap N, tam thoi khong the thu thap ..." -> bo ca loai mo
TOO_BIG = "toobig"  # mo con nhieu hon tai trong doi quan (doi khong cho het) -> bo qua cap nay, thu cap thap hon
# P3 (PM 2026-11-23)
OWN = "own"              # doi cua minh dang di toi chinh mo nay (cung loai/cap, cung thoi gian di) -> khong Xuat chinh
CONTESTED = "contested"  # hop thoai "Co Chi huy truong khac dang hanh quan den..." -> Huy (khong gay chien), doi mo khac
OCCUPIED = "occupied"    # mo da co nguoi (anh mau gather/mine_occupied) -> doi mo khac, khong bam nut tren mo
MSG_BAND = (0, 270, 540, 110)        # thong bao noi giua man (bot/game_msg.py)
DLG_BAND = (40, 400, 460, 110)       # than hop thoai xac nhan Xuat chinh (y 425-490)


def _ev(ctx, kind, rtype=None, level=None, note=None):
    """Ghi su kien thu thap vao memory.db (gather_ev) cho report_ro; khong co tri nho -> bo qua."""
    m = _mem(ctx)
    if m and hasattr(m, "log_gather"):
        m.log_gather(ctx.dev.idx, kind, rtype, level, note)


def _msg(img, band=MSG_BAND):
    """OCR thong bao/hop thoai -> loai (gather_rules.classify_msg) | None. Chi goi o nhanh that bai (~150-250 ms)."""
    try:
        return gather_rules.classify_msg(ocr.text(img, band, scale=2, psm=6))
    except Exception as e:
        log.debug("gather: OCR thong bao loi: %s", e)
        return None


def _has_msg(ctx, img, name, why):
    """Anh mau thong bao: co -> tim; thieu -> log 'thieu anh mau <ten>' (1 lan/gio) va tra False (dung OCR thay)."""
    return tplneed.has(ctx.v, name, why) and bool(ctx.v.find(img, name))


TAB_TH = 0.72  # chu tren thanh tab bi lech nua pixel khi cuon -> diem ~0.80; tab khac <= 0.65


def read_level(ctx):
    """Doc so trong o 'Cap:' bang anh mau gather/lv/1..9 (chon so khop nhat)."""
    g = ctx.cfg["gather"]
    x, y, w, h = g.get("level_box", [292, 798, 30, 20])
    box = ctx.shot()[y:y + h, x:x + w]
    best, score = None, 0.0
    for n in range(1, 10):
        if not ctx.v.has(f"gather/lv/{n}"):
            continue
        p = ctx.v.find(box, f"gather/lv/{n}", th=0.5)
        if p and p[2] > score:
            best, score = n, p[2]
    return best if score >= 0.9 else None


def set_level(ctx, level):
    """Bam +/- tung buoc (cham nhanh qua game bo qua) cho toi khi o 'Cap' = level.
    Tra ve False neu khong dat duoc (vd mo hop kim thap nhat la cap 3)."""
    minus = ctx.find("gather/btn_level_minus")
    plus = ctx.find("gather/btn_level_plus", fresh=False)
    if not (minus and plus):
        log.debug("Khong thay nut +/- cap, dung cap mac dinh cua game")
        return True
    for _ in range(12):
        cur = read_level(ctx)
        if cur is None:
            log.debug("Khong doc duoc cap - dung cap hien tai")
            return True
        if cur == level:
            return True
        btn = plus if cur < level else minus
        ctx.dev.tap(btn[0], btn[1])
        time.sleep(0.5)
        if read_level(ctx) == cur:  # bam ma khong doi -> da cham tran/san
            return False
    return False


def type_level(ctx, level):
    """P7-10 (chu du an 2026-11-24): GO SO truc tiep vao o "Cap" (giua nut - va +) thay vi bam +/- tung buoc.
    Doc lai khong ra dung cap -> bam +/- (set_level). -> True neu o 'Cap' = level."""
    minus = ctx.find("gather/btn_level_minus")
    plus = ctx.find("gather/btn_level_plus", fresh=False)
    if not (minus and plus) or not hasattr(ctx.dev, "type_digits"):
        return set_level(ctx, level)
    ctx.tap((minus[0] + plus[0]) // 2, (minus[1] + plus[1]) // 2, wait=0.8)
    ctx.dev.type_digits(int(level))
    time.sleep(0.8)
    if read_level(ctx) == level:
        log.info("O Cap: go truc tiep %d", level)
        return True
    log.info("O Cap: go %d khong an (doc %s) -> bam +/-", level, read_level(ctx))
    return set_level(ctx, level)


def select_tab(ctx, rtype, name=None):
    name = name or f"gather/tab_{rtype}"
    p = ctx.find(name, th=TAB_TH)
    for dx in (-330, 330):  # tab khong hien -> cuon thanh tab sang trai/phai
        if p:
            break
        ctx.dev.swipe(ctx.W // 2, 650, ctx.W // 2 + dx, 650, 500)
        time.sleep(0.8)
        p = ctx.find(name, th=TAB_TH)
    if not p:
        return False
    ctx.tap(p[0], p[1] - 30, wait=1.0)  # cham vao hinh mo phia tren chu
    return True


def close_map_menu(ctx, before=None):
    """Dong menu vong tron quanh o dat bang phim Back (KHONG cham man hinh: de cham trung icon su kien).
    before = anh ban do TRUOC khi cham o dat: man khong doi -> khong co menu nao mo -> KHONG bam Back
    (Back tren ban do = hop thoai 'Roi tro choi?'; truoc day moi lan cham trat deu bat hop thoai nay, 2026-11-21).
    O day khong dung ctx.press_back: menu mo thi nut 'Thanh pho' van hien -> is_home() van dung."""
    if before is not None and screens.same(before, ctx.shot()):
        return
    ctx._exp_begin("back", None, None, "gather.close_map_menu")
    ctx.dev.back()
    time.sleep(0.8)
    if ctx.tap_tpl("common/btn_cancel_exit", wait=0.6):
        log.warning("gather: Back dong menu o dat lai mo hop thoai thoat game -> da Huy")


def plausible(amount, g, known_cap=None, bounds=None):
    """Mo DAY (only_full) co tru luong tron chuc nghin (80000, 560000, 800000, 1320000 - do 2026-11-19).
    So le / qua nho = OCR doc sai (vd '606' cho mo cap 6 ~800000 -> bot da gui doi sai quy tac, #0 08:35)."""
    if not amount:
        return False
    if g.get("only_full", True):
        # mo alloy cap 7/8 = 62500 / 82500 (boi cua 2500, chu du an 2026-11-22) -> kiem boi 500 chu khong phai 1000
        if amount < g.get("min_mine_amount", 10000) or amount % 500:
            return False
        if known_cap and amount < known_cap * 0.9:
            return False
        if bounds:     # dung tich tang theo cap: lech khoi khoang cap thap/cap cao da biet = OCR rot chu so dau (1040000 -> 40000)
            lo, hi = bounds
            if (lo and amount < lo) or (hi and amount > hi):
                return False
    return True


def cap_bounds(ctx, rtype, level):
    """(cap lon nhat cua cac cap thap hon, cap nho nhat cua cac cap cao hon) da nho cho loai mo nay."""
    m = _mem(ctx)
    if not m:
        return None
    lo = hi = None
    for lv in range(1, 13):
        v = m.fact(ctx.dev.idx, f"mine_cap:{rtype}:{lv}")
        if not v or lv == level:
            continue
        v = int(v)
        if lv < level:
            lo = max(lo or 0, v)
        else:
            hi = min(hi or v, v)
    return (lo, hi)


def read_amount(ctx, g, tries=3, known_cap=None, bounds=None):
    """Tru luong mo duoi icon mo. Lan chay that 2026-11-19 doc ra None (anh chup luc bang mo chua hien xong)
    -> chup lai toi da 'tries' lan. (ROI rong hon da thu: doc sai -> chi dung ROI cau hinh.)"""
    rois = [tuple(g.get("node_amount_roi", [230, 521, 120, 17]))]
    img = ctx._img
    for i in range(tries):
        for roi in rois:
            v = ocr.label_number(img, roi)
            if plausible(v, g, known_cap, bounds):
                return v
            if v:
                log.info("  doc tru luong mo '%s' khong hop ly - doc lai", v)
        time.sleep(0.6)
        img = ctx.shot()
    return None


def try_dispatch(ctx, rtype, level, max_level):
    if not ctx.tap_tpl("gather/btn_search", wait=1.5):
        ctx.ensure_world()
        if not ctx.tap_tpl("gather/btn_search", wait=1.5):
            ctx.save_debug("no_search_btn")
            return NO_SEARCH
    if not ctx.wait_for("gather/btn_search_go", timeout=3):
        ctx.save_debug("no_search_panel")
        ctx.back_out()
        return ERROR
    if not select_tab(ctx, rtype):
        log.info("Khong thay tab %s", rtype)
        ctx.back_out()
        return NOT_FOUND
    if not set_level(ctx, level):
        log.debug("%s khong co cap %d", rtype, level)
        ctx.back_out()
        return NOT_FOUND
    if ctx.cfg["gather"].get("only_full", True):  # o "Chi tim kiem tai nguyen o diem tai nguyen day"
        ctx.tap_tpl("gather/chk_full_off", wait=0.6)
    ctx.tap_tpl("gather/btn_search_go", wait=3.0)
    img = ctx.shot()
    if (_has_msg(ctx, img, "gather/msg_not_found", "thong bao khong tim thay mo")
            or ctx.v.find(img, "gather/btn_search_go")):
        ctx.back_out()
        return NOT_FOUND
    # Ban do can giua mo vao 1 diem co dinh (~270,452 tren man 540x960). KHONG tinh theo mui ten xanh:
    # mui ten nhun len xuong nen lech ~25px -> cham trung o dat trong (menu Chuyen thanh/Chiem linh).
    cx, cy = ctx.cfg["gather"].get("node_xy", [ctx.W // 2, 452])
    occupied = False
    for dx, dy in ((0, 0), (0, 12), (0, -12)):
        before = ctx.shot()
        ctx.tap(cx + dx, cy + dy, wait=1.2)
        if ctx.find("gather/btn_gather"):
            break
        # mo da co nguoi (doi nguoi khac dang thu thap): KHONG bam nut nao tren bang mo (Tan cong / Trinh sat...)
        if tplneed.has(ctx.v, "gather/mine_occupied", "bang mo dang bi chiem") and                 ctx.find("gather/mine_occupied", fresh=False):
            occupied = True
        close_map_menu(ctx, before)  # cham trat (o dat trong / phien quan) -> dong menu (neu co) roi thu lech
        if occupied:
            log.info("  mo %s cap %d dang bi chiem - doi mo khac", rtype, level)
            return OCCUPIED
    else:
        ctx.save_debug(f"no_gather_btn_{rtype}{level}")
        return NOT_FOUND
    g = ctx.cfg["gather"]
    only_full = g.get("only_full", True)
    known = _mem(ctx).fact(ctx.dev.idx, f"mine_cap:{rtype}:{level}") if _mem(ctx) else None
    cap = gather_rules.table_cap(g.get("mine_caps"), rtype, level) or (int(known) if known else None)
    # P3: biet dung tich mo day -> chi doc 1 lan (OCR hong thi dung dung tich), khong biet -> doc lai toi 3 lan nhu cu
    read = read_amount(ctx, g, tries=1 if (cap and only_full) else 3, known_cap=cap,
                       bounds=cap_bounds(ctx, rtype, level))
    amount, src = gather_rules.choose_amount(read, cap, only_full)
    ctx.tap_tpl("gather/btn_gather", wait=1.5, fresh=False)
    if ctx.find("gather/msg_type_locked"):
        log.info("Chua du cap de thu thap %s - bo qua loai nay", rtype)
        if not ctx.tap_tpl("common/btn_confirm", wait=1.0, fresh=False):
            ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
        return LOCKED
    img = ctx.shot()
    if _has_msg(ctx, img, "gather/msg_march_full", "thong bao het doi hanh quan"):
        ctx.close_popups()
        return FULL
    if _has_msg(ctx, img, "gather/msg_no_troops", "thong bao het linh"):
        ctx.back_out()
        return NO_TROOPS
    if not ctx.wait_for("gather/btn_march", timeout=5):
        kind = _msg(ctx.shot())          # thieu anh mau msg_* -> doc thong bao bang OCR
        ctx.save_debug(f"no_march_panel_{kind or 'unknown'}")
        ctx.back_out()
        return {"march_full": FULL, "no_troops": NO_TROOPS, "locked": LOCKED, "occupied": OCCUPIED}.get(kind, ERROR)
    ctx.tap_tpl("gather/btn_recommended", wait=1.0)
    img = ctx.shot()
    load = ocr.amount(ocr.text(img, tuple(g.get("load_roi", [300, 843, 50, 18])), "0123456789"))
    travel = ocr.seconds(ocr.text(img, tuple(g.get("travel_roi", [350, 905, 72, 15])), "0123456789:"))
    log.info("  mo %s cap %d: con %s (doc %s, %s), tai trong doi %s, di mat %ss", rtype, level, amount, read,
             src or "-", load, travel)
    if src == "bang" and read != amount:
        log.info("  tru luong: dung dung tich mo day %s cho %s cap %d (OCR %s)", amount, rtype, level, read)
        _ev(ctx, "cap_table", rtype, level, read)
    ctx._gather_load = load
    note_load(ctx, load)
    m = _mem(ctx)
    if m:  # nho: dung tich mo day theo (loai, cap) + tai trong doi -> lan sau bo qua cap qua suc cho ma khong mo ban do
        if load:
            m.set_fact(ctx.dev.idx, "march_load", load)
        if amount and only_full:
            m.set_fact(ctx.dev.idx, f"mine_cap:{rtype}:{level}", max(amount, int(known or 0)))
    # Chu du an 2026-11-19: LUON dam bao tai trong doi >= tru luong mo (doi cho het mo).
    # Khong doc duoc 1 trong 2 so -> khong gui (khong dam bao duoc). Phong thu so tan tat kiem tra nay.
    if g.get("load_ge_mine", True):
        if not amount or not load:
            log.info("  khong doc duoc tru luong (%s) / tai trong (%s) - khong gui", amount, load)
            ctx.save_debug(f"gather_unread_{rtype}{level}")
            ctx.back_out()
            return UNREAD
        if load < amount:
            log.info("  tai trong %d < mo con %d - doi khong cho het, bo qua", load, amount)
            ctx.back_out()
            return TOO_BIG
    now = time.time()
    if travel and gather_rules.own_target(_dispatches(ctx), rtype, level, now, travel=travel):
        # P3: cung loai/cap + cung thoi gian di voi doi minh vua gui ma chua toi = CUNG MO -> bam Xuat chinh se hien hop
        # thoai "Chi huy truong khac..." (truoc P3 bot Huy o do = Huy oan, 7 lan 21-22/11) -> khong bam, doi cap khac
        log.info("  mo %s cap %d: doi minh dang toi dung mo nay (di %ss) - khong xuat chinh", rtype, level, travel)
        ctx.back_out()
        return OWN
    disp = {"type": rtype, "level": level, "amount": amount, "load": load, "travel": travel, "t": now}
    ctx.tap_tpl("gather/btn_march", wait=2.0)
    img = ctx.shot()
    contested = ctx.v.has("gather/dlg_contested") and ctx.v.find(img, "gather/dlg_contested")
    if contested or ctx.v.find(img, "common/btn_cancel_exit"):
        # Hop thoai xac nhan sau Xuat chinh: "Chu y! Co Chi huy truong khac dang hanh quan den diem tai nguyen nay, neu
        # ban tiep tuc hanh quan, co the se xay ra chien tranh! muon tiep tuc xuat chinh? [Huy] [Tiep tuc]".
        # KHONG BAO GIO bam "Tiep tuc" (co the danh nhau voi nguoi choi khac - CLAUDE.md). Huy + doi mo khac.
        if not contested and _msg(img, DLG_BAND) == "contested":
            contested = True
        own = gather_rules.own_target(_dispatches(ctx), rtype, level, now)
        if contested:
            kind = "own_dialog" if own else "contested"
            ctx.save_debug(f"march_{kind}_{rtype}{level}")
            log.warning("gather: hop thoai 'Chi huy truong khac dang hanh quan den mo nay' (%s cap %d, di %ss, %s) - Huy, "
                        "doi mo khac", rtype, level, travel, "doi cua minh" if own else "doi khac")
        else:
            kind = "dialog_unknown"
            ctx.save_debug(f"march_confirm_{rtype}{level}")
            log.warning("gather: hop thoai la sau Xuat chinh (%s cap %d) - Huy, khong tinh la da gui", rtype, level)
        _ev(ctx, kind, rtype, level, travel)
        ctx.tap_tpl("common/btn_cancel_exit", wait=1.0, fresh=False)
        ctx.back_out()
        return CONTESTED if contested else ERROR
    if ctx.v.find(img, "gather/btn_march"):  # van con bang -> khong co linh / het doi
        kind = _msg(img)
        log.info("Khong xuat chinh duoc (%s)", kind or "het linh?")
        ctx.back_out()
        return FULL if kind == "march_full" else NO_TROOPS
    ctx.last_dispatch = disp          # chi ghi khi THAT SU da gui (khong con bang / hop thoai)
    record_dispatch(ctx, disp)
    return OK


def _dispatches(ctx):
    """Cac lan gui gan day (state.json 'dispatches', giu qua cac lan ghe) + lan gui trong luot nay."""
    st = getattr(ctx, "store", None)
    out = list((st.inst(ctx.dev.idx).get("dispatches") or []) if st else [])
    last = getattr(ctx, "last_dispatch", None)
    if last and last not in out:
        out.append(last)
    return out


def record_dispatch(ctx, d):
    """Hien ngay doi vua gui len web (timeline: xuat phat -> toi mo -> thu thap xong -> ve thanh), khong cho
    'observe' cuoi luot (chu du an 2026-11-20: "gui quan di thu thap chua thay timeline"). observe se thay
    bang so doc OCR va giu lai thong tin mo (loai/cap/tru luong) qua 'dispatches'."""
    st = getattr(ctx, "store", None)
    if not st or not d:
        return
    t = d["t"]
    m = {"state": "marching", "remaining": d.get("travel"), "depart_at": t, "type": d["type"], "level": d["level"],
         "amount": d.get("amount"), "load": d.get("load"), "travel": d.get("travel"), "provisional": True}
    if d.get("travel"):
        m["arrive_at"] = t + d["travel"]
    cur = st.inst(ctx.dev.idx)
    disp = [x for x in (cur.get("dispatches") or []) if t - x.get("t", 0) < 86400][-9:] + [dict(d)]
    st.update(ctx.dev.idx, marches=(cur.get("marches") or []) + [m], dispatches=disp,
              march_used=(cur.get("march_used") or 0) + 1)


def _mem(ctx):
    return getattr(ctx, "mem", None)


def hq_level(ctx):
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    hq = st.get("hq_level")
    if hq is None and _mem(ctx):
        hq = _mem(ctx).fact(ctx.dev.idx, "hq_level")
    return hq


GATHER_TYPES = ("alloy", "metal", "food", "oil")


def rebels_reserve(ctx):
    """So quan doan DE DANH cho buoc phan quan (0|1): phan quan can 1 quan doan ranh nhung thu thap lap day ca 5/5 truoc nen buoc
    rebels luon 'het quan doan ranh' (#1 2026-11-22: 4 lan ghe lien tiep). Chi de khi phan quan con den han (nha chinh >=
    rebels.min_hq_level, chua du luot/ngay) va khong tat reserve_legion. Ghi ra facts de agent (planning) tinh dung doi ranh."""
    cfg = ctx.cfg
    rc = cfg.get("rebels", {})
    m = _mem(ctx)
    from bot.modules import warday
    if not m or not rc.get("reserve_legion", True) or not cfg.get("modules", {}).get("rebels", True):
        r = 0
    elif warday.gather_day(cfg):   # chu du an 2026-11-23: thu 2 = ngay thu thap -> moi quan doan di thu thap
        r = 0
    else:
        from bot import scheduler
        r = 1 if scheduler.rebels_ready(m, ctx.dev.idx, cfg)[0] else 0
    if m:
        m.set_fact(ctx.dev.idx, "rebels_reserve", r)
    return r


def sync_memory(ctx):
    """Chu ky tri nho: doi (cap nha chinh, so lan tuong tang cap) -> xoa cap/loai khoa da nho de do lai tu cap cao nhat."""
    m = _mem(ctx)
    if not m:
        return
    idx = ctx.dev.idx
    if not m.fact(idx, "gather_fix_v2"):
        # 1 lan: gather_top bi ghi tu tai trong cua quan doan nho (xem note_load) -> do lai tu cap cao nhat
        for t in GATHER_TYPES:
            m.set_fact(idx, f"gather_top:{t}", None)
        m.set_fact(idx, "gather_fix_v2", True)
        log.info("gather: xoa gather_top cu (ghi tu quan doan nho) - do lai mo tu cap cao nhat")
    sig = [hq_level(ctx), m.fact(idx, "hero_ups", 0)]
    old = m.fact(idx, "gather_sig")
    if old == sig:
        return
    log.info("gather: nha chinh / tuong doi %s -> %s - do lai mo tu cap cao nhat", old, sig)
    m.set_fact(idx, "gather_sig", sig)
    for t in GATHER_TYPES:
        m.set_fact(idx, f"gather_top:{t}", None)
        m.set_fact(idx, f"gather_locked:{t}", None)


HOLD_KEY = "gather_hold:{}:{}"       # fact: (loai, cap) tam bo toi moc nay (mo bi chiem / tranh chap / khong tim thay)


def hold(ctx, rtype, lv, result):
    """P3: tim kiem luon tra lai mo GAN NHAT -> mo bi chiem / tranh chap / khong co thi lan ghe sau cung vay. Nho
    (loai, cap) toi moc gather_rules.skip_until de khong lap vo ich qua cac lan ghe."""
    m = _mem(ctx)
    kind = {OCCUPIED: "occupied", CONTESTED: "contested", NOT_FOUND: "not_found"}.get(result)
    until = gather_rules.skip_until(kind, time.time(), ctx.cfg["gather"]) if kind else None
    if m and until:
        m.set_fact(ctx.dev.idx, HOLD_KEY.format(rtype, lv), [round(until), kind])


def skip_reason(ctx, rtype, lv, now=None):
    """Ly do bo (loai, cap) TRUOC khi mo bang tim kiem | None: dang tam bo (hold) hoac doi minh dang di toi mo do."""
    now = now or time.time()
    m = _mem(ctx)
    h = m.fact(ctx.dev.idx, HOLD_KEY.format(rtype, lv)) if m else None
    if h and h[0] > now:
        return f"tam bo ({h[1]}) toi {time.strftime('%H:%M', time.localtime(h[0]))}"
    d = gather_rules.own_target(_dispatches(ctx), rtype, lv, now)
    if d:
        _ev(ctx, "own_skip", rtype, lv)
        return f"doi minh dang di toi mo nay (toi luc {time.strftime('%H:%M:%S', time.localtime(d['t'] + d['travel']))})"
    return None


LOAD_WINDOW_S = 3 * 86400     # tai trong lon nhat cua cac quan doan duoc nho toi da 3 ngay


def note_load(ctx, load):
    """Nho tai trong LON NHAT trong cac quan doan da thay. Moi doi gui di dung 1 quan doan (Odin/Thor/Loki/Hawk/Hulk) co tai
    trong rieng: #1 2026-11-22 doc 44767 / 72383 / 75495 / 289534 / 517590 trong cung 1 gio. Cai da dung 'tai trong lan truoc'
    lam bo qua cap cao khi quan doan nho vua di, roi nho cap thap (gather_top=1) -> chi thu mo cap 1-2."""
    m = _mem(ctx)
    if not m or not load:
        return
    cur = m.fact(ctx.dev.idx, "march_load_max")
    now = time.time()
    if not cur or load >= cur[0] or now - cur[1] > LOAD_WINDOW_S:
        m.set_fact(ctx.dev.idx, "march_load_max", [int(load), now])


def max_load(ctx):
    m = _mem(ctx)
    if not m:
        return None
    cur = m.fact(ctx.dev.idx, "march_load_max")
    if cur and time.time() - cur[1] <= LOAD_WINDOW_S:
        return cur[0]
    return m.fact(ctx.dev.idx, "march_load")


def too_big_known(ctx, rtype, lv, min_lv):
    """Tri nho: mo (loai, cap) day co dung tich > tai trong cua BAT KY quan doan nao da thay -> khong quan doan nao cho het
    -> bo qua KHONG can mo ban do. Cap thap nhat luon thu (de doc lai tai trong khi linh tang). Quan doan nho hon thi mo
    ban do roi bo (TOO_BIG) tung lan, khong ghi nho."""
    m = _mem(ctx)
    if not m or lv <= min_lv:
        return False
    cap = m.fact(ctx.dev.idx, f"mine_cap:{rtype}:{lv}")
    load = max_load(ctx)
    return bool(cap and load and load < cap)


def remember_too_big(ctx, rtype, lv, load, min_lv):
    """Mo cap `lv` lon hon tai trong quan doan DANG CHON. Chi ghi nho cho ca loai (gather_top) khi quan doan do da la quan
    doan LON NHAT biet; quan doan nho hon chi bo qua cap nay trong lan nay."""
    m = _mem(ctx)
    if lv <= min_lv:
        # P7-1 (live #1 2026-11-24): cap thap nhat qua tai = quan doan dang ranh qua nho, KHONG phai thong tin ve loai mo
        # -> khong ghi gather_top (truoc day ghi 1 -> lan sau chi thu cap 1 du quan doan lon cho het cap cao hon)
        return
    if m and load and load >= (max_load(ctx) or 0):
        m.set_fact(ctx.dev.idx, f"gather_top:{rtype}", max(min_lv, lv - 1))


def run(ctx, limit=None):
    """limit: gui toi da N doi roi dung (agent gui tung doi, xac minh tung lan - B4); None = toi khi day."""
    g = ctx.cfg["gather"]
    max_lv, min_lv = g["max_level"], g["min_level"]
    # Chu du an 2026-11-19: tai trong doi phai >= mo; truoc nha chinh cap 9 (du 3 nha linh) doi khong cho het
    # noi mo cap 1 -> khong di thu thap, de thoi gian cho nhiem vu trong can cu.
    hq, min_hq = hq_level(ctx), g.get("min_hq_level", 9)
    if g.get("load_ge_mine", True) and hq is not None and hq < min_hq:
        log.info("Nha chinh cap %d < %d: tai trong doi chua du cho mo nao - bo qua thu thap", hq, min_hq)
        return 0
    ctx.ensure_world()
    sync_memory(ctx)
    mem, idx = _mem(ctx), ctx.dev.idx
    reserve = rebels_reserve(ctx)
    exhausted = set()
    sent = attempts = 0
    unknown_reads = 0
    while attempts < g.get("max_attempts", 40):
        mv = ctx.read_marches()
        if mv:
            used, total = mv
            if used >= total:
                log.info("Da day doi hanh quan %d/%d - xong", used, total)
                break
            if reserve and used >= total - reserve:
                log.info("Hanh quan %d/%d: de %d quan doan cho phan quan - dung gui thu thap", used, total, reserve)
                break
        else:
            unknown_reads += 1
            if sent >= g.get("fallback_march_slots", 1):
                log.warning("Khong doc duoc 'Hanh quan x/y'; da gui %d doi (fallback) - dung", sent)
                break
        result = None
        for rtype in g["priority"]:
            if mem and mem.fact(idx, f"gather_locked:{rtype}"):
                continue                      # tri nho: loai nay chua du cap nha chinh de thu thap
            stored = mem.fact(idx, f"gather_top:{rtype}") if mem else None
            fit = gather_rules.fit_level(g.get("mine_caps"), rtype, max_load(ctx), min_lv, max_lv)
            top = gather_rules.start_level(stored, fit, max_lv)
            for lv in range(top, min_lv - 1, -1):
                if (rtype, lv) in exhausted:
                    continue
                if g.get("load_ge_mine", True) and too_big_known(ctx, rtype, lv, min_lv):
                    log.info("  %s cap %d: tri nho - mo lon hon tai trong doi, bo qua", rtype, lv)
                    exhausted.add((rtype, lv))
                    continue
                why = skip_reason(ctx, rtype, lv)
                if why:
                    log.info("  %s cap %d: %s - bo qua", rtype, lv, why)
                    exhausted.add((rtype, lv))
                    continue
                attempts += 1
                result = try_dispatch(ctx, rtype, lv, max_lv)
                log.info("  %s cap %d -> %s", rtype, lv, result)
                _ev(ctx, {OK: "sent"}.get(result, result), rtype, lv)
                if result in (OCCUPIED, CONTESTED, NOT_FOUND):
                    hold(ctx, rtype, lv, result)
                if result == OK:
                    sent += 1
                    break
                if result in (FULL, NO_TROOPS, NO_SEARCH):
                    break
                if result == LOCKED:  # ca loai mo bi khoa theo cap -> bo moi cap cua loai nay (nho toi khi nha chinh len cap)
                    exhausted.update((rtype, x) for x in range(min_lv, max_lv + 1))
                    if mem:
                        mem.set_fact(idx, f"gather_locked:{rtype}", True)
                    break
                if result == TOO_BIG:   # chi nho khi quan doan nay la lon nhat biet (xem remember_too_big)
                    load_ = getattr(ctx, "_gather_load", None)
                    remember_too_big(ctx, rtype, lv, load_, min_lv)
                    # P7-1: cap thap hon ma bang van > tai trong -> bo luon (khong mo ban do tung cap); het cap -> loai khac
                    skip = gather_rules.too_big_levels(g.get("mine_caps"), rtype, load_, lv, min_lv)
                    if skip:
                        log.info("  %s: quan doan ranh (tai %s) khong cho het cap %s - bo qua", rtype, load_,
                                 ",".join(map(str, skip)))
                        exhausted.update((rtype, x) for x in skip)
                if result in (NOT_FOUND, ERROR, TOO_BIG, UNREAD, OWN, CONTESTED, OCCUPIED):
                    exhausted.add((rtype, lv))
            if result in (OK, FULL, NO_TROOPS, NO_SEARCH):
                break
        if result == OK:
            if limit is not None and sent >= limit:
                break
            time.sleep(1.0)
            continue
        if result == FULL:
            log.info("Game bao het doi hanh quan - xong")
        elif result == NO_SEARCH:
            log.error("Khong thay nut tim kiem (kinh lup) - kiem tra anh mau gather/btn_search.png")
        elif result == NO_TROOPS:
            log.warning("Het linh ranh - khong lap day duoc cac doi con lai")
        else:
            log.warning("Moi loai/moi cap deu khong tim duoc mo - dung")
        break
    log.info("Gui quan: %d doi moi", sent)
    ctx.ensure_city()
    return sent
