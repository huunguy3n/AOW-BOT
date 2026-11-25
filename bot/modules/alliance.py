"""Lien minh: dong gop cong nghe (bang VANG, khong bao gio kim cuong), tro giup, qua lien minh.

KHONG tu dong: nhan tin kenh lien minh (gui tin thay ban), mua do tiem lien minh, xay co.
"""
import re, logging, time
from bot import buttons, ocr, tplneed

log = logging.getLogger("aow")
TURNS_ROI = (350, 666, 80, 18)   # "Luot:9/10" trong bang quyen gop


def open_alliance(ctx):
    ctx.ensure_city()
    if not ctx.tap_tpl("ally/btn_open", wait=2.0):
        log.info("Khong thay nut Lien minh (chua vao lien minh?)")
        return False
    ctx.close_popups(1)
    return True


# P6 ra soat an toan (A-SAFE-5): chi tim o NUA PHAI - nut trai quyen gop bang kim cuong.
# P7-2 (anh chu du an 2026-11-24 "Lien minh vinh cuu"): nut ngon cai (de xuat) cung o NUA PHAI nhung PHIA TREN bang (~y 400)
# -> chi tim nut quyen gop o nua phai, NUA DUOI (y >= 480): "Quyen gop 100" vang (phai), KHONG "Quyen gop 40" kim cuong (trai)
DONATE_ROI = (270, 480, 270, 400)


def donate_safe(x, y, kind=None):
    """Diem cham quyen gop an toan: nua phai, nua duoi (khong trung nut ngon cai / nut kim cuong ben trai), va neu do duoc
    mau nut thi phai la nut xanh ngoc (vang) - nut kim cuong mau xanh duong (buttons.GO) -> tu choi."""
    rx, ry, rw, rh = DONATE_ROI
    return rx <= x <= rx + rw and ry <= y <= ry + rh and kind != buttons.GO


def _btn_kind(img, x, y):
    """Loai nut (theo mau) chua diem (x, y) | None (khong do duoc)."""
    try:
        for b in buttons.find(img, (max(0, x - 90), max(0, y - 40), 180, 80)):
            if abs(b.x - x) <= b.w // 2 + 4 and abs(b.y - y) <= b.h // 2 + 4:
                return b.kind
    except Exception:
        return None
    return None


def open_tech(ctx):
    """Mo bang quyen gop: cong nghe de xuat (dau ngon cai trong DANH SACH - cham than o, khong cham dau) hoac
    "Lien minh vinh cuu" (anh mau tuy chon ally/tech_vinh_cuu)."""
    p = ctx.find("ally/tech_recommended")
    if p:
        ctx.tap(p[0] + 48, p[1] + 40, wait=1.5)  # dau like nam goc tren-trai cua o cong nghe -> cham than o
        return True
    if ctx.v.has("ally/tech_vinh_cuu"):
        q = ctx.find("ally/tech_vinh_cuu", fresh=False)
        if q:
            ctx.tap(q[0], q[1], wait=1.5)
            return True
    log.info("Khong thay cong nghe de xuat")
    return False


def donate(ctx, max_n):
    if not ctx.tap_tpl("ally/tab_tech", wait=1.5):
        return 0
    if not open_tech(ctx):
        return 0
    n = 0
    while n < max_n:
        img = ctx.shot()
        m = re.search(r"(\d+)\s*/\s*(\d+)", ocr.text(img, TURNS_ROI))
        if m and int(m.group(1)) == 0:
            break
        p = ctx.v.find(img, "ally/btn_donate_gold", roi=DONATE_ROI)  # nut PHAI (vang); nut trai ton kim cuong
        if not p:
            break
        if not donate_safe(p[0], p[1], _btn_kind(img, p[0], p[1])):
            log.warning("Quyen gop: diem %d,%d khong phai nut vang an toan - dung", p[0], p[1])
            break
        ctx.tap(p[0], p[1], wait=1.2)  # cho so luot cap nhat truoc khi doc lai
        n += 1
    ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
    log.info("Dong gop cong nghe lien minh %d lan", n)
    return n


def help_all(ctx):
    # nut "Giup tat ca" chi hien khi co yeu cau (chua cat anh mau); thanh pho co icon bat tay common/btn_help
    if ctx.v.has("ally/btn_help_all") and ctx.tap_tpl("ally/tile_help", wait=1.5):
        ctx.tap_tpl("ally/btn_help_all", wait=1.0)
        ctx.back_out(1)


def run(ctx):
    a = ctx.cfg.get("alliance", {})
    if not ctx.cfg.get("quests", {}).get("alliance", True):
        return 0
    if not open_alliance(ctx):
        return 0
    n = donate(ctx, a.get("donate_max", 10))
    help_all(ctx)
    if a.get("territory", True):     # P7-2: moi lan dang nhap nhan loi nhuan Tranh Doat Cu Diem
        n += territory_claim(ctx)
    if a.get("gifts", True) and (main_tab(ctx) or (open_alliance(ctx) and main_tab(ctx))):
        n += gifts_tile(ctx)
    if a.get("boss", True) and main_tab(ctx):
        n += boss(ctx)
    if a.get("mine", True) and (main_tab(ctx) or (open_alliance(ctx) and main_tab(ctx))):
        n += ally_mine(ctx)
    ctx.ensure_city()
    ctx.help_and_free(use_help=True, use_free=False)
    return n


# ---------- qua tang lien minh ----------
GIFT_CAN_ROI = (380, 190, 150, 30)          # "Co the nhan:N" (goc phai, tren tab Qua thuong)
TAB_SPECIAL, TAB_NORMAL = (134, 251), (405, 251)


def gift_can_claim(img):
    """So qua THUONG con nhan duoc hom nay ("Co the nhan:N"). -> int | None (khong doc duoc)."""
    t = ocr.text(img, GIFT_CAN_ROI)
    m = re.search(r"[:;]\s*([0-9OoDd]+)", t or "")
    if not m:
        return None
    v = m.group(1).replace("O", "0").replace("o", "0").replace("D", "0").replace("d", "0")
    return int(v) if v.isdigit() else None


GIFT_SENT_ROI = (150, 850, 240, 30)          # "Gui Qua Thuong: 7/21" (day bang qua tang lien minh)


def gift_sent(img):
    """"Gui Qua Thuong: x/y" -> (x, y). Chu du an: 7/21 = da tan cong 14 luot."""
    m = re.search(r"(\d+)\s*/\s*(\d+)", ocr.text(img, GIFT_SENT_ROI, "0123456789/:", scale=4) or "")
    return (int(m.group(1)), int(m.group(2))) if m and int(m.group(1)) <= int(m.group(2)) <= 60 else None


def gift_more(before, after, rounds, max_rounds):
    """P7-2: lap "Nhan toan bo" o tab Qua thuong toi khi het (anh chu du an "Co the nhan: 103" can nhieu lan).
    Dung khi: het luot (0), so khong giam (nut khong co tac dung), hoac du max_rounds."""
    if rounds >= max_rounds or after == 0:
        return False
    return not (before is not None and after is not None and after >= before)


# P9-3 (chu du an 2026-11-24, gop y t39ua0 - CHUA CO ANH tab "Qua dac biet" / Ruong Lv.17: lam theo mo ta, khong
# bia anh mau): tab Qua dac biet -> bam "Nhan" tung mon toi het; Ruong Lv.17 (goc phai tren) co cham do -> nhan.
GIFT_LIST_ROI = (380, 280, 160, 560)        # cot nut "Nhan" ben phai danh sach qua (anh alliance_gift_qua_thuong)
CHEST_ROI = (400, 60, 140, 130)             # Ruong Lv.N goc phai tren (anh: ruong ~470,125, chu "Ruong Lv.17")
CHEST_TAP = (468, 128)
NHAN_RX = r"(?:^|\W)nh\w{1,2}n(?:\W|$)"   # chu "Nhan" (OCR mat dau)


def chest_dot(dots):
    """Cham do trong vung Ruong Lv.N -> True (ham thuan)."""
    x, y, w, h = CHEST_ROI
    return any(x <= d[0] <= x + w and y <= d[1] <= y + h for d in dots)


def lv_chest(ctx):
    """Ruong Lv.N cua qua lien minh: chi bam khi co cham do; nhan bang nut "Nhan" an toan (claim_buttons)."""
    from bot.badges import red_dots
    if not chest_dot(red_dots(ctx.shot(), CHEST_ROI)):
        return 0
    ctx.tap(*CHEST_TAP, wait=1.5)
    got = ctx.claim_buttons(max_taps=3)
    ctx.dismiss_reward()
    log.info("Qua lien minh: Ruong Lv (cham do) -> nhan %d", got or 1)
    if not ctx.find("ally/gift_title"):
        ctx.tap_first(["common/btn_close"] + ctx.POPUP_CLOSERS, wait=1.0)
    return max(got, 1)


def special_claim(ctx, max_taps=30, claim_all=True):
    """Tab "Qua dac biet": "Nhan toan bo" (neu co) roi bam "Nhan" TUNG MON (nut xanh co chu Nhan, khong dau hieu tra
    phi - buttons.with_text) toi khi het. Nut bam ma man khong doi -> khong bam lai. -> so lan nhan."""
    from bot import buttons, screens
    n = 0
    if claim_all and ctx.tap_tpl("ally/btn_gift_claim_all", wait=1.5, roi=CLAIM_ALL_ROI):
        ctx.dismiss_reward()
        n += 1
        log.info("Qua lien minh dac biet: nhan toan bo")
    dead, miss = set(), {}
    for _ in range(max_taps):
        img = ctx.shot()
        todo = [b for b in buttons.with_text(img, NHAN_RX, GIFT_LIST_ROI) if (b.x // 20, b.y // 20) not in dead]
        if not todo:
            break
        b = todo[0]
        k = (b.x // 20, b.y // 20)
        ctx.tap(b.x, b.y, wait=1.2)
        if screens.same(img, ctx.shot()):
            time.sleep(1.0)                 # P10-5 (live3 s153317: 2 mon con lai bi bo): hieu ung nhan cham -> chup lai
            if screens.same(img, ctx.shot()):
                miss[k] = miss.get(k, 0) + 1
                if miss[k] >= 2:            # 2 lan bam khong doi -> nut khong tac dung
                    dead.add(k)
                continue
        miss.pop(k, None)
        ctx.dismiss_reward()
        n += 1
    if n:
        log.info("Qua lien minh dac biet: nhan %d", n)
    return n


def gifts(ctx, x, y):
    """Icon hop qua (so do) tren thanh pho = "Qua tang lien minh" (chu du an 2026-11-21 #1)."""
    ctx.tap(x - 16, y + 17, wait=2.0)
    return gift_panel(ctx)


def gifts_tile(ctx):
    """P7-2: o "Qua tang lien minh" tren trang chinh Lien minh (moi lan dang nhap, khong cho cham do thanh pho)."""
    if not ctx.tap_tpl("ally/tile_gifts", wait=2.0, th=0.8):
        return 0
    n = gift_panel(ctx)
    ctx.back_out(1)
    return n


def gift_panel(ctx):
    """Bang "Qua tang lien minh" - MOI duong vao (icon thanh pho / reddots / rewards / o Lien minh) di qua day
    -> gift_loop (P11). -> so lan nhan."""
    if not ctx.wait_for("ally/gift_title", timeout=3):
        return 0
    return gift_loop(ctx)


# ---------- P11 (chu du an t52u 2026-11-24): nhan qua lien minh LAP DEN HET ----------
# Live3 #1: nhan 1 trang roi bo di, qua phat sinh lien tuc -> cuoi luot badge Lien minh van 26. So THAT dang cho nhan
# la SO DO TREN TAB (s152956: Qua dac biet 8, Qua thuong 43); "Co the nhan:243" la TRAN NHAN TRONG NGAY (243 -> 200
# sau khi nhan 43), khong phai so qua dang cho. Vong: nhan -> chuyen tab di roi ve (lam moi) -> doc lai -> lap.
TABS = {"special": TAB_SPECIAL, "normal": TAB_NORMAL}
TAB_NAME = {"special": "dac biet", "normal": "thuong"}
TAB_DOT_ROI = {"special": (200, 212, 80, 40), "normal": (470, 212, 70, 40)}   # so do goc phai-tren moi tab (~258/530,230)
TAB_FILL = {"special": (10, 235, 30, 23), "normal": (285, 235, 30, 23)}       # mau nen tab (dang chon = xanh ngoc)
CLAIM_ALL_ROI = (150, 860, 240, 90)          # "Nhan toan bo" (s152956 ~269,905); dong "Gui Qua Thuong" la chu, khong nut
EMPTY_ROI = (150, 545, 240, 50)              # "Chua co qua" giua bang (s153334)
EMPTY_RX = r"ch\w{0,2}a\s*c\w?\s*qu"


def active_tab(img):
    """Tab dang chon theo mau nen: xanh ngoc (BGR ~97,111,36) vs toi (~36,27,26). -> 'special' | 'normal' | None."""
    for k, (x, y, w, h) in TAB_FILL.items():
        b, g, r = (float(v) for v in img[y:y + h, x:x + w].reshape(-1, 3).mean(axis=0))
        if g > 80 and b > 65 and r < 70:
            return k
    return None


def tab_dot(img, tab):
    """Cham do (so) tren tab -> (x, y) | None."""
    from bot.badges import red_dots
    d = red_dots(img, TAB_DOT_ROI[tab])
    return d[0] if d else None


# (w, h, scale, bright, psm) - bo chon tren live3: s152939 13/43, s152956 8/43, s153301 8, s153326 2, s153309 (5) -> None
BADGE_OCR = ((24, 22, 6, 180, 8), (20, 20, 8, 190, 10), (24, 22, 6, None, 10), (22, 20, 7, None, 10), (24, 22, 6, 150, 10))


def badge_number(img, dot):
    """So trang trong cham do tab. OCR chu nho de sai (s153309 so 5 doc ra '3') -> chi nhan khi >= 2 cach doc trung
    nhau. -> int | None."""
    if not dot:
        return None
    x, y = dot
    votes = {}
    for w, h, sc, br, psm in BADGE_OCR:
        roi = (max(0, x - w // 2), max(0, y - h // 2), w, h)
        t = ocr.text(img, roi, "0123456789", scale=sc, psm=psm, bright=br, pad=6)
        if t and t.isdigit() and 0 < int(t) < 1000:
            votes[int(t)] = votes.get(int(t), 0) + 1
    best = max(votes.items(), key=lambda kv: kv[1], default=(None, 0))
    return best[0] if best[1] >= 2 else None


def list_buttons(img):
    """So nut xanh (Nhan) trong cot phai danh sach qua (dem theo mau, khong OCR)."""
    return len(buttons.find(img, GIFT_LIST_ROI))


def gift_empty(img):
    """Danh sach rong: khong nut nao trong danh sach + chu "Chua co qua" giua bang (s153334)."""
    if list_buttons(img):
        return False
    return bool(re.search(EMPTY_RX, buttons._norm(ocr.text(img, EMPTY_ROI))))


def gift_count(img, tab):
    """So qua DANG CHO tren tab dang mo (ham thuan tren anh). 0 = "Chua co qua" / khong nut + khong so do;
    so do doc duoc -> max(so do, so nut thay); khong doc duoc so -> so nut thay; co so do ma chua thay nut -> None."""
    btn = list_buttons(img)
    dot = tab_dot(img, tab)
    if not btn and (not dot or gift_empty(img)):
        return 0
    num = badge_number(img, dot)
    if num is not None:
        return max(num, btn)
    return btn or None


def show_tab(ctx, tab):
    """Mo tab va LAM MOI: tab dang chon -> chuyen sang tab kia roi ve (game tai lai danh sach). -> anh."""
    if active_tab(ctx.shot()) == tab:
        other = next(t for t in TABS if t != tab)
        ctx.tap(*TABS[other], wait=1.0)
    ctx.tap(*TABS[tab], wait=1.5)
    return ctx.shot()


def claim_all_once(ctx):
    """"Nhan toan bo" (anh mau, chi vung day bang CLAIM_ALL_ROI) -> True neu bam va man doi."""
    from bot import screens
    before = ctx.shot()
    if not ctx.tap_tpl("ally/btn_gift_claim_all", wait=1.5, roi=CLAIM_ALL_ROI):
        return False
    after = ctx.shot()
    ctx.dismiss_reward()
    return not screens.same(before, after)


def claim_tab(ctx, tab):
    """Nhan tren tab dang mo: uu tien "Nhan toan bo"; khong co thi "Nhan" tung mon. -> (so lan nhan, cach)."""
    if claim_all_once(ctx):
        return 1, "Nhan toan bo"
    return special_claim(ctx, claim_all=False), "Nhan tung mon"


def gift_progress(before, after, got):
    """Vong co tien trien: nhan duoc (man doi) hoac so giam. Ham thuan."""
    if got:
        return True
    return before is not None and after is not None and after < before


def gift_loop(ctx):
    """P11: Qua dac biet + Qua thuong (+ Ruong Lv co cham do): nhan -> lam moi tab -> doc lai so -> lap toi khi CA HAI
    tab rong ("Chua co qua" / khong so do / khong nut Nhan). Tran: alliance.gift_loop_rounds (30) vong HOAC
    gift_loop_max_s (180) giay; so khong giam + khong nhan duoc gift_stall_rounds (2) vong lien tiep -> anh + bo tab.
    KHONG bam "Gui Qua Thuong", "Tang qua an danh", goi tra phi (chi nut Nhan xanh / Nhan toan bo). -> so lan nhan."""
    a = ctx.cfg.get("alliance") or {}
    max_rounds = int(a.get("gift_loop_rounds", 30))
    max_s = float(a.get("gift_loop_max_s", 180))
    stall_n = int(a.get("gift_stall_rounds", 2))
    t0 = time.time()
    total = lv_chest(ctx)                  # P9-3: Ruong Lv.N goc phai tren co cham do -> nhan
    stall = {t: 0 for t in TABS}
    left = {t: None for t in TABS}
    off = {}                               # tab da bo: 'het luot' (Co the nhan 0) / 'ket'
    sent_done, clear, r, idle = False, False, 0, 0
    while r < max_rounds and time.time() - t0 < max_s:
        r += 1
        busy = False
        for tab in TABS:
            if tab in off:
                continue
            if time.time() - t0 >= max_s:
                busy = True
                break
            img = show_tab(ctx, tab)
            if tab == "normal":
                if not sent_done:
                    sent_done = True
                    _gift_sent_fact(ctx, img)
                if gift_can_claim(img) == 0:
                    off[tab], left[tab] = "het luot", 0
                    log.info("Qua lien minh thuong: het luot nhan hom nay (Co the nhan: 0) - bo qua tab")
                    continue
            before = gift_count(img, tab)
            if before == 0:
                left[tab] = 0
                continue
            busy = True
            got, how = claim_tab(ctx, tab)
            after = gift_count(show_tab(ctx, tab), tab)      # lam moi (chuyen tab di roi ve) roi DOC LAI
            left[tab] = after
            total += got
            log.info("Qua lien minh %s vong %d: con %s -> %s (%s, nhan %d)", TAB_NAME[tab], r,
                     "?" if before is None else before, "?" if after is None else after, how, got)
            if gift_progress(before, after, got):
                stall[tab] = 0
                continue
            stall[tab] += 1
            if stall[tab] >= stall_n:
                off[tab] = "ket"
                path = ctx.save_debug(f"ally_gift_stall_{tab}")
                log.warning("Qua lien minh %s: %d vong so khong giam (con %s) - nut khong an / OCR sai, dung tab (%s)",
                            TAB_NAME[tab], stall[tab], after, path)
        if len(off) == len(TABS):
            break
        if busy:
            idle = 0
            continue
        idle += 1
        img = ctx.shot()                   # doc lai so do 2 tab truoc khi dung (qua moi co the vua toi)
        dots = [t for t in TABS if t not in off and tab_dot(img, t)]
        if not dots or idle >= 2:          # 2 vong lien danh sach rong ma so do van hien -> so do cu, dung
            if dots:
                log.info("Qua lien minh: so do tab %s con nhung danh sach rong 2 vong - dung",
                         ", ".join(TAB_NAME[t] for t in dots))
            clear = True
            break
    total += lv_chest(ctx)                 # ruong Lv co the vua du diem sau khi nhan
    dt = time.time() - t0
    if clear:
        log.info("Qua lien minh: het qua sau %d vong (%.0f s), nhan %d lan", r, dt, total)
    elif len(off) < len(TABS):
        log.warning("Qua lien minh: cham tran (%d/%d vong, %.0f/%.0f s) - con dac biet %s, thuong %s; thoat",
                    r, max_rounds, dt, max_s, left["special"], left["normal"])
    else:
        log.info("Qua lien minh: dung sau %d vong (%s), nhan %d lan", r,
                 ", ".join(f"{TAB_NAME[t]} {why}" for t, why in off.items()), total)
    return total


def _gift_sent_fact(ctx, img):
    sent = gift_sent(img)
    if sent and getattr(ctx, "mem", None):
        ctx.mem.set_fact(ctx.dev.idx, "rebels_attacks_game", sent[1] - sent[0])
        log.info("Gui Qua Thuong %d/%d -> da tan cong phan quan %d luot hom nay", sent[0], sent[1], sent[1] - sent[0])


# ---------- Lanh tho > Tranh Doat Cu Diem (P7-2, chu du an 2026-11-24) ----------
TAB_ROW_ROI = (0, 50, 540, 70)                 # hang tab Lien minh / cong nghe / Lanh tho / Thanh vien / Su vu
CONTEST_BTN_ROI = (270, 860, 270, 100)         # nut "Tranh Doat Cu Diem" goc phai duoi tab Lanh tho
CONTEST_CLAIM_ROI = (360, 330, 180, 100)       # nut "Nhan" ben phai dong "Loi nhuan tai nguyen"
CLAIM_RX = r"\bnh\w{1,2}n\b"


def territory_claim(ctx):
    """Lien minh > tab "Lanh tho" > "Tranh Doat Cu Diem" > "Nhan" (loi nhuan tai nguyen). Thieu anh mau -> bo qua em.
    Nut "Nhan" mau xanh duong (khong phai xanh ngoc) -> tim bang anh mau, khong co thi bang mau + chu 'Nhan'."""
    if not (tplneed.has(ctx.v, "ally/tab_territory", "tab Lanh tho lien minh")
            and tplneed.has(ctx.v, "ally/btn_contest", "nut Tranh Doat Cu Diem")):
        return 0
    if not ctx.tap_tpl("ally/tab_territory", wait=1.5, roi=TAB_ROW_ROI):
        log.info("Lanh tho: khong thay tab")
        return 0
    if not ctx.tap_tpl("ally/btn_contest", wait=2.0, roi=CONTEST_BTN_ROI):
        log.info("Lanh tho: khong thay nut Tranh Doat Cu Diem")
        return 0
    img = ctx.shot()
    p = ctx.v.find(img, "ally/btn_contest_claim", roi=CONTEST_CLAIM_ROI) if ctx.v.has("ally/btn_contest_claim") else None
    if not p:
        bs = buttons.with_text(img, CLAIM_RX, CONTEST_CLAIM_ROI)
        p = (bs[0].x, bs[0].y) if bs else None
    n = 0
    if p:
        ctx.tap(p[0], p[1], wait=1.5)
        ctx.dismiss_reward()
        n = 1
        log.info("Tranh Doat Cu Diem: nhan loi nhuan tai nguyen")
    else:
        log.info("Tranh Doat Cu Diem: chua co loi nhuan de nhan")
    ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
    return n


# ---------- BOSS lien minh / Mo lien minh (chu du an 2026-11-21, anh #1) ----------
BOSS_CHESTS = (30, 470, 480, 90)        # hang ruong 30% / 60% / Tieu diet (cham do = nhan duoc)


def main_tab(ctx):
    """Ve tab "Lien minh" (trang chinh co o Mo lien minh, BOSS, N.vu, Tiem...)."""
    ctx.tap_tpl("ally/tab_main", wait=1.5, th=0.75, roi=(0, 50, 220, 70))
    return bool(ctx.find("ally/tile_boss", th=0.8) or ctx.find("ally/mine_go", th=0.8, fresh=False))


def boss(ctx):
    """O BOSS lien minh -> nhan ruong muc sat thuong (cham do). Khong khieu chien. -> so ruong."""
    from bot.badges import red_dots
    if not ctx.tap_tpl("ally/tile_boss", wait=2.0, th=0.8):
        return 0
    n = 0
    if ctx.wait_for("ally/boss_title", timeout=3):
        for _ in range(4):
            dots = red_dots(ctx.shot(), BOSS_CHESTS)
            if not dots:
                break
            x, y = dots[0]
            ctx.tap(x - 18, y + 22, wait=1.5)
            ctx.dismiss_reward()
            n += 1
            log.info("BOSS lien minh: nhan ruong @%d,%d", x, y)
    ctx.back_out(1)
    return n


MINE_EARLY_MIN_FREE = 2


def mine_decision(free):
    """Ham thuan P13b (chu du an t77u/t78u): so quan doan ranh -> 'full' (0: bo) | 'defer' (1: giu cho tinh bao/phan quan,
    gui cuoi luot cung gather) | 'early' (>=2: gui som trong buoc lien minh)."""
    if free <= 0:
        return "full"
    return "early" if free >= MINE_EARLY_MIN_FREE else "defer"


def ally_mine(ctx, late=False):
    """"Den thu thap" Mo lien minh (Xuong Hop Kim lien minh) -> gui 1 doi. P13b: som (trong buoc lien minh) chi khi con
    >= 2 doi ranh; con 1 -> hoan (ctx.ally_mine = 'deferred'), cuoi luot (late=True, truoc gather) moi gui. -> 1 | 0"""
    if ctx.march_full():
        log.info("Mo lien minh: het quan doan ranh - bo qua")
        return 0
    if not late:
        free = ctx.march_free()
        what = mine_decision(free)
        log.info("Mo lien minh: %d quan doan ranh -> %s", free,
                 {"early": "gui som", "defer": "hoan cuoi luot cung thu thap", "full": "bo qua"}[what])
        if what == "defer":
            ctx.ally_mine = "deferred"
        if what != "early":
            return 0
    if not ctx.tap_tpl("ally/mine_go", wait=3.0, th=0.8):
        return 0
    # ban do the gioi: vong menu quanh Xuong Hop Kim lien minh (Tin tuc / Thu thap / Huong dan / Quyen gop) -> "Thu thap"
    if ctx.wait_for("ally/mine_collect", timeout=5, th=0.8):
        ctx.tap_tpl("ally/mine_collect", wait=2.0, th=0.8, fresh=False)
    if not (ctx.wait_for("gather/btn_march", timeout=4) or ctx.find("gather/btn_gather", fresh=False)):
        ctx.save_debug("ally_mine_no_gather")          # chua biet man nay -> anh de bo sung
        ctx.ensure_city()
        return 0
    if ctx.find("gather/btn_gather", fresh=False):
        ctx.tap_tpl("gather/btn_gather", wait=1.5, fresh=False)
    ctx.tap_tpl("gather/btn_recommended", wait=1.0)
    ok = ctx.tap_tpl("gather/btn_march", wait=2.0)
    log.info("Mo lien minh: %s", "gui 1 doi thu thap" if ok else "khong gui duoc")
    if ok:
        ctx.march_sent()
        ctx.ally_mine = "sent"
    ctx.ensure_city()
    return int(bool(ok))


def ally_mine_end(ctx):
    """P13b: cuoi luot, ngay truoc gather: gui mo lien minh da hoan o buoc lien minh (con 1 doi ranh luc do). Da gui som /
    khong hoan -> khong lam gi. Het quan doan ranh luc nay -> bo (nhu thuong). -> 1 | 0"""
    if getattr(ctx, "ally_mine", None) != "deferred":
        return 0
    ctx.ally_mine = "done"           # moi lan ghe chi thu 1 lan
    a = ctx.cfg.get("alliance", {})
    if not a.get("mine", True) or not ctx.cfg.get("quests", {}).get("alliance", True):
        return 0
    log.info("Mo lien minh (cuoi luot, cung thu thap): gui doi da giu lai")
    if not (open_alliance(ctx) and main_tab(ctx)):
        ctx.ensure_city()
        return 0
    n = ally_mine(ctx, late=True)
    ctx.ensure_city()
    return n
