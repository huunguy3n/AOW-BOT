"""A-MEAS-1: bo dem hieu nang + bang perf + bao cao; A-INV-1: anh dieu tra 1 lan / ngay."""
import sqlite3
import threading

import numpy as np
import pytest

from bot import perf
from bot.build import inv_capture
from bot.device import Device
from bot.memory import Memory
from tools import report_ro


def test_drain_aggregates_and_resets():
    p = perf.Perf()
    for dt in (0.1, 0.2, 0.3, 0.4):
        p.add("adb_tap", dt)
    p.add("screencap", 0.5, "human")
    rows = {(k, s): r for k, s, *r in p.drain()}
    assert rows[("adb_tap", "bot")] == [4, 1.0, 0.3, 0.4, 0.4]
    assert rows[("screencap", "human")][0] == 1
    assert p.drain() == []


def test_src_is_per_thread():
    p = perf.Perf()
    seen = []

    def other():
        p.add("x", 1)
        seen.append(True)
    with perf.as_src("human"):
        p.add("x", 1)
        t = threading.Thread(target=other)
        t.start()
        t.join()
    assert sorted((k, s, n) for k, s, n, *_ in p.drain()) == [("x", "bot", 1), ("x", "human", 1)]
    assert seen


def test_measure_is_noop_without_binding():
    perf.bind(None)
    with perf.measure("ocr"):
        pass                     # khong loi, khong ghi


def test_measure_records_in_bound_thread():
    p = perf.Perf()
    perf.bind(p)
    try:
        with perf.measure("ocr"):
            pass
    finally:
        perf.bind(None)
    assert [r[:3] for r in p.drain()] == [("ocr", "bot", 1)]


@pytest.mark.parametrize("args, kind", [
    (("shell", "input", "tap", 1, 2), "tap"),
    (("shell", "input", "swipe", 1, 2, 3, 4, 300), "swipe"),
    (("shell", "input", "keyevent", "4"), "key"),
    (("exec-out", "screencap", "-p"), "screencap_png"),
    (("exec-out", "screencap"), "screencap_raw"),
    (("shell", "pidof", "pkg"), "pidof"),
])
def test_adb_command_kind(args, kind):
    assert Device._kind(args) == kind


def test_screencap_failure_is_counted(monkeypatch):
    d = Device("adb", 0)
    d.perf = perf.Perf()
    monkeypatch.setattr(d, "_screencap", lambda tries: (_ for _ in ()).throw(RuntimeError("Khong chup duoc man hinh")))
    with pytest.raises(RuntimeError, match="Khong chup duoc man hinh"):
        d.screencap(tries=1)
    assert [r[0] for r in d.perf.drain()] == ["screencap_fail"]


def test_log_perf_and_report(tmp_path):
    db = tmp_path / "m.db"
    m = Memory(str(db))
    v = m.visit_start(1)
    p = perf.Perf()
    p.add("adb_tap", 1.0)
    p.add("screencap", 0.4)
    p.add("ocr", 0.13)
    m.log_perf(v, 1, "gather", p.drain())
    m.visit_end(v, "ok")
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    r = report_ro.metrics(lambda s, a=(): c.execute(s, a).fetchall())
    assert r["perf"]["steps"]["gather"] == {"adb": 1, "screencap": 1, "ocr": 1, "identify": 0, "adb_s": 1.0}
    assert r["perf"]["kinds"]["adb_tap/bot"]["n"] == 1


def test_report_without_perf_table(tmp_path):
    db = tmp_path / "old.db"
    sqlite3.connect(db).execute("CREATE TABLE visits(id, inst, started, ended, result, why, mode)").connection.commit()
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE runs(visit, inst, step, started, dur, ret)")
    c.commit()
    r = report_ro.metrics(lambda s, a=(): c.execute(s, a).fetchall())
    assert r["perf"] == {}


def test_inv_capture_once_per_day(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class Dev:
        idx = 3
        shots = 0

        def screencap(self, tries=1):
            Dev.shots += 1
            return np.zeros((10, 10, 3), np.uint8)

    class Ctx:
        dev = Dev()
    assert inv_capture(Ctx(), "quests_tab_2_main_row1")
    assert inv_capture(Ctx(), "quests_tab_2_main_row1") is None
    assert Dev.shots == 1
