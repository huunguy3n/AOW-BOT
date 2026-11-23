"""Ngay chien tranh SVS + moc the luc + ngay thu thap. Luat thuan: aowbot.domain.warday (lich tuan su kien).

Chu du an 2026-11-23 (thay luat khien 8h/12h, chi vat pham cua 2026-11-21):
- Thu 7 = ngay chien tranh (lich `warday.weekdays` + gio reset `warday.reset_hour_utc`, cong tac tay `warday.mode`
  auto/on/off tren web, bang thong bao warday/notice, banner 'Giai doan N' tuy chon). Giu khien LIEN TUC ca ngay:
  Hiep uoc hoa binh (mien phi, chuan bi 1h) truoc gio G, sau do khien tuc thi - vat pham truoc, het thi MUA bang
  kim cuong KHONG gioi han (`warday.buy_gems`, `warday.gem_cap` null). Moi lan mua ghi log + so kim cuong (gem_ev).
- Khong chac -> giu khien: cua so mo som `lead_h`, dong muon `tail_min`; khong doc duoc dong ho khien thi dung han
  da ghi luc bat; man hinh bao 'chua bao ho' thi bat lai.
- Cam thu thap trong cua so (phan quan duoc phep): scheduler.plan_step + runner (BLOCK_STEPS).
- Ghi nhan lan ghe nhan the luc o moc 0h/8h/15h UTC (viec nhan do notify/rewards lam trong cung lan ghe).
"""
import logging
import time

from aowbot.domain import warday as W
from bot import ocr

log = logging.getLogger("aow")
TPL_NOTICE = "warday/notice"
BANNER_ROI = (150, 120, 240, 30)     # 'Giai doan N: ...' tren ban do the gioi - UOC LUONG tu anh dien thoai, chua kiem


def wcfg(cfg):
    return W.wcfg((cfg or {}).get("warday"))


def _num(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def facts(mem, idx):
    """(bang thong bao, banner) da thay -> epoch | None."""
    if not mem:
        return None, None
    return _num(mem.fact(idx, "war_notice_seen")), _num(mem.fact(idx, "war_banner_seen"))


def days_for(mem, idx, cfg, now=None):
    now = now or time.time()
    notice, banner = facts(mem, idx)
    return W.resolve_days(wcfg(cfg), notice, now, banner)


def window(mem, idx, cfg, now=None):
    """Cua so chien tranh dang mo (WarWindow) | None - dung cho defense (mua khong gioi han) va lich."""
    now = now or time.time()
    notice, banner = facts(mem, idx)
    return W.window_now(wcfg(cfg), notice, now, banner)


def sniff(ctx, img=None):
    """Co bang thong bao phoi hop chien tranh (hoac banner 'Giai doan N' neu bat banner_ocr) -> ghi nho."""
    c = wcfg(ctx.cfg)
    if not c["enabled"]:
        return False
    img = img if img is not None else ctx.shot()
    now = time.time()
    hit = None
    if ctx.v.has(TPL_NOTICE) and ctx.v.find(img, TPL_NOTICE):
        hit = "war_notice_seen"
    elif c["banner_ocr"] and W.banner_is_war(ocr.text(img, BANNER_ROI)):
        hit = "war_banner_seen"
    if not hit:
        return False
    s = W.war_saturday(now)
    if getattr(ctx, "mem", None) and s is not None:
        ctx.mem.set_fact(ctx.dev.idx, hit, now)
        log.info("Thay %s -> ngay chien tranh = %s UTC", "bang thong bao chien tranh" if hit == "war_notice_seen"
                 else "banner 'Giai doan N'", time.strftime("%d/%m/%Y", time.gmtime(s)))
    return s is not None


def screen_shield(ctx):
    """Dong ho khien tren man hinh -> (trang thai 'on'/'off'/None, giay con lai | None)."""
    from bot.modules import observe
    try:
        sh = observe.read_shield(ctx.shot())
    except Exception as e:   # noqa: BLE001 - khong doc duoc thi dung han da ghi (an toan hon doan)
        log.debug("doc khien loi: %s", e)
        return None, None
    return sh.get("state"), sh.get("left")


def known_until(state, left, recorded, now):
    """Han khien dang biet (ham thuan). Man hinh 'off' -> khong co khien (bat lai, ke ca khi da ghi). 'on' doc duoc
    gio -> dung gio do. Con lai (khong doc duoc) -> han da ghi luc bat neu con hieu luc."""
    if state == "off":
        return None
    if state == "on" and left:
        return now + left
    return recorded if recorded and recorded > now else None


def run(ctx):
    c = wcfg(ctx.cfg)
    if not c["enabled"]:
        return 0
    mem, idx, now = getattr(ctx, "mem", None), ctx.dev.idx, time.time()
    ctx.ensure_city()
    sniff(ctx)
    if c["stamina"] and mem and W.stamina_due(now, _num(mem.fact(idx, "stamina_claim_at")), c["stamina_delay_min"]):
        mem.set_fact(idx, "stamina_claim_at", now)
        log.info("Moc the luc %s UTC: nhan qua online/phuc loi (notify, rewards) trong lan ghe nay",
                 time.strftime("%H:%M", time.gmtime(W.last_stamina_mark(now))))
    if c["timed_login"] and mem and W.timed_login_due(now, _num(mem.fact(idx, "timed_login_at")),
                                                       c["timed_login_windows_utc"], c["timed_login_delay_min"]):
        mem.set_fact(idx, "timed_login_at", now)      # P7-11: lan ghe trong khung -> qua 5 the luc (notify, rewards)
        log.info("Dang nhap hen gio (khung %s UTC): ghe nhan 5 the luc trong lan ghe nay",
                 time.strftime("%H:%M", time.gmtime(W.login_window(now, c["timed_login_windows_utc"])[0])))
    days = days_for(mem, idx, ctx.cfg, now)
    if W.active_window(now, days, c["lead_h"], c["tail_min"]) is None:
        log.info("Ngay chien tranh: %s", W.shield_plan(now, days, None, c).why)
        return 0
    return ensure(ctx, c, days, now)


def ensure(ctx, c, days, now, why=""):
    """Trong cua so chien tranh: bao dam co khien theo W.shield_plan. -> 1 neu da bat (Hiep uoc / khien)."""
    from bot.modules import defense
    mem, idx = getattr(ctx, "mem", None), ctx.dev.idx
    state, left = screen_shield(ctx)
    recorded = _num(mem.fact(idx, "war_shield_until")) if mem else None
    peace_at = _num(mem.fact(idx, "peace_at")) if mem else None
    plan = W.shield_plan(now, days, known_until(state, left, recorded, now), c, peace_at)
    log.info("Ngay chien tranh%s: %s", why, plan.why)
    if plan.action == "peace":
        if defense.peace(ctx) == "peace":
            if mem:
                mem.set_fact(idx, "peace_at", now)
                mem.set_fact(idx, "war_shield_at", now)
            return 1
        log.warning("Khong dung duoc Hiep uoc hoa binh -> se bat khien tuc thi sat gio chien tranh")
        return 0
    if plan.action != "shield":
        return 0
    hours = defense.war_shield(ctx, plan.need_s, bool(c["buy_gems"]), c["gem_cap"])
    if not hours:
        log.error("NGAY CHIEN TRANH: KHONG BAT DUOC KHIEN (thu moi dong khien) - can cu co the bi tan cong")
        return 0
    if mem:
        mem.set_fact(idx, "war_shield_until", max(now, time.time()) + hours * 3600)
        mem.set_fact(idx, "war_shield_at", now)
    return 1


def gather_day(cfg, now=None):
    """Thu 2 = ngay thu thap (chu du an 2026-11-23): runner dua gather len dau, gather khong de danh doi phan quan."""
    return W.is_gather_day(wcfg(cfg), now or time.time())
