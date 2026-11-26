"""P13k (chu du an 26/11/2026): popup "Mo khoa Binh chung nay" -> bam "Xac nhan", khong bao gio "Den".

Anh: tests/fixtures/p13k/ = dung anh chu du an gui (543x957, co khung do khoanh tay quanh TIEU DE va quanh nut
"Xac nhan"; nut "Den" khong khoanh). Khong co anh that cua hop thoai "Roi tro choi?" trong git -> dung khung dan tu
anh mau nut Huy / Xac nhan."""
import types

import cv2
import numpy as np
import pytest

from bot import ctx as ctxmod
from bot import screens, tapguard
from bot import unlock_popup as U
from bot.modules import tutorial
from bot.vision import Vision

SHOT = "tests/fixtures/p13k/unlock_troop_xacnhan.png"
DEN = (78, 721, 227, 781)          # (x0, y0, x1, y1) nut "Den" do tren anh phong to
DEN_MID = (153, 751)
V = Vision("templates", 0.82)


def _popup():
    img = cv2.imread(SHOT)
    assert img is not None, SHOT
    return img


def _closed():
    """Cung man do sau khi popup dong: xoa tieu de + panel hai nut, giu thanh nut duoi (nut ban do)."""
    img = _popup()
    img[100:200] = (40, 70, 60)
    img[620:830] = (40, 70, 60)
    return img


def _paste(img, name, cx, cy):
    t = V.load(name)
    h, w = t.shape[:2]
    img[cy - h // 2:cy - h // 2 + h, cx - w // 2:cx - w // 2 + w] = t
    return img


def _confirm_box(img):
    """Khung do quanh nut 'Xac nhan' (nua phai, nua duoi anh) -> (x0, y0, x1, y1)."""
    b, g, r = (img[..., i].astype(int) for i in range(3))
    m = (r > 200) & (g < 50) & (b < 50)
    m[:680] = False
    m[:, :290] = False
    ys, xs = np.nonzero(m)
    return xs.min(), ys.min(), xs.max(), ys.max()


def _inside(p, box):
    return box[0] < p[0] < box[2] and box[1] < p[1] < box[3]


class Dev:
    """May gia: cham vao nut trong `moves` thi doi sang man ke tiep; ghi lai moi thao tac."""
    idx = 0

    def __init__(self, screens_, closes=True):
        self.frames, self.closes, self.log, self.act_seq = list(screens_), closes, [], 0

    def screencap(self, tries=None):
        return self.frames[0]

    def tap(self, x, y):
        self.act_seq += 1
        self.log.append((x, y))
        if self.closes and len(self.frames) > 1:
            self.frames.pop(0)

    def back(self):
        self.act_seq += 1
        self.log.append("back")


def make(monkeypatch, frames, closes=True):
    clock = [1000.0]
    monkeypatch.setattr(ctxmod.time, "time", lambda: clock[0])
    monkeypatch.setattr(ctxmod.time, "sleep", lambda s: clock.__setitem__(0, clock[0] + max(0.01, s)))
    dev = Dev(frames, closes)
    c = ctxmod.Ctx(dev, V, {"screen": {"width": 540, "height": 960}, "learn": {"enabled": False}})
    c.save_debug = c.debug_shots.append
    return c, dev


def _only_confirm(dev):
    box = _confirm_box(_popup())
    assert dev.log and all(t != "back" and _inside(t, box) and not _inside(t, DEN) for t in dev.log), dev.log


# ---------- nhan dien (ham thuan) ----------
def test_owner_shot_detected_point_in_confirm_not_den():
    img = _popup()
    p = U.find(img, V)
    assert p is not None and U.title_score(img, V) > 0.9
    assert _inside(p, _confirm_box(img))
    assert not _inside(p, DEN) and not U.in_go_zone(p[0], p[1])
    assert U.in_go_zone(*DEN_MID) and U.in_go_zone(DEN[0], DEN[1]) and U.in_go_zone(DEN[2], DEN[3])


@pytest.mark.parametrize("dx, dy", [(-6, 0), (-3, 3), (0, 3), (-4, -4)])
def test_detected_with_small_frame_offset(dx, dy):
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    img = cv2.warpAffine(_popup(), m, (540, 960))
    p = U.find(img, V)
    assert p and abs(p[0] - (401 + dx)) <= 2 and abs(p[1] - (751 + dy)) <= 2


@pytest.mark.parametrize("colour", [(0, 0, 0), (60, 90, 70), (200, 200, 200)])
def test_title_does_not_depend_on_background(colour):
    img = _popup()
    area = img[100:200]
    keep = cv2.dilate(U.gold_mask(area), np.ones((3, 3), np.uint8)) > 0
    area[~keep] = colour
    assert U.find(img, V)


def test_confirm_button_alone_or_title_alone_is_not_this_popup():
    no_title = _popup()
    no_title[100:200] = (40, 70, 60)
    assert U.find(no_title, V) is None                      # hop thoai "Xac nhan" khac: khong phai popup nay
    no_btn = _popup()
    no_btn[690:810, 290:500] = (40, 70, 60)
    assert U.find(no_btn, V) is None
    assert U.find(_closed(), V) is None and screens.identify(_closed(), V)[0] == "city"


@pytest.mark.parametrize("path", ["tests/fixtures/p13i/wrench_city.png", "tests/fixtures/p13j/intel_miss_1_tank.png",
                                  "tests/fixtures/p13j/intel_miss_2_crate.png"])
def test_other_owner_shots_not_matched(path):
    img = cv2.imread(path)
    assert img is not None and U.find(img, V) is None


def test_identify_popup_before_city():
    """Nut ban do van lo ra duoi popup: truoc P13k man nay bi nhan la 'city'."""
    assert V.find(_popup(), "common/btn_to_world")
    scr, det = screens.identify(_popup(), V)
    assert scr == "popup" and det[0] == U.BTN
    scr, act, arg = screens.nav_action(_popup(), V, "city")
    assert (scr, act) == ("popup", "tap") and _inside(arg, _confirm_box(_popup()))


def test_tutorial_decide_taps_confirm_and_is_not_a_guide():
    act, x, y, why = tutorial.decide(V, _popup(), state={"follow": True})
    assert (act, why) == ("tap", U.WHY) and _inside((x, y), _confirm_box(_popup()))
    assert tutorial.guide_visible(V, _popup()) is None      # truoc P13k: "o do duoi..." -> cham vao tieu de


# ---------- xu ly popup toan cuc ----------
@pytest.mark.parametrize("call", [
    lambda c: c.close_popups(rounds=5),
    lambda c: c.close_popups(rounds=5, settle=1),
    lambda c: c.back_out(),
    lambda c: c.skip_dialogs(),
    lambda c: c.dismiss_reward(),
    lambda c: c.goto("city", rounds=4),
    lambda c: c.ensure_city(),
], ids=["close", "settle", "back_out", "dialogs", "reward", "goto", "ensure_city"])
def test_every_popup_path_presses_confirm_once(monkeypatch, call):
    c, dev = make(monkeypatch, [_popup(), _closed()])
    call(c)
    assert len(dev.log) == 1
    _only_confirm(dev)


def test_late_popup_caught_while_settling(monkeypatch):
    c, dev = make(monkeypatch, [_closed()])
    real, seen = dev.screencap, []

    def cap(tries=None):
        seen.append(1)
        if len(seen) == 2:
            dev.frames = [_popup(), _closed()]
        return real()

    dev.screencap = cap
    c.close_popups(rounds=5, settle=3)
    assert len(dev.log) == 1
    _only_confirm(dev)


def test_stuck_popup_two_tries_then_blacklist(monkeypatch):
    c, dev = make(monkeypatch, [_popup()], closes=False)
    c.close_popups(rounds=10, settle=3)
    assert len(dev.log) == 2
    assert tapguard.of(c).blocked(U.SCOPE, 401, 751) and tapguard.of(c).blocked(U.SCOPE, 402, 749)
    assert c.debug_shots == ["unlock_troop_stuck"]
    c.close_popups()
    c.back_out()
    c.dismiss_reward()                                      # REWARD_CLOSERS co btn_confirm: khong duoc bam lai
    assert c.goto("city", rounds=10) is False               # khong Back, khong cham ra ngoai
    assert U.dismiss(c) is False
    assert len(dev.log) == 2
    _only_confirm(dev)


def test_second_try_closes(monkeypatch):
    c, dev = make(monkeypatch, [_popup(), _popup(), _closed()])
    assert U.dismiss(c) is True
    assert len(dev.log) == 2 and not tapguard.of(c).blocked(U.SCOPE, 401, 751)
    assert U.dismiss(c) is None


def test_follow_run_does_not_loop_on_stuck_popup(monkeypatch):
    c, dev = make(monkeypatch, [_popup()], closes=False)
    assert tutorial.run(c, max_steps=50, follow=True) == "stuck"
    assert len(dev.log) == 2
    _only_confirm(dev)


# ---------- chan nut "Den" ----------
def test_intel_go_template_matches_den_but_is_never_tapped(monkeypatch):
    p = V.find(_popup(), "intel/btn_go")
    assert p and _inside(p, DEN)                            # rui ro that: buoc Tinh bao bam mau nay
    c, dev = make(monkeypatch, [_popup(), _closed()])
    assert c.tap_tpl("intel/btn_go", wait=0.1) is False
    assert len(dev.log) == 1
    _only_confirm(dev)


@pytest.mark.parametrize("call", [
    lambda c: c.tap_first(["intel/btn_go"]),
    lambda c: c.tap_first(["intel/btn_go"], img=_popup()),
    lambda c: (c.shot(), c.tap(*DEN_MID)),
], ids=["tap_first", "tap_first_img", "tap"])
def test_den_zone_blocked_for_every_tap_helper(monkeypatch, call):
    c, dev = make(monkeypatch, [_popup(), _closed()])
    call(c)
    assert len(dev.log) == 1
    _only_confirm(dev)


def test_same_zone_tappable_without_popup(monkeypatch):
    c, dev = make(monkeypatch, [_closed()])
    c.shot()
    c.tap(*DEN_MID)
    assert dev.log == [DEN_MID]


# ---------- hop thoai "Roi tro choi?" ----------
def _exit_dialog(over=None):
    img = over if over is not None else _closed()
    _paste(img, "common/btn_cancel_exit", 154, 580)
    return _paste(img, "common/btn_confirm_unlock", 401, 751) if over is None else img


@pytest.mark.parametrize("call", [lambda c: c.close_popups(rounds=3), lambda c: c.dismiss_reward(),
                                  lambda c: c.goto("city", rounds=3)], ids=["close", "reward", "goto"])
def test_exit_dialog_only_cancel(monkeypatch, call):
    c, dev = make(monkeypatch, [_exit_dialog(), _closed()])
    assert U.find(dev.frames[0], V) is None
    call(c)
    assert len(dev.log) == 1 and abs(dev.log[0][0] - 154) <= 2 and abs(dev.log[0][1] - 580) <= 2


def test_exit_dialog_over_unlock_popup_cancelled_first(monkeypatch):
    both = _exit_dialog(over=_popup())
    assert U.find(both, V) is None
    c, dev = make(monkeypatch, [both, _popup(), _closed()])
    c.close_popups(rounds=5)
    assert len(dev.log) == 2
    assert abs(dev.log[0][1] - 580) <= 2 and _inside(dev.log[1], _confirm_box(_popup()))


def test_dismiss_checks_exit_dialog_before_every_confirm(monkeypatch):
    c, _dev = make(monkeypatch, [_popup(), _closed()])
    order = []
    real_cancel, real_tap = c.cancel_exit, c.tap
    c.cancel_exit = lambda *a, **k: (order.append("cancel_exit"), real_cancel(*a, **k))[1]
    c.tap = lambda *a, **k: (order.append("tap"), real_tap(*a, **k))[1]
    assert U.dismiss(c) is True
    assert order == ["cancel_exit", "tap"]


def test_bare_confirm_not_in_popup_closers():
    assert "common/btn_confirm" not in ctxmod.Ctx.POPUP_CLOSERS
    assert U.BTN not in ctxmod.Ctx.POPUP_CLOSERS and U.BTN not in screens.POPUPS


def test_fake_frames_and_vision_are_ignored():
    fake = types.SimpleNamespace(find=lambda *a, **k: (1, 1, 1.0))
    assert U.find("img", fake) is None
    assert U.find(np.zeros((960, 540, 3), np.uint8), fake) is None   # khong co anh tieu de -> khong nhan
