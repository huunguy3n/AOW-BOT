"""P12-4 (t55u, live-run-4): (a) popup 'Phien quan Lv.N' + 'Toi da co the tan cong phan quan cap X!' -> bam 'Tim kiem';
(b) nha chinh < 15 / < 6 van danh LE phien quan NPC cua nhiem vu (chi cam tham gia tap ket Co giap);
(c) o 'Cap' Co giap chi nhan boi so 5 (#1 s184116/s184141: 5 -> 10 -> 5) -> dich cap, khong tim lai cung cap."""
import inspect
import os
import types

import cv2
import pytest

from bot import scheduler
from bot.modules import gather, mainquest, rebels
from bot.vision import Vision

V = Vision("templates")
LIVE = "tests/fixtures/p12/rebel_search_i3.png"          # data/pm-shots/owner-20261124/live4/#3/auto/s193422.png
OWNER = "data/pm-shots/owner-20261124/live4-feedback/rebel_toi_da_cap_tim_kiem.png"


def _img(p, scale=None):
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    im = cv2.imread(p)
    return cv2.resize(im, None, fx=scale, fy=scale) if scale else im


def test_popup_search_live():
    assert mainquest.npc_popup_action(_img(LIVE), V) == "search"


def test_popup_search_owner_t55u():
    assert mainquest.npc_popup_action(_img(OWNER, 540 / 544), V) == "search"


def test_city_frame_not_search():
    im = _img(LIVE).copy()
    im[600:850, 100:440] = (30, 30, 30)
    assert mainquest.npc_popup_action(im, V) is None


class _Ctx:
    def __init__(self, frames):
        self.frames, self.taps, self._img = list(frames), [], None
        self.v = V
        self.cfg = {}

    def shot(self):
        self._img = self.frames[0] if len(self.frames) == 1 else self.frames.pop(0)
        return self._img

    def find(self, name, fresh=True, **kw):
        return self.v.find(self.shot() if fresh or self._img is None else self._img, name, **kw)

    def wait_for(self, name, timeout=6.0, **kw):
        return self.find(name, **kw)

    def tap(self, x, y, wait=1.0):
        self.taps.append((x, y))

    def settle(self, **k):
        return self.shot()


def test_npc_search_taps_tim_kiem_never_blind_centre():
    live = _img(LIVE)
    blank = live.copy()
    blank[:] = 20
    ctx = _Ctx([live, blank, blank, blank])
    assert mainquest.npc_search(ctx) is None                 # khong co bang Tan cong sau khi tim -> None
    assert ctx.taps == [(268, 738)]                           # chi nut 'Tim kiem'; P13m: khong cham giua man


def test_npc_attack_not_gated_by_world_hq(monkeypatch, caplog):
    src = inspect.getsource(mainquest._npc_attack_once)
    i = src.index("if not ctx.world_ready():")
    assert "return \"npc_skip\"" not in src[i:i + 400]          # truoc day: npc_skip ngay o nha chinh 4-5
    assert "npc_search(ctx)" in src


def test_hq_below_15_never_joins_mech_rally():
    class M:
        def fact(self, i, k):
            return 4 if k == "hq_level" else None
    assert not rebels.join_hq_ok(M(), 3, {"min_hq_level": 15})
    ok, why = scheduler.rebels_ready(M(), 3, {"rebels": {"min_hq_level": 15}})
    assert not ok and "15" in why                             # buoc rebels (tap ket Co giap) van bo


def test_mainquest_rebels_kind_still_runs_npc():
    assert mainquest.quest_rules.classify("Kich sat 1 lan phan quan Lv.3")[0] == "rebels"
    src = inspect.getsource(mainquest.step)
    assert 'if kind == "rebels":' in src and "npc_attack(ctx, mq)" in src


def test_snap_level():
    assert gather.snap_level(7, 5) == 5
    assert gather.snap_level(9, 5) == 5
    assert gather.snap_level(10, 5) == 10
    assert gather.snap_level(3, 5) == 5
    assert gather.snap_level(7, 1) == 7
    assert rebels.snap_levels([9, 8, 7], 5) == [5]
    assert rebels.snap_levels([11, 10, 9], 5) == [10, 5]


class _LvCtx:
    """O 'Cap' Co giap: moi lan bam +/- doi 5 cap (live4 #1)."""
    def __init__(self, cur=1, step=5, lo=5, hi=40):
        self.cur, self.step, self.lo, self.hi = cur, step, lo, hi
        self.dev = types.SimpleNamespace(tap=self._tap)
        self.taps = 0

    def find(self, name, fresh=True, **kw):
        return (40, 750) if name.endswith("minus") else (480, 750)

    def _tap(self, x, y):
        self.taps += 1
        d = self.step if x > 270 else -self.step
        if self.cur < self.lo:
            self.cur = self.lo
        else:
            self.cur = min(self.hi, max(self.lo, self.cur + d))


def test_set_level_learns_step_and_snaps(monkeypatch):
    ctx = _LvCtx(cur=5)
    monkeypatch.setattr(gather, "read_level", lambda c: c.cur)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.set_level(ctx, 9)                            # truoc: dao 5 <-> 10 roi 'KHONG dat'
    assert ctx.cur == 5 and ctx.level_step == 5
    assert gather.set_level(ctx, 12) and ctx.cur == 10


def test_set_level_step1_unchanged(monkeypatch):
    ctx = _LvCtx(cur=3, step=1, lo=1)
    monkeypatch.setattr(gather, "read_level", lambda c: c.cur)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.set_level(ctx, 7) and ctx.cur == 7


def test_type_level_snaps_known_step(monkeypatch):
    typed = []
    ctx = _LvCtx(cur=5)
    ctx.level_step = 5
    ctx.dev.type_digits = lambda n: typed.append(n) or setattr(ctx, "cur", n)
    ctx.tap = lambda *a, **k: None
    ctx.shot = lambda: None
    monkeypatch.setattr(gather, "read_level", lambda c: c.cur)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.type_level(ctx, 7) and typed == [5]          # go boi so 5, OCR xac nhan
