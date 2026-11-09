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

"""Execute JSON-lines requests, terminating both output streams with a JSON marker."""

import code
import json
import sys

_MARKER = "___EXECUTION_COMPLETE___"


def main():
    """Serve complete snippets in a persistent namespace without rewriting source."""
    sys.path[0] = ""  # Ensure correct working directory
    # Backwards compatibility with previous python -c launch.
    interpreter = code.InteractiveInterpreter()
    for line in sys.stdin:
        try:
            request = json.loads(line)
            code_to_run = request.get("code") if isinstance(request, dict) else None
            if not isinstance(code_to_run, str):
                raise ValueError("Expected a JSON object with a string 'code' field")
        except ValueError as exc:
            print(f"Invalid request: {exc}", file=sys.stderr)
        else:
            try:
                interpreter.runsource(code_to_run, filename="<script>", symbol="exec")
            except SystemExit:
                interpreter.showtraceback()

        sys.stdout.flush()
        sys.stderr.flush()
        # A leading newline separates the marker from output printed without a newline.
        print("\n" + _MARKER, file=sys.stdout, flush=True)


if __name__ == "__main__":
    main()
