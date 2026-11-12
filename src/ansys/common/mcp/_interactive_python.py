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

import ast
import code
import json
import sys
import types
import uuid

_MARKER_PREFIX = "___EXECUTION_COMPLETE___:"


def main():
    """Serve complete snippets in a persistent namespace without rewriting source."""
    sys.path[0] = ""  # Ensure correct working directory
    namespace = types.ModuleType("__main__")
    sys.modules["__main__"] = namespace
    interpreter = code.InteractiveInterpreter(namespace.__dict__)
    for line in sys.stdin:
        success = True
        request_id = uuid.uuid4().hex
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("Expected a JSON object")
            request_id = request.get("request_id", request_id)
            if not isinstance(request_id, str):
                raise ValueError("Expected a string 'request_id' field")
            action = request.get("action", "execute")
            if action == "shutdown":
                break
            if action != "execute":
                raise ValueError("Expected action 'execute' or 'shutdown'")
            code_to_run = request.get("code")
            if not isinstance(code_to_run, str):
                raise ValueError("Expected a JSON object with a string 'code' field")
        except ValueError as exc:
            success = False
            print(f"Invalid request: {exc}", file=sys.stderr)
        else:
            try:
                _run_code(interpreter, code_to_run)
            except SyntaxError:
                success = False
                interpreter.showsyntaxerror()
            except BaseException:
                # Submitted code, including its display hook, must not stop the worker.
                success = False
                interpreter.showtraceback()

        marker = f"\n{_MARKER_PREFIX}{request_id}:{json.dumps(success)}"
        print(marker, file=sys.stdout, flush=True)
        print(marker, file=sys.stderr, flush=True)


def _run_code(interpreter: code.InteractiveInterpreter, source: str) -> None:
    """Run Python code with user permissions, not sandboxing, and display its final expression."""
    code_object = interpreter.compile(source, "<script>", "exec")
    if code_object is None:
        raise SyntaxError("Incomplete Python snippet")

    try:
        tree = ast.parse(source, filename="<script>")
    except SyntaxError:
        # Running the submitted snippet is this worker's sole purpose, not a sandbox
        # escape; the AST-based display-hook path below cannot handle sources that
        # fail to re-parse (for example under `__future__` flags), so fall back to a
        # plain exec.
        exec(code_object, interpreter.locals)  # nosec B102
        return

    if not tree.body or not isinstance(tree.body[-1], ast.Expr):
        # Same rationale as above: executing arbitrary user code is intentional here.
        # Nothing to display (no trailing expression), so just run it as a statement.
        exec(code_object, interpreter.locals)  # nosec B102
        return

    expression = ast.Expression(tree.body[-1].value)
    prefix = ast.Module(body=tree.body[:-1], type_ignores=tree.type_ignores)
    flags = interpreter.compile.compiler.flags
    expression_code = compile(expression, "<script>", "eval", flags=flags, dont_inherit=True)
    prefix_code = (
        compile(prefix, "<script>", "exec", flags=flags, dont_inherit=True) if prefix.body else None
    )
    if prefix_code is not None:
        # Run the statements preceding the final expression; intentional, as above.
        exec(prefix_code, interpreter.locals)  # nosec B102
    # Evaluate the trailing expression so its value can be shown, like a REPL does;
    # same intentional-execution rationale as the exec() calls above.
    result = eval(expression_code, interpreter.locals)  # nosec B307
    sys.displayhook(result)


if __name__ == "__main__":
    main()
