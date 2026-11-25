"""P13-5: tinh bao khong ra/vao thanh pho lap lai: SKIP / mat tieu de / ghim khong ro -> o lai ban do, dong popup,
mo lai bang tinh bao; ve thanh pho toi da 1 lan trong buoc (intel.run ve 1 lan khi xong)."""
import types

import numpy as np

from bot import intel_rules as IR
from bot.modules import notify


class Ctx:
    def __init__(self):
        self.cfg = {"notify": {"intel_max": 6}}
        self.city = 0
        self.closed = 0
        self.title_open = False
        self.icon_seen = False       # icon Tinh bao co tren man hien tai (ban do) hay khong
        self.v = types.SimpleNamespace(find_all=lambda *a, **k: [(100, 300, 0.9)])
        self.dev = types.SimpleNamespace(idx=0)

    def find(self, name, **k):
        if name == "intel/title":
            return (1, 1) if self.title_open else None
        if name == "campaign/btn_open":
            return (60, 700) if self.icon_seen else None
        return None

    def ensure_city(self):
        self.city += 1
        self.icon_seen = True

    def close_popups(self, *a, **k):
        self.closed += 1
        self.icon_seen = True            # dong popup -> thay ban do + icon

    def tap(self, *a, **k):
        self.title_open = False          # tap icon tinh bao / ghim: ghi nhan; bang tieu de xu ly rieng
        return True

    def shot(self):
        return np.zeros((960, 540, 3), np.uint8)

    def dismiss_reward(self):
        pass


def test_skip_does_not_call_ensure_city(monkeypatch):
    ctx = Ctx()
    ctx.icon_seen = True
    results = iter([IR.SKIP[0]] * 5)
    monkeypatch.setattr(notify, "done_ticks", lambda img: [])
    monkeypatch.setattr(notify, "energy", lambda c: 99)
    monkeypatch.setattr(notify, "intel_mission", lambda c: next(results))
    monkeypatch.setattr(notify, "_pickups", lambda c: types.SimpleNamespace(done=lambda p: False))
    monkeypatch.setattr(notify.time, "sleep", lambda s: None)
    # moi lan ghim cach nhau de khong bi 'tried'
    pins = iter([[(100 + 40 * i, 300, 0.9)] for i in range(10)])
    ctx.v = types.SimpleNamespace(find_all=lambda *a, **k: next(pins))
    notify.intel(ctx, 5)
    assert ctx.city == 0                       # SKIP nhieu lan: KHONG ensure_city
    assert ctx.closed >= 1                     # chi dong popup


def test_open_intel_no_city_when_not_allowed():
    ctx = Ctx()
    assert notify.open_intel(ctx, allow_city=False) is True
    assert ctx.city == 0 and ctx.closed == 1
    ctx2 = Ctx()
    assert notify.open_intel(ctx2) is True and ctx2.city == 1      # mac dinh cu: ve thanh pho 1 lan
