"""Q0 (doc hang cho cot trai) + Q1 (thu tu uu tien chu du an, cham do dan vao tien trinh phu)."""
import types

import pytest

from bot import buttons, queues, scheduler
from bot.memory import Memory
from bot.modules import heal, notify, rebels, reddots, research, upgrade
from bot.runner import ORDER


# ---------------------------------------------------------------- Q0
@pytest.mark.parametrize("s, want", [("0/2", (0, 2)), (" 1 / 3 ", (1, 3)), ("/", None), ("0/13", None),
                                     ("3/2", None), ("02", None), ("", None), ("0/0", None)])
def test_parse(s, want):
    assert queues.parse(s) == want


def test_vote_needs_two_agreeing_reads():
    assert queues.vote(["/", "0/2", "/2", "0/2"]) == (0, 2)
    assert queues.vote(["0/2", "1/2"]) is None                 # hoa -> khong doan
    assert queues.vote(["0/2"]) is None                        # 1 phieu chua du
    assert queues.vote(["1/2", "1/2", "0/2"]) == (1, 2)


def test_idle_slots():
    assert queues.idle((1, 2)) == 1 and queues.idle((3, 3)) == 0 and queues.idle(None) is None


# ---------------------------------------------------------------- Q1
def test_order_follows_owner_priority():
    names = [n for n, _ in ORDER]
    prio = ["reddots", "play", "intel", "rebels"]
    assert [names.index(n) for n in prio] == sorted(names.index(n) for n in prio)
    assert max(names.index(n) for n in prio) < min(names.index(n) for n in ("train", "quests", "research"))
    assert names[-1] == "gather"     # P7-1 (chu du an 2026-11-24): thu thap luon cuoi luot


class Img:
    """Gia lap vision: tra vi tri icon theo ten anh mau."""

    def __init__(self, at):
        self.at = at

    def find(self, img, name, **k):
        return self.at.get(name)


@pytest.mark.parametrize("tpl, pos, dot, kind", [
    ("play/btn_open", (429, 905), (455, 880), "play"),
    ("research/icon_queue", (33, 208), (57, 190), "research"),
    ("train/queue_icon", (33, 262), (57, 245), "train"),
    ("build/icon_builder", (33, 142), (57, 124), "build"),
])
def test_queue_and_play_dots_route_to_modules(tpl, pos, dot, kind):
    ctx = types.SimpleNamespace(v=Img({tpl: (*pos, 0.95)}))
    assert reddots._kind(ctx, None, dot) == kind


def test_route_gates_follow_options():
    assert reddots.allowed("play", {"modules": {"play": False}})[0] is False
    assert reddots.allowed("rally", {"modules": {"rebels": False}})[0] is False
    assert reddots.allowed("rally", {"modules": {}})[0]
    assert reddots.allowed("train", {"modules": {"train": True}})[0]


# ---------------------------------------------------------------- Q2 xay theo nha chinh


@pytest.mark.parametrize("text, ok", [("2xuong kién tric Lv.4 > ghuong kiéntric}v.4 =,", True),
                                      ("Xưởng kiến trúc Lv.30", True), ("a Radar Lv.1 f fay.", False), ("", False)])
def test_hq_label(text, ok):
    assert upgrade.is_hq_label(text) is ok


def test_upgrade_step_runs_before_quest_building():
    names = [n for n, _ in ORDER]
    assert names.index("train") < names.index("upgrade") < names.index("mainquest") < names.index("quests")


def test_scheduler_drops_build_goal_at_hq_cap(tmp_path):
    mem = Memory(str(tmp_path / "m.db"))
    mem.set_fact(1, "builders_busy", 0)
    sc = scheduler.sched_cfg({})
    cfg = {"build": {"hq_max_level": 30, "max_builders": 1}}
    mem.set_fact(1, "hq_level", 12)
    assert scheduler.plan_step(mem, 1, "upgrade", sc, 1e9, {}, cfg).ready
    mem.set_fact(1, "hq_level", 30)
    assert scheduler.plan_step(mem, 1, "upgrade", sc, 1e9, {}, cfg) is None


class HqCtx:
    def __init__(self, hq=10, builders=(0, 2)):
        self.cfg = {"build": {"hq_max_level": 30, "max_builders": 1}}
        self.dev = types.SimpleNamespace(idx=1)
        self.mem = types.SimpleNamespace(fact=lambda i, k: hq if k == "hq_level" else None, set_fact=lambda *a: None)
        self.b, self.calls = builders, []

    def ensure_city(self):
        self.calls.append("city")

    def back_out(self, *a):
        pass


def test_upgrade_skips_when_no_idle_builder(monkeypatch):
    c = HqCtx(builders=(2, 2))
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: ctx.b)
    monkeypatch.setattr(upgrade, "goto_hq", lambda ctx: pytest.fail("khong duoc toi nha chinh"))
    assert upgrade.run(c) == 0


def test_upgrade_at_hq_cap_never_goes_to_hq(monkeypatch):
    seen = []
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: ctx.b)
    monkeypatch.setattr(upgrade, "goto_hq", lambda ctx: pytest.fail("HQ30: bo muc tieu xay nha chinh"))
    monkeypatch.setattr(upgrade, "other_buildings", lambda ctx: seen.append(1) or 0)
    assert upgrade.run(HqCtx(hq=30)) == 0 and seen == [1]      # P13f: tho ranh van duoc nang nha khac


def test_upgrade_starts_from_hq(monkeypatch):
    monkeypatch.setattr(upgrade.build, "builders", lambda ctx: ctx.b)
    monkeypatch.setattr(upgrade, "goto_hq", lambda ctx: (317, 557, 0.95))
    monkeypatch.setattr(upgrade.build, "upgrade_here", lambda ctx: "started")
    monkeypatch.setattr(upgrade.build, "quick_wait", lambda ctx: False)
    assert upgrade.run(HqCtx()) == 1


def test_builder_dot_routes_to_upgrade():
    assert reddots.allowed("build", {"modules": {"upgrade": False}})[0] is False


# ---------------------------------------------------------------- man chi tiet tuong: lap toi khi het viec
def test_hero_detail_rechecks_levelup_after_star(monkeypatch):
    seq = {"lv": [0, 3, 0], "star": [2, 0, 0], "story": [0, 1, 0]}
    monkeypatch.setattr(notify, "_hero_levelup", lambda ctx: seq["lv"].pop(0))
    monkeypatch.setattr(notify, "_hero_star", lambda ctx: seq["star"].pop(0))
    monkeypatch.setattr(notify, "hero_story", lambda ctx: seq["story"].pop(0))
    monkeypatch.setattr(notify, "_hero_exp", lambda ctx: 0)       # P9-8: khong thieu EXP
    assert notify.hero_detail(None) == 6        # truoc: 2 (tang sao roi bo, nut Tang cap con cham do)
    assert seq == {"lv": [], "star": [], "story": []}


# ---------------------------------------------------------------- Q3 nghien cuu: nhanh phu / cho nha chinh


class ResCtx:
    def __init__(self, screens):
        self.screens = list(screens)
        self.taps = []
        self.dev = types.SimpleNamespace(idx=1)
        self.facts = {"hq_level": 20}
        self.mem = types.SimpleNamespace(fact=lambda i, k: self.facts.get(k),
                                         set_fact=lambda i, k, v: self.facts.__setitem__(k, v))
        self.v = types.SimpleNamespace(find=lambda img, n, **k: (1, 1, 1) if img == "hq" and n == "build/btn_upgrade"
                                       else None)

    def settle(self):
        return self.screens.pop(0)

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def find(self, *a, **k):
        return None

    def back_out(self, *a):
        pass


def fake_buttons(monkeypatch, table):
    B = buttons.Button
    monkeypatch.setattr(buttons, "with_text", lambda img, pat, roi=None, kinds=None:
                        [B(400, 800, 120, 40, "claim", 86, t) for t in table.get((img, "ngh" in pat), [])])
    monkeypatch.setattr(research, "verify_start", lambda ctx: "started")   # P2: kiem sau khi bam - test rieng


def test_research_node_starts(monkeypatch):
    fake_buttons(monkeypatch, {("node", True): ["nghien cuu"]})
    assert research.node(ResCtx(["node"])) == "started"


def test_research_follows_prerequisite_branch(monkeypatch):
    fake_buttons(monkeypatch, {("node", False): ["den"], ("pre", True): ["nghien cuu"]})
    c = ResCtx(["node", "pre", "pre"])
    assert research.node(c) == "started" and len(c.taps) == 2


def test_research_waits_for_hq_and_scheduler_skips(monkeypatch, tmp_path):
    fake_buttons(monkeypatch, {("node", False): ["den"]})
    c = ResCtx(["node", "hq"])
    assert research.node(c) == "wait_hq" and c.facts["research_wait_hq"] == 20
    assert research.wait_hq(c)
    c.facts["hq_level"] = 21
    assert not research.wait_hq(c) and c.facts["research_wait_hq"] is None
    mem = Memory(str(tmp_path / "m.db"))
    mem.set_fact(1, "hq_level", 20)
    mem.set_fact(1, "research_wait_hq", 20)
    assert not scheduler.plan_research(mem, 1, scheduler.sched_cfg({}), 1e9).ready


# ---------------------------------------------------------------- Q5 benh vien
@pytest.mark.parametrize("text, ok", [("Bệnh Viện Lv.2", True), ("benh vien lv 2", True), ("Radar Lv.1", False)])
def test_hospital_label(text, ok):
    assert heal.is_hospital_label(text) is ok


def test_heal_step_registered_and_runs_every_visit():
    names = [n for n, _ in ORDER]
    assert names.index("rebels") < names.index("heal") < names.index("gather")
    assert "heal" in scheduler.ALWAYS


# ---------------------------------------------------------------- Q6 phan quan: chon cap + o tim kiem
def test_pick_level():
    assert rebels.pick_level({"best": None, "fail": {}}, start=10, now=1e9) == 10
    assert rebels.pick_level({"best": 12, "fail": {}}, now=1e9) == 13
    assert rebels.pick_level({"best": 12, "fail": {"13": 1e9 - 60}}, now=1e9) == 12
    assert rebels.pick_level({"best": None, "fail": {"10": 1e9 - 60, "9": 1e9 - 60}}, start=10, now=1e9) == 8


def test_classify_building_and_lab_wait_scheduler(tmp_path):
    assert research.classify_building("Xuong kien truc") == "hq"
    assert research.classify_building("Viện nghiên cứu Lv.7") == "lab"
    assert research.classify_building("Vien nghien cuu") == "lab"
    assert research.classify_building("Kho") is None
    mem = Memory(str(tmp_path / "m2.db"))
    mem.set_fact(1, "hq_level", 20)
    mem.set_fact(1, "research_wait_lab_until", 2000.0)
    p = scheduler.plan_research(mem, 1, scheduler.sched_cfg({}), 1000.0)
    assert not p.ready and p.at == 2000.0
