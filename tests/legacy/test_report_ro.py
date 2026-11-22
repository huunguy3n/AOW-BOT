"""F4L + A-REL-2: bao cao chi doc va Memory(readonly=True) khong ghi vao DB."""
import os
import sqlite3

import pytest

from bot.memory import SCHEMA, Memory
from tools import report_ro


@pytest.fixture
def db(tmp_path):
    p = tmp_path / "m.db"
    c = sqlite3.connect(p)
    c.executescript(SCHEMA)
    c.execute("PRAGMA user_version=3")       # khac VERSION hien tai -> phat hien neu bi ghi de
    rows = [  # id, inst, started, ended, result, why, mode
        (1, 0, 1000, 1400, "ok", "mainquest: tho xay ranh (0/1); quests: tho xay ranh (0/1)", "smart"),
        (2, 0, 5000, 5300, "ok", "gather: 2 doi ranh", "smart"),
        (3, 1, 9000, 9100, "error", "cycle", "fixed"),
    ]
    c.executemany("INSERT INTO visits(id, inst, started, ended, result, why, mode) VALUES (?,?,?,?,?,?,?)", rows)
    runs = [  # visit, inst, step, started, dur, result, ret
        (1, 0, "mainquest", 1060, 30, "ok", "0"),
        (1, 0, "quests", 1100, 90, "ok", "0"),
        (1, 0, "observe", 1300, 20, "ok", None),
        (2, 0, "gather", 5080, 60, "ok", "2"),
    ]
    c.executemany("INSERT INTO runs(visit, inst, step, started, dur, result, ret) VALUES (?,?,?,?,?,?,?)", runs)
    c.commit()
    c.close()
    return p


def test_readonly_memory_does_not_touch_schema_or_data(db):
    before = (os.path.getmtime(db), os.path.getsize(db))
    m = Memory(str(db), readonly=True)
    assert m.query("SELECT COUNT(*) FROM visits") == [(3,)]
    m.log_run(None, 0, "x", 0, 1, "ok")                       # ghi that bai -> nuot + canh bao, khong crash
    assert m.query("SELECT COUNT(*) FROM runs") == [(4,)]
    assert m.query("PRAGMA user_version") == [(3,)]
    assert (os.path.getmtime(db), os.path.getsize(db)) == before


def test_default_memory_still_migrates(db):
    Memory(str(db)).query("SELECT 1")
    assert sqlite3.connect(db).execute("PRAGMA user_version").fetchone() == (4,)


def test_metrics(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    m = report_ro.metrics(lambda s, a=(): c.execute(s, a).fetchall())
    assert m["visits"] == 3
    assert m["vm_h"] == round((400 + 300 + 100) / 3600, 2)
    assert m["by_result"] == {"ok": 2, "error": 1}
    assert m["start_med_s"] == 70.0                           # (60 + 80) / 2
    assert m["useless_visits"] == 1                           # lan ghe 1: mainquest + quests deu tra 0
    assert m["reasons"] == {"mainquest: tho xay ranh (#/#)": 1, "quests: tho xay ranh (#/#)": 1,
                            "gather: # doi ranh": 1}
    assert m["steps"]["quests"] == {"n": 1, "min": 1.5, "zero": 1, "zero_min": 1.5}
    assert m["steps"]["observe"]["zero"] == 0
    assert m["steps"]["gather"]["zero"] == 0


def test_metrics_window_and_instance_filter(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    q = lambda s, a=(): c.execute(s, a).fetchall()  # noqa: E731
    assert report_ro.metrics(q, 4000, None)["visits"] == 2
    assert report_ro.metrics(q, None, 4000)["visits"] == 1
    assert report_ro.metrics(q, insts=[1])["visits"] == 1


@pytest.mark.parametrize("why, expected", [
    ("mainquest: a; quests: b", {"mainquest", "quests"}),
    ("tran an toan 240 phut khong ghe", set()),
    (None, set()),
])
def test_trigger_steps(why, expected):
    assert report_ro.trigger_steps(why) == expected


def test_reason_key_strips_times_and_numbers():
    assert report_ro.reason_key(" gather: doi ve 11:31 ") == "gather: doi ve HH:MM"


def test_intel_metrics_from_logs(tmp_path):
    """P5-1: % 'unknown' tinh bao tu log; loc may chi lay dong [#N]."""
    (tmp_path / "bot-20261122.log").write_text(
        "2026-11-22 00:09:25 INFO [#3] Tinh bao: unknown\n"
        "2026-11-22 00:09:54 INFO [#3] Tinh bao: 0 nhiem vu\n"
        "2026-11-22 01:00:00 INFO [MainThread] Tinh bao: picked\n"
        "2026-11-22 02:00:00 INFO [#1] Tinh bao: win\n", encoding="utf-8")
    m = report_ro.intel_metrics(0, 1e12, log_dir=str(tmp_path))
    assert (m["_unknown"], m["_total"], m["_pct"]) == (1, 3, 33.3)
    assert report_ro.intel_metrics(0, 1e12, [1], log_dir=str(tmp_path)) == {"win": 1, "_unknown": 0, "_total": 1,
                                                                            "_pct": 0.0}
    assert report_ro.intel_metrics(0, 1e12, log_dir=str(tmp_path / "khong_co")) == {}


def test_combat_metrics():
    steps = {"rebels": {"n": 4, "zero": 2, "min": 3.0}, "gather": {"n": 1, "zero": 0, "min": 1.0}}
    assert report_ro.combat_metrics(steps) == {"rebels": {"n": 4, "ok": 2, "ok_pct": 50.0, "min": 3.0}}
