"""P13-11 (chu du an, anh bien_gioi_keo_vong / bien_gioi_icon_mo_khoa, t74u): MO RONG THANH PHO.

Quanh thanh pho co vien sang (ranh gioi lo dat chua mo). Moi lan dang nhap: keo camera doc vien sang (luot vong quanh
thanh pho nhu tim nha chinh); thay icon O KHOA MO (templates/build/plot_unlock.png) -> bam de lam nhiem vu mo rong.
Ngoai ra hang nhiem vu "mo rong thanh pho" tren thanh nhiem vu / bang nhiem vu (quest_rules 'expand') danh dau
`expand_pending` -> buoc nay chay ngay cung lan ghe, khong cho het khoang `expand.min_interval_min`.
An toan: hop thoai sau khi bam icon CHI bam nut co chu Den / Nhay / Mo rong / Xay dung (buttons.with_text da loc Mua / Nap /
Mo khoa tra phi / kim cuong / tang toc); khong tim thay -> luu anh logs/inv/plot_unlock_dialog va dong. Khong bao gio bam
nut co gia / kim cuong. Chua kiem tren may that (khong co khung ADB hop thoai).

P13m (chu du an t106u, anh expand_city_rebel_tile): con duong mo rong thu hai - PHIEN QUAN dung tren o do trong thanh
(linh minh o o xanh lam ben canh). Bam THAN con quan (guide_tile.find_rebel), danh qua cong du doan "Thang toan dien".
Dung chung cho buoc nay (quet vien thanh), mainquest (nhiem vu "Kich sat ... phan quan") va tutorial / follow.
"""
import logging
import os
import time

import cv2

from bot import build, buttons, guide_tile, tapguard

log = logging.getLogger("aow")
LOG_REBEL = "mo rong lanh tho: danh phien quan o"
REBEL_WHY = "o do duoi chan muc tieu: phien quan (mo rong lanh tho)"      # ly do trong tutorial.decide
CITY_MARKS = (guide_tile.CITY, "build/icon_hammer")        # nut ban do / icon bua: dang o thanh pho
ATTACK_BUTTONS = ("tutorial/btn_attack_red", "campaign/btn_attack", "intel/btn_attack")
FIGHT_LOOKS = 7                                            # so khung cho bang / man doi hinh sau khi cham
UNLOCK_TPL = "build/plot_unlock"
ROI = (30, 130, 480, 760)               # vung thanh pho khong bi HUD che
ACT_RX = r"\b(den|nhay|mo rong|xay dung)\b"
DIALOG_ROI = (0, 150, 540, 800)


def scfg(cfg):
    return {"enabled": True, "min_interval_min": 240, "ring": True, **((cfg or {}).get("expand") or {})}


def due(last_at, pending_at, now, interval_min):
    """Ham thuan: co chay buoc mo rong thanh pho khong. -> (bool, ly do)."""
    if pending_at and (not last_at or pending_at > last_at):
        return True, "co nhiem vu mo rong thanh pho (thanh / bang nhiem vu)"
    if not last_at or now - last_at >= interval_min * 60:
        return True, "quet vien thanh pho dinh ky"
    return False, f"vua quet {(now - last_at) / 60:.0f} phut truoc"


def find_unlock(v, img):
    """Ham thuan: icon o khoa MO tren thanh pho -> (x, y) | None."""
    p = v.find(img, UNLOCK_TPL, th=0.8, roi=ROI)
    return (p[0], p[1]) if p else None


def find_rebel(v, img, blocked=None):
    """Ham thuan: dang o thanh pho va co phien quan tren o do -> guide_tile.Guide(than con quan, 'rebel') | None."""
    if not hasattr(img, "shape") or not any(v.find(img, n, th=0.85) for n in CITY_MARKS):
        return None
    return guide_tile.find_rebel(img, blocked)


def _formation(v, img):
    """Man doi hinh (co cong du doan thang)?"""
    from bot.modules import campaign
    return bool(v.find(img, "campaign/btn_fight", th=0.8) or v.find(img, "tutorial/btn_auto_formation", th=0.85)
                or campaign.legion_screen(v, img))


def _gated_fight(ctx):
    """Man doi hinh: toi uu doi hinh -> CHI danh khi du doan "Thang toan dien". -> 'win' | 'lose' | 'skip' | 'error'."""
    from bot.modules import campaign
    campaign.auto_formation(ctx)
    if campaign.legion_screen(ctx.v, ctx.shot()):
        ctx.tap_tpl(campaign.LEGION_RECOMMEND, wait=1.5, th=0.85, roi=campaign.LEGION_ROI)
    if not campaign.predicted_win(ctx.v, ctx.shot()):
        log.info("Mo rong lanh tho: khong du doan thang -> khong danh")
        ctx.back_out(2)
        return "skip"
    return campaign.battle(ctx, only_win=True, pre_checked=True)


def fight_rebel(ctx, hit):
    """Bam than phien quan tren o do -> danh qua cong du doan thang.
    -> 'win' | 'lose' | 'skip' (luat khong cho danh) | 'error' | 'sent' (man quan doan, da xuat chinh) |
    'opened' (man da doi sang thu khac: de lam theo huong dan game) | 'miss' (cham khong doi man).
    Ket qua khac 'win' / 'opened' / 'sent' -> toa do vao danh sach den toi het luot ghe."""
    from bot.modules import mainquest
    log.info(LOG_REBEL)
    ctx.tap(hit.x, hit.y, wait=2.0)
    r, pressed, still = None, False, True
    for k in range(FIGHT_LOOKS):
        img = ctx.shot()
        if _formation(ctx.v, img):
            r = _gated_fight(ctx)
            break
        attack = mainquest.find_attack(img, ctx.v)
        if attack and mainquest.is_npc_popup(img):  # bang "Phien quan Lv.N": kiem cap / luc chien / du doan thang
            sent = mainquest.npc_engage(ctx, ctx.cfg.get("mainquest", {}), attack)
            r = {"npc_sent": "sent", "npc_none": "error"}.get(sent, "skip")
            break
        p = attack or next((q for q in (ctx.v.find(img, n, th=0.85) for n in ATTACK_BUTTONS) if q), None)
        if p and not pressed:
            ctx.tap(p[0], p[1], wait=2.0)
            pressed = True
            continue
        now = find_rebel(ctx.v, img)
        still = bool(now) and abs(now.x - hit.x) <= guide_tile.NEAR and abs(now.y - hit.y) <= guide_tile.NEAR
        if k + 1 < FIGHT_LOOKS:                     # man doi hinh tai cham: cho du so khung
            time.sleep(0.8)
    if r is None:
        r = "miss" if still and not pressed else "opened"
    log.info("Mo rong lanh tho: phien quan @%d,%d -> %s", hit.x, hit.y, r)
    if r not in ("win", "opened", "sent"):
        tapguard.of(ctx).ban("guide", hit.x, hit.y, "phien quan tren o do -> " + r)
    return r


def try_city_rebel(ctx):
    """Man hien tai co phien quan tren o do trong thanh -> danh -> ket qua fight_rebel; khong co -> None."""
    shot = getattr(ctx, "shot", None)
    if shot is None or getattr(ctx, "v", None) is None:
        return None
    hit = find_rebel(ctx.v, shot(), guide_tile.blocked_by(ctx))
    return fight_rebel(ctx, hit) if hit else None


def sweep(ctx, ring=True):
    """Xem man hien tai, roi luot camera quanh thanh pho (vong 8 huong) toi khi thay phien quan tren o do (-> Guide
    'rebel') hoac icon o khoa mo (-> (x, y)). Khong thay -> None."""
    img = ctx.settle()
    pos = (0, 0)
    steps = len(build.PAN_RING) if ring else 0
    for step in range(steps + 1):
        foe = find_rebel(ctx.v, img, guide_tile.blocked_by(ctx))
        if foe:
            return foe
        p = find_unlock(ctx.v, img)
        if p:
            return p
        if step >= steps:
            break
        nx, ny = build.PAN_RING[step]
        ctx.dev.swipe(270, 480, 270 + (nx - pos[0]) * 200, 480 + (ny - pos[1]) * 300, 600)
        pos = (nx, ny)
        img = ctx.settle()
    return None


def open_plot(ctx, p):
    """Bam icon o khoa mo -> hop thoai; chi bam nut Den / Nhay / Mo rong / Xay dung (khong gia, khong kim cuong). -> bool."""
    ctx.tap(p[0], p[1], wait=1.8)
    img = ctx.settle()
    d = os.path.join("logs", "inv", "plot_unlock_dialog")
    os.makedirs(d, exist_ok=True)
    cv2.imwrite(os.path.join(d, time.strftime("%Y%m%d-%H%M%S") + f"-i{ctx.dev.idx}.png"), img)
    for b in buttons.with_text(img, ACT_RX, DIALOG_ROI):
        log.info("Mo rong thanh pho: bam '%s' @%d,%d", b.text[:20], b.x, b.y)
        ctx.tap(b.x, b.y, wait=2.0)
        return True
    log.info("Mo rong thanh pho: hop thoai khong co nut an toan (Den / Nhay / Mo rong / Xay dung) - dong, luu anh")
    ctx.back_out(1)
    return False


def run(ctx):
    c = scfg(ctx.cfg)
    if not c["enabled"]:
        return 0
    m, idx, now = getattr(ctx, "mem", None), ctx.dev.idx, time.time()
    last = m.fact(idx, "expand_last") if m else None
    pend = m.fact(idx, "expand_pending") if m else None
    go, why = due(last, pend, now, c["min_interval_min"])
    if not go:
        log.info("Mo rong thanh pho: bo qua (%s)", why)
        return 0
    ctx.ensure_city()
    log.info("Mo rong thanh pho: %s", why)
    p = sweep(ctx, c["ring"])
    if m:
        m.set_fact(idx, "expand_last", now)
    if not p:
        log.info("Mo rong thanh pho: khong thay icon o khoa mo tren vien thanh pho")
        ctx.back_out()
        ctx.ensure_city()
        return 0
    if isinstance(p, guide_tile.Guide):          # P13m: phien quan tren o do
        r = fight_rebel(ctx, p)
        if r == "opened":
            from bot.modules import tutorial
            tutorial.follow(ctx, 20)
        n = 1 if r in ("win", "sent", "opened") else 0
    else:
        log.info("Mo rong thanh pho: thay icon o khoa mo @%d,%d", p[0], p[1])
        n = 1 if open_plot(ctx, p) else 0
    ctx.back_out()
    ctx.ensure_city()
    return n
