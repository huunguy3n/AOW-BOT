"""P13-2: toc do - buoc sau khong lam lai viec reddots vua lam; cho ngan hon (settle 0.25 s, recheck city 6 s)."""
import inspect
import types

import yaml

from bot import ctx as ctxmod
from bot import runner, visit
from bot.modules import mission, rewards


def test_visit_helpers():
    c = types.SimpleNamespace()
    assert not visit.seen(c, "mail")
    visit.mark(c, "mail")
    assert visit.seen(c, "mail") and not visit.seen(c, "vip")


def test_runner_resets_visit_kinds_each_visit():
    assert "ctx.visit_kinds = set()" in inspect.getsource(runner)


def test_mission_skipped_when_reddots_opened_it(monkeypatch):
    c = types.SimpleNamespace(cfg={}, visit_kinds={"mission"})
    assert mission.run(c) == 0                      # khong cham gi (ctx khong co v / tap)


def test_rewards_skip_routes_handled_by_reddots(monkeypatch):
    calls = []
    monkeypatch.setattr(rewards, "run_until_clear", lambda *a, **k: calls.append("mail") or 0)
    monkeypatch.setattr(rewards, "run_route", lambda c, p, m: calls.append(p) or 0)
    monkeypatch.setattr(rewards, "ally_gift_until_clear", lambda *a, **k: calls.append("ally") or 0)
    c = types.SimpleNamespace(cfg={"rewards": {"routes": ["mail", "vip", "celebration"], "ally_gift": True}},
                              visit_kinds={"mail", "vip", "ally_gift"})
    rewards.run(c)
    assert calls == ["rewards/celebration/"]        # mail / vip / ally_gift da lam -> bo; tuyen khac van chay


def test_wait_defaults_shorter():
    assert inspect.signature(ctxmod.Ctx.settle).parameters["interval"].default <= 0.25
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["nav"]["skip_recheck_s"] >= 6
    assert cfg["speed"]["wait_scale"] <= 0.75 and cfg["learn"]["adaptive_wait"] is True
