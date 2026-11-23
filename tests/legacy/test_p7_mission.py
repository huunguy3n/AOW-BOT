"""P7-7 (chu du an 2026-11-24): su kien "Su menh" - CHI tab Nhiem vu hang ngay + ruong mien phi Qua ky dieu khi co cham
do; KHONG BAO GIO cham The thong hanh (d250000), San kho bau (xuc xac), goi tra phi."""
import types

import pytest

from bot import buttons
from bot.modules import mission, reddots


def test_tap_zones():
    assert mission.tap_ok("main", 437, 213)            # tab Nhiem vu hang ngay (anh su_menh_1)
    assert mission.tap_ok("main", 190, 130)            # icon Qua ky dieu
    assert not mission.tap_ok("main", 268, 213)        # tab The thong hanh
    assert not mission.tap_ok("main", 97, 213)         # tab San kho bau
    assert not mission.tap_ok("main", 80, 130)         # icon San kho bau tren chien truong
    assert not mission.tap_ok("main", 270, 600)        # ban xuc xac
    assert not mission.tap_ok("main", 500, 915)        # nut "+" xuc xac
    assert mission.tap_ok("daily", 450, 400)
    assert not mission.tap_ok("daily", 268, 213)
    assert mission.tap_ok("gift", 80, 300)
    assert not mission.tap_ok("gift", 400, 700)        # goi tra phi
    assert not mission.tap_ok("nope", 1, 1)


@pytest.mark.parametrize("t", ["₫250000", "250.000 đ", "₫500000", "1250000", "Mua", "Thẻ thông hành", "Săn kho báu"])
def test_paid_text(t):
    assert mission.paid_text(t)


@pytest.mark.parametrize("t", ["Nhận", "Nhận toàn bộ", "Miễn phí"])
def test_free_text(t):
    assert not mission.paid_text(t)


class V:
    def __init__(self, have, found):
        self.have, self.found = set(have), dict(found)

    def has(self, name):
        return name in self.have

    def find(self, img, name, roi=None, **k):
        return self.found.get(name)


class Ctx:
    def __init__(self, v):
        self.v, self.taps, self.cfg = v, [], {"mission": {}}

    def shot(self):
        return None

    def find(self, name, roi=None, **k):
        return self.v.find(None, name, roi=roi)

    def wait_for(self, name, **k):
        return self.v.find(None, name)

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def ensure_city(self):
        pass

    def back_out(self, n=4):
        self.taps.append("back")

    def dismiss_reward(self):
        pass


def _claims(seq):
    it = iter(seq)
    return lambda img, roi=None: next(it, [])


def test_run_missing_icon_template_skips():
    c = Ctx(V(set(), {}))
    assert mission.run(c) == 0 and c.taps == []


def test_run_daily_tab_claims_only_safe(monkeypatch):
    v = V({"mission/icon", "mission/title", "mission/tab_daily"},
          {"mission/icon": (512, 305, 0.9), "mission/title": (270, 30, 0.9), "mission/tab_daily": (437, 213, 0.9)})
    ok = buttons.Button(450, 400, 100, 40, buttons.CLAIM, 88, "Nhan")
    bad = buttons.Button(268, 213, 100, 40, buttons.CLAIM, 88, "Nhan")       # khop nham o hang tab -> ngoai vung
    monkeypatch.setattr(buttons, "claims", _claims([[bad, ok], [bad]]))
    c = Ctx(v)
    assert mission.run(c) == 1
    assert c.taps == [(512, 305), (437, 213), (450, 400), "back"]


def test_tab_daily_found_in_forbidden_place_not_tapped(monkeypatch):
    v = V({"mission/icon", "mission/tab_daily"},
          {"mission/icon": (512, 305, 0.9), "mission/tab_daily": (268, 213, 0.9)})
    monkeypatch.setattr(buttons, "claims", _claims([]))
    c = Ctx(v)
    assert mission.run(c) == 0 and (268, 213) not in c.taps


def test_free_chest_needs_red_dot(monkeypatch):
    v = V({"mission/free_chest"}, {"mission/free_chest": (80, 300, 0.9)})
    monkeypatch.setattr(buttons, "claims", _claims([]))
    monkeypatch.setattr(mission, "red_dots", lambda img, roi: [])
    c = Ctx(v)
    assert mission.free_chest(c) == 0 and c.taps == []
    monkeypatch.setattr(mission, "red_dots", lambda img, roi: [(105, 280)])
    assert mission.free_chest(c) == 1 and c.taps == [(80, 300)]


def test_reddots_routes_mission_icon():
    assert reddots.allowed("mission", {"modules": {"mission": False}})[0] is False
    assert reddots.KIND_STEP["mission"] == "mission"
    v = types.SimpleNamespace(has=lambda n: n == "mission/icon",
                              find=lambda img, n, **k: (512, 305, 0.9) if n == "mission/icon" else None)
    ctx = types.SimpleNamespace(v=v)
    assert reddots._kind(ctx, None, (524, 290)) == "mission"
