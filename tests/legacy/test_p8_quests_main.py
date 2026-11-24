"""P8-4 (chu du an 2026-11-24): bat lai nhiem vu cho #1 - PM da sua data/settings.json
instances."1".modules.quests = true (file bi gitignore, KHONG sua o day, chi doc). #1 LAM nhiem vu (bam "Den"),
khong chi nhan; bang khong cuon, nhan dong xong tren cung; "Den" chi loai an toan
(khong mua / kim cuong / tan cong nguoi choi)."""
import json
import os
import time
import types

import pytest
import yaml

from bot import build, hqplan, quest_rules, runner, scheduler, stepgate
from bot.memory import Memory
from bot.modules import quests
from bot.state import deep_merge

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _cfg_i1():
    p = os.path.join(ROOT, "data", "settings.json")
    if not os.path.exists(p):
        pytest.skip("thieu data/settings.json (gitignore)")
    with open(os.path.join(ROOT, "config.yaml"), encoding="utf-8") as f:
        base = yaml.safe_load(f)
    with open(p, encoding="utf-8") as f:
        st = json.load(f)
    return deep_merge(deep_merge(base, st.get("global")), (st.get("instances") or {}).get("1")), st


@pytest.mark.fixtures
def test_settings_i1_quests_enabled_full_mode():
    cfg, st = _cfg_i1()
    assert st["instances"]["1"]["modules"]["quests"] is True             # PM da sua (khong commit)
    assert cfg["modules"]["quests"] is True
    assert quest_rules.quests_mode(bool(cfg["modules"]["quests"]), cfg.get("quests")) == "full"   # bam "Den"
    assert cfg["build"].get("follow_quests", True) is True


@pytest.mark.fixtures
def test_settings_i1_stepgate_lets_quests_run(tmp_path):
    cfg, _ = _cfg_i1()
    mem = Memory(str(tmp_path / "m.db"))
    now = time.time()
    g = stepgate.check(mem, 1, "quests", cfg, now, {})
    assert g.run, g.why
    assert not stepgate.planned_skip(mem, 1, "quests", cfg, now)


def test_settings_file_not_modified_by_tests():
    """Bao ve: test chi DOC settings.json (PM quan ly file nay)."""
    p = os.path.join(ROOT, "data", "settings.json")
    if not os.path.exists(p):
        pytest.skip("thieu data/settings.json")
    before = os.path.getmtime(p)
    _cfg_i1()
    assert os.path.getmtime(p) == before


@pytest.mark.parametrize(("title", "go"), [
    ("Tang 4 Xuong Thuc Pham den cap 26", True),          # xay -> bam Den (build.upgrade_here, khong "Tang cap ngay")
    ("Tang Xuong kien truc den cap 30", True),
    ("Tang 5 Tuong len cap 90", True),                     # tuong -> follow
    ("Mua 1 goi qua bat ky", False),                       # tra phi
    ("Nap the lan dau", False),
    ("Tieu hao 500 kim cuong", False),
    ("Tan cong can cu nguoi choi 3 lan", False),           # tan cong nguoi choi
    ("Pha huy 1 thanh pho", False),
    ("Cuop boc xe khai thac 2 lan", False),                # buoc play (so luc chien P8-2)
    ("Huan luyen 2000 Tank bac 6", False),                 # buoc train
    ("Tham gia tap ket tan cong 1 lan phan quan Co giap", False),
])
def test_row_plan_only_safe_kinds(title, go):
    assert quests.row_plan(title)[0] is go


@pytest.mark.parametrize("title", ["Mua 1 goi qua bat ky", "Tieu hao 500 kim cuong", "Tan cong can cu nguoi choi"])
def test_forbidden_kinds(title):
    kind, module = quest_rules.classify(title)
    assert quest_rules.forbidden(kind) and module == quest_rules.FORBIDDEN and quest_rules.delegated(kind)


def test_build_kinds_not_forbidden():
    for t in ("Tang 4 Xuong Thuc Pham den cap 26", "Sua chua cong trinh", "Xay dung Benh vien"):
        assert not quest_rules.forbidden(quest_rules.classify(t)[0])


# ---------------------------------------------------------------- luong quests.run (full) voi bang gia
class V:
    def find_all(self, img, name, **k):
        # 3 nut Den tren -> duoi: dong tra phi, dong tan cong nguoi choi, dong xay
        return [(470, 300, 0.95), (470, 420, 0.95), (470, 540, 0.95)] if name == "quest/btn_go" else []


class Ctx:
    def __init__(self):
        self.cfg = {"quests": {"main": False, "max_go_per_run": 3}, "build": {"follow_quests": True},
                    "mainquest": {}}
        self.quests_claim_only = False
        self.dev = types.SimpleNamespace(idx=1)
        self.v, self.taps, self.store, self.mem = V(), [], None, None

    def ensure_city(self):
        pass

    def shot(self):
        return None

    def claim_buttons(self, max_taps=8):
        return 0

    def claim_loop(self, names, max_taps=8, th=0.85):
        return 0

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def back_out(self, n=1):
        pass


def test_full_mode_taps_only_safe_row(monkeypatch):
    titles = {300: "Mua 1 goi qua bat ky", 420: "Tan cong can cu nguoi choi 3 lan", 540: "Tang Xuong Thep den cap 20"}
    monkeypatch.setattr(quests, "claim_dot_tabs", lambda ctx: 1)          # dong xong tren cung -> nhan
    monkeypatch.setattr(quests, "open_tab", lambda ctx, tab: True)
    monkeypatch.setattr(quests, "row_title", lambda img, p: titles[p[1]])
    monkeypatch.setattr(quests, "row_key", lambda img, p: p[1])
    monkeypatch.setattr(quests, "_battle_blocked", lambda ctx: False)
    monkeypatch.setattr(quests, "_hq_rush", lambda ctx: False)
    monkeypatch.setattr(quests, "_blocks", lambda ctx, now: {})
    monkeypatch.setattr(hqplan, "yield_builder", lambda ctx, step: False)
    monkeypatch.setattr(build, "builders", lambda ctx: (0, 2))
    monkeypatch.setattr(build, "upgrade_here", lambda ctx: "started")
    monkeypatch.setattr(build, "quick_wait", lambda ctx: None)
    c = Ctx()
    assert quests.run(c) == 2                                              # 1 nhan + 1 xay
    assert c.taps == [(470, 540)]                                          # KHONG cham dong tra phi / nguoi choi


@pytest.mark.fixtures
def test_settings_i1_scheduler_includes_quests(tmp_path):
    cfg, _ = _cfg_i1()
    mem = Memory(str(tmp_path / "m.db"))
    order = [n for n, _ in runner.ORDER]
    v = scheduler.decide_one(mem, 1, order, dict(cfg["modules"]), cfg, time.time())
    assert "quests" in v.steps
    assert "quests" in scheduler.piggyback_steps(mem, 1, order, dict(cfg["modules"]), cfg, time.time())
