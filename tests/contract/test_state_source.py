"""Hop dong AccountStateSource: LegacyMemoryReader (memory.db that, chi doc) va InMemoryStateSource (gia) phai
cho cung ket qua tren cung du lieu."""
import json
import os

import pytest

from aowbot.domain.freshness import Fact
from aowbot.domain.marches import MarchObservation
from aowbot.infrastructure.sqlite.legacy_memory_reader import LEGACY_CONFIDENCE, LegacyMemoryReader
from bot.memory import Memory
from tests.fakes import InMemoryStateSource

NOW = 1_800_000_000.0


def legacy(tmp_path):
    db = str(tmp_path / "m.db")
    m = Memory(db)
    for key, v in (("hq_level", 30), ("march_total", 5), ("march_used", 5), ("observed_at", NOW - 60)):
        m.set_fact(1, key, v)
        m._exec("UPDATE facts SET seen_at=? WHERE inst=1 AND key=?", (NOW - 60, key))
    m.set_timer(1, "march:0", NOW + 7200, conf=0.6)
    m.set_timer(1, "build:0", NOW + 100, conf=0.7)              # khong phai hanh quan -> bo qua
    m._exec("INSERT INTO observations(inst, at, resources, marches) VALUES (1, ?, ?, ?)",
            (NOW - 60, json.dumps({"metal": 5}), json.dumps([{"state": "gathering", "return_at": NOW + 1140}])))
    before = os.path.getmtime(db)
    return LegacyMemoryReader(db), db, before


def fake():
    s = InMemoryStateSource()
    s.facts[(1, "hq_level")] = Fact(30, "memory.facts:hq_level", NOW - 60, LEGACY_CONFIDENCE)
    s.facts[(1, "resources")] = Fact({"metal": 5}, "memory.observations:resources", NOW - 60, LEGACY_CONFIDENCE)
    s.march_obs[1] = MarchObservation(5, 5, NOW - 60, [(NOW + 7200, 0.6)])
    s.gaps[1] = [1200.0]
    return s


@pytest.fixture(params=["legacy", "fake"])
def src(request, tmp_path):
    if request.param == "fake":
        yield fake()
        return
    reader, db, before = legacy(tmp_path)
    yield reader
    reader.close()
    assert os.path.getmtime(db) == before                     # chi doc


def test_fact(src):
    f = src.fact(1, "hq_level")
    assert (f.value, f.observed_at, f.confidence) == (30, NOW - 60, LEGACY_CONFIDENCE)
    assert src.fact(1, "khong_co") is None
    assert src.fact(2, "hq_level") is None


def test_resources_from_observation(src):
    assert src.fact(1, "resources").value == {"metal": 5}


def test_marches(src):
    assert src.marches(1) == MarchObservation(5, 5, NOW - 60, [(NOW + 7200, 0.6)])
    assert src.marches(2) is None


def test_return_gaps(src):
    assert list(src.return_gaps(1)) == [1200.0]
