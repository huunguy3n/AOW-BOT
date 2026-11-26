"""P13e/P13f: so tho dung duoc theo may + lap tho ranh + lich xay (ham thuan / scheduler)."""
import types

import yaml

from aowbot.domain import builders as B
from aowbot.domain import drain
from bot import build, scheduler
from bot.memory import Memory
from bot.modules import upgrade


def test_effective_is_per_machine_not_game_total():
    assert B.effective_max(1, 2) == 1          # P13f-1: farm game bao x/2 nhung o thu 2 chua mua -> 1
    assert B.effective_max(1, 1) == 1
    assert B.effective_max(2, 1) == 1          # game bao it hon cau hinh -> kep xuong
    assert B.effective_max(1, None) == 1       # chua doc duoc -> cau hinh
    assert B.effective_max(1, 5) == 1
    assert B.effective_max(2, 2) == 2          # #1 van 2
    assert B.effective_max(None, 2) == 1


def _ctx(cfg_max=1, total=None):
    mem = types.SimpleNamespace(fact=lambda i, k: total if k == "builders_total" else None)
    return types.SimpleNamespace(cfg={"build": {"max_builders": cfg_max}}, dev=types.SimpleNamespace(idx=5), mem=mem)


def test_build_max_builders_from_fact_and_arg():
    assert build.max_builders(_ctx(1, 2)) == 1
    assert build.max_builders(_ctx(1, None), 2) == 1
    assert build.max_builders(_ctx(2, 2)) == 2
    assert build.max_builders(_ctx(2, None)) == 2


def test_farm_one_of_two_is_full(monkeypatch):
    c = _ctx(1, 2)
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: (0, 2))
    ok, why = upgrade.builder_idle(c)
    assert ok and "dung toi da 1" in why
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: (1, 2))
    assert upgrade.builder_idle(c)[0] is False       # 1/2 maxb=1 = DAY, khong lap o 2
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: (2, 2))
    assert upgrade.builder_idle(c)[0] is False


def test_main_account_two_builders(monkeypatch):
    c = _ctx(2, 2)
    for busy, idle in ((0, True), (1, True), (2, False)):
        monkeypatch.setattr(upgrade.build, "builders", lambda ctx, b=busy: (b, 2))
        assert upgrade.builder_idle(c)[0] is idle


def test_idle_slots_per_machine():
    assert drain.idle_slots({"build": (0, 2)}, 1) == ["build"]
    assert drain.idle_slots({"build": (1, 2)}, 1) == []          # farm 1/2 = khong ranh
    assert drain.idle_slots({"build": (1, 2)}, 2) == ["build"]   # #1
    assert drain.idle_slots({"build": (2, 2)}, 2) == []
    assert drain.idle_slots({"build": (1, 1)}, 2) == []


def test_repo_config_has_no_game_slot_path():
    with open("config.yaml", encoding="utf-8") as f:
        bc = yaml.safe_load(f)["build"]
    assert bc["max_builders"] == 1 and "use_game_slots" not in bc and "max_builders_cap" not in bc


def test_fill_state_runs_at_once_when_idle():
    f = B.FillState()
    assert f.decide(1, 0, 0, False) is False        # het tho
    assert f.decide(0, 1, 0, False) is True         # tho vua ranh -> xay NGAY
    assert f.decide(1, 0, 1, False) is False        # xay duoc -> day
    assert f.decide(0, 1, 1, False) is True         # cong trinh ngan xong -> xay tiep


def test_fill_state_does_not_loop_without_progress():
    f = B.FillState()
    assert f.decide(0, 1, 0, False) is True
    assert f.decide(0, 1, 0, False) is False        # lan chen khong xay duoc gi -> khong lap
    assert f.decide(0, 1, 0, True) is True          # vua co them tai nguyen -> thu lai
    assert f.decide(0, 1, 0, True) is True
    assert f.decide(0, 1, 0, True) is False         # het luot thu lai


def test_fill_state_retries_when_another_builder_finishes():
    f = B.FillState()
    assert f.decide(1, 1, 0, False) is True         # #1: 1/2
    assert f.decide(1, 1, 0, False) is False
    assert f.decide(0, 2, 0, False) is True         # tho kia vua xong
    g = B.FillState()
    g.attempt(0)                                          # buoc xay theo thu tu thuong, khong xay duoc
    assert g.decide(0, 1, 0, False) is False


def test_fill_state_round_cap():
    f, n = B.FillState(max_rounds=3), 0
    for built in range(20):
        n += f.decide(0, 1, built)
    assert n == 3
    assert B.FILL_STEPS[:2] == ("upgrade", "construct")   # nha chinh / tien quyet duoc chon truoc


def _mem(tmp_path, busy, total=2):
    m = Memory(str(tmp_path / "m.db"))
    m.set_fact(5, "builders_busy", busy)
    m.set_fact(5, "builders_total", total)
    return m


def test_schedule_farm_uses_one_builder(tmp_path):
    m = _mem(tmp_path, 0)
    cfg = {"build": {"max_builders": 1, "hq_max_level": 30}}
    p = scheduler.plan_step(m, 5, "upgrade", scheduler.sched_cfg(cfg), 1e9, {}, cfg)
    assert p.ready and "(0/1)" in p.why
    p = scheduler.plan_step(m, 5, "construct", scheduler.sched_cfg(cfg), 1e9, {}, cfg)
    assert p is not None and p.ready               # construct co plan xay (BUILD_STEPS)
    m.set_fact(5, "builders_busy", 1)              # 1/2 tren farm
    p = scheduler.plan_step(m, 5, "upgrade", scheduler.sched_cfg(cfg), 1e9, {}, cfg)
    assert "tho xay ranh" not in p.why and not p.confident
    main = {"build": {"max_builders": 2, "hq_max_level": 30}}
    p = scheduler.plan_step(m, 5, "upgrade", scheduler.sched_cfg(main), 1e9, {}, main)
    assert p.ready and "(1/2)" in p.why            # #1 con 1 tho ranh


def test_build_steps_forced_when_builder_idle(tmp_path):
    m = _mem(tmp_path, 0)
    cfg = {"build": {"max_builders": 1}}
    order = ["warday", "notify", "upgrade", "mainquest", "construct", "quests"]
    names = list(order)
    out = scheduler.with_build_steps(m, 5, ["warday", "notify"], names, order, cfg, 1e9)
    assert out == ["warday", "notify", "upgrade", "mainquest", "construct"]
    m.set_fact(5, "builders_busy", 1)
    assert scheduler.with_build_steps(m, 5, ["warday"], names, order, cfg, 1e9) == ["warday"]
    # may tat buoc do trong cai dat (khong nam trong names) -> khong ep
    m.set_fact(5, "builders_busy", 0)
    assert "construct" not in scheduler.with_build_steps(m, 5, ["warday"], ["warday", "upgrade"], order, cfg, 1e9)


def test_reschedule_when_all_builders_busy_uses_build_timer(tmp_path):
    m = _mem(tmp_path, 1)
    m.set_timer(5, "build:0", 1e9 + 600, "ocr_bar", 0.7)
    cfg = {"build": {"max_builders": 1, "hq_max_level": 30}}
    p = scheduler.plan_step(m, 5, "upgrade", scheduler.sched_cfg(cfg), 1e9, {}, cfg)
    assert not p.ready and p.at == 1e9 + 600 and "xay xong" in p.why
