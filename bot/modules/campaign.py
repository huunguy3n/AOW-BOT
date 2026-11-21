"""Chien dich (nhiem vu "Hoan tat Chien dich N"): danh cac man ke tiep + nhan Loi ich treo may.

Luong (540x960): icon "Chien dich" ben trai thanh pho -> "Khieu chien" -> bang man (du doan ket qua)
-> "Tan cong" -> doi hinh -> "Chien dau" -> tran tu danh (~35s) -> "Thang toan dien" -> "Dong".
An toan: chi danh khi bang man du doan "Thang toan dien" (campaign.only_predicted_win), thua thi dung.
"""
import cv2
import time, logging

log = logging.getLogger("aow")


def claim_idle(ctx):
    if ctx.tap_tpl("campaign/btn_idle_claim", wait=1.5, dy=-60):  # chu "Nhan" duoi ruong treo may
        if ctx.tap_tpl("campaign/btn_idle_get", wait=1.5):
            ctx.dismiss_reward()
            log.info("Da nhan Loi ich treo may")
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)


def predicted_win(v, img):
    """Man doi hinh co du doan "Thang toan dien" (chu XANH tren nut Chien dau)?
    Anh mau chi khop 0,77-0,79 tren #1 (2026-11-21) < nguong 0,82 -> bot tuong "khong du doan thang" va THOAT ra
    du da thang ("vi sao he thong luon out ra?"). Nay: anh mau >= 0,7 HOAC >= 60 diem chu xanh trong vung chu."""
    b = v.best(img, "campaign/pred_win", roi=(100, 820, 340, 100))
    if b and b[2] >= 0.7:
        return True
    hsv = cv2.cvtColor(img[850:900, 140:400], cv2.COLOR_BGR2HSV)
    g = (hsv[..., 0] >= 45) & (hsv[..., 0] <= 75) & (hsv[..., 1] >= 150) & (hsv[..., 2] >= 150)
    return int(g.sum()) >= 60


def auto_formation(ctx):
    """Bam "Tu xep doi hinh" (goc duoi phai) neu co -> True."""
    if ctx.tap_tpl("tutorial/btn_auto_formation", wait=1.5, th=0.8, roi=(440, 860, 100, 100)):
        log.info("Doi hinh: bam tu xep (toi uu)")
        return True
    return False


def fight_one(ctx, only_win):
    """'win' | 'lose' | 'skip' (du doan khong thang) | 'error'"""
    if not ctx.tap_tpl("campaign/btn_challenge", wait=1.5):
        return "error"
    if not ctx.wait_for("campaign/btn_attack", timeout=4):
        return "error"
    auto_formation(ctx)
    if only_win and not predicted_win(ctx.v, ctx.shot()):
        log.info("Man ke tiep khong du doan thang - dung")
        ctx.save_debug("campaign_pred")
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
        return "skip"
    ctx.tap_tpl("campaign/btn_attack", wait=2.0, fresh=False)
    return battle(ctx)


def close_result(ctx):
    """Dong man ket qua tran (thang: 'Dong' giua; thua: 'Dong' trai - KHONG bam 'Bat dau lai')."""
    for _ in range(4):
        time.sleep(1.2)  # man ket qua con hieu ung -> nut chua nhan cham ngay
        if not ctx.tap_first(["campaign/btn_done", "campaign/btn_done_lose"], wait=1.5):
            break
    ctx.dismiss_reward()


def battle(ctx, only_win=True):
    """Tu man doi hinh (nut "Chien dau") -> danh -> dong man ket qua. Dung chung cho Tinh bao."""
    # nut "Tu xep doi hinh" (goc duoi phai) LUON bam truoc khi danh (chu du an 2026-11-21 #1: "chua bam toi uu!!!",
    # doi hinh chi 3 tuong, 1 tuong Lv.1) -> du doan thang/thua tinh theo doi hinh da toi uu
    auto_formation(ctx)
    if only_win and ctx.find("campaign/btn_fight") and not predicted_win(ctx.v, ctx._img):
        log.info("Doi hinh khong du doan thang - bo")
        ctx.back_out(2)
        return "skip"
    if not ctx.tap_tpl("campaign/btn_fight", wait=0.5):
        if not ctx.wait_for("campaign/btn_fight", timeout=5):
            return "error"
        ctx.tap_tpl("campaign/btn_fight", wait=0.5, fresh=False)
    if ctx.cfg.get("battle", {}).get("steer", True):
        # tran kieu chay duong: giu ngon tay tren doi quan, nhat buff / ne nerf / ne vung tan cong
        from bot import steer
        r = steer.run_battle(ctx.dev.adb, ctx.dev.serial, ctx.v,
                             debug_dir=ctx.cfg.get("battle", {}).get("debug_dir"))
        if r in ("win", "lose"):
            if r == "lose":
                ctx.save_debug("campaign_result")
            close_result(ctx)
            return r
    t0 = time.time()
    while time.time() - t0 < 180:  # tran tu danh
        img = ctx.shot()
        if ctx.v.find(img, "campaign/btn_done") or ctx.v.find(img, "campaign/btn_done_lose"):
            from bot.steer import result_of
            win = result_of(ctx.v, img) == "win"
            if not win:
                ctx.save_debug("campaign_result")
            close_result(ctx)
            return "win" if win else "lose"
        time.sleep(3)
    ctx.save_debug("campaign_timeout")
    return "error"


def run(ctx):
    cc = ctx.cfg.get("campaign", {})
    ctx.ensure_city()
    if not ctx.tap_tpl("campaign/btn_open", wait=2.5) or not ctx.wait_for("campaign/title", timeout=4):
        log.info("Khong mo duoc Chien dich")
        return 0
    claim_idle(ctx)
    wins = 0
    for _ in range(cc.get("max_fights", 5)):
        r = fight_one(ctx, cc.get("only_predicted_win", True))
        log.info("Chien dich: %s", r)
        if r != "win":
            break
        wins += 1
    ctx.back_out()
    ctx.ensure_city()
    return wins
