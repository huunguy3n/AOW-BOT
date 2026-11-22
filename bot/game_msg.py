"""S2: doc THONG BAO NOI cua game (dai chu trang tren nen toi o giua man, vd "Khu vuc toa nha nay chua duoc mo
khoa, vui long mo khoa lo dat truoc", "Radar mo khoa cap 1") -> ly do viec bi chan (aowbot.domain.blockers).

Chi goi khi thao tac KHONG co tac dung (tiet kiem OCR ~150-250 ms/lan). Vi tri: anh logs/inv (A-INV-1), y ~300-345.
"""
from bot import ocr
from aowbot.domain.blockers import classify

BAND = (0, 270, 540, 110)   # dai thong bao noi (540x960)


def read(img):
    """-> (BlockReason | None, chuoi OCR)."""
    s = ocr.text(img, BAND, scale=2, psm=6)
    return classify(s), s
