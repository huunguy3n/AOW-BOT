"""Nhiem vu chinh UU TIEN: doc chu thanh nhiem vu goc trai duoi thanh pho -> phan loai -> lam / de buoc khac lam.

P4 (PM 2026-11-23; do 21-22/11: 32/33 lan tra 0, 76 follow_stuck): truoc day bot cham thanh nhiem vu roi "lam theo
huong dan" (follow) bat ke nhiem vu la gi -> "Tham gia tap ket phan quan" dua ra ban do the gioi, follow cham giua
ban do toi ket. Nay:
  1. OCR chu thanh nhiem vu (bot.quest_rules.classify) -> loai:
       build / hero / unknown -> cham thanh, lam nhu cu (nang cap qua build.upgrade_here, tran, follow)
       campaign               -> cham thanh -> man Chien dich -> danh man ke tiep (chi khi du doan thang)
       rebels (phien quan)    -> cong thuc hoc tu thao tac tay: muc tieu giua man -> "Tan cong" -> Xuat chinh
       rally/train/intel/...  -> KHONG cham: viec cua buoc phu trach (rebels, train, intel...), tra 0 -> stepgate gian
  2. Kiem ket qua THAT sau moi buoc: chu thanh nhiem vu doi (nhiem vu xong, sang nhiem vu moi) hoac xay/danh thang.
  3. Cung nhiem vu that bai lien tiep -> khong cham lai toi khi het thoi gian cho (mainquest.same_retry_h, gap doi).
  4. Nha chinh duoi muc tieu (build.hq_targets) + tho dang danh cho nha chinh -> khong cham nhiem vu xay (hqplan).
Khong bao gio bam nut ton kim cuong (build.upgrade_here, campaign giu luat do).
"""
import logging
import time

from bot import build, ocr, quest_rules, tplneed
from bot.modules import campaign

log = logging.getLogger("aow")
BANNER = (150, 818)
BANNER_TEXT_ROI = (36, 806, 480, 30)
TARGET = (272, 445)   # muc tieu (vd o do Mo ruong lanh tho / phien quan) sau khi camera can giua
NPC_ATTACK = "rebels/npc_attack"
NPC_SEARCH = "rebels/npc_btn_search"   # P12-4 (t55u): "Tim kiem" khi "Toi da co the tan cong phan quan cap X!" (s193422)
NPC_SEARCH_ROI = (100, 600, 340, 250)   # nut "Tan cong" bang phien quan (cat tu logs/human/20261121/002012-i3-mainquest-091)
SUCCESS = ("win", "build_started", "follow_build_started", "npc_sent")


def _power(ctx):
    return ocr.topbar(ctx.shot()).get("power")


TEXT_X0 = 52          # P9-9: chu bat dau sau icon (x < 52 = icon + cham do -> OCR ra '}' / ']')
TEXT_GAP = 18         # cot trong lien tiep >= 18 px sau chu = het chu (khoang giua 2 tu ~6 px)


def text_extent(img, roi=BANNER_TEXT_ROI, x0=TEXT_X0, gap=TEXT_GAP):
    """P9-9 (live2 11:10:39 '} C6 the nhan Ruong moi ngay : 8. S. N | P Cothenhan Ruongpd'): thanh nhiem vu trong suot,
    nen thanh pho sang phia PHAI chu bi OCR thanh rac. Ham thuan: cot co chu (trang sang V >= 200, S <= 60) tu x0; chu
    ket thuc o khoang trong >= gap cot. -> (x, y, w, h) chi phu chu | None (khong co chu)."""
    import cv2
    _, ry, rw, rh = roi
    x_end = roi[0] + rw
    hsv = cv2.cvtColor(img[ry + 2:ry + rh - 2, x0:x_end], cv2.COLOR_BGR2HSV)
    cols = ((hsv[..., 2] >= 200) & (hsv[..., 1] <= 60)).sum(0)
    start, last, run = None, None, 0
    for i, c in enumerate(cols):
        if c >= 1:              # chu kem mo (anh #0 'Tang Xuong kien truc') nhieu cot chi 1 diem sang
            start = i if start is None else start
            last, run = i, 0
        elif start is not None:
            run += 1
            if run >= gap:
                break
    if start is None or last is None:
        return None
    return x0, ry, min(x_end - x0, last + 10), rh


def read_banner(ctx, img=None):
    """Chu thanh nhiem vu (2 cach nhi phan, noi lai) - '' neu khong doc duoc. P9-9: chi OCR phan co chu (text_extent)."""
    img = img if img is not None else ctx.shot()
    roi = text_extent(img) or BANNER_TEXT_ROI
    parts = [clean_text(ocr.text(img, roi, bright=b, psm=7) or "") for b in (170, None)]
    return " | ".join(p for p in parts if p)


def clean_text(t):
    """P9-9: bo token rac dau (icon: '}' ']' '|' '~') va cuoi (chi dau cau: '.' ':' ';' '‘'). Ham thuan."""
    toks = t.split()
    while toks and not any(ch.isalnum() for ch in toks[0]):
        toks.pop(0)
    while toks and not any(ch.isalnum() for ch in toks[-1]):
        toks.pop()
    return " ".join(toks)


def _blocked(ctx, mq):
    """Gap boss qua kho: dung danh nhiem vu chinh cho toi khi luc chien tang du (lam viec tang suc manh truoc)."""
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    need = st.get("mainquest_need_power")
    if not need:
        return False
    p = _power(ctx)
    if p and p >= need:
        log.info("Luc chien %d >= %d - thu lai nhiem vu chinh", p, need)
        ctx.store.update(ctx.dev.idx, mainquest_need_power=None)
        return False
    log.info("Nhiem vu chinh tam dung: luc chien %s < %s (dang tang suc manh)", p, need)
    return True


def _block(ctx, mq, why):
    p = _power(ctx)
    if p and getattr(ctx, "store", None):
        need = int(p * (1 + mq.get("power_gain_pct", 5) / 100))
        ctx.store.update(ctx.dev.idx, mainquest_need_power=need, mainquest_block_reason=why)
        log.info("Tran nhiem vu chinh %s -> lam nhiem vu tang suc manh, thu lai khi luc chien >= %d", why, need)


def _fight(ctx, mq):
    campaign.auto_formation(ctx)                     # toi uu doi hinh TRUOC khi xem du doan
    if not campaign.predicted_win(ctx.v, ctx.shot()) and not mq.get("fight_unpredicted", False):
        ctx.back_out(2)
        ctx.ensure_city()
        _block(ctx, mq, "khong du doan thang")
        return "skip"
    r = campaign.battle(ctx, only_win=False)
    if r == "lose":
        ctx.ensure_city()
        _block(ctx, mq, "thua")
    return r


def npc_popup_action(img, v):
    """Ham thuan P12-4: bang phien quan dang mo -> 'attack' (nut Tan cong) | 'search' (popup 'Toi da co the tan cong
    phan quan cap X!' chi co nut 'Tim kiem' - game dan toi con dung cap) | None."""
    if v.find(img, NPC_ATTACK, th=0.85):
        return "attack"
    if v.has(NPC_SEARCH) and v.find(img, NPC_SEARCH, th=0.85, roi=NPC_SEARCH_ROI):
        return "search"
    return None


def npc_search(ctx):
    """P12-4: bam 'Tim kiem' -> camera toi phien quan dung cap -> cham muc tieu giua man -> cho nut 'Tan cong'.
    -> toa do nut Tan cong | None."""
    p = ctx.find(NPC_SEARCH, th=0.85, roi=NPC_SEARCH_ROI)
    if not p:
        return None
    log.info("Phien quan: 'Toi da co the tan cong phan quan cap X' -> bam 'Tim kiem' de game dan toi con dung cap")
    ctx.tap(p[0], p[1], wait=3.0)
    ctx.settle()
    a = ctx.find(NPC_ATTACK, th=0.85)
    if not a:
        ctx.tap(*TARGET, wait=1.8)
        a = ctx.wait_for(NPC_ATTACK, timeout=3, th=0.85)
    return a


def npc_attack(ctx, mq):
    """P13-12 (chu du an chua quyet viec danh le phien quan tu bang nhiem vu khi nha chinh < 15): GIU danh le cap thap CHI
    khi lan do thanh cong; that bai / khong vao duoc bang muc tieu / bo / tranh chap -> lui 2h (gap doi, tran 24h), khong
    thu lai moi lan ghe (live5 #2/#3/#4/#6: 'npc_none' moi lan, ~15 s / lan). Khong lien quan tham gia tap ket Co giap
    (HQ < 15 khong bao gio tham gia)."""
    m = getattr(ctx, "mem", None)
    idx, now = ctx.dev.idx, time.time()
    if m:
        ok, why = quest_rules.npc_gate(m.fact(idx, "npc_fail_until"), now)
        if not ok:
            log.info("Phien quan (nhiem vu): bo qua - %s", why)
            return "npc_wait"
    r = _npc_attack_once(ctx, mq)
    if m:
        if r in quest_rules.NPC_FAIL:
            n = int(m.fact(idx, "npc_fail_n") or 0) + 1
            m.set_fact(idx, "npc_fail_n", n)
            m.set_fact(idx, "npc_fail_until", now + quest_rules.npc_backoff_s(n))
            log.info("Phien quan (nhiem vu): that bai lan %d (%s) - lui %.0f gio", n, r, quest_rules.npc_backoff_s(n) / 3600)
        elif r == "npc_sent":
            m.set_fact(idx, "npc_fail_n", 0)
            m.set_fact(idx, "npc_fail_until", None)
    return r


def _npc_attack_once(ctx, mq):
    """Nhiem vu 'Kich sat N lan phien quan': thanh nhiem vu -> ban do, muc tieu giua man -> 'Tan cong' -> Xuat chinh.
    -> 'npc_sent' | 'npc_skip' | 'npc_full' | 'npc_contested' | 'npc_none'. Thieu anh mau -> 'npc_none' (khong bam)."""
    if not tplneed.has(ctx.v, NPC_ATTACK, "nut Tan cong bang phien quan"):
        return "npc_none"
    if not ctx.world_ready():
        # P12-4 (live4 #3-#6 nha chinh 4-5: npc_skip ngay vi world.min_hq_level 6) - thanh nhiem vu tu dan ra ban do;
        # khong toi duoc bang muc tieu thi 'npc_none' nhu cu. Danh LE phien quan NPC, khong phai tap ket Co giap.
        log.info("Phien quan (nhiem vu): ban do chua chac mo (nha chinh thap) - van theo thanh nhiem vu, danh le")
    if ctx.march_full():
        log.info("Phien quan: het doi hanh quan ranh - de lan sau")
        return "npc_full"
    ctx.tap(*BANNER, wait=3.0)
    ctx.settle()
    p = ctx.find(NPC_ATTACK, th=0.85)
    if not p and npc_popup_action(ctx.shot(), ctx.v) == "search":
        p = npc_search(ctx)
    if not p:
        ctx.tap(*TARGET, wait=1.8)
        p = ctx.wait_for(NPC_ATTACK, timeout=3, th=0.85)
    if not p and npc_popup_action(ctx.shot(), ctx.v) == "search":
        p = npc_search(ctx)
    if not p:
        log.info("Phien quan: khong mo duoc bang muc tieu")
        ctx.save_debug("mainquest_npc_none")
        ctx.back_out(2)
        return "npc_none"
    img = ctx._img
    title = ocr.text(img, quest_rules.NPC_TITLE_ROI, bright=None, psm=7) or ""
    digits = "".join(ch for ch in (ocr.text(img, quest_rules.NPC_POWER_ROI, "0123456789,.", psm=7) or "") if ch.isdigit())
    rec = int(digits) if 3 <= len(digits) <= 10 else None    # "5,000" / "5.000" (dau phan cach doc lan) -> 5000
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    ok, why = quest_rules.npc_ok(quest_rules.npc_level(title), int(rec) if rec else None, st.get("power"),
                                 mq.get("npc_max_level", 10), mq.get("npc_max_ratio", 0.3))
    if not ok:
        log.info("Phien quan: khong danh (%s, tieu de %r)", why, title[:30])
        ctx.back_out(2)
        return "npc_skip"
    ctx.tap(p[0], p[1], wait=2.0)
    if not ctx.wait_for("gather/btn_march", timeout=5):
        ctx.save_debug("mainquest_npc_no_march")
        ctx.back_out(3)
        return "npc_none"
    ctx.tap_tpl("gather/btn_recommended", wait=1.0)
    ctx.tap_tpl("gather/btn_march", wait=2.0)
    img = ctx.shot()
    if ctx.v.has("gather/dlg_contested") and ctx.v.find(img, "gather/dlg_contested"):
        # P3: hop thoai "Co Chi huy truong khac dang hanh quan den" -> LUON Huy, khong bao gio Tiep tuc
        ctx.tap_first(["common/btn_cancel_exit", "common/btn_x", "common/btn_close"], wait=1.0)
        ctx.back_out(3)
        return "npc_contested"
    if ctx.v.find(img, "gather/btn_march"):
        log.info("Phien quan: bam Xuat chinh khong di (man quan doan con)")
        ctx.save_debug("mainquest_npc_not_sent")
        ctx.back_out(3)
        return "npc_none"
    log.info("Phien quan: da xuat chinh (%s)", why)
    return "npc_sent"


def daily_chest(ctx, text=""):
    """P9-3: thanh nhiem vu "Co the nhan Ruong moi ngay" (live-run-2 doc ra '... C6 the nhan Ruong moi ngay ...' ->
    loai unknown, bo qua). Cham thanh -> CHI nhan bang nut "Nhan" xanh (claim_buttons: mau + chu, bo nut tra phi) va
    cham do trang VIP (rewards.vip_dots - khong bao gio mua goi VIP). -> so lan nhan."""
    from bot.modules import rewards
    log.info("Nhiem vu chinh %r -> nhan Ruong moi ngay (mien phi)", (text or "")[:60])
    ctx.tap(*BANNER, wait=2.5)
    n = ctx.claim_buttons(max_taps=4)
    if not ctx.is_home():
        n += rewards.vip_dots(ctx, max_taps=4)
    ctx.dismiss_reward()
    ctx.ensure_city()
    log.info("Ruong moi ngay: nhan %d", n)
    return n


def step(ctx, mq, kind="unknown"):
    ctx.ensure_city()
    if not ctx.find("quest/banner_icon"):
        return "none"
    if kind == "rebels":
        return npc_attack(ctx, mq)
    ctx.tap(*BANNER, wait=2.5)
    ctx.dismiss_reward()                      # "Nhan thuong" -> bang thuong
    ctx.skip_dialogs()
    if ctx.find("campaign/btn_fight"):
        return _fight(ctx, mq)
    img = ctx.shot()
    if ctx.v.find(img, "common/btn_close", th=0.85, roi=(440, 150, 100, 80)) and ctx.v.find(img, "quest/btn_go"):
        ctx.back_out()                        # thanh nhiem vu mo bang Chuong (sau tan thu) -> buoc 'quests' lam
        return "chapter_board"
    if ctx.find("campaign/title", fresh=False):
        return campaign.fight_one(ctx, ctx.cfg.get("campaign", {}).get("only_predicted_win", True))
    r = build.upgrade_here(ctx)
    if r != "none":
        return "build_" + r
    if ctx.is_home():                         # camera da toi muc tieu tren thanh pho
        ctx.tap(*TARGET, wait=3.0)
        if ctx.wait_for("campaign/btn_fight", timeout=3):
            return _fight(ctx, mq)
        r = build.upgrade_here(ctx)
        if r != "none":
            return "build_" + r
    q = ctx.cfg.get("quests", {})
    if q.get("follow", True):                 # vd danh sach Tuong, don phe tich -> lam theo huong dan game
        from bot.modules import tutorial
        r = tutorial.follow(ctx, q.get("follow_steps", 40))
        ctx.ensure_city()
        return "follow_" + str(r)
    ctx.save_debug("mainquest_unknown")
    ctx.back_out()
    return "unknown"


def _mem(ctx):
    return getattr(ctx, "mem", None)


def _remember(ctx, text, kind, progressed, now):
    """Nho nhiem vu + so lan that bai lien tiep (de giam chu ky khi cung nhiem vu cu ket)."""
    m = _mem(ctx)
    if not m:
        return
    last = m.fact(ctx.dev.idx, "mainquest_last") or {}
    same = quest_rules.same_quest(last.get("text"), text)
    fails = 0 if progressed else (int(last.get("fails", 0)) + 1 if same else 1)
    m.set_fact(ctx.dev.idx, "mainquest_last", {"text": (text or "")[:90], "kind": kind, "fails": fails, "at": now})


def _hq_yield(ctx, kind):
    """P4 muc 5: nhiem vu xay ma tho dang danh cho nha chinh (hqplan, len build.hq_targets) -> nhuong."""
    if kind not in ("build", "unknown"):
        return False
    from bot import hqplan
    try:
        return hqplan.yield_builder(ctx, "mainquest (nhiem vu xay)")
    except Exception as e:      # doc tho xay loi -> khong chan nhiem vu
        log.debug("hq_yield loi: %s", e)
        return False


def run(ctx):
    mq = ctx.cfg.get("mainquest", {})
    ctx.ensure_city()
    if _blocked(ctx, mq):
        return 0
    m = _mem(ctx)
    until = m.fact(ctx.dev.idx, "mainquest_busy_until") if m else None
    if until and until > time.time():
        log.info("Nhiem vu chinh dang thuc hien (cong trinh dang xay) - xong luc %s, bo qua",
                 time.strftime("%H:%M %d/%m", time.localtime(until)))
        return 0
    img = ctx.shot()
    if not ctx.v.find(img, "quest/banner_icon"):
        return 0
    text = read_banner(ctx, img) if mq.get("read_banner", True) else ""
    kind, module = quest_rules.classify(text)
    now = time.time()
    if getattr(ctx, "store", None):
        ctx.store.update(ctx.dev.idx, mainquest_text=text[:90], mainquest_kind=kind)
    if kind == "expand" and m:
        m.set_fact(ctx.dev.idx, "expand_pending", now)   # P13-11: buoc 'expand' chay ngay trong lan ghe nay
    if quest_rules.delegated(kind) and not (kind == "rebels" and mq.get("npc_rebels", True)):
        log.info("Nhiem vu chinh %r (%s) -> viec cua buoc %s, khong cham", text[:60], kind, module)
        _remember(ctx, text, kind, False, now)
        return 0
    if kind == "chest":
        return daily_chest(ctx, text)
    ok, why = quest_rules.should_retry(m.fact(ctx.dev.idx, "mainquest_last") if m else None, text, now,
                                       mq.get("same_retry_h", 1), mq.get("same_retry_cap_h", 8))
    if not ok:
        log.info("Nhiem vu chinh %r: %s", text[:60], why)
        return 0
    if _hq_yield(ctx, kind):
        return 0
    log.info("Nhiem vu chinh %r -> loai %s", text[:60], kind)
    done = 0
    for _ in range(mq.get("max_steps", 6)):
        r = step(ctx, mq, kind)
        ctx.ensure_city()
        after = read_banner(ctx) if text else ""
        changed = bool(text and after and not quest_rules.same_quest(text, after))
        log.info("Nhiem vu chinh: %s%s", r, " (nhiem vu da doi)" if changed else "")
        if r in ("build_busy", "build_maxed"):
            # chu du an 2026-11-21: cong trinh cua nhiem vu dang xay -> ghi nhan, khong lam o cac luot sau toi khi xong
            left = getattr(ctx, "last_busy", 0) or 0
            until = time.time() + (left + 60 if left else mq.get("busy_recheck_h", 2) * 3600)
            if m:
                m.set_fact(ctx.dev.idx, "mainquest_busy_until", until)
                if left:
                    m.set_timer(ctx.dev.idx, "build:quest", until, "quest", 0.8)
            if getattr(ctx, "store", None):
                ctx.store.update(ctx.dev.idx, mainquest_busy_until=until, mainquest_busy_why=r)
            break
        progressed = r in SUCCESS or changed
        _remember(ctx, text, kind, progressed, time.time())
        if not progressed:
            break  # thua / bo qua / khong ro -> de cac buoc tang suc manh chay
        done += 1
        if not changed or not after:
            if r == "npc_sent":
                break   # 1 doi / luot: doi ve roi moi danh tiep
            continue
        text = after   # nhiem vu moi -> phan loai lai
        kind, module = quest_rules.classify(text)
        if quest_rules.delegated(kind) and not (kind == "rebels" and mq.get("npc_rebels", True)):
            log.info("Nhiem vu chinh moi %r (%s) -> viec cua buoc %s", text[:60], kind, module)
            break
    ctx.ensure_city()
    return done
