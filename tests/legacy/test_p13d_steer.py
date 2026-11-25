"""P13d-2: runner - nhan vong tim + bang +5%, phat hien keo khong hieu luc, luong anh dung hinh."""
import os

import cv2
import pytest

from bot import steer, stream

IMG = "data/owner-feedback/p13/runner_khong_dieu_khien.png"


@pytest.mark.skipif(not os.path.exists(IMG), reason="thieu anh chu du an")
def test_detect_picks_banner_and_purple_rings():
    img = cv2.imread(IMG)[:960]
    buffs = steer.detect(img)["buff"]
    xs = sorted(int(b[0]) for b in buffs)
    assert len(buffs) >= 4, buffs                      # bang +5% + 3 vong tim
    assert any(abs(x - 74) < 40 for x in xs)           # bang +5% (trai)
    assert sum(1 for b in buffs if 140 <= b[0] <= 260) >= 3   # 3 vong tim giua-trai


def test_drag_watch_flags_when_squad_does_not_follow():
    w = steer.DragWatch(need=3)
    out = []
    for _ in range(6):
        out.append(w.update(286, 100.0))               # ra lenh keo phai 100 px, doi quan van 286
    assert True in out


def test_drag_watch_ok_when_following_or_at_edge():
    w = steer.DragWatch(need=3)
    x = 200
    for _ in range(8):
        assert not w.update(x, 100.0)
        x += 30                                        # doi quan di theo
    w2 = steer.DragWatch(need=2)
    assert not any(w2.update(485, 100.0) for _ in range(6))   # sat mep phai: bi chan that, khong bao dong gia


def test_drag_watch_ignores_small_commands():
    w = steer.DragWatch(need=2)
    assert not any(w.update(300, 5.0) for _ in range(10))


def test_frame_stream_restart_and_fps(monkeypatch):
    launched = []

    class _Out:
        @staticmethod
        def read(n):
            return b""

    class _P:
        stdout = _Out()

        def kill(self):
            launched.append("kill")

    def _popen(*a, **k):
        launched.append("popen")
        return _P()

    monkeypatch.setattr(stream.subprocess, "Popen", _popen)
    fs = stream.FrameStream("adb", "emulator-5554")
    fs.restart()
    assert launched.count("popen") == 2 and "kill" in launched and fs.restarts == 1
    assert fs.fps() == 0.0
    fs.close()
