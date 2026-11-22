"""Gan nhan nguoi: luu nhan (labels.json), ap nhan vao dataset -> v1 co split test (chi mau co nhan nguoi).

Khong import cv2 / flask: web (web/perception_api.py) va tools/perception_apply_labels.py dung chung.
labels.json: {"labels": {id: {"c": lop | "-", "w": int, "h": int}}, "builds": {"<instance>": "<ban game>"}}
Lop "-" = nguoi xac nhan KHONG co doi tuong tai diem cham (anh van complete=false).
"""
from __future__ import annotations

import csv
import json
import os
import shutil
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from . import dataset as ds

NONE = "-"
DEFAULT_SIZE = 48
Label = tuple[str, int, int, int, int]   # (lop, tap_x, tap_y, w, h)


def load_store(path: Path) -> dict[str, Any]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return {"labels": dict(d.get("labels", {})), "builds": dict(d.get("builds", {}))}


def save_store(path: Path, store: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def read_taps(review_csv: Path) -> dict[str, tuple[int, int]]:
    with review_csv.open(encoding="utf-8") as f:
        return {r["id"]: (int(r["tap_x"]), int(r["tap_y"])) for r in csv.DictReader(f)}


def to_labels(store: Mapping[str, Any], taps: Mapping[str, tuple[int, int]]) -> dict[str, Label]:
    out: dict[str, Label] = {}
    for sid, v in store["labels"].items():
        c = str(v.get("c", "")).strip()
        if c and sid in taps:
            out[sid] = (c, taps[sid][0], taps[sid][1], int(v.get("w") or DEFAULT_SIZE), int(v.get("h") or DEFAULT_SIZE))
    return out


def apply(data: ds.Dataset, labels: Mapping[str, Label], builds: Mapping[str, str],
          ratios: Mapping[str, float] | None = None) -> ds.Dataset:
    """Dataset moi (v1). Thuan. Mau test chi la mau co nhan nguoi; mau bootstrap trong phien test bi bo."""
    classes = list(data.classes)
    for c, *_ in labels.values():
        if c != NONE and c not in classes:
            classes.append(c)
    splits = ds.assign_splits({s.session for s in data.samples}, ratios or {"train": 0.5, "val": 0.2, "test": 0.3})
    out = []
    for s in data.samples:
        sp = splits[s.session]
        lab = labels.get(s.id)
        if sp == "test" and lab is None:
            continue
        anns = s.annotations
        if lab is not None and lab[0] != NONE:
            _, x, y, w, h = lab
            anns = (*anns, ds.Annotation(lab[0], ds.Box(max(0, x - w // 2), max(0, y - h // 2), w, h)))
        out.append(replace(s, split=sp, source="human" if lab is not None else "bootstrap", annotations=anns,
                           game_build=builds.get(str(s.instance), "unknown")))
    return ds.Dataset("v1", tuple(classes), tuple(out))


def materialize(src: Path, dst: Path, labels: Mapping[str, Label], builds: Mapping[str, str]) -> ds.Dataset:
    """Doc <src>/manifest.json, ap nhan, chep anh, ghi <dst>/manifest.json (da validate). Tra ve dataset moi."""
    new = apply(ds.load(src / "manifest.json"), labels, builds)
    (dst / "images").mkdir(parents=True, exist_ok=True)
    for s in new.samples:
        shutil.copyfile(src / s.path, dst / s.path)
    ds.save(new, dst / "manifest.json")
    return new
