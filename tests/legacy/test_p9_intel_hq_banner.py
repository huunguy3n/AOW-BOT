"""P9-9 (chu du an 2026-11-24, live2): Tinh bao bam tu ban do the gioi; toi da 2 hop qua (tick tran khong giai phong cho
hop dang nhat); nha chinh da skin (mau Halloween + vi tri/nhan ten); OCR thanh nhiem vu chinh khong con rac nen."""
import os
import types

import cv2
import pytest

from bot import intel_rules as IR
from bot import ocr, quest_rules
from bot.modules import intel, mainquest, notify, rebels, upgrade
from bot.vision import Vision

SH = "data/pm-shots/owner-20261124"
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def _img(rel):
    p = f"{SH}/{rel}"
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    return cv2.imread(p)[..., :3]


# ---------------------------------------------------------------- toi da 2 hop
def test_battle_tick_does_not_free_pickup_slot():
    """live2 11:06:57-11:07:05: 3 tick xanh = nhan thuong ghim da xong. Tick o ghim KHAC (tran) khong duoc giai phong
    cho cua 2 hop dang nhat -> hop thu 3 van phai cho."""
    pk = IR.Pickups(cap=2, dur=90)
    pk.add(0, (100, 300))
    pk.add(5, (400, 600))
    assert not pk.done((250, 450))          # tick tran giua ban do -> khong giai phong
    assert not pk.can_pick(10)
    assert pk.done((110, 290))              # tick tai ghim hop 1 -> giai phong
    assert pk.can_pick(10)
    pk.add(11, (200, 200))
    assert not pk.can_pick(12)              # van toi da 2


def test_three_claims_in_a_row_never_allow_third_pickup():
    pk = IR.Pickups(cap=2, dur=90)
    pk.add(0, (174, 540))
    pk.add(1, (300, 300))
    for t in ((174, 576), (185, 447), (222, 533)):   # 3 tick live2 (chi 1 trung ghim hop 1)
        pk.done(t)
    assert len(pk.until) == 1 and pk.can_pick(5)
    pk.add(5, (50, 50))
    assert not pk.can_pick(6)


def test_done_without_pos_keeps_old_behaviour():
    pk = IR.Pickups(cap=2, dur=90)
    pk.add(0)
    pk.add(10)
    assert pk.done() and pk.can_pick(11)


def test_pickup_records_pin_position(monkeypatch):
    ctx = types.SimpleNamespace(cfg={"notify": {}}, _intel_pin=(222, 498))
    monkeypatch.setattr(notify, "_grey_pickup", lambda c: False)       # P13l: nut "Nhat" co mau (bam duoc)
    monkeypatch.setattr(notify, "confirm_departure", lambda c, b, ok="": "picked")
    assert notify.pickup(ctx) == "picked"
    assert ctx._intel_pickups.pos == [(222, 498)]


# ---------------------------------------------------------------- tinh bao tu ban do the gioi
class WCtx:
    def __init__(self, on_world=True):
        self.on_world, self.taps, self.cities = on_world, [], 0

    def find(self, name):
        return (35, 701, 0.97) if name == "campaign/btn_open" and (self.on_world or self.cities) else None

    def ensure_city(self):
        self.cities += 1

    def tap(self, x, y, wait=1.0):
        self.taps.append((x, y))


def test_open_intel_from_world_without_going_city():
    c = WCtx(on_world=True)
    assert notify.open_intel(c)
    assert c.cities == 0 and c.taps == [(33, 645)]


def test_open_intel_falls_back_to_city():
    c = WCtx(on_world=False)
    assert notify.open_intel(c) and c.cities == 1


def test_intel_run_does_not_force_city_first(monkeypatch):
    c = WCtx(on_world=True)
    c.cfg = {"notify": {}}
    monkeypatch.setattr(notify, "intel", lambda ctx, n: 1)
    monkeypatch.setattr(notify, "leave", lambda ctx: None)
    assert intel.run(c) == 1
    assert c.cities == 1                    # chi lan ve thanh pho CUOI buoc (quy uoc), khong truoc khi vao


def test_world_icon_matches_template():
    v = Vision("templates", 0.82)
    for rel in ("live2/auto/s110646.png", "live2-feedback/tinh_bao_tu_world_map.png"):
        img = _img(rel)
        if img.shape[:2] != (960, 540):
            img = cv2.resize(img, (540, 960))
        hit = v.find(img, "campaign/btn_open")
        assert hit and abs(hit[0] - 35) <= 5 and abs(hit[1] - 701) <= 5


# ---------------------------------------------------------------- nha chinh da skin
def _tpls():
    out = [cv2.imread(f"templates/build/{n}.png") for n in ("hq_emblem_a", "hq_emblem_b", "hq_emblem_halloween")]
    if out[2] is None:
        pytest.skip("thieu templates/build/hq_emblem_halloween.png")
    return out


def test_halloween_skin_found_and_tap_on_building():
    tpls = _tpls()
    dys = [0, 0, upgrade.TAP_DY["build/hq_emblem_halloween"]]
    hit = upgrade.find_hq(_img("live2/00-before.png"), tpls, dys=dys)
    assert hit and abs(hit[0] - 270) <= 6
    assert 420 <= hit[1] + 35 <= 470        # _try_open cham y+35 -> giua san nha chinh (khong phai bong bong 270,510)
    phone = _img("live2-feedback/nha_chinh_mau_moi_halloween.png")
    assert upgrade.find_hq(phone, tpls, dys=dys)


def test_halloween_template_not_on_world_map():
    assert upgrade.find_hq(_img("live2/auto/s110646.png"), _tpls()) is None


def test_goto_hq_falls_back_to_position_and_label(monkeypatch):
    """Skin moi chua co mau: cham vi tri giua man (HQ_TAP) + kiem nhan 'Xuong kien truc' (khong phu thuoc skin)."""
    opened = []
    monkeypatch.setattr(upgrade, "_names", lambda ctx: ["build/hq_emblem_a"])
    monkeypatch.setattr(upgrade, "_templates", lambda ctx: [object()])
    monkeypatch.setattr(upgrade, "find_hq", lambda img, t, th=0, dys=None: None)
    monkeypatch.setattr(upgrade, "_try_open", lambda ctx, hit: opened.append(hit) or (300, 600))
    ctx = types.SimpleNamespace(world_ready=lambda: False, ensure_city=lambda: None, settle=lambda: None,
                               cfg={"build": {"recenter_world": False}})
    assert upgrade.goto_hq(ctx) == (300, 600)
    assert opened and opened[0][0] == upgrade.HQ_TAP[0] and opened[0][1] + 35 == upgrade.HQ_TAP[1]


def test_hq_below_15_never_joins_mech_rally_regardless_of_skin():
    mem = types.SimpleNamespace(fact=lambda idx, k: 14)
    assert not rebels.join_hq_ok(mem, 1, {"min_hq_level": 15})
    assert not rebels.join_hq_ok(types.SimpleNamespace(fact=lambda i, k: None), 1, {})
    assert rebels.join_hq_ok(types.SimpleNamespace(fact=lambda i, k: 30), 1, {})


# ---------------------------------------------------------------- OCR thanh nhiem vu chinh
def test_clean_text():
    assert mainquest.clean_text("} Co the nhan Ruong moi ngay :") == "Co the nhan Ruong moi ngay"
    assert mainquest.clean_text("| Tang Xuong kien truc den cap 6 \u2018") == "Tang Xuong kien truc den cap 6"
    assert mainquest.clean_text(" . : ") == ""


@pytest.mark.parametrize("rel", ["live2/auto/s111038.png", "live2/00-before.png", "p8-adb/cityend.png"])
def test_text_extent_stops_before_city_background(rel):
    e = mainquest.text_extent(_img(rel))
    assert e is not None and e[0] == 52 and 180 <= e[2] <= 230     # chu "Co the nhan Ruong moi ngay" ~ x 52-250


@pytest.mark.parametrize("rel", ["live2/auto/s111038.png", "live2/auto/s111029.png"])
def test_live2_banner_no_garbage(rel):
    """live2 11:10:39 doc '} C6 the nhan Ruong moi ngay : 8. S. N | P Cothenhan Ruongpd' -> nay sach, loai 'chest'."""
    img = _img(rel)
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    t = mainquest.read_banner(None, img)
    assert "}" not in t and "8." not in t
    for part in t.split(" | "):
        assert len(part) <= 34
    assert quest_rules.classify(t)[0] == "chest"


def test_banner_clean_frame_still_reads_building_quest():
    p = "logs/human/20261121/001219-i0-ngoai_buoc-002_before.png"
    if not os.path.exists(p):
        pytest.skip("thieu anh")
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    t = mainquest.read_banner(None, cv2.imread(p))
    assert "Xu" in t and quest_rules.classify(t)[0] == "build"
