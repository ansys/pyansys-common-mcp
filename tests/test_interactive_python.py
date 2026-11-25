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

import builtins
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from ansys.common.mcp import _interactive_python

_MARKER_PATTERN = re.compile(r"___EXECUTION_COMPLETE___:[0-9a-f]{32}:(?:true|false)")


def _without_markers(text: str) -> str:
    return re.sub(r"\n" + _MARKER_PATTERN.pattern + r"\n", "", text)


def _request(code: str, request_id: str) -> str:
    return json.dumps(
        {"action": "execute", "code": code, "request_id": request_id},
        ensure_ascii=False,
    )


@pytest.fixture
def run_interpreter(request, monkeypatch, capsys):
    """Exercise the same protocol in a real worker and in coverage-instrumented code."""
    script = Path(_interactive_python.__file__)

    def run(requests: list[str]) -> subprocess.CompletedProcess[str]:
        input_text = "".join(f"{request}\n" for request in requests)
        if getattr(request, "param", "in-process") == "in-process":
            monkeypatch.setattr(sys, "stdin", io.StringIO(input_text))
            monkeypatch.setattr(sys, "path", sys.path.copy())
            monkeypatch.setitem(sys.modules, "__main__", sys.modules["__main__"])
            monkeypatch.setattr(builtins, "_", None, raising=False)
            _interactive_python.main()
            captured = capsys.readouterr()
            return subprocess.CompletedProcess(
                args=[str(script)], returncode=0, stdout=captured.out, stderr=captured.err
            )
        return subprocess.run(
            [sys.executable, "-u", str(script)],
            input=input_text,
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
            _request("value = 41\nprint('ready')", "1" * 32),
            _request("print(value + 1)", "2" * 32),
        ]
    )

    assert result.returncode == 0
    assert result.stdout == (
        f"ready\n\n___EXECUTION_COMPLETE___:{'1' * 32}:true\n"
        f"42\n\n___EXECUTION_COMPLETE___:{'2' * 32}:true\n"
    )
    assert _without_markers(result.stderr) == ""
    assert len(_MARKER_PATTERN.findall(result.stderr)) == 2


def test_interpreter_reports_exceptions_and_continues(run_interpreter):
    """Exceptions, including SystemExit, do not stop later requests."""
    result = run_interpreter(
        [
            _request("value = 'still available'\nraise ValueError('failure')", "1" * 32),
            _request("raise SystemExit(2)", "2" * 32),
            _request("print(value)", "3" * 32),
        ]
    )

    assert result.returncode == 0
    assert len(_MARKER_PATTERN.findall(result.stdout)) == 3
    for request_id, success in (("1" * 32, "false"), ("2" * 32, "false"), ("3" * 32, "true")):
        marker = f"___EXECUTION_COMPLETE___:{request_id}:{success}"
        assert marker in result.stdout
        assert marker in result.stderr
    assert "still available" in result.stdout
    assert "ValueError: failure" in result.stderr
    assert "SystemExit: 2" in result.stderr


@pytest.mark.parametrize(
    "source, stdout, diagnostic",
    [
        ("for value in [1, 2]: print(value)", "1\n2\n", ""),
        ("if True print('bad')", "", "SyntaxError"),
        ("if True:", "", "SyntaxError: Incomplete Python snippet"),
        ("import sys; print('error message', file=sys.stderr)", "", "error message\n"),
        ("print('partial', end='')", "partial", ""),
        ("import sys; print('partial', end='', file=sys.stderr)", "", "partial"),
        ("2 + 2", "4\n", ""),
    ],
)
def test_worker_returns_response_and_recovers(run_interpreter, source, stdout, diagnostic):
    """Every snippet receives a marker and leaves the interpreter usable."""
    result = run_interpreter(
        [
            _request(source, "1" * 32),
            _request("x = 42", "2" * 32),
            _request("print(x)", "3" * 32),
        ]
    )

    assert result.returncode == 0
    assert re.split(r"\n" + _MARKER_PATTERN.pattern + r"\n", result.stdout) == [
        stdout,
        "",
        "42\n",
        "",
    ]
    if diagnostic:
        assert diagnostic in result.stderr
    else:
        assert _without_markers(result.stderr) == ""


@pytest.mark.parametrize(
    "request_line, diagnostic",
    [
        ("not JSON", "Invalid request:"),
        ("[]", "Expected a JSON object"),
        ("{}", "Expected a JSON object with a string 'code' field"),
        ('{"code": 42}', "Expected a JSON object with a string 'code' field"),
        ('{"action": "unknown"}', "Expected action 'execute' or 'shutdown'"),
        ('{"code": "", "request_id": 42}', "Expected a string 'request_id' field"),
    ],
)
def test_interpreter_reports_invalid_requests_and_continues(
    run_interpreter, request_line, diagnostic
):
    """Invalid input is reported on stderr and still receives a completion marker."""
    result = run_interpreter([request_line, _request("print('recovered')", "1" * 32)])

    assert result.returncode == 0
    assert f"___EXECUTION_COMPLETE___:{'1' * 32}:true" in result.stdout
    assert "recovered" in result.stdout
    assert result.stderr.count("Invalid request:") == 1
    assert diagnostic in result.stderr


def test_interpreter_shuts_down_on_protocol_request(run_interpreter):
    """The worker exits cleanly on an explicit shutdown request."""
    result = run_interpreter([json.dumps({"action": "shutdown"})])

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_future_compiler_flags_persist(run_interpreter):
    """Future syntax remains valid in later requests, including the AST fallback."""
    result = run_interpreter(
        [
            _request("from __future__ import barry_as_FLUFL", "1" * 32),
            _request("print(1 <> 2)", "2" * 32),
        ]
    )

    assert result.returncode == 0
    assert _without_markers(result.stdout) == "True\n"
    assert _without_markers(result.stderr) == ""


@pytest.mark.parametrize("run_interpreter", ["subprocess"], indirect=True)
def test_worker_subprocess_lifecycle(run_interpreter):
    """A real child starts, preserves state after errors, and shuts down cleanly."""
    result = run_interpreter(
        [
            _request("value = 41", "1" * 32),
            _request("raise ValueError('failure')", "2" * 32),
            _request("print(value + 1)", "3" * 32),
            json.dumps({"action": "shutdown"}),
            _request("print('must not execute')", "4" * 32),
        ]
    )

    assert result.returncode == 0
    assert _without_markers(result.stdout) == "42\n"
    assert "ValueError: failure" in result.stderr
    for token, status in (("1", "true"), ("2", "false"), ("3", "true")):
        marker = f"___EXECUTION_COMPLETE___:{token * 32}:{status}"
        assert marker in result.stdout
        assert marker in result.stderr
