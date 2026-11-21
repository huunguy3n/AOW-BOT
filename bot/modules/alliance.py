"""Lien minh: dong gop cong nghe (bang VANG, khong bao gio kim cuong), tro giup, qua lien minh.

KHONG tu dong: nhan tin kenh lien minh (gui tin thay ban), mua do tiem lien minh, xay co.
"""
import re, time, logging
from bot import ocr

log = logging.getLogger("aow")
TURNS_ROI = (350, 666, 80, 18)   # "Luot:9/10" trong bang quyen gop


def open_alliance(ctx):
    ctx.ensure_city()
    if not ctx.tap_tpl("ally/btn_open", wait=2.0):
        log.info("Khong thay nut Lien minh (chua vao lien minh?)")
        return False
    ctx.close_popups(1)
    return True


def donate(ctx, max_n):
    if not ctx.tap_tpl("ally/tab_tech", wait=1.5):
        return 0
    p = ctx.find("ally/tech_recommended")
    if not p:
        log.info("Khong thay cong nghe de xuat")
        return 0
    ctx.tap(p[0] + 48, p[1] + 40, wait=1.5)  # dau like nam goc tren-trai cua o cong nghe
    n = 0
    while n < max_n:
        img = ctx.shot()
        m = re.search(r"(\d+)\s*/\s*(\d+)", ocr.text(img, TURNS_ROI))
        if m and int(m.group(1)) == 0:
            break
        p = ctx.v.find(img, "ally/btn_donate_gold")  # nut PHAI (vang); nut trai ton kim cuong
        if not p:
            break
        ctx.tap(p[0], p[1], wait=1.2)  # cho so luot cap nhat truoc khi doc lai
        n += 1
    ctx.tap_first(ctx.POPUP_CLOSERS, wait=0.8)
    log.info("Dong gop cong nghe lien minh %d lan", n)
    return n


def help_all(ctx):
    # nut "Giup tat ca" chi hien khi co yeu cau (chua cat anh mau); thanh pho co icon bat tay common/btn_help
    if ctx.v.has("ally/btn_help_all") and ctx.tap_tpl("ally/tile_help", wait=1.5):
        ctx.tap_tpl("ally/btn_help_all", wait=1.0)
        ctx.back_out(1)


def run(ctx):
    a = ctx.cfg.get("alliance", {})
    if not ctx.cfg.get("quests", {}).get("alliance", True):
        return 0
    if not open_alliance(ctx):
        return 0
    n = donate(ctx, a.get("donate_max", 10))
    help_all(ctx)
    if a.get("boss", True) and main_tab(ctx):
        n += boss(ctx)
    if a.get("mine", True) and (main_tab(ctx) or (open_alliance(ctx) and main_tab(ctx))):
        n += ally_mine(ctx)
    ctx.ensure_city()
    ctx.cfg["_use_help"], ctx.cfg["_use_free"] = True, False
    ctx.help_and_free()
    return n


# ---------- qua tang lien minh ----------
GIFT_CAN_ROI = (380, 190, 150, 30)          # "Co the nhan:N" (goc phai, tren tab Qua thuong)
TAB_SPECIAL, TAB_NORMAL = (134, 251), (405, 251)


def gift_can_claim(img):
    """So qua THUONG con nhan duoc hom nay ("Co the nhan:N"). -> int | None (khong doc duoc)."""
    t = ocr.text(img, GIFT_CAN_ROI)
    m = re.search(r"[:;]\s*([0-9OoDd]+)", t or "")
    if not m:
        return None
    v = m.group(1).replace("O", "0").replace("o", "0").replace("D", "0").replace("d", "0")
    return int(v) if v.isdigit() else None


GIFT_SENT_ROI = (150, 850, 240, 30)          # "Gui Qua Thuong: 7/21" (day bang qua tang lien minh)


def gift_sent(img):
    """"Gui Qua Thuong: x/y" -> (x, y). Chu du an: 7/21 = da tan cong 14 luot."""
    m = re.search(r"(\d+)\s*/\s*(\d+)", ocr.text(img, GIFT_SENT_ROI, "0123456789/:", scale=4) or "")
    return (int(m.group(1)), int(m.group(2))) if m and int(m.group(1)) <= int(m.group(2)) <= 60 else None


def gifts(ctx, x, y):
    """Icon hop qua (so do) tren thanh pho = "Qua tang lien minh" (chu du an 2026-11-21 #1):
    - tab "Qua dac biet": nhan toan bo
    - tab "Qua thuong": CHI nhan khi "Co the nhan" > 0 (het gioi han thi cham do van hien nhung khong nhan duoc).
    -> so lan bam "Nhan toan bo"."""
    ctx.tap(x - 16, y + 17, wait=2.0)
    if not ctx.wait_for("ally/gift_title", timeout=3):
        return 0
    n = 0
    ctx.tap(*TAB_SPECIAL, wait=1.5)
    if ctx.tap_tpl("ally/btn_gift_claim_all", wait=1.5):
        ctx.dismiss_reward()
        n += 1
        log.info("Qua lien minh dac biet: nhan toan bo")
    ctx.tap(*TAB_NORMAL, wait=1.5)
    img = ctx.shot()
    can = gift_can_claim(img)
    sent = gift_sent(img)
    if sent and getattr(ctx, "mem", None):
        ctx.mem.set_fact(ctx.dev.idx, "rebels_attacks_game", sent[1] - sent[0])
        log.info("Gui Qua Thuong %d/%d -> da tan cong phan quan %d luot hom nay", sent[0], sent[1], sent[1] - sent[0])
    if can == 0:
        log.info("Qua lien minh thuong: het luot nhan hom nay (Co the nhan: 0) - bo qua")
    elif ctx.tap_tpl("ally/btn_gift_claim_all", wait=1.5):
        ctx.dismiss_reward()
        n += 1
        log.info("Qua lien minh thuong: nhan toan bo (con %s)", can)
    return n


# ---------- BOSS lien minh / Mo lien minh (chu du an 2026-11-21, anh #1) ----------
BOSS_CHESTS = (30, 470, 480, 90)        # hang ruong 30% / 60% / Tieu diet (cham do = nhan duoc)


def main_tab(ctx):
    """Ve tab "Lien minh" (trang chinh co o Mo lien minh, BOSS, N.vu, Tiem...)."""
    ctx.tap_tpl("ally/tab_main", wait=1.5, th=0.75, roi=(0, 50, 220, 70))
    return bool(ctx.find("ally/tile_boss", th=0.8) or ctx.find("ally/mine_go", th=0.8, fresh=False))


def boss(ctx):
    """O BOSS lien minh -> nhan ruong muc sat thuong (cham do). Khong khieu chien. -> so ruong."""
    from bot.badges import red_dots
    if not ctx.tap_tpl("ally/tile_boss", wait=2.0, th=0.8):
        return 0
    n = 0
    if ctx.wait_for("ally/boss_title", timeout=3):
        for _ in range(4):
            dots = red_dots(ctx.shot(), BOSS_CHESTS)
            if not dots:
                break
            x, y = dots[0]
            ctx.tap(x - 18, y + 22, wait=1.5)
            ctx.dismiss_reward()
            n += 1
            log.info("BOSS lien minh: nhan ruong @%d,%d", x, y)
    ctx.back_out(1)
    return n


def ally_mine(ctx):
    """"Den thu thap" Mo lien minh (Xuong Hop Kim lien minh) -> gui 1 doi neu con doi ranh. -> 1 | 0"""
    if ctx.march_full():
        log.info("Mo lien minh: het quan doan ranh - bo qua")
        return 0
    if not ctx.tap_tpl("ally/mine_go", wait=3.0, th=0.8):
        return 0
    # ban do the gioi: vong menu quanh Xuong Hop Kim lien minh (Tin tuc / Thu thap / Huong dan / Quyen gop) -> "Thu thap"
    if ctx.wait_for("ally/mine_collect", timeout=5, th=0.8):
        ctx.tap_tpl("ally/mine_collect", wait=2.0, th=0.8, fresh=False)
    if not (ctx.wait_for("gather/btn_march", timeout=4) or ctx.find("gather/btn_gather", fresh=False)):
        ctx.save_debug("ally_mine_no_gather")          # chua biet man nay -> anh de bo sung
        ctx.ensure_city()
        return 0
    if ctx.find("gather/btn_gather", fresh=False):
        ctx.tap_tpl("gather/btn_gather", wait=1.5, fresh=False)
    ctx.tap_tpl("gather/btn_recommended", wait=1.0)
    ok = ctx.tap_tpl("gather/btn_march", wait=2.0)
    log.info("Mo lien minh: %s", "gui 1 doi thu thap" if ok else "khong gui duoc")
    if ok:
        ctx.march_sent()
    ctx.ensure_city()
    return int(bool(ok))
