"""B7 (executor: 1 hanh dong / lan, xac minh, quan sat lai, khong thu vo han), B9 (dieu phoi theo su kien),
khoa tai khoan giua tien trinh, adapter gui quan cua bot cu, SCH-X (runner/scheduler)."""
import dataclasses

import pytest

from aowbot.app.config import load_agent_config
from aowbot.application.coordinator import AgentCoordinator
from aowbot.application.execute import ActionResult, SessionDeps, Status, run_session
from aowbot.application.scheduling import TimerRegistry
from aowbot.application.world_view import build_account_state
from aowbot.domain.actions import ActionName
from aowbot.domain.events import Event, EventStatus, EventType
from aowbot.domain.freshness import Fact
from aowbot.domain.marches import MarchObservation, MarchTimer
from aowbot.infrastructure.legacy import actions as legacy_actions
from aowbot.infrastructure.locks import AccountLock
from aowbot.infrastructure.sqlite.agent_store import SqliteAgentStore
from bot import scheduler
from bot.memory import Memory
from bot.runner import Runner
from tests.fakes import FakeClock, InMemoryStateSource

NOW = 1_800_000_000.0
CFG = load_agent_config({})
EV = Event(1, EventType.MARCH_RETURN_DUE, "march", NOW, "t")


class FakeLog:
    def __init__(self):
        self.rows = []

    def log_decision(self, d, dry_run, outcome=None):
        self.rows.append([d, dry_run, outcome])
        return len(self.rows) - 1

    def set_outcome(self, i, outcome):
        self.rows[i][2] = outcome


class Game:
    """The gioi gia: x/y hanh quan; dispatch tang x; observe ghi lai vao nguon trang thai."""

    def __init__(self, used, total=5, dispatch_ok=True):
        self.used, self.total, self.dispatch_ok = used, total, dispatch_ok
        self.src = InMemoryStateSource()
        self.calls = []
        self._write()

    def _write(self):
        for k, v in (("hq_level", 30), ("march_total", self.total), ("world_open", True), ("builders_busy", 2)):
            self.src.facts[(1, k)] = Fact(v, "t", NOW)
        self.src.march_obs[1] = MarchObservation(self.total, self.used, NOW, [(NOW + 3600, 0.9)] * self.used)

    def run(self, action):
        self.calls.append(action)
        if action is ActionName.OBSERVE_MARCHES:
            self._write()
            return ActionResult(Status.OK, "x/y")
        if action is ActionName.DISPATCH_GATHER and self.dispatch_ok:
            self.used += 1
            return ActionResult(Status.OK, "gui 1")
        return ActionResult(Status.FAILED, "khong gui duoc")

    def deps(self, log):
        return SessionDeps(lambda: build_account_state(1, self.src, FakeClock(NOW), CFG.world), self, log, CFG.decide)


def test_session_fills_free_marches_then_stops():
    g, log = Game(used=3), FakeLog()
    r = run_session(EV, g.deps(log))
    assert g.used == 5
    assert g.calls == [ActionName.DISPATCH_GATHER, ActionName.OBSERVE_MARCHES] * 2
    assert r.stopped == "het viec" and r.decisions[-1].action is None
    assert all(row[2] for row in log.rows) and not any(row[1] for row in log.rows)   # moi quyet dinh co ket qua


def test_failing_action_is_not_retried_forever():
    g = Game(used=0, dispatch_ok=False)
    r = run_session(EV, dataclasses.replace(g.deps(FakeLog()), max_actions=20))
    assert g.calls.count(ActionName.DISPATCH_GATHER) == 3            # max_retries 2 -> 3 lan roi Policy chan
    assert r.stopped == "het viec"


def test_session_bounded_by_max_actions():
    g = Game(used=0, total=50)
    r = run_session(EV, dataclasses.replace(g.deps(FakeLog()), max_actions=2))
    assert r.stopped.startswith("het tran") and g.calls.count(ActionName.DISPATCH_GATHER) == 2


# ---------------------------------------------------------------- coordinator
class Timers:
    def __init__(self, timers=()):
        self.timers = list(timers)

    def march_timers(self, account):
        return self.timers if account == 1 else []


def test_coordinator_bootstrap_sync_and_finish(tmp_path):
    clock = FakeClock(NOW)
    store = SqliteAgentStore(tmp_path / "m.db")
    timers = Timers()
    c = AgentCoordinator(TimerRegistry(store, clock), timers, clock)
    first = c.due_event(1)
    assert first.type is EventType.OBSERVE_DUE                     # chua co gi -> quan sat ngay
    c.begin(first)
    g = Game(used=5)
    result = run_session(first, g.deps(FakeLog()))
    c.finish(first, result)
    assert store.status(first.key) is EventStatus.DONE
    assert c.due_event(1) is None                                   # khong thuc day khi chua toi han
    assert c.next_at(1) == result.next_eval_at
    timers.timers = [MarchTimer(0, "march", NOW + 600, "ocr", 0.9)]
    clock.advance(700)
    due = c.due_event(1)
    assert due.type is EventType.MARCH_RETURN_DUE


def test_bootstrap_even_when_only_timer_events_exist(tmp_path):
    clock = FakeClock(NOW)
    c = AgentCoordinator(TimerRegistry(SqliteAgentStore(tmp_path / "m.db"), clock),
                         Timers([MarchTimer(0, "march", NOW + 9000, "ocr", 0.9)]), clock)
    e = c.due_event(1)
    assert e is not None and e.type is EventType.OBSERVE_DUE   # doi khong ro gio: khong cho toi timer xa
    assert c.due_event(2) is not None and c.due_event(2).account == 2


# ---------------------------------------------------------------- khoa
def test_account_lock_is_exclusive(tmp_path):
    a, b = AccountLock(str(tmp_path), 1), AccountLock(str(tmp_path), 1)
    assert a.acquire()
    assert not b.acquire()
    a.release()
    assert b.acquire()
    b.release()
    with AccountLock(str(tmp_path), 2) as got:
        assert got


# ---------------------------------------------------------------- adapter gui quan cua bot cu
class Ctx:
    def __init__(self, reads):
        self.reads = list(reads)

    def read_marches(self):
        return self.reads.pop(0)

    def ensure_world(self):
        pass


@pytest.mark.parametrize("reads, sent, status", [
    ([(2, 5), (3, 5)], 1, Status.OK),
    ([None], 0, Status.FAILED),                 # khong biet x/y -> khong gui mu (idempotency)
    ([(5, 5)], 0, Status.OK),                   # da day -> khong gui
    ([(2, 5), (2, 5)], 1, Status.UNVERIFIED),
    ([(2, 5), (2, 5)], 0, Status.FAILED),
])
def test_legacy_dispatch_verifies_counter(monkeypatch, reads, sent, status):
    calls = []
    monkeypatch.setattr(legacy_actions.gather, "run", lambda ctx, limit=None: calls.append(limit) or sent)
    r = legacy_actions.LegacyActionRunner(Ctx(reads)).run(ActionName.DISPATCH_GATHER)
    assert r.status is status
    assert calls in ([], [1])


# ---------------------------------------------------------------- SCH-X
def test_scheduler_leaves_gather_to_agent(tmp_path):
    mem = Memory(str(tmp_path / "m.db"))
    order = ["mainquest", "gather"]
    enabled = {"mainquest": True, "gather": True}
    legacy = scheduler.decide_one(mem, 1, order, enabled, {"schedule": {"mode": "smart"}}, NOW)
    agent = scheduler.decide_one(mem, 1, order, enabled, {"schedule": {"mode": "agent"}}, NOW)
    assert "gather" in legacy.steps and "gather" not in agent.steps


def test_runner_spawns_agent_visit_for_due_event():
    class Agent:
        def due_event(self, idx):
            return EV if idx == 1 else None

    class Store:
        def inst(self, idx):
            return {"enabled": True}

        def runner(self, **kw):
            pass
    r = Runner.__new__(Runner)
    r.base_cfg, r.store, r.agent, r._busy = {"instances": [0, 1]}, Store(), Agent(), {}
    spawned = []
    r._spawn = lambda idx, **kw: spawned.append((idx, kw))
    assert r._spawn_agent()
    assert spawned == [(1, {"modules": set(), "why": "agent march_return_due", "mode": "agent", "agent_event": EV})]
