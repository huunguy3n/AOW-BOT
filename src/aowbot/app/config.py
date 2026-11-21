"""Schema khoi `agent:` trong config.yaml (doc tu dict da parse; khoa la -> loi ro rang)."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from aowbot.application.world_view import WorldSettings
from aowbot.domain.freshness import FreshnessPolicy

DEFAULT_TTL_MIN = MappingProxyType({"default": 30.0, "hq_level": 360.0, "march_used": 20.0,
                                    "march_total": 1440.0, "world_open": 360.0})
AGENT_KEYS = frozenset({"ttl_min"})


@dataclass(frozen=True, slots=True)
class AgentConfig:
    world: WorldSettings


def load_agent_config(cfg: Mapping[str, Any]) -> AgentConfig:
    agent = dict(cfg.get("agent") or {})
    unknown = set(agent) - AGENT_KEYS
    if unknown:
        raise ValueError(f"agent: khoa khong hop le {sorted(unknown)} (hop le: {sorted(AGENT_KEYS)})")
    ttl_min = {**DEFAULT_TTL_MIN, **{str(k): float(v) for k, v in (agent.get("ttl_min") or {}).items()}}
    default = ttl_min.pop("default")
    policy = FreshnessPolicy(default * 60, tuple((k, v * 60) for k, v in sorted(ttl_min.items())))
    # cung gia tri voi lich cu (schedule.unknown_return_min) - mot cau hinh, hai noi dung
    unknown_return_s = float((cfg.get("schedule") or {}).get("unknown_return_min", 60)) * 60
    return AgentConfig(WorldSettings(policy, unknown_return_s))
