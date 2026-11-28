"""M2 lo trinh ML (chu du an 2026-11-28 "tich hop M2"): ham thuan xac suat thang, gia tri buoc, nha chinh dung yen."""
import math

from aowbot.domain import battle_model as BM
from aowbot.domain import hqstall, stepvalue


def _rows(n_each=15):
    rows = []
    for i in range(n_each):                       # manh hon nhieu -> thang; yeu hon -> thua; quanh 1 -> lan lon
        rows.append({"kind": "loot", "ours": 150 + i, "enemy": 100, "result": "win"})
        rows.append({"kind": "loot", "ours": 70 + i, "enemy": 100, "result": "lose"})
        rows.append({"kind": "loot", "ours": 100, "enemy": 100, "result": "win" if i % 2 else "lose"})
    return rows


def test_fit_needs_enough_wins_and_losses():
    assert BM.fit(_rows(2)) == {}                       # < MIN_N
    only_win = [{"kind": "arena", "ours": 2, "enemy": 1, "result": "win"}] * 30
    assert BM.fit(only_win) == {}
    assert BM.fit([{"kind": "x", "ours": None, "enemy": 1, "result": "win"}] * 30) == {}


def test_model_monotonic_and_ratio_for():
    m = BM.fit(_rows())["loot"]
    assert m.b > 0
    assert m.p_win(200, 100) > 0.8 > m.p_win(100, 100) > m.p_win(60, 100)
    r = m.ratio_for(0.8)
    assert r and abs(m.p_win(r * 100, 100) - 0.8) < 1e-6
    assert m.p_win(None, 100) is None


def test_calibration_bins():
    rows = [{"p_win": 0.9, "result": "win"}] * 9 + [{"p_win": 0.9, "result": "lose"}]
    cal = BM.calibration(rows)
    assert cal == [{"lo": 0.8, "hi": 1.0, "n": 10, "p_mean": 0.9, "win_rate": 0.9}]


def test_step_values_and_order_keeps_hard_rules():
    rows = [("research", 6, "1")] * 10 + [("construct", 60, "0")] * 10 + [("gather", 30, "2")] * 10 + \
           [("warday", 6, "0")] * 10 + [("_start", 5, "1")] * 10
    vals = stepvalue.values(rows)
    assert vals[0].step == "research" and all(v.step != "_start" for v in vals)
    order = stepvalue.suggest_order(["warday", "construct", "research", "quests", "gather"], vals)
    assert order[0] == "warday" and order[-1] == "gather"          # luat cung dau / cuoi luot
    assert order.index("research") < order.index("construct")
    assert "quests" in order                                         # chua du du lieu van giu
    assert not stepvalue.did_work("0") and stepvalue.did_work("3") and stepvalue.did_work("marched")


def test_hq_stall_reason_and_threshold():
    now = 100 * 3600.0
    hist = [(0.0, 5), (10 * 3600.0, 6), (40 * 3600.0, 7)]
    runs = [("upgrade", "0", "res_short"), ("upgrade", "0", None), ("construct", "2", None), ("train", "0", None)]
    s = hqstall.diagnose(3, hist, runs, now, plan="wait_resources")
    assert s.level == 7 and math.isclose(s.hours_since_up, 60.0) and s.stalled
    assert s.reasons == [("thieu_tai_nguyen", 1)] and s.build_runs == 3 and s.build_work == 1
    assert s.as_dict()["plan"] == "wait_resources"
    assert not hqstall.diagnose(1, [(0.0, 30)], [], now).stalled          # cap toi da khong tinh dung yen
