"""P13d-4: chi ghi hq_level khi doc hop ly; doc nhay/giam bat thuong can >=2 lan doc doc lap co nhan Xuong kien truc."""
from types import SimpleNamespace

import numpy as np

from bot.modules import observe as O


def test_judge_accepts_plausible():
    assert O.judge_hq(None, [(4, False)]) == 4
    assert O.judge_hq(4, [(4, True)]) == 4
    assert O.judge_hq(4, [(5, False)]) == 5


def test_judge_rejects_single_jump_live6c_5():
    assert O.judge_hq(4, [(7, True)]) is None          # 4 -> 7 trong 1 luot, 1 lan doc: khong ghi
    assert O.judge_hq(4, [(7, False), (7, False)]) is None   # khong nhan: khong tin
    assert O.judge_hq(7, [(4, True)]) is None          # giam cap: khong ghi


def test_judge_confirms_jump_with_two_labeled_reads():
    assert O.judge_hq(4, [(7, True), (7, True)]) == 7
    assert O.judge_hq(4, [(7, True), (4, True)]) == 4  # lan 2 ve lai 4 -> giu 4


def test_judge_none_when_unread():
    assert O.judge_hq(4, [(None, False)]) is None


def test_label_detection(monkeypatch):
    monkeypatch.setattr(O.ocr, "text", lambda img, roi, *a, **k: "Cap Xuong kien truc: 7")
    assert O.ocr_hq_ex(np.zeros((960, 540, 3), np.uint8))[:2] == (7, True)
    monkeypatch.setattr(O.ocr, "text", lambda img, roi, *a, **k: "" if k == {} and not a else "7")
    _lv, lab, _ = O.ocr_hq_ex(np.zeros((960, 540, 3), np.uint8))
    assert lab is False                                 # doc rieng chu so: khong co nhan


class _Mem:
    def __init__(self, hq):
        self.f = {(0, "hq_level"): hq}

    def query(self, *a):
        return []

    def fact(self, idx, k, d=None):
        return self.f.get((idx, k), d)

    def set_fact(self, idx, k, v):
        self.f[(idx, k)] = v


def _ctx(prev, texts):
    it = iter(texts)
    c = SimpleNamespace(mem=_Mem(prev), dev=SimpleNamespace(idx=0), cfg={"modules": {}}, store=None)
    c.ensure_city = lambda: None
    c.tap = lambda *a, **k: None
    c.shot = lambda: np.zeros((960, 540, 3), np.uint8)
    c.save_debug = lambda *a: None
    c._it = it
    return c


def test_read_hq_does_not_write_suspect(monkeypatch):
    c = _ctx(4, [])
    monkeypatch.setattr(O.time, "sleep", lambda s: None)
    # doc 7 lan 1, lan 2 cung 7 (nhat quan, co nhan) -> chap nhan; neu 3 lan cho ket qua khac nhau -> khong ghi
    seq = iter([(7, True, ""), (5, True, ""), (4, True, "")])
    monkeypatch.setattr(O, "ocr_hq_ex", lambda img: next(seq))
    r = O.read_hq(c, every_h=0)
    assert r in {5, 4}
    assert c.mem.fact(0, "hq_level") in (4, 5)         # khong bao gio 7
