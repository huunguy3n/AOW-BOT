"""P12-6 (live-run-4): (a) #5 popup khong dong (btn_x @488,266 cham 48 lan, goto(city) hong 10 lan, watchdog sau 5 phut)
-> X 3 lan khong dong: Back, roi cham RA NGOAI popup; khong bao gio cham nut mua / gia / kim cuong.
(b) #2 ScreencapError -> may treo -> khoi dong lai giua buoc upgrade, buoc bi bo -> thu lai DUNG 1 lan."""
import inspect

import numpy as np

from bot import ctx as ctxmod
from bot import runner, screens


def test_popup_escape_sequence():
    seq = [ctxmod.popup_escape("popup", n) for n in range(8)]
    assert seq[:3] == [None, None, None]                       # 3 lan dau: cham X binh thuong
    assert seq[3] == "back" and seq[4] == "outside" and seq[5] == "back" and seq[6] == "outside"
    assert ctxmod.popup_escape("city", 9) is None


def test_outside_point_is_screen_edge():
    x, y = ctxmod.OUTSIDE
    assert x <= 20 and 300 <= y <= 700                           # mep trai, xa nut mua (giua / phai popup)


class _Dev:
    idx, act_seq = 5, 0


def _goto_ctx(monkeypatch):
    """Man popup dung yen: nav_action luon bao cham X; ghi lai moi thao tac."""
    img = np.zeros((960, 540, 3), np.uint8)
    acts = []
    c = ctxmod.Ctx.__new__(ctxmod.Ctx)
    c.v, c.cfg, c.dev, c.nav = None, {"learn": {"enabled": False}}, _Dev(), []
    c.shot = lambda: img
    c.tap = lambda x, y, wait=1.0, tpl=None: acts.append(("tap", x, y))
    c.safe_back = lambda: acts.append(("back",))
    c.dismiss_reward = lambda: None
    monkeypatch.setattr(screens, "nav_action", lambda im, v, t: ("popup", "tap", (488, 266)))
    monkeypatch.setattr(screens, "same", lambda a, b, th=2.0: True)
    monkeypatch.setattr(screens, "last_detail", lambda: ("common/btn_x",))
    monkeypatch.setattr(ctxmod.time, "sleep", lambda s: None)
    return c, acts


def test_goto_stuck_popup_uses_back_and_outside(monkeypatch):
    c, acts = _goto_ctx(monkeypatch)
    assert c.goto("city", rounds=8) is False
    assert ("back",) in acts and ("tap", *ctxmod.OUTSIDE) in acts
    taps = [a for a in acts if a[0] == "tap"]
    assert all((a[1], a[2]) in ((488, 266), ctxmod.OUTSIDE) for a in taps)   # chi X / ngoai popup, khong nut khac
    assert sum(1 for a in taps if (a[1], a[2]) == (488, 266)) <= 3


def test_retry_after_recover_once():
    r = set()
    assert runner.retry_after_recover("upgrade", "err", r)
    r.add("upgrade")
    assert not runner.retry_after_recover("upgrade", "err", r)    # khong thu lai vo han
    assert not runner.retry_after_recover("observe", "err", set())
    assert not runner.retry_after_recover("upgrade", "ok", set())
    assert runner.retry_after_recover("upgrade", "stuck", set())


def test_runner_requeues_step_after_recover():
    src = inspect.getsource(runner.Runner)
    i = src.index("if self._recover_device(ctx, idx, pkg, cfg, recovers, name):")
    seg = src[i:i + 700]
    assert "retry_after_recover(name, res, retried)" in seg and "queue.insert(qi, (name, mod))" in seg
    assert "retried.add(name)" in seg

