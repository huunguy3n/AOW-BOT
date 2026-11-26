"""P13e: so tho hieu luc + lap tho ranh + lich xay (ham thuan / scheduler)."""
import types

from aowbot.domain import builders as B
from aowbot.domain import drain
from bot import build, scheduler
from bot.memory import Memory
from bot.modules import upgrade


def test_effective_uses_game_slots():
    assert B.effective_max(1, 2) == 2          # farm cau hinh 1, game 0/2 -> 2
    assert B.effective_max(1, 1) == 1          # o thu 2 chua co -> giu 1 (khong thue)
    assert B.effective_max(2, 1) == 1
    assert B.effective_max(1, None) == 1       # chua doc duoc -> cau hinh
    assert B.effective_max(1, 5) == 2          # tran cung
    assert B.effective_max(1, 2, use_game=False) == 1
    assert B.effective_max(2, 2) == 2          # #1 van 2


def _ctx(cfg_max=1, total=None):
    mem = types.SimpleNamespace(fact=lambda i, k: total if k == "builders_total" else None)
    return types.SimpleNamespace(cfg={"build": {"max_builders": cfg_max}}, dev=types.SimpleNamespace(idx=5), mem=mem)


def test_build_max_builders_from_fact_and_arg():
    assert build.max_builders(_ctx(1, 2)) == 2
    assert build.max_builders(_ctx(1, None)) == 1
    assert build.max_builders(_ctx(1, None), 2) == 2


def test_builder_idle_two_slots_no_hire(monkeypatch):
    c = _ctx(1, None)
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: (0, 2))
    ok, why = upgrade.builder_idle(c)
    assert ok and "dung toi da 2" in why
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: (1, 2))
    assert upgrade.builder_idle(c)[0] is True        # tho thu 2 con ranh
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: (2, 2))
    assert upgrade.builder_idle(c)[0] is False
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: (0, 1))
    assert upgrade.builder_idle(c)[0] is True and "toi da 1" in upgrade.builder_idle(c)[1]
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: (1, 1))
    assert upgrade.builder_idle(c)[0] is False       # o thu 2 chua co: KHONG dung / thue


def test_idle_slots_two():
    assert drain.idle_slots({"build": (0, 2)}, 2) == ["build"]
    assert drain.idle_slots({"build": (1, 2)}, 2) == ["build"]
    assert drain.idle_slots({"build": (2, 2)}, 2) == []
    assert drain.idle_slots({"build": (1, 1)}, 2) == []


def test_fill_steps():
    en = {"construct": True, "upgrade": True, "mainquest": False, "quests": True}
    assert B.fill_steps(2, 0, 2, True, en) == ["construct", "upgrade", "quests"]
    assert B.fill_steps(0, 0, 2, True, en) == []            # het tho ranh
    assert B.fill_steps(1, 1, 2, False, en) == []           # vong truoc khong bat dau duoc -> dung
    assert B.fill_steps(1, 1, 2, True, en) != []
    assert B.fill_steps(1, 2, 2, True, en) == []            # het vong


def _mem(tmp_path, busy, total=2):
    m = Memory(str(tmp_path / "m.db"))
    m.set_fact(5, "builders_busy", busy)
    m.set_fact(5, "builders_total", total)
    return m


def test_schedule_idle_shows_two_slots(tmp_path):
    m = _mem(tmp_path, 0)
    cfg = {"build": {"max_builders": 1, "hq_max_level": 30}}
    p = scheduler.plan_step(m, 5, "upgrade", scheduler.sched_cfg(cfg), 1e9, {}, cfg)
    assert p.ready and "(0/2)" in p.why
    p = scheduler.plan_step(m, 5, "construct", scheduler.sched_cfg(cfg), 1e9, {}, cfg)
    assert p is not None and p.ready               # construct co plan xay (BUILD_STEPS)
    m.set_fact(5, "builders_busy", 2)
    p = scheduler.plan_step(m, 5, "upgrade", scheduler.sched_cfg(cfg), 1e9, {}, cfg)
    assert "tho xay ranh" not in p.why and not p.confident   # 2/2 ban: khong con trigger 'tho ranh'


def test_build_steps_forced_when_builder_idle(tmp_path):
    m = _mem(tmp_path, 0)
    cfg = {"build": {"max_builders": 1}}
    order = ["warday", "notify", "upgrade", "mainquest", "construct", "quests"]
    names = list(order)
    out = scheduler.with_build_steps(m, 5, ["warday", "notify"], names, order, cfg, 1e9)
    assert out == ["warday", "notify", "upgrade", "mainquest", "construct"]
    m.set_fact(5, "builders_busy", 2)
    assert scheduler.with_build_steps(m, 5, ["warday"], names, order, cfg, 1e9) == ["warday"]
    # may tat buoc do trong cai dat (khong nam trong names) -> khong ep
    m.set_fact(5, "builders_busy", 0)
    assert "construct" not in scheduler.with_build_steps(m, 5, ["warday"], ["warday", "upgrade"], order, cfg, 1e9)


def test_reschedule_when_all_builders_busy_uses_build_timer(tmp_path):
    m = _mem(tmp_path, 2)
    m.set_timer(5, "build:0", 1e9 + 600, "ocr_bar", 0.7)
    cfg = {"build": {"max_builders": 1, "hq_max_level": 30}}
    p = scheduler.plan_step(m, 5, "upgrade", scheduler.sched_cfg(cfg), 1e9, {}, cfg)
    assert not p.ready and p.at == 1e9 + 600 and "xay xong" in p.why
