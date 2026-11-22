"""B-UI: /api/agent doc bang decisions/events (chi doc); trang /agent phuc vu duoc."""
from aowbot.app.config import load_agent_config
from aowbot.application.decide import decide
from aowbot.application.world_view import build_account_state
from aowbot.domain.events import Event, EventType
from aowbot.infrastructure.sqlite.agent_store import SqliteAgentStore
from bot.memory import Memory
from bot.runner import RingLog
from tests.fakes import FakeClock, InMemoryStateSource
from web.server import create_app

NOW = 1_800_000_000.0


class Store:
    def snapshot(self):
        return {"instances": {}, "runner": {}}

    def cfg_for(self, base, idx=None):
        return {**base, "schedule": {"mode": "agent" if idx == 1 else "smart"}}


class Runner:
    def __init__(self, mem):
        self.mem, self.base_cfg, self.running, self.queue = mem, {"instances": [0, 1]}, False, []


def test_agent_api_and_page(tmp_path):
    db = tmp_path / "m.db"
    mem = Memory(str(db))
    app = create_app(Runner(mem), Store(), RingLog())
    c = app.test_client()
    empty = c.get("/api/agent").get_json()
    assert empty["decisions"] == [] and empty["modes"] == {"0": "smart", "1": "agent"}
    store = SqliteAgentStore(db)
    cfg = load_agent_config({})
    d = decide(Event(1, EventType.MANUAL, "t", NOW, "t"),
               build_account_state(1, InMemoryStateSource(), FakeClock(NOW), cfg.world), cfg.decide)
    store.log_decision(d, dry_run=True)
    store.add(Event(1, EventType.OBSERVE_DUE, "agent", NOW + 60, "agent"), NOW)
    got = c.get("/api/agent").get_json()
    assert got["decisions"][0]["account"] == 1 and got["decisions"][0]["options"]
    assert got["events"][0]["type"] == "observe_due"
    r = c.get("/agent")  # trang cu da gop vao tab #hoc cua trang chinh
    assert r.status_code == 302 and r.headers["Location"].endswith("/#hoc")
