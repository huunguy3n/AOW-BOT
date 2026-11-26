"""P12-2 (live-run-4): danh sach den TOA DO cham vo hieu trong 1 lan ghe.

Live4: VIP @414,175 'nhan 0' lap lai o reddots + rewards (#0/#3/#4/#5/#6), o phuc loi @139,530 bam 4-5 lan (moi lan
20-40 s), cham do @134,35 mo ra khong lam gi -> buoc reddots cham tran 240 s. Luat: cung (pham vi, o luoi) cham
`limit` (2) lan KHONG co hieu ung (man khong doi / nhan 0 / khong mo duoc bang xu ly) -> danh sach den den het lan
ghe; cham co hieu ung -> xoa dem. Ham thuan, khong phu thuoc thiet bi (test offline).
"""
import logging

log = logging.getLogger("aow")
CELL = 30          # o luoi gom cac toa do lech nhau vai pixel (cham do / o qua dao dong +-3 px)


class TapGuard:
    def __init__(self, limit=2, cell=CELL):
        self.limit, self.cell = limit, cell
        self.fails: dict = {}
        self.black: dict = {}          # khoa -> ly do
        self.zones: list = []          # P13j: (pham vi, x, y) cam ca vung quanh diem (ban)

    def key(self, scope, x, y):
        return (scope, int(x) // self.cell, int(y) // self.cell)

    def blocked(self, scope, x, y):
        near = any(s == scope and abs(x - zx) <= self.cell and abs(y - zy) <= self.cell for s, zx, zy in self.zones)
        return near or self.key(scope, x, y) in self.black

    def record(self, scope, x, y, effect, why="khong hieu ung"):
        """Ghi ket qua 1 lan cham. -> True neu vua dua vao danh sach den."""
        k = self.key(scope, x, y)
        if effect:
            self.fails.pop(k, None)
            return False
        self.fails[k] = self.fails.get(k, 0) + 1
        if self.fails[k] >= self.limit and k not in self.black:
            self.black[k] = why
            log.info("Danh sach den (%s) @%d,%d: %d lan %s - bo qua toi het lan ghe", scope, x, y, self.fails[k], why)
            return True
        return False

    def ban(self, scope, x, y, why):
        """P13j: cam NGAY toa do (1 lan cham vo hieu) va vung +-cell quanh no - diem nhan lai lech vai pixel van bi chan."""
        self.zones.append((scope, int(x), int(y)))
        self.black[self.key(scope, x, y)] = why
        log.info("Danh sach den (%s) @%d,%d: %s - bo qua toi het lan ghe", scope, x, y, why)

    def keep(self, scope, pts):
        """Loc toa do chua bi danh sach den."""
        return [p for p in pts if not self.blocked(scope, p[0], p[1])]

    def summary(self):
        return [f"{s}@{gx * self.cell},{gy * self.cell}: {w}" for (s, gx, gy), w in self.black.items()]


def of(ctx):
    """TapGuard cua lan ghe hien tai (runner tao moi dau moi lan ghe; thieu thi tao)."""
    g = getattr(ctx, "tap_guard", None)
    if g is None:
        g = TapGuard()
        try:
            ctx.tap_guard = g
        except Exception:   # noqa: BLE001 - ctx gia trong test co the khong cho gan
            pass
    return g
