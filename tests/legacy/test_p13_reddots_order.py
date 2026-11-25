"""P13-3: cham do TREN XUONG, TRAI QUA PHAI (anh reddot_thu_tu.png); reddots dung truoc cac buoc rieng."""
from bot import runner
from bot.modules import reddots

# log live5 #1 ~20:31: Qua lien minh (duoi) -> Thu -> Su menh (tren phai) -> Tinh bao (trai) - nhay lung tung
DOTS = [((456, 796), "ally_gift"), ((515, 800), "mail"), ((510, 300), "mission"), ((64, 629), "intel"),
        ((414, 175), "vip"), ((441, 898), "play")]


def test_full_sequence_top_down_left_right():
    rest, seq = list(DOTS), []
    while rest:
        d = reddots.pick(rest)
        seq.append(d[1])
        rest.remove(d)
    assert seq == ["vip", "mission", "intel", "ally_gift", "mail", "play"]


def test_lower_never_before_upper():
    for i, a in enumerate(DOTS):
        for b in DOTS[i + 1:]:
            first = reddots.pick([a, b])
            top = min((a, b), key=lambda d: (d[0][1] // 30, d[0][0]))
            assert first == top


def test_same_row_left_first():
    assert reddots.pick([((300, 100), "generic"), ((40, 110), "generic")])[0] == (40, 110)


def test_runner_order_reddots_before_dedicated_steps():
    names = [n for n, _ in runner.ORDER]
    r = names.index("reddots")
    assert names.index("alliance") < r          # mo lien minh van gui quan som (uu tien dau cua buoc Lien minh)
    for s in ("notify", "rewards", "mission", "play", "intel"):
        assert r < names.index(s)
    assert names.index("gather") == len(names) - 1


def test_defer_off_by_default():
    assert reddots.rcfg({})["defer_to_steps"] is False
