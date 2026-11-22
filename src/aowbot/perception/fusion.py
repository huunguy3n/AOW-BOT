"""Hop nhat: CandidateMerger (gop ung vien cua nhieu detector), FeatureFusionEngine (hieu chuan + hop nhat log-odds),
ConfidenceEvaluator (xac suat -> Status). Thuan, khong cv2.

- Detector khong ap dung / khong chay KHONG co mat trong hop nhat = khong dong gop bang chung am
  (dac biet: thieu thong tin thoi gian khong phai bang chung vang mat cua vat the tinh).
- Moi Detection ra khoi day mang du Evidence cua cac detector dong gop + Evidence('fusion') ghi trong so da dung.
- Nguong cua ConfidenceEvaluator la THAM SO DO BANG BENCHMARK (tools/perception_calibrate.py), khong co mac dinh tuy y.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from .calibration import FusionModel
from .contract import Detection, Evidence, Outcome, Status
from .eval.dataset import Box
from .eval.metrics import iou

FUSION = "fusion"


@dataclass(frozen=True)
class Candidate:
    cls: str
    members: tuple[Detection, ...]


def _near(a: Box, b: Box, min_iou: float) -> bool:
    if iou(a, b) >= min_iou:
        return True
    ax, ay = a.x + a.w / 2, a.y + a.h / 2
    bx, by = b.x + b.w / 2, b.y + b.h / 2
    return abs(ax - bx) <= max(a.w, b.w) / 2 and abs(ay - by) <= max(a.h, b.h) / 2


class CandidateMerger:
    def __init__(self, min_iou: float = 0.3) -> None:
        self.min_iou = min_iou

    def merge(self, dets: Sequence[Detection]) -> list[Candidate]:
        """Gop theo lop + chong lan / tam gan nhau (don lien ket, du cho vai detector moi lop)."""
        groups: list[list[Detection]] = []
        for d in dets:
            for g in groups:
                if g[0].cls == d.cls and any(_near(m.box, d.box, self.min_iou) for m in g):
                    g.append(d)
                    break
            else:
                groups.append([d])
        return [Candidate(g[0].cls, tuple(g)) for g in groups]


class FeatureFusionEngine:
    def __init__(self, model: FusionModel) -> None:
        self.model = model

    def _probs(self, c: Candidate) -> tuple[dict[str, float], Detection]:
        """p da hieu chuan theo detector (lay detection tot nhat moi detector) + detection co p cao nhat (cho bbox)."""
        best: dict[str, tuple[float, Detection]] = {}
        for m in c.members:
            for e in m.evidence:
                cal = self.model.calibrators.get(e.detector)
                if cal is None or e.raw_score is None:
                    continue
                p = cal.prob(e.raw_score)
                if e.detector not in best or p > best[e.detector][0]:
                    best[e.detector] = (p, m)
        lead = max(best.values(), key=lambda t: t[0])[1] if best else c.members[0]
        return {d: v[0] for d, v in best.items()}, lead

    def fuse(self, c: Candidate) -> Detection:
        probs, lead = self._probs(c)
        evidence = tuple(e for m in c.members for e in m.evidence)
        feats: dict[str, float] = {}
        for m in c.members:
            feats.update(m.features)
        if not probs:       # khong detector nao co bo hieu chuan -> giu diem tho, khong bia confidence
            return replace(lead, evidence=evidence, features=feats, status=Status.UNCERTAIN, confidence=None)
        p = self.model.fused(probs)
        params: dict[str, float | str] = {f"p_{d}": v for d, v in probs.items()}
        params["model_source"] = self.model.source
        fe = Evidence(FUSION, p, "log-odds co trong so; detector vang mat khong dong gop", params)
        return replace(lead, evidence=(*evidence, fe), features=feats, status=Status.UNCERTAIN, confidence=p)


@dataclass(frozen=True)
class ConfidenceEvaluator:
    confirm_p: float        # >= : CONFIRMED
    reject_p: float         # <= : ung vien bi loai (NOT_DETECTED neu da tim du)
    primary: str | None = "template_ms"   # detector chinh: khong the bi detector phu 'keo' len CONFIRMED mot minh
    primary_floor: float = 0.5            # p cua detector chinh phai >= day (ranh gioi 0,5 cua bo hieu chuan)

    def __post_init__(self) -> None:
        if not 0.0 <= self.reject_p < self.confirm_p <= 1.0:
            raise ValueError("can 0 <= reject_p < confirm_p <= 1")

    def judge(self, cls: str, fused: Sequence[Detection], searched: bool) -> Outcome:
        """fused: cac ung vien da hop nhat cua lop; searched: da co it nhat 1 detector ap dung chay xong."""
        if not searched:
            return Outcome(cls, Status.UNKNOWN, None, "khong detector nao ap dung / thieu mau")
        scored = [d for d in fused if d.confidence is not None]
        if not scored:
            if fused:
                return Outcome(cls, Status.UNCERTAIN, fused[0], "co ung vien nhung chua hieu chuan")
            return Outcome(cls, Status.NOT_DETECTED, None, "tim du, khong ung vien")
        top = max(scored, key=lambda d: d.confidence or 0.0)
        p = top.confidence or 0.0
        if p >= self.confirm_p and self._primary_supports(top):
            return Outcome(cls, Status.CONFIRMED, replace(top, status=Status.CONFIRMED), "", p)
        if p <= self.reject_p:
            return Outcome(cls, Status.NOT_DETECTED, None, f"ung vien tot nhat p={p:.3f} <= reject", p)
        why = f"p={p:.3f} giua 2 nguong" if p < self.confirm_p else f"p={p:.3f}, detector chinh chua ung ho"
        return Outcome(cls, Status.UNCERTAIN, replace(top, status=Status.UNCERTAIN), why, p)

    def _primary_supports(self, d: Detection) -> bool:
        """Hop nhat co the bi detector phu (ORB) day len: do 2026-11-22, 'Xay dung lai' vs 'Bat dau lai' khop ORB
        9 inlier (chu 'lai' chung) du template chi 0,55 -> p 0,93. Detector phu chi duoc GIU ung vien o UNCERTAIN."""
        if self.primary is None:
            return True
        fe = next((e for e in d.evidence if e.detector == FUSION), None)
        v = fe.params.get(f"p_{self.primary}") if fe else None
        return isinstance(v, float) and v >= self.primary_floor
