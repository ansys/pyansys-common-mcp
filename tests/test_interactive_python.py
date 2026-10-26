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

"""Tests for the standalone interpreter's file output and control protocol."""

import json
from multiprocessing.connection import Listener
from pathlib import Path
import subprocess
import sys

import pytest

from ansys.common.mcp import helpers
from ansys.common.mcp._interactive_python import Interpreter
from ansys.common.mcp.helpers import _CodeTerminationMarker


@pytest.fixture
def run_worker(tmp_path):
    """Run bounded requests with separate output files and a local control connection."""

    def run(request_lines):
        worker = Path(helpers.__file__).with_name("_interactive_python.py")
        stdout_path = tmp_path / "stdout"
        stderr_path = tmp_path / "stderr"
        family = "AF_PIPE" if sys.platform == "win32" else "AF_UNIX"
        with (
            Listener(family=family) as listener,
            stdout_path.open("wb") as stdout,
            stderr_path.open("wb") as stderr,
        ):
            process = subprocess.Popen(
                [sys.executable, "-u", str(worker), listener.address, family],
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=stderr,
                text=True,
                encoding="utf-8",
            )
            try:
                with listener.accept() as control:
                    process.communicate(input="\n".join(request_lines) + "\n", timeout=10)
                    responses = []
                    for _ in request_lines:
                        assert control.poll(10), "Missing worker completion response"
                        responses.append(json.loads(control.recv_bytes()))
                assert process.returncode == 0, stderr_path.read_text(encoding="utf-8")
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
        return responses, stdout_path.read_bytes(), stderr_path.read_bytes()

    return run


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
        ("print('\\u03b1')", True, True, ""),
        ("import os; os.write(1, b'native output')", True, True, ""),
        ("import sys; print('partial', end='', file=sys.stderr)", True, True, "partial"),
    ],
)
def test_worker_emits_valid_marker_and_recovers(
    run_worker, source, success, is_complete, diagnostic
):
    """Each request reports file boundaries over control and leaves output unmodified."""
    requests = [{"code": source}, {"code": "x = 42"}, {"code": "print(x)"}]
    responses, stdout, stderr = run_worker([json.dumps(request) for request in requests])
    markers = [_CodeTerminationMarker.model_validate(response) for response in responses]
    assert len(markers) == 3
    assert markers[0].success is success
    assert markers[0].is_complete is is_complete
    assert all(marker.success and marker.is_complete for marker in markers[1:])
    assert stdout[responses[1]["stdout_end"] : responses[2]["stdout_end"]] == b"42\n"
    assert responses[1]["stdout_end"] == responses[0]["stdout_end"]
    assert responses[2]["stdout_end"] == len(stdout)
    assert all(response["stderr_end"] == len(stderr) for response in responses)
    assert b'{"marker":' not in stdout
    assert b'{"marker":' not in stderr
    if diagnostic:
        assert diagnostic in stderr.decode("utf-8")
    if source.startswith("for value"):
        assert stdout[: responses[0]["stdout_end"]] == b"1\n2\n"
    if source.startswith("print('partial'"):
        assert stdout[: responses[0]["stdout_end"]] == b"partial"
    if "end='', file=sys.stderr" in source:
        assert stderr == b"partial"
    if source == "print('\\u03b1')":
        assert stdout[: responses[0]["stdout_end"]] == "\u03b1\n".encode("utf-8")
    if source.startswith("import os;"):
        assert stdout[: responses[0]["stdout_end"]] == b"native output"


@pytest.mark.parametrize("request_line", ["not json", "[]", '{"code": 42}', "{}"])
def test_invalid_request_emits_failure_marker(run_worker, request_line):
    """Malformed requests report a control failure without contaminating output."""
    responses, stdout, stderr = run_worker([request_line])
    marker = _CodeTerminationMarker.model_validate(responses[0])
    assert not marker.success
    assert marker.is_complete
    assert b"Invalid request" in stderr
    assert stdout == b""
    assert responses[0]["stdout_end"] == 0
    assert responses[0]["stderr_end"] == len(stderr)
