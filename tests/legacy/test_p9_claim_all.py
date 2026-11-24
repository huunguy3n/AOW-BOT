"""P9-3 (chu du an 2026-11-24, live-run-2): nhan HET cham do / qua tren moi man nhan qua (lap toi khi het);
khong cot Su thi / goi ₫ / mua VIP. Mot cham roi bo di = FAIL."""
import inspect
import os
import re
import types

import cv2
import pytest

from bot import buttons, claimloop, quest_rules, screens
from bot.modules import alliance, notify

FB = "data/pm-shots/owner-20261124/live2-feedback"
AUTO = "data/pm-shots/owner-20261124/live2/auto"


def _img(path, size=(540, 960)):
    if not os.path.exists(path):
        pytest.skip(f"thieu anh {path}")
    img = cv2.imread(path)
    return cv2.resize(img, size) if img.shape[:2] != (size[1], size[0]) else img


# ---------- vong lap chung ----------
def test_until_clear_keeps_going_while_dots_and_claims():
    dots = [3]

    def once():
        dots[0] -= 1
        return 1
    total, rounds, left = claimloop.until_clear(once, lambda: dots[0] > 0, max_rounds=10)
    assert (total, rounds, left) == (3, 3, False)            # 1 cham roi bo di = FAIL -> phai nhan ca 3


def test_until_clear_stops_when_no_dots_or_no_progress():
    assert claimloop.until_clear(lambda: 1, lambda: False) == (0, 0, False)
    calls = []
    _total, rounds, left = claimloop.until_clear(lambda: calls.append(1) or 0, lambda: True, max_rounds=10)
    assert rounds == 1 and left                              # cham do khong xu ly an toan duoc -> khong lap vo han


def test_tabs_until_clear_empties_current_tab_before_switching():
    left = {"premium": 2, "normal": 3}
    seq = []

    def enter(t):
        seq.append(("enter", t))

    def once(t):
        if left[t] <= 0:
            return 0
        left[t] -= 1
        seq.append(("claim", t))
        return 1
    total, _book = claimloop.tabs_until_clear(["premium", "normal"], enter, once)
    assert total == 5 and left == {"premium": 0, "normal": 0}
    assert seq[:4] == [("enter", "premium"), ("claim", "premium"), ("claim", "premium"), ("enter", "normal")]


def test_recruit_uses_loop(monkeypatch):
    left = {"recruit/tab_premium": 1, "recruit/tab_normal": 2}

    def once(ctx, tab, use_tickets):
        if left[tab] <= 0:
            return 0
        left[tab] -= 1
        return 1
    monkeypatch.setattr(notify, "_recruit_once", once)
    ctx = types.SimpleNamespace(cfg={}, tap_tpl=lambda *a, **k: True, find=lambda *a, **k: True,
                                save_debug=lambda *a: None)
    assert notify.recruit(ctx) == 3 and not any(left.values())


# ---------- TT phuc loi ----------
def test_free_column_filter_drops_epic_and_banner():
    tiles = [(140, 630), (380, 630), (470, 395), (140, 300)]
    assert notify.free_column_tiles(tiles, 480) == [(140, 630)]
    assert notify.free_column_tiles(tiles, None) == tiles


def test_epic_header_on_owner_login_gift():
    img = _img(f"{FB}/qua_dang_nhap_mien_phi_chua_bam.png")
    y = notify.epic_header(img)
    assert y is not None and 430 <= y <= 560
    assert notify.free_column_tiles([(141, 630), (370, 630), (450, 630), (470, 395)], y) == [(141, 630)]


def test_epic_header_absent_on_other_screens():
    for f in ("diem_danh_30_ngay_o_hao_quang.png", "vip_reddot_ruong_moi_ngay.png"):
        assert notify.epic_header(_img(f"{FB}/{f}")) is None


    """Live-run-2 s105738: bot da luot (ngay 2 troi mat) truoc khi bam o phat sang -> nay o phat sang truoc."""
    _img(f"{AUTO}/s105738.png")
    src = inspect.getsource(notify.claim_content)
    assert src.index("claim_glow_tiles(ctx)") < src.index("claim_scroll(ctx)")


def test_hub_revisits_productive_tab_only():
    assert notify.tab_open_again(None)
    assert notify.tab_open_again((1, 2))                    # lan truoc nhan duoc -> vao lai
    assert not notify.tab_open_again((1, 0))                # lan truoc 0 -> thoi
    assert not notify.tab_open_again((notify.TAB_REVISIT, 5))


# ---------- qua lien minh ----------
def test_ally_chest_dot():
    assert alliance.chest_dot([(500, 80)])
    assert not alliance.chest_dot([(100, 80), (500, 400)])


def test_special_claim_clicks_each_nhan_until_none(monkeypatch):
    items = [1, 2, 3]
    taps = []
    monkeypatch.setattr(buttons, "with_text", lambda img, rx, roi=None, kinds=None: [
        buttons.Button(470, 320 + 100 * i, 80, 34, "go", 95, "nhan") for i in range(len(items))])
    monkeypatch.setattr(screens, "same", lambda a, b: False)

    def tap(x, y, wait=1.0):
        taps.append((x, y))
        items.pop()
    ctx = types.SimpleNamespace(tap_tpl=lambda *a, **k: False, shot=lambda: None, tap=tap,
                                dismiss_reward=lambda: None)
    assert alliance.special_claim(ctx) == 3 and not items
    assert all(x >= alliance.GIFT_LIST_ROI[0] for x, _ in taps)


def test_nhan_regex_matches_only_nhan():
    assert re.search(alliance.NHAN_RX, "nhan")
    assert not re.search(alliance.NHAN_RX, "xem")


# ---------- thanh "Co the nhan Ruong moi ngay" ----------
def test_daily_chest_bar_classified_from_live2_ocr():
    live2 = "} C6 thé nhan Ruong moi ngay : 8. S. N | P Cothénhan Ruongpd"
    assert quest_rules.classify(live2)[0] == "chest"
    assert quest_rules.classify("Co the nhan Ruong moi ngay")[0] == "chest"
    assert quest_rules.classify("Mua goi Ruong moi ngay")[0] == "paid"     # nhom cam van dung truoc
    assert not quest_rules.delegated("chest")


def test_vip_and_shop_never_tap_paid_text():
    for t in ("Mua goi VIP", "d25000", "₫125000", "Nap the", "Mo khoa"):
        assert not buttons.is_claim_text(t), t
    assert buttons.is_claim_text("Nhan") and buttons.is_claim_text("Mien phi")
