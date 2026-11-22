"""Vision Inspector (chi doc, chi dung anh da luu): luoi lat cat + bao cao JSON truy vet cho 1 anh.

  python tools/vision_inspector.py ANH.png [--prev ANH_TRUOC.png] [--prefix common/] [--th 0.82] [--out logs/inspect]

--prefix: chi chay mau legacy cua nhom do (khop man hinh day du ~30 ms/mau). Khong co --prefix = khong ve
phat hien nao (chi lat cat). Ket qua legacy gan trang thai UNCERTAIN: diem tho chua hieu chuan, confidence=None.
"""
import argparse
import os
import sys
from pathlib import Path

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [BASE, os.path.join(BASE, "src")]

import cv2  # noqa: E402

from aowbot.perception.contract import Detection, Evidence, FrameId, Status  # noqa: E402
from aowbot.perception.core.frame import ImageFrame  # noqa: E402
from aowbot.perception.diagnostics.inspector import save_inspection  # noqa: E402
from aowbot.perception.eval.dataset import Box  # noqa: E402
from bot.vision import Vision  # noqa: E402


def legacy_detections(img, prefix, th):
    """Mau legacy cua nhom `prefix` khop >= th -> Detection (UNCERTAIN, confidence None, bang chung = diem tho)."""
    v = Vision(os.path.join(BASE, "templates"), th)
    out = []
    for name in v.list(prefix):
        t = v.load(name, probe=True)
        best = v.best(img, name)
        if t is None or best is None or best[2] < th:
            continue
        h, w = t.shape[:2]
        out.append(Detection(
            cls=name, box=Box(best[0] - w // 2, best[1] - h // 2, w, h), status=Status.UNCERTAIN,
            evidence=(Evidence("legacy_template", best[2], "TM_CCOEFF_NORMED BGR", {"th": th}),)))
    return out


def load(path, seq):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"khong doc duoc anh: {path}")
    return ImageFrame(img, FrameId(0, seq), os.path.getmtime(path))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--prev")
    ap.add_argument("--prefix")
    ap.add_argument("--th", type=float, default=0.82)
    ap.add_argument("--out", default=os.path.join(BASE, "logs", "inspect"))
    a = ap.parse_args()
    frame = load(a.image, 1)
    prev = load(a.prev, 0) if a.prev else None
    dets = legacy_detections(frame.bgr, a.prefix, a.th) if a.prefix else []
    png = save_inspection(frame, Path(a.out), prev, dets)
    print(f"{png}  ({len(dets)} phat hien legacy)")


if __name__ == "__main__":
    main()
