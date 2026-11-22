"""Sua ten nghien cuu bi OCR doc sai dau tieng Viet (Tesseract chi co goi 'eng').

Vd "Chi?n thuat t?n c?ng IV" / "Chien thuat ten ceng IV" -> "Chiến thuật tấn công IV".
Cach lam: bo dau + ky tu la -> so tung tu voi bang tu vung co dau (gan dung) -> ghep lai.
Tu khong co trong bang thi giu nguyen dang da bo dau. Ham thuan, khong doc may/anh.
Muon them tu: bo sung vao VOCAB (viet co dau).
"""
import difflib
import re
import unicodedata

VOCAB = [
    "Chiến", "thuật", "tấn", "công", "phòng", "thủ", "thu", "thập", "tài", "nguyên", "sản", "xuất",
    "tăng", "tốc", "hành", "quân", "binh", "lính", "huấn", "luyện", "kỵ", "bộ", "cung", "thủ",
    "xe", "tăng", "pháo", "binh", "không", "quân", "hải", "quân", "sức", "mạnh", "máu", "giáp", "kháng",
    "sát", "thương", "tải", "trọng", "chịu", "tải", "dung", "lượng", "kho", "xây", "dựng", "nghiên", "cứu",
    "liên", "minh", "trị", "liệu", "bệnh", "viện", "hồi", "phục", "tướng", "kỹ", "năng", "chỉ", "huy",
    "trinh", "sát", "do", "thám", "kim", "loại", "thực", "phẩm", "dầu", "hợp", "gia", "cường", "nâng",
    "cao", "cấp", "tinh", "nhuệ", "đột", "kích", "chiến", "đấu", "trận", "địa", "hình", "chiêu", "mộ",
    "thuộc", "tính", "cơ", "bản", "nâng", "hiệu", "quả", "tối", "đa", "tiêu", "hao", "giảm", "thời", "gian",
]
_ROMAN = re.compile(r"^[IVXlI1|]{1,4}$")


def fold(s):
    """Bo dau, chuyen 'đ'->'d', chu thuong, bo ky tu khong phai chu/so."""
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if c.isascii() and c.isalnum()).lower()


_BY_FOLD = {}
for _w in VOCAB:
    _BY_FOLD.setdefault(fold(_w), _w)


def _word(tok):
    f = fold(tok)
    if not f:
        return ""
    if f in _BY_FOLD:
        return _BY_FOLD[f]
    best, score = None, 0.6                 # hoa diem -> tu dung truoc trong VOCAB thang
    for k in _BY_FOLD:
        r = difflib.SequenceMatcher(None, f, k).ratio()
        if r > score:
            best, score = k, r
    return _BY_FOLD[best] if best else f


def fix_name(raw):
    """Ten OCR (hong dau) -> ten co dau dep. Giu so La Ma (I, II, IV...) o cuoi. '' neu rong."""
    toks = re.split(r"[\s_\-]+", (raw or "").strip())
    out = []
    for i, raw_tok in enumerate(toks):
        t = raw_tok.strip()
        if not t:
            continue
        if i > 0 and _ROMAN.match(t):
            out.append(t.upper().replace("L", "I").replace("1", "I").replace("|", "I"))
            continue
        # token co ky tu la ('?', '�', ...) giua chu: bo ky tu la roi so khop
        w = _word(re.sub(r"[^\w]", "", t, flags=re.ASCII) if any(not c.isascii() for c in t) else t)
        if w:
            out.append(w)
    if out:
        out[0] = out[0][:1].upper() + out[0][1:]
    return " ".join(out)
