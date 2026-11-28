"""M2 (lo trinh ML): so lieu chi-doc cho web / report tu memory.db - KHONG doi hanh vi bot.

- battles(): M2-1 tong hop bang battle_ev theo loai tran + M2-2 mo hinh xac suat thang (che do bong) + do chuan.
- steps(): M2-3 gia tri moi buoc (lam duoc viec / phut) + thu tu de xuat so voi ORDER hien tai.
- hq(): M2-4 nha chinh dung yen theo may + ly do chinh tu cac buoc xay dung.
"""
import json
import logging
import time

from aowbot.domain import battle_model, hqstall, stepvalue

log = logging.getLogger("aow")


def battles(mem, days=7, now=None):
    now = time.time() if now is None else now
    since = now - days * 86400
    by = [{"kind": k, "decision": d, "result": r, "n": n} for k, d, r, n in mem.query(
        "SELECT kind, decision, COALESCE(result, '?'), COUNT(*) FROM battle_ev WHERE at>? GROUP BY 1, 2, 3 "
        "ORDER BY 1, 4 DESC", (since,))]
    from bot import battles as B
    ms = B.models(mem, now)
    models = [{"kind": k, "n": m.n, "wins": m.wins, "a": round(m.a, 3), "b": round(m.b, 3),
               "ratio_80": None if m.ratio_for(0.8) is None else round(m.ratio_for(0.8), 3)} for k, m in ms.items()]
    cal = battle_model.calibration({"p_win": p, "result": r} for p, r in mem.query(
        "SELECT p_win, result FROM battle_ev WHERE at>? AND p_win IS NOT NULL", (since,)))
    need = [{"kind": k, "n": n, "need": max(0, battle_model.MIN_N - n)} for k, n in mem.query(
        "SELECT kind, COUNT(*) FROM battle_ev WHERE result IN ('win','lose') AND ours IS NOT NULL "
        "AND enemy IS NOT NULL GROUP BY kind", ())]
    return {"by": by, "models": models, "calibration": cal, "data": need}


def steps(mem, days=3, now=None):
    now = time.time() if now is None else now
    rows = mem.query("SELECT step, dur, ret FROM runs WHERE started>?", (now - days * 86400,))
    vals = stepvalue.values(rows)
    try:
        from bot.runner import ORDER
        current = [n for n, _ in ORDER]
    except Exception:
        current = [v.step for v in vals]
    return {"values": [v.as_dict() for v in vals], "order_now": current,
            "order_suggest": stepvalue.suggest_order(current, vals)}


def hq(mem, days=2, now=None):
    now = time.time() if now is None else now
    out = []
    try:
        hist = {i: sorted((float(t), int(lv)) for t, lv in json.loads(v))
                for i, v in mem.query("SELECT inst, value FROM facts WHERE key='hq_history'")}
    except Exception as e:
        log.debug("mlinsight.hq: %s", e)
        hist = {}
    plans = {}
    for i, v in mem.query("SELECT inst, value FROM facts WHERE key='hq_plan'"):
        try:
            plans[i] = json.loads(v).get("status")
        except (TypeError, ValueError):
            pass
    for inst in sorted(hist):
        runs = mem.query("SELECT step, ret, note FROM runs WHERE inst=? AND started>?", (inst, now - days * 86400))
        out.append(hqstall.diagnose(inst, hist[inst], runs, now, plan=plans.get(inst)).as_dict())
    return out


def all(mem):
    out = {}
    for name, fn in (("battles", battles), ("steps", steps), ("hq", hq)):
        try:
            out[name] = fn(mem)
        except Exception as e:
            log.debug("mlinsight.%s: %s", name, e)
            out[name] = None
    return out
