"""G0 (docs/strategy/session-drain-proposal.md): so do CHI DOC cho de xuat "xa viec theo phien". Doc data/memory.db.

  python tools/measure_g0.py                 # toan bo du lieu
  python tools/measure_g0.py --since 72      # 72 gio gan nhat
  python tools/measure_g0.py --json

Chi so:
  downtime        khoang >30 phut khong co lan ghe nao (runner/web khong chay hoac khong dat lich)
  idle            thoi gian ranh uoc luong cua o tai nguyen (build/research/train) theo may:
                  quan sat ranh -> tinh toi quan sat ke tiep (can tren; quan sat chi co khi ghe may)
  nav             so thao tac dieu huong (bang nav) tren moi lan ghe / moi buoc; ti le 'back' va ve 'city'
  steps           moi buoc: so lan, ti le ret=0 (khong lam gi), ti le loi/warn, phut
  visits          ket qua cac lan ghe (ok/stopped/...) va thoi luong
"""
import argparse, json, os, sqlite3, statistics, sys, time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "memory.db")
GAP_S = 1800


def since_ts(s):
    if s is None:
        return 0.0
    try:
        return time.time() - float(s) * 3600
    except ValueError:
        return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M"))


def fmt(t):
    return time.strftime("%m-%d %H:%M", time.localtime(t))


def num(v):
    try:
        return float(v) if v not in (None, "", "null") else 0.0
    except (TypeError, ValueError):
        return None


def downtime(c, t0):
    ts = [r[0] for r in c.execute("select started from visits where started>=? order by started", (t0,))]
    gaps = [(a, b) for a, b in zip(ts, ts[1:]) if b - a > GAP_S]
    return {"visits": len(ts), "gaps": [(fmt(a), fmt(b), round((b - a) / 3600, 1)) for a, b in gaps],
            "gap_h": round(sum(b - a for a, b in gaps) / 3600, 1),
            "span_h": round((ts[-1] - ts[0]) / 3600, 1) if len(ts) > 1 else 0}


def idle(c, t0):
    out = {}
    now = time.time()
    for inst, kind in c.execute("select distinct inst, kind from queue_obs where at>=?", (t0,)).fetchall():
        rows = c.execute("select at, used, total from queue_obs where inst=? and kind=? and at>=? order by at",
                         (inst, kind, t0)).fetchall()
        if len(rows) < 2:
            continue
        idle_s = obs_s = 0.0
        for (a, u, tot), (b, _, _) in zip(rows, rows[1:]):
            obs_s += b - a
            if tot and u < min(tot, 1 if kind == "build" else tot):   # farm: 1 tho xay dung duoc
                idle_s += b - a
        out.setdefault(inst, {})[kind] = {"idle_pct_upper": round(100 * idle_s / obs_s, 1) if obs_s else None,
                                          "span_h": round(obs_s / 3600, 1), "obs": len(rows)}
    return out


def nav(c, t0):
    visits = c.execute("select id from visits where started>=?", (t0,)).fetchall()
    per_visit = {r[0]: r[1] for r in c.execute(
        "select visit, count(*) from nav where at>=? group by visit", (t0,))}
    n = list(per_visit.values())
    by_action = dict(c.execute("select action, count(*) from nav where at>=? group by action", (t0,)).fetchall())
    to_city = c.execute("select count(*) from nav where at>=? and screen='city'", (t0,)).fetchone()[0]
    per_step = {r[0]: (r[1], r[2]) for r in c.execute(
        "select step, count(*), count(distinct visit) from nav where at>=? group by step order by 2 desc limit 12", (t0,))}
    return {"visits": len(visits), "nav_total": sum(n),
            "nav_per_visit_med": statistics.median(n) if n else 0,
            "by_action": by_action, "city_events": to_city,
            "top_steps_nav": {k: {"nav": v[0], "per_visit": round(v[0] / v[1], 1)} for k, v in per_step.items()}}


def steps(c, t0):
    d = defaultdict(lambda: {"n": 0, "zero": 0, "bad": 0, "sec": 0.0})
    for step, dur, res, ret in c.execute("select step, dur, result, ret from runs where started>=?", (t0,)):
        s = d[step]
        s["n"] += 1
        s["sec"] += dur or 0
        if res not in ("ok", None):
            s["bad"] += 1
        if num(ret) == 0.0:
            s["zero"] += 1
    return {k: {"n": v["n"], "zero_pct": round(100 * v["zero"] / v["n"]), "bad_pct": round(100 * v["bad"] / v["n"]),
                "min": round(v["sec"] / 60, 1)} for k, v in sorted(d.items(), key=lambda kv: -kv[1]["sec"])}


def visits(c, t0):
    by = defaultdict(lambda: [0, 0.0])
    for res, st, en in c.execute("select result, started, ended from visits where started>=?", (t0,)):
        b = by[res or "(chua ket)"]
        b[0] += 1
        b[1] += ((en or st) - st)
    return {k: {"n": v[0], "avg_min": round(v[1] / v[0] / 60, 1)} for k, v in by.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    t0 = since_ts(a.since)
    res = {"downtime": downtime(c, t0), "idle": idle(c, t0), "nav": nav(c, t0), "steps": steps(c, t0),
           "visits": visits(c, t0)}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
        return
    d = res["downtime"]
    print(f"== Downtime: {d['visits']} lan ghe / {d['span_h']}h, khoang >30p khong ghe: {d['gap_h']}h")
    for g in d["gaps"][:15]:
        print("   ", *g)
    print("== Ranh o tai nguyen (can tren %, theo may)")
    for i, k in sorted(res["idle"].items()):
        print(f"   #{i}", {kk: f"{v['idle_pct_upper']}% /{v['span_h']}h" for kk, v in k.items()})
    n = res["nav"]
    print(f"== Dieu huong: {n['nav_total']} thao tac / {n['visits']} lan ghe (trung vi {n['nav_per_visit_med']}/lan)")
    print("   theo hanh dong:", n["by_action"], "| lan ve city:", n["city_events"])
    print("   buoc nhieu nav nhat:", n["top_steps_nav"])
    print("== Buoc (theo thoi gian): ten  lan  %ret0  %loi  phut")
    for k, v in res["steps"].items():
        print(f"   {k:12s} {v['n']:4d} {v['zero_pct']:4d}% {v['bad_pct']:4d}% {v['min']:7.1f}")
    print("== Lan ghe:", res["visits"])


if __name__ == "__main__":
    main()
