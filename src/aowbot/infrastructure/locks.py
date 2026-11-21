"""Khoa theo tai khoan giua cac TIEN TRINH (B9a): web va CLI cung chay runner khong duoc ghe cung 1 may.
Khoa he dieu hanh tren file -> tien trinh chet thi khoa tu nha (khong de lai khoa mo coi)."""
from __future__ import annotations

import os
import sys
from types import TracebackType

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


class AccountLock:
    def __init__(self, folder: str, account: int) -> None:
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, f"account-{account}.lock")
        self._fd: int | None = None

    def acquire(self) -> bool:
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT)
        try:
            if sys.platform == "win32":
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            if sys.platform == "win32":
                os.lseek(self._fd, 0, os.SEEK_SET)
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, t: type[BaseException] | None, e: BaseException | None, tb: TracebackType | None) -> None:
        self.release()
