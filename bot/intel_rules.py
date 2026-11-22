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


LOG_RX = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \w+ \[[^\]]*\] Tinh bao: ([a-z_]+)\s*$")


def parse_log(lines, t0=0, t1=1e12):
    """Dong log 'Tinh bao: <ket qua>' trong [t0, t1) -> {ket qua: so lan}. Bo dong 'Tinh bao: N nhiem vu'."""
    out = {}
    for ln in lines:
        m = LOG_RX.match(ln.rstrip("\n"))
        if not m:
            continue
        at = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
        if t0 <= at < t1:
            out[m.group(2)] = out.get(m.group(2), 0) + 1
    return out


def unknown_rate(counts):
    """{ket qua: n} -> (so unknown, tong, %) ; tong = moi lan xu ly 1 ghim."""
    tot = sum(counts.values())
    unk = sum(n for k, n in counts.items() if is_unknown(k))
    return unk, tot, (round(100.0 * unk / tot, 1) if tot else None)
