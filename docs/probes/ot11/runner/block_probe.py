"""How long may one tool call block a product-agent turn?  (ot11 P4)

The loop's ``train_status`` may wait up to 900 s and ``evaluate`` blocks for
its rollouts and film.  This probe measures whether the harness lets a tool
call block that long: a standard-library MCP server with one tool, ``block``,
which sleeps for the seconds it is given, driven by one ``claude -p`` call
with the flags ``cadex -p`` uses.

    python docs/probes/ot11/runner/block_probe.py --seconds 900 --out DIR

Writes ``DIR/block-probe.json`` (asked, measured by the server, measured by
the caller, whether the reply reached the model) and keeps the stream beside
it.  Run as ``--serve`` it is the MCP server itself.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

MODEL = "claude-opus-5-5"
SERVER = "probe"


def serve() -> int:
    def write(message: dict) -> None:
        sys.stdout.write(json.dumps(message) + "\n")
        sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        method, message_id = message.get("method"), message.get("id")
        params = message.get("params") or {}
        if method == "initialize":
            result = {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER, "version": "1"},
            }
        elif method == "tools/list":
            result = {"tools": [{
                "name": "block",
                "description": "Waits for the given number of seconds, then says how long it waited.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"seconds": {"type": "number"}},
                    "required": ["seconds"],
                },
            }]}
        elif method == "tools/call":
            seconds = float((params.get("arguments") or {}).get("seconds", 0))
            started = time.monotonic()
            time.sleep(seconds)
            waited = time.monotonic() - started
            result = {"content": [{"type": "text", "text": f"blocked {waited:.1f} s"}],
                      "isError": False}
        elif method == "ping":
            result = {}
        else:
            if message_id is not None:
                write({"jsonrpc": "2.0", "id": message_id,
                       "error": {"code": -32601, "message": f"Method not found: {method}"}})
            continue
        write({"jsonrpc": "2.0", "id": message_id, "result": result})
    return 0


def probe(seconds: float, out: Path, claude: str) -> int:
    out.mkdir(parents=True, exist_ok=True)
    config = out / "mcp_config.json"
    config.write_text(json.dumps({"mcpServers": {SERVER: {
        "command": sys.executable, "args": [str(Path(__file__).resolve()), "--serve"]}}}))
    command = [
        claude, "-p",
        f"Call the block tool exactly once with seconds={seconds:g}. "
        "Then reply with the tool's answer word for word and nothing else.",
        "--output-format", "stream-json", "--verbose", "--model", MODEL,
        "--mcp-config", str(config), "--strict-mcp-config", "--tools", "",
        "--allowedTools", f"mcp__{SERVER}__block",
    ]
    stream = out / "block-probe-stream.jsonl"
    called = answered = None
    reply, final, error = "", "", False
    started = time.monotonic()
    with stream.open("w") as log:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, cwd=str(out))
        for line in child.stdout:
            now = time.monotonic() - started
            log.write(line)
            log.flush()
            try:
                frame = json.loads(line)
            except ValueError:
                continue
            content = (frame.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if block.get("type") == "tool_use" and called is None:
                    called = now
                elif block.get("type") == "tool_result" and answered is None:
                    answered = now
                    error = bool(block.get("is_error"))
                    inner = block.get("content")
                    reply = inner if isinstance(inner, str) else " ".join(
                        str(part.get("text", "")) for part in inner or [])
            if frame.get("type") == "result":
                final = str(frame.get("result", ""))
        code = child.wait()
    receipt = {
        "schema": "ot11-block-probe-v1",
        "model": MODEL,
        "claude": subprocess.run([claude, "--version"], capture_output=True,
                                 text=True).stdout.strip(),
        "asked_s": seconds,
        "tool_called_at_s": called,
        "tool_answered_at_s": answered,
        "blocked_s": None if called is None or answered is None else round(answered - called, 1),
        "tool_reply": reply,
        "tool_reply_is_error": error,
        "final_text": final,
        "exit_code": code,
        "held": bool(answered is not None and not error and "blocked" in reply),
    }
    (out / "block-probe.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["held"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--seconds", type=float, default=900.0)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--claude", default="claude")
    args = parser.parse_args()
    if args.serve:
        return serve()
    if args.out is None:
        parser.error("--out is required")
    return probe(args.seconds, args.out, args.claude)


if __name__ == "__main__":
    raise SystemExit(main())
