"""Hang cho hoc tu thao tac tay: chi cham lam man doi, khong tren thanh pho/ban do, gom trung, danh dau da xem."""
import json

import cv2
import numpy as np

from bot import human_review as hr


class V:
    """Vision gia: man 'city' neu anh sang, 'popup' neu toi; nut Huy o (156, 582)."""
    def find(self, img, name):
        return (156, 582, 0.95) if name == "common/btn_cancel_exit" else None


def setup(tmp_path, monkeypatch, evs, imgs):
    day = tmp_path / "human" / "20261121"
    day.mkdir(parents=True)
    for name, val in imgs.items():
        cv2.imwrite(str(day / name), np.full((960, 540, 3), val, np.uint8))
    (day / "events.jsonl").write_text("\n".join(json.dumps(e) for e in evs), encoding="utf-8")
    monkeypatch.setattr(hr, "HUMAN", str(tmp_path / "human"))
    monkeypatch.setattr(hr, "STATE", str(tmp_path / "state.json"))
    monkeypatch.setattr(hr.screens, "identify", lambda img, v: ("city" if img.mean() > 100 else "popup", None))


def ev(n, x=100, y=100, changed=1, typ="tap", at=0):
    return {"type": typ, "x": x, "y": y, "changed": changed, "before": f"{n}_before.png", "after": f"{n}_after.png",
            "at": at, "step": "quests", "idx": 1, "clock": "10:00:00"}


def test_queue_filters_and_dedupes(tmp_path, monkeypatch):
    imgs = {f"{n}_before.png": v for n, v in (("a", 10), ("b", 10), ("c", 200), ("d", 10), ("e", 10))}
    setup(tmp_path, monkeypatch, [ev("a", at=5), ev("b", x=110, at=4),    # b trung a (cung man, cung o 40px)
                                  ev("c", at=3),                          # thanh pho -> bo
                                  ev("d", changed=0, at=2),               # cham khong an -> bo
                                  ev("e", typ="swipe", at=1)], imgs)      # keo -> bo
    q = hr.pending(V())
    assert [x["file"] for x in q] == ["20261121/a_before.png"] and q[0]["guess"] == "popup"
    hr.mark_done("20261121/a_before.png", "skip")
    assert [x["file"] for x in hr.pending(V())] == ["20261121/b_before.png"]


def test_path_guard_and_exit_cancel_only(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, [], {"a_before.png": 10})
    assert hr.path_of("20261121/a_before.png")
    assert hr.path_of("../x_before.png") is None and hr.path_of("20261121/a_after.png") is None
    img = np.zeros((960, 540, 3), np.uint8)
    assert hr.exit_tap_ok(img, V(), 160, 590)          # nut Huy
    assert not hr.exit_tap_ok(img, V(), 384, 582)      # nut Xac nhan (thoat game) -> khong bao gio hoc
