"""Drive the product agent through the training loop, turn by turn.  (ot11 P4)

One frozen first prompt, then a frozen continuation prompt for as long as
the project's loop ledger says the loop is not over.  Each turn is the
ordinary product path, ``cadex -p`` (the continuation with ``--resume``),
on ``claude-opus-5-5`` with no fallback; the only addition is that every
stream frame is written down as it arrives.  Nothing here names a behaviour:
the prompts do.

    pixi run python docs/probes/ot11/runner/rounds.py \
        --project PROJECT \
        --prompt docs/probes/ot11/prompts/NAME.loop.prompt.txt \
        --out OUT

Start it in a session of its own (``setsid``): the turns then outlive the
caller, as the training runs already do under their supervisor.  ``OUT``
gets ``registration.json`` before the first turn, ``turn-N/`` for each turn
and ``rounds.json`` when it ends.  ``--summarise`` prints the rounds read
back from the ledger and the transcripts and starts nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "cli"))

MODEL = "claude-opus-5-5"
CONTINUE = REPO / "docs/probes/ot11/prompts/continue.loop.prompt.txt"
LEDGER = "loop-ledger.jsonl"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def ledger(project: Path) -> list[dict]:
    path = project / LEDGER
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def standing(project: Path) -> dict:
    """Where the loop is, read from the project's own ledger."""
    rows = ledger(project)
    evaluations = [row for row in rows if row.get("kind") == "evaluated"]
    return {
        "runs_registered": sum(1 for row in rows if row.get("kind") == "train_registered"),
        "runs_ended": sum(1 for row in rows if row.get("kind") == "train_ended"),
        "evaluations": len(evaluations),
        "passed": bool(evaluations) and evaluations[-1].get("verdict") == "pass",
    }


def over(state: dict, max_runs: int) -> bool:
    return state["passed"] or (
        state["evaluations"] >= max_runs and state["runs_ended"] >= state["runs_registered"])


def turn(project: Path, out: Path, prompt: Path, *, resume: bool) -> int:
    from cadex_cli import __main__ as cli
    from cadex_cli.agent import ClaudeTurn, find_claude

    original = cli.command_prompt

    class CapturedTurn(ClaudeTurn):
        def __init__(self, **kwargs):
            kwargs["claude_path"] = find_claude("")
            super().__init__(**kwargs)

        def _absorb(self, frame, result):
            stamped = {"t": round(time.time(), 3), **frame}
            with (out / "transcript.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(stamped) + "\n")
            super()._absorb(frame, result)

    cli.command_prompt = lambda args, report: original(args, report, turn_factory=CapturedTurn)
    arguments = ["--project", str(project), "--json", "--model", MODEL,
                 "--out", str(out / "exports"), "-p", prompt.read_text(encoding="utf-8")]
    if resume:
        arguments.append("--resume")
    stdout = sys.stdout
    try:
        with (out / "turn.stdout.json").open("w", encoding="utf-8") as sink:
            sys.stdout = sink
            return int(cli.main(arguments) or 0)
    finally:
        sys.stdout = stdout
        cli.command_prompt = original


def tool_calls(transcript: Path) -> list[dict]:
    """Each tool call of a transcript with how long its answer took."""
    opened: dict[str, dict] = {}
    calls: list[dict] = []
    if not transcript.is_file():
        return calls
    for line in transcript.read_text(encoding="utf-8").splitlines():
        frame = json.loads(line)
        content = (frame.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if block.get("type") == "tool_use":
                call = {"tool": str(block.get("name", "")).rsplit("__", 1)[-1],
                        "input": block.get("input") or {}, "asked_at": frame.get("t")}
                opened[block.get("id")] = call
                calls.append(call)
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in opened:
                call = opened[block["tool_use_id"]]
                call["seconds"] = round(frame.get("t", 0) - call.pop("asked_at"), 1)
                call["is_error"] = bool(block.get("is_error"))
    return calls


def summarise(project: Path, out: Path) -> dict:
    rows = ledger(project)
    turns = []
    for folder in sorted(out.glob("turn-*"), key=lambda p: int(p.name.split("-")[1])):
        calls = tool_calls(folder / "transcript.jsonl")
        by_tool: dict[str, dict] = {}
        for call in calls:
            entry = by_tool.setdefault(call["tool"], {"calls": 0, "errors": 0, "longest_s": 0.0})
            entry["calls"] += 1
            entry["errors"] += int(call.get("is_error", False))
            entry["longest_s"] = max(entry["longest_s"], call.get("seconds", 0.0))
        receipt = folder / "turn.json"
        turns.append({**(json.loads(receipt.read_text()) if receipt.is_file() else {}),
                      "turn": folder.name, "tool_calls": len(calls), "by_tool": by_tool})
    return {"schema": "ot11-rounds-v1", "project": project.name, "standing": standing(project),
            "ledger": rows, "turns": turns}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--prompt", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-runs", type=int, default=4)
    parser.add_argument("--max-turns", type=int, default=4)
    parser.add_argument("--summarise", action="store_true")
    args = parser.parse_args()
    project, out = args.project.expanduser().resolve(), args.out.expanduser().resolve()
    if args.summarise:
        print(json.dumps(summarise(project, out), indent=2))
        return 0
    if args.prompt is None:
        parser.error("--prompt is required")
    out.mkdir(parents=True, exist_ok=True)
    if (out / "registration.json").exists():
        parser.error(f"{out} already holds a registered session")
    write(out / "registration.json", {
        "schema": "ot11-rounds-registration-v1",
        "project": project.name,
        "model": MODEL,
        "fallback": None,
        "first_prompt": {"file": args.prompt.name, "sha256": sha256(args.prompt)},
        "continue_prompt": {"file": CONTINUE.name, "sha256": sha256(CONTINUE)},
        "max_runs": args.max_runs,
        "max_turns": args.max_turns,
        "stop_rule": "an evaluation passes on every seed, or max_runs runs have been trained "
                     "and evaluated, or max_turns turns have ended",
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    for index in range(1, args.max_turns + 1):
        folder = out / f"turn-{index}"
        folder.mkdir()
        prompt = args.prompt if index == 1 else CONTINUE
        started = time.time()
        code = turn(project, folder, prompt, resume=index > 1)
        state = standing(project)
        write(folder / "turn.json", {"prompt": prompt.name, "resume": index > 1,
                                     "exit_code": code, "seconds": round(time.time() - started, 1),
                                     "standing_after": state})
        if over(state, args.max_runs):
            break
    write(out / "rounds.json", summarise(project, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
