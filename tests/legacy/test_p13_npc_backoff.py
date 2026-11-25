"""P13-12: danh le phien quan tu nhiem vu (HQ < 15): thanh cong thi giu; that bai -> lui, khong lap moi lan ghe.
HQ < 15 khong bao gio tham gia tap ket Co giap."""
import types

from bot import quest_rules
from bot.modules import mainquest, rebels


class Mem:
    def __init__(self):
        self.f = {}

    def fact(self, i, k):
        return self.f.get(k)

    def set_fact(self, i, k, v):
        self.f[k] = v


def _ctx():
    return types.SimpleNamespace(mem=Mem(), dev=types.SimpleNamespace(idx=3))


def test_backoff_schedule():
    hs = [quest_rules.npc_backoff_s(n) / 3600 for n in (1, 2, 3, 4, 5, 9)]
    assert hs == [2, 4, 8, 16, 24, 24]


def test_gate():
    assert quest_rules.npc_gate(None, 100)[0]
    assert not quest_rules.npc_gate(500, 100)[0]
    assert quest_rules.npc_gate(500, 600)[0]


def test_failure_backs_off_and_does_not_repeat(monkeypatch):
    calls = []
    monkeypatch.setattr(mainquest, "_npc_attack_once", lambda c, mq: calls.append(1) or "npc_none")
    c = _ctx()
    assert mainquest.npc_attack(c, {}) == "npc_none"
    assert mainquest.npc_attack(c, {}) == "npc_wait"            # ghe sau: khong mo bang, khong thu lai
    assert len(calls) == 1 and c.mem.f["npc_fail_n"] == 1
    c.mem.f["npc_fail_until"] = 0                              # het han lui
    assert mainquest.npc_attack(c, {}) == "npc_none" and c.mem.f["npc_fail_n"] == 2     # lui gap doi


def test_success_clears_backoff(monkeypatch):
    monkeypatch.setattr(mainquest, "_npc_attack_once", lambda c, mq: "npc_sent")
    c = _ctx()
    c.mem.f.update(npc_fail_n=3, npc_fail_until=0)
    assert mainquest.npc_attack(c, {}) == "npc_sent"
    assert c.mem.f["npc_fail_n"] == 0 and c.mem.f["npc_fail_until"] is None


def test_wait_is_not_success():
    assert "npc_wait" not in mainquest.SUCCESS


def test_hq_below_15_never_joins_mech_rally():
    mem = types.SimpleNamespace(fact=lambda i, k: 14)
    assert not rebels.join_hq_ok(mem, 3, {"min_hq_level": 15})
    assert not rebels.join_hq_ok(types.SimpleNamespace(fact=lambda i, k: None), 3, {})
