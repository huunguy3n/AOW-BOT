"""Che do hoc mau (#3, 2026-11-21): bot dung yen, ket thuc khi chu du an ngung thao tac; may khong vao vong auto."""
import types

import pytest

from bot import demo
from bot.runner import Runner


def clock(step=5):
    t = [0.0]

    def now():
        return t[0]

    def sleep(s):
        t[0] += s
    return now, sleep


def test_session_ends_after_idle_and_counts_actions():
    now, sleep = clock()
    hw = types.SimpleNamespace(n=10)
    ctx = types.SimpleNamespace(human=hw)
    ticks = []

    def check():
        ticks.append(now())
        if now() == 30:
            hw.n = 13            # chu du an thao tac 3 lan o giay 30
    n = demo.session(ctx, {"demo": {"idle_min": 1, "max_min": 60}}, check, now=now, sleep=sleep)
    assert n == 3 and now() == 90          # dung 60 s sau thao tac cuoi


def test_session_requires_human_watch():
    with pytest.raises(RuntimeError):
        demo.session(types.SimpleNamespace(human=None), {}, lambda: None)


def test_demo_machines_not_in_auto_rotation():
    modes = {0: "smart", 3: "demo"}
    store = types.SimpleNamespace(inst=lambda i: {"enabled": True},
                                  cfg_for=lambda base, i=None: {"schedule": {"mode": modes.get(i)}})
    r = types.SimpleNamespace(base_cfg={"instances": [0, 3]}, store=store)
    assert Runner._auto_ids(r) == [0]
