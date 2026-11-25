"""P13-13: screencap hong -> do lai dia chi -> thu DUNG 1 lan voi timeout gap doi; van hong -> dead (khong lap)."""
import os

import pytest

from bot.device import Device, ScreencapError


def _dev(results):
    d = Device.__new__(Device)
    d.dead, d.idx, d.serial, d.perf = False, 1, "emulator-5556", None
    d.shot_tries, d.shot_timeout, d.reconnect_wait = 3, 5.0, 1.0
    d.calls, d.timeouts = 0, []

    def _sc(tries):
        d.calls += 1
        d.timeouts.append(d.shot_timeout)
        r = results.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    d._screencap = _sc
    d.wait_ready = lambda s: True
    return d


def test_second_attempt_succeeds_with_longer_timeout():
    d = _dev([ScreencapError("timeout"), "IMG"])
    assert d.screencap() == "IMG"
    assert d.calls == 2 and d.timeouts == [5.0, 10.0] and d.shot_timeout == 5.0 and not d.dead


def test_still_failing_marks_dead_after_exactly_two_attempts():
    d = _dev([ScreencapError("t1"), ScreencapError("t2"), "NEVER"])
    with pytest.raises(ScreencapError):
        d.screencap()
    assert d.calls == 2 and d.dead and d.shot_timeout == 5.0
    with pytest.raises(ScreencapError):
        d.screencap()                                   # da dead: nem ngay, khong thu them
    assert d.calls == 2


def test_exchange_template_referenced():
    assert os.path.exists("templates/hero/btn_exchange.png")
    with open("bot/modules/notify.py", encoding="utf-8") as f:
        assert "hero/btn_exchange" in f.read()
