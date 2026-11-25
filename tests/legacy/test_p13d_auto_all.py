"""P13d-6: --auto-all goi runner.start() truoc serve(); chi --web thi khong."""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "aow_main", os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(main)


class _R:
    def __init__(self, calls):
        self.calls = calls

    def start(self):
        self.calls.append("start")


def test_parse_auto_all():
    ap = main.build_parser()
    assert ap.parse_args(["--web", "--auto-all"]).auto_all is True
    assert ap.parse_args(["--web"]).auto_all is False


def test_auto_all_starts_before_serve():
    calls = []
    main.launch_web(_R(calls), None, None, 8080, True, serve_fn=lambda *a: calls.append("serve"))
    assert calls == ["start", "serve"]


def test_web_only_does_not_start():
    calls = []
    main.launch_web(_R(calls), None, None, 8080, False, serve_fn=lambda *a: calls.append("serve"))
    assert calls == ["serve"]


def test_run_bat_passes_flag():
    with open(os.path.join(os.path.dirname(__file__), "..", "..", "run.bat")) as f:
        bat = f.read()
    assert "--auto-all" in bat
