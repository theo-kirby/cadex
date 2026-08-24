# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Claude Code backend: runs one `claude -p` subprocess per chat turn.

Claude Code owns the model loop (streaming, tool orchestration, retries,
context management, auth via the user's existing login). Mesh's Blender tools
are exposed to it as an MCP server (``mcp_shim.py``) that relays calls back
into Blender through the TCP bridge. Conversation continuity across turns uses
``--resume <session-id>``.

Stdout is ``--output-format stream-json``: newline-delimited JSON objects,
pushed onto the agent's event queue as ``("stream", obj)``. Process exit pushes
``("exit", returncode, stderr_tail)``.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

_CLAUDE_CANDIDATES = (
    "~/.claude/local/claude",
    "/opt/homebrew/bin/claude",
    "/usr/local/bin/claude",
    "/usr/bin/claude",
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


def find_claude(explicit_path=""):
    """Locate the `claude` CLI binary, or return None."""
    if explicit_path:
        path = os.path.expanduser(explicit_path)
        return path if os.path.exists(path) else None
    found = shutil.which("claude")
    if found:
        return found
    # GUI apps on macOS don't inherit the shell PATH; probe common locations.
    for candidate in _CLAUDE_CANDIDATES:
        path = os.path.expanduser(candidate)
        if os.path.exists(path):
            return path
    return None


class ClaudeCodeBackend:
    is_mock = False

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
            "--model", self.model,
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
