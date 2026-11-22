import pytest

from bot import ocr


@pytest.fixture(autouse=True)
def _restore_ocr_flag():
    """Test OCR that (@pytest.mark.ocr) goi ocr.init -> bat Tesseract toan cuc; test sau dung anh gia se goi Tesseract
    that va vo (vd test_priority_queues). Khoi phuc co sau moi test."""
    old = ocr._ok
    yield
    ocr._ok = old
