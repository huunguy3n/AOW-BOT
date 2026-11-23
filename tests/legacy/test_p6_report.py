"""P6-3: report_ro tong hop 24h - ti le buoc khong loi, kim cuong theo nguon, so may cung luc, ket luan tieu chi."""
import json
import sqlite3
from types import SimpleNamespace

import pytest

from bot.memory import SCHEMA, Memory
from bot.modules import defense
from tools import report_ro as R


@pytest.fixture
def q(tmp_path):
    p = tmp_path / "m.db"
    c = sqlite3.connect(p)
    c.executescript(SCHEMA)
    c.executemany("INSERT INTO visits(id, inst, started, ended, result, why, mode) VALUES (?,?,?,?,?,?,?)", [
        (1, 0, 1000, 2000, "ok", "", "smart"),
        (2, 1, 1500, 2500, "ok", "", "smart"),
        (3, 2, 1800, 1900, "ok", "", "smart"),        # 3 may cung luc 1800-1900 -> vi pham
    ])
    runs = [(1, 0, "gather", 1010, 5, "ok", "1")] * 18 + [(1, 0, "gather", 1100, 5, "err", None),
                                                           (2, 1, "train", 1600, 5, "stuck", None),
                                                           (2, 1, "train", 1700, 5, "warn", "0"),
                                                           (2, 1, "train", 1750, 5, "miss", "0")]
    c.executemany("INSERT INTO runs(visit, inst, step, started, dur, result, ret) VALUES (?,?,?,?,?,?,?)", runs)
    c.executemany("INSERT INTO gem_ev(inst, at, src, n) VALUES (?,?,?,?)",
                  [(0, 1200, "shield", 500), (0, 1300, "shield_war", 3600), (1, 1600, "mystery", 10)])
    obs = [(0, 1100, {"gems": 9000}), (0, 1400, {"gems": 4900}), (0, 1500, {"gems": 5000}),
           (1, 1550, {"gems": 800}), (1, 1650, {"gems": 100}), (1, 1700, None)]
    c.executemany("INSERT INTO observations(inst, at, resources) VALUES (?,?,?)",
                  [(i, t, json.dumps(r) if r else None) for i, t, r in obs])
    c.commit()
    return lambda s, a=(): c.execute(s, a).fetchall()


def test_step_health_counts_err_and_stuck_only(q):
    h = R.step_health(q, "started>=? AND started<?", [0, 1e12])
    assert h["n"] == 22 and h["fail"] == 2 and h["ok_pct"] == round(100 * 20 / 22, 1)
    assert h["worst"][0][0] == "train"


def test_gem_ledger_by_source_and_unexplained(q):
    g = R.gem_metrics(q, "at>=? AND at<?", [0, 1e12])
    assert g["by_src"] == {"shield": 500, "shield_war": 3600, "mystery": 10}
    assert g["outside_shield"] == 10
    assert g["drops"] == {0: 4100, 1: 700}
    assert g["unexplained"] == {1: 690}           # may 0: 4100 = 500 + 3600 da ghi so


def test_gem_drops_ignores_unread_and_increases():
    assert R.gem_drops([(0, 1, 100), (0, 2, None), (0, 3, 150), (0, 4, 120)]) == {0: 30}
    assert R.gem_drops([]) == {}


def test_concurrency_detects_three_machines(q):
    c = R.concurrency_metrics(q, "started>=? AND started<?", [0, 1e12])
    assert c["peak"] == 3 and c["peak_at"] == 1800 and c["over_limit_s"] == 100.0


def test_full_metrics_verdict(q, capsys):
    m = R.metrics(q)
    v = m["p6"]["verdict"]
    assert v == {"buoc_khong_loi": False, "kim_cuong_ngoai_khien": False, "toi_da_2_may": False}
    R.show("x", m)
    out = capsys.readouterr().out
    assert "KHONG DAT" in out and "CAN XEM" in out


def test_verdict_pass_on_clean_db(tmp_path):
    p = tmp_path / "m.db"
    c = sqlite3.connect(p)
    c.executescript(SCHEMA)
    c.execute("INSERT INTO visits(id, inst, started, ended, result) VALUES (1, 0, 10, 20, 'ok')")
    c.execute("INSERT INTO runs(visit, inst, step, started, dur, result) VALUES (1, 0, 'gather', 11, 1, 'ok')")
    c.commit()
    m = R.metrics(lambda s, a=(): c.execute(s, a).fetchall())
    assert all(m["p6"]["verdict"].values())


def test_memory_log_gem(tmp_path):
    m = Memory(str(tmp_path / "m.db"))
    m.log_gem(3, "shield_war", 4800, "khien 12h")
    assert m.query("SELECT inst, src, n, note FROM gem_ev") == [(3, "shield_war", 4800, "khien 12h")]


def test_defense_add_spent_writes_ledger(tmp_path):
    class St:
        def __init__(self):
            self.d = {}

        def inst(self, idx):
            return self.d

        def update(self, idx, **kw):
            self.d.update(kw)
    mem = Memory(str(tmp_path / "m.db"))
    ctx = SimpleNamespace(dev=SimpleNamespace(idx=4), mem=mem, store=St())
    defense._add_spent(ctx, 500, "shield")
    assert mem.query("SELECT inst, src, n FROM gem_ev") == [(4, "shield", 500)]
    assert defense.spent_today(ctx.store.d["gems_spent"]) == 500
