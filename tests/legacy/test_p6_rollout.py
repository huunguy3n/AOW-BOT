"""P6: agent chi chay khi cong tac chung bat; tran cung 2 may o runner / LDConsole; web bat-tat ro rang."""
import time

import yaml

from bot import device, scheduler
from bot.runner import RingLog, Runner
from tests.legacy.test_stepgate import SchedMem
from web.server import create_app

ORDER = ["gather", "train"]
ON = {"gather": True, "train": True}


def sched_cfg(switch, mode="agent"):
    return {"schedule": {"mode": mode}, "stepgate": {}, "warday": {"enabled": False}, "agent": {"enabled": switch}}


def test_switch_off_machine_keeps_gather_in_legacy_schedule():
    """Cong tac tat: may chon Agent chay nhu may thuong - gather KHONG bi bo (truoc P6 bi bo -> khong ai gui quan)."""
    now = time.time()
    v = scheduler.decide_one(SchedMem(), 0, ORDER, ON, sched_cfg(False), now)
    assert "gather" in v.steps
    assert "gather" in scheduler.piggyback_steps(SchedMem(), 0, ORDER, ON, sched_cfg(False), now)
    steps_on = scheduler.piggyback_steps(SchedMem(), 0, ORDER, ON, sched_cfg(True), now)
    assert "gather" not in steps_on
    v_on = scheduler.decide_one(SchedMem(), 0, ORDER, ON, sched_cfg(True), now)
    assert "gather" not in v_on.steps


class Store:
    def __init__(self, cfg):
        self.cfg = cfg

    def cfg_for(self, base, idx=None):
        return self.cfg


def runner_with(parallel, max_running):
    r = Runner.__new__(Runner)
    r.store = Store({"schedule": {"parallel": parallel}, "ldplayer": {"max_running": max_running}})
    r.base_cfg = {}
    return r


def test_runner_never_more_than_two_threads():
    assert runner_with(2, 2)._parallel() == 2
    assert runner_with(5, 5)._parallel() == 2         # config sai van chi 2
    assert runner_with(3, 1)._parallel() == 1
    assert runner_with(2, 9).effective_settings()["max_running"] == 2


class FakeConsole(device.LDConsole):
    """ldconsole gia: list2 tra cac may dang chay; launch them vao danh sach."""

    def __init__(self, running, max_running):
        super().__init__({"ldconsole": "x", "max_running": max_running, "wait_slot_min": 0, "boot_timeout": 5})
        self.on = list(running)
        self.launched = []

    def run(self, *args, timeout=60):
        if args[0] == "launch":
            self.launched.append(int(args[2]))
            self.on.append(int(args[2]))
        return ""

    def is_running(self, idx):
        return idx in self.on

    def running(self):
        return list(self.on)


def test_ldconsole_refuses_third_machine(monkeypatch):
    monkeypatch.setattr(device.time, "sleep", lambda s: None)
    c = FakeConsole([0, 1], max_running=5)            # cau hinh 5 -> van cat ve 2
    assert c.max_running == 2
    assert c.launch(3) is False and c.launched == []
    c2 = FakeConsole([0], max_running=2)
    assert c2.launch(3) is True and c2.launched == [3]


class WebStore:
    def __init__(self):
        self.settings = {}

    def snapshot(self):
        return {"instances": {}, "runner": {}}

    def cfg_for(self, base, idx=None):
        return {**base, "agent": dict(self.settings.get("agent") or {}),
                "schedule": {"mode": "agent" if idx == 1 else "smart"}}

    def set_settings(self, scope, patch):
        assert scope == "global"
        self.settings.update(patch)


class NoMem:
    @staticmethod
    def query(sql, args=()):
        return []


class WebRunner:
    def __init__(self):
        self.mem, self.base_cfg, self.running, self.queue = NoMem(), {"instances": [0, 1]}, False, []


def test_web_switch_status_and_validation():
    st = WebStore()
    c = create_app(WebRunner(), st, RingLog()).test_client()
    a = c.get("/api/agent").get_json()
    assert a["switch"] is False and a["status"] == {"0": "off", "1": "blocked"}
    assert c.post("/api/agent/switch", json={"on": "true"}).status_code == 400     # chi nhan bool that
    assert c.post("/api/agent/switch", json={}).status_code == 400
    assert st.settings == {}
    assert c.post("/api/agent/switch", json={"on": True}).get_json() == {"ok": True, "on": True}
    a = c.get("/api/agent").get_json()
    assert a["switch"] is True and a["status"]["1"] == "on"
    c.post("/api/agent/switch", json={"on": False})
    assert c.get("/api/agent").get_json()["status"]["1"] == "blocked"


def test_config_yaml_default_switch_off():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["agent"]["enabled"] is False
    assert cfg["ldplayer"]["max_running"] <= 2 and cfg["schedule"]["parallel"] <= 2
