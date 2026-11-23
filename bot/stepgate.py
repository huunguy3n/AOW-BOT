"""P1 'On dinh nen' (PM duyet 2026-11-23): dieu kien truoc khi chay + gian chu ky khi tra 0, theo may.

Do 21-22/11 (logs/pm-audit-1.txt): heal 45/45, campaign 14/14, warday 22/22, mainquest 32/33 lan tra 0 - moi lan
ghe deu mo game ra xem roi khong lam gi. Hai lop:

1. precheck(mem, idx, step, cfg, now, done) - KHONG mo man hinh, chi doc tri nho (memory.db facts):
   - warday   : chi chay khi toi moc the luc (0h/8h/15h UTC) hoac dang trong cua so ngay chien tranh. Bat buoc
                (must) khi toi han - khong bi lop 2 chan.
   - mainquest: dang cho cong trinh nhiem vu xay xong (mainquest_busy_until) / dang cho luc chien tang
                (mainquest_need_power > luc chien quan sat gan nhat) -> bo.
   - campaign : lan truoc khong du doan thang (campaign_need_power) va luc chien chua tang du, Loi ich treo may
                chua toi han nhan (campaign.idle_claim_h) -> bo.
   - heal     : bong bong chua tri (observe ghi heal_bubble) khong thay o lan quan sat gan nhat va trong lan ghe
                nay chua co tran nao (phan quan / phong thu) -> bo. Thay bong bong / vua danh -> bat buoc.
   Bo vi dieu kien qua stepgate.max_skip_h gio -> van chay 1 lan de kiem tra (luoi an toan khi tri nho sai).
2. Gian chu ky: buoc trong stepgate.steps chay xong 'ok' ma tra 0 lien tiep >= after lan -> tam bo
   min(base_min x 2^(n-after), cap_h) - luu fact 'idle:<buoc>' = {zeros, until} theo may (+ state.json idle_backoff
   cho web). Lam duoc viec (tra > 0) -> xoa. Loi/ket do runner._backoff lo (bang backoff rieng).

Ham thuan tren `mem` (fact/query) -> test offline (tests/legacy/test_stepgate.py).
"""
import time
from dataclasses import dataclass

from aowbot.domain import drain, warday as W

DEFAULTS = {"enabled": True, "steps": ["heal", "campaign", "warday", "mainquest"], "after": 2, "base_min": 60,
            "cap_h": 8, "max_skip_h": 6}
FIGHT_STEPS = ("rebels", "defense")   # trong lan ghe co tran -> co the co thuong binh -> heal bat buoc


@dataclass(frozen=True)
class Gate:
    run: bool
    why: str = ""
    must: bool = False     # dieu kien noi CAN chay ngay (bo qua gian chu ky)


def gcfg(cfg):
    return {**DEFAULTS, **((cfg or {}).get("stepgate") or {})}


def power(mem, idx):
    r = mem.fact(idx, "resources") or {}
    p = r.get("power") if isinstance(r, dict) else None
    return p if isinstance(p, (int, float)) and p > 0 else None


def _last_run(mem, idx, step):
    r = mem.query("SELECT started FROM runs WHERE inst=? AND step=? ORDER BY started DESC LIMIT 1", (idx, step))
    return r[0][0] if r and r[0][0] else None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def precheck(mem, idx, step, cfg, now=None, done=None):
    """-> Gate. done: {buoc: ret} cua lan ghe nay (None = goi tu lich, chua biet)."""
    now = now or time.time()
    g = gcfg(cfg)
    if not g["enabled"]:
        return Gate(True, "stepgate tat")
    if step == "warday":
        c = W.wcfg((cfg or {}).get("warday"))
        if not c["enabled"]:
            return Gate(False, "warday tat")
        if c["stamina"] and W.stamina_due(now, _num(mem.fact(idx, "stamina_claim_at")), c["stamina_delay_min"]):
            return Gate(True, "moc the luc", must=True)
        if W.window_now(c, _num(mem.fact(idx, "war_notice_seen")), now,
                        _num(mem.fact(idx, "war_banner_seen"))) is not None:
            return Gate(True, "cua so ngay chien tranh", must=True)
        return Gate(False, "chua toi moc the luc, ngoai ngay chien tranh")
    if step == "heal":
        if done and any(drain.worked(done.get(s)) for s in FIGHT_STEPS):
            return Gate(True, "vua co tran trong lan ghe", must=True)
        bub = mem.fact(idx, "heal_bubble")
        if bub is True:
            return Gate(True, "thay bong bong chua tri", must=True)
        if bub is False:
            return _soft(mem, idx, step, now, g, "lan quan sat truoc khong thay bong bong chua tri")
        return Gate(True, "chua biet benh vien")
    if step == "mainquest":
        until = _num(mem.fact(idx, "mainquest_busy_until"))
        if until and until > now:
            return Gate(False, "cong trinh nhiem vu dang xay toi " + time.strftime("%H:%M", time.localtime(until)))
        need, p = _num(mem.fact(idx, "mainquest_need_power")), power(mem, idx)
        if need and p and p < need:
            return _soft(mem, idx, step, now, g, f"cho luc chien {p:.0f} >= {need:.0f}")
        return Gate(True)
    if step == "campaign":
        need, p = _num(mem.fact(idx, "campaign_need_power")), power(mem, idx)
        if need and p and p < need:
            claim = _num(mem.fact(idx, "campaign_idle_at")) or 0
            idle_h = ((cfg or {}).get("campaign") or {}).get("idle_claim_h", 8)
            if now - claim < idle_h * 3600:
                return _soft(mem, idx, step, now, g, f"man ke tiep cho luc chien {p:.0f} >= {need:.0f}")
            return Gate(True, "toi han nhan Loi ich treo may", must=True)
        return Gate(True)
    return Gate(True)


def _soft(mem, idx, step, now, g, why):
    """Bo vi dieu kien - nhung qua max_skip_h gio chua chay thi chay 1 lan kiem tra."""
    last = _last_run(mem, idx, step)
    if g["max_skip_h"] and (last is None or now - last >= g["max_skip_h"] * 3600):
        return Gate(True, f"{why} - da {g['max_skip_h']} gio chua kiem tra")
    return Gate(False, why)


# ---------- gian chu ky khi tra 0 ----------
def idle_state(mem, idx, step):
    s = mem.fact(idx, f"idle:{step}")
    return s if isinstance(s, dict) else {"zeros": 0, "until": 0}


def idle_until(mem, idx, step, cfg=None):
    if cfg is not None and step not in gcfg(cfg)["steps"]:
        return 0
    return idle_state(mem, idx, step).get("until") or 0


def check(mem, idx, step, cfg, now=None, done=None):
    """Runner goi truoc khi chay buoc. -> Gate (run False = bo buoc, why = ly do ghi log)."""
    now = now or time.time()
    g = gcfg(cfg)
    if not g["enabled"]:
        return Gate(True)
    p = precheck(mem, idx, step, cfg, now, done)
    if not p.run or p.must:
        return p
    u = idle_until(mem, idx, step, cfg)
    if u > now:
        z = idle_state(mem, idx, step).get("zeros", 0)
        return Gate(False, f"tra 0 {z} lan lien tiep - gian chu ky toi " + time.strftime("%H:%M", time.localtime(u)))
    return p


def record(mem, idx, step, res, ret, cfg, now=None):
    """Runner goi sau khi chay buoc. -> thoi diem het tam bo (0 = khong tam bo)."""
    now = now or time.time()
    g = gcfg(cfg)
    if not g["enabled"] or step not in g["steps"] or res not in ("ok", "warn", "miss"):
        return 0
    if drain.worked(ret):
        if idle_state(mem, idx, step).get("zeros"):
            mem.set_fact(idx, f"idle:{step}", None)
        return 0
    z = int(idle_state(mem, idx, step).get("zeros", 0)) + 1
    until = 0
    if z >= g["after"]:
        until = now + min(g["base_min"] * 60 * 2 ** (z - g["after"]), g["cap_h"] * 3600)
    mem.set_fact(idx, f"idle:{step}", {"zeros": z, "until": until})
    return until


def planned_skip(mem, idx, step, cfg, now=None):
    """Lich (scheduler) co nen bo buoc nay khong: dang gian chu ky / dieu kien khong thoa. heal khong bo o lich
    (phu thuoc tran trong lan ghe - runner quyet)."""
    if step == "heal" or step not in gcfg(cfg)["steps"] or not gcfg(cfg)["enabled"]:
        return False
    return not check(mem, idx, step, cfg, now).run


def snapshot(mem, idx, cfg, now=None):
    """{buoc: {zeros, until}} dang tam bo -> state.json (web)."""
    now = now or time.time()
    out = {}
    for s in gcfg(cfg)["steps"]:
        st = idle_state(mem, idx, s)
        if (st.get("until") or 0) > now:
            out[s] = st
    return out
