"""Composition root: dung doi tuong ha tang va noi vao use case."""
from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

import yaml

from aowbot.app.config import AgentConfig, load_agent_config
from aowbot.application.decide import decide
from aowbot.application.shadow import ShadowSettings, Window, replay
from aowbot.application.world_view import build_account_state
from aowbot.domain.events import Event, EventType
from aowbot.infrastructure.clock import FixedClock, SystemClock
from aowbot.infrastructure.legacy.settings import instance_config
from aowbot.infrastructure.sqlite.agent_store import SqliteAgentStore
from aowbot.infrastructure.sqlite.legacy_memory_reader import LegacyMemoryReader
from aowbot.interfaces import cli


def read_config(path: str) -> Mapping[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: cau hinh phai la mapping")
    return data


def agent_config(cmd: cli.Command) -> AgentConfig:
    return load_agent_config(instance_config(read_config(cmd.config), cmd.account, cmd.settings))


def main(argv: Sequence[str]) -> int:
    cmd = cli.parse(argv)
    if not os.path.exists(cmd.db):
        raise FileNotFoundError(cmd.db)
    cfg = agent_config(cmd)
    source = LegacyMemoryReader(cmd.db)
    clock = FixedClock(cmd.at) if cmd.at is not None else SystemClock()
    try:
        if cmd.name == "world":
            print(cli.render_state(build_account_state(cmd.account, source, clock, cfg.world)))
        elif cmd.name == "plan":
            state = build_account_state(cmd.account, source, clock, cfg.world)
            d = decide(Event(cmd.account, EventType.MANUAL, "cli", state.at, "cli"), state, cfg.decide)
            if cmd.log:
                SqliteAgentStore(cmd.db).log_decision(d, dry_run=True)
            print(cli.render_decision(d))
        else:
            now = clock.now()
            window = Window(cmd.since or 0.0, cmd.until or now)
            settings = ShadowSettings(cfg.decide, cfg.world.ttl.ttl("march_used"), cfg.world.unknown_return_s,
                                      cfg.gather_retry_s)
            print(cli.render_shadow(replay(cmd.account, source, window, settings)))
    finally:
        source.close()
    return 0
