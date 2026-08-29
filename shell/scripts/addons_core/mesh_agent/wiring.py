# SPDX-FileCopyrightText: 2026 Cadex Authors
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

**It edits stored values, exactly as the sliders do.** A canvas full of
edits becomes one ``set_params(nets=[...], boards=[...])`` down the same path
a slider drag takes. It never writes the script text, and the AI is never in
the loop.

**And it is applied by pressing Apply** (ADR-122). It used to auto-push on a
150 ms leading-edge throttle, which meant a burst of twenty drags fired one
push after the first drag and left the other nineteen to pile up behind it —
and, because nothing polled the resulting ``Lifecycle``, every one of those
was then refused with ``STALE_PROGRAM_REVISION`` in silence. A net edit costs
a full re-execute, so "one gesture, one rebuild" was never the right unit
anyway: draw as many wires as you like, press Apply once, and **Revert** is
the way to throw the lot away.

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
    without this nothing marked the canvas dirty, the checkbox never reached
    ``set_params(nets=...)``, and it was picked up only incidentally, by the
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
    tree.cadex_dirty = True


def _row_edited(socket, _context):
    """A row field is an edit, exactly as the solder toggle is (ADR-120).

    ``NodeTree.update()`` fires on topology and never on a property written
    into an existing socket, so without this the number would change on
    screen and never reach the engine — the same hole the solder checkbox
    fell through before ADR-113. The mirror is the other half: a terminal is
    two sockets, and which one the sidebar draws is an accident of which end
    of a wire this board is.
    """

    if _suspend[0]:
        return
    tree = socket.id_data
    if getattr(tree, "bl_idname", "") != CadexWiringTree.bl_idname:
        return
    node = getattr(socket, "node", None)
    terminal = str(getattr(socket, "terminal", "") or "")
    if node is not None and terminal:
        _suspend[0] = True
        try:
            for other in list(node.inputs) + list(node.outputs):
                if other == socket or str(
                        getattr(other, "terminal", "") or "") != terminal:
                    continue
                other.origin = socket.origin
                other.axis = socket.axis
                other.hole_dia = socket.hole_dia
                other.depth = socket.depth
        finally:
            _suspend[0] = False
    if not getattr(node, "board_editable", False):
        return
    tree.cadex_dirty = True


class CadexTerminalSocket(bpy.types.NodeSocket):
    """One terminal, on one side of one board.

    Since ADR-120 it carries the terminal's **row** as well as its resolved
    position: ``origin``/``axis``/``hole_dia``/``depth``, in millimetres in
    the board's own frame, which is exactly what
    ``set_params(boards=[...])`` writes back. The resolved point stays in the
    engine's answer and out of here — it is world coordinates and derived
    from this row, so keeping a copy would be a second truth.
    """

    bl_idname = "CadexTerminalSocket"
    bl_label = "Terminal"

    terminal: bpy.props.StringProperty(
        name="Terminal",
        description="The engine's terminal name. This, not the socket name, "
                    "is the identity: Blender dedups duplicate socket names",
        default="",
    )
    kind: bpy.props.StringProperty(name="Kind", default="")
    #: True when the engine sent a row for this terminal, i.e. its board is a
    #: declared table rather than a selector. A socket without one draws and
    #: is never part of a pushed table.
    has_row: bpy.props.BoolProperty(default=False)
    origin: bpy.props.FloatVectorProperty(
        name="Origin",
        description="Where the wire lands, in the board's own frame (mm)",
        size=3, default=(0.0, 0.0, 0.0), subtype='XYZ', update=_row_edited,
    )
    axis: bpy.props.FloatVectorProperty(
        name="Axis",
        description="The direction the terminal is drilled into the body; "
                    "the wire leaves back along it",
        size=3, default=(0.0, 0.0, -1.0), subtype='XYZ', update=_row_edited,
    )
    #: Zero means absent, which is what says a row is a pad (ADR-117).
    hole_dia: bpy.props.FloatProperty(
        name="Bore",
        description="Hole diameter in mm; zero for a pad",
        default=0.0, min=0.0, update=_row_edited,
    )
    depth: bpy.props.FloatProperty(
        name="Depth",
        description="Descriptive bore depth in mm; nothing geometric reads it",
        default=0.0, min=0.0, update=_row_edited,
    )
    soldered: bpy.props.BoolProperty(
        name="Soldered",
        description="Whether the connection landing here carries a joint",
        default=False,
        update=_solder_toggled,
    )

    def draw(self, _context, layout, node, text):
        """One terminal: which column it is in, and whether it is soldered.

        The arrow is the whole of the disambiguation (ADR-122). A terminal
        draws twice on every board — ``tree.links.new`` raises "Same
        input/output direction of sockets" for output→output *and* for
        input→input, so an undirected edge needs one of each and one row per
        terminal is simply not reachable inside the stock node editor. Two
        identical rows called ``sda`` read as two terminals; ``sda ▸`` and
        ``▸ sda`` read as the two ends of one, which is what they are.

        The checkbox is on the row because a terminal *is* a value with a
        checkbox: ``part.solder`` takes a terminal and never a wire (ADR-063),
        and the sidebar's Solder box could only ever show the sockets of a
        selected node's *linked* terminals.
        """

        name = text or self.terminal
        row = layout.row(align=True)
        if self.is_output:
            row.label(text="{:s} ▸".format(name))
        else:
            row.label(text="▸ {:s}".format(name))
        if getattr(node.id_data, "cadex_editable", False):
            row.prop(self, "soldered", text="", icon='SNAP_MIDPOINT')

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
    #: The name ``boards(...)`` gave this component, or "" (ADR-120). The same
    #: string as ``port`` whenever both tables name it, which is by
    #: construction: a declared board reaches the registry as its own port.
    board: bpy.props.StringProperty(name="Board", default="")
    #: True when this board's terminals are a declared table the editor may
    #: write. A selector board draws identically and is read-only, because its
    #: rows come back from the shape on every run.
    board_editable: bpy.props.BoolProperty(default=False)
    #: Which terminal the sidebar acts on. Blender has no "active socket" for
    #: a custom node, so the node holds the name.
    cadex_terminal: bpy.props.StringProperty(name="Terminal", default="")

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
    #: The canvas has edits the engine has not been told about (ADR-122).
    #: What Apply is enabled *for*, and what the header highlights. It saves
    #: into the .blend, which is right: a file closed with wires drawn and
    #: never applied still has them drawn when it opens.
    cadex_dirty: bpy.props.BoolProperty(default=False)
    #: Set when the last sync could not draw every row the engine sent, so
    #: the canvas is not a faithful projection and must not be pushed back:
    #: a push replaces the declared table wholesale (ADR-065), and a table
    #: built from a canvas missing links is a wire deletion (ADR-115).
    cadex_stale: bpy.props.BoolProperty(default=False)
    cadex_error: bpy.props.StringProperty(default="")
    #: The row table, as JSON. Links hold no properties, so gauge, solder,
    #: enabled and the row *name* have to live beside the topology.
    cadex_rows: bpy.props.StringProperty(default="[]")
    #: The terminal table, as JSON, for the same reason (ADR-120): a socket
    #: holds its own row, but "what the engine last told us" has to be
    #: somewhere the no-op guard can read it.
    cadex_board_rows: bpy.props.StringProperty(default="[]")
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
        """Blender's change hook: fires on every link, node and socket edit.

        It **marks**, and sends nothing (ADR-122). A drag is one edit of
        twenty; the rebuild is what Apply asks for.
        """

        if _suspend[0] or not self.cadex_editable:
            return
        self.cadex_dirty = True


# ---------------------------------------------------------------------------
# the row table


#: The columns ``set_params(nets=...)`` carries, and the only ones the canvas
#: can describe. Everything else on a stored row — ``path`` and ``waypoints``
#: (ADR-118), ``kind``, ``editable`` — is the engine's, and comparing on it is
#: what made both no-op guards below permanently false.
_OVERRIDE_KEYS = ("name", "a", "b", "gauge_mm", "solder", "enabled")


def stored_rows(tree):
    try:
        rows = json.loads(tree.cadex_rows or "[]")
    except ValueError:
        return []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _comparable(rows):
    """The override columns alone, in order — what "unchanged" means here.

    ``rows_from_tree`` rebuilds six columns; an engine row carries those plus
    the route its run swept. Comparing the two dicts whole therefore *never*
    matched, so cutting a link and redrawing it in the same place cost a full
    re-execute — seconds on a small harness, ~18 s on the drone — and the
    "No change." branch could not be reached at all (ADR-120).
    """

    return [{key: row.get(key) for key in _OVERRIDE_KEYS} for row in rows]


def _store_rows(tree, rows, preserve=False):
    """Remember the table. ``preserve`` keeps what the canvas cannot describe.

    ``on_push_finished`` stores what the *canvas* says, and the canvas has no
    route: storing it flat dropped ``path`` off every row, which is what made
    Edit Wire Path answer "no published route to edit" for a wire whose route
    the engine had published and a sync would have restored. Matched on the
    unordered endpoint pair, the same key every other reconcile here uses.
    """

    if preserve:
        keep = {_pair(row): row for row in stored_rows(tree)}
        merged = []
        for row in rows:
            previous = keep.get(_pair(row)) or {}
            extra = {key: value for key, value in previous.items()
                     if key not in _OVERRIDE_KEYS and key not in row}
            merged.append({**extra, **dict(row)})
        rows = merged
    tree.cadex_rows = json.dumps(list(rows))


def stored_board_rows(tree):
    try:
        rows = json.loads(tree.cadex_board_rows or "[]")
    except ValueError:
        return []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _store_board_rows(tree, rows):
    tree.cadex_board_rows = json.dumps(list(rows))


def board_rows_from_tree(tree):
    """The terminal table the canvas currently describes (ADR-120).

    One row per terminal, from the socket that holds it — not two, though a
    terminal is two sockets: they are mirrored on every edit, so either is
    the answer and taking both would be a duplicate the engine refuses.
    Only boards the engine marked editable contribute; a selector board's
    rows are the geometry's and sending them back would be a stale copy.
    """

    rows = []
    for node in tree.nodes:
        board = str(getattr(node, "board", "") or "")
        if not board or not getattr(node, "board_editable", False):
            continue
        seen = set()
        for socket in list(node.inputs) + list(node.outputs):
            name = str(getattr(socket, "terminal", "") or "")
            if not name or name in seen or not getattr(socket, "has_row", False):
                continue
            seen.add(name)
            bore = float(getattr(socket, "hole_dia", 0.0) or 0.0)
            depth = float(getattr(socket, "depth", 0.0) or 0.0)
            rows.append({
                "board": board,
                "name": name,
                "origin": [round(float(value), 6) for value in socket.origin],
                "axis": [round(float(value), 6) for value in socket.axis],
                # Zero is how a Blender float property spells "absent", and
                # absent ``hole_dia`` is what says a row is a pad (ADR-117).
                "hole_dia": round(bore, 6) if bore > 0.0 else None,
                "depth": round(depth, 6) if depth > 0.0 else None,
            })
    return rows


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


def clean_terminal_name(text):
    """A terminal name the engine will accept: lower_snake_case, no dot.

    The same rule ``_clean_name`` applies to a row name, and deliberately so:
    a terminal name is the right half of every ``<board>.<terminal>``
    address, so the two halves are one grammar.
    """

    return _clean_name(text)


def rename_terminal(tree, node, old, new):
    """Rename one terminal on the canvas, and the wires addressing it.

    Both edits in one push (ADR-120): the terminal's row moves in the board
    table and every stored connection row naming it is rewritten, so the
    engine sees one ``set_params`` and the model rebuilds once. Rewriting the
    stored rows *here* is what makes the endpoint-pair match in
    :func:`rows_from_tree` still find them when Apply is pressed — without it
    the wire would come back renamed, at the default gauge, with its solder
    cleared.
    """

    board = str(getattr(node, "board", "") or "")
    if not board or not getattr(node, "board_editable", False):
        return False, "This board's terminals are stated by the script."
    if not new or new == old:
        return True, "No change."
    existing = {str(getattr(socket, "terminal", "") or "")
                for socket in list(node.inputs) + list(node.outputs)}
    if new in existing:
        return False, "This board already has a terminal called {!r}.".format(new)
    _suspend[0] = True
    try:
        for socket in list(node.inputs) + list(node.outputs):
            if str(getattr(socket, "terminal", "") or "") == old:
                socket.terminal = new
                socket.name = new
        node.cadex_terminal = new
        before = "{}.{}".format(str(getattr(node, "port", "") or ""), old)
        after = "{}.{}".format(str(getattr(node, "port", "") or ""), new)
        rows = []
        for row in stored_rows(tree):
            moved = dict(row)
            for side in ("a", "b"):
                if str(moved.get(side) or "") == before:
                    moved[side] = after
            rows.append(moved)
        _store_rows(tree, rows)
    finally:
        _suspend[0] = False
    tree.cadex_dirty = True
    return True, "Renamed."


def delete_terminal(tree, node, name):
    """Drop one terminal from the canvas; the push drops it from the table.

    Blender removes the links on a removed socket, so the connection table
    the canvas describes loses the wires that landed there in the same
    breath — which is the honest outcome and the one the engine would reach
    anyway when the row stopped existing.
    """

    board = str(getattr(node, "board", "") or "")
    if not board or not getattr(node, "board_editable", False):
        return False, "This board's terminals are stated by the script."
    removed = False
    _suspend[0] = True
    try:
        for collection in (node.inputs, node.outputs):
            for socket in list(collection):
                if str(getattr(socket, "terminal", "") or "") == name:
                    collection.remove(socket)
                    removed = True
        if node.cadex_terminal == name:
            node.cadex_terminal = ""
    finally:
        _suspend[0] = False
    if not removed:
        return False, "No terminal called {!r} on this board.".format(name)
    tree.cadex_dirty = True
    return True, "Removed."


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
    by_name = {str(item.get("name") or ""): item for item in terminals}
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
            # Soldered is the state of a terminal nothing has landed on yet
            # (ADR-122), so a wire drawn onto it is soldered without anyone
            # ticking anything — which is what a wire onto a pad or a bore
            # nearly always is. ``apply_state`` overwrites this from the
            # engine's own rows, in both directions, so an existing
            # unsoldered row survives the round trip.
            socket.soldered = True
            _apply_row(socket, by_name.get(name) or {})
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


def _apply_row(socket, terminal):
    """Carry one terminal's row onto its socket, if the engine sent one."""

    origin = list(terminal.get("origin") or [])
    axis = list(terminal.get("axis") or [])
    socket.has_row = len(origin) == 3 and len(axis) == 3
    if not socket.has_row:
        return
    socket.origin = [float(value) for value in origin]
    socket.axis = [float(value) for value in axis]
    bore = terminal.get("hole_dia")
    depth = terminal.get("depth")
    socket.hole_dia = float(bore or 0.0)
    socket.depth = float(depth or 0.0)


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
        skipped = []
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
                #
                # Recorded rather than dropped in silence: the node simply
                # was not there, and "one board is missing from the canvas"
                # with no message is indistinguishable from a broken editor.
                skipped.append(port or "(unnamed)")
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
            node.board = str(component.get("board") or "")
            node.board_editable = bool(component.get("editable"))
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
        # Solder is decided per *address* and applied after every row is
        # drawn, in both directions (ADR-122). Two things force that shape.
        # It only ever set True before, which was invisible while a fresh
        # socket defaulted to False and is a bug now one defaults to True: an
        # unsoldered stored row would come back soldered on the next sync. And
        # a terminal several wires land on has one flag between them, so the
        # rule has to be the same *any* rule ``_solder_for`` reads back out —
        # written row by row, the last row to touch a shared terminal would
        # win instead.
        landed = {}
        for row in rows:
            if not row.get("enabled", True):
                continue
            start = _socket_at_side(tree, str(row.get("a") or ""), outputs=True)
            end = _socket_at_side(tree, str(row.get("b") or ""), outputs=False)
            if start is None or end is None:
                undrawn.append(str(row.get("name") or "?"))
                continue
            tree.links.new(start, end)
            for address in (row.get("a"), row.get("b")):
                key = str(address or "")
                landed[key] = landed.get(key, False) or bool(row.get("solder"))
        for address, soldered in landed.items():
            for socket in _sockets_at(tree, address):
                socket.soldered = soldered
        _store_rows(tree, rows)
        _store_board_rows(tree, board_rows_from_tree(tree))
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
        elif skipped:
            tree.cadex_error = (
                "{:d} component(s) share a name with one already on the "
                "canvas ({}) and were not drawn; two terminal sets cannot be "
                "one node.".format(len(skipped), ", ".join(skipped[:4])))
        # The sync *is* the settling: whatever a push was waiting for, what
        # is on screen now came from the engine. Without this a push that
        # never reported back left "applying…" in the header for the life of
        # the file, because the flag saves into the .blend (ADR-115).
        tree.cadex_pending = False
        # ...and it is also the end of "unapplied": what is drawn is what the
        # engine says. Both flags save into the .blend, so both have to be
        # cleared by the thing that makes them untrue.
        tree.cadex_dirty = False
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


def push(scene):
    """The whole canvas → one ``set_params``. Called by Apply, and only by it.

    Both declared tables ride it (ADR-120): the connection rows the links
    describe and the terminal rows the sockets hold, whichever of them
    changed, in **one** re-execute rather than two. They share the op for the
    same reason they share a canvas.

    Every guard it grew is still here — read-only script, stale canvas, and
    the two no-op comparisons — because they were never about *when* the push
    happened. What went away with ADR-122 is the debounce that decided that,
    and the resync-on-failure that came with it: losing twenty drags to one
    refusal is worse than an inconsistent canvas, and Revert is the
    deliberate way to discard them.
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
    boards = board_rows_from_tree(tree)
    boards_changed = boards != stored_board_rows(tree)
    if not boards_changed and _comparable(rows) == _comparable(stored_rows(tree)):
        return True, "No change."
    payload = declared_rows(rows)
    nets_changed = (_comparable(payload)
                    != _comparable(declared_rows(stored_rows(tree))))
    if not boards_changed and not nets_changed:
        # Only an undeclared row moved — a bundle link dragged or cut. There
        # is nothing to send, and the next sync puts it back where the script
        # says it goes.
        return True, "No change."
    tree.cadex_pending = True
    tree.cadex_error = ""
    ok, report = cadex_backend.begin_set_tables(
        scene,
        nets=payload if nets_changed else None,
        boards=boards if boards_changed else None,
    )
    if not ok:
        # It never reached the engine at all — no project, no script. The
        # pump only reports what the engine answered.
        tree.cadex_pending = False
        tree.cadex_error = str(report or "The wiring change was not sent.")
    return ok, report


def on_push_finished(scene, ok, report):
    """Called by the wiring pump when one table push settles (ADR-122).

    The single completion path. On success the canvas becomes a true
    projection again — the stored tables are rewritten from it and one forced
    sync puts the engine's own answer, route and all, back on screen.

    **On failure the canvas is kept.** It used to resync, which threw away
    every edit the user had made in order to restore a definition; with one
    edit per push that was a fair trade and with twenty it is not. The error
    is on the header, the rows are still drawn, and Revert is the button that
    means "discard them".
    """

    tree = getattr(scene, "cadex_wiring", None)
    if tree is None:
        return
    tree.cadex_pending = False
    if not ok:
        tree.cadex_error = str(report
                               or "The engine refused the wiring change.")
        return
    tree.cadex_error = ""
    # ``preserve``: the canvas describes six columns and the engine's row
    # carries the route its run swept as well. Storing the canvas flat
    # dropped ``path`` off every row, which is what made Edit Wire Path
    # report "no published route to edit" on a wire that had one.
    _store_rows(tree, rows_from_tree(tree), preserve=True)
    _store_board_rows(tree, board_rows_from_tree(tree))
    tree.cadex_dirty = False
    # The push moved the revision, so the projection is one revision behind
    # the thing it projects. Forced, because `sync_from_engine` short-circuits
    # on a matching revision and this is exactly the case where the cached one
    # has not caught up yet.
    try:
        sync_from_engine(scene, force=True)
    except Exception as exc:
        tree.cadex_error = "Wiring sync failed: {}".format(exc)


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
    _sync_armed.clear()
    if hasattr(bpy.types.Scene, "cadex_wiring"):
        del bpy.types.Scene.cadex_wiring
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
