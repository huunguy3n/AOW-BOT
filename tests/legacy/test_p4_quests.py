"""P4 muc 3 + 5 (PM 2026-11-23): mainquest doc chu thanh nhiem vu, quests bo dong cua buoc khac, kiem ket qua that,
giam chu ky khi cung nhiem vu cu ket; nhan dien 'Tang cap thanh cong!'."""
import glob
import logging
import time
import types

import cv2
import pytest

from bot import build, ocr, quest_rules, tplneed
from bot.modules import mainquest, quests


# ---------- quest_rules: thu lai cung nhiem vu ----------
def test_should_retry_backoff_same_quest_only():
    t = "Tang 4 Xuong Thuc Pham den cap 26"
    now = 10_000.0
    assert quest_rules.should_retry(None, t, now, 1, 8)[0]
    last = {"text": t, "fails": 1, "at": now}
    assert quest_rules.should_retry(last, t, now, 1, 8)[0]                # 1 lan that bai: thu tiep
    last = {"text": t, "fails": 2, "at": now}
    assert not quest_rules.should_retry(last, t, now + 1800, 1, 8)[0]     # 2 lan: cho 1 gio
    assert quest_rules.should_retry(last, t, now + 3700, 1, 8)[0]
    last = {"text": t, "fails": 5, "at": now}
    assert quest_rules.retry_wait_s(5, 1, 8) == 8 * 3600                  # tran 8 gio
    assert quest_rules.should_retry(last, "Huan luyen 10 Tank", now, 1, 8)[0]   # nhiem vu khac -> thu ngay


def test_npc_rules():
    assert quest_rules.npc_level("Phién quan Lv.1") == 1         # OCR that (logs/human 21/11 00:20)
    assert quest_rules.npc_level("Phan quan Co giap Lv.3") is None   # co giap: chi tap ket (buoc rebels)
    assert quest_rules.npc_level("KienQuoc [LSN]") is None        # nguoi choi -> khong bao gio
    assert quest_rules.npc_ok(1, 5000, 571429, 10, 0.3)[0]
    assert not quest_rules.npc_ok(12, 5000, 571429, 10, 0.3)[0]
    assert not quest_rules.npc_ok(3, 300000, 571429, 10, 0.3)[0]
    assert not quest_rules.npc_ok(None, 1, 1, 10, 0.3)[0]


# ---------- quests: doc ten dong ----------
@pytest.mark.parametrize(("title", "go", "kind"), [
    ("Tang 4 XuGng Thuc Pham dén cap 26 Tang 4 Xuong Thuc Pham dén", True, "build"),   # OCR that bang tab Chinh #1
    ("Huan luyén 2000 Tank bac 6 Huan luyén 2000 Tank bac 6", False, "train"),
    ("Kich sat 5 phan quan Co giap cap 5 Kich sat 5 phan quan Co g", False, "rebels"),
    ("Tang 5 Tung lén cap 90 Tang 5 Tuong lén cap 90", True, "hero"),
    ("Chién thang Dau truong 290 lan Chién thang Dau truong 290 la", False, "arena"),
    ("", True, "unknown"),                       # khong doc duoc -> van bam nhu cu
])
def test_row_plan(title, go, kind):
    g, k, _ = quests.row_plan(title)
    assert (g, k) == (go, kind)


def test_is_hq_row():
    assert quests.is_hq_row("Tang Xuong kien truc den cap 9")
    assert not quests.is_hq_row("Tang 4 Xuong Thuc Pham den cap 26")


# ---------- mainquest ----------
class Mem:
    def __init__(self):
        self.f = {}

    def fact(self, i, k, default=None):
        return self.f.get(k, default)

    def set_fact(self, i, k, v):
        self.f[k] = v


class Store:
    def __init__(self):
        self.d = {}

    def inst(self, i):
        return self.d

    def update(self, i, **kw):
        self.d.update(kw)


class V:
    def __init__(self, have=()):
        self.have = set(have)

    def find(self, img, name, **k):
        return (100, 818, 0.9) if name in self.have else None

    def has(self, name):
        return name in self.have


class Ctx:
    def __init__(self, v):
        self.v = v
        self.cfg = {"mainquest": {}, "quests": {}}
        self.dev = types.SimpleNamespace(idx=4)
        self.mem, self.store = Mem(), Store()
        self.taps = []

    def ensure_city(self):
        pass

    def shot(self):
        return "img"

    def tap(self, x, y, **k):
        self.taps.append((x, y))


def test_mainquest_delegated_quest_never_taps(monkeypatch):
    c = Ctx(V({"quest/banner_icon"}))
    t = "Tham gia tap ket tan cong 1 lan phan quan Co giap"
    monkeypatch.setattr(mainquest, "read_banner", lambda ctx, img=None: t)
    monkeypatch.setattr(mainquest, "_blocked", lambda ctx, mq: False)
    assert mainquest.run(c) == 0
    assert c.taps == []                                    # khong cham thanh nhiem vu -> khong ra ban do
    assert c.store.d["mainquest_kind"] == "rally"
    assert c.mem.f["mainquest_last"]["kind"] == "rally"


def test_mainquest_same_failed_quest_waits(monkeypatch):
    c = Ctx(V({"quest/banner_icon"}))
    t = "Tang 5 Tuong len cap 90"
    c.mem.f["mainquest_last"] = {"text": t, "fails": 3, "at": time.time()}
    monkeypatch.setattr(mainquest, "read_banner", lambda ctx, img=None: t)
    monkeypatch.setattr(mainquest, "_blocked", lambda ctx, mq: False)
    monkeypatch.setattr(mainquest, "step", lambda *a, **k: pytest.fail("khong duoc cham"))
    assert mainquest.run(c) == 0


def test_mainquest_counts_only_real_progress(monkeypatch):
    c = Ctx(V({"quest/banner_icon"}))
    texts = iter(["Tang 5 Tuong len cap 90", "Hoan tat Chien dich 3", "Hoan tat Chien dich 3"])
    monkeypatch.setattr(mainquest, "read_banner", lambda ctx, img=None: next(texts))
    monkeypatch.setattr(mainquest, "_blocked", lambda ctx, mq: False)
    monkeypatch.setattr(mainquest, "_hq_yield", lambda ctx, kind: False)
    res = iter(["follow_idle", "skip"])
    monkeypatch.setattr(mainquest, "step", lambda ctx, mq, kind: next(res))
    # lan 1: follow_idle nhung chu doi -> tien trien (1); lan 2: 'skip' + chu khong doi -> dung
    assert mainquest.run(c) == 1
    assert c.mem.f["mainquest_last"]["fails"] == 1


def test_npc_attack_missing_template_logs_and_never_taps(caplog):
    caplog.set_level(logging.INFO, logger="aow")
    tplneed._last.clear()
    c = Ctx(V({"quest/banner_icon"}))
    assert mainquest.npc_attack(c, {}) == "npc_none"
    assert c.taps == []
    assert any("thieu anh mau rebels/npc_attack" in r.getMessage() for r in caplog.records)


# ---------- build: "Tang cap thanh cong!" ----------
OK_SHOTS = sorted(glob.glob("logs/shots/20261122-*-build_blocked.png"))


@pytest.mark.ocr
@pytest.mark.skipif(not OK_SHOTS, reason="khong co anh logs/shots (chi chay local)")
def test_upgraded_ok_on_real_success_shots():
    if not ocr.init(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
        pytest.skip("khong co Tesseract")
    assert sum(build.upgraded_ok(cv2.imread(f)) for f in OK_SHOTS) == len(OK_SHOTS)
    old = sorted(glob.glob("logs/shots/2026111*-build_blocked.png"))
    assert not any(build.upgraded_ok(cv2.imread(f)) for f in old)
