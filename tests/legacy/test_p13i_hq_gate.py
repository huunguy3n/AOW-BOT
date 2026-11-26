"""P13i: moi cho ghi hq_level di qua bot.hqlevel - 1 lan doc thoang khong bao gio ha cap (26/11: #2/#3 luu 7, man nang
cap ghi thang 6). Ha cap chi khi >= 2 lan doc chi tiet khop nhau, co WARNING."""
import logging
import types

import numpy as np
import pytest

from bot import build, hqlevel
from bot.memory import Memory
from bot.modules import observe, upgrade
from bot.runner import Runner

IMG = np.zeros((960, 540, 3), np.uint8)


class Store:
    def __init__(self, lv=None):
        self.d = {} if lv is None else {"hq_level": lv}

    def inst(self, idx):
        return self.d

    def update(self, idx, **kw):
        self.d.update(kw)


def _ctx(tmp_path, prev=7):
    m = Memory(str(tmp_path / "m.db"))
    if prev is not None:
        m.set_fact(2, "hq_level", prev)
    return types.SimpleNamespace(mem=m, store=Store(prev), dev=types.SimpleNamespace(idx=2),
                                 cfg={"build": {"hq_max_level": 30}, "modules": {}})


def _levels(c):
    return c.store.d.get("hq_level"), c.mem.fact(2, "hq_level")


def _warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING and "HA cap" in r.getMessage()]


def test_single_lower_read_never_written(tmp_path, caplog):
    c = _ctx(tmp_path)
    assert hqlevel.record(c, [(6, True)], "x") is None
    assert _levels(c) == (7, 7) and not _warnings(caplog)


def _upgrade_screen(c, monkeypatch, level):
    """Ctx dang o man nang cap nha chinh (title_hq) doc ra `level`, khong nang duoc (follow_quests tat)."""
    c.v = types.SimpleNamespace(find=lambda img, n, **k: (1, 1, 1.0) if n in ("build/btn_upgrade", "build/title_hq")
                                else None)
    c.shot = c.settle = lambda *a, **k: IMG
    c.find = lambda *a, **k: None
    c.skip_dialogs = lambda *a: 0
    c.cfg["build"]["follow_quests"] = False
    monkeypatch.setattr(build, "screen_level", lambda img: level)


def test_one_upgrade_screen_read_keeps_7_two_write_6_with_warning(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="aow")
    c = _ctx(tmp_path)
    _upgrade_screen(c, monkeypatch, 6)
    assert build.upgrade_here(c) == "blocked"
    assert _levels(c) == (7, 7) and not _warnings(caplog)
    build.upgrade_here(c)                                       # lan mo man thu 2 khop 6
    assert _levels(c) == (6, 6)
    (msg,) = _warnings(caplog)
    assert "may 2" in msg and "7 -> 6" in msg and "title_hq" in msg
    assert c.mem.fact(2, "hq_history")[-1][1] == 6


def test_two_matching_panel_reads_lower(tmp_path, caplog):
    c = _ctx(tmp_path)
    assert hqlevel.record(c, [(6, True), (6, True)], "panel") == 6
    assert _levels(c) == (6, 6) and len(_warnings(caplog)) == 1


@pytest.mark.parametrize("reads", [
    [[(6, False)], [(6, False)], [(6, False)]],      # khong nhan: khong phai man chi tiet chac chan
    [[(6, True)], [(7, True)], [(6, True)]],         # lan doc 7 chen vao -> dem lai
    [[(6, True)], [(5, True)]],                      # 2 gia tri khac nhau
    [[(6, True), (5, True)]],
    [[(6, True)], [(9, True)], [(6, True)]],         # doc cao hon (chua xac nhan) cung la mau thuan
])
def test_unconfirmed_lower_keeps_7(tmp_path, reads):
    c = _ctx(tmp_path)
    for r in reads:
        hqlevel.record(c, r, "x")
    assert _levels(c) == (7, 7)


def test_stale_evidence_expires(tmp_path, monkeypatch):
    c = _ctx(tmp_path)
    now = [1000.0]
    monkeypatch.setattr(hqlevel.time, "time", lambda: now[0])
    hqlevel.record(c, [(6, True)], "x")
    now[0] += hqlevel.PENDING_TTL_S + 1
    assert hqlevel.record(c, [(6, True)], "x") is None and _levels(c) == (7, 7)


def test_up_rules_unchanged(tmp_path):
    c = _ctx(tmp_path, prev=None)
    assert hqlevel.record(c, [(4, False)], "x") == 4
    assert hqlevel.record(c, [(5, False)], "x") == 5
    assert hqlevel.record(c, [(7, True)], "x") is None
    assert hqlevel.record(c, [(7, True)], "x") is None            # nhay > 1: 2 lan trong CUNG 1 dot (P13d)
    assert hqlevel.record(c, [(7, True), (7, True)], "x") == 7
    assert _levels(c) == (7, 7)


def test_judge_lower_needs_every_read_to_agree():
    assert hqlevel.judge_hq(7, [(6, True), (6, True)]) == 6
    assert hqlevel.judge_hq(7, [(6, True), (6, True), (7, True)]) == 7
    assert hqlevel.judge_hq(7, [(6, True), (6, True), (5, False)]) is None


def test_stored_takes_higher_of_state_and_memory(tmp_path):
    c = _ctx(tmp_path)
    c.store.d["hq_level"] = 6                                     # state da bi ban cu ghi de
    assert hqlevel.stored(c) == 7
    hqlevel.record(c, [(7, True)], "x")
    assert _levels(c) == (7, 7)


def test_runner_state_copy_never_lowers_memory():
    keys = Runner.FACT_KEYS
    assert Runner.facts_to_copy({"hq_level": 6}, {"hq_level": 7}, keys) == {}
    assert Runner.facts_to_copy({"hq_level": 8}, {"hq_level": 7}, keys) == {"hq_level": 8}
    assert Runner.facts_to_copy({"hq_level": 6}, {}, keys) == {"hq_level": 6}


@pytest.mark.parametrize("misread", [33, 70])
def test_hq_cap_from_misread_does_not_write(tmp_path, monkeypatch, misread):
    c = _ctx(tmp_path)
    _upgrade_screen(c, monkeypatch, misread)
    assert build.upgrade_here(c) == "hq_cap" and _levels(c) == (7, 7)
    monkeypatch.setattr(upgrade, "goto_hq", lambda *a, **k: (1, 1, 1.0))
    c.back_out = c.ensure_city = lambda *a: None
    assert upgrade.hq_chain(c) == (0, "hq_cap") and _levels(c) == (7, 7)     # truoc day ghi 30


def test_read_hq_single_lower_then_equal_keeps_7(tmp_path, monkeypatch):
    c = _ctx(tmp_path)
    c.ensure_city = c.tap = c.save_debug = lambda *a, **k: None
    c.shot = lambda: IMG
    seq = iter([(6, True, ""), (7, True, "")])
    monkeypatch.setattr(observe.time, "sleep", lambda s: None)
    monkeypatch.setattr(observe, "ocr_hq_ex", lambda img: next(seq))
    assert observe.read_hq(c, every_h=0) == 7 and _levels(c) == (7, 7)


def test_read_hq_two_panel_opens_agree_lower(tmp_path, monkeypatch, caplog):
    c = _ctx(tmp_path)
    opens = []
    c.ensure_city = c.save_debug = lambda *a, **k: None
    c.tap = lambda *a, **k: opens.append(1)
    c.shot = lambda: IMG
    monkeypatch.setattr(observe, "ocr_hq_ex", lambda img: (6, True, ""))
    assert observe.read_hq(c, every_h=0) == 6 and len(opens) == 2
    assert _levels(c) == (6, 6) and len(_warnings(caplog)) == 1
