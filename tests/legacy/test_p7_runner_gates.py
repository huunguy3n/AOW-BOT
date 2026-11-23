"""P7-8 (chu du an 2026-11-24, anh minigame_runner_gates_minus_plus): cong do "-X" ban du se lat "+Y" -> lao vao neu
hoa luc du lat kip, khong thi ne."""
from bot import steer


def test_parse_gate():
    assert steer.parse_gate("-5") == -5
    assert steer.parse_gate("+3") == 3
    assert steer.parse_gate("3") == -3          # bang DO mat dau '-' -> am
    assert steer.parse_gate("") is None


def test_gate_track_rate():
    tr = steer.GateTrack()
    assert tr.update(380, -6, 0.0) is None
    assert tr.update(390, -4, 1.0) == 2.0       # cung lan (x // 60), tang 2/giay
    assert tr.rate(100) is None


def test_flip_ok():
    # -5, tang 3/giay, cach doi quan 300 px -> 6,7 s -> du lat
    assert steer.flip_ok(-5, 3.0, steer.SQUAD_Y - 300)
    # -30, tang 1/giay, sat doi quan -> khong kip -> ne
    assert not steer.flip_ok(-30, 1.0, steer.SQUAD_Y - 60)
    assert not steer.flip_ok(-5, None, 200)     # chua biet toc do -> khong lao vao
    assert not steer.flip_ok(-5, -1.0, 200)     # khong bi ban (so giam) -> ne


def test_classify_gates_moves_flippable_to_flip_and_choose_goes_there():
    vals = iter([-4, -2])                       # 2 khung: -4 -> -2 sau 0,5 s = 4/giay
    det = {"buff": [], "nerf": [(420, 450, 120)], "danger": [], "enemy": [], "block": [], "target": []}
    tr = steer.GateTrack()
    steer.classify_gates(det, None, tr, 0.0, read=lambda *a: next(vals))
    assert det["flip"] == [] and det["nerf"] == [(420, 450, 120)]     # lan dau chua biet toc do -> giu ne
    det = {"buff": [], "nerf": [(420, 450, 120)], "danger": [], "enemy": [], "block": [], "target": []}
    steer.classify_gates(det, None, tr, 0.5, read=lambda *a: next(vals))
    assert det["flip"] == [(420, 450, 120)] and det["nerf"] == []
    x, _ = steer.choose(det, 380)
    assert abs(x - 420) <= 30                   # lao vao cong se lat


def test_unflippable_near_gate_avoided():
    det = {"buff": [], "nerf": [(270, 620, 140)], "danger": [], "enemy": [], "block": [], "target": []}
    tr = steer.GateTrack()
    tr.update(270, -40, 0.0)
    steer.classify_gates(det, None, tr, 0.5, read=lambda *a: -39)
    assert det["flip"] == []
    x, _ = steer.choose(det, 270)
    assert abs(x - 270) >= 60                   # ne cong do gan


def test_small_red_blobs_not_ocrd():
    calls = []
    det = {"buff": [], "nerf": [(200, 300, 40)], "target": []}
    steer.classify_gates(det, None, steer.GateTrack(), 0, read=lambda *a: calls.append(a))
    assert calls == [] and det["nerf"] == [(200, 300, 40)]
