"""Cau noi PerceptionResult -> World Model: AccountStateSource boc ngoai nguon cu, them khoa 'perception:<lop>'.

Quy tac (khong coi thieu bang chung la vang mat):
- CONFIRMED  -> Fact(True,  confidence = p hop nhat)
- NOT_DETECTED -> Fact(False, confidence = 1 - p cua ung vien tot nhat)
- UNCERTAIN / UNKNOWN / khung hong / chua co ket qua -> None  (World Model hieu la 'chua biet', freshness UNKNOWN)
Khoa khac duoc chuyen nguyen cho nguon ben trong. KHONG ghi gi vao memory.db.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from aowbot.application.ports import AccountStateSource
from aowbot.domain.freshness import Fact
from aowbot.domain.marches import MarchObservation
from aowbot.perception.contract import PerceptionResult, Status

PREFIX = "perception:"
SOURCE = "perception"


class PerceptionFactSource:
    def __init__(self, inner: AccountStateSource, latest: Callable[[int], PerceptionResult | None]) -> None:
        self._inner = inner
        self._latest = latest

    def fact(self, account: int, key: str) -> Fact[Any] | None:
        if not key.startswith(PREFIX):
            return self._inner.fact(account, key)
        r = self._latest(account)
        if r is None or not r.frame_valid:
            return None
        cls = key[len(PREFIX):]
        o = next((o for o in r.outcomes if o.cls == cls), None)
        if o is None:
            return None
        if o.status is Status.CONFIRMED:
            return Fact(True, SOURCE, r.timestamp, o.p if o.p is not None else 1.0)
        if o.status is Status.NOT_DETECTED and o.p is not None:
            return Fact(False, SOURCE, r.timestamp, 1.0 - o.p)
        return None

    def marches(self, account: int) -> MarchObservation | None:
        return self._inner.marches(account)

    def return_gaps(self, account: int) -> Sequence[float]:
        return self._inner.return_gaps(account)
