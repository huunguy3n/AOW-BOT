"""B6s: phat lai lich su quan sat cua 1 tai khoan, so cac lan agent se thuc day/quyet dinh voi lan ghe that
cua lich cu (dry-run, khong cham game). Ket qua la so do INFERRED: agent khong thay doi duoc qua khu."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from aowbot.application.decide import DecideSettings, decide
from aowbot.application.ports import HistorySource, ObservationRecord
from aowbot.application.world_view import AccountState, Labeled, MarchView
from aowbot.domain.events import DEDUP_BUCKET_S, Event, EventType, events_from_timers
from aowbot.domain.freshness import Fact, Freshness, freshness
from aowbot.domain.marches import MarchObservation, availability, lower_quartile, timers_from_rows


@dataclass(frozen=True, slots=True)
class Window:
    since: float
    until: float

    def __contains__(self, t: float) -> bool:
        return self.since <= t < self.until


@dataclass(frozen=True, slots=True)
class ShadowSettings:
    decide: DecideSettings
    ttl_march_s: float          # du lieu x/y cu hon -> STALE (agent quan sat lai thay vi gui mu)
    default_unknown_s: float    # gio ve uoc luong khi chua du lich su
    window_s: float             # lan ghe cu 'duoc phu' neu agent thuc day trong +- window_s (gather_retry_min)


@dataclass(frozen=True, slots=True)
class ShadowReport:
    account: int
    observations: int
    agent_wakes: int
    agent_actions: Mapping[str, int]
    legacy_gather_visits: int
    legacy_useful: int
    legacy_useless: int
    legacy_useful_covered: int      # lan ghe co gui quan cua lich cu ma agent cung thuc day trong +- window_s


@dataclass(frozen=True, slots=True)
class _Ctx:
    account: int
    hq: int | None
    ttl_s: float
    unknown_s: float


def _lab(value: object, seen: float, at: float) -> Labeled:
    f = Fact(value, "replay", seen)
    return Labeled(f, freshness(f, at, 10 ** 9))


def _state(c: _Ctx, at: float, o: ObservationRecord) -> AccountState:
    timers = [(t.due_at, t.confidence) for t in timers_from_rows(o.rows) if t.kind == "march"]
    avail = availability(MarchObservation(o.total, o.used, o.at, timers), at, c.unknown_s) if o.total else None
    view = MarchView(avail, freshness(Fact(o.used, "replay", o.at), at, c.ttl_s), c.unknown_s)
    facts = (("hq_level", _lab(c.hq, at, at)), ("builders_busy", Labeled(None, Freshness.UNKNOWN)),
             ("resources", Labeled(None, Freshness.UNKNOWN)), ("march_total", _lab(o.total, o.at, at)),
             ("march_used", _lab(o.used, o.at, at)), ("world_open", _lab(True, at, at)))
    return AccountState(c.account, at, facts, view)


def replay(account: int, src: HistorySource, window: Window, s: ShadowSettings) -> ShadowReport:
    obs = src.observations(account, window.since, window.until)
    hq_f = src.fact(account, "hq_level")
    gaps = [float(m["return_at"]) - o.at for o in obs for m in o.rows if m.get("return_at")]
    c = _Ctx(account, hq_f.value if hq_f is not None and isinstance(hq_f.value, int) else None,
             s.ttl_march_s, lower_quartile(gaps, s.default_unknown_s))
    wakes: dict[int, float] = {}
    for o in obs:
        evs = events_from_timers(account, [t for t in timers_from_rows(o.rows) if t.kind == "march"], "replay")
        d = decide(Event(account, EventType.MANUAL, "replay", o.at, "replay"), _state(c, o.at, o), s.decide)
        for t in [e.due_at for e in evs] + [d.next_eval_at]:
            if t in window:
                wakes.setdefault(int(t // DEDUP_BUCKET_S), t)
    actions: dict[str, int] = {}
    times = sorted(wakes.values())
    for t in times:
        latest = [o for o in obs if o.at <= t]
        if not latest:
            continue
        d = decide(Event(account, EventType.MARCH_RETURN_DUE, "march", t, "replay"), _state(c, t, latest[-1]),
                   s.decide)
        k = d.action.value if d.action else "none"
        actions[k] = actions.get(k, 0) + 1
    vis = [v for v in src.visits(account, window.since, window.until) if v.gather_sent is not None]
    useful = [v for v in vis if (v.gather_sent or 0) > 0]
    covered = sum(any(abs(t - v.started) <= s.window_s for t in times) for v in useful)
    return ShadowReport(account, len(obs), len(times), actions, len(vis), len(useful), len(vis) - len(useful),
                        covered)
