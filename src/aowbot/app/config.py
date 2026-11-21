"""Schema khoi `agent:` trong config.yaml (doc tu dict da parse; khoa la -> loi ro rang)."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from aowbot.application.decide import DecideSettings
from aowbot.application.planning import PlanSettings
from aowbot.application.scoring import Weights
from aowbot.application.world_view import WorldSettings
from aowbot.domain.freshness import FreshnessPolicy
from aowbot.domain.policy import SafetyPolicy

DEFAULT_TTL_MIN = MappingProxyType({"default": 30.0, "hq_level": 360.0, "march_used": 20.0,
                                    "march_total": 1440.0, "world_open": 360.0})
AGENT_KEYS = frozenset({"ttl_min", "weights", "idle_recheck_min", "min_state_confidence"})


@dataclass(frozen=True, slots=True)
class AgentConfig:
    world: WorldSettings
    decide: DecideSettings
    gather_retry_s: float


def load_agent_config(cfg: Mapping[str, Any]) -> AgentConfig:
    """cfg = cau hinh DA GOP cho 1 may (config.yaml <- settings.json global <- instance)."""
    agent = dict(cfg.get("agent") or {})
    unknown = set(agent) - AGENT_KEYS
    if unknown:
        raise ValueError(f"agent: khoa khong hop le {sorted(unknown)} (hop le: {sorted(AGENT_KEYS)})")
    ttl_min = {**DEFAULT_TTL_MIN, **{str(k): float(v) for k, v in (agent.get("ttl_min") or {}).items()}}
    default = ttl_min.pop("default")
    policy = FreshnessPolicy(default * 60, tuple((k, v * 60) for k, v in sorted(ttl_min.items())))
    sched = cfg.get("schedule") or {}
    # cung gia tri voi lich cu (schedule.unknown_return_min / gather_retry_min) - mot cau hinh, hai noi dung
    world = WorldSettings(policy, float(sched.get("unknown_return_min", 60)) * 60)
    plan = PlanSettings(int((cfg.get("gather") or {}).get("min_hq_level", 9)),
                        int((cfg.get("build") or {}).get("max_builders", 1)))
    decide = DecideSettings(plan, Weights(**{str(k): float(v) for k, v in (agent.get("weights") or {}).items()}),
                            SafetyPolicy(min_state_confidence=float(agent.get("min_state_confidence", 0.5))),
                            float(agent.get("idle_recheck_min", 60)) * 60)
    return AgentConfig(world, decide, float(sched.get("gather_retry_min", 60)) * 60)
