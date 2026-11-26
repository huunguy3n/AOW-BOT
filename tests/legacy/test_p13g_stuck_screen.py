"""P13g-2: #0 26/11 chay man 720x1280 -> khong anh mau nao khop -> 'goto(city) ... man cuoi unknown' -> bo luot.
Them: man nap game, cuu ket truoc khi bo luot, log loi buoc co noi dung, ADB hong luc quet cham do khong lam mat
buoc observe."""
import inspect
import logging
import os
import types
from typing import ClassVar

import cv2
import numpy as np
import pytest

from bot import device, human, runner, screens, touch
from bot.device import Device, ScreencapError
from bot.memory import Memory
from bot.vision import Vision

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
FIX = os.path.join(ROOT, "tests", "fixtures", "p13g")


# ---------- do phan giai khac 540x960 ----------
@pytest.mark.parametrize("w,h,scale", [
    (540, 960, 1.0), (720, 1280, 720 / 540), (1080, 1920, 2.0), (1280, 720, None), (960, 540, None), (720, 1600, None),
])
def test_frame_scale(w, h, scale):
    assert device.frame_scale(w, h) == (pytest.approx(scale) if scale else None)


def _dev(monkeypatch, shape):
    d = Device("adb", 0)
    sent = []
    monkeypatch.setattr(d, "_raw_shot", lambda: np.zeros((*shape, 3), np.uint8))
    monkeypatch.setattr(d, "_cmd", lambda *a, **k: sent.append(a))
    return d, sent


def test_720x1280_frames_are_scaled_down_and_input_scaled_up(monkeypatch, caplog):
    d, sent = _dev(monkeypatch, (1280, 720))
    with caplog.at_level(logging.WARNING, logger="aow"):
        assert d.screencap().shape == (960, 540, 3)
        d.screencap()
    assert caplog.text.count("720x1280, khac 540x960") == 1              # canh bao 1 lan
    d.tap(156, 581)                                                        # nut "Huy" tren he 540x960
    d.swipe(270, 650, 600, 650, 500)                                       # kep 600 -> 539 roi moi nhan
    assert sent[0] == ("shell", "input", "tap", 208, 775)
    assert sent[1] == ("shell", "input", "swipe", 360, 867, 719, 867, 500)
    assert next(iter(d.recent))[2:4] == [156, 581]                          # HumanWatch so theo he 540x960
    d.tap(539, 959)
    assert sent[2][-2:] == (719, 1279)


def test_normal_screen_unchanged(monkeypatch):
    d, sent = _dev(monkeypatch, (960, 540))
    d.screencap()
    d.tap(156, 581)
    assert d.scale == 1.0 and sent == [("shell", "input", "tap", 156, 581)]


def test_landscape_frame_keeps_last_scale(monkeypatch):
    d, _ = _dev(monkeypatch, (1280, 720))
    d.screencap()
    monkeypatch.setattr(d, "_raw_shot", lambda: np.zeros((720, 1280, 3), np.uint8))   # man chinh Android nam ngang
    assert d.screencap().shape == (720, 1280, 3) and d.scale == pytest.approx(4 / 3)


def test_finger_and_human_watch_use_scale():
    assert touch.Finger("adb", "s").sx == pytest.approx(touch.SX)
    assert touch.Finger("adb", "s", scale=4 / 3).sy == pytest.approx(touch.SY * 4 / 3)
    assert 'getattr(self.dev, "scale", 1.0)' in inspect.getsource(human.HumanWatch._read)


# ---------- man nap game ----------
def test_splash_is_loading_not_unknown():
    v = Vision(os.path.join(ROOT, "templates"))
    logo = v.load("common/splash_logo")
    blocks = np.random.default_rng(1).integers(0, 255, (16, 9, 3), np.uint8)     # man co chi tiet, khong toi
    img = cv2.resize(blocks, (540, 960), interpolation=cv2.INTER_NEAREST)
    assert screens.nav_action(img, v, "city")[:2] == ("unknown", "back")
    img[8:8 + logo.shape[0], 129:129 + logo.shape[1]] = logo
    assert screens.nav_action(img, v, "city")[:2] == ("loading", "wait")   # khong bam Back luc dang nap


@pytest.mark.fixtures
@pytest.mark.parametrize("name,want", [
    ("i0_city_720.png", "city"), ("i0_exit_720.png", "exit_dialog"), ("i0_loading_720.png", "loading"),
])
def test_real_720_frames_recognized_after_normalize(name, want):
    img = cv2.imread(os.path.join(FIX, name))
    if img is None:
        pytest.skip("thieu anh fixture")
    v = Vision(os.path.join(ROOT, "templates"))
    assert img.shape[:2] == (1280, 720)
    if want != "loading":
        assert screens.identify(img, v)[0] == "unknown"                    # truoc P13g
    assert screens.identify(device.normalize_frame(img)[0], v)[0] == want


# ---------- log loi buoc + ke hoach cuu ----------
def test_step_error_line_has_exception_on_first_line():
    line = runner.step_error_line("observe", ScreencapError("Khong chup duoc man hinh (may khong phan hoi)"))
    assert line == "Loi o buoc observe: ScreencapError: Khong chup duoc man hinh (may khong phan hoi)"
    assert "\n" not in line


@pytest.mark.parametrize("lost,rescues,most,plan", [
    (0, 0, 1, None), (1, 0, 1, None), (2, 0, 1, "rescue"), (2, 1, 1, None), (3, 1, 1, "give_up"),
    (2, 0, 0, None), (3, 0, 0, "give_up"),
])
def test_lost_plan(lost, rescues, most, plan):
    assert runner.lost_plan(lost, rescues, most) == plan


# ---------- luong run_account voi cac buoc gia ----------
class _Dev:
    idx = 0
    dead = False

    def __init__(self, *a):
        pass

    def configure(self, lc):
        return self

    def wait_ready(self, t):
        return True

    def app_alive(self, p):
        return True

    def force_stop(self, p):
        _World.log.append("force_stop")


class _World:
    """Trang thai chung: home = ve duoc thanh pho khong; restart_fixes = khoi dong lai game co het ket khong."""
    log: ClassVar[list] = []
    home = False
    restart_fixes = True


class _Ctx:
    def __init__(self, dev, vision, cfg):
        self.dev, self.v, self.cfg = dev, vision, cfg
        self.debug_shots, self.nav = [], []

    def goto(self, target="city", rounds=10):
        _World.log.append(f"goto:{target}")
        self.nav.append(("city", "done", None) if _World.home else ("unknown", "back", None))
        return _World.home

    def save_debug(self, tag):
        return f"logs/shots/{tag}.png"

    def __getattr__(self, name):
        if name in ("ensure_city", "close_popups", "wd_reset", "human_gate", "exp_flush", "shot"):
            return lambda *a, **k: None
        if name == "world_ready":
            return lambda: True
        raise AttributeError(name)


class _LD:
    def launch(self, i):
        return True

    def runapp(self, i, p):
        if _World.restart_fixes and "force_stop" in _World.log:
            _World.home = True

    def quit(self, i):
        pass


class _Store:
    def __init__(self, cfg):
        self.cfg, self.d, self.results = cfg, {}, []

    def cfg_for(self, base, idx=None):
        return self.cfg

    def update(self, idx, **kw):
        self.d.update(kw)

    def inst(self, idx):
        return dict(self.d)

    def step_result(self, idx, name, res, *a):
        self.results.append((name, res))


def _visit(monkeypatch, tmp_path, order, effects=None, final=None, final_sweep=False, recover=None):
    _World.log = []
    ran = []

    def mod(name):
        def run(ctx):
            ran.append(name)
            ctx.goto("city")
            return (effects or {}).get(name, lambda c: 0)(ctx)
        return types.SimpleNamespace(run=run)

    cfg = {"ldplayer": {"adb": "x", "game_package": "pkg"}, "modules": {n: True for n in order},
           "drain": {"enabled": False}, "priority": {"idle_first": False}, "build": {"fill_idle": False},
           "learn": {"watch_human": False}, "perf": {"enabled": False}, "guide_follow": False,
           "stepgate": {"enabled": False}, "watchdog": {"enabled": False}, "warday": {}, "nav": {"rescue_max": 1}}
    monkeypatch.setattr(runner, "ORDER", [(n, mod(n)) for n in order])
    monkeypatch.setattr(runner, "observe", mod("observe"))
    monkeypatch.setattr(runner, "Device", _Dev)
    monkeypatch.setattr(runner, "Ctx", _Ctx)
    monkeypatch.setattr(runner.time, "sleep", lambda s: None)
    monkeypatch.setattr(runner.warday, "sniff", lambda ctx: None)
    monkeypatch.setattr(runner.warday, "gather_day", lambda cfg: False)
    monkeypatch.setattr(runner.defense, "under_attack", lambda ctx: False)
    monkeypatch.setattr(runner.shield, "run", lambda ctx: 0)
    monkeypatch.setattr(runner.reddots, "final_claims", final or (lambda ctx: 0))
    monkeypatch.setattr(runner.reddots, "run", lambda ctx, final=False: 0)
    monkeypatch.setattr(runner.reddots, "rcfg", lambda cfg: {"final_sweep": final_sweep})
    r = runner.Runner.__new__(runner.Runner)
    r.base_cfg, r.store, r.vision = cfg, _Store(cfg), types.SimpleNamespace(miss_hits=0)
    r.ld, r.agent, r.mem = _LD(), None, Memory(str(tmp_path / "run.db"))
    r._check = lambda: None
    r._wait_game = lambda *a: None
    r._timed_due = lambda *a: False
    if recover:
        r._recover_device = recover
    r.run_account(0, mode="smart")
    return ran, r.store


def test_stuck_visit_is_rescued_by_restarting_game(monkeypatch, tmp_path):
    _World.home, _World.restart_fixes = False, True
    ran, store = _visit(monkeypatch, tmp_path, ["reddots", "notify", "rewards", "daily"])
    assert ran == ["reddots", "notify", "rewards", "daily", "observe"]      # khong bo luot
    assert _World.log.count("force_stop") == 1
    assert store.d.get("last_error") is None


def test_stuck_visit_is_dropped_only_after_rescue_failed(monkeypatch, tmp_path):
    _World.home, _World.restart_fixes = False, False
    ran, store = _visit(monkeypatch, tmp_path, ["reddots", "notify", "rewards", "daily"])
    assert ran == ["reddots", "notify"]                                     # khong chay tiep tren man la
    assert _World.log.count("force_stop") == 1
    assert "da cuu 1 lan" in store.d["last_error"] and "unknown" in store.d["last_error"]


def test_adb_dead_during_final_claims_still_runs_observe(monkeypatch, tmp_path, caplog):
    _World.home = True

    def final(ctx):
        ctx.dev.dead = True
        raise ScreencapError("Khong chup duoc man hinh (2 lan timeout 10 s)")

    recovered = []

    def recover(ctx, idx, pkg, cfg, done, name):
        recovered.append(name)
        ctx.dev.dead = False
        return True

    with caplog.at_level(logging.WARNING, logger="aow"):
        ran, store = _visit(monkeypatch, tmp_path, ["reddots"], final=final, recover=recover)
    assert ran == ["reddots", "observe"] and recovered == ["observe"]
    assert ("observe", "ok") in store.results
    assert "Nhan qua cuoi luot: loi ScreencapError: Khong chup duoc man hinh" in caplog.text
    assert "Loi o buoc" not in caplog.text


def test_step_exception_is_logged_on_first_line(monkeypatch, tmp_path, caplog):
    _World.home = True

    def boom(ctx):
        raise ValueError("so lieu hong")

    with caplog.at_level(logging.ERROR, logger="aow"):
        _, store = _visit(monkeypatch, tmp_path, ["daily"], effects={"daily": boom})
    first = [r.getMessage().splitlines()[0] for r in caplog.records]
    assert "Loi o buoc daily: ValueError: so lieu hong" in first
    assert "daily: ValueError: so lieu hong" in store.d["last_error"]
