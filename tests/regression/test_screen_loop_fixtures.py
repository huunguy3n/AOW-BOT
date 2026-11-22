"""S1/S2 tren anh that (logs/inv A-INV-1, bang nhiem vu #1) - tests/fixtures/screen_loop, chi co tren may local."""
import os

import cv2
import pytest

from aowbot.domain.blockers import BlockReason, hamming
from bot import buttons, game_msg, ocr, queues
from bot.modules import heal, notify, quests, upgrade
from bot.vision import Vision

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = os.path.join(ROOT, "tests", "fixtures", "screen_loop")
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"

pytestmark = [pytest.mark.fixtures,
              pytest.mark.skipif(not os.path.isdir(DIR), reason="thieu tests/fixtures/screen_loop (chi may local)")]


def img(name):
    return cv2.imread(os.path.join(DIR, name))


@pytest.mark.ocr
@pytest.mark.skipif(not os.path.exists(TESS), reason="thieu Tesseract")
@pytest.mark.parametrize("name, want", [
    ("msg_plot_locked_i2.png", BlockReason.PLOT_LOCKED),
    ("msg_plot_locked_i4.png", BlockReason.PLOT_LOCKED),
    ("msg_prereq_i2.png", BlockReason.PREREQ),
    ("msg_prereq_i2b.png", BlockReason.PREREQ),
    ("msg_none_i0.png", None),                    # tin tro giup lien minh: KHONG phai ly do chan
    ("upgrade_late_i2.png", None),
])
def test_game_message(name, want):
    ocr.init(TESS)
    assert game_msg.read(img(name))[0] is want


def test_upgrade_menu_visible_once_settled():
    v = Vision(os.path.join(ROOT, "templates"), 0.82)
    assert v.find(img("upgrade_late_i2.png"), "build/btn_upgrade_icon")


def test_row_keys_stable_across_frames_and_distinct_between_rows():
    v = Vision(os.path.join(ROOT, "templates"), 0.82)
    keys = []
    for name in ("panel_main_a.png", "panel_main_b.png"):
        im = img(name)
        keys.append([quests.row_key(im, p) for p in sorted(v.find_all(im, "quest/btn_go"), key=lambda p: p[1])])
    a, b = keys
    assert len(a) == len(b) >= 4
    for i, ka in enumerate(a):
        assert hamming(ka, b[i]) <= quests.ROW_MAX_DIST
        assert all(hamming(ka, kb) > 2 * quests.ROW_MAX_DIST for j, kb in enumerate(b) if j != i)


@pytest.mark.ocr
@pytest.mark.skipif(not os.path.exists(TESS), reason="thieu Tesseract")
@pytest.mark.parametrize("name, want", [
    ("queues_0-2_0-1_0-3.png", {"build": (0, 2), "research": (0, 1), "train": (0, 3)}),
    ("queues_1-2_0-1_0-3.png", {"build": (1, 2), "research": (0, 1), "train": (0, 3)}),
    ("queues_0-2_hard.png", {"build": (0, 2)}),               # so tren nen cong trinh xanh (#4)
    # P2: Tesseract khong doc duoc cac o duoi -> anh chu so templates/qdigits
    ("queues2_city_main_i1.png", {"build": (1, 2), "research": (1, 1), "train": (3, 3)}),
    ("queues2_reddots_i1.png", {"build": (2, 2), "research": (1, 1), "train": (3, 3)}),
    ("queues2_covered_i1.png", {"build": None, "research": (1, 1), "train": (3, 3)}),   # so tho xay bi icon qua che
    ("queues2_snap_city.png", {"build": (0, 2), "train": (0, 1)}),
    ("queues2_train11_i3.png", {"build": (0, 2), "train": (1, 1)}),
    ("queues2_dim_i3.png", {"train": (0, 2)}),                 # man bi phu toi
])
def test_queue_counters(name, want):
    ocr.init(TESS)
    v = Vision(os.path.join(ROOT, "templates"), 0.82)
    assert queues.read(v, img(name)) == want


@pytest.mark.ocr
@pytest.mark.skipif(not os.path.exists(TESS), reason="thieu Tesseract")
@pytest.mark.parametrize("name, is_hq", [("hq_menu_lv4.png", True), ("radar_menu.png", False)])
def test_hq_menu_label(name, is_hq):
    ocr.init(TESS)
    v = Vision(os.path.join(ROOT, "templates"), 0.82)
    im = img(name)
    ic = v.find(im, "build/btn_upgrade_icon")
    assert ic and upgrade.is_hq_label(upgrade.hq_label(im, ic[0], ic[1])) is is_hq


def test_hq_is_at_tap_point_after_world_to_city():
    """Q2: ve thanh pho tu the gioi -> nha chinh giua man; diem cham HQ_TAP nam tren than nha chinh (anh #6)."""
    v = Vision(os.path.join(ROOT, "templates"), 0.82)
    ic = v.find(img("hq_menu_lv4.png"), "build/btn_upgrade_icon")
    x, y = upgrade.HQ_TAP
    assert abs(ic[0] - 45 - x) < 60 and 60 < ic[1] - y < 160     # vong menu hien ngay duoi diem cham


def test_hero_detail_buttons_with_dots():
    """Anh chu du an gui 2026-11-21 (Doi Biet Kich SEAL): Tang cap, Tang sao, sach Cau chuyen deu co cham do."""
    v = Vision(os.path.join(ROOT, "templates"), 0.82)
    im = img("hero_detail_seal.png")
    b = v.find(im, "hero/btn_levelup")
    st = v.find(im, "hero/btn_star", th=0.9)
    bk = v.find(im, "hero/btn_book", th=0.85)
    assert b and notify._dot_near(im, b)
    assert st and notify._dot_near(im, st, dx=19, dy=-14, tol=(14, 14))
    assert bk and notify._dot_near(im, bk, dx=16, dy=-18, tol=(12, 12))


@pytest.mark.ocr
@pytest.mark.skipif(not os.path.exists(TESS), reason="thieu Tesseract")
@pytest.mark.parametrize("name, want", [
    ("quest_chapter_claim_all.png", ["nhan toan bo"]),      # thuong chuong - truoc day bo qua
    ("quest_main_claim_crop.png", ["nhan"]),                # tab Chinh: nut Nhan dong phu - truoc day chi bam 'Den'
    ("welfare_claim.png", ["nhan"]),
    ("teal_recruit_not_claim.png", []),                     # cung mau, chu 'Chieu mo'
    ("teal_gem_buy_not_claim.png", []),                     # cung mau, nut MUA bang kim cuong
])
def test_claim_buttons_by_color_and_text(name, want):
    ocr.init(TESS)
    assert [b.text for b in buttons.claims(img(name))] == want


@pytest.mark.parametrize("name, n", [("hospital_crop.png", 1), ("hospital_ring_crop.png", 1),
                                     ("city_hospital_i0.png", 1), ("city_hospital_b.png", 1),
                                     ("city_no_hospital_i5.png", 0)])
def test_hospital_cross(name, n):
    im = img(name)
    roi = (0, 0, im.shape[1], im.shape[0])
    assert len(heal.crosses(im, roi)) == n
