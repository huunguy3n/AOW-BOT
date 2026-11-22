"""Lam nhiem vu Chuong (cot truyen) va Chinh qua nut "Den" -> xay/nang cong trinh theo nhiem vu.

An toan: chi hanh dong khi "Den" dan toi man nang cap cong trinh (bot/build.py). Man khac (chien dich,
chieu mo, tuong...) -> quay ra, khong bam gi. Khong bam "Den" o tab Hang ngay (co nhiem vu chieu mo
cao cap co the ton kim cuong) - tien do hang ngay den tu cac buoc khac (gui quan, lien minh...).
Nhan thuong nhiem vu da xong: buoc 'daily'.
"""
import logging
import time

from aowbot.domain import blockers
from bot import build, game_msg, ocr, quest_rules, screens
from bot.modules import tutorial

log = logging.getLogger("aow")


def open_tab(ctx, tab):
    ctx.ensure_city()
    if not ctx.tap_tpl("daily/open_1", wait=1.5):
        return False
    if tab and not ctx.tap_tpl(tab, wait=1.2):
        return False
    return True


def _power(ctx):
    from bot import ocr
    try:
        ctx.ensure_city()
        return ocr.topbar(ctx.shot()).get("power")
    except Exception:
        return None


def _battle_blocked(ctx):
    """Tran theo nhiem vu chuong da thua -> khong danh lai toi khi luc chien tang power_gain_pct% (nhu mainquest)."""
    st = getattr(ctx, "store", None)
    need = st.inst(ctx.dev.idx).get("quests_need_power") if st else None
    if not need:
        return False
    p = _power(ctx)
    if p and p >= need:
        st.update(ctx.dev.idx, quests_need_power=None)
        log.info("Luc chien %d >= %d - nhiem vu chuong danh lai", p, need)
        return False
    log.info("Nhiem vu chuong: khong vao tran (luc chien %s < %s)", p, need)
    return True


def _block_battle(ctx):
    st = getattr(ctx, "store", None)
    p = _power(ctx)
    if st and p:
        pct = ctx.cfg.get("mainquest", {}).get("power_gain_pct", 5)
        need = int(p * (1 + pct / 100))
        st.update(ctx.dev.idx, quests_need_power=need)
        log.info("Nhiem vu chuong thua tran -> chi danh lai khi luc chien >= %d", need)


ROW_MAX_DIST = 12   # bit lech toi da cung 1 dong (do tren anh bang nhiem vu: cung dong 0-3, khac dong >= 28)


def row_title(img, p):
    """P4: chu tieu de dong nhiem vu (vung tren nut Den, cung vung voi row_key) - '' neu khong doc duoc."""
    y = int(p[1])
    roi = (110, max(0, y - 52), 280, 32)
    return " ".join(t for t in (ocr.text(img, roi, psm=7, bright=b) or "" for b in (None, 170)) if t)


def row_plan(title):
    """-> (bam Den?, loai, buoc phu trach). Ham thuan. Dong la viec cua buoc khac (huan luyen, phan quan, tinh bao,
    dau truong...) -> KHONG bam (do 21-22/11: 472 lan 'Den' tab Chinh -> none, deu la dong kieu nay)."""
    kind, module = quest_rules.classify(title)
    return not quest_rules.delegated(kind), kind, module


def is_hq_row(title):
    """Dong nhiem vu nang nha chinh ("Tang Xuong kien truc den cap N")."""
    return quest_rules.has_phrase(title, "kien truc")


def _hq_rush(ctx):
    from aowbot.domain import hqplan as dom
    m = getattr(ctx, "mem", None)
    lv = m.fact(ctx.dev.idx, "hq_level") if m else None
    return dom.hq_rush(lv, ctx.cfg.get("build", {}).get("hq_targets", dom.DEFAULT_TARGETS))


def row_key(img, p):
    """Dau van tay dong nhiem vu = dhash vung TIEU DE (tren nut Den, bo so tien do x/y hay doi)."""
    y = int(p[1])
    return screens.dhash(img[max(0, y - 52):max(1, y - 20), 110:390], 12)


def _blocks(ctx, now):
    st = getattr(ctx, "store", None)
    return blockers.load(st.inst(ctx.dev.idx).get("quest_blocks") if st else None, now)


def _save_blocks(ctx, blocks):
    st = getattr(ctx, "store", None)
    if st:
        st.update(ctx.dev.idx, quest_blocks=blockers.dump(blocks))


def _ttl(ctx):
    q = ctx.cfg.get("quests", {})
    ttl = dict(blockers.DEFAULT_TTL_S)
    if "none_retry_h" in q:
        ttl[blockers.BlockReason.NO_EFFECT] = float(q["none_retry_h"]) * 3600
    return ttl


def remember_block(ctx, blocks, key, now, first=None):
    """S2: 'Den' khong co tac dung -> doc thong bao noi cua game de biet vi sao, nho dong nay toi han.
    first: khung chup ngay sau khi cham (thong bao noi chi hien vai giay)."""
    reason, text = None, ""
    for img in (first, ctx.shot()):
        if img is not None and reason is None:
            reason, text = game_msg.read(img)
    reason = reason or blockers.BlockReason.NO_EFFECT
    b = blockers.block(key, reason, now, _ttl(ctx))
    blocks[key] = b
    _save_blocks(ctx, blocks)
    log.info("Nhiem vu: dong bi chan (%s) toi %s%s", reason.value, time.strftime("%H:%M", time.localtime(b.until)),
             f" - game: {text[:60]!r}" if text and reason is not blockers.BlockReason.NO_EFFECT else "")
    return reason


def claim_dot_tabs(ctx, max_tabs=3):
    """Bang nhiem vu co 3 tab (Chuong / Chinh / Hang ngay): tab nao co CHAM DO thi bam vao va nhan o tab do
    (chu du an 2026-11-22). Cham do o goc tren-phai tab; chi nhan nut 'Nhan' / 'Nhan toan bo' (claim_buttons)."""
    from bot.badges import red_dots
    if not open_tab(ctx, None):
        return 0
    n, seen = 0, set()
    for _ in range(max_tabs):
        dots = [d for d in red_dots(ctx.shot(), TAB_STRIP) if d[0] // 150 not in seen]
        if not dots:
            break
        x, y = dots[0]
        seen.add(x // 150)
        ctx.tap(x - 60, y + 22, wait=1.5)
        got = ctx.claim_buttons(max_taps=8) + ctx.claim_loop(["tutorial/btn_claim_all", "tutorial/btn_claim"], max_taps=8, th=0.85)
        n += got
        log.info("Nhiem vu: tab co cham do @%d,%d -> nhan %d", x, y, got)
    ctx.back_out()
    ctx.ensure_city()
    return n


TAB_STRIP = (0, 80, 540, 60)    # hang 3 tab bang nhiem vu (y ~112); cham do o goc tren-phai tab


def run(ctx):
    q = ctx.cfg.get("quests", {})
    claimed = 0
    try:
        claimed = claim_dot_tabs(ctx)
    except Exception as e:     # loi o day khong duoc chan buoc xay theo nhiem vu
        log.warning("Nhiem vu: loi khi nhan o tab co cham do: %s", e)
        ctx.ensure_city()
    if not ctx.cfg.get("build", {}).get("follow_quests", True):
        log.info("Tat xay theo nhiem vu - bo qua")
        return claimed
    from bot import hqplan
    if hqplan.yield_builder(ctx, "quests"):   # G1: tho ranh dang danh cho nha chinh
        return claimed
    tabs = []
    if q.get("story", True):
        tabs.append(None)                # tab Chuong mo san khi vao bang
    if q.get("main", True):
        tabs.append("daily/tab_2_main")
    max_go = q.get("max_go_per_run", 6)
    started = tries = 0
    no_battle = _battle_blocked(ctx)
    rush = _hq_rush(ctx)
    now = time.time()
    blocks = _blocks(ctx, now)
    for tab in tabs:
        tried = set()
        while tries < max_go:
            ctx.ensure_city()
            b = build.builders(ctx)
            if b and b[0] >= b[1] and not q.get("follow", True):
                log.info("Tho xay dang ban %d/%d - dung xay theo nhiem vu", *b)
                return started + claimed
            if not open_tab(ctx, tab):
                break
            # nhan thuong dong da xong + thuong chuong ("Nhan toan bo") - ca tab Chuong va Chinh (anh chu du an
            # 2026-11-21: ca 2 tab co nut Nhan ma bot bo qua) -> do nut theo mau + chu, them anh mau cu cho tab Chuong
            n = ctx.claim_buttons(max_taps=8)
            if tab is None:
                n += ctx.claim_loop(["tutorial/btn_claim_all", "tutorial/btn_claim"], max_taps=8, th=0.85)
            if n:
                log.info("Bang %s: nhan %d", (tab or "chuong").split("/")[-1], n)
                tried.clear()                # dong da nhan bien mat -> cac dong dich len, danh so lai
            img = ctx.shot()
            gos = sorted(ctx.v.find_all(img, "quest/btn_go"), key=lambda p: p[1])  # tren -> duoi
            keys = {k: row_key(img, p) for k, p in enumerate(gos)}
            for k in keys:   # S2: dong da biet bi chan (lo dat chua mo, thieu dieu kien, 'Den' vo tac dung) -> bo qua
                b = blockers.find_active(blocks, keys[k], now, ROW_MAX_DIST)
                if b and k not in tried:
                    tried.add(k)
                    log.info("Nhiem vu %s dong %d: bo qua (%s, con %.0f phut)", (tab or "chuong").split("/")[-1],
                             k + 1, b.reason.value, (b.until - now) / 60)
            todo = [(k, p) for k, p in enumerate(gos) if k not in tried]
            if q.get("read_rows", True):   # P4: doc tieu de dong, bo dong la viec cua buoc khac (khong bam Den)
                keep, titles = [], {}
                for k, p in todo:
                    titles[k] = row_title(img, p)
                    go, kind, module = row_plan(titles[k])
                    if go:
                        keep.append((k, p))
                    else:
                        tried.add(k)
                        log.info("Nhiem vu %s dong %d: %s -> viec cua buoc %s, khong bam Den",
                                 (tab or "chuong").split("/")[-1], k + 1, kind, module)
                todo = keep
                if rush:   # P4 muc 5: dang day nha chinh (build.hq_targets) -> dong "Xuong kien truc" lam truoc
                    todo.sort(key=lambda kp: 0 if is_hq_row(titles.get(kp[0], "")) else 1)
            if not todo:
                break
            k, p = todo[0]
            tried.add(k)
            tries += 1
            ctx.tap(p[0], p[1], wait=2.5)
            first = ctx.shot() if tab is not None else None   # giu khung co thong bao noi (neu co) cho S2
            res = build.upgrade_here(ctx)
            if res == "none" and tab is None:  # khong phai xay: tuong / don phe tich / xay moi... -> theo huong dan game
                res = "follow_" + str(tutorial.follow(ctx, ctx.cfg.get("quests", {}).get("follow_steps", 40),
                                                      no_battle=no_battle))
                if res in ("follow_lose", "follow_weak") and not no_battle:
                    no_battle = True             # cac dong sau van lam (tuong, phe tich...) nhung KHONG vao tran
                    _block_battle(ctx)
            log.info("Nhiem vu %s dong %d -> %s", (tab or "chuong").split("/")[-1], k + 1, res)
            if res == "none":   # A-INV-1: 'Den' khong dan toi man nang cap (391 lan 11-19..21) -> luu anh dieu tra
                build.inv_capture(ctx, f"quests_{(tab or 'chuong').split('/')[-1]}_row{k + 1}")
                if tab is not None:   # tab Chuong da theo huong dan game (follow) -> khong chan o day
                    remember_block(ctx, blocks, keys[k], now, first)
            if res in ("started", "follow_build_started"):
                started += 1
            ctx.back_out()
            if res in ("started", "follow_build_started"):
                build.quick_wait(ctx)    # xay nhanh -> cho xong, dong sau xay tiep (chu du an 2026-11-22)
            if res == "no_builder" and not q.get("follow", True):
                ctx.ensure_city()
                return started + claimed     # het tho: dong khac (tuong, phe tich...) van lam duoc neu bat follow
    ctx.ensure_city()
    return started + claimed
