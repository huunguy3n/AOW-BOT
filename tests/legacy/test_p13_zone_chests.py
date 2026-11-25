"""P13-9: Hoat dong tro choi > Chien Khu manh nhat: nhan ruong co cham do, bo ruong xam / cham do tab."""
import os

import cv2
import pytest

from bot import ocr
from bot.modules import notify

OWNER = "data/owner-feedback/p13/chien_khu_manh_nhat_ruong.png"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


@pytest.fixture(scope="module")
def img():
    if not os.path.exists(OWNER):
        pytest.skip("thieu anh chu")
    return cv2.imread(OWNER)


def test_only_dotted_chests(img):
    pts = notify.zone_chest_points(img)
    assert len(pts) == 3 and [p[0] for p in pts] == [92, 252, 412]    # 6M / 12M / 24M; 300K / 600K / 1.2M (xam) bo
    assert all(p[1] > 800 for p in pts)                                 # khong cham do tab (y~98) / tab con (y~458)


def test_title_matching():
    assert notify.is_zone_title("Chién Khu magne")
    assert notify.is_zone_title("whién Khu mAh.")
    assert not notify.is_zone_title("Quan quan tuan")
    assert not notify.is_zone_title("")


class V:
    def find(self, *a, **k):
        return None


class Ctx:
    def __init__(self, img):
        self.img, self.taps = img, []
        self.v = V()

    def shot(self):
        return self.img

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def tap_tpl(self, *a, **k):
        return False

    def dismiss_reward(self):
        pass


def test_zone_chests_taps_only_dotted(img):
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    c = Ctx(img)
    assert notify.zone_chests(c, max_taps=3) == 3
    assert [t[0] for t in c.taps] == [92, 252, 412]


def test_other_tab_untouched(img):
    c = Ctx(img[:, :].copy())
    c.img[225:275, 20:520] = 20            # xoa tieu de -> khong phai tab Chien Khu
    assert notify.zone_chests(c) == 0 and c.taps == []
