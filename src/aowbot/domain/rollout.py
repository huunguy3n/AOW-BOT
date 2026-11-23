"""P6: mo agent sang farm co kiem soat + gioi han so may chay cung luc. Ham thuan tren dict cau hinh DA GOP
(config.yaml <- settings.json global <- instance), dung chung cho runner / lich / web / AgentHooks (bot/ va web/
duoc import aowbot.domain - luat D7).

Agent chi chay tren 1 may khi CA HAI:
  - cong tac chung `agent.enabled` = true (mac dinh false; chu du an bat tren web, muc "Agent"), va
  - may do chon che do Agent (`schedule.mode` = 'agent', dat theo may tren web).
Cong tac chung tat -> may chon Agent chay theo lich chung (smart) nhu may thuong, KHONG bi bo bat ky buoc nao
(ke ca gather). Tat cong tac = dung khan cap agent tren moi may ma khong phai sua tung may."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

AGENT_MODE = "agent"
HARD_MAX_RUNNING = 2      # CLAUDE.md quy tac 4: toi da 2 instance cung luc - cau hinh lon hon cung bi cat ve 2


def agent_switch(cfg: Mapping[str, Any]) -> bool:
    """Cong tac chung. Chi True khi ghi ro `true` (chuoi 'true' / 1 tu file tay khong tinh - dong khi loi)."""
    return (cfg.get("agent") or {}).get("enabled") is True


def agent_requested(cfg: Mapping[str, Any]) -> bool:
    """May nay da chon che do Agent tren web (co the van bi chan boi cong tac chung)."""
    return (cfg.get("schedule") or {}).get("mode") == AGENT_MODE


def agent_active(cfg: Mapping[str, Any]) -> bool:
    return agent_switch(cfg) and agent_requested(cfg)


def agent_status(cfg: Mapping[str, Any]) -> str:
    """'on' (agent dang lo may nay) | 'blocked' (chon Agent nhung cong tac chung tat -> chay lich chung) | 'off'."""
    if not agent_requested(cfg):
        return "off"
    return "on" if agent_switch(cfg) else "blocked"


def max_running(configured: Any) -> int:
    """ldplayer.max_running hieu luc: 1..HARD_MAX_RUNNING (gia tri hong / <1 -> 1, > 2 -> 2)."""
    try:
        n = int(configured)
    except (TypeError, ValueError):
        n = 1
    return max(1, min(n, HARD_MAX_RUNNING))


def parallel_slots(parallel: Any, configured_max: Any) -> int:
    """So luong xu ly may cung luc = schedule.parallel, khong vuot max_running hieu luc."""
    try:
        p = int(parallel)
    except (TypeError, ValueError):
        p = 1
    return max(1, min(p, max_running(configured_max)))


def peak_concurrency(intervals: Iterable[tuple[float, float]]) -> tuple[int, float | None]:
    """[(bat, tat)] -> (so may chay cung luc lon nhat, thoi diem dau tien dat dinh). Tat truoc bat khi trung gio."""
    edges = sorted([(s, 1) for s, e in intervals if e > s] + [(e, -1) for s, e in intervals if e > s],
                   key=lambda x: (x[0], x[1]))
    cur, peak, at = 0, 0, None
    for t, d in edges:
        cur += d
        if cur > peak:
            peak, at = cur, t
    return peak, at


def time_over(intervals: Iterable[tuple[float, float]], limit: int) -> float:
    """Tong so giay co > limit may chay cung luc."""
    edges = sorted([(s, 1) for s, e in intervals if e > s] + [(e, -1) for s, e in intervals if e > s],
                   key=lambda x: (x[0], x[1]))
    cur, last, over = 0, None, 0.0
    for t, d in edges:
        if cur > limit and last is not None:
            over += t - last
        cur += d
        last = t
    return over
