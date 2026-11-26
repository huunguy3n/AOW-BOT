"""Bo lap lich (giai doan A2-A3): quyet dinh KHI NAO ghe tai khoan nao va chay BUOC nao.

Ham thuan: chi doc tri nho (bot/memory.py), khong mo game -> test offline (tools/sim_schedule.py).
Chu du an chot 2026-11-19:
  - Chi 3 viec duoc keo may len (trigger): XAY NHA (mainquest/quests), THU THAP (gather), NGHIEN CUU (research).
    Ngoai le: tai khoan dang bat 'tutorial' ma chua xong tan thu -> luon can choi tiep.
  - Moi buoc khac (cham do, qua, nhiem vu ngay, lien minh, tinh bao, huan luyen...) chi chay kem khi may da bat.
  - Tran an toan: qua schedule.max_gap_min (240) khong ghe -> van vao 1 lan, chay moi buoc bat.
  - Reset ngay 0h UTC (khong keo may, chi la ly do ghi kem).
Thu tu buoc trong 1 lan ghe van theo ORDER (runner), lich chi chon buoc nao + luc nao.
"""
import json, time
from dataclasses import dataclass, field

from aowbot.domain import builders as builders_dom, marches, rollout, warday
from bot import stepgate

TRIGGERS = ("warday", "gather", "upgrade", "mainquest", "quests", "research", "rebels")
DEFAULTS = {"max_gap_min": 240, "min_gap_min": 10, "batch_window_min": 5, "idle_check_min": 15,
            "gather_retry_min": 60, "unknown_return_min": 60, "build_every_min": 120, "research_every_min": 120, "extra_every_min": 180, "tutorial_every_min": 30,
            "research_hq_min": 7, "daily_reset_utc": 0}


@dataclass
class Plan:
    ready: bool            # co viec ngay bay gio
    at: float = None       # lan som nhat co viec (None = khong biet / khong keo may)
    why: str = ""
    confident: bool = True  # False = uoc luong theo chu ky (khi ghe thi cu chay de kiem tra)


@dataclass
class Visit:
    idx: int
    at: float
    steps: list = field(default_factory=list)
    why: str = ""
    full: bool = False     # ghe vi tran an toan -> chay moi buoc bat


def sched_cfg(cfg):
    return {**DEFAULTS, **(cfg.get("schedule") or {})}


def _last(mem, idx, step):
    r = mem.query("SELECT started, result, ret FROM runs WHERE inst=? AND step=? ORDER BY started DESC LIMIT 1",
                  (idx, step))
    return r[0] if r else (None, None, None)


def _hhmm(t):
    return time.strftime("%H:%M", time.localtime(t))


# ---------- ban do the gioi ----------
WORLD_STEPS = ("gather", "rebels")   # buoc can ban do the gioi


def world_ready(mem, idx, cfg=None, now=None, recheck_h=6):
    """Ban do the gioi da mo chua (chu du an 2026-11-20: "o < cf6 chua the mo the gioi ngoai").
    - biet cap nha chinh < world.min_hq_level (6) -> chua mo
    - lan thu gan nhat (trong recheck_h gio) nut chuyen ban do khong co tac dung -> chua mo
    - con lai (da mo / chua biet) -> cho thu."""
    now = now or time.time()
    w = (cfg or {}).get("world", {})
    hq = mem.fact(idx, "hq_level")
    if hq is not None and hq < w.get("min_hq_level", 6):
        return False
    r = mem.query("SELECT value, seen_at FROM facts WHERE inst=? AND key='world_open'", (idx,))
    if r and r[0][0] == "false" and now - (r[0][1] or 0) < w.get("recheck_h", recheck_h) * 3600:
        return False
    return True


# ---------- plan() tung trigger ----------
def march_slots(total, used, observed_at, timers, now, unknown_return_s):
    """Doi ranh + lan som nhat co doi ve (A-FIX-1). Luat nam o aowbot.domain.marches; ham nay chi doi sang dang
    cua lich: (so ranh, (luc, ly do, tin cay) | None)."""
    a = marches.availability(marches.MarchObservation(total, used, observed_at, timers), now, unknown_return_s)
    r = a.next_return
    if r is None:
        return a.free, None
    return a.free, (r.at, f"{'uoc luong doi ve' if r.estimated else 'doi ve'} {_hhmm(r.at)}", r.confident)


def typical_return_s(mem, idx, default_s, look=60):
    """Thoi gian tu luc quan sat toi luc doi ve cua cac doi DA doc duoc dong ho o may nay (phan vi 25 %,
    aowbot.domain.marches.lower_quartile) - dung cho doi khong doc duoc dong ho."""
    gaps = []
    for at, rows in mem.query("SELECT at, marches FROM observations WHERE inst=? AND marches IS NOT NULL "
                              "ORDER BY at DESC LIMIT ?", (idx, look)):
        try:
            rows = json.loads(rows or "[]")
        except ValueError:
            continue
        gaps += [m["return_at"] - at for m in rows if isinstance(m, dict) and m.get("return_at")]
    return marches.lower_quartile(gaps, default_s)


def plan_gather(mem, idx, sc, now, cfg=None):
    g = (cfg or {}).get("gather", {})
    if not world_ready(mem, idx, cfg, now):
        return Plan(False, None, "ban do the gioi chua mo")
    hq = mem.fact(idx, "hq_level")
    if g.get("load_ge_mine", True) and hq is not None and hq < g.get("min_hq_level", 9):
        return Plan(False, None, f"nha chinh {hq} < {g.get('min_hq_level', 9)}: chua thu thap")
    total = mem.fact(idx, "march_total")
    timers = mem.timers(idx, "march:")
    if total is None:  # chua doc duoc (vd ban do the gioi chua mo) -> thu lai theo chu ky, khong ghe moi min_gap
        t, _, _ = _last(mem, idx, "gather")
        at = (t or 0) + sc["gather_retry_min"] * 60
        return Plan(at <= now, at, "chua biet so doi hanh quan", confident=False)
    free, nxt = march_slots(total, mem.fact(idx, "march_used"), mem.fact(idx, "observed_at"),
                            [(d, c) for _, d, c, _ in timers], now,
                            typical_return_s(mem, idx, sc["unknown_return_min"] * 60))
    cands = []
    if free > 0:  # co doi ranh: vua gui ma van ranh (khong co mo vua tai trong / het linh) -> cho gather_retry_min
        t, _, _ = _last(mem, idx, "gather")
        cands.append(((t or 0) + sc["gather_retry_min"] * 60, f"{free} doi ranh", True))
    if nxt:  # doi dang di som nhat ve thanh (dong ho that, hoac uoc luong cho doi khong doc duoc dong ho)
        cands.append(nxt)
    arr = mem.timers(idx, "arrive:")
    if arr:  # chu du an 2026-11-21: tat ca doi toi mo -> dang nhap doc gio thu thap xong (chi hien khi da toi mo)
        last_arr = arr[-1][1] + 60
        cands.append((last_arr, f"doi toi mo {_hhmm(arr[-1][1])}: doc gio thu thap", True))
    at, why, conf = min(cands)
    return Plan(at <= now, at, why, confident=conf)


BUILD_STEPS = ("upgrade", "construct", "mainquest", "quests")   # P13e-3: construct cung la buoc xay (lich + chuoi 'tho ranh')


def build_slots(mem, idx, cfg):
    """P13e-1: so tho xay hieu luc cua may = so o game bao (fact builders_total) kep boi cau hinh (xem domain.builders)."""
    bc = (cfg or {}).get("build") or {}
    total = mem.fact(idx, "builders_total")
    try:
        total = int(total) if total is not None else None
    except (TypeError, ValueError):
        total = None
    return builders_dom.effective_max(bc.get("max_builders", 1), total, bc.get("use_game_slots", True),
                                      bc.get("max_builders_cap", 2))


def builder_idle_now(mem, idx, cfg):
    """May dang co tho RANH theo tri nho (observe lan truoc)? -> (bool, busy, toi_da)."""
    busy = mem.fact(idx, "builders_busy")
    maxb = build_slots(mem, idx, cfg)
    try:
        busy = int(busy) if busy is not None else None
    except (TypeError, ValueError):
        busy = None
    return busy is not None and busy < maxb, busy, maxb


def build_streak(rows, since=0):
    """So LAN GHE lien tiep gan nhat (moi nhat truoc) ma moi buoc xay (mainquest/quests) deu khong bat dau duoc
    cong trinh nao (ret 0 / trong / loi - bat ke ket qua ok hay khong, A-FIX-3). Lan chay truoc `since`
    (trang thai doi: vd cap nha chinh moi) khong tinh. rows: [(visit, started, ret)] sap moi -> cu."""
    streak, cur = 0, None
    for visit, started, ret in rows:
        if started < since:
            break
        try:
            v = float(ret) if ret not in (None, "", "null") else 0.0
        except (TypeError, ValueError):
            break                       # gia tri khong phai so = co viec
        if v > 0:
            break
        if visit != cur:
            streak, cur = streak + 1, visit
    return streak


def build_gap_s(streak, sc):
    """Khoang cach giua 2 lan ghe 'tho ranh': min_gap, x2 moi 2 lan ghe trang tay, toi da build_every_min."""
    base = sc["min_gap_min"] * 60
    return min(base * 2 ** (streak // 2), max(base, sc["build_every_min"] * 60))


def plan_build(mem, idx, sc, now, step, cfg=None):
    # so tho dang xay (observe doc icon bua "x/y") < so tho dung duoc (farm 1, TK chinh #1: 2) -> co tho ranh: xay ngay
    busy = mem.fact(idx, "builders_busy")
    maxb = build_slots(mem, idx, cfg)
    if busy is not None and busy < maxb:
        t, _, _ = _last(mem, idx, step)
        gap = sc["min_gap_min"] * 60
        if sc.get("build_backoff", True):
            # 2026-11-21: 111 lan ghe / 13,3 h vi 'tho ranh' ma khong xay duoc -> lan thu truoc trang tay thi gian
            # chu ky; doi cap nha chinh (A-FIX-2: seen_at chi doi khi gia tri doi) -> dem lai tu dau
            ph = ",".join("?" * len(BUILD_STEPS))
            rows = mem.query(f"SELECT visit, started, ret FROM runs WHERE inst=? AND step IN ({ph}) "
                             "ORDER BY started DESC LIMIT 40", (idx, *BUILD_STEPS))
            hq = mem.query("SELECT seen_at FROM facts WHERE inst=? AND key='hq_level'", (idx,))
            streak = build_streak(rows, (hq[0][0] or 0) if hq else 0)
            gap = build_gap_s(streak, sc)
        at = max((t or 0) + gap, now - 1)
        why = f"tho xay ranh ({busy}/{maxb})" + (f", {gap // 60:.0f} phut/lan sau {streak} lan khong xay duoc"
                                                 if gap > sc["min_gap_min"] * 60 else "")
        return Plan(at <= now, at, why)
    tm = mem.timers(idx, "build")
    if tm:
        return Plan(tm[0][1] <= now, tm[0][1], f"xay xong {_hhmm(tm[0][1])}")
    t, _, _ = _last(mem, idx, step)
    at = (t or 0) + sc["build_every_min"] * 60
    return Plan(at <= now, at, "kiem tra xay (chu ky)", confident=False)


def plan_research(mem, idx, sc, now):
    hq = mem.fact(idx, "hq_level")
    need = mem.fact(idx, "research_wait_hq")     # Q3: node can nha chinh len cap -> khong keo may toi khi HQ doi
    if need is not None and (hq is None or hq <= need):
        return Plan(False, None, f"nghien cuu cho nha chinh > {need}")
    if hq is not None and hq < sc["research_hq_min"]:
        return Plan(False, None, f"nha chinh {hq} < {sc['research_hq_min']}: chua mo nghien cuu")
    lab = mem.fact(idx, "research_wait_lab_until")      # dang nang cap Vien nghien cuu de mo node (research.upgrade_lab)
    try:
        lab = float(lab) if lab is not None else None
    except (TypeError, ValueError):
        lab = None
    if lab and lab > now:
        return Plan(False, lab, f"cho nang cap Vien nghien cuu xong {_hhmm(lab)}")
    nores = mem.fact(idx, "research_nores")              # P2: lan truoc thieu tai nguyen -> gian chu ky (research.py)
    try:
        nores = float((nores or {}).get("until") or 0)
    except (TypeError, ValueError, AttributeError):
        nores = 0
    if nores > now:
        return Plan(False, nores, f"nghien cuu thieu tai nguyen, thu lai {_hhmm(nores)}")
    tm = mem.timers(idx, "research")
    if tm:
        return Plan(tm[0][1] <= now, tm[0][1], f"nghien cuu xong {_hhmm(tm[0][1])}")
    t, _, _ = _last(mem, idx, "research")
    q = mem.fact(idx, "queue_research")                  # P2: observe doc duoc "0/1" (anh chu so) -> hang ranh, lam som
    if isinstance(q, (list, tuple)) and len(q) == 2 and q[0] < q[1]:
        # lan ghe truoc khong bat dau duoc (tra 0) -> gian: min_gap x2 moi 2 lan, toi da research_every_min
        rows = mem.query("SELECT ret FROM runs WHERE inst=? AND step='research' ORDER BY started DESC LIMIT 12", (idx,))
        streak = 0
        for (ret,) in rows:
            try:
                if float(ret or 0) > 0:
                    break
            except (TypeError, ValueError):
                pass
            streak += 1
        base = sc["min_gap_min"] * 60
        gap = min(base * 2 ** (streak // 2), max(base, sc["research_every_min"] * 60))
        at = max((t or 0) + gap, now - 1)
        return Plan(at <= now, at, f"hang nghien cuu ranh ({q[0]}/{q[1]})"
                    + (f", {gap // 60:.0f} phut/lan sau {streak} lan khong bat dau duoc" if streak >= 2 else ""))
    at = (t or 0) + sc["research_every_min"] * 60
    return Plan(at <= now, at, "kiem tra nghien cuu (chu ky)", confident=False)


# ---------- phan quan tap kich ----------
def rebels_done_today(mem, idx, now=None, reset_utc=0):
    """So luot Phan quan da danh tu luc reset ngay (tong gia tri buoc 'rebels' tra ve)."""
    now = now or time.time()
    n = 0
    for (ret,) in mem.query("SELECT ret FROM runs WHERE inst=? AND step='rebels' AND started>=?",
                            (idx, last_reset(now, reset_utc))):
        try:
            n += int(float(ret or 0))
        except (TypeError, ValueError):
            pass
    # chu du an 2026-11-21: "Gui Qua Thuong: 7/21" (bang Qua tang lien minh) = da tan cong 21-7 = 14 luot
    # (danh tay hoac bot) -> so doc tu game, lay lon hon so bot tu dem
    g = mem.query("SELECT value, seen_at FROM facts WHERE inst=? AND key='rebels_attacks_game'", (idx,))
    if g and g[0][0] and (g[0][1] or 0) >= last_reset(now, reset_utc):
        try:
            n = max(n, int(float(g[0][0])))
        except (TypeError, ValueError):
            pass
    return n


def rebels_ready(mem, idx, cfg=None, now=None):
    """Chu du an 2026-11-21: nha chinh >= rebels.min_hq_level (15) moi danh; 5 luot/ngay du thi thoi.
    -> (True|False, ly do). Chua biet cap nha chinh -> cho thu (module tu kiem tra man hinh)."""
    rc = (cfg or {}).get("rebels", {})
    hq = mem.fact(idx, "hq_level")
    if hq is not None and hq < rc.get("min_hq_level", 15):
        return False, f"nha chinh {hq} < {rc.get('min_hq_level', 15)}"
    done = rebels_done_today(mem, idx, now, sched_cfg(cfg or {})["daily_reset_utc"])
    if done >= rc.get("daily_target", 5):
        return False, f"da du {done}/{rc.get('daily_target', 5)} luot hom nay"
    return True, f"{done}/{rc.get('daily_target', 5)} luot hom nay"


def plan_rebels(mem, idx, sc, now, cfg=None):
    ok, why = rebels_ready(mem, idx, cfg, now)
    if not ok:
        if "luot hom nay" in why:      # du luot -> lan toi sau reset ngay
            return Plan(False, last_reset(now, sc["daily_reset_utc"]) + 86400, why)
        return Plan(False, None, why)
    if not world_ready(mem, idx, cfg, now):
        return Plan(False, None, "ban do the gioi chua mo")
    t, _, _ = _last(mem, idx, "rebels")
    at = (t or 0) + (cfg or {}).get("rebels", {}).get("every_min", 60) * 60
    return Plan(at <= now, at, f"phan quan {why}")


# ---------- ngay chien tranh + moc the luc ----------
def war_cfg(cfg):
    """Cau hinh warday day du (aowbot.domain.warday.wcfg: lich tuan, cong tac tay, khien)."""
    return warday.wcfg((cfg or {}).get("warday"))


def _fnum(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def war_days(mem, idx, cfg, now=None):
    """Ngay chien tranh: lich tuan + cong tac tay + bang thong bao / banner + ngay khai tay (chu du an 2026-11-23)."""
    return warday.resolve_days(war_cfg(cfg), _fnum(mem.fact(idx, "war_notice_seen")), now or time.time(),
                               _fnum(mem.fact(idx, "war_banner_seen")))


def war_window(mem, idx, cfg, now):
    c = war_cfg(cfg)
    return warday.active_window(now, war_days(mem, idx, cfg, now), c["lead_h"], c["tail_min"])


def war_blocks(mem, idx, step, cfg, now):
    """Buoc dua quan ra ngoai thu thap bi cam trong cua so chien tranh (phan quan duoc phep)."""
    return war_cfg(cfg)["enabled"] and step in warday.BLOCK_STEPS and war_window(mem, idx, cfg, now) is not None


def timed_login_due(mem, idx, cfg, now):
    """P7-11: dang trong khung "Dang nhap hen gio" (18-19h / 8-9h UTC) ma chua ghe nhan."""
    c = war_cfg(cfg)
    return bool(c["enabled"] and c["timed_login"] and warday.timed_login_due(
        now, _fnum(mem.fact(idx, "timed_login_at")), c["timed_login_windows_utc"], c["timed_login_delay_min"]))


def stamina_due(mem, idx, cfg, now):
    """Moc the luc 0h/8h/15h UTC hoac khung Dang nhap hen gio (P7-11) -> notify/rewards chay kem de nhan."""
    c = war_cfg(cfg)
    return bool(c["enabled"] and c["stamina"] and warday.stamina_due(now, mem.fact(idx, "stamina_claim_at"),
                                                                      c["stamina_delay_min"])) \
        or timed_login_due(mem, idx, cfg, now)


def plan_warday(mem, idx, sc, now, cfg=None):
    """Keo may len dung moc the luc (0h/8h/15h UTC) va dung gio can bat/gia han khien ngay chien tranh."""
    c = war_cfg(cfg)
    if not c["enabled"]:
        return None
    cands = []
    if c["stamina"]:
        at = warday.stamina_next_at(now, mem.fact(idx, "stamina_claim_at"), c["stamina_delay_min"])
        cands.append((at, "moc the luc " + _hhmm_utc(warday.last_stamina_mark(max(at, now)))))
    if c["timed_login"]:    # P7-11: hen gio co dinh - ghe moi may trong khung Dang nhap hen gio
        at = warday.timed_login_next_at(now, _fnum(mem.fact(idx, "timed_login_at")), c["timed_login_windows_utc"],
                                        c["timed_login_delay_min"])
        if at is not None:
            cands.append((at, "dang nhap hen gio " + _hhmm_utc(at)))
    until = max([x for x in (_fnum(mem.fact(idx, "shield_until")), _fnum(mem.fact(idx, "war_shield_until")))
                 if x is not None] or [0.0]) or None
    sp = warday.shield_plan(now, war_days(mem, idx, cfg, now), until, c, _fnum(mem.fact(idx, "peace_at")))
    if sp.at is not None:
        cands.append((sp.at, sp.why))
    if not cands:
        return None
    at, why = min(cands)
    return Plan(at <= now, at, why)


def _hhmm_utc(t):
    return time.strftime("%H:%M UTC", time.gmtime(t))


def plan_step(mem, idx, step, sc, now, enabled, cfg=None):
    if step == "warday":
        return plan_warday(mem, idx, sc, now, cfg)
    if step in warday.BLOCK_STEPS and war_blocks(mem, idx, step, cfg, now):
        w = war_window(mem, idx, cfg, now)
        return Plan(False, w.end, "ngay chien tranh: cam thu thap")
    if step == "rebels":
        return plan_rebels(mem, idx, sc, now, cfg)
    if step == "gather":
        if enabled.get("tutorial") and not mem.fact(idx, "tutorial_done"):
            # dang tan thu: ban do the gioi chua mo, nha chinh < min_hq_level -> khong keo may moi gio (#4 2026-11-19)
            return Plan(False, None, "dang tan thu: chua thu thap")
        return plan_gather(mem, idx, sc, now, cfg)
    if step == "upgrade":       # Q2: xay theo nha chinh - HQ da toi gioi han (30 = toi da) thi bo muc tieu xay
        hq, cap = mem.fact(idx, "hq_level"), ((cfg or {}).get("build") or {}).get("hq_max_level", 30)
        if hq is not None and hq >= cap:
            return None
        return plan_build(mem, idx, sc, now, step, cfg)
    if step in ("mainquest", "quests", "construct"):
        return plan_build(mem, idx, sc, now, step, cfg)
    if step == "research":
        return plan_research(mem, idx, sc, now)
    if step == "tutorial" and enabled.get("tutorial") and not mem.fact(idx, "tutorial_done"):
        if mem.fact(idx, "tutorial_need_power") or (mem.fact(idx, "tutorial_wait_until") or 0) > now:
            return None  # thua lien, dang cho tang luc chien -> khong keo may, chi chay kem (extra_every_min)
        # chu ky rieng: neu khong 4 may dang bat tan thu se duoc ghe moi min_gap phut (ke ca may dang ket, #4 2026-11-19)
        t, _, _ = _last(mem, idx, "tutorial")
        at = (t or 0) + sc["tutorial_every_min"] * 60
        return Plan(at <= now, at, "tan thu chua xong")
    return None  # khong phai trigger


DAILY = ("daily", "rewards", "notify", "play")   # play: 3 luot dau truong mien phi + cuop boc theo ngay
STAMINA_STEPS = ("notify", "rewards")   # moc the luc: nhan qua online/phuc loi
# xep vao moi lan ghe; tu gioi han ben trong: reddots (tan suat/thoi gian - A-OPT-1, PM 2026-11-23), heal (bot/stepgate.py)
ALWAYS = ("reddots", "heal")


def last_reset(now, hour_utc):
    day = 86400
    t = (now // day) * day + hour_utc * 3600
    return t if t <= now else t - day


def extra_due(mem, idx, step, sc, now):
    """Buoc chay kem: chi chay neu lan chay cuoi da qua extra_every_min, hoac (buoc theo ngay) chua chay tu luc reset."""
    t, _, _ = _last(mem, idx, step)
    if t is None:
        return True
    if step in DAILY and t < last_reset(now, sc["daily_reset_utc"]):
        return True
    return now - t >= sc["extra_every_min"] * 60 * value_factor(mem, idx, step)


def value_factor(mem, idx, step, look=4, cap=4):
    """H3: buoc chay kem lien tiep TRANG TAY (ket qua ok nhung tra ve 0) o may nay -> gian chu ky x2, x4 (toi da cap).
    Buoc vua co viec -> chu ky binh thuong. Gia tri tra ve khong phai so (dict...) coi nhu co viec."""
    zeros = 0
    for res, ret in mem.query("SELECT result, ret FROM runs WHERE inst=? AND step=? ORDER BY started DESC LIMIT ?",
                              (idx, step, look)):
        try:
            v = float(ret) if ret not in (None, "", "null") else 0.0
        except (TypeError, ValueError):
            break
        if res != "ok" or v != 0:
            break
        zeros += 1
    return min(cap, 2 ** (zeros // 2)) if zeros >= 2 else 1


def last_visit_end(mem, idx):
    r = mem.query("SELECT MAX(COALESCE(ended, started)) FROM visits WHERE inst=?", (idx,))
    return r[0][0] if r and r[0][0] else None


FORCE_BUILD = ("construct", "upgrade", "mainquest")   # P13e-3: tho ranh -> 3 buoc nay luon vao luot (neu may bat chung)


def with_build_steps(mem, idx, steps, names, order, cfg, now):
    """P13e-3: may dang co tho RANH (tri nho) -> them construct/upgrade/mainquest vao luot du bi stepgate gian chu ky /
    thieu trigger (lan 02:15, 04:51, 07:35 #5: construct+mainquest bi tat). Buoc bi loi-backoff (watchdog) van bo qua.
    Giu thu tu `order`."""
    idle, _, _ = builder_idle_now(mem, idx, cfg)
    if not idle:
        return steps
    add = [n for n in FORCE_BUILD if n in names and n not in steps and mem.backoff_until(idx, n) <= now]
    if not add:
        return steps
    pos = {n: i for i, n in enumerate(order)}
    return sorted(set(steps) | set(add), key=lambda n: pos.get(n, 99))


def decide_one(mem, idx, order, enabled, cfg, now):
    """-> Visit (at co the > now = chua toi luc)."""
    sc = sched_cfg(cfg)
    names = [n for n in order if enabled.get(n)]
    if rollout.agent_active(cfg):   # P6: chi khi cong tac chung agent.enabled bat
        names = [n for n in names if n != "gather"]   # SCH-X: hanh quan cua may nay do agent lo
    backoff = {n for n in names if mem.backoff_until(idx, n) > now}
    # P1: buoc dang gian chu ky / chua du dieu kien (bot.stepgate) -> khong chay; trigger da toi han cua no khong keo
    # may (truoc day mainquest tra 0 van keo may moi min_gap); hen tuong lai (vd moc the luc cua warday) van giu
    backoff |= {n for n in names if stepgate.planned_skip(mem, idx, n, cfg, now)}
    last = last_visit_end(mem, idx)
    plans = {n: plan_step(mem, idx, n, sc, now, enabled, cfg) for n in names}
    trig = {n: p for n, p in plans.items() if p is not None
            and (n not in backoff or (mem.backoff_until(idx, n) <= now and p.at is not None and p.at > now))}
    cap = (last or 0) + sc["max_gap_min"] * 60
    soon = now + sc["batch_window_min"] * 60
    nexts = [p.at for p in trig.values() if p.at is not None]
    at = min(nexts + [cap])
    why = [f"{n}: {p.why}" for n, p in trig.items() if p.at is not None and p.at <= max(at, soon)]
    full = cap <= max(at, now) and not why
    if last is not None:
        at = max(at, last + sc["min_gap_min"] * 60)
    if full:
        why = [f"tran an toan {sc['max_gap_min']} phut khong ghe"]
        steps = [n for n in names if n not in backoff]
    else:
        ready_at = max(at, now) + sc["batch_window_min"] * 60
        steps = []
        for n in names:
            if n in backoff:
                continue
            p = plans[n]
            if p is None:
                if n in ALWAYS or extra_due(mem, idx, n, sc, now) or (n in STAMINA_STEPS and stamina_due(mem, idx, cfg, now)):
                    steps.append(n)  # buoc chay kem (theo chu ky rieng / sau reset ngay / moc the luc)
            elif p.ready or (p.at is not None and p.at <= ready_at) or not p.confident:
                steps.append(n)  # trigger toi han / uoc luong theo chu ky (ghe thi kiem tra luon)
        if steps:
            steps = with_build_steps(mem, idx, steps, names, order, cfg, now)   # P13e-3
    return Visit(idx, at, steps, "; ".join(why) or "khong ro", full)


def piggyback_steps(mem, idx, order, enabled, cfg, now):
    """May DA BAT san (lan ghe agent): buoc cu toi han trong cua so gop + buoc chay kem (reddots, chu ky rieng).
    Vi sao: lan ghe agent tung chi gui quan roi tat may -> cham do / qua bi bo qua du may da ton ~70 s khoi dong."""
    sc = sched_cfg(cfg)
    names = [n for n in order if enabled.get(n)]
    if rollout.agent_active(cfg):   # P6: chi khi cong tac chung agent.enabled bat
        names = [n for n in names if n != "gather"]
    soon = now + sc["batch_window_min"] * 60
    out = []
    for n in names:
        if mem.backoff_until(idx, n) > now or stepgate.planned_skip(mem, idx, n, cfg, now):
            continue
        p = plan_step(mem, idx, n, sc, now, enabled, cfg)
        if p is None:
            if n in ALWAYS or extra_due(mem, idx, n, sc, now) or (n in STAMINA_STEPS and stamina_due(mem, idx, cfg, now)):
                out.append(n)
        elif p.ready or (p.at is not None and p.at <= soon) or not p.confident:
            out.append(n)
    return with_build_steps(mem, idx, out, names, order, cfg, now) if out else out


def decide(mem, insts, order, enabled_for, cfg_for, now=None):
    """insts: list idx dang bat auto. enabled_for(idx)/cfg_for(idx) -> dict. Tra ve Visit sap theo at."""
    now = now or time.time()
    out = [decide_one(mem, i, order, enabled_for(i), cfg_for(i), now) for i in insts]
    return sorted(out, key=lambda v: v.at)
