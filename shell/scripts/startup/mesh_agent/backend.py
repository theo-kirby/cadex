# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Agent-CLI backends: one subprocess per chat turn.

Each backend drives a coding-agent CLI the user is already logged into —
``claude`` (Claude Code), ``codex`` (OpenAI Codex) or ``pi``. The CLI owns
the model loop (streaming, tool orchestration, retries, context management,
auth via the user's existing subscription). Mesh's Blender tools reach it
over the TCP bridge, through one of two transports: an MCP stdio server
(``mcp_shim.py`` — Claude and Codex) or a native pi extension
(``pi_tools.js`` — pi speaks no MCP, and ADR-175 keeps MCP a transport
rather than the architecture). Conversation continuity across turns is the
CLI's own resume mechanism, keyed by a session id the backend learns from
the stream (or mints, for pi).

The event contract is the same for every backend: newline-delimited JSON
objects pushed onto the agent's event queue as ``("stream", obj)``, in Claude
Code's stream-json shapes — the agent understands exactly three of them
(text deltas, ``assistant`` frames carrying ``tool_use`` blocks, and a final
``result``), so a non-Claude backend translates its own stream into those
three rather than teaching the agent a second vocabulary. Process exit pushes
``("exit", returncode, stderr_tail)``.
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid

_CLAUDE_CANDIDATES = (
    "~/.claude/local/claude",
    "/opt/homebrew/bin/claude",
    "/usr/local/bin/claude",
    "/usr/bin/claude",
)

_CODEX_CANDIDATES = (
    "~/.local/bin/codex",
    "~/.codex/bin/codex",
    "/opt/homebrew/bin/codex",
    "/usr/local/bin/codex",
    "/usr/bin/codex",
)

_PI_CANDIDATES = (
    "~/.local/bin/pi",
    "/opt/homebrew/bin/pi",
    "/usr/local/bin/pi",
    "/usr/bin/pi",
)

#: Claude Code defers MCP tool *schemas* behind its built-in ``ToolSearch``
#: tool: only the tool name sits in the model's context, and the schema is
#: fetched on demand. That default is wrong for us in a way that is silent,
#: and it broke every turn until ADR-163.
#:
#: We pass ``--tools ""`` so the agent cannot reach Claude Code's own file and
#: shell tools -- every mutation has to arrive through the Mesh tools, on
#: Blender's main thread. ``ToolSearch`` is one of those built-ins. Disabling
#: the built-in set therefore removes the only key to the deferred Mesh tools,
#: and the model is left holding a list of names it can never open.
#:
#: It does not report that. It writes ``<invoke name="mcp__mesh__get_script">``
#: into the chat as prose, invents a reply, and carries on, so the user reads
#: a turn that looks like work and changed nothing.
#:
#: Turning deferral off makes the Mesh tools resident, which is what they
#: should have been all along: there are ~30 of them, they are the entire tool
#: surface, and the turn cannot start without them. It also costs one round
#: trip less per turn than searching would.
_NO_DEFERRED_TOOLS = {"ENABLE_TOOL_SEARCH": "false"}


def _find_cli(name, candidates, explicit_path=""):
    """Locate an agent CLI binary, or return None."""
    if explicit_path:
        path = os.path.expanduser(explicit_path)
        return path if os.path.exists(path) else None
    found = shutil.which(name)
    if found:
        return found
    # GUI apps on macOS don't inherit the shell PATH; probe common locations.
    for candidate in candidates:
        path = os.path.expanduser(candidate)
        if os.path.exists(path):
            return path
    return None


def find_claude(explicit_path=""):
    """Locate the `claude` CLI binary, or return None."""
    return _find_cli("claude", _CLAUDE_CANDIDATES, explicit_path)


def find_codex(explicit_path=""):
    """Locate the `codex` CLI binary, or return None."""
    return _find_cli("codex", _CODEX_CANDIDATES, explicit_path)


def find_pi(explicit_path=""):
    """Locate the `pi` CLI binary, or return None.

    pi installs as an npm global, so on an nvm machine it lives under a
    per-node-version bin directory that a GUI app's PATH has never heard
    of. The glob probes every installed node version, newest first.
    """
    found = _find_cli("pi", _PI_CANDIDATES, explicit_path)
    if found or explicit_path:
        return found
    candidates = glob.glob(os.path.expanduser("~/.nvm/versions/node/*/bin/pi"))

    def version_key(path):
        name = os.path.basename(os.path.dirname(os.path.dirname(path)))
        try:
            return tuple(int(part) for part in name.lstrip("v").split("."))
        except ValueError:
            return (0,)

    for path in sorted(candidates, key=version_key, reverse=True):
        if os.path.exists(path):
            return path
    return None


class ClaudeCodeBackend:
    is_mock = False
    provider = "claude"

    def __init__(self, claude_path, model, system_prompt, tool_names,
                 bridge_port, bridge_token):
        self.claude_path = claude_path
        self.model = model
        self.system_prompt = system_prompt
        self.tool_names = tool_names  # bare tool names, e.g. "run_python"
        self.bridge_port = bridge_port
        self.bridge_token = bridge_token
        self.session_id = None
        self._process = None
        self._workdir = tempfile.mkdtemp(prefix="mesh_agent_")
        self._mcp_config_path = self._write_mcp_config()

    def _write_mcp_config(self):
        shim = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_shim.py")
        config = {
            "mcpServers": {
                "mesh": {
                    "command": sys.executable,
                    "args": [shim,
                             "--port", str(self.bridge_port),
                             "--token", self.bridge_token],
                },
            },
        }
        path = os.path.join(self._workdir, "mcp_config.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(config, file)
        return path

    def _command(self, prompt):
        command = [
            self.claude_path, "-p", prompt,
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--mcp-config", self._mcp_config_path,
            "--strict-mcp-config",
            # Disable Claude Code's built-in tools; the agent must go through
            # the Mesh tools so every mutation runs on Blender's main thread.
            # This is only safe alongside _NO_DEFERRED_TOOLS -- read it.
            "--tools", "",
            "--system-prompt", self.system_prompt,
            "--allowedTools",
        ]
        command.extend("mcp__mesh__" + name for name in self.tool_names)
        if self.model:
            command.extend(["--model", self.model])
        if self.session_id:
            command.extend(["--resume", self.session_id])
        return command

    def _environment(self):
        """The CLI's environment: ours, plus the tool-deferral switch."""
        environment = dict(os.environ)
        environment.update(_NO_DEFERRED_TOOLS)
        return environment

    def start_turn(self, prompt, events):
        """Spawn `claude -p` for this turn; stream stdout onto `events`."""
        thread = threading.Thread(
            target=self._run_with_resume_fallback, args=(prompt, events),
            daemon=True, name="mesh-agent-claude")
        thread.start()

    def _run_with_resume_fallback(self, prompt, events):
        """Run the turn; if resuming failed, run it once more without.

        A session id saved in a .blend can outlive the Claude Code session
        it names — the file moved to another machine, or the local session
        history was pruned. That must degrade to a fresh conversation, not
        to a dead assistant. The retry is attempted only when resuming was
        in play and the process produced no stream output at all, so a
        turn that genuinely failed is not silently run twice.
        """
        resuming = bool(self.session_id)
        produced = self._run(prompt, events, swallow_exit=resuming)
        if not resuming or produced:
            return
        self.session_id = None
        events.put(("stream", {"type": "system",
                               "subtype": "resume_failed"}))
        self._run(prompt, events)

    def _run(self, prompt, events, swallow_exit=False):
        try:
            process = subprocess.Popen(
                self._command(prompt),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=self._workdir,
                env=self._environment(),
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as ex:
            events.put(("error", "Failed to launch Claude Code: {!s}".format(ex)))
            return False

        self._process = process
        stderr_tail = []
        produced = False

        def read_stderr():
            for line in process.stderr:
                stderr_tail.append(line)
                del stderr_tail[:-40]

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        try:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                session_id = obj.get("session_id")
                if session_id:
                    self.session_id = session_id
                produced = True
                events.put(("stream", obj))
        finally:
            process.stdout.close()
            returncode = process.wait()
            stderr_thread.join(timeout=2.0)
            self._process = None
            # When a failed --resume is about to be retried, the caller owns
            # the turn's outcome; emitting this exit would end it early.
            if not (swallow_exit and not produced):
                events.put(("exit", returncode, "".join(stderr_tail).strip()))
        return produced

    def cancel(self):
        process = self._process
        if process is not None:
            try:
                process.terminate()
            except OSError:
                pass


def _unwrap_codex_error(message):
    """A ``turn.failed`` message is often a JSON API envelope; say the words.

    ``{"type":"error","status":400,"error":{"message":"The 'x' model is not
    supported ..."}}`` becomes the inner sentence. Anything that does not
    parse comes back untouched.
    """
    try:
        data = json.loads(message)
    except (json.JSONDecodeError, ValueError):
        return message
    if not isinstance(data, dict):
        return message
    inner = data.get("error")
    if isinstance(inner, dict) and inner.get("message"):
        return str(inner["message"])
    return str(data.get("message") or message)


class CodexBackend:
    """One ``codex exec --json`` subprocess per chat turn.

    Same seat as :class:`ClaudeCodeBackend`, filled by OpenAI's Codex CLI on
    the user's ChatGPT login. The differences are mechanical, and each one is
    verified against codex-cli 0.142:

    - There is no ``--system-prompt`` flag. Codex reads ``AGENTS.md`` from its
      working root, so the system prompt is written there and the turn runs
      with ``-C <workdir>``.
    - The MCP server arrives as ``-c mcp_servers.mesh.*`` config overrides
      rather than a config file. ``default_tools_approval_mode = "approve"``
      is load-bearing: ``codex exec`` is non-interactive and auto-declines
      any tool call held for approval ("user cancelled MCP tool call"), which
      would silently disarm every Mesh tool. ``enabled_tools`` is the same
      allow-list Claude gets via ``--allowedTools``.
    - Codex's own shell tool cannot be removed, so it runs under
      ``--sandbox read-only``: every mutation still has to arrive through the
      Mesh tools, on Blender's main thread.
    - The prompt is fed on stdin (positional ``-``), so a prompt that starts
      with a dash can never be parsed as a flag.
    - Resume is ``codex exec resume <thread-id>``; the id is learned from the
      ``thread.started`` event.

    Stdout is JSONL in Codex's event vocabulary; :meth:`_translate` maps it
    onto the three Claude-shaped frames the agent understands.
    """

    is_mock = False
    provider = "codex"

    def __init__(self, codex_path, model, system_prompt, tool_names,
                 bridge_port, bridge_token):
        self.codex_path = codex_path
        self.model = model
        self.system_prompt = system_prompt
        self.tool_names = tool_names
        self.bridge_port = bridge_port
        self.bridge_token = bridge_token
        self.session_id = None
        self._process = None
        self._workdir = tempfile.mkdtemp(prefix="mesh_agent_codex_")
        with open(os.path.join(self._workdir, "AGENTS.md"), "w",
                  encoding="utf-8") as file:
            file.write(self.system_prompt)
        # Set per turn: whether any assistant text has streamed yet, so a
        # second agent_message gets a paragraph break in the transcript.
        self._spoke = False

    def _mcp_overrides(self):
        """``-c`` overrides wiring the Mesh MCP shim into this turn.

        Values are parsed as TOML; JSON string/array literals are valid TOML
        values, so ``json.dumps`` produces correctly-escaped ones.
        """
        shim = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "mcp_shim.py")
        args = [shim, "--port", str(self.bridge_port),
                "--token", self.bridge_token]
        return [
            "-c", "mcp_servers.mesh.command=" + json.dumps(sys.executable),
            "-c", "mcp_servers.mesh.args=" + json.dumps(args),
            "-c", 'mcp_servers.mesh.default_tools_approval_mode="approve"',
            "-c", "mcp_servers.mesh.enabled_tools="
                  + json.dumps(list(self.tool_names)),
        ]

    def _command(self):
        # ``exec resume`` accepts fewer flags than ``exec``: no ``-C``, no
        # ``--sandbox``, no ``--color`` — the resumed session keeps its
        # original working root, and the sandbox rides in as a ``-c``
        # override. An unknown flag would not merely be ignored: clap
        # rejects the argv, the turn produces nothing, and the resume
        # fallback silently downgrades every follow-up to a fresh
        # conversation — which is how this was found.
        if self.session_id:
            command = [
                self.codex_path, "exec", "resume", self.session_id,
                "--json",
                "--skip-git-repo-check",
                "-c", 'sandbox_mode="read-only"',
            ]
        else:
            command = [
                self.codex_path, "exec",
                "--json",
                "--skip-git-repo-check",
                "--color", "never",
                "-C", self._workdir,
                "--sandbox", "read-only",
            ]
        if self.model:
            command.extend(["--model", self.model])
        command.extend(self._mcp_overrides())
        command.append("-")  # prompt on stdin
        return command

    def start_turn(self, prompt, events):
        """Spawn `codex exec` for this turn; stream stdout onto `events`."""
        thread = threading.Thread(
            target=self._run_with_resume_fallback, args=(prompt, events),
            daemon=True, name="mesh-agent-codex")
        thread.start()

    def _run_with_resume_fallback(self, prompt, events):
        """Run the turn; if resuming failed, run it once more without.

        Same degradation rule as the Claude backend: a session id saved in a
        .blend can outlive the local session history it names, and that must
        become a fresh conversation, not a dead assistant. The retry happens
        only when resuming was in play and the model never spoke.
        """
        resuming = bool(self.session_id)
        produced = self._run(prompt, events, swallow_exit=resuming)
        if not resuming or produced:
            return
        self.session_id = None
        events.put(("stream", {"type": "system",
                               "subtype": "resume_failed"}))
        self._run(prompt, events)

    def _run(self, prompt, events, swallow_exit=False):
        try:
            process = subprocess.Popen(
                self._command(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                cwd=self._workdir,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as ex:
            events.put(("error", "Failed to launch Codex: {!s}".format(ex)))
            return False

        self._process = process
        self._spoke = False
        stderr_tail = []
        produced = False

        try:
            process.stdin.write(prompt)
            process.stdin.close()
        except OSError:
            pass

        def read_stderr():
            for line in process.stderr:
                stderr_tail.append(line)
                del stderr_tail[:-40]

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        try:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # In swallow mode the caller may still retry without resume;
                # holding back error results until the model has spoken keeps
                # a failed resume from leaving its error in the retried turn.
                if obj.get("type") == "error":
                    # Codex uses top-level errors for retryable trouble too
                    # (the turn may still complete), so this is not the
                    # turn's verdict — but if the process dies on it, the
                    # message is the best diagnostic there is.
                    message = str(obj.get("message") or "")
                    if message:
                        stderr_tail.append(message + "\n")
                    continue
                for frame in self._translate(obj):
                    is_error_result = (frame.get("type") == "result"
                                       and frame.get("is_error"))
                    if is_error_result and swallow_exit and not produced:
                        continue
                    events.put(("stream", frame))
                if obj.get("type") in ("item.started", "item.updated",
                                       "item.completed"):
                    item = obj.get("item") or {}
                    if item.get("type") in ("agent_message", "mcp_tool_call"):
                        produced = True
        finally:
            process.stdout.close()
            returncode = process.wait()
            stderr_thread.join(timeout=2.0)
            self._process = None
            if not (swallow_exit and not produced):
                events.put(("exit", returncode, "".join(stderr_tail).strip()))
        return produced

    def _translate(self, obj):
        """Map one Codex JSONL event onto Claude-shaped frames (or none)."""
        kind = obj.get("type")
        if kind == "thread.started":
            thread_id = obj.get("thread_id")
            if thread_id:
                self.session_id = thread_id
            return []
        if kind in ("item.started", "item.completed"):
            item = obj.get("item") or {}
            item_type = item.get("type")
            if kind == "item.completed" and item_type == "agent_message":
                text = str(item.get("text") or "")
                if not text:
                    return []
                if self._spoke:
                    text = "\n\n" + text
                self._spoke = True
                return [_text_delta_frame(text)]
            if kind == "item.started" and item_type == "mcp_tool_call":
                name = str(item.get("tool") or "")
                if name:
                    return [{"type": "assistant",
                             "message": {"content": [{"type": "tool_use",
                                                      "name": name}]}}]
            return []
        if kind == "turn.completed":
            return [{"type": "result", "is_error": False}]
        if kind == "turn.failed":
            error = obj.get("error") or {}
            message = _unwrap_codex_error(str(error.get("message")
                                              or "unknown error"))
            return [{"type": "result", "is_error": True, "result": message}]
        return []

    def cancel(self):
        process = self._process
        if process is not None:
            try:
                process.terminate()
            except OSError:
                pass


def _text_delta_frame(text):
    """A Claude-shaped streaming text delta — the frame the agent appends."""
    return {"type": "stream_event",
            "event": {"type": "content_block_delta",
                      "delta": {"type": "text_delta", "text": text}}}


class PiBackend:
    """One ``pi -p --mode json`` subprocess per chat turn.

    Same seat again, filled by the pi coding agent — and the proof that MCP
    is a transport, not the architecture (ADR-175): pi does not speak MCP by
    design, so the Mesh tools reach it through ``pi_tools.js``, a pi
    extension that registers them natively and relays each call to the same
    TCP bridge the MCP shim uses. The differences, each verified against
    pi 0.84.4:

    - Tools: ``--no-builtin-tools`` removes pi's own read/bash/edit/write
      (the ADR-163 posture — every mutation arrives through the bridge, on
      Blender's main thread), and ``-e pi_tools.js`` adds exactly the
      bridge's tools. The extension learns the bridge's address from
      MESH_BRIDGE_PORT / MESH_BRIDGE_TOKEN because pi has no per-extension
      argv. ``--no-extensions`` / ``--no-skills`` / ``--no-context-files`` /
      ``--no-prompt-templates`` keep the user's own pi setup out of the
      product's turns.
    - Sessions: pi takes an explicit ``--session-id`` and *creates a missing
      one fresh*, so this backend mints a UUID and there is no resume
      fallback to need — a stale id degrades to a new conversation inside
      pi itself. ``--session-dir`` pins storage to one stable place.
    - Model: pi is multi-provider with its own catalog and defaults, so
      ``model`` here is a free pattern ("provider/id" works) and "" means
      pi's own configured default.
    - pi is an npm global with a ``#!/usr/bin/env node`` shebang, so the
      subprocess PATH is prefixed with pi's own directory — under nvm that
      is the only place ``node`` is.

    Stdout is JSONL (``--mode json``); :meth:`_translate` maps it onto the
    three Claude-shaped frames the agent understands. Thinking deltas are
    deliberately dropped — the transcript shows answers, not reasoning.
    """

    is_mock = False
    provider = "pi"

    def __init__(self, pi_path, model, system_prompt, tool_names,
                 bridge_port, bridge_token):
        self.pi_path = pi_path
        self.model = model
        self.system_prompt = system_prompt
        self.tool_names = tool_names  # informational; the extension serves
        self.bridge_port = bridge_port  # exactly the bridge's tool list
        self.bridge_token = bridge_token
        self.session_id = None
        self._process = None
        self._workdir = tempfile.mkdtemp(prefix="mesh_agent_pi_")
        self._session_dir = os.path.expanduser("~/.pi/agent/cadex-sessions")
        # Per-turn translation state.
        self._spoke = False
        self._error = ""
        self._saw_end = False
        self._result_emitted = False

    def _extension_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "pi_tools.js")

    def _command(self, prompt):
        if not self.session_id:
            # pi creates a missing session id fresh, so minting one here is
            # both the first turn and the stale-id degradation path.
            self.session_id = str(uuid.uuid4())
        command = [
            self.pi_path, "-p",
            "--mode", "json",
            "--no-builtin-tools",
            "--no-extensions",
            "--no-skills",
            "--no-context-files",
            "--no-prompt-templates",
            "-e", self._extension_path(),
            "--system-prompt", self.system_prompt,
            "--session-dir", self._session_dir,
            "--session-id", self.session_id,
        ]
        if self.model:
            command.extend(["--model", self.model])
        command.extend(["--", prompt])
        return command

    def _environment(self):
        environment = dict(os.environ)
        environment["MESH_BRIDGE_PORT"] = str(self.bridge_port)
        environment["MESH_BRIDGE_TOKEN"] = self.bridge_token
        environment["PATH"] = (os.path.dirname(self.pi_path) + os.pathsep
                               + environment.get("PATH", ""))
        return environment

    def start_turn(self, prompt, events):
        """Spawn `pi -p` for this turn; stream stdout onto `events`."""
        thread = threading.Thread(
            target=self._run, args=(prompt, events),
            daemon=True, name="mesh-agent-pi")
        thread.start()

    def _run(self, prompt, events):
        try:
            process = subprocess.Popen(
                self._command(prompt),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=self._workdir,
                env=self._environment(),
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as ex:
            events.put(("error", "Failed to launch pi: {!s}".format(ex)))
            return False

        self._process = process
        self._spoke = False
        self._error = ""
        self._saw_end = False
        self._result_emitted = False
        stderr_tail = []

        def read_stderr():
            for line in process.stderr:
                stderr_tail.append(line)
                del stderr_tail[:-40]

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        try:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for frame in self._translate(obj):
                    events.put(("stream", frame))
        finally:
            process.stdout.close()
            returncode = process.wait()
            stderr_thread.join(timeout=2.0)
            self._process = None
            # ``agent_settled`` carries the verdict; a run that ended
            # cleanly without one (an older pi, say) still deserves an ok
            # result rather than a false "ended unexpectedly".
            if (not self._result_emitted and self._saw_end
                    and returncode == 0):
                events.put(("stream", {"type": "result",
                                       "is_error": bool(self._error),
                                       "result": self._error}))
            events.put(("exit", returncode, "".join(stderr_tail).strip()))
        return True

    def _translate(self, obj):
        """Map one pi JSONL event onto Claude-shaped frames (or none)."""
        kind = obj.get("type")
        if kind == "session":
            session_id = obj.get("id")
            if session_id:
                self.session_id = session_id
            return []
        if kind == "message_update":
            event = obj.get("assistantMessageEvent") or {}
            event_type = event.get("type")
            if event_type == "text_delta":
                delta = str(event.get("delta") or "")
                if not delta:
                    return []
                self._spoke = True
                return [_text_delta_frame(delta)]
            if event_type == "text_start" and self._spoke:
                return [_text_delta_frame("\n\n")]
            return []
        if kind == "tool_execution_start":
            name = str(obj.get("toolName") or "")
            if name:
                return [{"type": "assistant",
                         "message": {"content": [{"type": "tool_use",
                                                  "name": name}]}}]
            return []
        if kind == "message_end":
            message = obj.get("message") or {}
            if (message.get("role") == "assistant"
                    and message.get("stopReason") == "error"):
                self._error = str(message.get("errorMessage")
                                  or "unknown error")
            return []
        if kind == "agent_end":
            self._saw_end = True
            return []
        if kind == "agent_settled":
            self._saw_end = True
            self._result_emitted = True
            return [{"type": "result", "is_error": bool(self._error),
                     "result": self._error}]
        return []

    def cancel(self):
        process = self._process
        if process is not None:
            try:
                process.terminate()
            except OSError:
                pass
