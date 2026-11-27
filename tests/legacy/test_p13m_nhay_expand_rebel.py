"""P13m (chu du an t106u, t107u): "Nhay" dong dieu kien dau cua nha chinh; mo rong lanh tho danh phien quan tren o do
trong thanh; phien quan leo cap bang "Tim kiem" toi khi co "Tan cong".

Anh chu du an (force-add): tests/fixtures/p13m/. Anh la ban cat tu man dien thoai cung ti le be ngang ~540 -> bang
phien quan dat vao khung 540x960 o (1, 138) cho trung vi tri that (tieu de y ~195, nut y ~737)."""
import logging
import time
import types

import cv2
import numpy as np
import pytest

from bot import build, guide_tile, ocr, quest_rules, resources, tapguard
from bot import world_target as W
from bot.modules import arrow, campaign, expand, mainquest, rebels, tutorial
from bot.vision import Vision

D = "tests/fixtures/p13m/"
V = Vision("templates", 0.82)
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ---- A. bang "Cap sau8" (x0, y0, x1, y1) ----
JUMP_1 = (425, 147, 511, 178)          # "Nhay" So Cong Nghe (khung do chu khoanh)
JUMP_2 = (425, 196, 511, 228)
JUMP_3 = (425, 245, 511, 277)
GET_MORE = (424, 294, 511, 327)        # "Nhan cang nhieu"
DIAMOND = (82, 365, 243, 418)          # "Tang cap ngay" 5473 kim cuong
UPGRADE = (308, 365, 468, 418)         # "Tang cap"
# ---- B. phien quan trong thanh ----
MONSTER = (245, 305, 305, 385)         # than con quan trong khung do
SOLDIER = (165, 335, 232, 450)         # linh minh (o xanh lam)
# ---- C. phien quan ban do (toa do tren anh cat) ----
LV2_SPRITE = (110, 115, 145, 151)      # than con cap 2, TREN nhan (nhan y 152-175)
ARROW_AT = (150, 250)                  # vi tri dat anh mui ten trong khung 540x960
POPUP_AT = (1, 138)
SEARCH_BTN = (182, 584, 342, 637)      # "Tim kiem" tren anh cat
ATTACK_BTN = (185, 575, 345, 626)      # "Tan cong" tren anh cat


def _img(name):
    img = cv2.imread(D + name + ".png")
    assert img is not None, name
    return img


def _canvas(img, at):
    out = np.zeros((960, 540, 3), np.uint8)
    out[:] = np.median(img.reshape(-1, 3), axis=0)
    x, y = at
    h, w = min(img.shape[0], 960 - y), min(img.shape[1], 540 - x)
    out[y:y + h, x:x + w] = img[:h, :w]
    return out


def _in(p, box, at=(0, 0)):
    return box[0] + at[0] <= p[0] <= box[2] + at[0] and box[1] + at[1] <= p[1] <= box[3] + at[1]


def _need_ocr():
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")


def search_screen():
    return _canvas(_img("rebel_max_lv2_timkiem"), POPUP_AT)


def attack_screen():
    return _canvas(_img("rebel_lv2_tancong"), POPUP_AT)


def arrow_screen():
    return _canvas(_img("rebel_arrow_lv2"), ARROW_AT)


def blank():
    return np.full((960, 540, 3), 20, np.uint8)


class Mem:
    def __init__(self, f=None):
        self.f = dict(f or {})

    def fact(self, i, k):
        return self.f.get(k)

    def set_fact(self, i, k, v):
        self.f[k] = v


class Ctx:
    """Ctx gia: `screen` doi theo `on_tap(ctx, x, y)`; ghi moi cu cham."""

    def __init__(self, screen, on_tap=None):
        self.screen, self.on_tap, self.v = screen, on_tap, V
        self.taps, self.tpl_taps, self.backs, self._img = [], [], 0, None
        self.cfg = {"build": {"hq_max_level": 30}}
        self.mem = Mem()
        self.dev = types.SimpleNamespace(idx=3, back=lambda: None)
        self.POPUP_CLOSERS = ["common/btn_close"]

    def shot(self):
        self._img = self.screen
        return self._img

    def settle(self, **k):
        return self.shot()

    def find(self, name, fresh=True, **kw):
        return self.v.find(self.shot(), name, **kw)

    def wait_for(self, name, timeout=0, **kw):
        return self.find(name, **kw)

    def tap(self, x, y, wait=1.0, tpl=None):
        self.taps.append((x, y))
        if self.on_tap:
            self.on_tap(self, x, y)

    def tap_tpl(self, name, wait=1.0, fresh=True, **kw):
        p = self.find(name, **kw)
        if p:
            self.tpl_taps.append(name)
            self.tap(p[0], p[1])
        return bool(p)

    def tap_first(self, names, **kw):
        return False

    def back_out(self, rounds=1):
        self.backs += 1

    def skip_dialogs(self, *a):
        pass

    def save_debug(self, tag):
        pass

    def march_full(self):
        return False

    def world_ready(self):
        return True

    def is_home(self, img=None):
        return False

    def ensure_city(self):
        pass


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)


# ---------- A. nha chinh thieu dieu kien ----------
def test_first_jump_is_the_top_row():
    p = build.first_jump(V, _img("hq_prereq_nhay"))
    assert _in(p, JUMP_1), p
    assert not any(_in(p, b) for b in (JUMP_2, JUMP_3, GET_MORE, DIAMOND, UPGRADE))


def test_first_jump_even_when_a_lower_row_matches_better():
    img = _img("hq_prereq_nhay").copy()
    for x, y in ((440, 154), (500, 168), (452, 170)):       # tia sang tren nut dong 1
        cv2.circle(img, (x, y), 2, (255, 255, 255), -1)
    best = V.find(img, build.JUMP)
    assert not _in(best[:2], JUMP_1)                        # v.find (cach cu) roi vao dong khac
    assert _in(build.first_jump(V, img), JUMP_1)


def test_upgrade_here_taps_only_first_jump_and_is_depth_limited():
    ctx = Ctx(_img("hq_prereq_nhay"))                       # moi cong trinh dieu kien lai thieu dieu kien
    assert build.upgrade_here(ctx, max_depth=4) == "blocked"
    assert len(ctx.taps) == 4
    assert all(_in(p, JUMP_1) for p in ctx.taps), ctx.taps
    assert not ctx.tpl_taps


def test_upgrade_here_follows_jump_to_the_building_and_upgrades(monkeypatch):
    panel = _img("hq_prereq_nhay")
    seen = []

    def on_tap(c, x, y):
        seen.append((x, y))
        c.screen = blank()

    monkeypatch.setattr(build, "inv_capture", lambda *a: None)
    ctx = Ctx(panel, on_tap)
    assert build.upgrade_here(ctx) == "none"                # man trong sau 'Nhay' -> khong bam gi them
    assert len(seen) == 1 and _in(seen[0], JUMP_1)


def test_only_resources_missing_goes_to_refill_not_get_more(monkeypatch):
    img = _img("hq_prereq_nhay").copy()
    img[135:285, 20:545] = img[330:345, 20:545].mean(axis=(0, 1))     # 3 dong cong trinh da dat -> con dong tai nguyen
    assert build.first_jump(V, img) is None
    calls = []
    monkeypatch.setattr(resources, "retry", lambda c, redo: calls.append(1) or resources.NO_FREE)
    ctx = Ctx(img)
    build.upgrade_here(ctx)
    assert calls and ctx.taps and all(_in(p, UPGRADE) for p in ctx.taps), ctx.taps
    assert not any(_in(p, DIAMOND) or _in(p, GET_MORE) for p in ctx.taps)


# ---------- B. mo rong lanh tho ----------
def city():
    return _img("expand_city_rebel_tile")


def test_city_rebel_tap_is_on_the_monster_body():
    hit = expand.find_rebel(V, city())
    assert hit and hit.kind == "rebel"
    assert _in((hit.x, hit.y), MONSTER), hit
    assert not _in((hit.x, hit.y), SOLDIER)


def test_city_rebel_needs_city_marks():
    img = city().copy()
    img[535:600, 440:510] = 40                              # che icon bua (anh cat khong co nut ban do)
    assert expand.find_rebel(V, img) is None
    assert expand.find_rebel(V, None) is None


def test_decide_taps_monster_and_guide_visible():
    img = city()
    act, x, y, why = tutorial.decide(V, img, state={"follow": True})
    assert (act, why) == ("tap", expand.REBEL_WHY) and _in((x, y), MONSTER)
    assert tutorial.guide_visible(V, img) == expand.REBEL_WHY
    assert tutorial.guide_visible(V, img, lambda a, b: True) is None


def test_decide_keeps_the_six_tap_limit():
    state = {"follow": True}
    acts = [tutorial.decide(V, city(), state=state)[0] for _ in range(7)]
    assert acts[:6] == ["tap"] * 6 and acts[6] != "tap"


def test_fight_rebel_only_when_predicted_win(monkeypatch, caplog):
    fought = []
    monkeypatch.setattr(expand, "_formation", lambda v, img: True)
    monkeypatch.setattr(campaign, "auto_formation", lambda c: True)
    monkeypatch.setattr(campaign, "legion_screen", lambda v, img: None)
    monkeypatch.setattr(campaign, "battle", lambda c, **k: fought.append(k) or "win")
    for predicted, want in ((False, "skip"), (True, "win")):
        monkeypatch.setattr(campaign, "predicted_win", lambda v, img, p=predicted: p)
        ctx = Ctx(city())
        with caplog.at_level(logging.INFO, "aow"):
            assert expand.try_city_rebel(ctx) == want
        assert _in(ctx.taps[0], MONSTER) and len(ctx.taps) == 1
    assert fought == [{"only_win": True, "pre_checked": True}]
    assert "mo rong lanh tho: danh phien quan o" in caplog.messages


def test_fight_rebel_miss_is_blacklisted():
    ctx = Ctx(city())                                       # cham khong doi man
    assert expand.try_city_rebel(ctx) == "miss"
    assert expand.try_city_rebel(ctx) is None
    assert len(ctx.taps) == 1 and tapguard.of(ctx).blocked("guide", *ctx.taps[0])


@pytest.mark.parametrize("npc", [True, False])
def test_city_rebel_attack_button(monkeypatch, npc):
    """Bang "Phien quan" -> npc_engage (kiem cap / du doan). Nut "Tan cong" man khac -> bam roi cho man doi hinh."""
    sent = []
    monkeypatch.setattr(mainquest, "is_npc_popup", lambda img: npc)
    monkeypatch.setattr(mainquest, "npc_engage", lambda c, mq, p: sent.append(p) or "npc_sent")
    attack = attack_screen()
    ctx = Ctx(city(), lambda c, x, y: setattr(c, "screen", attack))
    r = expand.try_city_rebel(ctx)
    if npc:
        assert r == "sent" and _in(sent[0], ATTACK_BTN, POPUP_AT) and len(ctx.taps) == 1
    else:
        assert r == "opened" and not sent and len(ctx.taps) == 2 and _in(ctx.taps[1], ATTACK_BTN, POPUP_AT)


def test_npc_popup_title_ocr():
    _need_ocr()
    assert mainquest.is_npc_popup(attack_screen()) and not mainquest.is_npc_popup(city()[:593])


def test_expand_sweep_finds_city_rebel():
    p = expand.sweep(Ctx(city()), ring=False)
    assert isinstance(p, guide_tile.Guide) and _in((p.x, p.y), MONSTER)


def test_mainquest_banner_tap_then_city_rebel(monkeypatch):
    monkeypatch.setattr(expand, "fight_rebel", lambda c, hit: c.taps.append((hit.x, hit.y)) or "win")
    ctx = Ctx(blank(), lambda c, x, y: setattr(c, "screen", city()))
    assert mainquest.npc_attack(ctx, {}) == "win"
    assert ctx.taps[0] == mainquest.BANNER and _in(ctx.taps[1], MONSTER)


# ---------- C. phien quan leo cap ----------
def test_quest_banner_is_rebels_and_world_is_not_a_city_rebel():
    img = _img("rebel_quest_lv3")
    assert quest_rules.classify("Kich sat 1 lan phan quan Lv.3")[0] == "rebels"
    assert mainquest.npc_popup(img, V) is None
    assert expand.find_rebel(V, img) is None


def test_quest_world_label_pick_never_a_player_base():
    img = _img("rebel_quest_lv3")
    t = W.rebel_near(img, V, 272, 300, 150)
    assert t and t.kind == "rebel"
    assert not (t.x > 380 and t.y < 150), t                 # goc co can cu (LSS)MF001
    assert not W.city_near(img, t.x, t.y)


@pytest.mark.parametrize("img", [_img("rebel_max_lv2_timkiem"), search_screen()], ids=["crop", "canvas"])
def test_popup_lv3_is_search_not_attack(img):
    kind, p = mainquest.npc_popup(img, V)
    off = (0, 0) if img.shape[0] != 960 else POPUP_AT
    assert kind == "search" and _in(p, SEARCH_BTN, off), p
    assert mainquest.npc_popup_action(img, V) == "search" and mainquest.find_attack(img, V) is None


def test_max_level_ocr_is_2():
    _need_ocr()
    img = search_screen()
    assert mainquest.read_max_level(img, mainquest.npc_popup(img, V)[1]) == 2


def test_parse_max_level():
    assert mainquest.parse_max_level("Tối đa có thể tấn công phản quân cấp 2!") == 2
    assert mainquest.parse_max_level("Téi da cé thé tan cong phan quan cap 14!") == 14
    assert mainquest.parse_max_level("De xuat: 10,000") is None
    assert mainquest.parse_max_level("") is None


@pytest.mark.parametrize("img", [_img("rebel_lv2_tancong"), attack_screen()], ids=["crop", "canvas"])
def test_popup_lv2_is_attack(img):
    kind, p = mainquest.npc_popup(img, V)
    off = (0, 0) if img.shape[0] != 960 else POPUP_AT
    assert kind == "attack" and _in(p, ATTACK_BTN, off), p


def test_arrow_tap_is_the_lv2_sprite():
    img = arrow_screen()
    chevron = W.find_green_chevron(img)
    assert chevron
    t = W.pick(img, V, chevron, reach_x=mainquest.NPC_REACH_X)
    assert _in((t.x, t.y), LV2_SPRITE, ARROW_AT), t


def test_arrow_never_falls_to_the_lv6_rebel():
    img = arrow_screen().copy()
    x, y = ARROW_AT
    img[y + 140:y + 185, x + 65:x + 185] = img[y + 230:y + 275, x + 20:x + 140]     # che nhan + con cap 2
    img[y + 100:y + 150, x + 95:x + 160] = img[y + 220:y + 270, x + 60:x + 125]
    t = W.pick(img, V, reach_x=mainquest.NPC_REACH_X)
    assert t is None or t.x < x + 170, t


def _climb_ctx(after_sprite):
    """bang 'Tim kiem' -> ban do co mui ten -> cham sprite -> `after_sprite`."""
    def on_tap(c, x, y):
        if c.screen is first:
            c.screen = world
        elif c.screen is world:
            c.screen = after_sprite()

    first, world = search_screen(), arrow_screen()
    return Ctx(first, on_tap), first, on_tap


def test_climb_search_sprite_then_attack(caplog):
    _need_ocr()
    ctx, _, _ = _climb_ctx(attack_screen)
    with caplog.at_level(logging.INFO, "aow"):
        p = mainquest.npc_search(ctx)
    assert _in(p, ATTACK_BTN, POPUP_AT), p
    assert len(ctx.taps) == 2
    assert _in(ctx.taps[0], SEARCH_BTN, POPUP_AT) and _in(ctx.taps[1], LV2_SPRITE, ARROW_AT)
    assert mainquest.TARGET not in ctx.taps
    assert "phien quan: toi da cap 2 -> tim kiem" in caplog.messages
    assert ctx.mem.f["npc_max_level"] == 2


def test_climb_stops_when_search_popup_keeps_coming_back():
    state = {}

    def on_tap(c, x, y):
        c.screen = state["world"] if c.screen is state["search"] else state["search"]

    state.update(search=search_screen(), world=arrow_screen())
    ctx = Ctx(state["search"], on_tap)
    assert mainquest.npc_search(ctx) is None
    searches = [p for p in ctx.taps if _in(p, SEARCH_BTN, POPUP_AT)]
    assert len(searches) == mainquest.NPC_SAME_N and len(ctx.taps) <= 2 * mainquest.NPC_ROUNDS


def test_climb_search_button_dead_taps_once():
    ctx = Ctx(search_screen())
    assert mainquest.npc_search(ctx) is None
    assert len(ctx.taps) == 1


def test_dead_sprite_is_blacklisted_not_retapped():
    ctx = Ctx(arrow_screen())
    assert mainquest.tap_rebel(ctx) is False
    assert len(ctx.taps) == 1 and tapguard.of(ctx).blocked("world", *ctx.taps[0])
    assert mainquest.tap_rebel(ctx) is False and len(ctx.taps) == 1


def test_quest_flow_full_climb_never_taps_screen_centre(monkeypatch):
    sent = []
    monkeypatch.setattr(mainquest, "npc_engage", lambda c, mq, p: sent.append(p) or "npc_sent")
    screens = {"city": blank(), "search": search_screen(), "world": arrow_screen(), "attack": attack_screen()}
    nxt = {"city": "search", "search": "world", "world": "attack"}

    def on_tap(c, x, y):
        key = next(k for k, s in screens.items() if s is c.screen)
        c.screen = screens[nxt[key]]

    ctx = Ctx(screens["city"], on_tap)
    assert mainquest.npc_attack(ctx, {}) == "npc_sent"
    assert sent and _in(sent[0], ATTACK_BTN, POPUP_AT)
    assert ctx.taps[0] == mainquest.BANNER and mainquest.TARGET not in ctx.taps


def test_arrow_module_climbs_too(monkeypatch):
    sent = []
    monkeypatch.setattr(mainquest, "npc_engage", lambda c, mq, p: sent.append(p) or "npc_sent")
    ctx, first, _ = _climb_ctx(attack_screen)
    assert arrow.handle(ctx, first) == "sent"
    assert _in(sent[0], ATTACK_BTN, POPUP_AT)


def test_mech_search_popup_climbs_with_rally_goal(monkeypatch):
    goals = []
    monkeypatch.setattr(mainquest, "npc_search", lambda c, goal="attack": goals.append(goal))
    img = search_screen()
    assert rebels.popup_target(Ctx(img), {}, {"fail": {}}, img, (268, 195, 1.0)) == -1
    assert goals == ["rally"]


@pytest.mark.parametrize("win,want", [(False, "npc_skip"), (True, "npc_sent")])
def test_march_screen_needs_predicted_win(monkeypatch, win, want):
    """Man "Cai dat Quan doan" co gather/btn_march: chi Xuat chinh khi du doan thang toan dien."""
    march = blank()
    tpl = V.load("gather/btn_march")
    h, w = tpl.shape[:2]
    march[889 - h // 2:889 - h // 2 + h, 382 - w // 2:382 - w // 2 + w] = tpl
    monkeypatch.setattr(rebels, "pred_win", lambda img: win)
    monkeypatch.setattr(quest_rules, "npc_ok", lambda *a: (True, "phien quan Lv.2"))    # chi kiem cong du doan
    attack = attack_screen()

    def on_tap(c, x, y):
        c.screen = march if c.screen is attack else blank()

    ctx = Ctx(attack, on_tap)
    ctx.shot()
    assert mainquest.npc_engage(ctx, {}, mainquest.find_attack(attack, V)) == want
    assert ("gather/btn_march" in ctx.tpl_taps) is win
