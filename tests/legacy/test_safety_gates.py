"""A-SAFE-2/3/4: cham do ton trong tuy chon, dau truong khi khong doc duoc luc chien, chieu mo can bang chung."""
import copy
import inspect
import pathlib

import pytest

from bot import learn
from bot.ctx import Ctx
from bot.modules.notify import recruit_choice
from bot.modules.play import arena_eligible
from bot.modules.reddots import allowed
from bot.runner import _serial

BASE = {
    "modules": {"rewards": True, "intel": True, "notify": True, "alliance": True, "campaign": True, "daily": True},
    "notify": {"intel": True, "recruit": True, "hero": True},
    "rewards": {"routes": ["mail", "vip", "celebration", "city"]},
}


def cfg(**changes):
    c = copy.deepcopy(BASE)
    for path, value in changes.items():
        section, key = path.split("__")
        c[section][key] = value
    return c


# ---------------------------------------------------------------- A-SAFE-2 reddots
@pytest.mark.parametrize("kind", ["vip", "intel", "recruit", "hero", "alliance", "ally_gift", "campaign", "daily",
                                  "generic"])
def test_everything_allowed_with_default_options(kind):
    assert allowed(kind, BASE)[0]


@pytest.mark.parametrize("kind, change", [
    ("vip", {"modules__rewards": False}),
    ("vip", {"rewards__routes": ["mail"]}),
    ("recruit", {"notify__recruit": False}),
    ("recruit", {"modules__notify": False}),
    ("hero", {"notify__hero": False}),
    ("hero", {"modules__notify": False}),
    ("alliance", {"modules__alliance": False}),
    ("ally_gift", {"modules__alliance": False}),
    ("campaign", {"modules__campaign": False}),
    ("daily", {"modules__daily": False}),
])
def test_disabled_option_blocks_red_dot(kind, change):
    assert not allowed(kind, cfg(**change))[0]


def test_intel_needs_both_paths_disabled():
    assert allowed("intel", cfg(modules__intel=False))[0]                    # notify.intel van lo
    assert allowed("intel", cfg(notify__intel=False))[0]                     # buoc rieng van lo
    assert not allowed("intel", cfg(modules__intel=False, notify__intel=False))[0]
    assert not allowed("intel", cfg(modules__intel=False, modules__notify=False))[0]


def test_generic_red_dot_is_never_gated():
    assert allowed("generic", {"modules": {}, "notify": {}})[0]


# ---------------------------------------------------------------- A-SAFE-3 dau truong
@pytest.mark.parametrize("own", [None, 0])
def test_unknown_own_power_only_red_opponents(own):
    assert not arena_eligible(100_000, False, own, 1.0)
    assert not arena_eligible(10, False, own, 1.0)
    assert arena_eligible(100_000, True, own, 1.0)


@pytest.mark.parametrize("pw, ok", [(900_000, True), (1_000_000, True), (1_000_001, False)])
def test_ratio_limit_for_non_red(pw, ok):
    assert arena_eligible(pw, False, 1_000_000, 1.0) is ok


def test_unreadable_opponent_power_is_skipped():
    assert not arena_eligible(None, True, 1_000_000, 1.0)


def test_only_red_option():
    assert not arena_eligible(10, False, 1_000_000, 1.0, only_red=True)
    assert arena_eligible(2_000_000, True, 1_000_000, 1.0, only_red=True)


# ---------------------------------------------------------------- A-SAFE-4 chieu mo
def choice(free_ok=False, ten_dot=False, one_free=False, free_wait=False, use_tickets=False):
    return recruit_choice(free_ok, ten_dot, one_free, free_wait, use_tickets)


def test_no_evidence_no_tap():
    # truoc A-SAFE-4: khong thay dong ho 'free_wait' la bam '1 lan' nhu mien phi
    assert choice() is None


def test_free_button_first():
    assert choice(free_ok=True, ten_dot=True) == "free"


def test_ten_pull_only_with_red_dot():
    assert choice(ten_dot=True) == "ten"


def test_one_pull_free_needs_dot_and_no_timer():
    assert choice(one_free=True) == "one_free"
    assert choice(one_free=True, free_wait=True) is None


def test_tickets_only_when_enabled():
    assert choice(free_wait=True) is None
    assert choice(free_wait=True, use_tickets=True) == "one_ticket"


# ---------------------------------------------------------------- A-REL-3 / A-DUP-2 / A-CFG-1
def test_help_and_free_takes_options_not_shared_cfg():
    sig = inspect.signature(Ctx.help_and_free)
    assert {"use_help", "use_free"} <= set(sig.parameters)
    mods = ("train", "city", "alliance")
    src = "".join(pathlib.Path(f"bot/modules/{m}.py").read_text(encoding="utf-8") for m in mods)
    assert "_use_help" not in src and "_use_free" not in src


def test_review_candidate_rejects_unknown_template():
    assert learn.review_candidate("rewards/btn_claim", "abc", True) == ("bad", None)


def test_serial_lookup_accepts_int_and_str_keys():
    assert _serial({"adb_serials": {1: "a"}}, 1) == "a"
    assert _serial({"adb_serials": {"1": "b"}}, 1) == "b"
    assert _serial({}, 1) is None
