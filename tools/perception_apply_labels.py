"""Nap nhan nguoi vao dataset: v0 + labels.json (tu trang web "Nhan dien") -> v1 (source=human), co test.

  python tools/perception_apply_labels.py [--dir data/perception/v0] [--out data/perception/v1]
                                          [--builds builds.json]
Nhan lay tu <dir>/labels.json (web ghi). builds.json (tuy chon) ghi de {"0": "vn-2.5.16", ...}.
Logic: aowbot.perception.eval.labeling.
"""
import argparse
import json
import os
import sys
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

from aowbot.perception.eval import dataset as ds  # noqa: E402
from aowbot.perception.eval import labeling as lb  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(BASE, "data", "perception", "v0"))
    ap.add_argument("--out", default=os.path.join(BASE, "data", "perception", "v1"))
    ap.add_argument("--builds")
    a = ap.parse_args()
    src, dst = Path(a.dir), Path(a.out)
    store = lb.load_store(src / "labels.json")
    builds = {**store["builds"], **(json.loads(Path(a.builds).read_text(encoding="utf-8")) if a.builds else {})}
    labels = lb.to_labels(store, lb.read_taps(src / "review.csv"))
    new = lb.materialize(src, dst, labels, builds)
    n = {sp: len(new.in_split(sp)) for sp in ds.SPLITS}
    print(f"v1: {len(new.samples)} mau {n}; nhan nguoi: {len(labels)}; lop: {len(new.classes)}")
    print(f"-> {dst / 'manifest.json'}: {ds.verify_files(new, dst) or 'sha256 ok'}")


if __name__ == "__main__":
    main()
