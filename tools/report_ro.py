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
  march                        P3: % lan quan sat 'Hanh quan x/y' day (march_obs; DB cu: bang observations)
  gather_ev                    P3: su kien thu thap theo loai (own_dialog = Huy oan, contested, occupied...)
  follow                       P4: so anh logs/shots follow_stuck / follow_maxsteps / follow_lose trong khoang
  hq                           P4: cap nha chinh tung may (fact hq_history): dau / cuoi khoang, so cap tang, cap/ngay
  intel                        P5: ket qua moi ghim tinh bao (log 'Tinh bao: <kq>' trong logs/bot-*.log), % unknown
  combat                       P5: rebels / heal / defense - lan chay, lan co ket qua (> 0), % co ket qua, phut
"""
import argparse, glob, json, os, re, sqlite3, statistics, sys, time

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
    out["perf"] = perf_metrics(q, cond.replace("started", "at"), args)
    out["queues"] = queue_metrics(q, cond.replace("started", "at"), args)
    out["march"] = march_metrics(q, cond.replace("started", "at"), args)
    out["gather_ev"] = gather_events(q, cond.replace("started", "at"), args)
    out["follow"] = follow_metrics(t0, t1, insts)
    out["hq"] = hq_metrics(q, t0, t1, insts)
    out["intel"] = intel_metrics(t0, t1, insts)
    out["combat"] = combat_metrics(out["steps"])
    out["vm_h"], out["useless_h"] = round(out["vm_h"], 2), round(out["useless_h"], 2)
    for s in out["steps"].values():
        s["min"], s["zero_min"] = round(s["min"], 1), round(s["zero_min"], 1)
    return out


def queue_metrics(q, cond, args):
    """Q0 (bang queue_obs): ti le lan quan sat hang cho con cho ranh, theo loai. Chua co bang -> {}."""
    if not q("SELECT 1 FROM sqlite_master WHERE type='table' AND name='queue_obs'"):
        return {}
    out = {}
    for kind, n, idle, slots in q(f"SELECT kind, COUNT(*), SUM(used < total), SUM(total - used) FROM queue_obs "
                                  f"WHERE {cond} GROUP BY kind", args):
        out[kind] = {"n": n, "idle_pct": round(100 * (idle or 0) / n, 1), "idle_slots_avg": round((slots or 0) / n, 2)}
    return out


def _has_table(q, name):
    return bool(q("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)))


def march_metrics(q, cond, args):
    """P3: lan quan sat cuoi luot co 'Hanh quan' DAY. Bang march_obs (P3): day = used >= total - reserve (de danh cho
    phan quan), khong doc duoc thi dem rieng. Khoang khong co march_obs (truoc P3) -> bang observations, cach cu:
    khong doc duoc bi ghi 0 nen ti le day cu bi THAP hon thuc te."""
    if _has_table(q, "march_obs"):
        rows = q(f"SELECT used, total, reserve, src FROM march_obs WHERE {cond}", args)
        if rows:
            read = [(u, t, r or 0) for u, t, r, _ in rows if t]
            full = sum(u >= t - r for u, t, r in read)
            strict = sum(u >= t for u, t, _ in read)
            src = {}
            for *_, s in rows:
                src[s or "khong doc duoc"] = src.get(s or "khong doc duoc", 0) + 1
            return {"src": "march_obs", "n": len(rows), "read": len(read),
                    "full_pct": round(100 * full / len(read), 1) if read else None,
                    "full_strict_pct": round(100 * strict / len(read), 1) if read else None, "by_src": src}
    if not _has_table(q, "observations"):
        return {}
    rows = q(f"SELECT march_used, march_total FROM observations WHERE {cond} AND march_total > 0", args)
    if not rows:
        return {}
    full = sum((u or 0) >= t for u, t in rows)
    return {"src": "observations", "n": len(rows), "read": len(rows), "full_pct": round(100 * full / len(rows), 1),
            "full_strict_pct": round(100 * full / len(rows), 1), "by_src": {}}


def gather_events(q, cond, args):
    """P3 (bang gather_ev): {loai su kien: so lan}. Chua co bang -> {}."""
    if not _has_table(q, "gather_ev"):
        return {}
    return {k: n for k, n in q(f"SELECT kind, COUNT(*) FROM gather_ev WHERE {cond} GROUP BY kind ORDER BY 2 DESC", args)}


SHOT_RX = re.compile(r"^(\d{8}-\d{6})-i(\d+)-follow_(stuck|maxsteps|lose)\.png$")


def follow_metrics(t0, t1, insts=None, shots_dir=os.path.join("logs", "shots")):
    """P4: dem anh follow_* (ten file = gio chup) trong [t0, t1). Thu muc khong co -> {}."""
    out = {}
    if not os.path.isdir(shots_dir):
        return out
    for f in os.listdir(shots_dir):
        m = SHOT_RX.match(f)
        if not m or (insts and int(m.group(2)) not in insts):
            continue
        at = time.mktime(time.strptime(m.group(1), "%Y%m%d-%H%M%S"))
        if t0 <= at < t1:
            out[m.group(3)] = out.get(m.group(3), 0) + 1
    return out


LOG_INST_RX = re.compile(r"\[#(\d+)\]")


def intel_metrics(t0, t1, insts=None, log_dir="logs"):
    """P5-1: {kq: n, '_unknown': n, '_total': n, '_pct': %} tu log 'Tinh bao: <kq>' trong [t0, t1). --inst: chi dong
    co the [#N] (dong [MainThread] khong biet may -> bo khi loc may). Khong co log -> {}."""
    from bot import intel_rules as IR
    lines = []
    for f in sorted(glob.glob(os.path.join(log_dir, "bot-*.log"))):
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for ln in fh:
                    if "Tinh bao: " not in ln:
                        continue
                    if insts:
                        m = LOG_INST_RX.search(ln)
                        if not m or int(m.group(1)) not in insts:
                            continue
                    lines.append(ln)
        except OSError:
            continue
    c = IR.parse_log(lines, t0, t1)
    if not c:
        return {}
    unk, tot, pct = IR.unknown_rate(c)
    return {**c, "_unknown": unk, "_total": tot, "_pct": pct}


def combat_metrics(steps):
    """P5: buoc chien dau - lan chay, lan tra > 0 (co ket qua), % co ket qua, phut."""
    out = {}
    for step in ("rebels", "heal", "defense"):
        s = steps.get(step)
        if not s:
            continue
        ok = s["n"] - s["zero"]
        out[step] = {"n": s["n"], "ok": ok, "ok_pct": round(100.0 * ok / s["n"], 1) if s["n"] else None,
                     "min": round(s["min"], 1)}
    return out


def hq_metrics(q, t0, t1, insts=None):
    """P4: {may: {dau, cuoi, tang, ngay, cap_ngay}} tu fact hq_history [[ts, cap], ...] (observe ghi khi cap doi)."""
    out = {}
    if not _has_table(q, "facts"):     # DB cu / DB test khong co bang facts
        return out
    rows = q("SELECT inst, value FROM facts WHERE key='hq_history'")
    for inst, val in rows:
        if insts and inst not in insts:
            continue
        try:
            hist = [(float(t), int(lv)) for t, lv in json.loads(val)]
        except (TypeError, ValueError):
            continue
        before = [lv for t, lv in hist if t < t0]
        inside = [(t, lv) for t, lv in hist if t0 <= t < t1]
        if not inside and not before:
            continue
        start = before[-1] if before else inside[0][1]
        end = inside[-1][1] if inside else start
        lo = max(t0, hist[0][0])
        days = max((min(t1, time.time()) - lo) / 86400, 1 / 24)
        out[inst] = {"dau": start, "cuoi": end, "tang": end - start, "ngay": round(days, 2),
                     "cap_ngay": round((end - start) / days, 2)}
    return out


def perf_metrics(q, cond, args):
    """Bang perf (A-MEAS-1): theo loai thao tac va theo buoc. Chua co bang (DB cu) -> {}."""
    if not q("SELECT 1 FROM sqlite_master WHERE type='table' AND name='perf'"):
        return {}
    kinds = {f"{k}/{s}": {"n": n, "total_s": round(t or 0, 1), "max_s": round(mx or 0, 2)}
             for k, s, n, t, mx in q(f"SELECT kind, src, SUM(n), SUM(total), MAX(max) FROM perf WHERE {cond} "
                                     "GROUP BY kind, src ORDER BY SUM(total) DESC", args)}
    steps = {}
    for step, kind, n, t in q(f"SELECT step, kind, SUM(n), SUM(total) FROM perf WHERE {cond} GROUP BY step, kind", args):
        s = steps.setdefault(step, {"adb": 0, "screencap": 0, "ocr": 0, "identify": 0, "adb_s": 0.0})
        if kind.startswith("adb_"):
            s["adb"] += n
            s["adb_s"] = round(s["adb_s"] + (t or 0), 1)
        if kind in ("screencap", "ocr", "identify"):
            s[kind] += n
        if kind == "ocr_march":
            s["ocr"] += n
    return {"kinds": kinds, "steps": steps}


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
    if m.get("queues"):
        print("   hang cho (lan quan sat con cho ranh):")
        for k, v in m["queues"].items():
            print(f"     {k:<10}{v['idle_pct']:>6} % / {v['n']} lan, TB {v['idle_slots_avg']} cho ranh")
    mc = m.get("march")
    if mc:
        print(f"   hanh quan day (P3, nguon {mc['src']}): {mc['full_pct']} % / {mc['read']} lan doc duoc "
              f"({mc['n']} lan quan sat); day tuyet doi {mc['full_strict_pct']} %; nguon doc {mc['by_src']}")
    if m.get("gather_ev"):
        ev = m["gather_ev"]
        print(f"   thu thap (gather_ev): Huy oan (own_dialog) {ev.get('own_dialog', 0)}, hop thoai la "
              f"{ev.get('dialog_unknown', 0)}, tranh chap {ev.get('contested', 0)}, bo qua mo minh dang toi "
              f"{ev.get('own_skip', 0) + ev.get('own', 0)}, khong doc tru luong {ev.get('unread', 0)}")
        print("     " + ", ".join(f"{k} {n}" for k, n in ev.items()))
    if m.get("follow") is not None:
        f = m["follow"]
        print(f"   follow (P4, anh logs/shots): ket {f.get('stuck', 0)}, het buoc {f.get('maxsteps', 0)}, "
              f"thua {f.get('lose', 0)}")
    if m.get("hq"):
        print("   nha chinh (P4, hq_history): " + ", ".join(
            f"#{i} {h['dau']}->{h['cuoi']} (+{h['tang']} / {h['ngay']} ngay = {h['cap_ngay']}/ngay)"
            for i, h in sorted(m["hq"].items())))
    if m.get("intel"):
        it = m["intel"]
        print(f"   tinh bao (P5, log): unknown {it['_unknown']}/{it['_total']} ghim = {it['_pct']} %; "
              + ", ".join(f"{k} {n}" for k, n in sorted(it.items()) if not k.startswith("_")))
    if m.get("combat"):
        print("   chien dau (P5): " + ", ".join(f"{k} {v['ok']}/{v['n']} co ket qua ({v['ok_pct']} %, {v['min']} phut)"
                                             for k, v in m["combat"].items()))
    if m.get("perf"):
        print("   hieu nang (bang perf):")
        for k, v in list(m["perf"]["kinds"].items())[:15]:
            print(f"     {k:<28}{v['n']:>7} lan {v['total_s']:>9} s  max {v['max_s']} s")
        print(f"   {'buoc':<13}{'adb':>6}{'adb s':>8}{'anh':>6}{'ocr':>6}{'nhan dien':>10}")
        for step, s in sorted(m["perf"]["steps"].items(), key=lambda kv: -kv[1]["adb_s"]):
            print(f"   {step:<13}{s['adb']:>6}{s['adb_s']:>8}{s['screencap']:>6}{s['ocr']:>6}{s['identify']:>10}")


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
