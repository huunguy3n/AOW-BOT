"""P7-4 (chu du an 2026-11-24, live #1): tinh bao - kiem quan doan that su xuat phat, toi da 2 hop qua cung luc,
quet lai ban do khi co diem moi, het the luc dung binh 10 diem (khong bao gio "Mua")."""
import time
import types

import pytest

from bot import intel_rules as IR
from bot.modules import notify


# ---------- ham thuan ----------
def test_departed_by_march_count_then_by_button():
    assert IR.departed((2, 5), (3, 5), screen_gone=True)
    assert not IR.departed((2, 5), (2, 5), screen_gone=True)       # nut mat nhung x/y khong tang -> chua di
    assert IR.departed(None, None, screen_gone=True)               # khong doc duoc so -> theo nut
    assert not IR.departed(None, (3, 5), screen_gone=False)
    assert not IR.departed((2, 5), None, screen_gone=False)


def test_pickups_max_two_and_wait():
    pk = IR.Pickups(cap=2, dur=90)
    assert pk.can_pick(0)
    pk.add(0)
    pk.add(10)
    assert not pk.can_pick(20) and pk.wait_s(20) == 70
    assert pk.can_pick(91) and pk.wait_s(91) == 0                  # hop dau nhat xong
    pk.add(91)
    pk.done()                                                      # tick xanh -> giai phong som
    assert pk.can_pick(92)


def test_should_rescan():
    assert IR.should_rescan(1, 0, 3)
    assert not IR.should_rescan(0, 0, 3)                           # lan quet truoc khong lam duoc gi -> dung
    assert not IR.should_rescan(2, 3, 3)


def test_pick_use_button_never_buy():
    uses = [(450, 300, 0.9), (450, 420, 0.9)]
    assert IR.pick_use_button(uses, (120, 418, 0.9)) == (450, 420, 0.9)   # hang binh 10 diem
    assert IR.pick_use_button(uses, None) == (450, 300, 0.9)               # thieu anh binh 10 -> tren cung
    assert IR.pick_use_button(uses, (120, 418), buys=[(452, 421)]) is None  # "Dung" khop trung nut Mua -> bo
    assert IR.pick_use_button([], (120, 418)) is None
    assert IR.pick_use_button(uses, (120, 700)) is None                     # khong co nut Dung cung hang


# ---------- luong tren Ctx gia ----------
class V:
    def __init__(self, seen=(), alls=None):
        self.seen, self.alls = set(seen), alls or {}

    def has(self, name):
        return True

    def find(self, img, name, th=None, roi=None, **k):
        return (270, 300, 0.95) if name in self.seen else None

    def find_all(self, img, name, **k):
        return self.alls.get(name, [])


class Ctx:
    def __init__(self, v, marches=None, sticky=()):
        self.v, self.taps, self.caps, self.sent = v, [], [], 0
        self.cfg = {"notify": {}, "rebels": {}}
        self.dev = types.SimpleNamespace(idx=1)
        self.POPUP_CLOSERS = []
        self.marches = list(marches or [])
        self.sticky = set(sticky)          # nut khong bien mat sau khi bam (quan doan khong di)

    def shot(self):
        return "img"

    def find(self, name, fresh=True, **k):
        return self.v.find("img", name)

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def tap_tpl(self, name, **k):
        if self.v.find("img", name):
            self.taps.append(name)
            if name not in self.sticky:
                self.v.seen.discard(name)
            return True
        return False

    def back_out(self, n=4):
        self.taps.append("back")

    def read_marches(self):
        return self.marches.pop(0) if self.marches else None

    def march_sent(self):
        self.sent += 1


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(notify.time, "sleep", lambda s: None)
    monkeypatch.setattr("bot.build.inv_capture", lambda ctx, tag: ctx.caps.append(tag))


def test_confirm_departure_ok_when_count_rises():
    c = Ctx(V({"gather/btn_march"}), marches=[(1, 5), (2, 5)])
    assert notify.confirm_departure(c, "gather/btn_march") == "marched" and c.sent == 1


def test_confirm_departure_retries_then_not_departed():
    c = Ctx(V({"gather/btn_march"}), sticky={"gather/btn_march"})
    assert notify.confirm_departure(c, "gather/btn_march") == IR.NOT_DEPARTED
    assert c.taps.count("gather/btn_march") == 2 and c.caps == ["intel_" + IR.NOT_DEPARTED] and c.sent == 0


def test_confirm_departure_count_unchanged_is_not_departed():
    c = Ctx(V({"rebels/btn_march_out"}), marches=[(1, 5), (1, 5), (1, 5)])
    assert notify.confirm_departure(c, "rebels/btn_march_out") == IR.NOT_DEPARTED


def test_pickup_waits_for_slot_then_picks(monkeypatch):
    c = Ctx(V({"intel/btn_pickup"}))
    now = [1000.0]
    monkeypatch.setattr(notify.time, "time", lambda: now[0])
    pk = notify._pickups(c)
    pk.add(950)
    pk.add(960)                                  # 2 hop dang nhat; hop dau xong luc 1040 -> cho 40 s (<120)
    slept = []
    monkeypatch.setattr(notify.time, "sleep", lambda s: (slept.append(s), now.__setitem__(0, now[0] + s)))
    assert notify.pickup(c) == "picked" and slept == [40.0] and len(pk.until) == 2


def test_pickup_busy_when_wait_too_long():
    c = Ctx(V({"intel/btn_pickup"}))
    c.cfg["notify"] = {"intel_pickup_s": 1000, "intel_pickup_wait_max_s": 120}
    pk = notify._pickups(c)
    pk.add(time.time())
    pk.add(time.time())
    assert notify.pickup(c) == IR.PICKUP_BUSY and "intel/btn_pickup" not in c.taps
    assert IR.PICKUP_BUSY in IR.SKIP


def test_use_potion10_taps_row_of_10_not_buy():
    v = V({"intel/potion_10"}, alls={"intel/btn_use_potion": [(450, 250, 0.9), (450, 300, 0.9)],
                                    "intel/btn_buy_potion": [(450, 380, 0.9)]})
    c = Ctx(v)
    assert notify.use_potion10(c) and c.taps == [(450, 300)]
    c = Ctx(V(alls={"intel/btn_buy_potion": [(450, 300, 0.9)]}))
    assert not notify.use_potion10(c) and c.taps == []            # chi co nut Mua -> khong bam gi


def test_intel_rescans_after_done(monkeypatch):
    """Ghim xong -> het ghim -> quet lai; diem moi hien -> lam tiep; lan quet sau khong co gi -> dung."""
    scans = [[(200, 400, 0.9)], [], [(300, 420, 0.9)], [], []]

    class V2(V):
        def find_all(self, img, name, **k):
            if name == "intel/pin_base":
                return scans.pop(0) if scans else []
            return []
    c = Ctx(V2({"intel/title"}))
    monkeypatch.setattr(notify, "done_ticks", lambda img: [])
    monkeypatch.setattr(notify, "energy", lambda ctx: 50)
    monkeypatch.setattr(notify, "intel_mission", lambda ctx: "win")
    assert notify.intel(c, 20) == 2
    assert not scans                                               # da quet lai toi khi het
