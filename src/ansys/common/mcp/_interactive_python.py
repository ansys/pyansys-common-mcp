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

"""Execute JSON-lines requests and return captured Python output over a control connection."""

import argparse
import code
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from multiprocessing.connection import Connection, Listener
import sys


class Interpreter(code.InteractiveInterpreter):
    """Preserve normal interpreter diagnostics while tracking execution failures."""

    success = True

    def runsource(self, source, filename="<input>", symbol="single"):
        """Reset execution status before compiling and running each snippet."""
        self.success = True
        return super().runsource(source, filename=filename, symbol=symbol)

    def showsyntaxerror(self, filename=None, **kwargs):
        """Record a compilation failure and print the usual diagnostic."""
        self.success = False
        super().showsyntaxerror(filename, **kwargs)

    def showtraceback(self):
        """Record an execution failure and print the usual traceback."""
        self.success = False
        super().showtraceback()


def main():
    """Serve complete snippets in a persistent namespace without rewriting source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address")
    parser.add_argument("family", choices=("AF_UNIX", "AF_PIPE"))
    args = parser.parse_args()
    with Listener(args.address, family=args.family) as listener:
        with listener.accept() as control:
            serve(control)


def serve(control: Connection) -> None:
    """Capture each request's Python output and send one complete JSON response."""
    sys.path[0] = ""  # Preserve working-directory imports from the former ``python -c`` launch.
    interpreter = Interpreter()
    for line in sys.stdin:
        stdout, stderr = io.StringIO(), io.StringIO()
        request_id = None
        with redirect_stdout(stdout), redirect_stderr(stderr):
            is_complete = True
            try:
                request = json.loads(line)
                if isinstance(request, dict) and isinstance(request.get("id"), str):
                    request_id = request["id"]
                if request_id is None or not isinstance(request.get("code"), str):
                    raise ValueError("Expected a JSON object with string 'id' and 'code' fields")
            except ValueError as exc:
                interpreter.success = False
                print(f"Invalid request: {exc}", file=sys.stderr)
            else:
                try:
                    is_complete = not interpreter.runsource(
                        request["code"], filename="<script>", symbol="exec"
                    )
                except SystemExit:
                    interpreter.showtraceback()
        response = json.dumps(
            {
                "id": request_id,
                "success": interpreter.success and is_complete,
                "is_complete": is_complete,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
            }
        )
        control.send_bytes(response.encode("utf-8"))


if __name__ == "__main__":
    main()
