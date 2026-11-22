"""G2 (docs/strategy/session-drain-proposal.md): xa viec theo phien. Ham thuan, khong doc dong ho.

Mot lan ghe chay ORDER dung 1 luot. Buoc A lam duoc viec (ret > 0) co the mo khoa buoc B da chay TRUOC A (tai nguyen
moi, cong trinh moi, qua vua nhan...) -> chay lai B truoc 'observe' thay vi doi lan ghe sau (hang gio sau).
Chi chay lai buoc co the thay doi thanh viec thuc (hang cho/tho/quan), toi da 1 lan moi buoc, toi da `max_extra` buoc.
"""
from __future__ import annotations

from types import MappingProxyType

# nguon -> cac buoc co the co viec moi sau khi nguon lam duoc viec (chi xet buoc dung TRUOC nguon trong ORDER)
_RESOURCE = ("upgrade", "construct", "train", "research", "heal", "quests", "mainquest")
UNLOCKS = MappingProxyType({
    "rewards": _RESOURCE, "collect_city": _RESOURCE, "daily": _RESOURCE, "alliance": _RESOURCE,
    "campaign": _RESOURCE, "play": _RESOURCE, "notify": _RESOURCE, "reddots": _RESOURCE,
    "intel": _RESOURCE, "rebels": _RESOURCE,
    "construct": ("upgrade",),       # xay moi xong -> dieu kien cua nha chinh co the da du
    "heal": ("train",),              # linh hoi phuc -> cho huan luyen
})


def worked(ret) -> bool:
    """Buoc co lam viec khong? Tu gia tri tra ve cua mod.run: so > 0, hoac gia tri khac rong/khong phai so."""
    if ret in (None, "", False, 0, 0.0, [], {}):
        return False
    if isinstance(ret, (int, float)):
        return ret > 0
    return True


# so lan chay lai toi da moi buoc / luot ghe (mac dinh 1). 'upgrade': nang cap tuc thi (mien phi) cho phep ke tiep ngay,
# chuoi dieu kien cua nha chinh tien nhieu nut trong 1 lan ghe.
REPEAT_LIMIT = MappingProxyType({"upgrade": 6})
SELF_REPEAT = frozenset({"upgrade"})


def followups(order: list[str], done: dict[str, object], enabled: dict[str, bool],
              already: dict[str, int], max_extra: int = 8) -> list[str]:
    """order: ten buoc theo thu tu chay; done: ten -> ret cua lan chay gan nhat luot nay;
    already: ten -> so lan da chay lai. -> cac buoc nen chay lai (theo thu tu ORDER)."""
    pos = {n: i for i, n in enumerate(order)}
    want: set[str] = set()
    for src, ret in done.items():
        if not worked(ret) or src not in pos:
            continue
        targets = list(UNLOCKS.get(src, ()))
        if src in SELF_REPEAT:
            targets.append(src)
        for t in targets:
            ok_pos = t == src or (t in pos and pos[t] < pos[src] and t in done)
            if ok_pos and enabled.get(t) and already.get(t, 0) < (REPEAT_LIMIT.get(t, 1) if t == src else 1):
                want.add(t)
    return sorted(want, key=pos.__getitem__)[:max(0, max_extra - sum(already.values()))]
