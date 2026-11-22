"""P5 muc 4 (PM 2026-11-23): phong thu an toan khi thieu anh mau; giu luat khien (A-SAFE-1, ADR-0008)."""
import types

import pytest
import yaml

from bot import tplneed
from bot.modules import defense


class V:
    def __init__(self, have=(), seen=()):
        self.have, self.seen = set(have), set(seen)

    def has(self, name):
        return name in self.have

    def find(self, img, name, **k):
        return (100, 200, 0.9) if name in self.seen else None


# ---------- phong thu ----------
@pytest.fixture(autouse=True)
def _reset_tplneed():
    tplneed._last.clear()
    yield
    tplneed._last.clear()


class DefCtx:
    def __init__(self, v, cfg=None):
        self.v, self.cfg = v, cfg or {"defense": {"shield_hours": 8}}
        self.dev = types.SimpleNamespace(idx=0)

    def __getattr__(self, name):
        raise AssertionError(f"khong duoc thao tac ({name}) khi thieu anh mau")


def test_shield_missing_row_template_never_opens_panel(caplog):
    v = V(have={"defense/btn_shield_icon", "defense/title", "defense/row_12h"})
    with caplog.at_level("INFO", logger="aow"):
        assert defense.shield(DefCtx(v)) == "missing_tpl"
    assert "thieu anh mau defense/row_8h" in caplog.text


def test_shield_hours_override_missing_template():
    v = V(have={"defense/btn_shield_icon", "defense/title", "defense/row_12h"})
    assert defense.missing_tpls(v, 12) == []
    assert defense.missing_tpls(v, 8) == ["defense/row_8h"]
    assert defense.shield(DefCtx(v), hours=8, allow_buy=False, extend=True) == "missing_tpl"


def test_under_attack_without_alert_template_falls_back_to_red_flash(caplog, monkeypatch):
    monkeypatch.setattr(defense, "edge_red", lambda img: (0.0, 0.0))
    ctx = types.SimpleNamespace(v=V(), cfg={"defense": {"red_flash": True}}, shot=lambda: "img")
    with caplog.at_level("INFO", logger="aow"):
        assert defense.under_attack(ctx, "img") is False
    assert "thieu anh mau defense/alert_attack" in caplog.text


def test_war_day_never_buys_with_gems_by_default():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["warday"]["buy_gems"] is False
    # phong thu khi bi danh: mua chi khi config cho + trong tran ngay (A-SAFE-1, ADR-0008) - luat o policy
    assert defense.shield_choice(0, 99999, 3600, 0, 2000, False)[0] == "no_item"
    assert defense.shield_choice(0, 99999, 3600, 0, 2000, True)[0] == "cap"
