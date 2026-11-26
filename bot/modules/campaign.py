"""Chien dich (nhiem vu "Hoan tat Chien dich N"): danh cac man ke tiep + nhan Loi ich treo may.

Luong (540x960): icon "Chien dich" ben trai thanh pho -> "Khieu chien" -> bang man (du doan ket qua)
-> "Tan cong" -> doi hinh -> "Chien dau" -> tran tu danh (~35s) -> "Thang toan dien" -> "Dong".
An toan: chi danh khi bang man du doan "Thang toan dien" (campaign.only_predicted_win), thua thi dung.
"""
import cv2
import time, logging

log = logging.getLogger("aow")


def claim_idle(ctx):
    """-> True neu da nhan Loi ich treo may (P4: tinh la lam duoc viec, truoc chi dem tran thang -> 14/14 lan tra 0)."""
    got = False
    if ctx.tap_tpl("campaign/btn_idle_claim", wait=1.5, dy=-60):  # chu "Nhan" duoi ruong treo may
        if ctx.tap_tpl("campaign/btn_idle_get", wait=1.5):
            ctx.dismiss_reward()
            log.info("Da nhan Loi ich treo may")
            got = True
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
    return got


# P4 (anh logs/shots/*campaign_no_fight* 22/11: 8/8 anh): sau "Tan cong" game mo man "Cai dat quan doan" kieu moi -
# nut xanh "Doi hinh de xuat" (166,921) + nut do "Chien dau" (373,921), giong Dau truong/Cuop boc. Anh mau cu
# campaign/btn_fight chi khop 0,77 -> bot cho 12 s roi 'error'. Dung lai anh mau cua play (khop 1,00 tren ca 8 anh).
LEGION_FIGHT = "play/btn_arena_fight"
LEGION_RECOMMEND = "play/btn_arena_recommend"
LEGION_ROI = (0, 860, 540, 100)


def legion_screen(v, img):
    """Man "Cai dat quan doan" (Doi hinh de xuat + Chien dau do)? -> toa do nut Chien dau hoac None. Ham thuan."""
    return v.find(img, LEGION_FIGHT, th=0.85, roi=LEGION_ROI)


def legion_fight(ctx):
    """Man quan doan kieu moi: LUON bam "Doi hinh de xuat" truoc roi "Chien dau". -> True neu da bam Chien dau."""
    from bot import tplneed
    if not tplneed.has(ctx.v, LEGION_FIGHT, "man Cai dat quan doan cua Chien dich"):
        return False
    if not legion_screen(ctx.v, ctx.shot()):
        return False
    if ctx.tap_tpl(LEGION_RECOMMEND, wait=1.5, th=0.85, roi=LEGION_ROI, fresh=False):
        log.info("Doi hinh: bam Doi hinh de xuat")
    return bool(ctx.tap_tpl(LEGION_FIGHT, wait=0.5, th=0.85, roi=LEGION_ROI))


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
        # khong co nut "Thach dau" = man ke tiep chua mo / dang cho dieu kien -> khong phai loi, bo qua (2026-11-22:
        # 'Chien dich: error' ~8 lan/dem tren #0,#2,#3,#4,#6); luu anh 1 lan / may de xem
        log.info("Chien dich: khong thay nut Thach dau (man ke tiep chua mo) - bo qua")
        ctx.save_debug("campaign_no_challenge")
        return "skip"
    if not ctx.wait_for("campaign/btn_attack", timeout=4):
        return "error"
    auto_formation(ctx)
    if only_win and not predicted_win(ctx.v, ctx.shot()):
        log.info("Man ke tiep khong du doan thang - dung")
        ctx.save_debug("campaign_pred")
        ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
        return "skip"
    ctx.tap_tpl("campaign/btn_attack", wait=2.0, fresh=False)
    return battle(ctx, pre_checked=only_win)


SKIP_ROI = (430, 720, 110, 180)     # nut thoat/bo qua tran (goc phai duoi, duoi nut x2) - anh chien_dich_nut_bo_qua.png
CONTINUE_ROI = (270, 420, 270, 130)  # man 'Thang loi': nut 'Tiep tuc Chien dich' (phai) - anh chien_dich_tiep_tuc.png


def skip_turn_battle(ctx, wait_s=5.0):
    """P13-10 (chu du an): tran 'Luot n/25' - bam nut thoat/bo qua goc phai duoi thay vi ngoi xem du 25 luot.
    Cho toi wait_s giay de nut hien; khong thay (tran chay duong / khong co nut) -> False. -> True neu da bam."""
    if not ctx.cfg.get("campaign", {}).get("skip_battle", True) or not ctx.v.has("campaign/btn_skip_battle"):
        return False
    t0 = time.time()
    while time.time() - t0 < wait_s:
        img = ctx.shot()
        if ctx.v.find(img, "campaign/btn_skip_battle", th=0.8, roi=SKIP_ROI):
            ctx.tap_tpl("campaign/btn_skip_battle", wait=1.5, th=0.8, roi=SKIP_ROI, fresh=False)
            log.info("Chien dich: bam nut thoat/bo qua tran (khong xem du 25 luot)")
            return True
        if ctx.v.find(img, "campaign/btn_done") or ctx.v.find(img, "campaign/btn_continue"):
            return False
        time.sleep(0.5)
    return False


def continue_campaign(ctx):
    """P13-10: man 'Thang loi' -> bam 'Tiep tuc Chien dich' (KHONG bam 'Tro lai'). -> True neu da bam."""
    if not ctx.v.has("campaign/btn_continue"):
        return False
    if ctx.tap_tpl("campaign/btn_continue", wait=1.5, th=0.85, roi=CONTINUE_ROI):
        log.info("Chien dich: Thang loi -> bam 'Tiep tuc Chien dich'")
        return True
    return False


def close_result(ctx):
    """Dong man ket qua tran (thang: 'Dong' giua; thua: 'Dong' trai - KHONG bam 'Bat dau lai').
    P13-10: man 'Thang loi' kieu moi co 'Tro lai' | 'Tiep tuc Chien dich' -> bam 'Tiep tuc Chien dich'."""
    if continue_campaign(ctx):
        return
    for _ in range(4):
        time.sleep(1.2)  # man ket qua con hieu ung -> nut chua nhan cham ngay
        if not ctx.tap_first(["campaign/btn_done", "campaign/btn_done_lose"], wait=1.5):
            break
    ctx.dismiss_reward()


def battle(ctx, only_win=True, pre_checked=False):
    """Tu man doi hinh (nut "Chien dau") -> danh -> dong man ket qua. Dung chung cho Tinh bao.
    pre_checked: nguoi goi DA thay du doan "Thang toan dien" o bang man (fight_one) -> man quan doan kieu moi (khong
    hien du doan) duoc danh. Khong pre_checked + only_win + man kieu moi -> khong danh (khong biet du doan)."""
    # nut "Tu xep doi hinh" (goc duoi phai) LUON bam truoc khi danh (chu du an 2026-11-21 #1: "chua bam toi uu!!!",
    # doi hinh chi 3 tuong, 1 tuong Lv.1) -> du doan thang/thua tinh theo doi hinh da toi uu
    auto_formation(ctx)
    if only_win and ctx.find("campaign/btn_fight") and not predicted_win(ctx.v, ctx._img):
        log.info("Doi hinh khong du doan thang - bo")
        ctx.back_out(2)
        return "skip"
    if not ctx.tap_tpl("campaign/btn_fight", wait=0.5):
        if legion_screen(ctx.v, ctx._img) and only_win and not pre_checked:
            log.info("Man quan doan khong hien du doan - khong danh")
            ctx.back_out(2)
            return "skip"
        if not legion_fight(ctx):
            t0, ok = time.time(), False
            while time.time() - t0 < 12 and not ok:   # man doi hinh tai cham tren may yeu (#0 2026-11-22: 'error' sau 9 s)
                time.sleep(1.5)
                if ctx.tap_tpl("campaign/btn_fight", wait=0.5):
                    ok = True
                elif legion_screen(ctx.v, ctx._img) and (pre_checked or not only_win):
                    ok = legion_fight(ctx)
            if not ok:
                ctx.save_debug("campaign_no_fight")
                return "error"
    skipped = skip_turn_battle(ctx, ctx.cfg.get("campaign", {}).get("skip_wait_s", 5.0))
    if not skipped and ctx.cfg.get("battle", {}).get("steer", True):
        # tran kieu chay duong: giu ngon tay tren doi quan, nhat buff / ne nerf / ne vung tan cong
        from bot import steer
        bc = ctx.cfg.get("battle", {})
        # P7-9: nhan tran rong hon + cho vao tran lau hon (live #1: khong xac nhan duoc tran -> khong lai, thua)
        r = steer.run_battle(ctx.dev.adb, ctx.dev.serial, ctx.v, debug_dir=bc.get("debug_dir"),
                             is_battle=steer.campaign_battle, enter_wait=bc.get("enter_wait_s", steer.ENTER_WAIT_S),
                             scale=getattr(ctx.dev, "scale", 1.0))
        if r in ("win", "lose"):
            if r == "lose":
                ctx.save_debug("campaign_result")
            close_result(ctx)
            return r
    t0 = time.time()
    while time.time() - t0 < 180:  # tran tu danh
        img = ctx.shot()
        if (ctx.v.find(img, "campaign/btn_done") or ctx.v.find(img, "campaign/btn_done_lose")
                or ctx.v.find(img, "campaign/btn_continue")):
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
    claimed = 1 if claim_idle(ctx) else 0
    m, idx = getattr(ctx, "mem", None), ctx.dev.idx
    if m:
        m.set_fact(idx, "campaign_idle_at", time.time())
    wins, r = 0, None
    for _ in range(cc.get("max_fights", 5)):
        r = fight_one(ctx, cc.get("only_predicted_win", True))
        log.info("Chien dich: %s", r)
        if r != "win":
            break
        wins += 1
    if m:
        note_power(m, idx, cc, wins, r)
    ctx.back_out()
    ctx.ensure_city()
    return wins + claimed


def note_power(m, idx, cc, wins, last):
    """P1 (stepgate): man ke tiep khong du doan thang / thua -> nho luc chien can (+power_gain_pct %); lan sau chi mo
    Chien dich khi luc chien tang du (hoac toi han nhan Loi ich treo may). Thang -> xoa."""
    if wins:
        m.set_fact(idx, "campaign_need_power", None)
        return
    if last not in ("skip", "lose"):
        return
    p = (m.fact(idx, "resources") or {}).get("power") if isinstance(m.fact(idx, "resources"), dict) else None
    if p:
        need = int(p * (1 + cc.get("power_gain_pct", 5) / 100))
        m.set_fact(idx, "campaign_need_power", need)
        log.info("Chien dich: cho luc chien >= %d moi mo lai (tru khi toi han nhan treo may)", need)
