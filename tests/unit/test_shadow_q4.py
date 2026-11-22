"""P6-Q4: so sanh agent / lich cu - ham thuan (ket qua phien that, rui ro)."""
from aowbot.application.shadow import RiskRules, ShadowReport, live_summary, outcome_class, shadow_risks, top_failures


def rep(**kw):
    base = dict(account=1, observations=10, agent_wakes=10, agent_actions={"none": 10}, legacy_gather_visits=0,
                legacy_useful=0, legacy_useless=0, legacy_useful_covered=0, legacy_visits=10,
                agent_dispatch_alone=0, span_days=1.0)
    return ShadowReport(**{**base, **kw})


def test_outcome_class():
    assert outcome_class("ok: gui 1 doi: 0 -> 1/5") == "ok"
    assert outcome_class("failed: khong doc duoc x/y truoc khi gui") == "failed"
    assert outcome_class("khong lam gi") == "none"
    assert outcome_class(None) == "open"


def test_live_summary_and_top_failures():
    rows = [("dispatch_gather", "ok: gui 1 doi: 0 -> 1/5"), ("dispatch_gather", "failed: bat dau 0"),
            ("dispatch_gather", "failed: bat dau 1"), ("dispatch_gather", None), (None, "khong lam gi")]
    s = live_summary(rows)
    assert s["dispatch_gather"] == {"ok": 1, "failed": 2, "none": 0, "open": 1}
    assert s["none"]["none"] == 1
    assert top_failures(rows)["dispatch_gather"] == [("failed: bat dau #", 2)]


def test_no_observations_is_flagged():
    assert "khong co lan quan sat" in shadow_risks(rep(observations=0), [], 30)[0]


def test_clean_account_has_no_risk():
    assert shadow_risks(rep(), [], 30) == []


def test_missed_useful_visits():
    r = shadow_risks(rep(legacy_useful=4, legacy_useful_covered=3), [], 30)
    assert len(r) == 1 and r[0].startswith("bo sot: 1/4")


def test_missed_visits_under_hq_rule_are_not_a_bug():
    r = shadow_risks(rep(legacy_useful=2, legacy_useful_covered=0), [], 7)
    assert r[0].startswith("khac biet theo luat")


def test_extra_dispatch_and_wake_rate():
    r = shadow_risks(rep(agent_dispatch_alone=3, agent_wakes=50, legacy_visits=10), [], 30)
    assert any(x.startswith("them lan ghe: 3") for x in r)
    assert any(x.startswith("thuc day nhieu") for x in r)


def test_dispatch_below_min_hq_is_rule_violation():
    r = shadow_risks(rep(agent_actions={"dispatch_gather": 1}), [], 5, RiskRules(min_hq_gather=9))
    assert any(x.startswith("sai luat") for x in r)


def test_live_failure_rate_threshold():
    rows = [("dispatch_gather", "failed: khong doc duoc x/y")] * 3 + [("dispatch_gather", "ok: gui")] * 7
    assert any("dispatch_gather that bai 3/10" in x for x in shadow_risks(rep(), rows, 30))
    rows_ok = [("dispatch_gather", "failed: x")] * 2 + [("dispatch_gather", "ok")] * 2   # duoi fail_min
    assert shadow_risks(rep(), rows_ok, 30) == []
