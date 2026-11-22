"""P2 (PM 2026-11-23): anh mau CHUA CO (chu du an se chup sau) -> bo qua nhanh + log ro "thieu anh mau <ten>".
Khong crash, khong bam mo. Log moi ten toi da 1 lan / LOG_EVERY_S giay (khong lam ngap log moi lan ghe)."""
import logging
import time

log = logging.getLogger("aow")
LOG_EVERY_S = 3600
_last = {}


def has(v, name, why=""):
    """v.has(name); thieu -> log INFO 'thieu anh mau <ten> (<why>)' (gioi han tan suat) va tra False."""
    try:
        ok = bool(v.has(name))
    except Exception:
        ok = False
    if ok:
        return True
    now = time.time()
    if now - _last.get(name, 0) >= LOG_EVERY_S:
        _last[name] = now
        log.info("thieu anh mau %s%s", name, f" ({why})" if why else "")
    return False
