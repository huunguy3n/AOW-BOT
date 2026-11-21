"""Lam nhiem vu Chuong (cot truyen) va Chinh qua nut "Den" -> xay/nang cong trinh theo nhiem vu.

An toan: chi hanh dong khi "Den" dan toi man nang cap cong trinh (bot/build.py). Man khac (chien dich,
chieu mo, tuong...) -> quay ra, khong bam gi. Khong bam "Den" o tab Hang ngay (co nhiem vu chieu mo
cao cap co the ton kim cuong) - tien do hang ngay den tu cac buoc khac (gui quan, lien minh...).
Nhan thuong nhiem vu da xong: buoc 'daily'.
"""
import time, logging
from bot import build
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


def run(ctx):
    q = ctx.cfg.get("quests", {})
    if not ctx.cfg.get("build", {}).get("follow_quests", True):
        log.info("Tat xay theo nhiem vu - bo qua")
        return 0
    tabs = []
    if q.get("story", True):
        tabs.append(None)                # tab Chuong mo san khi vao bang
    if q.get("main", True):
        tabs.append("daily/tab_2_main")
    max_go = q.get("max_go_per_run", 6)
    started = tries = 0
    no_battle = _battle_blocked(ctx)
    for tab in tabs:
        tried = set()
        while tries < max_go:
            ctx.ensure_city()
            b = build.builders(ctx)
            if b and b[0] >= b[1] and not q.get("follow", True):
                log.info("Tho xay dang ban %d/%d - dung xay theo nhiem vu", *b)
                return started
            if not open_tab(ctx, tab):
                break
            if tab is None:                  # bang Chuong: nhan thuong dong da xong + thuong chuong (nut SANG)
                n = ctx.claim_loop(["tutorial/btn_claim_all", "tutorial/btn_claim"], max_taps=8, th=0.85)
                if n:
                    log.info("Bang chuong: nhan %d", n)
                    tried.clear()            # dong da nhan bien mat -> cac dong dich len, danh so lai
            gos = sorted(ctx.v.find_all(ctx.shot(), "quest/btn_go"), key=lambda p: p[1])  # tren -> duoi
            todo = [(k, p) for k, p in enumerate(gos) if k not in tried]
            if not todo:
                break
            k, p = todo[0]
            tried.add(k)
            tries += 1
            ctx.tap(p[0], p[1], wait=2.5)
            res = build.upgrade_here(ctx)
            if res == "none" and tab is None:  # khong phai xay: tuong / don phe tich / xay moi... -> theo huong dan game
                res = "follow_" + str(tutorial.follow(ctx, ctx.cfg.get("quests", {}).get("follow_steps", 40),
                                                      no_battle=no_battle))
                if res in ("follow_lose", "follow_weak") and not no_battle:
                    no_battle = True             # cac dong sau van lam (tuong, phe tich...) nhung KHONG vao tran
                    _block_battle(ctx)
            log.info("Nhiem vu %s dong %d -> %s", (tab or "chuong").split("/")[-1], k + 1, res)
            if res in ("started", "follow_build_started"):
                started += 1
            ctx.back_out()
            if res == "no_builder" and not q.get("follow", True):
                ctx.ensure_city()
                return started      # het tho: dong khac (tuong, phe tich...) van lam duoc neu bat follow
    ctx.ensure_city()
    return started
