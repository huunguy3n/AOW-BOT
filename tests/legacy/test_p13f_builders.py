"""P13f-2 (chu du an t90u 26/11/2026): trong 1 luot auto, nha xay xong -> xay tiep NGAY, truoc moi buoc khac."""
import types

import cv2
import numpy as np
import pytest

from aowbot.domain import hqplan as hqdom
from bot import build, hqplan, runner
from bot.memory import Memory
from bot.modules import upgrade


def _ctx(maxb=1):
    return types.SimpleNamespace(cfg={"build": {"max_builders": maxb, "quick_s": 600, "quick_total_s": 600}},
                                 dev=types.SimpleNamespace(idx=5), mem=None, ensure_city=lambda: None,
                                 shot=lambda: None, wd_reset=lambda *a: None, visit_pending={"alliance", "campaign"})


# ---------------------------------------------------------------- should_quick_wait / quick_wait
def test_should_quick_wait_never_postpones_when_idle():
    pending = {"alliance", "campaign", "collect_city", "daily"}
    ok, why = build.should_quick_wait(pending, (0, 2), 1)
    assert not ok and "xay tiep ngay" in why and "lam truoc" not in why
    ok, why = build.should_quick_wait(pending, (1, 2), 2)          # #1: con tho thu 2
    assert not ok and "xay tiep ngay" in why
    ok, why = build.should_quick_wait(pending, (1, 2), 1)          # farm 1/2 = day -> duoc di lam viec khac
    assert not ok and "tho dang ban het" in why


@pytest.mark.parametrize("busy,maxb", [((0, 2), 1), ((1, 2), 2), ((0, 1), 1)])
def test_quick_wait_returns_continue_at_once_when_idle(monkeypatch, busy, maxb):
    monkeypatch.setattr(build, "builders", lambda ctx, img=None: busy)
    monkeypatch.setattr(build, "free_speedup", lambda ctx: pytest.fail("tho ranh: khong can tang toc"))
    monkeypatch.setattr(build.time, "sleep", lambda s: pytest.fail("tho ranh: khong cho"))
    assert build.quick_wait(_ctx(maxb)) is True                    # co viec khac trong luot van xay tiep


def test_quick_wait_farm_one_of_two_is_busy(monkeypatch):
    monkeypatch.setattr(build, "builders", lambda ctx, img=None: (1, 2))
    monkeypatch.setattr(build, "free_speedup", lambda ctx: 0)
    assert build.quick_wait(_ctx(1)) is False


def test_free_speedup_frees_builder_then_continue(monkeypatch):
    seq = iter([(1, 2), (0, 2)])
    monkeypatch.setattr(build, "builders", lambda ctx, img=None: next(seq))
    monkeypatch.setattr(build, "free_speedup", lambda ctx: 1)
    assert build.quick_wait(_ctx(1)) is True


# ---------------------------------------------------------------- nhuong tho cho nha chinh
def _mem_ctx(tmp_path, busy, monkeypatch, maxb=1):
    m = Memory(str(tmp_path / "m.db"))
    c = _ctx(maxb)
    c.mem = m
    m.set_fact(5, hqplan.KEY, hqdom.record(None, "started", 1e12).to_json())   # chain, con han giu rat dai
    monkeypatch.setattr(build, "builders", lambda ctx, img=None: busy)
    return c


def test_chain_never_skips_idle_builder(tmp_path, monkeypatch):
    c = _mem_ctx(tmp_path, (0, 2), monkeypatch)
    for step in ("construct", "quests", "mainquest"):
        assert hqplan.yield_builder(c, step) is False


def test_full_builder_skips_build(tmp_path, monkeypatch):
    c = _mem_ctx(tmp_path, (1, 2), monkeypatch)
    assert hqplan.yield_builder(c, "construct") is True
    assert hqplan.yield_builder(c, "mainquest", only_hq=True) is True       # dang lam tien quyet nha chinh


# ---------------------------------------------------------------- upgrade: chuoi + nha khac
def _upgrade_env(monkeypatch, results, busy):
    state = {"busy": busy}
    res = iter(results)

    def here(ctx, **k):
        r = next(res)
        if r == "started_busy":
            state["busy"] += 1
            return "started"
        return r

    monkeypatch.setattr(upgrade.build, "builders", lambda ctx, img=None: (state["busy"], 2))
    monkeypatch.setattr(upgrade.build, "upgrade_here", here)
    monkeypatch.setattr(upgrade.build, "free_speedup", lambda ctx: 0)
    monkeypatch.setattr(upgrade, "goto_hq", lambda ctx, again=False: (317, 557, 0.95))
    c = _ctx(1)
    c.back_out = lambda *a: None
    c.cfg["build"].update(hq_max_level=30, probe_plot_lock=False, quick_s=0)
    return c, state


def test_instant_upgrades_chain_until_builder_busy(monkeypatch):
    c, state = _upgrade_env(monkeypatch, ["started", "started", "started_busy"], 0)
    monkeypatch.setattr(upgrade, "other_buildings", lambda ctx: pytest.fail("tho da ban"))
    assert upgrade.run(c) == 3 and state["busy"] == 1


@pytest.mark.parametrize("hq_result", ["blocked", "none", "busy"])
def test_other_building_when_hq_cannot_proceed(monkeypatch, hq_result):
    c, state = _upgrade_env(monkeypatch, [hq_result], 0)
    seen = []

    def res(ctx):
        seen.append(1)
        state["busy"] += 1
        return "started"

    monkeypatch.setattr(upgrade, "upgrade_resource", res)
    assert upgrade.run(c) == 1 and seen == [1]


def test_full_farm_builder_never_opens_other_building(monkeypatch):
    c, _ = _upgrade_env(monkeypatch, [], 1)
    monkeypatch.setattr(upgrade, "upgrade_resource", lambda ctx: pytest.fail("1/2 farm = day"))
    monkeypatch.setattr(upgrade, "goto_hq", lambda ctx: pytest.fail("1/2 farm = day"))
    assert upgrade.run(c) == 0


# ---------------------------------------------------------------- anh mau nha tai nguyen
def test_resource_candidates_skip_hud():
    rng = np.random.default_rng(7)
    tpl = rng.integers(0, 255, (44, 54, 3), np.uint8)
    img = np.zeros((960, 540, 3), np.uint8)
    for x, y in ((250, 400), (430, 230), (20, 600), (250, 860)):     # 1 nha + 3 cho trong vung HUD
        img[y:y + 44, x:x + 54] = tpl[:44, :min(54, 540 - x)]
    got = upgrade.res_candidates(img, [tpl, None])
    assert [(x, y) for x, y, _ in got] == [(277, 422)]


def test_resource_templates_exist():
    for n in ("res_food", "res_tower"):
        assert cv2.imread(f"templates/build/{n}.png") is not None


# ---------------------------------------------------------------- runner: SAU MOI BUOC
def test_with_fill_moves_pending_steps_forward():
    mods = {n: n for n in ("upgrade", "construct", "research", "quests", "observe")}
    rest = [(n, n) for n in ("research", "construct", "observe")]
    q = runner.with_fill(rest, ["upgrade", "construct"], mods)
    assert [n for n, _ in q] == ["upgrade", "construct", "research", "observe"]


class _LD:
    def launch(self, i):
        return True

    def runapp(self, i, p):
        pass

    def quit(self, i):
        pass


class _Store:
    def __init__(self, cfg):
        self.cfg, self.d = cfg, {}

    def cfg_for(self, base, idx=None):
        return self.cfg

    def update(self, idx, **kw):
        self.d.update(kw)

    def inst(self, idx):
        return dict(self.d)

    def step_result(self, *a):
        pass


class _Dev:
    idx = 5
    dead = False

    def __init__(self, *a):
        pass

    def configure(self, lc):
        return self

    def wait_ready(self, t):
        return True

    def app_alive(self, p):
        return True


class _Ctx:
    def __init__(self, dev, vision, cfg):
        self.dev, self.v, self.cfg = dev, vision, cfg
        self.debug_shots, self.nav = [], []

    def __getattr__(self, name):
        if name in ("ensure_city", "close_popups", "wd_reset", "human_gate", "exp_flush", "shot"):
            return lambda *a, **k: None
        if name == "world_ready":
            return lambda: True
        raise AttributeError(name)


def _run_visit(monkeypatch, tmp_path, effects, order, modules=None, final=None):
    """Chay run_account voi cac buoc gia. effects[ten](ctx, state) doi trang thai tho. -> thu tu buoc da chay."""
    state, ran = {"busy": 1}, []

    def mod(name):
        def run(ctx):
            ran.append(name)
            return effects.get(name, lambda c, s: 0)(ctx, state)
        return types.SimpleNamespace(run=run)

    cfg = {"ldplayer": {"adb": "x", "game_package": "pkg"}, "modules": {n: True for n in order},
           "build": {"max_builders": 1}, "drain": {"enabled": False}, "priority": {"idle_first": False},
           "learn": {"watch_human": False}, "perf": {"enabled": False}, "guide_follow": False,
           "stepgate": {"enabled": False}, "watchdog": {"enabled": False}, "warday": {}}
    monkeypatch.setattr(runner, "ORDER", [(n, mod(n)) for n in order])
    monkeypatch.setattr(runner, "observe", mod("observe"))
    monkeypatch.setattr(runner, "Device", _Dev)
    monkeypatch.setattr(runner, "Ctx", _Ctx)
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)
    monkeypatch.setattr(runner.warday, "sniff", lambda ctx: None)
    monkeypatch.setattr(runner.warday, "gather_day", lambda cfg: False)
    monkeypatch.setattr(runner.defense, "under_attack", lambda ctx: False)
    monkeypatch.setattr(runner.shield, "run", lambda ctx: 0)
    monkeypatch.setattr(runner.reddots, "final_claims", lambda ctx: (final or (lambda s: None))(state))
    monkeypatch.setattr(runner.reddots, "rcfg", lambda cfg: {"final_sweep": False})
    monkeypatch.setattr(build, "builders", lambda ctx, img=None: (state["busy"], 2))
    r = runner.Runner.__new__(runner.Runner)
    r.base_cfg, r.store, r.vision = cfg, _Store(cfg), types.SimpleNamespace(miss_hits=0)
    r.ld, r.agent, r.mem = _LD(), None, Memory(str(tmp_path / "run.db"))
    r._check = lambda: None
    r._wait_game = lambda *a: None
    r._timed_due = lambda *a: False
    r._serial = None
    r.run_account(5, modules=modules, why="lich" if modules else None, mode="smart")
    assert r.store.d.get("last_error") is None, r.store.d.get("last_error")
    return ran


def _finish(ctx, s):
    s["busy"] = 0            # cong trinh vua xong trong luc buoc nay chay
    return 1


def _start(ctx, s):
    if s["busy"] == 0:
        s["busy"] = 1
        build.note_started(ctx)
        return 1
    return 0


def test_after_step_idle_builder_builds_before_next_step(monkeypatch, tmp_path):
    ran = _run_visit(monkeypatch, tmp_path, {"alliance": _finish, "upgrade": _start},
                     ["alliance", "train", "upgrade", "mainquest", "construct", "quests", "research"])
    assert ran[:3] == ["alliance", "upgrade", "train"]      # xay NGAY; het tho -> phan con lai ve thu tu cu
    assert ran == ["alliance", "upgrade", "train", "mainquest", "construct", "quests", "research", "observe"]


def test_after_step_busy_builder_inserts_nothing(monkeypatch, tmp_path):
    ran = _run_visit(monkeypatch, tmp_path, {}, ["alliance", "train", "upgrade", "construct"])
    assert ran == ["alliance", "train", "upgrade", "construct", "observe"]


def test_fill_includes_build_steps_outside_scheduled_visit(monkeypatch, tmp_path):
    """Luot lich khong co upgrade/construct (luc lap lich tho dang ban) ma tho ranh giua luot -> van xay."""
    ran = _run_visit(monkeypatch, tmp_path, {"alliance": _finish, "construct": _start},
                     ["alliance", "train", "upgrade", "construct"], modules={"alliance", "train"})
    assert ran == ["alliance", "upgrade", "construct", "train", "observe"]


def test_no_endless_loop_when_nothing_buildable(monkeypatch, tmp_path):
    ran = _run_visit(monkeypatch, tmp_path, {"alliance": lambda c, s: s.update(busy=0) or 0},
                     ["alliance", "train", "research", "heal", "upgrade", "construct"])
    assert ran == ["alliance", "upgrade", "construct", "train", "research", "heal", "observe"]


def test_builder_freed_during_final_claims_builds_before_observe(monkeypatch, tmp_path):
    ran = _run_visit(monkeypatch, tmp_path, {"upgrade": _start}, ["train", "upgrade", "reddots"],
                     final=lambda s: s.update(busy=0))
    assert ran[-2:] == ["upgrade", "observe"] and ran.count("observe") == 1
