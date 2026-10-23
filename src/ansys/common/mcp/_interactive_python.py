import code
import json
import sys


interpreter = code.InteractiveInterpreter()

for line in sys.stdin:
    try:
        request = json.loads(line)
        source = request["code"]
        if not isinstance(source, str):
            raise TypeError("'code' must be a string")
    except Exception as exc:
        print(json.dumps({
            "status": "failure",
            "stdout": "",
            "stderr": f"Invalid request: {exc}",
        }), flush=True)
        continue

    incomplete = interpreter.runsource(
        source,
        filename="<mcp>",
        symbol="exec",
    )

    if incomplete:
        status = "incomplete"
    else:
        status = "complete"

    print(json.dumps({
        "status": status,
        "stdout": stdout_buffer.getvalue(),
        "stderr": stderr_buffer.getvalue(),
    }), flush=True)

