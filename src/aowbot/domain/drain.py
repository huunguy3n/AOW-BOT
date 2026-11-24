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


def worked(ret: object) -> bool:
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


# ---- uu tien o rong (chu du an 2026-11-22): tho 0/2 xay truoc, nghien cuu 0/1, huan luyen x/3
HEAD = ("warday", "tutorial", "shield")            # buoc dau luot: luon giu dau (P9-2: khien som)
SLOT_STEPS = (("build", ("upgrade", "construct", "quests")), ("research", ("research",)), ("train", ("train",)))


def idle_slots(queues: dict[str, tuple[int, int] | None], max_builders: int = 1) -> list[str]:
    """Hang cho nao co o RANH: {'build'|'research'|'train': (dang chay, tong) | None}. Thu tu uu tien: xay, nghien cuu,
    huan luyen. Khong doc duoc so (None) thi khong coi la ranh."""
    out = []
    for kind, _ in SLOT_STEPS:
        q = queues.get(kind)
        if not q:
            continue
        busy, total = q
        cap = min(max_builders, total) if kind == "build" else total
        if busy < cap:
            out.append(kind)
    return out


def prioritize(order: list[str], idle: list[str], enabled: dict[str, bool] | None = None) -> list[str]:
    """Dua buoc cua cac hang cho dang ranh len ngay sau buoc dau luot (warday, tutorial); con lai giu nguyen thu tu."""
    head = [n for n in order if n in HEAD]
    front = []
    for kind, steps in SLOT_STEPS:
        if kind in idle:
            front += [n for n in steps if n in order and (enabled is None or enabled.get(n)) and n not in front]
    rest = [n for n in order if n not in head and n not in front]
    return head + front + rest
