"""M2-1 (chu du an 2026-11-28): ghi tran tu ben ngoai bang boc ham - hanh vi KHONG doi, ket qua tra ve nguyen."""
import os
import tempfile
import types

from bot import battles
from bot.memory import Memory
from bot.modules import campaign, notify, play


def _ctx(step="intel", power=1_000_000):
    d = tempfile.mkdtemp()
    c = types.SimpleNamespace(mem=Memory(os.path.join(d, "m.db")), cfg={"ml": {"battle_log": True}},
                              dev=types.SimpleNamespace(idx=4), step=step)
    c.store = types.SimpleNamespace(inst=lambda i: {"resources": {"power": power}})
    return c


def rows(c):
    return c.mem.query("SELECT kind, step, decision, pred, ours, enemy, result FROM battle_ev ORDER BY id")


def test_campaign_battle_wrapper_records_and_returns_same():
    c = _ctx()
    w = battles._wrap_campaign_battle(lambda ctx, only_win=True, pre_checked=False: "lose")
    assert w(c) == "lose"
    w2 = battles._wrap_campaign_battle(lambda ctx, only_win=True, pre_checked=False: "skip")
    assert w2(c) == "skip"
    assert rows(c) == [("intel", "intel", "fight", "win", 1_000_000, None, "lose"),
                       ("intel", "intel", "skip", "lose", 1_000_000, None, None)]


def test_loot_powers_from_power_check_then_result():
    c = _ctx(step="play")
    pc = battles._wrap_power_check(lambda g, o, m=0.0: (o > g, "ok" if o > g else "ho ve manh hon"))
    run = battles._wrap_play_run(lambda ctx: (pc(300, 200), pc(100, 200), lr(ctx)))
    lr = battles._wrap_loot_result(lambda ctx, timeout=120: "win")
    run(c)
    assert rows(c) == [("loot", "play", "skip", None, 200, 300, None), ("loot", "play", "fight", None, 200, 100, "win")]
    assert battles._tl.ctx is None


def test_legion_march_records_decision_not_no_march():
    c = _ctx()
    for r in ("no_march", "lose_pred", "marched"):
        assert battles._wrap_legion_march(lambda ctx, r=r: r)(c) == r
    assert [(k, d, p) for k, _, d, p, *_ in rows(c)] == [("legion", "skip", "lose"), ("legion", "march", "win")]


def test_switch_off_and_errors_swallowed():
    c = _ctx()
    c.cfg = {"ml": {"battle_log": False}}
    assert battles._wrap_play_fight(lambda ctx: "win")(c) == "win"
    assert rows(c) == []
    c2 = types.SimpleNamespace(mem=None, cfg={}, dev=None, step=None)
    assert battles._wrap_play_fight(lambda ctx: "lose")(c2) == "lose"     # khong co mem -> khong ghi, khong loi


def test_install_wraps_real_functions_once():
    battles.install()
    battles.install()
    for fn in (campaign.battle, play.fight, play.power_check, play._loot_result, play.run, notify.legion_march):
        assert getattr(fn, "_m2_wrapped", False)
        assert not getattr(getattr(fn, "__wrapped__", None), "_m2_wrapped", False)   # khong boc 2 lan
