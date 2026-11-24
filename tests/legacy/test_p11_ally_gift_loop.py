"""P11 (chu du an t52u 2026-11-24): qua lien minh nhan LAP DEN HET tren ca 2 tab (Qua dac biet + Qua thuong).
Live3 #1: nhan 1 trang roi bo di (log 'nhan toan bo lan 1 (co the nhan 243 -> 200)'), qua phat sinh lien tuc ->
cuoi luot badge Lien minh 26. Vong moi: nhan -> lam moi tab -> doc lai so -> lap; tran vong/giay; chong ket."""
import logging
import os
import re
import types
from pathlib import Path

import cv2
import pytest

from bot import buttons, ocr, screens
from bot.modules import alliance, reddots, rewards

AUTO = "data/pm-shots/owner-20261124/live3/auto"
TESS = "C:/Program Files/Tesseract-OCR/tesseract.exe"


def _img(name):
    p = f"{AUTO}/{name}.png"
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    return cv2.imread(p)


def _tess():
    if not ocr.init(TESS):
        pytest.skip("khong co Tesseract")


# ---------- ham thuan tren khung live3 that (ADB 540x960) ----------
def test_active_tab_live3():
    assert alliance.active_tab(_img("s152956")) == "normal"
    assert alliance.active_tab(_img("s153301")) == "special"
    assert alliance.active_tab(_img("s153326")) == "special"
    assert alliance.active_tab(_img("s153334")) == "normal"


def test_tab_dots_live3():
    img = _img("s152956")                                  # Qua dac biet 8, Qua thuong 43
    assert alliance.tab_dot(img, "special") and alliance.tab_dot(img, "normal")
    img = _img("s153334")                                  # "Chua co qua", khong so do
    assert not alliance.tab_dot(img, "special") and not alliance.tab_dot(img, "normal")


def test_list_buttons_live3():
    assert alliance.list_buttons(_img("s152956")) == 5     # 5 nut Nhan thay tren trang (con 43)
    assert alliance.list_buttons(_img("s153301")) == 5
    assert alliance.list_buttons(_img("s153326")) == 2     # danh sach co dan
    assert alliance.list_buttons(_img("s153334")) == 0


@pytest.mark.parametrize("name,tab,n", [
    ("s152956", "normal", 43),     # so do tab 43 > 5 nut thay -> 43 (khong phai 'Co the nhan:243')
    ("s153301", "special", 8),
    ("s153309", "special", 5),     # so do doc khong chac -> so nut thay
    ("s153326", "special", 2),
    ("s153334", "normal", 0),      # "Chua co qua"
])
def test_gift_count_live3(name, tab, n):
    _tess()
    assert alliance.gift_count(_img(name), tab) == n


def test_gift_empty_live3():
    _tess()
    assert alliance.gift_empty(_img("s153334"))
    assert not alliance.gift_empty(_img("s152956"))
    assert not alliance.gift_empty(_img("s153326"))


def test_can_claim_is_daily_cap_not_pending():
    _tess()
    assert alliance.gift_can_claim(_img("s152956")) == 243   # tran trong ngay
    assert alliance.gift_can_claim(_img("s153334")) == 200   # van 200 khi danh sach rong


def test_claim_all_roi_excludes_anon_and_send():
    x, y, w, h = alliance.CLAIM_ALL_ROI
    assert x <= 269 <= x + w and y <= 905 <= y + h           # "Nhan toan bo" s152956
    lx, ly, _lw, lh = alliance.GIFT_LIST_ROI
    assert ly + lh < 915 and lx > 330                         # o "Tang qua an danh" (~30,928) ngoai cot nut Nhan


def test_gift_progress():
    assert alliance.gift_progress(8, 6, 2)
    assert alliance.gift_progress(43, 0, 0)
    assert not alliance.gift_progress(5, 5, 0)
    assert not alliance.gift_progress(None, None, 0)
    assert alliance.gift_progress(None, None, 1)


# ---------- mo phong bang qua (qua phat sinh lien tuc) ----------
class Game:
    """Bang Qua tang lien minh gia: so qua moi tab, tab dang chon, qua moi den khi lam moi tab."""

    def __init__(self, special=0, normal=0, can=200, arrivals=None, claim_all_dead=False):
        self.n = {"special": special, "normal": normal}
        self.active, self.can = "normal", can
        self.arrivals = list(arrivals or [])        # [(tab, so)] moi lan lam moi (chuyen tab) lay 1
        self.claim_all_dead = claim_all_dead
        self.taps, self.tpl, self.debug, self.claimed = [], [], [], 0
        self.clock = 0.0

    def img(self):
        return ("img", self.active, self.n["special"], self.n["normal"], self.can)

    # ctx
    def shot(self):
        self.clock += 0.5
        return self.img()

    def tap(self, x, y, wait=1.0):
        self.clock += wait
        self.taps.append((x, y))
        for k, p in alliance.TABS.items():
            if (x, y) == p:
                if k != self.active and self.arrivals:
                    t, add = self.arrivals.pop(0)
                    self.n[t] += add
                self.active = k
                return
        if alliance.GIFT_LIST_ROI[0] <= x and self.n[self.active] > 0:    # nut "Nhan" tung mon
            self.n[self.active] -= 1
            self.claimed += 1

    def tap_tpl(self, name, wait=1.2, roi=None, **k):
        self.clock += wait
        self.tpl.append((name, roi))
        if name != "ally/btn_gift_claim_all" or self.active != "normal" or self.n["normal"] <= 0:
            return False
        if not self.claim_all_dead:
            self.claimed += self.n["normal"]
            self.can -= self.n["normal"]
            self.n["normal"] = 0
        return True

    def dismiss_reward(self):
        pass

    def wait_for(self, name, **k):
        return True

    def save_debug(self, tag):
        self.debug.append(tag)
        return f"logs/shots/x-{tag}.png"


@pytest.fixture
def sim(monkeypatch):
    def make(cfg=None, **kw):
        g = Game(**kw)
        monkeypatch.setattr(alliance.time, "time", lambda: g.clock)
        monkeypatch.setattr(alliance.time, "sleep", lambda s: None)
        monkeypatch.setattr(alliance, "lv_chest", lambda ctx: 0)
        monkeypatch.setattr(alliance, "gift_sent", lambda img: None)
        monkeypatch.setattr(alliance, "active_tab", lambda img: img[1])
        monkeypatch.setattr(alliance, "gift_can_claim", lambda img: img[4])
        monkeypatch.setattr(alliance, "tab_dot", lambda img, t: (1, 1) if img[2 if t == "special" else 3] else None)
        monkeypatch.setattr(alliance, "gift_count", lambda img, t: img[2 if t == "special" else 3])
        monkeypatch.setattr(screens, "same", lambda a, b: a == b)
        monkeypatch.setattr(buttons, "with_text", lambda img, rx, roi=None, **k: [
            buttons.Button(468, 319 + 104 * i, 84, 32, "go", 95, "nhan")
            for i in range(min(5, img[2] if img[1] == "special" else 0))])
        ctx = types.SimpleNamespace(cfg={"alliance": cfg or {}}, mem=None,
                                    dev=types.SimpleNamespace(idx=1), shot=g.shot, tap=g.tap, tap_tpl=g.tap_tpl,
                                    dismiss_reward=g.dismiss_reward, wait_for=g.wait_for, save_debug=g.save_debug)
        return g, ctx
    return make


def test_loop_keeps_going_when_gifts_keep_arriving(sim, caplog):
    """Live3: 8 dac biet + 43 thuong; trong luc nhan co them qua (dac biet +2, thuong +5, thuong +3) -> nhan het."""
    g, ctx = sim(special=8, normal=43, arrivals=[("normal", 5), ("special", 2), ("normal", 3)])
    with caplog.at_level(logging.INFO, logger="aow"):
        alliance.gift_loop(ctx)
    assert g.n == {"special": 0, "normal": 0}
    assert g.claimed == 8 + 2 + 43 + 5 + 3
    assert "het qua sau" in caplog.text
    assert re.search(r"Qua lien minh thuong vong 1: con \d+ -> 0 \(Nhan toan bo", caplog.text)
    assert "Qua lien minh dac biet vong 1: con 8 -> " in caplog.text


def test_loop_rereads_after_refresh_not_one_page(sim):
    """Khong dung chi vi da nhan het 1 trang: sau khi nhan, lam moi thay qua moi -> vong tiep."""
    g, ctx = sim(special=0, normal=43, arrivals=[("special", 0), ("normal", 7)] * 2)
    alliance.gift_loop(ctx)
    assert g.n["normal"] == 0 and g.claimed == 43 + 7 + 7


def test_loop_empty_stops_fast(sim):
    g, ctx = sim(special=0, normal=0)
    assert alliance.gift_loop(ctx) == 0
    assert not any(n == "ally/btn_gift_claim_all" for n, _ in g.tpl)
    assert len(g.taps) <= 4                                 # 1 vong: mo 2 tab (+ lam moi) roi dung


def test_loop_round_cap(sim, caplog):
    """Qua den moi lan lam moi (vo han) -> dung o gift_loop_rounds, log con bao nhieu."""
    _g, ctx = sim(normal=3, arrivals=[("normal", 3)] * 500, cfg={"gift_loop_rounds": 4, "gift_loop_max_s": 10_000})
    with caplog.at_level(logging.INFO, logger="aow"):
        alliance.gift_loop(ctx)
    assert "cham tran (4/4 vong" in caplog.text and "thuong" in caplog.text


def test_loop_time_cap(sim, caplog):
    g, ctx = sim(normal=3, arrivals=[("normal", 3)] * 500, cfg={"gift_loop_rounds": 999, "gift_loop_max_s": 30})
    with caplog.at_level(logging.INFO, logger="aow"):
        alliance.gift_loop(ctx)
    assert "cham tran" in caplog.text
    assert g.clock < 30 + 15                                # khong chay qua tran nhieu


def test_loop_stall_saves_shot_and_stops(sim, caplog):
    """"Nhan toan bo" bam ma khong an (man khong doi, so khong giam) 2 vong -> anh logs/shots + dung tab."""
    g, ctx = sim(normal=20, claim_all_dead=True)
    with caplog.at_level(logging.INFO, logger="aow"):
        alliance.gift_loop(ctx)
    assert g.debug == ["ally_gift_stall_normal"]
    assert "vong so khong giam" in caplog.text
    assert sum(1 for n, _ in g.tpl if n == "ally/btn_gift_claim_all") == 2


def test_loop_skips_normal_when_daily_cap_zero(sim):
    g, ctx = sim(special=3, normal=10, can=0)
    alliance.gift_loop(ctx)
    assert g.n == {"special": 0, "normal": 10}              # Co the nhan 0 -> khong bam tab thuong
    assert g.claimed == 3


def test_loop_never_taps_send_or_anon_area(sim):
    g, ctx = sim(special=12, normal=43, arrivals=[("special", 4), ("normal", 6)])
    alliance.gift_loop(ctx)
    for x, y in g.taps:
        assert (x, y) in alliance.TABS.values() or (x >= alliance.GIFT_LIST_ROI[0] and y < 860)
    assert all(roi == alliance.CLAIM_ALL_ROI for n, roi in g.tpl if n == "ally/btn_gift_claim_all")


# ---------- moi duong vao deu qua gift_loop ----------
def test_all_entry_points_use_gift_loop(monkeypatch):
    calls = []
    monkeypatch.setattr(alliance, "gift_loop", lambda ctx: calls.append("loop") or 7)
    ctx = types.SimpleNamespace(tap=lambda *a, **k: None, wait_for=lambda *a, **k: True,
                                tap_tpl=lambda *a, **k: True, back_out=lambda n=1: None)
    assert alliance.gifts(ctx, 456, 796) == 7               # reddots._handle + rewards.ally_gift_until_clear
    assert alliance.gifts_tile(ctx) == 7                    # alliance.run
    assert alliance.gift_panel(ctx) == 7
    assert calls == ["loop"] * 3
    src = "".join(Path(m.__file__).read_text(encoding="utf-8") for m in (reddots, rewards))
    assert "btn_gift_claim_all" not in src                  # khong con nhanh nhan 1 trang rieng
