"""G1: cau noi giua ke hoach nha chinh (aowbot.domain.hqplan, ham thuan) va facts trong memory.db."""
import logging
import time

from aowbot.domain import hqplan as dom

log = logging.getLogger("aow")
KEY = "hq_plan"


def load(ctx):
    m = getattr(ctx, "mem", None)
    d = m.fact(ctx.dev.idx, KEY) if m else None
    return dom.HqPlan.from_json(d) if d else None


def save(ctx, result, level=None, busy_s=None):
    """Ghi ket qua buoc 'upgrade' vao ke hoach; tra ve HqPlan moi (hoac None neu khong co bo nho)."""
    m = getattr(ctx, "mem", None)
    if not m:
        return None
    new = dom.record(load(ctx), result, time.time(), level=level, busy_s=busy_s)
    m.set_fact(ctx.dev.idx, KEY, new.to_json())
    log.info("Ke hoach nha chinh: %s (thuc day %s, none lien tiep %d)", new.status.value,
             time.strftime("%H:%M", time.localtime(new.wake_at)) if new.wake_at else "-", new.none_streak)
    return new


def should_attempt(ctx):
    return dom.should_attempt(load(ctx), time.time())


def yield_builder(ctx, step, only_hq=False):
    """Buoc xay `step` co nen bo phan xay khong? P13f-2: CHI khi moi tho dung duoc dang BAN (farm 1/2 = day, khong thue
    o 2). Tho ranh hoac khong doc duoc -> False (xay tiep). only_hq: chi bo khi tho dang lam nha chinh / tien quyet."""
    from bot import build
    idle, b = build.builder_state(ctx)
    if idle is None or idle > 0:
        return False
    hq, why = dom.reserve(load(ctx), time.time(), idle)
    if only_hq and not hq:
        return False
    log.info("Bo buoc %s: het tho xay (%d/%d, dung toi da %d)%s", step, b[0], b[1], build.max_builders(ctx, b[1]),
             f" - {why}" if hq else "")
    return True


def after_construct(ctx):
    """Buoc 'construct' vua xay xong cong trinh moi: neu nha chinh dang lui lich vi 'none' (nut Nhay dan toi cong trinh
    chua xay), bo lui lich de lan ghe sau thu lai ngay."""
    m = getattr(ctx, "mem", None)
    cur = load(ctx)
    if not m or cur is None:
        return False
    new = dom.after_construct(cur, time.time())
    if new is cur:
        return False
    m.set_fact(ctx.dev.idx, KEY, new.to_json())
    log.info("Ke hoach nha chinh: vua xay cong trinh moi -> bo lui lich, thu lai nha chinh")
    return True
