import json

from aowbot.perception.eval import dataset as ds
from aowbot.perception.eval import labeling as lb


def S(i, sess):
    return ds.Sample(i, f"{i}.png", "0" * 64, sess, 3, "unknown", "unknown", "train", "bootstrap", False, ())


def test_apply_labels():
    data = ds.Dataset("v0", ("a",), tuple(S(f"x{k}", f"s{k}") for k in range(40)))
    labels = {f"x{k}": ("new/cls", 100, 100, 40, 20) if k % 2 else ("-", 5, 5, 48, 48) for k in range(40)}
    new = lb.apply(data, labels, {"3": "vn-2.5.16"})
    assert ds.validate(new) == []
    assert "new/cls" in new.classes and "-" not in new.classes
    assert all(s.source == "human" and s.game_build == "vn-2.5.16" for s in new.samples)
    assert next(s for s in new.samples if s.annotations).annotations[0].box == ds.Box(80, 90, 40, 20)
    assert new.in_split("test")


def test_unlabelled_never_in_test():
    data = ds.Dataset("v0", ("a",), tuple(S(f"x{k}", f"s{k}") for k in range(60)))
    new = lb.apply(data, {}, {})
    assert ds.validate(new) == [] and not new.in_split("test") and all(s.source == "bootstrap" for s in new.samples)


def test_store_roundtrip_and_to_labels(tmp_path):
    p = tmp_path / "labels.json"
    assert lb.load_store(p) == {"labels": {}, "builds": {}}      # thieu file -> rong, khong loi
    st = {"labels": {"a": {"c": "x/y", "w": 30, "h": 0}, "b": {"c": ""}, "zz": {"c": "q"}}, "builds": {"1": "vn"}}
    lb.save_store(p, st)
    assert json.loads(p.read_text(encoding="utf-8")) == st
    out = lb.to_labels(lb.load_store(p), {"a": (7, 8), "b": (1, 1)})
    assert out == {"a": ("x/y", 7, 8, 30, lb.DEFAULT_SIZE)}      # rong / id la bi bo; h=0 -> mac dinh
