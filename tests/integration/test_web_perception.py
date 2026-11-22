# ruff: noqa: RUF001
"""Tab Nhan dien: /api/perception* gan nhan qua web (dataset tong hop trong thu muc tam, khong dung data that)."""
import json

import cv2
import numpy as np
import pytest
from flask import Flask

from aowbot.perception.eval import dataset as ds
from web import perception_api


@pytest.fixture()
def client(tmp_path, monkeypatch):
    root = tmp_path / "perception"
    d = root / "v0"
    (d / "images").mkdir(parents=True)
    (d / "review").mkdir()
    samples = []
    for i in range(3):
        sid = f"h-i{i}-000{i}"
        p = d / "images" / f"{sid}.png"
        cv2.imwrite(str(p), np.zeros((960, 540, 3), np.uint8))
        cv2.imwrite(str(d / "review" / f"{sid}.png"), np.zeros((120, 120, 3), np.uint8))
        samples.append(ds.Sample(sid, f"images/{sid}.png", ds.sha256_file(p), f"sess{i}", i, "unknown", "unknown",
                                 "train", "bootstrap", False, ()))
    ds.save(ds.Dataset("v0", ("a/b",), tuple(samples)), d / "manifest.json")
    (d / "review.csv").write_text("id,tap_x,tap_y,changed,outcome,class,w,h\n"
                                  + "".join(f"{s.id},100,200,1,changed,,,\n" for s in samples), encoding="utf-8")
    monkeypatch.setattr(perception_api, "ROOT", root)
    app = Flask(__name__)
    perception_api.register(app)
    return app.test_client(), samples, root


def test_state_label_roundtrip(client):
    c, samples, _ = client
    j = c.get("/api/perception").get_json()
    assert j["ok"] and len(j["items"]) == 3 and j["labelled"] == 0 and j["instances"] == [0, 1, 2]
    assert j["names"]["map/rebel_mech"] == "Bản đồ › Phản quân Cơ giáp (thân)" and j["names"]["a/b"] == "a/b"
    sid = samples[0].id
    assert c.post("/api/perception/label", json={"id": sid, "cls": "new/cls", "w": 30, "h": 20}).get_json()["ok"]
    assert c.post("/api/perception/label", json={"id": samples[1].id, "cls": "-"}).get_json()["ok"]
    j = c.get("/api/perception").get_json()
    assert j["labelled"] == 2 and j["none_count"] == 1 and j["new_classes"] == ["new/cls"]
    assert j["items"][0]["label"] == {"c": "new/cls", "w": 30, "h": 20}
    c.post("/api/perception/label", json={"id": sid, "cls": ""})            # xoa nhan
    assert c.get("/api/perception").get_json()["labelled"] == 1


def test_label_rejects_bad_input(client):
    c, samples, _ = client
    assert c.post("/api/perception/label", json={"id": "../x", "cls": "a"}).status_code == 400
    assert c.post("/api/perception/label", json={"id": "khong-co", "cls": "a"}).status_code == 400
    assert c.post("/api/perception/label", json={"id": samples[0].id, "cls": "a,b"}).status_code == 400
    assert c.post("/api/perception/label", json={"id": samples[0].id, "cls": "x" * 81}).status_code == 400
    assert c.get("/api/perception?ds=../etc").status_code == 404


def test_images_served_and_traversal_blocked(client):
    c, samples, _ = client
    assert c.get(f"/perception_img/v0/crop/{samples[0].id}").status_code == 200
    assert c.get(f"/perception_img/v0/full/{samples[0].id}").status_code == 200
    assert c.get("/perception_img/v0/other/x").status_code == 404
    assert c.get("/perception_img/v0/crop/..%2Fmanifest.json").status_code == 404


def test_builds_and_apply(client):
    c, samples, root = client
    assert c.post("/api/perception/apply", json={}).status_code == 400       # chua co nhan
    c.post("/api/perception/builds", json={"builds": {"0": "vn-2.5.16", "1": "  "}})
    for s in samples:
        c.post("/api/perception/label", json={"id": s.id, "cls": "x/y"})
    j = c.post("/api/perception/apply", json={}).get_json()
    assert j["ok"] and j["labelled"] == 3 and j["samples"] <= 3
    v1 = ds.load(root / "v1" / "manifest.json")
    assert ds.validate(v1) == [] and all(s.source == "human" for s in v1.samples)
    assert {s.instance: s.game_build for s in v1.samples}.get(0, "vn-2.5.16") == "vn-2.5.16"
    assert json.loads((root / "v0" / "labels.json").read_text(encoding="utf-8"))["builds"] == {"0": "vn-2.5.16"}
