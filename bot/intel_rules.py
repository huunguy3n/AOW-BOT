"""P5-1 (PM 2026-11-23): luat thuan tinh bao - phan loai bang nhiem vu, vung tim ghim muc tieu, thong ke log.

Phan tich du lieu 20-22/11 (logs/pm-audit-1.txt: 64 log 'Tinh bao: unknown', 11 anh intel_panel_unknown):
  * 11/11 anh intel_panel_unknown la bang "Chuc mung nhan duoc" (ghim hop qua). Mau common/msg_reward khop 0,79-0,93
    tren anh luu SAU do, nhung luc kiem tra bang con dang hien (hieu ung tia sang de len tieu de) -> 'unknown'.
    -> panel_kind() + cho toi da INTEL_PANEL_WAIT_S giay thay vi xet 1 khung.
  * Nhat ky cham (bang exp, 22/11): sau "Di" co 2 kieu that bai chinh khong co anh:
      (a) mau ghim muc tieu intel/marker_fight (nguong 0,55, ca man) khop NHAM goc trai duoi (cham 97,805) roi cac
          diem co dinh deu truot -> MARKER_ROI chi giua man + nguong 0,6 (anh ban do: diem nhieu cao nhat 0,51-0,58).
      (b) bam "Tan cong" nhung khong thay "Chien dau"/"Xuat chinh" (gather/btn_march) -> may #1 (nha chinh 30) dung
          man "Cai dat Quan doan" kieu moi (nut rebels/btn_march_out co dong ho) -> nhan them man nay.
  * Moi 'unknown' nay co ly do rieng (UNKNOWN_*) + 1 anh/ngay/may (logs/inv/<ly do>/) de bo sung tiep.
"""
import re
import time

INTEL_PANEL_WAIT_S = 3.0        # bang nhiem vu / bang qua hien tre sau khi cham ghim (hieu ung)
MARKER_ROI = (60, 200, 420, 420)  # x, y, w, h: ghim muc tieu sau "Di" nam giua man (do 263,363 / 267,388)
MARKER_TH = 0.6
REWARD_TH = 0.75

UNKNOWN_PANEL = "unknown_panel"        # cham ghim: khong ra bang co nut "Di", khong ra bang qua
UNKNOWN_TARGET = "unknown_target"      # sau "Di": khong cham duoc muc tieu (khong ra Tan cong / Tiep te / Tap ket)
UNKNOWN_AFTER = "unknown_attack"       # sau "Tan cong": khong ra man Chien dau / Xuat chinh
UNKNOWNS = (UNKNOWN_PANEL, UNKNOWN_TARGET, UNKNOWN_AFTER, "unknown")
DONE = ("win", "marched", "picked")
STOP = ("no_march", "lose")
SKIP = ("skipped", "lose_pred")         # lose_pred: man quan doan du doan khong thang -> bo ghim, khong tinh unknown


def panel_kind(img, v):
    """Anh sau khi cham ghim -> 'go' (bang nhiem vu co nut "Di") | 'reward' (bang "Chuc mung nhan duoc") | None."""
    if v.find(img, "intel/btn_go"):
        return "go"
    if v.find(img, "common/msg_reward", th=REWARD_TH):
        return "reward"
    return None


def is_unknown(r):
    return isinstance(r, str) and r.startswith("unknown")


# 'YYYY-mm-dd HH:MM:SS INFO [#1] Tinh bao: kq' hoac dinh dang cu 'HH:MM:SS INFO Tinh bao: kq' (ngay lay tu ten file)
LOG_RX = re.compile(r"^(?:(\d{4}-\d\d-\d\d) )?(\d\d:\d\d:\d\d) \w+ (?:\[[^\]]*\] )?Tinh bao: ([a-z_]+)\s*$")


def parse_log(lines, t0=0, t1=1e12, day=None):
    """Dong log 'Tinh bao: <ket qua>' trong [t0, t1) -> {ket qua: so lan}. Bo dong 'Tinh bao: N nhiem vu'.
    day 'YYYY-mm-dd': ngay cho dong dinh dang cu khong co ngay (khong co -> bo dong do)."""
    out = {}
    for ln in lines:
        m = LOG_RX.match(ln.rstrip("\n"))
        if not m or not (m.group(1) or day):
            continue
        at = time.mktime(time.strptime(f"{m.group(1) or day} {m.group(2)}", "%Y-%m-%d %H:%M:%S"))
        if t0 <= at < t1:
            out[m.group(3)] = out.get(m.group(3), 0) + 1
    return out


def unknown_rate(counts):
    """{ket qua: n} -> (so unknown, tong, %) ; tong = moi lan xu ly 1 ghim."""
    tot = sum(counts.values())
    unk = sum(n for k, n in counts.items() if is_unknown(k))
    return unk, tot, (round(100.0 * unk / tot, 1) if tot else None)


# ---------- P7-4 (chu du an 2026-11-24, live #1) ----------
NOT_DEPARTED = "not_departed"   # bam Xuat chinh / Tiep te nhung quan doan khong di (nut con nguyen, x/y khong tang)
PICKUP_BUSY = "pickup_busy"     # da co PICKUP_MAX hop dang nhat -> cho het gio van day: bo ghim nay (lan sau)
PICKUP_MAX = 2                  # hop qua tinh bao (moi mau) toi da 2 hop dang nhat cung luc
PICKUP_S = 90                   # thoi gian nhat 1 hop (uoc luong; cau hinh notify.intel_pickup_s)
SKIP = SKIP + (PICKUP_BUSY, NOT_DEPARTED)
# P13j: da cham theo huong dan xanh trong thanh, huong dan het ma khong co bang nao -> sang ghim ke (tick xanh nhan sau)
GUIDED = "guided"
SKIP = SKIP + (GUIDED,)
NO_MARCH = "no_march"           # P13j: het quan doan ranh -> DUNG buoc Tinh bao toi het luot ghe may


def departed(before, after, screen_gone):
    """Quan doan/don vi tinh bao co THAT SU xuat phat? before/after: (dang di, tong) doc 'Hanh quan x/y' (None = khong doc
    duoc); screen_gone: nut Xuat chinh / Tiep te da bien mat sau khi bam. -> True | False.
    Doc duoc ca 2 so: so dang di phai tang. Khong doc duoc: dua vao nut da bien mat."""
    if before and after and before[1] == after[1]:
        return after[0] > before[0]
    return bool(screen_gone)


class Pickups:
    """Hop qua dang nhat (ham thuan, thoi gian truyen vao): toi da `cap` hop cung luc; het `dur` giay coi nhu nhat xong.

    P9-9 (live2 11:06:57-11:07:05, 3 lan "nhan hop qua da xong" lien tiep): do la NHAN THUONG ghim da xong (tick xanh,
    khung s110655 "Chuc mung nhan duoc"), khong phai gui 3 don vi nhat cung luc -> khong vi pham. Nhung truoc P9 moi
    tick (ke ca tick cua tran thang / quan doan) deu goi done() -> giai phong 1 cho cua hop CON DANG NHAT -> co the gui
    hop thu 3. Nay nho VI TRI ghim moi hop; done(pos) chi giai phong khi tick nam o ghim hop do."""

    NEAR = 60                   # px: tick xanh ~ dau ghim (diem cham ghim y - 35)

    def __init__(self, cap=PICKUP_MAX, dur=PICKUP_S):
        self.cap, self.dur, self.until, self.pos = cap, dur, [], []

    def _prune(self, now):
        keep = [i for i, t in enumerate(self.until) if t > now]
        self.until = [self.until[i] for i in keep]
        self.pos = [self.pos[i] for i in keep]

    def can_pick(self, now):
        self._prune(now)
        return len(self.until) < self.cap

    def wait_s(self, now):
        """Giay phai cho toi khi co cho trong (0 = nhat duoc ngay)."""
        self._prune(now)
        return 0.0 if len(self.until) < self.cap else max(0.0, min(self.until) - now)

    def add(self, now, pos=None):
        self._prune(now)
        self.until.append(now + self.dur)
        self.pos.append(pos)

    def done(self, pos=None):
        """Ghim hop vua nhan thuong (tick xanh) -> 1 hop da xong, giai phong cho. pos = vi tri tick: chi giai phong hop
        nhat tai ghim gan do (tick cua tran / ghim khac -> khong giai phong). pos None -> hop som nhat (cu).
        -> True neu da giai phong."""
        if not self.until:
            return False
        if pos is None:
            i = self.until.index(min(self.until))
        else:
            near = [i for i, p in enumerate(self.pos)
                    if p is not None and abs(p[0] - pos[0]) <= self.NEAR and abs(p[1] - pos[1]) <= self.NEAR]
            if not near:
                return False
            i = min(near, key=lambda k: self.until[k])
        del self.until[i]
        del self.pos[i]
        return True


def should_rescan(done_since_scan, rescans, max_rescans):
    """Hoan thanh tinh bao co the sinh diem moi -> quet lai ban do khi lan quet truoc co lam duoc viec, toi da max_rescans."""
    return done_since_scan > 0 and rescans < max_rescans


def pick_use_button(uses, potion_row, buys=(), tol=22):
    """Bang "Thuoc The Luc": chon nut "Dung" cung hang voi binh 10 diem; KHONG BAO GIO tra nut "Mua".
    uses / buys: [(x, y, ...)] nut Dung / Mua; potion_row: (x, y, ...) icon/chu binh 10 diem hoac None.
    potion_row None -> nut Dung tren cung (hanh vi cu). Nut Dung trung vi tri nut Mua (khop nham) bi loai."""
    ok = [u for u in uses if all(abs(u[0] - b[0]) > tol or abs(u[1] - b[1]) > tol for b in buys)]
    if not ok:
        return None
    if potion_row is None:
        return min(ok, key=lambda u: u[1])
    best = min(ok, key=lambda u: abs(u[1] - potion_row[1]))
    return best if abs(best[1] - potion_row[1]) <= 45 else None
