"""Nghien cuu (So Cong Nghe). Chu du an 2026-11-21 (#1, anh So Cong Nghe Cap 30):
  - CHI CO 1 hang nghien cuu (icon "1/1" thu hai cot trai thanh pho). Dang nghien cuu (thanh tien do + nut
    "Chi tiet" o day man) -> KHONG bat dau duoc gi -> chi ghi thoi gian con lai (lich ghe lai luc xong, web hien).
  - Chi nghien cuu duoc node co huy hieu x/y voi x < y (3/3 = da xong).
Mo bang: cham icon hang cho nghien cuu (research/icon_queue) -> "So Cong Nghe" (research/title).
KHONG BAO GIO bam nut tang toc / nghien cuu ngay bang kim cuong.
"""
import re, time, logging
import cv2
from bot import ocr
from bot.vnames import fix_name

log = logging.getLogger("aow")
STRICT = re.compile(r"(?:(\d{1,2})d:)?(\d{2}):(\d{2}):(\d{2})")
BUSY_NAME, BUSY_TIME = (30, 818, 300, 26), (100, 888, 200, 24)


def parse_left(t):
    m = STRICT.search(t or "")
    if not m:
        return None
    d, h, mi, s = (int(v) if v else 0 for v in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s if h < 24 and mi < 60 and s < 60 else None


def busy(v, img):
    """Dang nghien cuu? -> (ten, giay_con_lai) | None. Dau hieu: nut "Chi tiet" goc phai duoi."""
    if not v.find(img, "research/btn_detail", th=0.8, roi=(360, 840, 180, 110)):
        return None
    return (ocr.text(img, BUSY_NAME) or "").strip(), parse_left(ocr.text(img, BUSY_TIME, "0123456789d:", scale=4))


def badges(img, roi_y=(90, 790)):
    """Huy hieu "x/y" (vong tron toi goc phai duoi moi node) -> [(x, y, a, b)]."""
    g = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 3)
    c = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT, 1, 30, param1=100, param2=18, minRadius=13, maxRadius=19)
    out = []
    for x, y, r in (c[0] if c is not None else []):
        x, y, r = int(x), int(y), int(r)
        if not roi_y[0] <= y <= roi_y[1]:
            continue
        m = re.search(r"(\d+)\s*/\s*(\d+)", ocr.text(img, (x - r, y - r // 2 - 2, 2 * r, r + 4), "0123456789/", scale=5) or "")
        if m:
            out.append((x, y, int(m.group(1)), int(m.group(2))))
    return out


def glow_score(img, x, y, r=62):
    """Do 'sang xanh' (hao quang node duoc de xuat sau khi bam "Den"): so diem xanh-trang rat sang trong vong ban kinh r
    quanh tam node (x, y). Node thuong khong co vet sang nay (anh chu du an 2026-11-22: node Khuyen khich co hao quang)."""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = max(0, x - r), max(0, y - r), min(w, x + r), min(h, y + r)
    hsv = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    m = (hsv[..., 0] >= 90) & (hsv[..., 0] <= 118) & (hsv[..., 1] >= 40) & (hsv[..., 2] >= 235)
    return int(m.sum())


def pick_recommended(img, cands, min_score=25):
    """cands = [(x, y, a, b)] huy hieu x/y con nghien cuu duoc -> node co hao quang manh nhat | None."""
    best = None
    for x, y, a, b in cands:
        sc = glow_score(img, x - 55, y - 45)
        if sc >= min_score and (best is None or sc > best[0]):
            best = (sc, (x, y, a, b))
    return best[1] if best else None


def recommended(ctx):
    """Buoc cua chu du an 2026-11-22: man So Cong Nghe -> o duoi "Khuyen khich" co nut "Den" -> bam -> cay cuon toi node duoc de
    xuat (co hao quang) -> bam node -> bang chi tiet -> "Nghien cuu" (node(ctx)). -> 'started'|ket qua node|None (khong lam duoc,
    de vong cu lam tiep)."""
    from bot import buttons
    img = ctx.shot()
    go = [b for b in buttons.with_text(img, GO_TXT, roi=(240, 860, 300, 100), kinds=(buttons.GO,))]
    if not go:
        return None
    b = go[-1]
    ctx.tap(b.x, b.y, wait=1.8, tpl="btn:den_khuyen_khich")
    img = ctx.settle()
    cands = [p for p in badges(img) if p[2] < p[3]]
    pick = pick_recommended(img, cands)
    if not pick:
        log.info("Nghien cuu: bam 'Den' nhung khong thay node co hao quang - lam theo thu tu")
        return None
    x, y, a, bb = pick
    log.info("Nghien cuu: node de xuat %d/%d @%d,%d", a, bb, x, y)
    ctx.tap(x - 55, y - 45, wait=1.5)
    res = node(ctx)
    log.info("Nghien cuu node de xuat -> %s", res)
    ctx.back_out(1)
    return res


def open_research(ctx):
    ctx.ensure_city()
    if ctx.tap_tpl("research/icon_queue", wait=2.0, th=0.8, roi=(0, 90, 120, 320)) and ctx.wait_for("research/title", timeout=4):
        return True
    if ctx.v.has("research/btn_research_building") and ctx.tap_tpl("research/btn_research_building", wait=1.2):
        ctx.tap_tpl("research/btn_research_enter", wait=1.5)
        if ctx.wait_for("research/title", timeout=4):
            return True
    log.info("Khong mo duoc So Cong Nghe")
    ctx.save_debug("research_open")
    return False


def record(ctx, name, left):
    """Ghi nghien cuu dang chay: timer 'research' (lich) + state (web)."""
    until = time.time() + left if left else None
    name = fix_name(name) if name else name      # OCR chi co goi 'eng' -> sua dau tieng Viet
    m = getattr(ctx, "mem", None)
    if m:
        m.clear_timers(ctx.dev.idx, "research")
        if until:
            m.set_timer(ctx.dev.idx, "research", until, "ocr", 0.9)
    if getattr(ctx, "store", None):
        ctx.store.update(ctx.dev.idx, research={"name": name, "until": until, "at": time.time(), "idle": not name})


RESEARCH_TXT = r"\bngh\w{0,3}n c\w{0,2}u\b"        # "Nghien cuu" (OCR mat dau); "... ngay" bi buttons chan
GO_TXT = r"\bd\w{0,2}n\b"                         # "Den"


TITLE_ROI = (60, 92, 420, 56)          # ten cong trinh tren man Tang cap (phia tren "Cap hien tai N")
LAB_WAIT_S = 20 * 60                   # nang cap Vien nghien cuu khong doc duoc gio xong -> ghe lai sau N giay


def classify_building(text):
    """Ten cong trinh tren man Tang cap -> 'hq' | 'lab' | None (ham thuan; OCR 'eng' mat dau nen so khop gan dung)."""
    from aowbot.domain.blockers import normalize
    s = normalize(text or "")
    if "kien truc" in s or "kien tr" in s or "xuong kien" in s:
        return "hq"
    if "nghien" in s or "vien ngh" in s or "nghien cuu" in s:
        return "lab"
    return None


def building_title(img):
    return " ".join(ocr.text(img, TITLE_ROI, bright=b, psm=6) or "" for b in (170, None))


def lab_wait_until(ctx):
    """Dang cho nang cap Vien nghien cuu xong (epoch) hoac None."""
    m = getattr(ctx, "mem", None)
    t = m.fact(ctx.dev.idx, "research_wait_lab_until") if m else None
    try:
        t = float(t) if t is not None else None
    except (TypeError, ValueError):
        t = None
    return t if t and t > time.time() else None


def upgrade_lab(ctx):
    """Dang o man Tang cap Vien nghien cuu (node can cap N): nang cap no (build.upgrade_here, thieu dieu kien thi
    'Nhay' sang cong trinh can nang truoc), xong moi nghien cuu tiep. Chu du an 2026-11-21.
    Dat moc 'cho' de khong ghe lai lien tuc: nang cap bat dau/het tho/thieu tai nguyen -> LAB_WAIT_S."""
    from bot import build
    res = build.upgrade_here(ctx)
    log.info("Nghien cuu: nang cap Vien nghien cuu -> %s", res)
    m = getattr(ctx, "mem", None)
    if m and res in ("started", "busy", "blocked", "no_builder"):
        wait = max(LAB_WAIT_S, getattr(ctx, "last_busy", 0) or 0) if res in ("started", "busy") else LAB_WAIT_S
        m.set_fact(ctx.dev.idx, "research_wait_lab_until", time.time() + wait)
    return "lab_upgrade" if res == "started" else f"lab_{res}"


def wait_hq(ctx):
    """Q3: nghien cuu dang cho nha chinh len cap (node yeu cau cap Xuong kien truc) -> True neu van phai cho."""
    m = getattr(ctx, "mem", None)
    if not m:
        return False
    need, hq = m.fact(ctx.dev.idx, "research_wait_hq"), m.fact(ctx.dev.idx, "hq_level")
    if need is None:
        return False
    if hq is not None and hq > need:
        m.set_fact(ctx.dev.idx, "research_wait_hq", None)
        log.info("Nha chinh da len cap %d > %d - nghien cuu tiep", hq, need)
        return False
    return True


# ---- P2 muc 3 (PM 2026-11-23): anh mau bang node (chu du an chup tren #1 sau). Thieu -> dung MAU + CHU (khong bam mo),
# log "thieu anh mau <ten>" (bot/tplneed.py).
TPL_BTN = "research/btn_research"      # nut PHAI "Nghien cuu" o day bang chi tiet node (KHONG phai "Nghien cuu ngay")
TPL_PANEL = "research/node_panel"      # tieu de / khung bang chi tiet node (xac nhan da mo dung bang)
TPL_NORES = "research/msg_no_res"      # hop thoai / thong bao thieu tai nguyen sau khi bam "Nghien cuu"
BTN_ROI = (200, 320, 340, 640)         # vung tim nut "Nghien cuu" khi khong thay khung bang: nua phai, 2/3 duoi man
PANEL_TH = 0.9                         # node_panel khop 0,807 voi hop thoai 'Doi da du' (#1 2026-11-23) -> nguong 0,9
BTN_TH = 0.85                          # btn_research: 1,0 tren nut that, 0,41 voi nut "Nghien cuu ngay" (kim cuong)


def btn_roi(panel):
    """Vung tim nut "Nghien cuu" (ham thuan). Bang chi tiet node tren #1 nam GIUA man (nut o y~491, khung X/i o
    (489, 282)) chu khong sat day -> tim tu tren khung bang toi day man, nua phai. Khong thay khung -> BTN_ROI."""
    if not panel:
        return BTN_ROI
    top = max(0, int(panel[1]) - 60)
    return (200, top, 340, 960 - top)
NORES_FACT = "research_nores"          # {"until": epoch, "n": so lan lien tiep}: het tai nguyen -> khong mo lai toi moc
SKIP_FACT = "research_skip"            # {khoa node: epoch}: node bam vao khong lam duoc gi -> bo qua toi moc


def start_buttons(ctx, img):
    """Nut "Nghien cuu" tren bang node -> [(x, y, nhan)] (duoi cung truoc). Anh mau neu co, khong thi MAU + CHU
    (buttons.with_text tu chan '... ngay' / kim cuong)."""
    from bot import buttons, tplneed
    if tplneed.has(ctx.v, TPL_BTN, "dung mau + chu thay the"):
        panel = ctx.v.find(img, TPL_PANEL, th=PANEL_TH) if ctx.v.has(TPL_PANEL) else None
        p = ctx.v.find(img, TPL_BTN, th=BTN_TH, roi=btn_roi(panel))
        return [(p[0], p[1], "tpl")] if p else []
    return [(b.x, b.y, b.text) for b in reversed(buttons.with_text(img, RESEARCH_TXT))]


def no_res_shown(ctx, img):
    """Sau khi bam "Nghien cuu": co hop thoai thieu tai nguyen? (anh mau neu co; common/msg_insufficient du phong)."""
    from bot import tplneed
    for name in (TPL_NORES, "common/msg_insufficient"):
        why = "khong nhan ra thieu tai nguyen bang anh - kiem bang trang thai dang nghien cuu"
        if tplneed.has(ctx.v, name, why) and ctx.v.find(img, name, th=0.8):
            return True
    return False


def verify_start(ctx):
    """Sau khi bam "Nghien cuu" -> 'started' | 'no_res'. Khong tin 1 lan bam: kiem lai bang (1) hop thoai thieu tai
    nguyen, (2) nut "Nghien cuu" con nguyen cho (game chua nhan), (3) cay cong nghe hien thanh tien do + "Chi tiet"."""
    time.sleep(0.8)
    img = ctx.shot()
    if no_res_shown(ctx, img):
        log.info("Nghien cuu: thieu tai nguyen (hop thoai)")
        ctx.close_popups(2)          # chi nut X/Dong - KHONG bam 'Dung vat pham' / mua bang kim cuong
        return "no_res"
    if start_buttons(ctx, img):
        log.info("Nghien cuu: bam 'Nghien cuu' nhung nut van con -> coi nhu thieu tai nguyen/dieu kien")
        ctx.close_popups(2)
        return "no_res"
    for _ in range(3):               # bang node tu dong hoac hien popup che -> dong tung lop, nhin day cay cong nghe
        img = ctx.shot()
        b = busy(ctx.v, img)
        if b:
            record(ctx, *b)
            return "started"
        if ctx.v.find(img, "research/title", th=0.8):
            break
        ctx.close_popups(1)
    log.info("Nghien cuu: khong thay thanh tien do sau khi bam -> coi nhu chua bat dau (thieu tai nguyen?)")
    return "no_res"


def node(ctx, depth=0, max_depth=4):
    """Q3 - bang chi tiet 1 node (chu du an 2026-11-21): co nut "Nghien cuu" -> bam (KHONG BAO GIO "Nghien cuu ngay",
    kim cuong); thieu nhanh phu -> nut "Den" o dong dieu kien -> sang node do, lam tiep (toi max_depth); "Den" dan toi
    man nang cap NHA CHINH -> ghi 'cho nha chinh' (khong thu lai toi khi HQ len cap).
    Nut nhan bang anh mau research/btn_research neu co, khong thi MAU + CHU (bot/buttons.py).
    -> 'started' | 'no_res' | 'wait_hq' | 'chain_long' | 'unknown'."""
    from bot import buttons, tplneed
    img = ctx.settle()
    if tplneed.has(ctx.v, TPL_PANEL, "khong xac nhan duoc bang node bang anh") and not ctx.v.find(img, TPL_PANEL, th=PANEL_TH):
        if not start_buttons(ctx, img):          # co anh mau ma khong thay bang node va khong co nut -> khong bam gi
            build_inv(ctx)
            return "unknown"
    go = start_buttons(ctx, img)
    if go:
        x, y, text = go[0]                           # nut hanh dong o day bang
        ctx.tap(x, y, wait=1.5, tpl="btn:nghien_cuu")
        res = verify_start(ctx)
        if res == "started":
            log.info("Bat dau nghien cuu (nut '%s')", text)
        return res
    req = buttons.with_text(img, GO_TXT, kinds=(buttons.GO,))
    if req:
        if depth >= max_depth:
            return "chain_long"
        b = req[0]
        ctx.tap(b.x, b.y, wait=2.0, tpl="btn:den")
        after = ctx.settle()
        if ctx.v.find(after, "build/btn_upgrade") or ctx.v.find(after, "build/title_hq")                 or ctx.v.find(after, "build/btn_upgrade_icon"):
            kind = "hq" if ctx.v.find(after, "build/title_hq") else classify_building(building_title(after))
            if kind == "lab":
                log.info("Nghien cuu can Vien nghien cuu len cap -> nang cap no truoc")
                return upgrade_lab(ctx)
            m = getattr(ctx, "mem", None)
            hq = m.fact(ctx.dev.idx, "hq_level") if m else None
            if m:
                m.set_fact(ctx.dev.idx, "research_wait_hq", hq if hq is not None else 0)
            log.info("Nghien cuu can nha chinh len cap (dang %s) -> cho, khong thu lai", hq)
            ctx.back_out()
            return "wait_hq"
        log.info("Nghien cuu: thieu nhanh phu -> sang node dieu kien (sau %d)", depth + 1)
        return node(ctx, depth + 1, max_depth)
    build_inv(ctx)
    return "unknown"


def build_inv(ctx):
    from bot import build
    build.inv_capture(ctx, "research_node")            # chua nhan ra bang node -> 1 anh/ngay de bo sung


def nores_until(entry, now):
    """Fact research_nores -> epoch con chan | None (ham thuan)."""
    try:
        t = float((entry or {}).get("until") or 0)
    except (TypeError, ValueError, AttributeError):
        return None
    return t if t > now else None


def note_nores(entry, now, base_min=60, cap_h=6):
    """Them 1 lan het tai nguyen (ham thuan): chan base_min * 2^(n-1) phut, toi da cap_h gio."""
    n = int((entry or {}).get("n") or 0) + 1
    return {"until": now + min(cap_h * 3600, base_min * 60 * 2 ** (n - 1)), "n": n}


def node_key(tab, page, x, y):
    """Khoa node theo nhanh / trang cuon / vi tri (lam tron 30px)."""
    return f"{tab}:{page}:{int(round(x / 30.0))}:{int(round(y / 30.0))}"


def live_skips(entries, now):
    return {k: v for k, v in (entries or {}).items() if isinstance(v, (int, float)) and v > now}


def pick_node(cands, skips, tab, page, now):
    """Node con nghien cuu duoc (a < b) theo uu tien tren -> duoi, trai -> phai, bo node dang bi bo qua (ham thuan).
    cands = [(x, y, a, b)] -> (x, y, a, b) | None."""
    for p in sorted((p for p in cands if p[2] < p[3]), key=lambda p: (p[1], p[0])):
        if (skips or {}).get(node_key(tab, page, p[0], p[1]), 0) <= now:
            return p
    return None


def set_nores(ctx, rc):
    m = getattr(ctx, "mem", None)
    if not m:
        return
    e = note_nores(m.fact(ctx.dev.idx, NORES_FACT), time.time(), rc.get("nores_backoff_min", 60), rc.get("nores_cap_h", 6))
    m.set_fact(ctx.dev.idx, NORES_FACT, e)
    log.info("Nghien cuu: thieu tai nguyen lan %d lien tiep -> thu lai luc %s", e["n"],
             time.strftime("%H:%M", time.localtime(e["until"])))


def clear_nores(ctx):
    m = getattr(ctx, "mem", None)
    if m and m.fact(ctx.dev.idx, NORES_FACT):
        m.set_fact(ctx.dev.idx, NORES_FACT, None)


def on_tree(ctx):
    """Dang o cay cong nghe (So Cong Nghe)? - truoc moi lan cham tab / node (khong bam mo)."""
    return bool(ctx.v.find(ctx.shot(), "research/title", th=0.8))


def pick_and_start(ctx, rc):
    """P2 muc 3: chon node hop le theo uu tien (nhanh theo research.branch_order: 0 Phat trien, 1 Dao tao, 2 Quan su;
    trong nhanh tren -> duoi), bo node vua hong (research_skip), toi da research.max_nodes_per_run node / luot.
    Thieu tai nguyen -> ghi research_nores (gian chu ky) va dung. -> so nghien cuu da bat dau (0/1)."""
    m = getattr(ctx, "mem", None)
    now = time.time()
    skips = live_skips(m.fact(ctx.dev.idx, SKIP_FACT) if m else None, now)
    tries, t0 = 0, now
    try:
        for i, tab in enumerate(rc.get("branch_order", [0, 1, 2])):
            if not on_tree(ctx):
                log.info("Nghien cuu: khong con o cay cong nghe - dung (khong bam mo)")
                return 0
            if i or tab:
                ctx.tap(95 + 175 * int(tab), 82, wait=1.5)
            page = 0
            while page < rc.get("pages_per_branch", 4):
                if time.time() - t0 > rc.get("max_s", 150):
                    log.info("Nghien cuu: het %ss cho luot nay", rc.get("max_s", 150))
                    return 0
                img = ctx.shot()
                p = pick_node(badges(img), skips, tab, page, time.time())
                if p:
                    x, y, a, bb = p
                    log.info("Nghien cuu: nhanh %s trang %d node %d/%d @%d,%d", tab, page, a, bb, x, y)
                    ctx.tap(x - 55, y - 45, wait=1.5)            # tam node (huy hieu o goc phai duoi)
                    res = node(ctx)
                    log.info("Nghien cuu node %d/%d -> %s", a, bb, res)
                    if res == "started":
                        clear_nores(ctx)
                        return 1
                    if res in ("no_res", "wait_hq") or res.startswith("lab_"):
                        if res == "no_res":
                            set_nores(ctx, rc)
                        return 0
                    # 'unknown' / 'chain_long': node nay khong lam duoc -> bo qua research.node_skip_h gio, thu node khac
                    skips[node_key(tab, page, x, y)] = time.time() + rc.get("node_skip_h", 6) * 3600
                    tries += 1
                    ctx.back_out(1)
                    if tries >= rc.get("max_nodes_per_run", 3) or not on_tree(ctx):
                        return 0
                    continue                                       # chon lai tren cung trang (node vua hong da bo qua)
                ctx.dev.swipe(270, 650, 270, 300, 500)            # cuon cay cong nghe xuong
                time.sleep(1.0)
                page += 1
        log.info("Nghien cuu: khong con node x<y nao (khong ghi 'dang ranh' vi co the doc sai)")
        return 0
    finally:
        if m:
            m.set_fact(ctx.dev.idx, SKIP_FACT, skips)


def run(ctx):
    rc = ctx.cfg.get("research", {})
    if wait_hq(ctx):
        log.info("Nghien cuu: dang cho nha chinh len cap - bo qua")
        return 0
    if lab_wait_until(ctx):
        log.info("Nghien cuu: dang cho nang cap Vien nghien cuu xong - bo qua")
        return 0
    m = getattr(ctx, "mem", None)
    nr = nores_until(m.fact(ctx.dev.idx, NORES_FACT) if m else None, time.time())
    if nr:
        log.info("Nghien cuu: lan truoc thieu tai nguyen - bo toi %s", time.strftime("%H:%M", time.localtime(nr)))
        return 0
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    hq = st.get("hq_level")
    if hq is not None and hq < rc.get("min_hq", 7):
        log.info("Xuong kien truc cap %d < %d - chua co Vien nghien cuu, bo qua", hq, rc.get("min_hq", 7))
        return 0
    if not open_research(ctx):
        return 0
    started = 0
    try:
        img = ctx.shot()
        b = busy(ctx.v, img)
        if not b:                                                # bang duoi co the hien cham -> nhin lai 1 lan
            time.sleep(1.5)
            img = ctx.shot()
            b = busy(ctx.v, img)
        if b:
            name, left = b
            record(ctx, name, left)
            log.info("Dang nghien cuu '%s' con %s -> chi 1 hang, cho xong", name,
                     f"{left // 86400}d {left % 86400 // 3600}h{left % 3600 // 60:02d}" if left else "?")
            return 0
        ctx.save_debug("research_screen")     # khong thay nut "Chi tiet" -> luu anh doi chieu (#1 dang nghien cuu 13 ngay)
        rec = recommended(ctx)                # truoc het: lam theo "Khuyen khich" (chu du an 2026-11-22)
        if rec == "started":
            clear_nores(ctx)
            return 1
        if rec == "no_res":
            set_nores(ctx, rc)
            return 0
        if rec is not None and rec != "unknown":
            return started
        return started + pick_and_start(ctx, rc)
    finally:
        ctx.ensure_city()
        rc = ctx.cfg.get("research", {})
        ctx.help_and_free(use_help=rc.get("use_help", True), use_free=rc.get("use_free_speedup", True))
