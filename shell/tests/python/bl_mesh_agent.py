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

CUBE_MODEL = """\
from mesh_model import params, Float

p = params(
    size=Float(1.0, min=0.2, max=4.0, name="Size",
               description="Cube edge length"),
)

import bpy
bpy.ops.mesh.primitive_cube_add(size=p.size)
bpy.context.active_object.name = "ParamCube"
"""


def check(condition, label):
    status = "ok" if condition else "FAIL"
    print("  {:s}: {:s}".format(status, label))
    if not condition:
        FAILURES.append(label)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # These tests exercise the *local* model path (exec() in Blender). Cadex
    # is the default mode since cadex ADR-024, so say which path is under
    # test rather than depending on the default staying put.
    bpy.context.scene.mesh_agent_mode = 'GENERAL' 


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


def test_model_rebuild_and_params():
    """The parametric core, without the agent: script -> scene -> sliders."""
    print("test_model_rebuild_and_params")
    reset_scene()
    scene = bpy.context.scene

    model_module.set_script(CUBE_MODEL)
    ok, report = model_module.rebuild()
    check(ok, "rebuild succeeds ({:s})".format(report.splitlines()[0] if report else ""))
    cube = bpy.data.objects.get("ParamCube")
    check(cube is not None, "script created the cube")
    check(cube is not None and abs(cube.dimensions.x - 1.0) < 1e-4,
          "default parameter value applied")
    check(cube is not None
          and any(c.name == model_module.COLLECTION_NAME
                  for c in cube.users_collection),
          "cube lives in the Model collection")

    specs = model_module.load_specs(scene)
    check(len(specs) == 1 and specs[0]["id"] == "size"
          and specs[0]["type"] == 'FLOAT',
          "parameter spec saved to the scene")
    check(hasattr(scene, "mesh_params") and hasattr(scene.mesh_params, "size"),
          "slider property group registered")

    # Change the value the way the set_params tool / a slider would.
    ok, _report = model_module.set_values({"size": 2.0})
    check(ok, "set_values rebuild succeeds")
    cube = bpy.data.objects.get("ParamCube")
    check(cube is not None and abs(cube.dimensions.x - 2.0) < 1e-4,
          "rebuild used the new value")
    check(len(bpy.data.objects) == 1, "rebuild replaced, not duplicated")

    # Out-of-range values clamp to the declared max.
    ok, _report = model_module.set_values({"size": 99.0})
    cube = bpy.data.objects.get("ParamCube")
    check(ok and cube is not None and abs(cube.dimensions.x - 4.0) < 1e-4,
          "values clamp to the declared range")

    ok, _report = model_module.set_values({"nope": 1.0})
    check(not ok, "unknown parameter rejected")

    # Edit the script (same param id, extra object): stored value persists.
    model_module.set_script(CUBE_MODEL + "\n"
                            "bpy.ops.mesh.primitive_uv_sphere_add(radius=p.size / 2)\n"
                            "bpy.context.active_object.name = 'ParamBall'\n")
    ok, _report = model_module.rebuild()
    cube = bpy.data.objects.get("ParamCube")
    check(ok and "ParamBall" in bpy.data.objects,
          "edited script rebuilds with new object")
    check(cube is not None and abs(cube.dimensions.x - 4.0) < 1e-4,
          "stored value survives a script edit with a stable id")


def test_params_persist_through_save_load():
    """Script, specs and user-set values must round-trip through the .blend."""
    print("test_params_persist_through_save_load")
    reset_scene()
    model_module.set_script(CUBE_MODEL)
    ok, _report = model_module.rebuild()
    check(ok, "initial rebuild succeeds")
    ok, _report = model_module.set_values({"size": 2.5})
    check(ok, "value change rebuild succeeds")

    path = os.path.join(tempfile.gettempdir(), "mesh_param_persist.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=path)
    try:
        scene = bpy.context.scene
        check(model_module.get_script().strip() != "", "model script restored")
        specs = model_module.load_specs(scene)
        check(any(spec["id"] == "size" for spec in specs),
              "parameter specs restored")
        stored = model_module.stored_values(scene).get("size", 0.0)
        check(abs(stored - 2.5) < 1e-4,
              "user-set value restored (got {!s})".format(stored))
        cube = bpy.data.objects.get("ParamCube")
        check(cube is not None and abs(cube.dimensions.x - 2.5) < 1e-4,
              "geometry restored from the file")
        ok, _report = model_module.rebuild()
        cube = bpy.data.objects.get("ParamCube")
        check(ok and cube is not None and abs(cube.dimensions.x - 2.5) < 1e-4,
              "rebuild after load reproduces the model")
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_mock_turn_builds_model_with_single_undo():
    print("test_mock_turn_builds_model_with_single_undo")
    reset_scene()
    script = [[
        ("text", "Building a cube.\n"),
        ("tool", "write_script", {"content": CUBE_MODEL}),
        ("tool", "scene_summary", {}),
        ("text", "Done."),
        ("result", False, "Done."),
    ]]
    agent, holder, undo_pushes = make_agent(script)
    try:
        check(run_turn(agent, "build a cube"), "turn completes")
        check("ParamCube" in bpy.data.objects, "cube exists in scene")
        check(len(undo_pushes) == 1, "exactly one undo push per turn")
        check(undo_pushes and undo_pushes[0].startswith("Mesh: "),
              "undo push is labelled")

        backend = holder["backend"]
        write_reply = backend.tool_results[0][1]
        check(write_reply["is_error"] is False, "write_script succeeded")
        check("Rebuilt OK" in write_reply["content"][0]["text"]
              and "size=" in write_reply["content"][0]["text"],
              "rebuild report includes objects and parameters")
        summary_reply = backend.tool_results[1][1]
        summary = json.loads(summary_reply["content"][0]["text"])
        check(any(entry["name"] == "ParamCube" for entry in summary["objects"]),
              "scene_summary reports the cube")

        texts = [message.text for message in agent.history.messages]
        check(any("Building a cube." in text for text in texts),
              "streamed text reached the transcript")
        check(agent.history.messages[0].role == "user",
              "transcript starts with the user prompt")
    finally:
        agent.shutdown()


def test_script_error_roundtrip():
    print("test_script_error_roundtrip")
    reset_scene()
    script = [[
        ("tool", "write_script", {"content": "1/0\n"}),
        ("text", "That failed."),
        ("result", False, "That failed."),
    ]]
    agent, holder, undo_pushes = make_agent(script)
    try:
        check(run_turn(agent, "divide by zero"), "turn completes")
        reply = holder["backend"].tool_results[0][1]
        check(reply["is_error"] is True, "tool result flagged is_error")
        check("ZeroDivisionError" in reply["content"][0]["text"],
              "traceback returned to the model")
        check(len(undo_pushes) == 0, "no undo push when the rebuild failed")
    finally:
        agent.shutdown()


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

        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "write_script",
                         "arguments": {"content":
                                       "import bpy\n"
                                       "bpy.ops.mesh.primitive_uv_sphere_add()\n"
                                       "bpy.context.active_object.name = 'ShimSphere'\n"
                                       "print('sphere ok')"}}})
        call_reply = wait_for(3)
        check(call_reply is not None
              and call_reply["result"]["isError"] is False
              and "sphere ok" in call_reply["result"]["content"][0]["text"],
              "tools/call rebuilt the model in Blender and returned stdout")
        check("ShimSphere" in bpy.data.objects,
              "object created on the Blender main thread")
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


def main():
    print("=== bl_mesh_agent tests ===")
    mesh_agent.register()
    try:
        test_bridge_chunked_request()
        test_model_rebuild_and_params()
        test_params_persist_through_save_load()
        test_mock_turn_builds_model_with_single_undo()
        test_image_attachment_roundtrip()
        test_script_error_roundtrip()
        test_tool_call_cap()
        test_transcript_persistence()
        test_session_id_round_trips_and_is_per_file()
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
