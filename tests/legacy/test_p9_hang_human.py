"""P9-1 (live-run-2 #1, 2026-11-24): may treo -> khoi dong lai may + game, chay tiep buoc ke tiep;
timeout screencap ngan; chu cham tay lien tiep -> bot tam dung."""
import inspect
import subprocess
import types

import numpy as np
import pytest
import yaml

from bot import device, hang
from bot.ctx import Ctx
from bot.device import Device, ScreencapError
from bot.runner import Runner


# ---------- timeout screencap ----------
def test_default_screencap_timeouts_short():
    d = Device("adb", 1)
    assert d.shot_timeout == hang.SHOT_TIMEOUT_S <= 5
    assert d.shot_budget == hang.SHOT_BUDGET_S <= 15
    assert d.reconnect_wait == hang.RECONNECT_WAIT_S <= 10
    assert hang.worst_detect_s() <= 30          # truoc P9 ~47 s, truoc P1 ~190 s: khong de treo hang phut


def test_config_yaml_screencap_matches_defaults():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    sc = cfg["ldplayer"]["screencap"]
    assert sc["timeout_s"] <= 5 and sc["budget_s"] <= 15 and sc["reconnect_wait_s"] <= 10
    assert cfg["ldplayer"]["recover"] is True and cfg["ldplayer"]["recover_max"] >= 1
    hp = cfg["human_pause"]
    assert hp["enabled"] and hp["taps"] >= 2 and hp["quiet_s"] > 0


def test_hung_device_detected_within_worst_case(monkeypatch):
    clock = [0.0]

    def run(cmd, capture_output=True, timeout=None, **kw):
        if "getprop" in cmd or "connect" in cmd:
            clock[0] += timeout or 0
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        clock[0] += timeout
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(device.subprocess, "run", run)
    monkeypatch.setattr(device.time, "sleep", lambda s: clock.__setitem__(0, clock[0] + s))
    monkeypatch.setattr(device.time, "time", lambda: clock[0])
    monkeypatch.setattr(device.time, "monotonic", lambda: clock[0])
    d = Device("adb", 1)
    with pytest.raises(ScreencapError):
        d.screencap()
    assert d.dead
    assert clock[0] <= 60                        # ca do lai dia chi (wait_ready thu 3 dia chi x 3 s toi thieu)


# ---------- quyet dinh cuu may ----------
def test_recover_plan():
    assert hang.recover_plan(running=False, adb_ok=None, done=0, max_recover=1) == "launch"
    assert hang.recover_plan(running=True, adb_ok=True, done=0, max_recover=1) == "reboot"
    assert hang.recover_plan(running=True, adb_ok=None, done=1, max_recover=1) == "give_up"
    assert hang.recover_cfg({}) == {"max": 1, "enabled": True}


class FakeLD:
    def __init__(self, running=(1,), launch_ok=True):
        self._running = list(running)
        self.calls = []
        self.launch_ok = launch_ok

    def running(self):
        self.calls.append("list2")
        return list(self._running)

    def quit(self, idx):
        self.calls.append(("quit", idx))
        self._running = [i for i in self._running if i != idx]
        return True

    def launch(self, idx):
        self.calls.append(("launch", idx))
        if self.launch_ok:
            self._running.append(idx)
        return self.launch_ok

    def runapp(self, idx, pkg):
        self.calls.append(("runapp", idx, pkg))


class FakeStore:
    def __init__(self):
        self.d = {}

    def update(self, idx, **kw):
        self.d.update(kw)

    def inst(self, idx):
        return self.d


class FakeDev:
    def __init__(self, ready=True):
        self.dead = True
        self.ready = ready
        self.cmds = []

    def wait_ready(self, t):
        return self.ready

    def _cmd(self, *a, **k):          # bat moi lenh adb: khong duoc co pm clear / uninstall
        self.cmds.append(a)


class FakeCtx:
    def __init__(self, dev):
        self.dev = dev
        self.popups = 0

    def wd_reset(self, *_):
        pass

    def close_popups(self, **kw):
        self.popups += 1

    def shot(self):
        return np.zeros((960, 540, 3), np.uint8)


def _runner(ld):
    r = types.SimpleNamespace(ld=ld, store=FakeStore(), waited=[])
    r._wait_game = lambda ctx, cfg, pkg: r.waited.append(pkg)
    return r


CFG = {"ldplayer": {"boot_timeout": 5, "recover": True, "recover_max": 1}}


def test_recover_hung_running_device_reboots_and_reopens_game():
    ld = FakeLD(running=(1, 3))
    r = _runner(ld)
    dev = FakeDev()
    ctx = FakeCtx(dev)
    assert Runner._recover_device(r, ctx, 1, "pkg.vn", CFG, 0, "quests") is True
    assert ("quit", 1) in ld.calls and ("launch", 1) in ld.calls and ("runapp", 1, "pkg.vn") in ld.calls
    assert ld.calls[0] == "list2"                      # kiem ldconsole list2 truoc
    assert dev.dead is False and r.waited == ["pkg.vn"] and ctx.popups == 1
    assert ("quit", 3) not in ld.calls                 # khong dung may khac
    assert not any("clear" in map(str, c) or "uninstall" in map(str, c) for c in dev.cmds)


def test_recover_stopped_device_only_launches():
    ld = FakeLD(running=())
    r = _runner(ld)
    assert Runner._recover_device(r, FakeCtx(FakeDev()), 1, "p", CFG, 0, "quests") is True
    assert ("quit", 1) not in ld.calls and ("launch", 1) in ld.calls


def test_recover_gives_up_after_max_and_on_failure():
    ld = FakeLD()
    assert Runner._recover_device(_runner(ld), FakeCtx(FakeDev()), 1, "p", CFG, 1, "quests") is False
    assert ("launch", 1) not in ld.calls
    assert Runner._recover_device(_runner(FakeLD(launch_ok=False)), FakeCtx(FakeDev()), 1, "p", CFG, 0, "x") is False
    dev = FakeDev(ready=False)
    assert Runner._recover_device(_runner(FakeLD()), FakeCtx(dev), 1, "p", CFG, 0, "x") is False
    assert dev.dead                                     # ADB khong ve -> van dead -> runner bo may
    off = {"ldplayer": {"recover": False}}
    assert Runner._recover_device(_runner(FakeLD()), FakeCtx(FakeDev()), 1, "p", off, 0, "x") is False


def test_runner_continues_with_next_step_after_recovery():
    """Ma nguon run_account: khi dead -> goi _recover_device, thanh cong thi `continue` (buoc ke tiep), khong raise."""
    src = inspect.getsource(Runner.run_account)
    i = src.index("self._recover_device(")
    seg = src[i:i + 300]
    assert "continue" in seg and "raise RuntimeError" in seg
    assert seg.index("continue") < seg.index("raise RuntimeError")   # cuu duoc -> buoc ke tiep; khong -> bo may
    assert "blind >= 2" in src[i - 600:i]                             # 2 buoc mu lien tiep cung duoc cuu


# ---------- tam dung khi chu cham tay ----------
def test_human_pause_triggers_on_burst_and_resumes_when_quiet():
    hp = hang.HumanPause(taps=3, window_s=20, quiet_s=30)
    # live-run-2 11:00:51 .. 11:00:57: 5 lan cham trong 6 s
    for t in (51, 53, 55, 56, 57):
        hp.note(1000 + t)
    assert hp.paused(1000 + 58)
    assert hp.paused(1000 + 80)                  # tay yen 23 s < 30 -> van dung
    assert not hp.paused(1000 + 88)              # yen 31 s -> chay lai
    assert hp.pauses == 1


def test_single_human_tap_does_not_pause():
    hp = hang.HumanPause(taps=3, window_s=20, quiet_s=30)
    hp.note(100)
    hp.note(150)
    assert not hp.paused(151)
    hp.enabled = False
    for t in range(5):
        hp.note(200 + t)
    assert not hp.paused(206)


def test_human_pause_wait_loops_until_quiet_and_is_bounded():
    clock = [0.0]
    hp = hang.HumanPause(taps=2, window_s=10, quiet_s=5, max_wait_s=60)
    hp.note(0.0)
    hp.note(1.0)
    clock[0] = 2.0
    waited = hp.wait(now=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
    assert 3.0 <= waited <= 5.0                  # cho toi khi yen 5 s tu lan cham cuoi (t=1)
    # chu cham lien tuc -> khong cho qua max_wait
    hp2 = hang.HumanPause(taps=2, window_s=10, quiet_s=5, max_wait_s=20)
    clock[0] = 0.0

    def sleep(s):
        clock[0] += s
        hp2.note(clock[0])

    hp2.note(0.0)
    hp2.note(0.5)
    assert hp2.wait(now=lambda: clock[0], sleep=sleep) <= 21


def test_ctx_tap_waits_for_human():
    calls = []
    hp = hang.HumanPause(taps=2, window_s=10, quiet_s=5)
    c = types.SimpleNamespace(human_pause=hp, step="mission", step_limit=None, _img="x",
                              wd_reset=lambda *a: calls.append("wd"))
    hp.wait = lambda why="", **k: calls.append(("wait", why)) or 3.0
    assert Ctx.human_gate(c) == 3.0
    assert calls[0] == ("wait", "o buoc mission") and "wd" in calls and c._img is None
    c.human_pause = None
    assert Ctx.human_gate(c) == 0.0
