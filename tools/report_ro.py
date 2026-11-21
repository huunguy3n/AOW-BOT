"""F4-lite: so do truoc/sau cho moi task (docs/strategy/performance-baseline.md §3). CHI DOC data/memory.db.

  python tools/report_ro.py                         # toan bo du lieu
  python tools/report_ro.py --since 24              # 24 gio gan nhat (hoac --since "2026-11-21 08:00")
  python tools/report_ro.py --split "2026-11-22 09:00"   # so 2 khoang truoc / sau moc (vd luc ap dung 1 ban sua)
  python tools/report_ro.py --inst 1 --json         # 1 may, xuat JSON

Chi so (cung cach tinh o moi lan chay de so sanh duoc):
  vm_h, visits, by_result      gio may bat, so lan ghe, theo ket qua
  start_med_s, start_p90_s     bat may -> buoc dau (lan ghe 'ok')
  useless_visits/_h            lan ghe smart ma moi buoc trigger trong ly do deu tra ve 0
  reasons                      lan ghe smart theo ly do (da bo gio/so)
  steps                        theo buoc: lan, phut, so lan tra 0, phut tra 0
"""
import argparse, json, os, re, sqlite3, statistics, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.memory import DB, Memory  # noqa: E402


def parse_time(s):
    """'24' -> 24 gio truoc; 'YYYY-mm-dd HH:MM' -> gio may. None -> None."""
    if s is None:
        return None
    try:
        return time.time() - float(s) * 3600
    except ValueError:
        return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M"))


def _num(ret):
    try:
        return float(ret) if ret not in (None, "", "null") else 0.0
    except (TypeError, ValueError):
        return None             # gia tri khong phai so (dict...) = co viec


def reason_key(part):
    """'gather: doi ve 11:31' -> 'gather: doi ve HH:MM'; so -> #. De gom lan ghe cung ly do."""
    return re.sub(r"\d+", "#", re.sub(r"\d\d:\d\d", "HH:MM", part.strip()))


def trigger_steps(why):
    """Ly do smart 'mainquest: ...; quests: ...' -> {'mainquest', 'quests'}."""
    return {p.split(":", 1)[0].strip() for p in (why or "").split(";") if ":" in p}


def _pct(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * p))], 1) if xs else None


def metrics(q, t0=None, t1=None, insts=None):
    """q(sql, args) -> rows. Ham chi doc, tinh tren khoang [t0, t1) theo visits.started."""
    t0, t1 = t0 or 0, t1 or 1e12
    cond, args = "started>=? AND started<?", [t0, t1]
    if insts:
        cond += f" AND inst IN ({','.join('?' * len(insts))})"
        args += list(insts)
    visits = q(f"SELECT id, inst, started, ended, result, why, mode FROM visits WHERE {cond}", args)
    out = {"visits": len(visits), "vm_h": 0.0, "by_result": {}, "reasons": {}, "useless_visits": 0,
           "useless_h": 0.0, "start_med_s": None, "start_p90_s": None, "steps": {}}
    starts = []
    for vid, _inst, st, en, res, why, mode in visits:
        dur = (en or st) - st
        out["vm_h"] += dur / 3600
        out["by_result"][res] = out["by_result"].get(res, 0) + 1
        runs = q("SELECT step, started, ret FROM runs WHERE visit=? ORDER BY started", (vid,))
        if res == "ok" and runs:
            starts.append(runs[0][1] - st)
        if mode == "smart":
            for part in (why or "").split(";"):
                k = reason_key(part)
                out["reasons"][k] = out["reasons"].get(k, 0) + 1
            trig = trigger_steps(why)
            vals = [_num(r) for s, _, r in runs if s in trig]
            if trig and vals and all(v == 0 for v in vals):
                out["useless_visits"] += 1
                out["useless_h"] += dur / 3600
    out["start_med_s"], out["start_p90_s"] = (round(statistics.median(starts), 1) if starts else None,
                                              _pct(starts, 0.9))
    rcond = cond.replace("started", "r.started").replace("inst", "r.inst")
    for step, dur, ret in q(f"SELECT step, dur, ret FROM runs r WHERE {rcond}", args):
        s = out["steps"].setdefault(step, {"n": 0, "min": 0.0, "zero": 0, "zero_min": 0.0})
        s["n"] += 1
        s["min"] += (dur or 0) / 60
        if step != "observe" and _num(ret) == 0:     # runner khong ghi ret cua observe
            s["zero"] += 1
            s["zero_min"] += (dur or 0) / 60
    out["vm_h"], out["useless_h"] = round(out["vm_h"], 2), round(out["useless_h"], 2)
    for s in out["steps"].values():
        s["min"], s["zero_min"] = round(s["min"], 1), round(s["zero_min"], 1)
    return out


def show(title, m):
    print(f"== {title}")
    print(f"   lan ghe {m['visits']}, gio may {m['vm_h']}, ket qua {m['by_result']}")
    print(f"   bat may -> buoc dau: trung vi {m['start_med_s']} s, p90 {m['start_p90_s']} s")
    print(f"   lan ghe smart vo ich (buoc trigger deu tra 0): {m['useless_visits']} ({m['useless_h']} h)")
    for k, n in sorted(m["reasons"].items(), key=lambda kv: -kv[1])[:8]:
        print(f"     {n:4d}  {k}")
    print(f"   {'buoc':<13}{'lan':>5}{'phut':>8}{'tra 0':>7}{'phut tra 0':>12}")
    for step, s in sorted(m["steps"].items(), key=lambda kv: -kv[1]["min"]):
        print(f"   {step:<13}{s['n']:>5}{s['min']:>8}{s['zero']:>7}{s['zero_min']:>12}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--since", help="N gio truoc, hoac 'YYYY-mm-dd HH:MM'")
    ap.add_argument("--until", help="nhu --since")
    ap.add_argument("--split", help="moc 'YYYY-mm-dd HH:MM': in 2 khoang truoc / sau")
    ap.add_argument("--inst", help="vd 0,5")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.db):
        sys.exit(f"Khong co {a.db}")
    mem = Memory(a.db, readonly=True)

    def q(sql, args=()):
        try:
            return mem._conn().execute(sql, args).fetchall()
        except sqlite3.Error as e:
            sys.exit(f"Loi doc {a.db}: {e}")
    insts = [int(x) for x in a.inst.split(",")] if a.inst else None
    t0, t1 = parse_time(a.since), parse_time(a.until)
    if a.split:
        mid = parse_time(a.split)
        res = {"truoc": metrics(q, t0, mid, insts), "sau": metrics(q, mid, t1, insts)}
    else:
        res = {"khoang": metrics(q, t0, t1, insts)}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for k, m in res.items():
            show(k, m)


if __name__ == "__main__":
    main()
