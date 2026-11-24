"""P10-5 (live-run-3): reddots het 240 s (Tinh bao an ~4 phut) con 11 cham do - hop qua lien minh 12, thu 4 (tab Bao
cao), Quà dac biet con 2 mon (s153317/s153326), chieu mo 1. Uu tien nhan qua, de tien trinh dai cho buoc rieng, Doc &
nhan nhanh o moi tab co cham do (khong 'Xoa tat ca da doc'), Qua dac biet lap toi het, quet nhan qua cuoi luot."""
import os
import types

import cv2
import numpy as np
import pytest

from bot import buttons, screens
from bot.badges import red_dots
from bot.modules import alliance, reddots, rewards
from bot.vision import Vision

AUTO = "data/pm-shots/owner-20261124/live3/auto"


def _img(name):
    p = f"{AUTO}/{name}.png"
    if not os.path.exists(p):
        pytest.skip(f"thieu anh {p}")
    return cv2.imread(p)


def test_claim_kinds_before_long_kinds():
    kinded = [((64, 629), "intel"), ((525, 730), "mail"), ((456, 796), "ally_gift"), ((441, 898), "play")]
    assert reddots.pick(kinded)[1] in ("mail", "ally_gift")


def test_long_kind_deferred_when_step_pending():
    assert reddots.defer_to_step("intel", {"intel", "rebels", "gather"}) == "intel"
    assert reddots.defer_to_step("play", {"play"}) == "play"
    assert reddots.defer_to_step("intel", {"gather"}) is None          # buoc rieng da chay -> lam luon
    assert reddots.defer_to_step("mail", {"rewards"}) is None          # nhan qua khong hoan
    assert reddots.defer_to_step("intel", None) is None


def test_grace_only_for_claim_kinds():
    assert reddots.in_budget("intel", 100, 200, 90)
    assert not reddots.in_budget("intel", 250, 200, 90)
    assert reddots.in_budget("mail", 250, 200, 90) and reddots.in_budget("ally_gift", 289, 200, 90)
    assert not reddots.in_budget("mail", 291, 200, 90)
    assert reddots.in_budget("generic", 10**9, None, 0)


def test_mail_report_tab_frame():
    """s153252: dang o tab Bao cao (cham do tab 414,68), dong thu con cham do x 515; nut 'Doc & nhan nhanh' ben PHAI."""
    img = _img("s153252")
    assert red_dots(img, (0, 58, 540, 50))
    assert red_dots(img, rewards.ITEM_DOTS["mail"])
    v = Vision("templates")
    p = v.find(img, "rewards/mail/once_1", roi=rewards.ONCE_ROI["mail"])
    assert p and p[0] >= 300                              # khong phai "Xoa tat ca da doc" (trai)


class MailCtx:
    def __init__(self, dots_after):
        self.dots_after = list(dots_after)
        self.taps = []

    def claim_loop(self, claims, n):
        return 0

    def tap_tpl(self, name, wait=1.0, roi=None, **k):
        self.taps.append((name, roi))
        return True

    def dismiss_reward(self):
        pass

    def shot(self):
        img = np.zeros((960, 540, 3), np.uint8)
        if self.dots_after and self.dots_after.pop(0):
            cv2.circle(img, (515, 300), 8, (0, 0, 255), -1)
        return img


def test_read_and_claim_repeats_while_rows_dotted():
    c = MailCtx([True, False])
    assert rewards.claim_tab(c, [], ["rewards/mail/once_1"], 30, "mail") == 2
    assert all(r == rewards.ONCE_ROI["mail"] for _, r in c.taps)     # chi vung phai duoi


def test_special_gifts_retry_slow_claim(monkeypatch):
    """2 mon cuoi: lan bam dau man chua doi (hieu ung) -> chup lai, bam lai; khong bo som."""
    items = [1, 1]
    seq = iter([True, True, False, False])           # lan 1: man chua doi ca sau khi cho -> bam lai (khong bo)
    monkeypatch.setattr(alliance.time, "sleep", lambda s: None)
    monkeypatch.setattr(screens, "same", lambda a, b: next(seq, False))

    def with_text(img, rx, roi=None, **k):
        return [buttons.Button(510, 320, 70, 30, "claim", 90, "nhan")] if items else []
    monkeypatch.setattr(buttons, "with_text", with_text)
    taps = []

    def tap(x, y, wait=1.0):
        taps.append((x, y))
        if len(taps) > 1 and items:
            items.pop()
    ctx = types.SimpleNamespace(tap_tpl=lambda *a, **k: False, shot=lambda: None, tap=tap, dismiss_reward=lambda: None)
    assert alliance.special_claim(ctx) == 2 and not items


def test_final_claims_runs_mail_ally_recruit(monkeypatch):
    calls = []
    monkeypatch.setattr(rewards, "ally_gift_until_clear", lambda ctx, r: calls.append("ally") or 3)
    monkeypatch.setattr(rewards, "run_until_clear", lambda ctx, route, a, b: calls.append(route) or 2)
    monkeypatch.setattr(reddots, "_handle", lambda ctx, kind, x, y: calls.append(kind) or 1)
    monkeypatch.setattr(reddots, "red_dots", lambda img, *a: [(130, 730)])
    ctx = types.SimpleNamespace(cfg={"rewards": {"routes": ["mail"], "ally_gift": True}, "modules": {}},
                                ensure_city=lambda: None, shot=lambda: None,
                                v=types.SimpleNamespace(find=lambda img, n, **k: (130, 760, 0.9)))
    assert reddots.final_claims(ctx) == 6
    assert calls == ["ally", "mail", "recruit"]


def test_final_claims_can_be_disabled():
    ctx = types.SimpleNamespace(cfg={"reddots": {"final_claims": False}})
    assert reddots.final_claims(ctx) == 0
