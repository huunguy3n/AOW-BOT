"""ActionRunner tren Ctx cua bot cu (B4/B7): moi hanh dong goi dung module da on dinh, khong viet lai thao tac UI."""
from __future__ import annotations

import logging
from typing import Any

from aowbot.application.execute import ActionResult, Status
from aowbot.domain.actions import ActionName
from bot.modules import gather, mainquest, observe, quests

log = logging.getLogger("aow")


class LegacyActionRunner:
    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx

    def run(self, action: ActionName) -> ActionResult:
        log.info("Agent: %s", action.value)
        if action is ActionName.OBSERVE_MARCHES:
            return self._observe()
        if action is ActionName.DISPATCH_GATHER:
            return self._dispatch()
        return self._build()

    def _observe(self) -> ActionResult:
        info = observe.run(self._ctx)       # ghi facts/timers/observations nhu luot cu -> World Model doc lai
        total = (info or {}).get("march_total")
        if total is None:
            return ActionResult(Status.UNVERIFIED, "khong doc duoc 'Hanh quan x/y'")
        return ActionResult(Status.OK, f"hanh quan {(info or {}).get('march_used')}/{total}")

    def _dispatch(self) -> ActionResult:
        before = self._ctx.read_marches()
        if before is None:
            # idempotency: khong biet x/y thi khong biet doi truoc da di chua -> khong gui mu
            return ActionResult(Status.FAILED, "khong doc duoc x/y truoc khi gui")
        if before[0] >= before[1]:
            return ActionResult(Status.OK, f"hanh quan da day {before[0]}/{before[1]} - khong gui")
        sent = gather.run(self._ctx, limit=1)
        self._ctx.ensure_world()
        after = self._ctx.read_marches()
        if sent and after and after[0] == before[0] + 1:
            return ActionResult(Status.OK, f"gui 1 doi: {before[0]} -> {after[0]}/{after[1]}")
        if sent:
            return ActionResult(Status.UNVERIFIED, f"gather bao gui {sent}, x/y {before} -> {after}")
        return ActionResult(Status.FAILED, "khong gui duoc doi nao (khong co mo hop le / het linh)")

    def _build(self) -> ActionResult:
        started = (mainquest.run(self._ctx) or 0) + (quests.run(self._ctx) or 0)
        return ActionResult(Status.OK if started else Status.FAILED, f"bat dau {started} nang cap")
