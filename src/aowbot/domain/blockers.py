"""S2 (vong man hinh): thong bao cua game -> ly do viec bi chan + han thu lai.

Vi sao: dong nhiem vu "Chinh" tra 'none' 363 lan/ngay vi game bao "Khu vuc toa nha nay chua duoc mo khoa, vui long
mo khoa lo dat truoc" / "Radar mo khoa cap 1" ma bot khong doc -> lan ghe nao cung thu lai. Luat thuan: nhan CHUOI
OCR (Tesseract 'eng' mat dau, sai chu: "dugc mé khéa", "16 dat") -> ly do; nho theo khoa cua viec, bo qua toi han.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


class BlockReason(StrEnum):
    PLOT_LOCKED = "plot_locked"      # lo dat chua mo: can mo dat (viec khac) - lau moi doi
    PREREQ = "prereq"                # "<cong trinh> mo khoa cap N": thieu cong trinh/cap dieu kien
    NO_EFFECT = "no_effect"          # 'Den' khong dan toi man nang cap, khong co thong bao doc duoc


# thu tu quan trong: thong bao lo dat co ca chu "mo khoa" -> xet truoc PREREQ
_RULES: tuple[tuple[re.Pattern[str], BlockReason], ...] = (
    (re.compile(r"toa nha nay|chua d\w{0,3}c m\w kh|kh\w{1,2}a l\w dat|\blo dat"), BlockReason.PLOT_LOCKED),
    (re.compile(r"\bm[oe0] kh\w{1,3} cap \d"), BlockReason.PREREQ),
)

DEFAULT_TTL_S: Mapping[BlockReason, float] = MappingProxyType({
    BlockReason.PLOT_LOCKED: 12 * 3600.0,
    BlockReason.PREREQ: 6 * 3600.0,
    BlockReason.NO_EFFECT: 2 * 3600.0,
})


def normalize(text: str) -> str:
    """Bo dau, chu thuong, gop khoang trang (OCR 'eng' co the tra ca ky tu co dau sai: 'mé', 'khéa')."""
    s = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s).strip()


def classify(text: str) -> BlockReason | None:
    s = normalize(text)
    for pattern, reason in _RULES:
        if pattern.search(s):
            return reason
    return None


@dataclass(frozen=True, slots=True)
class Block:
    key: str
    reason: BlockReason
    until: float

    def to_dict(self) -> dict[str, object]:
        return {"reason": self.reason.value, "until": self.until}


def block(key: str, reason: BlockReason, now: float,
          ttl_s: Mapping[BlockReason, float] = DEFAULT_TTL_S) -> Block:
    return Block(key, reason, now + ttl_s[reason])


def load(raw: Mapping[str, Mapping[str, object]] | None, now: float) -> dict[str, Block]:
    """Doc tu dang luu (JSON) va bo muc het han / hong."""
    out: dict[str, Block] = {}
    for key, v in (raw or {}).items():
        try:
            b = Block(key, BlockReason(str(v["reason"])), float(str(v["until"])))
        except (KeyError, ValueError):
            continue
        if b.until > now:
            out[key] = b
    return out


def dump(blocks: Mapping[str, Block]) -> dict[str, dict[str, object]]:
    return {k: b.to_dict() for k, b in blocks.items()}


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b, strict=False)) + abs(len(a) - len(b))


def find_active(blocks: Mapping[str, Block], key: str, now: float, max_dist: int = 0) -> Block | None:
    """Khoa = dau van tay anh dong nhiem vu (chuoi bit): so gan dung vi so tien do / hieu ung lam lech vai bit."""
    for k, b in blocks.items():
        if b.until > now and hamming(k, key) <= max_dist:
            return b
    return None
