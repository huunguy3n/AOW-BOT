"""P12-2 (live-run-4): cung toa do 2 lan khong hieu ung -> danh sach den trong lan ghe; cham khac van lam.
Live4: VIP @414,175 'nhan 0' lap lai (#0/#3/#4/#5/#6), o phuc loi @139,530 bam 4-5 lan, reddots cham tran 240 s."""
import inspect
import types

from bot import runner, tapguard
from bot.modules import notify, reddots, rewards


def test_two_no_effect_blacklists():
    g = tapguard.TapGuard()
    assert not g.record("vip", 414, 175, False)
    assert not g.blocked("vip", 414, 175)
    assert g.record("vip", 416, 177, False)            # lech vai px = cung o
    assert g.blocked("vip", 414, 175)
    assert not g.blocked("vip", 351, 893)              # cham khac khong bi anh huong
    assert not g.blocked("reddot", 414, 175)           # pham vi khac
    assert g.keep("vip", [(414, 175), (351, 893)]) == [(351, 893)]
    assert g.summary()


def test_effect_resets_count():
    g = tapguard.TapGuard()
    g.record("glow", 139, 530, False)
    g.record("glow", 139, 530, True)
    assert not g.record("glow", 139, 530, False)
    assert not g.blocked("glow", 139, 530)


def test_of_creates_once():
    ctx = types.SimpleNamespace()
    g = tapguard.of(ctx)
    assert tapguard.of(ctx) is g


def test_runner_resets_guard_each_visit():
    src = inspect.getsource(runner)
    assert "ctx.tap_guard = tapguard.TapGuard()" in src


def test_remaining_excludes_blacklisted():
    g = tapguard.TapGuard()
    g.record("reddot", 61, 397, False)
    g.record("reddot", 61, 397, False)
    rest, black = reddots.remaining([(61, 397), (526, 115), (40, 801)], {reddots._key((40, 801))}, g)
    assert rest == [(526, 115)] and black == [(61, 397)]
    rest, black = reddots.remaining([(61, 397)], set(), g)
    assert rest == [] and black == [(61, 397)]          # chi con cham den -> vong quet dung, khong cho 240 s


class _Ctx:
    """VIP: cham do @414,175 luon nhan 0, @351,893 nhan 1 lan dau roi het."""
    def __init__(self, dots):
        self.dots, self.taps, self.cfg = dots, [], {"rewards": {"use_vip_items": False}}
        self.v = types.SimpleNamespace(find=lambda *a, **k: None)

    def shot(self):
        return list(self.dots)

    def tap(self, x, y, wait=1.0):
        self.taps.append((x, y))

    def claim_buttons(self):
        return 0

    def save_debug(self, *a):
        return None

    def dismiss_reward(self):
        pass

    def tap_first(self, *a, **k):
        return False


def test_vip_dot_claim0_twice_then_skipped(monkeypatch):
    monkeypatch.setattr(rewards, "red_dots", lambda img, roi=None: img)
    ctx = _Ctx([(414, 175)])
    rewards.vip_dots(ctx)                                    # buoc reddots: 1 lan (seen trong ham)
    rewards.vip_dots(ctx)                                    # buoc rewards: lan 2 -> den
    n_taps = len(ctx.taps)
    rewards.vip_dots(ctx)                                    # final / lan sau: khong cham nua
    assert n_taps == 2 and len(ctx.taps) == 2
    assert ctx.tap_guard.blocked("vip", 414, 175)


def test_glow_tile_still_glowing_blacklisted(monkeypatch):
    monkeypatch.setattr(notify, "glow_tiles", lambda img: [(139, 530)])
    monkeypatch.setattr(notify, "nhan_tiles", lambda img: [])
    monkeypatch.setattr(notify, "epic_header", lambda img: None)
    ctx = _Ctx([])
    ctx.tap_tpl = lambda *a, **k: False
    for _ in range(4):                                       # live4: notify.run lai moi vong reddots
        notify.claim_glow_tiles(ctx)
    assert ctx.taps == [(139, 530), (139, 530)]


def test_glow_tile_effect_not_blacklisted(monkeypatch):
    state = {"on": True}
    monkeypatch.setattr(notify, "glow_tiles", lambda img: [(139, 530)] if state["on"] else [])
    monkeypatch.setattr(notify, "nhan_tiles", lambda img: [])
    monkeypatch.setattr(notify, "epic_header", lambda img: None)
    ctx = _Ctx([])
    ctx.tap_tpl = lambda *a, **k: False

    def tap(x, y, wait=1.0):
        ctx.taps.append((x, y))
        state["on"] = False
    ctx.tap = tap
    assert notify.claim_glow_tiles(ctx) == 1
    assert not ctx.tap_guard.blocked("glow", 139, 530)


def test_reddots_loop_uses_guard():
    src = inspect.getsource(reddots.run)
    assert 'guard.keep("reddot"' in src and 'guard.record("reddot"' in src
