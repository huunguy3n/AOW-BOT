# ruff: noqa: RUF001
import glob
import os

from aowbot.perception.eval import names as nm

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def template_ids():
    out = []
    for f in glob.glob(os.path.join(ROOT, "templates", "*", "*.png")):
        grp = os.path.basename(os.path.dirname(f))
        stem = os.path.basename(f)[:-4]
        # anh chu so (bot/queues.py, bot/march_count.py), khong phai vat the
        if "@" not in stem and grp not in ("digits", "qdigits", "mdigits"):
            out.append(f"{grp}/{stem}")
    return out


def test_every_template_has_a_vietnamese_name():
    missing = [c for c in template_ids() if c not in nm.NAMES]
    assert not missing, f"thieu ten hien thi: {missing}"


def test_groups_cover_all_names_and_display_unique():
    for cid in nm.NAMES:
        assert cid.split("/", 1)[0] in nm.GROUPS, cid
    shown = [nm.display(c) for c in nm.NAMES]
    assert len(shown) == len(set(shown)), "ten hien thi bi trung"


def test_display_and_resolve_roundtrip():
    m = nm.display_map(["intel/btn_attack", "ten/la"])
    assert m["intel/btn_attack"] == "Tình báo › Nút Tấn công (tình báo)"
    assert m["ten/la"] == "ten/la"                       # lop la: giu nguyen
    assert "map/rebel_mech" in m                          # vat the bo sung luon co
    assert nm.resolve("Tình báo › Nút Tấn công (tình báo)", m) == "intel/btn_attack"
    assert nm.resolve("  tình báo › nút tấn công (tình báo) ", m) == "intel/btn_attack"   # khong phan biet hoa/thuong
    assert nm.resolve("intel/btn_attack", m) == "intel/btn_attack"
    assert nm.resolve("Quái mới lạ", m) == "Quái mới lạ"   # go tu do -> lop moi
