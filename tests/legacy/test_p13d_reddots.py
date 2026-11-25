"""P13d-1: cham do quet den het - bao ve Lien minh/Tinh bao/Chien dich/Nhan, tri nho theo lan ghe, tran moi cham."""
from types import SimpleNamespace

import cv2
import numpy as np

from bot.modules import reddots as R
from tests.legacy.test_reddots_limits import Mem


def test_protected_kinds_never_skipped():
    for k in ("alliance", "intel", "campaign", "nhan", "ally_gift", "mail", "construct"):
        assert R.must_open(k), k
    assert not R.must_open("generic")


def test_nhan_icon_dot_is_hud_and_kind_nhan():
    assert R.is_hud_dot((197, 748))               # anh reddot_con_sot.png: cham icon "Nhan"
    assert not R.is_hud_dot((320, 798))           # mai do cong trinh van bi loai


def test_hammer_dot_detected_with_loose_threshold():
    img = np.zeros((960, 540, 3), np.uint8)
    cv2.circle(img, (530, 796), 7, (0, 0, 175), -1)          # do hoi toi (V ~175) < nguong thuong 190
    assert R.hammer_dots(img) and not R.red_dots(img, R.CITY)


def test_remember_clears_worked_position_and_stores_visit():
    m = Mem()
    rc = R.rcfg({})
    k = (3, 5)
    R.remember(m, 0, rc, {}, {}, {k}, set(), {k}, 1000.0, visit=7)
    assert m.fact(0, "reddots_dead_visit") == 7
    assert "3,5" not in m.fact(0, "reddots_dead")  # nhan duoc -> khong coi vo ich


def test_rcfg_has_dot_cap_and_final_sweep():
    rc = R.rcfg({})
    assert rc["dot_max_s"] > 0 and rc["final_sweep"] and rc["final_max_s"] > 0


class _Ctx:
    def __init__(self, visit, done=None):
        self.cfg = {"modules": {}}
        self.dev = SimpleNamespace(idx=0)
        self.mem, self.visit, self.visit_done = Mem(), visit, done or {}
        self.v = SimpleNamespace()
        self.tap_guard = None

    def ensure_city(self):
        pass

    def shot(self):
        return np.zeros((960, 540, 3), np.uint8)

    def save_debug(self, *a):
        pass


def _patch(mp, dots, kinds, calls, n_ret=0):
    mp.setattr(R, "_left", lambda img, v=None: list(dots))
    mp.setattr(R, "_kind", lambda ctx, img, d: kinds[d])
    mp.setattr(R, "_handle", lambda ctx, kind, x, y: (calls.append(kind), n_ret)[1])
    mp.setattr(R.notify, "badged", lambda ctx: False)
    mp.setattr(R.chat, "clear", lambda ctx: 0)
    mp.setattr(R, "_keep_last", lambda ctx, img: None)


def test_protected_dot_opened_even_if_step_idle_and_no_infinite_loop(monkeypatch):
    calls = []
    d = (300, 900)                                       # Lien minh
    _patch(monkeypatch, [d], {d: "alliance"}, calls)
    ctx = _Ctx(1, done={"alliance": 0})                  # buoc rieng vua chay tra 0 -> truoc day bi bo qua
    R.run(ctx)
    assert calls == ["alliance"]                          # van mo 1 lan, khong lap vo han


def test_useless_memory_expires_per_visit(monkeypatch):
    calls = []
    d = (30, 400)
    _patch(monkeypatch, [d], {d: "generic"}, calls)
    ctx = _Ctx(1)
    R.run(ctx)                                            # mo, vo ich -> nho
    assert calls == ["generic"]
    R.run(ctx, final=True)                                # cung lan ghe nhung cuoi luot -> quet lai that
    ctx.visit = 1
    calls.clear()
    R.run(ctx)                                            # cung visit, trong han 30 phut -> bo qua (due), khong mo
    assert calls == []
    ctx.tap_guard = None                                  # lan ghe moi: guard moi (runner tao)
    ctx.visit = 2                                         # lan ghe moi: tri nho het han (ep toi han)
    ctx.mem.set_fact(0, "reddots_last_at", 0)
    R.run(ctx)
    assert calls == ["generic"]


def test_dot_time_cap(monkeypatch):
    calls = []
    d = (30, 400)
    _patch(monkeypatch, [d], {d: "generic"}, calls, n_ret=1)
    ctx = _Ctx(1)
    ctx.cfg["reddots"] = {"dot_max_s": 0}
    R.run(ctx)
    assert calls == []                                    # tran 0 s -> khong ket vao 1 diem
