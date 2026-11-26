"""P13e-1: so tho xay HIEU LUC. Ham thuan, khong goi thiet bi.

Loi cu: build.max_builders cung 1 cho farm -> dung 1 tho du game bao 0/2 (o tho thu 2 da co san). So tho hieu luc lay tu
so o game bao (x/y cua hang cho xay): o da CO thi dung het. Bot KHONG BAO GIO thue tho / mua o bang kim cuong; o chua
co thi game chi bao y = 1 va bot giu 1.
"""
from __future__ import annotations


def effective_max(cfg_max: int | None, observed_total: int | None, use_game: bool = True, cap: int = 2) -> int:
    """cfg_max: build.max_builders (tran cau hinh); observed_total: y trong 'x/y' game bao (None = chua doc duoc);
    use_game: build.use_game_slots - lay so o tu game; cap: build.max_builders_cap (tran cung, >= cfg_max).
    - chua doc duoc y -> cfg_max;  - use_game -> min(cap, y);  - tat use_game -> min(cfg_max, y) (cach cu)."""
    base = max(1, int(cfg_max or 1))
    if not observed_total or observed_total < 1:
        return base
    if use_game:
        return max(1, min(max(cap, base), int(observed_total)))
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
