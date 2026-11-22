"""P3 (PM 2026-11-23): doc "Hanh quan x/y" goc trai tren ban do the gioi.

Truoc P3: Tesseract (nguong 150 roi Otsu). Do tren 547 anh ban do the gioi co khung "Hanh quan" trong logs/ +
tests/fixtures: doc duoc 540, sai 3 ("5/5" -> "3/5": bot tuong con doi ranh), hut 7. Gio doc theo 3 lop:
  1. ANH CHU SO templates/mdigits/ (1..5, slash; cat tu anh that #1/#3 - co chu nho hon qdigits cua cot icon thanh
     pho) - khop xam ~1 ms, dung chung queues.read_glyph_box.
  2. Tesseract (cach cu) + templates/digits/ (du phong cu) - trong ctx.read_marches.
  3. KHUNG "Hanh quan" (templates/gather/march_header) KHONG hien tren ban do the gioi = 0 doi dang di (game an khung
     khi khong co doi nao, xem ghi chu trail 2026-11-21) -> (0, tong da biet). Chi ket luan khi chac dang o ban do
     the gioi (thay nut kinh lup gather/btn_search) va biet tong; khong thi None nhu cu.
Ham thuan (nhan anh) de test offline.
"""
import os

from bot import queues

BOX = (150, 132, 70, 30)            # vung tim chu so 'x/y' (rong hon march_counter_roi: khung lech theo so dong)
GLYPH_TH = 0.70
HEADER = "gather/march_header"      # chu "Hanh quan" + mui ten (x 8-110, y 138-158)
HEADER_ROI = (0, 110, 160, 80)
WORLD = "gather/btn_search"         # nut kinh lup chi co tren ban do the gioi
GLYPH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "mdigits")
_GLYPHS = None


def parse(s):
    """'a/b' -> (a, b) voi 1 <= b <= 9, a <= b; khac -> None."""
    try:
        a, b = (int(x) for x in (s or "").split("/"))
    except ValueError:
        return None
    return (a, b) if 1 <= b <= 9 and 0 <= a <= b else None


def glyphs():
    global _GLYPHS
    if _GLYPHS is None:
        _GLYPHS = queues.load_glyph_dir(GLYPH_DIR)
    return _GLYPHS


def read_glyphs(img, box=BOX, tpls=None, th=GLYPH_TH):
    """Lop 1: (dang di, tong) | None."""
    return queues.read_glyph_box(img, box, glyphs() if tpls is None else tpls, th, parse)


def header_state(v, img):
    """True = thay khung 'Hanh quan'; False = chac chan KHONG co (dang o ban do the gioi); None = khong ket luan
    (thieu anh mau, khong phai ban do the gioi)."""
    if not (v.has(HEADER) and v.has(WORLD)):
        return None
    if v.find(img, HEADER, th=0.8, roi=HEADER_ROI):
        return True
    return False if v.find(img, WORLD) else None


def infer(read, header, known_total):
    """Ham thuan ket hop: so doc duoc | khung vang mat + tong da biet -> (0, tong) | None.
    Doc duoc ma khung chac chan vang mat = mau thuan (chu so lay tu cho khac) -> None."""
    if read:
        return None if header is False else read
    if header is False and known_total:
        return (0, int(known_total))
    return None
