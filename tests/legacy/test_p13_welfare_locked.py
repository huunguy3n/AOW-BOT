"""P13-7: tab Duong Tuong Lv.3 - o khoa cot Mien phi (moc 26-30) KHONG nhan duoc (anh duong_tuong_sai.png)."""
import inspect
import os

import cv2
import pytest

from bot import badges, tapguard
from bot.modules import notify

OWNER = "data/owner-feedback/p13/duong_tuong_sai.png"
TILES = [(138, 521), (138, 620), (138, 719), (138, 818), (138, 917)]     # tam o cot Mien phi, moc 26..30


@pytest.fixture(scope="module")
def img():
    if not os.path.exists(OWNER):
        pytest.skip("thieu anh chu")
    return cv2.imread(OWNER)


def test_all_five_locked_tiles_rejected(img):
    assert all(badges.tile_locked(img, x, y) for x, y in TILES)


def test_unlocked_tile_accepted(img):
    clean = img.copy()
    for x, y in TILES:                                   # xoa o khoa -> o mo
        clean[y - 40:y + 6, x - 46:x - 14] = (60, 50, 40)
    assert not any(badges.tile_locked(clean, x, y) for x, y in TILES)


def test_claim_glow_filters_locked(img, monkeypatch):
    class G:
        def keep(self, kind, tiles):
            return tiles

        def record(self, *a, **k):
            pass

    taps = []

    class Ctx:
        def shot(self):
            return img

        def tap(self, x, y, **k):
            taps.append((x, y))

        def tap_tpl(self, *a, **k):
            return False

        def dismiss_reward(self):
            pass

    monkeypatch.setattr(tapguard, "of", lambda ctx: G())
    monkeypatch.setattr(notify, "glow_tiles", lambda i: list(TILES))
    monkeypatch.setattr(notify, "nhan_tiles", lambda i: [])
    assert notify.claim_glow_tiles(Ctx()) == 0 and taps == []


def test_never_buy_or_unlock_templates_not_in_claim_flow():
    src = inspect.getsource(notify.claim_glow_tiles)
    for bad in ("cap_mua", "mo_khoa", "nhan_diem", "unlock", "buy"):
        assert bad not in src
