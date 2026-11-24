"""P7-10 (chu du an 2026-11-24): go so vao o "Cap" khi tim phan quan; rally tick "3Phut" + "Du thanh vien se xuat phat"
-> Xac nhan -> Xuat chinh; farm nha chinh < 15 KHONG BAO GIO tham gia tap ket Co giap; dau truong chi doi thu yeu hon,
khong co thi "Lam moi"."""
import types

import pytest
import yaml

from bot.device import Device
from bot.modules import gather, play, rebels


# ---------- go so o "Cap" ----------
class Dev:
    def __init__(self):
        self.typed = []

    def type_digits(self, s):
        self.typed.append(s)

    def tap(self, x, y):
        pass


class LvCtx:
    def __init__(self, after):
        self.dev, self.after, self.taps = Dev(), after, []

    def find(self, name, fresh=True, **k):
        return {"gather/btn_level_minus": (180, 600, 0.9), "gather/btn_level_plus": (360, 600, 0.9)}.get(name)

    def tap(self, x, y, wait=0):
        self.taps.append((x, y))


def test_type_level_taps_field_and_types(monkeypatch):
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    c = LvCtx(12)
    monkeypatch.setattr(gather, "read_level", lambda ctx: ctx.after)
    assert gather.type_level(c, 12)
    # P9-7: cham O "Cap" (nut - + (239, 50)), KHONG cham giua - va + (270,600 = thanh truot, live-run-2 doi cap)
    assert c.taps == [(180 + 239, 600 + 50)] and c.dev.typed == [12]


def test_type_level_falls_back_to_plus_minus(monkeypatch):
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    monkeypatch.setattr(gather, "read_level", lambda ctx: 9)
    called = []
    monkeypatch.setattr(gather, "set_level", lambda ctx, lv: called.append(lv) or True)
    assert gather.type_level(LvCtx(9), 12) and called == [12]


def test_type_digits_only_digits():
    d = Device.__new__(Device)
    sent = []
    d._cmd = lambda *a: sent.append(a)
    d.type_digits(15)
    assert ("shell", "input", "text", "15") in sent
    with pytest.raises(ValueError):
        d.type_digits("abc; rm")


# ---------- rally ----------
class V:
    def __init__(self, have=(), seen=()):
        self.have, self.seen = set(have), set(seen)

    def has(self, name):
        return name in self.have


class RCtx:
    def __init__(self, v, sticky=()):
        self.v, self.taps, self.sticky = v, [], set(sticky)

    def find(self, name, **k):
        return (100, 500, 0.9) if name in self.v.seen else None

    def tap(self, x, y, wait=0):
        self.taps.append((x, y))
        for n in list(self.v.seen):
            if n not in self.sticky:
                self.v.seen.discard(n)


def test_rally_ticks_only_unchecked():
    v = V({"rebels/chk_3min_off", "rebels/chk_full_start_off"}, {"rebels/chk_full_start_off"})
    c = RCtx(v)
    assert rebels.rally_ticks(c) == 1 and len(c.taps) == 1     # 3Phut da chon san (khong khop mau chua chon)
    assert rebels.rally_ticks(RCtx(V())) == 0                  # thieu anh mau -> bo qua em


def test_join_never_for_farm_below_hq15():
    rc = {"join_mech_rally": True, "min_hq_level": 15}
    mem = types.SimpleNamespace(fact=lambda idx, k: 12)
    assert not rebels.join_hq_ok(mem, 2, rc)
    assert not rebels.join_hq_ok(types.SimpleNamespace(fact=lambda idx, k: None), 2, rc)
    assert rebels.join_hq_ok(types.SimpleNamespace(fact=lambda idx, k: 30), 1, rc)
    c = types.SimpleNamespace(cfg={"rebels": rc}, mem=mem, dev=types.SimpleNamespace(idx=2),
                              v=V({"rebels/rally_mech", "rebels/btn_join"}),
                              ensure_city=lambda: (_ for _ in ()).throw(AssertionError("khong mo lien minh")))
    assert rebels.join(c) == 0


def test_config_join_off_and_type_level_on():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["rebels"]["join_mech_rally"] is False and cfg["rebels"]["type_level"] is True
    assert cfg["arena"]["weaker_only"] is True


# ---------- dau truong ----------
def test_arena_weaker_only():
    assert play.arena_eligible(900_000, False, 1_000_000, 1.0, weaker_only=True)
    assert not play.arena_eligible(1_000_000, False, 1_000_000, 1.0, weaker_only=True)   # bang -> khong
    assert not play.arena_eligible(2_000_000, True, 1_000_000, 1.0, weaker_only=True)    # do khong mien
    assert not play.arena_eligible(10, True, None, 1.0, weaker_only=True)


class AV:
    def __init__(self, have=True):
        self.have = have

    def has(self, name):
        return self.have

    def find(self, img, name, **k):
        return (470, 140, 0.9)


class ACtx:
    POPUP_CLOSERS = ("common/btn_x",)

    def __init__(self, title_after=True, have=True):
        self.v, self.taps, self.title_after, self.debug = AV(have), [], title_after, []

    def shot(self):
        return None

    def tap(self, x, y, wait=0):
        self.taps.append((x, y))

    def wait_for(self, name, **k):
        return self.title_after

    def tap_first(self, names, **k):
        self.taps.append("close")

    def save_debug(self, tag):
        self.debug.append(tag)


def test_arena_refresh_free_text(monkeypatch):
    monkeypatch.setattr(play.ocr, "text", lambda *a, **k: "Lam moi")
    c = ACtx()
    assert [play.arena_refresh(c, {"refresh_max": 2}) for _ in range(3)] == [True, True, False]


def test_arena_refresh_with_cost_never_tapped(monkeypatch):
    monkeypatch.setattr(play.ocr, "text", lambda *a, **k: "50")
    c = ACtx()
    assert not play.arena_refresh(c, {}) and c.taps == []


def test_arena_refresh_unexpected_dialog_closes(monkeypatch):
    monkeypatch.setattr(play.ocr, "text", lambda *a, **k: "Lam moi")
    c = ACtx(title_after=False)
    assert not play.arena_refresh(c, {}) and c.taps[-1] == "close"
    assert not play.arena_refresh(c, {})


def test_arena_refresh_missing_template():
    c = ACtx(have=False)
    assert not play.arena_refresh(c, {}) and c.taps == []
