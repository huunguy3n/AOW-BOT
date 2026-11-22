"""B6s: phat lai lich su tren DB tam."""
import json

from aowbot.app.composition import main
from aowbot.app.config import load_agent_config
from aowbot.application.shadow import ShadowSettings, Window, replay
from aowbot.infrastructure.sqlite.agent_store import SqliteAgentStore
from aowbot.infrastructure.sqlite.legacy_memory_reader import LegacyMemoryReader
from bot.memory import Memory

NOW = 1_800_000_000.0
H = 3600


def test_replay_counts_wakes_and_legacy_visits(tmp_path):
    db = str(tmp_path / "m.db")
    m = Memory(db)
    m.set_fact(1, "hq_level", 30)
    m._exec("INSERT INTO observations(inst, at, march_used, march_total, marches) VALUES (1, ?, 5, 5, ?)",
            (NOW, json.dumps([{"state": "gathering", "return_at": NOW + H}])))
    m._exec("INSERT INTO observations(inst, at, march_used, march_total, marches) VALUES (1, ?, 1, 5, ?)",
            (NOW + 2 * H, json.dumps([{"state": "returning", "return_at": NOW + 2 * H + 600}])))
    v1 = m.visit_start(1)
    m._exec("UPDATE visits SET started=? WHERE id=?", (NOW + H + 60, v1))
    m.log_run(v1, 1, "gather", NOW + H + 100, 60, "ok", ret=2)
    v2 = m.visit_start(1)
    m._exec("UPDATE visits SET started=? WHERE id=?", (NOW + 1800, v2))
    m.log_run(v2, 1, "gather", NOW + 1900, 10, "ok", ret=0)
    cfg = load_agent_config({})
    s = ShadowSettings(cfg.decide, 20 * 60, H, 10 * 60)
    r = replay(1, LegacyMemoryReader(db), Window(NOW - 1, NOW + 5 * H), s)
    assert r.observations == 2
    assert r.legacy_gather_visits == 2 and r.legacy_useful == 1 and r.legacy_useless == 1
    assert r.legacy_useful_covered == 1              # agent thuc day luc doi ve NOW + H
    assert r.agent_wakes >= 2 and sum(r.agent_actions.values()) == r.agent_wakes


def test_shadow_all_reads_decisions_and_reports_risks(tmp_path, capsys):
    """P6-Q4: 'shadow all' chi doc memory.db, in moi may trong config + phien that + rui ro."""
    db = str(tmp_path / "m.db")
    m = Memory(db)
    m.set_fact(1, "hq_level", 30)
    m._exec("INSERT INTO observations(inst, at, march_used, march_total, marches) VALUES (1, ?, 1, 5, '[]')", (NOW,))
    SqliteAgentStore(db)       # tao bang decisions nhu agent that
    for out in ["failed: khong doc duoc x/y truoc khi gui"] * 3 + ["ok: gui 1 doi: 0 -> 1/5"]:
        m._exec("INSERT INTO decisions(at, account, action, dry_run, outcome) VALUES (?, 1, 'dispatch_gather', 0, ?)",
                (NOW, out))
    cfg = tmp_path / "c.yaml"
    cfg.write_text("instances: [1, 2]\n", encoding="utf-8")
    before = (tmp_path / "m.db").stat().st_mtime
    assert main(["shadow", "all", "--db", db, "--config", str(cfg), "--settings", str(tmp_path / "none.json"),
                 "--at", "2030-01-01 00:00"]) == 0
    text = capsys.readouterr().out
    assert "Shadow #1" in text and "Shadow #2" in text
    assert "dispatch_gather ok 1 / loi 3" in text and "RUI RO: phien that: dispatch_gather that bai 3/4" in text
    assert (tmp_path / "m.db").stat().st_mtime == before      # khong ghi
