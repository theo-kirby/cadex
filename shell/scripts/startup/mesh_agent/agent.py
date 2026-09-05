# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Turn orchestration for the Mesh agent.

Threading model: the backend (a `claude -p` subprocess reader, or the mock)
runs in worker threads and pushes stream events onto ``self.events``; the MCP
bridge pushes pending tool calls onto ``self.bridge.requests``. Both queues are
drained on Blender's main thread — via a ``bpy.app.timers`` callback in the
GUI, or an explicit ``drain()`` loop in background mode/tests — because ``bpy``
is not thread-safe. Tool calls execute inside ``drain()`` and their results
unblock the waiting bridge socket thread, which resumes Claude Code.

Undo batching: mutating tool calls are counted per turn and a single
``ed.undo_push`` is issued when the turn finishes, so one Cmd-Z reverts the
whole chat turn.
"""

import os
import queue
import threading
import traceback

from . import history as history_module
from . import modes
from . import tools
from .bridge import BridgeServer

DEFAULT_PROVIDER = "claude"
DEFAULT_MODEL = ""
DEFAULT_CODEX_MODEL = ""
#: "" = pi's own configured default; pi manages its own model catalog.
DEFAULT_PI_MODEL = ""

#: Display names for the provider choices, shared with the preferences UI.
PROVIDER_NAMES = {"claude": "Claude Code", "codex": "Codex", "pi": "pi"}


def provider_from_prefs(prefs):
    """The chosen agent CLI, tolerant of preferences saved before providers."""
    return getattr(prefs, "provider", DEFAULT_PROVIDER) or DEFAULT_PROVIDER


def model_from_prefs(prefs, provider):
    """The chosen model for ``provider``, with per-provider defaults."""
    if provider == "codex":
        attr, default = "codex_model", DEFAULT_CODEX_MODEL
    elif provider == "pi":
        attr, default = "pi_model", DEFAULT_PI_MODEL
    else:
        attr, default = "model", DEFAULT_MODEL
    if prefs is None:
        return default
    return getattr(prefs, attr, default) or default

# Behaviour, and nothing about the API. Every claim this prompt used to make
# about the runtime — `bpy` available, units in meters, a `mesh_model` import
# — described the local execution mode ADR-030 deleted, and the overlay had
# to contradict it line by line. The authoring contract is the engine's, and
# describe_cad_api serves it live (ADR-123).
SYSTEM_PROMPT = """\
You are the Mesh assistant: you build and edit parametric 3D models in a live \
session on behalf of the user. You are their 3D artist and engineer; most \
users never touch a modelling UI themselves, so do the work for them.

The model is defined by a single Python script — the source of truth. You \
never edit the scene directly: you write and evolve the script (write_script, \
edit_script), the model is rebuilt from it, and what you see displayed is \
that rebuild. So the script must be deterministic and self-contained: it \
builds everything it needs and never relies on what a previous run left \
behind.

Declare every dimension or choice the user might want to tweak as a \
parameter at the top of the script. They render as live sliders next to the \
chat, and dragging one re-runs the script. Use them throughout instead of \
literal numbers so the model stays parametric, derive secondary dimensions \
from the primary ones so it scales coherently, and keep parameter ids stable \
across edits — user-set values persist by id. Use set_params to change values \
without touching the code.

Rules:
- Act only through the mcp__mesh__* tools. Call get_script before editing an \
existing model.
- When the user attaches images (marked in their message), view them with \
get_attached_image before building; use them as visual reference.
- +Z is up. Give outputs short meaningful names.
- write_script reports the rebuild result; on failure, fix the script and \
rewrite it. Verify the outcome with scene_summary, or viewport_screenshot \
when a viewport is available, and fix problems you find.
- Keep chat replies to a few short sentences; they render in a narrow panel. \
Describe the model and its new parameters, not the code.
"""


def _default_undo_push(message):
    import bpy
    try:
        bpy.ops.ed.undo_push(message=message)
    except RuntimeError:
        # Undo may be unavailable (e.g. some background configurations).
        pass


def _tag_redraw():
    import bpy
    if bpy.app.background:
        return
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            # TEXT_EDITOR because one of them may be showing the script mirror,
            # which a turn (or a rebuild) rewrites under it.
            if area.type in {'VIEW_3D', 'CADEX_CHAT', 'CADEX_PARAMS',
                             'CADEX_ENV', 'CADEX_POLICY',
                             'CADEX_TRAINING', 'CADEX_LIVE',
                             'CADEX_BLUEPRINT', 'TEXT_EDITOR'}:
                area.tag_redraw()


def get_prefs():
    """The application's AI settings (prefs.py, ADR-183). The name is kept
    from the AddonPreferences era because it is the API every caller and
    the test stubs already speak."""
    from . import prefs
    return prefs.get()


class Agent:
    def __init__(self):
        self.history = history_module.ChatHistory()
        self.events = queue.Queue()
        self.bridge = None
        self.backend = None
        self.busy = False
        self.last_error = ""
        # Image attachments for the session; indices are stable so the model
        # can request any of them across turns via get_attached_image.
        self.attachments = []
        self._sent_attachments = 0
        # Test/injection hooks.
        self.backend_factory = None
        self.tool_cap_override = None
        self._undo_push = _default_undo_push
        self._prompt = ""
        self._tool_calls = 0
        self._mutations = 0
        self._got_result = False
        self._timer_fn = self._timer
        # A tool call whose engine work is still running: (request, Pending).
        # At most one, because the bridge socket thread blocks on the reply,
        # so Claude Code cannot issue a second tool call until this one is
        # answered. Kept as a slot rather than a queue so that invariant is
        # visible rather than assumed.
        self._pending = None
        # Per-turn cancel flag, polled by the cadexd client every 50 ms.
        self._cancel_event = threading.Event()
        # Set once per turn when the model has written a tool call into its
        # prose instead of making one. See _note_imitated_tool_call.
        self._imitated_tool_call = False

    # -- setup -------------------------------------------------------------

    def ensure_bridge(self):
        if self.bridge is None:
            self.bridge = BridgeServer(tools.list_tools)
        return self.bridge

    # -- conversation state, which belongs to the .blend -------------------

    def save_state(self):
        """Persist the transcript and the session id into the .blend."""
        if self.backend is not None:
            self.history.session_id = str(
                getattr(self.backend, "session_id", "") or "")
            self.history.session_provider = str(
                getattr(self.backend, "provider", "") or "")
        self.history.save_to_text_block()

    def _saved_session_for(self, backend):
        """The saved session id, if it belongs to this backend's provider.

        A session id is meaningful only to the CLI that minted it; handing a
        Codex thread id to ``claude --resume`` (or the reverse) buys a resume
        failure at best. Untagged saves predate providers and were all Claude
        Code's; a backend with no provider (the mock, test fakes) adopts
        whatever is saved, as it always has.
        """
        saved = self.history.session_id or None
        if saved is None:
            return None
        saved_provider = self.history.session_provider or DEFAULT_PROVIDER
        backend_provider = getattr(backend, "provider", "")
        if backend_provider and saved_provider != backend_provider:
            return None
        return saved

    def load_state(self):
        """Adopt the newly-opened .blend's conversation.

        The Agent is a process-level singleton, so without this the backend
        keeps the *previous* file's session id and the next turn resumes
        the wrong conversation into the wrong model. Opening a file
        therefore rebinds the session, and a file with no saved session
        starts a fresh one.
        """
        self.history.load_from_text_block()
        if self.backend is not None and hasattr(self.backend, "session_id"):
            self.backend.session_id = self._saved_session_for(self.backend)

    def new_conversation(self):
        """Start a fresh conversation. False if a turn is running.

        Emptying the transcript is not enough on its own. The backend outlives
        the turn and keeps the session id it learned from the stream, so the
        next turn would still pass ``--resume`` and the model would answer
        with everything the user just cleared still in its context. The
        attachments go with it: their indices are what ``get_attached_image``
        takes, and a new conversation starts them again at zero.
        """
        if self.busy:
            return False
        self.history.clear()
        if self.backend is not None and hasattr(self.backend, "session_id"):
            self.backend.session_id = None
        self.attachments = []
        self._sent_attachments = 0
        self.save_state()
        _tag_redraw()
        return True

    def shutdown(self):
        if self.backend is not None:
            self.backend.cancel()
        if self.bridge is not None:
            self.bridge.stop()
            self.bridge = None

    def _make_backend(self):
        import bpy

        bridge = self.ensure_bridge()
        if self.backend_factory is not None:
            return self.backend_factory(bridge)

        if os.environ.get("MESH_AGENT_MOCK"):
            from .mock_backend import MockBackend
            return MockBackend(bridge_port=bridge.port, bridge_token=bridge.token)

        if not bpy.app.online_access:
            self.history.add(
                "status",
                "Online access is disabled. Enable it in Preferences > System > "
                "Network to use the assistant.")
            return None

        prefs = get_prefs()
        provider = provider_from_prefs(prefs)
        model = model_from_prefs(prefs, provider)
        tool_names = [tool["name"] for tool in tools.list_tools()]

        if provider == "codex":
            from .backend import CodexBackend, find_codex
            codex_path = find_codex(
                getattr(prefs, "codex_path", "") if prefs is not None else "")
            if codex_path is None:
                self.history.add(
                    "status",
                    "Codex CLI not found. Install it (npm install -g "
                    "@openai/codex, or https://developers.openai.com/codex) "
                    "or set its path in Settings > AI.")
                return None
            backend = CodexBackend(
                codex_path=codex_path,
                model=model,
                system_prompt=modes.system_prompt(),
                tool_names=tool_names,
                bridge_port=bridge.port,
                bridge_token=bridge.token,
            )
        elif provider == "pi":
            from .backend import PiBackend, find_pi
            pi_path = find_pi(
                getattr(prefs, "pi_path", "") if prefs is not None else "")
            if pi_path is None:
                self.history.add(
                    "status",
                    "pi CLI not found. Install it (npm install -g "
                    "@earendil-works/pi-coding-agent) "
                    "or set its path in Settings > AI.")
                return None
            backend = PiBackend(
                pi_path=pi_path,
                model=model,
                system_prompt=modes.system_prompt(),
                tool_names=tool_names,
                bridge_port=bridge.port,
                bridge_token=bridge.token,
            )
        else:
            from .backend import ClaudeCodeBackend, find_claude
            claude_path = find_claude(
                prefs.claude_path if prefs is not None else "")
            if claude_path is None:
                self.history.add(
                    "status",
                    "Claude Code CLI not found. Install it "
                    "(https://claude.com/claude-code) "
                    "or set its path in Settings > AI.")
                return None
            backend = ClaudeCodeBackend(
                claude_path=claude_path,
                model=model,
                system_prompt=modes.system_prompt(),
                tool_names=tool_names,
                bridge_port=bridge.port,
                bridge_token=bridge.token,
            )
        # A conversation saved in the .blend resumes only into the CLI that
        # minted it; anything else starts fresh.
        backend.session_id = self._saved_session_for(backend)
        return backend

    def _sync_provider(self):
        """Drop the backend when the preferences now name a different CLI.

        Switching providers is a new conversation by construction — one CLI
        cannot resume another's session — so the backend and its session id
        go, while the visible transcript stays. The next turn builds the new
        provider's backend and says so.
        """
        prefs = get_prefs()
        if prefs is None or self.backend is None:
            return
        current = getattr(self.backend, "provider", "")
        wanted = provider_from_prefs(prefs)
        if not current or current == wanted:
            return
        self.backend.cancel()
        self.backend = None
        self.history.session_id = ""
        self.history.session_provider = ""
        self.history.add(
            "status",
            "Assistant: {:s}. It starts a fresh conversation; the transcript "
            "above does not carry over.".format(
                PROVIDER_NAMES.get(wanted, wanted)))

    def _sync_model(self):
        """Adopt the preferences' model before a turn starts. Like the mode,
        the backend rebuilds its argv per turn, so updating ``backend.model``
        in place switches models while the CLI's resume keeps the
        conversation. Backends without a ``model`` attribute (the mock) are
        left alone."""
        prefs = get_prefs()
        if (prefs is None or self.backend is None
                or not hasattr(self.backend, "model")):
            return
        model = model_from_prefs(
            prefs, getattr(self.backend, "provider", DEFAULT_PROVIDER))
        if self.backend.model != model:
            self.backend.model = model
            self.history.add("status",
                             "Model: " + (model or "the provider's default"))

    # -- turn lifecycle ----------------------------------------------------

    def attach_image(self, path):
        """Queue an image for the next turn. Returns its index or -1."""
        if not path or not os.path.isfile(path):
            return -1
        index = len(self.attachments)
        self.attachments.append({"path": path,
                                 "name": os.path.basename(path)})
        self.history.add("status", "Attached image #{:d}: {:s}".format(
            index, os.path.basename(path)))
        _tag_redraw()
        return index

    def pending_attachment_count(self):
        return len(self.attachments) - self._sent_attachments

    def _attachment_note(self):
        """Prompt suffix describing attachments added since the last turn."""
        new = self.attachments[self._sent_attachments:]
        if not new:
            return ""
        lines = ["[The user attached image #{:d} ({:s}); call "
                 "get_attached_image with index={:d} to view it.]".format(
                     self._sent_attachments + offset, item["name"],
                     self._sent_attachments + offset)
                 for offset, item in enumerate(new)]
        self._sent_attachments = len(self.attachments)
        return "\n\n" + "\n".join(lines)

    def start_turn(self, prompt):
        if self.busy:
            return False
        prompt = prompt.strip()
        if not prompt and self.pending_attachment_count() == 0:
            return False
        if not prompt:
            prompt = "See the attached image(s)."

        # The first message is one of the landing screen's exits (ADR-167):
        # a person who starts typing has chosen the chat over the start page.
        try:
            from . import cadex_landing
            cadex_landing.dismiss()
        except Exception:
            pass

        if self.backend_factory is None and not os.environ.get("MESH_AGENT_MOCK"):
            from . import prefs as prefs_module
            prefs = get_prefs()
            if prefs is not None and prefs_module.model_unavailable(prefs):
                self.history.add("status", "The selected model is no longer reported by this harness. "
                                 "Choose a model from the header or use Harness default.")
                _tag_redraw()
                return False

        self.history.add("user", prompt)
        self._sync_provider()
        self._sync_model()

        if self.backend is None:
            self.backend = self._make_backend()
        if self.backend is None:
            _tag_redraw()
            return False

        self._prompt = prompt
        self._tool_calls = 0
        self._mutations = 0
        self._got_result = False
        self._imitated_tool_call = False
        self.last_error = ""
        self._cancel_event.clear()
        self.busy = True
        self.history.begin_assistant()
        # The transcript shows the plain prompt; the model additionally gets
        # notes about freshly attached images and freshly picked BREP pins.
        note = self._attachment_note()
        from . import cadex_pick
        note += cadex_pick.consume_pin_notes()
        # A measured terminal is not a pin (docs/XSCRIPT.md): its own queue,
        # its own wording, drained here so several picks cost one turn
        # rather than one turn each (ADR-067).
        from . import cadex_terminal_pick
        note += cadex_terminal_pick.consume_board_notes()
        note += cadex_terminal_pick.consume_terminal_notes()
        # ...and a wire path the user dragged (ADR-118): the same idiom
        # again, and the third queue drained here.
        from . import cadex_wire_path
        note += cadex_wire_path.consume_wire_path_notes()
        # ...and the sections tagged on the blueprint draft (ADR-178):
        # the fourth queue, same idiom.
        from . import cadex_drawings
        note += cadex_drawings.consume_section_notes()
        self.backend.start_turn(prompt + note, self.events)
        self._ensure_timer()
        _tag_redraw()
        return True

    def cancel(self):
        if not self.busy:
            return
        # Set the flag before killing Claude Code: a modeling request already
        # in flight is cancelled through the protocol (the engine answers
        # RUN_CANCELLED), not left to finish into a dead turn.
        self._cancel_event.set()
        if self.backend is not None:
            self.backend.cancel()
        self.history.add("status", "Cancelled.")

    def cancellation_check(self):
        """Predicate handed to long-running tools; true once cancelled."""
        return self._cancel_event.is_set

    # -- main-thread pump --------------------------------------------------

    def _timer(self):
        try:
            self.drain()
        except Exception:
            traceback.print_exc()
        return 0.1 if self.busy else None

    def _ensure_timer(self):
        import bpy
        if bpy.app.background:
            return
        if not bpy.app.timers.is_registered(self._timer_fn):
            bpy.app.timers.register(self._timer_fn, first_interval=0.05)

    def drain(self):
        """Process pending tool calls and stream events. Main thread only."""
        handled = False

        if self._pending is not None and self._poll_pending():
            handled = True

        # While a tool's engine work is in flight the bridge cannot have sent
        # another call (it blocks on the reply), but leaving the queue alone
        # keeps replies strictly in dispatch order regardless.
        if self._pending is None and self.bridge is not None:
            while True:
                try:
                    request = self.bridge.requests.get_nowait()
                except queue.Empty:
                    break
                handled = True
                self._handle_tool_request(request)

        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            handled = True
            kind = event[0]
            if kind == "stream":
                self._on_stream(event[1])
            elif kind == "error":
                self._finish(error=event[1])
            elif kind == "exit":
                returncode, stderr_tail = event[1], event[2]
                if self.busy and not self._got_result:
                    name = PROVIDER_NAMES.get(
                        getattr(self.backend, "provider", ""), "The assistant")
                    detail = stderr_tail or "exit code {:d}".format(returncode)
                    self._finish(
                        error="{:s} ended unexpectedly: {:s}".format(
                            name, detail))
                elif self.busy:
                    self._finish()

        if handled:
            _tag_redraw()
        return handled

    def _handle_tool_request(self, request):
        # No limit in normal use; tests and the eval harness set
        # tool_cap_override to bound a runaway mock or benchmark turn.
        cap = self.tool_cap_override
        if cap is not None and self._tool_calls >= cap:
            request.reply(
                [{"type": "text",
                  "text": "Tool call limit ({:d}) reached for this turn. "
                          "Summarize progress and stop.".format(cap)}],
                True)
            return
        self._tool_calls += 1
        result = tools.execute(request.tool, request.input, agent=self)
        if isinstance(result, tools.Pending):
            self._pending = (request, result)
            # Background mode has no timer to poll us again, so resolve here.
            # Same code path either way — the poll loop just runs inline.
            import bpy
            if bpy.app.background:
                while not self._poll_pending():
                    pass
            return
        self._settle(request, result)

    def _settle(self, request, result):
        """Reply to one tool call and account for it. Main thread only."""
        content, is_error = result
        if not is_error and request.tool in tools.MUTATING_TOOLS:
            self._mutations += 1
        request.reply(content, is_error)

    def _poll_pending(self):
        """Poll the deferred tool call; True once it has been answered."""
        pending = self._pending
        if pending is None:
            return False
        request, work = pending
        try:
            outcome = work.poll()
        except Exception:
            outcome = ([{"type": "text", "text": traceback.format_exc()}], True)
        if outcome is None:
            return False
        self._pending = None
        self._settle(request, outcome)
        return True

    def _note_imitated_tool_call(self, text):
        """Say so when the model writes a tool call instead of making one.

        A model that has been told it has tools but cannot reach them does not
        say so. It writes the call out as prose -- ``<invoke name="mcp__mesh__
        get_script">`` -- invents a plausible reply to itself, and answers as
        though the work happened. That is indistinguishable from a working turn
        until you look at the model and find it unchanged, which is how ADR-163
        went unnoticed for as long as it did.

        The markup is never legitimate: a real call arrives as a ``tool_use``
        block and never reaches the transcript as text. So one sentence, once
        per turn, naming the likely cause.
        """
        if self._imitated_tool_call or "<invoke name=" not in text:
            return
        self._imitated_tool_call = True
        self.history.end_assistant()
        self.history.add(
            "status",
            "The assistant wrote a tool call as text instead of making one, "
            "which means it cannot reach the Mesh tools. Nothing in this turn "
            "changed the model. Check that the Claude Code CLI still honours "
            "ENABLE_TOOL_SEARCH (mesh_agent/backend.py, ADR-163).")
        self.history.begin_assistant()

    def _on_stream(self, obj):
        obj_type = obj.get("type")
        if obj_type == "stream_event":
            event = obj.get("event", {})
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    self.history.append_stream(delta["text"])
        elif obj_type == "assistant":
            for block in obj.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    self._note_imitated_tool_call(block.get("text", ""))
                if block.get("type") == "tool_use":
                    name = block.get("name", "")
                    short = name.rsplit("__", 1)[-1]
                    self.history.end_assistant()
                    self.history.add("status", "· " + short)
                    self.history.begin_assistant()
        elif obj_type == "result":
            self._got_result = True
            if obj.get("is_error"):
                self.last_error = str(obj.get("result", "unknown error"))

    def _finish(self, error=None):
        if not self.busy:
            return
        # A turn can end (cancel, backend crash) while a tool is still
        # waiting on the engine. Answer it, or the bridge socket thread
        # blocks until its 600 s timeout.
        if self._pending is not None:
            request, work = self._pending
            self._pending = None
            outcome = None
            try:
                outcome = work.poll()
            except Exception:
                pass
            self._settle(request, outcome or (
                [{"type": "text", "text": "The turn ended before this tool "
                                          "finished."}], True))
        self.busy = False
        self.history.end_assistant()
        if error:
            self.last_error = str(error)
        if self.last_error:
            self.history.add("status", "Error: " + self.last_error)
        if self._mutations > 0:
            self._undo_push("Mesh: " + self._prompt[:60])
        try:
            self.save_state()
        except Exception:
            traceback.print_exc()


# Module-level singleton used by the UI.
_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


def shutdown_agent():
    global _agent
    if _agent is not None:
        _agent.shutdown()
        _agent = None
