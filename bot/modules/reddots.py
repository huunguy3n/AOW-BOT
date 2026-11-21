"""Quet lai cham do CUOI luot (chu du an 2026-11-20: "chua uu tien bam cac cham do").

Buoc 'notify' chay dau luot nhung chi biet 6 icon co anh mau; cac buoc sau (nhiem vu, tan thu, chien dich)
lai lam hien cham do moi. Buoc nay chay ngay truoc 'observe':
  - moi cham do tren thanh pho, TU TREN XUONG, TU TRAI QUA PHAI (chu du an 2026-11-20): VIP, cot phai, chat,
    Tro ly lien minh, Tinh bao, Chien dich, Chieu mo, Nhiem vu, hop qua, Tuong, Lien minh...
    icon da biet -> module rieng (vip/intel/campaign/recruit/hero/daily); con lai -> mo, chi nhan bang cac ham
    an toan cua notify (nut "Nhan" xanh / o qua phat sang / o co cham do), dong lai.
  - icon "Qua" (dong xu $, tren cung cot phai) = goi TRA PHI -> KHONG mo (ADR-0008).
  - lap lai nhieu vong toi khi het cham do; vong nao khong nhan them duoc gi thi dung (tranh vong vo han voi
    cham do khong xu ly an toan duoc) -> luu anh logs/shots/*reddots_left.png de bo sung xu ly.
"""
import logging, os
import cv2
from bot.badges import red_dots
from bot.modules import notify, rewards, intel, campaign, daily, alliance

log = logging.getLogger("aow")


def _keep_last(ctx, img):
    """Luu khung thanh pho cuoi buoc (ghi de) -> logs/live/reddots_i<idx>.png de doi chieu khi bot bao 'khong con cham do'."""
    try:
        os.makedirs("logs/live", exist_ok=True)
        cv2.imwrite(f"logs/live/reddots_i{ctx.dev.idx}.png", img)
    except Exception:
        pass


CITY = (0, 0, 540, 960)           # ca man: VIP tren cung, cot trai/phai, thanh duoi (Tuong, Lien minh...)
NEAR = (-10, 70, -60, 25)          # cham do o goc tren-phai icon: dx, dy so voi tam anh mau icon


def _left(img):
    """Cham do con tren thanh pho, bo icon "Qua" ($, goi TRA PHI, goc tren-phai) - ADR-0008."""
    return [d for d in red_dots(img, CITY) if not (d[0] > 470 and d[1] < 150)]


def _order(dots):
    """Thu tu chu du an 2026-11-20: tu tren xuong duoi, tu trai qua phai (cung hang ~30 px)."""
    return sorted(dots, key=lambda d: (d[1] // 30, d[0]))


def _key(d):
    return (d[0] // 40, d[1] // 40)


def _near(d, p):
    return p is not None and NEAR[0] < d[0] - p[0] < NEAR[1] and NEAR[2] < d[1] - p[1] < NEAR[3]


def _kind(ctx, img, d):
    """Cham do thuoc icon nao -> ten trinh xu ly rieng; 'generic' = mo va chi nhan nut "Nhan" an toan."""
    if d[1] < 70:
        return "vip"                               # chu "VIP n" tren cung (cham do ben phai chu)
    camp = ctx.v.find(img, "campaign/btn_open")
    if camp and _near(d, (camp[0] - 2, camp[1] - 56)):
        return "intel"                             # icon Tinh bao nam ngay tren Chien dich
    if _near(d, camp):
        return "campaign"
    for name, tpl in (("recruit", "badge/recruit"), ("hero", "badge/hero"), ("daily", "daily/open_1")):
        if _near(d, ctx.v.find(img, tpl)):
            return name
    if d[1] > 850 and 290 < d[0] < 400:
        return "alliance"                          # nut "Lien minh" thanh duoi (cham do/so goc tren-phai)
    # chu du an 2026-11-21 (#1): icon kiem cheo = dang co tap hop phan quan/quai -> bo qua;
    # icon hop qua (so do) = Qua tang lien minh -> trinh rieng (qua thuong co gioi han nhan / ngay)
    if _near(d, ctx.v.find(img, "rebels/icon_rally", th=0.8, roi=(330, 600, 210, 300))):
        return "rally"
    if _near(d, ctx.v.find(img, "ally/icon_gift", th=0.8, roi=(330, 600, 210, 300))):
        return "ally_gift"
    return "generic"


def _handle(ctx, kind, x, y):
    """Xu ly 1 cham do bang dung module cua icon do. -> so viec lam duoc."""
    mods = ctx.cfg.get("modules", {})
    try:
        if kind == "vip":
            return rewards.run_route(ctx, "rewards/vip/")
        if kind == "intel":
            return intel.run(ctx)
        if kind == "campaign" and mods.get("campaign", True):
            return campaign.run(ctx) or 0
        if kind == "alliance" and mods.get("alliance", True):
            return alliance.run(ctx) or 0
        if kind == "daily":
            return daily.run(ctx)
        if kind == "rally":
            return 0
        if kind == "ally_gift":
            return alliance.gifts(ctx, x, y)
        if kind in ("recruit", "hero"):
            ctx.tap(x - 16, y + 17, wait=2.5)
            return notify.recruit(ctx) if kind == "recruit" else notify.heroes(ctx)
        return _open_dot(ctx, x, y)
    finally:
        notify.leave(ctx)
        ctx.ensure_city()


def _open_dot(ctx, x, y):
    """Mo icon mang cham do (cham do o goc tren-phai icon) -> chi nhan bang cac ham an toan cua notify
    (nut "Nhan" xanh / o qua phat sang / o co cham do). Khong bam nut nao khac. -> so lan nhan."""
    ctx.tap(x - 16, y + 17, wait=2.5)
    if ctx.is_home():                          # cham trung cho trong / icon khong mo man -> khong co gi de nhan
        return 0
    return notify.heal_event(ctx) + notify.hub(ctx, cards=True) + notify.event_tiles(ctx)


def run(ctx):
    """Lam toi khi HET cham do (chu du an 2026-11-20: "con reddots thi phai lam tiep toi khi het").
    Moi vong: notify (icon biet ten) -> moi cham do con lai tren thanh pho -> mo, nhan. Lap lai den khi khong con
    cham do, hoac 1 vong tron khong nhan them duoc gi (cham do khong xu ly duoc an toan, vd chieu mo can kim cuong,
    Tuong thieu EXP) -> dung, luu anh 'reddots_left' (buoc ghi 'co anh loi', khong tinh la xong sach)."""
    rc = ctx.cfg.get("reddots", {})
    max_rounds = rc.get("max_rounds", 6)
    ctx.ensure_city()
    total, dead = 0, set()          # dead: vi tri da mo ma khong nhan duoc gi -> khong mo lai trong buoc nay
    # G3: tri nho cham do vo ich giua cac lan ghe (het han reddots.dead_h gio) -> khong mo lai moi lan ghe
    m = getattr(ctx, "mem", None)
    import time as _t
    old = {k: u for k, u in ((m.fact(ctx.dev.idx, "reddots_dead") or {}) if m else {}).items() if u > _t.time()}
    dead |= {tuple(int(v) for v in k.split(",")) for k in old}
    if old:
        log.info("Cham do: bo qua %d vi tri da biet la vo ich (tri nho)", len(old))
    handled = {}                    # vi tri -> so lan da xu ly trong buoc nay
    ignored = set()                 # cham do CO Y bo qua (tap hop phan quan, qua lien minh het luot) -> khong tinh 'con sot'
    use_notify = ctx.cfg.get("modules", {}).get("notify", True)
    left = []
    for rnd in range(1, max_rounds + 1):
        got = 0
        # icon notify quan ly (phuc loi, hoat dong, chieu mo mien phi, tuong...) - chay ca khi lich khong xep 'notify'
        if use_notify and notify.badged(ctx):
            r = notify.run(ctx)
            got += sum(v for v in (r or {}).values() if isinstance(v, int))
            ctx.ensure_city()
        # cac cham do con lai (cot phai truoc, roi tren xuong): mo tung cai 1 lan / vong
        for _ in range(12):
            img = ctx.shot()
            todo = _order([d for d in _left(img) if _key(d) not in dead])
            if not todo:
                break
            x, y = todo[0]
            kind = _kind(ctx, img, (x, y))
            if kind == "rally":
                dead.add(_key((x, y)))
                ignored.add(_key((x, y)))
                log.info("Cham do @%d,%d: icon tap hop phan quan/quai - bo qua", x, y)
                continue
            n = _handle(ctx, kind, x, y)
            n = n if isinstance(n, int) else 0
            handled[_key((x, y))] = handled.get(_key((x, y)), 0) + 1
            # cham do khong bao gio mat (so "66" o nut Lien minh = tin nhan / thong bao) -> moi vi tri toi da
            # 2 lan / buoc, Lien minh 1 lan (chu du an 2026-11-21: "khong co hoat dong ma he thong lien tuc bam")
            if kind == "alliance" or handled[_key((x, y))] >= 2:
                dead.add(_key((x, y)))
                if n:
                    ignored.add(_key((x, y)))
            if n:
                log.info("Cham do %s @%d,%d: lam %d (vong %d)", kind, x, y, n, rnd)
            else:
                dead.add(_key((x, y)))
                if kind == "ally_gift":
                    ignored.add(_key((x, y)))       # qua thuong het luot nhan hom nay: cham do van hien
                log.info("Cham do %s @%d,%d: mo ra khong lam duoc gi", kind, x, y)
            got += n
        total += got
        ctx.ensure_city()
        img = ctx.shot()
        left = [d for d in _left(img) if _key(d) not in ignored]
        if not left:
            log.info("Het cham do sau %d vong", rnd)
            break
        if not got:
            log.info("Vong %d khong nhan them duoc gi - dung (con %s)", rnd, left)
            break
    if m:
        until = _t.time() + rc.get("dead_h", 2) * 3600
        keep = {**old, **{f"{k[0]},{k[1]}": until for k in dead if f"{k[0]},{k[1]}" not in old}}
        m.set_fact(ctx.dev.idx, "reddots_dead", keep)
    _keep_last(ctx, ctx.shot())
    if left:
        ctx.save_debug("reddots_left")      # -> buoc ghi "co anh loi" (khong tinh la xong sach)
        log.info("Cham do con sot sau quet: %s", left)
    log.info("Quet cham do cuoi luot: nhan %d, con %d cham do", total, len(left))
    return total
