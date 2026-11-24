"""P9-7 (chu du an 2026-11-24, live-run-2 11:09): tap ket phan quan - o "Cap" doc duoc 2 chu so (truoc P9 chi anh mau
1 chu so -> 'doc None'), go cap vao O (khong phai thanh truot), "Doi hinh de xuat" -> "Xuat chinh", nhan "Dang tap ket";
nha chinh < 15 khong bao gio tham gia tap ket co giap."""
import os
import types

import cv2
import numpy as np
import pytest
import yaml

from bot import ocr
from bot.modules import gather, rebels
from bot.vision import Vision

AUTO = "data/pm-shots/owner-20261124/live2/auto"
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def test_parse_level_and_box():
    assert gather.parse_level("20") == 20 and gather.parse_level(" 3O") == 3 and gather.parse_level("") is None
    assert gather.parse_level("99") is None
    assert gather.level_box((68, 758, 1.0)) == (272, 797, 72, 24)
    x, _y, w, _h = gather.level_box(None, [292, 798, 30, 20])
    assert w >= 72 and x <= 272                       # du rong cho 2 chu so


@pytest.mark.parametrize("f,lv", [("s110928", 20), ("s110937", 30)])
def test_read_level_two_digits_live2(f, lv):
    p = f"{AUTO}/{f}.png"
    if not os.path.exists(p):
        pytest.skip("thieu anh live2")
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")
    img = cv2.imread(p)
    with open("config.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    ctx = types.SimpleNamespace(cfg=cfg, v=Vision("templates", 0.85), shot=lambda: img)
    assert gather.read_level(ctx) == lv


class Ctx:
    def __init__(self, reads):
        self.taps, self.typed = [], []
        self.reads = list(reads)
        self.cfg = {"gather": {}}
        self.dev = types.SimpleNamespace(type_digits=lambda s: self.typed.append(int(s)),
                                         tap=lambda x, y: self.taps.append(("dev", x, y)))

    def find(self, name, **k):
        return {"gather/btn_level_minus": (68, 758, 1.0), "gather/btn_level_plus": (476, 758, 1.0)}.get(name)

    def tap(self, x, y, wait=1.0):
        self.taps.append((x, y))


def test_type_level_taps_box_not_slider(monkeypatch):
    c = Ctx([30])
    monkeypatch.setattr(gather, "read_level", lambda ctx: c.reads.pop(0) if c.reads else None)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.type_level(c, 30)
    assert c.taps[0] == (307, 808)                    # o "Cap"
    assert (272, 758) not in c.taps                   # KHONG cham giua - va + (thanh truot)
    assert c.typed == [30]


def test_type_level_when_ocr_blank_falls_back_without_crash(monkeypatch):
    c = Ctx([])
    monkeypatch.setattr(gather, "read_level", lambda ctx: None)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    assert gather.type_level(c, 30) is True           # go so roi; doc trong -> giu so da go (khong bam +/- mu)
    assert c.typed == [30]


def test_rally_started_text():
    assert rebels.rally_started_text("Dang tap ket 00:02:57")
    assert rebels.rally_started_text("Đang tập kết")
    assert not rebels.rally_started_text("Dang thu thap")


class RallyCtx:
    def __init__(self):
        self.seq = []
        self.cfg = {"rebels": {}}
        self.mem = None

    def tap_tpl(self, name, **k):
        self.seq.append(name)
        return True

    def wait_for(self, name, **k):
        return True

    def find(self, name, **k):
        return None

    def tap(self, x, y, **k):
        self.seq.append(("tap", x, y))

    def shot(self):
        return np.zeros((960, 540, 3), np.uint8)

    def march_sent(self):
        self.seq.append("march_sent")

    def ensure_world(self):
        pass

    def back_out(self, n=1):
        self.seq.append("back")


def test_launch_rally_recommend_then_march(monkeypatch):
    monkeypatch.setattr(rebels, "pred_win", lambda img: True)
    monkeypatch.setattr(rebels, "rally_started", lambda ctx: True)
    monkeypatch.setattr(rebels, "rally_ticks", lambda ctx: 0)
    monkeypatch.setattr(rebels, "_save", lambda ctx, rec: None)
    c = RallyCtx()
    assert rebels.launch_rally(c, {}, {}, 30) == 1
    i_rec = c.seq.index("play/btn_arena_recommend")
    i_out = c.seq.index("rebels/btn_march_out")
    assert c.seq.index("rebels/btn_rally") < c.seq.index("rebels/btn_rally_confirm") < i_rec < i_out


def test_launch_rally_no_march_when_not_predicted_win(monkeypatch):
    monkeypatch.setattr(rebels, "pred_win", lambda img: False)
    monkeypatch.setattr(rebels, "rally_ticks", lambda ctx: 0)
    monkeypatch.setattr(rebels, "_save", lambda ctx, rec: None)
    c = RallyCtx()
    assert rebels.launch_rally(c, {}, {}, 30) == -1
    assert "rebels/btn_march_out" not in c.seq and "play/btn_arena_recommend" in c.seq


def test_hq_below_15_never_joins_mech_rally():
    mem = types.SimpleNamespace(fact=lambda i, k: 14)
    assert not rebels.join_hq_ok(mem, 0, {"min_hq_level": 15})
    assert rebels.join_hq_ok(types.SimpleNamespace(fact=lambda i, k: 30), 1, {"min_hq_level": 15})
