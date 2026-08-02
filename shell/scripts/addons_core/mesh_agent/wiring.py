# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Wiring graph: the harness as a node tree (ADR-066).

The engine grew a connection table and a way to read it (ADR-065). This is
the window that makes it a thing you can *do* something with: one Python node
tree hosted in Blender's stock Node Editor, where a board is a node, a
terminal is a socket, and a wire is a link you drag.

Three properties carry the module.

**The graph is a projection of the engine, never a second copy.**
:func:`sync_from_engine` rebuilds nodes, sockets and links from
``inspect scope="wiring"`` and *never* from what is on screen. That is what
makes a failed push recoverable: resync, and the link the user drew goes
away because the engine never accepted it. The one thing the graph owns and
the engine does not is **layout** — ``Node.location``, which lives in the
.blend and which a rebuild must never touch.

**It edits stored values, exactly as the sliders do.** A link change becomes
one debounced ``set_params(nets=[...])`` down the same path a slider drag
takes. It never writes the script text, and the AI is never in the loop.

**Terminals are keyed by a registered property, never by socket name.**
Blender dedups duplicate socket names into ``sda``/``sda_001`` identifiers
and ``node.inputs["sda"]`` returns whichever came first, so a name is not an
identity. And a ``NodeSocket`` refuses ``socket["key"] = v`` outright
(``bNodeSocket`` carries an ``IDProperty *`` in DNA but does not expose it to
``bpy_struct[]``), so the key has to be a registered ``StringProperty``. Both
facts were found by probing the shipped bundle, and a test pins them.

**Every terminal contributes two sockets**, one input and one output, both
carrying the same ``terminal`` string. Blender refuses an input→input link
("Same input/output direction of sockets") and a board is both source and
sink, so a single socket per terminal cannot express a harness at all. The
cost is honest — a 12-terminal board draws 24 rows — and the direction of a
link on the canvas is cosmetic: a row is stored with its endpoints in the
engine's own order.
"""

import json

import bpy

from .cadex_hydrate import OUTPUT_PROP


#: Set while :func:`sync_from_engine` mutates the tree. ``NodeTree.update()``
#: fires on *every* ``nodes.new`` / ``inputs.new`` / ``links.new``, so without
#: this the engine's own rebuild would start a push, which would start a
#: rebuild. A list rather than a module global so the closure below can write
#: it — the idiom ``model._suspend_updates`` already uses for the sliders.
_suspend = [False]

#: Roots with an edit waiting for the debounce to fire.
_dirty = set()

#: The same 150 ms the slider drag debounces on (``model._schedule_rebuild``).
_DEBOUNCE_SECONDS = 0.15

#: Grid pitch for a node the sync had to invent a position for.
_LAYOUT_PITCH_X = 340.0
_LAYOUT_PITCH_Y = 260.0
_LAYOUT_COLUMNS = 4

_HOLE_COLOR = (0.35, 0.62, 0.95, 1.0)
_PAD_COLOR = (0.95, 0.72, 0.28, 1.0)
_SOLDER_COLOR = (0.85, 0.92, 1.0, 1.0)
_IDLE_ALPHA = 0.35


def _clean_name(text):
    """A lower_snake_case row name the engine will accept."""

    out = []
    for char in str(text or "").lower():
        out.append(char if (char.isalnum() or char == "_") else "_")
    name = "".join(out).strip("_") or "wire"
    if not (name[0].isalpha() or name[0] == "_"):
        name = "w_" + name
    return name[:64]


def row_name(a, b):
    """The name a newly drawn link takes, from the two ends it joins."""

    return _clean_name("{}__{}".format(a.replace(".", "_"), b.replace(".", "_")))


def _pair(row):
    """A row's endpoints as an unordered key: direction on canvas is cosmetic."""

    return frozenset((str(row.get("a") or ""), str(row.get("b") or "")))


# ---------------------------------------------------------------------------
# the classes


def _solder_toggled(socket, _context):
    """A solder toggle is an edit, and nothing else in Blender says so.

    ``NodeTree.update()`` fires on topology — a link, a node, a socket added
    or removed — and never on a property written into an existing socket. So
    without this the 150 ms debounce never ran, no ``set_params(nets=...)``
    was ever sent, and the checkbox was picked up only incidentally, by the
    next edit that *did* change the topology (ADR-113).

    The mirror is the other half. A terminal is two sockets only because
    Blender refuses an input→input link, and which of the pair the sidebar
    draws is an accident of which end of the wire this board is; keeping them
    equal is what lets :func:`_solder_for` read either one.
    """

    if _suspend[0]:
        return
    tree = socket.id_data
    if getattr(tree, "bl_idname", "") != CadexWiringTree.bl_idname:
        return
    node = getattr(socket, "node", None)
    terminal = str(getattr(socket, "terminal", "") or "")
    value = bool(socket.soldered)
    if node is not None and terminal:
        _suspend[0] = True
        try:
            for other in list(node.inputs) + list(node.outputs):
                if other == socket:
                    continue
                if str(getattr(other, "terminal", "") or "") != terminal:
                    continue
                if bool(other.soldered) != value:
                    other.soldered = value
        finally:
            _suspend[0] = False
    if not getattr(tree, "cadex_editable", False):
        return
    _mark_dirty(tree)


class CadexTerminalSocket(bpy.types.NodeSocket):
    """One terminal, on one side of one board."""

    bl_idname = "CadexTerminalSocket"
    bl_label = "Terminal"

    terminal: bpy.props.StringProperty(
        name="Terminal",
        description="The engine's terminal name. This, not the socket name, "
                    "is the identity: Blender dedups duplicate socket names",
        default="",
    )
    kind: bpy.props.StringProperty(name="Kind", default="")
    soldered: bpy.props.BoolProperty(
        name="Soldered",
        description="Whether the connection landing here carries a joint",
        default=False,
        update=_solder_toggled,
    )

    def draw(self, _context, layout, _node, text):
        layout.label(text=text or self.terminal)

    def draw_color(self, _context, _node):
        """Colour is where solder state lives, because a link cannot hold it.

        Blender links carry no properties of their own, so there is nothing
        to hang "this end is soldered" on. The socket is the only honest
        place, and it is also the right granularity: ``part.solder`` takes a
        terminal, never a wire (ADR-063).
        """

        base = _SOLDER_COLOR if self.soldered else (
            _PAD_COLOR if self.kind == "pad" else _HOLE_COLOR)
        if self.is_linked:
            return base
        return (base[0], base[1], base[2], _IDLE_ALPHA)


class CadexBoardNode(bpy.types.Node):
    """One component with terminals: a board, a module, a motor."""

    bl_idname = "CadexBoardNode"
    bl_label = "Board"
    bl_icon = 'MESH_CUBE'

    port: bpy.props.StringProperty(
        name="Port",
        description="The name nets(ports=...) gave this component; half of "
                    "every endpoint address",
        default="",
    )
    # Deliberately the same string cadex_hydrate keys its objects by, so
    # "which object is this node" is a lookup rather than a convention. A
    # test asserts the two agree.
    cadex_output: bpy.props.StringProperty(
        name="Output",
        description="The script result key this component is published as",
        default="",
    )

    @classmethod
    def poll(cls, tree):
        return getattr(tree, "bl_idname", "") == CadexWiringTree.bl_idname

    def draw_buttons(self, _context, layout):
        if self.cadex_output:
            layout.label(text=self.cadex_output, icon='OUTLINER_OB_MESH')


class CadexWiringTree(bpy.types.NodeTree):
    """The harness of one project."""

    # The C++ filter in rna_SpaceNodeEditor_tree_type_poll keys on this
    # prefix, so a second Cadex tree needs no C++ edit (ADR-066).
    bl_idname = "CadexWiringTree"
    bl_label = "Wiring"
    bl_description = "The project's harness: boards, terminals and wires"
    # Required. Registration raises without it.
    bl_icon = 'NODETREE'

    cadex_revision: bpy.props.StringProperty(default="")
    #: The last revision a sync was *attempted* for, successful or not.
    #: Without it, a project with no accepted revision re-asks the
    #: engine on every single redraw.
    cadex_attempted_revision: bpy.props.StringProperty(default="")
    cadex_root: bpy.props.StringProperty(default="")
    cadex_editable: bpy.props.BoolProperty(default=False)
    cadex_source: bpy.props.StringProperty(default="")
    cadex_pending: bpy.props.BoolProperty(default=False)
    #: Set when the last sync could not draw every row the engine sent, so
    #: the canvas is not a faithful projection and must not be pushed back:
    #: a push replaces the declared table wholesale (ADR-065), and a table
    #: built from a canvas missing links is a wire deletion (ADR-115).
    cadex_stale: bpy.props.BoolProperty(default=False)
    cadex_error: bpy.props.StringProperty(default="")
    #: The row table, as JSON. Links hold no properties, so gauge, solder,
    #: enabled and the row *name* have to live beside the topology.
    cadex_rows: bpy.props.StringProperty(default="[]")
    new_gauge_mm: bpy.props.FloatProperty(
        name="New Wire Gauge",
        description="Gauge given to a connection drawn in this editor",
        default=0.8, min=0.01, max=20.0, unit='LENGTH',
    )

    @classmethod
    def get_from_context(cls, context):
        """Which tree a Wiring editor shows: this scene's, always (ADR-074).

        This is what puts nodes on the *canvas* rather than only in the
        sidebar, and it is worth being precise about why. Everything
        ``node_draw_space`` draws is inside ``if (snode.treepath.last)``, and
        only ``ED_node_tree_start`` pushes onto ``treepath``. ``snode_set_
        context`` calls it on every redraw — but *only* if the tree type
        supplies this callback, and ours did not, so ``ntree`` stayed null and
        the editor drew an empty grid while ``wiring_ui``'s panels, which read
        ``scene.cadex_wiring`` directly, listed every board.

        A callback rather than an operator because it repairs the editor
        however it is opened: from the editor-type menu, from a restored
        .blend, from a split, with nothing to keep in sync. The two ``None``s
        are the ID owner and the "from" ID — a shader tree returns its
        material there, and a harness belongs to the scene, which the caller
        already has.
        """

        scene = getattr(context, "scene", None)
        return getattr(scene, "cadex_wiring", None), None, None

    def update(self):
        """Blender's change hook: fires on every link, node and socket edit."""

        if _suspend[0] or not self.cadex_editable:
            return
        _mark_dirty(self)


# ---------------------------------------------------------------------------
# the row table


def stored_rows(tree):
    try:
        rows = json.loads(tree.cadex_rows or "[]")
    except ValueError:
        return []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _store_rows(tree, rows):
    tree.cadex_rows = json.dumps(list(rows))


def rows_from_tree(tree):
    """The connection table the canvas currently describes.

    Every link becomes one row. Attributes that a link cannot carry — the
    name, the gauge, the two flags — come from the stored table, matched on
    the unordered endpoint pair, so redrawing a link the user just cut
    restores what it had rather than resetting it.
    """

    known = {_pair(row): row for row in stored_rows(tree)}
    disabled = [row for row in stored_rows(tree) if not row.get("enabled", True)]
    rows = []
    seen = set()
    for link in tree.links:
        a = _address(link.from_node, link.from_socket)
        b = _address(link.to_node, link.to_socket)
        if not a or not b or a == b:
            continue
        key = frozenset((a, b))
        if key in seen:
            continue
        seen.add(key)
        previous = known.get(key, {})
        row = {
            "name": str(previous.get("name") or row_name(a, b)),
            "a": a,
            "b": b,
            "gauge_mm": float(previous.get("gauge_mm")
                              or tree.new_gauge_mm),
            "solder": bool(_solder_for(tree, a, b, previous)),
            "enabled": True,
        }
        if not previous.get("editable", True):
            # A cable or bundle the script built outside nets(...). It draws
            # like any other link and `declared_rows` keeps it out of the
            # table that gets pushed — the marker is what tells them apart.
            row["editable"] = False
            row["kind"] = str(previous.get("kind") or "")
        rows.append(row)
    # A disabled row has no link on the canvas — there is nothing to draw for
    # a wire that is not built — so it would otherwise be deleted by the act
    # of looking at it.
    for row in disabled:
        if _pair(row) not in seen:
            rows.append(dict(row))
    return _uniquely_named(rows)


def declared_rows(rows):
    """The half of the table ``set_params(nets=...)`` is allowed to carry.

    The call replaces the declared list wholesale, and a row the script wrote
    by hand is not in that list — sending one back would either be refused
    (``canonical_rows`` takes no ``editable`` key) or, worse, quietly promote
    a bundle conductor into a declared wire.
    """

    return [dict(row) for row in rows if row.get("editable", True)]


def _uniquely_named(rows):
    seen = {}
    for row in rows:
        name = _clean_name(row.get("name"))
        if name in seen:
            index = 2
            while "{}_{}".format(name, index) in seen:
                index += 1
            name = "{}_{}".format(name, index)
        seen[name] = True
        row["name"] = name
    return rows


def _solder_for(tree, a, b, previous):
    """Solder follows the sockets, which is where the user toggles it.

    Authoritative, not monotone: if either end resolves to a socket, those
    sockets *are* the answer, so unticking takes the joint away exactly as
    ticking puts one there. It used to fall through to the stored row
    whenever the sockets read False, which meant solder could only ever be
    turned on (ADR-113). The stored value is the fallback for one case only —
    a row with no sockets on the canvas at all, which is a disabled row, and
    there is nothing to read from it.

    A row carries one flag and a connection has two ends, so the rule is
    *any*: tick either end and the row is soldered; it goes away when both
    ends are clear. That is the same rule ``_derived_wires`` applies to a
    script's own ``part.solder`` calls, so the two tables agree.
    """

    sockets = _sockets_at(tree, a) + _sockets_at(tree, b)
    if sockets:
        return any(bool(socket.soldered) for socket in sockets)
    return bool(previous.get("solder", False))


def _address(node, socket):
    port = str(getattr(node, "port", "") or "")
    terminal = str(getattr(socket, "terminal", "") or "")
    if not port or not terminal:
        return ""
    return "{}.{}".format(port, terminal)


# ---------------------------------------------------------------------------
# the tree itself


def ensure_tree(scene):
    """Find or create this scene's wiring tree."""

    tree = getattr(scene, "cadex_wiring", None)
    if tree is not None and tree.bl_idname == CadexWiringTree.bl_idname:
        return tree
    tree = bpy.data.node_groups.new("Wiring", CadexWiringTree.bl_idname)
    # A real user, so the tree saves in the .blend without a fake user.
    scene.cadex_wiring = tree
    return tree


def _find_node(tree, port):
    for node in tree.nodes:
        if str(getattr(node, "port", "") or "") == port:
            return node
    return None


def _reconcile_sockets(node, terminals):
    """Match the engine's terminal list onto the node's two socket lists."""

    wanted = [str(item.get("name") or "") for item in terminals]
    kinds = {str(item.get("name") or ""): str(item.get("kind") or "")
             for item in terminals}
    for collection, is_output in ((node.inputs, False), (node.outputs, True)):
        have = {str(getattr(socket, "terminal", "") or ""): socket
                for socket in collection}
        for name in list(have):
            if name not in wanted or not name:
                collection.remove(have.pop(name))
        for name in wanted:
            socket = have.get(name)
            if socket is None:
                socket = collection.new(CadexTerminalSocket.bl_idname, name)
                socket.terminal = name
                have[name] = socket
            socket.kind = kinds.get(name, "")
            socket.soldered = False
            if not is_output:
                # A terminal may carry several links: that is what a
                # multi-drop net looks like on screen.
                socket.link_limit = 64
        for index, name in enumerate(wanted):
            socket = have.get(name)
            if socket is None:
                continue
            current = list(collection).index(socket)
            if current != index:
                collection.move(current, index)


def apply_state(tree, state, root=""):
    """Rebuild the graph from one ``inspect scope="wiring"`` payload.

    Nodes, sockets and links come from the engine. ``location``, ``label``,
    ``width``, ``color`` and ``parent`` are the user's layout and are never
    touched on a node that already exists — which is the whole reason this
    reconciles rather than clearing and recreating.
    """

    if not isinstance(state, dict):
        return False
    components = list(state.get("components") or [])
    rows = [dict(row) for row in list(state.get("wires") or [])]
    _suspend[0] = True
    try:
        tree.cadex_root = str(root or tree.cadex_root)
        tree.cadex_source = str(state.get("source") or "")
        tree.cadex_editable = bool(state.get("editable"))
        wanted_ports = []
        for index, component in enumerate(components):
            port = str(component.get("port") or "")
            if not port or port in wanted_ports:
                # The engine names one node per terminal set and those names
                # are distinct (ADR-115). A repeat would mean two sets sharing
                # a node, and `_reconcile_sockets` would hand the node the
                # *last* set's terminals — silently unaddressing the first
                # set's, which is how three declared wires became no links at
                # all. Cheap to assert here, and the failure it prevents is
                # invisible.
                continue
            wanted_ports.append(port)
            node = _find_node(tree, port)
            if node is None:
                node = tree.nodes.new(CadexBoardNode.bl_idname)
                node.port = port
                node.location = (
                    _LAYOUT_PITCH_X * (index % _LAYOUT_COLUMNS),
                    -_LAYOUT_PITCH_Y * (index // _LAYOUT_COLUMNS),
                )
            node.cadex_output = str(component.get("output") or "")
            node.label = node.cadex_output or port
            _reconcile_sockets(node, list(component.get("terminals") or []))
        # Contract-driven GC, the peer of hydrate_display's: a component the
        # script no longer declares takes its node with it. A *renamed* port
        # loses its position, which is correct — it is a different port.
        for node in [n for n in tree.nodes
                     if str(getattr(n, "port", "") or "") not in wanted_ports]:
            tree.nodes.remove(node)

        tree.links.clear()
        undrawn = []
        for row in rows:
            if not row.get("enabled", True):
                continue
            start = _socket_at_side(tree, str(row.get("a") or ""), outputs=True)
            end = _socket_at_side(tree, str(row.get("b") or ""), outputs=False)
            if start is None or end is None:
                undrawn.append(str(row.get("name") or "?"))
                continue
            tree.links.new(start, end)
            if row.get("solder"):
                for address in (row.get("a"), row.get("b")):
                    for socket in _sockets_at(tree, str(address or "")):
                        socket.soldered = True
        _store_rows(tree, rows)
        tree.cadex_revision = str(state.get("revision") or "")
        # A row whose endpoint resolves to no socket is a hole in the
        # projection, and the canvas is only safe to push while it is a whole
        # one. Say so rather than drawing a subset that looks complete.
        tree.cadex_stale = bool(undrawn)
        if undrawn:
            tree.cadex_error = (
                "{:d} connection(s) have no terminal to attach to on the "
                "canvas ({}); editing is held until the model and the "
                "harness agree.".format(len(undrawn), ", ".join(undrawn[:4])))
        # The sync *is* the settling: whatever a push was waiting for, what
        # is on screen now came from the engine. Without this a push that
        # never reported back left "applying…" in the header for the life of
        # the file, because the flag saves into the .blend (ADR-115).
        tree.cadex_pending = False
        return True
    finally:
        _suspend[0] = False


def _sockets_at(tree, address):
    port, _, terminal = str(address).partition(".")
    found = []
    for node in tree.nodes:
        if str(getattr(node, "port", "") or "") != port:
            continue
        for socket in list(node.inputs) + list(node.outputs):
            if str(getattr(socket, "terminal", "") or "") == terminal:
                found.append(socket)
    return found


def _socket_at_side(tree, address, *, outputs):
    port, _, terminal = str(address).partition(".")
    node = _find_node(tree, port)
    if node is None:
        return None
    for socket in (node.outputs if outputs else node.inputs):
        if str(getattr(socket, "terminal", "") or "") == terminal:
            return socket
    return None


# ---------------------------------------------------------------------------
# the two directions


def sync_from_engine(scene, force=False):
    """Read the engine's wiring and project it onto the tree."""

    from . import cadex_backend

    tree = ensure_tree(scene)
    root = cadex_backend.project_root(scene)
    # Record the attempt before making it, so a revision that answers
    # `ok: false` (no accepted revision yet, no terminals at all) is not
    # retried on every redraw for the rest of the session.
    tree.cadex_attempted_revision = _engine_revision(scene)
    state = cadex_backend.wiring_state(scene)
    if not isinstance(state, dict) or state.get("ok") is False:
        tree.cadex_error = str((state or {}).get("error") or
                               "The engine has no wiring to show yet.")
        return False
    if not force and tree.cadex_revision == str(state.get("revision") or ""):
        return True
    tree.cadex_error = ""
    return apply_state(tree, state, root=root)


# --- staying in step with the engine ---------------------------------------
#
# The graph is a projection, so something has to notice when the thing it
# projects has moved.  Shipping without this was the bug: `sync_from_engine`
# had exactly one caller, the header's refresh button, and the header did not
# draw that button until a tree existed -- so a fresh file opened to an empty
# canvas with no way to fill it.
#
# A draw handler may not mutate data, so the header *arms* and a one-shot
# timer syncs.  The arming is guarded twice: `_sync_armed` stops a redraw
# storm queueing a hundred timers, and the attempted-revision stamp stops a
# project with nothing to show from re-asking the engine forever.

_sync_armed = set()


def _engine_revision(scene):
    """The accepted revision, from the local cache. Never opens a project."""

    from . import cadex_backend

    state = cadex_backend.cached_script_state(scene)
    return str(getattr(state, "revision", "") or "")


def needs_sync(scene):
    tree = getattr(scene, "cadex_wiring", None)
    revision = _engine_revision(scene)
    if not revision:
        return False
    if tree is None:
        return True
    return (tree.cadex_revision != revision
            and tree.cadex_attempted_revision != revision)


def arm_sync(scene):
    """Ask for a sync on the next timer tick. Safe to call from a draw."""

    if not needs_sync(scene):
        return
    root = ""
    try:
        from . import cadex_backend

        root = cadex_backend.project_root(scene)
    except Exception:
        pass
    if root in _sync_armed:
        return
    _sync_armed.add(root)
    try:
        bpy.app.timers.register(_sync_timer, first_interval=0.0)
    except Exception:
        _sync_armed.discard(root)


def _sync_timer():
    _sync_armed.clear()
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return None
    try:
        sync_from_engine(scene)
    except Exception as exc:  # a timer has no operator report to land in
        try:
            from . import model

            model.record_error("Wiring sync failed: {}".format(exc))
        except Exception:
            pass
    return None


def _mark_dirty(tree):
    root = str(tree.cadex_root or "")
    if root in _dirty:
        return
    _dirty.add(root)
    try:
        bpy.app.timers.register(_push_timer, first_interval=_DEBOUNCE_SECONDS)
    except Exception:
        _dirty.discard(root)


def _push_timer():
    """The debounce. Runs outside any operator, so it reports through model."""

    if _suspend[0]:
        # A sync is rebuilding the canvas right now: `apply_state` clears the
        # links and re-draws them one at a time, so what is on screen is part
        # of the engine's answer, and pushing it would delete the rows it has
        # not drawn yet — a stored row list replaces the declared table
        # wholesale (ADR-065), so a half-drawn canvas is a wire deletion.
        # `NodeTree.update()` has always honoured this flag; the push did not
        # (ADR-113). Stay dirty and come back.
        return _DEBOUNCE_SECONDS
    _dirty.clear()
    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return None
    try:
        push(scene)
    except Exception as exc:  # a timer has no operator report to land in
        try:
            from . import model

            model.record_error("Wiring push failed: {}".format(exc))
        except Exception:
            pass
    return None


def push(scene):
    """One canvas state → one debounced ``set_params(nets=[...])``.

    Optimistic: the link is already on screen the instant the mouse comes up,
    because a net edit costs a full re-execute — seconds on a small harness,
    ~18 s on the drone (ADR-063) — and waiting would make dragging unusable.
    On failure the graph is put *back* from the engine, which is the only
    honest thing once it is defined as a projection.
    """

    from . import cadex_backend

    tree = ensure_tree(scene)
    if not tree.cadex_editable:
        tree.cadex_error = (
            "This script predates nets(...), so its wiring is read-only. "
            "Ask the assistant to declare it with nets(ports=..., wires=...).")
        return False, tree.cadex_error
    if tree.cadex_stale:
        # The canvas is missing links the engine sent, so the table it
        # describes is smaller than the one that exists. Pushing it would
        # delete the difference.
        return False, (tree.cadex_error
                       or "The canvas does not match the model yet.")
    rows = rows_from_tree(tree)
    if rows == stored_rows(tree):
        return True, "No change."
    payload = declared_rows(rows)
    if payload == declared_rows(stored_rows(tree)):
        # Only an undeclared row moved — a bundle link dragged or cut. There
        # is nothing to send, and the next sync puts it back where the script
        # says it goes.
        return True, "No change."
    tree.cadex_pending = True
    started = cadex_backend.begin_set_nets(scene, payload)
    if isinstance(started, tuple):
        tree.cadex_pending = False
        ok, report = started
        if not ok:
            _resync_after_failure(scene, tree, report)
        return ok, report
    return True, started


def _resync_after_failure(scene, tree, report):
    tree.cadex_error = str(report or "The engine refused the wiring change.")
    try:
        from . import model

        model.record_error(tree.cadex_error)
    except Exception:
        pass
    sync_from_engine(scene, force=True)


def on_push_finished(scene, ok, report):
    """Called by the backend when a wiring lifecycle settles."""

    tree = getattr(scene, "cadex_wiring", None)
    if tree is None:
        return
    tree.cadex_pending = False
    if ok:
        tree.cadex_error = ""
        _store_rows(tree, rows_from_tree(tree))
    else:
        _resync_after_failure(scene, tree, report)


# ---------------------------------------------------------------------------

classes = (
    CadexTerminalSocket,
    CadexBoardNode,
    CadexWiringTree,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cadex_wiring = bpy.props.PointerProperty(
        name="Wiring",
        description="This scene's harness graph",
        type=CadexWiringTree,
    )


def unregister():
    _dirty.clear()
    _sync_armed.clear()
    if hasattr(bpy.types.Scene, "cadex_wiring"):
        del bpy.types.Scene.cadex_wiring
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
