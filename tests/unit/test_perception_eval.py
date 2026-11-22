import pytest

from aowbot.perception.eval import dataset as ds
from aowbot.perception.eval import metrics as m
from aowbot.perception.eval.dataset import Annotation, Box, Dataset, Sample


def sample(i, session="s1", split="train", source="human", anns=(), complete=True):
    return Sample(i, f"{i}.png", "0" * 64, session, 1, "vn-2.5.16", "city", split, source, complete, tuple(anns))


def ann(cls, x=0, y=0, w=10, h=10, **kw):
    return Annotation(cls, Box(x, y, w, h), **kw)


def pred(cls, x=0, y=0, w=10, h=10, score=0.9):
    return m.Prediction(cls, Box(x, y, w, h), score)


# ------------------------------------------------------------ dataset
def test_box_rejects_empty():
    with pytest.raises(ValueError):
        Box(0, 0, 0, 5)


def test_validate_ok_and_roundtrip(tmp_path):
    d = Dataset("v1", ("a",), (sample("1", anns=[ann("a")]), sample("2", "s2", "test")))
    assert ds.validate(d) == []
    p = tmp_path / "m.json"
    ds.save(d, p)
    assert ds.load(p) == d


def test_validate_catches_session_leak_bootstrap_test_unknown_class_dup():
    d = Dataset("v1", ("a",), (
        sample("1", "s1", "train"), sample("2", "s1", "test"),              # phien o 2 split
        sample("3", "s3", "test", source="bootstrap"),                       # bootstrap trong test
        sample("4", anns=[ann("zzz")]), sample("4", "s9")))                  # lop la + trung id
    errs = " | ".join(ds.validate(d))
    assert "nhieu split" in errs and "test chi nhan" in errs and "lop la" in errs and "trung id" in errs


def test_save_refuses_invalid(tmp_path):
    with pytest.raises(ValueError):
        ds.save(Dataset("v", ("a",), (sample("1", split="bad"),)), tmp_path / "x.json")


def test_assign_splits_deterministic_and_order_independent():
    sess = [f"s{i}" for i in range(200)]
    a = ds.assign_splits(sess)
    assert a == ds.assign_splits(reversed(sess))
    counts = {k: sum(v == k for v in a.values()) for k in ds.SPLITS}
    assert 90 < counts["train"] < 150 and counts["val"] > 10 and counts["test"] > 10
    with pytest.raises(ValueError):
        ds.assign_splits(sess, {"train": 0.5, "val": 0.2, "test": 0.2})


def test_verify_files(tmp_path):
    f = tmp_path / "1.png"
    f.write_bytes(b"abc")
    good = Sample("1", "1.png", ds.sha256_file(f), "s", 1, "b", "u", "train", "human", True)
    bad = Sample("2", "2.png", "0" * 64, "s", 1, "b", "u", "train", "human", True)
    d = Dataset("v", ("a",), (good, bad))
    assert ds.verify_files(d, tmp_path) == ["2: thieu file 2.png"]
    f.write_bytes(b"changed")
    assert "sai sha256" in ds.verify_files(d, tmp_path, [good])[0]


# ------------------------------------------------------------ metrics
def test_iou():
    assert m.iou(Box(0, 0, 10, 10), Box(0, 0, 10, 10)) == 1.0
    assert m.iou(Box(0, 0, 10, 10), Box(20, 20, 5, 5)) == 0.0
    assert m.iou(Box(0, 0, 10, 10), Box(5, 0, 10, 10)) == pytest.approx(50 / 150)


def test_prf_and_fpr():
    ss = [sample("1", anns=[ann("a")]), sample("2", anns=[ann("a")]), sample("3"), sample("4")]
    preds = {"1": [pred("a")],                         # TP
             "2": [pred("a", 100, 100)],               # FP + FN
             "3": [pred("a", 50, 50)],                 # FP tren negative
             "4": []}
    r = m.evaluate(ss, preds, ["a"])
    c = r.per_class["a"]
    assert (c.tp, c.fp, c.fn) == (1, 2, 1)
    assert c.precision == pytest.approx(1 / 3) and c.recall == 0.5
    assert c.f1 == pytest.approx(0.4)
    assert (c.neg_samples, c.neg_fired) == (2, 1) and c.fpr == 0.5   # anh 3,4 la negative; 3 bi bao


def test_incomplete_sample_is_not_negative():
    r = m.evaluate([sample("1", complete=False)], {"1": [pred("a")]}, ["a"])
    assert r.per_class["a"].neg_samples == 0 and r.per_class["a"].fpr is None


def test_undefined_metrics_are_none_not_zero():
    r = m.evaluate([sample("1")], {}, ["a"])
    c = r.per_class["a"]
    assert c.precision is None and c.recall is None and c.f1 is None


def test_one_gt_matches_one_prediction_duplicate_is_fp():
    r = m.evaluate([sample("1", anns=[ann("a")])], {"1": [pred("a", score=0.9), pred("a", score=0.8)]}, ["a"])
    assert (r.per_class["a"].tp, r.per_class["a"].fp) == (1, 1)


def test_confusion_between_classes_and_background():
    ss = [sample("1", anns=[ann("a")]), sample("2", anns=[ann("a")]), sample("3")]
    preds = {"1": [pred("b")], "3": [pred("b", 40, 40)]}
    r = m.evaluate(ss, preds, ["a", "b"])
    assert r.confusion["a"]["b"] == 1               # nhan a bi goi la b
    assert r.confusion["a"][m.BACKGROUND] == 1      # anh 2: bo sot
    assert r.confusion[m.BACKGROUND]["b"] == 1      # anh 3: bao thua


def test_hidden_annotation_not_counted_as_fn():
    r = m.evaluate([sample("1", anns=[ann("a", visible=False)])], {}, ["a"])
    assert r.per_class["a"].fn == 0


def test_percentile_latency_compare():
    assert m.percentile([], 50) is None
    assert m.percentile(list(range(1, 101)), 95) == 95
    assert m.latency([1, 2, 3, 4])["p50"] == 2
    a = m.evaluate([sample("1", anns=[ann("a")])], {}, ["a"])
    b = m.evaluate([sample("1", anns=[ann("a")])], {"1": [pred("a")]}, ["a"])
    assert m.compare(a, b)["a"]["recall"] == 1.0 and m.compare(a, b)["a"]["precision"] is None
