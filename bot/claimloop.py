"""P9-3 (chu du an 2026-11-24, live-run-2): nhan HET cham do / qua tren MOI man nhan qua - lap toi khi khong con
cham do. Live-run-2: Chieu mo / Hoat dong chi bam 1 cham do roi bo di, qua lien minh nhan 1 lan, ~14 cham do con sot.

Ham thuan (khong cham adb) - module truyen vao ham `once` (lam 1 luot, tra so lan nhan) va `still` (con cham do?).
Dung khi: het cham do; 1 luot khong nhan them duoc gi (cham do khong xu ly an toan duoc -> tranh vong vo han);
hoac du so vong.
"""
import logging

log = logging.getLogger("aow")


def until_clear(once, still, max_rounds=6):
    """-> (tong so lan nhan, so vong, con cham do sau cung?)."""
    total, rounds = 0, 0
    while rounds < max_rounds and still():
        n = once() or 0
        rounds += 1
        total += n
        if n <= 0:
            break
    return total, rounds, bool(still())


def tabs_until_clear(tabs, enter, claim_once, max_per_tab=10, max_rounds=3):
    """Nhieu tab (vd Chieu mo cao cap / Chieu mo thuong): vao tab -> bam HET cham do o tab nay (claim_once lap toi khi
    tra 0) roi moi sang tab ke; ca vong khong nhan them gi -> dung. -> (tong, nhat ky [(tab, so lan)])."""
    total, logbook = 0, []
    for _ in range(max_rounds):
        got_round = 0
        for tab in tabs:
            enter(tab)
            got_tab = 0
            for _ in range(max_per_tab):
                n = claim_once(tab) or 0
                if n <= 0:
                    break
                got_tab += n
            logbook.append((tab, got_tab))
            got_round += got_tab
        total += got_round
        if not got_round:
            break
    return total, logbook


def current_then_tabs(tabs, enter, claim_once, has_dot, max_per_tab=10, max_rounds=3):
    """P10-2 (live-run-3 15:31:17: man Chieu mo mo san tab THUONG co nut "Mien phi" + cham do, bot lai chuyen sang tab
    cao cap truoc roi bo ve -> nhan 0). Bam HET o tab HIEN TAI truoc (khong chuyen tab), roi moi vao tab con cham do
    (`has_dot(tab)`: True / False / None = khong biet -> vao thu); lap toi khi ca vong khong nhan them hoac khong tab nao
    con cham do. -> (tong, nhat ky [(tab, so lan)]); tab hien tai ghi la "current"."""
    def drain(tab):
        got = 0
        for _ in range(max_per_tab):
            n = claim_once(tab) or 0
            if n <= 0:
                break
            got += n
        return got
    total = drain("current")
    logbook = [("current", total)]
    for _ in range(max_rounds):
        got_round, entered = 0, 0
        for tab in tabs:
            if has_dot(tab) is False:
                continue
            enter(tab)
            entered += 1
            got = drain(tab)
            logbook.append((tab, got))
            got_round += got
        total += got_round
        if not entered or not got_round:
            break
    return total, logbook
