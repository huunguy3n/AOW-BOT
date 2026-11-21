"""A-MEAS-1: bo dem hieu nang (so lan + thoi gian) theo loai thao tac, de lap cac chi so baseline con UNKNOWN
(docs/strategy/performance-baseline.md §4): do tre ADB, so anh/OCR moi buoc, chi phi human.py, khoi dong lan ghe.

Runner tao 1 Perf moi lan ghe, gan vao Device (lenh adb tu moi luong) va bind() vao luong cua lan ghe (OCR,
nhan dien man - cac ham module khong co ctx). Sau moi buoc runner drain() -> bang `perf` trong memory.db.
Khong bind -> moi ham ghi la no-op (cong cu offline, test).
"""
import contextlib, threading, time

_tl = threading.local()


class Perf:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {}                  # (kind, src) -> [giay]

    def add(self, kind, dt, src=None):
        key = (kind, src or getattr(_tl, "src", "bot"))
        with self._lock:
            self._data.setdefault(key, []).append(dt)

    @contextlib.contextmanager
    def span(self, kind):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.add(kind, time.perf_counter() - t0)

    def drain(self):
        """-> [(kind, src, n, total, p50, p90, max)] va xoa so lieu da lay."""
        with self._lock:
            data, self._data = self._data, {}
        out = []
        for (kind, src), xs in sorted(data.items()):
            xs.sort()
            out.append((kind, src, len(xs), round(sum(xs), 3), round(xs[len(xs) // 2], 3),
                        round(xs[min(len(xs) - 1, int(len(xs) * 0.9))], 3), round(xs[-1], 3)))
        return out


def bind(perf):
    """Gan Perf cho luong hien tai (None = bo gan)."""
    _tl.perf = perf


def current():
    return getattr(_tl, "perf", None)


@contextlib.contextmanager
def as_src(src):
    """Thao tac trong khoi nay tinh cho nguon `src` (vd 'human' = anh chup do bot/human.py)."""
    old = getattr(_tl, "src", "bot")
    _tl.src = src
    try:
        yield
    finally:
        _tl.src = old


@contextlib.contextmanager
def measure(kind):
    """Do thoi gian cho Perf da bind o luong nay; chua bind -> khong lam gi."""
    p = current()
    if p is None:
        yield
        return
    with p.span(kind):
        yield
