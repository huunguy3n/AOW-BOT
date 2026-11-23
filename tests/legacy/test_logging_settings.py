"""A-REL-1 (log theo ngay cua dong log) + A-REL-4 (log cau hinh hieu luc)."""
import logging
import time

import main
from bot.runner import Runner
from bot.state import deep_merge


def _record(msg, created):
    r = logging.LogRecord("aow", logging.INFO, __file__, 1, msg, None, None)
    r.created = created
    return r


def test_daily_handler_switches_file_at_midnight(tmp_path):
    h = main.DailyFileHandler(str(tmp_path))
    h.setFormatter(logging.Formatter("%(message)s"))
    d1 = time.mktime((2026, 11, 21, 23, 59, 0, 0, 0, -1))
    h.emit(_record("truoc nua dem", d1))
    h.emit(_record("sau nua dem", d1 + 120))
    h.close()
    assert (tmp_path / "bot-20261121.log").read_text(encoding="utf-8").strip() == "truoc nua dem"
    assert (tmp_path / "bot-20261122.log").read_text(encoding="utf-8").strip() == "sau nua dem"


class FakeStore:
    def __init__(self, settings):
        self.settings = settings

    def cfg_for(self, base, idx=None):
        return deep_merge(base, self.settings)


def _runner(settings):
    r = Runner.__new__(Runner)             # khong goi __init__: khong cham ldconsole
    r.base_cfg = {"ldplayer": {"max_running": 2}, "schedule": {"mode": "fixed", "parallel": 2},
                  "speed": {"wait_scale": 0.75}}
    r.store = FakeStore(settings)
    return r


def test_effective_settings_reflect_overrides_and_cap():
    r = _runner({"schedule": {"mode": "smart", "parallel": 5}, "speed": {"wait_scale": 0.5}})
    assert r.effective_settings() == {"mode": "smart", "parallel": 2, "max_running": 2, "agent": "tat",
                                      "wait_scale": 0.5}


def test_settings_logged_once_until_changed(caplog):
    r = _runner({})
    with caplog.at_level(logging.INFO, logger="aow"):
        r._log_settings()
        r._log_settings()
        r.store.settings = {"schedule": {"parallel": 1}}
        r._log_settings()
    lines = [m for m in caplog.messages if m.startswith("Cau hinh hieu luc")]
    assert len(lines) == 2
    assert "parallel=1" in lines[1]
