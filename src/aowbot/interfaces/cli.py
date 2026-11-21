"""CLI chi doc / dry-run (khong cham game):

  python -m aowbot world  <idx> [--db] [--config] [--settings] [--at 'YYYY-mm-dd HH:MM']   trang thai + do tuoi
  python -m aowbot plan   <idx> [...] [--log]       agent se lam gi bay gio, vi sao (--log: ghi bang decisions)
  python -m aowbot shadow <idx> [...] [--since 'YYYY-mm-dd HH:MM'] [--until ...]   phat lai so voi lich cu
"""
from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from dataclasses import dataclass

from aowbot.application.decide import Decision
from aowbot.application.shadow import ShadowReport
from aowbot.application.world_view import AccountState


@dataclass(frozen=True, slots=True)
class Command:
    name: str               # world | plan | shadow
    account: int
    db: str
    config: str
    settings: str
    at: float | None
    since: float | None = None
    until: float | None = None
    log: bool = False


def _t(s: str | None) -> float | None:
    return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M")) if s else None


def parse(argv: Sequence[str]) -> Command:
    ap = argparse.ArgumentParser(prog="python -m aowbot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, text in (("world", "trang thai tai khoan kem do tuoi tung du kien"),
                       ("plan", "quyet dinh dry-run cua agent kem giai thich"),
                       ("shadow", "phat lai lich su: agent so voi lich cu")):
        p = sub.add_parser(name, help=text)
        p.add_argument("account", type=int)
        p.add_argument("--db", default="data/memory.db")
        p.add_argument("--config", default="config.yaml")
        p.add_argument("--settings", default="data/settings.json")
        p.add_argument("--at", help="danh gia tai 'YYYY-mm-dd HH:MM' (gio may); mac dinh: bay gio")
        if name == "plan":
            p.add_argument("--log", action="store_true", help="ghi quyet dinh (dry_run=1) vao bang decisions")
        if name == "shadow":
            p.add_argument("--since")
            p.add_argument("--until")
    a = ap.parse_args(list(argv))
    return Command(a.cmd, a.account, a.db, a.config, a.settings, _t(a.at), _t(getattr(a, "since", None)),
                   _t(getattr(a, "until", None)), bool(getattr(a, "log", False)))


def _clock(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))


def render_state(state: AccountState) -> str:
    lines = [f"Tai khoan #{state.account} luc {_clock(state.at)}"]
    for key, lab in state.facts:
        if lab.fact is None:
            lines.append(f"  {key:<14} {lab.freshness.value:<9} -")
            continue
        age = (state.at - lab.fact.observed_at) / 60
        lines.append(f"  {key:<14} {lab.freshness.value:<9} {lab.fact.value!s:.60}  ({age:.0f} phut truoc, "
                     f"{lab.fact.source})")
    m = state.marches
    if m.availability is None:
        lines.append(f"  hanh quan      {m.freshness.value:<9} chua doc duoc 'Hanh quan x/y'")
    else:
        nxt = m.availability.next_return
        when = "-" if nxt is None else f"{_clock(nxt.at)}{' (uoc luong)' if nxt.estimated else ''}"
        lines.append(f"  hanh quan      {m.freshness.value:<9} ranh {m.availability.free}, doi ve som nhat {when}, "
                     f"doi khong ro gio uoc luong {m.unknown_return_s / 60:.0f} phut")
    return "\n".join(lines)


def render_decision(d: Decision) -> str:
    lines = [f"Quyet dinh #{d.account} luc {_clock(d.at)}: {d.action.value if d.action else 'khong lam gi'}",
             f"  vi sao: {d.why}",
             f"  ky vong: {d.expected_effect or '-'}; danh gia lai luc {_clock(d.next_eval_at)}",
             "  cac lua chon:"]
    for o in d.options:
        detail = (f"diem {o.score.total} (muc tieu {o.score.goal}, thoi gian {o.score.time}, rui ro {o.score.risk}, "
                  f"tin {o.score.confidence}) policy: {o.policy}") if o.score else f"khong kha thi: {o.blocker}"
        lines.append(f"    {o.action:<16} [{o.goal}: {o.goal_reason}] {detail}")
    return "\n".join(lines)


def render_shadow(r: ShadowReport) -> str:
    return "\n".join([
        f"Shadow #{r.account}: {r.observations} lan quan sat",
        f"  agent thuc day {r.agent_wakes} lan: {dict(r.agent_actions)}",
        f"  lich cu: {r.legacy_gather_visits} lan ghe co gather; co gui {r.legacy_useful}, gui 0 {r.legacy_useless}",
        f"  lan ghe co gui duoc agent phu (+- gather_retry_min): {r.legacy_useful_covered}/{r.legacy_useful}",
        "  (INFERRED: phat lai khong doi duoc qua khu; so lan thuc day la can tren)"])
