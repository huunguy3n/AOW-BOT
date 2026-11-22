"""Chi so theo doi: MOTA, ID switch, IDF1 (CLEAR-MOT / Ristani 2016). Thuan.

Dau vao: moi khung = danh sach (id, Box). Khop GT-hyp theo IoU >= iou_min, khoi dau tu khop khung truoc
(giu danh tinh de dem ID switch dung nghia CLEAR-MOT), roi tim cap toi uu bang Hungarian.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from ..tracking.assign import assign
from .dataset import Box
from .metrics import iou

Frame = Sequence[tuple[int, Box]]


@dataclass(frozen=True)
class TrackingScores:
    gt: int
    tp: int
    fp: int
    fn: int
    id_switches: int
    mota: float
    idf1: float
    rmse: float          # sai so vi tri tam (px) tren cac khung khop


def _frame_matches(gt: Frame, hyp: Frame, prev: dict[int, int], iou_min: float) -> list[tuple[int, int]]:
    """[(chi so gt, chi so hyp)]: uu tien giu cap cu cua khung truoc (neu van chong lan), phan con lai gan toi uu."""
    pairs: list[tuple[int, int]] = []
    used_h: set[int] = set()
    for gi, (gid, gb) in enumerate(gt):
        hid = prev.get(gid)
        for hi, (h, hb) in enumerate(hyp):
            if h == hid and hi not in used_h and iou(gb, hb) >= iou_min:
                pairs.append((gi, hi))
                used_h.add(hi)
    free_g = [gi for gi in range(len(gt)) if gi not in {p[0] for p in pairs}]
    free_h = [hi for hi in range(len(hyp)) if hi not in used_h]
    if free_g and free_h:
        cost = [[1.0 - iou(gt[g][1], hyp[h][1]) for h in free_h] for g in free_g]
        pairs += [(free_g[i], free_h[j]) for i, j in assign(cost, 1.0 - iou_min)]
    return pairs


def _idf1(overlap: dict[tuple[int, int], int], n_gt: int, n_hyp: int) -> float:
    gids = sorted({g for g, _ in overlap})
    hids = sorted({h for _, h in overlap})
    idtp = 0
    if gids and hids:
        cost = [[-float(overlap.get((g, h), 0)) for h in hids] for g in gids]
        idtp = int(sum(-cost[i][j] for i, j in assign(cost, 0.0)))
    denom = n_gt + n_hyp
    return 2 * idtp / denom if denom else 1.0


def score(gt: Sequence[Frame], hyp: Sequence[Frame], iou_min: float = 0.5) -> TrackingScores:
    if len(gt) != len(hyp):
        raise ValueError("gt va hyp phai cung so khung")
    prev: dict[int, int] = {}
    last_h: dict[int, int] = {}
    tp = fp = fn = idsw = n_gt = n_hyp = 0
    err2 = 0.0
    overlap: dict[tuple[int, int], int] = defaultdict(int)
    for g, h in zip(gt, hyp, strict=True):
        pairs = _frame_matches(g, h, prev, iou_min)
        n_gt += len(g)
        n_hyp += len(h)
        tp += len(pairs)
        fn += len(g) - len(pairs)
        fp += len(h) - len(pairs)
        cur: dict[int, int] = {}
        for gi, hi in pairs:
            gid, gb = g[gi]
            hid, hb = h[hi]
            cur[gid] = hid
            overlap[(gid, hid)] += 1
            if gid in last_h and last_h[gid] != hid:
                idsw += 1
            last_h[gid] = hid
            err2 += ((gb.x + gb.w / 2 - hb.x - hb.w / 2) ** 2 + (gb.y + gb.h / 2 - hb.y - hb.h / 2) ** 2)
        prev = cur
    mota = 1.0 - (fn + fp + idsw) / n_gt if n_gt else 1.0
    return TrackingScores(n_gt, tp, fp, fn, idsw, mota, _idf1(overlap, n_gt, n_hyp), (err2 / tp) ** 0.5 if tp else 0.0)
