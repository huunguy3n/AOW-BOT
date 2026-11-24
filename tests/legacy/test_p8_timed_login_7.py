"""P8-3 (chu du an 2026-11-24): khung "Dang nhap hen gio" 1 gio (01-02h, 15-16h VN = 18-19h, 8-9h UTC) DU cho ca 7 may.
Luot ghe trong khung la luot NGAN (ruong DAU TIEN, notify/rewards neu con thoi gian, <= ~12 phut), toi da 2 may cung
luc, may dang chay luot dai -> nhan ruong o buoc ke tiep roi nhuong luong; may lo khung -> log canh bao."""
import calendar
import collections
import logging
import threading
import time

import pytest

from aowbot.domain import warday as W
from bot import runner as R
from bot.modules import notify

WIN = ((18, 19), (8, 9))
IDS = [0, 1, 2, 3, 4, 5, 6]


def utc(s):
    return calendar.timegm(time.strptime(s, "%Y-%m-%d %H:%M"))


T0, T1 = utc("2026-11-24 18:00"), utc("2026-11-24 19:00")


# ---------------------------------------------------------------- ham thuan
def test_pending_sorted_and_only_in_window():
    lasts = {3: None, 0: T0 - 3600, 1: T0 + 60, 6: None}
    assert W.timed_login_pending(T0, lasts, WIN) == [0, 3, 6]          # bat may NGAY dau khung (khong cho delay)
    assert W.timed_login_pending(T0 - 1, lasts, WIN) == []
    assert W.timed_login_pending(T1, lasts, WIN) == []


def test_missed_and_window_edges():
    assert W.timed_login_missed(T0, {0: T0 + 5, 1: None, 2: T0 - 10}) == [1, 2]
    assert W.last_closed_window(T1 + 60, WIN) == (T0, T1)
    assert W.last_closed_window(T0 + 60, WIN)[1] <= T0
    assert W.next_window_start(T0 - 600, WIN) == T0
    assert W.next_window_start(T0 + 1, WIN) == utc("2026-11-25 08:00")


def test_seven_machines_two_threads_short_visit_fit():
    sched = W.simulate_waves(IDS, T0, 2, 12 * 60)
    assert len(sched) == 7 and max(e for _, _, e in sched) == T0 + 48 * 60     # 4 dot x 12 phut
    assert W.waves_fit(IDS, (T0, T1), 2, 12 * 60)
    # 2 luong dang chay luot dai luc mo khung, nhuong o buoc ke tiep (~10 phut) -> van du
    assert W.waves_fit(IDS, (T0, T1), 2, 12 * 60, free_at=(T0 + 600, T0 + 600))
    # luot dai ~19 phut (P7) -> KHONG du 7 may (ly do co luot ngan)
    assert not W.waves_fit(IDS, (T0, T1), 2, 19 * 60)
    # khong bao gio qua 2 may cung luc
    for t in range(T0, T1, 60):
        assert sum(1 for _, b, e in sched if b <= t < e) <= 2


def test_yield_only_in_window_with_waiters():
    assert W.timed_login_yield(T0 + 60, WIN, 3)
    assert not W.timed_login_yield(T0 + 60, WIN, 0)
    assert not W.timed_login_yield(T0 - 60, WIN, 3)


def test_defaults():
    c = W.wcfg(None)
    assert c["timed_login_visit_max_min"] == 12 and c["timed_login_yield"] is True
    assert tuple(c["timed_login_steps"]) == ("warday", "notify", "rewards")


# ---------------------------------------------------------------- runner (mo phong dong ho, khong bat may)
class Store:
    def __init__(self, cfg):
        self.cfg = cfg

    def cfg_for(self, base, idx=None):
        return self.cfg

    def inst(self, i):
        return {}

    def runner(self, **k):
        pass


class Mem:
    def __init__(self):
        self.f = {}

    def fact(self, i, k):
        return self.f.get((i, k))

    def set_fact(self, i, k, v):
        self.f[(i, k)] = v


def _runner(claim_after_s=180, visit_s=12 * 60, ids=IDS):
    r = object.__new__(R.Runner)
    cfg = {"instances": list(ids), "schedule": {}, "warday": {"stamina": False},
           "modules": {"warday": True, "notify": True, "rewards": True, "gather": True}}
    r.base_cfg, r.store, r.mem = cfg, Store(cfg), Mem()
    r._busy, r.queue = {}, collections.deque()
    r._stop, r._wake = threading.Event(), threading.Event()
    r.spawned, r.clock = [], [T0]

    def spawn(idx, **kw):
        r.spawned.append((idx, r.clock[0], kw))
        r._busy[idx] = r.clock[0] + visit_s
        r.mem.set_fact(idx, "timed_login_at", r.clock[0] + claim_after_s)   # ruong nhan dau luot (~3 phut)
    r._spawn = spawn
    return r


def _simulate(r, parallel=2, until=T1):
    peak = 0
    while r.clock[0] < until:
        t = r.clock[0]
        for i in [i for i, e in r._busy.items() if e <= t]:
            r._busy.pop(i)
        while len(r._busy) < parallel and r._timed_spawn(t):
            pass
        peak = max(peak, len(r._busy))
        nxt = min(r._busy.values(), default=until)
        r.clock[0] = max(t + 1, nxt)
    return peak


def test_runner_all_seven_claim_in_window():
    r = _runner()
    peak = _simulate(r)
    assert peak <= 2
    assert sorted(i for i, _, _ in r.spawned) == IDS                       # moi may dung 1 luot ngan
    assert all(T0 <= r.mem.fact(i, "timed_login_at") < T1 for i in IDS)
    assert r.spawned[0][1] == T0 and r.spawned[1][1] == T0                 # bat dau NGAY dau khung
    kw = r.spawned[0][2]
    assert kw["mode"] == "timed" and kw["why"] == R.Runner.TIMED_WHY
    assert kw["modules"] == {"warday", "notify", "rewards"}                # luot ngan: khong gather / buoc dai


def test_runner_long_visits_running_at_window_open():
    """2 may (5, 6) dang chay luot dai luc 18:00: nhan ruong o buoc ke tiep (18:01) va nhuong luong luc 18:10."""
    r = _runner()
    r._busy = {5: T0 + 600, 6: T0 + 600}
    r.mem.set_fact(5, "timed_login_at", T0 + 60)
    r.mem.set_fact(6, "timed_login_at", T0 + 60)
    assert r._timed_ready(T0) == [0, 1, 2, 3, 4]                           # may ban khong bi bat lai
    _simulate(r)
    assert sorted(i for i, _, _ in r.spawned) == [0, 1, 2, 3, 4]
    assert all(T0 <= r.mem.fact(i, "timed_login_at") < T1 for i in IDS)


def test_runner_retry_cap_per_window():
    """Luot ngan hong truoc khi nhan (khong ghi fact) -> thu lai toi da 2 lan / khung, khong bat may lien tuc."""
    r = _runner()
    r._spawn = lambda idx, **kw: r.spawned.append(idx)
    for _ in range(20):
        r._timed_spawn(T0 + 60)
    assert collections.Counter(r.spawned)[0] == 2 and len(r.spawned) == 14


def test_runner_reports_missed_machines(caplog):
    caplog.set_level(logging.INFO, logger="aow")
    r = _runner()
    r._t_started = T0 - 60
    for i in IDS[:5]:
        r.mem.set_fact(i, "timed_login_at", T0 + 120)
    assert r._timed_report(T0 + 1800) == []                                # khung chua dong
    assert r._timed_report(T1 + 60) == [5, 6]
    assert "LO khung 18:00 UTC" in caplog.text
    assert r._timed_report(T1 + 120) == []                                 # chi bao 1 lan / khung


def test_runner_report_ignores_windows_before_start():
    r = _runner()
    r._t_started = T1 + 10
    assert r._timed_report(T1 + 60) == []


def test_pause_capped_to_next_window():
    r = _runner()
    assert r._timed_wait_cap(T0 - 600, 1800) == 601                       # nghi 30 phut -> thuc dung 18:00
    assert r._timed_wait_cap(T0 - 3600, 1800) == 1800


def test_timed_login_disabled_no_spawn():
    r = _runner()
    r.store.cfg["warday"] = {"stamina": False, "timed_login": False}
    assert not r._timed_spawn(T0 + 60) and r.spawned == []


# ---------------------------------------------------------------- nhan ruong (notify.timed_login_chest)
class V:
    def __init__(self, have):
        self.have = set(have)

    def has(self, n):
        return n in self.have


class Ctx:
    def __init__(self, chest_after_taps, have=("badge/activity", "event/timed_login")):
        self.v, self.taps, self.n = V(have), [], chest_after_taps
        self.dev = type("D", (), {"swipe": lambda *a, **k: None})()

    def ensure_city(self):
        pass

    def find(self, name, **k):
        if name == "badge/activity":
            return (480, 200, 0.9)
        if name == "event/timed_login":
            return (270, 400, 0.9) if len(self.taps) > self.n else None
        return None

    def shot(self):
        return None

    def tap(self, x, y, **k):
        self.taps.append((x, y))

    def dismiss_reward(self):
        self.taps.append("reward")

    def is_home(self):
        return True


def test_chest_claimed_first_on_red_tab(monkeypatch):
    monkeypatch.setattr(notify, "red_dots", lambda img, roi=None: [(200, 80), (330, 80)])
    c = Ctx(chest_after_taps=2)                                            # ruong o tab co cham do thu 2
    assert notify.timed_login_chest(c) == 1
    assert c.taps == [(480, 200), (170, 120), (300, 120), notify.TIMED_CHEST, "reward"]


def test_chest_not_found_returns_zero(monkeypatch):
    monkeypatch.setattr(notify, "red_dots", lambda img, roi=None: [])
    monkeypatch.setattr(time, "sleep", lambda s: None)
    c = Ctx(chest_after_taps=99)
    assert notify.timed_login_chest(c) == 0 and notify.TIMED_CHEST not in c.taps


def test_chest_missing_templates_no_taps():
    c = Ctx(0, have=())
    assert notify.timed_login_chest(c) == 0 and c.taps == []


@pytest.mark.parametrize("vn", [(1, 2), (15, 16)])
def test_windows_are_vn_hours(vn):
    c = W.wcfg(None)
    assert vn in [((a + 7) % 24, (b + 7) % 24) for a, b in c["timed_login_windows_utc"]]
