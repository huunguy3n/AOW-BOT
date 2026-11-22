"""P5 muc 3 (PM 2026-11-23): benh vien chi mo khi co dau hieu thuong binh (bong bong / vua co tran)."""
import pytest
import yaml

from bot.modules import heal


# ---------- benh vien ----------
@pytest.mark.parametrize(("tpl", "bubble", "fought", "cfg", "want"), [
    (True, False, False, False, False),   # co anh mau, khong bong bong, khong tran -> khong mo (truoc: 45/45 mo ra xem)
    (True, True, False, False, True),     # thay bong bong
    (True, False, True, False, True),     # vua co tran trong lan ghe
    (True, False, False, True, True),     # cau hinh heal.open_without_bubble
    (False, False, False, False, True),   # thieu anh mau bong bong -> khong biet -> cach cu
])
def test_should_open(tpl, bubble, fought, cfg, want):
    assert heal.should_open(tpl, bubble, fought, cfg) is want


def test_fought_uses_rebels_and_defense():
    assert not heal.fought(None) and not heal.fought({"rebels": 0, "gather": 3})
    assert heal.fought({"rebels": 1}) and heal.fought({"defense": 1})


class V:
    def __init__(self, have=(), seen=()):
        self.have, self.seen = set(have), set(seen)

    def has(self, name):
        return name in self.have

    def find(self, img, name, **k):
        return (100, 200, 0.9) if name in self.seen else None


class HealCtx:
    def __init__(self, v, done=None, cfg=None):
        self.v, self.visit_done, self.cfg = v, done or {}, cfg or {}
        self.taps = []

    def world_ready(self):
        return False

    def ensure_city(self):
        pass

    def settle(self):
        return "img"

    def tap(self, x, y, **k):
        self.taps.append((x, y))


def test_heal_run_no_bubble_no_fight_does_not_tap(monkeypatch):
    def boom(img):
        raise AssertionError("khong duoc tim chu thap do / mo benh vien")
    monkeypatch.setattr(heal, "crosses", boom)
    c = HealCtx(V(have={"build/heal_bubble"}))
    assert heal.run(c) == 0 and c.taps == []


def test_heal_run_after_fight_looks_for_hospital(monkeypatch):
    monkeypatch.setattr(heal, "crosses", lambda img: [])
    c = HealCtx(V(have={"build/heal_bubble"}), done={"rebels": 1})
    assert heal.run(c) == 0 and c.taps == []      # tim chu thap do (khong thay) -> bo


def test_config_heal_default_off():
    with open("config.yaml", encoding="utf-8") as f:
        assert yaml.safe_load(f)["heal"]["open_without_bubble"] is False
