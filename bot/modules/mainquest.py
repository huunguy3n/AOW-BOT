"""Nhiem vu chinh UU TIEN (chay dau tien): cham thanh nhiem vu goc trai duoi thanh pho -> lam theo noi no dan toi.

Thanh nhiem vu (icon quest/banner_icon + chu ben phai) dua camera/man hinh toi viec can lam:
  - man doi hinh ("Chien dau")            -> danh (co lai doi quan)        vd "Mo ruong 6 lanh tho"
  - camera toi muc tieu tren thanh pho    -> cham muc tieu (giua man ~272,445) roi nhu tren
  - menu/man nang cap cong trinh          -> nang cap (bot/build.py, nha chinh <= gioi han)
  - man Chien dich                        -> danh man ke tiep
  - "Nhan thuong" (nhiem vu xong)         -> cham la nhan, dong bang thuong
Khong nhan ra -> quay ra, dung (de buoc khac chay).
"""
import time, logging
from bot import build, ocr
from bot.modules import campaign

log = logging.getLogger("aow")
BANNER = (150, 818)
TARGET = (272, 445)   # muc tieu (vd o do Mo ruong lanh tho) sau khi camera can giua


def _power(ctx):
    return ocr.topbar(ctx.shot()).get("power")


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


def step(ctx, mq):
    ctx.ensure_city()
    if not ctx.find("quest/banner_icon"):
        return "none"
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


def run(ctx):
    mq = ctx.cfg.get("mainquest", {})
    ctx.ensure_city()
    if _blocked(ctx, mq):
        return 0
    m = getattr(ctx, "mem", None)
    until = m.fact(ctx.dev.idx, "mainquest_busy_until") if m else None
    if until and until > time.time():
        log.info("Nhiem vu chinh dang thuc hien (cong trinh dang xay) - xong luc %s, bo qua",
                 time.strftime("%H:%M %d/%m", time.localtime(until)))
        return 0
    done = 0
    losses = 0
    for _ in range(mq.get("max_steps", 6)):
        r = step(ctx, mq)
        log.info("Nhiem vu chinh: %s", r)
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
        if r in ("win", "build_started", "follow_build_started"):
            done += 1
            continue
        break  # thua / bo qua / khong ro -> de cac buoc tang suc manh chay
    ctx.ensure_city()
    return done
