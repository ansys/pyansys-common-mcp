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

"""Execute JSON-lines requests with file-backed output and a separate control channel."""

import argparse
import code
import json
from multiprocessing.connection import Client
import os
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
    with Client(args.address, family=args.family) as control:
        serve(control)


def serve(control):
    """Report completion and byte boundaries after flushing file-backed output."""
    sys.path[0] = ""  # Preserve working-directory imports from the former ``python -c`` launch.
    interpreter = Interpreter()
    for line in sys.stdin:
        is_complete = True
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or not isinstance(request.get("code"), str):
                raise ValueError("Expected a JSON object with a string 'code' field")
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

        sys.stdout.flush()
        sys.stderr.flush()
        marker = json.dumps(
            {
                "marker": "___EXECUTION_COMPLETE___",
                "success": interpreter.success and is_complete,
                "is_complete": is_complete,
                "stdout_end": os.lseek(sys.stdout.fileno(), 0, os.SEEK_CUR),
                "stderr_end": os.lseek(sys.stderr.fileno(), 0, os.SEEK_CUR),
            }
        )
        control.send_bytes(marker.encode("utf-8"))


if __name__ == "__main__":
    main()
