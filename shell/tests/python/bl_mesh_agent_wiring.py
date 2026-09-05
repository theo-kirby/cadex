# SPDX-FileCopyrightText: 2026 Cadex Authors
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

# mesh_agent is application code in scripts/startup (ADR-183): the app has
# already registered its bundled copy. The suite tests the SOURCE tree, so
# put that copy down, purge it, and import ours (bl_mesh_agent.py explains).
_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", ".."))
_SOURCE_STARTUP = os.path.join(_REPO, "scripts", "startup")
_bundled = sys.modules.get("mesh_agent")
if _bundled is not None and not os.path.abspath(
        _bundled.__file__).startswith(_SOURCE_STARTUP + os.sep):
    _bundled.unregister()
    for _name in [n for n in sys.modules
                  if n == "mesh_agent" or n.startswith("mesh_agent.")]:
        del sys.modules[_name]
sys.path.insert(0, _SOURCE_STARTUP)

import mesh_agent  # noqa: E402
from mesh_agent import cadex_backend  # noqa: E402
from mesh_agent import wiring  # noqa: E402
from mesh_agent import wiring_ui  # noqa: E402
from mesh_agent import cadex_hydrate  # noqa: E402
from mesh_agent import cadex_pick  # noqa: E402
from mesh_agent import cadex_terminal_pick as pick  # noqa: E402
from mesh_agent import cadex_wire_path as wire_path  # noqa: E402

FAILURES = []


def check(condition, label):
    print("  {:s}: {:s}".format("ok" if condition else "FAIL", label))
    if not condition:
        FAILURES.append(label)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


SIGNALS = ("sda", "scl", "gnd")


def _terminals(names=SIGNALS, kind="hole", rows=False):
    """The engine's resolved sockets; ``rows`` adds the board table's own
    columns, which is what a board declared with boards(...) carries."""

    terminals = []
    for index, name in enumerate(names):
        terminal = {
            "name": name,
            "point": [0.0, 2.54 * index, 0.0],
            "direction": [0.0, 0.0, 1.0],
            "kind": kind,
            "radius": 0.5,
            "depth": 1.6,
        }
        if rows:
            terminal.update({
                "origin": [0.0, 2.54 * index, 1.6],
                "axis": [0.0, 0.0, -1.0],
                "hole_dia": 1.0 if kind == "hole" else None,
                "depth": 1.6,
            })
        terminals.append(terminal)
    return terminals


def _state(ports=("sen", "esp"), wires=None, editable=True, revision="r1",
           boards=False):
    return {
        "revision": revision,
        "source": "nets" if editable else "derived",
        "editable": editable,
        "components": [
            {
                "port": port,
                "board": port if boards else "",
                "editable": bool(boards),
                "output": port + "_board",
                "domain": "part",
                "terminals": _terminals(rows=boards),
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


def _sockets(tree, address):
    """Both sockets of one ``<port>.<terminal>`` address."""

    port, _, terminal = address.partition(".")
    return [socket for node in tree.nodes if node.port == port
            for socket in list(node.inputs) + list(node.outputs)
            if socket.terminal == terminal]


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
    marked = {s.terminal for n in tree.nodes
              for s in list(n.inputs) + list(n.outputs) if s.soldered}
    check("sda" in marked, "both ends of the soldered row are marked")
    rows = wiring.rows_from_tree(tree)
    check(rows and rows[0]["solder"] is True,
          "and the flag survives the round trip back to a row")


def test_a_new_terminal_is_soldered_and_a_stored_no_stays_no():
    """Solder on by default, and never at the cost of a stored answer (ADR-122).

    A wire onto a pad or a bore nearly always carries a joint, so a terminal
    nothing has landed on yet reads soldered and a freshly drawn wire is
    soldered without anyone ticking anything. What that breaks if it is done
    carelessly is the other direction: ``apply_state`` only ever *set* True,
    which was invisible while a fresh socket defaulted to False and would
    silently re-solder an unticked row now that one does not.
    """
    print("test_a_new_terminal_is_soldered_and_a_stored_no_stays_no")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[]))
    sen = next(n for n in tree.nodes if n.port == "sen")
    check(all(s.soldered for s in list(sen.inputs) + list(sen.outputs)),
          "a terminal nothing has landed on yet is soldered")

    esp = next(n for n in tree.nodes if n.port == "esp")
    tree.links.new(sen.outputs[0], esp.inputs[0])
    row = next((r for r in wiring.rows_from_tree(tree)
                if {r["a"], r["b"]} == {"sen.sda", "esp.sda"}), {})
    check(row.get("solder") is True, "so a wire drawn onto it is soldered")

    # ...and the engine's own "no" survives the round trip.
    wiring.apply_state(tree, _state(revision="r2", wires=[
        {"name": "sda", "a": "sen.sda", "b": "esp.sda",
         "gauge_mm": 0.8, "solder": False, "enabled": True},
    ]))
    check(not any(s.soldered for s in _sockets(tree, "sen.sda")),
          "an unsoldered stored row lands unsoldered on both its sockets")
    check(not any(s.soldered for s in _sockets(tree, "esp.sda")),
          "at the far end too")
    back = wiring.rows_from_tree(tree)
    check(back and back[0]["solder"] is False, "and reads back unsoldered")


def test_a_terminal_several_wires_land_on_holds_one_flag():
    """A row carries one flag; a terminal may carry several rows (ADR-122).

    ``_solder_for`` reads the sockets with an *any* rule, so the sync has to
    write them with the same one — row by row, the last row to touch a shared
    terminal would decide for all of them.
    """
    print("test_a_terminal_several_wires_land_on_holds_one_flag")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(ports=("sen", "esp", "fc"), wires=[
        {"name": "a", "a": "sen.gnd", "b": "esp.gnd",
         "gauge_mm": 0.8, "solder": True, "enabled": True},
        {"name": "b", "a": "sen.gnd", "b": "fc.gnd",
         "gauge_mm": 0.8, "solder": False, "enabled": True},
    ]))
    check(all(s.soldered for s in _sockets(tree, "sen.gnd")),
          "the shared terminal keeps the joint one of its wires asked for")
    check(not any(s.soldered for s in _sockets(tree, "fc.gnd")),
          "and the end that asked for none does not get one")


def test_a_solder_toggle_is_an_edit_the_tree_notices():
    """Without the update callback the checkbox was a dead control (ADR-113).

    ``NodeTree.update()`` fires on topology only, so a property written into
    an existing socket reached the engine nowhere: nothing marked the canvas
    dirty and the value was picked up incidentally, by the next link edit.
    """
    print("test_a_solder_toggle_is_an_edit_the_tree_notices")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[
        {"name": "sda", "a": "sen.sda", "b": "esp.sda",
         "gauge_mm": 0.8, "solder": False, "enabled": True},
    ]))
    tree.cadex_dirty = False
    sen = next(n for n in tree.nodes if n.port == "sen")
    socket = next(s for s in sen.outputs if s.terminal == "sda")
    socket.soldered = True
    check(tree.cadex_dirty, "the toggle marks the canvas the same way a link does")
    check(wiring._suspend[0] is False, "and released the suspend it mirrored under")
    tree.cadex_dirty = False


def test_both_sockets_of_one_terminal_hold_one_state():
    """A terminal is two sockets only because Blender refuses input→input."""
    print("test_both_sockets_of_one_terminal_hold_one_state")
    _scene, tree = _fresh_tree()
    # Every terminal starts soldered since ADR-122, so the state worth
    # carrying across the pair is the *cleared* one.
    wiring.apply_state(tree, _state(wires=[]))
    sen = next(n for n in tree.nodes if n.port == "sen")
    next(s for s in sen.outputs if s.terminal == "sda").soldered = False
    check(next(s for s in sen.inputs if s.terminal == "sda").soldered is False,
          "unticking the drawn socket carries its twin with it")
    check({s.terminal for s in list(sen.inputs) + list(sen.outputs)
           if not s.soldered} == {"sda"}, "and touches no other terminal")
    next(s for s in sen.outputs if s.terminal == "sda").soldered = True
    check(all(s.soldered for s in list(sen.inputs) + list(sen.outputs)),
          "and ticking carries it back")
    tree.cadex_dirty = False


def test_solder_can_be_turned_off_again():
    """It used to be monotone: the row fell back to its stored True."""
    print("test_solder_can_be_turned_off_again")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state())
    check(wiring.rows_from_tree(tree)[0]["solder"] is True, "the row starts soldered")
    for port in ("sen", "esp"):
        node = next(n for n in tree.nodes if n.port == port)
        next(s for s in node.outputs if s.terminal == "sda").soldered = False
        next(s for s in node.inputs if s.terminal == "sda").soldered = False
    rows = wiring.rows_from_tree(tree)
    check(rows and rows[0]["solder"] is False,
          "clearing both ends clears the row")
    check(rows and rows[0]["name"] == "sda" and abs(rows[0]["gauge_mm"] - 0.8) < 1e-6,
          "and nothing else about the row moved")
    # One end is enough to keep it: a row carries one flag, a wire two ends.
    esp = next(n for n in tree.nodes if n.port == "esp")
    next(s for s in esp.inputs if s.terminal == "sda").soldered = True
    check(wiring.rows_from_tree(tree)[0]["solder"] is True,
          "and either end alone puts it back")
    tree.cadex_dirty = False


def test_an_edit_marks_the_canvas_and_sends_nothing():
    """The debounce is gone; Apply is the only thing that sends (ADR-122).

    It was a *leading-edge* throttle, so a burst of twenty drags fired one
    push 0.15 s after the first and left nineteen to pile up behind it on the
    client lock — each one then refused as stale, in silence. Twenty drags now
    cost nothing at all until the button is pressed.
    """
    print("test_an_edit_marks_the_canvas_and_sends_nothing")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[]))
    check(tree.cadex_dirty is False, "the engine's own answer is not an edit")

    sen = next(n for n in tree.nodes if n.port == "sen")
    esp = next(n for n in tree.nodes if n.port == "esp")
    for index in range(3):
        tree.links.new(sen.outputs[index], esp.inputs[index])
    check(tree.cadex_dirty is True, "three drags mark the canvas")
    check(len(wiring.rows_from_tree(tree)) == 3,
          "and all three are on the canvas, waiting to go together")
    check(not hasattr(wiring, "_push_timer"),
          "and there is no debounce timer left to fire behind them")
    check(not hasattr(wiring, "_mark_dirty"),
          "nor the throttle that armed it")


def test_the_graph_does_not_answer_its_own_edit():
    """Without the suspend, every engine rebuild would mark the canvas dirty."""
    print("test_the_graph_does_not_answer_its_own_edit")
    _scene, tree = _fresh_tree()
    tree.cadex_dirty = True
    wiring.apply_state(tree, _state())
    check(tree.cadex_dirty is False,
          "a sync that created nodes, sockets and links owes nothing back")
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


def test_two_sets_on_one_board_do_not_share_a_node():
    """The bug that drew every board and not one wire (ADR-115).

    A board with a front header and a back header is two terminal sets on one
    component, and both used to answer to the component's output name. This
    keys a node by that name, so the second set's sockets replaced the first
    set's and the declared wires had nowhere to land: three wires, no links,
    and a header still confidently reading "3 wires". The engine now names
    them apart; this is the half that must not re-introduce the merge.
    """
    print("test_two_sets_on_one_board_do_not_share_a_node")
    _scene, tree = _fresh_tree()
    state = _state()
    back = dict(state["components"][0])
    back["terminals"] = _terminals(("h1", "h2", "h3"))
    state["components"].append(back)
    wiring.apply_state(tree, state)

    sen = next(n for n in tree.nodes if n.port == "sen")
    check([s.terminal for s in sen.outputs] == list(SIGNALS),
          "the first set kept its own terminals")
    check(len(tree.links) == 1, "so the declared wire still found both ends")
    check(tree.cadex_stale is False, "and the canvas is a whole projection")


def test_a_row_with_nowhere_to_land_holds_the_canvas():
    """An incomplete projection is not a table, so it is not pushed."""
    print("test_a_row_with_nowhere_to_land_holds_the_canvas")
    scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[
        {"name": "sda", "a": "sen.sda", "b": "esp.sda",
         "gauge_mm": 0.8, "solder": False, "enabled": True},
        {"name": "miso", "a": "sen.miso", "b": "esp.miso",
         "gauge_mm": 0.8, "solder": False, "enabled": True},
    ]))
    check(len(tree.links) == 1, "the row it can draw is drawn")
    check(tree.cadex_stale is True, "the one it cannot marks the tree stale")
    check("miso" in tree.cadex_error, "and the error names it")
    ok, report = wiring.push(scene)
    check(ok is False, "a push is refused rather than deleting the difference")
    check("miso" in report, "and says why")


def test_a_sync_clears_a_stuck_applying_flag():
    """`cadex_pending` saves into the .blend, so a lost reply is forever."""
    print("test_a_sync_clears_a_stuck_applying_flag")
    _scene, tree = _fresh_tree()
    tree.cadex_pending = True
    wiring.apply_state(tree, _state())
    check(tree.cadex_pending is False,
          "the engine's answer on screen is the end of 'applying…'")


def test_a_hand_built_wire_draws_but_is_never_pushed():
    """A cable or bundle outside nets(...) is part of the picture, not the table."""
    print("test_a_hand_built_wire_draws_but_is_never_pushed")
    scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[
        {"name": "sda", "a": "sen.sda", "b": "esp.sda",
         "gauge_mm": 0.8, "solder": True, "enabled": True},
        {"name": "ribbon_0", "a": "sen.gnd", "b": "esp.gnd", "gauge_mm": 0.5,
         "solder": False, "enabled": True, "kind": "bundle", "editable": False},
    ]))
    check(len(tree.links) == 2, "both connections are drawn")

    rows = wiring.rows_from_tree(tree)
    check(len(rows) == 2, "and both come back off the canvas")
    ribbon = next((r for r in rows if r["name"] == "ribbon_0"), {})
    check(ribbon.get("editable") is False, "the hand-built one stays marked")
    check(ribbon.get("kind") == "bundle", "and keeps what kind it is")

    payload = wiring.declared_rows(rows)
    check([r["name"] for r in payload] == ["sda"],
          "only the declared row is offered to set_params(nets=...)")
    check(all("editable" not in r for r in payload),
          "and it carries no key canonical_rows would refuse")

    # Cutting a link the script owns is not an edit of the declared table.
    for link in list(tree.links):
        if link.from_socket.terminal == "gnd":
            tree.links.remove(link)
    ok, report = wiring.push(scene)
    check(ok is True and report == "No change.",
          "so deleting one sends nothing; the next sync puts it back")


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
# ADR-122 — Apply, Revert, and the pump that drives a push to completion


class _FakeEngine:
    """One cadexd project's revision guard, without a cadexd.

    Everything ADR-122 is about lives between ``wiring.push`` and
    ``Lifecycle.poll``, and none of it needs geometry: the bug was that
    nothing polled, so the guard never moved, so the *second* request carried
    the *first* one's ``expected_revision`` and was refused. That is exactly
    what this models — a revision that advances on every accepted request and
    a refusal for any request that arrives naming the wrong one — so the
    regression is asserted on the recorded ``expected_revision`` rather than
    on a symptom downstream of it.
    """

    def __init__(self, state):
        from mesh_agent import cadex_backend

        self.backend = cadex_backend
        self.state = dict(state)
        self.sent = []
        self.refuse = ""
        self.serial = 1
        self.root = ""
        self._saved = {}

    # -- installation -----------------------------------------------------

    def install(self, scene):
        backend = self.backend
        self.root = backend.project_root(scene)
        backend._wirings.pop(self.root, None)
        cached = backend._state_for(self.root)
        cached.revision = str(self.state.get("revision") or "")
        cached.script_present = True
        self._saved = {
            "ensure_open": backend.ensure_open,
            "begin_lifecycle": backend.begin_lifecycle,
            "wiring_state": backend.wiring_state,
            "schedule_refine": backend._schedule_refine,
        }
        backend.ensure_open = lambda _scene, **_kw: (True, "")
        backend.begin_lifecycle = self._begin_lifecycle
        backend.wiring_state = lambda _scene: dict(self.state)
        backend._schedule_refine = lambda _scene: None
        return self

    def remove(self):
        backend = self.backend
        for name, value in (("ensure_open", self._saved.get("ensure_open")),
                            ("begin_lifecycle",
                             self._saved.get("begin_lifecycle")),
                            ("wiring_state", self._saved.get("wiring_state")),
                            ("_schedule_refine",
                             self._saved.get("schedule_refine"))):
            if value is not None:
                setattr(backend, name, value)
        backend._wirings.pop(self.root, None)

    # -- the engine half --------------------------------------------------

    def _begin_lifecycle(self, scene, op, args, **_kwargs):
        """Snapshot the guard exactly where the real ``Lifecycle`` does."""

        request = dict(args)
        request["expected_revision"] = \
            self.backend._state_for(self.root).revision
        return _FakeLifecycle(self, request)

    def answer(self, request):
        """One request, judged. Returns ``(ok, report)`` as ``poll`` would."""

        self.sent.append(dict(request))
        if request.get("expected_revision") != self.state.get("revision"):
            return False, ("cadexd set_params failed [STALE_PROGRAM_REVISION] "
                           "the program has moved since this was prepared")
        if self.refuse:
            return False, self.refuse
        if "nets" in request:
            self.state["wires"] = [dict(row) for row in request["nets"]]
        self.serial += 1
        self.state["revision"] = "r{:d}".format(self.serial)
        # What ``_revision_from_payload`` does on the way back.
        self.backend._state_for(self.root).revision = self.state["revision"]
        return True, "Accepted revision " + self.state["revision"]


class _FakeLifecycle(cadex_backend.Lifecycle):
    """A ``Lifecycle`` that answers on its second poll. Never calls super().

    A real subclass because ``_start_wiring`` tests ``isinstance(started,
    Lifecycle)`` to tell "in flight" from "never started", and that check is
    the one that has to keep working.
    """

    def __init__(self, engine, request):  # noqa: D107 - deliberately not super
        self._engine = engine
        self._request = dict(request)
        self._pending = 1

    @property
    def request(self):
        return dict(self._request)

    def poll(self):
        if self._pending > 0:
            self._pending -= 1
            return None
        return self._engine.answer(self._request)


def _applied(scene, engine):
    """Press Apply and drain the pump, as a timer would. ``(ok, report)``."""

    ok, report = wiring.push(scene)
    if not ok:
        return ok, report
    return cadex_backend.wiring_apply_now(engine.root)


def test_apply_sends_once_and_the_pump_drives_it_to_completion():
    """The reported bug's first half: nothing polled, so nothing finished.

    ``begin_set_tables`` returned a raw ``Lifecycle`` and ``push`` handed it
    to a timer that dropped it, so ``hydrate``, the revision update and
    ``on_push_finished`` never ran — which is why "applying…" stuck and why
    the wire that *did* land was not repainted until something else rebuilt.
    """
    print("test_apply_sends_once_and_the_pump_drives_it_to_completion")
    scene, tree = _fresh_tree()
    engine = _FakeEngine(_state(wires=[])).install(scene)
    try:
        wiring.apply_state(tree, dict(engine.state), root=engine.root)
        sen = next(n for n in tree.nodes if n.port == "sen")
        esp = next(n for n in tree.nodes if n.port == "esp")
        for index in range(3):
            tree.links.new(sen.outputs[index], esp.inputs[index])

        ok, _report = wiring.push(scene)
        check(ok, "Apply was accepted for sending")
        check(tree.cadex_pending is True, "and the header says applying…")
        check(cadex_backend.wiring_stats(engine.root)["requests"] == 1,
              "three drags became exactly one request")

        while cadex_backend.wiring_stats(engine.root)["in_flight"]:
            cadex_backend.pump_wiring_once(engine.root)
        check(len(engine.sent) == 1, "which reached the engine once")
        check(len(engine.sent[0].get("nets") or []) == 3,
              "carrying all three wires together")
        check(tree.cadex_pending is False,
              "the pump cleared applying… itself, without waiting for a sync")
        check(tree.cadex_dirty is False, "and the canvas owes nothing")
        check(len(tree.links) == 3, "the wires are still drawn")
        check(not tree.cadex_error, "with no error: {!r}".format(tree.cadex_error))
    finally:
        engine.remove()


def test_a_second_apply_carries_the_revision_the_first_one_returned():
    """THE bug (ADR-122): twenty wires applied, one landed, nineteen vanished.

    Nothing polled the lifecycle, so ``_revision_from_payload`` never ran and
    the shell's cached ``expected_revision`` still named the revision from
    before the first apply. Every push after the first was therefore refused
    with ``STALE_PROGRAM_REVISION`` — and the refusal was dropped on the floor
    too, because nobody read the payload. Asserted on the guard itself, which
    is the thing that was wrong.
    """
    print("test_a_second_apply_carries_the_revision_the_first_one_returned")
    scene, tree = _fresh_tree()
    engine = _FakeEngine(_state(wires=[])).install(scene)
    try:
        wiring.apply_state(tree, dict(engine.state), root=engine.root)
        sen = next(n for n in tree.nodes if n.port == "sen")
        esp = next(n for n in tree.nodes if n.port == "esp")

        tree.links.new(sen.outputs[0], esp.inputs[0])
        ok, report = _applied(scene, engine)
        check(ok, "the first apply landed: {!s}".format(report))
        first = engine.sent[0]["expected_revision"]

        tree.links.new(sen.outputs[1], esp.inputs[1])
        ok, report = _applied(scene, engine)
        check(ok, "and so did the second: {!s}".format(report))
        check(len(engine.sent) == 2, "two applies, two requests")
        second = engine.sent[1]["expected_revision"]
        check(first == "r1" and second == "r2",
              "the second carried the revision the first returned "
              "({!r} after {!r})".format(second, first))
        check(len(engine.state["wires"]) == 2,
              "so both wires exist in the accepted table")
        check(len(tree.links) == 2, "and both are still on the canvas")
    finally:
        engine.remove()


def test_a_refused_apply_keeps_the_canvas_and_revert_discards_it():
    """Losing twenty drags to a refusal is worse than an odd canvas (ADR-122)."""
    print("test_a_refused_apply_keeps_the_canvas_and_revert_discards_it")
    scene, tree = _fresh_tree()
    engine = _FakeEngine(_state(wires=[])).install(scene)
    try:
        wiring.apply_state(tree, dict(engine.state), root=engine.root)
        sen = next(n for n in tree.nodes if n.port == "sen")
        esp = next(n for n in tree.nodes if n.port == "esp")
        for index in range(3):
            tree.links.new(sen.outputs[index], esp.inputs[index])

        engine.refuse = "cadexd set_params failed: no route for wire sda"
        ok, report = _applied(scene, engine)
        check(ok is False, "the refusal reached the caller: {!s}".format(report))
        check(len(tree.links) == 3,
              "and all three drags are still on the canvas")
        check("no route" in tree.cadex_error,
              "with the engine's reason on the header: {!r}".format(
                  tree.cadex_error))
        check(tree.cadex_pending is False, "and applying… is over")

        # Revert is the deliberate way to throw them away.
        engine.refuse = ""
        check(wiring.sync_from_engine(scene, force=True), "Revert re-read")
        check(len(tree.links) == 0, "and the canvas is the engine's again")
        check(tree.cadex_dirty is False, "owing nothing")
    finally:
        engine.remove()


def test_a_push_arriving_mid_flight_replaces_the_queued_one():
    """The canvas is the whole table, so the newest push supersedes (ADR-122).

    Unlike a slider drag, there is nothing to coalesce: each push carries
    every row, so a second one while the first is in flight replaces what is
    queued rather than starting a second request on the client lock — which
    is what "it took a really long time" was.
    """
    print("test_a_push_arriving_mid_flight_replaces_the_queued_one")
    scene, _tree = _fresh_tree()
    engine = _FakeEngine(_state(wires=[])).install(scene)
    try:
        rows = [{"name": "a", "a": "sen.sda", "b": "esp.sda",
                 "gauge_mm": 0.8, "solder": True, "enabled": True}]
        ok, _report = cadex_backend.begin_set_tables(scene, nets=rows)
        check(ok, "the first push went in flight")
        check(cadex_backend.wiring_stats(engine.root)["in_flight"],
              "and holds the slot")

        for gauge in (1.0, 1.2):
            cadex_backend.begin_set_tables(
                scene, nets=[dict(rows[0], gauge_mm=gauge)])
        check(cadex_backend.wiring_stats(engine.root)["queued"],
              "two more pushes queued as one")
        check(cadex_backend.wiring_stats(engine.root)["requests"] == 1,
              "and started no second request")

        while cadex_backend.wiring_stats(engine.root)["in_flight"]:
            cadex_backend.pump_wiring_once(engine.root)
        check(len(engine.sent) == 2,
              "the queued one ran after it, so two requests in total")
        check(abs(engine.sent[1]["nets"][0]["gauge_mm"] - 1.2) < 1e-6,
              "and it is the NEWEST table, not the older queued one")
        check(engine.sent[1]["expected_revision"] == "r2",
              "carrying the revision the first request returned")
        check(engine.state["wires"][0]["gauge_mm"] == 1.2,
              "which is what the engine ended up holding")
    finally:
        engine.remove()


def test_the_apply_and_revert_operators_are_registered():
    print("test_the_apply_and_revert_operators_are_registered")
    check(hasattr(bpy.types, "MESH_AGENT_OT_apply_wiring"),
          "Apply is registered whether or not the editor exists")
    check(wiring_ui.MESH_AGENT_OT_sync_wiring.bl_idname
          == "mesh_agent.sync_wiring",
          "Revert kept the idname the button row asserts on")
    check(wiring_ui.MESH_AGENT_OT_sync_wiring.bl_label == "Revert",
          "and is labelled Revert")

    import inspect as _inspect
    source = _inspect.getsource(wiring_ui.CADEX_WIRING_HT_header.draw)
    check("_draw_apply_revert" in source, "the header draws the pair")
    pair = _inspect.getsource(wiring_ui._draw_apply_revert)
    check("cadex_dirty" in pair, "and alerts Apply while the canvas is dirty")


def test_apply_is_not_clickable_while_one_is_in_flight():
    print("test_apply_is_not_clickable_while_one_is_in_flight")
    scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state())
    check(wiring_ui.MESH_AGENT_OT_apply_wiring.poll(bpy.context) is True,
          "Apply is clickable on a settled canvas")
    tree.cadex_pending = True
    check(wiring_ui.MESH_AGENT_OT_apply_wiring.poll(bpy.context) is False,
          "and not while a push is in flight")
    tree.cadex_pending = False


def test_a_terminal_says_which_column_it_is_in():
    """Two rows called sda are two ends of one terminal, not two (ADR-122).

    ``tree.links.new`` raises "Same input/output direction of sockets" for
    output→output *and* for input→input, so an undirected edge needs one of
    each — one row per terminal is not reachable inside the stock node editor.
    Asserted here rather than left as a puzzle, because it is the reason the
    canvas looks the way it does.
    """
    print("test_a_terminal_says_which_column_it_is_in")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[]))
    sen = next(n for n in tree.nodes if n.port == "sen")
    esp = next(n for n in tree.nodes if n.port == "esp")

    refused = ""
    try:
        tree.links.new(sen.outputs[0], esp.outputs[0])
    except Exception as exc:
        refused = str(exc)
    check("direction" in refused,
          "Blender refuses output->output even from the API: {!r}".format(
              refused))

    drawn = []

    class _Row:
        def __init__(self, sink):
            self._sink = sink

        def row(self, **_kwargs):
            return self

        def label(self, text="", **_kwargs):
            self._sink.append(text)

        def prop(self, _data, name, **_kwargs):
            self._sink.append("<" + name + ">")

    sen.outputs[0].draw(bpy.context, _Row(drawn), sen, "sda")
    sen.inputs[0].draw(bpy.context, _Row(drawn), sen, "sda")
    check(drawn[:1] == ["sda ▸"], "an output draws as 'sda ▸': {!r}".format(drawn))
    check("▸ sda" in drawn, "and an input as '▸ sda'")
    check(drawn.count("<soldered>") == 2,
          "with the solder checkbox on the socket row, where the terminal is")


def test_the_sidebar_lists_a_board_as_one_list_of_terminals():
    print("test_the_sidebar_lists_a_board_as_one_list_of_terminals")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(boards=True))
    sen = next(n for n in tree.nodes if n.port == "sen")
    for node in tree.nodes:
        node.select = False
    check(wiring_ui._selected_board(tree) is None,
          "nothing is selected, so no board is listed")
    sen.select = True
    # `==`, not `is`: iterating a Blender collection hands back a fresh Python
    # wrapper each time, so identity is not a usable comparison here.
    check(wiring_ui._selected_board(tree) == sen, "selecting one finds it")
    listed = [str(socket.terminal) for socket in wiring_ui._terminals_of(sen)]
    check(listed == list(SIGNALS),
          "and the board reads as one row per terminal: {!r}".format(listed))
    check(hasattr(bpy.types, "MESH_AGENT_OT_select_terminal"),
          "with an operator to make one of them active")


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


def _rectangle(width, height, z, count=6, centre=(0.0, 0.0), angle=0.0):
    """A rectangle's outline, ``count`` points per side, optionally rotated."""

    import math
    cos, sin = math.cos(angle), math.sin(angle)
    half_w, half_h = width / 2.0, height / 2.0
    corners = [(-half_w, -half_h), (half_w, -half_h),
               (half_w, half_h), (-half_w, half_h)]
    points = []
    for index in range(4):
        (x1, y1), (x2, y2) = corners[index], corners[(index + 1) % 4]
        for step in range(count):
            x = x1 + (x2 - x1) * step / count
            y = y1 + (y2 - y1) * step / count
            points.append((centre[0] + x * cos - y * sin,
                           centre[1] + x * sin + y * cos, z))
    return points


def test_fit_terminal_finds_a_bore_from_one_ring():
    """ADR-117: one ring is a bore's mouth and the wire ends flush in it."""
    print("test_fit_terminal_finds_a_bore_from_one_ring")
    points = _ring(0.5, 1.6, centre=(3.0, -2.0))
    row, report = pick.measure_selection(points, view_direction=(0.0, 0.0, 1.0))
    check(row is not None, "the fit succeeded: {!s}".format(report))
    if row is None:
        return
    check(report["kind"] == "hole", "and one ring on its own reads as a hole")
    check(report["fit_model"] == "circle", "because the circle model won")
    check(abs(row["origin"][0] - 3.0) < 1e-4 and abs(row["origin"][1] + 2.0) < 1e-4,
          "centred exactly on the bore")
    check(abs(row["origin"][2] - 1.6) < 1e-4,
          "and the landing is IN the selected ring's own plane")
    check("depth" not in row, "no depth: the bore behind the mouth is left empty")
    check(abs(row["hole_dia"] - 1.0) < 1e-4, "twice the radius as hole_dia")
    check(report["residual_mm"] < 1e-6, "residual is zero on an exact circle")
    check(report["far_loop_ignored"] is False, "and there was no second loop")


def test_selecting_both_rims_takes_the_near_one_and_says_so():
    """The far loop is dropped rather than paired for a depth (ADR-117).

    Which rim is near follows the axis, and the axis follows the viewport, so
    this is asserted from both sides — the engine's own selector took the
    wrong end first and only a kernel test caught it.
    """
    print("test_selecting_both_rims_takes_the_near_one_and_says_so")
    from mathutils import Vector

    points = _ring(0.5, 1.6) + _ring(0.5, 0.0)
    for view, expect_z, landing_z in (((0.0, 0.0, -1.0), -1.0, 1.6),
                                      ((0.0, 0.0, 1.0), 1.0, 0.0)):
        row, report = pick.measure_selection(points, view_direction=view)
        if row is None:
            check(False, "fit succeeded for view {!r}: {!s}".format(view, report))
            continue
        axis = Vector(row["axis"])
        check(abs(axis.z - expect_z) < 1e-6,
              "axis points away from a viewer at {!r}".format(view))
        check(report["far_loop_ignored"] is True, "the far rim was dropped")
        check(abs(row["origin"][2] - landing_z) < 1e-4,
              "and the landing is the rim the wire arrives at")
        check("depth" not in row, "with no depth measured across the two")


def test_fit_terminal_finds_a_pad_from_a_rectangle():
    """The pad half of ADR-117: a rectangle, fitted as a rectangle."""
    print("test_fit_terminal_finds_a_pad_from_a_rectangle")
    row, report = pick.measure_selection(
        _rectangle(2.0, 1.0, 0.0, centre=(4.0, 5.0)),
        view_direction=(0.0, 0.0, 1.0))
    check(row is not None, "the fit succeeded: {!s}".format(report))
    if row is None:
        return
    check(report["kind"] == "pad", "a rectangle outline reads as a pad")
    check(report["fit_model"] == "rectangle", "because the rectangle model won")
    check(abs(row["origin"][0] - 4.0) < 1e-4 and abs(row["origin"][1] - 5.0) < 1e-4,
          "the wire ends at the rectangle's centre")
    check("hole_dia" not in row, "and there is no bore diameter")
    check("depth" not in row, "nor a depth")
    check(abs(report["width_mm"] - 2.0) < 1e-4
          and abs(report["height_mm"] - 1.0) < 1e-4,
          "width and height are in the REPORT, so pad_dia_mm can be chosen")
    check("width_mm" not in row and "height_mm" not in row,
          "and never in the row: a layout row has no rectangle field (ADR-065)")


def test_a_rotated_rectangle_fits_as_well_as_an_axis_aligned_one():
    """Rotating calipers, not an axis-aligned box: the pad may sit at any angle."""
    print("test_a_rotated_rectangle_fits_as_well_as_an_axis_aligned_one")
    import math
    row, report = pick.measure_selection(
        _rectangle(3.0, 1.2, 0.0, centre=(-2.0, 1.0), angle=math.radians(31.0)),
        view_direction=(0.0, 0.0, 1.0))
    check(row is not None, "the fit succeeded: {!s}".format(report))
    if row is None:
        return
    check(report["kind"] == "pad", "still a pad at 31 degrees")
    check(report["residual_mm"] < 1e-6,
          "and an exact fit, which an axis-aligned box could not manage")
    sides = sorted((report["width_mm"], report["height_mm"]))
    check(abs(sides[0] - 1.2) < 1e-4 and abs(sides[1] - 3.0) < 1e-4,
          "with the true side lengths recovered")
    check(abs(row["origin"][0] + 2.0) < 1e-4 and abs(row["origin"][1] - 1.0) < 1e-4,
          "centred on the pad")


def test_four_corners_are_ambiguous_and_are_refused_not_guessed():
    """ADR-117: a rectangle's four corners are concyclic, so nothing can tell.

    ADR-067's rule is that a residual is a quality signal and never a
    classifier, which is why "the circle fits well" cannot decide this. Both
    models fit *exactly*, the margin between them is zero, and the honest
    answer is to say so and let the operator's enum settle it.
    """
    print("test_four_corners_are_ambiguous_and_are_refused_not_guessed")
    square = [(1.0, 1.0, 0.0), (-1.0, 1.0, 0.0), (-1.0, -1.0, 0.0), (1.0, -1.0, 0.0)]
    row, report = pick.measure_selection(square, view_direction=(0.0, 0.0, 1.0))
    check(row is None, "AUTO refuses rather than guessing")
    check("equally well" in str(report), "and says the two models tie")
    check("Choose Hole or Pad" in str(report), "naming the way out")
    check("2.828" in str(report) and "2.000" in str(report),
          "with both fits quoted: the circle's diameter and the rectangle")

    # The operator's enum is the override, and it is what makes the refusal
    # workable rather than a dead end.
    forced, forced_report = pick.measure_selection(square, kind='PAD',
                                                  view_direction=(0.0, 0.0, 1.0))
    check(forced is not None and "hole_dia" not in forced,
          "kind='PAD' takes the rectangle")
    check(forced_report is not None and abs(forced_report["width_mm"] - 2.0) < 1e-4,
          "measuring the square it really is")
    bored, bored_report = pick.measure_selection(square, kind='HOLE',
                                                 view_direction=(0.0, 0.0, 1.0))
    check(bored is not None and "hole_dia" in bored, "kind='HOLE' takes the circle")
    check(bored_report is not None and bored_report["kind_guessed"] is False,
          "and neither is recorded as a guess")


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
            check(report["kind"] == "hole",
                  "{:s}: noise does not turn a rim into a pad".format(label))
            check(0.0 < report["residual_mm"] < 0.05,
                  "{:s}: residual is a usable quality signal ({:.4f})".format(
                      label, report["residual_mm"]))
            check(report["model_margin"] > pick.AMBIGUOUS_MARGIN,
                  "{:s}: and the circle still beats the rectangle clearly "
                  "({:.4f})".format(label, report["model_margin"]))


def test_a_scribble_is_refused_rather_than_averaged():
    """The quality gate survives the second model (ADR-117).

    Two models is not two chances to accept: whichever wins still has to fit.
    The bar moved with the second model, though, and the fixture had to move
    with it — the old scribble was six points scattered round the *edge* of a
    blob, which is not a circle but is very nearly a rectangle's outline, and
    accepting it as a pad is the right answer. What is neither shape is a
    selection with points in the **middle**, which is what a lasso over a
    face actually gives you.
    """
    print("test_a_scribble_is_refused_rather_than_averaged")
    points = [(0.0, 0.0, 0.0), (5.0, 0.1, 0.0), (1.0, 4.0, 0.0),
              (4.5, 3.8, 0.0), (0.2, 2.0, 0.0), (2.5, 0.05, 0.0),
              (2.5, 2.0, 0.0), (3.1, 1.6, 0.0)]
    row, report = pick.measure_selection(points, view_direction=(0.0, 0.0, 1.0))
    check(row is None, "a selection that is neither shape is refused")
    check("is not a" in str(report) or "equally well" in str(report),
          "and says which fit it could not make: {!s}".format(report))
    # Forcing a kind does not force it through: the gate is about quality, and
    # the enum only settles which model is being judged.
    for kind in ('HOLE', 'PAD'):
        forced, forced_report = pick.measure_selection(
            points, kind=kind, view_direction=(0.0, 0.0, 1.0))
        check(forced is None,
              "kind={!r} does not override the quality gate: {!s}".format(
                  kind, forced_report))


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
    check("MEASURED a hole terminal" in note, "the note says terminal, and which kind")
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
    check(note.count("MEASURED a hole terminal") == 19,
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


def test_the_canvas_is_pointed_at_the_tree_the_sidebar_reads():
    """Regression: the sidebar was full and the canvas was blank (ADR-074).

    ``node_draw_space`` wraps everything it draws in
    ``if (snode.treepath.last)``, and only ``ED_node_tree_start`` pushes onto
    ``treepath``. ``snode_set_context`` calls it on every redraw — but only
    for a tree type that supplies ``get_from_context``, and ours did not. The
    panels never noticed, because ``wiring_ui._tree`` reads
    ``scene.cadex_wiring`` directly and uses the space only as a filter.
    """
    print("test_the_canvas_is_pointed_at_the_tree_the_sidebar_reads")
    scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state())

    getter = getattr(wiring.CadexWiringTree, "get_from_context", None)
    check(callable(getter), "the tree type supplies get_from_context")
    if not callable(getter):
        return
    check(isinstance(
        wiring.CadexWiringTree.__dict__.get("get_from_context"), classmethod),
        "as a classmethod, which is how Blender calls it")

    result = wiring.CadexWiringTree.get_from_context(bpy.context)
    check(isinstance(result, tuple) and len(result) == 3,
          "returning (tree, owner id, from id)")
    check(result[0] is tree, "and the tree is this scene's harness")

    # The symptom itself, named: a populated tree beside a space showing
    # nothing is the state that has to be treated as needing attachment.
    class _Space:
        tree_type = "CadexWiringTree"
        node_tree = None

    check(len(tree.nodes) > 0 and _Space.node_tree is None
          and wiring.CadexWiringTree.get_from_context(bpy.context)[0] is tree,
          "a space with no tree is answered with the one that has the nodes")

    # It must survive a scene with no wiring at all rather than raise from a
    # draw, which would take the whole editor down.
    reset_scene()
    check(wiring.CadexWiringTree.get_from_context(bpy.context)[0] is None,
          "and a scene with no harness answers None rather than raising")


def test_the_wiring_toggle_sets_the_type_before_the_tree():
    """The order is the bug, so the order is what is asserted (ADR-074).

    ``rna_SpaceNodeEditor_node_tree_poll`` rejects the assignment unless
    ``snode->tree_idname`` already matches the tree's idname, and ``ui_type``
    is what sets it — so ``node_tree =`` first is silently dropped. Read off
    the operator's own source, the same way
    ``test_the_sync_button_is_always_reachable`` reads the header's.
    """
    print("test_the_wiring_toggle_sets_the_type_before_the_tree")
    import inspect as _inspect

    check(hasattr(bpy.types, "MESH_AGENT_OT_toggle_wiring"),
          "the toggle is registered whether or not the editor exists")
    source = _inspect.getsource(wiring_ui.MESH_AGENT_OT_toggle_wiring.execute)
    ui_type = source.index("ui_type")
    node_tree = source.index("node_tree =")
    check(ui_type < node_tree,
          "ui_type is set before node_tree, or the poll rejects it")
    check("temp_override" in source[:ui_type],
          "and the area-type change carries a window, or it no-ops")

    # NODE_EDITOR is shared, so the predicate must discriminate on the tree
    # type -- a toggle keyed on the space type alone closes the compositor.
    predicate = _inspect.getsource(wiring_ui.wiring_area)
    check("tree_type" in predicate,
          "and the open/close predicate matches on the tree type, not just "
          "the space type")


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
    # Since ADR-122 a terminal is soldered by default, so the state that
    # proves the flag round-trips at all is the *cleared* one.
    for socket in _sockets(tree, "sen.gnd"):
        socket.soldered = False

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
    check(all(s.soldered for s in _sockets(tree, "sen.sda"))
          and not any(s.soldered for s in _sockets(tree, "sen.gnd")),
          "and its solder flag, in both states")
    check(len(wiring.stored_rows(tree)) == 1, "the row table survived")
    check(tree.cadex_revision == "r1", "and the revision it mirrors")
    reset_scene()



# ---------------------------------------------------------------------------
# ADR-118 — dragging a routed wire onto the path you wanted


PATH = [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 2.0],
        [12.0, 4.0, 9.0], [30.0, 4.0, 9.0],
        [40.0, 0.0, 2.0], [40.0, 0.0, 1.0], [40.0, 0.0, 0.0]]
WAYPOINTS = [[12.0, 4.0, 9.0], [30.0, 4.0, 9.0]]


def _routed_tree(waypoints=None, kind=None, output="wire_sda"):
    """A canvas holding one routed wire, and its cable active in the viewport.

    The wire is identified by the **object**, not by a link: a Blender
    ``NodeLink`` carries no selection state at all (its RNA is the four
    endpoints plus is_hidden/is_muted/is_valid), so "the selected wire" does
    not exist on the canvas — and two selected board nodes would be ambiguous
    the moment two signals run between the same pair, which is normal.
    """
    scene, tree = _fresh_tree()
    row = {"name": "sda", "a": "sen.sda", "b": "esp.sda",
           "gauge_mm": 0.8, "solder": False, "enabled": True,
           "path": PATH,
           "waypoints": WAYPOINTS if waypoints is None else waypoints}
    if kind is not None:
        row["kind"] = kind
        row["editable"] = False
    wiring.apply_state(tree, _state(wires=[row]))

    cable = bpy.data.objects.new(output, bpy.data.meshes.new(output))
    cable[cadex_hydrate.OUTPUT_PROP] = output
    scene.collection.objects.link(cable)
    bpy.context.view_layer.objects.active = cable
    return scene, tree


def test_the_editable_part_of_a_route_is_the_interior_the_engine_published():
    """No stub arithmetic in the shell (ADR-118).

    The engine publishes `path` and `waypoints` separately precisely so that
    nothing here has to know how many collinear knots a stand-off stub is
    written as — which is a number that has already changed once (ADR-114).
    """
    print("test_the_editable_part_of_a_route_is_the_interior_the_engine_published")
    check(wire_path._interior({"path": PATH, "waypoints": WAYPOINTS}) == WAYPOINTS,
          "the published interior is what you get to drag")
    # A straight run has no interior and still needs something to grab.
    single = wire_path._interior({"path": PATH, "waypoints": []})
    check(len(single) == 1, "a straight run yields one handle")
    check(abs(single[0][0] - 20.0) < 1e-9,
          "at the midpoint of its own centreline")
    check(wire_path._interior({}) == [], "and a row with no route yields none")


def test_editing_a_wire_path_builds_a_curve_you_can_drag():
    print("test_editing_a_wire_path_builds_a_curve_you_can_drag")
    scene, _tree = _routed_tree()
    wire_path.clear(scene)
    result = bpy.ops.mesh_agent.edit_wire_path()
    check(result == {'FINISHED'}, "the operator ran: {!r}".format(result))
    obj = wire_path.path_object(scene)
    check(obj is not None, "a curve object exists")
    if obj is None:
        return
    check(obj.type == 'CURVE', "and it is a real Blender curve, not a gizmo")
    check(obj.hide_select is False, "selectable, because it exists to be grabbed")
    check(obj.hide_render is True and obj.display_type == 'WIRE',
          "but drawn as an overlay and never rendered")
    points = [tuple(round(v, 5) for v in p.co[:3])
              for spline in obj.data.splines for p in spline.points]
    check(points == [tuple(p) for p in WAYPOINTS],
          "seeded with the interior alone: {!r}".format(points))
    check(str(obj.get(wire_path.ROW_PROP)) == "sda", "and it knows its row")
    # It lives in its own collection, so the hydrate GC never sees it.
    check(wire_path.COLLECTION_NAME in bpy.data.collections,
          "in a sibling collection of Model")
    wire_path.clear(scene)
    reset_scene()


def test_confirming_a_dragged_path_queues_it_and_deletes_the_curve():
    print("test_confirming_a_dragged_path_queues_it_and_deletes_the_curve")
    scene, _tree = _routed_tree()
    wire_path.clear_paths()
    bpy.ops.mesh_agent.edit_wire_path()
    obj = wire_path.path_object(scene)
    if obj is None:
        check(False, "the curve was built")
        return
    # Drag one control point clear of whatever was in the way.
    obj.data.splines[0].points[0].co = (12.0, 4.0, 25.0, 1.0)
    bpy.ops.mesh_agent.confirm_wire_path()

    check(wire_path.pending_path_count() == 1, "the path queued for the turn")
    note = wire_path.consume_wire_path_notes()
    check("DRAGGED a path" in note, "the note says the path was dragged")
    check("'sda'" in note, "and names the row it belongs to")
    check("sen.sda" in note and "esp.sda" in note, "and both endpoints")
    check("[12.0, 4.0, 25.0]" in note, "carrying the moved point")
    check("waypoints=" in note, "and names the argument to add")
    check("does not move when a parameter moves" in note,
          "and says the staleness out loud, which is the ADR-056 reversal")
    check(wire_path.path_object(scene) is None,
          "the curve is gone once it has been sent")
    reset_scene()


def test_cancelling_leaves_the_script_and_the_wire_alone():
    """The third state, and the reason it is an operator (ADR-118)."""
    print("test_cancelling_leaves_the_script_and_the_wire_alone")
    scene, _tree = _routed_tree()
    wire_path.clear_paths()
    bpy.ops.mesh_agent.edit_wire_path()
    check(wire_path.path_object(scene) is not None, "a curve is open")
    bpy.ops.mesh_agent.cancel_wire_path()
    check(wire_path.path_object(scene) is None, "and cancel removes it")
    check(wire_path.pending_path_count() == 0,
          "queueing nothing, so the next turn carries no path")
    check(wire_path.consume_wire_path_notes() == "", "and no note")
    reset_scene()


def test_a_bundle_conductors_path_is_read_only():
    """ADR-115 §4: a bundle's route belongs to the bundle."""
    print("test_a_bundle_conductors_path_is_read_only")
    scene, _tree = _routed_tree(waypoints=[], kind="bundle")
    wire_path.clear(scene)
    # bpy.ops raises when an operator reports an ERROR, so the refusal is the
    # exception -- and its message is the part worth pinning.
    refused = ""
    try:
        bpy.ops.mesh_agent.edit_wire_path()
    except RuntimeError as exc:
        refused = str(exc)
    check("bundle" in refused,
          "editing one conductor is refused: {!r}".format(refused))
    check("script" in refused, "and says where a bundle's route is changed")
    check(wire_path.path_object(scene) is None, "and no curve is built")
    reset_scene()


def test_the_three_wire_path_operators_are_registered():
    print("test_the_three_wire_path_operators_are_registered")
    for name in ("edit_wire_path", "confirm_wire_path", "cancel_wire_path"):
        check(hasattr(bpy.ops.mesh_agent, name),
              "mesh_agent.{:s} is registered".format(name))


# ---------------------------------------------------------------------------
# ADR-119 — "define this as a board"


def _hydrated(output="range_finder_board"):
    scene, _tree = _fresh_tree()
    obj = bpy.data.objects.new(output, bpy.data.meshes.new(output))
    obj[cadex_hydrate.OUTPUT_PROP] = output
    scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return scene, obj


def test_define_board_queues_the_engines_output_key_and_not_a_blender_name():
    """The identity is the engine's, which is the whole risk of this gesture.

    Everything else in the add-on routes object identity through the engine
    deliberately; this one starts from a click on the mirror, so it is the one
    that has to convert.
    """
    print("test_define_board_queues_the_engines_output_key_and_not_a_blender_name")
    pick.clear_boards()
    _scene, obj = _hydrated()
    # A Blender name that is NOT the output key: `.001` suffixes are exactly
    # how these drift apart.
    obj.name = "range_finder_board.001"

    bpy.ops.mesh_agent.define_board(name="range finder")
    check(pick.pending_board_count() == 1, "the board queued")
    note = pick.consume_board_notes()
    check("'range_finder_board'" in note, "the note carries the output key")
    check("range_finder_board.001" not in note,
          "and never the Blender object's name")
    check("'range_finder'" in note, "with the name, cleaned to a port name")
    check("nets(ports=" in note, "and asks for it to be declared as a port")
    check(pick.pending_board_count() == 0, "draining empties the queue")
    reset_scene()


def test_a_board_note_promises_around_neither_engine_limit():
    """ADR-113 §5, twice — because "this is the range finder" invites both."""
    print("test_a_board_note_promises_around_neither_engine_limit")
    pick.clear_boards()
    _scene, _obj = _hydrated()
    bpy.ops.mesh_agent.define_board(name="esp")
    note = pick.consume_board_notes()

    check("cannot avoid itself as a mesh" in note,
          "designating a board does not make it avoidable by its own wires")
    check("shape_from_mesh" in note and "multi-shell" in note,
          "and the workaround that exists does not always exist")
    check("does not conjure a node" in note,
          "a board with no terminals yet has no node: a node is a terminal set")
    reset_scene()


def test_a_designated_board_names_every_terminal_picked_on_it():
    """The second effect, and what makes the gesture compose (ADR-119).

    Click board, click terminals, one turn declares the whole port.
    """
    print("test_a_designated_board_names_every_terminal_picked_on_it")
    pick.clear_boards()
    pick.clear_terminals()
    _scene, obj = _hydrated()
    bpy.ops.mesh_agent.define_board(name="sen")
    check(str(obj.get(pick.BOARD_PROP)) == "sen",
          "the object is stamped with the board name")

    row, report = pick.measure_selection(_ring(0.5, 1.6),
                                         view_direction=(0.0, 0.0, 1.0))
    pick.queue_terminal({
        "output": str(obj.get(cadex_hydrate.OUTPUT_PROP) or ""),
        "object": obj.name, "row": row, "report": report,
        "board": str(obj.get(pick.BOARD_PROP) or ""),
    })
    note = pick.consume_terminal_notes()
    check("the board 'sen'" in note,
          "so the terminal note says which port it belongs to: {!r}".format(
              note[:160]))
    reset_scene()


def test_a_board_name_is_cleaned_into_something_nets_will_take():
    print("test_a_board_name_is_cleaned_into_something_nets_will_take")
    check(pick._board_name("Range Finder") == "range_finder", "spaces and case")
    check(pick._board_name("esp32-cam!") == "esp32_cam", "punctuation")
    check(pick._board_name("  __a__b__  ") == "a_b", "runs and edges")
    check(pick._board_name("32u4").startswith("b_"),
          "a leading digit, which a port name may not have")
    check(pick._board_name("") == "", "and nothing is nothing")


def test_define_board_needs_an_object_the_engine_built():
    print("test_define_board_needs_an_object_the_engine_built")
    reset_scene()
    scene = bpy.context.scene
    stray = bpy.data.objects.new("just_a_cube", bpy.data.meshes.new("just_a_cube"))
    scene.collection.objects.link(stray)
    bpy.context.view_layer.objects.active = stray

    check(pick.MESH_AGENT_OT_define_board.poll(bpy.context) is False,
          "an object the engine did not build is not a board")
    reset_scene()

# ---------------------------------------------------------------------------
# the board table (ADR-120) and the pick that writes it (ADR-121)


def test_a_declared_boards_sockets_carry_their_row():
    print("test_a_declared_boards_sockets_carry_their_row")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(boards=True))
    node = next(n for n in tree.nodes if n.port == "sen")
    check(node.board == "sen", "the node knows which board it is")
    check(node.board_editable is True, "and that its table is writable")
    socket = node.inputs[1]
    check(socket.has_row is True, "the socket carries a row")
    check(abs(socket.origin[1] - 2.54) < 1e-6, "with the row's own origin")
    check(abs(socket.axis[2] + 1.0) < 1e-6, "and its axis")
    check(abs(socket.hole_dia - 1.0) < 1e-6, "and its bore")


def test_a_selector_board_draws_but_holds_no_row():
    print("test_a_selector_board_draws_but_holds_no_row")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state())
    node = next(n for n in tree.nodes if n.port == "sen")
    check(node.board == "", "no declared board")
    check(node.board_editable is False, "so nothing here is writable")
    check(node.inputs[0].has_row is False, "and the socket holds no row")
    check(wiring.board_rows_from_tree(tree) == [],
          "so the canvas describes no terminal table at all")


def test_the_terminal_table_is_one_row_per_terminal():
    """A terminal is two sockets; the table it describes is not two rows."""
    print("test_the_terminal_table_is_one_row_per_terminal")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(ports=("sen",), wires=[], boards=True))
    rows = wiring.board_rows_from_tree(tree)
    check(len(rows) == 3, "three terminals, three rows")
    check([row["name"] for row in rows] == list(SIGNALS), "in declared order")
    check(rows[0]["board"] == "sen", "each naming its board")
    check(rows[0]["hole_dia"] == 1.0, "a hole keeps its bore")


def test_editing_a_row_field_mirrors_and_marks_the_tree():
    """A property write fires no NodeTree.update(), so the socket must."""
    print("test_editing_a_row_field_mirrors_and_marks_the_tree")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(boards=True))
    tree.cadex_dirty = False
    node = next(n for n in tree.nodes if n.port == "sen")
    node.inputs[0].origin = (9.0, 9.0, 9.0)
    check(abs(node.outputs[0].origin[0] - 9.0) < 1e-6,
          "the terminal's other socket followed")
    check(tree.cadex_dirty, "and the edit marked the canvas dirty")
    rows = wiring.board_rows_from_tree(tree)
    check(rows[0]["origin"] == [9.0, 9.0, 9.0], "the table carries the new row")
    tree.cadex_dirty = False


def test_renaming_a_terminal_carries_its_wires():
    print("test_renaming_a_terminal_carries_its_wires")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(boards=True))
    node = next(n for n in tree.nodes if n.port == "sen")
    ok, _report = wiring.rename_terminal(tree, node, "sda", "i2c_sda")
    check(ok, "the rename was accepted")
    check([row["name"] for row in wiring.board_rows_from_tree(tree)][0]
          == "i2c_sda", "the row moved")
    rows = {row["name"]: row for row in wiring.rows_from_tree(tree)}
    check("sda" in rows and rows["sda"]["a"] == "sen.i2c_sda",
          "and the wire that addressed it followed, keeping its own row")
    check(abs(rows["sda"]["gauge_mm"] - 0.8) < 1e-6, "gauge and all")
    tree.cadex_dirty = False


def test_a_rename_refuses_a_collision_and_a_read_only_board():
    print("test_a_rename_refuses_a_collision_and_a_read_only_board")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(boards=True))
    node = next(n for n in tree.nodes if n.port == "sen")
    ok, report = wiring.rename_terminal(tree, node, "sda", "gnd")
    check(not ok and "already has" in report, "a duplicate name is refused")
    wiring.apply_state(tree, _state(revision="r2"))
    plain = next(n for n in tree.nodes if n.port == "sen")
    ok, report = wiring.rename_terminal(tree, plain, "sda", "x")
    check(not ok and "stated by the script" in report,
          "and a selector board is not the editor's to rename")
    tree.cadex_dirty = False


def test_deleting_a_terminal_takes_its_wire():
    print("test_deleting_a_terminal_takes_its_wire")
    _scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(boards=True))
    node = next(n for n in tree.nodes if n.port == "sen")
    ok, _report = wiring.delete_terminal(tree, node, "sda")
    check(ok, "the delete was accepted")
    names = [row["name"] for row in wiring.board_rows_from_tree(tree)
             if row["board"] == "sen"]
    check(names == ["scl", "gnd"], "the row is gone from that board's table")
    check(len(tree.links) == 0, "and the link that landed on it went with it")
    tree.cadex_dirty = False


def test_the_no_op_guard_actually_fires():
    """The guard could never fire: engine rows carry a route and the canvas
    does not, so every comparison differed and a redrawn link cost a full
    re-execute (ADR-120)."""

    print("test_the_no_op_guard_actually_fires")
    scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[
        {"name": "sda", "a": "sen.sda", "b": "esp.sda", "gauge_mm": 0.8,
         "solder": True, "enabled": True,
         "path": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
         "waypoints": [[1.0, 0.0, 0.0]]},
    ]))
    ok, report = wiring.push(scene)
    check(ok and report == "No change.",
          "an untouched canvas sends nothing at all")

    sen = next(n for n in tree.nodes if n.port == "sen")
    esp = next(n for n in tree.nodes if n.port == "esp")
    tree.links.clear()
    tree.links.new(sen.outputs[0], esp.inputs[0])
    ok, report = wiring.push(scene)
    check(ok and report == "No change.",
          "and a link cut and redrawn in the same place still sends nothing")
    tree.cadex_dirty = False


def test_a_finished_push_keeps_the_route_it_was_not_told_about():
    """``_store_rows`` used to flatten the table to the canvas's six columns,
    which is what made Edit Wire Path report no published route."""

    print("test_a_finished_push_keeps_the_route_it_was_not_told_about")
    scene, tree = _fresh_tree()
    wiring.apply_state(tree, _state(wires=[
        {"name": "sda", "a": "sen.sda", "b": "esp.sda", "gauge_mm": 0.8,
         "solder": True, "enabled": True,
         "path": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
         "waypoints": [[1.0, 0.0, 0.0]]},
    ]))
    wiring.on_push_finished(scene, True, "")
    stored = {row["name"]: row for row in wiring.stored_rows(tree)}
    check("path" in stored.get("sda", {}), "the route survived the push")
    check(stored["sda"]["waypoints"] == [[1.0, 0.0, 0.0]],
          "and so did its editable interior")
    check(abs(stored["sda"]["gauge_mm"] - 0.8) < 1e-6,
          "with the canvas's own columns still authoritative")


def test_a_duplicate_port_is_reported_rather_than_dropped_in_silence():
    print("test_a_duplicate_port_is_reported_rather_than_dropped_in_silence")
    _scene, tree = _fresh_tree()
    state = _state(wires=[])
    state["components"].append(dict(state["components"][0]))
    wiring.apply_state(tree, state)
    check(len(tree.nodes) == 2, "the repeat is still not drawn")
    check("share a name" in tree.cadex_error,
          "but the canvas says so instead of looking broken")


def test_the_pick_writes_a_world_frame_row():
    """The measurement is data, and data goes in the table (ADR-121)."""
    print("test_the_pick_writes_a_world_frame_row")
    from mathutils import Matrix

    row, _report = pick.measure_selection(_ring(0.5, 1.6),
                                          view_direction=(0.0, 0.0, 1.0))
    placement = (Matrix.Translation((10.0, 0.0, 0.0))
                 @ Matrix.Rotation(1.5707963268, 4, 'Z'))
    written = pick.world_row(placement, row, "fc", "batt_pos")
    check(written["board"] == "fc" and written["name"] == "batt_pos",
          "the row is addressed <board>.<terminal>")
    check(written["frame"] == "world",
          "and marked world, because a click has no other frame")
    check(abs(written["origin"][0] - 10.0) < 1e-3,
          "the origin went through the placement")
    check(abs(written["hole_dia"] - 1.0) < 1e-3, "and the bore came with it")


def test_the_pick_sends_the_whole_table_and_replaces_by_name():
    print("test_the_pick_sends_the_whole_table_and_replaces_by_name")
    state = _state(ports=("fc",), wires=[], boards=True)
    rows = pick.terminal_rows(state)
    check([row["name"] for row in rows] == list(SIGNALS),
          "every existing row is read back off the engine's answer")
    written = {"board": "fc", "name": "scl", "origin": [1.0, 2.0, 3.0],
               "axis": [0.0, 0.0, -1.0], "frame": "world"}
    replaced = pick.rows_with(state, written)
    check(len(replaced) == 3, "re-measuring a terminal replaces its row")
    check(replaced[-1]["origin"] == [1.0, 2.0, 3.0], "with the new numbers")
    check(pick.free_name(state, "fc") == "t1",
          "and an unnamed pick gets a free name on that board")


def test_the_pick_falls_back_to_a_note_without_a_board():
    """A project with no boards(...) has no table to write into, and making
    one is authoring — which is the assistant's job (ADR-121)."""

    print("test_the_pick_falls_back_to_a_note_without_a_board")
    check(pick.board_of(_state(boards=True), "sen_board") == "sen",
          "a declared board is found by its output key")
    check(pick.board_of(_state(), "sen_board") == "",
          "a component that is no declared board is not one")
    selector = _state(ports=("sen",), boards=True)
    selector["components"][0]["editable"] = False
    check(pick.board_of(selector, "sen_board") == "",
          "and a selector board is not the editor's to write")


def test_the_two_terminal_operators_are_registered():
    print("test_the_two_terminal_operators_are_registered")
    check(hasattr(bpy.types, "MESH_AGENT_OT_rename_terminal"),
          "rename is registered whether or not the editor exists")
    check(hasattr(bpy.types, "MESH_AGENT_OT_delete_terminal"),
          "and so is delete")


def main():
    mesh_agent.register()
    try:
        for test in (
            test_the_wiring_tree_registers,
            test_a_board_node_names_a_script_output,
            test_a_terminal_is_keyed_by_property_not_by_name,
            test_a_sync_builds_the_graph_the_engine_describes,
            test_solder_rides_the_socket_because_a_link_cannot_hold_it,
            test_a_solder_toggle_is_an_edit_the_tree_notices,
            test_a_new_terminal_is_soldered_and_a_stored_no_stays_no,
            test_a_terminal_several_wires_land_on_holds_one_flag,
            test_both_sockets_of_one_terminal_hold_one_state,
            test_solder_can_be_turned_off_again,
            test_an_edit_marks_the_canvas_and_sends_nothing,
            test_apply_sends_once_and_the_pump_drives_it_to_completion,
            test_a_second_apply_carries_the_revision_the_first_one_returned,
            test_a_refused_apply_keeps_the_canvas_and_revert_discards_it,
            test_a_push_arriving_mid_flight_replaces_the_queued_one,
            test_the_apply_and_revert_operators_are_registered,
            test_apply_is_not_clickable_while_one_is_in_flight,
            test_a_terminal_says_which_column_it_is_in,
            test_the_sidebar_lists_a_board_as_one_list_of_terminals,
            test_the_graph_does_not_answer_its_own_edit,
            test_a_rebuild_keeps_the_layout,
            test_a_dropped_component_takes_its_node,
            test_a_drawn_link_becomes_one_row,
            test_a_redrawn_link_keeps_the_row_it_had,
            test_a_disabled_row_is_not_deleted_by_looking_at_it,
            test_two_sets_on_one_board_do_not_share_a_node,
            test_a_row_with_nowhere_to_land_holds_the_canvas,
            test_a_sync_clears_a_stuck_applying_flag,
            test_a_hand_built_wire_draws_but_is_never_pushed,
            test_a_legacy_harness_is_read_only,
            test_the_wiring_ui_registers_or_stands_down,
            test_a_declared_boards_sockets_carry_their_row,
            test_a_selector_board_draws_but_holds_no_row,
            test_the_terminal_table_is_one_row_per_terminal,
            test_editing_a_row_field_mirrors_and_marks_the_tree,
            test_renaming_a_terminal_carries_its_wires,
            test_a_rename_refuses_a_collision_and_a_read_only_board,
            test_deleting_a_terminal_takes_its_wire,
            test_the_no_op_guard_actually_fires,
            test_a_finished_push_keeps_the_route_it_was_not_told_about,
            test_a_duplicate_port_is_reported_rather_than_dropped_in_silence,
            test_the_pick_writes_a_world_frame_row,
            test_the_pick_sends_the_whole_table_and_replaces_by_name,
            test_the_pick_falls_back_to_a_note_without_a_board,
            test_the_two_terminal_operators_are_registered,
            test_fit_terminal_finds_a_bore_from_one_ring,
            test_selecting_both_rims_takes_the_near_one_and_says_so,
            test_fit_terminal_finds_a_pad_from_a_rectangle,
            test_a_rotated_rectangle_fits_as_well_as_an_axis_aligned_one,
            test_four_corners_are_ambiguous_and_are_refused_not_guessed,
            test_fewer_than_four_vertices_is_refused,
            test_a_noisy_rim_still_fits_and_reports_its_quality,
            test_a_scribble_is_refused_rather_than_averaged,
            test_the_editable_part_of_a_route_is_the_interior_the_engine_published,
            test_editing_a_wire_path_builds_a_curve_you_can_drag,
            test_confirming_a_dragged_path_queues_it_and_deletes_the_curve,
            test_cancelling_leaves_the_script_and_the_wire_alone,
            test_a_bundle_conductors_path_is_read_only,
            test_the_three_wire_path_operators_are_registered,
            test_define_board_queues_the_engines_output_key_and_not_a_blender_name,
            test_a_board_note_promises_around_neither_engine_limit,
            test_a_designated_board_names_every_terminal_picked_on_it,
            test_a_board_name_is_cleaned_into_something_nets_will_take,
            test_define_board_needs_an_object_the_engine_built,
            test_a_fitted_terminal_is_not_a_pin,
            test_several_picks_batch_into_one_turn,
            test_the_model_is_told_these_numbers_are_measured,
            test_the_graph_fills_itself,
            test_the_sync_button_is_always_reachable,
            test_the_canvas_is_pointed_at_the_tree_the_sidebar_reads,
            test_the_wiring_toggle_sets_the_type_before_the_tree,
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
