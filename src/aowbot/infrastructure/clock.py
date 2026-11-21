"""Dong ho he thong va dong ho co dinh (dry-run tai mot thoi diem / test)."""
from __future__ import annotations

import time
from dataclasses import dataclass


class SystemClock:
    def now(self) -> float:
        return time.time()


@dataclass(frozen=True, slots=True)
class FixedClock:
    at: float

    def now(self) -> float:
        return self.at
