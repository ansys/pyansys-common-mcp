# Copyright (C) 2025 - 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the standalone interpreter's raw-output and termination-marker protocol."""

import io
import json
from pathlib import Path
import subprocess
import sys

import pytest

from ansys.common.mcp import _interactive_python as worker, helpers
from ansys.common.mcp._interactive_python import Interpreter
from ansys.common.mcp.helpers import _CodeTerminationMarker


@pytest.mark.parametrize(
    "source, success, is_complete, stdout, diagnostic",
    [
        ("print('partial', end='')", True, True, "partial", ""),
        ("print('\\u03b1')", True, True, "\u03b1\n", ""),
        ("for value in [1, 2]: print(value)", True, True, "1\n2\n", ""),
        ("raise ValueError('problem')", False, True, "", "ValueError"),
        ("if True print('bad')", False, True, "", "SyntaxError"),
        ("raise SystemExit(2)", False, True, "", "SystemExit"),
        ("if True:", False, False, "", ""),
    ],
)
def test_worker_returns_captured_response(
    monkeypatch, mocker, capfd, source, success, is_complete, stdout, diagnostic
):
    """Return one complete response per request, without printing protocol data."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"code": source}) + "\n"))
    control = mocker.Mock()

    worker.serve(control)

    control.send_bytes.assert_called_once()
    response = json.loads(control.send_bytes.call_args.args[0])
    assert response["success"] is success
    assert response["is_complete"] is is_complete
    assert response["stdout"] == stdout
    if diagnostic:
        assert diagnostic in response["stderr"]
    else:
        assert response["stderr"] == ""
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_worker_separates_native_output_and_preserves_state(monkeypatch, mocker, capfd):
    """Native writes bypass Python capture; each response contains only its own output."""
    requests = [
        {
            "code": "import os, sys\n"
            "value = 41\n"
            "print('python stdout', end='')\n"
            "print('python stderr', end='', file=sys.stderr)\n"
            "os.write(1, b'native stdout')\n"
            "os.write(2, b'native stderr')"
        },
        {"code": "print(value + 1)"},
    ]
    monkeypatch.setattr(
        sys, "stdin", io.StringIO("".join(json.dumps(request) + "\n" for request in requests))
    )
    control = mocker.Mock()

    worker.serve(control)

    responses = [json.loads(call.args[0]) for call in control.send_bytes.call_args_list]
    assert len(responses) == 2
    assert all(response["success"] for response in responses)
    assert responses[0]["stdout"] == "python stdout"
    assert responses[0]["stderr"] == "python stderr"
    assert responses[1]["stdout"] == "42\n"
    assert responses[1]["stderr"] == ""
    captured = capfd.readouterr()
    assert captured.out == "native stdout"
    assert captured.err == "native stderr"


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
        ("import sys; print('partial', end='', file=sys.stderr)", True, True, "partial"),
    ],
)
def test_worker_emits_valid_marker_and_recovers(source, success, is_complete, diagnostic):
    """Each request terminates both streams with matching markers and remains usable."""
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
    stderr_markers = [
        _CodeTerminationMarker.model_validate_json(line)
        for line in result.stderr.splitlines()
        if line.startswith('{"marker":')
    ]
    assert stderr_markers == markers
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
    if "end='', file=sys.stderr" in source:
        assert result.stderr.startswith('partial\n{"marker":')


@pytest.mark.parametrize("request_line", ["not json", "[]", '{"code": 42}', "{}"])
def test_invalid_request_emits_failure_marker(request_line):
    """Malformed requests report a diagnostic and a marker on each output stream."""
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
    stderr_marker = _CodeTerminationMarker.model_validate_json(result.stderr.splitlines()[-1])
    assert stderr_marker == marker
