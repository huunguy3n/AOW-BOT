"""Ngay chien tranh SVS + moc the luc (chu du an 2026-11-21). Luat thuan: aowbot.domain.warday.

- sniff(ctx): thay bang thong bao "phoi hop chien tranh" (anh mau warday/notice.png) -> nho `war_notice_seen`;
  thu 7 (UTC) ke tu ngay thay la ngay chien tranh. Co the khai tay: warday.dates: ["YYYY-MM-DD"].
- run(ctx): trong cua so chien tranh (thu 6 22h UTC -> het thu 7) bao dam co khien: 8h luc 22h UTC thu 6, het thi
  12h, sap het 12h ma chua qua ngay thi bat tiep 12h. Chi dung VAT PHAM khien (warday.buy_gems mac dinh false).
  Cung ghi nhan lan ghe nhan the luc o moc 0h/8h/15h UTC (viec nhan do notify/rewards lam trong cung lan ghe).
Cam thu thap (phan quan duoc phep) trong cua so: scheduler.plan_step + runner (BLOCK_STEPS).
"""
import time, logging
from aowbot.domain import warday as W

log = logging.getLogger("aow")
TPL_NOTICE = "warday/notice"


def wcfg(cfg):
    return {"enabled": True, "stamina": True, "lead_h": 2, "renew_before_min": 20, "stamina_delay_min": 1,
            "buy_gems": False, "dates": [], **(cfg.get("warday") or {})}


def days_for(mem, idx, cfg, now=None):
    c = wcfg(cfg)
    seen = mem.fact(idx, "war_notice_seen") if mem else None
    return W.war_days(seen, c["dates"], now)


def sniff(ctx, img=None):
    """Co bang thong bao phoi hop chien tranh tren man hinh khong -> ghi nho. Goi truoc khi dong popup."""
    if not wcfg(ctx.cfg)["enabled"] or not ctx.v.has(TPL_NOTICE):
        return False
    img = img if img is not None else ctx.shot()
    if not ctx.v.find(img, TPL_NOTICE):
        return False
    now = time.time()
    s = W.war_saturday(now)
    if getattr(ctx, "mem", None) and s is not None:
        ctx.mem.set_fact(ctx.dev.idx, "war_notice_seen", now)
        log.info("Thay bang thong bao phoi hop chien tranh -> ngay chien tranh = %s UTC",
                 time.strftime("%d/%m/%Y", time.gmtime(s)))
    return s is not None


def _shield_until(ctx):
    """Dong ho khien doc truc tiep tren man hinh (chinh xac hon fact cu) -> epoch | None (khong co khien)."""
    from bot.modules import observe
    sh = observe.read_shield(ctx.shot())
    return time.time() + sh["left"] if sh.get("left") else None


def run(ctx):
    c = wcfg(ctx.cfg)
    if not c["enabled"]:
        return 0
    mem, idx, now = getattr(ctx, "mem", None), ctx.dev.idx, time.time()
    ctx.ensure_city()
    sniff(ctx)
    if c["stamina"] and mem and W.stamina_due(now, mem.fact(idx, "stamina_claim_at"), c["stamina_delay_min"]):
        mem.set_fact(idx, "stamina_claim_at", now)
        log.info("Moc the luc %s UTC: nhan qua online/phuc loi (notify, rewards) trong lan ghe nay",
                 time.strftime("%H:%M", time.gmtime(W.last_stamina_mark(now))))
    days = days_for(mem, idx, ctx.cfg, now)
    plan = W.shield_plan(now, days, _shield_until(ctx), c["lead_h"], c["renew_before_min"])
    if plan.hours is None:
        log.info("Ngay chien tranh: %s", plan.why)
        return 0
    from bot.modules import defense
    log.info("Ngay chien tranh: %s", plan.why)
    res = defense.shield(ctx, hours=plan.hours, allow_buy=bool(c["buy_gems"]), extend=True)
    if res != "shielded":
        log.warning("Khong bat duoc khien %dh ngay chien tranh (%s)", plan.hours, res)
        return 0
    if mem:
        mem.set_fact(idx, "war_shield_at", now)
    return 1
