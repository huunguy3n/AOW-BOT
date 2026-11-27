"""P13l (chu du an t100u-t102u): mui ten xanh tren ban do the gioi -> cham MUC TIEU THAT roi lam TAI CHO.

  bang "Phan quan Co giap" -> luong rebels (tu mo tap ket; nha chinh < rebels.min_hq_level -> bo tap ket Co giap)
  bang "Phien quan" / "Tim kiem" -> leo cap (mainquest.npc_search) roi danh le (mainquest.npc_engage: "Tan cong" ->
                 du doan thang -> xuat chinh; thuoc chi "Dung")
  nut "Thu thap" (mo) -> luong gather (cap 8 -> 7 -> 6, trung mo thi doi, khong 2 quan doan 1 mo), 1 quan doan
  menu can cu nguoi choi / o dat trong -> map_menu dong ngay, danh sach den diem do, thu vat the ke (toi da TRIES).
"""
import logging

from bot import map_menu, tapguard, world_target

log = logging.getLogger("aow")

TRIES = 3
TITLE = "rebels/popup_title"


def engage(ctx):
    """-> 'sent' (da gui quan) | 'skip' (mo dung muc tieu nhung luat khong cho danh / het quan) | 'miss' (cham hut het
    luot) | 'none' (khong thay vat the an toan duoi mui ten)."""
    tried = 0
    while tried < TRIES:
        img = ctx.shot()
        if map_menu.dismiss(ctx, img):
            tried += 1
            continue
        t = world_target.pick(img, ctx.v, blocked=lambda x, y: map_menu.blocked(ctx, x, y))
        if t is None:
            return "miss" if tried else "none"
        tried += 1
        log.info("Mui ten xanh: cham muc tieu %s @%d,%d (lan %d/%d)", t.kind, t.x, t.y, tried, TRIES)
        menus = getattr(ctx, "_menu_closed", 0)
        ctx.tap(t.x, t.y, wait=1.8)
        img = ctx.shot()
        if map_menu.dismiss(ctx, img) or getattr(ctx, "_menu_closed", 0) != menus:
            tapguard.of(ctx).ban(map_menu.SCOPE, t.x, t.y, "mui ten xanh: mo menu, khong phai muc tieu")
            continue
        r = handle(ctx, img)
        if r is not None:
            log.info("Mui ten xanh: %s", r)
            return r
        tapguard.of(ctx).ban(map_menu.SCOPE, t.x, t.y, "mui ten xanh: khong ra bang muc tieu")
        ctx.close_popups(1)
    return "miss"


def handle(ctx, img):
    """Bang hien sau khi cham muc tieu -> 'sent' | 'skip' | None (khong phai bang muc tieu)."""
    from bot.modules import mainquest
    title = ctx.v.find(img, TITLE, th=0.8)
    if title:
        return _mech(ctx, img, title)
    if mainquest.npc_popup_action(img, ctx.v):
        return _npc(ctx, img)
    if ctx.v.find(img, map_menu.GATHER):
        return _mine(ctx, img)
    return None


def _close(ctx):
    ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)


def _mech(ctx, img, title):
    from bot.modules import rebels
    rc = ctx.cfg.get("rebels", {})
    if not rebels.join_hq_ok(getattr(ctx, "mem", None), ctx.dev.idx, rc):
        log.info("Mui ten xanh: Phan quan Co giap nhung nha chinh < %s -> bo tap ket", rc.get("min_hq_level", 15))
        _close(ctx)
        return "skip"
    if ctx.march_full():
        log.info("Mui ten xanh: het quan doan ranh -> khong tap ket")
        _close(ctx)
        return "skip"
    _, rec = rebels._mem(ctx)
    return "sent" if rebels.popup_target(ctx, rc, rec, img, title) == 1 else "skip"


def _npc(ctx, img):
    from bot.modules import mainquest
    if ctx.march_full():
        log.info("Mui ten xanh: het quan doan ranh -> khong danh phien quan")
        _close(ctx)
        return "skip"
    p = mainquest.npc_search(ctx)       # co "Tan cong" -> tra ngay; bang "Tim kiem" -> leo cap toi khi co (P13m)
    if not p:
        _close(ctx)
        return "skip"
    return "sent" if mainquest.npc_engage(ctx, ctx.cfg.get("mainquest", {}), p) == "npc_sent" else "skip"


def _mine(ctx, img):
    from bot.modules import gather
    ctx.dev.back()              # dong menu mo (Back tren ban do chi dong menu) roi di theo luong thu thap
    ctx.wait_change(img, 0.8)
    ctx.tap_tpl("common/btn_cancel_exit", wait=0.6)
    if not ctx.cfg.get("modules", {}).get("gather", True) or ctx.march_full():
        log.info("Mui ten xanh: la mo nhung buoc thu thap tat / het quan doan -> bo")
        return "skip"
    return "sent" if gather.run(ctx, limit=1) else "skip"
