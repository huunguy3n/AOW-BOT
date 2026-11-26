"""P13j (chu du an 26/11/2026): "tinh bao dang bam hut lien tuc".
(1) sau "Di" trong thanh pho: bam VAT trong o sang xanh la (xe tang / hom), khong bam linh, khong bam bong bong;
(2) het quan doan ranh -> dung buoc Tinh bao cho het luot ghe may.

Anh: tests/fixtures/p13j/ = dung 2 anh chu du an gui (co khung do khoanh tay quanh cho PHAI bam).
  anh 1: crop 544x632, khung 540x960 = crop + (-5, +230) (do bang icon Chien dich / Chieu mo / Thu / bua);
  anh 2: crop phong to 327x380 cung ti le, vi tri trong khung khong biet -> test 2 vi tri dat.
Ca 2 crop mat thanh nut duoi -> dan them anh mau nut 'ban do' vao dung cho cua no (khung that luon co)."""
import types

import cv2
import numpy as np
import pytest

from bot import guide_tile, tapguard
from bot import intel_rules as IR
from bot.modules import intel, notify, reddots, tutorial
from bot.vision import Vision

TANK = "tests/fixtures/p13j/intel_miss_1_tank.png"
CRATE = "tests/fixtures/p13j/intel_miss_2_crate.png"
AT1 = (-5, 230)
AT2 = (234, 286)                       # cung goc may voi anh 1 (khop thung cam)
WORLD_SPOTS = [(268, 405), (268, 438), (265, 365)]
# (x0, y0, x1, y1) theo toa do CROP, do tren anh phong to
SOLDIER = {TANK: (245, 135, 320, 250), CRATE: (110, 150, 165, 235)}
BUBBLE = {TANK: (415, 225, 492, 292), CRATE: (177, 170, 236, 233)}
V = Vision("templates", 0.82)


def _read(path):
    img = cv2.imread(path)
    assert img is not None, path
    return img


def _red_box(crop):
    """Khung do chu du an khoanh -> (x0, y0, x1, y1) theo toa do crop."""
    b, g, r = (crop[..., i].astype(int) for i in range(3))
    m = ((r > 200) & (g < 50) & (b < 50)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    boxes = [st[k] for k in range(1, n) if st[k][2] > 30 and st[k][3] > 30]
    assert len(boxes) == 1
    x, y, w, h = boxes[0][:4]
    return int(x), int(y), int(x + w), int(y + h)


def _frame(crop=None, at=(0, 0), city=True):
    f = np.zeros((960, 540, 3), np.uint8)
    if crop is not None:
        ox, oy = at
        h, w = crop.shape[:2]
        x0, y0, x1, y1 = max(0, ox), max(0, oy), min(540, ox + w), min(960, oy + h)
        f[y0:y1, x0:x1] = crop[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    if city:
        t = _read("templates/common/btn_to_world.png")
        h, w = t.shape[:2]
        f[919 - h // 2:919 - h // 2 + h, 57 - w // 2:57 - w // 2 + w] = t
    return f


def _inside(p, box, at):
    return box[0] + at[0] <= p[0] <= box[2] + at[0] and box[1] + at[1] <= p[1] <= box[3] + at[1]


def _check_point(path, p, at):
    assert _inside(p, _red_box(_read(path)), at), f"{p} ngoai khung do"
    assert not _inside(p, SOLDIER[path], at), f"{p} trung linh"
    assert not _inside(p, BUBBLE[path], at), f"{p} trung bong bong"


# ---------------------------------------------------------------- nhan dien
def test_image1_offset_matches_hud():
    p = V.find(_frame(_read(TANK), AT1), "campaign/btn_open")
    assert p and abs(p[0] - 35) <= 3 and abs(p[1] - 701) <= 3


def test_tank_tap_inside_red_box():
    g = guide_tile.find(V, _frame(_read(TANK), AT1))
    assert g and g.kind == "beam"
    _check_point(TANK, g, AT1)


@pytest.mark.parametrize("at", [AT2, (100, 250), (40, 420)])
def test_crate_tap_inside_red_box_not_bubble(at):
    g = guide_tile.find(V, _frame(_read(CRATE), at))
    assert g and g.kind == "hand"
    _check_point(CRATE, g, at)


@pytest.mark.parametrize("scale", [0.9, 1.15])
def test_multi_scale(scale):
    for path, at in ((TANK, AT1), (CRATE, (80, 250))):
        crop = cv2.resize(_read(path), None, fx=scale, fy=scale)
        at_ = (-5, 200) if path == TANK else at
        g = guide_tile.find(V, _frame(crop, at_))
        assert g, (path, scale)
        box = tuple(int(v * scale) for v in _red_box(_read(path)))
        assert _inside(g, box, at_), (path, scale, g, box)


@pytest.mark.parametrize("path,at", [(TANK, AT1), (CRATE, AT2)])
def test_result_does_not_depend_on_red_annotation(path, at):
    crop = _read(path)
    x0, y0, x1, y1 = _red_box(crop)
    mask = np.zeros(crop.shape[:2], np.uint8)
    cv2.rectangle(mask, (x0 + 1, y0 + 1), (x1 - 2, y1 - 2), 255, 9)
    clean = cv2.inpaint(crop, mask, 4, cv2.INPAINT_TELEA)
    a, b = guide_tile.find(V, _frame(crop, at)), guide_tile.find(V, _frame(clean, at))
    assert a and b and abs(a.x - b.x) <= 8 and abs(a.y - b.y) <= 8


def test_hand_template_has_no_red_and_finger_tip():
    t = _read("templates/intel/point_hand.png")
    b, g, r = (t[..., i].astype(int) for i in range(3))
    assert not ((r > 200) & (g < 50) & (b < 50)).any()
    hand = guide_tile.find_hand(V, _frame(_read(CRATE), (0, 200)))
    assert hand and abs(hand[0] - 215) <= 5 and abs(hand[1] - 361) <= 5
    assert guide_tile.find_hand(V, _frame(_read(TANK), AT1)) is None


def test_no_guide_without_lit_tile_and_beam_needs_city():
    assert guide_tile.find(V, _frame()) is None
    assert guide_tile.find(V, _read("tests/fixtures/p13i/wrench_city.png")) is None
    assert guide_tile.find(V, _frame(_read(TANK), AT1, city=False)) is None   # cot sang khong tay: chi trong thanh
    f = _frame(_read(TANK), AT1)
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    f[(hsv[..., 0] >= 25) & (hsv[..., 0] <= 90) & (hsv[..., 1] >= 120) & (hsv[..., 2] >= 150)] = 0
    assert guide_tile.find(V, f) is None               # con o xanh LAM cua linh -> khong phai muc tieu


def test_blocked_point_is_skipped():
    f = _frame(_read(TANK), AT1)
    g = guide_tile.find(V, f)
    guard = tapguard.TapGuard()
    guard.ban("guide", g.x + 4, g.y - 3, "thu")
    assert guide_tile.find(V, f, lambda x, y: guard.blocked("guide", x, y)) is None


# ---------------------------------------------------------------- follow / runner
@pytest.mark.parametrize("path,at", [(TANK, AT1), (CRATE, AT2)])
def test_follow_decide_taps_object(path, at):
    f = _frame(_read(path), at)
    act, x, y, why = tutorial.decide(V, f, state={"follow": True})
    assert act == "tap" and why.startswith(guide_tile.WHY)
    _check_point(path, (x, y), at)
    assert tutorial.guide_visible(V, f).startswith(guide_tile.WHY)
    assert tutorial.guide_visible(V, f, lambda x, y: True) is None
    assert not tutorial.decide(V, f, state={})[3].startswith(guide_tile.WHY)    # tan thu: luat cu giu nguyen


# ---------------------------------------------------------------- sau "Di"
class Ctx:
    """Man hinh that (anh) + chuoi man: bam trung khung do cua man hien tai -> man ke."""
    def __init__(self, screens):
        self.screens, self.i = screens, 0          # [(frame, hop do | None)]
        self.v, self.taps, self.backs, self.cfg = V, [], 0, {"notify": {}, "rebels": {}}
        self.dev = types.SimpleNamespace(idx=1)
        self.POPUP_CLOSERS = []
        self.tap_guard = tapguard.TapGuard()

    def shot(self):
        return self.screens[self.i][0]

    def find(self, name, fresh=True, **k):
        return V.find(self.shot(), name, **k)

    def tap(self, x, y, wait=1.0, tpl=None):
        self.taps.append((x, y))
        box = self.screens[self.i][1]
        if box and _inside((x, y), box[0], box[1]):
            self.i += 1

    def tap_tpl(self, name, **k):
        if name == "intel/btn_go":
            return True
        p = self.find(name)
        if p:
            self.taps.append(name)
        return bool(p)

    def wait_for(self, name, **k):
        return self.find(name)

    def back_out(self, *a):
        self.backs += 1

    def dismiss_reward(self):
        pass


@pytest.fixture
def mission(monkeypatch):
    monkeypatch.setattr(guide_tile.time, "sleep", lambda s: None)
    monkeypatch.setattr(notify.time, "sleep", lambda s: None)
    monkeypatch.setattr(notify, "wait_panel", lambda ctx: "go")
    caps = []
    monkeypatch.setattr("bot.build.inv_capture", lambda ctx, tag: caps.append(tag))
    return caps


def test_after_go_taps_tank_then_crate_never_world_spots(mission):
    ctx = Ctx([(_frame(_read(TANK), AT1), (_red_box(_read(TANK)), AT1)),
               (_frame(_read(CRATE), AT2), (_red_box(_read(CRATE)), AT2)),
               (_frame(), None)])
    assert notify.intel_mission(ctx) == IR.GUIDED
    assert len(ctx.taps) == 2 and mission == [] and ctx.backs == 0
    _check_point(TANK, ctx.taps[0], AT1)
    _check_point(CRATE, ctx.taps[1], AT2)
    assert not set(ctx.taps) & set(WORLD_SPOTS)
    assert IR.GUIDED in IR.SKIP


def test_tap_without_change_is_blacklisted_and_not_repeated(mission):
    f = _frame(_read(TANK), AT1)
    ctx = Ctx([(f, None)])                       # man khong doi du bam
    assert notify.intel_mission(ctx) == IR.UNKNOWN_TARGET
    assert len(ctx.taps) == 1 and ctx.tap_guard.blocked("guide", *ctx.taps[0])
    assert notify.intel_mission(ctx) == IR.UNKNOWN_TARGET
    assert len(ctx.taps) == 1                    # khong bam lai, khong roi sang toa do ban do the gioi


def test_guide_reappearing_at_same_spot_is_banned_after_two_taps(mission, monkeypatch):
    results = []
    monkeypatch.setattr(guide_tile, "tap_and_check",
                        lambda ctx, hit: results.append((hit.x, hit.y)) or "changed")   # nhap nhay: tuong da doi
    ctx = Ctx([(_frame(_read(TANK), AT1), None)])
    assert guide_tile.follow_city(ctx) == "miss"
    assert len(results) == 2 and ctx.tap_guard.blocked("guide", *results[0])


def test_ban_covers_neighbourhood_only():
    g = tapguard.TapGuard()
    g.ban("guide", 360, 498, "thu")
    assert g.blocked("guide", 389, 470) and not g.blocked("guide", 450, 532)
    assert not g.blocked("tap", 360, 498) and len(g.summary()) == 1


def test_city_without_guide_does_not_use_world_spots(mission):
    ctx = Ctx([(_frame(), None)])
    assert notify.intel_mission(ctx) == IR.UNKNOWN_TARGET and ctx.taps == []


def test_world_map_keeps_old_logic(mission):
    ctx = Ctx([(_frame(city=False), None)])
    assert guide_tile.follow_city(ctx) is None
    notify.intel_mission(ctx)
    assert ctx.taps == WORLD_SPOTS


# ---------------------------------------------------------------- het quan doan ranh
class Visit:
    def __init__(self):
        self.cfg = {"notify": {"intel_max": 6}, "modules": {"notify": False, "intel": True}}
        self.dev = types.SimpleNamespace(idx=1)
        self.v = types.SimpleNamespace(find_all=lambda *a, **k: [(100, 300, 0.9), (300, 500, 0.9)],
                                       find=lambda *a, **k: None, has=lambda n: False)
        self.touched, self.pins = [], []
        self.POPUP_CLOSERS = []

    def find(self, name, **k):
        self.touched.append(("find", name))
        return (1, 1) if name in ("intel/title", "campaign/btn_open") else None

    def shot(self):
        self.touched.append(("shot",))
        return np.zeros((960, 540, 3), np.uint8)

    def tap(self, x, y, **k):
        self.pins.append((x, y))

    def ensure_city(self):
        self.touched.append(("city",))

    def close_popups(self, *a, **k):
        pass

    def is_home(self):
        return True

    def save_debug(self, tag):
        pass


def test_no_march_stops_intel_for_whole_visit(monkeypatch):
    ctx, results = Visit(), iter(["marched", "no_march", "win", "win"])
    monkeypatch.setattr(notify, "done_ticks", lambda img: [])
    monkeypatch.setattr(notify, "energy", lambda c: 99)
    monkeypatch.setattr(notify, "intel_mission", lambda c: next(results))
    monkeypatch.setattr(notify.time, "sleep", lambda s: None)
    assert notify.intel(ctx, 6) == 1
    assert len(ctx.pins) == 2 and ctx.intel_stop == "no_march"       # khong chon ghim sau no_march, khong quet lai
    ctx.touched.clear()
    assert notify.intel(ctx, 6) == 0 and intel.run(ctx) == 0
    assert ctx.touched == [] and len(ctx.pins) == 2                  # khong chup, khong cham, khong ve thanh pho
    assert notify.intel_stopped(Visit()) is None                     # luot ghe sau (ctx moi) lam binh thuong


@pytest.mark.parametrize("result", ["lose", "skipped", "unknown_target"])
def test_other_results_do_not_stop_the_visit(monkeypatch, result):
    ctx = Visit()
    monkeypatch.setattr(notify, "done_ticks", lambda img: [])
    monkeypatch.setattr(notify, "energy", lambda c: 99)
    monkeypatch.setattr(notify, "intel_mission", lambda c: result)
    notify.intel(ctx, 1)
    assert notify.intel_stopped(ctx) is None


def test_notify_run_does_not_open_intel_after_stop(monkeypatch):
    ctx = Visit()
    ctx.cfg = {"notify": {"welfare": False, "events": False}, "modules": {"intel": False}}
    ctx.intel_stop = "no_march"
    monkeypatch.setattr(notify, "badged", lambda c: [("intel", (64, 650, 0.9))])
    monkeypatch.setattr(notify, "intel", lambda c, n: pytest.fail("goi lai tinh bao"))
    assert notify.run(ctx) == {} and ctx.pins == []


@pytest.mark.parametrize("stop,calls", [("no_march", 0), (None, 1)])
def test_reddots_skips_intel_dot_after_stop(monkeypatch, stop, calls):
    ctx, handled, saved = Visit(), [], []
    ctx.intel_stop = stop
    ctx.save_debug = saved.append
    monkeypatch.setattr(reddots, "_left", lambda img, v=None: [(64, 629)])
    monkeypatch.setattr(reddots, "_kind", lambda c, img, d: "intel")
    monkeypatch.setattr(reddots, "_handle", lambda c, kind, x, y: handled.append(kind) or 0)
    monkeypatch.setattr(reddots, "_keep_last", lambda c, img: None)
    monkeypatch.setattr(reddots.chat, "clear", lambda c: None)
    reddots.run(ctx)
    assert len(handled) == calls
    if stop:
        assert saved == []                    # co y bo qua -> khong tinh la cham do con sot
