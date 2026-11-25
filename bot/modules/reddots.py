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
from bot import scheduler, screens, stepgate, tapguard, visit
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
    out += [d for d in hammer_dots(img) if not any(abs(d[0] - o[0]) < 12 and abs(d[1] - o[1]) < 12 for o in out)]
    g = v.find(img, "ally/icon_gift", th=0.8, roi=(330, 600, 210, 300)) if v is not None else None
    if g:
        out += [d for d in dots if d not in out and GIFT_DOT[0] <= d[0] - g[0] <= GIFT_DOT[1] and GIFT_DOT[2] <= d[1] - g[1] <= GIFT_DOT[3]]
    return out


NHAN_ZONE = (150, 725, 235, 785)   # x1, y1, x2, y2: cham do cua icon "Nhan" (anh: cham @197,748, icon @175,765)
PROTECTED = ("alliance", "intel", "campaign", "ally_gift", "mail", "nhan", "construct")   # P13d-1: khong bao gio bo qua


def in_nhan_zone(d):
    return NHAN_ZONE[0] <= d[0] <= NHAN_ZONE[2] and NHAN_ZONE[1] <= d[1] <= NHAN_ZONE[3]


def must_open(kind):
    """P13d-1 (chu du an): cham do Lien minh / Tinh bao / Chien dich / Nhan (+ qua lien minh, thu, xay) KHONG duoc bo qua
    som (buoc rieng vua tra 0, stepgate gian chu ky, tri nho vo ich): co cham do la mo it nhat 1 lan moi luot quet."""
    return kind in PROTECTED


HAMMER_DOT_ROI = (470, 765, 70, 75)


def hammer_dots(img):
    """P13d-1: cham do nut bua (goc phai duoi, tren nut thu): nen xanh ngoc nen cham nho/toi -> dung nguong long hon."""
    return red_dots(img, HAMMER_DOT_ROI, min_r=3, min_v=150)


def is_hud_dot(d):
    """Cham do THAT nam tren HUD co dinh: cot trai (x<=170), thanh duoi (y>=850), cot phai tren (y<=460),
    goc phai duoi (nut thu/xay). Mai do / chu thap do cua cong trinh giua thanh pho (i2 2026-11-22: @423,773 va
    @320,798) khong phai cham do -> bo; huy hieu tin nhan chat (~49,327) cung khong phai viec can lam."""
    x, y = d
    if 30 <= x <= 70 and 305 <= y <= 350:
        return False                                   # so tin nhan chat
    if in_nhan_zone(d):
        return True                                    # P13d-1: icon "Nhan" (hop vang canh Chieu mo) - anh reddot_con_sot.png
    return x <= 170 or y >= 850 or (x >= 420 and y <= 460) or (x >= 480 and y >= 690)


def _order(dots):
    """Thu tu chu du an 2026-11-20: tu tren xuong duoi, tu trai qua phai (cung hang ~30 px)."""
    return sorted(dots, key=lambda d: (d[1] // 30, d[0]))


def pick(kinded):
    """kinded: [((x, y), kind)] -> cham do xu ly truoc | None.
    P13-3 (chu du an 2026-11-20, anh reddot_thu_tu.png): CHI theo vi tri - hang (y//30) tren xuong, cung hang trai qua
    phai. Bo lop uu tien theo loai (KIND_PRIO, P7-3) vi no lam bot nhay Qua lien minh (duoi) -> Thu -> Su menh (tren
    phai) -> Tinh bao (trai). Chat khong uu tien: xoa huy hieu chat van chay cuoi (chat.clear)."""
    if not kinded:
        return None
    return min(kinded, key=lambda dk: (dk[0][1] // 30, dk[0][0]))


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
    if in_nhan_zone(d):
        return "nhan"                              # P13d-1: icon "Nhan" canh Chieu mo
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
    if _near(d, ctx.v.find(img, "build/icon_hammer", th=0.85, roi=(440, 760, 100, 110))) or (
            d[0] >= 480 and 765 <= d[1] <= 840):
        return "construct"                         # P13d-1: nut bua co cham do = co cong trinh moi de xay
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
    if kind == "construct":
        return mods.get("construct", True), "modules.construct"
    if kind == "shop_gift":
        return mods.get("rewards", True), "modules.rewards"
    return True, ""


KIND_STEP = {"intel": "intel", "campaign": "campaign", "daily": "daily", "play": "play", "alliance": "alliance",
             "research": "research", "train": "train", "build": "upgrade", "rally": "rebels",
             "mission": "mission", "construct": "construct"}


# P10-5 (live3 15:34-15:37:49: cham do Tinh bao an ~4 phut cua 240 s -> het gio, con 11 cham do: thu, qua lien minh...)
CLAIM_KINDS = ("mail", "ally_gift", "vip", "shop_gift", "recruit", "hero", "nhan")   # nhan qua nhanh - lam ca khi het gio (grace)
DEFER_KINDS = ("intel", "play", "rally", "campaign")                          # tien trinh dai co buoc rieng


def defer_to_step(kind, pending, enabled=False):
    """Ham thuan: cham do loai tien trinh dai ma buoc rieng CON CHO trong luot nay -> de buoc rieng lam (khong ton thoi
    gian quet cham do). P13-3: MAC DINH TAT (reddots.defer_to_steps false) - vong cham do la truc chinh, moi cham do goi
    dung trinh xu ly cua icon theo thu tu tren->duoi, trai->phai; buoc rieng chi cho viec KHONG co cham do.
    -> ten buoc | None."""
    if not enabled:
        return None
    step = KIND_STEP.get(kind)
    return step if kind in DEFER_KINDS and step and pending and step in pending else None


def in_budget(kind, now, deadline, grace_s):
    """Ham thuan: con duoc xu ly cham do loai nay? Het max_s -> chi loai nhan qua (CLAIM_KINDS) them grace_s giay."""
    if deadline is None or now < deadline:
        return True
    return kind in CLAIM_KINDS and now < deadline + grace_s


def remaining(dots, ignored_keys, guard):
    """Ham thuan P12-2: cham do con can lam = chua co y bo qua va chua vao danh sach den. -> (con lam, da den)."""
    rest = [d for d in dots if _key(d) not in ignored_keys]
    black = [d for d in rest if guard.blocked("reddot", d[0], d[1])]
    return [d for d in rest if d not in black], black


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
        if kind == "construct":   # P13d-1: nut bua co cham do -> xay cong trinh moi
            from bot.modules import construct
            return construct.run(ctx) or 0
        if kind == "nhan":        # P13d-1: icon "Nhan" (hop vang): cham -> nhan qua, dong popup
            before = ctx.shot()
            ctx.tap(x - 22, y + 17, wait=1.5)
            if screens.same(before, ctx.shot()):
                return 0
            n = ctx.claim_buttons()
            ctx.dismiss_reward()
            return max(1, n)
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


def final_claims(ctx):
    """P10-5: quet NHAN QUA cuoi luot (truoc observe) - thu (moi tab co cham do, ca Bao cao: tran tinh bao / dau truong /
    thu thap sinh bao cao MOI sau buoc reddots), hop qua lien minh (Qua dac biet + Ruong Lv.N + Qua thuong), chieu mo.
    Live3 cuoi luot: hop qua 12, thu 4, chieu mo 1. Khong cham goi tra phi (cac ham nhan dung chung, loc chu). -> so lan."""
    rc = rcfg(ctx.cfg)
    if not rc["final_claims"]:
        return 0
    mods, rw = ctx.cfg.get("modules", {}), ctx.cfg.get("rewards", {})
    got = {}
    ctx.ensure_city()
    if mods.get("alliance", True) and rw.get("ally_gift", True):
        got["ally_gift"] = rewards.ally_gift_until_clear(ctx, rw.get("repeat_rounds", 4))
    if mods.get("rewards", True) and "mail" in (rw.get("routes") or []):
        got["mail"] = rewards.run_until_clear(ctx, "mail", rw.get("max_taps_per_route", 30), rw.get("repeat_rounds", 4))
    ok, _why = allowed("recruit", ctx.cfg)
    if ok:
        ctx.ensure_city()
        img = ctx.shot()
        p = ctx.v.find(img, "badge/recruit")
        dot = next((d for d in red_dots(img) if _near(d, p)), None) if p else None
        if dot:
            got["recruit"] = _handle(ctx, "recruit", dot[0], dot[1]) or 0
    ctx.ensure_city()
    log.info("Nhan qua cuoi luot: %s", got)
    return sum(v for v in got.values() if isinstance(v, int))


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
    from bot.modules import champion      # P13d-5: icon vua mo la man cuoc Quan quan tuan -> dat cuoc (bar su kien, khong kim cuong)
    if champion.screen_of(ctx, opened):
        return champion.handle(ctx)
    n = notify.heal_event(ctx) + notify.hub(ctx, cards=True) + notify.event_tiles(ctx) + ctx.claim_buttons()
    if not n:
        # chu du an 2026-11-21: tinh nang chua co cach xu ly -> dua vao muc hoc (web "Hoc & Agent", man la) de day
        path = screens.save_unknown(opened, ctx.dev.idx, "reddot")
        if path:
            log.info("Cham do @%d,%d: chua biet xu ly - luu %s de chu du an day", x, y, path)
    return n


def rcfg(cfg):
    """A-OPT-1 (PM 2026-11-23): reddots khong chay moi lan ghe - gioi han thoi gian / tan suat, nho icon vo ich."""
    return {"claim_grace_s": 90, "final_claims": True,
            "max_rounds": 6, "skip_idle_steps": True, "dead_h": 2, "dead_cap_h": 24, "max_s": 240,
            "min_interval_min": 30, "defer_to_steps": False,
            "dot_max_s": 75, "final_sweep": True, "final_max_s": 90, **(cfg.get("reddots") or {})}


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


def remember(m, idx, rc, old, dead_n, dead, useless, worked_at, now, visit=None):
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
        keep.pop(_k2s(k), None)      # P13d-1: vi tri da nhan duoc -> khong con la 'vo ich'
    m.set_fact(idx, "reddots_dead_visit", visit)    # P13d-1: tri nho vo ich chi dung trong CHINH lan ghe nay
    m.set_fact(idx, "reddots_dead", keep)
    m.set_fact(idx, "reddots_dead_n", {k: v for k, v in dead_n.items() if k in keep})
    m.set_fact(idx, "reddots_last_at", now)
    return keep


def run(ctx, final=False):  # noqa: C901 - vong quet giu nguyen cau truc cu
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
    max_s = rc["final_max_s"] if final else rc["max_s"]
    deadline = t_start + max_s if max_s else None
    m, idx = getattr(ctx, "mem", None), ctx.dev.idx
    vid = getattr(ctx, "visit", None)
    same_visit = bool(m) and (vid is None or m.fact(idx, "reddots_dead_visit") == vid)   # P13d-1: het han theo lan ghe
    old = {k: u for k, u in ((m.fact(idx, "reddots_dead") or {}) if (m and same_visit and not final) else {}).items()
           if u > t_start}
    dead_n = dict((m.fact(idx, "reddots_dead_n") or {}) if m else {})
    ctx.ensure_city()
    if m:
        vd = getattr(ctx, "visit_done", None) or {}
        seen = {_s2k(k) for k in (m.fact(idx, "reddots_seen") or [])}
        new = [d for d in _left(ctx.shot(), ctx.v) if _key(d) not in seen and _k2s(_key(d)) not in old]
        ok_, why_ = (True, "quet lai cuoi luot") if final else due(
            m.fact(idx, "reddots_last_at"), t_start, rc["min_interval_min"], drain.worked(vd.get("notify")), new)
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
    spent, prot = {}, set()         # P13d-1: giay da ton / vi tri; vi tri loai bao ve (khong ghi vao tri nho vo ich)
    ignored = set()                 # cham do CO Y bo qua (tap hop phan quan, qua lien minh het luot) -> khong tinh 'con sot'
    use_notify = ctx.cfg.get("modules", {}).get("notify", True)
    left, timed_out, img = [], False, None
    guard = tapguard.of(ctx)       # P12-2: toa do 2 lan vo hieu (ca o buoc khac trong lan ghe) -> bo qua

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
            img = ctx.shot()
            todo = _order([d for d in guard.keep("reddot", _left(img, ctx.v)) if _key(d) not in dead])
            if not todo:
                break
            (x, y), kind = pick([(d, _kind(ctx, img, d)) for d in todo])   # P7-3: so do co the nhan truoc
            k = _key((x, y))
            if not in_budget(kind, time.time(), deadline, rc["claim_grace_s"]):
                timed_out = True        # P10-5: het gio - chi con loai nhan qua (thu, qua lien minh...) duoc lam them
                break
            if spent.get(k, 0) >= rc["dot_max_s"]:     # P13d-1: tran thoi gian MOI cham do - khong ket 1 diem
                dead.add(k)
                log.info("Cham do %s @%d,%d: da ton %.0f s (tran %s s) - sang cham khac", kind, x, y, spent.get(k, 0), rc["dot_max_s"])
                continue
            if must_open(kind):
                prot.add(k)
            step_later = defer_to_step(kind, getattr(ctx, "visit_pending", None), bool(rc.get("defer_to_steps")))
            if step_later:
                dead.add(k)
                ignored.add(k)
                log.info("Cham do %s @%d,%d: buoc rieng '%s' chay sau trong luot nay - de no lam", kind, x, y, step_later)
                continue
            ok, gate = allowed(kind, ctx.cfg)
            if not ok:
                dead.add(k)
                ignored.add(k)      # co y bo qua -> khong tinh la 'con sot'
                log.info("Cham do %s @%d,%d: dang tat trong tuy chon (%s) - bo qua", kind, x, y, gate)
                continue
            if rc["skip_idle_steps"] and not must_open(kind) and already_idle(ctx, kind):
                dead.add(k)
                ignored.add(k)
                log.info("Cham do %s @%d,%d: buoc rieng vua chay xong khong lam duoc gi - bo qua", kind, x, y)
                continue
            step = KIND_STEP.get(kind)
            if m and step and not must_open(kind):
                g = stepgate.check(m, idx, step, ctx.cfg, time.time(), getattr(ctx, "visit_done", None))
                if not g.run:   # P1: buoc rieng dang gian chu ky / chua du dieu kien -> mo icon cung vo ich
                    dead.add(k)
                    ignored.add(k)
                    log.info("Cham do %s @%d,%d: %s - bo qua", kind, x, y, g.why)
                    continue
            t_dot = time.time()
            n = _handle(ctx, kind, x, y)
            n = n if isinstance(n, int) else 0
            spent[k] = spent.get(k, 0) + (time.time() - t_dot)
            visit.mark(ctx, kind)       # P13-2: buoc sau (rewards / mission) khong mo lai cung icon trong lan ghe nay
            guard.record("reddot", x, y, n > 0, f"{kind} khong lam duoc gi")
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
                if kind not in PROTECTED:
                    useless.add(k)
                if kind == "ally_gift":
                    ignored.add(k)       # qua thuong het luot nhan hom nay: cham do van hien
                log.info("Cham do %s @%d,%d: mo ra khong lam duoc gi", kind, x, y)
            got += n
        total += got
        ctx.ensure_city()
        img = ctx.shot()
        left, black = remaining(_left(img, ctx.v), ignored, guard)
        if not left:
            if black:
                log.info("Het cham do lam duoc sau %d vong - chi con cham do trong danh sach den: %s",
                         rnd, guard.summary())
            else:
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
        remember(m, idx, rc, old, dead_n, dead - prot, useless, worked_at, time.time(), vid)
        m.set_fact(idx, "reddots_seen", sorted({_k2s(_key(d)) for d in _left(img, ctx.v)}))
    _keep_last(ctx, img)
    if left and not timed_out:
        ctx.save_debug("reddots_left")      # -> buoc ghi "co anh loi" (khong tinh la xong sach)
        log.info("Cham do con sot sau quet: %s", left)
    log.info("Quet cham do cuoi luot: nhan %d, con %d cham do, %.0f s", total, len(left), time.time() - t_start)
    return total
