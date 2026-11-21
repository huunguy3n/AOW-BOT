"""Composition root: dung doi tuong ha tang va noi vao use case."""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import yaml

from aowbot.app.config import load_agent_config
from aowbot.application.world_view import AccountState, build_account_state
from aowbot.infrastructure.clock import FixedClock, SystemClock
from aowbot.infrastructure.sqlite.legacy_memory_reader import LegacyMemoryReader
from aowbot.interfaces import cli


def read_config(path: str) -> Mapping[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: cau hinh phai la mapping")
    return data


def world_query(cfg: Mapping[str, Any], db: str, at: float | None) -> Callable[[int], AccountState]:
    if not os.path.exists(db):
        raise FileNotFoundError(db)
    settings = load_agent_config(cfg).world
    source = LegacyMemoryReader(db)
    clock = FixedClock(at) if at is not None else SystemClock()
    return lambda account: build_account_state(account, source, clock, settings)


def main(argv: Sequence[str]) -> int:
    cmd = cli.parse(argv)
    query = world_query(read_config(cmd.config), cmd.db, cmd.at)
    print(cli.render(query(cmd.account)))
    return 0
