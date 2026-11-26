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


def yield_builder(ctx, step):
    """Buoc xay khac co phai nhuong tho cho nha chinh? Chi tinh khi tho dang RANH (con ban thi buoc do khong xay duoc
    gi nen khong gay tranh). True -> buoc nen bo qua phan xay."""
    from bot import build
    maxb = build.max_builders(ctx)
    ok, why = dom.reserve(load(ctx), time.time(), maxb)
    if not ok:
        return False
    b = build.builders(ctx)
    if b is not None and b[0] >= min(build.max_builders(ctx, b[1]), b[1]):
        return False
    log.info("Bo buoc %s: %s", step, why)
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
