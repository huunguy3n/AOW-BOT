"""Dataset nhan dien: manifest JSON co phien ban, nhan bbox, chia split theo PHIEN CHUP.

Schema: docs/perception/dataset-schema.md. Anh nam ngoai git (data/perception/); manifest ghi sha256 de tai lap.
Luat thuan, khong import cv2.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SPLITS = ("train", "val", "test")
SOURCES = ("human", "bootstrap")   # bootstrap = nhan goi y tu nhan dien cu: KHONG duoc nam trong test


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int

    def __post_init__(self) -> None:
        if self.w <= 0 or self.h <= 0:
            raise ValueError(f"bbox khong hop le: {self}")


@dataclass(frozen=True)
class Annotation:
    cls: str
    box: Box
    visible: bool = True        # False = bi che hoan toan nhung biet no o do
    occlusion: float = 0.0      # 0..1 phan bi che
    animated: bool = False


@dataclass(frozen=True)
class Sample:
    id: str
    path: str                   # tuong doi so voi thu muc dataset
    sha256: str
    session: str                # phien chup (don vi chia split)
    instance: int
    game_build: str             # vd "vn-2.5.16", "global-3.6.0"
    ui_state: str               # vd "city", "popup", "tutorial_dark"
    split: str
    source: str                 # human | bootstrap
    complete: bool              # True = moi lop quan tam deu da gan nhan -> lop vang mat la negative that
    annotations: tuple[Annotation, ...] = ()

    def has(self, cls: str) -> bool:
        return any(a.cls == cls for a in self.annotations)


@dataclass(frozen=True)
class Dataset:
    version: str
    classes: tuple[str, ...]
    samples: tuple[Sample, ...] = field(default_factory=tuple)

    def in_split(self, split: str) -> tuple[Sample, ...]:
        return tuple(s for s in self.samples if s.split == split)


def _sample_errors(s: Sample, known: set[str]) -> list[str]:
    errs: list[str] = []
    if s.split not in SPLITS:
        errs.append(f"{s.id}: split la '{s.split}'")
    if s.source not in SOURCES:
        errs.append(f"{s.id}: source la '{s.source}'")
    if s.split == "test" and s.source != "human":
        errs.append(f"{s.id}: test chi nhan nhan do nguoi xac nhan")
    for a in s.annotations:
        if a.cls not in known:
            errs.append(f"{s.id}: lop la '{a.cls}'")
        if not 0.0 <= a.occlusion <= 1.0:
            errs.append(f"{s.id}: occlusion ngoai 0..1")
    return errs


def validate(ds: Dataset) -> list[str]:
    """Tra ve danh sach loi (rong = hop le). Bat ro-rang: ro ri phien giua cac split, bootstrap trong test, lop la."""
    errs: list[str] = []
    ids: set[str] = set()
    sess_split: dict[str, set[str]] = defaultdict(set)
    known = set(ds.classes)
    for s in ds.samples:
        if s.id in ids:
            errs.append(f"trung id: {s.id}")
        ids.add(s.id)
        sess_split[s.session].add(s.split)
        errs += _sample_errors(s, known)
    errs += [f"phien '{k}' nam o nhieu split: {sorted(v)}" for k, v in sess_split.items() if len(v) > 1]
    return errs


def assign_splits(sessions: Iterable[str], ratios: Mapping[str, float] | None = None,
                  seed: str = "aow1") -> dict[str, str]:
    """Chia split theo phien, xac dinh (bam sha256(seed+phien)) -> tai lap duoc, khong phu thuoc thu tu."""
    r = dict(ratios or {"train": 0.6, "val": 0.2, "test": 0.2})
    if set(r) != set(SPLITS) or abs(sum(r.values()) - 1.0) > 1e-6:
        raise ValueError("ratios phai gom train/val/test va cong bang 1")
    out: dict[str, str] = {}
    for sess in sorted(set(sessions)):
        h = int(hashlib.sha256(f"{seed}:{sess}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        acc = 0.0
        for name in SPLITS:
            acc += r[name]
            if h <= acc + 1e-12:
                out[sess] = name
                break
        else:
            out[sess] = "test"
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- JSON
def _ann_from(d: Mapping[str, Any]) -> Annotation:
    b = d["box"]
    return Annotation(d["cls"], Box(int(b[0]), int(b[1]), int(b[2]), int(b[3])), bool(d.get("visible", True)),
                      float(d.get("occlusion", 0.0)), bool(d.get("animated", False)))


def from_dict(d: Mapping[str, Any]) -> Dataset:
    if d.get("schema") != SCHEMA_VERSION:
        raise ValueError(f"schema khong ho tro: {d.get('schema')}")
    samples = tuple(
        Sample(s["id"], s["path"], s["sha256"], s["session"], int(s["instance"]), s["game_build"],
               s["ui_state"], s["split"], s["source"], bool(s.get("complete", True)),
               tuple(_ann_from(a) for a in s.get("annotations", ())))
        for s in d["samples"])
    return Dataset(str(d["version"]), tuple(d["classes"]), samples)


def to_dict(ds: Dataset) -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERSION, "version": ds.version, "classes": list(ds.classes),
        "samples": [{
            "id": s.id, "path": s.path, "sha256": s.sha256, "session": s.session, "instance": s.instance,
            "game_build": s.game_build, "ui_state": s.ui_state, "split": s.split, "source": s.source,
            "complete": s.complete,
            "annotations": [{"cls": a.cls, "box": [a.box.x, a.box.y, a.box.w, a.box.h], "visible": a.visible,
                             "occlusion": a.occlusion, "animated": a.animated} for a in s.annotations],
        } for s in ds.samples],
    }


def load(path: Path) -> Dataset:
    return from_dict(json.loads(path.read_text(encoding="utf-8")))


def save(ds: Dataset, path: Path) -> None:
    errs = validate(ds)
    if errs:
        raise ValueError("dataset khong hop le: " + "; ".join(errs[:5]))
    path.write_text(json.dumps(to_dict(ds), ensure_ascii=False, indent=1), encoding="utf-8")


def verify_files(ds: Dataset, root: Path, samples: Sequence[Sample] | None = None) -> list[str]:
    """Kiem tra anh con do va dung sha256 (tai lap)."""
    errs = []
    for s in samples if samples is not None else ds.samples:
        p = root / s.path
        if not p.exists():
            errs.append(f"{s.id}: thieu file {s.path}")
        elif sha256_file(p) != s.sha256:
            errs.append(f"{s.id}: sai sha256")
    return errs
