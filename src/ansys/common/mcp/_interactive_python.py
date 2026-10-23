import code
import json
import os
import sys
import tempfile


# Reserve the original stdout pipe exclusively for protocol responses.
sys.stdout.flush()
sys.stderr.flush()

protocol = os.fdopen(
    os.dup(sys.stdout.fileno()),
    "w",
    encoding="utf-8",
    buffering=1,
)

interpreter = code.InteractiveInterpreter()

with open(os.devnull, "wb") as quiet:
    # Outside execution, ordinary output must not enter the protocol.
    os.dup2(quiet.fileno(), 1)
    os.dup2(quiet.fileno(), 2)

    for line in sys.stdin:
        try:
            request = json.loads(line)
            source = request["code"]
            if not isinstance(source, str):
                raise TypeError("'code' must be a string")
        except (ValueError, KeyError, TypeError) as exc:
            protocol.write(json.dumps({
                "status": "failure",
                "stdout": "",
                "stderr": f"Invalid request: {exc}",
            }) + "\n")
            protocol.flush()
            continue

        with (
            tempfile.TemporaryFile(mode="w+b") as stdout_file,
            tempfile.TemporaryFile(mode="w+b") as stderr_file,
        ):
            os.dup2(stdout_file.fileno(), 1)
            os.dup2(stderr_file.fileno(), 2)

            try:
                try:
                    incomplete = interpreter.runsource(
                        source,
                        filename="<script>",
                        symbol="exec",
                    )
                    status = "incomplete" if incomplete else "complete"
                except SystemExit as exc:
                    # Treat exit() as a request error, not server shutdown.
                    status = "failure"
                    print(
                        f"SystemExit: {exc}",
                        file=sys.stderr,
                    )
            finally:
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                finally:
                    os.dup2(quiet.fileno(), 1)
                    os.dup2(quiet.fileno(), 2)

            stdout_file.seek(0)
            stderr_file.seek(0)

            response = {
                "status": status,
                "stdout": stdout_file.read().decode(
                    "utf-8", errors="replace"
                ),
                "stderr": stderr_file.read().decode(
                    "utf-8", errors="replace"
                ),
            }

        protocol.write(json.dumps(response) + "\n")
        protocol.flush()