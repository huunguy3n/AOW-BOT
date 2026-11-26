"""P13l (chu du an t103u + "Tinh bao con lai"): thua 1 tran -> bo dung LOP ghim (bieu tuong + mau); nut khoa; thuoc
"Dung"; nha chinh thap lam Tinh bao moi luot, som.

Anh: tests/fixtures/p13l/intel_icons_types.png (423x455, chu du an khoanh cac loai ghim) va intel_map_faded.png (man
Tinh bao 540x960 co 1 ghim mo)."""
import types

import cv2
import numpy as np
import pytest
import yaml

from aowbot.domain import drain
from bot import guide_tile, memory, scheduler
from bot import intel_pins as P
from bot import intel_rules as IR
from bot.modules import campaign, notify, rebels
from bot.vision import Vision

D = "tests/fixtures/p13l/"
V = Vision("templates", 0.82)


class Loose:
    """Khung do chu ve de len vong chan 1 ghim sung tim tren anh nay -> ha nguong intel/pin_base 0,6 -> 0,55."""

    def __getattr__(self, name):
        return getattr(V, name)

    def find_all(self, img, name, th=None, **k):
        return V.find_all(img, name, th=0.55 if name == "intel/pin_base" else th, **k)

# (tam dau ghim) -> lop; du 8 loai trong yeu cau, 2 ghim sung tim cung 1 lop
EXPECTED = {(104, 121): "guns-purple", (57, 185): "guns-purple", (134, 215): "guns-blue", (348, 199): "guns-green",
            (244, 272): "skull-green", (278, 314): "skull-purple", (346, 95): "badge-gold", (152, 185): "crate-gold",
            (172, 303): "crate-grey"}


def _img(name):
    img = cv2.imread(D + name + ".png")
    assert img is not None, name
    return img


def _icons():
    return _img("intel_icons_types")


def test_every_pin_on_owner_image_is_classified():
    pins = P.find_pins(_icons(), V)
    assert len(pins) == len(EXPECTED), pins
    for (x, y), cls in EXPECTED.items():
        near = [p for p in pins if abs(p.x - x) <= 6 and abs(p.y - y) <= 6]
        assert len(near) == 1 and near[0].cls == cls, ((x, y), cls, near)


def test_factory_and_march_are_not_pins():
    for p in P.find_pins(_icons(), V):
        assert not (180 <= p.x <= 300 and 100 <= p.y <= 220), p          # nha may giua anh
        assert not p.y > 340, p                                           # doan quan duoi cung


def test_class_from_pin_base_positions():
    img = _icons()
    pins = P.find_pins(img, V)
    bases = Loose().find_all(img, "intel/pin_base", th=0.6, min_dist=15)
    got = [P.class_at(pins, x, y) for x, y, _ in bases]
    assert len(bases) == 8 and None not in got and got.count("guns-purple") == 2


def test_full_screen_and_faded_pin():
    img = _img("intel_map_faded")
    pins = P.find_pins(img, V)
    assert sorted(p.cls for p in pins) == sorted(["guns-blue", "skull-purple", "skull-blue", "crate-gold",
                                                  "crate-purple", "crate-gold", "skull-blue", "guns-blue"])
    bases = V.find_all(img, "intel/pin_base", th=0.6, min_dist=15)
    faded = [(x, y) for x, y, _ in bases if IR.faded_pin(img, x, y)]
    assert len(faded) == 1 and abs(faded[0][0] - 128) <= 6 and abs(faded[0][1] - 539) <= 6
    assert not IR.faded_pin(np.zeros((960, 540, 3), np.uint8), 100, 300)


# ---------- nho lop thua ----------
def test_lost_gate_needs_more_power():
    e = {"power": 100000, "at": 1000}
    assert IR.lost_gate(e, 100000, 2000) == (True, e)
    assert IR.lost_gate(e, 104999, 10**9)[0]                      # khong het han theo gio khi biet luc chien
    assert IR.lost_gate(e, None, 2000)[0]
    assert IR.lost_gate(e, 105000, 2000) == (False, None)
    assert IR.lost_gate(e, 109000, 2000, pct=10)[0] and not IR.lost_gate(e, 110000, 2000, pct=10)[0]
    assert IR.lost_gate(None, 1, 1) == (False, None)
    unknown = {"power": None, "at": 1000}
    assert IR.lost_gate(unknown, 90000, 2000) == (True, {"power": 90000, "at": 1000})
    assert IR.lost_gate(unknown, None, 2000) == (True, unknown)
    assert IR.lost_gate(unknown, None, 1000 + 25 * 3600) == (False, None)


class Mem:
    def __init__(self, power):
        self.facts = {"resources": {"power": power}, "hq_level": 8}

    def fact(self, idx, key, default=None):
        return self.facts.get(key, default)

    def set_fact(self, idx, key, value):
        self.facts[key] = value


class IntelCtx:
    def __init__(self, mem):
        self.cfg = {"notify": {"intel_rescans": 0}}
        self.v, self.mem, self.dev = Loose(), mem, types.SimpleNamespace(idx=3)
        self.taps = []

    def shot(self):
        return _icons()

    def find(self, name, **k):
        return (1, 1) if name == "intel/title" else None

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def close_popups(self, *a, **k):
        pass


def _run(monkeypatch, ctx, result_of):
    """Chay notify.intel; -> [lop ghim da cham] (theo thu tu)."""
    classes = []
    pins = P.find_pins(_icons(), V)

    def mission(c):
        x, y = c.taps[-1]
        cls = P.class_at(pins, x, y + 35)
        classes.append(cls)
        return result_of(cls)
    monkeypatch.setattr(notify, "done_ticks", lambda img: [])
    monkeypatch.setattr(notify, "energy", lambda c: 99)
    monkeypatch.setattr(notify, "intel_mission", mission)
    notify.intel(ctx, 20)
    return classes


def test_losing_blocks_only_that_class(monkeypatch, caplog):
    mem = Mem(100000)
    first = _run(monkeypatch, IntelCtx(mem), lambda cls: "lose" if cls == "guns-purple" else "win")
    assert first.count("guns-purple") == 1                       # ghim sung tim thu 2 bi bo ngay trong luot
    assert set(first) == set(EXPECTED.values()) - {"crate-gold"}   # hom cam bi che chan -> khong co pin_base
    assert mem.facts[notify.LOST_CLASSES]["guns-purple"]["power"] == 100000

    mem.facts["resources"] = {"power": 104000}                  # luot ghe sau, tang chua du
    with caplog.at_level("INFO", logger="aow"):
        later = _run(monkeypatch, IntelCtx(mem), lambda cls: "win")
    assert "guns-purple" not in later and {"guns-blue", "guns-green", "skull-purple", "crate-grey"} <= set(later)
    assert "Tinh bao: bo qua guns-purple (thua luc chien 100000, nay 104000)" in caplog.text
    assert caplog.text.count("Tinh bao: bo qua guns-purple") == 1

    mem.facts["resources"] = {"power": 105000}                  # tang du -> thu lai, thang -> quen
    retry = _run(monkeypatch, IntelCtx(mem), lambda cls: "win")
    assert retry.count("guns-purple") == 2 and mem.facts[notify.LOST_CLASSES] == {}


def test_lost_classes_are_per_instance_and_survive_restart(tmp_path):
    m = memory.Memory(str(tmp_path / "memory.db"))
    a = types.SimpleNamespace(cfg={"notify": {}}, mem=m, dev=types.SimpleNamespace(idx=2))
    notify.note_fight(a, "lose", "skull-green")
    again = types.SimpleNamespace(cfg={"notify": {}}, mem=memory.Memory(str(tmp_path / "memory.db")),
                                  dev=types.SimpleNamespace(idx=2))
    assert list(notify.blocked_classes(again)) == ["skull-green"]
    again.dev = types.SimpleNamespace(idx=4)
    assert notify.blocked_classes(again) == {}


def test_non_fight_results_do_not_block():
    c = types.SimpleNamespace(cfg={"notify": {}}, dev=types.SimpleNamespace(idx=0))
    for r in ("marched", "picked", "lose_pred", "skipped", "no_march", "unknown_target"):
        notify.note_fight(c, r, "guns-blue")
    notify.note_fight(c, "lose", None)                          # khong phan loai duoc -> khong chan
    assert notify.blocked_classes(c) == {}


# ---------- nut khoa / thuoc / du doan ----------
class FakeV:
    def __init__(self, hits):
        self.hits = hits

    def find(self, img, name, **k):
        return self.hits.get(name)


def test_grey_buttons_are_locked_not_pressed():
    img = np.full((960, 540, 3), 128, np.uint8)
    img[480:520, 200:340] = (130, 110, 10)                       # nut co mau
    for name in ("intel/btn_go", "intel/btn_pickup"):
        assert IR.target_kind(img, FakeV({name: (270, 700, 1)})) == IR.LOCKED
    assert IR.panel_kind(img, FakeV({"intel/btn_go": (270, 700, 1)})) == IR.LOCKED
    assert IR.panel_kind(img, FakeV({"intel/btn_go": (270, 500, 1)})) == "go"
    assert IR.target_kind(img, FakeV({"intel/btn_attack": (270, 700, 1)})) is None
    assert IR.target_kind(img, FakeV({"intel/btn_attack": (270, 500, 1)})) == "attack"
    assert IR.target_kind(img, FakeV({"intel/potion_title": (1, 1, 1)})) == "potion"
    assert IR.LOCKED in IR.SKIP and IR.dead_pin(IR.LOCKED) and IR.dead_pin("lose")
    assert not IR.dead_pin(IR.NOT_DEPARTED) and not IR.dead_pin("marched")
    assert "lose" not in IR.STOP and IR.NO_MARCH in IR.STOP and IR.NO_ENERGY in IR.STOP


class BattleCtx:
    """Nut Chien dau hien tre: lan kiem dau chua thay."""

    def __init__(self):
        self.looks, self.taps, self.backed = 0, [], 0
        self.v, self._img, self.cfg = None, None, {}

    def find(self, name, **k):
        if name != "campaign/btn_fight":
            return None
        self.looks += 1
        return None if self.looks == 1 else (270, 900, 1)

    def tap_tpl(self, name, **k):
        self.taps.append(name)
        return True

    def back_out(self, *a):
        self.backed += 1


def test_late_fight_button_still_needs_predicted_win(monkeypatch):
    monkeypatch.setattr(campaign, "auto_formation", lambda c: None)
    monkeypatch.setattr(campaign, "predicted_win", lambda v, img: False)
    monkeypatch.setattr(campaign, "legion_screen", lambda v, img: False)
    monkeypatch.setattr(campaign.time, "sleep", lambda s: None)
    c = BattleCtx()
    assert campaign.battle(c) == "skip" and "campaign/btn_fight" not in c.taps and c.backed == 1


def test_enemy_tile_in_city_after_go():
    img = _img("intel_enemy_tile")
    g = guide_tile.find_enemy(img)
    assert g and g.kind == "enemy" and 330 <= g.x <= 410 and 370 <= g.y <= 440       # linh tren o do, khong phai o lam


# ---------- nha chinh thap: Tinh bao moi luot, som ----------
class SMem:
    def __init__(self, hq=None, backoff=0, last=None):
        self.hq, self.backoff, self.last = hq, backoff, last

    def fact(self, idx, key, default=None):
        return self.hq if key == "hq_level" else default

    def backoff_until(self, idx, step):
        return self.backoff


def test_intel_priority_by_hq():
    assert scheduler.intel_priority(SMem(8), 0, {}) and scheduler.intel_priority(SMem(None), 0, {})
    assert not scheduler.intel_priority(SMem(15), 0, {}) and not scheduler.intel_priority(SMem(30), 1, {})
    assert not scheduler.intel_priority(SMem(8), 0, {"schedule": {"intel_priority_hq": 0}})


def test_intel_added_to_every_visit_for_low_hq():
    order = ["warday", "intel", "train", "gather"]
    names = ["intel", "train", "gather"]
    assert scheduler.with_intel_step(SMem(8), 0, ["train"], names, order, {}, 100) == ["intel", "train"]
    assert scheduler.with_intel_step(SMem(20), 0, ["train"], names, order, {}, 100) == ["train"]
    assert scheduler.with_intel_step(SMem(8, backoff=200), 0, ["train"], names, order, {}, 100) == ["train"]
    assert scheduler.with_intel_step(SMem(8), 0, ["train"], ["train"], order, {}, 100) == ["train"]


def test_intel_empty_runs_do_not_stretch_its_period(monkeypatch):
    sc = {**scheduler.DEFAULTS}
    now = 10**9
    monkeypatch.setattr(scheduler, "_last", lambda m, i, s: (now - sc["extra_every_min"] * 60 - 1, 0, None))
    monkeypatch.setattr(scheduler, "value_factor", lambda *a, **k: 4)
    monkeypatch.setattr(scheduler, "last_reset", lambda *a: 0)
    assert scheduler.extra_due(None, 0, "intel", sc, now)
    assert not scheduler.extra_due(None, 0, "reddots", sc, now)


def test_promote_keeps_build_first_when_builder_idle():
    order = ["warday", "tutorial", "notify", "upgrade", "construct", "train", "intel", "observe"]
    assert drain.promote(order, "intel", False)[:3] == ["warday", "tutorial", "intel"]
    got = drain.promote(order, "intel", True)
    assert got.index("upgrade") < got.index("intel") < got.index("notify") and sorted(got) == sorted(order)
    assert drain.promote(order, "gather", True) == order


@pytest.mark.parametrize("hq,want", [(8, False), (20, True)])
def test_intel_mech_rally_only_from_hq_15(hq, want):
    with open("config.yaml", encoding="utf-8") as f:
        rc = yaml.safe_load(f)["rebels"]
    assert rebels.intel_rally_ok(SMem(hq), 0, rc) is want
