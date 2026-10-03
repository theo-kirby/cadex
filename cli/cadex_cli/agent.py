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

import base64
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .studio import ENGINE_MODULE_DIR
from .tools import BRIDGE_TOOLS, CLI_TOOL_OPS

#: The model a turn spends when nobody has said otherwise. Override with
#: ``--model``, or with ``$CADEX_MODEL`` for a whole machine.
DEFAULT_MODEL = "claude-fable-5"

#: Name the model once for a machine, the way ``$CADEX_PROJECT`` and
#: ``$CADEX_ENGINE_ROOT`` name the other two things a headless run needs.
#: A box whose default model is unavailable -- out of usage credit, not
#: enabled on the account -- otherwise has no way to run ``cadex walk``
#: without a person putting ``--model`` on every command, which is the one
#: thing a lifecycle walk is not allowed to need.
MODEL_ENV = "CADEX_MODEL"


def default_model(project_model: str = "") -> str:
    """Resolve machine, project, then built-in model when no flag was given."""

    return os.environ.get(MODEL_ENV, "").strip() or project_model or DEFAULT_MODEL


#: Every turn is launched at an explicit effort level (ADR-356). On the
#: adaptive-reasoning models the CLI defaults to, effort is Claude Code's
#: documented per-step thinking control; its fixed ``MAX_THINKING_TOKENS``
#: budget is documented as having no effect on them. Pinning the level
#: keeps a headless turn from inheriting whatever an interactive session on
#: the same account last saved. ``high`` is the harness's own default.
EFFORT_ENV = "CADEX_EFFORT"
DEFAULT_EFFORT = "high"
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

#: The hard per-message bound: the request's max output tokens, which caps
#: thinking and text together (ADR-356). The one F4 turn that reached a
#: model spent 16.5 of its 30 minutes on a single 64,000-token thinking
#: message that ended on the provider's cap and produced nothing. 32,000
#: halves that worst case and still leaves a 30 KB script submission room
#: after 20,000 tokens of thinking. Reaches the harness as its documented
#: ``CLAUDE_CODE_MAX_OUTPUT_TOKENS`` variable.
MAX_OUTPUT_TOKENS_ENV = "CADEX_MAX_OUTPUT_TOKENS"
DEFAULT_MAX_OUTPUT_TOKENS = 32000
HARNESS_MAX_OUTPUT_TOKENS_ENV = "CLAUDE_CODE_MAX_OUTPUT_TOKENS"


def default_effort() -> str:
    """The effort level a turn is launched at: ``$CADEX_EFFORT`` or ``high``."""

    level = os.environ.get(EFFORT_ENV, "").strip() or DEFAULT_EFFORT
    if level not in EFFORT_LEVELS:
        raise ValueError(
            f"${EFFORT_ENV}={level!r} is not an effort level; use one of "
            + ", ".join(EFFORT_LEVELS)
        )
    return level


def default_max_output_tokens() -> int:
    """The per-message output cap: ``$CADEX_MAX_OUTPUT_TOKENS`` or 32,000."""

    text = os.environ.get(MAX_OUTPUT_TOKENS_ENV, "").strip()
    if not text:
        return DEFAULT_MAX_OUTPUT_TOKENS
    if not text.isdigit() or int(text) <= 0:
        raise ValueError(
            f"${MAX_OUTPUT_TOKENS_ENV}={text!r} is not a positive token count"
        )
    return int(text)

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


#: The engine's agent guidance (ADR-446): proof by measured facts, the design
#: language, a complete robot, what a policy may read, how a walk is paid.
#: Engine data shared with the shell, read from the engine the CLI resolved.
GUIDANCE_FILE = "CadexAgentGuidance.md"
GUIDANCE_MARKER = "<!-- guidance -->\n"
#: This front end's tool name for each placeholder the guidance uses.
CLI_TOOL_NAMES = {
    "look": "look",
    "inspect": "inspect",
    "write_script": "write_script",
    "edit_script": "edit_script",
    "set_params": "set_params",
    "rebuild": "rebuild",
}


def agent_guidance(module_dir: Path | str, names: dict[str, str]) -> str:
    """The guidance below the marker, with every ``{{placeholder}}`` filled from ``names``."""

    source = Path(module_dir) / GUIDANCE_FILE
    text = source.read_text(encoding="utf-8")
    head, marker, body = text.partition(GUIDANCE_MARKER)
    if not marker:
        raise RuntimeError(f"{source} has no {GUIDANCE_MARKER.strip()} line.")
    for placeholder, name in names.items():
        body = body.replace("{{" + placeholder + "}}", name)
    left = sorted(set(re.findall(r"\{\{(\w+)\}\}", body)))
    if left:
        raise RuntimeError(f"{source} uses placeholders this client does not fill: {left}")
    return body


#: The CLI's own overlay. Written fresh for this front end (the shell's is
#: GPL and says different things anyway — it is talking to a model that has
#: a viewport). Everything about the *API* is left to describe_api, which is
#: appended live; this text is only about the situation.
CLI_OVERLAY = """\
You are the modelling half of Cadex, a CAD application, running headless in \
a terminal. There is no window and no user watching a screen: your caller is \
a person at a shell prompt or a script in a pipeline.

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

PURCHASED HARDWARE: publish each catalog body and place purchased instances \
as separate assembly components with `assembly.component`, separate from \
printed solids. Use `describe_api` for the signatures. Transformed catalog \
bodies may also be clearance cutters; a cutter does not imply another \
purchased part. Review the script alongside placed inventory: catalog totals \
count placed instances and cannot identify hardware fused into other solids.

ALL LENGTHS ARE MILLIMETRES.

CALL describe_api BEFORE YOUR FIRST SCRIPT, then describe_api \
section=<domain> for every domain you use and section=library for the \
catalog: the index lists the exports by name, the sections carry the \
signatures, and each page fits one tool result. Call again whenever you \
need an exact signature. It is served live by the engine you are talking \
to, so it is the truth about this version. Do not write an xscript API \
from memory.

""" + agent_guidance(ENGINE_MODULE_DIR, CLI_TOOL_NAMES) + """\
A FILE THE CALLER HANDS YOU — a trained .cxpolicy and the .json/.xml it \
travels with, a mesh to import, a .cxpart — enters the project through \
put_asset, by path. Its reply carries the stored name and sha256; \
assembly.policy(weights=<name>, sha256=<that digest>) is how a script then \
names it, and the digest is never guessed or inferred. You have no shell. \
The caller has commands of its own for the same legs -- `cadex train --out \
DIR --put`, or `cadex export --out DIR`, the trainer and `cadex asset --put \
walk.cxpolicy` -- and you do not invent flags for any of them. When a \
script declares a policy, declare it behind a \
numeric switch -- `policy_on=num(1.0, min=0.0, max=1.0, step=1.0)` and \
`if p.policy_on >= 0.5:` around assembly.policy, assembly.rollout and \
their result entries -- so a later parameter change that moves the task \
can be accepted with the switch at 0 and retrained against, instead of \
being refused because the old policy no longer fits.

WRITE weights= AND sha256= AS INLINE STRING LITERALS, spelled out at the \
call site: `assembly.policy(task, weights="walk.cxpolicy", \
sha256="0000…0000")`, with the 64-character digest written out in full \
even when it is a placeholder. Factoring either string into a module \
constant (`WEIGHTS = "walk.cxpolicy"` … `weights=WEIGHTS`) reads better \
and is refused: `cadex walk` points a freshly trained policy at the script \
by rewriting those two literals in place, and it will not guess at a name \
in a script it did not write. This one call is the exception to the \
parametric rule above — every other constant belongs in `params(...)`.

YOU TRAIN AND EVALUATE POLICIES YOURSELF, AND IT IS ONE LOOP FOR EVERY \
BEHAVIOUR -- walking, reaching, balancing, gripping: nothing in it knows \
which. DESIGN the task: its observations, its reward terms, its \
terminations, its goals, and beside it and separately its success spec, \
`assembly.task(..., success=assembly.success(...))` -- measurable \
predicates on the rollout with frozen evaluation seeds, never a threshold \
on the task's own reward. When the caller hands you a spec, write it \
exactly as given and never loosen it. TRAIN with train_start: it \
pre-registers one bounded run on the task as accepted now (a name, a \
wall-clock budget, the settings, and your reason) and returns while the \
run trains under a supervisor that outlives your turn; train_status reads \
its progress and can wait for it, train_stop ends it. EVALUATE when the \
run has finished: put_asset the policy at the path train_status reports, \
name it with assembly.policy(task, weights=..., sha256=...) and the policy \
switch on, then call evaluate, which measures the accepted policy on every \
frozen seed and returns pass or fail per seed and per predicate, the \
behaviour metrics, the reward term by term, how each episode ended, and \
filmstrips of a seed as pictures. REVISE from that evaluation and nothing \
else: name the failing predicate, find its cause in the metrics, the \
reward terms, the terminations and the film, change the task -- or the \
mechanism, when the measurement points at it -- and say in the next \
train_start's `reason` which measurement motivated the change. Then train \
and evaluate again, and say whether the change helped. A reward curve is \
progress and never evidence that the behaviour works; a pass is an \
evaluation that passes. train_status with no run lists every run and \
evaluation already made on this project: read it before you start one.

THE PROJECT IS A CODEBASE. Beside the script it keeps ARCHITECTURE.md \
(what it is, what the script declares, where the domain docs are), \
DECISIONS.md (its own ADR log: what was chosen, over what, why) and \
PROGRESS.md (one row per accepted run, with the numbers). They are pasted \
in below when they exist; read them before you act, and do not repeat work \
a row says was already tried. You cannot open files here, so to record a \
decision end your closing paragraph with one line per decision starting \
`DECISION:` -- the CLI lands each one in DECISIONS.md -- and it writes the \
PROGRESS.md row for this run itself. Longer notes belong under docs/, one \
file per subject, and land the same way: a closing line \
`NOTE <subject>: <text>` becomes a dated bullet in docs/<subject>.md. \
Write one whenever the mechanism has actuators or sensors -- \
`NOTE actuators:` for what drives each joint and the torque, speed and \
damping you assumed (docs/actuators.md), `NOTE sensors:` for what each \
sensor measures (docs/sensors.md) -- and for a ratio you chose \
(docs/gear-ratios.md) or an approach you tried and dropped \
(docs/rejected.md). The notes are pasted back on your next visit, \
so write what that turn would need and not what this one can already see. \
docs/inventory.md and docs/clearance.md are the CLI's own reports, not \
note subjects.

REVISION GUARDS ARE HANDLED FOR YOU. Every tool result reports the revision \
it produced, and the next call is guarded with it automatically. You never \
need to pass expected_revision, and you should not try.

BE DONE WHEN IT IS BUILT AND YOU HAVE LOOKED AT IT. Finish with one short \
paragraph saying what you built and which parameters the caller can now \
sweep. No preamble, no \
progress narration, no offer to continue.
"""


def system_prompt(api: dict[str, Any], *, project_docs: str = "") -> str:
    """The overlay plus the engine's own authoring contract.

    ``api`` is a ``describe_api`` reply. The engine's ``instructions``,
    ``program_schema``, ``source_globals``, ``result_contract`` and
    ``parameters`` prose are pasted in rather than restated, so this file
    never becomes a second, staler copy of the xscript API.

    ``project_docs`` is the project's own ``ARCHITECTURE.md``,
    ``DECISIONS.md`` and ``PROGRESS.md`` as one bounded section
    (:func:`cadex_cli.project_docs.read_project_docs`), so the agent reads
    them on every visit without a file tool (ADR-193).
    """

    sections = [CLI_OVERLAY]
    if project_docs.strip():
        sections += ["THIS PROJECT'S OWN DOCS", project_docs.strip()]
    sections += ["THE ENGINE'S OWN AUTHORING CONTRACT", ""]
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


#: What an attached image may be, by its leading bytes rather than its name:
#: the four formats the Messages API reads.
IMAGE_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
#: Bound on one attached image, in bytes: base64 grows it by a third, and
#: the API refuses an image over 5 MB as sent.
IMAGE_LIMIT = 3_750_000
#: Bound on how many images one prompt carries.
IMAGES_PER_TURN = 4


class ImageRefused(ValueError):
    """An attachment that is not an image a turn can carry."""


@dataclass(frozen=True)
class ImageAttachment:
    """One image the owner attached to a prompt (ADR-507)."""

    name: str
    media_type: str
    data: bytes = field(repr=False)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    def summary(self) -> dict[str, Any]:
        """What the envelope records: never the bytes."""

        return {"name": self.name, "media_type": self.media_type,
                "bytes": len(self.data), "sha256": self.sha256}

    def content_block(self) -> dict[str, Any]:
        return {"type": "image", "source": {"type": "base64", "media_type": self.media_type,
                                            "data": base64.b64encode(self.data).decode("ascii")}}


def image_attachment(data: bytes, name: str) -> ImageAttachment:
    """Check ``data`` is a PNG, JPEG, GIF or WebP under the limit; raise :class:`ImageRefused`."""

    label = Path(str(name)).name or "image"
    if not data:
        raise ImageRefused(f"{label} is empty.")
    if len(data) > IMAGE_LIMIT:
        raise ImageRefused(f"{label} is {len(data)} bytes; an attached image is at most {IMAGE_LIMIT}.")
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ImageAttachment(label, "image/webp", bytes(data))
    for signature, media_type in IMAGE_SIGNATURES:
        if data.startswith(signature):
            return ImageAttachment(label, media_type, bytes(data))
    raise ImageRefused(f"{label} is not a PNG, JPEG, GIF or WebP image.")


def read_image(path: str | Path) -> ImageAttachment:
    """:func:`image_attachment` over a file; an unreadable one is refused too."""

    try:
        data = Path(path).expanduser().read_bytes()
    except OSError as exc:
        raise ImageRefused(f"cannot read {path}: {exc.strerror or exc}") from exc
    return image_attachment(data, str(path))


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
        effort: str = "",
        max_output_tokens: int = 0,
    ) -> None:
        self.claude_path = claude_path
        self.model = model
        self.effort = effort or default_effort()
        self.max_output_tokens = int(max_output_tokens or default_max_output_tokens())
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

    def _command(self, prompt: str, *, resume: bool, stream_input: bool = False) -> list[str]:
        # A prompt with images cannot be an argument: it goes in on stdin as
        # one stream-json user message, text block then image blocks
        # (ADR-507). The agent has no file tool to open a path with.
        command = [self.claude_path, "-p"]
        command.extend(["--input-format", "stream-json"] if stream_input else [prompt])
        command += [
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.model,
            "--effort",
            self.effort,
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
        # Enumerated rather than wildcarded: the list is a dozen names and it
        # cannot be mangled by a shell on its way through. The bridge's own
        # tools are in it beside the op-named ones (ADR-464): a tool the
        # model is shown and may not call is a turn that stalls on it.
        command.extend(
            f"mcp__{MCP_SERVER_NAME}__{op}" for op in (*CLI_TOOL_OPS, *BRIDGE_TOOLS))
        if resume and self.session_id:
            command.extend(["--resume", self.session_id])
        return command

    def _environment(self) -> dict[str, str]:
        """The child's environment: ours, plus the per-message output cap."""

        return {**os.environ, HARNESS_MAX_OUTPUT_TOKENS_ENV: str(self.max_output_tokens)}

    def run(self, prompt: str, images: Sequence[ImageAttachment] = ()) -> TurnResult:
        """Run the turn, falling back to a fresh conversation if resume fails."""

        resuming = bool(self.session_id)
        result = self._run_once(prompt, resume=resuming, images=images)
        if not resuming or result.ok or _model_spoke(result.frames):
            return result
        # The turn failed and the model never said a word, so it never
        # started: the id names a session this machine does not have. (Not
        # "produced no output at all" — Claude Code reports an unknown
        # session id as a perfectly well-formed error result frame, which
        # is output.) Start over rather than report failure.
        stale = self.session_id
        self.session_id = ""
        fresh = self._run_once(prompt, resume=False, images=images)
        fresh.resume_failed = True
        if not fresh.error and result.error:
            fresh.error = (
                f"--resume {stale} produced nothing; ran a fresh conversation "
                f"instead ({result.error})"
            )
        return fresh

    def _run_once(self, prompt: str, *, resume: bool,
                  images: Sequence[ImageAttachment] = ()) -> TurnResult:
        result = TurnResult()
        try:
            process = subprocess.Popen(
                self._command(prompt, resume=resume, stream_input=bool(images)),
                stdin=subprocess.PIPE if images else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._cwd,
                env=self._environment(),
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            result.error = f"Could not start the claude CLI: {exc}"
            result.exit_code = 1
            return result

        if images:
            assert process.stdin is not None
            message = {"type": "user", "message": {"role": "user", "content": [
                {"type": "text", "text": prompt}, *(image.content_block() for image in images)]}}
            try:
                process.stdin.write(json.dumps(message) + "\n")
                process.stdin.close()
            except BrokenPipeError:
                pass  # the child is gone; its exit status says why
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
