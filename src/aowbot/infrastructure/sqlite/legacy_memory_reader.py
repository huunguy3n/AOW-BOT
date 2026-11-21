"""AccountStateSource tren data/memory.db cua bot cu - CHI DOC (mode=ro), khong chay schema/PRAGMA."""
from __future__ import annotations

import json
import pathlib
import sqlite3
from collections.abc import Sequence
from typing import Any

from aowbot.application.ports import ObservationRecord, VisitRecord
from aowbot.domain.freshness import Fact
from aowbot.domain.marches import MarchObservation

# do tin cua du kien chep tu bot cu (khong ghi kem do tin): OCR da qua kiem tra hop ly cua module
LEGACY_CONFIDENCE = 0.8


class LegacyMemoryReader:
    def __init__(self, path: str | pathlib.Path) -> None:
        uri = pathlib.Path(path).resolve().as_uri() + "?mode=ro"
        self._c = sqlite3.connect(uri, uri=True, timeout=10)

    def close(self) -> None:
        self._c.close()

    def _rows(self, sql: str, args: tuple[Any, ...]) -> list[tuple[Any, ...]]:
        return self._c.execute(sql, args).fetchall()

    def fact(self, account: int, key: str) -> Fact[Any] | None:
        if key == "resources":
            return self._resources(account)
        r = self._rows("SELECT value, seen_at FROM facts WHERE inst=? AND key=?", (account, key))
        if not r or r[0][1] is None:
            return None
        value = json.loads(r[0][0]) if r[0][0] is not None else None
        return Fact(value, f"memory.facts:{key}", float(r[0][1]), LEGACY_CONFIDENCE)

    def _resources(self, account: int) -> Fact[Any] | None:
        # tai nguyen lay tu observations (moc thoi gian that cua lan doc), khong tu facts
        r = self._rows("SELECT at, resources FROM observations WHERE inst=? AND resources IS NOT NULL "
                       "ORDER BY at DESC LIMIT 1", (account,))
        if not r:
            return None
        return Fact(json.loads(r[0][1]), "memory.observations:resources", float(r[0][0]), LEGACY_CONFIDENCE)

    def marches(self, account: int) -> MarchObservation | None:
        total = self.fact(account, "march_total")
        if total is None or total.value is None:
            return None
        used = self.fact(account, "march_used")
        seen = self.fact(account, "observed_at")
        timers = [(float(d), float(c if c is not None else 0.0))
                  for d, c in self._rows("SELECT due_at, conf FROM timers WHERE inst=? AND key LIKE 'march:%'",
                                         (account,))]
        return MarchObservation(int(total.value), None if used is None else used.value,
                                None if seen is None or seen.value is None else float(seen.value), timers)

    def return_gaps(self, account: int, look: int = 60) -> Sequence[float]:
        gaps: list[float] = []
        for at, raw in self._rows("SELECT at, marches FROM observations WHERE inst=? AND marches IS NOT NULL "
                                  "ORDER BY at DESC LIMIT ?", (account, look)):
            try:
                rows = json.loads(raw or "[]")
            except ValueError:
                continue
            gaps += [m["return_at"] - at for m in rows if isinstance(m, dict) and m.get("return_at")]
        return gaps

    # ---------- HistorySource (B6s) ----------
    def observations(self, account: int, since: float, until: float) -> list[ObservationRecord]:
        out = []
        for at, used, total, raw in self._rows(
                "SELECT at, march_used, march_total, marches FROM observations WHERE inst=? AND at>=? AND at<? "
                "ORDER BY at", (account, since, until)):
            try:
                rows = json.loads(raw or "[]")
            except ValueError:
                rows = []
            out.append(ObservationRecord(float(at), used, total, [r for r in rows if isinstance(r, dict)]))
        return out

    def visits(self, account: int, since: float, until: float) -> list[VisitRecord]:
        out = []
        for vid, started, why in self._rows("SELECT id, started, why FROM visits WHERE inst=? AND started>=? "
                                            "AND started<? ORDER BY started", (account, since, until)):
            r = self._rows("SELECT ret FROM runs WHERE visit=? AND step='gather'", (vid,))
            sent = None
            if r:
                try:
                    sent = int(float(r[0][0])) if r[0][0] not in (None, "", "null") else 0
                except (TypeError, ValueError):
                    sent = 0
            out.append(VisitRecord(float(started), why or "", sent))
        return out
