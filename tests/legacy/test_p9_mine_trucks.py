"""P9-6 (chu du an 2026-11-24): Mo khoang san > Xe khai thac cua toi - dua xe cua minh di toi het luot; lam moi chi
khi Mien phi / con luot ('1/0' dung); SR/SSR tinh the -> moi ho tro > 400M, khong ai thi KHONG xuat phat; xe thuong
Doi hinh de xuat -> Luu -> Xuat phat; hop Chu y chi Xac nhan, khong tick o."""
import os
import types

import cv2
import numpy as np
import pytest

from bot import buttons, ocr
from bot.modules import mine_trucks as M

AUTO = "data/pm-shots/owner-20261124/live2/auto"
FB = "data/pm-shots/owner-20261124/live2-feedback"
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def _img(p, pad=True):
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    img = cv2.imread(p)
    if pad and img.shape[:2] != (960, 540):
        out = np.zeros((960, 540, 3), np.uint8)
        out[:min(960, img.shape[0]), :min(540, img.shape[1])] = img[:960, :540]
        return out
    return img


def test_parse_left_and_refresh_rules():
    assert M.parse_left("S6 lan khai thac con 1ai:4/4") == 4
    assert M.parse_left("con lai: 0/4") == 0
    assert M.parse_left("") is None
    assert M.refresh_allowed("Mien phi") and M.refresh_allowed("Miễn phí")
    assert not M.refresh_allowed("1/0")                   # anh xe_mo_2: het luot lam moi
    assert M.refresh_allowed("0/1")
    assert not M.refresh_allowed("")                      # khong doc duoc -> khong bam (co the ton phi)
    assert not M.refresh_allowed("50")


def test_truck_plan():
    assert M.truck_plan("SSR", True) == "support" and M.truck_plan("SR", True) == "support"
    assert M.truck_plan("SR", False) == "normal" and M.truck_plan("N", True) == "normal"
    assert M.truck_plan(None, False) == "normal"


def test_pick_supporter_over_400m_only():
    rows = [(None, (403, 237)), (375966435, (403, 581)), (410936678, (403, 411))]
    assert M.pick_supporter(rows, 400_000_000) == (410936678, (403, 411))
    assert M.pick_supporter([(132587832, (430, 297)), (159676080, (430, 471))], 400_000_000) is None


def test_checkbox_never_tapped():
    assert not M.safe_tap_point(105, 408)                 # o tick "Hom nay khong hien thi lai" (xe_mo_7)
    assert M.safe_tap_point(400, 485)                     # Xac nhan


def test_plus_marks_on_live2_mine_screen():
    img = _img(f"{AUTO}/s110403.png")
    pts = M.plus_marks(img)
    assert len(pts) == 2 and abs(pts[0][0] - 153) <= 8 and abs(pts[1][0] - 389) <= 8


def test_left_counter_ocr_live2():
    img = _img(f"{AUTO}/s110403.png")
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    assert M.parse_left(ocr.text(img, M.LEFT_ROI)) == 4


def test_rarity_owner_popup_is_n():
    assert M.rarity_letter(_img(f"{FB}/xe_mo_1_lam_moi_mien_phi.png")) == "N"


def test_support_rows_owner_image():
    img = _img(f"{FB}/xe_mo_5_chon_tren_400M.png")
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    got = M.pick_supporter(M.support_rows(img), 400_000_000)
    assert got and got[0] == 410936678


# ---------------------------------------------------------------- luong (gia lap)
class Ctx:
    def __init__(self, texts):
        self.cfg = {}
        self.taps = []
        self.texts = texts          # pattern -> co nut khong
        self.dev = types.SimpleNamespace(swipe=lambda *a, **k: self.taps.append("swipe"))

    def shot(self):
        return np.zeros((960, 540, 3), np.uint8)

    def tap(self, x, y, wait=1.0):
        assert M.safe_tap_point(x, y)
        self.taps.append((x, y))

    def back_out(self, n=1):
        self.taps.append("back")

    def find(self, *a, **k):
        return (1, 1, 1.0)


def _with_text(present):
    def f(img, pattern, roi=None, kinds=None):
        for key, (x, y) in present.items():
            if key in pattern:
                return [buttons.Button(x, y, 120, 40, "claim", 85, key)]
        return []
    return f


def test_normal_truck_recommend_save_depart_confirm(monkeypatch):
    present = {"de xu": (150, 925), "lu": (380, 925), "xu\\w{0,2}t ph": (268, 780), "c nh": (400, 485)}
    monkeypatch.setattr(buttons, "with_text", _with_text(present))
    c = Ctx(present)
    assert M.normal_depart(c)
    assert c.taps == [M.GEAR, (150, 925), (380, 925), (268, 780), (400, 485)]


def test_support_no_one_over_400m_does_not_depart(monkeypatch):
    monkeypatch.setattr(M, "support_rows", lambda img: [(132587832, (430, 297)), (159676080, (430, 471))])
    monkeypatch.setattr(buttons, "with_text", _with_text({"li\\w{0,2}n\\s*minh": (360, 115)}))
    c = Ctx({})
    assert M.support_depart(c, 400_000_000, pages=2) is False
    assert (268, 780) not in c.taps and c.taps[-1] == "back"       # KHONG Xuat phat, dong bang
    assert (430, 297) not in c.taps and (430, 471) not in c.taps   # khong moi nguoi < 400M


def test_support_invites_over_400m(monkeypatch):
    monkeypatch.setattr(M, "support_rows", lambda img: [(375966435, (403, 581)), (410936678, (403, 411))])
    monkeypatch.setattr(buttons, "with_text", _with_text({}))
    c = Ctx({})
    assert M.support_depart(c, 400_000_000)
    assert (403, 411) in c.taps and (403, 581) not in c.taps


def test_run_stops_refresh_on_1_0_and_when_counter_zero(monkeypatch):
    labels = iter(["4/4", "1/0", "3/4", "3/4"])
    rois = (M.LEFT_ROI, M.REFRESH_LABEL_ROI)
    monkeypatch.setattr(ocr, "text", lambda img, roi, *a, **k: next(labels, "0/4") if roi in rois else "")
    monkeypatch.setattr(M, "plus_marks", lambda img: [(153, 478)])
    monkeypatch.setattr(M, "rarity_letter", lambda img: "N")
    monkeypatch.setattr(M, "normal_depart", lambda ctx: ctx.taps.append("depart") or True)
    c = Ctx({})
    c.cfg = {"mine_trucks": {"max_trucks": 1}}
    assert M.run(c) == 1
    assert M.REFRESH not in c.taps                          # "1/0" -> khong lam moi
    assert "depart" in c.taps
