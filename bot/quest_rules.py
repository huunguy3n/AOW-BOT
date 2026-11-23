"""P4 (PM 2026-11-23): luat THUAN cho nhiem vu chinh/chuong + man hinh cua che do follow. Khong goi thiet bi.

Rut ra tu (logs/p4/, tools/follow_stats.py):
  - 129 anh follow_stuck 18-22/11: 52 ban do the gioi (thanh nhiem vu "Tham gia tap ket ... phan quan" dan ra ban do,
    follow cham giua man 3 lan -> chon o dat "Chuyen thanh / Chiem linh" -> ket), 38 bang nhiem vu kieu moi (nut X do
    goc tren-phai thay cho nut dong cu -> decide() khong nhan ra, nut "Nhan toan bo" ngay truoc mat), 24 ban do
    Tinh bao, 6 bang co nut "<", 4 popup X, 3 chieu mo, 1 tuong, 1 khac.
  - 78 anh follow_maxsteps: 56 lan ket o CHE DO XAY (keo the 8 lan khong ra o xanh -> "che do xay: cho" toi het buoc).
  - tab Chinh: 472 lan "Den" -> none (dong la huan luyen / giet phan quan / tuong / dau truong... khong phai xay).
  - thao tac tay logs/human (2 531 thao tac, tools/follow_stats.py --human): o bang nhiem vu chu du an bam "Nhan" /
    "Nhan toan bo" roi X; o ban do the gioi / Tinh bao bam nut ve thanh pho / mui ten "<" goc tren-trai; khong ai
    cham giua ban do.

classify(text) doc chu tieu de nhiem vu (OCR 'eng' mat dau, sai vai ky tu) -> loai + buoc phu trach.
"""
from __future__ import annotations

import difflib
import re

from aowbot.domain.blockers import normalize

# (loai, cac cum tu khoa da bo dau, buoc phu trach). THU TU QUAN TRONG: cum dac hieu truoc.
# buoc None = mainquest/quests tu lam (xay qua build.upgrade_here, tuong/sua chua/don phe tich qua follow).
RULES: tuple[tuple[str, tuple[str, ...], str | None], ...] = (
    ("alliance", ("lien minh",), "alliance"),                # truoc 'rally': "Tham gia lien minh" la viec lien minh
    ("rally", ("tap ket", "tham gia"), "rebels"),            # "Tham gia tap ket tan cong 1 lan phan quan Co giap"
    ("rebels", ("phan quan",), "rebels"),                    # "Kich sat 1 lan phan quan Lv.3"
    ("train", ("huan luyen",), "train"),                     # "Huan luyen 2000 Tank bac 6"
    ("intel", ("tinh bao",), "intel"),                       # "Hoan thanh 1 lan tinh bao"
    ("arena", ("dau truong",), "play"),                      # "Chien thang Dau truong 290 lan"
    ("gather", ("thu thap",), "gather"),
    ("research", ("nghien cuu",), "research"),
    ("recruit", ("chieu mo",), "notify"),
    ("campaign", ("chien dich",), "campaign"),               # "Hoan tat Chien dich 1" - mainquest danh qua campaign
    ("build", ("den cap", "xay dung", "sua chua", "xuong"), None),   # "Tang 4 Xuong Thuc Pham den cap 26"
    ("hero", ("tuong",), None),                              # "Tang 5 Tuong len cap 90" -> follow (man Tuong)
    ("build", ("nang cap", "tang"), None),
)
DELEGATED = {k for k, _, m in RULES if m and k != "campaign"}   # mainquest/quests KHONG tu lam: de buoc phu trach


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize(s))


def _word_ok(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) >= 2 and len(b) - len(a) == 1 and b.startswith(a):   # OCR mat ky tu cuoi: 'ke' ~ 'ket'
        return True
    if len(b) <= 2 or len(a) <= 2:
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.84   # 1 ky tu sai trong tu 5 chu (xuong/tuong) KHONG khop


def has_phrase(text: str, phrase: str) -> bool:
    """Cum tu khoa co trong chu OCR (gan dung tung tu: 'tap két' / 'phan quéh' / 'céng' van khop)."""
    ws, ks = _words(text), phrase.split()
    return any(all(_word_ok(ws[i + j], k) for j, k in enumerate(ks)) for i in range(len(ws) - len(ks) + 1))


def classify(text: str) -> tuple[str, str | None]:
    """-> (loai, buoc phu trach). Khong doc duoc / khong khop -> ('unknown', None)."""
    if not text or len(_words(text)) < 2:
        return "unknown", None
    for kind, phrases, module in RULES:
        if any(has_phrase(text, p) for p in phrases):
            return kind, module
    return "unknown", None


def delegated(kind: str) -> bool:
    return kind in DELEGATED


def text_key(text: str) -> str:
    """Khoa on dinh cua 1 nhiem vu (bo so tien do, ky tu rac OCR) -> so sanh 'nhiem vu da doi chua'."""
    return " ".join(w for w in _words(text) if not w.isdigit() and len(w) > 1)[:60]


def same_quest(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return difflib.SequenceMatcher(None, text_key(a), text_key(b)).ratio() >= 0.8


# ---------- man hinh cua che do follow ----------
# Ten anh mau (da co trong templates/) -> loai man. Dung trong tutorial.decide() o che do follow.
QUEST_BOARD_TABS = ("daily/tab_2_main", "daily/tab_3_daily")
BOARD_CLOSE = (("common/btn_x_small", (440, 0, 100, 80)), ("common/btn_x", (430, 0, 110, 120)))
WORLD = "common/btn_to_city"
INTEL = "intel/title"


def follow_screen(v, img) -> str | None:
    """Man ma follow biet chac phai lam gi (khong co huong dan cua game). -> 'quest_board' | 'intel' | 'world' | None.
    Goi SAU khi da xet chu V / ban tay / nut quen thuoc (huong dan cua game luon uu tien)."""
    if any(v.find(img, n, th=0.85) for n in QUEST_BOARD_TABS):
        return "quest_board"
    if v.find(img, INTEL, th=0.85):
        return "intel"
    if v.find(img, WORLD):
        return "world"
    return None


def board_close(v, img):
    """Nut X dong bang nhiem vu kieu moi (goc tren-phai) -> (x, y) hoac None."""
    for n, roi in BOARD_CLOSE:
        p = v.find(img, n, th=0.85, roi=roi)
        if p:
            return p[0], p[1]
    return None


# ---------- che do xay trong follow ----------
BUILD_MAX_DRAGS = 8      # = gioi han keo trong decide()
BUILD_MAX_WAITS = 4      # het keo + cho them N nhip khong xac nhan duoc -> huy (nut X do), khong cho toi het buoc


def build_give_up(state: dict) -> bool:
    """Che do xay: da keo toi da ma khong co o xanh, cho them BUILD_MAX_WAITS nhip -> bo (huy bang X, nho the)."""
    return state.get("drags", 0) >= BUILD_MAX_DRAGS and state.get("build_waits", 0) >= BUILD_MAX_WAITS


# ---------- nhiem vu "Kich sat N lan phien quan Lv.X" (hoc tu thao tac tay #3 21/11 00:20, #4 22/11 22:47) ----------
# Chu du an: cham thanh nhiem vu -> camera ra ban do, muc tieu giua man -> cham muc tieu (~270,450) -> bang
# "Phien quan Lv.1" (De xuat: luc chien) -> "Tan cong" (267,738) -> man quan doan (gather/btn_recommended +
# gather/btn_march) -> Xuat chinh. Phien quan = linh NPC (KHONG phai nguoi choi). "Phan quan Co giap" chi danh bang
# tap ket (buoc rebels) -> khong danh o day.
NPC_TITLE_ROI = (110, 176, 300, 40)
NPC_POWER_ROI = (290, 668, 100, 26)


def npc_level(title: str) -> int | None:
    """Tieu de bang muc tieu -> cap phien quan NPC, hoac None neu KHONG phai phien quan don (co giap / nguoi choi /
    khong doc duoc). Chi tra so khi chac chan."""
    if not has_phrase(title, "phien quan") or has_phrase(title, "co giap"):
        return None
    m = re.search(r"lv\W{0,2}(\d{1,2})\b", normalize(title))
    return int(m.group(1)) if m else None


def npc_ok(level: int | None, recommend: int | None, power: int | None, max_level: int, max_ratio: float):
    """Duoc danh phien quan nay khong? -> (bool, ly do). Luc chien de xuat > luc chien x max_ratio -> khong."""
    if level is None:
        return False, "khong phai phien quan / khong doc duoc cap"
    if level > max_level:
        return False, f"cap {level} > {max_level}"
    if recommend and power and recommend > power * max_ratio:
        return False, f"de xuat {recommend} > luc chien {power} x {max_ratio}"
    return True, f"phien quan Lv.{level}"


# ---------- thu lai cung 1 nhiem vu (giam chu ky khi khong co viec) ----------
def retry_wait_s(fails: int, base_h: float, cap_h: float) -> float:
    """Cung nhiem vu that bai `fails` lan lien tiep -> cho bao lau moi cham lai (0 = cham ngay)."""
    if fails < 2:
        return 0.0
    return min(base_h * 3600 * 2 ** (fails - 2), cap_h * 3600)


def should_retry(last: dict | None, text: str, now: float, base_h: float, cap_h: float) -> tuple[bool, str]:
    """last = {'text', 'fails', 'at'} cua lan truoc. Nhiem vu khac (chu doi) -> luon thu."""
    if not last or not same_quest(last.get("text"), text):
        return True, "nhiem vu moi"
    wait = retry_wait_s(int(last.get("fails", 0)), base_h, cap_h)
    left = float(last.get("at", 0)) + wait - now
    if left > 0:
        return False, f"cung nhiem vu, that bai {last.get('fails')} lan - thu lai sau {left / 60:.0f} phut"
    return True, "het thoi gian cho"


def quests_mode(enabled: bool, qcfg: dict | None, forced: bool = False) -> str | None:
    """P7-5 (live #1 2026-11-24: buoc quests KHONG chay lan nao vi cai dat may #1 `modules.quests: false`, runner bo qua
    im lang). -> 'full' (bat: nhan + "Den" xay) | 'claim' (tat nhung quests.claim_when_off: CHI nhan thuong o tab co cham
    do, khong bam "Den") | None (khong chay). Chay tay theo --modules / Chay ngay (forced) giu nguyen cai dat."""
    if enabled:
        return "full"
    if forced or not (qcfg or {}).get("claim_when_off", True):
        return None
    return "claim"
