"""CLI: `python -m aowbot world <idx> [--db PATH] [--config PATH] [--at 'YYYY-mm-dd HH:MM']` (chi doc)."""
from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from dataclasses import dataclass

from aowbot.application.world_view import AccountState


@dataclass(frozen=True, slots=True)
class WorldCommand:
    account: int
    db: str
    config: str
    at: float | None


def parse(argv: Sequence[str]) -> WorldCommand:
    ap = argparse.ArgumentParser(prog="python -m aowbot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("world", help="trang thai tai khoan kem do tuoi tung du kien (chi doc)")
    w.add_argument("account", type=int)
    w.add_argument("--db", default="data/memory.db")
    w.add_argument("--config", default="config.yaml")
    w.add_argument("--at", help="danh gia tai thoi diem 'YYYY-mm-dd HH:MM' (gio may); mac dinh: bay gio")
    a = ap.parse_args(list(argv))
    at = time.mktime(time.strptime(a.at, "%Y-%m-%d %H:%M")) if a.at else None
    return WorldCommand(a.account, a.db, a.config, at)


def _clock(t: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t))


def render(state: AccountState) -> str:
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
