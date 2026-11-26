"""P13f-3: do thoi gian cac thao tac chuyen tiep cua Ctx CU (git rev) va MOI bang MO PHONG (khong cham thiet bi).

    python tools/bench_transitions.py [--old 2aaf70e] [--trials 41]

May gia: dong ho ao; 1 lan chup 0,282 s, tap 0,188 s, Back 0,271 s (trung vi do trong bang perf ngay 26/11/2026);
sau thao tac man doi sau 0,15..0,6 s. Chi phi khop anh khong tinh (hai ban khop gan nhu nhau) -> so tiet kiem chu yeu
la so lan chup va thoi gian ngu. Day la UOC LUONG mo phong, khong phai do tren may that.
"""
import argparse
import os
import random
import statistics
import subprocess
import sys
import types

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from bot import ctx as new_ctx  # noqa: E402

CAP, TAP, BACK = 0.282, 0.188, 0.271
SHADE = {"home": 40, "panel": 120, "blank": 80, "popup": 200}
FOUND = {40: {"common/btn_to_world": (60, 900, 0.9)}, 120: {"common/btn_back": (40, 40, 0.9)},
         200: {"common/btn_x": (500, 200, 0.9)}}
IMG = {k: np.full((960, 540, 3), v, np.uint8) for k, v in SHADE.items()}


class Clock:
    t = 1000.0

    def time(self):
        return self.t

    def sleep(self, s):
        self.t += max(0.0, s)

    def perf_counter(self):
        return self.t


class Dev:
    idx = 0

    def __init__(self, clock, screen, after, delay):
        self.c, self.screen, self.after, self.delay = clock, screen, list(after), delay
        self.pending, self.shots, self.act_seq = None, 0, 0

    def screencap(self, tries=None):
        shown = self.screen if not self.pending or self.c.t < self.pending[0] else self.pending[1]
        self.c.t += CAP
        self.shots += 1
        if self.pending and self.c.t >= self.pending[0]:
            self.screen, self.pending = self.pending[1], None
        return IMG[shown]

    def _act(self, cost):
        self.c.t += cost
        self.act_seq += 1
        if self.after:
            self.pending = (self.c.t + self.delay, self.after.pop(0))

    def tap(self, x, y):
        self._act(TAP)

    def back(self):
        self._act(BACK)


class V:
    def find(self, img, name, **k):
        return FOUND.get(int(img[0, 0, 0]), {}).get(name)


def old_module(rev):
    src = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:bot/ctx.py"], capture_output=True, check=True).stdout
    mod = types.ModuleType("ctx_old")
    mod.__file__ = os.path.join(ROOT, "bot", "ctx_old.py")
    exec(compile(src.decode("utf-8"), mod.__file__, "exec"), mod.__dict__)
    return mod


# ten -> (man dau, man hien sau moi thao tac, popup den muon (giay, man) | None, thao tac)
CASES = {
    "ensure_city (dang o thanh pho)": ("home", [], None, lambda c: c.ensure_city()),
    "ensure_city (tu 1 bang, nut <)": ("panel", ["home"], None, lambda c: c.ensure_city()),
    "back_out (nut <)": ("panel", ["home"], None, lambda c: c.back_out()),
    "back_out (phim Back)": ("blank", ["home"], None, lambda c: c.back_out()),
    "back_out (dang o thanh pho)": ("home", [], None, lambda c: c.back_out()),
    "dong popup luc vao game, khong popup (settle 3 s)": ("home", [], None,
                                                          lambda c: c.close_popups(rounds=10, settle=3)),
    "dong popup luc vao game, popup noi tiep sau 1 s": ("popup", ["home", "home"], (1.8, "popup"),
                                                        lambda c: c.close_popups(rounds=10, settle=3)),
}


def run(mod, case, delay):
    first, after, late, op = CASES[case]
    clock = Clock()
    mod.time = clock
    dev = Dev(clock, first, after, delay)
    c = mod.Ctx(dev, V(), {"screen": {"width": 540, "height": 960}, "learn": {"enabled": False},
                           "speed": {"wait_scale": 0.55}, "nav": {"skip_recheck_s": 3.0}})
    if late:                                   # popup thu hai hien muon
        real_tap = dev.tap

        def tap(x, y, once=[True]):            # noqa: B006
            real_tap(x, y)
            if once:
                once.pop()
                dev.screen, dev.pending = "home", (clock.t + late[0], late[1])
        dev.tap = tap
    t0 = clock.t
    op(c)
    return clock.t - t0, dev.shots, dev.act_seq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="2aaf70e")
    ap.add_argument("--trials", type=int, default=41)
    a = ap.parse_args()
    old = old_module(a.old)
    rng = random.Random(13)
    delays = [rng.uniform(0.15, 0.6) for _ in range(a.trials)]
    print(f"{'thao tac':52} {'cu (s)':>8} {'moi (s)':>8} {'chup cu':>8} {'chup moi':>8} thao tac cu/moi")
    for case in CASES:
        res = {n: [run(m, case, d) for d in delays] for n, m in (("old", old), ("new", new_ctx))}
        med = {n: [statistics.median(x[i] for x in r) for i in range(3)] for n, r in res.items()}
        o, n = med["old"], med["new"]
        print(f"{case:52} {o[0]:8.2f} {n[0]:8.2f} {o[1]:8.0f} {n[1]:8.0f} {o[2]:5.0f}/{n[2]:.0f}")


if __name__ == "__main__":
    main()
