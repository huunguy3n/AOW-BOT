"""B6s: phat lai lich su quan sat cua 1 tai khoan, so cac lan agent se thuc day/quyet dinh voi lan ghe that
cua lich cu (dry-run, khong cham game). Ket qua la so do INFERRED: agent khong thay doi duoc qua khu."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
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
    legacy_visits: int = 0          # P6-Q4: moi lan ghe cua lich cu trong khoang (moi che do)
    agent_dispatch_alone: int = 0   # lan agent quyet dinh gui quan ma lich cu KHONG ghe trong +- window_s
    span_days: float = 0.0          # do dai khoang du lieu (quan sat dau -> cuoi), de quy ra /ngay


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
    dispatch_at: list[float] = []
    for t in times:
        latest = [o for o in obs if o.at <= t]
        if not latest:
            continue
        d = decide(Event(account, EventType.MARCH_RETURN_DUE, "march", t, "replay"), _state(c, t, latest[-1]),
                   s.decide)
        k = d.action.value if d.action else "none"
        actions[k] = actions.get(k, 0) + 1
        if k == "dispatch_gather":
            dispatch_at.append(t)
    every = src.visits(account, window.since, window.until)
    vis = [v for v in every if v.gather_sent is not None]
    useful = [v for v in vis if (v.gather_sent or 0) > 0]
    covered = sum(any(abs(t - v.started) <= s.window_s for t in times) for v in useful)
    alone = sum(not any(abs(t - v.started) <= s.window_s for v in every) for t in dispatch_at)
    span = (obs[-1].at - obs[0].at) / 86400 if len(obs) > 1 else 0.0
    return ShadowReport(account, len(obs), len(times), actions, len(vis), len(useful), len(vis) - len(useful),
                        covered, len(every), alone, round(span, 2))


# ---------- P6-Q4: ket qua phien agent THAT da ghi (bang decisions, dry_run=0) + rui ro ----------
def outcome_class(outcome: str | None) -> str:
    """Chuoi outcome trong bang decisions -> 'ok' | 'failed' | 'none' (khong lam gi) | 'open' (chua ghi ket qua)."""
    if outcome is None:
        return "open"
    o = outcome.strip().lower()
    if o.startswith("ok"):
        return "ok"
    if o.startswith("failed"):
        return "failed"
    return "none"


def live_summary(rows: Sequence[tuple[str | None, str | None]]) -> dict[str, dict[str, int]]:
    """[(action, outcome)] -> {action|'none': {'ok','failed','none','open': n}}."""
    out: dict[str, dict[str, int]] = {}
    for action, outcome in rows:
        c = out.setdefault(action or "none", {"ok": 0, "failed": 0, "none": 0, "open": 0})
        c[outcome_class(outcome)] += 1
    return out


def top_failures(rows: Sequence[tuple[str | None, str | None]], n: int = 2) -> dict[str, list[tuple[str, int]]]:
    """{action: [(ly do that bai, so lan)]} - ly do da bo so de gom (vd 'gui 1 doi: 2 -> 3/5')."""
    cnt: dict[str, dict[str, int]] = {}
    for action, outcome in rows:
        if outcome_class(outcome) == "failed":
            key = re.sub(r"\d+", "#", str(outcome))
            d = cnt.setdefault(action or "none", {})
            d[key] = d.get(key, 0) + 1
    return {a: sorted(d.items(), key=lambda kv: -kv[1])[:n] for a, d in cnt.items()}


@dataclass(frozen=True, slots=True)
class RiskRules:
    min_hq_gather: int = 9          # gather.min_hq_level
    wake_ratio: float = 2.0         # agent thuc day > ratio x lan ghe lich cu / ngay -> canh bao gio may
    fail_pct: float = 20.0          # phien that: % that bai cua 1 hanh dong > nguong -> canh bao
    fail_min: int = 3               # ... va it nhat N lan


def shadow_risks(r: ShadowReport, live_rows: Sequence[tuple[str | None, str | None]], hq: int | None,
                 rules: RiskRules = RiskRules()) -> list[str]:
    """Khac biet agent / lich cu dang chu y (ham thuan; doc tren ShadowReport + bang decisions)."""
    out: list[str] = []
    if r.observations == 0:
        return ["khong co lan quan sat nao trong khoang - shadow khong co gia tri cho may nay"]
    miss = r.legacy_useful - r.legacy_useful_covered
    if miss > 0 and hq is not None and hq < rules.min_hq_gather:
        out.append(f"khac biet theo luat (khong phai loi): {miss}/{r.legacy_useful} lan lich cu gui quan khi "
                   f"chua co luat nha chinh >= {rules.min_hq_gather}; nay nha chinh {hq} nen agent khong gui")
    elif miss > 0:
        out.append(f"bo sot: {miss}/{r.legacy_useful} lan lich cu gui duoc quan ma agent khong thuc day gan do "
                   "(co the gui quan cham hon)")
    if r.agent_dispatch_alone > 0:
        out.append(f"them lan ghe: {r.agent_dispatch_alone} lan agent gui quan khi lich cu khong ghe "
                   "(ton them gio may, can tren)")
    days = max(r.span_days, 1 / 24)
    if r.legacy_visits and r.agent_wakes / days > rules.wake_ratio * r.legacy_visits / days:
        out.append(f"thuc day nhieu: {r.agent_wakes / days:.0f} lan/ngay so voi lich cu "
                   f"{r.legacy_visits / days:.0f} lan/ngay (can tren, gop theo su kien)")
    if hq is not None and hq < rules.min_hq_gather and r.agent_actions.get("dispatch_gather", 0):
        out.append(f"sai luat: agent de xuat gui quan khi nha chinh {hq} < {rules.min_hq_gather}")
    fails = top_failures(live_rows)
    for action, c in live_summary(live_rows).items():
        tried = c["ok"] + c["failed"]
        if tried and c["failed"] >= rules.fail_min and 100.0 * c["failed"] / tried > rules.fail_pct:
            why = ", ".join(f"{k} x{n}" for k, n in fails.get(action, []))
            out.append(f"phien that: {action} that bai {c['failed']}/{tried} ({why})")
    return out
