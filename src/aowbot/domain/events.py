"""Su kien danh thuc agent (B1). Khoa chong trung: cung tai khoan + loai + doi tuong + khung thoi gian."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aowbot.domain.marches import MarchTimer

DEDUP_BUCKET_S = 120.0   # 2 lan quan sat doan cung 1 luc ve lech <= 2 phut (OCR dong ho) = cung su kien


class EventType(Enum):
    MARCH_RETURN_DUE = "march_return_due"    # 1 doi du kien ranh lai -> co the gui quan
    MARCH_ARRIVE_DUE = "march_arrive_due"    # doi toi mo -> doc gio thu thap (chi hien khi da toi)
    OBSERVE_DUE = "observe_due"              # du lieu qua cu -> can quan sat lai
    MANUAL = "manual"                        # chay tay / dry-run


class EventStatus(Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    DONE = "done"
    FAILED = "failed"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class Event:
    account: int
    type: EventType
    subject: str
    due_at: float
    source: str

    @property
    def key(self) -> str:
        return f"{self.account}:{self.type.value}:{self.subject}:{int(self.due_at // DEDUP_BUCKET_S)}"


def events_from_timers(account: int, timers: list[MarchTimer], source: str) -> list[Event]:
    """Timer hanh quan -> su kien. Doi tuong = 'march' chung (chi so dong OCR khong on dinh giua cac lan doc),
    nen 2 doi ve trong cung khung 2 phut gop 1 su kien: 1 lan thuc day xu ly moi doi ranh."""
    out = []
    for t in timers:
        kind = EventType.MARCH_RETURN_DUE if t.kind == "march" else EventType.MARCH_ARRIVE_DUE
        out.append(Event(account, kind, "march", t.due_at, source))
    return out
