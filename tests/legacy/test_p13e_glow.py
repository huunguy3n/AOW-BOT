"""P13e-4: o phat sang bam roi van sang -> khong bam lai trong luot ghe (live #5 @130,669 @138,729 @139,530)."""
import types

import numpy as np

from bot import tapguard
from bot.modules import notify


class Ctx:
    def __init__(self):
        self.taps, self.mem = [], None
        self.tap_guard = tapguard.TapGuard()
        self.dev = types.SimpleNamespace(idx=5)

    def shot(self):
        return np.zeros((960, 540, 3), np.uint8)

    def tap(self, x, y, wait=0):
        self.taps.append((x, y))

    def tap_tpl(self, *a, **k):
        return False

    def dismiss_reward(self):
        pass


def test_still_glowing_tile_not_retapped(monkeypatch):
    monkeypatch.setattr(notify, "glow_tiles", lambda img: [(138, 729)])
    monkeypatch.setattr(notify, "nhan_tiles", lambda img: [])
    monkeypatch.setattr(notify, "epic_header", lambda img: None)
    monkeypatch.setattr(notify, "tile_locked", lambda img, x, y: False)
    c = Ctx()
    notify.claim_glow_tiles(c)
    notify.claim_glow_tiles(c)
    notify.claim_glow_tiles(c)
    assert len(c.taps) == 1
