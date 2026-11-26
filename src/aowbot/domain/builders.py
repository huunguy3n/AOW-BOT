"""So tho xay HIEU LUC (P13f-1). Ham thuan, khong goi thiet bi.

Chu du an (t90u 26/11/2026): "So tho toi da la 2/2 nhung acc farm chi co 1/2. Chi 2/2 khi mua bang tien.
Vi du #1 la 2/2. Con lai la 1/2." Game luon bao tong 2 (y trong 'x/y') ke ca khi o thu 2 chua mua
-> y KHONG noi so tho dung duoc.
So tho dung duoc = build.max_builders THEO MAY (mac dinh 1; #1 = 2 trong data/settings.json). Farm 1/2 = DAY.
Bot KHONG BAO GIO thue tho / mua o thu 2.
"""
from __future__ import annotations


def effective_max(cfg_max: int | None, observed_total: int | None = None) -> int:
    """cfg_max: build.max_builders cua may; observed_total: y game bao - chi de KEP XUONG (game bao it hon cau hinh),
    khong bao gio nang len."""
    base = max(1, int(cfg_max or 1))
    if not observed_total or observed_total < 1:
        return base
    return min(base, int(observed_total))


def idle_count(busy: int, effective: int) -> int:
    return max(0, effective - busy)


# thu tu buoc lap tho rảnh cuoi luot: cong trinh moi, nha chinh (+ dieu kien), nhiem vu xay
FILL_STEPS = ("construct", "upgrade", "mainquest", "quests")


def fill_steps(idle: int, rounds: int, max_rounds: int, progressed: bool, enabled: dict[str, bool]) -> list[str]:
    """Cuoi luot: con tho ranh -> chay lai cac buoc xay. Dung khi het vong, hoac vong truoc khong bat dau duoc viec nao
    (rounds >= 1 va not progressed) - khong lap vo ich."""
    if idle <= 0 or rounds >= max_rounds or (rounds >= 1 and not progressed):
        return []
    return [n for n in FILL_STEPS if enabled.get(n)]
