"""P13i (chu du an t96u 26/11/2026): bong bong tron vang CO LE tren cong trinh = nang duoc ngay -> bam truoc tien.
Anh: tests/fixtures/p13i/wrench_city.png = dung anh chu du an gui (crop 542x674 tu mep tren khung 540x960, co khung do
khoanh tay quanh bong bong co le; 2 bong bong ban tay la THU TAI NGUYEN)."""
import time
import types

import cv2
import numpy as np
import pytest

from bot import build, hqplan, tapguard, wrench
from bot.memory import Memory
from bot.modules import construct, upgrade
from bot.vision import Vision

CITY = "tests/fixtures/p13i/wrench_city.png"
WRENCH_AT = (92, 283)                      # tam vong tron (khung do cua chu: x 61-127, y 253-315)
HARVEST = ((207, 237), (437, 352))         # bong bong thu tai nguyen


def _city():
    img = cv2.imread(CITY)
    assert img is not None, CITY
    return img


def _tpl():
    t = cv2.imread("templates/build/wrench_bubble.png")
    assert t is not None
    return t


def _near(p, q, tol=6):
    return abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol


def _bubble_patch(img, at, r=22):
    x, y = at
    return img[y - r:y + r, x - r:x + r].copy()


def _paste(img, patch, at):
    h, w = patch.shape[:2]
    x, y = at[0] - w // 2, at[1] - h // 2
    img[y:y + h, x:x + w] = patch
    return img


def _grass(img):
    """Khung 540x960 toan co (cat tu anh that), de dat bong bong vao cho tuy y."""
    patch = img[500:560, 200:260]
    return np.tile(patch, (16, 9, 1))[:960, :540].copy()


# ---------------------------------------------------------------- nhan dien
def test_template_is_tight_and_has_no_red_annotation():
    t = _tpl()
    assert 32 <= t.shape[0] <= 40 and 32 <= t.shape[1] <= 40
    hsv = cv2.cvtColor(t, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, (0, 200, 180), (6, 255, 255)) | cv2.inRange(hsv, (172, 200, 180), (180, 255, 255))
    assert int((red > 0).sum()) == 0


def test_finds_exactly_the_wrench_on_owner_screenshot():
    found = wrench.find_bubbles(_city(), _tpl())
    assert len(found) == 1 and _near(found[0], WRENCH_AT), found


def test_harvest_bubbles_are_not_wrench():
    img, tpl = _city(), _tpl()
    found = wrench.find_bubbles(img, tpl, block=())            # ke ca khi khong loc vung HUD
    assert not any(_near(f, h, 20) for f in found for h in HARVEST)
    for h in HARVEST:                                          # tung bong bong thu hoach, o cac goc lac va ti le
        for angle in (-30, -20, -10, 0, 10, 20, 30):
            for scale in (0.9, 1.0, 1.2):
                patch = _bubble_patch(img, h)
                m = cv2.getRotationMatrix2D((22, 22), angle, scale)
                patch = cv2.warpAffine(patch, m, (44, 44), borderMode=cv2.BORDER_REPLICATE)
                assert wrench.find_bubbles(_paste(_grass(img), patch, (270, 400)), tpl) == [], (h, angle, scale)


@pytest.mark.parametrize("scale", [0.9, 1.1, 1.3])
def test_wrench_found_when_camera_zoomed(scale):
    img = cv2.resize(_city(), None, fx=scale, fy=scale)
    found = wrench.find_bubbles(img, _tpl(), block=())
    assert len(found) == 1 and _near(found[0], (WRENCH_AT[0] * scale, WRENCH_AT[1] * scale), 8), found


@pytest.mark.parametrize("at", [(270, 450), (430, 640), (130, 760)])
def test_wrench_found_anywhere_when_city_scrolled(at):
    img = _city()
    frame = _paste(_grass(img), _bubble_patch(img, WRENCH_AT, 19), at)
    found = wrench.find_bubbles(frame, _tpl())
    assert len(found) == 1 and _near(found[0], at), found


@pytest.mark.parametrize("angle", [-25, -15, -8])
def test_wrench_found_while_wobbling(angle):
    img = _city()
    patch = _bubble_patch(img, WRENCH_AT)
    m = cv2.getRotationMatrix2D((22, 22), angle, 1.0)
    patch = cv2.warpAffine(patch, m, (44, 44), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    found = wrench.find_bubbles(_paste(_grass(img), patch, (270, 400)), _tpl())
    assert len(found) == 1 and _near(found[0], (270, 400)), found


def test_no_bubble_no_hit_and_hud_blocked():
    img, tpl = _city(), _tpl()
    patch = _bubble_patch(img, WRENCH_AT, 19)
    for hud in ((35, 135), (470, 810), (270, 40), (270, 920)):   # icon tho xay, bua goc phai duoi, thanh tren / duoi
        assert wrench.find_bubbles(_paste(_grass(img), patch, hud), tpl) == [], hud
    assert wrench.find_bubbles(_grass(img), tpl) == []
    assert wrench.find_bubbles(img, None) == []


def test_hq_bubble_ordered_first():
    hq = (110, 390, 0.9)
    assert wrench.above_hq(WRENCH_AT, hq)
    assert not wrench.above_hq((400, 300), hq) and not wrench.above_hq((110, 480), hq)
    got = wrench.ordered([(400, 600, 0.95), (92, 283, 0.6)], hq)
    assert [(b[0], b[3]) for b in got] == [(92, True), (400, False)]
    got = wrench.ordered([(400, 600, 0.95), (92, 283, 0.6)], None)          # khong biet nha chinh: theo diem
    assert [(b[0], b[3]) for b in got] == [(400, False), (92, False)]


# ---------------------------------------------------------------- luong bam
class Ctx:
    def __init__(self, tmp_path, img, busy=0, maxb=1, modules=None):
        self.cfg = {"build": {"max_builders": maxb, "chain_max": 6, "quick_s": 0, "hq_max_level": 30,
                              "probe_plot_lock": False, "other_when_blocked": False},
                    "modules": modules or {"upgrade": True}}
        self.dev, self.v = types.SimpleNamespace(idx=2), Vision("templates")
        self.mem = Memory(str(tmp_path / "m.db"))
        self.tap_guard = tapguard.TapGuard()
        self.img, self.busy, self.taps = img, busy, []

    def settle(self, *a, **k):
        return self.img

    def shot(self):
        return self.img

    def tap(self, x, y, wait=1.0, tpl=None):
        self.taps.append((x, y))

    def ensure_city(self):
        pass

    def back_out(self, *a):
        pass


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Tho: ctx.busy / 2; upgrade_here tra lan luot `results` ('started' thi them 1 tho ban)."""
    def make(results, img=None, **kw):
        ctx = Ctx(tmp_path, _city() if img is None else img, **kw)
        seq = iter(results)

        def here(c, *a, **k):
            r = next(seq)
            if r == "started":
                c.busy += 1
            return r

        monkeypatch.setattr(build, "builders", lambda c, img=None: (c.busy, 2))
        monkeypatch.setattr(build, "upgrade_here", here)
        monkeypatch.setattr(build, "free_speedup", lambda c: 0)
        monkeypatch.setattr(upgrade, "recenter_hq", lambda c: False)
        return ctx
    return make


def test_taps_bubble_then_upgrades_one_builder_farm(env):
    ctx = env(["started"])
    assert upgrade.wrench_upgrades(ctx) == (1, "started")
    assert len(ctx.taps) == 1 and _near(ctx.taps[0], WRENCH_AT)


@pytest.mark.parametrize("busy,maxb", [(1, 1), (2, 2)])
def test_no_tap_when_usable_builders_busy(env, busy, maxb):
    ctx = env([], busy=busy, maxb=maxb)                     # farm 1/2 = DAY du UI ghi 2 o
    assert upgrade.wrench_upgrades(ctx) == (0, None) and ctx.taps == []


def test_second_builder_of_main_account_used(env):
    ctx = env(["started"], busy=1, maxb=2)
    assert upgrade.wrench_upgrades(ctx) == (1, "started")


def test_tap_that_opens_nothing_is_blacklisted(env):
    ctx = env(["none", "none"])
    assert upgrade.wrench_upgrades(ctx) == (0, "none") and len(ctx.taps) == 1
    assert ctx.tap_guard.blocked("wrench", *ctx.taps[0])
    assert upgrade.wrench_upgrades(ctx) == (0, None) and len(ctx.taps) == 1      # khong bam lai trong lan ghe


def test_blocked_bubble_not_retapped_in_same_call_and_two_strikes(env):
    ctx = env(["blocked", "blocked", "blocked"])
    assert upgrade.wrench_upgrades(ctx) == (0, "blocked") and len(ctx.taps) == 1
    assert upgrade.wrench_upgrades(ctx) == (0, "blocked") and len(ctx.taps) == 2
    assert upgrade.wrench_upgrades(ctx) == (0, None) and len(ctx.taps) == 2


def test_config_switch_off(env):
    ctx = env([])
    ctx.cfg["build"]["wrench"] = False
    assert upgrade.wrench_upgrades(ctx) == (0, None) and ctx.taps == []


def test_hq_bubble_tapped_first_and_plan_saved(env, monkeypatch):
    img = _city()
    two = _paste(_grass(img), _bubble_patch(img, WRENCH_AT, 19), (400, 330))
    two = _paste(two, _bubble_patch(img, WRENCH_AT, 19), (150, 500))
    ctx = env(["started"], img=two)
    monkeypatch.setattr(upgrade, "_hq_hit", lambda c, i: (165, 610, 0.9))
    upgrade.wrench_upgrades(ctx)
    assert len(ctx.taps) == 1 and _near(ctx.taps[0], (150, 500))
    assert hqplan.load(ctx).status.value == "chain"


def test_recenters_once_when_hq_not_on_screen(env, monkeypatch):
    ctx = env(["started"])
    trips = []
    monkeypatch.setattr(upgrade, "_hq_hit", lambda c, i: None)
    monkeypatch.setattr(upgrade, "recenter_hq", lambda c: trips.append(1) or True)
    assert upgrade.wrench_upgrades(ctx, recenter=True)[0] == 1 and trips == [1]


def test_upgrade_run_uses_bubble_before_hq_search(env, monkeypatch):
    ctx = env(["started"])
    monkeypatch.setattr(upgrade, "goto_hq", lambda *a, **k: pytest.fail("bong bong co le truoc"))
    monkeypatch.setattr(upgrade, "other_buildings", lambda c: pytest.fail("tho da ban"))
    assert upgrade.run(ctx) == 1


def test_upgrade_run_falls_back_to_hq_without_bubble(env, monkeypatch):
    ctx = env([], img=_grass(_city()))
    seen = []
    monkeypatch.setattr(upgrade, "goto_hq", lambda *a, **k: seen.append(1))
    assert upgrade.run(ctx) == 0 and seen == [1] and ctx.taps == []


def test_hq_chain_tries_bubble_again_before_next_hq_search(env, monkeypatch):
    ctx = env(["started", "started"], img=_grass(_city()), busy=0, maxb=2)
    searches = []

    def goto(c, again=False):
        searches.append(1)
        c.img = _city()                       # sau cong trinh dau, bong bong co le hien ra
        return (317, 557, 0.9)

    monkeypatch.setattr(upgrade, "goto_hq", goto)
    monkeypatch.setattr(build, "quick_wait", lambda c: c.busy < 2)
    assert upgrade.hq_chain(ctx) == (2, "started") and searches == [1]
    assert _near(ctx.taps[-1], WRENCH_AT)


@pytest.mark.parametrize("upgrade_on,calls", [(True, 1), (False, 0)])
def test_construct_tries_bubble_first(env, monkeypatch, upgrade_on, calls):
    ctx = env([], modules={"upgrade": upgrade_on})
    seen = []
    monkeypatch.setattr(construct, "roads", lambda c: 0)
    monkeypatch.setattr(upgrade, "wrench_upgrades", lambda c, **k: (seen.append(1), setattr(c, "busy", 1), (1, "x"))[2])
    monkeypatch.setattr(construct, "block_until", lambda c: time.time() + 60)   # dung ngay sau buoc bong bong
    assert construct.run(ctx) == calls and len(seen) == calls
