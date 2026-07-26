# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Headless tests for the Mesh agent add-on.

Run:
    blender --background --factory-startup --python tests/python/bl_mesh_agent.py

Uses the mock backend (no network, no `claude` needed) but exercises the real
TCP bridge and the real MCP shim subprocess. Set MESH_AGENT_LIVE=1 to also run
one live end-to-end turn through `claude -p` (requires a logged-in Claude Code
install; makes a real API call).

Scope note (ADR-030): this suite covers the agent loop, the bridge, the MCP
shim, transcript persistence and engine discovery -- everything that does not
need a running engine. Four tests that drove the *local* bpy model path
(script -> exec() -> scene -> sliders) went with that path. What they proved
that still matters -- one undo push per turn, a rejected script reported as an
error, parameters surviving save and load -- is proved against the real engine
in bl_mesh_agent_cadex.py, which is the suite that speaks for the product.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time

import bpy

# Make the repo's add-on importable regardless of which Blender runs this.
_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import mesh_agent  # noqa: E402
from mesh_agent import agent as agent_module  # noqa: E402
from mesh_agent import history as history_module  # noqa: E402
from mesh_agent import model as model_module  # noqa: E402
from mesh_agent.mock_backend import MockBackend  # noqa: E402

FAILURES = []


def check(condition, label):
    status = "ok" if condition else "FAIL"
    print("  {:s}: {:s}".format(status, label))
    if not condition:
        FAILURES.append(label)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def run_turn(agent, prompt, timeout=30.0):
    """Drive one turn synchronously, draining on this (main) thread."""
    started = agent.start_turn(prompt)
    deadline = time.monotonic() + timeout
    while agent.busy and time.monotonic() < deadline:
        agent.drain()
        time.sleep(0.01)
    return started and not agent.busy


def make_agent(script, tool_cap=None):
    agent = agent_module.Agent()
    agent.tool_cap_override = tool_cap
    holder = {}

    def factory(bridge):
        backend = MockBackend(script=script, bridge_port=bridge.port,
                              bridge_token=bridge.token)
        holder["backend"] = backend
        return backend

    agent.backend_factory = factory
    undo_pushes = []
    agent._undo_push = undo_pushes.append
    return agent, holder, undo_pushes


def test_image_attachment_roundtrip():
    """An attached image must reach the model through get_attached_image."""
    print("test_image_attachment_roundtrip")
    reset_scene()

    path = os.path.join(tempfile.gettempdir(), "mesh_test_attach.png")
    image = bpy.data.images.new("mesh_test_attach", 16, 16)
    image.filepath_raw = path
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)

    script = [[
        ("tool", "get_attached_image", {"index": 0}),
        ("tool", "get_attached_image", {"index": 5}),
        ("text", "Nice reference."),
        ("result", False, "Nice reference."),
    ]]
    agent, holder, undo_pushes = make_agent(script)
    try:
        index = agent.attach_image(path)
        check(index == 0, "attachment registered with index 0")
        check(agent.pending_attachment_count() == 1, "attachment pending")
        check(run_turn(agent, "model this"), "turn completes")
        check(agent.pending_attachment_count() == 0,
              "attachment marked sent with the turn")

        prompt = holder["backend"].prompts[0]
        check("index=0" in prompt and "mesh_test_attach.png" in prompt,
              "prompt tells the model about the attachment")
        good_reply = holder["backend"].tool_results[0][1]
        check(good_reply["is_error"] is False
              and good_reply["content"][0]["type"] == "image"
              and len(good_reply["content"][0]["data"]) > 100,
              "image content block returned to the model")
        bad_reply = holder["backend"].tool_results[1][1]
        check(bad_reply["is_error"] is True, "out-of-range index rejected")
        check(len(undo_pushes) == 0, "viewing an image is not a mutation")
    finally:
        agent.shutdown()
        if os.path.exists(path):
            os.remove(path)


def test_tool_call_cap():
    print("test_tool_call_cap")
    reset_scene()
    script = [[
        ("tool", "scene_summary", {}),
        ("tool", "scene_summary", {}),
        ("result", False, "done"),
    ]]
    agent, holder, _undo = make_agent(script, tool_cap=1)
    try:
        check(run_turn(agent, "spam tools"), "turn completes")
        results = holder["backend"].tool_results
        check(results[0][1]["is_error"] is False, "first call allowed")
        check(results[1][1]["is_error"] is True
              and "limit" in results[1][1]["content"][0]["text"],
              "second call rejected by per-turn cap")
    finally:
        agent.shutdown()


def test_transcript_persistence():
    print("test_transcript_persistence")
    reset_scene()
    script = [[("text", "Hello from mock."), ("result", False, "Hello from mock.")]]
    agent, _holder, _undo = make_agent(script)
    try:
        check(run_turn(agent, "say hello"), "turn completes")
        text_block = bpy.data.texts.get(history_module.TEXT_BLOCK_NAME)
        check(text_block is not None, "transcript text block exists")
        data = json.loads(text_block.as_string())
        check(data.get("schema") == history_module.SCHEMA,
              "transcript carries its schema")
        check("session_id" in data,
              "transcript carries the Claude session id")
        messages = data["messages"]
        check(messages[0]["role"] == "user"
              and messages[0]["text"] == "say hello",
              "user prompt persisted")
        check(any(item["role"] == "assistant"
                  and "Hello from mock." in item["text"]
                  for item in messages),
              "assistant reply persisted")

        fresh = history_module.ChatHistory()
        fresh.load_from_text_block()
        check(len(fresh.messages) == len(agent.history.messages),
              "transcript round-trips through the text block")
    finally:
        agent.shutdown()


def test_bridge_chunked_request():
    """The bridge must tolerate requests arriving in tiny TCP fragments."""
    print("test_bridge_chunked_request")
    agent = agent_module.Agent()
    bridge = agent.ensure_bridge()
    try:
        payload = json.dumps({"op": "list_tools", "token": bridge.token}).encode() + b"\n"
        with socket.create_connection(("127.0.0.1", bridge.port), timeout=10) as sock:
            for i in range(0, len(payload), 3):
                sock.sendall(payload[i:i + 3])
                time.sleep(0.001)
            buf = b""
            while not buf.endswith(b"\n"):
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
        reply = json.loads(buf)
        names = [tool["name"] for tool in reply["tools"]]
        check("write_script" in names and "scene_summary" in names,
              "tool list served over fragmented request")
        check("run_python" not in names,
              "direct-mutation tools are gone from the tool list")
    finally:
        agent.shutdown()


def test_mcp_shim_protocol():
    """Speak real MCP (JSON-RPC over stdio) to the shim subprocess."""
    print("test_mcp_shim_protocol")
    reset_scene()
    agent = agent_module.Agent()
    bridge = agent.ensure_bridge()
    shim = os.path.join(_REPO, "scripts", "addons_core", "mesh_agent", "mcp_shim.py")
    process = subprocess.Popen(
        [sys.executable, shim, "--port", str(bridge.port), "--token", bridge.token],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    responses = {}
    responses_lock = threading.Condition()

    def reader():
        for line in process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            with responses_lock:
                responses[message.get("id")] = message
                responses_lock.notify_all()

    threading.Thread(target=reader, daemon=True).start()

    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    def wait_for(msg_id, timeout=15.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            agent.drain()  # execute any pending tool calls on this thread
            with responses_lock:
                if msg_id in responses:
                    return responses.pop(msg_id)
            time.sleep(0.01)
        return None

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                         "clientInfo": {"name": "test", "version": "0"}}})
        init = wait_for(1)
        check(init is not None and init["result"]["serverInfo"]["name"] == "mesh",
              "initialize handshake")
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools_reply = wait_for(2)
        names = [tool["name"] for tool in tools_reply["result"]["tools"]]
        check("write_script" in names, "tools/list relayed from Blender")

        # focus_view rather than write_script: this test is about the MCP
        # round trip, and every modelling tool now needs a running engine
        # (ADR-030) which this suite deliberately does not have. The reply
        # text is proof enough that the call landed inside Blender -- only
        # code with `bpy` can read bpy.app.background, and the shim
        # subprocess has no bpy at all.
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "focus_view", "arguments": {}}})
        call_reply = wait_for(3)
        check(call_reply is not None
              and call_reply["result"]["isError"] is False,
              "tools/call round-trips shim -> bridge -> main thread -> shim")
        check(call_reply is not None
              and "background mode" in call_reply["result"]["content"][0]["text"],
              "the reply was produced by bpy on the Blender main thread")
    finally:
        process.stdin.close()
        process.terminate()
        agent.shutdown()


def test_live_claude_turn():
    """Optional: one real `claude -p` turn (MESH_AGENT_LIVE=1)."""
    print("test_live_claude_turn")
    from mesh_agent import tools as tools_module
    from mesh_agent.backend import ClaudeCodeBackend, find_claude

    claude_path = find_claude()
    check(claude_path is not None, "claude CLI found")
    if claude_path is None:
        return

    reset_scene()
    agent = agent_module.Agent()

    def factory(bridge):
        return ClaudeCodeBackend(
            claude_path=claude_path,
            model="claude-haiku-4-5",
            system_prompt=agent_module.SYSTEM_PROMPT,
            tool_names=[tool["name"] for tool in tools_module.list_tools()],
            bridge_port=bridge.port,
            bridge_token=bridge.token,
        )

    agent.backend_factory = factory
    undo_pushes = []
    agent._undo_push = undo_pushes.append
    try:
        completed = run_turn(
            agent,
            "Write a model script that builds a single cube named LiveTestCube "
            "at the origin, with a Float parameter `width` (default 2, min 0.5, "
            "max 5) controlling its width. Then verify with scene_summary and "
            "reply with one short sentence.",
            timeout=240.0)
        check(completed, "live turn completes")
        check("LiveTestCube" in bpy.data.objects, "live agent created the cube")
        specs = model_module.load_specs(bpy.context.scene)
        check(any(spec["id"] == "width" for spec in specs),
              "live agent declared the width parameter")
        check(not agent.last_error, "no backend error ({:s})".format(agent.last_error))
        check(len(undo_pushes) == 1, "one undo push for the live turn")
    finally:
        agent.shutdown()


# -- cadex engine discovery (no engine, no Blender-side state) --------------

def _fake_engine(root, binary_rel, module_rel, manifest=True):
    """Build a fake engine layout in ``root``; returns the binary path."""
    binary = os.path.join(root, *binary_rel)
    os.makedirs(os.path.dirname(binary), exist_ok=True)
    with open(binary, "w", encoding="utf-8") as handle:
        handle.write("#!/bin/sh\nexit 0\n")
    os.chmod(binary, 0o755)
    os.makedirs(os.path.join(root, *module_rel), exist_ok=True)
    if manifest:
        with open(os.path.join(root, "cadex-engine.json"), "w",
                  encoding="utf-8") as handle:
            json.dump({
                "schema": "cadex-engine-v1",
                "version": "0.0.2",
                "protocol": "cadex-cadexd-v1",
                "freecadcmd": "/".join(binary_rel),
                "module_dir": "/".join(module_rel),
            }, handle)
    return binary


def test_cadex_engine_discovery():
    """The discovery matrix: three real-world layouts, all found.

    cadexd_client is deliberately bpy-free, so this runs without Blender
    state, without an engine, and without the cadex repo.
    """
    print("test_cadex_engine_discovery")
    from mesh_agent import cadexd_client

    for name in ("MESH_FREECADCMD", "MESH_CADEXD_MODULE", "MESH_CADEX_ENGINE"):
        os.environ.pop(name, None)

    # 1. Unix install: <prefix>/bin/FreeCADCmd + <prefix>/Mod/cadex.
    unix = tempfile.mkdtemp(prefix="fake-engine-unix-")
    unix_binary = _fake_engine(unix, ("bin", "FreeCADCmd"), ("Mod", "cadex"),
                               manifest=False)
    check(cadexd_client.find_freecadcmd(unix_binary) == unix_binary,
          "explicit path wins")
    check(cadexd_client.cadexd_module_dir(unix_binary)
          == os.path.join(unix, "Mod", "cadex"),
          "unix layout: Mod/cadex beside bin/")

    # 2. Windows root layout: <root>/freecadcmd + <root>/Mod/cadex, i.e. the
    #    module dir is beside the BINARY, not beside its parent.
    win = tempfile.mkdtemp(prefix="fake-engine-win-")
    win_binary = _fake_engine(win, ("freecadcmd",), ("Mod", "cadex"),
                              manifest=False)
    check(cadexd_client.cadexd_module_dir(win_binary)
          == os.path.join(win, "Mod", "cadex"),
          "windows root layout: Mod/cadex beside the binary")

    # 3. Bundled payload found by manifest alone (cadex ADR-020) — the
    #    layout is never guessed at, it is read.
    bundle = tempfile.mkdtemp(prefix="fake-engine-bundle-")
    bundle_binary = _fake_engine(bundle, ("bin", "freecadcmd"),
                                 ("Mod", "cadex"))
    found = cadexd_client.find_freecadcmd("", (bundle,))
    check(found == bundle_binary, "bundled manifest supplies the binary")
    check(cadexd_client.cadexd_module_dir(found, (bundle,))
          == os.path.join(bundle, "Mod", "cadex"),
          "bundled manifest supplies the module dir")
    ok, reason, remedy = cadexd_client.preflight("", (bundle,))
    check(ok and not reason and not remedy, "preflight green on the bundle")

    # A manifest for a protocol this client does not speak is refused,
    # not guessed at.
    with open(os.path.join(bundle, "cadex-engine.json"), "w",
              encoding="utf-8") as handle:
        json.dump({"schema": "cadex-engine-v1", "version": "9.9.9",
                   "protocol": "cadex-cadexd-v99",
                   "freecadcmd": "bin/freecadcmd",
                   "module_dir": "Mod/cadex"}, handle)
    check(cadexd_client.read_engine_manifest(bundle) is None,
          "manifest with an unknown protocol is refused")

    # Nothing anywhere: preflight explains itself instead of raising.
    empty = tempfile.mkdtemp(prefix="fake-engine-empty-")
    os.environ["MESH_CADEXD_MODULE"] = ""
    ok, reason, remedy = cadexd_client.preflight(
        os.path.join(empty, "nope"), (empty,))
    check(not ok and reason and remedy, "preflight reports reason and remedy")

    # Binary but no module: the second, distinct failure.
    lone = tempfile.mkdtemp(prefix="fake-engine-lone-")
    lone_binary = _fake_engine(lone, ("bin", "FreeCADCmd"), ("unused",),
                               manifest=False)
    ok, reason, _remedy = cadexd_client.preflight(lone_binary, ())
    check(not ok and "module" in reason,
          "binary without the module reports the module problem")

    import shutil
    for path in (unix, win, bundle, empty, lone):
        shutil.rmtree(path, ignore_errors=True)



# -- cadex engine budgets (fake cadexd; no engine needed) -------------------

_FAKE_CADEXD = r"""
import json, sys
record = sys.argv[1]
sys.stdout.write(json.dumps({"id": None, "event": {"event": "ready"}}) + "\n")
sys.stdout.flush()
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    frame = json.loads(line)
    with open(record, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    if frame.get("op") == "shutdown":
        sys.stdout.write(json.dumps({"id": frame["id"], "ok": True}) + "\n")
        sys.stdout.flush()
        break
    sys.stdout.write(json.dumps({"id": frame["id"], "ok": True,
                                 "script": {}}) + "\n")
    sys.stdout.flush()
"""


def test_cadex_budgets_reach_open_project():
    """Budgets ride open_project, and changing them respawns the child.

    Budgets are sent exactly once per child, so a client reused across a
    preference change would keep the old numbers forever -- the bug this
    covers.
    """
    print("test_cadex_budgets_reach_open_project")
    from mesh_agent import cadexd_client

    workdir = tempfile.mkdtemp(prefix="fake-cadexd-")
    fake = os.path.join(workdir, "fake_cadexd.py")
    with open(fake, "w", encoding="utf-8") as handle:
        handle.write(_FAKE_CADEXD)
    record = os.path.join(workdir, "frames.jsonl")
    command = [sys.executable, fake, record]
    root = os.path.join(workdir, "project")

    def frames():
        if not os.path.isfile(record):
            return []
        with open(record, "r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    try:
        budgets = {"timeout_seconds": 42.0, "memory_limit_mb": 512}
        client = cadexd_client.client_for(root, command, budgets=budgets)
        reply = client.request("inspect", {"scope": "script"})
        check(reply.get("ok") is True, "fake cadexd answered")
        opens = [f for f in frames() if f.get("op") == "open_project"]
        check(len(opens) == 1, "one open_project frame")
        check(opens and opens[0]["args"].get("budgets") == budgets,
              "open_project carries the budgets: {!r}".format(
                  opens[0]["args"].get("budgets") if opens else None))

        # Same budgets -> same child.
        again = cadexd_client.client_for(root, command, budgets=budgets)
        check(again is client, "unchanged budgets reuse the child")

        # Changed budgets -> respawn, and the new numbers are sent.
        changed = {"timeout_seconds": 99.0, "memory_limit_mb": 1024}
        third = cadexd_client.client_for(root, command, budgets=changed)
        check(third is not client, "changed budgets respawn the child")
        third.request("inspect", {"scope": "script"})
        opens = [f for f in frames() if f.get("op") == "open_project"]
        check(len(opens) == 2, "second open_project after the budget change")
        check(opens[-1]["args"].get("budgets") == changed,
              "the new budgets reached the engine")
    finally:
        cadexd_client.close_all()
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)



# -- the cadex overlay must not restate the engine's API --------------------

def test_cadex_overlay_carries_no_api_names():
    """The system prompt describes behavior; the engine describes its API.

    A hand-written API listing in the prompt is a copy of the engine's
    truth that nothing keeps in sync — the drift class describe_cad_api
    exists to kill. This guardrail is the thing that keeps it dead.
    """
    print("test_cadex_overlay_carries_no_api_names")
    import re
    from mesh_agent import modes, tools

    overlay = modes.CADEX_OVERLAY
    leaked = re.findall(
        r"\b(?:part|mesh|assembly|partdesign|sketcher)\.[A-Za-z_]+",
        overlay)
    check(not leaked,
          "no xscript API names in CADEX_OVERLAY (found: {!r})".format(
              sorted(set(leaked))))
    check("params(" not in overlay and "result =" not in overlay,
          "no script skeleton in CADEX_OVERLAY either")
    check(len(overlay) < 2500,
          "CADEX_OVERLAY stays small ({:d} chars)".format(len(overlay)))
    check("describe_cad_api" in overlay,
          "the overlay points at describe_cad_api instead")
    names = [tool["name"] for tool in tools.list_tools()]
    check("describe_cad_api" in names, "describe_cad_api is served to Claude")



# -- conversation state lives in the .blend ---------------------------------

def test_session_id_round_trips_and_is_per_file():
    """The transcript and the Claude session id belong to the .blend.

    The Agent is a process-level singleton, so before M8 opening a second
    file kept the first file's session id and the next turn resumed the
    wrong conversation.
    """
    print("test_session_id_round_trips_and_is_per_file")
    from mesh_agent import agent as agent_module

    workdir = tempfile.mkdtemp(prefix="mesh-session-")
    first = os.path.join(workdir, "one.blend")
    second = os.path.join(workdir, "two.blend")

    class _FakeBackend:
        def __init__(self, session_id=None):
            self.session_id = session_id
            self.system_prompt = ""
            self.model = ""

        def cancel(self):
            pass

    agent = agent_module.get_agent()
    try:
        # File one: a conversation with a session id.
        bpy.ops.wm.read_homefile(use_empty=True)
        agent.history.clear()
        agent.backend = _FakeBackend("session-one")
        agent.history.add("user", "make a bracket")
        agent.history.add("assistant", "Done.")
        agent.save_state()
        bpy.ops.wm.save_as_mainfile(filepath=first)

        # File two: its own conversation, its own session.
        bpy.ops.wm.read_homefile(use_empty=True)
        agent.load_state()
        check(agent.history.session_id == "",
              "a fresh file starts with no session: {!r}".format(
                  agent.history.session_id))
        check(agent.backend.session_id is None,
              "the backend was rebound to a fresh session")
        agent.backend = _FakeBackend("session-two")
        agent.history.add("user", "make a gear")
        agent.save_state()
        bpy.ops.wm.save_as_mainfile(filepath=second)

        # Reopen file one: its own transcript and its own session return.
        bpy.ops.wm.open_mainfile(filepath=first)
        agent.load_state()
        check(agent.history.session_id == "session-one",
              "file one resumes its own session: {!r}".format(
                  agent.history.session_id))
        check(agent.backend.session_id == "session-one",
              "the backend adopted file one's session")
        texts = [m.text for m in agent.history.messages]
        check("make a bracket" in texts, "file one's transcript came back")
        check("make a gear" not in texts,
              "file two's transcript did not leak into file one")

        # And the other way round.
        bpy.ops.wm.open_mainfile(filepath=second)
        agent.load_state()
        check(agent.history.session_id == "session-two",
              "file two resumes its own session")
        texts = [m.text for m in agent.history.messages]
        check("make a gear" in texts and "make a bracket" not in texts,
              "file two's transcript is its own")
    finally:
        agent.backend = None
        agent.history.clear()
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)


def test_new_conversation_starts_a_fresh_session():
    """New Chat must reset the session, not just the transcript.

    The backend outlives the turn, so clearing only the visible messages
    left ``--resume`` pointing at the conversation the user just cleared.
    """
    print("test_new_conversation_starts_a_fresh_session")
    from mesh_agent import agent as agent_module

    class _FakeBackend:
        def __init__(self, session_id=None):
            self.session_id = session_id

        def cancel(self):
            pass

    bpy.ops.wm.read_homefile(use_empty=True)
    agent = agent_module.get_agent()
    try:
        agent.backend = _FakeBackend("session-one")
        agent.history.add("user", "make a bracket")
        agent.attachments = [{"path": "/nonexistent.png", "name": "a.png"}]
        agent._sent_attachments = 1

        check(agent.new_conversation(), "new_conversation reported success")
        check(agent.history.messages == [], "the transcript is empty")
        check(agent.backend.session_id is None,
              "the backend no longer resumes the old session")
        check(agent.history.session_id == "",
              "the saved session id is empty: {!r}".format(
                  agent.history.session_id))
        check(agent.attachments == [] and agent.pending_attachment_count() == 0,
              "the attachments restart at zero")

        saved = json.loads(bpy.data.texts[history_module.TEXT_BLOCK_NAME]
                           .as_string())
        check(saved["messages"] == [] and not saved["session_id"],
              "the .blend's copy was rewritten too")

        # A running turn owns the session; the button is polled out, and the
        # call itself refuses as well.
        agent.busy = True
        agent.history.add("user", "still talking")
        check(not agent.new_conversation(),
              "new_conversation refuses while a turn is running")
        check(len(agent.history.messages) == 1,
              "a running turn's transcript survived")
    finally:
        agent.busy = False
        agent.backend = None
        agent.history.clear()


KEPT_EDITORS = (
    'VIEW_3D', 'CADEX_CHAT', 'CADEX_PARAMS', 'PROPERTIES', 'OUTLINER',
    'TEXT_EDITOR', 'CONSOLE', 'INFO', 'PREFERENCES', 'FILES',
)

# Identifiers as the editor-type menu spells them. The animation, image, node
# and file editors surface *subtype* identifiers rather than their space
# type's own (rna_Area_ui_type_itemf calls space_subtype_item_extend), so
# asserting on "DOPESHEET_EDITOR" or "GRAPH_EDITOR" would pass vacuously --
# those strings were never valid ui_type values.
HIDDEN_EDITORS = (
    # space_action. Only these two of the seven SpaceDopeSheetEditor modes are
    # menu items (rna_enum_space_action_mode_items is a subset of
    # ..._mode_all_items); the rest would assert vacuously.
    'DOPESHEET', 'TIMELINE',
    # space_graph
    'FCURVES', 'DRIVERS',
    # space_nla
    'NLA_EDITOR',
    # space_image
    'IMAGE_EDITOR', 'UV',
    # space_node
    'ShaderNodeTree', 'CompositorNodeTree', 'GeometryNodeTree',
    'TextureNodeTree',
    # space_sequencer, space_spreadsheet, space_clip
    'SEQUENCE_EDITOR', 'SPREADSHEET', 'CLIP_EDITOR',
    # the asset browser, a space_file subtype
    'ASSETS',
)


def _ui_type_accepted(area, identifier):
    """Whether the editor menu offers this identifier.

    `Area.ui_type` is a dynamic enum, so its item list is not readable from
    Python without a context -- `enum_items` comes back empty. Assigning it
    is: RNA validates the value against the same itemf the menu is built
    from, and raises TypeError when it is not in the list.
    """
    try:
        area.ui_type = identifier
    except TypeError:
        return False
    return True


def test_cadex_editors_are_registered():
    """Chat and Parameters are editor types, not Properties areas told apart
    by where they sit."""
    print("test_cadex_editors_are_registered")
    space_types = bpy.types.Space.bl_rna.properties['type'].enum_items.keys()
    for name in ('CADEX_CHAT', 'CADEX_PARAMS'):
        check(name in space_types, "{:s} is a space type".format(name))
    for name in ('SpaceCadexChat', 'SpaceCadexParams'):
        check(hasattr(bpy.types, name),
              "bpy.types.{:s} exists".format(name))


def test_editor_menu_is_short():
    """The editor-type menu offers what Cadex builds and nothing else.

    An editor quietly coming back is invisible otherwise -- it only shows up
    as a dropdown entry that destroys the layout when picked.
    """
    print("test_editor_menu_is_short")
    area = next((a for s in bpy.data.screens for a in s.areas), None)
    if area is None:
        check(False, "a screen area to read the editor menu from")
        return
    was = area.ui_type
    try:
        for name in KEPT_EDITORS:
            check(_ui_type_accepted(area, name),
                  "{:s} is on the editor menu".format(name))
        for name in HIDDEN_EDITORS:
            check(not _ui_type_accepted(area, name),
                  "{:s} is off the editor menu".format(name))
        # The two bars are not editors and never were offered.
        for name in ('TOPBAR', 'STATUSBAR'):
            check(not _ui_type_accepted(area, name),
                  "{:s} is off the editor menu".format(name))
    finally:
        try:
            area.ui_type = was
        except TypeError:
            pass


def test_panels_are_homed_on_the_cadex_editors():
    """Each panel names the editor it belongs to, and no poll asks where it
    is being drawn -- that was the whole job of the geometry classifier."""
    print("test_panels_are_homed_on_the_cadex_editors")
    from mesh_agent import ui as mesh_ui

    expected = {
        'CADEX_CHAT_PT_transcript': ('CADEX_CHAT', 'WINDOW'),
        'CADEX_CHAT_PT_input': ('CADEX_CHAT', 'EXECUTE'),
        'CADEX_PARAMS_PT_parameters': ('CADEX_PARAMS', 'WINDOW'),
    }
    for name, (space, region) in expected.items():
        cls = getattr(bpy.types, name, None)
        if cls is None:
            check(False, "{:s} is registered".format(name))
            continue
        check(cls.bl_space_type == space,
              "{:s} draws in {:s}".format(name, space))
        check(cls.bl_region_type == region,
              "{:s} draws in the {:s} region".format(name, region))
        check("poll" not in cls.__dict__,
              "{:s} has no poll".format(name))

    check(not hasattr(mesh_ui, "_area_roles"),
          "the geometry classifier is gone")
    check(not hasattr(mesh_ui, "_column_role"),
          "the column-role lookup is gone")


def test_confirming_the_input_sends():
    """Return in the message box sends: Blender commits the field's value
    when the edit ends, and the property's update callback is what turns
    that into a turn."""
    print("test_confirming_the_input_sends")
    from mesh_agent import agent as agent_module

    class _FakeBackend:
        session_id = None

        def __init__(self):
            self.prompts = []

        def start_turn(self, prompt, _events):
            self.prompts.append(prompt)

        def cancel(self):
            pass

    bpy.ops.wm.read_homefile(use_empty=True)
    agent = agent_module.get_agent()
    backend = _FakeBackend()
    window_manager = bpy.context.window_manager
    try:
        agent.history.clear()
        agent.backend = backend

        window_manager.mesh_chat_input = "make a bracket"
        check(backend.prompts == ["make a bracket"],
              "the confirmed message reached the backend: {!r}".format(
                  backend.prompts))
        check(agent.busy, "the turn is running")
        check(window_manager.mesh_chat_input == "",
              "the field was cleared without re-entering the callback")

        # Nothing is sent while a turn is running, or for an empty field.
        window_manager.mesh_chat_input = "and a gear"
        check(backend.prompts == ["make a bracket"],
              "a second message during a turn is not sent")
        agent.busy = False
        window_manager.mesh_chat_input = "   "
        check(backend.prompts == ["make a bracket"],
              "whitespace alone is not sent")
    finally:
        agent.busy = False
        agent.backend = None
        agent.history.clear()
        window_manager.mesh_chat_input = ""


def test_message_box_widget_is_available():
    """The input is a text-box widget, not a text field; without it the chat
    would silently fall back to nothing at all."""
    print("test_message_box_widget_is_available")
    check("textbox" in bpy.types.UILayout.bl_rna.functions,
          "UILayout.textbox exists in this build")


def main():
    print("=== bl_mesh_agent tests ===")
    mesh_agent.register()
    try:
        test_bridge_chunked_request()
        test_image_attachment_roundtrip()
        test_tool_call_cap()
        test_transcript_persistence()
        test_session_id_round_trips_and_is_per_file()
        test_new_conversation_starts_a_fresh_session()
        test_cadex_editors_are_registered()
        test_editor_menu_is_short()
        test_panels_are_homed_on_the_cadex_editors()
        test_confirming_the_input_sends()
        test_message_box_widget_is_available()
        test_mcp_shim_protocol()
        test_cadex_engine_discovery()
        test_cadex_budgets_reach_open_project()
        test_cadex_overlay_carries_no_api_names()
        if os.environ.get("MESH_AGENT_LIVE"):
            test_live_claude_turn()
        else:
            print("test_live_claude_turn skipped (set MESH_AGENT_LIVE=1 to run)")
    finally:
        mesh_agent.unregister()

    if FAILURES:
        print("\n{:d} FAILURE(S):".format(len(FAILURES)))
        for label in FAILURES:
            print("  - " + label)
        sys.exit(1)
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
