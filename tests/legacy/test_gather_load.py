"""Gather: tai trong thay doi theo QUAN DOAN (Odin/Thor/...): chi cap vuot quan doan LON NHAT moi bi bo/ghi nho."""
import time
from types import SimpleNamespace

from bot.modules import gather


class Mem:
    def __init__(self, facts=None):
        self.f = dict(facts or {})

    def fact(self, idx, key, default=None):
        return self.f.get((idx, key), default)

    def set_fact(self, idx, key, value):
        self.f[(idx, key)] = value


def ctx(facts=None):
    return SimpleNamespace(mem=Mem(facts), dev=SimpleNamespace(idx=1))


def test_max_load_keeps_biggest_legion_not_last():
    c = ctx()
    for load in (517590, 44767, 72383):        # 3 doi lien tiep o #1 2026-11-22
        gather.note_load(c, load)
    assert gather.max_load(c) == 517590


def test_load_window_expires_old_max():
    old = time.time() - gather.LOAD_WINDOW_S - 10
    c = ctx({(1, "march_load_max"): [900000, old]})
    gather.note_load(c, 50000)
    assert gather.max_load(c) == 50000


def test_too_big_known_uses_max_load_so_big_levels_are_not_skipped_after_small_legion():
    c = ctx({(1, "mine_cap:oil:8"): 330000, (1, "mine_cap:oil:7"): 260000, (1, "march_load"): 72383})
    gather.note_load(c, 517590)
    gather.note_load(c, 72383)                  # quan doan nho vua di: KHONG duoc keo nguong xuong
    assert not gather.too_big_known(c, "oil", 8, 1)
    assert not gather.too_big_known(c, "oil", 7, 1)
    c2 = ctx({(1, "mine_cap:food:8"): 1320000})
    gather.note_load(c2, 517590)
    assert gather.too_big_known(c2, "food", 8, 1)           # khong quan doan nao cho het -> bo qua dung
    assert not gather.too_big_known(c2, "food", 1, 1)       # cap thap nhat luon thu


def test_small_legion_too_big_does_not_poison_gather_top():
    c = ctx()
    gather.note_load(c, 517590)
    gather.remember_too_big(c, "metal", 8, 44767, 1)        # quan doan nho: chi bo cap nay lan nay
    assert c.mem.fact(1, "gather_top:metal") is None
    gather.remember_too_big(c, "metal", 8, 517590, 1)       # quan doan lon nhat van khong cho het: ghi nho
    assert c.mem.fact(1, "gather_top:metal") == 7
