"""S2: thong bao game -> ly do chan + han (luat thuan). Chuoi OCR lay nguyen tu anh logs/inv (A-INV-1)."""
import pytest

from aowbot.domain.blockers import (
    DEFAULT_TTL_S,
    BlockReason,
    block,
    classify,
    dump,
    find_active,
    hamming,
    load,
    normalize,
)

NOW = 1_800_000_000.0


@pytest.mark.parametrize("text, want", [
    ("Khu vyc toa nha nay chua dugc mé Kchda, van hens\nkhéa 16 dat truéc oS", BlockReason.PLOT_LOCKED),
    ("Ki vyc toa nha nay chua dugc mé khéa, vui long thd\na .° khéa 16 dat trudc oe", BlockReason.PLOT_LOCKED),
    ("Khu vực tòa nhà này chưa được mở khóa, vui lòng mở khóa lô đất trước", BlockReason.PLOT_LOCKED),
    ("a a\nRadar mé khéa cap 1 z >: “Pn", BlockReason.PREREQ),
    ("Radar mở khóa cấp 1", BlockReason.PREREQ),
    ("~~ Bly 0 [lo Jle gitip ban xay dung cap 4-Xudng Xe\n@®. = Tang, di gidm 35 gidy!", None),  # tro giup lien minh
    ("— WP Phiestun.", None),
    ("", None),
])
def test_classify_ocr_text(text, want):
    assert classify(text) is want


def test_normalize_strips_accents():
    assert normalize("  Lô  ĐẤT ") == "lo dat"


def test_block_expiry_and_roundtrip():
    b = block("1010", BlockReason.PREREQ, NOW)
    assert b.until == NOW + DEFAULT_TTL_S[BlockReason.PREREQ]
    raw = dump({"1010": b, "old": block("old", BlockReason.NO_EFFECT, NOW - 10 * 3600)})
    got = load(raw, NOW)
    assert set(got) == {"1010"} and got["1010"] == b


def test_load_ignores_garbage():
    assert load({"a": {"reason": "khong_co"}, "b": {}, "c": {"reason": "prereq", "until": "x"}}, NOW) == {}
    assert load(None, NOW) == {}


def test_find_active_tolerates_small_bit_noise():
    blocks = {"1111000011110000": block("1111000011110000", BlockReason.PLOT_LOCKED, NOW)}
    assert find_active(blocks, "1111000011110001", NOW, max_dist=2) is not None
    assert find_active(blocks, "0000111100001111", NOW, max_dist=2) is None
    assert find_active(blocks, "1111000011110000", NOW + 13 * 3600, max_dist=2) is None   # het han
    assert hamming("10", "101") == 1
