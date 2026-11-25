"""P13-2: nho viec da LAM TRONG LAN GHE NAY (runner tao moi dau moi lan ghe) de buoc sau khong lam lai cung viec.
Vi sao: live5 #3 - reddots mo Thu / VIP / Su menh / Qua lien minh xong, buoc rewards + mission ngay sau do mo LAI tung cai
(~1 phut / lan ghe, nhieu lan 'Ruong ... khong co nut nhan'). Ham thuan tren thuoc tinh ctx.visit_kinds (set)."""


def mark(ctx, kind):
    s = getattr(ctx, "visit_kinds", None)
    if s is None:
        s = set()
        try:
            ctx.visit_kinds = s
        except Exception:   # noqa: BLE001 - ctx gia trong test
            return
    s.add(kind)


def seen(ctx, kind):
    return kind in (getattr(ctx, "visit_kinds", None) or ())
