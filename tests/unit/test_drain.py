"""aowbot.domain.drain (G2): buoc lam duoc viec mo khoa buoc da chay truoc no."""
from aowbot.domain.drain import followups, worked

ORDER = ["notify", "rewards", "train", "upgrade", "construct", "research", "daily"]
EN = dict.fromkeys(ORDER, True)


def test_worked():
    assert worked(2) and worked({"a": 1}) and not worked(0) and not worked(None) and not worked("")


def test_daily_claim_reruns_earlier_resource_steps():
    done = dict.fromkeys(ORDER)
    done["daily"] = 3
    assert followups(ORDER, done, EN, {}) == ["train", "upgrade", "construct", "research"]


def test_source_without_work_does_nothing():
    done = dict.fromkeys(ORDER, 0)
    assert followups(ORDER, done, EN, {}) == []


def test_only_steps_before_source_and_only_ran():
    done = {"notify": 0, "rewards": 2}      # rewards xong luc nay; train/upgrade chua chay (chua toi) -> khong chay lai
    assert followups(ORDER, done, EN, {}) == []
    done = dict.fromkeys(ORDER, 0)
    done["rewards"] = 2
    assert followups(ORDER, done, EN, {}) == []   # cac buoc sau rewards da chay sau no roi


def test_construct_reruns_upgrade_once_and_respects_cap_and_enabled():
    done = dict.fromkeys(ORDER, 0)
    done["construct"] = 2
    assert followups(ORDER, done, EN, {}) == ["upgrade"]
    assert followups(ORDER, done, EN, {"upgrade": 1}) == []
    assert followups(ORDER, done, {**EN, "upgrade": False}, {}) == []
    done["daily"] = 1
    assert len(followups(ORDER, done, EN, {}, max_extra=2)) == 2
    assert followups(ORDER, done, EN, {"train": 1, "research": 1}, max_extra=2) == []


def test_upgrade_repeats_while_it_keeps_working_up_to_limit():
    done = dict.fromkeys(ORDER, 0)
    done["upgrade"] = 1
    assert followups(ORDER, done, EN, {}) == ["upgrade"]
    assert followups(ORDER, done, EN, {"upgrade": 5}) == ["upgrade"]
    assert followups(ORDER, done, EN, {"upgrade": 6}) == []
    done["upgrade"] = 0
    assert followups(ORDER, done, EN, {"upgrade": 2}) == []
