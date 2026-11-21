"""B1: SqliteAgentStore (bang events/decisions) + TimerRegistry: chong trung, den han, khoi phuc sau khi chet."""
import json
import sqlite3

from aowbot.app.config import load_agent_config
from aowbot.application.decide import decide
from aowbot.application.scheduling import TimerRegistry
from aowbot.application.world_view import build_account_state
from aowbot.domain.events import Event, EventStatus, EventType
from aowbot.infrastructure.sqlite.agent_store import SqliteAgentStore
from bot.memory import Memory
from tests.fakes import FakeClock, InMemoryStateSource

NOW = 1_800_000_000.0


def ev(t, account=1):
    return Event(account, EventType.MARCH_RETURN_DUE, "march", t, "t")


def test_duplicate_events_scheduled_once(tmp_path):
    reg = TimerRegistry(SqliteAgentStore(tmp_path / "m.db"), FakeClock(NOW))
    assert reg.schedule([ev(NOW + 100), ev(NOW + 101), ev(NOW + 100)]) == 1
    assert reg.schedule([ev(NOW + 100)]) == 0


def test_due_order_claim_complete(tmp_path):
    store = SqliteAgentStore(tmp_path / "m.db")
    clock = FakeClock(NOW)
    reg = TimerRegistry(store, clock)
    reg.schedule([ev(NOW + 600), ev(NOW + 300), ev(NOW + 9000, account=2)])
    assert reg.due() == []
    clock.advance(700)
    due = reg.due()
    assert [e.due_at for e in due] == [NOW + 300, NOW + 600]
    reg.claim(due[0])
    assert reg.due() == [due[1]]
    reg.complete(due[0], ok=True)
    assert store.status(due[0].key) is EventStatus.DONE
    assert reg.next_for(2).due_at == NOW + 9000


def test_recover_stale_claims(tmp_path):
    store = SqliteAgentStore(tmp_path / "m.db")
    clock = FakeClock(NOW)
    reg = TimerRegistry(store, clock, claim_timeout_s=600)
    e = ev(NOW)
    reg.schedule([e])
    reg.claim(e)
    clock.advance(300)
    assert reg.recover() == []
    clock.advance(400)
    assert reg.recover() == [e]
    assert store.status(e.key) is EventStatus.PENDING


def test_agent_tables_coexist_with_legacy_schema(tmp_path):
    db = tmp_path / "m.db"
    Memory(str(db)).log_run(None, 0, "gather", NOW, 1, "ok", ret=1)
    SqliteAgentStore(db)
    c = sqlite3.connect(db)
    assert c.execute("SELECT COUNT(*) FROM runs").fetchone() == (1,)
    assert c.execute("PRAGMA user_version").fetchone() == (4,)          # khong doi phien ban schema cu
    Memory(str(db)).query("SELECT 1")                                    # bot cu van mo binh thuong


def test_decision_log(tmp_path):
    store = SqliteAgentStore(tmp_path / "m.db")
    cfg = load_agent_config({})
    state = build_account_state(1, InMemoryStateSource(), FakeClock(NOW), cfg.world)
    d = decide(Event(1, EventType.MANUAL, "t", NOW, "t"), state, cfg.decide)
    i = store.log_decision(d, dry_run=True)
    store.set_outcome(i, "khong lam gi")
    row = sqlite3.connect(tmp_path / "m.db").execute("SELECT dry_run, outcome, detail FROM decisions").fetchone()
    assert row[0] == 1 and row[1] == "khong lam gi" and json.loads(row[2])["account"] == 1
