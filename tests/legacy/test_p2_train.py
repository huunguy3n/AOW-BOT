"""P2 muc 4 (PM 2026-11-23): huan luyen dung train/btn_max neu co, an toan khi thieu anh, xu ly thieu tai nguyen."""
import logging
import time
import types

import pytest

from bot import tplneed
from bot.modules import train


class V:
    def __init__(self, have=(), seen=()):
        self.have, self.seen = set(have), set(seen)

    def has(self, name):
        return name in self.have

    def find(self, img, name, **k):
        return (300, 900, 0.9) if (img, name) in self.seen else None


class Ctx:
    def __init__(self, v, shots=("x",)):
        self.v, self.shots, self.tapped = v, list(shots), []
        self.dev = types.SimpleNamespace(idx=2)
        self.facts = {}
        self.mem = types.SimpleNamespace(fact=lambda i, k: self.facts.get(k),
                                         set_fact=lambda i, k, v: self.facts.__setitem__(k, v))

    def shot(self):
        return self.shots.pop(0) if len(self.shots) > 1 else self.shots[0]

    def tap_tpl(self, name, **k):
        self.tapped.append(name)
        return name in self.v.have


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(train.time, "sleep", lambda s: None)


def test_use_max_missing_template_logs_and_never_taps(caplog):
    tplneed._last.clear()
    c = Ctx(V())
    with caplog.at_level(logging.INFO, logger="aow"):
        assert train.use_max(c, {"use_max_button": True}) is False
    assert c.tapped == []
    assert any("thieu anh mau train/btn_max" in r.getMessage() for r in caplog.records)


def test_use_max_taps_when_template_present():
    c = Ctx(V(have={train.TPL_MAX}))
    assert train.use_max(c, {"use_max_button": True}) is True and c.tapped == [train.TPL_MAX]
    d = Ctx(V(have={train.TPL_MAX}))
    assert train.use_max(d, {}) is False and d.tapped == []      # mac dinh tat (chu du an 2026-11-23)
    assert train.use_max(Ctx(V(have={train.TPL_MAX})), {"use_max_button": False}) is False


def test_started_checks():
    assert train.started(Ctx(V(), ["gone"]))                                         # nut bien mat -> da luyen
    assert not train.started(Ctx(V(seen={("p", "train/btn_train")}), ["p", "p"]))    # nut con 2 lan -> chua
    assert train.started(Ctx(V(seen={("p", "train/btn_train")}), ["p", "q"]))        # lan 2 da chuyen man
    v = V(have={"common/msg_insufficient"}, seen={("m", "common/msg_insufficient")})
    assert not train.started(Ctx(v, ["m"]))


def test_run_skips_while_out_of_resources(monkeypatch):
    c = Ctx(V())
    c.cfg = {"train": {}}
    c.facts[train.NORES_FACT] = {"until": time.time() + 600, "n": 1}
    c.ensure_city = lambda: pytest.fail("khong duoc mo thanh pho")
    assert train.run(c) == 0


def test_run_skips_when_all_barracks_busy(monkeypatch):
    c = Ctx(V())
    c.cfg = {"train": {}}
    c.ensure_city = lambda: None
    monkeypatch.setattr(train, "queue_full", lambda ctx: True)
    monkeypatch.setattr(train, "train_once", lambda ctx, tc: pytest.fail("hang day - khong mo bang"))
    assert train.run(c) == 0


def test_run_stops_on_no_res_and_clears_after_success(monkeypatch):
    seq = ["no_res"]
    c = Ctx(V())
    c.cfg = {"train": {}}
    c.ensure_city = c.back_out = lambda *a: None
    c.help_and_free = lambda **k: None
    monkeypatch.setattr(train, "queue_full", lambda ctx: None)
    monkeypatch.setattr(train, "train_once", lambda ctx, tc: seq.pop(0))
    assert train.run(c) == 0 and seq == []
    seq[:] = [True, True, False]
    c.facts[train.NORES_FACT] = {"until": 0, "n": 2}
    assert train.run(c) == 2 and c.facts[train.NORES_FACT] is None
