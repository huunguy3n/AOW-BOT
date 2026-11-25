"""P9-2 khien SOM ngay thuong (chu du an 2026-11-24, live-run-2: #1 khong co khien, buoc warday/phong thu chua toi
luot thi may treo). Doc lap voi buoc warday: chay ngay sau warday/tutorial, truoc lien minh / cham do / tinh bao.

Ngay thuong, khien dang TAT (icon khien thanh pho xam, observe.read_shield):
  1. Hiep uoc hoa binh dong 8h - MIEN PHI (chi khi co chu 'Mien phi'; dang hoi thi bo qua)
  2. vat pham khien khac (khong ton kim cuong)
  3. mua bang kim cuong TRONG tran defense.gem_cap_daily (2000/ngay; policy.shield_decision kiem tran, ghi gem_ev)
Ngay chien tranh (cua so warday): KHONG lam gi o day - buoc warday giu khien 24h, moi loai khien, khong tran.
P12-1: Hiep uoc chuan bi 1h KHONG bao ho -> dung Hiep uoc xong ma khien chua bat (hoac Hiep uoc dang chuan bi /
hoi chieu) thi dung vat pham khien ngay (1h, 12h, 3d), het moi mua trong tran.
"""
import logging
import time

from aowbot.domain import warday as W

log = logging.getLogger("aow")
PEACE_STATUS = {"peace": "vua dung (chuan bi 1h)", "cooldown": "HOI CHIEU", "preparing": "CHUAN BI",
                "active": "dang bao ho", "error": "loi"}
SRC = "shield_daily"   # nguon ghi kim cuong (gem_ev) - tinh vao tran ngay thuong (defense.counts_toward_cap)


def scfg(cfg):
    return {"buy_gems": True, "peace_prep_min": 60, "renew_below_min": 60, **((cfg or {}).get("shield") or {})}


def _hm(sec):
    return f"{int(sec) // 3600}h{int(sec) % 3600 // 60:02d}"


def peace_preparing(peace_at, now, prep_min):
    """Ham thuan: Hiep uoc vua dung trong prep_min phut -> dang 'chuan bi' (CHUA bao ho)."""
    return bool(peace_at) and now - peace_at < prep_min * 60


def plan(state, war_window, peace_at, now, prep_min, left=None, renew_min=60):
    """Ham thuan: co bat / gia han khien som khong. -> (True/False, ly do).
    P10-7 (live3: bat 1h luc dau luot, cuoi luot 'CO con 0h35' -> tat truoc lan ghe sau): khien dang BAT nhung con
    < renew_min phut (doc duoc gio) -> gia han; con >= renew_min hoac khong doc duoc gio -> khong bat chong.
    P12-1 (live4: #0/#2-#6 bam Hiep uoc dau luot, 'chuan bi' 17-28 phut, cuoi luot khien TAT): Hiep uoc dang chuan bi
    KHONG phai la khien -> khien tat thi van bat ngay bang vat pham (bo dong Hiep uoc)."""
    if war_window:
        return False, "ngay chien tranh - buoc warday giu khien"
    if state == "on":
        if left is None:
            return False, "dang co khien (khong doc duoc gio con lai - khong bat chong)"
        if left >= renew_min * 60:
            return False, f"dang co khien con {_hm(left)} >= {renew_min} phut"
        return True, f"khien con {_hm(left)} < {renew_min} phut - gia han"
    if state != "off":
        return False, "khong doc duoc trang thai khien"
    if peace_preparing(peace_at, now, prep_min):
        return True, (f"khien dang tat, Hiep uoc dang chuan bi (dung {int((now - peace_at) / 60)} phut truoc, "
                      "chua bao ho) - dung vat pham ngay")
    return True, "khien dang tat"


def peace_ok_for_renew(left, prep_min):
    """Ham thuan: gia han bang Hiep uoc (chuan bi prep_min phut, KHONG bao ho trong luc chuan bi) chi khi khien hien tai
    con du de phu het thoi gian chuan bi - khong de ho (learning 2026-11-23: Hiep uoc giua chung -> ho 1h)."""
    return left is not None and left >= prep_min * 60


def options(renew, left, preparing, prep_min, buy_gems):
    """Ham thuan P12-1: thu tu thu khien ngay thuong -> [(gio, mua)]. Dong 8h (Hiep uoc) bi bo khi Hiep uoc dang chuan
    bi (dung lai vo ich) hoac khi gia han ma khien con < thoi gian chuan bi (se ho)."""
    opts = W.daily_shield_options(bool(buy_gems))
    if preparing or (renew and not peace_ok_for_renew(left, prep_min)):
        opts = [o for o in opts if o[0] != 8]
    return opts


def run(ctx):
    """P13-4 (chu du an t59u/t60u, ghi de P10/P12): ngay thuong CHI bat khien bang Hiep uoc hoa binh 8h MIEN PHI san dung.
    KHONG dung vat pham khien, KHONG kim cuong, KHONG bat moi lan dang nhap: khien dang bat / Hiep uoc dang chuan bi /
    hoi chieu -> bo qua. Ngay chien tranh (thu 7 co huy hieu) do buoc warday lo."""
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
    if state == "on":
        log.info("Khien som: khien con %s - khong gia han bang vat pham / kim cuong (luat P13-4)", _hm(left or 0))
        return 0
    if peace_preparing(peace_at, now, c["peace_prep_min"]):
        log.info("Khien som: Hiep uoc dang chuan bi - KHONG dung vat pham / kim cuong (luat P13-4), cho bao ho")
        return 0
    res = defense.peace(ctx, skip_if_active=True)
    log.info("Khien som: Hiep uoc hoa binh mien phi -> %s", PEACE_STATUS.get(res, res))
    if res == "peace":
        if mem:
            mem.set_fact(idx, "peace_at", now)
        return 1
    log.info("Khien som: khong co Hiep uoc 8h mien phi san dung - KHONG bat khien (khong vat pham, khong kim cuong)")
    return 0
