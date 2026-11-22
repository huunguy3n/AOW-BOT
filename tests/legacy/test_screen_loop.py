"""S1 (doi man dung yen roi moi doc) + S2 (dong nhiem vu bi chan -> khong thu lai toi han)."""
import types

import numpy as np

from aowbot.domain import blockers
from bot import build
from bot import ctx as ctx_mod
from bot.ctx import Ctx
from bot.modules import quests

NOW = 1_800_000_000.0


def frame(v):
    return np.full((960, 540, 3), v, np.uint8)


# ---------------------------------------------------------------- S1 settle
def settle_ctx(frames):
    c = types.SimpleNamespace(seq=list(frames), shots=0)

    def shot():
        c.shots += 1
        c._img = c.seq.pop(0) if len(c.seq) > 1 else c.seq[0]
        return c._img
    c.shot = shot
    return c


def test_settle_waits_until_two_frames_match(monkeypatch):
    monkeypatch.setattr(ctx_mod.time, "sleep", lambda s: None)
    c = settle_ctx([frame(0), frame(80), frame(160), frame(160)])     # camera truot 2 nhip roi dung
    img = Ctx.settle(c, max_s=10)
    assert int(img[0, 0, 0]) == 160 and c.shots == 4


def test_settle_gives_up_after_max_s(monkeypatch):
    t = iter(range(0, 1000))
    monkeypatch.setattr(ctx_mod.time, "time", lambda: float(next(t)))
    monkeypatch.setattr(ctx_mod.time, "sleep", lambda s: None)
    c = settle_ctx([frame(i * 40 % 250) for i in range(50)])          # hoat anh lien tuc
    Ctx.settle(c, max_s=3)
    assert c.shots <= 5


# ---------------------------------------------------------------- S1 upgrade_here doc lai khi man hien tre
class LateCtx:
    """Lan doc dau: chua co gi (camera dang truot). Sau settle(max_s=4): menu cong trinh hien ra."""

    def __init__(self):
        self.cfg, self.calls, self.late = {}, [], False
        self._img = frame(0)
        self.v = types.SimpleNamespace(find=self._find)

    def _find(self, img, name, **k):
        return (300, 550, 0.95) if self.late and name == "build/btn_upgrade_icon" else None

    def settle(self, max_s=3.0, **k):
        if max_s >= 4:
            self.late = True
        return self._img

    def find(self, name, fresh=True, **k):
        return self._find(self._img, name)

    def shot(self):
        return self._img

    def skip_dialogs(self):
        pass

    def tap_tpl(self, name, **k):
        self.calls.append(name)
        self.late = False          # sau khi cham icon: gia lap man Tang cap khong mo -> 'none' lan 2
        return True

    def back_out(self, *a):
        pass


def test_upgrade_here_rereads_when_menu_appears_late(monkeypatch):
    monkeypatch.setattr(build, "menu_busy", lambda *a: None)
    monkeypatch.setattr(build, "menu_level", lambda *a: 5)
    c = LateCtx()
    assert build.upgrade_here(c) == "none"
    assert c.calls == ["build/btn_upgrade_icon"]          # truoc S1: tra 'none' ma khong cham icon


# ---------------------------------------------------------------- S2 quests bo qua dong bi chan
class QuestCtx:
    def __init__(self, store):
        self.cfg = {"quests": {"story": False, "main": True, "follow": True, "max_go_per_run": 6}}
        self.dev = types.SimpleNamespace(idx=3)
        self.store = store
        self.taps = []
        img = frame(30)
        for k, y in enumerate((309, 431, 542)):                         # 3 dong, tieu de khac nhau
            img[y - 52:y - 20, 110 + 60 * k:170 + 60 * k] = 220
        self.img = img
        self.v = types.SimpleNamespace(find_all=lambda im, n: [(442, 309, .9), (442, 431, .9), (442, 542, .9)])

    def ensure_city(self):
        pass

    def tap_tpl(self, *a, **k):
        return True

    def shot(self):
        return self.img

    def tap(self, x, y, **k):
        self.taps.append(y)

    def claim_buttons(self, **k):
        return 0

    def back_out(self, *a):
        pass


class Store:
    def __init__(self):
        self.d = {}

    def inst(self, idx):
        return self.d

    def update(self, idx, **kw):
        self.d.update(kw)


def run_once(monkeypatch, store, msg=(None, "")):
    monkeypatch.setattr(quests.time, "time", lambda: NOW)
    monkeypatch.setattr(build, "builders", lambda ctx: (0, 2))
    monkeypatch.setattr(build, "inv_capture", lambda *a: None)
    monkeypatch.setattr(build, "upgrade_here", lambda ctx: "none")
    monkeypatch.setattr(quests.game_msg, "read", lambda img: msg)
    c = QuestCtx(store)
    quests.run(c)
    return c


def test_none_rows_are_remembered_and_skipped_next_visit(monkeypatch):
    store = Store()
    first = run_once(monkeypatch, store, (blockers.BlockReason.PLOT_LOCKED, "lo dat"))
    assert first.taps == [309, 431, 542]
    saved = store.d["quest_blocks"]
    assert len(saved) == 3 and {v["reason"] for v in saved.values()} == {"plot_locked"}
    again = run_once(monkeypatch, store)
    assert again.taps == []                                  # truoc S2: 3 lan 'Den' vo ich moi lan ghe


def test_unexplained_none_uses_config_ttl(monkeypatch):
    store = Store()
    c = run_once(monkeypatch, store)
    assert c.taps and all(v["reason"] == "no_effect" and v["until"] == NOW + 2 * 3600
                          for v in store.d["quest_blocks"].values())


def test_row_key_ignores_progress_counter():
    img = frame(30)
    img[257:289, 130:300] = 200                                     # tieu de dong nut y=309
    a = quests.row_key(img, (442, 309))
    img[260:290, 420:470] = 255                                     # so tien do "3/4" doi
    assert blockers.hamming(a, quests.row_key(img, (442, 309))) == 0
