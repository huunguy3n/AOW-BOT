"""Gia lap offline 24h: so che do fixed (vong cu) va smart (bot/scheduler.py) - khong cham LDPlayer.

  python tools/sim_schedule.py                # 6 may, 24 h
  python tools/sim_schedule.py --hours 48 --seed 3 -v

The gioi gia: moi may 3 doi hanh quan, moi chuyen thu thap 2-5 h; lan ghe mat boot_min + step_min x so buoc;
gather gui het doi ranh (xac suat that bai fail_p); 1 runner chay tuan tu (nhu that).
Chi so: phut may bat / may / ngay, doi-gio nam khong, tran khoang cach giua 2 lan ghe, so lan ghe.
"""
import argparse, os, random, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.memory import Memory  # noqa: E402
from bot import scheduler  # noqa: E402

from bot.runner import ORDER as _ORDER  # noqa: E402
ORDER = [n for n, _ in _ORDER]
ENABLED = {n: n != "tutorial" for n in ORDER}


class World:
    def __init__(self, n, rng, a):
        self.rng, self.a = rng, a
        self.ret = {i: [0.0] * 3 for i in range(n)}  # luc tung doi ranh (0 = ranh tu dau)
        self.idle = 0.0
        self.on = {i: 0.0 for i in range(n)}
        self.visits = {i: [] for i in range(n)}

    def gather(self, i, t):
        sent = 0
        for k, r in enumerate(self.ret[i]):
            if r <= t:
                self.idle += t - r
                if self.rng.random() < self.a.fail_p:
                    self.ret[i][k] = t  # van ranh: tinh tiep tu day (khong cong 2 lan)
                    continue
                self.ret[i][k] = t + self.rng.uniform(2, 5) * 3600
                sent += 1
        return sent

    def visit(self, mem, i, t, steps):
        dur = (self.a.boot_min + self.a.step_min * (len(steps) + 1)) * 60
        self.visits[i].append(t)
        vid = mem._exec("INSERT INTO visits(inst, started, ended, mode) VALUES (?,?,?,?)", (i, t, t + dur, "sim")).lastrowid
        gt = t + self.a.boot_min * 60 + self.a.step_min * 60 * (steps.index("gather") if "gather" in steps else 0)
        for s in steps:
            ret = self.gather(i, gt) if s == "gather" else None
            mem._exec("INSERT INTO runs(visit, inst, step, started, dur, result, ret) VALUES (?,?,?,?,?,?,?)",
                      (vid, i, s, gt if s == "gather" else t, self.a.step_min * 60, "ok", str(ret)))
        # observe cuoi luot ghi lai doi dang di
        end = t + dur
        mem.clear_timers(i, "march:")
        for k, r in enumerate(self.ret[i]):
            if r > end:
                mem.set_timer(i, f"march:{k}", r, "sim", 0.9)
        mem.set_fact(i, "march_total", 3)
        mem.set_fact(i, "hq_level", 10)
        self.on[i] += dur
        return end


def run(mode, a, seed):
    rng = random.Random(seed)
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    mem = Memory(path)
    n, T = a.n, a.hours * 3600
    w = World(n, rng, a)
    t = 0.0
    cfg = {"schedule": {}}
    if mode == "fixed":
        while t < T:
            for i in range(n):
                t = w.visit(mem, i, t, [s for s in ORDER if ENABLED[s]])
            t += a.pause_min * 60
    else:
        while t < T:
            vs = scheduler.decide(mem, list(range(n)), ORDER, lambda i: ENABLED, lambda i: cfg, now=t)
            due = [v for v in vs if v.at <= t + 1]
            if due:
                v = due[0]
                if a.v:
                    print(f"  {t / 3600:6.2f}h may {v.idx}: {v.why} -> {len(v.steps)} buoc")
                t = w.visit(mem, v.idx, t, v.steps)
            else:
                t = max(t + 1, min(v.at for v in vs))
    # doi da ve ma toi cuoi ky van chua duoc gui lai -> tinh vao nam khong
    for i in range(n):
        w.idle += sum(t - r for r in w.ret[i] if r < t)
    gaps = []
    for i in range(n):
        vv = w.visits[i]
        gaps += [b - c for c, b in zip(vv, vv[1:])]
    try:
        os.remove(path)
    except OSError:
        pass
    days = a.hours / 24
    return {"on_min_day": sum(w.on.values()) / n / 60 / days,
            "idle_h_day": w.idle / 3600 / n / days,
            "visits_day": sum(len(v) for v in w.visits.values()) / n / days,
            "max_gap_h": max(gaps) / 3600 if gaps else 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--boot-min", dest="boot_min", type=float, default=3)
    ap.add_argument("--step-min", dest="step_min", type=float, default=1.5)
    ap.add_argument("--pause-min", dest="pause_min", type=float, default=30)
    ap.add_argument("--fail-p", dest="fail_p", type=float, default=0.1)
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    res = {m: run(m, a, a.seed) for m in ("fixed", "smart")}
    print(f"{'chi so (moi may)':<28} {'fixed':>8} {'smart':>8} {'doi':>7}")
    for k, lab in (("on_min_day", "phut may bat / ngay"), ("idle_h_day", "doi-gio nam khong / ngay"),
                   ("visits_day", "lan ghe / ngay"), ("max_gap_h", "khoang cach max (h)")):
        f, s = res["fixed"][k], res["smart"][k]
        print(f"{lab:<28} {f:>8.1f} {s:>8.1f} {(s - f) / f * 100 if f else 0:>6.0f}%")


if __name__ == "__main__":
    main()
