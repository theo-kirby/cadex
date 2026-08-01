# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Headless tests for the Wiring graph (ADR-066).

Run:
    blender --background --factory-startup --python tests/python/bl_mesh_agent_wiring.py

**Everything here runs without an engine and without a rebuilt shell.** The
node tree, its sockets, its links, the sync, the layout-preserving reconcile,
the contract GC and the push payload are all exercised against fabricated
``inspect scope="wiring"`` payloads — which is the whole reason the model was
kept separate from the chrome. What cannot be covered here is the C++ half
(the editor appearing on the menu, and the link-drag gesture itself, since
``node.link`` does not exist in a bundle that never registered the space
type); those live in ``bl_mesh_agent.py::test_editor_menu_is_short`` and need
a build.

Two of these are regression tests for behaviour the Blender API forces on us
rather than for bugs we wrote: duplicate socket names dedup into
``sda``/``sda_001`` so a name is not an identity, and ``NodeTree.update()``
fires on our own mutations so a sync that did not suspend it would answer its
own edit forever.
"""

import os
import sys

import bpy

_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import mesh_agent  # noqa: E402
from mesh_agent import wiring  # noqa: E402
from mesh_agent import wiring_ui  # noqa: E402
from mesh_agent import cadex_hydrate  # noqa: E402
from mesh_agent import cadex_pick  # noqa: E402
from mesh_agent import cadex_terminal_pick as pick  # noqa: E402

FAILURES = []


def check(condition, label):
    print("  {:s}: {:s}".format("ok" if condition else "FAIL", label))
    if not condition:
        FAILURES.append(label)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


SIGNALS = ("sda", "scl", "gnd")


def _terminals(names=SIGNALS, kind="hole"):
    return [
        {
            "name": name,
            "point": [0.0, 2.54 * index, 0.0],
            "direction": [0.0, 0.0, 1.0],
            "kind": kind,
            "radius": 0.5,
            "depth": 1.6,
        }
        for index, name in enumerate(names)
    ]


def _state(ports=("sen", "esp"), wires=None, editable=True, revision="r1"):
    return {
        "revision": revision,
        "source": "nets" if editable else "derived",
        "editable": editable,
        "components": [
            {
                "port": port,
                "output": port + "_board",
                "domain": "part",
                "terminals": _terminals(),
            }
            for port in ports
        ],
        "wires": list(wires if wires is not None else [
            {"name": "sda", "a": "sen.sda", "b": "esp.sda",
             "gauge_mm": 0.8, "solder": True, "enabled": True},
        ]),
    }


def _fresh_tree():
    reset_scene()
    scene = bpy.context.scene
    tree = wiring.ensure_tree(scene)
    return scene, tree


# ---------------------------------------------------------------------------


def test_the_wiring_tree_registers():
    print("test_the_wiring_tree_registers")
    scene, tree = _fresh_tree()
    check(tree is not None, "ensure_tree returns a tree")
    check(tree.bl_idname == "CadexWiringTree", "of the Cadex tree type")
    check(scene.cadex_wiring == tree, "and the scene points at it")
    # A real user, so it saves in the .blend without a fake user.
    check(tree.users >= 1, "the scene pointer is a real user")
    check(wiring.ensure_tree(scene) is tree, "ensure_tree is find-or-create")


def test_a_board_node_names_a_script_output():
    """The join between the graph and the viewport, asserted not assumed."""
    print("test_a_board_node_names_a_script_output")
    properties = wiring.CadexBoardNode.bl_rna.properties
    check("cadex_output" in properties, "a board node carries cadex_output")
    check(cadex_hydrate.OUTPUT_PROP == "cadex_output",
          "and it is the same string cadex_hydrate keys objects by")


def test_a_terminal_is_keyed_by_property_not_by_name():
    """Blender dedups duplicate socket names; a name is not an identity."""
    print("test_a_terminal_is_keyed_by_property_not_by_name")
    _scene, tree = _fresh_tree()
    node = tree.nodes.new(wiring.CadexBoardNode.bl_idname)
    first = node.inputs.new(wiring.CadexTerminalSocket.bl_idname, "sda")
    second = node.inputs.new(wiring.CadexTerminalSocket.bl_idname, "sda")
    first.terminal, second.terminal = "sda", "sda_from_the_other_row"
    check(first.identifier != second.identifier,
          "two sockets named sda get different identifiers")
    check(node.inputs["sda"] == first,
          "and lookup by name silently returns the first")
    found = {socket.terminal for socket in node.inputs}
    check(found == {"sda", "sda_from_the_other_row"},
          "so the sync keys on .terminal, which stays distinct")


def test_a_sync_builds_the_graph_the_engine_describes():
    print("test_a_sync_builds_the_graph_the_engine_describes")
    _scene, tree = _fresh_tree()
    check(wiring.apply_state(tree, _state()), "apply_state accepted the payload")
    check(len(tree.nodes) == 2, "one node per component")
    ports = sorted(node.port for node in tree.nodes)
    check(ports == ["esp", "sen"], "named by their ports")
    node = next(n for n in tree.nodes if n.port == "esp")
    check(node.cadex_output == "esp_board", "and bound to their outputs")
    check([s.terminal for s in node.inputs] == list(SIGNALS),
          "terminals become inputs, in the engine's order")
    check([s.terminal for s in node.outputs] == list(SIGNALS),
          "and outputs too: a board is both source and sink")
    check(len(tree.links) == 1, "one link per enabled row")
    check(tree.cadex_revision == "r1", "the revision is recorded")
    check(tree.cadex_editable is True, "and a nets() script is editable")


def test_solder_rides_the_socket_because_a_link_cannot_hold_it():
    print("test_solder_rides_the_socket_because_a_link_cannot_hold_it")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state())
    soldered = {s.terminal for n in tree.nodes
                for s in list(n.inputs) + list(n.outputs) if s.soldered}
    check(soldered == {"sda"}, "both ends of the soldered row are marked")
    rows = wiring.rows_from_tree(tree)
    check(rows and rows[0]["solder"] is True,
          "and the flag survives the round trip back to a row")


def test_the_graph_does_not_answer_its_own_edit():
    """Without the suspend, every engine rebuild would start a push."""
    print("test_the_graph_does_not_answer_its_own_edit")
    _scene, tree = _fresh_tree()
    wiring._dirty.clear()
    wiring.apply_state(tree, _state())
    check(not wiring._dirty,
          "a sync that created nodes, sockets and links pushed nothing")
    check(wiring._suspend[0] is False, "and the suspend was released after")


def test_a_rebuild_keeps_the_layout():
    print("test_a_rebuild_keeps_the_layout")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state())
    node = next(n for n in tree.nodes if n.port == "sen")
    node.location = (123.0, -456.0)
    node.width = 210.0

    grown = _state(revision="r2")
    grown["components"][0]["terminals"] = _terminals(SIGNALS + ("miso",))
    wiring.apply_state(tree, grown)

    node = next(n for n in tree.nodes if n.port == "sen")
    check(abs(node.location.x - 123.0) < 1e-3 and abs(node.location.y + 456.0) < 1e-3,
          "the node kept the position the user gave it")
    check(abs(node.width - 210.0) < 1e-3, "and its width")
    check([s.terminal for s in node.inputs] == list(SIGNALS) + ["miso"],
          "the new terminal appeared, in the engine's order")
    check(len(tree.links) == 1, "and the existing link survived")


def test_a_dropped_component_takes_its_node():
    """Contract-driven GC, the peer of hydrate_display's."""
    print("test_a_dropped_component_takes_its_node")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state())
    wiring.apply_state(tree, _state(ports=("sen",), wires=[], revision="r2"))
    check([n.port for n in tree.nodes] == ["sen"], "the dropped port's node went")
    check(len(tree.links) == 0, "and took its link with it")


def test_a_drawn_link_becomes_one_row():
    print("test_a_drawn_link_becomes_one_row")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[]))
    check(wiring.rows_from_tree(tree) == [], "an empty graph is an empty table")

    sen = next(n for n in tree.nodes if n.port == "sen")
    esp = next(n for n in tree.nodes if n.port == "esp")
    tree.new_gauge_mm = 0.6
    tree.links.new(sen.outputs[2], esp.inputs[2])

    rows = wiring.rows_from_tree(tree)
    check(len(rows) == 1, "one link, one row")
    row = rows[0] if rows else {}
    check({row.get("a"), row.get("b")} == {"sen.gnd", "esp.gnd"},
          "addressed <port>.<terminal>")
    check(abs(float(row.get("gauge_mm", 0)) - 0.6) < 1e-6,
          "and taking the editor's new-wire gauge")
    check(row.get("name") == wiring.row_name(row["a"], row["b"]),
          "with a lower_snake_case name derived from the two ends")
    check(row.get("enabled") is True, "enabled by default")


def test_a_redrawn_link_keeps_the_row_it_had():
    """Matched on the unordered pair: canvas direction is cosmetic."""
    print("test_a_redrawn_link_keeps_the_row_it_had")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state())
    sen = next(n for n in tree.nodes if n.port == "sen")
    esp = next(n for n in tree.nodes if n.port == "esp")
    tree.links.clear()
    # Redrawn the other way round.
    tree.links.new(esp.outputs[0], sen.inputs[0])
    rows = wiring.rows_from_tree(tree)
    check(len(rows) == 1, "still one row")
    check(rows[0]["name"] == "sda", "and it kept the engine's name")
    check(abs(rows[0]["gauge_mm"] - 0.8) < 1e-6, "and its gauge")


def test_a_disabled_row_is_not_deleted_by_looking_at_it():
    """A disabled wire has no link to draw, so it must survive the read."""
    print("test_a_disabled_row_is_not_deleted_by_looking_at_it")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[
        {"name": "sda", "a": "sen.sda", "b": "esp.sda",
         "gauge_mm": 0.8, "solder": False, "enabled": True},
        {"name": "gnd", "a": "sen.gnd", "b": "esp.gnd",
         "gauge_mm": 0.8, "solder": False, "enabled": False},
    ]))
    check(len(tree.links) == 1, "only the enabled row is drawn")
    names = [row["name"] for row in wiring.rows_from_tree(tree)]
    check(sorted(names) == ["gnd", "sda"], "but both rows come back")


def test_a_legacy_harness_is_read_only():
    print("test_a_legacy_harness_is_read_only")
    scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(editable=False))
    check(tree.cadex_editable is False, "the payload says so and the tree obeys")
    ok, report = wiring.push(scene)
    check(ok is False, "a push is refused rather than attempted")
    check("nets(" in str(report), "and the refusal names the way out")


def test_the_wiring_ui_registers_or_stands_down():
    """The ADR-036 failure — an aborted registration loop — caught."""
    print("test_the_wiring_ui_registers_or_stands_down")
    check(hasattr(bpy.types, "MESH_AGENT_OT_sync_wiring"),
          "the sync operator registered either way")
    node_editor = any(item.identifier == 'NODE_EDITOR' for item in
                      bpy.types.Space.bl_rna.properties['type'].enum_items)
    if wiring_ui.EDITOR_AVAILABLE:
        check(hasattr(bpy.types, "CADEX_WIRING_HT_header"),
              "the header registered on a build with the node editor")
    else:
        check(True, "no node editor in this build; the chrome stood down")
    check(node_editor or not wiring_ui.EDITOR_AVAILABLE,
          "EDITOR_AVAILABLE agrees with whether the space type exists")
    # The point of the guard: everything else came up regardless. Note the
    # test is on NodeTree.__subclasses__() and not on bpy.types — a
    # Python-registered node tree does *not* appear there the way an operator
    # or a panel does (measured; bpy.types carries SpaceCadexChat but never
    # CadexWiringTree).
    check("CadexWiringTree" in {getattr(t, "bl_idname", "")
                                for t in bpy.types.NodeTree.__subclasses__()},
          "the tree registered anyway")


# ---------------------------------------------------------------------------
# ADR-067 — defining a terminal by clicking


def _ring(radius, z, count=32, centre=(0.0, 0.0), noise=0.0):
    import math
    points = []
    for index in range(count):
        angle = 2.0 * math.pi * index / count
        jitter = noise * (1.0 if index % 2 else -1.0)
        points.append((centre[0] + (radius + jitter) * math.cos(angle),
                       centre[1] + (radius + jitter) * math.sin(angle),
                       z))
    return points


def test_fit_terminal_finds_a_hole():
    """Two coaxial loops of matching radius are one bore."""
    print("test_fit_terminal_finds_a_hole")
    points = _ring(0.5, 1.6, centre=(3.0, -2.0)) + _ring(0.5, 0.0, centre=(3.0, -2.0))
    row, report = pick.measure_selection(points, view_direction=(0.0, 0.0, 1.0))
    check(row is not None, "the fit succeeded: {!s}".format(report))
    if row is None:
        return
    check(report["kind"] == "hole", "and it read as a hole")
    check(report["loops"] == 2, "from two loops")
    check(abs(row["origin"][0] - 3.0) < 1e-4 and abs(row["origin"][1] + 2.0) < 1e-4,
          "centred exactly on the bore")
    check(abs(row["depth"] - 1.6) < 1e-4, "with the loop separation as the depth")
    check(abs(row["hole_dia"] - 1.0) < 1e-4, "and twice the radius as hole_dia")
    check(report["residual_mm"] < 1e-6, "residual is zero on an exact circle")


def test_the_fitted_axis_points_into_the_material():
    """ADR-062's convention: origin + axis*depth lands on the far face.

    The engine's own selector implementation took the *near* end first and
    only a kernel test caught it, so this is asserted in both directions.
    """
    print("test_the_fitted_axis_points_into_the_material")
    from mathutils import Vector

    points = _ring(0.5, 1.6) + _ring(0.5, 0.0)
    for view, expect_z in (((0.0, 0.0, -1.0), -1.0), ((0.0, 0.0, 1.0), 1.0)):
        row, _report = pick.measure_selection(points, view_direction=view)
        if row is None:
            check(False, "fit succeeded for view {!r}".format(view))
            continue
        axis = Vector(row["axis"])
        check(abs(axis.z - expect_z) < 1e-6,
              "axis points away from a viewer at {!r}".format(view))
        landing = Vector(row["origin"]) + axis * row["depth"]
        check(abs(landing.z - (1.6 if expect_z > 0 else 0.0)) < 1e-4,
              "and origin + axis*depth lands on the far face")


def test_fit_terminal_finds_a_pad():
    print("test_fit_terminal_finds_a_pad")
    row, report = pick.measure_selection(_ring(1.2, 0.0),
                                         view_direction=(0.0, 0.0, 1.0))
    check(row is not None, "the fit succeeded: {!s}".format(report))
    if row is None:
        return
    check(report["kind"] == "pad", "one loop reads as a pad")
    check(row["depth"] == 0.0, "with no depth")
    check("hole_dia" not in row, "and no bore diameter")


def test_a_square_is_not_classified_by_its_residual():
    """Four corners fit a circle with zero error: residual is not a classifier."""
    print("test_a_square_is_not_classified_by_its_residual")
    square = [(1.0, 1.0, 0.0), (-1.0, 1.0, 0.0), (-1.0, -1.0, 0.0), (1.0, -1.0, 0.0)]
    row, report = pick.measure_selection(square, view_direction=(0.0, 0.0, 1.0))
    check(row is not None, "the fit does not fail, which is the point")
    if row is not None:
        check(report["residual_mm"] < 1e-9,
              "a square pad's corners fit a circle exactly")
        check(report["kind_guessed"] is True,
              "so the operator records that the kind was a guess, not a reading")
    # And the user can override it, which is the actual remedy.
    forced, _report = pick.measure_selection(square, kind='PAD',
                                             view_direction=(0.0, 0.0, 1.0))
    check(forced is not None and forced["depth"] == 0.0,
          "kind='PAD' overrides the guess")


def test_fewer_than_four_vertices_is_refused():
    """Three points always fit exactly, so the residual means nothing."""
    print("test_fewer_than_four_vertices_is_refused")
    row, report = pick.measure_selection(
        [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)])
    check(row is None, "three vertices are refused")
    check("3" in str(report), "and the refusal names the count")


def test_a_noisy_rim_still_fits_and_reports_its_quality():
    print("test_a_noisy_rim_still_fits_and_reports_its_quality")
    for noise, label in ((0.005, "5 um"), (0.02, "20 um")):
        points = _ring(0.5, 1.6, noise=noise) + _ring(0.5, 0.0, noise=noise)
        row, report = pick.measure_selection(points, view_direction=(0.0, 0.0, 1.0))
        check(row is not None, "{:s} of vertex noise still fits".format(label))
        if row is not None:
            check(0.0 < report["residual_mm"] < 0.05,
                  "{:s}: residual is a usable quality signal ({:.4f})".format(
                      label, report["residual_mm"]))


def test_a_scribble_is_refused_rather_than_averaged():
    print("test_a_scribble_is_refused_rather_than_averaged")
    points = [(0.0, 0.0, 0.0), (5.0, 0.1, 0.0), (1.0, 4.0, 0.0),
              (4.5, 3.8, 0.0), (0.2, 2.0, 0.0), (2.5, 0.05, 0.0)]
    row, report = pick.measure_selection(points, view_direction=(0.0, 0.0, 1.0))
    check(row is None, "a selection that is not round is refused")
    check("not a circle" in str(report), "and says so")


def test_a_fitted_terminal_is_not_a_pin():
    """docs/XSCRIPT.md's naming rule, enforced in code."""
    print("test_a_fitted_terminal_is_not_a_pin")
    pick.clear_terminals()
    cadex_pick._pending_pins.clear()
    row, report = pick.measure_selection(_ring(0.5, 1.6) + _ring(0.5, 0.0),
                                         view_direction=(0.0, 0.0, 1.0))
    pick.queue_terminal({"output": "esp_placed", "object": "esp",
                         "row": row, "report": report})
    check(pick.pending_terminal_count() == 1, "the terminal queued")
    check(cadex_pick.pending_pin_count() == 0, "and the pin queue is untouched")
    note = pick.consume_terminal_notes()
    check("MEASURED a terminal" in note, "the note says terminal")
    check("pinned" not in note, "and never says pinned")
    check("Transcribe" in note, "and tells the model to copy, not re-derive")
    check(pick.pending_terminal_count() == 0, "draining empties the queue")
    check(cadex_pick.consume_pin_notes() == "", "the two queues drain apart")


def test_several_picks_batch_into_one_turn():
    print("test_several_picks_batch_into_one_turn")
    pick.clear_terminals()
    row, report = pick.measure_selection(_ring(0.5, 1.6) + _ring(0.5, 0.0),
                                         view_direction=(0.0, 0.0, 1.0))
    for index in range(19):
        pick.queue_terminal({"output": "hdr", "object": "hdr",
                             "row": dict(row, name="p{:d}".format(index)),
                             "report": report})
    note = pick.consume_terminal_notes()
    check(note.count("MEASURED a terminal") == 19,
          "a 19-pin header is 19 lines in one note")
    check(pick.pending_terminal_count() == 0, "drained in one go")


def test_the_model_is_told_these_numbers_are_measured():
    print("test_the_model_is_told_these_numbers_are_measured")
    from mesh_agent import modes

    check("MEASURE a terminal" in modes.CADEX_OVERLAY,
          "the overlay names the gesture")
    check("do not re-derive them" in modes.CADEX_OVERLAY,
          "and tells the model to transcribe rather than estimate")


def test_the_graph_fills_itself():
    """Regression: the editor opened blank with no way to fill it (ADR-066).

    `sync_from_engine` shipped with exactly one caller — the header's refresh
    button — and the header only drew that button once a tree already
    existed. So a freshly opened file showed "No project wiring", and there
    was no control anywhere that would populate it. The graph is a projection
    of the engine; something has to notice the engine moved.
    """
    print("test_the_graph_fills_itself")
    from mesh_agent import cadex_backend

    scene = bpy.context.scene
    wiring._sync_armed.clear()

    # No engine state cached: nothing to sync to, and nothing should be armed.
    check(wiring.needs_sync(scene) is False,
          "a project with no accepted revision asks for nothing")

    state = cadex_backend._state_for(cadex_backend.project_root(scene))
    state.revision = "rev-one"
    check(wiring.needs_sync(scene) is True,
          "an accepted revision with no tree asks for a sync")

    tree = wiring.ensure_tree(scene)
    wiring.apply_state(tree, _state(revision="rev-one"))
    check(wiring.needs_sync(scene) is False,
          "a tree already at that revision asks for nothing")

    state.revision = "rev-two"
    check(wiring.needs_sync(scene) is True, "a moved revision asks again")

    # The failure path must not re-ask forever: one attempt per revision.
    tree.cadex_attempted_revision = "rev-two"
    check(wiring.needs_sync(scene) is False,
          "a revision already attempted is not retried on every redraw")

    state.revision = ""


def test_the_sync_button_is_always_reachable():
    """The control that fills the graph must not be hidden until it is full."""
    print("test_the_sync_button_is_always_reachable")
    import inspect as _inspect

    source = _inspect.getsource(wiring_ui.CADEX_WIRING_HT_header.draw)
    button = source.index("MESH_AGENT_OT_sync_wiring")
    guard = source.index("if tree is None")
    check(button < guard,
          "the header draws the refresh button before it gives up on the tree")
    check("arm_sync" in source, "and arms an automatic sync from the draw")


def test_the_node_editor_tool_system_is_initialised():
    """Regression: opening the Wiring editor must not raise (ADR-066).

    `NODE_PT_tools_active` was defined in `bl_ui/space_toolsystem_toolbar.py`
    but left out of its `classes` tuple by ADR-036 — harmless while SPACE_NODE
    was unregistered, because nothing ever looked the class up. Once the
    editor exists, `wm.tool_set_by_id` finds it by space type on the first
    click into the editor and dies:

        AttributeError: type object 'NODE_PT_tools_active'
        has no attribute '_tool_group_active'

    `_tool_group_active` is initialised by `ToolSelectPanelHelper.register()`,
    which only runs when the class is registered. So the test is that it *is*.
    """
    print("test_the_node_editor_tool_system_is_initialised")
    if not wiring_ui.EDITOR_AVAILABLE:
        check(True, "no node editor in this build; nothing to initialise")
        return
    cls = getattr(bpy.types, "NODE_PT_tools_active", None)
    check(cls is not None, "NODE_PT_tools_active is registered")
    if cls is None:
        return
    check(hasattr(cls, "_tool_group_active"),
          "and therefore carries _tool_group_active")
    # The viewport's helper must keep working too — this file's `classes`
    # tuple is shared.
    viewport = getattr(bpy.types, "VIEW3D_PT_tools_active", None)
    check(viewport is not None and hasattr(viewport, "_tool_group_active"),
          "and the viewport's tool system is untouched")


def test_the_graph_survives_a_blend_round_trip():
    """The one risk ADR-066 flagged with a fallback, closed.

    ``bNodeSocket`` carries an ``IDProperty *`` in DNA but does not expose it
    to ``bpy_struct[]``, which is why ``terminal`` and ``soldered`` are
    *registered* properties rather than ID properties. Whether registered
    properties on a socket are written to the .blend was the open question:
    if they were not, both would have had to move onto the node as a parallel
    array. They are.

    Runs last, and resets the scene after: ``open_mainfile`` replaces
    everything, including the scene the other tests build on.
    """
    print("test_the_graph_survives_a_blend_round_trip")
    import os
    import tempfile

    scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state())
    node = next(n for n in tree.nodes if n.port == "sen")
    node.location = (77.0, -33.0)

    path = os.path.join(tempfile.mkdtemp(), "wiring.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)

    tree = bpy.context.scene.cadex_wiring
    check(tree is not None and tree.bl_idname == "CadexWiringTree",
          "the tree came back through the scene pointer")
    if tree is None:
        return
    check(len(tree.nodes) == 2 and len(tree.links) == 1,
          "with its nodes and links")
    node = next((n for n in tree.nodes if n.port == "sen"), None)
    check(node is not None, "and the port property survived")
    if node is None:
        return
    check(abs(node.location.x - 77.0) < 1e-3 and abs(node.location.y + 33.0) < 1e-3,
          "node position round-trips, so the user's layout is durable")
    check(node.cadex_output == "sen_board", "the output binding survived")
    terminals = [s.terminal for s in node.inputs]
    check(terminals == list(SIGNALS),
          "every socket kept its terminal identity: {!r}".format(terminals))
    check(all(s.kind == "hole" for s in node.inputs), "and its kind")
    soldered = {s.terminal for n in tree.nodes
                for s in list(n.inputs) + list(n.outputs) if s.soldered}
    check(soldered == {"sda"}, "and its solder flag")
    check(len(wiring.stored_rows(tree)) == 1, "the row table survived")
    check(tree.cadex_revision == "r1", "and the revision it mirrors")
    reset_scene()


def main():
    mesh_agent.register()
    try:
        for test in (
            test_the_wiring_tree_registers,
            test_a_board_node_names_a_script_output,
            test_a_terminal_is_keyed_by_property_not_by_name,
            test_a_sync_builds_the_graph_the_engine_describes,
            test_solder_rides_the_socket_because_a_link_cannot_hold_it,
            test_the_graph_does_not_answer_its_own_edit,
            test_a_rebuild_keeps_the_layout,
            test_a_dropped_component_takes_its_node,
            test_a_drawn_link_becomes_one_row,
            test_a_redrawn_link_keeps_the_row_it_had,
            test_a_disabled_row_is_not_deleted_by_looking_at_it,
            test_a_legacy_harness_is_read_only,
            test_the_wiring_ui_registers_or_stands_down,
            test_fit_terminal_finds_a_hole,
            test_the_fitted_axis_points_into_the_material,
            test_fit_terminal_finds_a_pad,
            test_a_square_is_not_classified_by_its_residual,
            test_fewer_than_four_vertices_is_refused,
            test_a_noisy_rim_still_fits_and_reports_its_quality,
            test_a_scribble_is_refused_rather_than_averaged,
            test_a_fitted_terminal_is_not_a_pin,
            test_several_picks_batch_into_one_turn,
            test_the_model_is_told_these_numbers_are_measured,
            test_the_graph_fills_itself,
            test_the_sync_button_is_always_reachable,
            test_the_node_editor_tool_system_is_initialised,
            # Last: open_mainfile replaces the whole session.
            test_the_graph_survives_a_blend_round_trip,
        ):
            test()
    finally:
        try:
            mesh_agent.unregister()
        except Exception:
            pass
    print("")
    if FAILURES:
        print("FAILED ({:d}):".format(len(FAILURES)))
        for label in FAILURES:
            print("  - " + label)
        sys.exit(1)
    print("all wiring tests passed")


if __name__ == "__main__":
    main()
