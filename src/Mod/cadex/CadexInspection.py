# SPDX-License-Identifier: LGPL-2.1-or-later

"""Deterministic, bounded inspection for the active modeling surface."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from CadexModelingSurface import resolve_service_surface


MAX_INSPECT_RESULT_BYTES = 32 * 1024
_PREVIEW_BYTES = 1024
_PROPERTY_SEQUENCE_LIMIT = 256
_HEAVY_PROPERTIES = frozenset({"Mesh", "Points", "Proxy", "Shape", "ViewObject"})


def _surface_summary(resolution: Any) -> dict[str, Any]:
    result = {
        "workbench": str(resolution.workbench or ""),
        "engine": str(resolution.engine or ""),
        "domain": resolution.domain,
        "surface_id": str(resolution.surface_id or ""),
        "available": bool(resolution.available),
    }
    if not resolution.available:
        result["unavailable_reason"] = str(resolution.unavailable_reason or "")
    return result


def _identity(obj: Any) -> dict[str, Any]:
    return {
        "name": str(getattr(obj, "Name", "") or ""),
        "label": str(getattr(obj, "Label", "") or ""),
        "type": str(getattr(obj, "TypeId", "") or type(obj).__name__),
    }


def _document_identity(doc: Any) -> dict[str, Any]:
    if doc is None:
        return {"name": None, "uid": None, "object_count": 0}
    return {
        "name": str(getattr(doc, "Name", "") or ""),
        "uid": str(getattr(doc, "Uid", "") or ""),
        "object_count": len(getattr(doc, "Objects", []) or []),
    }


def _stable_value(value: Any, *, depth: int = 0) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if depth >= 5:
        return {"omitted": True, "reason": "value_depth", "type": type(value).__name__}
    if hasattr(value, "Name") and hasattr(value, "TypeId"):
        return _identity(value)
    if isinstance(value, Mapping):
        items = list(value.items())
        result = {
            str(key): _stable_value(item, depth=depth + 1)
            for key, item in items[:_PROPERTY_SEQUENCE_LIMIT]
        }
        if len(items) > _PROPERTY_SEQUENCE_LIMIT:
            result["_items_omitted"] = len(items) - _PROPERTY_SEQUENCE_LIMIT
        return result
    if isinstance(value, (list, tuple)):
        values = list(value)
        result = [
            _stable_value(item, depth=depth + 1)
            for item in values[:_PROPERTY_SEQUENCE_LIMIT]
        ]
        if len(values) > _PROPERTY_SEQUENCE_LIMIT:
            result.append({"items_omitted": len(values) - _PROPERTY_SEQUENCE_LIMIT})
        return result
    if all(hasattr(value, axis) for axis in ("x", "y", "z")):
        try:
            return {
                "x": float(value.x),
                "y": float(value.y),
                "z": float(value.z),
            }
        except Exception:
            pass
    quantity_value = getattr(value, "Value", None)
    quantity_unit = getattr(value, "Unit", None)
    if isinstance(quantity_value, (int, float)) and quantity_unit is not None:
        return {"value": float(quantity_value), "unit": str(quantity_unit)}
    text = str(value)
    if len(text) <= 2048:
        return text
    return {
        "omitted": True,
        "reason": "value_text_size",
        "characters": len(text),
        "utf8_bytes": len(text.encode("utf-8", errors="replace")),
        "type": type(value).__name__,
    }


def _object_detail(obj: Any) -> dict[str, Any]:
    result = _identity(obj)
    properties = list(getattr(obj, "PropertiesList", []) or [])
    captured: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for raw_name in properties:
        name = str(raw_name)
        if name in _HEAVY_PROPERTIES:
            captured[name] = {
                "omitted": True,
                "reason": "heavy_native_property",
                "property_type": str(
                    getattr(obj, "getTypeIdOfProperty", lambda _name: "")(name) or ""
                ),
            }
            continue
        try:
            value = getattr(obj, name)
            captured[name] = {
                "property_type": str(
                    getattr(obj, "getTypeIdOfProperty", lambda _name: "")(name) or ""
                ),
                "group": str(
                    getattr(obj, "getGroupOfProperty", lambda _name: "")(name) or ""
                ),
                "value": _stable_value(value),
            }
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
    result["property_count"] = len(properties)
    result["properties"] = captured
    if errors:
        result["property_errors"] = errors
    return result


def _edit_object() -> None:
    """Always None: interactive edit state was a Qt shell concept.

    The engine's document is cadexd's ephemeral one — nothing is ever "in
    edit" in it, because no user interacts with it. Kept as a field of the
    document inspection so the payload shape does not change for clients
    (ADR-021).
    """

    return None


def capture_inspection(service: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Capture only document-affine state; artifact reads happen in complete()."""

    scope = str(arguments.get("scope") or "")
    target = str(arguments.get("target") or "")
    path = str(arguments.get("path") or "")
    offset = int(arguments.get("offset") or 0)
    limit = int(arguments.get("limit") or 20)
    attach = bool(arguments.get("attach", False))
    if offset < 0 or offset > 100000000:
        raise ValueError("offset must be between 0 and 100000000.")
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50.")
    if len(target) > 512 or len(path) > 512:
        raise ValueError("target and path are each limited to 512 characters.")
    if attach and scope != "image":
        raise ValueError("attach=true is valid only for image scope.")
    if scope == "object" and not target:
        raise ValueError(f"{scope} scope requires an exact target.")
    if scope == "image" and attach and not target:
        raise ValueError("image scope requires an exact target when attach=true.")
    workbench = service.active_workbench_name()
    resolution = resolve_service_surface(service, workbench)
    doc = service._active_document()
    common = {
        "scope": scope,
        "target": target,
        "path": path,
        "offset": offset,
        "limit": limit,
        "attach": attach,
        "surface": _surface_summary(resolution),
        "document": _document_identity(doc),
    }
    if scope == "document":
        objects = (getattr(doc, "Objects", []) or []) if doc is not None else []
        if path == "/objects":
            total = len(objects)
            end = min(offset + limit, total)
            values = [_identity(objects[index]) for index in range(offset, end)]
            return {
                **common,
                "kind": "document_objects_page",
                "values": values,
                "total": total,
            }
        if path.startswith("/objects/"):
            raise ValueError(
                "Inspect /objects as a page, then use object scope with the exact "
                "returned internal name."
            )
        raw = {
            **common["document"],
            "edit_object": _edit_object(),
            "objects": {
                "type": "array",
                "item_count": len(objects),
                "inspect_path": "/objects",
            },
        }
        return {**common, "kind": "captured", "raw": raw}
    if scope == "object":
        if doc is None:
            raise ValueError("No active document.")
        obj = doc.getObject(target) if target else None
        if obj is None:
            raise ValueError(f"Object not found by exact internal name: {target!r}.")
        return {**common, "kind": "captured", "raw": _object_detail(obj)}
    if scope == "script":
        # THE project script: source text, parameter specs/values, revisions,
        # accepted contract/digest, latest candidate. Artifact reads happen in
        # complete_inspection, off the document thread.
        return {
            **common,
            "kind": "script",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    if scope == "api":
        schemas = [
            service.registry.get(name).to_schema(active_workbench=workbench)
            for name in resolution.tool_names
            if name in service.registry.names()
        ]
        return {**common, "kind": "api", "schemas": schemas}
    if scope == "image":
        return {
            **common,
            "kind": "image",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    if scope == "assets":
        # What ``mesh.import_file`` can name. Store-backed like image scope,
        # so the walk happens in complete_inspection, off the document thread.
        return {
            **common,
            "kind": "assets",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    if scope == "output":
        # The accepted revision's per-output facts, read from the pinned
        # attempt directory rather than from the run that produced them.
        return {
            **common,
            "kind": "output",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    if scope == "wiring":
        # The harness as a graph (ADR-065): the terminals the accepted run
        # resolved, joined to the connection table the script declares. Both
        # halves are store-backed, so the read happens off the document
        # thread like every other artifact-backed scope.
        return {
            **common,
            "kind": "wiring",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    if scope == "history":
        # The undo trail (ADR-045): every accepted revision's source, newest
        # last. Store-backed, so the read happens off the document thread.
        # With no target it lists; with one it serves that version's source.
        return {
            **common,
            "kind": "history",
            "project_root": str(service.project_scope_snapshot().get("root") or ""),
        }
    raise ValueError(f"Unknown core.inspect scope: {scope!r}.")


def _complete_api(captured: Mapping[str, Any]) -> Any:
    surface = captured["surface"]
    if str(surface.get("engine") or "") != "xscript":
        return {"surface": surface, "tools": list(captured.get("schemas") or [])}
    from CadexScriptedRuntime import describe_project_api

    return describe_project_api()


def _complete_script(captured: Mapping[str, Any]) -> Any:
    """Read THE project script's persisted state; paged by _bounded_page."""

    root = str(captured.get("project_root") or "")
    if not root:
        return {
            "ok": False,
            "error": "The active document has no durable Cadex project root.",
        }
    from CadexScriptStore import CadexProjectScriptStore

    store = CadexProjectScriptStore(root)
    state = store.read_state()
    source = store.read_source()
    return {
        "script_present": bool(source),
        "source": source,
        "source_characters": len(source),
        "params": {
            "specs": list(state.get("param_specs") or []),
            "values": dict(state.get("param_values") or {}),
        },
        "revisions": {
            "working_revision": str(state.get("working_revision") or ""),
            "accepted_revision": str(state.get("accepted_revision") or ""),
        },
        "accepted": {
            "contract": state.get("accepted_contract"),
            "digest": str(state.get("accepted_digest") or ""),
        },
        # The mount table, beside the parameters and for the same reason
        # (ADR-126): it is script state something outside the script sets, so
        # the party doing the setting has to be able to read it first.
        # ``rows`` is the table as a run would build it — declared, replaced
        # wholesale by the stored overrides where there are any — which is
        # exactly what ``set_params(mounts=[...])`` takes back.
        "mounts": _script_mounts(state),
        # ...and the section cage (ADR-127): the overlay draws these rings
        # and Apply writes them back, so the shell has to be able to read
        # the table it is about to replace.
        "cages": _script_cages(state),
        "latest_candidate": state.get("latest_candidate"),
        "updated_at": str(state.get("updated_at") or ""),
    }


def _script_mounts(state: Mapping[str, Any]) -> dict[str, Any]:
    from CadexMounts import declared_groups, effective_mounts

    specs = dict(state.get("mount_specs") or {})
    return {
        "components": sorted(declared_groups(specs)),
        "rows": effective_mounts(specs, state.get("mount_values")),
    }


def _script_cages(state: Mapping[str, Any]) -> dict[str, Any]:
    from CadexCage import declared_cages, effective_rings

    specs = dict(state.get("cage_specs") or {})
    declared = declared_cages(specs)
    return {
        "cages": [
            {
                "name": name,
                "axis": list(entry.get("axis") or [1.0, 0.0, 0.0]),
                "origin": list(entry.get("origin") or [0.0, 0.0, 0.0]),
                "up": list(entry.get("up") or [0.0, 0.0, 1.0]),
            }
            for name, entry in declared.items()
        ],
        "rows": effective_rings(specs, state.get("cage_values")),
    }


def _complete_image(captured: Mapping[str, Any]) -> tuple[Any, dict[str, Any] | None]:
    root = Path(str(captured.get("project_root") or ""))
    state_path = root / "references.json"
    entries: list[dict[str, Any]] = []
    if state_path.is_file():
        data = json.loads(state_path.read_text(encoding="utf-8"))
        raw = data.get("reference_images") if isinstance(data, dict) else None
        if isinstance(raw, list):
            entries = [dict(item) for item in raw if isinstance(item, dict)]
    target = str(captured.get("target") or "")
    if not target:
        return {
            "image_count": len(entries),
            "images": [
                {key: item.get(key) for key in ("id", "name", "label", "format", "image_size")}
                for item in entries
            ],
        }, None
    selected = next(
        (
            item
            for item in entries
            if str(item.get("id") or "") == target
            or str(item.get("name") or "") == target
        ),
        None,
    )
    if selected is None:
        return {"ok": False, "error": f"No reference image matches {target!r}."}, None
    public = {
        key: selected.get(key)
        for key in ("id", "name", "label", "format", "size_bytes", "image_size", "attached_at")
        if selected.get(key) not in (None, "", [], {})
    }
    if not captured.get("attach"):
        return {"ok": True, "image": public, "attached": False}, None
    path = Path(str(selected.get("path") or ""))
    allowed_root = (root / "references").resolve()
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(allowed_root)
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"Reference image artifact is unavailable: {exc}"}, None
    if not resolved.is_file():
        return {"ok": False, "error": "Reference image artifact is not a file."}, None
    return (
        {"ok": True, "image": public, "attached": True},
        {"path": str(resolved), "name": str(selected.get("name") or target)},
    )


def _complete_assets(captured: Mapping[str, Any]) -> Any:
    """The project's importable mesh assets — how the agent discovers them."""

    root = str(captured.get("project_root") or "")
    if not root:
        return {
            "ok": False,
            "error": "The active document has no durable Cadex project root.",
        }
    from CadexScriptedRuntime import list_project_assets

    entries = list_project_assets(root)
    return {
        "asset_count": len(entries),
        "assets": entries,
        "note": (
            "Names here are what mesh.import_file() takes. Add one with the "
            "shell's File > Import Geometry, or the import_geometry tool."
        ),
    }


def _complete_history(captured: Mapping[str, Any]) -> Any:
    """The project's accepted-revision history — the undo trail (ADR-045).

    No target lists it, newest last. A target selects one version by ordinal
    or revision prefix and serves that version's source, which is what a
    revert reads before writing it back.
    """

    root = str(captured.get("project_root") or "")
    if not root:
        return {
            "ok": False,
            "error": "The active document has no durable Cadex project root.",
        }
    from CadexScriptStore import CadexProjectScriptStore

    store = CadexProjectScriptStore(root)
    target = str(captured.get("target") or "").strip()
    if target:
        source = store.read_history_source(target)
        if not source:
            return {
                "ok": False,
                "error": (
                    "No stored version matches {!r}. Inspect scope=history "
                    "with no target for the list.".format(target)
                ),
            }
        return {"selector": target, "source": source, "characters": len(source)}

    entries = store.read_history()
    return {
        "version_count": len(entries),
        "versions": entries,
        "note": (
            "Every accepted revision, oldest first. Inspect one with "
            "target=<ordinal|revision>; write it back with write_script to "
            "revert (replace=true if it drops outputs you have now)."
        ),
    }


#: The harness operations whose arguments name terminals. A script written
#: before ``nets(...)`` says what it connects only by calling these, which is
#: what the derived (read-only) view reconstructs from.
_HARNESS_OPERATIONS = ("cable", "bundle", "solder")


def _terminal_identity(port: Any) -> str:
    """The registry identity of one endpoint payload: its set, minus the name.

    The same construction ``cadex_part_worker.terminal_set_key`` memoises by,
    without its hash — matching canonical JSON is enough here and keeps the
    host free of a worker import.
    """

    if not isinstance(port, Mapping) or "terminal" not in port:
        return ""
    return json.dumps(
        {key: value for key, value in port.items() if key != "terminal"},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _label_atom(value: Any) -> str:
    """One candidate label, made safe to be the left half of an address."""

    # Addresses are split on the first ``.``, so a label may not carry one.
    return str(value or "").strip().replace(".", "_")


def _component_labels(registry: list[Any]) -> list[str]:
    """One label per registry entry, distinct across the whole graph.

    The label *is* the node's identity on the canvas and the left half of
    every ``<port>.<terminal>`` address, so two entries may not share one.
    Two terminal sets on the same component do share an output name — a board
    with a front header and a back header is one import and two
    ``terminals(...)`` calls — and while both answered to it the canvas gave
    the second set's sockets to the first set's node, leaving every declared
    wire with an endpoint that no longer existed (ADR-115).

    A declared port keeps its own name whatever order it arrives in, which is
    why the reservation pass runs first: the addresses in ``net_specs`` are
    written against those names and nothing here may move them.
    """

    entries = [entry if isinstance(entry, Mapping) else {} for entry in registry]
    # Board names are reserved in the same first pass, and for the same
    # reason: ``board_values`` rows are written against them, so nothing here
    # may move one (ADR-120). The two namespaces are one by construction — a
    # declared board reaches the registry as its own ``port`` too.
    used = {str(entry.get("port") or "") for entry in entries}
    used |= {str(entry.get("board") or "") for entry in entries}
    used.discard("")
    labels: list[str] = []
    for index, entry in enumerate(entries):
        # A declared name, whichever table declared it: the rows of both are
        # written against these names and nothing here may move one.
        port = str(entry.get("port") or "") or str(entry.get("board") or "")
        if port:
            labels.append(port)
            continue
        # A legacy harness declares no ports, so the output name is the best
        # human-readable handle the component has; then its own label, which
        # is what an inline component — a transformed pad, never published
        # under a result key — has instead; then the index.
        component = entry.get("component")
        properties = component.get("properties") if isinstance(component, Mapping) else None
        base = (
            _label_atom(entry.get("output"))
            or _label_atom((properties or {}).get("label") if isinstance(properties, Mapping) else "")
            or f"component_{index}"
        )
        label = base
        suffix = 2
        while label in used:
            label = f"{base}#{suffix}"
            suffix += 1
        used.add(label)
        labels.append(label)
    return labels


def _wiring_components(
    registry: list[Any],
    board_rows: Mapping[Any, Any] | None = None,
    editable_boards: Any = (),
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """The nodes of the graph, plus ``identity -> port label`` for the wires.

    ``board_rows`` is the effective terminal table keyed ``(board, name)``
    (ADR-120). Where it has a row, the socket carries the row's own fields —
    which is what makes the canvas able to *write* one back rather than only
    draw it. The resolved point and direction stay beside them: they are
    world coordinates and the row is the board's own frame, and the canvas
    needs both.

    ``editable_boards`` is the set of declared boards whose rows are a table
    rather than a selector's derived output. It is a property of the *board*,
    not of its rows, so a board whose terminals were all deleted from the
    canvas is still editable and can have one added back.
    """

    rows = dict(board_rows or {})
    editable = {str(name) for name in editable_boards or ()}
    components: list[dict[str, Any]] = []
    label_by_identity: dict[str, str] = {}
    labels = _component_labels(registry)
    for index, entry in enumerate(registry):
        if not isinstance(entry, Mapping):
            continue
        label = labels[index]
        board = str(entry.get("board") or "")
        terminals = []
        for terminal in list(entry.get("terminals") or []):
            if not isinstance(terminal, Mapping):
                continue
            metrics = dict(terminal.get("metrics") or {})
            name = str(terminal.get("name") or "")
            socket = {
                "name": name,
                "point": list(terminal.get("point") or []),
                "direction": list(terminal.get("direction") or []),
                "kind": str(metrics.get("kind") or ""),
                "radius": metrics.get("radius"),
                "depth": metrics.get("depth"),
            }
            row = rows.get((board, name)) if board else None
            if isinstance(row, Mapping):
                socket["origin"] = [float(value) for value in row.get("origin") or []]
                socket["axis"] = [float(value) for value in row.get("axis") or []]
                socket["hole_dia"] = row.get("hole_dia")
                socket["depth"] = row.get("depth")
            terminals.append(socket)
        components.append(
            {
                "port": label,
                # The declared board this node is, and whether its rows are a
                # table the editor may write. A selector board is a node like
                # any other and its terminals are read-only, because they are
                # derived from the shape on every run.
                "board": board,
                "editable": board in editable,
                "output": str(entry.get("output") or ""),
                "domain": str(entry.get("domain") or ""),
                "terminals": terminals,
            }
        )
        identity = _terminal_identity(
            {
                "terminal": "",
                "component": entry.get("component"),
                "layout": entry.get("layout"),
            }
        )
        if identity:
            label_by_identity.setdefault(identity, label)
    return components, label_by_identity


def _address(port: Any, labels: Mapping[str, str]) -> str:
    identity = _terminal_identity(port)
    label = labels.get(identity, "")
    if not label:
        return ""
    return f"{label}.{str(port.get('terminal') or '')}"


def _derived_wires(
    registry: list[Any], outputs: list[Any]
) -> list[dict[str, Any]]:
    """The harness of a script written before ``nets(...)``, read-only.

    Reconstructed by scanning the accepted revision's ``cable``/``bundle``
    payloads for terminal endpoints and its ``solder`` payloads for which of
    those ends carry a joint. It is a complete picture of what the run built
    and it is not editable — nothing outside the script names these rows, so
    there is nothing an override could address. The editor draws them and
    offers to convert; the conversion is a chat turn.
    """

    _components, labels = _wiring_components(registry)
    soldered: set[str] = set()
    rows: list[dict[str, Any]] = []
    for item in outputs:
        if not isinstance(item, Mapping):
            continue
        definition = item.get("definition")
        if not isinstance(definition, Mapping):
            continue
        operation = str(definition.get("operation") or "")
        if operation not in _HARNESS_OPERATIONS:
            continue
        arguments = list(definition.get("arguments") or [])
        properties = dict(definition.get("properties") or {})
        name = str(item.get("name") or "")
        if operation == "solder":
            if arguments:
                soldered.add(_address(arguments[0], labels))
            continue
        if operation == "cable":
            if len(arguments) < 2:
                continue
            ends = [arguments[0], arguments[1]]
            kind = "cable"
        else:
            connections = arguments[0] if arguments else []
            index = int(properties.get("conductor") or 0)
            if not isinstance(connections, list) or index >= len(connections):
                continue
            pair = connections[index]
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            ends = [pair[0], pair[1]]
            kind = "bundle"
        addresses = [_address(end, labels) for end in ends]
        if not all(addresses):
            # A literal (point, direction) port has no component behind it and
            # so no node to draw from; reporting half a wire would be worse
            # than reporting none.
            continue
        row = {
            "name": name,
            "a": addresses[0],
            "b": addresses[1],
            "gauge_mm": float(properties.get("gauge_mm") or 0.0),
            "enabled": True,
            "kind": kind,
        }
        # The centreline the run actually swept, and the interior of it that a
        # user may author (ADR-118). ``waypoints`` is empty on a bundle
        # conductor, which is what makes the editor treat a bundle's path as
        # read-only without having to know what a bundle is.
        route = item.get("route")
        if isinstance(route, Mapping):
            row["path"] = [list(point) for point in (route.get("path") or [])]
            row["waypoints"] = [
                list(point) for point in (route.get("waypoints") or [])
            ]
        rows.append(row)
    # Applied after the scan, not during it: a solder output may be declared
    # anywhere in the result dict, including before the cable it lands on.
    for row in rows:
        row["solder"] = row["a"] in soldered or row["b"] in soldered
    return rows


def _undeclared_wires(
    registry: list[Any], outputs: list[Any], declared: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """What a ``nets(...)`` script builds *outside* its table, read-only.

    Declaring a harness does not stop a script also calling ``part.cable`` or
    ``part.bundle`` directly, and a bundle cannot be declared at all — a net
    row is one conductor between two terminals, so a twisted run is always
    written by hand (ADR-065). Those connections were simply absent from the
    canvas: the boards they land on drew as nodes with nothing attached,
    which reads as a broken editor rather than as an undeclared wire.

    They are marked ``editable: false`` and the shell keeps them out of the
    table it pushes back, because ``set_params(nets=...)`` replaces the
    declared list wholesale and these rows are not in it.
    """

    pairs = {
        frozenset((str(row.get("a") or ""), str(row.get("b") or "")))
        for row in declared
    }
    return [
        {**row, "editable": False}
        for row in _derived_wires(registry, outputs)
        if frozenset((row["a"], row["b"])) not in pairs
    ]


def _complete_wiring(captured: Mapping[str, Any]) -> Any:
    """The harness as a graph: what is connected, and where the ends are.

    Terminals come from the accepted run's own resolution, published into its
    worker report (ADR-065). They cannot be re-derived here: a ``holes=``
    selector needs the built shape, and the live process never runs user code.

    ``source`` says which of the two tables answered. ``nets`` is the declared
    one and is editable through ``set_params(nets=...)``; ``derived`` is a
    script that predates ``nets(...)``, reconstructed from what it built and
    read-only because nothing outside it names a row.
    """

    root = str(captured.get("project_root") or "")
    if not root:
        return {
            "ok": False,
            "error": "The active document has no durable Cadex project root.",
        }
    from CadexBoards import declared_boards, effective_terminals
    from CadexNets import effective_rows
    from CadexPinResolution import accepted_attempt_dir, load_worker_report
    from CadexScriptStore import CadexProjectScriptStore

    state = CadexProjectScriptStore(root).read_state()
    revision = str(state.get("accepted_revision") or "")
    if not revision:
        return {
            "ok": False,
            "error": "The project has no accepted revision to inspect the wiring of.",
        }
    report = load_worker_report(accepted_attempt_dir(Path(root), state))
    registry = [item for item in list(report.get("wiring") or [])]
    # The terminal table as the run built it: the declared rows, replaced
    # wholesale by the stored overrides where there are any, pruned the same
    # way the runtime prunes them (ADR-120). Joined onto the resolved sockets
    # so a canvas that draws a terminal can also write the row behind it.
    board_specs = dict(state.get("board_specs") or {})
    board_rows = {
        (str(row.get("board") or ""), str(row.get("name") or "")): row
        for row in effective_terminals(board_specs, state.get("board_values"))
    }
    editable_boards = {
        name
        for name, entry in declared_boards(board_specs).items()
        if not entry.get("selector")
    }
    components, _labels = _wiring_components(registry, board_rows, editable_boards)
    specs = dict(state.get("net_specs") or {})
    if specs:
        declared = effective_rows(specs, state.get("net_values"))
        outputs = list(report.get("outputs") or [])
        # The scan is what knows the routes, and the declared table is what
        # knows the rows, so they are joined on the endpoint pair — the same
        # unordered key the shell reconciles a redrawn link on (ADR-118).
        scanned = _derived_wires(registry, outputs)
        routes = {
            frozenset((row["a"], row["b"])): row
            for row in scanned
            if "path" in row
        }
        for row in declared:
            found = routes.get(frozenset((row.get("a"), row.get("b"))))
            if found is not None:
                row["path"] = found["path"]
                row["waypoints"] = found["waypoints"]
        return {
            "revision": revision,
            "source": "nets",
            "editable": True,
            "components": components,
            "wires": declared + _undeclared_wires(registry, outputs, declared),
            "note": (
                "Rows are edited with xscript.project.set_params(nets=[...]), "
                "which replaces the whole list. Endpoints are "
                "'<port>.<terminal>'; avoid, label and every routing argument "
                "stay in the script. A row carrying editable=false is a "
                "cable or bundle the script built outside the table — drawn "
                "so the picture is complete, and changed only in the script. "
                "'path' is the centreline the run swept and 'waypoints' its "
                "interior; both are read-only here, because a path is script "
                "state and set_params(nets=) carries editor state. A row with "
                "an empty 'waypoints' is a bundle conductor, whose route "
                "belongs to the bundle. A component carrying editable=true is "
                "a board declared with boards(...): its terminals carry their "
                "row fields (origin, axis, hole_dia, depth, in millimetres in "
                "that board's own frame) and are edited with "
                "set_params(boards=[...]), which replaces the whole list the "
                "same way."
            ),
        }
    return {
        "revision": revision,
        "source": "derived",
        "editable": False,
        "components": components,
        "wires": _derived_wires(registry, list(report.get("outputs") or [])),
        "note": (
            "This script predates nets(...), so its connections are "
            "reconstructed from the cable/bundle/solder calls it made and "
            "cannot be edited — nothing outside the script names these rows. "
            "Declare the harness with nets(ports=..., wires=...) to make it "
            "editable. Rows marked kind='bundle' stay read-only either way."
        ),
    }


#: Per-output detail the worker already computed, in the order an agent
#: reading a page wants it. Absent keys are simply not reported.
_OUTPUT_DETAIL_KEYS = (
    "name",
    "type",
    "domain",
    "artifact_kind",
    "facts",
    "mesh_data",
    "operation_diagnostics",
)


def _complete_output(captured: Mapping[str, Any]) -> Any:
    """Facts for any output of the *accepted* revision, on demand.

    The facts already exist: every attempt's ``result.json`` carries them,
    and ``script.json``'s ``accepted_attempt`` pins that directory against
    GC. Before this they were readable only on the rebuild response that
    produced them, so "how big is the bracket I imported an hour ago" had no
    answer (ADR-043). Nothing is computed here.
    """

    root = str(captured.get("project_root") or "")
    if not root:
        return {
            "ok": False,
            "error": "The active document has no durable Cadex project root.",
        }
    from CadexPinResolution import (
        accepted_attempt_dir,
        accepted_output_item,
        load_worker_report,
    )
    from CadexScriptStore import CadexProjectScriptStore

    state = CadexProjectScriptStore(root).read_state()
    revision = str(state.get("accepted_revision") or "")
    if not revision:
        return {
            "ok": False,
            "error": "The project has no accepted revision to inspect outputs of.",
        }
    report = load_worker_report(accepted_attempt_dir(Path(root), state))
    items = [item for item in list(report.get("outputs") or []) if isinstance(item, Mapping)]
    target = str(captured.get("target") or "")
    if not target:
        return {
            "revision": revision,
            "output_count": len(items),
            "outputs": [
                {
                    "name": str(item.get("name") or ""),
                    "type": str(item.get("type") or ""),
                    "domain": str(item.get("domain") or ""),
                    "artifact_kind": item.get("artifact_kind"),
                }
                for item in items
            ],
        }
    try:
        item = accepted_output_item(report, target)
    except KeyError:
        raise ValueError(
            f"The accepted revision has no output named {target!r}; it publishes "
            f"{sorted(str(entry.get('name') or '') for entry in items)}."
        ) from None
    detail = {
        key: item[key] for key in _OUTPUT_DETAIL_KEYS if item.get(key) is not None
    }
    detail["revision"] = revision
    return detail


def _json_pointer_parts(pointer: str) -> list[str]:
    if not pointer:
        return []
    if not pointer.startswith("/"):
        raise ValueError("path must be an empty string or a JSON Pointer beginning with '/'.")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def _resolve_pointer(value: Any, pointer: str) -> Any:
    current = value
    for part in _json_pointer_parts(pointer):
        if isinstance(current, Mapping):
            if part not in current:
                raise ValueError(f"JSON Pointer path does not exist: {pointer!r}.")
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                raise ValueError(f"JSON Pointer path does not exist: {pointer!r}.") from exc
        else:
            raise ValueError(f"JSON Pointer traverses a scalar: {pointer!r}.")
    return current


def _pointer_child(pointer: str, value: str | int) -> str:
    escaped = str(value).replace("~", "~0").replace("/", "~1")
    return f"{pointer}/{escaped}" if pointer else f"/{escaped}"


def _encoded_bytes(value: Any) -> int:
    return len(
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    )


def _preview(value: Any, pointer: str) -> Any:
    if _encoded_bytes(value) <= _PREVIEW_BYTES:
        return value
    if isinstance(value, Mapping):
        return {"type": "object", "entry_count": len(value), "inspect_path": pointer}
    if isinstance(value, list):
        return {"type": "array", "item_count": len(value), "inspect_path": pointer}
    if isinstance(value, str):
        return {
            "type": "string",
            "characters": len(value),
            "utf8_bytes": len(value.encode("utf-8", errors="replace")),
            "inspect_path": pointer,
        }
    return {"type": type(value).__name__, "json_bytes": _encoded_bytes(value)}


def _page_value(value: Any, pointer: str, offset: int, limit: int) -> tuple[Any, dict[str, Any]]:
    if isinstance(value, Mapping):
        keyed = sorted(((str(key), key) for key in value), key=lambda item: item[0])
        string_keys = [item[0] for item in keyed]
        if len(set(string_keys)) != len(string_keys):
            raise ValueError("The inspected mapping contains ambiguous non-string keys.")
        selected = keyed[offset : offset + limit]
        page = {
            public_key: _preview(value[actual_key], _pointer_child(pointer, public_key))
            for public_key, actual_key in selected
        }
        return page, {
            "kind": "mapping",
            "total": len(keyed),
            "offset": offset,
            "returned": len(selected),
            "next_offset": (
                offset + len(selected)
                if offset + len(selected) < len(keyed)
                else None
            ),
        }
    if isinstance(value, list):
        selected = value[offset : offset + limit]
        return [
            _preview(item, _pointer_child(pointer, offset + index))
            for index, item in enumerate(selected)
        ], {
            "kind": "array",
            "total": len(value),
            "offset": offset,
            "returned": len(selected),
            "next_offset": offset + len(selected) if offset + len(selected) < len(value) else None,
        }
    if isinstance(value, str):
        character_limit = limit * 1024
        selected = value[offset : offset + character_limit]
        return selected, {
            "kind": "string",
            "total_characters": len(value),
            "offset": offset,
            "returned_characters": len(selected),
            "next_offset": offset + len(selected) if offset + len(selected) < len(value) else None,
        }
    if offset:
        raise ValueError("offset must be zero when the selected path is a scalar.")
    return value, {"kind": "scalar", "returned": 1, "next_offset": None}


def _bounded_page(raw: Any, captured: Mapping[str, Any]) -> dict[str, Any]:
    pointer = str(captured.get("path") or "")
    selected = _resolve_pointer(raw, pointer)
    offset = int(captured.get("offset") or 0)
    requested_limit = int(captured.get("limit") or 1)
    effective_limit = requested_limit
    while True:
        value, page = _page_value(selected, pointer, offset, effective_limit)
        result = {
            "ok": True,
            "scope": str(captured.get("scope") or ""),
            "target": str(captured.get("target") or ""),
            "path": pointer,
            "surface": dict(captured.get("surface") or {}),
            "document": dict(captured.get("document") or {}),
            "page": {
                **page,
                "requested_limit": requested_limit,
                "effective_limit": effective_limit,
            },
            "value": value,
        }
        result["result_json_bytes"] = 0
        size = _encoded_bytes(result)
        while result["result_json_bytes"] != size:
            result["result_json_bytes"] = size
            size = _encoded_bytes(result)
        if size <= MAX_INSPECT_RESULT_BYTES:
            return result
        if effective_limit > 1:
            effective_limit = max(1, effective_limit // 2)
            continue
        raise RuntimeError("The selected scalar exceeds the 32 KiB inspection result limit.")


def _bounded_document_objects_page(captured: Mapping[str, Any]) -> dict[str, Any]:
    values = list(captured.get("values") or [])
    requested_limit = int(captured.get("limit") or 1)
    effective_limit = len(values)
    offset = int(captured.get("offset") or 0)
    total = int(captured.get("total") or 0)
    while True:
        page_values = values[:effective_limit]
        returned = len(page_values)
        result = {
            "ok": True,
            "scope": "document",
            "target": str(captured.get("target") or ""),
            "path": "/objects",
            "surface": dict(captured.get("surface") or {}),
            "document": dict(captured.get("document") or {}),
            "page": {
                "kind": "array",
                "total": total,
                "offset": offset,
                "returned": returned,
                "next_offset": offset + returned if offset + returned < total else None,
                "requested_limit": requested_limit,
                "effective_limit": effective_limit,
            },
            "value": page_values,
        }
        result["result_json_bytes"] = 0
        size = _encoded_bytes(result)
        while result["result_json_bytes"] != size:
            result["result_json_bytes"] = size
            size = _encoded_bytes(result)
        if size <= MAX_INSPECT_RESULT_BYTES:
            return result
        if effective_limit > 1:
            effective_limit = max(1, effective_limit // 2)
            continue
        raise RuntimeError("One document object identity exceeds the inspection result limit.")


def complete_inspection(captured: Mapping[str, Any]) -> dict[str, Any]:
    """Complete artifact-backed reads and apply the exact result-size boundary."""

    try:
        kind = str(captured.get("kind") or "")
        attachment = None
        if kind == "captured":
            raw = captured.get("raw")
        elif kind == "document_objects_page":
            return _bounded_document_objects_page(captured)
        elif kind == "script":
            raw = _complete_script(captured)
        elif kind == "api":
            raw = _complete_api(captured)
        elif kind == "image":
            raw, attachment = _complete_image(captured)
        elif kind == "assets":
            raw = _complete_assets(captured)
        elif kind == "output":
            raw = _complete_output(captured)
        elif kind == "history":
            raw = _complete_history(captured)
        elif kind == "wiring":
            raw = _complete_wiring(captured)
        else:
            raise ValueError("Invalid captured core.inspect operation.")
        result = _bounded_page(raw, captured)
        if attachment is not None:
            result["_cadex_image_attachment"] = attachment
        return result
    except Exception as exc:
        error = str(exc)
        if len(error) > 4096:
            error = error[:4093] + "..."
        result = {
            "ok": False,
            "tool": "core.inspect",
            "failure_code": "INSPECTION_FAILED",
            "failure_stage": "precondition",
            "error": error,
            "scope": str(captured.get("scope") or ""),
            "target": str(captured.get("target") or ""),
        }
        result["result_json_bytes"] = 0
        size = _encoded_bytes(result)
        while result["result_json_bytes"] != size:
            result["result_json_bytes"] = size
            size = _encoded_bytes(result)
        return result
