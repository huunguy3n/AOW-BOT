"""A-OPT-3: may treo -> screencap bao loi nhanh (timeout ngan, thu lai co gioi han),
danh dau dead de runner bo may."""
import subprocess

import numpy as np
import pytest

from bot import device
from bot.device import Device, ScreencapError


class FakeRun:
    """Gia lap subprocess.run cua adb: hang = moi lenh timeout; ghi lai timeout da dung."""

    def __init__(self, hang=True, ready=False):
        self.hang, self.ready = hang, ready
        self.calls = []

    def __call__(self, cmd, capture_output=True, timeout=None, **kw):
        self.calls.append((cmd, timeout))
        if "getprop" in cmd:
            out = b"1" if self.ready else b""
            return subprocess.CompletedProcess(cmd, 0, out, b"")
        if "connect" in cmd:
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        if self.hang:
            raise subprocess.TimeoutExpired(cmd, timeout)
        return subprocess.CompletedProcess(cmd, 0, b"", b"")


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(device.time, "sleep", lambda s: None)


def _dev(**sc):
    return Device("adb", 0).configure({"screencap": {"timeout_s": 8, "tries": 3, "reconnect_wait_s": 3, **sc}})


def test_hung_device_gives_up_after_two_timeouts_and_marks_dead(monkeypatch, no_sleep):
    fr = FakeRun(hang=True)
    monkeypatch.setattr(device.subprocess, "run", fr)
    d = _dev()
    with pytest.raises(ScreencapError, match="Khong chup duoc man hinh"):
        d.screencap()
    shots = [t for c, t in fr.calls if "screencap" in c]
    assert len(shots) == 2                       # 2 lan timeout -> dung, khong thu PNG sau raw timeout
    assert all(t == 8 for t in shots)            # timeout ngan (truoc day 20 s)
    assert d.dead
    n = len(fr.calls)
    with pytest.raises(ScreencapError):          # may da danh dau dead -> loi ngay, khong goi adb nua
        d.screencap()
    assert len(fr.calls) == n


def test_reconnect_success_then_shot(monkeypatch, no_sleep):
    d = _dev()
    seq = iter([None, None, None, np.zeros((960, 540, 3), np.uint8)])
    monkeypatch.setattr(Device, "_raw_shot", lambda self: next(seq))
    monkeypatch.setattr(Device, "_cmd", lambda self, *a, **k: b"")      # PNG rong
    monkeypatch.setattr(device.subprocess, "run", FakeRun(hang=False, ready=True))
    img = d.screencap()
    assert img is not None and not d.dead


def test_single_try_does_not_reconnect_or_mark_dead(monkeypatch, no_sleep):
    fr = FakeRun(hang=True)
    monkeypatch.setattr(device.subprocess, "run", fr)
    d = _dev()
    with pytest.raises(ScreencapError):
        d.screencap(tries=1)                    # _wait_game / cho man doi: 1 lan, khong do lai dia chi
    assert not d.dead
    assert not any("getprop" in c for c, _ in fr.calls)


def test_configure_defaults_when_missing():
    d = Device("adb", 0).configure({})
    assert d.shot_timeout == Device.shot_timeout and d.shot_tries == Device.shot_tries
