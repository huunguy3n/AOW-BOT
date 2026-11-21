"""B2b: world_view gan nhan do tuoi; cau hinh khoi agent."""
import pytest

from aowbot.app.config import load_agent_config
from aowbot.application.world_view import build_account_state
from aowbot.domain.freshness import Fact, Freshness
from aowbot.domain.marches import MarchObservation
from tests.fakes import FakeClock, InMemoryStateSource

NOW = 1_800_000_000.0
SETTINGS = load_agent_config({}).world


def source():
    s = InMemoryStateSource()
    s.facts[(1, "hq_level")] = Fact(30, "ocr", NOW - 3600)
    s.facts[(1, "builders_busy")] = Fact(2, "ocr", NOW - 3600)
    s.march_obs[1] = MarchObservation(5, 5, NOW - 600, [(NOW + 7200, 0.6)])
    return s


def test_labels_follow_ttl():
    st = build_account_state(1, source(), FakeClock(NOW), SETTINGS)
    assert st.get("hq_level").freshness is Freshness.OBSERVED        # TTL nha chinh 6 h
    assert st.get("builders_busy").freshness is Freshness.STALE      # TTL mac dinh 30 phut
    assert st.get("resources").freshness is Freshness.UNKNOWN
    assert st.marches.freshness is Freshness.OBSERVED
    assert st.marches.availability.free == 0


def test_march_view_goes_stale_but_still_estimates():
    clock = FakeClock(NOW)
    clock.advance(3 * 3600)
    st = build_account_state(1, source(), clock, SETTINGS)
    assert st.marches.freshness is Freshness.STALE
    assert st.marches.availability.free == 5                     # moi uoc luong da qua


def test_unknown_account():
    st = build_account_state(9, InMemoryStateSource(), FakeClock(NOW), SETTINGS)
    assert st.marches.availability is None and st.marches.freshness is Freshness.UNKNOWN


def test_deterministic():
    a = build_account_state(1, source(), FakeClock(NOW), SETTINGS)
    b = build_account_state(1, source(), FakeClock(NOW), SETTINGS)
    assert a == b


def test_config_overrides_and_validation():
    cfg = load_agent_config({"agent": {"ttl_min": {"default": 5, "hq_level": 60}},
                             "schedule": {"unknown_return_min": 30}})
    assert cfg.world.ttl.ttl("hq_level") == 3600 and cfg.world.ttl.ttl("x") == 300
    assert cfg.world.unknown_return_s == 1800
    with pytest.raises(ValueError, match="khoa khong hop le"):
        load_agent_config({"agent": {"ttl": {}}})
    with pytest.raises(ValueError):
        load_agent_config({"agent": {"ttl_min": {"default": 0}}})
