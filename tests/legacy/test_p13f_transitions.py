"""P13f-3: buoc chuyen tiep nhanh hon (it khung chup thua, cho toi khi man doi) ma khong doi dieu kien bam."""
import types

import numpy as np
import pytest

from bot import ctx as ctxmod
from bot.ctx import Ctx
from bot.modules import upgrade

HOME = np.full((960, 540, 3), 40, np.uint8)
PANEL = np.full((960, 540, 3), 120, np.uint8)
POPUP = np.full((960, 540, 3), 200, np.uint8)
FOUND = {40: {"common/btn_to_world": (60, 900, 0.9)}, 120: {"common/btn_back": (40, 40, 0.9)},
         200: {"common/btn_x": (500, 200, 0.9)}}


class Clock:
    def __init__(self):
        self.t = 1000.0

    def time(self):
        return self.t

    def sleep(self, s):
        self.t += max(0.0, s)


class Dev:
    """Man doi theo kich ban: sau moi thao tac, `after[i]` hien ra sau `delay` giay."""
    idx = 0
    CAP = 0.28

    def __init__(self, clock, screen, after=(), delay=0.3):
        self.c, self.screen, self.after, self.delay = clock, screen, list(after), delay
        self.pending, self.shots, self.log, self.act_seq = None, 0, [], 0

    def screencap(self, tries=None):
        self.c.t += self.CAP
        self.shots += 1
        if self.pending and self.c.t >= self.pending[0]:
            self.screen, self.pending = self.pending[1], None
        return self.screen

    def _act(self, what):
        self.act_seq += 1
        self.log.append(what)
        if self.after:
            self.pending = (self.c.t + self.delay, self.after.pop(0))

    def tap(self, x, y):
        self._act(("tap", x, y))

    def back(self):
        self._act(("back",))


class V:
    def find(self, img, name, **k):
        return FOUND.get(int(img[0, 0, 0]), {}).get(name)


def make(monkeypatch, screen, after=(), delay=0.3):
    clock = Clock()
    monkeypatch.setattr(ctxmod.time, "time", clock.time)
    monkeypatch.setattr(ctxmod.time, "sleep", clock.sleep)
    dev = Dev(clock, screen, after, delay)
    c = Ctx(dev, V(), {"screen": {"width": 540, "height": 960}, "learn": {"enabled": False}})
    return c, dev, clock


def test_back_out_at_home_never_presses_back_one_frame(monkeypatch):
    c, dev, _ = make(monkeypatch, HOME)
    c.back_out()
    assert dev.log == [] and dev.shots == 1


def test_back_confirms_two_frames_apart_then_waits_for_change(monkeypatch):
    blank = np.full((960, 540, 3), 80, np.uint8)     # man khong co nut nao -> phim Back
    c, dev, clock = make(monkeypatch, blank, after=[HOME])
    times = []
    real = dev.screencap
    dev.screencap = lambda tries=None: (times.append(clock.t), real(tries))[1]
    t0 = clock.t
    c.back_out()
    assert dev.log == [("back",)]
    assert times[1] - times[0] >= ctxmod.BACK_CONFIRM_S - 1e-6      # van 2 khung cach nhau >= 0,5 s truoc khi Back
    assert clock.t - t0 < 2.6


def test_no_back_when_second_frame_is_home(monkeypatch):
    blank = np.full((960, 540, 3), 80, np.uint8)
    c, dev, _ = make(monkeypatch, blank)
    dev.pending = (1000.4, HOME)                     # ban do dang truot: khung 2 thay nut ban do
    assert c.press_back("x") is False and dev.log == []


def test_wait_change_waits_for_new_stable_frame(monkeypatch):
    c, dev, clock = make(monkeypatch, PANEL)
    dev.pending = (1000.5, HOME)
    img = c.wait_change(PANEL, 3.0)
    assert img[0, 0, 0] == 40 and 0.5 <= clock.t - 1000.0 < 1.5
    t = clock.t
    assert c.wait_change(HOME, 0.8)[0, 0, 0] == 40 and clock.t - t >= 0.8     # khong doi -> cho het tran


def test_close_popups_settle_ends_early_on_quiet_home(monkeypatch):
    c, dev, clock = make(monkeypatch, HOME)
    c.close_popups(rounds=10, settle=3)
    assert dev.log == [] and clock.t - 1000.0 < 3.0


def test_close_popups_settle_still_catches_late_popup(monkeypatch):
    c, dev, _ = make(monkeypatch, HOME, after=[HOME])
    dev.pending = (1001.0, POPUP)                    # popup noi tiep hien sau 1 s
    c.close_popups(rounds=10, settle=3)
    assert dev.log and dev.log[0] == ("tap", 500, 200)


def test_close_popups_settle_waits_full_cap_while_loading(monkeypatch):
    blank = np.full((960, 540, 3), 80, np.uint8)     # khong phai thanh pho / ban do: dang tai
    c, _, clock = make(monkeypatch, blank)
    c.close_popups(rounds=10, settle=3)
    assert clock.t - 1000.0 >= 3.0


def test_recent_frame_invalidated_by_any_input(monkeypatch):
    c, dev, clock = make(monkeypatch, HOME)
    dev.tap(1, 1)
    c.shot()
    assert c.recent_frame() is not None
    clock.t += 2
    assert c.recent_frame() is None                  # qua cu
    c.shot()
    dev.tap(1, 1)
    assert c.recent_frame() is None                  # da cham: phai chup lai


def test_close_popups_reuses_given_frame(monkeypatch):
    c, dev, _ = make(monkeypatch, HOME)
    c.close_popups(img=HOME)
    assert dev.shots == 0 and dev.log == []


@pytest.mark.parametrize("hit,ok", [((270, 450, 0.9), True), ((330, 540, 0.9), True), ((450, 450, 0.9), False),
                                    (None, False)])
def test_hq_centered(hit, ok):
    assert upgrade.hq_centered(hit) is ok


@pytest.mark.parametrize("again,hit,trips", [(False, (270, 450, 0.9), 1), (True, (270, 450, 0.9), 0),
                                             (True, (450, 700, 0.9), 1)])
def test_recenter_only_when_needed(monkeypatch, again, hit, trips):
    done = []
    monkeypatch.setattr(upgrade, "recenter_hq", lambda ctx: done.append(1) or True)
    monkeypatch.setattr(upgrade, "_names", lambda ctx: ["build/hq_emblem_a"])
    monkeypatch.setattr(upgrade, "_templates", lambda ctx: [np.zeros((2, 2, 3), np.uint8)])
    monkeypatch.setattr(upgrade, "find_hq", lambda *a, **k: hit)
    monkeypatch.setattr(upgrade, "_try_open", lambda ctx, h: (1, 2, 3))
    monkeypatch.setattr(upgrade, "_drag", lambda ctx, dx, dy: None)
    c = types.SimpleNamespace(ensure_city=lambda: None, settle=lambda: None)
    assert upgrade.goto_hq(c, again=again) == (1, 2, 3) and len(done) == trips
