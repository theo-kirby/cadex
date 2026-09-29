# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Count the product agent's refused tool calls, by class (ot10 A4).

A4 asks that four hex2/hex3 refusal classes stop recurring in A5's
transcripts. This is the mechanical count: it reads a product-agent session
transcript (a Claude Code ``.jsonl``, local to the machine and never
committed), takes every tool result marked ``is_error``, and assigns each
one class from the engine's own refusal text and ``failure_code``.

The four A4 classes are anchored on the exact sentences the engine emits,
old wording (hex2/hex3) and new (ADR-416) alike, so an output that happens
to be called ``horn`` is not a horn-style refusal. That false match is what
the notes-directory counter this replaces got wrong on hexapod attempt 2.

    pixi run python docs/probes/ot10/runner/refusals.py \\
        --out docs/probes/ot10/refusals.json NAME=STATUS=TRANSCRIPT.jsonl ...

``refusals.json`` keeps, per transcript, its sha256, the counts, and each
refusal's tool, ``failure_code`` and the first 200 characters of its error,
so the counts can be re-derived from the committed file without the
transcript.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

A4_CLASSES = ("horn_style", "edit_before_script", "assembly_output_count", "joint_listing")
CLASSES = A4_CLASSES + (
    "cpu_limit", "sandbox", "kernel", "json_pointer", "edit_replacement",
    "outputs_dropped", "retire_linked_output", "reset_variation", "other",
)
STATUSES = ("counted", "failed_attempt", "not_an_attempt")
EXCERPT = 200

_PATTERNS = (
    # hex2/hex3: "lib.servo.horn: style must be one of ..."; ADR-416: "'x' is not a horn style".
    ("horn_style", None, r"is not a horn style|\.horn: style must be one of"),
    ("edit_before_script", "NO_PROJECT_SCRIPT", r"no (accepted )?project script (to edit )?yet"),
    ("assembly_output_count", None, r"must return exactly one assembly and one solver_diagnostics output"),
    ("joint_listing", None, r"Every (joint|component) listed in api\.assembly must be returned exactly once"),
    ("cpu_limit", None, r"exceeded its CPU limit"),
    ("sandbox", None, r"^name '\w+' is not defined|imports are not allowed|private attributes are not allowed"),
    ("json_pointer", None, r"^JSON Pointer path does not exist"),
    ("edit_replacement", "REPLACEMENT_NOT_UNIQUE", None),
    ("outputs_dropped", "PROJECT_OUTPUTS_DROPPED", r"^This script drops outputs that the accepted revision declares"),
    ("retire_linked_output", None, r"^Cannot retire XScript output"),
    ("reset_variation", None, r"The reset variation in task output .* further into the floor"),
    ("kernel", None, r"OpenCascade|refused the requested radius|refining its result|"
     r"invalid bounding box|did not match its declared cardinality|could be blended at that radius"),
)


def classify(failure_code: str, error: str) -> str:
    """One class for one refusal: the first pattern whose code or text matches."""
    for name, code, pattern in _PATTERNS:
        if code is not None and failure_code == code:
            return name
        if pattern is not None and re.search(pattern, error, re.IGNORECASE):
            return name
    return "other"


def _text(content) -> str:
    if isinstance(content, list):
        return " ".join(item.get("text", "") for item in content if isinstance(item, dict))
    return content if isinstance(content, str) else json.dumps(content)


def _fields(text: str) -> tuple[str, str]:
    """The refusal's failure_code and error, from its JSON body.

    A long refusal reaches the transcript with its middle truncated by the
    agent CLI, which leaves invalid JSON; the two fields are then read by
    pattern, since both precede the cut in every such body."""
    try:
        body = json.loads(text)
    except ValueError:
        body = None
    if isinstance(body, dict):
        return str(body.get("failure_code") or ""), str(body.get("error") or "")
    code = re.search(r'"failure_code": "(\w*)"', text)
    error = re.search(r'"error": "((?:[^"\\]|\\.)*)"', text)
    if error is None:
        return (code.group(1) if code else ""), text
    return (code.group(1) if code else ""), json.loads(f'"{error.group(1)}"')


def refused_calls(transcript: Path) -> list[dict]:
    """Every tool result marked is_error, in transcript order."""
    tools: dict[str, str] = {}
    refused = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        message = json.loads(line).get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), list):
            continue
        for item in message["content"]:
            if item.get("type") == "tool_use":
                tools[item["id"]] = item["name"].removeprefix("mcp__cadex__")
            elif item.get("type") == "tool_result" and item.get("is_error"):
                text = _text(item.get("content"))
                code, error = _fields(text)
                refused.append({
                    "tool": tools.get(item.get("tool_use_id"), "?"),
                    "failure_code": code,
                    "error": " ".join(error.split())[:EXCERPT],
                })
    return refused


def counts(refused: list[dict]) -> dict[str, int]:
    tally = {name: 0 for name in CLASSES}
    for call in refused:
        tally[classify(call["failure_code"], call["error"])] += 1
    return tally


def census(transcript: Path, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, not {status!r}")
    refused = refused_calls(transcript)
    return {
        "status": status,
        "transcript_sha256": hashlib.sha256(transcript.read_bytes()).hexdigest(),
        "refused": len(refused),
        "counts": counts(refused),
        "calls": refused,
    }


_SHOWN = ("cpu_limit", "sandbox", "kernel", "json_pointer")
_HEADER = (
    "| project | status | horn style | edit before script | output count "
    "| joint listing | refused | CPU limit | sandbox | kernel | JSON pointer | rest |"
)


def table(data: dict) -> str:
    """The README's census table: the four A4 classes first, then the rest."""
    lines = [_HEADER, "|" + "---|" * _HEADER.count(" | ") + "---|"]
    total = {name: 0 for name in CLASSES}
    refused = 0
    for name, row in data["projects"].items():
        tally = row["counts"]
        rest = row["refused"] - sum(tally[c] for c in A4_CLASSES + _SHOWN)
        cells = [f"`{name}`", row["status"].replace("_", " ")]
        cells += [str(tally[c]) for c in A4_CLASSES]
        cells += [str(row["refused"])] + [str(tally[c]) for c in _SHOWN] + [str(rest)]
        lines.append("| " + " | ".join(cells) + " |")
        refused += row["refused"]
        for c in CLASSES:
            total[c] += tally[c]
    rest = refused - sum(total[c] for c in A4_CLASSES + _SHOWN)
    cells = ["**all**", f"{len(data['projects'])} transcripts"]
    cells += [f"**{total[c]}**" for c in A4_CLASSES]
    cells += [str(refused)] + [str(total[c]) for c in _SHOWN] + [str(rest)]
    lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("entries", nargs="+", metavar="NAME=STATUS=TRANSCRIPT")
    args = parser.parse_args(argv)
    projects = {}
    for entry in args.entries:
        name, status, path = entry.split("=", 2)
        projects[name] = census(Path(path), status)
    args.out.write_text(
        json.dumps({"schema": "ot10-refusals-v1", "classes": list(CLASSES),
                    "a4_classes": list(A4_CLASSES), "projects": projects},
                   indent=2) + "\n",
        encoding="utf-8",
    )
    print(table({"projects": projects}))
    for name, row in projects.items():
        print(name, row["status"], row["refused"],
              {k: v for k, v in row["counts"].items() if v})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
