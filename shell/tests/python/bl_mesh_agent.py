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

#: Names the prompt and the tool descriptions may say, each because a
#: workflow instruction is keyed to that one call rather than because
#: anyone is restating the API. A closed set: anything else fails.
_ALLOWED_API_NAMES = {
    "assembly.mjcf",     # ADR-091: check the collision shapes after this call
    "mesh.import_file",  # ADR-086 §4: import_geometry's wording, parked
    # ADR-138: link_part's whole point is that the stored name is what the
    # script then names, so the tool that stores it says which call takes it.
    # The same shape as import_geometry's line above, and named for the same
    # reason -- a tool that puts a file in the store and does not say how to
    # reach it leaves the model guessing.
    "part.import_part",
    # ADR-139: the Measure button queues a sentence for the next turn rather
    # than writing the script itself, so the sentence has to name the call it
    # is asking for. Nothing else in the overlay mentions measurements.
    "part.measurement",
}

#: The local-bpy-mode vocabulary ADR-030 deleted. It survived in the base
#: prompt for a hundred ADRs because this test only ever read the overlay.
_DELETED_VOCABULARY = ("mesh_model", "Float(", "Int(", "Bool(", "Color(",
                       "bpy.")


def test_prompt_carries_no_api_names():
    """The prompt describes behavior; the engine describes its API.

    A hand-written API listing in the prompt is a copy of the engine's
    truth that nothing keeps in sync — the drift class describe_cad_api
    exists to kill. This guardrail is the thing that keeps it dead, and
    until ADR-123 it read the overlay alone: the drift was in the base
    prompt the overlay is appended to, and in the tool descriptions.
    """
    print("test_prompt_carries_no_api_names")
    import re
    from mesh_agent import modes, tools

    pattern = re.compile(
        r"\b(?:part|mesh|assembly|partdesign|sketcher)\.[A-Za-z_]+")
    texts = {"the system prompt": modes.system_prompt()}
    for tool in tools.TOOL_DEFS:
        texts["{:s}'s description".format(tool["name"])] = tool["description"]

    for label, text in sorted(texts.items()):
        leaked = sorted(set(pattern.findall(text)) - _ALLOWED_API_NAMES)
        check(not leaked,
              "no xscript API names in {:s} (found: {!r})".format(
                  label, leaked))
        said = [word for word in _DELETED_VOCABULARY if word in text]
        check(not said,
              "no deleted runtime vocabulary in {:s} (found: {!r})".format(
                  label, said))

    overlay = modes.CADEX_OVERLAY
    check("params(" not in overlay and "result =" not in overlay,
          "no script skeleton in CADEX_OVERLAY either")
    check(len(overlay) < 3500,
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
    'VIEW_3D', 'CADEX_CHAT', 'CADEX_PARAMS',
    # The four ADR-108 split out of CADEX_PARAMS. Six Cadex editors is more
    # than ADR-036 wanted to exist, and the reason is stated there: five
    # panel groups in one editor cannot be arranged, and arranging them is
    # most of what a person does with a workspace.
    'CADEX_ENV', 'CADEX_POLICY', 'CADEX_TRAINING', 'CADEX_LIVE',
    'PROPERTIES', 'OUTLINER',
    'TEXT_EDITOR', 'CONSOLE', 'INFO', 'PREFERENCES', 'FILES',
    # The node editor is registered again, for exactly one tree type: the
    # wiring graph (ADR-066). The menu lists node *subtypes* rather than the
    # space, so what it gained is "Wiring", not "Node Editor" -- which is why
    # ADR-036's rule survives and why the four stock trees below are still
    # asserted absent.
    'CadexWiringTree',
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
    # space_node. These four changed meaning with ADR-066 and the change is
    # the point of keeping them: the space type IS registered now, so they
    # are no longer hidden by not-registering. They are hidden by
    # rna_SpaceNodeEditor_tree_type_poll, which filters the tree types the
    # menu is built from down to Cadex ones -- the same shape space_file.cc
    # already used to hide the asset browser. These four are therefore the
    # assertion that the filter is still there. Do not delete them as stale.
    'ShaderNodeTree', 'CompositorNodeTree', 'GeometryNodeTree',
    'TextureNodeTree',
    # And the base row is never offered either: a space type with a subtype
    # extender contributes its subtypes instead of itself.
    'NODE_EDITOR',
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
    """The six Cadex editors are editor types, not Properties areas told
    apart by where they sit.

    Two of them since ADR-036; the other four since ADR-108, which split
    Environment, Policy, Training and Live out of Parameters so each can be
    docked, split and closed on its own.
    """
    print("test_cadex_editors_are_registered")
    space_types = bpy.types.Space.bl_rna.properties['type'].enum_items.keys()
    for name in ('CADEX_CHAT', 'CADEX_PARAMS', 'CADEX_ENV', 'CADEX_POLICY',
                 'CADEX_TRAINING', 'CADEX_LIVE'):
        check(name in space_types, "{:s} is a space type".format(name))
    for name in ('SpaceCadexChat', 'SpaceCadexParams', 'SpaceCadexEnv',
                 'SpaceCadexPolicy', 'SpaceCadexTraining', 'SpaceCadexLive'):
        check(hasattr(bpy.types, name),
              "bpy.types.{:s} exists".format(name))
        # Every Cadex space is a bare SpaceLink header: no space data of its
        # own, so nothing here has to be versioned into an existing .blend.
        # The check is that the RNA struct carries no property but the ones
        # `Space` itself defines plus the header toggle.
        cls = getattr(bpy.types, name, None)
        if cls is not None:
            own = set(cls.bl_rna.properties.keys()) - set(
                bpy.types.Space.bl_rna.properties.keys())
            check(own <= {'show_region_header'},
                  "{:s} stores no state of its own, holds {!r}".format(
                      name, sorted(own)))
    # The third editor is not a space type at all: it is one Python node tree
    # hosted in the stock Node Editor, which is what made it cost no DNA, no
    # RNA and no -Wswitch case (ADR-066). It is therefore checked through
    # NodeTree.__subclasses__() and not through bpy.types, which carries a
    # registered operator or space but never a registered node tree.
    check('CadexWiringTree' in {getattr(t, 'bl_idname', '')
                                for t in bpy.types.NodeTree.__subclasses__()},
          "the wiring tree is a registered node tree type")


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
    """Each panel names the editor it belongs to, and no poll asks *where*
    it is being drawn -- that was the whole job of the geometry classifier.

    The third column is whether the panel polls at all. `False` is the
    strong claim: a panel that is always shown in its editor has nothing to
    decide, which is what having a space type buys. `True` is allowed only
    for the four ADR-108 moved out of Parameters, and only because they poll
    on **content** -- a scene flag saying the model has collision geometry,
    a simulation, policy commands or a training report. That distinction is
    the point of the test, and
    `test_the_simulation_panel_polls_on_content_not_geometry` is where one
    of them is checked in full.
    """
    print("test_panels_are_homed_on_the_cadex_editors")
    from mesh_agent import ui as mesh_ui

    expected = {
        'CADEX_CHAT_PT_transcript': ('CADEX_CHAT', 'WINDOW', False),
        'CADEX_CHAT_PT_input': ('CADEX_CHAT', 'EXECUTE', False),
        'CADEX_PARAMS_PT_parameters': ('CADEX_PARAMS', 'WINDOW', False),
        # ADR-108: one panel group per editor, so each can be arranged
        # separately. Renamed with them -- a class called
        # CADEX_PARAMS_PT_collision drawing in CADEX_ENV would be a name
        # that lies about where it appears.
        'CADEX_ENV_PT_collision': ('CADEX_ENV', 'WINDOW', True),
        'CADEX_POLICY_PT_simulation': ('CADEX_POLICY', 'WINDOW', True),
        'CADEX_POLICY_PT_actuators': ('CADEX_POLICY', 'WINDOW', True),
        'CADEX_TRAINING_PT_training': ('CADEX_TRAINING', 'WINDOW', True),
    }
    for name, (space, region, polls) in expected.items():
        cls = getattr(bpy.types, name, None)
        if cls is None:
            check(False, "{:s} is registered".format(name))
            continue
        check(cls.bl_space_type == space,
              "{:s} draws in {:s}".format(name, space))
        check(cls.bl_region_type == region,
              "{:s} draws in the {:s} region".format(name, region))
        check(("poll" in cls.__dict__) == polls,
              "{:s} {:s}".format(
                  name,
                  "polls on content" if polls else "has no poll"))
        if not polls:
            continue
        # ...and what it polls on is content. `area`, `region` and
        # `space_data` are how a poll asks where it is; none may appear.
        import inspect
        body = inspect.getsource(cls.__dict__["poll"].__func__)
        geometry = [word for word in ('.area', '.region', '.space_data')
                    if word in body]
        check(not geometry,
              "{:s}'s poll reads no geometry (found {!r})".format(
                  name, geometry))

    check(not hasattr(mesh_ui, "_area_roles"),
          "the geometry classifier is gone")
    check(not hasattr(mesh_ui, "_column_role"),
          "the column-role lookup is gone")


#: Menus the File menu points at that are registered from C
#: (`editors/space_topbar/space_topbar.cc`) and so never appear in
#: `bpy.types` -- there is no way to check them from Python.
TOPBAR_C_MENUS = frozenset({'TOPBAR_MT_file_open_recent'})


def _identifiers_drawn_by(module):
    """The operator and menu identifiers a module's draw functions name.

    Read out of the source rather than kept in a list beside it: the point is
    to catch an upstream rename on a Blender merge, and a hand-maintained
    list is exactly what a merge does not update.
    """
    import inspect
    import re
    source = inspect.getsource(module)
    return (set(re.findall(r'\.operator\(\s*"([^"]+)"', source)),
            set(re.findall(r'\.menu\(\s*"([^"]+)"', source)))


def _operator_exists(idname):
    module, _, function = idname.partition(".")
    submodule = getattr(bpy.ops, module, None)
    # Operator types defined in C are absent from `bpy.types`, so this asks
    # `bpy.ops` -- which lists them, and lists nothing that is not registered.
    return submodule is not None and function in dir(submodule)


def test_cadex_topbar_is_the_product_bar():
    """File and Edit are back on the top bar, and every entry resolves.

    The app template blanked the bar entirely (ADR-037), which is how Open,
    Save, Import, Export and Preferences went missing; ADR-041 puts back two
    menus of our own rather than Blender's six. A menu entry naming an
    operator this build does not have draws as a red row, so the identifiers
    are checked against the running build rather than trusted.
    """
    print("test_cadex_topbar_is_the_product_bar")
    from mesh_agent import topbar

    for name in ('CADEX_MT_file', 'CADEX_MT_edit', 'CADEX_MT_editor_menus'):
        check(getattr(bpy.types, name, None) is not None,
              "{:s} is registered".format(name))

    operators, menus = _identifiers_drawn_by(topbar)
    for idname in ("wm.open_mainfile", "wm.save_mainfile",
                   "wm.save_as_mainfile", "wm.revert_mainfile",
                   "screen.userpref_show"):
        check(idname in operators, "the bar offers {:s}".format(idname))
    for name in ('TOPBAR_MT_file_import', 'TOPBAR_MT_file_export',
                 'TOPBAR_MT_file_open_recent'):
        check(name in menus, "the File menu offers {:s}".format(name))

    for idname in sorted(operators):
        check(_operator_exists(idname),
              "{:s} exists in this build".format(idname))
    for name in sorted(menus - TOPBAR_C_MENUS):
        check(getattr(bpy.types, name, None) is not None,
              "{:s} exists in this build".format(name))

    # Blender's bar must come back exactly as it was: disabling the add-on
    # runs uninstall, and a half-restored header is a broken session.
    stock = bpy.types.TOPBAR_HT_upper_bar.draw
    check(not topbar.installed(), "the bar is not installed by registering")
    try:
        topbar.install()
        check(bpy.types.TOPBAR_HT_upper_bar.draw is topbar.draw_upper_bar,
              "install puts the Cadex bar on the top bar")
        topbar.install()
        check(bpy.types.TOPBAR_HT_upper_bar.draw is topbar.draw_upper_bar,
              "installing twice is a no-op")
    finally:
        topbar.uninstall()
    check(bpy.types.TOPBAR_HT_upper_bar.draw is stock,
          "uninstall gives the stock bar back")


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


class _RecordingLayout:
    """Enough of ``UILayout`` to record what a draw asks for.

    Groups nest, so a row remembers its parent's ``enabled``: that is what
    makes "drawn but greyed out" distinguishable from "drawn and live".
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.drawn = [] if parent is None else parent.drawn
        self.separators = [0] if parent is None else parent.separators
        self._enabled = True

    @property
    def enabled(self):
        return self._enabled and (self.parent is None or self.parent.enabled)

    @enabled.setter
    def enabled(self, value):
        self._enabled = bool(value)

    def row(self, **_kwargs):
        return _RecordingLayout(self)

    column = row

    def separator(self, **_kwargs):
        self.separators[0] += 1

    def operator(self, idname, **kwargs):
        self.drawn.append({"idname": idname, "enabled": self.enabled, **kwargs})

    def label(self, **kwargs):
        self.drawn.append({"label": kwargs.get("text", "")})

    def prop(self, _data, name, **_kwargs):
        self.drawn.append({"prop": name})

    def template_header(self):
        pass


class _FakeScreen:
    areas = ()


class _FakeContext:
    """A context for a draw, in a build with no window at all."""

    screen = _FakeScreen()
    edit_object = None

    def __init__(self):
        self.scene = bpy.context.scene
        self.window_manager = bpy.context.window_manager


def test_every_chat_action_is_in_one_row_under_the_message_box():
    """One place to look for a button, and a row that does not resize.

    The controls used to be split across the header (the two pins) and this
    row (everything else), which made "where is the button" depend on which
    button. ADR-074 moved them together: the header carries status, the row
    carries actions.

    The width claim is the other half. ``Define Terminal`` used to be drawn
    only when its ``poll`` passed, so entering Edit Mode grew the row and
    moved every other button under the pointer. It is drawn disabled instead.
    """
    print("test_every_chat_action_is_in_one_row_under_the_message_box")
    from mesh_agent import cadex_terminal_pick
    from mesh_agent import spaces as mesh_spaces
    from mesh_agent import ui as mesh_ui

    context = _FakeContext()
    layout = _RecordingLayout()
    mesh_ui.draw_chat_buttons(layout, context)
    drawn = [entry for entry in layout.drawn if "idname" in entry]
    idnames = [entry["idname"] for entry in drawn]

    for idname in (
        "mesh_agent.attach_image",
        "mesh_agent.paste_image",
        "mesh_agent.pick_pin",
        "mesh_agent.pick_point",
        "mesh_agent.define_board",
        "mesh_agent.define_terminal",
        # The wire-path round trip's three states (ADR-118): open, send,
        # abandon. All three are in the row, always drawn, greyed when they
        # do not apply -- like Define Terminal, and for the same reason.
        "mesh_agent.edit_wire_path",
        "mesh_agent.confirm_wire_path",
        "mesh_agent.cancel_wire_path",
        "mesh_agent.rebuild_model",
        "mesh_agent.toggle_params",
        "mesh_agent.show_script",
        "mesh_agent.toggle_wiring",
        "mesh_agent.chat_new",
        "mesh_agent.chat_send",
    ):
        check(idname in idnames, "{:s} is in the row".format(idname))

    # Rebuild is the always-on one: its poll is "the assistant is idle", so
    # nothing about the selection or a pending failure can grey it out.
    rebuild = getattr(bpy.types, "MESH_AGENT_OT_rebuild_model", None)
    check(rebuild is not None and rebuild.poll(bpy.context),
          "Rebuild Model is clickable with nothing selected")

    # Out of Edit Mode: drawn, and disabled rather than missing.
    terminal = next(e for e in drawn
                    if e["idname"] == "mesh_agent.define_terminal")
    check(cadex_terminal_pick.MESH_AGENT_OT_define_terminal.poll(context)
          is False, "the terminal gesture does not apply here")
    check(terminal["enabled"] is False, "so its button is greyed out")

    # ...and the row is the same width either way, which is the point.
    was = cadex_terminal_pick.MESH_AGENT_OT_define_terminal.poll
    try:
        cadex_terminal_pick.MESH_AGENT_OT_define_terminal.poll = (
            classmethod(lambda cls, ctx: True))
        editing = _RecordingLayout()
        mesh_ui.draw_chat_buttons(editing, context)
    finally:
        cadex_terminal_pick.MESH_AGENT_OT_define_terminal.poll = was
    check([e["idname"] for e in editing.drawn if "idname" in e] == idnames,
          "the same buttons draw in Edit Mode, in the same order")

    # The header keeps status only: a model dropdown and a count, no actions.
    header = _RecordingLayout()
    mesh_spaces.CADEX_CHAT_HT_header.draw(
        type("_H", (), {"layout": header})(), context)
    check(not [e for e in header.drawn if "idname" in e],
          "the chat header draws no operators any more")


def test_message_box_widget_is_available():
    """The input is a text-box widget, not a text field; without it the chat
    would silently fall back to nothing at all."""
    print("test_message_box_widget_is_available")
    check("textbox" in bpy.types.UILayout.bl_rna.functions,
          "UILayout.textbox exists in this build")



# -- simulation playback: the pure trace -> F-curve conversion --------------
#
# No bpy, no engine: this is arithmetic and ordering, and every one of these
# failure modes is silent in the viewport (ADR-050).

def _trace_frames(count, *, step=0.05, flip_at=None):
    """Solver frames, optionally with a deliberate quaternion sign flip."""
    frames = [{
        "frame_index": 0,
        "frame_kind": "input",
        "nominal_time_s": None,
        "component_placements": {
            "swing": {"position_mm": [0.0, 0.0, 0.0],
                      "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
        },
    }]
    for index in range(count):
        # A quarter turn about Z, as xyzw.
        quaternion = [0.0, 0.0, 0.3826834, 0.9238795]
        if flip_at is not None and index >= flip_at:
            quaternion = [-value for value in quaternion]
        frames.append({
            "frame_index": index + 1,
            "frame_kind": "solver_output",
            "nominal_time_s": round(index * step, 6),
            "component_placements": {
                "swing": {"position_mm": [float(index), 1.0, 2.0],
                          "rotation_xyzw": quaternion},
            },
        })
    return frames


def test_playback_keys_on_time_not_frame_index():
    from mesh_agent import cadex_animate

    # 0.05 s solver step at 30 fps: 1.5 Blender frames per sample. Keying
    # on the frame index would play this at 1/1.5 speed.
    check(abs(cadex_animate.frame_of(0.0, 0.0, 30) - 1.0) < 1e-9,
          "the first sample is frame 1")
    check(abs(cadex_animate.frame_of(0.05, 0.0, 30) - 2.5) < 1e-9,
          "a 0.05 s sample at 30 fps lands on frame 2.5, not frame 2")
    check(abs(cadex_animate.frame_of(1.0, 0.0, 30) - 31.0) < 1e-9,
          "one second at 30 fps is frame 31")
    # A non-integral step/fps ratio must stay fractional rather than
    # collapsing several samples onto one frame.
    landings = [cadex_animate.frame_of(index * 0.01, 0.0, 30)
                for index in range(4)]
    check(len(set(landings)) == 4,
          "four 0.01 s samples land on four distinct fractional frames")


def test_playback_reorders_the_quaternion_and_keeps_it_continuous():
    from mesh_agent import cadex_animate

    curves = cadex_animate.curves_for_component(
        _trace_frames(4), "swing", 0.0, 30)

    # The trace is xyzw; Blender is wxyz. w=0.9238795 must be channel 0.
    first_w = curves[("rotation_quaternion", 0)][1]
    check(abs(first_w - 0.9238795) < 1e-6,
          "the quaternion is reordered xyzw -> wxyz")
    first_z = curves[("rotation_quaternion", 3)][1]
    check(abs(first_z - 0.3826834) < 1e-6,
          "and the vector part follows w")

    # mm 1:1, no conversion.
    check(curves[("location", 1)][1] == 1.0
          and curves[("location", 2)][1] == 2.0,
          "positions are raw mm, 1:1")

    # Frame 0 has no time and is not keyed.
    check(len(curves[("location", 0)]) == 8,
          "four solver frames become four keys; the input frame is skipped")

    # A deliberate q -> -q at sample 2. The solver means the same
    # orientation; keyed raw it takes the long way round the sphere.
    flipped = cadex_animate.curves_for_component(
        _trace_frames(4, flip_at=2), "swing", 0.0, 30)
    w_values = flipped[("rotation_quaternion", 0)][1::2]
    check(all(value > 0.0 for value in w_values),
          "a q -> -q sign flip is walked back into one hemisphere")
    check(max(w_values) - min(w_values) < 1e-6,
          "so a constant orientation stays constant across the flip")


def test_playback_frame_range_covers_the_run():
    from mesh_agent import cadex_animate

    start, end = cadex_animate.frame_range(
        {"parameters": {"start_time_s": 0.0, "end_time_s": 1.0,
                        "frames_per_second": 30}})
    check(start == 1 and end == 31,
          "a 1 s run at 30 fps is frames 1..31")
    start, end = cadex_animate.frame_range(
        {"parameters": {"start_time_s": 0.0, "end_time_s": 2.5,
                        "frames_per_second": 24}})
    check(start == 1 and end == 61, "2.5 s at 24 fps is frames 1..61")


def test_playback_skips_the_input_frame():
    from mesh_agent import cadex_animate

    frames = _trace_frames(3)
    solved = cadex_animate.solver_frames(frames)
    check(len(solved) == 3 and all(f["frame_kind"] == "solver_output"
                                   for f in solved),
          "the input frame is not a playback sample")
    check(all(f["nominal_time_s"] is not None for f in solved),
          "and every playback sample has a time")



def test_the_simulation_panel_polls_on_content_not_geometry():
    """The one panel with a poll, and it is about the model, not the layout.

    ADR-035 removed every poll that asked *where* a panel was being drawn.
    This one asks whether the model has a simulation at all, so a model
    without one sees the parameters editor exactly as before -- a different
    question, and the only kind of poll still worth having.
    """
    print("test_the_simulation_panel_polls_on_content_not_geometry")
    from mesh_agent import cadex_animate

    cls = getattr(bpy.types, "CADEX_POLICY_PT_simulation", None)
    check(cls is not None, "CADEX_POLICY_PT_simulation is registered")
    if cls is None:
        return
    check(cls.bl_space_type == 'CADEX_POLICY',
          "it lives in the policy editor (ADR-108)")
    check(cls.bl_region_type == 'WINDOW', "in the main region")
    check("poll" in cls.__dict__, "and it does poll")

    scene = bpy.context.scene
    if cadex_animate.SCENE_FLAG in scene:
        del scene[cadex_animate.SCENE_FLAG]
    check(not cls.poll(bpy.context),
          "a model with no simulation does not show the panel")
    scene[cadex_animate.SCENE_FLAG] = {"fps": 30, "frames": 21,
                                       "components": 2, "seconds": 1.0}
    check(cls.poll(bpy.context),
          "a model with one does")
    del scene[cadex_animate.SCENE_FLAG]


def test_render_views_cameras_frame_the_model():
    """The four cameras are computed, not read off the user's viewport.

    ``view_matrices`` is the half of render_views that imports no bpy
    (ADR-124), which is why it can be checked here: aim, fit and orientation
    are arithmetic on a bounding box. What cannot be checked headless is the
    image -- ``draw_view3d`` needs a real VIEW_3D -- so the last check here is
    that the background refusal is still a sentence, and the composite's real
    dimensions are recorded by the gate instead.
    """
    print("test_render_views_cameras_frame_the_model")
    from mesh_agent import capture

    bbox = ((-30.0, -10.0, 0.0), (10.0, 50.0, 24.0))
    centre = (-10.0, 20.0, 12.0)
    views = capture.view_matrices(bbox, aspect=1.0)
    check(len(views) == 4, "four views")
    check([view["name"] for view in views] ==
          ["front", "right", "top", "three-quarter"],
          "front, right, top, three-quarter")
    check(sorted(view["quadrant"] for view in views) ==
          ["bottom-left", "bottom-right", "top-left", "top-right"],
          "one per quadrant of the 2x2 composite")

    for view in views:
        aimed = capture.transform(view["view"], centre)
        check(abs(aimed[0]) < 1e-6 and abs(aimed[1]) < 1e-6,
              "{:s} looks at the bbox centre".format(view["name"]))
        check(aimed[2] < 0.0,
              "{:s} has the model in front of the camera".format(view["name"]))

    axis_true = {"front": (0.0, -1.0, 0.0), "right": (1.0, 0.0, 0.0),
                 "top": (0.0, 0.0, 1.0)}
    for view in views:
        expected = axis_true.get(view["name"])
        if expected is None:
            continue
        check(max(abs(a - b) for a, b in zip(view["direction"], expected)) < 1e-9,
              "{:s} is axis-true {!s}".format(view["name"], expected))
    directions = {tuple(round(axis, 6) for axis in view["direction"])
                  for view in views}
    check(len(directions) == 4, "the four directions are distinct")
    hero = [view for view in views if view["name"] == "three-quarter"][0]
    check(hero["direction"][0] > 0.1 and hero["direction"][1] < -0.1
          and hero["direction"][2] > 0.1,
          "the three-quarter view is up, right and in front")

    corners = [(x, y, z) for x in (bbox[0][0], bbox[1][0])
               for y in (bbox[0][1], bbox[1][1])
               for z in (bbox[0][2], bbox[1][2])]
    for view in views:
        projected = [capture.project(view["view"], view["window"], corner)
                     for corner in corners]
        inside = all(p is not None and abs(p[0]) <= 1.0 and abs(p[1]) <= 1.0
                     and -1.0 <= p[2] <= 1.0 for p in projected)
        check(inside, "{:s} contains the whole bbox".format(view["name"]))
        if view["ortho"]:
            widest = max(max(abs(p[0]), abs(p[1])) for p in projected)
            check(0.85 < widest <= 1.0,
                  "{:s} fits it snugly, with a margin".format(view["name"]))

    wide = capture.view_matrices(bbox, aspect=2.0)
    front_wide = [v for v in wide if v["name"] == "front"][0]
    projected = [capture.project(front_wide["view"], front_wide["window"], c)
                 for c in corners]
    check(all(abs(p[0]) <= 1.0 and abs(p[1]) <= 1.0 for p in projected),
          "a non-square tile still contains the bbox")

    flat = capture.view_matrices(((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
    check(len(flat) == 4, "a degenerate bbox frames a unit box instead of "
                          "dividing by zero")

    red, green, blue, white = ([1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0],
                               [0.0, 0.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0])
    pixels, width, height = capture.composite_2x2(
        [red, green, blue, white], 1, 1)
    check((width, height) == (2, 2), "the composite is 2x2 tiles")
    # Blender image rows run bottom-up, so the first row of the buffer is the
    # BOTTOM of the picture: top-left/top-right land in the second row.
    check(pixels[0:4] == blue and pixels[4:8] == white,
          "top and three-quarter are the bottom row")
    check(pixels[8:12] == red and pixels[12:16] == green,
          "front and right are the top row")

    ok, message = capture.render_views()
    check(ok is None and "background" in str(message),
          "render_views refuses in background mode, in a sentence")

    from mesh_agent import tools
    names = [entry["name"] for entry in tools.TOOL_DEFS]
    check("render_views" in names, "render_views is a tool")
    check("viewport_screenshot" in names,
          "and viewport_screenshot is still one -- a different question")
    check("render_views" not in tools.MUTATING_TOOLS,
          "looking at the model does not enter the undo stack")
    check("render_views" not in tools._ENGINE_TOOLS,
          "and it never reaches the engine")


def test_exploded_poses_interpolate_in_staged_windows():
    """The explosion arithmetic, in the half that imports no bpy (ADR-149).

    Stage i of N owns factor window [i/N, (i+1)/N]: a component moves inside
    its own windows, holds outside them, and carries earlier stages forward.
    The midpoint check is the load-bearing one — it is the number the gate's
    factor-0.5 assertion compares the viewport against, so it must be pinned
    here first, on a fixture whose answer is checkable by hand.
    """
    print("test_exploded_poses_interpolate_in_staged_windows")
    from mesh_agent import cadex_explode

    half_root_two = 0.5 ** 0.5
    identity = (0.0, 0.0, 0.0, 1.0)
    quarter_z = (0.0, 0.0, half_root_two, half_root_two)
    solved = {"top": ((0.0, 0.0, 0.0), identity),
              "base": ((0.0, 0.0, -10.0), identity)}
    # Two moves, both on `top`, cumulative: up 20, then over 10 with a 90°
    # twist. `base` is never named, so it must sit still at every factor.
    stages = [
        {"move_index": 0, "kind": "normal", "component_outputs": ["top"],
         "poses": {"top": {"position_mm": [0.0, 0.0, 20.0],
                           "quaternion_xyzw": list(identity)}}},
        {"move_index": 1, "kind": "normal", "component_outputs": ["top"],
         "poses": {"top": {"position_mm": [10.0, 0.0, 20.0],
                           "quaternion_xyzw": list(quarter_z)}}},
    ]

    def near(a, b, tolerance=1e-9):
        return max(abs(x - y) for x, y in zip(a, b)) < tolerance

    at_zero = cadex_explode.poses_at(0.0, solved, stages)
    check(near(at_zero["top"][0], (0.0, 0.0, 0.0))
          and near(at_zero["top"][1], identity),
          "factor 0 is the solved pose")
    check(near(at_zero["base"][0], (0.0, 0.0, -10.0)),
          "an unmoved component sits at its solved pose")

    at_half = cadex_explode.poses_at(0.5, solved, stages)
    check(near(at_half["top"][0], (0.0, 0.0, 20.0)),
          "factor 0.5 is exactly the end of stage 0 of 2")
    check(near(at_half["top"][1], identity),
          "and stage 1's twist has not started")

    # Middle of stage 1: half the translation, half the rotation — a 45°
    # twist, which is the slerp midpoint, not the lerp one.
    at_three_quarters = cadex_explode.poses_at(0.75, solved, stages)
    eighth_z = (0.0, 0.0, (0.5 - 0.5 * half_root_two) ** 0.5,
                (0.5 + 0.5 * half_root_two) ** 0.5)
    check(near(at_three_quarters["top"][0], (5.0, 0.0, 20.0)),
          "mid-stage translation is the lerp midpoint")
    check(near(at_three_quarters["top"][1], eighth_z, 1e-9),
          "mid-stage rotation is the slerp midpoint (45° about Z)")
    check(near(at_three_quarters["base"][0], (0.0, 0.0, -10.0)),
          "the unmoved component still has not moved")

    at_one = cadex_explode.poses_at(1.0, solved, stages)
    check(near(at_one["top"][0], (10.0, 0.0, 20.0))
          and near(at_one["top"][1], quarter_z),
          "factor 1 is the final pose")

    # q and -q are one orientation: a target on the far hemisphere must
    # interpolate the short way round, not sweep 270°.
    flipped = cadex_explode._slerp(identity,
                                   tuple(-v for v in quarter_z), 0.5)
    agreement = abs(sum(x * y for x, y in zip(flipped, eighth_z)))
    check(abs(agreement - 1.0) < 1e-9,
          "a sign-flipped quaternion still takes the short way")

    # The factor-0 endpoint comes from the display placement matrix.
    ninety_about_z = [0.0, -1.0, 0.0, 1.0,
                      1.0, 0.0, 0.0, 2.0,
                      0.0, 0.0, 1.0, 3.0,
                      0.0, 0.0, 0.0, 1.0]
    position, quaternion = cadex_explode.decompose_matrix16(ninety_about_z)
    check(near(position, (1.0, 2.0, 3.0)),
          "decompose reads the translation column")
    check(near(quaternion, quarter_z, 1e-9),
          "decompose reads the rotation as an xyzw quaternion")

    # One exploded view or none: the D5 rule, stated once and refused with
    # every candidate named.
    record = {"assembly_output": "asm"}
    entry, reason = cadex_explode.exploded_entry(
        {"boom": {"exploded_view": record}, "plate": {}})
    check(entry == ("boom", record) and reason == "",
          "one exploded view is found by its key")
    entry, reason = cadex_explode.exploded_entry({"plate": {}})
    check(entry is None and "no exploded view" in reason,
          "no exploded view is a stated reason, not an error")
    entry, reason = cadex_explode.exploded_entry(
        {"boom": {"exploded_view": record},
         "bang": {"exploded_view": record}})
    check(entry is None and "bang" in reason and "boom" in reason,
          "two exploded views are refused with both named")

    # Leader lines grow with their component's own staged progress: the k-th
    # line of a component is its k-th move, and grows only during it.
    lines = [
        {"component_output": "top", "start_mm": [0.0, 0.0, 0.0],
         "end_mm": [0.0, 0.0, 20.0]},
        {"component_output": "top", "start_mm": [0.0, 0.0, 20.0],
         "end_mm": [10.0, 0.0, 20.0]},
    ]
    check(cadex_explode.line_points_at(
              0.0, lines, cadex_explode.component_progress(0.0, stages)) == [],
          "no lines at factor 0")
    at_half_lines = cadex_explode.line_points_at(
        0.5, lines, cadex_explode.component_progress(0.5, stages))
    check(len(at_half_lines) == 1 and near(at_half_lines[0][1], (0.0, 0.0, 20.0)),
          "at factor 0.5 the first line is complete and the second absent")
    at_three_quarter_lines = cadex_explode.line_points_at(
        0.75, lines, cadex_explode.component_progress(0.75, stages))
    check(len(at_three_quarter_lines) == 2
          and near(at_three_quarter_lines[1][1], (5.0, 0.0, 20.0)),
          "mid-stage, its line has grown exactly halfway")

    from mesh_agent import tools
    names = [entry["name"] for entry in tools.TOOL_DEFS]
    check("exploded_view" in names, "exploded_view is a tool")
    check("exploded_view" not in tools.MUTATING_TOOLS,
          "looking at the assembly spread does not enter the undo stack")
    check("exploded_view" not in tools._ENGINE_TOOLS,
          "and it never reaches the engine")


def test_dimension_is_drawn_in_pixels_around_its_number():
    from mesh_agent import cadex_dimension

    # 200 px apart, horizontal, with a 60 px wide number.
    drawing = cadex_dimension.dimension_geometry(
        (100.0, 100.0), (300.0, 100.0), 60.0)

    check(drawing["kind"] == "dimension", "a 200 px span is a dimension")
    check(len(drawing["segments"]) == 6,
          "two extension lines, two dimension-line halves and two ticks")

    # The dimension line is *broken* around the number, which is the shape
    # the feature was asked for: a line from each end, and a gap in the
    # middle exactly wide enough for the text plus its padding.
    halves = [segment for segment in drawing["segments"]
              if abs(segment[1] - segment[3]) < 1e-9
              and abs(segment[1] - (100.0 + cadex_dimension.OFFSET_PX)) < 1e-9]
    check(len(halves) == 2, "the dimension line is two segments, not one")
    gap = min(segment[0] for segment in halves
              if segment[0] > 200.0) - max(segment[2] for segment in halves
                                           if segment[2] < 200.0)
    check(abs(gap - (60.0 + 2.0 * cadex_dimension.TEXT_PAD_PX)) < 1e-9,
          "and the gap is the number's width plus its padding")

    # Extension lines start clear of the anchor and overrun the dimension
    # line, both by pixel constants rather than by anything model-sized.
    verticals = [segment for segment in drawing["segments"]
                 if abs(segment[0] - segment[2]) < 1e-9]
    check(len(verticals) == 2, "one extension line per anchor")
    for segment in verticals:
        check(abs(segment[1] - 105.0) < 1e-9,
              "an extension line starts EXTENSION_GAP_PX clear of its anchor")
        check(abs(segment[3] - 130.0) < 1e-9,
              "and overruns the dimension line by EXTENSION_OVERRUN_PX")

    check(abs(drawing["text_angle"]) < 1e-9,
          "a horizontal dimension has horizontal text")

    # A number wider than the span leaves no line to draw. It must clamp
    # rather than emit a segment that runs backwards through its own label.
    crowded = cadex_dimension.dimension_geometry(
        (100.0, 100.0), (130.0, 100.0), 200.0)
    check(len(crowded["segments"]) == 4,
          "a number wider than the span suppresses the dimension line halves")

    # Text follows the line, and is never upside down: the flip happens
    # exactly once, as the line passes vertical.
    import math as _math
    check(abs(_math.degrees(cadex_dimension.text_angle((0.0, 1.0))) - 90.0) < 1e-9,
          "a vertical dimension reads bottom-to-top")
    check(abs(_math.degrees(cadex_dimension.text_angle((-1.0, -0.001)))) < 1.0,
          "and a line pointing down-left reads left-to-right, not upside down")


def test_an_edge_on_dimension_becomes_a_leader():
    from mesh_agent import cadex_dimension

    # Looking straight down the measured axis: the two anchors project to
    # nearly the same pixel. This is the case the whole overlay is judged on
    # -- the number must survive, because "see the right value from any
    # angle" is the feature.
    drawing = cadex_dimension.dimension_geometry(
        (100.0, 100.0), (103.0, 101.0), 60.0)

    check(drawing["kind"] == "leader",
          "a span under MINIMUM_SPAN_PX stops being a dimension")
    check(len(drawing["segments"]) == 2, "a leader is a stub and a shelf")
    check(abs(drawing["text_angle"]) < 1e-9,
          "and its number is horizontal, whatever the camera is doing")
    check(drawing["text_at"][0] > 100.0 and drawing["text_at"][1] > 100.0,
          "the number sits clear of the anchor it points at")

    # The threshold is a real boundary, not a rounding accident.
    just_over = cadex_dimension.dimension_geometry(
        (0.0, 0.0), (cadex_dimension.MINIMUM_SPAN_PX + 0.1, 0.0), 10.0)
    check(just_over["kind"] == "dimension",
          "and one pixel over the threshold is a dimension again")


def test_diameter_picks_the_widest_on_screen_and_survives_a_bore_down_z():
    from mesh_agent import cadex_dimension

    # A circle has infinitely many diameters; the legible one is whichever
    # faces the camera. The ring is published, the endpoints are per frame.
    ring = cadex_dimension.circle_points((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 5.0)
    check(len(ring) == cadex_dimension.DIAMETER_SAMPLES,
          "the ring is sampled DIAMETER_SAMPLES times")
    for point in ring:
        check(abs((point[0] ** 2 + point[1] ** 2) ** 0.5 - 5.0) < 1e-9,
              "every sample is on the circle")
        check(abs(point[2]) < 1e-9, "and in the circle's own plane")

    # A bore drilled down Z is the most common thing anyone measures, so a
    # basis built from a fixed reference axis would fail on the first real
    # model rather than an exotic one.
    for normal in ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)):
        points = cadex_dimension.circle_points((0.0, 0.0, 0.0), normal, 2.0)
        check(all(abs(sum(point[axis] * normal[axis] for axis in range(3)))
                  < 1e-9 for point in points),
              "the ring stays perpendicular to its normal, down {!s}".format(
                  normal))

    # Projected as an ellipse squashed 4:1, the widest diameter is the major
    # axis -- and it is a diameter, never a chord.
    projected = [(point[0] * 10.0 + 200.0, point[1] * 2.5 + 200.0)
                 for point in ring]
    near, far = cadex_dimension.widest_diameter(projected)
    width = ((far[0] - near[0]) ** 2 + (far[1] - near[1]) ** 2) ** 0.5
    check(abs(width - 100.0) < 1e-6,
          "the widest diameter of a 4:1 squashed ring is its major axis")
    check(abs(near[0] + far[0] - 400.0) < 1e-6
          and abs(near[1] + far[1] - 400.0) < 1e-6,
          "and its two ends are opposite each other about the centre")

    # A point behind the camera disqualifies its pair rather than its ring.
    holed = list(projected)
    holed[0] = None
    check(cadex_dimension.widest_diameter(holed) is not None,
          "one unprojectable sample does not lose the whole measurement")
    check(cadex_dimension.widest_diameter([None] * len(projected)) is None,
          "and a ring entirely behind the camera draws nothing")


def test_measurement_anchors_follow_the_placement_of_what_they_measure():
    from mesh_agent import cadex_dimension

    # The anchors the engine publishes are in the measured output's OWN
    # frame. An output an assembly places carries a solved placement, and
    # skipping it puts the dimension somewhere the part is not.
    moved = cadex_dimension.transformed(
        (1.0, 2.0, 3.0),
        [1.0, 0.0, 0.0, 10.0,
         0.0, 1.0, 0.0, 20.0,
         0.0, 0.0, 1.0, 30.0,
         0.0, 0.0, 0.0, 1.0])
    check(moved == (11.0, 22.0, 33.0), "a translation moves an anchor")
    check(cadex_dimension.transformed((1.0, 2.0, 3.0), []) == (1.0, 2.0, 3.0),
          "and no placement leaves it alone")

    display = {
        "plate": {"artifact_kind": "brep", "tessellation": {},
                  "placement": [1.0, 0.0, 0.0, 5.0,
                                0.0, 1.0, 0.0, 0.0,
                                0.0, 0.0, 1.0, 0.0,
                                0.0, 0.0, 0.0, 1.0]},
        "height": {"artifact_kind": None, "tessellation": None,
                   "measurement": {"kind": "distance", "subject": "plate",
                                   "label": "overall height",
                                   "value_mm": 10.0, "text": "10.00 mm",
                                   "anchors_mm": [[0.0, 0.0, 0.0],
                                                  [0.0, 0.0, 10.0]]}},
        "bore": {"artifact_kind": None, "tessellation": None,
                 "measurement": {"kind": "diameter", "subject": "plate",
                                 "label": "", "value_mm": 6.0,
                                 "text": "⌀6.00 mm",
                                 "center_mm": [0.0, 0.0, 5.0],
                                 "radius_mm": 3.0,
                                 "normal": [0.0, 0.0, 1.0]}},
    }
    records = cadex_dimension.records_from_display(display)
    check(len(records) == 2,
          "only the outputs carrying a measurement are drawn")
    by_name = {record["output"]: record for record in records}
    check(by_name["height"]["anchors_mm"][0] == (5.0, 0.0, 0.0),
          "a distance's anchors are moved by its subject's placement")
    ring = by_name["bore"]["ring_mm"]
    check(all(abs(((point[0] - 5.0) ** 2 + point[1] ** 2) ** 0.5 - 3.0) < 1e-9
              and abs(point[2] - 5.0) < 1e-9 for point in ring),
          "and a diameter's whole ring moves with it, still 3 mm about the "
          "placed centre")
    check(by_name["bore"]["text"] == "⌀6.00 mm",
          "the number is formatted engine-side and passed through verbatim")


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
        test_cadex_topbar_is_the_product_bar()
        test_confirming_the_input_sends()
        test_every_chat_action_is_in_one_row_under_the_message_box()
        test_message_box_widget_is_available()
        test_mcp_shim_protocol()
        test_cadex_engine_discovery()
        test_cadex_budgets_reach_open_project()
        test_prompt_carries_no_api_names()
        test_playback_keys_on_time_not_frame_index()
        test_playback_reorders_the_quaternion_and_keeps_it_continuous()
        test_playback_frame_range_covers_the_run()
        test_playback_skips_the_input_frame()
        test_the_simulation_panel_polls_on_content_not_geometry()
        test_render_views_cameras_frame_the_model()
        test_exploded_poses_interpolate_in_staged_windows()
        test_dimension_is_drawn_in_pixels_around_its_number()
        test_an_edge_on_dimension_becomes_a_leader()
        test_diameter_picks_the_widest_on_screen_and_survives_a_bore_down_z()
        test_measurement_anchors_follow_the_placement_of_what_they_measure()
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
