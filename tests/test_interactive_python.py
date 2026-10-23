"""Tests for the standalone interpreter's raw-output and termination-marker protocol."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from ansys.common.mcp import helpers
from ansys.common.mcp._interactive_python import Interpreter
from ansys.common.mcp.helpers import _CodeTerminationMarker


@pytest.mark.parametrize("source", ["raise ValueError('problem')", "if True print('bad')"])
def test_runsource_resets_success_after_failure(source):
    """Reuse the interpreter after failure without manually resetting its status."""
    interpreter = Interpreter()
    assert interpreter.runsource("x = 42") is False
    assert interpreter.success

    assert interpreter.runsource(source) is False
    assert not interpreter.success

    assert interpreter.runsource("y = x + 1") is False
    assert interpreter.success
    assert interpreter.locals["y"] == 43


@pytest.mark.parametrize(
    "source, success, is_complete, diagnostic",
    [
        ("for value in [1, 2]: print(value)", True, True, ""),
        ("raise ValueError('problem')", False, True, "ValueError"),
        ("if True print('bad')", False, True, "SyntaxError"),
        ("raise SystemExit(2)", False, True, "SystemExit"),
        ("if True:", False, False, ""),
        ("import sys; print('error message', file=sys.stderr)", True, True, "error message"),
        ("print('partial', end='')", True, True, ""),
    ],
)
def test_worker_emits_valid_marker_and_recovers(source, success, is_complete, diagnostic):
    """Each request emits one model-valid marker and leaves the worker usable."""
    worker = Path(helpers.__file__).with_name("_interactive_python.py")
    requests = [{"code": source}, {"code": "x = 42"}, {"code": "print(x)"}]
    result = subprocess.run(
        [sys.executable, "-u", str(worker)],
        input="".join(json.dumps(request) + "\n" for request in requests),
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    markers = [
        _CodeTerminationMarker.model_validate_json(line)
        for line in result.stdout.splitlines()
        if line.startswith('{"marker":')
    ]
    assert len(markers) == 3
    assert markers[0].success is success
    assert markers[0].is_complete is is_complete
    assert all(marker.success and marker.is_complete for marker in markers[1:])
    assert "\n42\n" in result.stdout
    if diagnostic:
        assert diagnostic in result.stderr
    if source.startswith("for value"):
        assert result.stdout.startswith("1\n2\n")
    if source.startswith("print('partial'"):
        assert result.stdout.startswith('partial\n{"marker":')


@pytest.mark.parametrize("request_line", ["not json", "[]", '{"code": 42}', "{}"])
def test_invalid_request_emits_failure_marker(request_line):
    """Malformed requests report a diagnostic and exactly one termination marker."""
    worker = Path(helpers.__file__).with_name("_interactive_python.py")
    result = subprocess.run(
        [sys.executable, "-u", str(worker)],
        input=request_line + "\n",
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    marker = _CodeTerminationMarker.model_validate_json(result.stdout.strip())
    assert not marker.success
    assert marker.is_complete
    assert "Invalid request" in result.stderr
