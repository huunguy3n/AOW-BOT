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
    return {"buy_gems": True, "peace_prep_min": 60, "renew_below_min": 60, **((cfg or {}).get("shield") or {})}


def _hm(sec):
    return f"{int(sec) // 3600}h{int(sec) % 3600 // 60:02d}"


def plan(state, war_window, peace_at, now, prep_min, left=None, renew_min=60):
    """Ham thuan: co bat / gia han khien som khong. -> (True/False, ly do).
    P10-7 (live3: bat 1h luc dau luot, cuoi luot 'CO con 0h35' -> tat truoc lan ghe sau): khien dang BAT nhung con
    < renew_min phut (doc duoc gio) -> gia han; con >= renew_min hoac khong doc duoc gio -> khong bat chong."""
    if war_window:
        return False, "ngay chien tranh - buoc warday giu khien"
    if peace_at and now - peace_at < prep_min * 60:
        return False, f"Hiep uoc hoa binh dang chuan bi (dung {int((now - peace_at) / 60)} phut truoc)"
    if state == "on":
        if left is None:
            return False, "dang co khien (khong doc duoc gio con lai - khong bat chong)"
        if left >= renew_min * 60:
            return False, f"dang co khien con {_hm(left)} >= {renew_min} phut"
        return True, f"khien con {_hm(left)} < {renew_min} phut - gia han"
    if state != "off":
        return False, "khong doc duoc trang thai khien"
    return True, "khien dang tat"


def peace_ok_for_renew(left, prep_min):
    """Ham thuan: gia han bang Hiep uoc (chuan bi prep_min phut, KHONG bao ho trong luc chuan bi) chi khi khien hien tai
    con du de phu het thoi gian chuan bi - khong de ho (learning 2026-11-23: Hiep uoc giua chung -> ho 1h)."""
    return left is not None and left >= prep_min * 60


def run(ctx):
    from bot.modules import defense, warday
    c = scfg(ctx.cfg)
    mem, idx, now = getattr(ctx, "mem", None), ctx.dev.idx, time.time()
    ctx.ensure_city()
    win = warday.window(mem, idx, ctx.cfg, now)
    state, left = warday.screen_shield(ctx)
    peace_at = warday._num(mem.fact(idx, "peace_at")) if mem else None
    go, why = plan(state, win is not None, peace_at, now, c["peace_prep_min"], left, c["renew_below_min"])
    if not go:
        log.info("Khien som: %s - bo qua", why)
        return 0
    renew = state == "on"
    log.warning("Khien som: %s -> Hiep uoc mien phi > vat pham > kim cuong (tran %s/ngay)",
                why.upper() if not renew else why, (ctx.cfg.get("defense") or {}).get("gem_cap_daily", 0))
    for hours, buy in W.daily_shield_options(bool(c["buy_gems"])):
        if hours == 8:
            if renew and not peace_ok_for_renew(left, c["peace_prep_min"]):
                log.info("Khien som: bo Hiep uoc khi gia han - chuan bi %d phut > khien con %s (se ho)",
                         c["peace_prep_min"], _hm(left or 0))
                continue
            res = defense.peace(ctx, skip_if_active=not renew)
            if res == "peace":
                if mem:
                    mem.set_fact(idx, "peace_at", now)
                log.info("Khien som: da dung Hiep uoc hoa binh (mien phi)")
                return 1
        else:
            res = defense.shield(ctx, hours=hours, allow_buy=buy, src=SRC, extend=renew)
            if res == "shielded":
                if mem:
                    mem.set_fact(idx, "shield_daily_at", now)
                return 1
        if res == "active" and not renew:
            log.info("Khien som: bang bao ho cho biet dang con khien")
            return 0
        if res == "missing_tpl":
            log.warning("Khien som: thieu anh mau - dung")
            return 0
        log.info("Khien som: %s %dh -> %s, thu cach ke", "mua" if buy else ("Hiep uoc" if hours == 8 else "vat pham"),
                 hours, res)
    log.error("Khien som: KHONG %s DUOC KHIEN (het Hiep uoc / vat pham / kim cuong trong tran)",
              "GIA HAN" if renew else "BAT")
    return 0
