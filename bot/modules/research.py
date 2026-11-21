"""Nghien cuu (So Cong Nghe). Chu du an 2026-11-21 (#1, anh So Cong Nghe Cap 30):
  - CHI CO 1 hang nghien cuu (icon "1/1" thu hai cot trai thanh pho). Dang nghien cuu (thanh tien do + nut
    "Chi tiet" o day man) -> KHONG bat dau duoc gi -> chi ghi thoi gian con lai (lich ghe lai luc xong, web hien).
  - Chi nghien cuu duoc node co huy hieu x/y voi x < y (3/3 = da xong).
Mo bang: cham icon hang cho nghien cuu (research/icon_queue) -> "So Cong Nghe" (research/title).
KHONG BAO GIO bam nut tang toc / nghien cuu ngay bang kim cuong.
"""
import re, time, logging
import cv2
from bot import ocr

log = logging.getLogger("aow")
STRICT = re.compile(r"(?:(\d{1,2})d:)?(\d{2}):(\d{2}):(\d{2})")
BUSY_NAME, BUSY_TIME = (30, 818, 300, 26), (100, 888, 200, 24)


def parse_left(t):
    m = STRICT.search(t or "")
    if not m:
        return None
    d, h, mi, s = (int(v) if v else 0 for v in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s if h < 24 and mi < 60 and s < 60 else None


def busy(v, img):
    """Dang nghien cuu? -> (ten, giay_con_lai) | None. Dau hieu: nut "Chi tiet" goc phai duoi."""
    if not v.find(img, "research/btn_detail", th=0.8, roi=(360, 840, 180, 110)):
        return None
    return (ocr.text(img, BUSY_NAME) or "").strip(), parse_left(ocr.text(img, BUSY_TIME, "0123456789d:", scale=4))


def badges(img, roi_y=(90, 790)):
    """Huy hieu "x/y" (vong tron toi goc phai duoi moi node) -> [(x, y, a, b)]."""
    g = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 3)
    c = cv2.HoughCircles(g, cv2.HOUGH_GRADIENT, 1, 30, param1=100, param2=18, minRadius=13, maxRadius=19)
    out = []
    for x, y, r in (c[0] if c is not None else []):
        x, y, r = int(x), int(y), int(r)
        if not roi_y[0] <= y <= roi_y[1]:
            continue
        m = re.search(r"(\d+)\s*/\s*(\d+)", ocr.text(img, (x - r, y - r // 2 - 2, 2 * r, r + 4), "0123456789/", scale=5) or "")
        if m:
            out.append((x, y, int(m.group(1)), int(m.group(2))))
    return out


def open_research(ctx):
    ctx.ensure_city()
    if ctx.tap_tpl("research/icon_queue", wait=2.0, th=0.8, roi=(0, 90, 120, 320)) and ctx.wait_for("research/title", timeout=4):
        return True
    if ctx.v.has("research/btn_research_building") and ctx.tap_tpl("research/btn_research_building", wait=1.2):
        ctx.tap_tpl("research/btn_research_enter", wait=1.5)
        if ctx.wait_for("research/title", timeout=4):
            return True
    log.info("Khong mo duoc So Cong Nghe")
    ctx.save_debug("research_open")
    return False


def record(ctx, name, left):
    """Ghi nghien cuu dang chay: timer 'research' (lich) + state (web)."""
    until = time.time() + left if left else None
    m = getattr(ctx, "mem", None)
    if m:
        m.clear_timers(ctx.dev.idx, "research")
        if until:
            m.set_timer(ctx.dev.idx, "research", until, "ocr", 0.9)
    if getattr(ctx, "store", None):
        ctx.store.update(ctx.dev.idx, research={"name": name, "until": until, "at": time.time(), "idle": not name})


def run(ctx):
    rc = ctx.cfg.get("research", {})
    st = ctx.store.inst(ctx.dev.idx) if getattr(ctx, "store", None) else {}
    hq = st.get("hq_level")
    if hq is not None and hq < rc.get("min_hq", 8):
        log.info("Xuong kien truc cap %d < %d - chua co Vien nghien cuu, bo qua", hq, rc.get("min_hq", 8))
        return 0
    if not open_research(ctx):
        return 0
    started = 0
    try:
        img = ctx.shot()
        b = busy(ctx.v, img)
        if not b:                                                # bang duoi co the hien cham -> nhin lai 1 lan
            time.sleep(1.5)
            img = ctx.shot()
            b = busy(ctx.v, img)
        if b:
            name, left = b
            record(ctx, name, left)
            log.info("Dang nghien cuu '%s' con %s -> chi 1 hang, cho xong", name,
                     f"{left // 86400}d {left % 86400 // 3600}h{left % 3600 // 60:02d}" if left else "?")
            return 0
        ctx.save_debug("research_screen")     # khong thay nut "Chi tiet" -> luu anh doi chieu (#1 dang nghien cuu 13 ngay)
        idle_seen = False
        for tab in range(3):                                     # Phat trien / Dao tao / Quan su
            if tab:
                ctx.tap(95 + 175 * tab, 82, wait=1.5)
            for _ in range(4):
                img = ctx.shot()
                todo = sorted((p for p in badges(img) if p[2] < p[3]), key=lambda p: (p[1], p[0]))
                if todo:
                    x, y, a, bb = todo[0]
                    log.info("Nghien cuu: node con mo duoc %d/%d @%d,%d", a, bb, x, y)
                    ctx.tap(x - 55, y - 45, wait=1.5)            # tam node (huy hieu o goc phai duoi)
                    if ctx.v.has("research/btn_research") and ctx.tap_tpl("research/btn_research", wait=1.5):
                        if ctx.find("common/msg_insufficient"):
                            log.info("Thieu tai nguyen de nghien cuu")
                            ctx.close_popups()
                            return started
                        started += 1
                        log.info("Bat dau nghien cuu node %d/%d", a, bb)
                        return started
                    ctx.save_debug("research_node")              # chua co anh mau nut Nghien cuu -> anh de cat
                    ctx.back_out(1)
                    return started
                ctx.dev.swipe(270, 650, 270, 300, 500)            # cuon cay cong nghe xuong
                time.sleep(1.0)
        log.info("Nghien cuu: khong con node x<y nao (khong ghi 'dang ranh' vi co the doc sai)")
        return started
    finally:
        ctx.ensure_city()
        rc = ctx.cfg.get("research", {})
        ctx.help_and_free(use_help=rc.get("use_help", True), use_free=rc.get("use_free_speedup", True))
