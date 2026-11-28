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
  p6                           P6 tong hop 24h (--24h = --since 24): ti le buoc khong loi (tieu chi >= 95 %),
                               kim cuong theo nguon (bang gem_ev; chi khien duoc phep) + kim cuong giam ma so khong
                               giai thich (observations), so may chay cung luc lon nhat (tieu chi <= 2) va theo gio,
                               cac chi so P1-P5 gom 1 cho, ket luan DAT / KHONG DAT tung tieu chi.
"""
import argparse, glob, json, os, re, sqlite3, statistics, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.memory import DB, Memory  # noqa: E402
from aowbot.domain import rollout  # noqa: E402

GEM_ALLOWED = ("shield", "shield_war")   # ADR-0008 + chu du an 2026-11-23: chi khien (bi tan cong / ngay chien tranh)
STEP_FAIL = ("err", "stuck")             # 'warn' (co anh) / 'miss' (thieu anh mau) khong tinh la loi
OK_MIN_PCT = 95.0


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
    out["p6"] = p6_metrics(q, cond, args, out)
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
    c = {}
    for f in sorted(glob.glob(os.path.join(log_dir, "bot-*.log"))):
        m = re.search(r"bot-(\d{4})(\d\d)(\d\d)\.log$", f)
        day = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
        lines = []
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for ln in fh:
                    if "Tinh bao: " not in ln:
                        continue
                    if insts:
                        mi = LOG_INST_RX.search(ln)
                        if not mi or int(mi.group(1)) not in insts:
                            continue
                    lines.append(ln)
        except OSError:
            continue
        for k, n in IR.parse_log(lines, t0, t1, day).items():
            c[k] = c.get(k, 0) + n
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


def step_health(q, cond, args):
    """P6: buoc khong loi = ket qua khong phai err/stuck. -> {n, fail, ok_pct, worst: [(buoc, % khong loi, n)]}."""
    rcond = cond.replace("started", "r.started").replace("inst", "r.inst")
    per = {}
    if "result" not in {r[1] for r in q("PRAGMA table_info(runs)")}:   # DB rat cu / DB test
        return {"n": 0, "fail": 0, "ok_pct": None, "worst": []}
    for step, res in q(f"SELECT step, result FROM runs r WHERE {rcond}", args):
        p = per.setdefault(step, [0, 0])
        p[0] += 1
        p[1] += res in STEP_FAIL
    n, fail = sum(v[0] for v in per.values()), sum(v[1] for v in per.values())
    worst = sorted(((k, round(100 * (v[0] - v[1]) / v[0], 1), v[0]) for k, v in per.items() if v[1]),
                   key=lambda x: x[1])[:5]
    return {"n": n, "fail": fail, "ok_pct": round(100 * (n - fail) / n, 1) if n else None, "worst": worst}


def gem_drops(obs):
    """[(inst, at, gems)] -> {may: tong kim cuong GIAM giua 2 lan quan sat lien tiep}. Kim cuong chi giam khi tieu
    -> can tren so da tieu (nhan qua lam tang co the che bot; OCR doc sai cung co the gay giam gia)."""
    last, out = {}, {}
    for inst, _at, g in sorted(obs, key=lambda r: (r[0], r[1])):
        if g is None:
            continue
        if inst in last and g < last[inst]:
            out[inst] = out.get(inst, 0) + last[inst] - g
        last[inst] = g
    return out


def gem_metrics(q, cond, args):
    """P6: kim cuong theo nguon (gem_ev) + kim cuong giam theo quan sat ma so khong giai thich duoc."""
    by_src, by_inst = {}, {}
    if _has_table(q, "gem_ev"):
        for inst, src, n in q(f"SELECT inst, src, SUM(n) FROM gem_ev WHERE {cond} GROUP BY inst, src", args):
            by_src[src] = by_src.get(src, 0) + (n or 0)
            by_inst[inst] = by_inst.get(inst, 0) + (n or 0)
    obs = []
    if _has_table(q, "observations"):
        for inst, at, res in q(f"SELECT inst, at, resources FROM observations WHERE {cond}", args):
            try:
                g = (json.loads(res) or {}).get("gems") if res else None
            except (TypeError, ValueError, AttributeError):
                g = None
            obs.append((inst, at, g if isinstance(g, (int, float)) else None))
    drops = gem_drops(obs)
    unexplained = {i: d - by_inst.get(i, 0) for i, d in drops.items() if d > by_inst.get(i, 0)}
    outside = sum(n for s, n in by_src.items() if s not in GEM_ALLOWED)
    return {"by_src": by_src, "outside_shield": outside, "drops": drops, "unexplained": unexplained}


def concurrency_metrics(q, cond, args):
    """P6: so may chay cung luc tu visits (bat -> tat). Lan ghe chua dong (ended NULL) coi nhu dai 0."""
    pairs = [(st, en or st) for st, en in q(f"SELECT started, ended FROM visits WHERE {cond}", args)]
    peak, at = rollout.peak_concurrency(pairs)
    hourly = {}
    for h in sorted({int(s // 3600) for s, _ in pairs}):
        lo, hi = h * 3600, (h + 1) * 3600
        hourly[time.strftime("%d/%m %H:00", time.localtime(lo))] = rollout.peak_concurrency(
            [(max(s, lo), min(e, hi)) for s, e in pairs if s < hi and e > lo])[0]
    return {"peak": peak, "peak_at": at, "over_limit_s": round(rollout.time_over(pairs, rollout.HARD_MAX_RUNNING), 1),
            "hourly": hourly}


def p6_metrics(q, cond, args, m):
    """P6: tong hop 24h + ket luan theo tieu chi (logs/pm-audit-1.txt dong P6)."""
    health = step_health(q, cond, args)
    gems = gem_metrics(q, cond.replace("started", "at"), args)
    conc = concurrency_metrics(q, cond, args)
    rebels = (m.get("combat") or {}).get("rebels")
    indices = {
        "idle_queue_pct": {k: v["idle_pct"] for k, v in (m.get("queues") or {}).items()},
        "march_full_pct": (m.get("march") or {}).get("full_pct"),
        "follow_stuck": (m.get("follow") or {}).get("stuck", 0),
        "hq_per_day": {i: h["cap_ngay"] for i, h in (m.get("hq") or {}).items()},
        "intel_unknown_pct": (m.get("intel") or {}).get("_pct"),
        "rebels": f"{rebels['ok']}/{rebels['n']}" if rebels else None,
    }
    verdict = {
        "buoc_khong_loi": health["ok_pct"] is not None and health["ok_pct"] >= OK_MIN_PCT,
        "kim_cuong_ngoai_khien": gems["outside_shield"] == 0,
        "toi_da_2_may": conc["peak"] <= rollout.HARD_MAX_RUNNING,
    }
    return {"steps": health, "gems": gems, "concurrency": conc, "indices": indices, "verdict": verdict}


def _ok(b):
    return "DAT" if b else "KHONG DAT"


def show_p6(p):
    v, h, g, c, i = p["verdict"], p["steps"], p["gems"], p["concurrency"], p["indices"]
    print("   -- P6 tong hop (tieu chi chay 24h) --")
    print(f"   buoc khong loi: {h['ok_pct']} % ({h['n'] - h['fail']}/{h['n']}; can >= {OK_MIN_PCT}) -> "
          f"{_ok(v['buoc_khong_loi'])}")
    if h["worst"]:
        print("     buoc loi nhieu: " + ", ".join(f"{s} {pct} % / {n}" for s, pct, n in h["worst"]))
    print(f"   kim cuong theo nguon {g['by_src']}; ngoai khien {g['outside_shield']} -> "
          f"{_ok(v['kim_cuong_ngoai_khien'])}")
    if g["unexplained"]:
        print(f"     CAN XEM: kim cuong giam ma so khong ghi (may: so) {g['unexplained']} "
              "(co the OCR doc sai - xem anh/log cua may do)")
    print(f"   may chay cung luc toi da {c['peak']} (tran {rollout.HARD_MAX_RUNNING}), qua tran {c['over_limit_s']} s"
          f" -> {_ok(v['toi_da_2_may'])}")
    if 0 < len(c["hourly"]) <= 26:
        print("     theo gio: " + ", ".join(f"{k} {n}" for k, n in c["hourly"].items()))
    elif c["hourly"]:
        dist = {}
        for n in c["hourly"].values():
            dist[n] = dist.get(n, 0) + 1
        print("     so gio co N may cung luc: " + ", ".join(f"{n} may: {k} gio" for n, k in sorted(dist.items()))
              + " (--json de xem tung gio)")
    print(f"   P1-P5: hang cho ranh {i['idle_queue_pct']}, hanh quan day {i['march_full_pct']} %, "
          f"follow ket {i['follow_stuck']}, nha chinh/ngay {i['hq_per_day']}, tinh bao unknown "
          f"{i['intel_unknown_pct']} %, phan quan co ket qua {i['rebels']}")


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
    if m.get("p6"):
        show_p6(m["p6"])
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


def show_ml(mem, days, as_json=False):
    """M0 (docs/strategy/ml-roadmap.md): so do ML theo ngay - cham an %, ML chan, luot ghe, may-gio, loi, cap nha chinh."""
    from bot import learn
    rows = learn.scoreboard(mem, days)
    noop = learn.noop_status(learn.Learner(mem, {}))
    if as_json:
        print(json.dumps({"days": rows, "noop": noop}, ensure_ascii=False, indent=1))
        return
    print(f"== So do ML {days} ngay (tran may-gio 48/ngay)")
    print("   ngay   cham    an%   chan(chet/anh/diem)  ghe  phut/ghe  may-gio  loi buoc/ghe  nha chinh")
    for r in rows:
        hq = " ".join(f"#{k}:{v}" for k, v in sorted(r["hq"].items()))
        print(f"   {r['day']}  {r['taps']:6d}  {r['ok_pct'] if r['ok_pct'] is not None else '-':>5}  "
              f"{r['skips']:5d} ({r['skip_dead']}/{r['skip_crop']}/{r['skip_score']}){'':4s} {r['visits']:4d}  "
              f"{r['visit_min'] if r['visit_min'] is not None else '-':>7}  {r['machine_h']:7}  "
              f"{r['step_err']:4d}/{r['visit_err']:<4d}  {hq}")
    from bot import mlinsight
    m2 = mlinsight.all(mem)
    b = m2.get("battles") or {}
    print("\n== M2-1 Tran 7 ngay (loai / quyet dinh / ket qua)")
    for r in b.get("by", []):
        print(f"   {r['kind']:10s} {r['decision']:12s} {r['result']:5s} {r['n']:4d}")
    print("== M2-2 Xac suat thang (che do bong):", ", ".join(
        f"{m['kind']} n={m['n']} can ta/dich {m['ratio_80']} de thang 80 %" for m in b.get("models", [])) or
        "chua du mau (" + ", ".join(f"{d['kind']} con thieu {d['need']}" for d in b.get("data", [])) + ")")
    s = m2.get("steps") or {}
    print("\n== M2-3 Gia tri buoc 3 ngay (lam duoc viec / phut) - chi de xuat, runner KHONG doi thu tu")
    for v in (s.get("values") or [])[:12]:
        print(f"   {v['step']:13s} chay {v['runs']:4d}  lam duoc {100 * v['work_rate']:5.1f} %  "
              f"{v['mean_min']:5.2f} phut  gia tri {v['value']:.2f}")
    print("   de xuat:", " > ".join(s.get("order_suggest") or []))
    print("\n== M2-4 Nha chinh")
    for h in m2.get("hq") or []:
        print(f"   #{h['inst']} cap {h['level']}  {h['hours_since_up']} gio chua len cap  "
              f"{'DUNG YEN' if h['stalled'] else 'ok':8s} ke hoach: {h['plan']}  "
              f"xay {h['build_work']}/{h['build_runs']}  {h['reasons']}")
    print("\n== Doan cham vo ich (M1-1/2): khoa duoc phep chan sau tu kiem bo-ra")
    for n in noop:
        print(f"   {'BAT' if n['on'] else 'tat'}  {n['key']:45s} mau {n['n']:4d}  doan {n['pred']:3d}  dung {n['precision']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB)
    ap.add_argument("--since", help="N gio truoc, hoac 'YYYY-mm-dd HH:MM'")
    ap.add_argument("--until", help="nhu --since")
    ap.add_argument("--split", help="moc 'YYYY-mm-dd HH:MM': in 2 khoang truoc / sau")
    ap.add_argument("--inst", help="vd 0,5")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--24h", dest="day", action="store_true", help="P6: 24 gio gan nhat (= --since 24)")
    ap.add_argument("--ml", type=int, nargs="?", const=7, metavar="NGAY",
                    help="M0: bang so do ML theo ngay (mac dinh 7 ngay) + khoa ML dang duoc chan")
    a = ap.parse_args()
    if a.day and not a.since:
        a.since = "24"
    if not os.path.exists(a.db):
        sys.exit(f"Khong co {a.db}")
    mem = Memory(a.db, readonly=True)

    def q(sql, args=()):
        try:
            return mem._conn().execute(sql, args).fetchall()
        except sqlite3.Error as e:
            sys.exit(f"Loi doc {a.db}: {e}")
    if a.ml:
        show_ml(mem, a.ml, a.json)
        return
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
