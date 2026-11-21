"""Tinh chi so do moc (giai doan A0/A5) tu data/memory.db.

  python tools/baseline.py                  # toan bo du lieu
  python tools/baseline.py --since 24       # 24 gio gan nhat
  python tools/baseline.py --inst 0,5 --mode fixed

Chi so (docs/product/ke-hoach-A-tri-nho-lap-lich.md §2):
  1. Thoi gian may bat / tai khoan / ngay  (visits: started -> ended)
  2. Thoi gian doi quan nam khong: doi ve thanh (return_at do observe uoc tinh) hoac doi con trong luc observe
     -> den lan 'gather' ke tiep cua tai khoan do. Doi 'dang thu thap' khong biet thoi gian di -> khong tinh (bao so luong).
  3. Buoc chay ma khong co viec: hien chi do duoc 'gather' gui 0 doi.
"""
import argparse, json, os, statistics, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.memory import Memory, DB  # noqa: E402


def fmt_min(sec):
    return f"{sec / 60:.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=float, help="chi tinh N gio gan nhat")
    ap.add_argument("--inst", help="vd 0,5")
    ap.add_argument("--mode", help="fixed | smart (visits.mode)")
    ap.add_argument("--db", default=DB)
    a = ap.parse_args()
    if not os.path.exists(a.db):
        print("Chua co", a.db, "- chay bot it nhat 1 luot truoc")
        return
    mem = Memory(a.db, readonly=True)
    t_from = time.time() - a.since * 3600 if a.since else 0
    insts = [int(x) for x in a.inst.split(",")] if a.inst else \
        [r[0] for r in mem.query("SELECT DISTINCT inst FROM visits WHERE started>=? ORDER BY inst", (t_from,))]
    if not insts:
        print("Khong co lan ghe nao trong khoang thoi gian nay")
        return
    mode_sql, mode_arg = (" AND mode=?", (a.mode,)) if a.mode else ("", ())

    print(f"== 1. Thoi gian may bat (tu {time.strftime('%d/%m %H:%M', time.localtime(t_from)) if t_from else 'dau'}) ==")
    print(f"{'may':>4} {'lan ghe':>8} {'phut bat':>9} {'phut/lan':>9} {'khoang do (h)':>14} {'phut/ngay':>10}  ket qua")
    for i in insts:
        rows = mem.query("SELECT started, ended, result FROM visits WHERE inst=? AND started>=? AND ended IS NOT NULL" + mode_sql,
                         (i, t_from) + mode_arg)
        if not rows:
            print(f"{i:>4}  (chua co lan ghe hoan tat)")
            continue
        on = sum(e - s for s, e, _ in rows)
        span = max(e for _, e, _ in rows) - min(s for s, _, _ in rows)
        per_day = on / (span / 86400) if span > 3600 else float("nan")
        res = {}
        for _, _, r in rows:
            res[r] = res.get(r, 0) + 1
        print(f"{i:>4} {len(rows):>8} {fmt_min(on):>9} {fmt_min(on / len(rows)):>9} {span / 3600:>14.1f} "
              f"{per_day / 60:>10.1f}  {res}")
    print("  (phut/ngay chi co nghia khi khoang do >= vai gio; < 1 h -> nan)")

    print("\n== 2. Doi quan nam khong (ve/trong -> lan gather ke tiep) ==")
    print(f"{'may':>4} {'mau':>5} {'trung vi (ph)':>14} {'TB (ph)':>8} {'max (ph)':>9} {'doi-gio/ngay':>13} {'khong ro':>9}")
    for i in insts:
        obs = mem.query("SELECT at, march_used, march_total, marches FROM observations WHERE inst=? AND at>=? ORDER BY at",
                        (i, t_from))
        gathers = [r[0] for r in mem.query("SELECT started FROM runs WHERE inst=? AND step='gather' AND started>=? ORDER BY started",
                                           (i, t_from))]
        idles, unknown = [], 0
        for at, used, total, mj in obs:
            nxt = next((g for g in gathers if g > at), None)
            if nxt is None:
                continue  # chua co lan gather sau quan sat nay
            for m in json.loads(mj or "[]"):
                ra = m.get("return_at")
                if ra is None:
                    unknown += 1
                elif ra < nxt:
                    idles.append(nxt - ra)
            if used is not None and total:
                idles += [nxt - at] * max(0, total - used)  # doi trong ngay luc quan sat (gather chua lap day)
        if not idles:
            print(f"{i:>4} {0:>5}  (chua du du lieu: can >= 2 lan ghe co observe + gather)  khong ro={unknown}")
            continue
        span = (gathers[-1] - obs[0][0]) if obs else 0
        per_day = sum(idles) / 3600 / (span / 86400) if span > 3600 else float("nan")
        print(f"{i:>4} {len(idles):>5} {fmt_min(statistics.median(idles)):>14} {fmt_min(statistics.mean(idles)):>8} "
              f"{fmt_min(max(idles)):>9} {per_day:>13.1f} {unknown:>9}")

    print("\n== 3. Buoc: so lan, thoi gian, ket qua ==")
    ph = ",".join("?" * len(insts))
    rows = mem.query(f"SELECT step, COUNT(*), AVG(dur), SUM(dur), "
                     f"SUM(result='ok'), SUM(result IN ('err','stuck')), "
                     f"SUM(step='gather' AND ret='0') "
                     f"FROM runs WHERE inst IN ({ph}) AND started>=? GROUP BY step ORDER BY SUM(dur) DESC",
                     tuple(insts) + (t_from,))
    print(f"{'buoc':<13} {'lan':>5} {'TB (s)':>7} {'tong (ph)':>10} {'% ok':>6} {'loi/ket':>8} {'khong viec':>11}")
    for step, n, avg, tot, ok, bad, idle in rows:
        idle_s = str(idle) if step == "gather" else "-"
        print(f"{step:<13} {n:>5} {avg:>7.1f} {fmt_min(tot):>10} {100 * ok / n:>6.0f} {bad:>8} {idle_s:>11}")
    print("  khong viec: 'gather' gui 0 doi (hanh quan da day / het linh). Cac buoc khac chua do duoc o A0.")

    print("\n== 4. Dieu huong goto() (giai doan B/C) ==")
    rows = mem.query(f"SELECT step, COUNT(*), SUM(screen='unknown'), SUM(changed=0 AND action!='done'), "
                     f"SUM(action='back'), SUM(action='done') FROM nav WHERE inst IN ({ph}) AND at>=? "
                     f"GROUP BY step ORDER BY COUNT(*) DESC", tuple(insts) + (t_from,))
    if not rows:
        print("  (chua co du lieu - can ban co nav.smart)")
    else:
        print(f"{'buoc':<13} {'hanh dong':>9} {'man la':>7} {'cham khong an':>14} {'Back':>5} {'toi dich':>9}")
        for step, n, unk, stale, back, done in rows:
            print(f"{step:<13} {n:>9} {unk:>7} {stale:>14} {back:>5} {done:>9}")
        scr = mem.query(f"SELECT screen, COUNT(*) FROM nav WHERE inst IN ({ph}) AND at>=? GROUP BY screen ORDER BY 2 DESC",
                        tuple(insts) + (t_from,))
        print("  man gap:", ", ".join(f"{s}={n}" for s, n in scr), "| anh man la: logs/unknown/")

    print("\n== 6. Tien do tai khoan (giai doan D: muc tieu) ==")
    print(f"{'may':>4} {'luc chien dau':>14} {'cuoi':>10} {'+/ngay':>9} {'kim loai +/ngay':>16} {'thuc pham +/ngay':>17}")
    for i in insts:
        obs = mem.query("SELECT at, resources FROM observations WHERE inst=? AND at>=? ORDER BY at", (i, t_from))
        pts = [(at, json.loads(r or "{}")) for at, r in obs]
        pts = [(at, r) for at, r in pts if r.get("power")]
        if len(pts) < 2:
            print(f"{i:>4}  (can >= 2 lan observe doc duoc luc chien)")
            continue
        (t0, a0), (t1, a1) = pts[0], pts[-1]
        d = max((t1 - t0) / 86400, 1e-9)

        def rate(k):
            if a0.get(k) is None or a1.get(k) is None:
                return float("nan")
            return (a1[k] - a0[k]) / d
        print(f"{i:>4} {a0['power']:>14} {a1['power']:>10} {rate('power'):>9.0f} {rate('metal'):>16.0f} {rate('food'):>17.0f}")

    print("\n== 5. Buoc dang tam bo (backoff, chi tac dung o smart) ==")
    for i in insts:
        for step, fails, until, note in mem.backoffs(i):
            print(f"  may {i}: {step} loi {fails} lan, tam bo toi {time.strftime('%H:%M', time.localtime(until))} - {note}")


if __name__ == "__main__":
    main()
