# SPDX-License-Identifier: LGPL-2.1-or-later

"""Bounded live-document publication for XScript domain candidates."""

from __future__ import annotations

from array import array
import copy
import hashlib
from io import BytesIO
import json
import math
import re
from typing import Any, Mapping
import zipfile

import CadexReferenceContracts as reference_contracts
import CadexScriptedPublication as scripted_publication
import CadexScriptedDomains as contracts

PROP_DEFINITION = "CadexXScriptDefinition"
PROP_OUTPUT_TYPE = "CadexXScriptOutputType"
PROP_INPUT_OBJECTS = "CadexXScriptInputObjects"
PROP_NESTED_INPUT_OBJECTS = "CadexXScriptNestedInputObjects"
PROP_INPUT_SNAPSHOTS = "CadexXScriptInputSnapshots"
PROP_MESH_VALIDATION = "CadexMeshValidation"
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_]")
_ASSEMBLY_DEPENDENCY_SUFFIX = "__dependencies"
_ASSEMBLY_DEPENDENCY_OUTPUT_TYPE = "dependency_anchor"

_PERSISTED_INPUT_SNAPSHOT_KEYS = (
    "document_uid",
    "object_name",
    "artifact_kind",
    "shape_type",
    "brep_sha256",
    "brep_bytes",
    "mesh_sha256",
    "mesh_bytes",
    "mesh_segments",
    "mesh_source_placement_matrix",
    "artifact_sha256",
    "artifact_bytes",
    "attribute_artifacts",
    "structured",
    "type_id",
    "source_kind",
    "source_program_id",
    "source_program_domain",
    "source_revision",
    "transient_topology",
    "requires_semantic_interfaces",
    "reference_contract_sha256",
)


_NATIVE_TYPE_BY_OUTPUT: dict[str, str] = {
    "sketch": "Sketcher::SketchObject",
    "assembly": "Assembly::AssemblyObject",
    "component_link": "App::Link",
    "joint": "App::FeaturePython",
    "motion": "App::FeaturePython",
    "exploded_view": "App::FeaturePython",
    "solver_diagnostics": "App::FeaturePython",
    "simulation": "App::FeaturePython",
    "mjcf": "App::FeaturePython",
    "task": "App::FeaturePython",
}

_BREP_OUTPUT_TYPES = frozenset(
    {
        "solid",
        "shell",
        "face",
        "wire",
        "compound",
        "surface",
        "fill",
        "blend",
        "extension",
        "loft",
        "brep",
        "curve",
    }
)

_MESH_ROLLBACK_PROPERTIES = (
    contracts.PROP_PROGRAM_ID,
    contracts.PROP_PROGRAM_DOMAIN,
    contracts.PROP_PROGRAM_WORKBENCH,
    contracts.PROP_PROGRAM_REVISION,
    contracts.PROP_PROGRAM_OUTPUT,
    PROP_OUTPUT_TYPE,
    PROP_DEFINITION,
    PROP_INPUT_OBJECTS,
    PROP_INPUT_SNAPSHOTS,
    PROP_MESH_VALIDATION,
    reference_contracts.PROP_DERIVED_STATE,
    reference_contracts.PROP_STALE_REASON,
    reference_contracts.PROP_SOURCE_REVISION,
)
_MAX_MESH_ROLLBACK_PROPERTIES = 256
_MAX_MESH_ROLLBACK_PROPERTY_BYTES = 2 * 1024 * 1024
_MAX_ROLLBACK_PROPERTY_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
def _property_content_sha256(content: bytes | bytearray) -> str:
    """Hash persisted property data while ignoring ZIP container metadata."""

    raw = bytes(content)
    digest = hashlib.sha256()
    try:
        with zipfile.ZipFile(BytesIO(raw), "r") as archive:
            infos = sorted(
                archive.infolist(),
                key=lambda item: (str(item.filename), int(item.header_offset)),
            )
            uncompressed_bytes = sum(int(item.file_size) for item in infos)
            if uncompressed_bytes > _MAX_ROLLBACK_PROPERTY_UNCOMPRESSED_BYTES:
                raise RuntimeError(
                    "A rollback property exceeds the bounded uncompressed content limit."
                )
            digest.update(b"zip\0")
            for info in infos:
                name = str(info.filename).encode("utf-8", errors="surrogatepass")
                with archive.open(info, "r") as handle:
                    payload = handle.read(
                        _MAX_ROLLBACK_PROPERTY_UNCOMPRESSED_BYTES + 1
                    )
                if len(payload) > _MAX_ROLLBACK_PROPERTY_UNCOMPRESSED_BYTES:
                    raise RuntimeError(
                        "A rollback property entry exceeds the bounded content limit."
                    )
                digest.update(len(name).to_bytes(8, "big"))
                digest.update(name)
                digest.update(len(payload).to_bytes(8, "big"))
                digest.update(payload)
            return digest.hexdigest()
    except zipfile.BadZipFile:
        digest.update(b"raw\0")
        digest.update(raw)
        return digest.hexdigest()


def _properties(obj: Any) -> set[str]:
    return set(getattr(obj, "PropertiesList", []) or [])


def _add_string_property(obj: Any, name: str, description: str) -> None:
    if name not in _properties(obj):
        obj.addProperty("App::PropertyString", name, "Cadex", description)


def _add_property(obj: Any, property_type: str, name: str, description: str) -> None:
    if name not in _properties(obj):
        obj.addProperty(property_type, name, "Cadex", description)


def compact_persisted_input_snapshots(doc: Any) -> dict[str, Any]:
    """Remove obsolete full input facts from accepted-revision metadata.

    Runtime execution receives authenticated facts from the candidate input
    bundle. Persisted live objects need only stable identities and digests.
    Older documents duplicated the full facts payload on every output, so
    equal property strings are decoded once and compacted in place.
    """

    compacted_by_raw: dict[str, str | None] = {}
    changed_objects: list[str] = []
    invalid_objects: list[str] = []
    before_bytes = 0
    after_bytes = 0
    for obj in list(getattr(doc, "Objects", []) or []):
        if PROP_INPUT_SNAPSHOTS not in _properties(obj):
            continue
        raw = str(getattr(obj, PROP_INPUT_SNAPSHOTS, "") or "")
        if raw not in compacted_by_raw:
            compacted: str | None = raw
            try:
                snapshots = json.loads(raw)
                if not isinstance(snapshots, list) or not all(
                    isinstance(snapshot, dict) for snapshot in snapshots
                ):
                    raise ValueError("input snapshots must be a list of objects")
                if any("facts" in snapshot for snapshot in snapshots):
                    compacted = json.dumps(
                        [
                            {
                                key: value
                                for key, value in snapshot.items()
                                if key != "facts"
                            }
                            for snapshot in snapshots
                        ],
                        ensure_ascii=True,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
            except (TypeError, ValueError):
                compacted = None
            compacted_by_raw[raw] = compacted
        compacted = compacted_by_raw[raw]
        if compacted is None:
            invalid_objects.append(str(getattr(obj, "Name", "") or ""))
            continue
        if compacted == raw:
            continue
        before_bytes += len(raw.encode("utf-8"))
        after_bytes += len(compacted.encode("utf-8"))
        setattr(obj, PROP_INPUT_SNAPSHOTS, compacted)
        changed_objects.append(str(getattr(obj, "Name", "") or ""))
    return {
        "changed_objects": changed_objects,
        "invalid_objects": invalid_objects,
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
    }


def _assembly_dependency_output_name(assembly_output: str) -> str:
    return f"{assembly_output}.{_ASSEMBLY_DEPENDENCY_SUFFIX}"


def _find_assembly_dependency_anchor(
    doc: Any,
    program_id: str,
    assembly_output: str,
) -> Any | None:
    output_name = _assembly_dependency_output_name(assembly_output)
    matches = [
        obj
        for obj in _program_objects(doc, program_id, "assembly")
        if str(getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or "")
        == output_name
    ]
    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple Assembly dependency anchors claim {output_name!r}."
        )
    if not matches:
        return None
    anchor = matches[0]
    if str(getattr(anchor, "TypeId", "") or "") != "App::FeaturePython":
        raise RuntimeError(
            f"Assembly dependency anchor {anchor.Name!r} is not an App::FeaturePython."
        )
    return anchor


def _create_assembly_dependency_anchor(
    doc: Any,
    program_id: str,
    assembly_output: str,
) -> Any:
    name = _SAFE_NAME.sub(
        "_",
        f"VibeAssembly_{program_id[:8]}_{assembly_output}_Dependencies",
    )[:120]
    anchor = doc.addObject("App::FeaturePython", name)
    if anchor is None:
        raise RuntimeError("FreeCAD did not create the Assembly dependency anchor.")
    anchor.Label = "XScript Assembly dependencies"
    view = getattr(anchor, "ViewObject", None)
    if view is not None:
        view.Visibility = False
        if hasattr(view, "ShowInTree"):
            view.ShowInTree = False
    return anchor


def migrate_assembly_dependency_anchors(doc: Any) -> dict[str, Any]:
    """Move external dependency links off native Assembly containers.

    ``Assembly::AssemblyObject`` enforces GeoFeatureGroup scope for its link
    properties. Older publications put cross-container dependency links on the
    assembly itself, causing an out-of-scope warning on every recompute. A
    hidden top-level ``App::FeaturePython`` owns those invalidation links instead.
    """

    migrated: list[str] = []
    created: list[str] = []
    for assembly in list(getattr(doc, "Objects", []) or []):
        if str(getattr(assembly, "TypeId", "") or "") != "Assembly::AssemblyObject":
            continue
        if (
            str(getattr(assembly, contracts.PROP_PROGRAM_DOMAIN, "") or "")
            != "assembly"
        ):
            continue
        direct = list(getattr(assembly, PROP_INPUT_OBJECTS, []) or [])
        nested = list(getattr(assembly, PROP_NESTED_INPUT_OBJECTS, []) or [])
        if not direct and not nested:
            continue
        program_id = str(
            getattr(assembly, contracts.PROP_PROGRAM_ID, "") or ""
        )
        output_name = str(
            getattr(assembly, contracts.PROP_PROGRAM_OUTPUT, "") or ""
        )
        if not program_id or not output_name:
            raise RuntimeError(
                f"Assembly {assembly.Name!r} has dependency links without stable "
                "XScript program metadata."
            )
        anchor = _find_assembly_dependency_anchor(
            doc,
            program_id,
            output_name,
        )
        if anchor is None:
            anchor = _create_assembly_dependency_anchor(
                doc,
                program_id,
                output_name,
            )
            created.append(str(anchor.Name))
        view = getattr(anchor, "ViewObject", None)
        if view is not None:
            view.Visibility = False
            if hasattr(view, "ShowInTree"):
                view.ShowInTree = False
        string_fields = (
            contracts.PROP_PROGRAM_ID,
            contracts.PROP_PROGRAM_DOMAIN,
            contracts.PROP_PROGRAM_WORKBENCH,
            contracts.PROP_PROGRAM_REVISION,
            PROP_DEFINITION,
            PROP_INPUT_SNAPSHOTS,
            reference_contracts.PROP_DERIVED_STATE,
            reference_contracts.PROP_STALE_REASON,
            reference_contracts.PROP_SOURCE_REVISION,
        )
        for name in string_fields:
            _add_string_property(anchor, name, "Migrated Assembly dependency metadata.")
            setattr(anchor, name, str(getattr(assembly, name, "") or ""))
        _add_string_property(
            anchor,
            contracts.PROP_PROGRAM_OUTPUT,
            "Internal Assembly dependency owner.",
        )
        setattr(
            anchor,
            contracts.PROP_PROGRAM_OUTPUT,
            _assembly_dependency_output_name(output_name),
        )
        _add_string_property(
            anchor,
            PROP_OUTPUT_TYPE,
            "Internal XScript publication type.",
        )
        setattr(anchor, PROP_OUTPUT_TYPE, _ASSEMBLY_DEPENDENCY_OUTPUT_TYPE)
        _add_property(
            anchor,
            "App::PropertyXLinkList",
            PROP_INPUT_OBJECTS,
            "Live document objects used by the accepted Assembly revision.",
        )
        setattr(anchor, PROP_INPUT_OBJECTS, direct)
        _add_property(
            anchor,
            "App::PropertyXLinkList",
            PROP_NESTED_INPUT_OBJECTS,
            "Nested objects used by the accepted Assembly revision.",
        )
        setattr(anchor, PROP_NESTED_INPUT_OBJECTS, nested)
        setattr(assembly, PROP_INPUT_OBJECTS, [])
        if PROP_NESTED_INPUT_OBJECTS in _properties(assembly):
            setattr(assembly, PROP_NESTED_INPUT_OBJECTS, [])
        migrated.append(str(assembly.Name))
    return {"migrated_assemblies": migrated, "created_anchors": created}


def _ensure_assembly_motion_properties(obj: Any) -> None:
    for property_type, name, description in (
        (
            "App::PropertyXLinkSubHidden",
            "Joint",
            "The native joint driven by this motion.",
        ),
        ("App::PropertyString", "Formula", "The native symbolic motion formula."),
        ("App::PropertyEnumeration", "MotionType", "Angular or linear motion."),
    ):
        if name not in _properties(obj):
            obj.addProperty(property_type, name, "Motion", description, locked=True)


def _ensure_assembly_simulation_properties(obj: Any) -> None:
    if "Group" not in _properties(obj):
        obj.addExtension("App::GroupExtensionPython")
    for property_type, name, description in (
        ("App::PropertyTime", "aTimeStart", "Simulation start time."),
        ("App::PropertyTime", "bTimeEnd", "Simulation end time."),
        ("App::PropertyTime", "cTimeStepOutput", "Simulation output time step."),
        (
            "App::PropertyFloat",
            "fGlobalErrorTolerance",
            "Integration global error tolerance.",
        ),
        ("App::PropertyInteger", "jFramesPerSecond", "Playback frames per second."),
    ):
        if name not in _properties(obj):
            obj.addProperty(property_type, name, "Simulation", description, locked=True)


def _ensure_assembly_mjcf_properties(obj: Any) -> None:
    """The settings an exported model was built under, as live properties.

    Deliberately the *inputs* rather than the file's contents: gravity and
    the solver step are what a reader would change and re-export, while the
    XML itself is retained as a program artifact and identified by its
    digest. There is no ``Group`` here -- an export has no motions and
    nothing hangs off it (M5 phase 4).
    """

    for property_type, name, description in (
        ("App::PropertyString", "aKeyframe", "The keyframe holding the solved pose."),
        (
            "App::PropertyFloatList",
            "bGravity",
            "Gravity the model was exported under, in metres per second squared.",
        ),
        (
            "App::PropertyFloat",
            "cSolverStep",
            "Solver time step recorded in the exported model, in seconds.",
        ),
    ):
        if name not in _properties(obj):
            obj.addProperty(property_type, name, "MJCF", description, locked=True)


class AssemblyMjcfProxy:
    """Persistent proxy for one exported MuJoCo model's settings."""

    def __init__(self, obj: Any | None = None) -> None:
        if obj is not None:
            obj.Proxy = self
            _ensure_assembly_mjcf_properties(obj)

    def onDocumentRestored(self, obj: Any) -> None:  # noqa: N802
        _ensure_assembly_mjcf_properties(obj)

    def execute(self, _obj: Any) -> None:
        return None

    def dumps(self) -> None:
        return None

    def loads(self, _state: Any) -> None:
        return None


class AssemblyMotionProxy:
    """Persistent headless-safe proxy for a native Assembly motion contract."""

    def __init__(self, obj: Any | None = None) -> None:
        if obj is not None:
            obj.Proxy = self
            _ensure_assembly_motion_properties(obj)

    def onDocumentRestored(self, obj: Any) -> None:  # noqa: N802
        _ensure_assembly_motion_properties(obj)

    def execute(self, _obj: Any) -> None:
        return None

    def dumps(self) -> None:
        return None

    def loads(self, _state: Any) -> None:
        return None


class AssemblySimulationProxy:
    """Persistent proxy for precomputed native Assembly simulation settings."""

    def __init__(self, obj: Any | None = None) -> None:
        if obj is not None:
            obj.Proxy = self
            _ensure_assembly_simulation_properties(obj)

    def onDocumentRestored(self, obj: Any) -> None:  # noqa: N802
        _ensure_assembly_simulation_properties(obj)

    def execute(self, _obj: Any) -> None:
        return None

    def dumps(self) -> None:
        return None

    def loads(self, _state: Any) -> None:
        return None


def _set_metadata(
    obj: Any,
    prepared: Mapping[str, Any],
    output_name: str,
    output_type: str,
    definition: Mapping[str, Any],
) -> None:
    fields = (
        (
            contracts.PROP_PROGRAM_ID,
            "Stable XScript program id.",
            str(prepared["program_id"]),
        ),
        (
            contracts.PROP_PROGRAM_DOMAIN,
            "XScript workbench domain.",
            prepared["pack"].domain,
        ),
        (
            contracts.PROP_PROGRAM_WORKBENCH,
            "Workbench owning this XScript program.",
            prepared["pack"].workbench,
        ),
        (
            contracts.PROP_PROGRAM_REVISION,
            "Accepted XScript program revision.",
            str(prepared["revision"]),
        ),
        (
            contracts.PROP_PROGRAM_OUTPUT,
            "Stable XScript output name.",
            output_name,
        ),
        (PROP_OUTPUT_TYPE, "Declared XScript output type.", output_type),
        (
            PROP_DEFINITION,
            "Validated declarative XScript output definition.",
            json.dumps(
                dict(definition),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ),
        ),
    )
    for name, description, value in fields:
        _add_string_property(obj, name, description)
        setattr(obj, name, value)
    input_link_property_type = (
        "App::PropertyXLinkList"
        if prepared["pack"].domain == "assembly"
        and output_type == _ASSEMBLY_DEPENDENCY_OUTPUT_TYPE
        else "App::PropertyLinkList"
    )
    _add_property(
        obj,
        input_link_property_type,
        PROP_INPUT_OBJECTS,
        "Live document objects snapshotted as inputs for this accepted output.",
    )
    document = getattr(obj, "Document", None)
    resolved_references = list(prepared.get("resolved_references") or [])
    targets = []
    snapshots = []
    for reference in resolved_references:
        if reference.get("reference_kind") == "point_artifact":
            snapshots.append(
                {
                    key: reference.get(key)
                    for key in (
                        "reference_kind",
                        "artifact_id",
                        "name",
                        "label",
                        "format",
                        "artifact_sha256",
                        "artifact_bytes",
                    )
                }
            )
            continue
        target = (
            document.getObject(str(reference.get("object_name") or ""))
            if document is not None
            else None
        )
        if target is None:
            raise RuntimeError(
                f"Accepted input object {reference.get('object_name')!r} disappeared "
                "before publication metadata was applied."
            )
        targets.append(target)
        snapshots.append(
            {
                key: reference.get(key)
                for key in _PERSISTED_INPUT_SNAPSHOT_KEYS
            }
        )
    dependency_targets = targets
    if prepared["pack"].domain == "assembly":
        # Native Assembly containers and children reject links outside their
        # GeoFeatureGroup scope. A hidden top-level dependency anchor owns all
        # source links used for downstream invalidation.
        dependency_targets = (
            targets
            if output_type == _ASSEMBLY_DEPENDENCY_OUTPUT_TYPE
            else []
        )
    setattr(obj, PROP_INPUT_OBJECTS, dependency_targets)
    if prepared["pack"].domain == "assembly":
        _add_property(
            obj,
            "App::PropertyXLinkList",
            PROP_NESTED_INPUT_OBJECTS,
            "Nested native source objects authenticated through an Assembly/App::Part hierarchy.",
        )
        nested_targets: list[Any] = []
        if output_type == _ASSEMBLY_DEPENDENCY_OUTPUT_TYPE:
            import FreeCAD as App

            documents_by_uid = {
                str(getattr(candidate, "Uid", "") or ""): candidate
                for candidate in App.listDocuments().values()
            }
            seen_identities = {
                (
                    str(getattr(getattr(target, "Document", None), "Uid", "") or ""),
                    str(getattr(target, "Name", "") or ""),
                )
                for target in targets
            }
            for reference in resolved_references:
                hierarchy = reference.get("assembly_hierarchy")
                if not isinstance(hierarchy, Mapping):
                    continue
                for node in list(hierarchy.get("nodes") or []):
                    if not isinstance(node, Mapping):
                        continue
                    identity = node.get("identity")
                    if not isinstance(identity, Mapping):
                        continue
                    identity_key = (
                        str(identity.get("document_uid") or ""),
                        str(identity.get("object_name") or ""),
                    )
                    source_document = documents_by_uid.get(identity_key[0])
                    target = (
                        source_document.getObject(identity_key[1])
                        if source_document is not None
                        else None
                    )
                    if target is None:
                        raise RuntimeError(
                            "Accepted nested Assembly source "
                            f"{identity_key[1]!r} disappeared before publication could "
                            "install downstream invalidation."
                        )
                    if identity_key not in seen_identities:
                        nested_targets.append(target)
                        seen_identities.add(identity_key)
        setattr(obj, PROP_NESTED_INPUT_OBJECTS, nested_targets)
    _add_string_property(
        obj,
        PROP_INPUT_SNAPSHOTS,
        "Immutable identities and input artifact digests used by the accepted revision.",
    )
    setattr(
        obj,
        PROP_INPUT_SNAPSHOTS,
        json.dumps(snapshots, sort_keys=True, separators=(",", ":")),
    )
    for name in (
        reference_contracts.PROP_DERIVED_STATE,
        reference_contracts.PROP_STALE_REASON,
        reference_contracts.PROP_SOURCE_REVISION,
    ):
        _add_string_property(obj, name, "Accepted input snapshot state.")
    setattr(obj, reference_contracts.PROP_DERIVED_STATE, "accepted")
    setattr(obj, reference_contracts.PROP_STALE_REASON, "")
    setattr(obj, reference_contracts.PROP_SOURCE_REVISION, str(prepared["revision"]))


def mark_programs_stale_from_source(source: Any, property_name: str) -> list[str]:
    """Mark v2 outputs stale when a linked native snapshot source changes."""

    changed_property = str(property_name or "")
    if not changed_property or changed_property.startswith("Cadex"):
        return []
    label_only = changed_property == "Label"
    marked: list[str] = []
    programs: dict[tuple[str, str, str], Any] = {}
    for output in list(getattr(source, "InList", []) or []):
        properties = _properties(output)
        if not ({PROP_INPUT_OBJECTS, PROP_NESTED_INPUT_OBJECTS} & properties):
            continue
        inputs = [
            *list(getattr(output, PROP_INPUT_OBJECTS, []) or []),
            *list(getattr(output, PROP_NESTED_INPUT_OBJECTS, []) or []),
        ]
        if not any(item is source for item in inputs):
            continue
        output_document = getattr(output, "Document", None)
        program_id = str(getattr(output, contracts.PROP_PROGRAM_ID, "") or "")
        domain = str(getattr(output, contracts.PROP_PROGRAM_DOMAIN, "") or "")
        if label_only and domain != "assembly":
            continue
        if output_document is None or not program_id or not domain:
            continue
        programs[
            (
                str(getattr(output_document, "Uid", "") or ""),
                program_id,
                domain,
            )
        ] = output_document
    for (_document_uid, program_id, domain), document in programs.items():
        candidates = _program_objects(document, program_id, domain)
        for output in candidates:
            already_stale = (
                str(getattr(output, reference_contracts.PROP_DERIVED_STATE, "") or "")
                == "stale"
            )
            if not already_stale:
                revision = str(
                    getattr(output, contracts.PROP_PROGRAM_REVISION, "") or ""
                )
                reference_contracts.mark_stale(
                    output,
                    revision,
                    f"Input object {getattr(source, 'Name', '<object>')}."
                    f"{changed_property} changed after this XScript snapshot; "
                    "regenerate the program.",
                )
            if not already_stale:
                marked.append(str(getattr(output, "Name", "") or ""))
    return sorted(set(marked))


def _program_objects(doc: Any, program_id: str, domain: str) -> list[Any]:
    result = []
    for obj in list(getattr(doc, "Objects", []) or []):
        properties = _properties(obj)
        if not {contracts.PROP_PROGRAM_ID, contracts.PROP_PROGRAM_DOMAIN} <= properties:
            continue
        if (
            str(getattr(obj, contracts.PROP_PROGRAM_ID, "") or "") == program_id
            and str(getattr(obj, contracts.PROP_PROGRAM_DOMAIN, "") or "") == domain
        ):
            result.append(obj)
    return result


def _objects_by_output(doc: Any, prepared: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for obj in _program_objects(
        doc, str(prepared["program_id"]), prepared["pack"].domain
    ):
        output_name = str(getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or "")
        if not output_name or "." in output_name:
            continue
        if output_name in result:
            raise RuntimeError(
                f"Multiple live objects claim XScript output {output_name!r}."
            )
        result[output_name] = obj
    return result


def _retired_program_objects(
    doc: Any,
    prepared: Mapping[str, Any],
    desired_outputs: set[str],
) -> list[Any]:
    owned = _program_objects(doc, str(prepared["program_id"]), prepared["pack"].domain)
    internal = list(owned)
    for obj in owned:
        if str(getattr(obj, "TypeId", "")) == "Assembly::AssemblyObject":
            joint_group = _assembly_joint_group(obj)
            if joint_group is not None:
                internal.append(joint_group)
            simulation_group = _assembly_simulation_group(obj)
            if simulation_group is not None:
                internal.append(simulation_group)
            view_group = _assembly_view_group(obj)
            if view_group is not None:
                internal.append(view_group)
    retired = []
    for obj in owned:
        output_name = str(getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or "")
        root_name = output_name.partition(".")[0]
        if not output_name or root_name in desired_outputs:
            continue
        external = _external_uses(doc, [obj], internal)
        if external:
            raise _reference_error(
                f"Cannot retire XScript output {output_name!r}; human-created "
                "or foreign document objects still reference it",
                external,
            )
        retired.append(obj)
    return retired


def _remove_owned_objects(doc: Any, objects: list[Any]) -> list[str]:
    # Work from live name lookups: removing one object can cascade-delete
    # another in the set (group/origin internals), leaving stale proxies that
    # raise ReferenceError on attribute access.
    remaining = {str(obj.Name) for obj in objects}
    removed: list[str] = []
    while remaining:
        live = {name: doc.getObject(name) for name in sorted(remaining)}
        remaining = {name for name, obj in live.items() if obj is not None}
        if not remaining:
            break
        children = [
            name
            for name in sorted(remaining)
            if not any(
                str(getattr(parent, "Name", "") or "") in remaining
                for parent in list(getattr(live[name], "InList", []) or [])
            )
        ]
        name = children[0] if children else next(iter(sorted(remaining)))
        remaining.discard(name)
        if doc.getObject(name) is not None:
            doc.removeObject(name)
            removed.append(name)
    return removed


def _external_uses(
    doc: Any,
    targets: list[Any],
    internal: list[Any],
) -> list[dict[str, Any]]:
    if not targets:
        return []
    return scripted_publication.external_reference_uses(
        doc,
        targets,
        internal_objects=internal,
    )


def _reference_error(prefix: str, uses: list[dict[str, Any]]) -> RuntimeError:
    details = scripted_publication.json_reference_uses(uses)
    return RuntimeError(f"{prefix}: {json.dumps(details, sort_keys=True)}")


def _preflight_output_updates(
    doc: Any,
    targets: list[Any],
    internal: list[Any],
) -> list[dict[str, Any]]:
    uses = _external_uses(doc, targets, internal)
    unsafe = [item for item in uses if list(item.get("subelements") or [])]
    if unsafe:
        raise _reference_error(
            "Cannot regenerate these stable XScript outputs while native objects "
            "hold Face/Edge/Vertex references. This domain does not claim those transient "
            "subelement names are semantically stable; remove or retarget the listed "
            "consumers, then retry",
            unsafe,
        )
    return uses


def _refresh_external_consumers(
    uses: list[dict[str, Any]],
    *,
    revision: str,
) -> dict[str, Any]:
    touched: list[str] = []
    stale: list[str] = []
    owners: dict[int, Any] = {
        id(item["owner"]): item["owner"]
        for item in uses
        if item.get("owner") is not None
    }
    for owner in owners.values():
        name = str(getattr(owner, "Name", "") or "")
        touch = getattr(owner, "touch", None)
        if callable(touch):
            touch()
            touched.append(name)
    return {"touched": sorted(set(touched)), "marked_stale": sorted(set(stale))}


def _internal_name(prepared: Mapping[str, Any], output_name: str) -> str:
    domain = _SAFE_NAME.sub("_", prepared["pack"].domain.title())
    output = _SAFE_NAME.sub("_", output_name)
    return f"Vibe{domain}_{str(prepared['program_id'])[:8]}_{output}"[:120]


def _native_type(output_type: str) -> str:
    if output_type in _BREP_OUTPUT_TYPES:
        return "Part::Feature"
    if output_type == "mesh":
        return "Mesh::Feature"
    native_type = _NATIVE_TYPE_BY_OUTPUT.get(output_type)
    if native_type is None:
        raise RuntimeError(
            f"No native publisher exists for output type {output_type!r}."
        )
    return native_type


def _definition_argument(
    definition: Mapping[str, Any],
    index: int,
    *names: str,
    default: Any = None,
) -> Any:
    arguments = list(definition.get("arguments") or [])
    if index < len(arguments):
        return arguments[index]
    properties = dict(definition.get("properties") or {})
    for name in names:
        if name in properties:
            return properties[name]
    return default


def _create_object(
    doc: Any,
    prepared: Mapping[str, Any],
    output_name: str,
    output_type: str,
    definition: Mapping[str, Any],
    assembly: Any | None,
) -> Any:
    native_type = _native_type(output_type)
    name = _internal_name(prepared, output_name)
    if output_type == "component_link" and assembly is not None:
        source = _definition_argument(definition, 0, "source")
        target = _reference_target(doc, source, f"output {output_name} source")
        native_type = (
            "Assembly::AssemblyLink"
            if bool(
                getattr(target, "isDerivedFrom", lambda _type: False)(
                    "Assembly::AssemblyObject"
                )
            )
            else "App::Link"
        )
        obj = assembly.newObject(native_type, name)
    elif output_type == "joint" and assembly is not None:
        joint_group = _assembly_joint_group(assembly)
        if joint_group is None:
            joint_group = assembly.newObject("Assembly::JointGroup", "Joints")
        obj = joint_group.newObject(native_type, name)
    elif (
        prepared["pack"].domain == "assembly"
        and output_type == "motion"
        and assembly is not None
    ):
        obj = assembly.newObject(native_type, name)
    elif (
        prepared["pack"].domain == "assembly"
        and output_type == "simulation"
        and assembly is not None
    ):
        simulation_group = _assembly_simulation_group(assembly)
        if simulation_group is None:
            simulation_group = assembly.newObject(
                "Assembly::SimulationGroup", "Simulations"
            )
        obj = simulation_group.newObject(native_type, name)
    elif (
        prepared["pack"].domain == "assembly"
        and output_type == "exploded_view"
        and assembly is not None
    ):
        view_group = _assembly_view_group(assembly)
        if view_group is None:
            view_group = assembly.newObject("Assembly::ViewGroup", "Exploded Views")
        obj = view_group.newObject(native_type, name)
    else:
        obj = doc.addObject(native_type, name)
    if obj is None:
        raise RuntimeError(
            f"FreeCAD did not create native type {native_type!r} for output {output_name!r}."
        )
    if output_type == "assembly":
        obj.Type = "Assembly"
        if _assembly_joint_group(obj) is None:
            obj.newObject("Assembly::JointGroup", "Joints")
    return obj


def _definition(item: Mapping[str, Any]) -> dict[str, Any]:
    raw = item.get("definition")
    if not isinstance(raw, dict):
        raise RuntimeError(f"Output {item.get('name')!r} has no validated definition.")
    return raw


def _definition_properties(item: Mapping[str, Any]) -> dict[str, Any]:
    raw = _definition(item).get("properties")
    return dict(raw) if isinstance(raw, dict) else {}


def _label(item: Mapping[str, Any], fallback: str) -> str:
    value = str(_definition_properties(item).get("label") or "").strip()
    return value or fallback


def _reference_target(doc: Any, value: Any, label: str) -> Any:
    if not isinstance(value, dict) or set(value) != {"document_uid", "object_name"}:
        raise RuntimeError(f"{label} must be one validated stable document reference.")
    if str(value.get("document_uid") or "") != str(getattr(doc, "Uid", "") or ""):
        raise RuntimeError(f"{label} refers to another document.")
    target = doc.getObject(str(value.get("object_name") or ""))
    if target is None:
        raise RuntimeError(f"{label} target disappeared before publication.")
    return target


def _component_native_type(doc: Any, item: Mapping[str, Any]) -> str:
    data = item.get("assembly_data")
    data = dict(data) if isinstance(data, dict) else {}
    source = data.get("source")
    if source is None:
        source = _definition_argument(_definition(item), 0, "source")
    target = _reference_target(doc, source, f"output {item.get('name')} source")
    return (
        "Assembly::AssemblyLink"
        if bool(
            getattr(target, "isDerivedFrom", lambda _type: False)(
                "Assembly::AssemblyObject"
            )
        )
        else "App::Link"
    )


def _placement(value: Any) -> Any:
    import FreeCAD as App

    if value is None:
        return App.Placement()
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return App.Placement(
            App.Vector(*(float(item) for item in value)), App.Rotation()
        )
    if not isinstance(value, dict):
        raise RuntimeError("placement must be [x,y,z] or an object.")
    position = value.get("position", [0.0, 0.0, 0.0])
    if not isinstance(position, (list, tuple)) or len(position) != 3:
        raise RuntimeError("placement.position must be [x,y,z].")
    rotation = value.get("rotation", [0.0, 0.0, 0.0, 1.0])
    if not isinstance(rotation, (list, tuple)) or len(rotation) != 4:
        raise RuntimeError("placement.rotation must be quaternion [x,y,z,w].")
    return App.Placement(
        App.Vector(*(float(item) for item in position)),
        App.Rotation(
            float(rotation[0]),
            float(rotation[1]),
            float(rotation[2]),
            float(rotation[3]),
        ),
    )


def _placement_from_matrix(values: Any) -> Any:
    import FreeCAD as App

    if not isinstance(values, list) or len(values) != 16:
        raise RuntimeError("A solved placement matrix must contain 16 numbers.")
    matrix = App.Matrix()
    for name, value in zip(
        (
            "A11",
            "A12",
            "A13",
            "A14",
            "A21",
            "A22",
            "A23",
            "A24",
            "A31",
            "A32",
            "A33",
            "A34",
            "A41",
            "A42",
            "A43",
            "A44",
        ),
        values,
    ):
        setattr(matrix, name, float(value))
    return App.Placement(matrix)


def _assembly_joint_group(assembly: Any) -> Any | None:
    for child in list(getattr(assembly, "Group", []) or []):
        if str(getattr(child, "TypeId", "")) == "Assembly::JointGroup":
            return child
    for child in list(getattr(assembly, "OutList", []) or []):
        if str(getattr(child, "TypeId", "")) == "Assembly::JointGroup":
            return child
    return None


def _assembly_simulation_group(assembly: Any) -> Any | None:
    for child in list(getattr(assembly, "Group", []) or []):
        if str(getattr(child, "TypeId", "")) == "Assembly::SimulationGroup":
            return child
    for child in list(getattr(assembly, "OutList", []) or []):
        if str(getattr(child, "TypeId", "")) == "Assembly::SimulationGroup":
            return child
    return None


def _assembly_view_group(assembly: Any) -> Any | None:
    for child in list(getattr(assembly, "Group", []) or []):
        if str(getattr(child, "TypeId", "")) == "Assembly::ViewGroup":
            return child
    for child in list(getattr(assembly, "OutList", []) or []):
        if str(getattr(child, "TypeId", "")) == "Assembly::ViewGroup":
            return child
    return None


def _assembly_component_reference(
    prepared: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any] | None:
    data = item.get("assembly_data")
    data = dict(data) if isinstance(data, Mapping) else {}
    source = data.get("source")
    if not isinstance(source, Mapping):
        arguments = list(_definition(item).get("arguments") or [])
        source = arguments[0] if arguments else None
    if not isinstance(source, Mapping):
        return None
    key = (
        str(source.get("document_uid") or ""),
        str(source.get("object_name") or ""),
    )
    return next(
        (
            dict(reference)
            for reference in list(prepared.get("resolved_references") or [])
            if (
                str(reference.get("document_uid") or ""),
                str(reference.get("object_name") or ""),
            )
            == key
        ),
        None,
    )


def _live_assembly_reference(
    component: Any,
    descriptor: Mapping[str, Any],
    stable_path: str,
    subelements: list[str],
    *,
    context: str,
) -> dict[str, Any]:
    """Resolve a stable source path without consuming generated child names."""

    nodes = descriptor.get("nodes")
    node_by_id = {
        str(node.get("node_id") or ""): node
        for node in list(nodes or [])
        if isinstance(node, Mapping)
    }
    root_node_id = str(descriptor.get("root_node_id") or "")
    current_node = node_by_id.get(root_node_id)
    if current_node is None or not stable_path:
        raise RuntimeError(f"{context} has no authenticated stable occurrence path.")
    container = component
    target = component
    prefix_names: list[str] = []
    locked = False
    leaf = None
    leaf_live = False
    for index, segment in enumerate(stable_path.split("/")):
        occurrence = next(
            (
                item
                for item in list(current_node.get("occurrences") or [])
                if isinstance(item, Mapping)
                and str(item.get("name") or "") == segment
            ),
            None,
        )
        if occurrence is None:
            raise RuntimeError(
                f"{context} occurrence_path {stable_path!r} changed after validation."
            )
        source_node = node_by_id.get(str(occurrence.get("source_node_id") or ""))
        if source_node is None:
            raise RuntimeError(f"{context} occurrence path reaches a missing source node.")
        source_identity = current_node.get("identity")
        if not isinstance(source_identity, Mapping):
            raise RuntimeError(f"{context} source node has no stable identity.")
        source_document = getattr(component, "Document", None)
        source_occurrence = (
            source_document.getObject(str(occurrence.get("name") or ""))
            if source_document is not None
            else None
        )
        source_container = (
            source_document.getObject(str(source_identity.get("object_name") or ""))
            if source_document is not None
            else None
        )
        if source_occurrence is None or source_container is None or source_occurrence not in list(
            getattr(source_container, "Group", []) or []
        ):
            raise RuntimeError(
                f"{context} source occurrence {segment!r} disappeared before publication."
            )

        container_type = str(getattr(container, "TypeId", "") or "")
        if container_type == "Assembly::AssemblyLink":
            matches = [
                child
                for child in list(getattr(container, "Group", []) or [])
                if getattr(child, "LinkedObject", None) is source_occurrence
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"{context} could not map stable occurrence_path {stable_path!r} "
                    f"at segment {index}; native synchronization produced "
                    f"{len(matches)} matches. Recompute the source Assembly and retry."
                )
            actual = matches[0]
            actual_live = True
        else:
            # An App::Link to an App::Part addresses deeper source objects by
            # subname; those objects are not independent live occurrences.
            actual = source_occurrence
            actual_live = False

        if locked:
            prefix_names.append(str(actual.Name))
        elif container_type == "Assembly::AssemblyLink":
            if bool(getattr(container, "Rigid", True)):
                locked = True
                prefix_names.append(str(actual.Name))
            else:
                target = actual
                prefix_names = []
        else:
            locked = True
            prefix_names.append(str(actual.Name))
        leaf = actual
        leaf_live = actual_live
        container = actual
        current_node = source_node
    if leaf is None:
        raise RuntimeError(f"{context} did not resolve an occurrence.")
    prefix = ".".join(prefix_names)
    native_subelements = [
        (
            f"{prefix}.{value}"
            if prefix and value
            else f"{prefix}."
            if prefix
            else value
        )
        for value in subelements
    ]
    return {
        "target": target,
        "subelements": native_subelements,
        "leaf": leaf,
        "leaf_live": leaf_live,
    }


def _configure_component(
    doc: Any,
    obj: Any,
    item: Mapping[str, Any],
    outputs: Mapping[str, Any],
    prepared: Mapping[str, Any],
) -> None:
    properties = _definition_properties(item)
    assembly_data = item.get("assembly_data")
    assembly_data = dict(assembly_data) if isinstance(assembly_data, dict) else {}
    source = assembly_data.get("source", properties.get("source"))
    if source is None:
        arguments = list(_definition(item).get("arguments") or [])
        source = arguments[0] if arguments else None
    target = _reference_target(doc, source, f"output {item['name']} source")
    flexible = bool(assembly_data.get("flexible", properties.get("flexible", False)))
    is_assembly_link = str(getattr(obj, "TypeId", "") or "") == (
        "Assembly::AssemblyLink"
    )
    if flexible and not is_assembly_link:
        raise RuntimeError(
            f"Flexible component output {item['name']!r} requires a native "
            "Assembly::AssemblyLink."
        )
    was_linked = getattr(obj, "LinkedObject", None) is not None
    mode_changed = is_assembly_link and bool(getattr(obj, "Rigid", True)) is flexible
    if was_linked and mode_changed:
        managed = _program_objects(
            doc,
            str(prepared["program_id"]),
            prepared["pack"].domain,
        )
        external = _external_uses(doc, [obj], managed)
        if external:
            raise _reference_error(
                f"Cannot change flexible mode for component output {item['name']!r}; "
                "external objects reference its current rigid/flexible identity. "
                "Keep the mode or return the changed component under a new output name",
                external,
            )
    initial_placement = _placement(
        properties.get("placement") or properties.get("position")
    )
    obj.LinkedObject = target
    if is_assembly_link:
        if not was_linked or mode_changed:
            obj.Placement = initial_placement
            obj.Rigid = not flexible
        synchronize = getattr(obj, "synchronizeContents", None)
        if not callable(synchronize):
            raise RuntimeError(
                "AssemblyLink.synchronizeContents is unavailable; rebuild the native "
                "Assembly module before publishing flexible XScript components."
            )
        synchronize()
    if item.get("solved_placement_matrix") is not None:
        obj.Placement = _placement_from_matrix(item["solved_placement_matrix"])
    else:
        obj.Placement = initial_placement
    reference = _assembly_component_reference(prepared, item)
    descriptor = (
        reference.get("assembly_hierarchy")
        if isinstance(reference, Mapping)
        else None
    )
    solved_occurrences = assembly_data.get("solved_occurrences")
    if solved_occurrences is not None:
        states = list(solved_occurrences)
        if not isinstance(descriptor, Mapping) or any(
            not isinstance(state, Mapping) for state in states
        ):
            raise RuntimeError(
                f"Component output {item['name']!r} has malformed occurrence evidence."
            )
        if not is_assembly_link and any(
            bool(state.get("live_occurrence")) for state in states
        ):
            raise RuntimeError(
                f"Component output {item['name']!r} claims live occurrence placements "
                "without a native AssemblyLink."
            )
        for state in states:
            if not bool(state.get("live_occurrence")):
                continue
            path = str(state.get("occurrence_path") or "")
            resolved = _live_assembly_reference(
                obj,
                descriptor,
                path,
                ["", ""],
                context=f"component output {item['name']!r}",
            )
            local = state.get("local_placement")
            if not bool(resolved["leaf_live"]) or not isinstance(local, Mapping):
                raise RuntimeError(
                    f"Component output {item['name']!r} occurrence {path!r} lost "
                    "its live placement before publication."
                )
            resolved["leaf"].Placement = _placement_from_matrix(
                list(local.get("matrix") or [])
            )
    grounded = bool(assembly_data.get("grounded", properties.get("grounded")))
    assembly = next(
        (
            output
            for output in outputs.values()
            if str(getattr(output, "TypeId", "")) == "Assembly::AssemblyObject"
        ),
        None,
    )
    ground_output = f"{item['name']}.ground"
    joint_group = _assembly_joint_group(assembly) if assembly is not None else None
    existing = next(
        (
            child
            for child in list(getattr(joint_group, "Group", []) or [])
            if str(getattr(child, contracts.PROP_PROGRAM_OUTPUT, "") or "")
            == ground_output
        ),
        None,
    )
    if grounded:
        if assembly is None:
            raise RuntimeError("A grounded component requires an assembly output.")
        assert joint_group is not None
        if existing is None:
            import JointObject

            existing = joint_group.newObject(
                "App::FeaturePython", _SAFE_NAME.sub("_", f"Ground_{item['name']}")
            )
            JointObject.GroundedJoint(existing, obj)
            JointObject.ensureViewProviderGroundedJoint(existing)
        _set_metadata(
            existing,
            prepared,
            ground_output,
            "joint",
            {"operation": "ground", "component_output": item["name"]},
        )
    elif existing is not None:
        external = _external_uses(
            doc,
            [existing],
            _program_objects(
                doc,
                str(prepared["program_id"]),
                prepared["pack"].domain,
            ),
        )
        if external:
            raise _reference_error(
                f"Cannot unground component output {item['name']!r}; external objects "
                "reference its managed grounding joint",
                external,
            )
        doc.removeObject(str(existing.Name))


def _configure_joint_while_suspended(
    obj: Any,
    item: Mapping[str, Any],
    outputs: Mapping[str, Any],
    prepared: Mapping[str, Any],
) -> None:
    properties = _definition_properties(item)
    assembly_data = item.get("assembly_data")
    assembly_data = dict(assembly_data) if isinstance(assembly_data, dict) else {}
    kind = str(
        assembly_data.get("kind") or properties.get("type") or "revolute"
    ).lower()
    native_names = {
        "fixed": "Fixed",
        "revolute": "Revolute",
        "cylindrical": "Cylindrical",
        "slider": "Slider",
        "ball": "Ball",
        "distance": "Distance",
        "parallel": "Parallel",
        "perpendicular": "Perpendicular",
        "angle": "Angle",
        "rack_pinion": "RackPinion",
        "screw": "Screw",
        "gears": "Gears",
        "belt": "Belt",
    }
    try:
        import JointObject
    except Exception as exc:
        raise RuntimeError(
            f"Native Assembly JointObject is unavailable: {exc}"
        ) from exc
    native = native_names.get(kind)
    if native is None or native not in list(JointObject.JointTypes):
        raise RuntimeError(f"Unsupported native assembly joint type {kind!r}.")
    if not hasattr(obj, "Proxy") or obj.Proxy is None:
        JointObject.Joint(obj, JointObject.JointTypes.index(native))
    elif str(getattr(obj, "JointType", "") or "") != native:
        obj.Proxy.setJointType(obj, native)
    JointObject.ensureViewProviderJoint(obj)
    if assembly_data:
        obj.Detach1 = True
        obj.Detach2 = True
        obj.Reference1 = None
        obj.Reference2 = None
        parameters = dict(assembly_data.get("parameters") or {})
        if kind == "distance":
            obj.Distance = float(parameters["distance_mm"])
        elif kind == "angle":
            obj.Angle = float(parameters["angle_degrees"])
        elif kind == "rack_pinion":
            obj.Distance = float(parameters["pitch_radius_mm"])
        elif kind == "screw":
            obj.Distance = float(parameters["thread_pitch_mm"])
        elif kind in {"gears", "belt"}:
            obj.Distance = float(parameters["radius1_mm"])
            obj.Distance2 = float(parameters["radius2_mm"])
        length_limits = assembly_data.get("length_limits_mm")
        length_min = length_limits[0] if length_limits is not None else None
        length_max = length_limits[1] if length_limits is not None else None
        obj.EnableLengthMin = length_min is not None
        obj.EnableLengthMax = length_max is not None
        if length_limits is not None:
            if length_min is not None:
                obj.LengthMin = float(length_min)
            if length_max is not None:
                obj.LengthMax = float(length_max)
        angle_limits = assembly_data.get("angle_limits_degrees")
        angle_min = angle_limits[0] if angle_limits is not None else None
        angle_max = angle_limits[1] if angle_limits is not None else None
        obj.EnableAngleMin = angle_min is not None
        obj.EnableAngleMax = angle_max is not None
        if angle_limits is not None:
            if angle_min is not None:
                obj.AngleMin = float(angle_min)
            if angle_max is not None:
                obj.AngleMax = float(angle_max)
        connectors = list(assembly_data.get("connectors") or [])
        if len(connectors) != 2:
            raise RuntimeError("A validated Assembly joint must have two connectors.")
        for index, connector in enumerate(connectors, start=1):
            component_name = str(connector.get("component_output") or "")
            component = outputs.get(component_name)
            if component is None:
                raise RuntimeError(
                    f"Assembly joint refers to unknown component output {component_name!r}."
                )
            element = str(connector.get("element") or "")
            anchor = str(connector.get("anchor") or element)
            native_target = component
            native_subelements = [element, anchor]
            occurrence_path = str(connector.get("occurrence_path") or "")
            if occurrence_path:
                source = getattr(component, "LinkedObject", None)
                key = (
                    str(getattr(getattr(source, "Document", None), "Uid", "") or ""),
                    str(getattr(source, "Name", "") or ""),
                )
                reference = next(
                    (
                        value
                        for value in list(prepared.get("resolved_references") or [])
                        if (
                            str(value.get("document_uid") or ""),
                            str(value.get("object_name") or ""),
                        )
                        == key
                    ),
                    None,
                )
                descriptor = (
                    reference.get("assembly_hierarchy")
                    if isinstance(reference, Mapping)
                    else None
                )
                if not isinstance(descriptor, Mapping):
                    raise RuntimeError(
                        f"Assembly joint occurrence_path {occurrence_path!r} has no "
                        "authenticated live hierarchy."
                    )
                resolved = _live_assembly_reference(
                    component,
                    descriptor,
                    occurrence_path,
                    [element, anchor],
                    context=(
                        f"joint output {item['name']!r} connector {index}"
                    ),
                )
                native_target = resolved["target"]
                native_subelements = list(resolved["subelements"])
            setattr(
                obj,
                f"Offset{index}",
                _placement_from_matrix(
                    list((connector.get("offset") or {}).get("matrix") or [])
                ),
            )
            setattr(
                obj,
                f"Reference{index}",
                [native_target, native_subelements],
            )
            setattr(
                obj,
                f"Placement{index}",
                _placement_from_matrix(
                    list((connector.get("local_frame") or {}).get("matrix") or [])
                ),
            )
        if hasattr(obj, "Suppressed"):
            obj.Suppressed = bool(assembly_data.get("suppressed"))
        _add_string_property(
            obj,
            "CadexAssemblyJointValidation",
            "Precomputed native connector frames, compatibility, and parameter readback.",
        )
        obj.CadexAssemblyJointValidation = json.dumps(
            assembly_data,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return
    references = []
    for key in ("reference1", "reference2"):
        reference = properties.get(key)
        if not isinstance(reference, dict):
            raise RuntimeError(f"Assembly joint {key} must be an object.")
        component_name = str(reference.get("component_output") or "")
        component = outputs.get(component_name)
        if component is None:
            raise RuntimeError(
                f"Assembly joint refers to unknown component output {component_name!r}."
            )
        element = str(reference.get("element") or "")
        references.append([component, [element, element]])
    obj.Proxy.setJointConnectors(obj, references)


def _configure_joint(
    obj: Any,
    item: Mapping[str, Any],
    outputs: Mapping[str, Any],
    prepared: Mapping[str, Any],
) -> None:
    """Apply precomputed joint state with native auto-solve temporarily disabled."""

    import Preferences

    preferences = Preferences.preferences()
    previous = bool(preferences.GetBool("SolveInJointCreation", True))
    preferences.SetBool("SolveInJointCreation", False)
    try:
        _configure_joint_while_suspended(obj, item, outputs, prepared)
    finally:
        preferences.SetBool("SolveInJointCreation", previous)


def _configure_assembly_motion(
    obj: Any, item: Mapping[str, Any], outputs: Mapping[str, Any]
) -> None:
    """Apply one authenticated native motion contract without running kinematics."""

    data = item.get("assembly_data")
    if not isinstance(data, Mapping):
        raise RuntimeError("An Assembly motion has no validated native data.")
    data = dict(data)
    joint_name = str(data.get("joint_output") or "")
    joint = outputs.get(joint_name)
    if joint is None or str(getattr(joint, "TypeId", "")) != "App::FeaturePython":
        raise RuntimeError(
            f"Assembly motion {item['name']!r} joint {joint_name!r} is unavailable."
        )
    if not isinstance(getattr(obj, "Proxy", None), AssemblyMotionProxy):
        AssemblyMotionProxy(obj)
    else:
        _ensure_assembly_motion_properties(obj)
    obj.MotionType = ["Angular", "Linear"]
    obj.MotionType = str(data["native_motion_type"])
    obj.Joint = joint
    obj.Formula = str(data["formula"])
    reference = getattr(obj, "Joint", None)
    if (
        not isinstance(reference, (list, tuple))
        or not reference
        or reference[0] is not joint
        or str(obj.MotionType) != str(data["native_motion_type"])
        or str(obj.Formula) != str(data["formula"])
    ):
        raise RuntimeError(
            f"Live Assembly motion {item['name']!r} changed its validated contract."
        )
    _add_string_property(
        obj,
        "CadexAssemblyMotionValidation",
        "Authenticated native Assembly motion definition and driven joint identity.",
    )
    obj.CadexAssemblyMotionValidation = json.dumps(
        data,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _configure_assembly_simulation(
    obj: Any, item: Mapping[str, Any], outputs: Mapping[str, Any]
) -> None:
    """Publish worker-generated kinematic settings and a bounded trace preview."""

    data = item.get("assembly_data")
    preview = item.get("simulation_trace_preview")
    if not isinstance(data, Mapping) or not isinstance(preview, list):
        raise RuntimeError("An Assembly simulation has no authenticated trace summary.")
    data = dict(data)
    motion_names = [str(name) for name in list(data.get("motion_outputs") or [])]
    motion_objects = []
    for name in motion_names:
        motion = outputs.get(name)
        if motion is None or str(getattr(motion, "TypeId", "")) != "App::FeaturePython":
            raise RuntimeError(
                f"Assembly simulation {item['name']!r} motion {name!r} is unavailable."
            )
        motion_objects.append(motion)
    if not isinstance(getattr(obj, "Proxy", None), AssemblySimulationProxy):
        AssemblySimulationProxy(obj)
    else:
        _ensure_assembly_simulation_properties(obj)
    parameters = data.get("parameters")
    if not isinstance(parameters, Mapping):
        raise RuntimeError("An Assembly simulation has no validated parameters.")
    obj.aTimeStart = float(parameters["start_time_s"])
    obj.bTimeEnd = float(parameters["end_time_s"])
    obj.cTimeStepOutput = float(parameters["time_step_s"])
    obj.fGlobalErrorTolerance = float(parameters["error_tolerance"])
    obj.jFramesPerSecond = int(parameters["frames_per_second"])
    obj.Group = motion_objects
    observed_group = list(getattr(obj, "Group", []) or [])
    observed_parameters = (
        float(getattr(obj.aTimeStart, "Value", obj.aTimeStart)),
        float(getattr(obj.bTimeEnd, "Value", obj.bTimeEnd)),
        float(getattr(obj.cTimeStepOutput, "Value", obj.cTimeStepOutput)),
        float(obj.fGlobalErrorTolerance),
        int(obj.jFramesPerSecond),
    )
    expected_parameters = (
        float(parameters["start_time_s"]),
        float(parameters["end_time_s"]),
        float(parameters["time_step_s"]),
        float(parameters["error_tolerance"]),
        int(parameters["frames_per_second"]),
    )
    if observed_group != motion_objects or any(
        not math.isclose(observed, expected, rel_tol=1.0e-12, abs_tol=1.0e-12)
        for observed, expected in zip(
            observed_parameters[:4], expected_parameters[:4], strict=True
        )
    ) or observed_parameters[4] != expected_parameters[4]:
        raise RuntimeError(
            f"Live Assembly simulation {item['name']!r} changed its validated settings."
        )
    for property_type, name, value, description in (
        (
            "App::PropertyInteger",
            "CadexFrameCount",
            int(data["frame_count"]),
            "Authenticated native simulation frame count.",
        ),
        (
            "App::PropertyInteger",
            "CadexPoseCount",
            int(data["pose_count"]),
            "Authenticated component-placement sample count.",
        ),
        (
            "App::PropertyString",
            "CadexTraceSHA256",
            str(data["artifact_sha256"]),
            "SHA-256 of the retained complete native simulation trace.",
        ),
    ):
        _add_property(obj, property_type, name, description)
        setattr(obj, name, value)
    _add_string_property(
        obj,
        "CadexAssemblySimulationValidation",
        "Authenticated native Assembly simulation settings, motion effects, and trace identity.",
    )
    obj.CadexAssemblySimulationValidation = json.dumps(
        data,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    _add_string_property(
        obj,
        "CadexSimulationTracePreview",
        "Input, middle, and final authenticated trace frames; the complete trace is retained as a program artifact.",
    )
    obj.CadexSimulationTracePreview = json.dumps(
        preview,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _configure_assembly_mjcf(obj: Any, item: Mapping[str, Any]) -> None:
    """Publish one exported MuJoCo model's authenticated identity (ADR-066).

    Everything here is worker-computed and re-read after assignment, the
    same discipline ``_configure_assembly_simulation`` follows: this
    publishes facts about a file that already exists, and never recomputes
    one. The digest is the file's identity and the counts are what a reader
    checks it against without opening it.

    ``mujoco_version`` is published for hazard 3's sake. An exported file's
    bytes are in no project digest -- ``compute_project_digest`` hashes an
    output's canonical definition JSON for anything that is not ``brep`` or
    ``mesh`` -- so a MuJoCo release changes every exported model silently.
    ADR-064 routed the real fix to ``main`` because the digest code is
    shared with the kinematics trace; until then the drift is at least
    legible here.
    """

    data = item.get("assembly_data")
    if not isinstance(data, Mapping):
        raise RuntimeError("An Assembly MJCF export has no authenticated summary.")
    data = dict(data)
    evidence = data.get("mjcf")
    if not isinstance(evidence, Mapping):
        raise RuntimeError("An Assembly MJCF export has no verification evidence.")
    evidence = dict(evidence)
    if not isinstance(getattr(obj, "Proxy", None), AssemblyMjcfProxy):
        AssemblyMjcfProxy(obj)
    else:
        _ensure_assembly_mjcf_properties(obj)

    obj.aKeyframe = str(evidence["keyframe"])
    obj.bGravity = [float(value) for value in evidence["gravity_m_s2"]]
    obj.cSolverStep = float(evidence["solver_step_s"])
    if (
        str(obj.aKeyframe) != str(evidence["keyframe"])
        or [float(value) for value in obj.bGravity]
        != [float(value) for value in evidence["gravity_m_s2"]]
        or not math.isclose(
            float(obj.cSolverStep),
            float(evidence["solver_step_s"]),
            rel_tol=1.0e-12,
            abs_tol=1.0e-15,
        )
    ):
        raise RuntimeError(
            f"Live Assembly MJCF export {item['name']!r} changed its validated "
            "settings."
        )

    for property_type, name, value, description in (
        (
            "App::PropertyString",
            "CadexMjcfSHA256",
            str(data["artifact_sha256"]),
            "SHA-256 of the retained exported MuJoCo model.",
        ),
        (
            "App::PropertyInteger",
            "CadexMjcfBytes",
            int(data["artifact_bytes"]),
            "Size of the retained exported MuJoCo model, in bytes.",
        ),
        (
            "App::PropertyInteger",
            "CadexMjcfBodyCount",
            int(evidence["body_count"]),
            "Bodies in the exported model, world included.",
        ),
        (
            "App::PropertyInteger",
            "CadexMjcfJointCount",
            int(evidence["joint_count"]),
            "Joints in the exported model.",
        ),
        (
            "App::PropertyInteger",
            "CadexMjcfActuatorCount",
            int(evidence["actuator_count"]),
            "Actuators in the exported model.",
        ),
        (
            "App::PropertyInteger",
            "CadexMjcfGeomCount",
            int(evidence["geom_count"]),
            "Collision geoms in the exported model; an export carries no visual ones.",
        ),
        (
            "App::PropertyString",
            "CadexMjcfMuJoCoVersion",
            str(evidence["mujoco_version"]),
            "The MuJoCo release that wrote the exported model.",
        ),
    ):
        _add_property(obj, property_type, name, description)
        setattr(obj, name, value)
        observed = getattr(obj, name)
        expected = value
        if isinstance(expected, int) and not isinstance(expected, bool):
            observed = int(observed)
        else:
            observed = str(observed)
        if observed != expected:
            raise RuntimeError(
                f"Live Assembly MJCF export {item['name']!r} changed {name}."
            )
    _add_string_property(
        obj,
        "CadexAssemblyMjcfValidation",
        "Authenticated exported MuJoCo model identity, settings, and verification "
        "evidence.",
    )
    obj.CadexAssemblyMjcfValidation = json.dumps(
        data,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _configure_assembly_exploded_view(
    doc: Any,
    obj: Any,
    item: Mapping[str, Any],
    outputs: Mapping[str, Any],
    prepared: Mapping[str, Any],
) -> None:
    """Publish only authenticated native view settings; never calculate geometry."""

    data = item.get("assembly_data")
    if not isinstance(data, Mapping):
        raise RuntimeError("An Assembly exploded view has no authenticated native data.")
    data = dict(data)
    assembly_name = str(data.get("assembly_output") or "")
    assembly = outputs.get(assembly_name)
    if assembly is None or str(getattr(assembly, "TypeId", "")) != (
        "Assembly::AssemblyObject"
    ):
        raise RuntimeError(
            f"Assembly exploded view {item['name']!r} assembly "
            f"{assembly_name!r} is unavailable."
        )
    moves = data.get("moves")
    if not isinstance(moves, list) or not 1 <= len(moves) <= 64:
        raise RuntimeError(
            f"Assembly exploded view {item['name']!r} has no bounded move graph."
        )
    try:
        import CommandCreateView
    except Exception as exc:
        raise RuntimeError(
            f"Native Assembly exploded-view API is unavailable: {exc}"
        ) from exc
    if type(getattr(obj, "Proxy", None)).__name__ != "ExplodedView":
        CommandCreateView.ExplodedView(obj)
    elif "Group" not in _properties(obj):
        obj.addExtension("App::GroupExtensionPython")

    view_name = str(item["name"])
    prefix = f"{view_name}.move."
    program_objects = _program_objects(
        doc,
        str(prepared["program_id"]),
        prepared["pack"].domain,
    )
    existing_steps: dict[str, Any] = {}
    for candidate in program_objects:
        output_key = str(
            getattr(candidate, contracts.PROP_PROGRAM_OUTPUT, "") or ""
        )
        if not output_key.startswith(prefix):
            continue
        if output_key in existing_steps:
            raise RuntimeError(
                f"Multiple managed exploded-view moves claim identity {output_key!r}."
            )
        existing_steps[output_key] = candidate
    foreign_group_members = [
        child
        for child in list(getattr(obj, "Group", []) or [])
        if existing_steps.get(
            str(getattr(child, contracts.PROP_PROGRAM_OUTPUT, "") or "")
        )
        is not child
    ]
    if foreign_group_members:
        names = [str(getattr(child, "Name", "") or "") for child in foreign_group_members]
        raise RuntimeError(
            f"Assembly exploded view {view_name!r} contains unmanaged move objects "
            f"{names}; remove them or use a separate human-authored view before "
            "regenerating this program."
        )

    desired_steps: list[Any] = []
    desired_keys: set[str] = set()
    for move_index, move in enumerate(moves):
        if not isinstance(move, Mapping):
            raise RuntimeError(
                f"Assembly exploded view {view_name!r} move {move_index} is malformed."
            )
        kind = str(move.get("kind") or "")
        if kind not in {"normal", "radial"}:
            raise RuntimeError(
                f"Assembly exploded view {view_name!r} move {move_index} has "
                f"unsupported kind {kind!r}."
            )
        key = f"{prefix}{move_index:03d}"
        desired_keys.add(key)
        step = existing_steps.get(key)
        if step is None:
            step = assembly.newObject(
                "App::FeaturePython",
                _SAFE_NAME.sub("_", f"{view_name}_Move_{move_index + 1}"),
            )
            if step is None:
                raise RuntimeError(
                    f"FreeCAD did not create exploded-view move {move_index}."
                )
        elif str(getattr(step, "TypeId", "")) != "App::FeaturePython":
            raise RuntimeError(
                f"Stable exploded-view move {key!r} changed native type."
            )
        if type(getattr(step, "Proxy", None)).__name__ != "ExplodedViewStep":
            CommandCreateView.ExplodedViewStep(step, 1 if kind == "radial" else 0)
        step.MoveType = "Radial" if kind == "radial" else "Normal"
        movement = move.get("movement_transform")
        if not isinstance(movement, Mapping):
            raise RuntimeError(
                f"Assembly exploded view {view_name!r} move {move_index} has no "
                "authenticated movement transform."
            )
        step.MovementTransform = _placement_from_matrix(movement.get("matrix"))
        component_names = [
            str(name) for name in list(move.get("component_outputs") or [])
        ]
        component_objects = []
        reference_paths = []
        for component_name in component_names:
            component = outputs.get(component_name)
            if component is None or str(getattr(component, "TypeId", "")) not in {
                "App::Link",
                "Assembly::AssemblyLink",
            }:
                raise RuntimeError(
                    f"Assembly exploded view {view_name!r} move {move_index} "
                    f"component {component_name!r} is unavailable."
                )
            component_objects.append(component)
            reference_paths.append(f"{component.Name}.")
        if not component_objects:
            raise RuntimeError(
                f"Assembly exploded view {view_name!r} move {move_index} is empty."
            )
        step.References = [assembly, reference_paths]
        step.Label = f"{_label(item, view_name)} / Move {move_index + 1}"
        readback = getattr(step, "References", None)
        if (
            not isinstance(readback, (list, tuple))
            or len(readback) < 2
            or readback[0] is not assembly
            or list(readback[1]) != reference_paths
            or str(step.MoveType) != ("Radial" if kind == "radial" else "Normal")
        ):
            raise RuntimeError(
                f"Live exploded-view move {key!r} changed its validated references."
            )
        expected_placement = _placement_from_matrix(movement.get("matrix"))
        if any(
            not math.isclose(left, right, rel_tol=1.0e-10, abs_tol=1.0e-9)
            for left, right in zip(
                _matrix_values(step.MovementTransform),
                _matrix_values(expected_placement),
                strict=True,
            )
        ):
            raise RuntimeError(
                f"Live exploded-view move {key!r} changed its validated transform."
            )
        _set_metadata(
            step,
            prepared,
            key,
            "exploded_view_step",
            {
                "operation": "exploded_view_move",
                "parent_output": view_name,
                "move_index": move_index,
                "kind": kind,
                "component_outputs": component_names,
            },
        )
        desired_steps.append(step)

    surplus = [
        candidate
        for key, candidate in existing_steps.items()
        if key not in desired_keys
    ]
    if surplus:
        view_group = _assembly_view_group(assembly)
        internal = list(program_objects)
        if view_group is not None:
            internal.append(view_group)
        external = _external_uses(doc, surplus, internal)
        if external:
            raise _reference_error(
                f"Cannot shorten exploded view {view_name!r}; human-created or "
                "foreign objects reference retired move identities",
                external,
            )
    obj.Group = desired_steps
    if list(getattr(obj, "Group", []) or []) != desired_steps:
        raise RuntimeError(
            f"Live Assembly exploded view {view_name!r} changed its validated move order."
        )
    if surplus:
        _remove_owned_objects(doc, surplus)
    _add_string_property(
        obj,
        "CadexAssemblyExplodedViewValidation",
        "Authenticated native exploded-view moves, placements, lines, and source bounds.",
    )
    obj.CadexAssemblyExplodedViewValidation = json.dumps(
        data,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _matrix_values(placement: Any) -> list[float]:
    matrix = placement.toMatrix()
    return [
        float(getattr(matrix, name))
        for name in (
            "A11",
            "A12",
            "A13",
            "A14",
            "A21",
            "A22",
            "A23",
            "A24",
            "A31",
            "A32",
            "A33",
            "A34",
            "A41",
            "A42",
            "A43",
            "A44",
        )
    ]


def _assert_matrix(actual: Any, expected: Any, label: str) -> None:
    observed = _matrix_values(actual)
    requested = _matrix_values(expected)
    if any(
        not math.isclose(left, right, rel_tol=1.0e-9, abs_tol=1.0e-9)
        for left, right in zip(observed, requested)
    ):
        raise RuntimeError(f"Published {label} changed its validated placement.")


def _configure_sketch(doc: Any, obj: Any, item: Mapping[str, Any]) -> None:
    import FreeCAD as App

    from cadex_sketcher_worker import (
        populate_sketch_without_solving,
        sketch_external_reference_records,
        sketch_expression_map,
    )

    definition = _definition(item)
    properties = _definition_properties(item)
    validation = item.get("sketch_validation")
    if not isinstance(validation, dict):
        raise RuntimeError("A sketch output has no isolated solver validation.")
    support = properties.get("support")
    if hasattr(obj, "AttachmentSupport"):
        if support is None:
            obj.AttachmentSupport = None
        else:
            if not isinstance(support, dict):
                raise RuntimeError("Validated Sketch support is malformed.")
            support_validation = item.get("sketch_validation", {}).get("support")
            if not isinstance(support_validation, dict):
                raise RuntimeError("Validated Sketch support has no worker resolution.")
            target = _reference_target(doc, support.get("reference"), "Sketch support")
            subelements = [
                str(value)
                for value in list(support_validation.get("resolved_subelements") or [])
            ]
            obj.AttachmentSupport = (target, subelements)
    if properties.get("map_mode") is not None and hasattr(obj, "MapMode"):
        obj.MapMode = str(properties["map_mode"])
    attachment = properties.get("attachment_offset")
    if attachment is not None and hasattr(obj, "AttachmentOffset"):
        if not isinstance(attachment, dict):
            raise RuntimeError("Validated Sketch attachment offset is malformed.")
        position = list(attachment.get("position") or [])
        rotation = list(attachment.get("rotation") or [])
        if len(position) != 3 or len(rotation) != 4:
            raise RuntimeError(
                "Validated Sketch attachment offset has the wrong dimensions."
            )
        obj.AttachmentOffset = App.Placement(
            App.Vector(*(float(value) for value in position)),
            App.Rotation(*(float(value) for value in rotation)),
        )

    external_by_graph = {
        str(value.get("graph_id") or ""): dict(value)
        for value in list(validation.get("external_geometry") or [])
        if isinstance(value, dict) and str(value.get("graph_id") or "")
    }

    def resolve_external(value: Mapping[str, Any]) -> tuple[Any, str, dict[str, Any]]:
        definition_properties = value.get("properties")
        if not isinstance(definition_properties, Mapping):
            raise RuntimeError("Validated external geometry properties are malformed.")
        graph_id = str(definition_properties.get("graph_id") or "")
        expected = external_by_graph.get(graph_id)
        if expected is None:
            raise RuntimeError(
                f"External Sketcher geometry {graph_id!r} has no worker resolution."
            )
        target = _reference_target(
            doc,
            expected.get("reference"),
            f"External Sketcher geometry {graph_id}",
        )
        subelement = str(expected.get("resolved_subelement") or "")
        if not re.fullmatch(r"(?:Edge|Vertex)[1-9][0-9]*", subelement):
            raise RuntimeError(
                f"External Sketcher geometry {graph_id!r} resolved an invalid subelement."
            )
        return target, subelement, dict(expected)

    geometry, constraints, _geometry_indexes, published_external = (
        populate_sketch_without_solving(
            obj,
            definition,
            replace_existing=True,
            external_resolver=resolve_external,
        )
    )
    if published_external != list(validation.get("external_geometry") or []):
        raise RuntimeError(
            "Published Sketcher external geometry differs from worker validation."
        )
    if int(getattr(obj, "GeometryCount", -1)) != int(
        validation.get("native_geometry_count", -2)
    ):
        raise RuntimeError(
            "Published Sketcher geometry count differs from worker validation."
        )
    external_references = sketch_external_reference_records(obj)
    if len(external_references) != int(validation.get("external_geometry_count", -1)):
        raise RuntimeError(
            "Published Sketcher external geometry count differs from worker validation."
        )
    unmatched_references = list(external_references)
    for index, expected in enumerate(published_external):
        expected_target = _reference_target(
            doc,
            expected.get("reference"),
            f"External Sketcher geometry {index}",
        )
        expected_subelement = str(expected.get("resolved_subelement") or "")
        match = next(
            (
                record
                for record in unmatched_references
                if record[0] is expected_target and record[1] == expected_subelement
            ),
            None,
        )
        if match is None:
            raise RuntimeError(
                f"Published Sketcher external geometry {index} changed its native link."
            )
        unmatched_references.remove(match)
    if unmatched_references:
        raise RuntimeError(
            "Published Sketcher external geometry has undeclared native links."
        )
    if int(getattr(obj, "ConstraintCount", -1)) != len(constraints):
        raise RuntimeError(
            "Published Sketcher constraint count differs from worker validation."
        )
    expression_bindings = sketch_expression_map(obj)
    for index, expected in enumerate(list(validation.get("constraints") or [])):
        native = obj.Constraints[index]
        if str(getattr(native, "Type", "") or "") != str(
            expected.get("native_type") or ""
        ):
            raise RuntimeError(
                f"Published Sketcher constraint {index} changed native type."
            )
        if str(getattr(native, "Name", "") or "") != str(expected.get("name") or ""):
            raise RuntimeError(f"Published Sketcher constraint {index} changed name.")
        if bool(getattr(native, "Driving", True)) != bool(
            expected.get("driving", True)
        ):
            raise RuntimeError(
                f"Published Sketcher constraint {index} changed driving state."
            )
        if bool(getattr(native, "IsActive", True)) != bool(
            expected.get("active", True)
        ):
            raise RuntimeError(
                f"Published Sketcher constraint {index} changed active state."
            )
        if bool(getattr(native, "InVirtualSpace", False)) != bool(
            expected.get("virtual", False)
        ):
            raise RuntimeError(
                f"Published Sketcher constraint {index} changed virtual state."
            )
        expression_bound = f"Constraints[{index}]" in expression_bindings
        if expression_bound != bool(expected.get("expression_bound")):
            raise RuntimeError(
                f"Published Sketcher constraint {index} changed expression binding."
            )
    _add_string_property(
        obj,
        "CadexSketchValidation",
        "Isolated Sketcher solver, DoF, conflict, and profile diagnostics.",
    )
    obj.CadexSketchValidation = json.dumps(
        validation,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _configure_solver_diagnostics(obj: Any, item: Mapping[str, Any]) -> None:
    diagnostics = item.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise RuntimeError("A solver diagnostics output has no validated diagnostics.")
    _add_string_property(obj, "CadexSolverStatus", "Isolated native solver status.")
    _add_property(
        obj,
        "App::PropertyInteger",
        "CadexSolverCode",
        "Native solver return code from the isolated worker.",
    )
    _add_property(
        obj,
        "App::PropertyInteger",
        "CadexJointCount",
        "Validated joint count in the isolated assembly.",
    )
    _add_property(
        obj,
        "App::PropertyInteger",
        "CadexComponentCount",
        "Validated component count in the isolated assembly.",
    )
    _add_string_property(
        obj,
        "CadexSolverDiagnostics",
        "Complete bounded isolated solver diagnostics as JSON.",
    )
    obj.CadexSolverStatus = str(diagnostics.get("status") or "")
    obj.CadexSolverCode = int(diagnostics.get("solver_code") or 0)
    obj.CadexJointCount = int(diagnostics.get("joint_count") or 0)
    obj.CadexComponentCount = int(diagnostics.get("component_count") or 0)
    obj.CadexSolverDiagnostics = json.dumps(
        diagnostics,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _remove_failed_domain_creations(doc: Any, object_names: list[str]) -> list[str]:
    """Remove live objects created before a domain publication failure."""

    leftovers = [doc.getObject(name) for name in object_names]
    return _remove_owned_objects(doc, [obj for obj in leftovers if obj is not None])


def _mesh_assigned_facts(mesh: Any) -> dict[str, Any]:
    box = mesh.BoundBox
    return {
        "points": int(mesh.CountPoints),
        "facets": int(mesh.CountFacets),
        "edges": int(mesh.CountEdges),
        "area_mm2": float(mesh.Area),
        "volume_mm3": float(mesh.Volume),
        "bounds": [
            float(box.XMin),
            float(box.YMin),
            float(box.ZMin),
            float(box.XMax),
            float(box.YMax),
            float(box.ZMax),
        ],
    }


def _mesh_local_facts(mesh: Any) -> dict[str, Any]:
    """Inspect the assigned kernel independently of its document Placement."""

    import FreeCAD as App

    local = mesh.copy()
    local.Placement = App.Placement()
    return _mesh_assigned_facts(local)


def _mesh_assigned_facts_match(
    observed: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> bool:
    if any(
        observed.get(key) != expected.get(key) for key in ("points", "facets", "edges")
    ):
        return False
    for key in ("area_mm2", "volume_mm3"):
        if not math.isclose(
            float(observed.get(key, math.nan)),
            float(expected.get(key, math.nan)),
            rel_tol=1.0e-9,
            abs_tol=1.0e-9,
        ):
            return False
    left = list(observed.get("bounds") or [])
    right = list(expected.get("bounds") or [])
    return len(left) == len(right) == 6 and all(
        math.isclose(float(first), float(second), rel_tol=1.0e-9, abs_tol=1.0e-9)
        for first, second in zip(left, right)
    )


def _configure_mesh(obj: Any, item: Mapping[str, Any]) -> None:
    if str(getattr(obj, "TypeId", "") or "") != "Mesh::Feature":
        raise RuntimeError("A stable Mesh output changed native type.")
    detached = item.get("detached_mesh")
    data = item.get("mesh_data")
    facts = item.get("facts")
    if detached is None or not isinstance(data, dict) or not isinstance(facts, dict):
        raise RuntimeError("A Mesh output has no validated detached native state.")
    import FreeCAD as App

    preserved_placement = App.Placement(obj.Placement)
    obj.Mesh = detached
    obj.Placement = preserved_placement
    expected = {
        "points": int(facts["points"]),
        "facets": int(facts["facets"]),
        "edges": int(facts["edges"]),
        "area_mm2": float(facts["area_mm2"]),
        "volume_mm3": float(facts["volume_mm3"]),
        "bounds": [
            *[float(value) for value in facts["bounds"]["minimum"]],
            *[float(value) for value in facts["bounds"]["maximum"]],
        ],
    }
    if not _mesh_assigned_facts_match(_mesh_local_facts(obj.Mesh), expected):
        raise RuntimeError(
            "Published native Mesh state differs from isolated worker validation."
        )
    _assert_matrix(obj.Placement, preserved_placement, "Mesh output placement")
    _add_string_property(
        obj,
        PROP_MESH_VALIDATION,
        "Validated isolated native mesh topology and conversion diagnostics.",
    )
    setattr(
        obj,
        PROP_MESH_VALIDATION,
        json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
    )


def _mesh_rollback_states(objects: list[Any]) -> list[dict[str, Any]]:
    states = []
    for obj in objects:
        if str(getattr(obj, "TypeId", "") or "") != "Mesh::Feature":
            continue
        property_names = list(getattr(obj, "PropertiesList", []) or [])
        if len(property_names) > _MAX_MESH_ROLLBACK_PROPERTIES:
            raise RuntimeError(
                f"Mesh object {obj.Name!r} has {len(property_names)} properties; "
                f"the rollback limit is {_MAX_MESH_ROLLBACK_PROPERTIES}."
            )
        properties = {}
        property_bytes = 0
        for name in property_names:
            if name in {"Mesh", "ExpressionEngine"}:
                continue
            try:
                content = bytes(obj.dumpPropertyContent(name))
            except Exception as exc:
                raise RuntimeError(
                    f"Mesh object {obj.Name!r} property {name!r} cannot be captured "
                    f"for rollback: {type(exc).__name__}: {exc}"
                ) from exc
            property_bytes += len(content)
            if property_bytes > _MAX_MESH_ROLLBACK_PROPERTY_BYTES:
                raise RuntimeError(
                    f"Mesh object {obj.Name!r} rollback properties exceed "
                    f"{_MAX_MESH_ROLLBACK_PROPERTY_BYTES} serialized bytes."
                )
            properties[name] = {
                "type": str(obj.getTypeIdOfProperty(name) or ""),
                "group": str(obj.getGroupOfProperty(name) or ""),
                "documentation": str(obj.getDocumentationOfProperty(name) or ""),
                "editor_modes": list(obj.getEditorMode(name) or []),
                "content": content,
            }
        missing_managed = [
            name
            for name in _MESH_ROLLBACK_PROPERTIES
            if name in _properties(obj) and name not in properties
        ]
        if missing_managed:
            raise RuntimeError(
                f"Mesh object {obj.Name!r} managed properties were not captured: "
                f"{missing_managed}."
            )
        states.append(
            {
                "document": obj.Document,
                "name": str(obj.Name),
                "label": str(obj.Label),
                "mesh": obj.Mesh.copy(),
                "facts": _mesh_assigned_facts(obj.Mesh),
                "properties": properties,
                "expressions": [
                    [str(path), str(expression)]
                    for path, expression in list(obj.ExpressionEngine or [])
                ],
            }
        )
    return states


def _restore_mesh_rollback_states(states: list[dict[str, Any]]) -> list[str]:
    failures = []
    restored = []
    resolved = []
    for state in states:
        document = state["document"]
        name = str(state["name"])
        obj = document.getObject(name)
        try:
            if obj is None:
                obj = document.addObject("Mesh::Feature", name)
            if (
                obj is None
                or str(obj.Name) != name
                or str(obj.TypeId) != "Mesh::Feature"
            ):
                raise RuntimeError("native Mesh identity could not be restored")
            for property_name, captured in state["properties"].items():
                if property_name not in _properties(obj):
                    obj.addProperty(
                        str(captured["type"]),
                        property_name,
                        str(captured["group"]),
                        str(captured["documentation"]),
                    )
            resolved.append((obj, state))
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    for obj, state in resolved:
        name = str(state["name"])
        try:
            for property_name, captured in state["properties"].items():
                obj.restorePropertyContent(
                    property_name,
                    bytearray(captured["content"]),
                )
                for mode in list(captured["editor_modes"]):
                    obj.setPropertyStatus(property_name, str(mode))
            for path, _expression in list(obj.ExpressionEngine or []):
                obj.setExpression(str(path).lstrip("."), None)
            for path, expression in state["expressions"]:
                obj.setExpression(str(path).lstrip("."), str(expression))
            obj.Label = str(state["label"])
            obj.Mesh = state["mesh"].copy()
            if [
                [str(path), str(expression)]
                for path, expression in list(obj.ExpressionEngine or [])
            ] != state["expressions"]:
                raise RuntimeError(
                    "restored Mesh expressions do not match accepted state"
                )
            if not _mesh_assigned_facts_match(
                _mesh_assigned_facts(obj.Mesh), state["facts"]
            ):
                raise RuntimeError("restored native Mesh does not match accepted state")
            restored.append(name)
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError(
            "Mesh operation failed and accepted assigned state could not be fully "
            f"restored: {'; '.join(failures)}"
        )
    return restored


def _configure_object(
    doc: Any,
    obj: Any,
    item: Mapping[str, Any],
    outputs: Mapping[str, Any],
    prepared: Mapping[str, Any],
) -> None:
    output_type = str(item["type"])
    if prepared["pack"].domain == "mesh":
        _configure_mesh(obj, item)
    elif output_type == "sketch":
        _configure_sketch(doc, obj, item)
    elif output_type in _BREP_OUTPUT_TYPES:
        obj.Shape = item["detached_shape"]
    elif output_type == "mesh":
        obj.Mesh = item["detached_mesh"]
    elif output_type == "component_link":
        _configure_component(doc, obj, item, outputs, prepared)
    elif output_type == "joint":
        _configure_joint(obj, item, outputs, prepared)
    elif prepared["pack"].domain == "assembly" and output_type == "motion":
        _configure_assembly_motion(obj, item, outputs)
    elif prepared["pack"].domain == "assembly" and output_type == "simulation":
        _configure_assembly_simulation(obj, item, outputs)
    elif prepared["pack"].domain == "assembly" and output_type == "mjcf":
        _configure_assembly_mjcf(obj, item)
    elif prepared["pack"].domain == "assembly" and output_type == "exploded_view":
        _configure_assembly_exploded_view(doc, obj, item, outputs, prepared)
    elif output_type == "solver_diagnostics":
        _configure_solver_diagnostics(obj, item)


def _surface_still_matches(service: Any, prepared: Mapping[str, Any]) -> None:
    from CadexModelingSurface import resolve_service_surface

    live = resolve_service_surface(service, service.active_workbench_name())
    if not live.available:
        raise RuntimeError(
            live.unavailable_reason
            or "The live modeling surface is unavailable for domain publication."
        )
    expected = prepared["surface"]
    observed_tuple = (live.workbench, live.engine, live.surface_id)
    expected_tuple = (
        str(expected.get("workbench") or ""),
        str(expected.get("engine") or ""),
        str(expected.get("surface_id") or ""),
    )
    if observed_tuple != expected_tuple:
        raise RuntimeError(
            "The workbench or modeling engine changed while the domain worker ran."
        )


def _assembly_model_evidence(item: Mapping[str, Any]) -> dict[str, Any] | None:
    """Keep accepted Assembly evidence useful without exposing generated names."""

    data = item.get("assembly_data")
    if not isinstance(data, Mapping):
        return None
    output_type = str(item.get("type") or "")
    if output_type == "component_link":
        raw_states = list(data.get("solved_occurrences") or [])
        states = [
            {
                key: state.get(key)
                for key in (
                    "occurrence_path",
                    "source_kind",
                    "source_label",
                    "native_target_mode",
                    "live_occurrence",
                    "local_placement",
                    "global_placement",
                )
                if key in state
            }
            for state in raw_states[:128]
            if isinstance(state, Mapping)
        ]
        paths = [str(path) for path in list(data.get("occurrence_paths") or [])]
        return {
            "assembly_output": str(data.get("assembly_output") or ""),
            "source": dict(data.get("source") or {}),
            "source_kind": str(data.get("source_kind") or ""),
            "grounded": bool(data.get("grounded")),
            "flexible": bool(data.get("flexible")),
            "hierarchy_sha256": str(data.get("hierarchy_sha256") or ""),
            "occurrence_path_count": int(data.get("occurrence_path_count", 0)),
            "occurrence_paths": paths[:256],
            "occurrence_paths_truncated": len(paths) > 256,
            "occurrence_paths_omitted": max(0, len(paths) - 256),
            "solved_placement": dict(data.get("solved_placement") or {}),
            "solved_occurrences": states,
            "solved_occurrences_truncated": len(raw_states) > len(states),
            "solved_occurrences_omitted": max(0, len(raw_states) - len(states)),
        }
    if output_type == "joint":
        connectors = []
        for connector in list(data.get("connectors") or []):
            if not isinstance(connector, Mapping):
                continue
            connectors.append(
                {
                    key: connector.get(key)
                    for key in (
                        "component_output",
                        "occurrence_path",
                        "selection",
                        "semantic_selection",
                        "geometry_type",
                        "offset",
                        "local_frame",
                        "global_frame",
                    )
                    if key in connector
                }
            )
        return {
            "assembly_output": str(data.get("assembly_output") or ""),
            "kind": str(data.get("kind") or ""),
            "suppressed": bool(data.get("suppressed")),
            "parameters": dict(data.get("parameters") or {}),
            "length_limits_mm": data.get("length_limits_mm"),
            "angle_limits_degrees": data.get("angle_limits_degrees"),
            "connectors": connectors,
        }
    if output_type in {"assembly", "solver_diagnostics", "motion", "simulation"}:
        return dict(data)
    if output_type == "exploded_view":
        return {
            key: data.get(key)
            for key in (
                "schema",
                "assembly_output",
                "moves",
                "assembly_bounds",
                "final_component_placements",
                "line_count",
            )
            if key in data
        }
    return None


class _PartDesignShapeCarrier:
    """Detached validated shape presented to the shared publication service."""

    def __init__(self, item: Mapping[str, Any]) -> None:
        import FreeCAD as App

        self.Name = str(item["name"])
        self.Label = str(
            dict(item.get("partdesign_data") or {}).get("body_label")
            or item["name"]
        )
        self.Shape = item["detached_shape"]
        self.Placement = App.Placement()
        self.ViewObject = None

    def getGlobalPlacement(self) -> Any:
        return self.Placement


def _partdesign_program_root(doc: Any, program_id: str) -> Any | None:
    matches = []
    for obj in list(getattr(doc, "Objects", []) or []):
        properties = _properties(obj)
        v2_id = str(getattr(obj, contracts.PROP_PROGRAM_ID, "") or "")
        v1_id = str(getattr(obj, "CadexXScriptModelId", "") or "")
        publication_id = str(
            getattr(obj, scripted_publication.PROP_MODEL_ID, "") or ""
        )
        if program_id not in {v2_id, v1_id, publication_id}:
            continue
        if (
            scripted_publication.role_of(obj) == scripted_publication.ROLE_MODEL
            or (
                str(getattr(obj, "TypeId", "") or "") == "App::Part"
                and not str(
                    getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or ""
                )
                and not str(
                    getattr(obj, "CadexXScriptOutputKey", "") or ""
                )
            )
        ):
            matches.append(obj)
    unique = {str(obj.Name): obj for obj in matches}
    if len(unique) > 1:
        raise RuntimeError(
            f"Multiple Part Design program roots claim id {program_id}: "
            f"{sorted(unique)}."
        )
    return next(iter(unique.values()), None)


def _partdesign_publications(
    doc: Any,
    root: Any,
    program_id: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    candidates = [
        obj
        for obj in list(getattr(doc, "Objects", []) or [])
        if scripted_publication.is_publication(obj)
        and str(getattr(obj, scripted_publication.PROP_MODEL_ID, "") or "")
        == program_id
    ]
    candidates.extend(
        obj
        for obj in list(getattr(root, "Group", []) or [])
        if obj not in candidates
        and (
            scripted_publication.is_publication(obj)
            or "CadexXScriptOutputKey" in _properties(obj)
        )
    )
    for obj in candidates:
        output_name = str(
            getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "")
            or getattr(obj, scripted_publication.PROP_OUTPUT_KEY, "")
            or getattr(obj, "CadexXScriptOutputKey", "")
            or ""
        )
        if not output_name:
            continue
        if output_name in result and result[output_name] is not obj:
            raise RuntimeError(
                f"Multiple Part Design publications claim output {output_name!r}."
            )
        result[output_name] = obj
    return result


def _tag_partdesign_root(root: Any, prepared: Mapping[str, Any]) -> None:
    scripted_publication.tag_object(
        root,
        role=scripted_publication.ROLE_MODEL,
        engine="xscript:partdesign",
        model_id=str(prepared["program_id"]),
        revision=str(prepared["revision"]),
    )
    for name, description, value in (
        (
            contracts.PROP_PROGRAM_ID,
            "Stable XScript program id.",
            str(prepared["program_id"]),
        ),
        (
            contracts.PROP_PROGRAM_DOMAIN,
            "XScript workbench domain.",
            "partdesign",
        ),
        (
            contracts.PROP_PROGRAM_WORKBENCH,
            "Workbench owning this XScript program.",
            "PartDesignWorkbench",
        ),
        (
            contracts.PROP_PROGRAM_REVISION,
            "Accepted XScript program revision.",
            str(prepared["revision"]),
        ),
    ):
        _add_string_property(root, name, description)
        setattr(root, name, value)
    scripted_publication.ensure_string_property(
        root, scripted_publication.PROP_INTERFACES
    )


def _partdesign_interface_table(
    validated: Mapping[str, Any],
    publications: Mapping[str, Any],
) -> dict[str, Any]:
    table: dict[str, Any] = {}
    for item in list(validated.get("outputs") or []):
        output_name = str(item["name"])
        published = publications[output_name]
        data = item.get("partdesign_data")
        if not isinstance(data, Mapping):
            raise RuntimeError(
                f"Part Design output {output_name!r} has no interface evidence."
            )
        for raw_name, raw in dict(data.get("interfaces") or {}).items():
            name = str(raw_name)
            if name in table:
                raise RuntimeError(
                    f"Part Design semantic interface {name!r} is declared by more "
                    "than one output."
                )
            if not isinstance(raw, Mapping):
                raise RuntimeError(
                    f"Part Design semantic interface {name!r} is malformed."
                )
            table[name] = {
                "output": output_name,
                "selection": dict(raw.get("selection") or {}),
                **(
                    {"description": str(raw.get("description") or "")}
                    if raw.get("description")
                    else {}
                ),
                "resolved": {
                    "object": str(published.Name),
                    "subelements": list(raw.get("subelements") or []),
                    "geometry": list(raw.get("geometry") or []),
                },
            }
    return table


def _publish_partdesign_candidate(
    service: Any,
    prepared: Mapping[str, Any],
    validated: Mapping[str, Any],
    doc: Any,
    *,
    manage_transaction: bool = True,
) -> dict[str, Any]:
    """Publish one v2 Part Design candidate through the shared stable boundary.

    With ``manage_transaction=False`` no transaction is opened, committed, or
    aborted here; the caller owns exactly one enclosing transaction and
    exceptions propagate to it.
    """

    program_id = str(prepared["program_id"])
    root = _partdesign_program_root(doc, program_id)
    publications = (
        _partdesign_publications(doc, root, program_id) if root is not None else {}
    )
    previous_interfaces: dict[str, Any] = {}
    if root is not None:
        try:
            previous_interfaces = json.loads(
                str(
                    getattr(root, scripted_publication.PROP_INTERFACES, "{}")
                    or "{}"
                )
            )
        except ValueError as exc:
            raise RuntimeError(
                f"Part Design program {program_id} has invalid interface metadata: {exc}"
            ) from exc
        if not isinstance(previous_interfaces, dict):
            raise RuntimeError(
                f"Part Design program {program_id} has a non-object interface table."
            )
    existing_values = list(publications.values())
    reference_preflight = (
        reference_contracts.preflight_regeneration(
            service,
            existing_values,
            model_root=root,
        )
        if root is not None and existing_values
        else None
    )
    desired = {str(item["name"]) for item in validated["outputs"]}
    retired_names = sorted(set(publications) - desired)
    for name in retired_names:
        uses = scripted_publication.external_reference_uses(
            doc,
            [publications[name]],
            internal_objects=[root, *existing_values] if root is not None else existing_values,
        )
        if uses:
            raise _reference_error(
                f"Cannot retire Part Design XScript output {name!r} while "
                "downstream objects reference it",
                uses,
            )
    transaction_open = False
    created: list[str] = []
    removed: list[str] = []
    try:
        if manage_transaction and hasattr(doc, "openTransaction"):
            doc.openTransaction(
                f"Publish Part Design XScript: {prepared['program_name']}"
            )
            transaction_open = True
        if root is None:
            root = doc.addObject(
                "App::Part", _internal_name(prepared, "Program")
            )
            if root is None:
                raise RuntimeError("FreeCAD did not create the Part Design program root.")
            created.append(str(root.Name))
        root.Label = str(prepared["program_name"])
        _tag_partdesign_root(root, prepared)
        for name in retired_names:
            removed.extend(
                scripted_publication.delete_publication(
                    doc, root, publications.pop(name)
                )
            )
        for item in validated["outputs"]:
            name = str(item["name"])
            carrier = _PartDesignShapeCarrier(item)
            published = publications.get(name)
            if published is None:
                published = scripted_publication.create_publication(
                    doc,
                    root,
                    carrier,
                    internal_name=_internal_name(prepared, name),
                    label=carrier.Label,
                    engine="xscript:partdesign",
                    model_id=program_id,
                    output_key=name,
                    revision=str(prepared["revision"]),
                )
                publications[name] = published
                created.append(str(published.Name))
            else:
                scripted_publication.tag_object(
                    published,
                    role=scripted_publication.ROLE_PUBLICATION,
                    engine="xscript:partdesign",
                    model_id=program_id,
                    output_key=name,
                    revision=str(prepared["revision"]),
                )
                scripted_publication.update_publication(
                    published,
                    root,
                    carrier,
                    revision=str(prepared["revision"]),
                )
                published.Label = carrier.Label
            _set_metadata(
                published,
                prepared,
                name,
                "solid",
                _definition(item),
            )
        interface_table = _partdesign_interface_table(validated, publications)
        reference_contracts.validate_removed_interfaces(
            doc,
            list(publications.values()),
            program_id,
            set(previous_interfaces),
            set(interface_table),
            preflight=reference_preflight,
        )
        setattr(
            root,
            scripted_publication.PROP_INTERFACES,
            json.dumps(
                interface_table,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
        )
        downstream = reference_contracts.refresh_after_publication(
            service,
            program_id,
            list(publications.values()),
            revision=str(prepared["revision"]),
            preflight=reference_preflight,
        )
        if hasattr(doc, "commitTransaction") and transaction_open:
            doc.commitTransaction()
            transaction_open = False
    except Exception:
        if transaction_open and hasattr(doc, "abortTransaction"):
            doc.abortTransaction()
        raise
    live_outputs: dict[str, Any] = {}
    output_rows: list[dict[str, Any]] = []
    for item in validated["outputs"]:
        name = str(item["name"])
        published = publications[name]
        row = {
            "object_name": str(published.Name),
            "label": str(published.Label),
            "type_id": str(published.TypeId),
            "output_type": "solid",
            "facts": dict(item.get("facts") or {}),
            "partdesign_data": dict(item.get("partdesign_data") or {}),
            "derived_state": str(
                getattr(published, reference_contracts.PROP_DERIVED_STATE, "")
                or ""
            ),
            "stale_reason": str(
                getattr(published, reference_contracts.PROP_STALE_REASON, "")
                or ""
            ),
            "source_revision": str(
                getattr(published, reference_contracts.PROP_SOURCE_REVISION, "")
                or ""
            ),
        }
        live_outputs[name] = row
        output_rows.append({"name": name, **row})
    return {
        "ok": True,
        "outputs": output_rows,
        "live_outputs": live_outputs,
        "interfaces": interface_table,
        "created_objects": created,
        "retired_objects": removed,
        "downstream_references": downstream,
        "recompute_deferred": True,
        "stdout": str(validated.get("stdout") or ""),
        "budget": dict(validated.get("budget") or {}),
    }


def publish_candidate(
    service: Any,
    prepared: dict[str, Any],
    validated: dict[str, Any],
    *,
    manage_transaction: bool = True,
    check_surface: bool = True,
) -> dict[str, Any]:
    """Apply detached, validated values without process waits or artifact I/O.

    ``check_surface=False`` skips the workbench/engine surface match (project
    publication has no per-domain surface). ``manage_transaction=False`` opens
    no transaction and never commits or aborts; the caller owns exactly one
    enclosing transaction and exceptions propagate to it.
    """

    if check_surface:
        _surface_still_matches(service, prepared)
    doc = service._active_document()
    if doc is None or str(getattr(doc, "Name", "") or "") != prepared["document_name"]:
        raise RuntimeError("The active document changed while the domain worker ran.")
    if str(getattr(doc, "Uid", "") or "") != prepared["document_uid"]:
        raise RuntimeError(
            "The active document identity changed while the domain worker ran."
        )
    if manage_transaction and (
        str(service.provider_document_revision()) != prepared["document_revision"]
    ):
        # With manage_transaction=False the enclosing caller has already run
        # this guard and holds the one open transaction — whose booked id is
        # part of the revision token, so recomputing it here can never match.
        raise RuntimeError(
            "The document changed while the domain worker ran; regenerate on the live state."
        )
    if prepared["pack"].domain == "partdesign":
        return _publish_partdesign_candidate(
            service,
            prepared,
            validated,
            doc,
            manage_transaction=manage_transaction,
        )
    existing = _objects_by_output(doc, prepared)
    desired_output_names = {str(item["name"]) for item in validated["outputs"]}
    retired = _retired_program_objects(doc, prepared, desired_output_names)
    internal_objects = _program_objects(
        doc,
        str(prepared["program_id"]),
        prepared["pack"].domain,
    )
    if prepared["pack"].domain == "assembly":
        for candidate in list(internal_objects):
            if str(getattr(candidate, "TypeId", "")) != "Assembly::AssemblyObject":
                continue
            for group in (
                _assembly_joint_group(candidate),
                _assembly_simulation_group(candidate),
                _assembly_view_group(candidate),
            ):
                if group is not None and group not in internal_objects:
                    internal_objects.append(group)
    updated_objects = [
        existing[str(item["name"])]
        for item in validated["outputs"]
        if str(item["name"]) in existing
    ]
    if prepared["pack"].domain == "assembly":
        updated_names = {str(item["name"]) for item in validated["outputs"]}
        updated_objects.extend(
            obj
            for obj in internal_objects
            if ".move." in str(
                getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or ""
            )
            and str(
                getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or ""
            ).partition(".")[0]
            in updated_names
        )
    mesh_rollbacks = (
        _mesh_rollback_states(internal_objects)
        if prepared["pack"].domain == "mesh"
        else []
    )
    downstream_uses = _preflight_output_updates(
        doc,
        updated_objects,
        internal_objects,
    )
    outputs: dict[str, Any] = {}
    created: list[Any] = []
    removed: list[str] = []
    assembly_dependency_anchor: Any | None = None
    transaction_open = False
    try:
        if manage_transaction and hasattr(doc, "openTransaction"):
            doc.openTransaction(
                f"Publish {prepared['pack'].title} XScript: {prepared['program_name']}"
            )
            transaction_open = True
        assembly_item = next(
            (item for item in validated["outputs"] if item["type"] == "assembly"),
            None,
        )
        if assembly_item is not None:
            name = str(assembly_item["name"])
            assembly = existing.get(name)
            if assembly is None:
                assembly = _create_object(
                    doc, prepared, name, "assembly", _definition(assembly_item), None
                )
                created.append(assembly)
            elif str(getattr(assembly, "TypeId", "")) != "Assembly::AssemblyObject":
                raise RuntimeError("A stable assembly output changed native type.")
            outputs[name] = assembly
        assembly = next(
            (
                obj
                for obj in outputs.values()
                if obj.TypeId == "Assembly::AssemblyObject"
            ),
            None,
        )
        if prepared["pack"].domain == "assembly" and assembly_item is not None:
            assembly_output = str(assembly_item["name"])
            assembly_dependency_anchor = _find_assembly_dependency_anchor(
                doc,
                str(prepared["program_id"]),
                assembly_output,
            )
            if assembly_dependency_anchor is None:
                assembly_dependency_anchor = _create_assembly_dependency_anchor(
                    doc,
                    str(prepared["program_id"]),
                    assembly_output,
                )
                created.append(assembly_dependency_anchor)
        for item in validated["outputs"]:
            output_name = str(item["name"])
            output_type = str(item["type"])
            obj = outputs.get(output_name) or existing.get(output_name)
            if obj is None:
                obj = _create_object(
                    doc,
                    prepared,
                    output_name,
                    output_type,
                    _definition(item),
                    assembly,
                )
                created.append(obj)
            expected_native = (
                _component_native_type(doc, item)
                if output_type == "component_link"
                else _native_type(output_type)
            )
            if output_type == "component_link":
                compatible = str(getattr(obj, "TypeId", "")) == expected_native
            elif output_type == "joint":
                compatible = str(getattr(obj, "TypeId", "")) == "App::FeaturePython"
            else:
                compatible = str(getattr(obj, "TypeId", "")) == expected_native
            if not compatible:
                raise RuntimeError(
                    f"Stable output {output_name!r} cannot change from native type "
                    f"{getattr(obj, 'TypeId', '')!r} to {expected_native!r}."
                )
            outputs[output_name] = obj
        configure_order = list(validated["outputs"])
        if prepared["pack"].domain == "assembly":
            priority = {
                "assembly": 0,
                "component_link": 1,
                "joint": 2,
                "motion": 3,
                "simulation": 4,
                "exploded_view": 5,
                "solver_diagnostics": 6,
            }
            configure_order.sort(key=lambda item: priority.get(str(item["type"]), 7))
        for item in configure_order:
            output_name = str(item["name"])
            obj = outputs[output_name]
            obj.Label = _label(item, output_name)
            _configure_object(doc, obj, item, outputs, prepared)
            _set_metadata(
                obj,
                prepared,
                output_name,
                str(item["type"]),
                _definition(item),
            )
        if assembly_dependency_anchor is not None and assembly_item is not None:
            assembly_output = str(assembly_item["name"])
            assembly_dependency_anchor.Label = "XScript Assembly dependencies"
            view = getattr(assembly_dependency_anchor, "ViewObject", None)
            if view is not None:
                view.Visibility = False
                if hasattr(view, "ShowInTree"):
                    view.ShowInTree = False
            _set_metadata(
                assembly_dependency_anchor,
                prepared,
                _assembly_dependency_output_name(assembly_output),
                _ASSEMBLY_DEPENDENCY_OUTPUT_TYPE,
                _definition(assembly_item),
            )
        downstream_refresh = _refresh_external_consumers(
            downstream_uses,
            revision=str(prepared["revision"]),
        )
        removed = _remove_owned_objects(doc, retired)
        if hasattr(doc, "commitTransaction") and transaction_open:
            doc.commitTransaction()
            transaction_open = False
    except Exception as publication_error:
        created_names = [str(getattr(obj, "Name", "") or "") for obj in created]
        if transaction_open and hasattr(doc, "abortTransaction"):
            try:
                doc.abortTransaction()
            except Exception:
                pass
        if prepared["pack"].domain == "mesh":
            rollback_failures: list[str] = []
            if mesh_rollbacks:
                try:
                    _restore_mesh_rollback_states(mesh_rollbacks)
                except Exception as rollback_error:
                    rollback_failures.append(str(rollback_error))
            try:
                _remove_failed_domain_creations(
                    doc, [name for name in created_names if name]
                )
            except Exception as cleanup_error:
                rollback_failures.append(
                    "failed candidate objects could not be removed: "
                    f"{type(cleanup_error).__name__}: {cleanup_error}"
                )
            if rollback_failures:
                raise RuntimeError(
                    f"{publication_error} Explicit {prepared['pack'].title} "
                    "rollback failure: "
                    f"{' | '.join(rollback_failures)}"
                ) from publication_error
        raise
    live_outputs = {
        name: {
            "object_name": str(obj.Name),
            "label": str(obj.Label),
            "type_id": str(obj.TypeId),
            "output_type": str(getattr(obj, PROP_OUTPUT_TYPE, "") or ""),
            "derived_state": str(
                getattr(obj, reference_contracts.PROP_DERIVED_STATE, "") or ""
            ),
            "stale_reason": str(
                getattr(obj, reference_contracts.PROP_STALE_REASON, "") or ""
            ),
            "source_revision": str(
                getattr(obj, reference_contracts.PROP_SOURCE_REVISION, "") or ""
            ),
        }
        for name, obj in outputs.items()
    }
    for item in validated["outputs"]:
        name = str(item["name"])
        if isinstance(item.get("facts"), dict):
            live_outputs[name]["facts"] = dict(item["facts"])
        if isinstance(item.get("operation_diagnostics"), dict):
            live_outputs[name]["operation_diagnostics"] = dict(
                item["operation_diagnostics"]
            )
        if isinstance(item.get("mesh_data"), dict):
            live_outputs[name]["mesh_data"] = dict(item["mesh_data"])
        if prepared["pack"].domain == "assembly":
            evidence = _assembly_model_evidence(item)
            if evidence is not None:
                live_outputs[name]["assembly_data"] = evidence
    published_outputs = []
    for item in validated["outputs"]:
        name = str(item["name"])
        summary = {"name": name, **live_outputs[name]}
        if isinstance(item.get("diagnostics"), dict):
            summary["diagnostics"] = dict(item["diagnostics"])
        if isinstance(item.get("sketch_validation"), dict):
            summary["sketch_validation"] = dict(item["sketch_validation"])
        if isinstance(item.get("mesh_data"), dict):
            summary["mesh_data"] = dict(item["mesh_data"])
        published_outputs.append(summary)
    return {
        "ok": True,
        "outputs": published_outputs,
        "live_outputs": live_outputs,
        "created_objects": [str(obj.Name) for obj in created],
        "retired_objects": removed,
        "downstream_references": {
            "safe_whole_object_uses": scripted_publication.json_reference_uses(
                downstream_uses
            ),
            **downstream_refresh,
        },
        "recompute_deferred": True,
        "stdout": str(validated.get("stdout") or ""),
        "budget": dict(validated.get("budget") or {}),
    }


_PROJECT_PROGRAM_ID = "project"
_PROJECT_PROGRAM_NAME = "Project Script"
_PROJECT_DOMAIN_ORDER = ("sketcher", "part", "partdesign", "mesh", "assembly")


def _clone_output_item(item: Mapping[str, Any]) -> dict[str, Any]:
    """Deep copy of one validated output item, sharing its detached values.

    The plain JSON evidence is copied so per-domain rewrites never mutate the
    caller's validated result; the imported ``detached_shape``/``detached_mesh``
    (attached by validation, not deep-copyable) are shared by reference.
    """

    detached_keys = ("detached_shape", "detached_mesh")
    clone = copy.deepcopy(
        {key: value for key, value in dict(item).items() if key not in detached_keys}
    )
    for key in detached_keys:
        if key in item:
            clone[key] = item[key]
    return clone


def _rewrite_inline_source_refs(
    value: Any,
    document_uid: str,
    live_by_token: Mapping[str, str],
    context: str,
) -> None:
    """Rewrite worker inline-source tokens to live published object identities.

    The worker records same-script component sources as ``{document_uid:
    "xscript-project", object_name: <token>}``; publication resolves each
    token to the object just published for the declared source output.
    Mutates ``value`` (a deep copy of one validated output item) in place.
    """

    from cadex_project_api import INLINE_SOURCE_UID

    if isinstance(value, dict):
        if str(value.get("document_uid") or "") == INLINE_SOURCE_UID:
            token = str(value.get("object_name") or "")
            live_name = live_by_token.get(token)
            if not live_name:
                raise RuntimeError(
                    f"{context} references inline source {token!r} that no "
                    "published part/partdesign output provides."
                )
            value["document_uid"] = document_uid
            value["object_name"] = live_name
            return
        for child in value.values():
            _rewrite_inline_source_refs(child, document_uid, live_by_token, context)
    elif isinstance(value, list):
        for child in value:
            _rewrite_inline_source_refs(child, document_uid, live_by_token, context)


def _project_domain_prepared(
    prepared: Mapping[str, Any],
    pack: Any,
) -> dict[str, Any]:
    return {
        "tool_name": str(prepared.get("tool_name") or ""),
        "pack": pack,
        "program_id": _PROJECT_PROGRAM_ID,
        "program_name": _PROJECT_PROGRAM_NAME,
        "revision": str(prepared["revision"]),
        "staging": str(prepared["staging"]),
        "attempt_id": str(prepared.get("attempt_id") or ""),
        "document_name": str(prepared["document_name"]),
        "document_uid": str(prepared["document_uid"]),
        "document_revision": str(prepared["document_revision"]),
        "resolved_references": [],
    }


def publish_project_candidate(
    service: Any,
    prepared: dict[str, Any],
    validated: dict[str, Any],
) -> dict[str, Any]:
    """Publish ONE validated multi-domain project script under ONE transaction.

    Sub-publishes each capability domain that has outputs in the validated
    contract (sketcher -> part -> partdesign -> assembly) through the
    existing per-domain publishers with ``manage_transaction=False``, rewrites
    same-script assembly component sources to the live objects published in
    the same pass, garbage-collects owned objects whose outputs left the
    contract, and refuses to commit while any document object stays outside
    the project's owned closure (PUBLICATION_UNTAGGED_OBJECT).
    """

    import CadexScriptedOwnership as ownership

    doc = service._active_document()
    if doc is None or str(getattr(doc, "Name", "") or "") != prepared["document_name"]:
        raise RuntimeError("The active document changed while the project worker ran.")
    if str(getattr(doc, "Uid", "") or "") != prepared["document_uid"]:
        raise RuntimeError(
            "The active document identity changed while the project worker ran."
        )
    if str(service.provider_document_revision()) != prepared["document_revision"]:
        raise RuntimeError(
            "The document changed while the project worker ran; regenerate on the live state."
        )
    packs_by_domain = {
        pack.domain: pack for pack in contracts.XSCRIPT_WORKBENCH_PACKS.values()
    }
    contract = [dict(item) for item in list(validated.get("contract") or [])]
    items_by_domain: dict[str, list[Mapping[str, Any]]] = {}
    for item in list(validated.get("outputs") or []):
        items_by_domain.setdefault(str(item.get("domain") or ""), []).append(item)
    unsupported = sorted(set(items_by_domain) - set(_PROJECT_DOMAIN_ORDER))
    if unsupported:
        raise RuntimeError(
            f"Project outputs claim unsupported domains: {unsupported}."
        )
    component_sources = {
        str(token): str(output_name)
        for token, output_name in dict(
            validated.get("component_sources") or {}
        ).items()
    }
    outputs_map: dict[str, str] = {}
    live_outputs: dict[str, dict[str, Any]] = {}
    created: list[str] = []
    removed: list[str] = []
    transaction_open = False
    try:
        if hasattr(doc, "openTransaction"):
            doc.openTransaction("Publish Cadex project script")
            transaction_open = True
        for domain in _PROJECT_DOMAIN_ORDER:
            items = items_by_domain.get(domain) or []
            if not items:
                continue
            sub_prepared = _project_domain_prepared(prepared, packs_by_domain[domain])
            sub_items: list[dict[str, Any]] = []
            for item in items:
                clone = _clone_output_item(item)
                if (
                    str(clone.get("artifact_kind") or "") == "brep"
                    and clone.get("detached_shape") is None
                ):
                    raise RuntimeError(
                        f"Project output {clone.get('name')!r} has no detached "
                        "validated shape; run validate_project_result first."
                    )
                if (
                    str(clone.get("artifact_kind") or "") == "mesh"
                    and clone.get("detached_mesh") is None
                ):
                    raise RuntimeError(
                        f"Project output {clone.get('name')!r} has no detached "
                        "validated mesh; run validate_project_result first."
                    )
                sub_items.append(clone)
            if domain == "assembly":
                live_by_token: dict[str, str] = {}
                for token, output_name in component_sources.items():
                    live_name = outputs_map.get(output_name)
                    if not live_name:
                        raise RuntimeError(
                            f"Assembly component source output {output_name!r} was "
                            "not published before the assembly pass."
                        )
                    live_by_token[token] = live_name
                for clone in sub_items:
                    _rewrite_inline_source_refs(
                        clone,
                        str(getattr(doc, "Uid", "") or ""),
                        live_by_token,
                        f"Project output {clone.get('name')!r}",
                    )
            sub_validated = {
                "outputs": sub_items,
                "stdout": "",
                "budget": {},
            }
            result = publish_candidate(
                service,
                sub_prepared,
                sub_validated,
                manage_transaction=False,
                check_surface=False,
            )
            for name, row in dict(result.get("live_outputs") or {}).items():
                outputs_map[str(name)] = str(row.get("object_name") or "")
                live_outputs[str(name)] = {
                    "object_name": str(row.get("object_name") or ""),
                    "label": str(row.get("label") or ""),
                    "type_id": str(row.get("type_id") or ""),
                    "output_type": str(row.get("output_type") or ""),
                    "domain": domain,
                }
            created.extend(
                str(name) for name in list(result.get("created_objects") or [])
            )
            removed.extend(
                str(name) for name in list(result.get("retired_objects") or [])
            )
        # Orphan GC: whole domains (and any stragglers) whose outputs left the
        # accepted contract are removed inside the same transaction.
        orphans = ownership.orphaned_outputs(doc, _PROJECT_PROGRAM_ID, contract)
        removed.extend(_remove_owned_objects(doc, orphans))
        # Ownership lint: the project script is the sole source of truth, so
        # every remaining document object must be inside the owned closure.
        untagged = ownership.untagged_objects(doc, _PROJECT_PROGRAM_ID)
        if untagged:
            names = sorted(
                str(getattr(obj, "Name", "") or "") for obj in untagged
            )
            error = RuntimeError(
                "PUBLICATION_UNTAGGED_OBJECT: the document contains objects the "
                f"project script does not own: {names}. Delete them or model "
                "them in the project script, then publish again."
            )
            error.details = {  # type: ignore[attr-defined]
                "failure_code": "PUBLICATION_UNTAGGED_OBJECT",
                "untagged_objects": names,
            }
            raise error
        if transaction_open and hasattr(doc, "commitTransaction"):
            doc.commitTransaction()
            transaction_open = False
    except Exception:
        if transaction_open and hasattr(doc, "abortTransaction"):
            try:
                doc.abortTransaction()
            except Exception:
                pass
        raise
    return {
        "ok": True,
        "outputs": outputs_map,
        "live_outputs": live_outputs,
        "created": sorted(set(created)),
        "removed": removed,
        "recompute_deferred": True,
        "stdout": str(validated.get("stdout") or ""),
        "budget": dict(validated.get("budget") or {}),
    }


def _delete_partdesign_program(
    doc: Any,
    prepared: Mapping[str, Any],
) -> dict[str, Any]:
    program_id = str(prepared["program_id"])
    root = _partdesign_program_root(doc, program_id)
    if root is None:
        return {"ok": True, "deleted_objects": [], "recompute_deferred": True}
    publications = _partdesign_publications(doc, root, program_id)
    internal = [
        root,
        *list(getattr(root, "OutListRecursive", []) or []),
        *publications.values(),
    ]
    external = _external_uses(doc, list(publications.values()), internal)
    if external:
        raise _reference_error(
            "Cannot delete this Part Design XScript program while downstream "
            "objects reference its stable publications",
            external,
        )
    deleted: list[dict[str, Any]] = [
        {
            "object_name": str(obj.Name),
            "label": str(obj.Label),
            "type_id": str(obj.TypeId),
            "output_name": str(name),
        }
        for name, obj in publications.items()
    ]
    transaction_open = False
    try:
        if hasattr(doc, "openTransaction"):
            doc.openTransaction("Delete Part Design XScript program")
            transaction_open = True
        for published in list(publications.values()):
            scripted_publication.delete_publication(doc, root, published)
        for child in reversed(list(getattr(root, "Group", []) or [])):
            child_name = str(getattr(child, "Name", "") or "")
            if child_name and doc.getObject(child_name) is not None:
                doc.removeObject(child_name)
        root_name = str(root.Name)
        if doc.getObject(root_name) is not None:
            doc.removeObject(root_name)
        if hasattr(doc, "commitTransaction") and transaction_open:
            doc.commitTransaction()
            transaction_open = False
    except Exception:
        if transaction_open and hasattr(doc, "abortTransaction"):
            doc.abortTransaction()
        raise
    return {"ok": True, "deleted_objects": deleted, "recompute_deferred": True}


def delete_live_program(service: Any, prepared: Mapping[str, Any]) -> dict[str, Any]:
    _surface_still_matches(service, prepared)
    doc = service._active_document()
    if doc is None or str(getattr(doc, "Name", "") or "") != prepared["document_name"]:
        raise RuntimeError("The active document changed before deletion.")
    if str(getattr(doc, "Uid", "") or "") != str(prepared.get("document_uid") or ""):
        raise RuntimeError("The active document identity changed before deletion.")
    if prepared["pack"].domain == "partdesign":
        if str(service.provider_document_revision()) != str(
            prepared.get("document_revision") or ""
        ):
            raise RuntimeError(
                "The document changed before Part Design deletion; inspect and retry."
            )
        return _delete_partdesign_program(doc, prepared)
    objects = _program_objects(
        doc, str(prepared["program_id"]), prepared["pack"].domain
    )
    mesh_rollbacks = (
        _mesh_rollback_states(objects)
        if prepared["pack"].domain == "mesh"
        else []
    )
    internal = list(objects)
    for obj in objects:
        if str(getattr(obj, "TypeId", "")) == "Assembly::AssemblyObject":
            joint_group = _assembly_joint_group(obj)
            if joint_group is not None:
                internal.append(joint_group)
            simulation_group = _assembly_simulation_group(obj)
            if simulation_group is not None:
                internal.append(simulation_group)
            view_group = _assembly_view_group(obj)
            if view_group is not None:
                internal.append(view_group)
    external = _external_uses(doc, objects, internal)
    if external:
        raise _reference_error(
            "Cannot delete this XScript program while human-created or foreign "
            "document objects reference its stable outputs",
            external,
        )
    deleted = [
        {
            "object_name": str(obj.Name),
            "label": str(obj.Label),
            "type_id": str(obj.TypeId),
            "output_name": str(getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or ""),
        }
        for obj in objects
    ]
    transaction_open = False
    try:
        if hasattr(doc, "openTransaction"):
            doc.openTransaction(f"Delete {prepared['pack'].title} XScript program")
            transaction_open = True
        _remove_owned_objects(doc, objects)
        if hasattr(doc, "commitTransaction") and transaction_open:
            doc.commitTransaction()
            transaction_open = False
    except Exception as deletion_error:
        if transaction_open and hasattr(doc, "abortTransaction"):
            try:
                doc.abortTransaction()
            except Exception:
                pass
        if mesh_rollbacks:
            try:
                _restore_mesh_rollback_states(mesh_rollbacks)
            except Exception as rollback_error:
                raise RuntimeError(
                    f"{deletion_error} Explicit Mesh deletion rollback failure: "
                    f"{rollback_error}"
                ) from deletion_error
        raise
    return {"ok": True, "deleted_objects": deleted, "recompute_deferred": True}
