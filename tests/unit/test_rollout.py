"""P6: cong tac chung agent + tran 2 may (ham thuan aowbot.domain.rollout)."""
import pytest

from aowbot.domain import rollout as R


def cfg(switch=None, mode=None):
    c = {}
    if switch is not None:
        c["agent"] = {"enabled": switch}
    if mode is not None:
        c["schedule"] = {"mode": mode}
    return c


@pytest.mark.parametrize("switch, mode, status", [
    (None, None, "off"), (None, "agent", "blocked"), (False, "agent", "blocked"), (True, "agent", "on"),
    (True, "smart", "off"), (True, None, "off"), ("true", "agent", "blocked"), (1, "agent", "blocked"),
])
def test_agent_needs_switch_and_machine_mode(switch, mode, status):
    c = cfg(switch, mode)
    assert R.agent_status(c) == status
    assert R.agent_active(c) is (status == "on")


def test_default_config_is_off():
    assert not R.agent_switch({})
    assert not R.agent_switch({"agent": None})


@pytest.mark.parametrize("v, want", [(2, 2), (1, 1), (3, 2), (99, 2), (0, 1), (-5, 1), (None, 1), ("x", 1),
                                     ("2", 2)])
def test_max_running_hard_cap(v, want):
    assert R.max_running(v) == want


@pytest.mark.parametrize("par, mx, want", [(2, 2, 2), (5, 5, 2), (1, 2, 1), (2, 1, 1), (None, 2, 1), (3, None, 1)])
def test_parallel_slots(par, mx, want):
    assert R.parallel_slots(par, mx) == want


def test_peak_concurrency():
    assert R.peak_concurrency([]) == (0, None)
    assert R.peak_concurrency([(0, 10), (5, 15)]) == (2, 5)
    assert R.peak_concurrency([(0, 10), (10, 20)]) == (1, 0)      # tat dung luc may kia bat: khong chong
    assert R.peak_concurrency([(0, 10), (2, 8), (4, 6)]) == (3, 4)
    assert R.peak_concurrency([(5, 5), (7, 3)]) == (0, None)        # khoang hong bi bo


def test_time_over_limit():
    assert R.time_over([(0, 10), (2, 8), (4, 6)], 2) == 2.0
    assert R.time_over([(0, 10), (5, 15)], 2) == 0.0
