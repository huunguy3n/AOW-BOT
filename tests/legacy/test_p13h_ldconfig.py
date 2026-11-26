"""P13h: #0 26/11 bi LDPlayer tra ve mac dinh (1280x720, ADB tung tat). Truoc khi bat may: doc leidian{idx}.config,
sai thi sua khi may DA TAT (modify --resolution + chi khoa adbDebug); tat may nhe va cho tat han.
Test hoan toan voi file gia + ldconsole gia (khong goi ldconsole / adb that)."""
import json
import logging
import os
import time

import pytest
import yaml

from bot import device, ldconfig, runner
from bot.device import LDConsole

IDENTITY = {
    "propertySettings.phoneIMEI": "000000000000000",
    "propertySettings.phoneModel": "SM-FAKE",
    "propertySettings.phoneAndroidId": "feedfacefeedface",
    "propertySettings.phoneIMSI": "111111111111111",
    "propertySettings.macAddress": "AABBCCDDEEFF",
    "propertySettings.phoneManufacturer": "fakemaker",
    "propertySettings.phoneSimSerial": "22222222222222222222",
    "propertySettings.phoneNumber": "3333333333",
}


def config_text(w=1280, h=720, dpi=240, adb=0):
    """Giong dinh dang that: 4 dau cach, CRLF, khong newline cuoi, khoa phang co dau cham."""
    d = dict(IDENTITY)
    d["advancedSettings.resolution"] = {"width": w, "height": h}
    d["advancedSettings.resolutionDpi"] = dpi
    d["basicSettings.left"] = 12
    if adb is not None:
        d["basicSettings.adbDebug"] = adb
    d["statusSettings.playerName"] = "MF001"
    return json.dumps(d, indent=4).replace("\n", "\r\n").encode()


class Fake(LDConsole):
    """ldconsole gia. state: 'off' | 'on' | 'busy'. modify sua dung do phan giai trong file nhu ban that."""

    def __init__(self, folder, state="off", cfg_for=None, modify_works=True, **lc):
        cfg = {"ldconsole": str(folder / "ldconsole.exe"), "config_settle_s": 0, "wait_slot_min": 0,
               "boot_timeout": 5, **lc}
        super().__init__(cfg, cfg_for)
        self.folder = folder / "vms" / "config"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.states = {0: state}
        self.calls = []
        self.modify_works = modify_works

    def write(self, raw, idx=0):
        p = self.folder / f"leidian{idx}.config"
        p.write_bytes(raw)
        return p

    def run(self, *args, timeout=60):
        self.calls.append(tuple(args))
        cmd = args[0]
        idx = args[2] if len(args) > 2 else 0
        st = self.states.get(idx, "off")
        if cmd == "list2":
            cols = {"off": "0,0,0,-1,-1", "on": "11,22,1,4000,4001", "busy": "0,0,0,4000,4001"}
            return "\n".join(f"{i},MF{i},{cols[s]},540,960,240" for i, s in self.states.items())
        if cmd == "isrunning":
            return "running" if st == "on" else "stop"
        if cmd == "launch":
            self.states[idx] = "on"
        if cmd == "quit":
            self.states[idx] = "off"
        if cmd == "modify" and self.modify_works:
            w, h, dpi = map(int, args[4].split(","))
            p = self.folder / f"leidian{idx}.config"
            d = json.loads(p.read_bytes())
            d["advancedSettings.resolution"] = {"width": w, "height": h}
            d["advancedSettings.resolutionDpi"] = dpi
            p.write_bytes(json.dumps(d, indent=4).replace("\n", "\r\n").encode())
        return ""

    def did(self, cmd):
        return [c for c in self.calls if c[0] == cmd]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    clock = [time.time()]
    monkeypatch.setattr(device.time, "time", lambda: clock[0])
    monkeypatch.setattr(device.time, "sleep", lambda s: clock.__setitem__(0, clock[0] + max(s, 0.01)))
    return clock


def load(path):
    return json.loads(path.read_bytes())


# ---------- sai cau hinh, may dang tat ----------
def test_default_reset_config_is_fixed_before_launch(tmp_path, caplog):
    ld = Fake(tmp_path)
    p = ld.write(config_text(1280, 720, 240, adb=0))
    caplog.set_level(logging.INFO, logger="aow")
    assert ld.launch(0) is True
    assert ld.did("modify") == [("modify", "--index", 0, "--resolution", "540,960,240")]
    d = load(p)
    assert d["advancedSettings.resolution"] == {"width": 540, "height": 960}
    assert d["advancedSettings.resolutionDpi"] == 240 and d["basicSettings.adbDebug"] == 1
    assert {k: d[k] for k in IDENTITY} == IDENTITY
    names = [c[0] for c in ld.calls]
    assert names.index("modify") < names.index("launch")             # sua xong moi bat
    warn = " ".join(r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)
    assert "1280" in warn and "basicSettings.adbDebug=0" in warn      # gia tri cu
    assert not any(v in caplog.text for v in IDENTITY.values())       # khong log khoa dinh danh
    assert not os.path.exists(str(p) + ".aowtmp")


def test_only_adb_wrong_rewrites_only_that_value(tmp_path):
    ld = Fake(tmp_path)
    raw = config_text(540, 960, 240, adb=0)
    p = ld.write(raw)
    assert ld.check_display(0) == "fixed"
    assert ld.did("modify") == []
    assert p.read_bytes() == raw.replace(b'"basicSettings.adbDebug": 0', b'"basicSettings.adbDebug": 1')


@pytest.mark.parametrize("old", [config_text(540, 960, 240, adb=None), b"\xef\xbb\xbf" + config_text(adb=None),
                                 b"{}"])
def test_missing_adb_key_is_inserted_without_touching_others(old):
    new = ldconfig.with_adb_debug(old)
    assert json.loads(new.decode("utf-8-sig")) == {**json.loads(old.decode("utf-8-sig")), "basicSettings.adbDebug": 1}
    assert new.startswith(old[:old.index(b"{") + 1]) and new.endswith(old[old.index(b"{") + 1:])


def test_adb_rewrite_refuses_when_it_cannot_be_exact():
    odd = b'{"basicSettings.adbDebug": 0.5, "x": 1}'      # regex chi doi phan nguyen -> JSON doi khac ky vong
    with pytest.raises(ValueError):
        ldconfig.with_adb_debug(odd)


@pytest.mark.parametrize("kw", [{"dpi": 320}, {"w": 720, "h": 1280}])
def test_resolution_or_dpi_alone_triggers_modify(tmp_path, kw):
    ld = Fake(tmp_path)
    ld.write(config_text(**{"w": 540, "h": 960, "adb": 1, **kw}))
    assert ld.check_display(0) == "fixed"
    assert ld.did("modify") == [("modify", "--index", 0, "--resolution", "540,960,240")]


def test_modify_only_ever_passes_resolution(tmp_path):
    ld = Fake(tmp_path)
    ld.write(config_text())
    ld.launch(0)
    assert [a for c in ld.did("modify") for a in c if str(a).startswith("--")] == ["--index", "--resolution"]


def test_modify_without_effect_is_reported_and_launch_continues(tmp_path, caplog):
    ld = Fake(tmp_path, modify_works=False)
    p = ld.write(config_text())
    assert ld.launch(0) is True and ld.did("launch")
    assert "chua duoc" in caplog.text and load(p)["basicSettings.adbDebug"] == 1


# ---------- khong duoc dung vao ----------
def test_correct_config_is_left_alone(tmp_path):
    ld = Fake(tmp_path)
    raw = config_text(540, 960, 240, adb=1)
    p = ld.write(raw)
    before = os.stat(p).st_mtime_ns
    assert ld.check_display(0) == "ok"
    assert ld.launch(0) is True
    assert ld.did("modify") == [] and p.read_bytes() == raw and os.stat(p).st_mtime_ns == before


@pytest.mark.parametrize("state", ["on", "busy"])
def test_running_or_stopping_machine_is_never_written(tmp_path, caplog, state):
    ld = Fake(tmp_path, state=state)
    raw = config_text()
    p = ld.write(raw)
    assert ld.check_display(0) == "running"
    assert ld.did("modify") == [] and ld.did("quit") == [] and p.read_bytes() == raw
    assert "KHONG modify" in caplog.text


def test_launch_of_running_machine_only_warns(tmp_path, caplog):
    ld = Fake(tmp_path, state="on")
    raw = config_text()
    p = ld.write(raw)
    assert ld.launch(0) is True
    assert not ld.did("launch") and not ld.did("modify") and not ld.did("quit")
    assert p.read_bytes() == raw and "Cau hinh LDPlayer sai" in caplog.text


def test_fixed_on_next_launch_after_gentle_quit(tmp_path):
    ld = Fake(tmp_path, state="on")
    p = ld.write(config_text())
    ld.launch(0)
    assert ld.quit(0) is True
    assert ld.launch(0) is True
    assert load(p)["basicSettings.adbDebug"] == 1 and len(ld.did("modify")) == 1


def test_unknown_state_is_not_treated_as_off(tmp_path):
    ld = Fake(tmp_path)
    ld.states = {}                                    # list2 rong / loi
    raw = config_text()
    p = ld.write(raw)
    assert ld.check_display(0) == "running" and p.read_bytes() == raw and not ld.did("modify")


def test_half_written_config_is_not_touched(tmp_path, caplog):
    ld = Fake(tmp_path)
    raw = config_text()[:150]
    p = ld.write(raw)
    assert ld.check_display(0) == "unreadable"
    assert ld.launch(0) is True and p.read_bytes() == raw and not ld.did("modify")
    assert not any(v in caplog.text for v in IDENTITY.values())


def test_missing_file_or_disabled_check_is_skipped(tmp_path):
    ld = Fake(tmp_path)
    assert ld.check_display(0) == "skip" and ld.calls == []
    off = Fake(tmp_path, fix_display=False)
    off.write(config_text())
    assert off.check_display(0) == "skip" and off.calls == []


def test_bad_expected_value_does_not_block_launch(tmp_path, caplog):
    ld = Fake(tmp_path, resolution="rong")
    raw = config_text()
    p = ld.write(raw)
    assert ld.launch(0) is True and p.read_bytes() == raw and not ld.did("modify")
    assert "Kiem cau hinh LDPlayer loi" in caplog.text


def test_waits_for_file_to_settle_before_writing(tmp_path, monkeypatch):
    ld = Fake(tmp_path, config_settle_s=5)
    p = ld.write(config_text())
    clock = [os.path.getmtime(p) + 1]                 # LDPlayer vua ghi 1 s truoc
    monkeypatch.setattr(ldconfig.time, "time", lambda: clock[0])
    slept = []

    def sleep(s):
        slept.append(s)
        assert not ld.did("modify")                   # chua yen thi chua sua
        clock[0] += s

    monkeypatch.setattr(ldconfig.time, "sleep", sleep)
    ld.modify_works = False
    ld.check_display(0)
    assert sum(slept) >= 4 and ld.did("modify")


def test_file_that_keeps_changing_is_given_up(tmp_path, monkeypatch):
    p = tmp_path / "leidian0.config"
    p.write_bytes(config_text())
    clock = [0.0]
    monkeypatch.setattr(ldconfig.os.path, "getmtime", lambda _: clock[0])
    monkeypatch.setattr(ldconfig.time, "time", lambda: clock[0])
    monkeypatch.setattr(ldconfig.time, "sleep", lambda s: clock.__setitem__(0, clock[0] + s))
    assert ldconfig.wait_quiet(str(p), 5, max_wait_s=12) is False


# ---------- cau hinh ky vong ----------
def test_per_machine_expected_display(tmp_path):
    ld = Fake(tmp_path, cfg_for=None)
    own = {**ld.cfg, "resolution": [720, 1280], "dpi": 320}
    ld.cfg_for = lambda i: own
    p = ld.write(config_text(720, 1280, 320, adb=1))
    assert ld.check_display(0) == "ok"
    ld.write(config_text(540, 960, 240, adb=1))
    assert ld.check_display(0) == "fixed"
    assert ld.did("modify")[-1][-1] == "720,1280,320" and load(p)["advancedSettings.resolutionDpi"] == 320


def test_defaults_paths_and_shipped_config():
    assert ldconfig.expected_display({}) == (540, 960, 240)
    assert ldconfig.expected_display({"resolution": "720x1280", "dpi": 320}) == (720, 1280, 320)
    got = ldconfig.config_path({"ldconsole": os.path.join("D:", "LD", "ldconsole.exe")}, 3)
    assert got == os.path.join("D:", "LD", "vms", "config", "leidian3.config")
    assert ldconfig.config_path({"config_dir": "x"}, 0) == os.path.join("x", "leidian0.config")
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert ldconfig.expected_display(cfg["ldplayer"]) == (540, 960, 240) and cfg["ldplayer"]["fix_display"] is True
    assert (cfg["screen"]["width"], cfg["screen"]["height"]) == (540, 960)


def test_runner_reads_per_machine_settings(monkeypatch):
    class Store:
        def cfg_for(self, base, idx=None):
            return {"ldplayer": {**base["ldplayer"], "dpi": 320 if idx == 2 else 240}}

        def snapshot(self):
            return {}

        def runner(self, **kw):
            pass

    monkeypatch.setattr(runner, "Memory", lambda: None)
    monkeypatch.setattr(runner.ocr, "init", lambda *_: None)
    monkeypatch.setattr(runner, "instance_names", lambda ld: {})
    r = runner.Runner({"ldplayer": {"ldconsole": "x"}, "instances": []}, Store(), None)
    assert r.ld.cfg_for(2)["dpi"] == 320 and r.ld.cfg_for(0)["dpi"] == 240


# ---------- tat may nhe ----------
class Sequence(Fake):
    """list2 tra lan luot cac trang thai trong `seq` (giu trang thai cuoi)."""

    def __init__(self, folder, seq):
        super().__init__(folder)
        self.seq = list(seq)

    def run(self, *args, timeout=60):
        if args[0] == "list2":
            self.states[0] = self.seq.pop(0) if len(self.seq) > 1 else self.seq[0]
        if args[0] == "quit":
            self.calls.append(tuple(args))
            return ""
        return super().run(*args, timeout=timeout)


def test_quit_waits_until_process_has_exited(tmp_path):
    ld = Sequence(tmp_path, ["on", "busy", "busy", "off"])
    assert ld.quit(0) is True
    assert len(ld.did("quit")) == 1 and len(ld.did("list2")) == 4


def test_quit_retries_then_accepts_android_off(tmp_path, caplog):
    ld = Sequence(tmp_path, ["busy"])
    assert ld.quit(0, wait=6) is True
    assert len(ld.did("quit")) == 2 and "chua thoat" in caplog.text


@pytest.mark.parametrize("state", ["on", None])
def test_quit_reports_failure_without_killing(tmp_path, state):
    ld = Sequence(tmp_path, ["on"])
    if state is None:
        ld.run = lambda *a, **k: ld.calls.append(a) or ""       # list2 rong: khong duoc coi la da tat
    assert ld.quit(0, wait=6) is False
    assert {c[0] for c in ld.calls} <= {"quit", "list2"}
