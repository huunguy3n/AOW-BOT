from types import SimpleNamespace

from bot.modules import reddots


def _ctx(done):
    return SimpleNamespace(visit_done=done)


def test_skip_when_step_ran_idle():
    assert reddots.already_idle(_ctx({"campaign": 0}), "campaign")
    assert reddots.already_idle(_ctx({"upgrade": None}), "build")


def test_no_skip_when_step_worked_or_not_run():
    assert not reddots.already_idle(_ctx({"campaign": 2}), "campaign")
    assert not reddots.already_idle(_ctx({}), "campaign")
    assert not reddots.already_idle(SimpleNamespace(), "campaign")
    assert not reddots.already_idle(_ctx({"x": 0}), "generic")
