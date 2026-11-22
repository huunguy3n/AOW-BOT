"""Composition root: dung doi tuong ha tang va noi vao use case."""
from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

import yaml

from aowbot.app.config import AgentConfig, load_agent_config
from aowbot.application.decide import decide
from aowbot.application.shadow import RiskRules, ShadowSettings, Window, live_summary, replay, shadow_risks
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


def _shadow(cmd: cli.Command, source: LegacyMemoryReader, now: float) -> str:
    """Phat lai 1 may hoac moi may (shadow all, P6-Q4): chi doc memory.db, khong ghi, khong cham game."""
    window = Window(cmd.since or 0.0, cmd.until or now)
    base = read_config(cmd.config)
    accounts = [int(i) for i in base.get("instances") or []] if cmd.all_accounts else [cmd.account]
    out = []
    for acc in accounts:
        mcfg = instance_config(base, acc, cmd.settings)
        cfg = load_agent_config(mcfg)
        settings = ShadowSettings(cfg.decide, cfg.world.ttl.ttl("march_used"), cfg.world.unknown_return_s,
                                  cfg.gather_retry_s)
        r = replay(acc, source, window, settings)
        rows = source.decisions(acc, window.since, window.until)
        hq = source.fact(acc, "hq_level")
        rules = RiskRules(min_hq_gather=int((mcfg.get("gather") or {}).get("min_hq_level", 9)))
        out.append(cli.render_shadow(r, live_summary(rows),
                                     shadow_risks(r, rows, hq.value if hq and isinstance(hq.value, int) else None,
                                                  rules)))
    return "\n".join(out)


def main(argv: Sequence[str]) -> int:
    cmd = cli.parse(argv)
    if not os.path.exists(cmd.db):
        raise FileNotFoundError(cmd.db)
    source = LegacyMemoryReader(cmd.db)
    clock = FixedClock(cmd.at) if cmd.at is not None else SystemClock()
    try:
        if cmd.name == "shadow":
            print(_shadow(cmd, source, clock.now()))
            return 0
        cfg = agent_config(cmd)
        if cmd.name == "world":
            print(cli.render_state(build_account_state(cmd.account, source, clock, cfg.world)))
        elif cmd.name == "plan":
            state = build_account_state(cmd.account, source, clock, cfg.world)
            d = decide(Event(cmd.account, EventType.MANUAL, "cli", state.at, "cli"), state, cfg.decide)
            if cmd.log:
                SqliteAgentStore(cmd.db).log_decision(d, dry_run=True)
            print(cli.render_decision(d))
    finally:
        source.close()
    return 0
