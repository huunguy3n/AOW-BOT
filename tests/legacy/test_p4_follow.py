"""P4 muc 1-2 (PM 2026-11-23): phan loai nhiem vu theo chu OCR + luat follow cho man ket hay gap."""
import glob

import cv2
import numpy as np
import pytest

from bot import quest_rules as qr
from bot.modules import tutorial
from bot.vision import Vision

# chu OCR THAT doc tu thanh nhiem vu tren anh logs/shots/*follow_stuck* (Tesseract 'eng', mat dau, sai ky tu)
OCR_SAMPLES = [
    ("| Tham gia tap két tan cong 1 lan phan quan Co giap . te", "rally", "rebels"),
    ("] Tham gia tap ké tn céng 1 Ian phan quéh pe ee Ee", "rally", "rebels"),
    ("} Kich sat 1 lan phan quan Lv.3 an we", "rebels", "rebels"),
    ("] Tang 4 Xuéng Thuc Pham dén cap 26” cP 10 mm i. 7 Bc", "build", None),
    ("Huan luyén 10 Tank bat ky", "train", "train"),
    ("Huấn luyện 2000 Tank bậc 6", "train", "train"),
    ("Tăng 5 Tướng lên cấp 90", "hero", None),
    ("Chiến thắng Đấu trường 290 lần", "arena", "play"),
    ("Hoàn tất Chiến dịch 1", "campaign", "campaign"),
    ("Hoàn thành 1 lần tình báo", "intel", "intel"),
    ("Sửa chữa radar 1", "build", None),
    ("Xây dựng 1 Bệnh Viện", "build", None),
    ("Tang 4 Xuong", "build", None),            # 'xuong' ~ 'tuong' chi khac 1 chu -> KHONG duoc thanh hero
    ("Tham gia 1 lien minh", "alliance", "alliance"),
    ("oO", "unknown", None),
    ("", "unknown", None),
]


@pytest.mark.parametrize(("text", "kind", "module"), OCR_SAMPLES)
def test_classify_ocr_samples(text, kind, module):
    assert qr.classify(text) == (kind, module)


def test_delegated_kinds():
    assert qr.delegated("rally") and qr.delegated("train") and qr.delegated("intel")
    assert not qr.delegated("build") and not qr.delegated("hero") and not qr.delegated("campaign")
    assert not qr.delegated("unknown")


def test_same_quest_ignores_ocr_noise():
    a = "| Tham gia tap két tan cong 1 lan phan quan Co giap . te"
    b = "] Tham gia tap ket tan cong 1 lan phan quan Co giap TD te"
    assert qr.same_quest(a, b)
    assert not qr.same_quest(a, "Tang 4 Xuong Thuc Pham den cap 26")
    assert not qr.same_quest(None, a)


def test_build_give_up():
    assert not qr.build_give_up({"drags": 8, "build_waits": 3})
    assert qr.build_give_up({"drags": 8, "build_waits": 4})
    assert not qr.build_give_up({"drags": 2, "build_waits": 10})


# ---------- decide() o che do follow voi vision gia ----------
class V:
    """seen: {ten anh mau: (x, y)}; moi anh mau khac coi nhu khong thay."""

    def __init__(self, seen):
        self.seen = dict(seen)

    def find(self, img, name, th=None, roi=None, **k):
        p = self.seen.get(name)
        return (p[0], p[1], 0.95) if p else None

    def find_all(self, img, name, **k):
        p = self.seen.get(name)
        return [(p[0], p[1], 0.95)] if p else []

    def best(self, img, name, **k):
        return self.find(img, name)


IMG = np.full((960, 540, 3), 90, np.uint8)   # anh xam phang: khong co chu V / ban tay / cot sang


@pytest.fixture(autouse=True)
def no_color_detectors(monkeypatch):
    for fn in ("find_beam", "find_hand_rot", "find_hand_beam", "find_green_chevron", "find_ring"):
        monkeypatch.setattr(tutorial, fn, lambda *a, **k: None)
    monkeypatch.setattr("bot.badges.free_bubbles", lambda img: [])


def test_world_map_follow_exits_instead_of_center_taps():
    v = V({"common/btn_to_city": (60, 900)})
    st = {"follow": True}
    acts = [tutorial.decide(v, IMG, idle, st)[0] for idle in range(3)]
    assert "exit" in acts
    assert not any(a == "tap" for a in acts)       # khong bao gio cham giua ban do (o dat "Chuyen thanh")


def test_world_map_not_follow_keeps_old_behaviour():
    v = V({"common/btn_to_city": (60, 900)})
    assert tutorial.decide(v, IMG, 0, {"follow": False})[0] != "exit"


def test_quest_board_claims_then_closes(monkeypatch):
    v = V({"daily/tab_2_main": (270, 112), "tutorial/btn_claim_all": (270, 850), "common/btn_x_small": (515, 20)})
    st = {"follow": True}
    monkeypatch.setattr(tutorial, "_colored", lambda img, x, y, min_sat=80: True)   # nut sang
    act, x, y, why = tutorial.decide(v, IMG, 0, st)
    assert (act, (x, y)) == ("tap", (270, 850)) and "Nhan toan bo" in why
    del v.seen["tutorial/btn_claim_all"]
    assert tutorial.decide(v, IMG, 0, st)[0] == "wait"             # cho 1 nhip huong dan
    act, x, y, _ = tutorial.decide(v, IMG, 1, st)
    assert (act, (x, y)) == ("exit", (515, 20))


def test_intel_map_exits_by_back_arrow():
    v = V({"intel/title": (100, 30), "common/btn_back": (40, 30)})
    assert tutorial.decide(v, IMG, 1, {"follow": True})[:3] == ("exit", 40, 30)


def test_popup_x_top_right_closes_never_join():
    v = V({"common/btn_x": (484, 100)})
    assert tutorial.decide(v, IMG, 1, {"follow": True})[:3] == ("tap", 484, 100)


def test_build_mode_gives_up_after_drags():
    v = V({"common/btn_close": (504, 875)})
    st = {"follow": True, "in_build": True, "drags": 8}
    acts = []
    for idle in range(6):
        acts.append(tutorial.decide(v, IMG, idle, st)[0])
    assert acts[:3] == ["wait"] * 3 and acts[3] == "build_fail"


def test_build_mode_tutorial_never_gives_up():
    v = V({"common/btn_close": (504, 875)})
    st = {"follow": False, "in_build": True, "drags": 8}
    assert all(tutorial.decide(v, IMG, i, st)[0] == "wait" for i in range(8))


# ---------- hoi quy tren anh that (chi khi co logs/shots local; fixture khong co trong git) ----------
SHOTS = sorted(glob.glob("logs/shots/*-follow_stuck.png"))[::4]   # ~30 anh cho nhanh; du: tools/follow_stats.py


@pytest.mark.skipif(not SHOTS, reason="khong co anh logs/shots (chi chay local)")
def test_real_stuck_shots_mostly_have_exit():
    v = Vision("templates")
    ok = 0
    for f in SHOTS:
        img = cv2.imread(f)
        st = {"follow": True}
        for idle in range(3):
            act, _, _, why = tutorial.decide(v, img, idle, st)
            if act == "exit" or (act == "tap" and not why.startswith(("man la", "dung yen"))):
                ok += 1
                break
    assert ok / len(SHOTS) >= 0.9     # tieu chi P4: follow_stuck giam >= 70 %
