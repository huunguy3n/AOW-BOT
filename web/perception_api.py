"""Tab "Nhan dien" (web): gan nhan tay cho dataset nhan dien (docs/perception/dataset-schema.md).

Doc data/perception/<ds>/{manifest.json, review.csv, review/, images/}; nhan luu <ds>/labels.json (ghi atomic).
Chi doc/ghi du lieu dataset - khong cham may, khong dung runner. Logic thuan: aowbot.perception.eval.labeling.
"""
import csv
import os
import re
import threading
from pathlib import Path

from flask import jsonify, request, send_from_directory

from aowbot.perception.eval import dataset as ds
from aowbot.perception.eval import labeling as lb
from aowbot.perception.eval import names as nm

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data" / "perception"
SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")
BAD_CLS_CHARS = frozenset(",'<>") | {chr(34)}   # cam trong ten lop (CSV/HTML)
_lock = threading.Lock()


def _dir(name):
    """Thu muc dataset hop le (v0, v1...) hoac None."""
    name = name or "v0"
    if not SAFE.match(name) or not (ROOT / name / "manifest.json").exists():
        return None
    return ROOT / name


def _items(d):
    with (d / "review.csv").open(encoding="utf-8") as f:
        return [{"id": r["id"], "x": int(r["tap_x"]), "y": int(r["tap_y"]), "outcome": r["outcome"]}
                for r in csv.DictReader(f)]


def _check_label(j):
    """-> (thu muc, id, lop, loi). loi = None neu hop le."""
    d = _dir(j.get("ds"))
    sid, cls = str(j.get("id", "")), str(j.get("cls", "")).strip()
    if d is None or not SAFE.match(sid):
        return d, sid, cls, "dataset/id khong hop le"
    if sid not in {i["id"] for i in _items(d)}:
        return d, sid, cls, "id khong co trong review.csv"
    if len(cls) > 80 or (not cls.isprintable() or BAD_CLS_CHARS & set(cls)):
        return d, sid, cls, "ten lop khong hop le (<=80 ky tu, khong dau phay/nhay/<>)"
    return d, sid, cls, None


def register(app):
    _register_read(app)
    _register_write(app)


def _register_read(app):
    @app.get("/api/perception")
    def perception_state():
        d = _dir(request.args.get("ds"))
        if d is None:
            return jsonify(ok=False, error="chua co dataset: chay tools/perception_build_dataset.py"), 404
        data = ds.load(d / "manifest.json")
        with _lock:
            store = lb.load_store(d / "labels.json")
        items = _items(d) if (d / "review.csv").exists() else []
        inst = {s.id: s.instance for s in data.samples}
        for it in items:
            it["inst"] = inst.get(it["id"])
            it["label"] = store["labels"].get(it["id"])
        insts = sorted({s.instance for s in data.samples})
        named = [i for i in items if (i["label"] or {}).get("c")]
        new_classes = sorted({i["label"]["c"] for i in named} - set(data.classes) - {lb.NONE})
        return jsonify(ok=True, dataset=d.name, version=data.version, classes=list(data.classes), items=items,
                       instances=insts, builds=store["builds"], labelled=len(named),
                       none_count=sum(1 for i in named if i["label"]["c"] == lb.NONE),
                       new_classes=new_classes, names=nm.display_map([*data.classes, *new_classes]),
                       splits={sp: len(data.in_split(sp)) for sp in ds.SPLITS},
                       outputs=sorted(p.name for p in ROOT.iterdir() if (p / "manifest.json").exists()))

    @app.get("/perception_img/<name>/<kind>/<sid>")
    def perception_img(name, kind, sid):
        d = _dir(name)
        sub = {"crop": "review", "full": "images"}.get(kind)
        if d is None or sub is None or not SAFE.match(sid):
            return "", 404
        return send_from_directory(d / sub, sid + ".png")


def _register_write(app):
    @app.post("/api/perception/label")
    def perception_label():
        j = request.json or {}
        d, sid, cls, err = _check_label(j)
        if err:
            return jsonify(ok=False, error=err), 400
        w = max(8, min(540, int(j.get("w") or lb.DEFAULT_SIZE)))
        h = max(8, min(960, int(j.get("h") or lb.DEFAULT_SIZE)))
        with _lock:
            store = lb.load_store(d / "labels.json")
            if cls:
                store["labels"][sid] = {"c": cls, "w": w, "h": h}
            else:
                store["labels"].pop(sid, None)
            lb.save_store(d / "labels.json", store)
        return jsonify(ok=True)

    @app.post("/api/perception/builds")
    def perception_builds():
        j = request.json or {}
        d = _dir(j.get("ds"))
        b = j.get("builds")
        if d is None or not isinstance(b, dict):
            return jsonify(ok=False, error="dataset/builds khong hop le"), 400
        clean = {str(int(k)): str(v).strip()[:40] for k, v in b.items() if str(v).strip()}
        with _lock:
            store = lb.load_store(d / "labels.json")
            store["builds"] = clean
            lb.save_store(d / "labels.json", store)
        return jsonify(ok=True)

    @app.post("/api/perception/apply")
    def perception_apply():
        """Tao v1 tu nhan da gan (ghi de v1 cu - chi la du lieu dan xuat, nguon v0 + labels.json khong doi)."""
        j = request.json or {}
        d = _dir(j.get("ds"))
        if d is None or d.name == "v1":
            return jsonify(ok=False, error="dataset nguon khong hop le"), 400
        with _lock:
            store = lb.load_store(d / "labels.json")
        labels = lb.to_labels(store, lb.read_taps(d / "review.csv"))
        if not labels:
            return jsonify(ok=False, error="chua gan nhan nao"), 400
        try:
            new = lb.materialize(d, ROOT / "v1", labels, store["builds"])
        except ValueError as e:
            return jsonify(ok=False, error=str(e)), 400
        return jsonify(ok=True, samples=len(new.samples), classes=len(new.classes),
                       splits={sp: len(new.in_split(sp)) for sp in ds.SPLITS}, labelled=len(labels))
