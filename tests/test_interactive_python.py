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

"""Tests for the standalone interpreter's captured-output control protocol."""

import io
import json
from multiprocessing.connection import Client
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

import pytest

from ansys.common.mcp import _interactive_python as worker, helpers
from ansys.common.mcp._interactive_python import Interpreter


@pytest.fixture
def run_worker(tmp_path):
    """Run requests through the real worker and its platform-local control connection."""

    def run(requests):
        script = Path(helpers.__file__).with_name("_interactive_python.py")
        family = "AF_PIPE" if sys.platform == "win32" else "AF_UNIX"
        address = (
            rf"\\.\pipe\worker-test-{uuid4().hex}"
            if family == "AF_PIPE"
            else str(tmp_path / "control")
        )
        with (
            (tmp_path / "stdout").open("wb") as stdout,
            (tmp_path / "stderr").open("wb") as stderr,
        ):
            process = subprocess.Popen(
                [sys.executable, "-u", str(script), address, family],
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=stderr,
                text=True,
                encoding="utf-8",
            )
            try:
                deadline = time.monotonic() + 5
                while True:
                    try:
                        control = Client(address, family=family)
                        break
                    except OSError:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            raise
                        time.sleep(0.01)
                responses = []
                with control:
                    for request in requests:
                        process.stdin.write(request + "\n")
                        process.stdin.flush()
                        assert control.poll(5), "Worker did not return a completion response"
                        responses.append(json.loads(control.recv_bytes()))
                    process.stdin.close()
                    assert process.wait(timeout=5) == 0
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                if process.stdin is not None:
                    process.stdin.close()
        return responses, (tmp_path / "stdout").read_bytes(), (tmp_path / "stderr").read_bytes()

    return run


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
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"id": "request-1", "code": source}) + "\n")
    )
    control = mocker.Mock()

    worker.serve(control)

    control.send_bytes.assert_called_once()
    response = json.loads(control.send_bytes.call_args.args[0])
    assert response["id"] == "request-1"
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
            "id": "first",
            "code": "import os, sys\n"
            "value = 41\n"
            "print('python stdout', end='')\n"
            "print('python stderr', end='', file=sys.stderr)\n"
            "os.write(1, b'native stdout')\n"
            "os.write(2, b'native stderr')",
        },
        {"id": "second", "code": "print(value + 1)"},
    ]
    monkeypatch.setattr(
        sys, "stdin", io.StringIO("".join(json.dumps(request) + "\n" for request in requests))
    )
    control = mocker.Mock()

    worker.serve(control)

    responses = [json.loads(call.args[0]) for call in control.send_bytes.call_args_list]
    assert len(responses) == 2
    assert [response["id"] for response in responses] == ["first", "second"]
    assert all(response["success"] for response in responses)
    assert responses[0]["stdout"] == "python stdout"
    assert responses[0]["stderr"] == "python stderr"
    assert responses[1]["stdout"] == "42\n"
    assert responses[1]["stderr"] == ""
    captured = capfd.readouterr()
    assert captured.out == "native stdout"
    assert captured.err == "native stderr"


def test_native_output_goes_to_subprocess_logs(run_worker):
    """Descriptor writes reach log files, not the captured control response."""
    responses, stdout, stderr = run_worker(
        [
            json.dumps(
                {
                    "id": "native",
                    "code": "import os\n"
                    "print('captured')\n"
                    "os.write(1, b'native stdout')\n"
                    "os.write(2, b'native stderr')",
                }
            )
        ]
    )
    assert responses == [
        {
            "id": "native",
            "success": True,
            "is_complete": True,
            "stdout": "captured\n",
            "stderr": "",
        }
    ]
    assert stdout == b"native stdout"
    assert stderr == b"native stderr"


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
def test_worker_returns_response_and_recovers(run_worker, source, success, is_complete, diagnostic):
    """Real control messages carry matching IDs and isolated output across requests."""
    requests = [
        {"id": "first", "code": source},
        {"id": "second", "code": "x = 42"},
        {"id": "third", "code": "print(x)"},
    ]
    responses, stdout, stderr = run_worker([json.dumps(request) for request in requests])
    assert [response["id"] for response in responses] == ["first", "second", "third"]
    assert responses[0]["success"] is success
    assert responses[0]["is_complete"] is is_complete
    assert all(response["success"] and response["is_complete"] for response in responses[1:])
    assert responses[1]["stdout"] == responses[1]["stderr"] == ""
    assert responses[2]["stdout"] == "42\n"
    assert responses[2]["stderr"] == ""
    assert stdout == stderr == b""
    if diagnostic:
        assert diagnostic in responses[0]["stderr"]
    if source.startswith("for value"):
        assert responses[0]["stdout"] == "1\n2\n"
    if source.startswith("print('partial'"):
        assert responses[0]["stdout"] == "partial"
    if "end='', file=sys.stderr" in source:
        assert responses[0]["stderr"] == "partial"


@pytest.mark.parametrize(
    "request_line, request_id",
    [
        ("not json", None),
        ("[]", None),
        ('{"code": 42}', None),
        ("{}", None),
        ('{"id":"invalid","code":42}', "invalid"),
        ('{"id":42,"code":"pass"}', None),
    ],
)
def test_invalid_request_returns_failure(run_worker, request_line, request_id):
    """Malformed requests return captured diagnostics and preserve valid request IDs."""
    responses, stdout, stderr = run_worker(
        [request_line, json.dumps({"id": "recovery", "code": "print('ok')"})]
    )
    assert responses[0]["id"] == request_id
    assert not responses[0]["success"]
    assert responses[0]["is_complete"]
    assert responses[0]["stdout"] == ""
    assert "Invalid request" in responses[0]["stderr"]
    assert responses[1]["id"] == "recovery"
    assert responses[1]["success"]
    assert responses[1]["stdout"] == "ok\n"
    assert stdout == stderr == b""
