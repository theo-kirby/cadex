# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One ``claude -p`` turn, and the prompt that tells it where it is.

Claude Code owns the model loop — streaming, tool orchestration, retries,
context, and the user's existing login. The CLI owns the engine and the
tools, and nothing else. That division is the same one the Blender shell
makes, and ADR-061 is candid that running it a second time here *is* a
second turn orchestration; what stops the two drifting is that neither
states the xscript API. Both ask the engine for it through ``describe_api``
and paste the answer into the prompt, so there is one contract and two
callers of it.

Turn continuity is Claude Code's own ``--resume <session-id>``, with the
session id kept in the project's ``agent.json``. A stale id must degrade to
a fresh conversation rather than to a dead run: an id can outlive the
history it names — the project directory was copied to another machine, or
the local sessions were pruned — and a pipeline step that dies for that is
a pipeline step that dies for nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .tools import CLI_TOOL_OPS

#: The shell's default, and it stays the shell's default: one model
#: answers "what does Cadex run" wherever you ask. Override with
#: ``--model``.
DEFAULT_MODEL = "claude-fable-5"

MCP_SERVER_NAME = "cadex"

_CLAUDE_CANDIDATES = (
    "~/.claude/local/claude",
    "~/.local/bin/claude",
    "/usr/local/bin/claude",
    "/usr/bin/claude",
    "/opt/homebrew/bin/claude",
)


class ClaudeUnavailable(RuntimeError):
    """No ``claude`` CLI to drive."""


def find_claude(explicit: str = "") -> str:
    """Locate the ``claude`` binary; raise :class:`ClaudeUnavailable`."""

    if explicit:
        path = os.path.expanduser(explicit)
        if os.path.exists(path):
            return path
        raise ClaudeUnavailable(f"No claude CLI at {path}.")
    found = shutil.which("claude")
    if found:
        return found
    for candidate in _CLAUDE_CANDIDATES:
        path = os.path.expanduser(candidate)
        if os.path.exists(path):
            return path
    raise ClaudeUnavailable(
        "The `claude` CLI was not found on PATH. Install Claude Code, or "
        "pass --claude <path>. `cadex params` and `cadex export` need no "
        "model and run without it."
    )


#: The CLI's own overlay. Written fresh for this front end (the shell's is
#: GPL and says different things anyway — it is talking to a model that has
#: a viewport). Everything about the *API* is left to describe_api, which is
#: appended live; this text is only about the situation.
CLI_OVERLAY = """\
You are the modelling half of Cadex, a CAD application, running headless in \
a terminal. There is no viewport, no window, and no user watching a screen: \
your caller is a person at a shell prompt or a script in a pipeline.

THE MODEL IS ONE SCRIPT. The whole document is a single xscript project \
script that the engine runs to produce geometry. There is no other state. \
Write it with write_script, change it with edit_script, change only its \
numbers with set_params.

BUILD IT PARAMETRIC. This is the point of the CLI. Declare every dimension \
a caller might want to vary as a parameter at the top of the script — \
`p = params(wall=num(4.0, unit="mm", min=2.0, max=10.0, step=0.5), ...)` — \
and use `p.wall` throughout rather than repeating the literal. A later run \
sweeps those parameters with `cadex params --set wall=6` and never calls a \
model at all, which is thousands of times cheaper than asking you to edit \
the script. A script whose dimensions are hard-coded throws that away. Keep \
parameter names stable across turns: a pipeline is holding them.

ALL LENGTHS ARE MILLIMETRES.

CALL describe_api BEFORE YOUR FIRST SCRIPT, and again whenever you need an \
exact signature. It is served live by the engine you are talking to, so it \
is the truth about this version. Do not write an xscript API from memory.

YOU CANNOT SEE YOUR WORK. There is no screenshot, no render and no viewport \
here, and no way for the caller to click a face and hand it to you. Verify \
through facts instead, and do verify:

- `inspect scope=output` for the accepted revision's per-output facts — \
shape type, volume, bounding box, face and edge counts. Check that the \
numbers are the ones you intended. A bore you meant to be through is a \
volume you can compute in advance.
- `print(...)` in the script: its stdout comes back on every result.
- The engine validates the geometry itself and refuses what it cannot build, \
so a result that says ok is a shape that exists — but it is not necessarily \
the shape that was asked for. That part is yours.

WHEN A CALL IS REFUSED, read the failure envelope. `failure_code`, \
`observed` and `retry` say what went wrong and whether trying again could \
help. Fix the script and write again; do not repeat the same call unchanged.

REVISION GUARDS ARE HANDLED FOR YOU. Every tool result reports the revision \
it produced, and the next call is guarded with it automatically. You never \
need to pass expected_revision, and you should not try.

BE DONE WHEN IT IS BUILT. Finish with one short paragraph saying what you \
built and which parameters the caller can now sweep. No preamble, no \
progress narration, no offer to continue.
"""


def system_prompt(api: dict[str, Any]) -> str:
    """The overlay plus the engine's own authoring contract.

    ``api`` is a ``describe_api`` reply. The engine's ``instructions``,
    ``program_schema``, ``source_globals``, ``result_contract`` and
    ``parameters`` prose are pasted in rather than restated, so this file
    never becomes a second, staler copy of the xscript API.
    """

    sections = [CLI_OVERLAY, "THE ENGINE'S OWN AUTHORING CONTRACT", ""]
    schema = str(api.get("program_schema") or "")
    if schema:
        sections.append(f"Program schema: {schema}")
    globals_ = api.get("source_globals")
    if isinstance(globals_, list) and globals_:
        sections.append("Script globals: " + ", ".join(str(g) for g in globals_))
    for key in ("instructions", "result_contract", "revision_rule"):
        text = str(api.get(key) or "").strip()
        if text:
            sections.append(text)
    parameters = api.get("parameters")
    if isinstance(parameters, dict):
        for name in ("params", "num", "values"):
            text = str(parameters.get(name) or "").strip()
            if text:
                sections.append(text)
    return "\n\n".join(section for section in sections if section is not None)


@dataclass
class TurnResult:
    """What one ``claude -p`` turn produced, as the CLI needs to report it."""

    ok: bool = False
    session_id: str = ""
    text: str = ""
    exit_code: int = 0
    error: str = ""
    resume_failed: bool = False
    #: Every stream-json object, kept for tests and for ``--json`` debugging.
    frames: list[dict[str, Any]] = field(default_factory=list)


TextCallback = Callable[[str], None]


class ClaudeTurn:
    """Runs one turn per :meth:`run` call, resuming the same conversation."""

    def __init__(
        self,
        *,
        claude_path: str,
        model: str,
        system_prompt_text: str,
        socket_path: str,
        token: str,
        session_id: str = "",
        on_text: TextCallback | None = None,
        cwd: str | Path | None = None,
    ) -> None:
        self.claude_path = claude_path
        self.model = model
        self.system_prompt_text = system_prompt_text
        self.socket_path = str(socket_path)
        self.token = token
        self.session_id = str(session_id or "")
        self.on_text = on_text
        self._workdir = Path(tempfile.mkdtemp(prefix="cadex-cli-turn-"))
        # Claude Code files a conversation under the directory it ran in, so
        # ``--resume`` only finds one when the turn runs where the last turn
        # ran. A scratch directory per turn silently breaks resume for good
        # (it looks exactly like an expired session), so the caller passes
        # the project root and the conversation is scoped to the project it
        # is about.
        self._cwd = str(cwd or self._workdir)
        self._config_path = self._write_mcp_config()

    def _write_mcp_config(self) -> Path:
        # Spawned by a program we do not control, so it is named as a plain
        # script path rather than as ``-m cadex_cli.mcp``: the shim imports
        # nothing but the standard library precisely so that neither
        # ``sys.path`` nor an inherited ``PYTHONPATH`` has to be right for it
        # to start.
        shim = Path(__file__).resolve().parent / "mcp.py"
        config = {
            "mcpServers": {
                MCP_SERVER_NAME: {
                    "command": _python_executable(),
                    "args": [
                        str(shim),
                        "--socket",
                        self.socket_path,
                        "--token",
                        self.token,
                    ],
                }
            }
        }
        path = self._workdir / "mcp_config.json"
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return path

    def _command(self, prompt: str, *, resume: bool) -> list[str]:
        command = [
            self.claude_path,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.model,
            "--mcp-config",
            str(self._config_path),
            "--strict-mcp-config",
            # No built-in tools: this agent's whole world is the engine. A
            # model that can reach the filesystem here would edit the store
            # behind the engine's back, which is exactly the thing
            # `open_project`'s restore pass exists to catch.
            "--tools",
            "",
            "--system-prompt",
            self.system_prompt_text,
            "--allowedTools",
        ]
        # Enumerated rather than wildcarded: the list is six names and it
        # cannot be mangled by a shell on its way through.
        command.extend(f"mcp__{MCP_SERVER_NAME}__{op}" for op in CLI_TOOL_OPS)
        if resume and self.session_id:
            command.extend(["--resume", self.session_id])
        return command

    def run(self, prompt: str) -> TurnResult:
        """Run the turn, falling back to a fresh conversation if resume fails."""

        resuming = bool(self.session_id)
        result = self._run_once(prompt, resume=resuming)
        if not resuming or result.ok or _model_spoke(result.frames):
            return result
        # The turn failed and the model never said a word, so it never
        # started: the id names a session this machine does not have. (Not
        # "produced no output at all" — Claude Code reports an unknown
        # session id as a perfectly well-formed error result frame, which
        # is output.) Start over rather than report failure.
        stale = self.session_id
        self.session_id = ""
        fresh = self._run_once(prompt, resume=False)
        fresh.resume_failed = True
        if not fresh.error and result.error:
            fresh.error = (
                f"--resume {stale} produced nothing; ran a fresh conversation "
                f"instead ({result.error})"
            )
        return fresh

    def _run_once(self, prompt: str, *, resume: bool) -> TurnResult:
        result = TurnResult()
        try:
            process = subprocess.Popen(
                self._command(prompt, resume=resume),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            result.error = f"Could not start the claude CLI: {exc}"
            result.exit_code = 1
            return result

        assert process.stdout is not None
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                frame = json.loads(line)
            except ValueError:
                continue
            if not isinstance(frame, dict):
                continue
            result.frames.append(frame)
            self._absorb(frame, result)
        process.stdout.close()
        result.exit_code = process.wait()
        stderr = (process.stderr.read() if process.stderr is not None else "") or ""
        if process.stderr is not None:
            process.stderr.close()
        result.ok = result.exit_code == 0 and not _is_error_result(result.frames)
        if not result.ok and not result.error:
            result.error = _turn_error(result, stderr)
        return result

    def _absorb(self, frame: dict[str, Any], result: TurnResult) -> None:
        session_id = frame.get("session_id")
        if isinstance(session_id, str) and session_id:
            result.session_id = session_id
            self.session_id = session_id
        kind = frame.get("type")
        if kind == "assistant":
            message = frame.get("message") or {}
            for block in message.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = str(block.get("text") or "")
                    if text:
                        result.text += text
                        if self.on_text is not None:
                            self.on_text(text)
        elif kind == "result":
            text = frame.get("result")
            if isinstance(text, str) and text and not result.text:
                result.text = text

    def cleanup(self) -> None:
        shutil.rmtree(self._workdir, ignore_errors=True)


def _python_executable() -> str:
    """The interpreter the MCP child should run under.

    ``sys.executable`` when it exists, which under ``pixi run`` is the conda
    environment's python — the one that can already import this package.
    """

    import sys

    return sys.executable or "python3"


def _model_spoke(frames: list[dict[str, Any]]) -> bool:
    """True when the model produced an assistant message — i.e. it ran."""

    return any(frame.get("type") == "assistant" for frame in frames)


def _is_error_result(frames: list[dict[str, Any]]) -> bool:
    for frame in reversed(frames):
        if frame.get("type") == "result":
            return bool(frame.get("is_error"))
    return False


def _turn_error(result: TurnResult, stderr: str) -> str:
    for frame in reversed(result.frames):
        if frame.get("type") == "result" and frame.get("is_error"):
            text = frame.get("result")
            if isinstance(text, str) and text.strip():
                return text.strip()
    tail = "\n".join(stderr.strip().splitlines()[-20:]).strip()
    if tail:
        return tail
    return f"The claude CLI exited with status {result.exit_code}."
