"""P7-5 (chu du an 2026-11-24): bang nhiem vu KHONG cuon (hoan thanh luon tren cung); buoc quests khong bao gio chay o
live #1 vi cai dat may #1 `modules.quests: false` -> tat = chi nhan thuong (quests.claim_when_off)."""
import types

import yaml

from bot import quest_rules
from bot.modules import daily, quests


def test_live1_cause_quests_off_on_machine_now_claims():
    # tai hien live #1: cfg_for(#1) -> modules.quests False -> truoc day runner 'continue' im lang, khong lan nao chay
    assert quest_rules.quests_mode(False, {}) == "claim"
    assert quest_rules.quests_mode(True, {}) == "full"
    assert quest_rules.quests_mode(False, {"claim_when_off": False}) is None
    assert quest_rules.quests_mode(False, {}, forced=True) is None      # bam "Bat khien" / --modules: giu cai dat


def test_config_default_claims_when_off():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["quests"]["claim_when_off"] is True


class Ctx:
    def __init__(self, claim_only):
        self.cfg = {"quests": {}, "build": {"follow_quests": True}}
        self.quests_claim_only = claim_only
        self.dev = types.SimpleNamespace(idx=1)

    def ensure_city(self):
        pass


def test_claim_only_mode_never_taps_go(monkeypatch):
    monkeypatch.setattr(quests, "claim_dot_tabs", lambda ctx: 3)
    monkeypatch.setattr(quests, "open_tab", lambda ctx, tab: (_ for _ in ()).throw(AssertionError("khong mo bam Den")))
    assert quests.run(Ctx(True)) == 3


def test_daily_tab_no_scroll():
    swipes = []

    class V:
        def has(self, name):
            return False

        def list(self, prefix):
            return []

    c = types.SimpleNamespace(v=V(), dev=types.SimpleNamespace(swipe=lambda *a: swipes.append(a)), W=540, H=960,
                              claim_loop=lambda names, max_taps, th=0.9: 2, shot=lambda: None)
    assert daily._claim_tab(c, ["daily/claim_1"], 40) == 2
    assert swipes == []
