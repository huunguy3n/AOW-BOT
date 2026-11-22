"""P2 muc 3 (PM 2026-11-23): chon node nghien cuu theo uu tien, xu ly het tai nguyen, an toan khi thieu anh mau."""
import logging
import types

import pytest

from bot import buttons, scheduler, tplneed
from bot.memory import Memory
from bot.modules import research


class V:
    """Vision gia: `have` = anh mau co trong kho; `seen` = {(anh, ten)} thay tren anh."""

    def __init__(self, have=(), seen=()):
        self.have, self.seen = set(have), set(seen)

    def has(self, name):
        return name in self.have

    def find(self, img, name, **k):
        return (400, 880, 0.95) if name in self.have and (img, name) in self.seen else None


class Ctx:
    def __init__(self, shots, v=None):
        self.shots = list(shots)
        self.v = v or V()
        self.taps, self.closed = [], 0
        self.dev = types.SimpleNamespace(idx=1)
        self.facts = {}
        self.mem = types.SimpleNamespace(fact=lambda i, k: self.facts.get(k),
                                         set_fact=lambda i, k, v: self.facts.__setitem__(k, v))

    def shot(self):
        return self.shots.pop(0) if len(self.shots) > 1 else self.shots[0]

    settle = shot

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def close_popups(self, n=5):
        self.closed += 1


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(research.time, "sleep", lambda s: None)
    monkeypatch.setattr(research, "record", lambda ctx, name, left: ctx.facts.__setitem__("rec", name))
    monkeypatch.setattr(buttons, "with_text", lambda img, pat, roi=None, kinds=None:
                        [buttons.Button(420, 880, 120, 40, "claim", 86, "nghien cuu")] if img == "panel" else [])


def test_verify_start_confirms_with_progress_bar(monkeypatch):
    monkeypatch.setattr(research, "busy", lambda v, img: ("Khai thac", 3600) if img == "tree_busy" else None)
    c = Ctx(["after", "tree_busy"])
    assert research.verify_start(c) == "started" and c.facts["rec"] == "Khai thac"


def test_verify_start_button_still_there_is_no_res(monkeypatch):
    monkeypatch.setattr(research, "busy", lambda v, img: None)
    c = Ctx(["panel"])
    assert research.verify_start(c) == "no_res" and c.closed


def test_verify_start_no_res_dialog_template(monkeypatch):
    monkeypatch.setattr(research, "busy", lambda v, img: None)
    c = Ctx(["dlg"], V(have={research.TPL_NORES}, seen={("dlg", research.TPL_NORES)}))
    assert research.verify_start(c) == "no_res"


def test_verify_start_unconfirmed_is_not_started(monkeypatch):
    monkeypatch.setattr(research, "busy", lambda v, img: None)
    assert research.verify_start(Ctx(["blank"])) == "no_res"


def test_start_buttons_prefers_template_and_never_taps_blind():
    c = Ctx(["x"], V(have={research.TPL_BTN}, seen={("panel", research.TPL_BTN)}))
    assert research.start_buttons(c, "panel") == [(400, 880, "tpl")]
    assert research.start_buttons(c, "other") == []            # co anh mau ma khong thay -> khong dung mau+chu


def test_start_buttons_falls_back_to_color_text_and_logs_missing(caplog):
    tplneed._last.clear()
    with caplog.at_level(logging.INFO, logger="aow"):
        assert research.start_buttons(Ctx(["x"]), "panel") == [(420, 880, "nghien cuu")]
        research.start_buttons(Ctx(["x"]), "panel")
    msgs = [r.getMessage() for r in caplog.records if "thieu anh mau research/btn_research" in r.getMessage()]
    assert len(msgs) == 1                                     # log 1 lan / gio, khong ngap log


def test_node_with_panel_template_but_not_seen_does_nothing(monkeypatch):
    monkeypatch.setattr(research, "build_inv", lambda ctx: None)
    c = Ctx(["weird"], V(have={research.TPL_PANEL}))
    assert research.node(c) == "unknown" and c.taps == []


def test_pick_node_priority_and_skips():
    cands = [(300, 500, 0, 3), (100, 200, 3, 3), (400, 200, 1, 5), (200, 200, 0, 1)]
    assert research.pick_node(cands, {}, 0, 0, 0) == (200, 200, 0, 1)        # tren -> duoi, trai -> phai, bo 3/3
    sk = {research.node_key(0, 0, 200, 200): 100}
    assert research.pick_node(cands, sk, 0, 0, 50) == (400, 200, 1, 5)
    assert research.pick_node(cands, sk, 0, 0, 150) == (200, 200, 0, 1)      # het han bo qua
    assert research.pick_node([(1, 1, 2, 2)], {}, 0, 0, 0) is None


def test_nores_backoff():
    e = research.note_nores(None, 0, base_min=60, cap_h=6)
    assert e == {"until": 3600, "n": 1}
    e = research.note_nores(e, 0)
    assert e["until"] == 7200 and e["n"] == 2
    for _ in range(6):
        e = research.note_nores(e, 0)
    assert e["until"] == 6 * 3600
    assert research.nores_until(e, 10) == 6 * 3600 and research.nores_until(e, 7 * 3600) is None
    assert research.nores_until(None, 0) is None and research.nores_until("rac", 0) is None


def test_run_skips_fast_when_out_of_resources(monkeypatch):
    c = Ctx(["x"])
    c.cfg = {"research": {}}
    c.facts[research.NORES_FACT] = {"until": research.time.time() + 600, "n": 1}
    monkeypatch.setattr(research, "open_research", lambda ctx: pytest.fail("khong duoc mo So Cong Nghe"))
    assert research.run(c) == 0


def test_scheduler_research(tmp_path):
    mem = Memory(str(tmp_path / "m.db"))
    sc = scheduler.sched_cfg({})
    mem.set_fact(1, "hq_level", 20)
    mem.set_fact(1, "queue_research", [0, 1])
    p = scheduler.plan_research(mem, 1, sc, 1e9)
    assert p.ready and "ranh" in p.why                       # hang nghien cuu ranh -> lam ngay
    mem.set_fact(1, "research_nores", {"until": 1e9 + 600, "n": 1})
    p = scheduler.plan_research(mem, 1, sc, 1e9)
    assert not p.ready and p.at == 1e9 + 600                  # thieu tai nguyen -> khong keo may
    mem.set_fact(1, "research_nores", None)
    for i in range(4):                                        # 4 lan ghe khong bat dau duoc -> gian chu ky
        mem.log_run(i, 1, "research", 1e9 - 100 + i, 1.0, "ok", "", 0)
    p = scheduler.plan_research(mem, 1, sc, 1e9)
    assert not p.ready and "khong bat dau duoc" in p.why
