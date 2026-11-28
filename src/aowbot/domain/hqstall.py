"""M2-4 (lo trinh ML, chu du an 2026-11-28): chan doan nha chinh dung yen.

Ham thuan. Vao: lich su cap nha chinh (fact hq_history [[ts, cap], ...]) + ket qua cac buoc xay dung (upgrade /
construct / quests / mainquest) trong khoang gan day. Ra: so gio tu lan len cap cuoi + ly do chinh (phan loai chu
note / ret cua runs) de chu du an thay may nao dang ket va vi sao. Khong ra quyet dinh, chi bao cao.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise

from aowbot.domain.stepvalue import did_work

BUILD_STEPS = ("upgrade", "construct", "quests", "mainquest")
STALL_H = 24.0                       # qua N gio khong len cap -> 'dung yen'

# (nhan, regex tren chu thuong khong dau cua note / ret) - thu tu = uu tien khi mot dong khop nhieu nhan
REASONS: tuple[tuple[str, str], ...] = (
    ("thieu_tai_nguyen", r"nores|thieu tai nguyen|khong du tai nguyen|res_short|resource"),
    ("tho_ban", r"tho ban|builder_busy|dang xay|busy"),
    ("thieu_dieu_kien", r"jump|nhay|dieu kien|require|locked|khoa"),
    ("khong_toi_man", r"no_screen|khong mo|not_found|khong thay|error|stuck|ket"),
    ("hq_max", r"hq_max|cap toi da|max_level"),
)


@dataclass(frozen=True, slots=True)
class Stall:
    inst: int
    level: int | None
    hours_since_up: float | None
    stalled: bool
    reasons: list[tuple[str, int]]     # [(nhan, so lan)] giam dan
    build_runs: int
    build_work: int
    plan: str | None = None             # trang thai ke hoach nha chinh (fact hq_plan.status): ly do chinh hien tai

    def as_dict(self) -> dict:
        return {"inst": self.inst, "level": self.level,
                "hours_since_up": None if self.hours_since_up is None else round(self.hours_since_up, 1),
                "stalled": self.stalled, "reasons": self.reasons, "build_runs": self.build_runs,
                "build_work": self.build_work, "plan": self.plan}


def classify(text: str | None) -> str | None:
    s = (text or "").lower()
    for label, rx in REASONS:
        if re.search(rx, s):
            return label
    return None


def diagnose(inst: int, history: Sequence[tuple[float, int]], runs: Iterable[tuple[str, object, str | None]],
             now: float, *, plan: str | None = None) -> Stall:
    """history: [(ts, cap)] tang dan theo ts. runs: (buoc, ret, note) cac buoc xay dung trong khoang xet.
    plan: hq_plan.status (wait_builder / wait_resources / unreached / chain ...) - ly do chinh khi co."""
    level = history[-1][1] if history else None
    last_up = None
    for (_, a), (t, b) in pairwise(history):
        if b > a:
            last_up = t
    if last_up is None and history:
        last_up = history[0][0]
    hours = None if last_up is None else max(0.0, (now - last_up) / 3600.0)
    cnt: Counter[str] = Counter()
    n = work = 0
    for step, ret, note in runs:
        if step not in BUILD_STEPS:
            continue
        n += 1
        if did_work(ret):
            work += 1
            continue
        lab = classify(f"{note or ''} {ret or ''}")
        if lab:
            cnt[lab] += 1
    return Stall(inst, level, hours, bool(hours is not None and hours >= STALL_H and (level or 0) < 30),
                 cnt.most_common(4), n, work, plan)
