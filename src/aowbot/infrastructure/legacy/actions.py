"""ActionRunner tren Ctx cua bot cu (B4/B7): moi hanh dong goi dung module da on dinh, khong viet lai thao tac UI."""
from __future__ import annotations

import logging
from typing import Any

from aowbot.application.execute import ActionResult, Status
from aowbot.domain.actions import ActionName
from bot.modules import gather, mainquest, observe, quests, research, train, upgrade

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
        if action is ActionName.LEGACY_TRAIN:
            return self._step(train.run, "bat dau huan luyen")
        if action is ActionName.LEGACY_RESEARCH:
            return self._step(research.run, "bat dau nghien cuu")
        return self._build()

    def _step(self, run: Any, what: str) -> ActionResult:
        n = run(self._ctx) or 0
        return ActionResult(Status.OK if n else Status.FAILED, f"{what}: {n}")

    def _observe(self) -> ActionResult:
        info = observe.run(self._ctx)       # ghi facts/timers/observations nhu luot cu -> World Model doc lai
        total = (info or {}).get("march_total")
        if total is None:
            return ActionResult(Status.UNVERIFIED, "khong doc duoc 'Hanh quan x/y'")
        return ActionResult(Status.OK, f"hanh quan {(info or {}).get('march_used')}/{total}")

    def _dispatch(self) -> ActionResult:
        # "Hanh quan x/y" chi co tren ban do the gioi: doc o thanh pho (observe ket thuc o do) -> None -> FAILED
        # -> quan sat lai -> thu lai = ra vao the gioi lien tuc (#1, 2026-11-21 17:08)
        self._ctx.ensure_world()
        before = self._ctx.read_marches()
        if before is None:
            # khung "Hanh quan x/y" CHI hien khi co doi dang di (observe.py) -> khung an tren ban do = 0 doi ra ngoai.
            # Biet tong tu lan quan sat truoc thi coi la (0, tong); sau khi gui van kiem 'after' = 1 de xac nhan.
            st = self._ctx.store.inst(self._ctx.dev.idx) if getattr(self._ctx, "store", None) else {}
            total = st.get("march_total")
            if not total:
                # idempotency: khong biet tong thi khong biet con cho trong khong -> khong gui mu
                return ActionResult(Status.FAILED, "khong doc duoc x/y truoc khi gui")
            before = (0, int(total))
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
        # Q2: nha chinh truoc (thieu dieu kien -> 'Nhay' sang cong trinh do), roi nhiem vu cho tho con lai
        started = (upgrade.run(self._ctx) or 0) + (mainquest.run(self._ctx) or 0) + (quests.run(self._ctx) or 0)
        return ActionResult(Status.OK if started else Status.FAILED, f"bat dau {started} nang cap")
