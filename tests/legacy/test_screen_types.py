"""Loai man chi tiet + muc dich cho cham (chu du an 2026-11-21: cham khong chi de thoat ma con nhan / lam nhiem vu)."""
import numpy as np
import pytest

from bot import screen_types as st


@pytest.fixture
def tmp_catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(st, "CATALOG", str(tmp_path / "types.json"))
    monkeypatch.setattr(st, "TAUGHT", str(tmp_path / "taught.jsonl"))
    monkeypatch.setattr(st, "BASE", str(tmp_path))
    taught = []
    monkeypatch.setattr("bot.learn.teach", lambda mem, img, label, x=None, y=None: taught.append((label, x, y)))
    return taught


class V:
    def find(self, img, name):
        return (156, 582, 0.95) if name == "common/btn_cancel_exit" else None


IMG = np.zeros((960, 540, 3), np.uint8)


def test_add_type_keeps_base_parent(tmp_catalog):
    k = st.add("Tăng cấp tướng", "panel")
    assert k == "tang_cap_tuong" and st.get(k)["parent"] == "panel" and not st.get(k)["base"]
    with pytest.raises(ValueError):
        st.add("X", "khong_co")


def test_only_close_intent_feeds_navigation(tmp_catalog):
    k = st.add("Tăng cấp tướng", "panel")
    assert st.teach(None, V(), IMG, "d/a_before.png", k, "progress", 285, 827) is None
    assert st.teach(None, V(), IMG, "d/b_before.png", k, "close", 30, 40) is None
    # kNN ghi theo nhom GOC; cho cham 'Tang cap' (progress) KHONG thanh cho thoat
    assert tmp_catalog == [("panel", None, None), ("panel", 30, 40)]
    assert st.taught()["d/a_before.png"]["intent"] == "progress"


def test_exit_dialog_close_must_be_cancel(tmp_catalog):
    assert st.teach(None, V(), IMG, "d/c_before.png", "exit_dialog", "close", 384, 582)   # 'Xac nhan' -> loi
    assert st.teach(None, V(), IMG, "d/c_before.png", "exit_dialog", "close", 160, 585) is None


def test_no_follow_flag(tmp_catalog):
    k = st.add("Danh sách kênh chat", "panel", no_follow=True)
    assert st.get(k)["no_follow"] is True
