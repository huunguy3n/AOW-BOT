"""So tho xay HIEU LUC (P13f-1). Ham thuan, khong goi thiet bi.

Chu du an (t90u 26/11/2026): "So tho toi da la 2/2 nhung acc farm chi co 1/2. Chi 2/2 khi mua bang tien.
Vi du #1 la 2/2. Con lai la 1/2." Game luon bao tong 2 (y trong 'x/y') ke ca khi o thu 2 chua mua
-> y KHONG noi so tho dung duoc.
So tho dung duoc = build.max_builders THEO MAY (mac dinh 1; #1 = 2 trong data/settings.json). Farm 1/2 = DAY.
Bot KHONG BAO GIO thue tho / mua o thu 2.
"""
from __future__ import annotations

from dataclasses import dataclass


def effective_max(cfg_max: int | None, observed_total: int | None = None) -> int:
    """cfg_max: build.max_builders cua may; observed_total: y game bao - chi de KEP XUONG (game bao it hon cau hinh),
    khong bao gio nang len."""
    base = max(1, int(cfg_max or 1))
    if not observed_total or observed_total < 1:
        return base
    return min(base, int(observed_total))


def idle_count(busy: int, effective: int) -> int:
    return max(0, effective - busy)


# buoc xay chen vao khi tho ranh: nha chinh (+ tien quyet) truoc, cong trinh moi, nhiem vu chinh / nhiem vu xay
FILL_STEPS = ("upgrade", "construct", "mainquest", "quests")


@dataclass
class FillState:
    """P13f-2: trong 1 luot ghe, sau moi buoc - co chen cac buoc xay vao truoc buoc ke khong. Chong lap vo ich: mot lan
    thu khong bat dau duoc cong trinh nao thi chi thu lai khi co them tho vua xong, hoac vua co them tai nguyen."""
    max_rounds: int = 8              # so lan chen toi da
    max_retries: int = 2             # so lan thu lai nho tai nguyen moi
    rounds: int = 0                  # so lan da chen
    retries: int = 0                 # so lan thu lai nho tai nguyen moi
    mark: int | None = None          # != None: dang co 1 lan thu xay; gia tri = so cong trinh da bat dau luc mo
    stall_busy: int | None = None    # != None: lan thu gan nhat khong xay duoc gi; so tho dang ban luc do

    def attempt(self, started: int) -> None:
        """Sap chay 1 buoc xay (theo thu tu thuong hoac chen them)."""
        if self.mark is None:
            self.mark = started

    def decide(self, busy: int, idle: int, started: int, new_resources: bool = False) -> bool:
        """busy/idle: tho dang ban / tho dung duoc con ranh; started: so cong trinh da bat dau trong luot;
        new_resources: buoc vua chay co the da them tai nguyen. -> True = chay cac buoc xay NGAY."""
        if self.mark is not None:
            self.stall_busy = None if started > self.mark else busy
            self.mark = None
        if idle <= 0:
            self.stall_busy = None
            return False
        if self.rounds >= self.max_rounds:
            return False
        if self.stall_busy is not None and busy >= self.stall_busy:
            if not new_resources or self.retries >= self.max_retries:
                return False
            self.retries += 1
        self.rounds += 1
        self.mark = started
        self.stall_busy = None
        return True
