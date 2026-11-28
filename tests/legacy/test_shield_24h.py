"""Chu du an 2026-11-28 (ngay chien tranh): bang Bao Ho Chien Tranh co dong vat pham "24 tieng" ma bot chua biet ->
bo qua vat pham 24h dang co, mua khien 12h 4800 kim cuong. Gio: 24h vao thu tu vat pham, khong bao gio mua; chua co
anh mau dong 24h thi tim bang OCR '24' giua dong 12h va 3 ngay."""
from aowbot.domain import warday as W
from bot.modules import defense


def test_24h_item_tried_before_any_purchase():
    opts = W.shield_options(15 * 3600, True)
    first_buy = next(i for i, (_, b) in enumerate(opts) if b)
    assert (24, False) in opts[:first_buy]
    assert (24, True) not in opts


def test_row24_y_between_12h_and_3d_needs_ocr_24():
    txt = {500: "Bao Ho Chien Tranh 24 tieng"}
    assert defense.row24_y(395, 605, lambda y: txt.get(y, "")) == 500
    assert defense.row24_y(395, None, lambda y: "Bao Ho Chien Tranh 24 tieng" if y == 500 else "") == 500
    assert defense.row24_y(395, 605, lambda y: "Bao Ho Chien Tranh 3 ngay") is None   # OCR khong ra 24 -> khong bam
    assert defense.row24_y(None, 605, lambda y: "24") is None
