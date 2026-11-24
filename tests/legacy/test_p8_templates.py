"""P8-1: 14 anh mau cat bang ADB 540x960 tren #1 (commit 9cc0c25) duoc noi dung ten/ROI trong code, kiem tren chinh
anh ADB goc data/pm-shots/owner-20261124/p8-adb/ (data/ bi gitignore -> tu skip khi thieu).
Kem luong an toan: Su menh khong cham goi d, bang Thuoc The Luc khong bao gio chon nut "Mua"."""
import os

import cv2
import numpy as np
import pytest

from bot import buttons, intel_rules, ocr
from bot.modules import alliance, mission, play
from bot.vision import Vision

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
SHOTS = os.path.join(ROOT, "data", "pm-shots", "owner-20261124", "p8-adb")
TPL = os.path.join(ROOT, "templates")

NEW = ["mission/icon", "mission/title", "mission/tab_daily", "mission/gift_icon", "mission/free_chest",
       "ally/tab_territory", "ally/btn_contest", "ally/btn_contest_claim", "ally/tech_vinh_cuu",
       "intel/potion_10", "intel/btn_buy_potion", "play/btn_refresh", "play/item_crystal", "play/btn_arena_refresh"]


def _shot(name):
    img = cv2.imread(os.path.join(SHOTS, name + ".png"))
    if img is None:
        pytest.skip(f"thieu anh ADB {name}.png (data/ khong co trong git)")
    return img


@pytest.fixture(scope="module")
def v():
    return Vision(TPL)


@pytest.mark.parametrize("name", NEW)
def test_new_templates_exist_and_fit_540x960(v, name):
    t = v.load(name, probe=True)
    assert t is not None, name
    assert t.shape[0] < 200 and t.shape[1] < 540


# (anh ADB, anh mau, ROI code dang dung, tam mong doi)
CASES = [
    ("p8_a", "mission/icon", mission.ICON_ROI, (509, 322)),
    ("mis1", "mission/title", None, (271, 27)),
    ("mis1", "mission/tab_daily", mission.TAB_ROI, (440, 212)),
    ("mis1", "mission/gift_icon", mission.GIFT_ROI, (187, 126)),
    ("mis2", "mission/free_chest", mission.FREE_CHEST_ROI, (43, 311)),
    ("ally1", "ally/tab_territory", alliance.TAB_ROW_ROI, (266, 78)),
    ("ally2", "ally/tab_territory", alliance.TAB_ROW_ROI, (266, 78)),       # tab da chon van khop ~0.92
    ("ally2", "ally/btn_contest", alliance.CONTEST_BTN_ROI, (409, 928)),
    ("ally3", "ally/btn_contest_claim", alliance.CONTEST_CLAIM_ROI, (450, 381)),
    ("ally5", "ally/tech_vinh_cuu", None, (264, 797)),
    ("intel2", "intel/potion_10", None, (222, 324)),
    ("intel2", "intel/btn_buy_potion", None, (439, 782)),
    ("mine2", "play/btn_refresh", None, (491, 208)),
    ("truck1", "play/item_crystal", play.CRYSTAL_ROI, (79, 700)),
    ("arena1", "play/btn_arena_refresh", None, (436, 672)),
]


@pytest.mark.fixtures
@pytest.mark.parametrize(("shot", "name", "roi", "at"), CASES)
def test_template_found_at_code_roi(v, shot, name, roi, at):
    p = v.find(_shot(shot), name, roi=roi, th=0.85)
    assert p is not None, f"{name} khong thay tren {shot}"
    assert abs(p[0] - at[0]) <= 3 and abs(p[1] - at[1]) <= 3, p


@pytest.mark.fixtures
@pytest.mark.parametrize(("shot", "name", "roi"), [
    ("cityend", "mission/title", None),
    ("mis1", "mission/free_chest", mission.FREE_CHEST_ROI),
    ("ally1", "ally/btn_contest_claim", alliance.CONTEST_CLAIM_ROI),
    ("intel1", "intel/potion_10", None),
    ("mine1", "play/btn_refresh", None),
    ("mine2", "play/item_crystal", play.CRYSTAL_ROI),
    ("play1", "play/item_crystal", play.CRYSTAL_ROI),      # icon pha le the Loi choi (~314,182) ngoai vung popup
    ("play1", "play/btn_arena_refresh", None),
])
def test_template_not_found_on_wrong_screen(v, shot, name, roi):
    assert v.find(_shot(shot), name, roi=roi, th=0.85) is None


@pytest.mark.fixtures
def test_free_chest_red_dot_on_real_shot(v):
    """Cham do ruong Qua ky dieu toi/cam (H~8, V 130-170): red_dots thuong khong thay -> chest_dot phai thay."""
    img = _shot("mis2")
    c = v.find(img, "mission/free_chest", roi=mission.FREE_CHEST_ROI)
    assert c and mission.chest_dot(img, c)


@pytest.mark.fixtures
def test_mission_daily_and_gift_buttons_never_paid(v):
    """Goi d125000 / d250000 (Qua ky dieu ~451,539 / 451,755): buttons.claims khong tra (khong co chu Nhan) va ca tren
    man San kho bau / Qua ky dieu khong co nut nao duoc claim_safe chap nhan."""
    for s in ("mis1", "mis2"):
        img = _shot(s)
        for screen, roi in (("daily", mission.DAILY_ROI), ("gift", mission.FREE_CHEST_ROI)):
            ok = [b for b in buttons.claims(img, roi)
                  if mission.tap_ok(screen, b.x, b.y) and not mission.paid_text(b.text)]
            assert ok == [], (s, screen, ok)
    assert not mission.tap_ok("gift", 451, 539) and not mission.tap_ok("gift", 451, 755)
    assert not mission.tap_ok("main", 268, 213) and not mission.tap_ok("main", 97, 213)   # The thong hanh / San kho bau


@pytest.mark.fixtures
def test_mission_free_chest_flow_on_real_shot(v):
    img = _shot("mis2")

    class C:
        def __init__(self):
            self.v, self.taps = v, []

        def shot(self):
            return img

        def tap(self, x, y, **k):
            self.taps.append((x, y))

        def dismiss_reward(self):
            pass

    c = C()
    assert mission.free_chest(c) >= 1
    assert c.taps and all(mission.tap_ok("gift", x, y) for x, y in c.taps)
    assert (43, 311) in c.taps


@pytest.mark.fixtures
def test_potion_use_row_never_buy(v):
    img = _shot("intel2")
    uses = v.find_all(img, "intel/btn_use_potion")
    buys = v.find_all(img, "intel/btn_buy_potion")
    row = v.find(img, "intel/potion_10")
    p = intel_rules.pick_use_button(uses, row, buys)
    assert p is not None and abs(p[0] - 438) <= 3 and abs(p[1] - 340) <= 3
    assert all(abs(p[1] - b[1]) > 22 for b in buys)


def test_potion_use_matching_on_buy_button_rejected():
    """Nut Dung khop nham dung cho nut Mua -> loai, khong co nut nao -> None (khong bam gi)."""
    assert intel_rules.pick_use_button([(439, 782, 0.9)], (222, 324, 0.99), [(439, 782, 0.99)]) is None
    assert intel_rules.pick_use_button([(439, 782, 0.9), (438, 341, 0.9)], (222, 324, 0.99),
                                       [(439, 782, 0.99)])[:2] == (438, 341)


def test_chest_dot_synthetic():
    img = np.zeros((960, 540, 3), np.uint8)
    img[:] = (90, 40, 60)
    assert not mission.chest_dot(img, (43, 311))
    hsv = np.zeros((1, 1, 3), np.uint8)
    hsv[:] = (8, 255, 150)
    bgr = tuple(int(x) for x in cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0])
    cv2.circle(img, (81, 285), 8, bgr, -1)                 # cham do toi/cam nhu anh that
    assert mission.chest_dot(img, (43, 311))
    big = np.zeros((960, 540, 3), np.uint8)
    cv2.rectangle(big, (50, 262), (110, 310), bgr, -1)     # mang do lon (anh nen) -> khong phai cham
    assert not mission.chest_dot(big, (43, 311))


@pytest.mark.fixtures
@pytest.mark.ocr
def test_truck_popup_guard_power_and_loot_count_ocr():
    t, m = _shot("truck1"), _shot("mine2")
    if not ocr.init(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytest.skip("thieu Tesseract")
    assert play._digits(t, (155, 634, 120, 24)) == 98565656    # luc chien ho ve (P8-2 dung lai vung nay)
    assert play.popup_rarity(t) == "SR"
    assert play.loot_left(m) == 1
