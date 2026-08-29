# SPDX-FileCopyrightText: 2026 Cadex Authors
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


def test_the_mesh_tools_are_not_deferred_behind_a_disabled_tool():
    """The two flags that must agree, and the reason they must (ADR-163).

    ``--tools ""`` turns off Claude Code's built-in tools, so the agent can
    only mutate the scene through the Mesh tools, on Blender's main thread.
    ``ToolSearch`` is a built-in, and Claude Code defers MCP tool *schemas*
    behind it. Together those two facts leave the model with a list of tool
    names and no way to open any of them -- at which point it writes the call
    out as prose and invents the reply, which reads as a working turn and
    changes nothing.

    So this asserts both halves and the join: built-ins off, deferral off.
    A change to either one alone is the bug.
    """
    print("test_the_mesh_tools_are_not_deferred_behind_a_disabled_tool")
    from mesh_agent import tools as tools_module
    from mesh_agent.backend import ClaudeCodeBackend

    backend = ClaudeCodeBackend(
        claude_path="/nonexistent/claude", model="claude-opus-5",
        system_prompt="test", bridge_port=1, bridge_token="t",
        tool_names=[tool["name"] for tool in tools_module.list_tools()])
    command = backend._command("hello")
    environment = backend._environment()

    check("--tools" in command and command[command.index("--tools") + 1] == "",
          "the built-in tool set is still disabled")
    check(environment.get("ENABLE_TOOL_SEARCH", "").lower()
          in {"false", "0", "off"},
          "tool-schema deferral is off, so the Mesh tools are resident "
          "({!r})".format(environment.get("ENABLE_TOOL_SEARCH")))
    # The environment is ours plus the switch, not a stripped one: the CLI
    # needs PATH and HOME to find its own install and the user's login.
    check(environment.get("PATH") == os.environ.get("PATH"),
          "the CLI keeps the environment it was launched with")


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


def _operator_exists(idname):
    module, _, function = idname.partition(".")
    submodule = getattr(bpy.ops, module, None)
    # Operator types defined in C are absent from `bpy.types`, so this asks
    # `bpy.ops` -- which lists them, and lists nothing that is not registered.
    return submodule is not None and function in dir(submodule)


def test_native_menu_targets_exist():
    """Every operator the OS menu bar maps to exists in this build.

    ADR-166 moved File and Edit to the native menu bar: the menus are built
    in `GHOST_SystemCocoa.mm` and each item's tag maps to an operator in
    `wm_window.cc` (`GHOST_kEventNativeMenu`). That map is C and cannot be
    read from here, so this list mirrors it -- if an operator below is
    renamed or dropped, a menu item goes dead silently, which is exactly
    what this catches. The in-window bar and its menus are gone with the
    install machinery (`topbar.install`), so what `topbar.py` keeps is the
    four product operators and their dialogs.
    """
    print("test_native_menu_targets_exist")
    from mesh_agent import topbar

    # The native menu map in wm_window.cc, tag for tag.
    for idname in (
        "wm.read_homefile",
        "wm.open_mainfile",
        "wm.revert_mainfile",
        "wm.save_mainfile",
        "wm.save_as_mainfile",
        "mesh_agent.import_asset",
        "mesh_agent.link_part",
        "mesh_agent.refresh_linked_parts",
        "mesh_agent.export_printable",
        "ed.undo",
        "ed.redo",
        "screen.userpref_show",
    ):
        check(_operator_exists(idname),
              "{:s} exists for its native menu item".format(idname))

    # The in-window menus and the header swap are gone, not merely unused.
    for name in ('CADEX_MT_file', 'CADEX_MT_edit', 'CADEX_MT_editor_menus'):
        check(getattr(bpy.types, name, None) is None,
              "{:s} is unregistered".format(name))
    for attr in ('install', 'uninstall', 'installed', 'draw_upper_bar'):
        check(not hasattr(topbar, attr),
              "topbar.{:s} is deleted".format(attr))


def test_landing_layout_is_pure_and_hit_testable():
    """The landing screen's geometry is arithmetic, not drawing (ADR-167).

    ``landing_layout`` runs with no window and no gpu, so the hit targets a
    click resolves against can be pinned here: every target inside the
    region, no two targets overlapping, and ``hit_test`` naming each one
    from its own centre.
    """
    print("test_landing_layout_is_pure_and_hit_testable")
    from mesh_agent import cadex_landing

    def centre(rect):
        x, y, w, h = rect
        return x + w / 2.0, y + h / 2.0

    def overlaps(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah

    for width, height, expect_two_column in ((1600, 900, True),
                                             (620, 820, False)):
        layout = cadex_landing.landing_layout(width, height, scale=1.0,
                                              with_demo=True)
        check(layout["two_column"] == expect_two_column,
              "{}x{} lays out {}".format(
                  width, height,
                  "two-column" if expect_two_column else "single-column"))
        rects = [("demo", layout["card"]["rect"])]
        rects += [(b["id"], b["rect"]) for b in layout["buttons"]]
        check([b["id"] for b in layout["buttons"]] ==
              ["new", "open", "tutorial"],
              "the three actions draw in their declared order")
        for name, rect in rects:
            x, y, w, h = rect
            check(0 <= x and x + w <= width and 0 <= y and y + h <= height,
                  "{} target is inside the {}x{} region".format(
                      name, width, height))
            check(cadex_landing.hit_test(layout, *centre(rect)) == name,
                  "{} answers from its own centre".format(name))
        for i, (name_a, rect_a) in enumerate(rects):
            for name_b, rect_b in rects[i + 1:]:
                check(not overlaps(rect_a, rect_b),
                      "{} and {} do not overlap".format(name_a, name_b))
        check(cadex_landing.hit_test(layout, 1.0, 1.0) is None,
              "the scrim corner hits nothing")

    # A region shorter than the natural layout shrinks instead of clipping.
    small = cadex_landing.landing_layout(500, 300, scale=1.0)
    check(small["scale"] < 1.0, "a small region scales the layout down")
    x, y, w, h = small["card"]["rect"]
    check(y >= 0 and y + h <= 300, "the shrunken card still fits")

    # The rounded corners are geometry, and the polygon stays in its rect.
    rect = (10.0, 20.0, 100.0, 50.0)
    points = cadex_landing.rounded_rect_points(rect, 8.0, segments=6)
    check(len(points) == 28, "four corners of seven points each")
    check(all(10.0 - 1e-6 <= px <= 110.0 + 1e-6 and
              20.0 - 1e-6 <= py <= 70.0 + 1e-6 for px, py in points),
          "every rounded point stays inside the rect")
    check(cadex_landing.rounded_rect_points(rect, 0.0) ==
          [(10.0, 20.0), (110.0, 20.0), (110.0, 70.0), (10.0, 70.0)],
          "zero radius degenerates to the four corners")
    oversized = cadex_landing.rounded_rect_points((0, 0, 20, 10), 400.0)
    check(all(0 <= px <= 20 and 0 <= py <= 10 for px, py in oversized),
          "a radius past half the rect is clamped, not folded")


def test_landing_degrades_without_a_demo():
    """No demo ships, and the landing screen knows it (ADR-171).

    The drone example was removed because its imported STLs had no
    recorded origin — nothing of unknown origin ships. The plumbing
    stays: ``demo_source`` reports absence, the layout drops the card
    (no rect to click, no EXAMPLE PROJECT overline), ``hit_test`` never
    answers ``demo``, and ``open_demo`` refuses politely rather than
    raising. The logo mark is not part of the demo and still ships.
    """
    print("test_landing_degrades_without_a_demo")
    from mesh_agent import cadex_landing

    blend, store = cadex_landing.demo_source()
    check(blend is None and store is None,
          "no demo project ships in the add-on (ADR-171)")

    layout = cadex_landing.landing_layout(1600, 900, scale=1.0,
                                          with_demo=False)
    check(layout["card"] is None and layout["overline"] is None
          and layout["caption"] is None,
          "the layout hides the card when no demo ships")
    hits = {cadex_landing.hit_test(layout, x, y)
            for x in range(0, 1600, 40) for y in range(0, 900, 40)}
    check("demo" not in hits,
          "no click anywhere resolves to the demo")
    check({b["id"] for b in layout["buttons"]} <= hits,
          "the action buttons still hit-test")

    ok, message = cadex_landing.open_demo()
    check(ok is False and "demo" in message.lower(),
          "open_demo refuses with a message rather than raising")

    logo = os.path.join(os.path.dirname(cadex_landing.__file__),
                        cadex_landing.LOGO_NAME)
    check(os.path.isfile(logo) and os.path.getsize(logo) > 0,
          "the logo mark ships in the add-on")


def test_landing_shows_dismisses_and_yields_to_chat():
    """The landing screen's exits behave (ADR-167).

    In a headless session it never shows on its own (`--background` is one
    of `maybe_show_on_startup`'s refusals); shown by hand it dismisses
    cleanly, the startup file leaves it up, and the first chat message
    takes it down -- the exit that makes 'the chat is already live' true.
    """
    print("test_landing_shows_dismisses_and_yields_to_chat")
    from mesh_agent import agent as agent_module
    from mesh_agent import cadex_landing

    check(not cadex_landing.visible(),
          "a background session never opens onto the landing screen")
    for idname in ("mesh_agent.landing_click", "mesh_agent.landing_hover",
                   "mesh_agent.landing_dismiss"):
        check(_operator_exists(idname),
              "{:s} is registered".format(idname))

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
    window_manager = bpy.context.window_manager
    try:
        cadex_landing.show()
        check(cadex_landing.visible(), "show() puts the screen up")
        cadex_landing.on_file_loaded()
        check(cadex_landing.visible(),
              "the startup file (no filepath) leaves it up")
        cadex_landing.dismiss()
        check(not cadex_landing.visible(), "dismiss() takes it down")
        cadex_landing.dismiss()  # twice is safe, the cadex_dimension rule

        cadex_landing.show()
        agent.history.clear()
        agent.backend = _FakeBackend()
        window_manager.mesh_chat_input = "make a bracket"
        check(not cadex_landing.visible(),
              "the first chat message dismisses the landing screen")
    finally:
        agent.busy = False
        agent.backend = None
        agent.history.clear()
        window_manager.mesh_chat_input = ""
        cadex_landing.dismiss()


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
    box = row

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
        "mesh_agent.chat_new",
        "mesh_agent.chat_send",
    ):
        check(idname in idnames, "{:s} is in the row".format(idname))

    # Rebuild and the viewport switches act on the model or the viewport,
    # not on the chat, so ADR-164 moved them out of this row and into the
    # parameters editor's Interface section.
    for idname in (
        "mesh_agent.rebuild_model",
        "mesh_agent.toggle_collision",
        "mesh_agent.toggle_dimensions",
        "mesh_agent.toggle_section",
        "mesh_agent.toggle_explode",
        "mesh_agent.toggle_blueprint",
    ):
        check(idname not in idnames,
              "{:s} left the chat row for the Interface section".format(
                  idname))

    interface = _RecordingLayout()
    mesh_ui._draw_interface(interface, context)
    interface_idnames = [e["idname"] for e in interface.drawn
                         if "idname" in e]
    for idname in (
        "mesh_agent.rebuild_model",
        "mesh_agent.toggle_collision",
        "mesh_agent.toggle_dimensions",
        "mesh_agent.toggle_cage",
        "mesh_agent.toggle_section",
        "mesh_agent.toggle_explode",
        "mesh_agent.toggle_blueprint",
    ):
        check(idname in interface_idnames,
              "{:s} is in the Interface section".format(idname))

    # There are no open-this-editor operators at all any more (ADR-165):
    # editors are opened and arranged with Blender's own editor dropdown and
    # area tiling. Gone from the registry, not merely from the rows.
    for name in (
        "MESH_AGENT_OT_toggle_params",
        "MESH_AGENT_OT_show_script",
        "MESH_AGENT_OT_toggle_wiring",
    ):
        check(getattr(bpy.types, name, None) is None,
              "{:s} is unregistered".format(name))

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


def test_blueprint_styles_the_viewport_from_one_table():
    from mesh_agent import cadex_blueprint, cadex_views, cadexd_client, tools

    # The themes are honest RGB: three channels in range, and the lines
    # always contrast with the ground they are drawn on.
    check(cadex_blueprint.DEFAULT_THEME in cadex_blueprint.THEMES,
          "the default theme exists")
    for name, theme in cadex_blueprint.THEMES.items():
        check(set(theme) == {"background", "solid", "line"},
              "theme {:s} carries exactly its three colours".format(name))
        for key, color in theme.items():
            check(len(color) == 3 and all(0.0 <= c <= 1.0 for c in color),
                  "{:s}.{:s} is an RGB 3-tuple in range".format(name, key))
        contrast = sum(theme["line"]) - sum(theme["background"])
        check(contrast > 1.0,
              "{:s}'s lines stand off its ground".format(name))

    # The field table is the contract the gate asserts against the styled
    # viewport, so its invariants are pinned here: overlays ON (the Edges
    # wires do not draw otherwise), every sub-overlay explicitly held, the
    # grid pair following the toggle, and facet wires never fighting the
    # true BREP edges.
    values = cadex_blueprint.shading_values("blueprint", grid=True)
    check(next(iter(values)) == "shading.type",
          "shading.type is applied first, so enum writes validate")
    check(values["shading.type"] == 'SOLID'
          and values["shading.color_type"] == 'SINGLE'
          and values["shading.background_type"] == 'VIEWPORT',
          "flat single-colour solids on a viewport ground")
    check(values["overlay.show_overlays"] is True,
          "overlays are ON -- the wires draw through the overlay pass")
    check(values["shading.show_object_outline"] is True
          and values["shading.object_outline_color"]
          == cadex_blueprint.THEMES["blueprint"]["line"],
          "every object is silhouetted in the line colour")
    check(values["overlay.show_wireframes"] is False,
          "facet wires stay off; the Edges children are the real edges")
    check(values["overlay.show_floor"] is True
          and values["overlay.show_ortho_grid"] is True,
          "grid=True drives both grid overlays")
    no_grid = cadex_blueprint.shading_values("grey", grid=False)
    check(no_grid["overlay.show_floor"] is False
          and no_grid["overlay.show_ortho_grid"] is False,
          "grid=False switches both off")
    others = {field: value for field, value in values.items()
              if field.startswith("overlay.")
              and field not in ("overlay.show_overlays", "overlay.show_floor",
                                "overlay.show_ortho_grid",
                                "overlay.grid_scale")}
    check(all(value is False for value in others.values()),
          "every other sub-overlay is explicitly False")
    check(set(cadex_blueprint.PRODUCT_LOOK) == set(values),
          "the fallback restore table covers exactly the fields written")
    check(cadex_blueprint.PRODUCT_LOOK["shading.type"] == 'SOLID'
          and cadex_blueprint.PRODUCT_LOOK["shading.light"] == 'MATCAP'
          and cadex_blueprint.PRODUCT_LOOK["overlay.show_overlays"] is False,
          "the fallback equals the pinned startup look the gate asserts")

    # The registry orders the five views; blueprint suspends for
    # render_views and hooks nothing else.
    names = [view.name for view in cadex_views.registered()]
    check(names == ["collision", "section", "explode", "dimensions",
                    "blueprint"],
          "the view registry is the five views in order: {!r}".format(names))
    blueprint_view = next(view for view in cadex_views.registered()
                          if view.name == "blueprint")
    check(blueprint_view.suspend is not None
          and blueprint_view.on_hydrate is None,
          "blueprint suspends for renders and needs no hydrate hook")

    # This suite runs --background, which is exactly where the sheet
    # renderer must refuse in the sentence the tool relays.
    from mesh_agent import capture
    sheet, error = capture.render_blueprint()
    check(sheet is None and error == (
              "Blueprint rendering is unavailable in background mode; "
              "use scene_summary instead."),
          "render_blueprint refuses headless, in the stated sentence")

    # Classification: the toggle is a view (neither set); the sheet maker
    # reaches the engine (preflighted) but never the undo stack.
    names = [entry["name"] for entry in tools.TOOL_DEFS]
    check("blueprint_view" in names and "make_blueprint" in names,
          "both blueprint tools are served")
    check("blueprint_view" not in tools.MUTATING_TOOLS
          and "blueprint_view" not in tools._ENGINE_TOOLS,
          "the view toggle is in neither set (the section_view precedent)")
    check("make_blueprint" in tools._ENGINE_TOOLS
          and "make_blueprint" not in tools.MUTATING_TOOLS,
          "the sheet maker preflights the engine and skips the undo stack")
    check("put_blueprint" in cadexd_client.MODELING_OPS,
          "the client serialises put_blueprint against rebuilds")


def test_blueprint_sheets_compose_from_pure_arithmetic():
    """ADR-151's pure half: the spec, the tiling and the dressing arithmetic.

    The tiling assertion is paint-counting: every template at every count
    and at awkward sizes must cover its canvas exactly once, because the
    boundaries are shared integer arrays and no-gap/no-overlap is meant to
    hold by construction. The fit_view and composite_rects checks are
    wrapper regressions: render_views' behaviour must not have moved when
    its internals became the sheet's primitives.
    """
    print("test_blueprint_sheets_compose_from_pure_arithmetic")
    from mesh_agent import capture, cadex_sheet, tools

    outputs = ("housing", "pin", "shaft")

    # -- defaults: an omitted views is the five-view triptych sheet ----------
    specs, error = cadex_sheet.normalize_views(None, outputs)
    check(error == "" and len(specs) == 5,
          "omitted views yield the five default specs")
    check([spec["view"] for spec in specs] ==
          ["front", "top", "bottom", "three-quarter", "custom"],
          "front, top, bottom, the three-quarter and the rear perspective")
    check(specs[4]["label"] == "exploded"
          and specs[4]["explode"] == 1.0
          and specs[4]["azimuth"] == 225.0
          and specs[4]["elevation"] == 25.0
          and not specs[4]["ortho"],
          "the default right column is the rear (Z+180) perspective, "
          "fully exploded")
    template, hero_index, error = cadex_sheet.choose_layout("triptych",
                                                            specs)
    check((template, hero_index, error) == ("triptych", None, ""),
          "the default sheet lays out as a triptych")

    # -- every refusal is a sentence carrying the fix ------------------------
    cases = (
        ([{"view": "rear"}], "Unknown view 'rear' in views[0]"),
        ([{"view": "front"}] * 9, "at most 6 views; got 9"),
        ([], "views is empty"),
        ([{"view": "custom"}], "does not give both azimuth and elevation"),
        ([{"view": "front", "azimuth": 30.0}],
         "angles belong to view 'custom'"),
        ([{"view": "front", "hide": ["housng"]}], "names no declared output"),
        ([{"view": "front", "hero": True}, {"view": "top", "hero": True}],
         "both flagged hero"),
        ([{"view": "front", "explode": 3}], "0 (assembled) to 1"),
        ([{"view": "front", "section": "Q"}], "one of X, Y, Z"),
        ([{"view": "front", "section_offset_mm": 4}], "no section axis"),
        ([{"view": "front", "section": "off", "section_flip": True}],
         "drop them"),
        ([{"view": "front", "hid": ["x"]}], "unknown key"),
        ([{"view": "front", "projection": "iso"}],
         "'ortho' or 'perspective'"),
        (["front"], "must be an object"),
    )
    for raw, fragment in cases:
        result, error = cadex_sheet.normalize_views(raw, outputs)
        check(result is None and fragment in error,
              "refused with {!r} in: {:s}".format(fragment,
                                                  error or "(no error)"))
    bad_hide = cadex_sheet.normalize_views(
        [{"view": "front", "hide": ["housng"]}], outputs)[1]
    check("housing, pin, shaft" in bad_hide,
          "the hide refusal names the declared outputs")
    check("Compose two sheets" in cadex_sheet.normalize_views(
              [{"view": "front"}] * 9, outputs)[1],
          "the cap refusal offers the fix: compose two sheets")

    # -- duplicates are allowed; overrides land in the spec ------------------
    specs, error = cadex_sheet.normalize_views(
        [{"view": "front", "hide": ["housing"], "explode": 0.5,
          "section": "z", "section_offset_mm": 4, "section_flip": True},
         {"view": "front"},
         {"view": "custom", "azimuth": 30, "elevation": 15},
         {"view": "three-quarter", "projection": "ortho"}], outputs)
    check(error == "" and len(specs) == 4,
          "duplicates and per-view overrides pass: " + (error or "ok"))
    check(specs[0]["hide"] == ("housing",) and specs[0]["explode"] == 0.5
          and specs[0]["section"] == {"axis": "Z", "offset_mm": 4.0,
                                      "flip": True},
          "the overrides are normalized into the spec")
    check(specs[2]["view"] == "custom" and not specs[2]["ortho"]
          and specs[2]["label"] == "custom 30/15",
          "a custom view defaults to perspective and labels its angles")
    check(specs[3]["ortho"] is True,
          "projection overrides the named view's default")
    meta = cadex_sheet.spec_meta(specs[0])
    check(meta["hide"] == ["housing"] and meta["explode"] == 0.5
          and meta["section"] == {"axis": "Z", "offset_mm": 4.0,
                                  "flip": True},
          "spec_meta is the JSON-safe record of the overrides")

    # -- choose_layout picks by shape ----------------------------------------
    one = cadex_sheet.normalize_views([{"view": "front"}], outputs)[0]
    two = cadex_sheet.normalize_views([{"view": "front"}, {"view": "top"}],
                                      outputs)[0]
    three = cadex_sheet.normalize_views(
        [{"view": "front"}, {"view": "top"}, {"view": "right"}], outputs)[0]
    mixed = cadex_sheet.normalize_views(
        [{"view": "front"}, {"view": "three-quarter"}, {"view": "top"}],
        outputs)[0]
    check(cadex_sheet.choose_layout("auto", one)[0] == "single",
          "auto: one view is a single")
    check(cadex_sheet.choose_layout("auto", two)[0] == "row",
          "auto: two orthos are a row")
    check(cadex_sheet.choose_layout("auto", three)[0] == "grid",
          "auto: an all-ortho sheet is a grid")
    check(cadex_sheet.choose_layout("auto", mixed)[:2] == ("hero", 1),
          "auto: one perspective among orthos is the hero, unflagged")
    check(cadex_sheet.choose_layout("hero", three)[:2] == ("hero", 2),
          "explicit hero with no candidate takes the last view")
    check(cadex_sheet.choose_layout("hero", one)[0] == "single",
          "a hero of one degenerates to single")
    check("Unknown layout 'hexagon'"
          in cadex_sheet.choose_layout("hexagon", one)[2],
          "unknown layouts are refused")
    check("takes one view" in cadex_sheet.choose_layout("single", two)[2],
          "single with two views is refused")
    check("takes at least 3 views"
          in cadex_sheet.choose_layout("triptych", two)[2],
          "a triptych of two is refused")

    # -- only: the isolate, normalized into the hide the apply path knows ----
    iso, error = cadex_sheet.normalize_views(
        [{"view": "front", "only": ["pin", "shaft"]}], outputs)
    check(error == "" and iso[0]["only"] == ("pin", "shaft")
          and iso[0]["hide"] == ("housing",),
          "only becomes the complement hide over the declared outputs")
    check(cadex_sheet.spec_meta(iso[0]).get("only") == ["pin", "shaft"]
          and "hide" not in cadex_sheet.spec_meta(iso[0]),
          "and the meta records the only, not its derived complement")
    for raw, fragment in (
            ([{"view": "front", "only": ["pin"], "hide": ["housing"]}],
             "both hide and only"),
            ([{"view": "front", "only": []}], "non-empty list"),
            ([{"view": "front", "only": ["gearz"]}],
             "names no declared output"),
    ):
        result, error = cadex_sheet.normalize_views(raw, outputs)
        check(result is None and fragment in error,
              "only refused with {!r} in: {:s}".format(
                  fragment, error or "(no error)"))

    # -- mosaic: freeform placement, held to the tiling invariant by refusal -
    placed, error = cadex_sheet.normalize_views(
        [{"view": "three-quarter", "cell": [1, 1], "span": [2, 2]},
         {"view": "front", "cell": [1, 3]},
         {"view": "top", "cell": [3, 1], "span": [1, 3]}], outputs)
    check(error == "" and placed[0]["cell"] == (1, 1)
          and placed[0]["span"] == (2, 2) and placed[1]["span"] == (1, 1),
          "cells and spans normalize, span defaulting to [1, 1]")
    check(cadex_sheet.choose_layout("auto", placed)[:2] == ("mosaic", None),
          "auto routes placed views to the mosaic")
    check(cadex_sheet.choose_layout("mosaic", placed)[:2]
          == ("mosaic", None),
          "and explicit mosaic agrees")
    rects, width, height = cadex_sheet.layout_rects(
        "mosaic", 3, 1024,
        cells=[(1, 1, 2, 2), (1, 3, 1, 1), (3, 1, 1, 3)])
    check((width, height) == (1024, 1024)
          and rects[0] == (0, 341, 683, 683)
          and rects[1] == (683, 683, 341, 341)
          and rects[2] == (0, 0, 1024, 341),
          "mosaic rects follow the shared boundaries, spans and all")
    canvas = bytearray(width * height)
    overlapped = False
    for x, y, w, h in rects:
        for row in range(y, y + h):
            start = row * width + x
            if any(canvas[start:start + w]):
                overlapped = True
            canvas[start:start + w] = b"\x01" * w
    check(not overlapped and not all(canvas),
          "no overlap, and the unclaimed cell stays a hole on purpose")
    wide_rects, wide_w, wide_h = cadex_sheet.layout_rects(
        "mosaic", 2, 1024, cells=[(1, 1, 1, 1), (1, 2, 1, 1)])
    check((wide_w, wide_h) == (1024, 512),
          "the field's aspect follows the grid, longest edge max_size")
    for raw, layout, fragment in (
            ([{"view": "front", "cell": [1, 1], "span": [2, 2]},
              {"view": "top", "cell": [2, 2]}], "auto", "overlap on the "
                                                        "mosaic"),
            ([{"view": "front", "cell": [1, 1]}, {"view": "top"}], "auto",
             "views[1] has none"),
            ([{"view": "front", "cell": [1, 1]}], "hero",
             "use layout 'mosaic'"),
            ([{"view": "front"}], "mosaic", "give every view a cell"),
    ):
        mosaic_specs, error = cadex_sheet.normalize_views(raw, outputs)
        check(error == "", "the mosaic fixture normalizes: " + error)
        _t, _h, error = cadex_sheet.choose_layout(layout, mosaic_specs)
        check(fragment in error,
              "mosaic refused with {!r} in: {:s}".format(
                  fragment, error or "(no error)"))
    for raw, fragment in (
            ([{"view": "front", "span": [2, 2]}], "span but no cell"),
            ([{"view": "front", "cell": [0, 1]}], "1-based"),
            ([{"view": "front", "cell": [1, 1], "span": [1, 0]}],
             "at least 1"),
            ([{"view": "front", "cell": [6, 1], "span": [2, 1]}],
             "up to 6 rows"),
    ):
        result, error = cadex_sheet.normalize_views(raw, outputs)
        check(result is None and fragment in error,
              "mosaic spec refused with {!r} in: {:s}".format(
                  fragment, error or "(no error)"))

    # -- layout_rects: exact tiling by paint-counting, at awkward sizes ------
    for template in ("single", "row", "column", "grid", "hero", "triptych"):
        for count in range(1, cadex_sheet.MAX_VIEWS + 1):
            if template == "single" and count > 1:
                continue
            for size in (256, 1023, 1024):
                rects, width, height = cadex_sheet.layout_rects(
                    template, count, size, hero=count - 1)
                tag = "{:s}/{:d}/{:d}".format(template, count, size)
                check(len(rects) == count, tag + ": one rect per view")
                canvas = bytearray(width * height)
                overlapped = False
                for x, y, w, h in rects:
                    for row in range(y, y + h):
                        start = row * width + x
                        if any(canvas[start:start + w]):
                            overlapped = True
                        canvas[start:start + w] = b"\x01" * w
                check(not overlapped and all(canvas),
                      tag + ": no gap, no overlap, whole canvas covered")
                if template == "hero" and count >= 2:
                    x, y, w, h = rects[count - 1]
                    areas = [rw * rh for _x, _y, rw, rh in rects]
                    check(areas[count - 1] == max(areas)
                          and areas.count(max(areas)) == 1
                          and x + w == width and h == height and x > 0,
                          tag + ": the hero cell is strictly largest, full "
                                "height, on the RIGHT")

    # rects come back in view order, hero placed by index
    rects, width, height = cadex_sheet.layout_rects("hero", 4, 1024, hero=3)
    check(rects[3] == (341, 0, 683, 1024),
          "the default hero cell is the right two-thirds at full height")
    check(all(rect[0] == 0 and rect[2] == 341 for rect in rects[:3])
          and [rect[3] for rect in rects[:3]] == [341, 342, 341],
          "the three orthos stack down the left at ~341 px")
    check(rects[0][1] > rects[1][1] > rects[2][1],
          "in view order, top to bottom")
    moved, _w, _h = cadex_sheet.layout_rects("hero", 4, 1024, hero=0)
    check(moved[0] == (341, 0, 683, 1024),
          "the hero index places the hero cell, whichever view it is")
    grid, width, height = cadex_sheet.layout_rects("grid", 3, 1024)
    check(grid[0][1] + grid[0][3] == height and grid[0][0] == 0,
          "a grid reads from the top-left")
    check(grid[2][2] == 1024,
          "a partial last row widens to span -- no hole")
    rects, width, height = cadex_sheet.layout_rects("triptych", 5, 1024)
    check((width, height) == (1024, 1024)
          and all(rect[0] == 0 and rect[2] == 341 for rect in rects[:3])
          and rects[0][1] > rects[1][1] > rects[2][1],
          "a triptych stacks the first views down the left third, top to "
          "bottom")
    check(rects[3] == (341, 0, 342, 1024)
          and rects[4] == (683, 0, 341, 1024),
          "and the last two views are full-height centre and right columns")

    # -- fit_view is view_matrices' loop body, field for field ---------------
    bbox = ((-30.0, -10.0, 0.0), (10.0, 50.0, 24.0))
    wrapped = capture.view_matrices(bbox, aspect=1.3)
    for index, view in enumerate(capture.VIEWS):
        check(capture.fit_view(view, bbox, aspect=1.3) == dict(wrapped[index]),
              "fit_view({:s}) equals view_matrices' entry".format(
                  view["name"]))

    # -- NAMED_VIEWS aim true, at every entry ---------------------------------
    centre = (-10.0, 20.0, 12.0)
    corners = [(x, y, z) for x in (-30.0, 10.0) for y in (-10.0, 50.0)
               for z in (0.0, 24.0)]
    axis_true = {"front": (0.0, -1.0, 0.0), "back": (0.0, 1.0, 0.0),
                 "left": (-1.0, 0.0, 0.0), "right": (1.0, 0.0, 0.0),
                 "top": (0.0, 0.0, 1.0), "bottom": (0.0, 0.0, -1.0)}
    for name, view in capture.NAMED_VIEWS.items():
        fitted = capture.fit_view(view, bbox)
        aimed = capture.transform(fitted["view"], centre)
        check(abs(aimed[0]) < 1e-6 and abs(aimed[1]) < 1e-6 and aimed[2] < 0,
              "{:s} looks at the bbox centre".format(name))
        projected = [capture.project(fitted["view"], fitted["window"], c)
                     for c in corners]
        check(all(p is not None and abs(p[0]) <= 1.0 and abs(p[1]) <= 1.0
                  and -1.0 <= p[2] <= 1.0 for p in projected),
              "{:s} contains the whole bbox".format(name))
        expected = axis_true.get(name)
        if expected is not None:
            check(max(abs(a - b) for a, b in
                      zip(fitted["direction"], expected)) < 1e-9,
                  "{:s} is axis-true".format(name))

    # -- composite_rects places by rect; the 2x2 wrapper is unchanged --------
    red, green, blue, white = ([1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0],
                               [0.0, 0.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0])
    direct = capture.composite_rects(
        [(red, (0, 1, 1, 1)), (green, (1, 1, 1, 1)),
         (blue, (0, 0, 1, 1)), (white, (1, 0, 1, 1))], 2, 2)
    wrapped_pixels, width, height = capture.composite_2x2(
        [red, green, blue, white], 1, 1)
    check((width, height) == (2, 2) and wrapped_pixels == direct,
          "composite_2x2 is composite_rects with the quadrant rects")
    tile = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    out = capture.composite_rects([(tile, (1, 0, 1, 2))], 3, 2)
    check(out[4:8] == tile[0:4] and out[16:20] == tile[4:8]
          and out[0:4] == [0.0] * 4,
          "a rect lands row by row exactly where it says")

    # -- the dressing arithmetic ----------------------------------------------
    check(cadex_sheet.margin_px(256) == 20
          and cadex_sheet.margin_px(1024) == 25,
          "the margin band scales with the sheet and floors at 20 px")
    grid = cadex_sheet.zone_grid(1074, 1074)
    check(grid["pitch"] == 130 and abs(grid["sub_pitch"] - 26.0) < 1e-9,
          "the zone pitch is a round pixel count with a fifth sub-grid")
    check([label for label, _x in grid["columns"]][:3] == ["1", "2", "3"]
          and [label for label, _y in grid["rows"]][:3] == ["A", "B", "C"],
          "columns are numbered along the top, rows lettered down the left")
    check(grid["rows"][0][1] > grid["rows"][-1][1],
          "row A sits at the TOP of the sheet")
    check(all(float(x) % grid["pitch"] == 0.0 for x in grid["verticals"]),
          "zone lines sit on the pitch")
    check(all(min(x % grid["pitch"], grid["pitch"] - x % grid["pitch"]) > 1.0
              for x in grid["sub_verticals"]),
          "the sub-grid skips the zone lines")

    titles = cadex_sheet.title_lines("bracket", "1.2.3", "abcdef123456789",
                                     "2026-08-19", "blueprint")
    check(titles[0] == {"corner": "top-left", "text": "bracket"},
          "the project name sits in the top corner")
    check(titles[1]["corner"] == "bottom-right"
          and "CADEX 1.2.3" in titles[1]["text"]
          and "rev abcdef123456" in titles[1]["text"]
          and "2026-08-19" in titles[1]["text"]
          and "blueprint" in titles[1]["text"],
          "the version block carries version, revision, date and theme")
    check("CADEX dev"
          in cadex_sheet.title_lines("", "", "", "", "")[0]["text"],
          "a missing version reads dev, not nothing")

    hero_specs, _error = cadex_sheet.normalize_views(
        [{"view": "front"}, {"view": "top"}, {"view": "right"},
         {"view": "three-quarter", "hero": True, "hide": ["housing"],
          "explode": 1.0}], outputs)
    rects, _width, _height = cadex_sheet.layout_rects("hero", 4, 1024,
                                                      hero=3)
    legend = cadex_sheet.cell_legend(hero_specs, rects)
    check("cell 4 (large, right): three-quarter perspective" in legend
          and "housing hidden" in legend and "exploded 1" in legend,
          "the legend names the hero cell and its overrides")
    check(legend.index("cell 1") < legend.index("cell 4"),
          "cells are captioned in view order")
    tri_specs, _error = cadex_sheet.normalize_views(None, outputs)
    tri_rects, _w2, _h2 = cadex_sheet.layout_rects("triptych", 5, 1024)
    tri_legend = cadex_sheet.cell_legend(tri_specs, tri_rects)
    check("cell 4 (large, centre)" in tri_legend
          and "cell 5 (right)" in tri_legend and "exploded 1" in tri_legend,
          "the triptych legend reads centre and right, not left/right "
          "halves")

    encoded = cadex_sheet.display_color((0.032, 0.082, 0.230))
    check(all(0.0 <= value <= 1.0 for value in encoded)
          and all(after > before for after, before
                  in zip(encoded, (0.032, 0.082, 0.230))),
          "display_color lifts the linear ground into display range")
    ends = cadex_sheet.display_color((0.0, 1.0, 2.0))
    check(ends[0] == 0.0 and abs(ends[1] - 1.0) < 1e-9
          and abs(ends[2] - 1.0) < 1e-9,
          "and is clamped at the ends")

    # -- ADR-153: the sheet's aspect ------------------------------------------
    check(cadex_sheet.sheet_aspect(None, "grid") == (16.0 / 9.0, ""),
          "an omitted aspect is 16:9")
    check(cadex_sheet.sheet_aspect(None, "mosaic") == (None, ""),
          "except on the mosaic, whose shape is the agent's grid")
    check(cadex_sheet.sheet_aspect("auto", "grid") == (None, ""),
          "'auto' follows the layout's own shape")
    check(cadex_sheet.sheet_aspect("4:3", "grid")[0] == 4.0 / 3.0
          and cadex_sheet.sheet_aspect("9:16", "grid")[0] == 9.0 / 16.0,
          "any width:height parses, portrait included")
    for bad in ("wide", "16:0", "0:9", "16:9:2"):
        ratio, error = cadex_sheet.sheet_aspect(bad, "grid")
        check(ratio is None and "width:height" in error,
              "aspect {!r} refused: {:s}".format(bad, error or "(none)"))
    check("between 1:5 and 5:1"
          in cadex_sheet.sheet_aspect("1:9", "grid")[1],
          "an extreme aspect names its bounds")

    rects, width, height = cadex_sheet.layout_rects("triptych", 5, 1024,
                                                    aspect=16.0 / 9.0)
    check((width, height) == (1024, 576)
          and rects[0] == (0, 384, 341, 192)
          and rects[3] == (341, 0, 342, 576)
          and rects[4] == (683, 0, 341, 576),
          "the default 16:9 triptych is three columns over 1024x576")
    for template in ("single", "row", "column", "grid", "hero", "triptych"):
        for count in (1, 3, 5):
            if template == "single" and count > 1:
                continue
            rects, width, height = cadex_sheet.layout_rects(
                template, count, 1023, hero=count - 1, aspect=16.0 / 9.0)
            tag = "16:9 {:s}/{:d}".format(template, count)
            canvas = bytearray(width * height)
            overlapped = False
            for x, y, w, h in rects:
                for row in range(y, y + h):
                    start = row * width + x
                    if any(canvas[start:start + w]):
                        overlapped = True
                    canvas[start:start + w] = b"\x01" * w
            check(not overlapped and all(canvas),
                  tag + ": exact tiling holds at 16:9 too")
    check(cadex_sheet.layout_rects("single", 1, 1024, aspect=0.5)[1:]
          == (512, 1024),
          "a portrait aspect keeps the longest edge at max_size")
    check(cadex_sheet.layout_rects(
              "mosaic", 2, 1024, cells=[(1, 1, 1, 1), (1, 2, 1, 1)],
              aspect=16.0 / 9.0)[1:] == (1024, 576),
          "an explicit aspect overrides the mosaic's grid shape")

    # -- ADR-153: part-name callouts ------------------------------------------
    check(cadex_sheet.callouts_active({"callouts": None, "explode": 1.0})
          and not cadex_sheet.callouts_active({"callouts": None,
                                               "explode": 0.0})
          and not cadex_sheet.callouts_active({"callouts": None,
                                               "explode": None})
          and not cadex_sheet.callouts_active({"callouts": False,
                                               "explode": 1.0})
          and cadex_sheet.callouts_active({"callouts": True}),
          "callouts default on for exploded cells; an explicit flag wins")
    named, error = cadex_sheet.normalize_views(
        [{"view": "front", "callouts": True},
         {"view": "top", "explode": 1.0, "callouts": False}], outputs)
    check(error == "" and named[0]["callouts"] is True
          and named[1]["callouts"] is False,
          "the callouts flag rides the spec")
    check(cadex_sheet.spec_meta(named[1]).get("callouts") is False,
          "and an explicit flag lands in the meta")
    result, error = cadex_sheet.normalize_views(
        [{"view": "front", "callouts": "yes"}], outputs)
    check(result is None and "true or false" in error,
          "a non-boolean callouts is refused")
    defaults, _error = cadex_sheet.normalize_views(None, outputs)
    check(cadex_sheet.callouts_active(defaults[4]),
          "the default sheet's exploded column names its parts")
    check("parts named" in cadex_sheet.cell_legend(
              defaults, cadex_sheet.layout_rects("triptych", 5, 1024)[0]),
          "and the legend says so")

    anchors = [("base", 100.0, 400.0), ("pin", 120.0, 380.0),
               ("swing", 500.0, 300.0)]
    entries, dropped = cadex_sheet.callout_layout(anchors, 600, 500, 12.0,
                                                  top_pad=20.0)
    check(dropped == 0 and len(entries) == 3,
          "every anchor gets a label when the cell has room")
    sides = {entry["name"]: entry["side"] for entry in entries}
    check(sides == {"base": "left", "pin": "left", "swing": "right"},
          "labels go to the side their anchor is on")
    lefts = sorted((entry for entry in entries if entry["side"] == "left"),
                   key=lambda entry: -entry["label_y"])
    check(lefts[0]["label_y"] - lefts[1]["label_y"] >= 12.0 + 6.0,
          "stacked labels keep the minimum spacing")
    check(all(abs(entry["label_x"] - 4.8) < 1e-9 for entry in lefts)
          and abs(next(entry for entry in entries
                       if entry["side"] == "right")["label_x"] - 595.2)
          < 1e-9,
          "label_x is the outer text edge on each side")
    crowded = [("p{:d}".format(index), 10.0, 30.0) for index in range(5)]
    entries, dropped = cadex_sheet.callout_layout(crowded, 600, 40, 12.0)
    check(dropped == 3 and len(entries) == 2,
          "a cell too small for its callouts drops the excess, counted")
    check(cadex_sheet.callout_layout(crowded, 600, 10, 12.0) == ((), 5),
          "a cell with no label band drops them all")
    check(cadex_sheet.callout_layout(anchors, 200, 500, 12.0) == ((), 3),
          "and so does a cell too narrow to carry names beside the model")

    # -- ADR-153: the parameters panel ----------------------------------------
    panel, error = cadex_sheet.normalize_views(
        [{"view": "three-quarter"}, {"view": "params"}], outputs)
    check(error == "" and panel[1]["view"] == "params"
          and panel[1]["label"] == "parameters" and panel[1]["ortho"]
          and panel[1]["hide"] == (),
          "a params cell normalizes: a cell of the sheet, not of the model")
    check(cadex_sheet.spec_meta(panel[1]) == {"view": "params",
                                              "label": "parameters"},
          "and its meta is just what it is")
    placed_panel, error = cadex_sheet.normalize_views(
        [{"view": "front", "cell": [1, 1]},
         {"view": "params", "cell": [1, 2], "span": [2, 1]}], outputs)
    check(error == ""
          and placed_panel[1]["cell"] == (1, 2)
          and placed_panel[1]["span"] == (2, 1),
          "a params cell places and spans on the mosaic like any view")
    result, error = cadex_sheet.normalize_views(
        [{"view": "params", "explode": 1.0}], outputs)
    check(result is None
          and "takes only cell, span, hero, aspect and title" in error
          and "explode" in error,
          "camera and scene keys on a params cell are refused by name")
    check("parameters panel" in cadex_sheet.cell_legend(
              panel, cadex_sheet.layout_rects("row", 2, 512)[0]),
          "the legend names the panel")

    rows = cadex_sheet.param_rows(
        [{"name": "bore", "default": 6.0, "min": 2.0, "max": 14.0,
          "unit": "mm", "label": "Bore"},
         {"name": "tooth_count", "default": 4.0},
         {"name": "offset", "default": -2.0},
         {"default": 1.0}], {"bore": 8.0})
    check(len(rows) == 3, "a nameless spec is skipped, as the bridge does")
    check(rows[0]["label"] == "Bore" and rows[0]["value_text"] == "8 mm"
          and abs(rows[0]["fraction"] - 0.5) < 1e-9,
          "a declared range places the knob at the value's fraction")
    check(rows[1]["label"] == "Tooth Count"
          and (rows[1]["min"], rows[1]["max"]) == (0.0, 16.0)
          and abs(rows[1]["fraction"] - 0.25) < 1e-9,
          "an undeclared range defaults exactly as the slider bridge does")
    check((rows[2]["min"], rows[2]["max"]) == (-8.0, 1.0),
          "and a negative default gets the bridge's negative range")
    clamped = cadex_sheet.param_rows(
        [{"name": "bore", "default": 6.0, "min": 2.0, "max": 14.0}],
        {"bore": 99.0})
    check(clamped[0]["fraction"] == 1.0,
          "an out-of-range value clamps the knob, not the panel")

    layout_info = cadex_sheet.params_panel_layout(4, 341, 576)
    check(layout_info["shown"] == 4 and layout_info["more"] == 0
          and layout_info["row_height"] == 46.0,
          "four params in a tall cell all fit at the full row height")
    squeezed = cadex_sheet.params_panel_layout(20, 200, 150)
    check(squeezed["shown"] == 4 and squeezed["more"] == 16,
          "a small cell shows what fits and counts the rest as +N more")
    # ADR-157: the cell's own label is drawn over it by the sheet dressing,
    # and a windowed probe found the first slider row running through it.
    capped = cadex_sheet.params_panel_layout(6, 341, 144, top_pad=28.0)
    check(capped["shown"] < cadex_sheet.params_panel_layout(
              6, 341, 144)["shown"] and capped["more"] > 0,
          "a params cell yields rows to the band its title is drawn in")

    # -- the tool advertises the composition surface --------------------------
    entry = next(e for e in tools.TOOL_DEFS if e["name"] == "make_blueprint")
    properties = entry["input_schema"]["properties"]
    check("views" in properties and "layout" in properties
          and "aspect" in properties,
          "make_blueprint's schema advertises views, layout and aspect")
    check("params" in properties["views"]["items"]["properties"]["view"]
          ["enum"],
          "and the view enum offers the parameters panel")
    check(properties["views"]["maxItems"] == cadex_sheet.MAX_VIEWS,
          "and caps views at the module's MAX_VIEWS")
    check(set(properties["views"]["items"]["properties"])
          == set(cadex_sheet.SPEC_KEYS),
          "the per-view schema is exactly the spec keys, one level deep")
    check(tuple(properties["layout"]["enum"]) == cadex_sheet.LAYOUTS,
          "and the layout enum is the module's LAYOUTS")


def test_blueprint_sheets_are_named_shaped_and_revisable():
    """ADR-157's pure half: per-cell shape, text panels, and the recipe.

    Three properties carry the feature, and each one is a property rather
    than an example: **the tiling invariant survives weighting** (checked by
    the same paint-counting the templates get, over random asks), **a cell
    that asks for a shape gets measurably closer to it**, and **a recipe
    round-trips** — ``normalize_views(recipe_views(specs)) == specs``, which
    is what makes a stored sheet revisable rather than merely recorded.
    """
    print("test_blueprint_sheets_are_named_shaped_and_revisable")
    import random

    from mesh_agent import cadex_sheet, tools

    outputs = ("housing", "pin", "shaft")

    def paint(rects, width, height):
        canvas = bytearray(width * height)
        overlapped = False
        for x, y, w, h in rects:
            if w <= 0 or h <= 0:
                return False, False
            for row in range(y, y + h):
                start = row * width + x
                if any(canvas[start:start + w]):
                    overlapped = True
                canvas[start:start + w] = b"\x01" * w
        return not overlapped, all(canvas)

    # -- a cell's own aspect: parsed like the sheet's, refused like it ------
    check(cadex_sheet.parse_aspect("1:3")[0] == 1.0 / 3.0
          and cadex_sheet.parse_aspect("auto") == (None, ""),
          "parse_aspect is one parser for the sheet's shape and a cell's")
    for raw, fragment in (
            ([{"view": "front", "aspect": "tall"}], "must be 'width:height'"),
            ([{"view": "front", "aspect": "1:9"}], "between 1:5 and 5:1"),
            ([{"view": "front", "aspect": "auto"}], "omit it to take the "
                                                    "layout's own shape"),
    ):
        result, error = cadex_sheet.normalize_views(raw, outputs)
        check(result is None and fragment in error,
              "cell aspect refused with {!r} in: {:s}".format(
                  fragment, error or "(no error)"))
    shaped, error = cadex_sheet.normalize_views(
        [{"view": "front"}, {"view": "top"},
         {"view": "custom", "azimuth": 225, "elevation": 25, "explode": 1.0,
          "aspect": "1:3"}], outputs)
    check(error == "" and abs(shaped[2]["aspect"] - 1.0 / 3.0) < 1e-9
          and "aspect" not in shaped[0],
          "the ask rides the spec, and only where it was made")

    # -- the tiling invariant survives weighting -----------------------------
    random.seed(157)
    asks = (None, None, 0.25, 0.5, 1.0, 2.0, 4.0)
    for template in ("row", "column", "grid", "hero", "triptych"):
        for count in range(2, cadex_sheet.MAX_VIEWS + 1):
            if template == "triptych" and count < 3:
                continue
            for size in (256, 1023):
                for sheet in (None, 16.0 / 9.0, 0.5):
                    wanted = [random.choice(asks) for _ in range(count)]
                    rects, width, height = cadex_sheet.layout_rects(
                        template, count, size, hero=count - 1, aspect=sheet,
                        aspects=wanted)
                    clean, whole = paint(rects, width, height)
                    check(clean and whole,
                          "{:s}/{:d}/{:d}: weighted tiling still covers the "
                          "canvas exactly once".format(template, count, size))

    # -- and a cell that asks gets measurably closer -------------------------
    plain, _w, _h = cadex_sheet.layout_rects("triptych", 5, 1024,
                                             aspect=16.0 / 9.0)
    asked, width, height = cadex_sheet.layout_rects(
        "triptych", 5, 1024, aspect=16.0 / 9.0,
        aspects=[None, None, None, None, 1.0 / 3.0])
    before = plain[4][2] / float(plain[4][3])
    after = asked[4][2] / float(asked[4][3])
    check(abs(after - 1.0 / 3.0) < abs(before - 1.0 / 3.0)
          and abs(after - 1.0 / 3.0) < 0.05,
          "a 1:3 ask on the right column lands within 0.05 of 1:3 "
          "(was {:.2f}, now {:.2f})".format(before, after))
    check((width, height) == (1024, 576),
          "and the sheet's own shape is untouched by a cell's ask")
    check(sum(rect[2] for rect in asked[-2:]) + asked[0][2] == width,
          "the columns still share their boundaries exactly")
    exact, _w, _h = cadex_sheet.layout_rects(
        "row", 3, 1024, aspect=None, aspects=[None, 3.0, None])
    check(abs(exact[1][2] / float(exact[1][3]) - 3.0) < 0.02,
          "on an auto sheet the ask is met outright")
    check(cadex_sheet.layout_rects("single", 1, 1024, aspects=[0.4])[1:]
          == (410, 1024),
          "one cell IS the field, so its ask is the sheet's shape")
    check(cadex_sheet.layout_rects("single", 1, 1024, aspect=16.0 / 9.0,
                                   aspects=[0.4])[1:] == (1024, 576),
          "...unless the sheet stated one, which wins")

    # An ask nobody can satisfy must not produce slivers.
    crowded, width, height = cadex_sheet.layout_rects(
        "row", 6, 256, aspect=16.0 / 9.0, aspects=[0.2] * 6)
    clean, whole = paint(crowded, width, height)
    check(clean and whole and all(rect[2] >= 8 for rect in crowded),
          "six impossible asks on one small sheet stay drawable")

    # -- the legend reports the shape it drew, not the shape asked for -------
    legend = cadex_sheet.cell_legend(shaped, cadex_sheet.layout_rects(
        "triptych", 3, 1024, aspect=16.0 / 9.0,
        aspects=[spec.get("aspect") for spec in shaped])[0])
    check("asked 1:3, drawn 1:" in legend,
          "the caption is the agent's feedback channel: " + legend)

    # -- text panels ---------------------------------------------------------
    panels, error = cadex_sheet.normalize_views(
        [{"view": "three-quarter"},
         {"view": "text", "text": "M3 threads.\nDeburr all edges.",
          "title": "notes to the shop", "aspect": "1:2"}], outputs)
    check(error == "" and panels[1]["view"] == "text"
          and panels[1]["label"] == "notes to the shop"
          and panels[1]["text"] == "M3 threads.\nDeburr all edges.",
          "a text panel normalizes with its words and its heading")
    check(cadex_sheet.spec_meta(panels[1]) == {
              "view": "text", "label": "notes to the shop", "chars": 29,
              "aspect": "1:2"},
          "and its RECORD counts the characters -- the recipe keeps the "
          "text, so a panel's words are not stored twice")
    for raw, fragment in (
            ([{"view": "text"}], "carries no text"),
            ([{"view": "text", "text": "  "}], "carries no text"),
            ([{"view": "text", "text": "x" * 501}], "Split it across two"),
            ([{"view": "text", "text": "hi", "explode": 1.0}],
             "is the text panel"),
            ([{"view": "params", "text": "hi"}], "text belongs to view"),
            ([{"view": "front", "text": "hi"}], "a panel of words is view"),
            ([{"view": "front", "title": "x" * 61}], "the cap is 60"),
            ([{"view": "front", "title": " "}], "must be a line of text"),
    ):
        result, error = cadex_sheet.normalize_views(raw, outputs)
        check(result is None and fragment in error,
              "text panel refused with {!r} in: {:s}".format(
                  fragment, error or "(no error)"))
    check("text panel, 'M3 threads. Deburr all edges.'"
          in cadex_sheet.cell_legend(
              panels, cadex_sheet.layout_rects("row", 2, 512)[0]),
          "the legend quotes what the panel says")
    titled, error = cadex_sheet.normalize_views(
        [{"view": "front", "title": "section A-A"}], outputs)
    check(error == "" and titled[0]["label"] == "section A-A",
          "a title renames any cell, not just a panel")

    # -- wrapping is measured, not counted -----------------------------------
    lines, dropped = cadex_sheet.wrap_text(
        "the quick brown fox jumps over the lazy dog", len, 12)
    check(dropped == 0 and all(len(line) <= 12 for line in lines)
          and " ".join(lines) == "the quick brown fox jumps over the lazy dog",
          "wrapping loses no words and breaks under the width: {!r}".format(
              lines))
    paragraphs, _dropped = cadex_sheet.wrap_text("one\n\ntwo", len, 20)
    check(paragraphs == ("one", "", "two"),
          "a blank line between paragraphs is kept")
    check(cadex_sheet.wrap_text("one\n\n\n", len, 20)[0] == ("one",),
          "and trailing blanks are not")
    broken, _dropped = cadex_sheet.wrap_text("M3x0.5-6H-THROUGH-BORE", len, 8)
    check(all(len(line) <= 8 for line in broken)
          and "".join(broken) == "M3x0.5-6H-THROUGH-BORE",
          "a word with no spaces in it is broken by character, not clipped")
    clipped, dropped = cadex_sheet.wrap_text("a b c d e f g h", len, 3,
                                             max_lines=2)
    check(clipped == ("a b", "c d") and dropped == 2,
          "what does not fit is counted, so the caption can say so")

    shape = cadex_sheet.text_panel_layout(341, 576, top_pad=24.0)
    check(shape["max_lines"] > 1 and shape["text_width"] < 341
          and 9.0 <= shape["text_size"] <= 15.0,
          "a text cell divides into readable rows inside its padding")
    check(cadex_sheet.text_panel_layout(200, 40)["max_lines"] >= 1,
          "and a cell too short for a line still reports one, not zero")

    # -- the recipe round-trips ----------------------------------------------
    composed, error = cadex_sheet.normalize_views(
        [{"view": "front", "hide": ["housing"], "section": "z",
          "section_offset_mm": 4, "section_flip": True, "aspect": "2:1"},
         {"view": "custom", "azimuth": 225, "elevation": 25, "explode": 1.0,
          "callouts": False, "title": "exploded rear"},
         {"view": "top", "only": ["pin", "shaft"], "hero": True},
         {"view": "params"},
         {"view": "text", "text": "Bill of materials:\n2x M3 bolt"}],
        outputs)
    check(error == "", "the composed fixture normalizes: " + (error or "ok"))
    again, error = cadex_sheet.normalize_views(
        cadex_sheet.recipe_views(composed), outputs)
    check(error == "" and again == composed,
          "normalize_views(recipe_views(specs)) == specs -- a stored sheet "
          "can be drawn again: " + (error or "ok"))
    defaults, _error = cadex_sheet.normalize_views(None, outputs)
    round_tripped, error = cadex_sheet.normalize_views(
        cadex_sheet.recipe_views(defaults), outputs)
    check(error == "" and round_tripped == defaults,
          "the DEFAULT sheet round-trips too, so 'change one cell of the "
          "default' needs no restatement of the other four")
    placed, _error = cadex_sheet.normalize_views(
        [{"view": "front", "cell": [1, 1], "span": [2, 1]},
         {"view": "text", "text": "notes", "cell": [1, 2]}], outputs)
    check(cadex_sheet.normalize_views(cadex_sheet.recipe_views(placed),
                                      outputs)[0] == placed,
          "and so does a mosaic, placements and panels included")

    recipe = cadex_sheet.sheet_recipe(composed, "grey", "mosaic", "4:3", 800)
    check(recipe["theme"] == "grey" and recipe["layout"] == "mosaic"
          and recipe["aspect"] == "4:3" and recipe["max_size"] == 800
          and len(recipe["views"]) == 5,
          "the sheet recipe carries everything make_blueprint needs again")

    # -- meta is trimmed before the engine can refuse it ---------------------
    fat = {"recipe": recipe, "views": [{"pad": "y" * 400}] * 8,
           "rects": [[0, 0, 10, 10]] * 8, "theme": "grey"}
    trimmed = cadex_sheet.trim_meta(fat, 2048)
    check("recipe" in trimmed and "rects" not in trimmed
          and "views" not in trimmed,
          "the recipe is what a trim defends -- without it the sheet stops "
          "being revisable")
    check(cadex_sheet.trim_meta(fat, 64 * 1024) == fat,
          "and a meta that fits is untouched")

    # -- the tool advertises all of it ---------------------------------------
    entry = next(e for e in tools.TOOL_DEFS if e["name"] == "make_blueprint")
    properties = entry["input_schema"]["properties"]
    check("based_on" in properties,
          "make_blueprint's schema advertises based_on")
    check(set(properties["views"]["items"]["properties"])
          == set(cadex_sheet.SPEC_KEYS),
          "the per-view schema is still exactly the spec keys")
    check("text" in properties["views"]["items"]["properties"]["view"]["enum"],
          "and the view enum offers the text panel")
    check(all(word in entry["description"]
              for word in ("based_on", "text", "aspect")),
          "and the description tells the model the three new moves")


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


def test_training_plot_layout_is_pure_arithmetic():
    """The reward-curve plot's numbers, with no region and no GPU.

    The draw handler draws exactly what ``plot_layout`` returns, so the
    None-cases here are the handler's early exits and the pixel arithmetic
    here is the plot.
    """

    from mesh_agent import cadex_training_plot as plot

    # curve_from tolerates everything an old or torn progress file can be.
    check(plot.curve_from(None) == [], "no report reads as no curve")
    check(plot.curve_from({}) == [], "a report without the field too")
    check(plot.curve_from({"curve": "oops"}) == [],
          "...and one where the field is not a list")
    check(plot.curve_from({"curve": [[0, 1.0], [1]]}) == [],
          "a torn pair poisons nothing: the whole curve reads as absent")
    check(plot.curve_from({"curve": [[0, 1.0], [1, float("nan")]]}) == [],
          "...and so does a NaN")
    points = plot.curve_from({"curve": [[0, -0.5], [10, 0.25], [20, 2.0]]})
    check(points == [(0, -0.5), (10, 0.25), (20, 2.0)],
          "a sound curve arrives as (iteration, reward) pairs")

    # The None-cases the handler early-exits on.
    check(plot.plot_layout(800, 600, []) is None, "no points, no plot")
    check(plot.plot_layout(800, 600, [(0, 1.0)]) is None,
          "one point is a dot, not a curve")
    check(plot.plot_layout(100, 600, points) is None,
          "a sliver of a region draws panel-only")

    layout = plot.plot_layout(800, 600, points, best_iteration=10, total=50)
    check(layout is not None, "a real curve in a real region lays out")
    x0, y0, x1, y1 = layout["frame"]
    check(y1 <= 600 * plot.PLOT_FRACTION + 1e-9,
          "the plot keeps to the bottom of the region; the panel owns the top")
    xs = [point[0] for point in layout["polyline"]]
    check(xs == sorted(xs) and len(set(xs)) == len(xs),
          "iteration maps to x monotonically")
    check(abs(xs[0] - x0) < 1e-9, "the first iteration sits on the frame")
    check(xs[-1] < x1 - 1e-9,
          "with total=50 the curve has room to grow: iteration 20 is "
          "inside the frame, not on its right edge")
    ys = [point[1] for point in layout["polyline"]]
    check(all(y0 - 1e-9 <= y <= y1 + 1e-9 for y in ys),
          "every reward lands inside the frame")
    check(layout["best"] == layout["polyline"][1],
          "the best marker sits on its own curve point")
    check(layout["zero"] is not None and y0 < layout["zero"] < y1,
          "a curve crossing zero draws the zero line inside the frame")
    check(layout["ticks"] and all(
        y0 - 1e-9 <= y <= y1 + 1e-9 for y, _ in layout["ticks"]),
        "ticks land inside the frame")
    labels = [label for _, label in layout["ticks"]]
    check(len(set(labels)) == len(labels), "and no two ticks read the same")

    # A flat curve pads its range rather than dividing by zero.
    flat = plot.plot_layout(800, 600, [(0, 1.0), (1, 1.0), (2, 1.0)])
    check(flat is not None, "a flat curve still lays out")
    flat_ys = {round(point[1], 6) for point in flat["polyline"]}
    check(len(flat_ys) == 1, "...flat")
    only = flat["polyline"][0][1]
    check(flat["frame"][1] < only < flat["frame"][3],
          "...and mid-frame, not on an edge")

    # An all-negative run keeps zero out of the frame rather than wasting
    # half of it on empty space.
    sunk = plot.plot_layout(800, 600, [(0, -3.0), (1, -2.0), (2, -2.5)])
    check(sunk is not None and sunk["zero"] is None,
          "zero is only drawn when the curve crosses it")

    check(plot.axis_ticks(0.0, 0.0) == [], "a degenerate range has no ticks")
    ticks = plot.axis_ticks(-0.13, 2.62)
    check(ticks and all(-0.13 <= value <= 2.62 for value in ticks),
          "ticks stay inside the range")
    steps = {round(b - a, 9) for a, b in zip(ticks, ticks[1:])}
    check(len(steps) == 1, "and are evenly spaced on a round step")


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
        test_native_menu_targets_exist()
        test_landing_layout_is_pure_and_hit_testable()
        test_landing_degrades_without_a_demo()
        test_landing_shows_dismisses_and_yields_to_chat()
        test_confirming_the_input_sends()
        test_every_chat_action_is_in_one_row_under_the_message_box()
        test_message_box_widget_is_available()
        test_the_mesh_tools_are_not_deferred_behind_a_disabled_tool()
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
        test_blueprint_styles_the_viewport_from_one_table()
        test_blueprint_sheets_compose_from_pure_arithmetic()
        test_blueprint_sheets_are_named_shaped_and_revisable()
        test_dimension_is_drawn_in_pixels_around_its_number()
        test_an_edge_on_dimension_becomes_a_leader()
        test_diameter_picks_the_widest_on_screen_and_survives_a_bore_down_z()
        test_measurement_anchors_follow_the_placement_of_what_they_measure()
        test_training_plot_layout_is_pure_arithmetic()
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
