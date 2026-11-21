"""B2b: `python -m aowbot world` tren DB tam - chay that qua tien trinh con, ket qua lap lai duoc."""
import os
import subprocess
import sys

from bot.memory import Memory

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(*args):
    return subprocess.run([sys.executable, "-m", "aowbot", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False,
                          env={**os.environ, "PYTHONIOENCODING": "utf-8",
                               "PYTHONPATH": os.path.join(ROOT, "src") + os.pathsep + ROOT})


def test_world_cli_is_read_only_and_deterministic(tmp_path):
    db = tmp_path / "m.db"
    m = Memory(str(db))
    for k, v in (("hq_level", 5), ("march_total", 1), ("march_used", 0)):
        m.set_fact(0, k, v)
    before = os.path.getmtime(db)
    a = run("world", "0", "--db", str(db), "--at", "2026-11-21 12:00")
    b = run("world", "0", "--db", str(db), "--at", "2026-11-21 12:00")
    assert a.returncode == 0, a.stderr
    assert a.stdout == b.stdout
    assert "hq_level" in a.stdout and "hanh quan" in a.stdout
    assert os.path.getmtime(db) == before


def test_world_cli_missing_db(tmp_path):
    r = run("world", "0", "--db", str(tmp_path / "none.db"))
    assert r.returncode != 0
