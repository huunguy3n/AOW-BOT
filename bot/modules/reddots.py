"""Quet lai cham do CUOI luot (chu du an 2026-11-20: "chua uu tien bam cac cham do").

Buoc 'notify' chay dau luot nhung chi biet 6 icon co anh mau; cac buoc sau (nhiem vu, tan thu, chien dich)
lai lam hien cham do moi. Buoc nay chay ngay truoc 'observe':
  - moi cham do tren thanh pho, TU TREN XUONG, TU TRAI QUA PHAI (chu du an 2026-11-20): VIP, cot phai, chat,
    Tro ly lien minh, Tinh bao, Chien dich, Chieu mo, Nhiem vu, hop qua, Tuong, Lien minh...
    icon da biet -> module rieng (vip/intel/campaign/recruit/hero/daily); con lai -> mo, chi nhan bang cac ham
    an toan cua notify (nut "Nhan" xanh / o qua phat sang / o co cham do), dong lai.
  - icon "Qua" (dong xu $, tren cung cot phai) = goi TRA PHI: mo nhung CHI bam nut "Nhan" xanh, khong bam nut co gia (ADR-0008).
  - lap lai nhieu vong toi khi het cham do; vong nao khong nhan them duoc gi thi dung (tranh vong vo han voi
    cham do khong xu ly an toan duoc) -> luu anh logs/shots/*reddots_left.png de bo sung xu ly.
"""
import logging, os, time
import cv2
from bot.badges import red_dots
from aowbot.domain import drain
from bot import scheduler, screens, stepgate
from bot.modules import notify, rewards, intel, campaign, daily, alliance, play, rebels, research, train, upgrade, chat

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


GIFT_DOT = (10, 40, -32, -8)        # cham do/so cua icon "Qua lien minh" so voi tam icon (anh #1: icon 434,817 -> so 60 o 456,797)


def _left(img, v=None):
    """Cham do con tren thanh pho, bo icon "Qua" ($, goi TRA PHI, goc tren-phai) - ADR-0008.
    v (Vision): them so tren icon "Qua lien minh" (goc phai duoi, nam trong vung mai/cong trinh bi bo) - chu du an 2026-11-22
    'chua lam xong cac muc do': so 60 tren icon qua lien minh khong bao gio duoc xu ly."""
    dots = red_dots(img, CITY)
    out = [d for d in dots if is_hud_dot(d)]
    g = v.find(img, "ally/icon_gift", th=0.8, roi=(330, 600, 210, 300)) if v is not None else None
    if g:
        out += [d for d in dots if d not in out and GIFT_DOT[0] <= d[0] - g[0] <= GIFT_DOT[1] and GIFT_DOT[2] <= d[1] - g[1] <= GIFT_DOT[3]]
    return out


def is_hud_dot(d):
    """Cham do THAT nam tren HUD co dinh: cot trai (x<=170), thanh duoi (y>=850), cot phai tren (y<=460),
    goc phai duoi (nut thu/xay). Mai do / chu thap do cua cong trinh giua thanh pho (i2 2026-11-22: @423,773 va
    @320,798) khong phai cham do -> bo; huy hieu tin nhan chat (~49,327) cung khong phai viec can lam."""
    x, y = d
    if 30 <= x <= 70 and 305 <= y <= 350:
        return False                                   # so tin nhan chat
    return x <= 170 or y >= 850 or (x >= 420 and y <= 460) or (x >= 480 and y >= 690)


def _order(dots):
    """Thu tu chu du an 2026-11-20: tu tren xuong duoi, tu trai qua phai (cung hang ~30 px)."""
    return sorted(dots, key=lambda d: (d[1] // 30, d[0]))


# P7-3 (chu du an 2026-11-24): uu tien so do CO THE NHAN (thu, qua lien minh, VIP, nhiem vu ngay...) truoc; chat KHONG uu
# tien (xoa huy hieu chat chay cuoi, chi khi con thoi gian). Cung muc -> tren xuong, trai qua phai.
KIND_PRIO = {"mail": 0, "ally_gift": 0, "vip": 1, "daily": 1, "shop_gift": 2, "intel": 2, "play": 2,
             "build": 3, "research": 3, "train": 3, "campaign": 3, "recruit": 3, "hero": 3, "alliance": 4,
             "rally": 4, "mission": 2, "generic": 5}


def pick(kinded):
    """kinded: [((x, y), kind)] -> phan tu xu ly truoc (uu tien loai, roi tren xuong / trai qua phai) | None."""
    if not kinded:
        return None
    return min(kinded, key=lambda dk: (KIND_PRIO.get(dk[1], 5), dk[0][1] // 30, dk[0][0]))


def _key(d):
    return (d[0] // 40, d[1] // 40)


def _near(d, p):
    return p is not None and NEAR[0] < d[0] - p[0] < NEAR[1] and NEAR[2] < d[1] - p[1] < NEAR[3]


def _kind(ctx, img, d):
    """Cham do thuoc icon nao -> ten trinh xu ly rieng; 'generic' = mo va chi nhan nut "Nhan" an toan."""
    if d[1] < 70:
        return "vip"                               # chu "VIP n" tren cung (cham do ben phai chu)
    if d[0] > 470 and d[1] < 150:
        return "shop_gift"                         # icon "Qua" ($, goc tren-phai): chi nhan nut "Nhan" xanh (chu du an 2026-11-22)
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
    if _near(d, ctx.v.find(img, "play/btn_open", th=0.85, roi=(330, 860, 160, 100))):
        return "play"                              # Q1: "Loi choi" (mo khoang san, dau truong) -> lam luon
    # Q1: cham do tren icon hang cho cot trai = hang cho dang RANH -> lam dung viec do
    for name, tpl in (("research", "research/icon_queue"), ("train", "train/queue_icon"),
                      ("build", "build/icon_builder")):
        if _near(d, ctx.v.find(img, tpl, th=0.7 if name == "train" else 0.8, roi=(0, 90, 120, 320))):
            return name
    # chu du an 2026-11-21 (#1): icon kiem cheo = dang co tap hop phan quan/quai -> bo qua;
    # icon hop qua (so do) = Qua tang lien minh -> trinh rieng (qua thuong co gioi han nhan / ngay)
    if _near(d, ctx.v.find(img, "rebels/icon_rally", th=0.8, roi=(330, 600, 210, 300))):
        return "rally"
    if _near(d, ctx.v.find(img, "ally/icon_gift", th=0.8, roi=(330, 600, 210, 300))):
        return "ally_gift"
    if ctx.v.has("mission/icon") and _near(d, ctx.v.find(img, "mission/icon", roi=(440, 90, 100, 420))):
        return "mission"                           # P7-7: icon Su menh -> module rieng (khong mo "generic")
    if _near(d, ctx.v.find(img, "rewards/mail/open_1", roi=(400, 600, 140, 300))):
        return "mail"                              # P7-3: icon thu (so do) goc phai duoi -> nhan het, lap toi khi het so
    return "generic"


def allowed(kind, cfg):
    """Cham do loai nay co duoc xu ly theo tuy chon cua chu du an khong (A-SAFE-2: truoc day reddots goi thang
    intel/VIP/daily/chieu mo/tuong ke ca khi da tat). Cung cong voi notify.run va buoc rieng. -> (bool, ly do)"""
    mods, nc = cfg.get("modules", {}), cfg.get("notify", {})
    if kind == "vip":
        ok = mods.get("rewards", True) and "vip" in (cfg.get("rewards", {}).get("routes") or [])
        return ok, "rewards / tuyen vip"
    if kind == "intel":
        # tinh bao co 2 cong: buoc rieng 'intel' hoac notify.intel (notify.run tu xu ly khi buoc rieng tat)
        return mods.get("intel", True) or (mods.get("notify", True) and nc.get("intel", True)), "intel / notify.intel"
    if kind in ("recruit", "hero"):
        return mods.get("notify", True) and nc.get(kind, True), f"notify.{kind}"
    if kind in ("alliance", "ally_gift"):
        return mods.get("alliance", True), "modules.alliance"
    if kind in ("campaign", "daily", "play", "research", "train", "mission"):
        return mods.get(kind, True), f"modules.{kind}"
    if kind == "build":
        return mods.get("upgrade", True), "modules.upgrade"
    if kind == "rally":
        return mods.get("rebels", True), "modules.rebels"
    if kind == "shop_gift":
        return mods.get("rewards", True), "modules.rewards"
    return True, ""


KIND_STEP = {"intel": "intel", "campaign": "campaign", "daily": "daily", "play": "play", "alliance": "alliance",
             "research": "research", "train": "train", "build": "upgrade", "rally": "rebels",
             "mission": "mission"}


def already_idle(ctx, kind):
    """Buoc rieng cua icon nay vua chay TRONG LAN GHE NAY va khong lam duoc gi -> mo lai cham do cung vo ich
    (cham do van hien vi game dem thong bao khac; do 2026-11-22: campaign/intel/daily mo lai ~20-40 s moi cai)."""
    step = KIND_STEP.get(kind)
    vd = getattr(ctx, "visit_done", None)
    return bool(step and vd is not None and step in vd and not drain.worked(vd[step]))


def _handle(ctx, kind, x, y):
    """Xu ly 1 cham do bang dung module cua icon do. -> so viec lam duoc."""
    try:
        if kind == "vip":
            return rewards.run_route(ctx, "rewards/vip/")
        if kind == "intel":
            return intel.run(ctx)
        if kind == "campaign":
            return campaign.run(ctx) or 0
        if kind == "alliance":
            return alliance.run(ctx) or 0
        if kind == "daily":
            return daily.run(ctx)
        if kind == "play":
            return play.run(ctx) or 0
        if kind == "mission":     # P7-7: Su menh -> chi tab Nhiem vu hang ngay + ruong mien phi (khong mo tab tra phi)
            from bot.modules import mission
            return mission.run(ctx) or 0
        if kind == "build":       # Q2: tho xay ranh -> nang nha chinh (thieu dieu kien -> cong trinh dieu kien)
            return upgrade.run(ctx) or 0
        if kind in ("research", "train"):
            return (research if kind == "research" else train).run(ctx) or 0
        if kind == "rally":       # Q1: tap hop phan quan -> buoc phan quan (cap HQ / luot trong ngay do no kiem)
            ok, why = scheduler.rebels_ready(getattr(ctx, "mem", None), ctx.dev.idx, ctx.cfg)                 if getattr(ctx, "mem", None) else (True, "")
            if not ok:
                log.info("Cham do phan quan: %s - bo qua", why)
                return 0
            return rebels.run(ctx) or 0
        if kind == "ally_gift":
            return alliance.gifts(ctx, x, y)
        if kind == "mail":
            rc_ = ctx.cfg.get("rewards", {})
            return rewards.run_until_clear(ctx, "mail", rc_.get("max_taps_per_route", 30), rc_.get("repeat_rounds", 4))
        if kind == "shop_gift":   # goi tra phi KHONG bam; chi nut "Nhan" xanh (claim_buttons nhan theo mau + chu)
            ctx.tap(x - 16, y + 17, wait=2.5)
            if ctx.is_home():
                return 0
            ctx.save_debug("shop_gift")
            from bot import claimloop    # P9-3: lap toi khi bang Qua het cham do (tab + o mien phi)
            n, rounds, left = claimloop.until_clear(lambda: _shop_gift(ctx),
                                                    lambda: bool(red_dots(ctx.shot(), SHOP_DOTS)), max_rounds=4)
            log.info("Qua ($): nhan %d lan / %d vong%s", n, rounds, " - con cham do khong nhan an toan duoc" if left else "")
            return n
        if kind in ("recruit", "hero"):
            ctx.tap(x - 16, y + 17, wait=2.5)
            return notify.recruit(ctx) if kind == "recruit" else notify.heroes(ctx)
        return _open_dot(ctx, x, y)
    finally:
        notify.leave(ctx)
        ctx.ensure_city()


def _free_chest(ctx, img, d):
    """Cham do canh ruong nho co nhan "Mien phi" ben duoi (tab Qua) -> bam ruong. Khong co chu Mien phi -> khong bam."""
    from bot import buttons, ocr
    t = buttons._norm(ocr.text(img, (max(0, d[0] - 80), d[1] + 25, 130, 55), scale=3, psm=7, bright=170))
    if "phi" not in t or "mi" not in t:
        return 0
    ctx.tap(d[0] - 30, d[1] + 25, wait=1.5)
    ctx.dismiss_reward()
    log.info("Qua: nhan ruong Mien phi @%d,%d", d[0], d[1])
    return 1


def _shop_page(ctx):
    """1 tab cua bang Qua: nut Nhan / Nhan thuong / Mien phi xanh + ruong nho co nhan Mien phi."""
    n = ctx.claim_buttons()
    seen = set()
    for _ in range(4):
        img = ctx.shot()
        dots = [d for d in red_dots(img, (0, 125, 540, 700)) if (d[0] // 30, d[1] // 30) not in seen]
        if not dots:
            break
        seen.add((dots[0][0] // 30, dots[0][1] // 30))
        n += _free_chest(ctx, img, dots[0])
    return n


SHOP_DOTS = (90, 30, 450, 800)   # hang tab + noi dung bang Qua


def _shop_gift(ctx):
    """Bang Qua (goc tren-phai): duyet cac tab con cham do, nhan qua co nut Nhan / chu Mien phi; goi co gia tien KHONG bam
    (chu du an 2026-11-22: "co chu mien phi, hoac khong ghi so tien thi nhan")."""
    n = _shop_page(ctx)
    seen = set()
    for _ in range(8):
        tabs = [d for d in red_dots(ctx.shot(), (90, 30, 450, 90)) if (d[0] // 30, d[1] // 30) not in seen]
        if not tabs:
            break
        d = tabs[0]
        seen.add((d[0] // 30, d[1] // 30))
        ctx.tap(d[0] - 45, d[1] + 28, wait=1.5)
        n += _shop_page(ctx)
    return n


def _open_dot(ctx, x, y):
    """Mo icon mang cham do (cham do o goc tren-phai icon) -> chi nhan bang cac ham an toan cua notify
    (nut "Nhan" xanh / o qua phat sang / o co cham do). Khong bam nut nao khac. -> so lan nhan."""
    ctx.tap(x - 16, y + 17, wait=2.5)
    if ctx.is_home():                          # cham trung cho trong / icon khong mo man -> khong co gi de nhan
        return 0
    opened = ctx.shot()
    n = notify.heal_event(ctx) + notify.hub(ctx, cards=True) + notify.event_tiles(ctx) + ctx.claim_buttons()
    if not n:
        # chu du an 2026-11-21: tinh nang chua co cach xu ly -> dua vao muc hoc (web "Hoc & Agent", man la) de day
        path = screens.save_unknown(opened, ctx.dev.idx, "reddot")
        if path:
            log.info("Cham do @%d,%d: chua biet xu ly - luu %s de chu du an day", x, y, path)
    return n


def rcfg(cfg):
    """A-OPT-1 (PM 2026-11-23): reddots khong chay moi lan ghe - gioi han thoi gian / tan suat, nho icon vo ich."""
    return {"max_rounds": 6, "skip_idle_steps": True, "dead_h": 2, "dead_cap_h": 24, "max_s": 240,
            "min_interval_min": 30, **(cfg.get("reddots") or {})}


def due(last_at, now, interval_min, notify_worked, new_dots):
    """Co nen quet cham do lan nay khong -> (bool, ly do). Ham thuan (test offline)."""
    if last_at is None or now - last_at >= interval_min * 60:
        return True, "toi han"
    if notify_worked:
        return True, "notify vua nhan duoc qua (co cham do moi)"
    if new_dots:
        return True, f"{len(new_dots)} cham do moi"
    return False, f"da quet luc {time.strftime('%H:%M', time.localtime(last_at))}, khong co cham do moi"


def dead_until(n, now, dead_h, cap_h):
    """Vi tri mo ra vo ich lan thu n (lien tiep qua cac lan ghe) -> bo qua dead_h x 2^(n-1) gio, toi da cap_h."""
    return now + min(dead_h * 2 ** max(0, n - 1), cap_h) * 3600


def _k2s(k):
    return f"{k[0]},{k[1]}"


def _s2k(s):
    return tuple(int(v) for v in s.split(","))


def remember(m, idx, rc, old, dead_n, dead, useless, worked_at, now):
    """Ghi tri nho sau 1 lan quet: vi tri vo ich -> bo qua lau dan (gap doi), vi tri lam duoc viec -> xoa dem."""
    keep = dict(old)
    olds = {_s2k(s) for s in old}
    for k in dead - olds:
        if k in useless:
            n_ = int(dead_n.get(_k2s(k), 0)) + 1
            dead_n[_k2s(k)] = n_
            keep[_k2s(k)] = dead_until(n_, now, rc["dead_h"], rc["dead_cap_h"])
        else:
            keep[_k2s(k)] = now + rc["dead_h"] * 3600
    for k in worked_at:
        dead_n.pop(_k2s(k), None)
    m.set_fact(idx, "reddots_dead", keep)
    m.set_fact(idx, "reddots_dead_n", {k: v for k, v in dead_n.items() if k in keep})
    m.set_fact(idx, "reddots_last_at", now)
    return keep


def run(ctx):  # noqa: C901 - vong quet giu nguyen cau truc cu
    """Lam toi khi HET cham do (chu du an 2026-11-20: "con reddots thi phai lam tiep toi khi het").
    Moi vong: notify (icon biet ten) -> moi cham do con lai tren thanh pho -> mo, nhan. Lap lai den khi khong con
    cham do, hoac 1 vong tron khong nhan them duoc gi (cham do khong xu ly duoc an toan, vd chieu mo can kim cuong,
    Tuong thieu EXP) -> dung, luu anh 'reddots_left' (buoc ghi 'co anh loi', khong tinh la xong sach).
    A-OPT-1 (PM 2026-11-23; do 21-22/11: 51 lan, 198 phut, ~30 % thoi gian may): moi may toi da 1 lan /
    reddots.min_interval_min tru khi notify vua nhan duoc qua hoac co cham do MOI; toi da reddots.max_s giay / lan;
    vi tri mo ra vo ich -> bo qua dead_h gio, lap lai thi gap doi (toi da dead_cap_h)."""
    rc = rcfg(ctx.cfg)
    max_rounds = rc["max_rounds"]
    t_start = time.time()
    deadline = t_start + rc["max_s"] if rc["max_s"] else None
    m, idx = getattr(ctx, "mem", None), ctx.dev.idx
    old = {k: u for k, u in ((m.fact(idx, "reddots_dead") or {}) if m else {}).items() if u > t_start}
    dead_n = dict((m.fact(idx, "reddots_dead_n") or {}) if m else {})
    ctx.ensure_city()
    if m:
        vd = getattr(ctx, "visit_done", None) or {}
        seen = {_s2k(k) for k in (m.fact(idx, "reddots_seen") or [])}
        new = [d for d in _left(ctx.shot(), ctx.v) if _key(d) not in seen and _k2s(_key(d)) not in old]
        ok_, why_ = due(m.fact(idx, "reddots_last_at"), t_start, rc["min_interval_min"],
                        drain.worked(vd.get("notify")), new)
        if not ok_:
            log.info("Cham do: bo qua lan nay (%s)", why_)
            return 0
        log.info("Cham do: quet (%s), toi da %s s", why_, rc["max_s"] or "-")
    total, dead = 0, set()          # dead: vi tri da mo ma khong nhan duoc gi -> khong mo lai trong buoc nay
    useless, worked_at = set(), set()   # vo ich -> nho lau dan; lam duoc viec -> xoa dem vo ich
    # G3: tri nho cham do vo ich giua cac lan ghe (het han) -> khong mo lai moi lan ghe
    dead |= {_s2k(k) for k in old}
    if old:
        log.info("Cham do: bo qua %d vi tri da biet la vo ich (tri nho)", len(old))
    handled = {}                    # vi tri -> so lan da xu ly trong buoc nay
    ignored = set()                 # cham do CO Y bo qua (tap hop phan quan, qua lien minh het luot) -> khong tinh 'con sot'
    use_notify = ctx.cfg.get("modules", {}).get("notify", True)
    left, timed_out, img = [], False, None

    def over():
        return deadline is not None and time.time() >= deadline

    for rnd in range(1, max_rounds + 1):
        got = 0
        # icon notify quan ly (phuc loi, hoat dong, chieu mo mien phi, tuong...) - chay ca khi lich khong xep 'notify'
        if use_notify and not over() and notify.badged(ctx):
            r = notify.run(ctx)
            got += sum(v for v in (r or {}).values() if isinstance(v, int))
            ctx.ensure_city()
        # cac cham do con lai (cot phai truoc, roi tren xuong): mo tung cai 1 lan / vong
        for _ in range(12):
            if over():
                timed_out = True
                break
            img = ctx.shot()
            todo = _order([d for d in _left(img, ctx.v) if _key(d) not in dead])
            if not todo:
                break
            (x, y), kind = pick([(d, _kind(ctx, img, d)) for d in todo])   # P7-3: so do co the nhan truoc
            k = _key((x, y))
            ok, gate = allowed(kind, ctx.cfg)
            if not ok:
                dead.add(k)
                ignored.add(k)      # co y bo qua -> khong tinh la 'con sot'
                log.info("Cham do %s @%d,%d: dang tat trong tuy chon (%s) - bo qua", kind, x, y, gate)
                continue
            if rc["skip_idle_steps"] and already_idle(ctx, kind):
                dead.add(k)
                ignored.add(k)
                log.info("Cham do %s @%d,%d: buoc rieng vua chay xong khong lam duoc gi - bo qua", kind, x, y)
                continue
            step = KIND_STEP.get(kind)
            if m and step:
                g = stepgate.check(m, idx, step, ctx.cfg, time.time(), getattr(ctx, "visit_done", None))
                if not g.run:   # P1: buoc rieng dang gian chu ky / chua du dieu kien -> mo icon cung vo ich
                    dead.add(k)
                    ignored.add(k)
                    log.info("Cham do %s @%d,%d: %s - bo qua", kind, x, y, g.why)
                    continue
            n = _handle(ctx, kind, x, y)
            n = n if isinstance(n, int) else 0
            handled[k] = handled.get(k, 0) + 1
            # cham do khong bao gio mat (so "66" o nut Lien minh = tin nhan / thong bao) -> moi vi tri toi da
            # 2 lan / buoc, Lien minh 1 lan (chu du an 2026-11-21: "khong co hoat dong ma he thong lien tuc bam")
            if kind == "alliance" or handled[k] >= 2:
                dead.add(k)
                if n:
                    ignored.add(k)
            if n:
                worked_at.add(k)
                log.info("Cham do %s @%d,%d: lam %d (vong %d)", kind, x, y, n, rnd)
            else:
                dead.add(k)
                useless.add(k)
                if kind == "ally_gift":
                    ignored.add(k)       # qua thuong het luot nhan hom nay: cham do van hien
                log.info("Cham do %s @%d,%d: mo ra khong lam duoc gi", kind, x, y)
            got += n
        total += got
        ctx.ensure_city()
        img = ctx.shot()
        left = [d for d in _left(img, ctx.v) if _key(d) not in ignored]
        if not left:
            log.info("Het cham do sau %d vong", rnd)
            break
        if timed_out or over():
            timed_out = True
            log.info("Cham do: het %s s - dung (con %s)", rc["max_s"], left)
            break
        if not got:
            log.info("Vong %d khong nhan them duoc gi - dung (con %s)", rnd, left)
            break
    if not over():
        try:
            chat.clear(ctx)        # chu du an 2026-11-22: mo roi thoat chat de mat huy hieu; P7-3: KHONG uu tien -> cuoi
        except Exception as e:     # loi o day khong duoc lam hong ca buoc cham do
            log.warning("Chat: loi khi xoa huy hieu: %s", e)
        ctx.ensure_city()
        img = ctx.shot()
    if img is None:                 # max_rounds = 0
        img = ctx.shot()
    if m:
        remember(m, idx, rc, old, dead_n, dead, useless, worked_at, time.time())
        m.set_fact(idx, "reddots_seen", sorted({_k2s(_key(d)) for d in _left(img, ctx.v)}))
    _keep_last(ctx, img)
    if left and not timed_out:
        ctx.save_debug("reddots_left")      # -> buoc ghi "co anh loi" (khong tinh la xong sach)
        log.info("Cham do con sot sau quet: %s", left)
    log.info("Quet cham do cuoi luot: nhan %d, con %d cham do, %.0f s", total, len(left), time.time() - t_start)
    return total
