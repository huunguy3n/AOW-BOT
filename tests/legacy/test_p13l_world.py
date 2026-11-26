"""P13l (chu du an t100u-t105u): mui ten xanh -> bam dung phien quan; KHONG BAO GIO bam can cu nguoi choi.

Anh: tests/fixtures/p13l/arrow_miss_world.png (340x314: menu dat trong, o do chu khoanh = diem bot da bam hut) va
world_tap_player_city.png (486x469: menu can cu nguoi choi, co dau X do chu ve)."""
import types

import cv2
import numpy as np
import pytest

from bot import ctx as ctxmod
from bot import map_menu as M
from bot import tapguard
from bot import world_target as W
from bot.modules import arrow, gather, notify, rebels, tutorial
from bot.vision import Vision

D = "tests/fixtures/p13l/"
V = Vision("templates", 0.82)

RED_BOX = (145, 118, 185, 158)                    # o dat trong bot da bam hut
LAND_BUTTONS = ((50, 153), (260, 153))            # "Chuyen thanh", "Chiem linh"
MECH = (82, 155, 175, 265)                        # con phien quan (than + huy hieu cap + thanh mau)
CITY_BUTTONS = {"menu_scout": (167, 183), "menu_rally": (336, 181), "menu_news": (148, 266),
                "menu_attack": (356, 266)}        # Trinh sat, Tap ket, Tin tuc, Tan cong


def _img(name):
    img = cv2.imread(D + name + ".png")
    assert img is not None, name
    return img


def arrow_img():
    return _img("arrow_miss_world")


def city_img():
    return _img("world_tap_player_city")


def no_menu():
    """Anh mui ten sau khi menu dong: to nen co len 2 nut vong tron."""
    img = arrow_img()
    for x, y in LAND_BUTTONS:
        img[y - 32:y + 40, max(0, x - 45):x + 45] = img[60:132, 195:285][:, :x + 45 - max(0, x - 45)]
    return img


def _in(p, box):
    return box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]


def _far(p, spots, r=40):
    return all(abs(p[0] - x) > r or abs(p[1] - y) > r for x, y in spots)


def _safe_unit_point(p):
    assert _in(p, MECH), p
    assert not _in(p, RED_BOX), p
    assert _far(p, LAND_BUTTONS), p


# ---------- mui ten xanh ----------
def test_arrow_found_although_near_the_top():
    ax, ay = W.find_green_chevron(arrow_img())
    assert abs(ax - 155) <= 5 and 105 <= ay <= 125          # y < 110 cu bi xoa
    assert tutorial.find_green_chevron is W.find_green_chevron


def test_tap_point_is_the_rebel_not_the_empty_tile():
    for img in (arrow_img(), no_menu()):
        t = W.pick(img, V)
        assert t and t.kind == "unit"
        _safe_unit_point((t.x, t.y))


def test_blacklisted_point_is_not_picked_again():
    first = W.pick(no_menu(), V)
    other = W.pick(no_menu(), V, blocked=lambda x, y: (x, y) == (first.x, first.y))
    assert other is None or (other.x, other.y) != (first.x, first.y)


def test_nothing_to_tap_in_city_or_without_arrow():
    img = np.full((960, 540, 3), (60, 140, 90), np.uint8)
    assert W.pick(img, V) is None
    city = no_menu()
    city = cv2.copyMakeBorder(city, 0, 400, 0, 200, cv2.BORDER_REPLICATE)
    t = V.load("common/btn_to_world")
    city[600:600 + t.shape[0], 20:20 + t.shape[1]] = t
    assert W.pick(city, V) is None


def test_land_menu_is_a_miss():
    assert M.classify(arrow_img(), V) == "land"
    assert M.classify(no_menu(), V) is None
    assert tutorial.decide(V, arrow_img())[0] == "mapmenu"


def test_follow_decides_target_and_stays_on_world():
    act, x, y, why = tutorial.decide(V, no_menu(), state={"follow": True})
    assert act == "target" and why.startswith(tutorial.ARROW_WHY)
    _safe_unit_point((x, y))
    assert tutorial.guide_visible(V, no_menu())
    assert tutorial.guide_visible(V, arrow_img()) is None


# ---------- can cu nguoi choi ----------
def test_player_city_menu_recognised():
    assert M.classify(city_img(), V) == "city"
    found = M.find_buttons(city_img(), V)
    for name, (x, y) in CITY_BUTTONS.items():
        assert abs(found[name][0] - x) <= 6 and abs(found[name][1] - y) <= 6, name


@pytest.mark.parametrize("hidden", list(CITY_BUTTONS))
def test_player_city_menu_with_one_button_hidden(hidden):
    img = city_img()
    x, y = CITY_BUTTONS[hidden]
    img[y - 30:y + 30, x - 30:x + 30] = (60, 110, 140)
    assert M.classify(img, V) == "city"


def test_rectangular_attack_buttons_are_not_the_ring_menu():
    img = np.zeros((960, 540, 3), np.uint8)
    for k, n in enumerate(("rebels/npc_attack", "intel/btn_attack", "rebels/btn_rally")):
        t = V.load(n)
        img[300 + 90 * k:300 + 90 * k + t.shape[0], 150:150 + t.shape[1]] = t
    assert M.classify(img, V) is None


class Dev:
    idx = 0

    def __init__(self, frames):
        self.frames, self.taps, self.backs, self.act_seq = list(frames), [], 0, 0

    def screencap(self, tries=None):
        return self.frames[0]

    def tap(self, x, y):
        self.act_seq += 1
        self.taps.append((x, y))

    def back(self):
        self.act_seq += 1
        self.backs += 1
        if len(self.frames) > 1:
            self.frames.pop(0)


def _ctx(dev):
    return ctxmod.Ctx(dev, V, {"screen": {"width": 540, "height": 960}, "speed": {"wait_scale": 0}})


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(M.time, "sleep", lambda s: None)
    monkeypatch.setattr(ctxmod.time, "sleep", lambda s: None)


def _blank():
    return np.full((469, 486, 3), (60, 140, 90), np.uint8)


def test_dismiss_only_closes_and_logs(caplog):
    dev = Dev([city_img(), _blank()])
    c = _ctx(dev)
    c._last_tap = (243, 225, M.time.time())
    with caplog.at_level("INFO", logger="aow"):
        assert M.dismiss(c) == "city"
    assert dev.backs == 1 and dev.taps == []                  # chi Back, khong bam nut nao tren menu
    assert "tap trung can cu nguoi choi -> dong" in caplog.text
    assert M.blocked(c, 243, 225) and M.dismiss(c) is None


@pytest.mark.parametrize("name", list(CITY_BUTTONS))
def test_ctx_never_taps_a_city_menu_button(name):
    for how in ("tap", "tap_tpl", "tap_first"):
        dev = Dev([city_img(), _blank()])
        c = _ctx(dev)
        c.shot()
        if how == "tap":
            c.tap(*CITY_BUTTONS[name], wait=0)
        elif how == "tap_tpl":
            assert not c.tap_tpl(f"map/{name}", wait=0, fresh=False)
        else:
            assert c.tap_first([f"map/{name}"], wait=0, img=c._img) is None
        assert dev.taps == [] and dev.backs == 1, how


def test_menu_closed_right_after_the_tap_that_opened_it():
    dev = Dev([_blank()])
    c = _ctx(dev)
    c.shot()
    c.tap(243, 225, wait=0)
    dev.frames = [city_img(), _blank()]
    img = c.shot()                                            # khung dau sau cham: dong ngay
    assert dev.backs == 1 and M.classify(img, V) is None and dev.taps == [(243, 225)]
    assert c.last_menu == "city" and M.blocked(c, 243, 225)


def test_close_popups_closes_the_menu_with_back_only():
    dev = Dev([city_img(), _blank()])
    c = _ctx(dev)
    c.close_popups(2)
    assert dev.backs == 1 and dev.taps == []


def test_player_nameplates_are_excluded_but_rebels_are_not():
    img = city_img()
    assert len(W.flags(img)) == 7 and W.flags(arrow_img()) == []
    for p in ((250, 225), (60, 100), (150, 100), (60, 200), (240, 330), (440, 330)):
        assert W.city_near(img, *p, wide=True), p
    assert not W.city_near(img, 178, 29, wide=True)           # "3 Phien quan"
    assert W.TAG_RX.search("(LSB)Maxxx") and W.TAG_RX.search("> LSB)Nhuan")
    assert not W.TAG_RX.search("26 Phien quan")


def test_rebel_label_target_on_the_city_image():
    """Mui ten tren "3 Phien quan" (dan mui ten that vao): bam quan phien, khong bam thanh."""
    img = city_img()
    a = arrow_img()[84:120, 143:170]
    img = cv2.copyMakeBorder(img, 120, 0, 0, 0, cv2.BORDER_REPLICATE)
    img[62:98, 160:187] = a
    ax, ay = W.find_green_chevron(img)
    t = W.pick(img, V, (ax, ay))
    assert t and t.kind == "rebel" and abs(t.x - 178) <= 10 and 130 <= t.y <= 165, t


def test_intel_world_spots_skip_player_cities(monkeypatch):
    seen = []
    monkeypatch.setattr(notify.world_target, "city_near", lambda img, x, y, **k: seen.append((x, y)) or True)
    monkeypatch.setattr(notify.world_target, "blind_tap_ok", lambda img, v, x, y: seen.append((x, y)) or False)
    monkeypatch.setattr(notify.time, "sleep", lambda s: None)
    monkeypatch.setattr(notify.guide_tile, "follow_city", lambda ctx: None)
    monkeypatch.setattr(notify, "wait_panel", lambda ctx: "go")
    taps = []
    v = types.SimpleNamespace(find=lambda *a, **k: None)
    c = types.SimpleNamespace(v=v, cfg={}, shot=_blank, tap=lambda x, y, **k: taps.append((x, y)),
                              tap_tpl=lambda n, **k: n == "intel/btn_go", find=lambda *a, **k: None,
                              wait_for=lambda *a, **k: None, back_out=lambda *a: None, dev=types.SimpleNamespace(idx=0))
    monkeypatch.setattr(notify, "_intel_unknown", lambda ctx, why: why)
    assert notify.intel_mission(c) == "unknown_target"
    assert seen and taps == []


def test_real_frame_fixed_intel_spots_hit_a_player_base():
    """Log that 26/11 #1 (ADB 540x960): sau "Di" diem co dinh (268,405) mo menu can cu "(LSS)MF006"."""
    img = _img("world_city_menu_adb")
    assert M.classify(img, V) == "city"
    for spot in ((268, 405), (268, 438), (265, 365)):
        assert not W.blind_tap_ok(img, V, *spot), spot
    assert W.blind_tap_ok(np.zeros((960, 540, 3), np.uint8), V, 268, 405)     # khong phai ban do -> duoc


# ---------- lam tai cho ----------
class ArrowCtx(ctxmod.Ctx):
    def __init__(self, dev):
        super().__init__(dev, V, {"screen": {"width": 540, "height": 960}, "speed": {"wait_scale": 0}})

    def close_popups(self, *a, **k):
        pass


def test_engage_closes_miss_menu_then_taps_only_the_rebel(monkeypatch):
    dev = Dev([arrow_img(), no_menu()])
    c = ArrowCtx(dev)
    monkeypatch.setattr(arrow, "handle", lambda ctx, img: "sent")
    assert arrow.engage(c) == "sent"
    assert dev.backs == 1 and len(dev.taps) == 1
    _safe_unit_point(dev.taps[0])


def test_engage_is_bounded_when_nothing_opens(monkeypatch):
    dev = Dev([no_menu()])
    c = ArrowCtx(dev)
    monkeypatch.setattr(arrow, "handle", lambda ctx, img: None)
    assert arrow.engage(c) in ("miss", "none")
    assert 1 <= len(dev.taps) <= arrow.TRIES and len(set(dev.taps)) == len(dev.taps)
    assert all(_far(p, LAND_BUTTONS) and not _in(p, RED_BOX) for p in dev.taps)
    assert tapguard.of(c).blocked(M.SCOPE, *dev.taps[0])


def _mech_ctx(hq, full=False):
    closed = []
    mem = types.SimpleNamespace(fact=lambda i, k, d=None: hq if k == "hq_level" else None)
    c = types.SimpleNamespace(cfg={"rebels": {"min_hq_level": 15}}, mem=mem, dev=types.SimpleNamespace(idx=2),
                              march_full=lambda: full, POPUP_CLOSERS=[],
                              tap_first=lambda *a, **k: closed.append(1))
    return c, closed


@pytest.mark.parametrize("hq,full,want,rallies", [(8, False, "skip", 0), (None, False, "skip", 0),
                                                  (20, True, "skip", 0), (20, False, "sent", 1)])
def test_mech_rally_follows_rebel_rules(monkeypatch, hq, full, want, rallies):
    calls = []
    monkeypatch.setattr(rebels, "popup_target", lambda *a: calls.append(1) or 1)
    c, _ = _mech_ctx(hq, full)
    assert arrow._mech(c, None, (0, 0)) == want and len(calls) == rallies


def test_mine_goes_through_the_gather_flow(monkeypatch):
    runs = []
    monkeypatch.setattr(gather, "run", lambda ctx, limit=None: runs.append(limit) or 1)
    c = types.SimpleNamespace(cfg={"modules": {"gather": True}}, dev=types.SimpleNamespace(back=lambda: None),
                              wait_change=lambda *a: None, tap_tpl=lambda *a, **k: False, march_full=lambda: False)
    assert arrow._mine(c, None) == "sent" and runs == [1]
    c.march_full = lambda: True
    assert arrow._mine(c, None) == "skip" and runs == [1]
