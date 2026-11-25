"""P13-8 / P13-13: the Tuong 'Co the doi' (du manh 11/10) -> mo the -> bam 'Chieu mo' (templates/hero/btn_exchange.png,
cat tu anh chu du an tuong_chieu_mo.png)."""
import os

import cv2
import pytest

from bot.modules import notify

LIST = "data/owner-feedback/p13/tuong_co_the_doi.png"
DETAIL = "data/owner-feedback/p13/tuong_chieu_mo.png"
TPL = "templates/hero/btn_exchange.png"


def test_template_exists_and_matches_owner_detail():
    assert os.path.exists(TPL)
    if not os.path.exists(DETAIL):
        pytest.skip("thieu anh chu")
    t, img = cv2.imread(TPL), cv2.imread(DETAIL)
    assert cv2.minMaxLoc(cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED))[1] >= 0.9


def test_card_with_full_shards_detected():
    if not os.path.exists(LIST):
        pytest.skip("thieu anh chu")
    cards = notify.full_shard_cards(cv2.imread(LIST))
    assert cards == [(80, 166)]                       # chi the 'Co the doi' (11/10); the 0/10 khong


class V:
    def find(self, img, name, **k):
        return (1, 1) if name == "hero/title" else None


class Ctx:
    def __init__(self, img):
        self.POPUP_CLOSERS = []
        self.img, self.taps, self.tpl = img, [], []
        self.v = V()

    def shot(self):
        return self.img

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def tap_tpl(self, name, **k):
        self.tpl.append(name)
        return False

    def find(self, name, **k):
        return (1, 1)

    def save_debug(self, *a):
        pass

    def tap_first(self, *a, **k):
        return None


def test_unlock_taps_card_then_only_exchange_button():
    if not os.path.exists(LIST):
        pytest.skip("thieu anh chu")
    c = Ctx(cv2.imread(LIST))
    notify.unlock_heroes(c, max_cards=1)
    assert c.taps == [(80, 166)] and c.tpl == ["hero/btn_exchange"]     # khong bam gi khac (khong mua / goi tra phi)
