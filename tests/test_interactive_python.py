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

"""Tests for the persistent interactive Python script."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from ansys.common.mcp import _interactive_python

_MARKER = "___EXECUTION_COMPLETE___"


@pytest.fixture
def run_interpreter():
    """Run JSON-line requests through the real interactive Python script."""
    script = Path(_interactive_python.__file__)

    def run(requests: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-u", str(script)],
            input="".join(f"{request}\n" for request in requests),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
            check=False,
        )

    return run


def test_interpreter_preserves_state_between_requests(run_interpreter):
    """Each request runs in the same interpreter and produces a completion marker."""
    result = run_interpreter(
        [
            json.dumps({"code": "value = 41\nprint('ready')"}),
            json.dumps({"code": "print(value + 1)"}),
        ]
    )

    assert result.returncode == 0
    assert result.stdout == f"ready\n\n{_MARKER}\n42\n\n{_MARKER}\n"
    assert result.stderr == ""


def test_interpreter_reports_exceptions_and_continues(run_interpreter):
    """Exceptions, including SystemExit, do not stop later requests."""
    result = run_interpreter(
        [
            json.dumps({"code": "value = 'still available'\nraise ValueError('failure')"}),
            json.dumps({"code": "raise SystemExit(2)"}),
            json.dumps({"code": "print(value)"}),
        ]
    )

    assert result.returncode == 0
    assert result.stdout.count(_MARKER) == 3
    assert "still available" in result.stdout
    assert "ValueError: failure" in result.stderr
    assert "SystemExit: 2" in result.stderr


@pytest.mark.parametrize("request_line", ["not JSON", "[]", "{}", '{"code": 42}'])
def test_interpreter_reports_invalid_requests_and_continues(run_interpreter, request_line):
    """Invalid input is reported on stderr and still receives a completion marker."""
    result = run_interpreter([request_line, json.dumps({"code": "print('recovered')"})])

    assert result.returncode == 0
    assert result.stdout.count(_MARKER) == 2
    assert "recovered" in result.stdout
    assert result.stderr.count("Invalid request:") == 1
