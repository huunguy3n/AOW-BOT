"""P9-2 khien SOM ngay thuong (chu du an 2026-11-24, live-run-2: #1 khong co khien, buoc warday/phong thu chua toi
luot thi may treo). Doc lap voi buoc warday: chay ngay sau warday/tutorial, truoc lien minh / cham do / tinh bao.

Ngay thuong, khien dang TAT (icon khien thanh pho xam, observe.read_shield):
  1. Hiep uoc hoa binh dong 8h - MIEN PHI (chi khi co chu 'Mien phi'; dang hoi thi bo qua)
  2. vat pham khien khac (khong ton kim cuong)
  3. mua bang kim cuong TRONG tran defense.gem_cap_daily (2000/ngay; policy.shield_decision kiem tran, ghi gem_ev)
Ngay chien tranh (cua so warday): KHONG lam gi o day - buoc warday giu khien 24h, moi loai khien, khong tran.
Hiep uoc vua dung (chuan bi 1h) -> khong bat/mua them khien trong shield.peace_prep_min phut.
"""
import logging
import time

from aowbot.domain import warday as W

log = logging.getLogger("aow")
SRC = "shield_daily"   # nguon ghi kim cuong (gem_ev) - tinh vao tran ngay thuong (defense.counts_toward_cap)


def scfg(cfg):
    return {"buy_gems": True, "peace_prep_min": 60, **((cfg or {}).get("shield") or {})}


def plan(state, war_window, peace_at, now, prep_min):
    """Ham thuan: co bat khien som khong. -> (True/False, ly do)."""
    if war_window:
        return False, "ngay chien tranh - buoc warday giu khien"
    if state == "on":
        return False, "dang co khien"
    if peace_at and now - peace_at < prep_min * 60:
        return False, f"Hiep uoc hoa binh dang chuan bi (dung {int((now - peace_at) / 60)} phut truoc)"
    if state != "off":
        return False, "khong doc duoc trang thai khien"
    return True, "khien dang tat"


def run(ctx):
    from bot.modules import defense, warday
    c = scfg(ctx.cfg)
    mem, idx, now = getattr(ctx, "mem", None), ctx.dev.idx, time.time()
    ctx.ensure_city()
    win = warday.window(mem, idx, ctx.cfg, now)
    state, _left = warday.screen_shield(ctx)
    peace_at = warday._num(mem.fact(idx, "peace_at")) if mem else None
    go, why = plan(state, win is not None, peace_at, now, c["peace_prep_min"])
    if not go:
        log.info("Khien som: %s - bo qua", why)
        return 0
    log.warning("Khien som: KHIEN DANG TAT -> Hiep uoc mien phi > vat pham > kim cuong (tran %s/ngay)",
                (ctx.cfg.get("defense") or {}).get("gem_cap_daily", 0))
    for hours, buy in W.daily_shield_options(bool(c["buy_gems"])):
        if hours == 8:
            res = defense.peace(ctx, skip_if_active=True)
            if res == "peace":
                if mem:
                    mem.set_fact(idx, "peace_at", now)
                log.info("Khien som: da dung Hiep uoc hoa binh (mien phi)")
                return 1
        else:
            res = defense.shield(ctx, hours=hours, allow_buy=buy, src=SRC)
            if res == "shielded":
                if mem:
                    mem.set_fact(idx, "shield_daily_at", now)
                return 1
        if res == "active":
            log.info("Khien som: bang bao ho cho biet dang con khien")
            return 0
        if res == "missing_tpl":
            log.warning("Khien som: thieu anh mau - dung")
            return 0
        log.info("Khien som: %s %dh -> %s, thu cach ke", "mua" if buy else ("Hiep uoc" if hours == 8 else "vat pham"),
                 hours, res)
    log.error("Khien som: KHONG BAT DUOC KHIEN (het Hiep uoc / vat pham / kim cuong trong tran)")
    return 0
