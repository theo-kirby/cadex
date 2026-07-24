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
PROP_MESHPART_VALIDATION = "CadexMeshPartValidation"
PROP_POINTS_VALIDATION = "CadexPointsValidation"
PROP_REVERSE_VALIDATION = "CadexReverseEngineeringValidation"
PROP_INSPECTION_VALIDATION = "CadexInspectionValidation"
PROP_ROBOT_VALIDATION = "CadexRobotValidation"
PROP_FEM_VALIDATION = "CadexFEMValidation"
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
    "inspection_group": "Inspection::Group",
    "inspection_feature": "Inspection::Feature",
    "measurement": "App::FeaturePython",
    "report": "App::FeaturePython",
    "fit_metrics": "App::FeaturePython",
    "robot": "Robot::RobotObject",
    "trajectory": "Robot::TrajectoryObject",
    "dressup": "Robot::TrajectoryDressUpObject",
    "simulation": "App::FeaturePython",
    "analysis": "App::DocumentObjectGroup",
    "solver": "App::FeaturePython",
    "material": "App::FeaturePython",
    "constraint": "App::FeaturePython",
    "load_case": "App::DocumentObjectGroup",
    "result": "App::FeaturePython",
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
    PROP_MESHPART_VALIDATION,
    reference_contracts.PROP_DERIVED_STATE,
    reference_contracts.PROP_STALE_REASON,
    reference_contracts.PROP_SOURCE_REVISION,
)
_MAX_MESH_ROLLBACK_PROPERTIES = 256
_MAX_MESH_ROLLBACK_PROPERTY_BYTES = 2 * 1024 * 1024
_MAX_SHAPE_ROLLBACK_BREP_BYTES = 256 * 1024 * 1024
_MAX_POINTS_ROLLBACK_PROPERTIES = 256
_MAX_POINTS_ROLLBACK_PROPERTY_BYTES = 2 * 1024 * 1024
_MAX_INSPECTION_ROLLBACK_PROPERTIES = 256
_MAX_INSPECTION_ROLLBACK_PROPERTY_BYTES = 2 * 1024 * 1024
_MAX_INSPECTION_ROLLBACK_DISTANCES = 2_000_000
_MAX_ROBOT_ROLLBACK_PROPERTIES = 256
_MAX_ROBOT_ROLLBACK_PROPERTY_BYTES = 4 * 1024 * 1024
_MAX_ROLLBACK_PROPERTY_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
_ROBOT_TRAJECTORY_TYPES = frozenset(
    {"Robot::TrajectoryObject", "Robot::TrajectoryDressUpObject"}
)
_INSPECTION_FEATURE_KERNEL_PROPERTIES = frozenset(
    {
        "Actual",
        "Nominals",
        "SearchRadius",
        "Thickness",
        "Distances",
    }
)


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


def _object_is_frozen(obj: Any, contract: str) -> bool:
    checker = getattr(obj, "isFrozen", None)
    if not callable(checker):
        raise RuntimeError(
            f"This FreeCAD build cannot freeze native {contract} results; "
            "synchronous recompute protection is unavailable."
        )
    return bool(checker())


def _freeze_object(obj: Any, contract: str) -> None:
    freezer = getattr(obj, "freeze", None)
    if not callable(freezer):
        raise RuntimeError(
            f"This FreeCAD build cannot freeze native {contract} results; "
            "synchronous recompute protection is unavailable."
        )
    obj.purgeTouched()
    freezer()
    obj.purgeTouched()
    if not _object_is_frozen(obj, contract):
        raise RuntimeError(f"The native {contract} result did not enter frozen state.")


def _unfreeze_object(obj: Any, contract: str) -> None:
    if not _object_is_frozen(obj, contract):
        return
    unfreezer = getattr(obj, "unfreeze", None)
    if not callable(unfreezer):
        raise RuntimeError(f"The native {contract} result cannot be unfrozen safely.")
    unfreezer(True)
    if _object_is_frozen(obj, contract):
        raise RuntimeError(f"The native {contract} result remained frozen during update.")


def _inspection_feature_is_frozen(obj: Any) -> bool:
    return _object_is_frozen(obj, "Inspection")


def _freeze_inspection_feature(obj: Any) -> None:
    _freeze_object(obj, "Inspection")


def _unfreeze_inspection_feature(obj: Any) -> None:
    _unfreeze_object(obj, "Inspection")


def _robot_dressup_is_frozen(obj: Any) -> bool:
    return _object_is_frozen(obj, "Robot dress-up")


def _freeze_robot_dressup(obj: Any) -> None:
    _freeze_object(obj, "Robot dress-up")


def _unfreeze_robot_dressup(obj: Any) -> None:
    _unfreeze_object(obj, "Robot dress-up")


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
            inspection_feature = (
                domain == "inspection"
                and str(getattr(output, "TypeId", "") or "")
                == "Inspection::Feature"
            )
            already_stale = (
                str(getattr(output, reference_contracts.PROP_DERIVED_STATE, "") or "")
                == "stale"
            )
            if not already_stale:
                if inspection_feature:
                    _unfreeze_inspection_feature(output)
                revision = str(
                    getattr(output, contracts.PROP_PROGRAM_REVISION, "") or ""
                )
                try:
                    reference_contracts.mark_stale(
                        output,
                        revision,
                        f"Input object {getattr(source, 'Name', '<object>')}."
                        f"{changed_property} changed after this XScript snapshot; "
                        "regenerate the program.",
                    )
                finally:
                    if inspection_feature:
                        _freeze_inspection_feature(output)
            elif inspection_feature and not _inspection_feature_is_frozen(output):
                _freeze_inspection_feature(output)
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
        type_id = str(getattr(owner, "TypeId", "") or "").lower()
        if any(
            marker in type_id
            for marker in (
                "fem",
                "path::",
                "techdraw",
                "robot",
                "inspection",
            )
        ):
            reference_contracts.mark_stale(
                owner,
                revision,
                "A referenced XScript Part output changed; regenerate this derived result.",
            )
            stale.append(name)
    return {"touched": sorted(set(touched)), "marked_stale": sorted(set(stale))}


def _internal_name(prepared: Mapping[str, Any], output_name: str) -> str:
    domain = _SAFE_NAME.sub("_", prepared["pack"].domain.title())
    output = _SAFE_NAME.sub("_", output_name)
    return f"Vibe{domain}_{str(prepared['program_id'])[:8]}_{output}"[:120]


def _native_type(output_type: str, domain: str = "") -> str:
    if domain == "fem":
        native_type = {
            "analysis": "Fem::FemAnalysis",
            "solver": "Fem::FemSolverObjectPython",
            "material": "App::MaterialObjectPython",
            "constraint": "Fem::ConstraintFixed",
            "load_case": "App::DocumentObjectGroup",
            "mesh": "Fem::FemMeshShapeBaseObjectPython",
            "result": "Fem::FemResultObjectPython",
        }.get(output_type)
        if native_type is None:
            raise RuntimeError(
                f"No native FEM publisher exists for output type {output_type!r}."
            )
        return native_type
    if output_type in _BREP_OUTPUT_TYPES:
        return "Part::Feature"
    if output_type == "mesh":
        return "Mesh::Feature"
    if output_type == "points":
        return "Points::Feature"
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


def _native_vector(value: Any, label: str) -> Any:
    import FreeCAD as App

    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise RuntimeError(f"{label} must be [x, y, z].")
    return App.Vector(*(float(item) for item in value))


def _create_object(
    doc: Any,
    prepared: Mapping[str, Any],
    output_name: str,
    output_type: str,
    definition: Mapping[str, Any],
    assembly: Any | None,
) -> Any:
    native_type = _native_type(output_type, prepared["pack"].domain)
    name = _internal_name(prepared, output_name)
    if prepared["pack"].domain == "fem":
        import ObjectsFem

        if output_type == "analysis":
            obj = ObjectsFem.makeAnalysis(doc, name)
        elif output_type == "solver":
            obj = ObjectsFem.makeSolverCalculiXCcxTools(doc, name)
        elif output_type == "material":
            obj = ObjectsFem.makeMaterialSolid(doc, name)
        elif output_type == "constraint":
            kind = str(dict(definition.get("properties") or {}).get("kind") or "")
            factory = {
                "fixed": ObjectsFem.makeConstraintFixed,
                "force": ObjectsFem.makeConstraintForce,
                "pressure": ObjectsFem.makeConstraintPressure,
            }.get(kind)
            if factory is None:
                raise RuntimeError(f"Unsupported native FEM constraint kind {kind!r}.")
            obj = factory(doc, name)
        elif output_type == "load_case":
            obj = doc.addObject("App::DocumentObjectGroup", name)
        elif output_type == "mesh":
            obj = ObjectsFem.makeMeshGmsh(doc, name)
        elif output_type == "result":
            obj = ObjectsFem.makeResultMechanical(doc, name)
        else:
            raise RuntimeError(f"No native FEM factory exists for {output_type!r}.")
    elif prepared["pack"].domain == "inspection":
        import Inspection

        del Inspection
        obj = doc.addObject(native_type, name)
    elif prepared["pack"].domain == "robot":
        import Robot

        del Robot
        obj = doc.addObject(native_type, name)
    elif output_type == "component_link" and assembly is not None:
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


def _configure_surface(obj: Any, item: Mapping[str, Any]) -> None:
    """Apply one detached Surface result without recompute or live OCC construction."""

    data = item.get("surface_data")
    detached = item.get("detached_shape")
    facts = item.get("facts")
    if not isinstance(data, dict) or not isinstance(facts, dict):
        raise RuntimeError(
            f"Surface output {item.get('name')!r} has no validated native readback."
        )
    if detached is None or not hasattr(obj, "Shape"):
        raise RuntimeError(
            f"Surface output {item.get('name')!r} has no detached Shape."
        )
    expected_shape_type = str(facts.get("shape_type") or "")
    if str(getattr(detached, "ShapeType", "") or "") != expected_shape_type:
        raise RuntimeError(
            f"Surface output {item.get('name')!r} detached Shape changed type."
        )
    obj.Shape = detached
    if str(getattr(obj.Shape, "ShapeType", "") or "") != expected_shape_type:
        raise RuntimeError(
            f"Published Surface output {item.get('name')!r} changed OCC ShapeType."
        )
    _add_string_property(
        obj,
        "CadexSurfaceOperation",
        "Exact Surface API operation accepted by the isolated worker.",
    )
    _add_string_property(
        obj,
        "CadexSurfaceEngine",
        "Native OCC or Surface engine used in the isolated worker.",
    )
    _add_string_property(
        obj,
        "CadexSurfaceValidation",
        "Bounded isolated Surface operation and typed-shape readback.",
    )
    obj.CadexSurfaceOperation = str(data.get("operation") or "")
    obj.CadexSurfaceEngine = str(data.get("engine") or "")
    obj.CadexSurfaceValidation = json.dumps(
        data,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


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


def _configure_reverse_engineering(obj: Any, item: Mapping[str, Any]) -> None:
    data = item.get("reverse_data")
    if not isinstance(data, Mapping):
        raise RuntimeError("A Reverse Engineering output has no validated native data.")
    output_type = str(item.get("type") or "")
    if output_type in _BREP_OUTPUT_TYPES:
        shape = item.get("detached_shape")
        if shape is None or shape.isNull() or not shape.isValid():
            raise RuntimeError("A Reverse Engineering BREP output is not valid.")
        obj.Shape = shape
    elif output_type == "mesh":
        mesh = item.get("detached_mesh")
        if mesh is None or int(mesh.CountFacets) <= 0:
            raise RuntimeError("A Reverse Engineering mesh output is empty.")
        obj.Mesh = mesh
    elif output_type == "fit_metrics":
        metrics = data.get("fit_metrics")
        if not isinstance(metrics, Mapping):
            raise RuntimeError("A fit-metrics output has no validated report.")
        properties = (
            (
                "App::PropertyString",
                "CadexTargetOutput",
                str(data.get("target_output") or ""),
                "Stable output name whose fit report is published here.",
            ),
            (
                "App::PropertyString",
                "CadexTargetOperation",
                str(data.get("target_operation") or ""),
                "Canonical Reverse Engineering operation measured by this report.",
            ),
            (
                "App::PropertyString",
                "CadexTargetOutputType",
                str(data.get("target_output_type") or ""),
                "Declared output type measured by this report.",
            ),
            (
                "App::PropertyInteger",
                "CadexSourcePointCount",
                int(metrics.get("source_point_count") or 0),
                "Authenticated source point count.",
            ),
            (
                "App::PropertyInteger",
                "CadexEvaluatedPointCount",
                int(metrics.get("evaluated_point_count") or 0),
                "Deterministically evaluated source sample count.",
            ),
            (
                "App::PropertyLength",
                "CadexMeanFitDistance",
                float(metrics.get("mean_distance") or 0.0),
                "Mean native source-to-result distance.",
            ),
            (
                "App::PropertyLength",
                "CadexRMSFitDistance",
                float(metrics.get("rms_distance") or 0.0),
                "Root-mean-square native source-to-result distance.",
            ),
            (
                "App::PropertyLength",
                "CadexMaximumFitDistance",
                float(metrics.get("maximum_distance") or 0.0),
                "Maximum native source-to-result distance.",
            ),
            (
                "App::PropertyLength",
                "CadexFitTolerance",
                float(metrics.get("tolerance") or 0.0),
                "Tolerance used for the pass fraction.",
            ),
            (
                "App::PropertyPercent",
                "CadexWithinTolerance",
                int(
                    round(
                        float(metrics.get("within_tolerance_fraction") or 0.0)
                        * 100.0
                    )
                ),
                "Rounded display percentage of evaluated source points within tolerance.",
            ),
            (
                "App::PropertyFloat",
                "CadexWithinToleranceFraction",
                float(metrics.get("within_tolerance_fraction") or 0.0),
                "Full-precision fraction of evaluated source points within tolerance.",
            ),
            (
                "App::PropertyInteger",
                "CadexSegmentCount",
                int(metrics.get("segment_count") or 0),
                "Validated segmentation count, or zero for a fitting output.",
            ),
        )
        for property_type, name, value, description in properties:
            _add_property(obj, property_type, name, description)
            setattr(obj, name, value)
    else:
        raise RuntimeError(
            f"No Reverse Engineering publisher exists for output type {output_type!r}."
        )
    _add_string_property(
        obj,
        PROP_REVERSE_VALIDATION,
        "Authenticated Reverse Engineering operation, native facts, and fit metrics.",
    )
    setattr(
        obj,
        PROP_REVERSE_VALIDATION,
        json.dumps(
            dict(data),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
    )


def _configure_inspection(
    doc: Any,
    obj: Any,
    item: Mapping[str, Any],
    outputs: Mapping[str, Any],
) -> None:
    """Apply precomputed native Inspection state without running its solver."""

    data = item.get("inspection_data")
    if not isinstance(data, Mapping):
        raise RuntimeError("An Inspection output has no validated native data.")
    output_type = str(item.get("type") or "")
    if output_type == "inspection_feature":
        definition = _definition(item)
        arguments = list(definition.get("arguments") or [])
        if len(arguments) != 2 or not isinstance(arguments[1], list):
            raise RuntimeError("An Inspection comparison definition is malformed.")
        actual = _reference_target(doc, arguments[0], "Inspection actual")
        nominals = [
            _reference_target(doc, reference, f"Inspection nominal {index}")
            for index, reference in enumerate(arguments[1])
        ]
        distances = item.get("detached_distances")
        if not isinstance(distances, list) or not distances:
            raise RuntimeError("An Inspection comparison has no detached distances.")
        for property_name in ("Actual", "Nominals", "SearchRadius", "Thickness"):
            setter = getattr(obj, "setPropertyStatus", None)
            if callable(setter):
                setter(property_name, "NoRecompute")
        obj.Actual = actual
        obj.Nominals = nominals
        obj.SearchRadius = float(data["search_radius"])
        obj.Thickness = float(data["thickness"])
        obj.Distances = [float(value) for value in distances]
        observed = [float(value) for value in list(obj.Distances)]
        if observed != distances:
            raise RuntimeError(
                "The live Inspection::Feature changed its precomputed float32 distances."
            )
        summary = data.get("distance_summary")
        if not isinstance(summary, Mapping):
            raise RuntimeError("An Inspection comparison has no distance summary.")
        typed = (
            (
                "App::PropertyFloat",
                "CadexToleranceLower",
                float(data["tolerance"][0]),
                "Accepted lower signed deviation tolerance in millimetres.",
            ),
            (
                "App::PropertyFloat",
                "CadexToleranceUpper",
                float(data["tolerance"][1]),
                "Accepted upper signed deviation tolerance in millimetres.",
            ),
            (
                "App::PropertyBool",
                "CadexRequireComplete",
                bool(data["require_complete"]),
                "Whether every actual sample must find a nominal within the search radius.",
            ),
            (
                "App::PropertyBool",
                "CadexPassed",
                bool(summary["passed"]),
                "Validated aggregate tolerance verdict.",
            ),
            (
                "App::PropertyInteger",
                "CadexSampleCount",
                int(summary["sample_count"]),
                "Native actual sample count.",
            ),
            (
                "App::PropertyInteger",
                "CadexMeasuredCount",
                int(summary["measured_count"]),
                "Samples with a nominal result inside the search radius.",
            ),
            (
                "App::PropertyInteger",
                "CadexUnmeasuredCount",
                int(summary["unmeasured_count"]),
                "Samples without a nominal result inside the search radius.",
            ),
            (
                "App::PropertyFloat",
                "CadexMinimumDistance",
                float(summary["minimum"] or 0.0),
                "Minimum measured signed distance in millimetres.",
            ),
            (
                "App::PropertyFloat",
                "CadexMaximumDistance",
                float(summary["maximum"] or 0.0),
                "Maximum measured signed distance in millimetres.",
            ),
            (
                "App::PropertyFloat",
                "CadexMeanDistance",
                float(summary["mean"] or 0.0),
                "Mean measured signed distance in millimetres.",
            ),
            (
                "App::PropertyFloat",
                "CadexRMSDistance",
                float(summary["rms"] or 0.0),
                "Root-mean-square measured distance in millimetres.",
            ),
            (
                "App::PropertyFloat",
                "CadexAbsoluteMaximumDistance",
                float(summary["absolute_maximum"] or 0.0),
                "Largest absolute measured deviation in millimetres.",
            ),
            (
                "App::PropertyFloat",
                "CadexWithinToleranceFraction",
                float(summary["within_tolerance_fraction"]),
                "Fraction of measured samples inside the accepted tolerance.",
            ),
        )
        for property_type, name, value, description in typed:
            _add_property(obj, property_type, name, description)
            setattr(obj, name, value)
    elif output_type == "inspection_group":
        member_names = list(data.get("member_outputs") or [])
        members = []
        for name in member_names:
            member = outputs.get(str(name))
            if member is None or str(getattr(member, "TypeId", "")) != "Inspection::Feature":
                raise RuntimeError(
                    f"Inspection group member {name!r} is missing or has the wrong native type."
                )
            members.append(member)
        for current in list(getattr(obj, "Group", []) or []):
            if not any(current is member for member in members):
                obj.removeObject(current)
        for member in members:
            if not any(current is member for current in list(obj.Group or [])):
                obj.addObject(member)
        if [str(member.Name) for member in list(obj.Group or [])] != [
            str(member.Name) for member in members
        ]:
            raise RuntimeError("The live Inspection::Group changed member order.")
        for property_type, name, value, description in (
            (
                "App::PropertyInteger",
                "CadexComparisonCount",
                int(data["comparison_count"]),
                "Stable comparison member count.",
            ),
            (
                "App::PropertyInteger",
                "CadexPassedCount",
                int(data["passed_count"]),
                "Passing comparison count.",
            ),
            (
                "App::PropertyInteger",
                "CadexFailedCount",
                int(data["failed_count"]),
                "Failing comparison count.",
            ),
            (
                "App::PropertyBool",
                "CadexPassed",
                bool(data["passed"]),
                "Aggregate group verdict.",
            ),
        ):
            _add_property(obj, property_type, name, description)
            setattr(obj, name, value)
    elif output_type == "measurement":
        target_name = str(data.get("target_output") or "")
        target = outputs.get(target_name)
        if target is None or str(getattr(target, "TypeId", "")) != "Inspection::Feature":
            raise RuntimeError("An Inspection measurement target is unavailable.")
        for property_type, name, value, description in (
            (
                "App::PropertyLink",
                "CadexComparison",
                target,
                "Stable comparison supplying this scalar.",
            ),
            (
                "App::PropertyString",
                "CadexMetric",
                str(data["metric"]),
                "Canonical scalar metric name.",
            ),
            (
                "App::PropertyFloat",
                "CadexValue",
                float(data["value"]),
                "Validated scalar value.",
            ),
            (
                "App::PropertyString",
                "CadexUnit",
                str(data["unit"]),
                "Scalar unit: mm, ratio, or count.",
            ),
            (
                "App::PropertyBool",
                "CadexPassed",
                bool(data["passed"]),
                "Verdict of the source comparison.",
            ),
        ):
            _add_property(obj, property_type, name, description)
            setattr(obj, name, value)
    elif output_type == "report":
        group_name = str(data.get("group_output") or "")
        group = outputs.get(group_name)
        if group is None or str(getattr(group, "TypeId", "")) != "Inspection::Group":
            raise RuntimeError("An Inspection report group is unavailable.")
        for property_type, name, value, description in (
            (
                "App::PropertyLink",
                "CadexInspectionGroup",
                group,
                "Stable native Inspection group summarized by this report.",
            ),
            (
                "App::PropertyInteger",
                "CadexComparisonCount",
                int(data["comparison_count"]),
                "Reported comparison count.",
            ),
            (
                "App::PropertyInteger",
                "CadexPassedCount",
                int(data["passed_count"]),
                "Passing comparison count.",
            ),
            (
                "App::PropertyInteger",
                "CadexFailedCount",
                int(data["failed_count"]),
                "Failing comparison count.",
            ),
            (
                "App::PropertyBool",
                "CadexPassed",
                bool(data["passed"]),
                "Aggregate report verdict.",
            ),
        ):
            _add_property(obj, property_type, name, description)
            setattr(obj, name, value)
        _add_string_property(
            obj,
            "CadexInspectionEntries",
            "Complete bounded per-comparison report entries as JSON.",
        )
        obj.CadexInspectionEntries = json.dumps(
            list(data["entries"]),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    else:
        raise RuntimeError(
            f"No Inspection publisher exists for output type {output_type!r}."
        )
    validation = dict(data)
    if output_type == "inspection_feature":
        validation.update(
            {
                "distance_artifact_schema": str(item.get("artifact_schema") or ""),
                "distance_artifact_sha256": str(item.get("artifact_sha256") or ""),
                "distance_artifact_bytes": int(item.get("artifact_bytes") or 0),
            }
        )
    _add_string_property(
        obj,
        PROP_INSPECTION_VALIDATION,
        "Authenticated native Inspection graph, trace, distances, and verdict.",
    )
    setattr(
        obj,
        PROP_INSPECTION_VALIDATION,
        json.dumps(
            validation,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
    )


def _robot_placement_matches(actual: Any, expected: Mapping[str, Any]) -> bool:
    position = expected.get("position")
    rotation = expected.get("rotation")
    if (
        not isinstance(position, (list, tuple))
        or len(position) != 3
        or not isinstance(rotation, (list, tuple))
        or len(rotation) != 4
    ):
        return False
    observed_position = [float(value) for value in actual.Base]
    observed_rotation = [float(value) for value in actual.Rotation.Q]
    expected_position = [float(value) for value in position]
    expected_rotation = [float(value) for value in rotation]
    if not all(
        math.isclose(left, right, rel_tol=1.0e-10, abs_tol=1.0e-8)
        for left, right in zip(observed_position, expected_position)
    ):
        return False
    observed_norm = math.sqrt(sum(value * value for value in observed_rotation))
    expected_norm = math.sqrt(sum(value * value for value in expected_rotation))
    if observed_norm <= 1.0e-15 or expected_norm <= 1.0e-15:
        return False
    dot = sum(
        left * right
        for left, right in zip(observed_rotation, expected_rotation)
    ) / (observed_norm * expected_norm)
    return math.isclose(abs(dot), 1.0, rel_tol=1.0e-10, abs_tol=1.0e-10)


def _robot_kinematic_rows(value: Any) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != 6:
        raise RuntimeError("A Robot output must contain exactly six kinematic rows.")
    rows: list[list[float]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, list) or len(raw) != 8:
            raise RuntimeError(
                f"Robot kinematic row {index} must contain exactly eight numbers."
            )
        row = [float(item) for item in raw]
        if not all(math.isfinite(item) for item in row):
            raise RuntimeError(f"Robot kinematic row {index} contains a non-finite value.")
        if row[4] not in {-1.0, 1.0} or row[6] > row[5] or row[7] <= 0.0:
            raise RuntimeError(f"Robot kinematic row {index} is inconsistent.")
        rows.append(row)
    return rows


def _robot_trajectory_summary(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "waypoint_count",
        "length",
        "duration",
    }:
        raise RuntimeError(f"{label} has a malformed native trajectory summary.")
    count = value.get("waypoint_count")
    length = value.get("length")
    duration = value.get("duration")
    if (
        type(count) is not int
        or count < 0
        or isinstance(length, bool)
        or not isinstance(length, (int, float))
        or isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(length))
        or not math.isfinite(float(duration))
        or float(length) < 0.0
        or float(duration) < 0.0
    ):
        raise RuntimeError(f"{label} has invalid native trajectory values.")
    return {
        "waypoint_count": count,
        "length": float(length),
        "duration": float(duration),
    }


def _swap_robot_trajectory(obj: Any, trajectory: Any) -> dict[str, dict[str, Any]]:
    import Robot

    raw = Robot.swapPrecomputedTrajectory(obj, trajectory)
    try:
        if not isinstance(raw, Mapping) or set(raw) != {"installed", "displaced"}:
            raise RuntimeError(
                "The native Robot trajectory swap returned malformed state."
            )
        return {
            "installed": _robot_trajectory_summary(
                raw["installed"], "Installed trajectory"
            ),
            "displaced": _robot_trajectory_summary(
                raw["displaced"], "Displaced trajectory"
            ),
        }
    except Exception as validation_error:
        try:
            Robot.swapPrecomputedTrajectory(obj, trajectory)
        except Exception as rollback_error:
            raise RuntimeError(
                f"{validation_error} Native Robot trajectory swap rollback failed: "
                f"{type(rollback_error).__name__}: {rollback_error}"
            ) from validation_error
        raise


def _robot_summary_matches(summary: Mapping[str, Any], data: Mapping[str, Any]) -> bool:
    return (
        int(summary.get("waypoint_count", -1)) == int(data.get("waypoint_count", -2))
        and math.isclose(
            float(summary.get("length", -1.0)),
            float(data.get("length", -2.0)),
            rel_tol=1.0e-10,
            abs_tol=1.0e-8,
        )
        and math.isclose(
            float(summary.get("duration", -1.0)),
            float(data.get("duration", -2.0)),
            rel_tol=1.0e-10,
            abs_tol=1.0e-8,
        )
    )


def _configure_robot(
    obj: Any,
    item: Mapping[str, Any],
    outputs: Mapping[str, Any],
    trajectory_swaps: list[dict[str, Any]],
) -> None:
    """Install validated native Robot state without recompute or path generation."""

    data = item.get("robot_data")
    if not isinstance(data, Mapping):
        raise RuntimeError("A Robot output has no validated native data.")
    data = dict(data)
    output_type = str(item.get("type") or "")
    if str(data.get("native_type") or getattr(obj, "TypeId", "")) != str(
        getattr(obj, "TypeId", "")
    ) and output_type != "simulation":
        raise RuntimeError("A Robot output changed its validated native type.")

    if output_type == "robot":
        rows = _robot_kinematic_rows(data.get("kinematics"))
        setter = getattr(obj, "setKinematic", None)
        if not callable(setter):
            raise RuntimeError(
                "This FreeCAD build cannot apply in-memory Robot kinematics."
            )
        setter(rows)
        obj.Base = _placement(data["base"])
        obj.Tool = _placement(data["tool"])
        obj.Home = [float(value) for value in data["home"]]
        expected_axes = [float(value) for value in data["axis_positions"]]
        if len(expected_axes) != 6:
            raise RuntimeError("A Robot output must contain exactly six axis positions.")
        for axis, value in enumerate(expected_axes, start=1):
            setattr(obj, f"Axis{axis}", value)
        native = obj.getRobot()
        observed_axes = [
            float(getattr(native, f"Axis{axis}")) for axis in range(1, 7)
        ]
        if (
            any(
                not math.isclose(left, right, rel_tol=1.0e-10, abs_tol=1.0e-8)
                for left, right in zip(observed_axes, expected_axes)
            )
            or not _robot_placement_matches(obj.Base, data["base"])
            or not _robot_placement_matches(obj.Tool, data["tool"])
            or not _robot_placement_matches(obj.Tcp, data["tcp"])
        ):
            raise RuntimeError("The live native Robot state differs from worker validation.")
    elif output_type in {"trajectory", "dressup"}:
        if output_type == "dressup":
            source_name = str(data.get("source_output") or "")
            source = outputs.get(source_name)
            if source is None or str(getattr(source, "TypeId", "")) != (
                "Robot::TrajectoryObject"
            ):
                raise RuntimeError("A Robot dress-up source is unavailable.")
            obj.Source = source
            speed = data.get("speed")
            acceleration = data.get("acceleration")
            continuous = data.get("continuous")
            obj.UseSpeed = speed is not None
            if speed is not None:
                obj.Speed = float(speed)
            obj.UseAcceleration = acceleration is not None
            if acceleration is not None:
                obj.Acceleration = float(acceleration)
            obj.ContType = (
                "DontChange"
                if continuous is None
                else ("Continues" if continuous else "Discontinues")
            )
            obj.AddType = {
                "none": "DontChange",
                "use_orientation": "UseOrientation",
                "add_position": "AddPosition",
                "add_orientation": "AddOrintation",
                "add_position_and_orientation": "AddPositionAndOrientation",
            }[str(data["offset_mode"])]
            obj.PosAdd = _placement(data.get("offset"))
        obj.Base = _placement(data["base"])
        trajectory = item.get("detached_trajectory")
        if trajectory is None:
            raise RuntimeError("A Robot path has no detached precomputed trajectory.")
        swapped = _swap_robot_trajectory(obj, trajectory)
        trajectory_swaps.append(
            {
                "object_name": str(obj.Name),
                "object": obj,
                "holder": trajectory,
                "accepted_summary": dict(swapped["displaced"]),
            }
        )
        if not _robot_summary_matches(swapped["installed"], data):
            raise RuntimeError(
                "The installed native Robot trajectory differs from worker validation."
            )
        for property_type, name, value, description in (
            (
                "App::PropertyInteger",
                "CadexWaypointCount",
                int(data["waypoint_count"]),
                "Validated native waypoint count.",
            ),
            (
                "App::PropertyFloat",
                "CadexTrajectoryLength",
                float(data["length"]),
                "Validated native trajectory length in millimetres.",
            ),
            (
                "App::PropertyFloat",
                "CadexTrajectoryDuration",
                float(data["duration"]),
                "Validated native trajectory duration in seconds.",
            ),
        ):
            _add_property(obj, property_type, name, description)
            setattr(obj, name, value)
    elif output_type == "simulation":
        robot_name = str(data.get("robot_output") or "")
        trajectory_name = str(data.get("trajectory_output") or "")
        robot = outputs.get(robot_name)
        trajectory = outputs.get(trajectory_name)
        if robot is None or str(getattr(robot, "TypeId", "")) != "Robot::RobotObject":
            raise RuntimeError("A Robot simulation robot is unavailable.")
        if trajectory is None or str(getattr(trajectory, "TypeId", "")) not in (
            _ROBOT_TRAJECTORY_TYPES
        ):
            raise RuntimeError("A Robot simulation trajectory is unavailable.")
        for property_type, name, value, description in (
            ("App::PropertyLink", "CadexRobot", robot, "Simulated native robot."),
            (
                "App::PropertyLink",
                "CadexTrajectory",
                trajectory,
                "Simulated native trajectory or dress-up.",
            ),
            (
                "App::PropertyFloat",
                "CadexDuration",
                float(data["duration"]),
                "Validated simulation duration in seconds.",
            ),
            (
                "App::PropertyFloat",
                "CadexLength",
                float(data["length"]),
                "Validated simulated path length in millimetres.",
            ),
            (
                "App::PropertyInteger",
                "CadexSampleCount",
                int(data["sample_count"]),
                "Authenticated simulation sample count.",
            ),
            (
                "App::PropertyInteger",
                "CadexReachableCount",
                int(data["reachable_count"]),
                "Samples solved by native inverse kinematics.",
            ),
            (
                "App::PropertyInteger",
                "CadexUnreachableCount",
                int(data["unreachable_count"]),
                "Samples rejected by native inverse kinematics.",
            ),
            (
                "App::PropertyBool",
                "CadexSamplesLimited",
                bool(data["samples_limited"]),
                "Whether the requested simulation was capped by its sample budget.",
            ),
            (
                "App::PropertyString",
                "CadexArtifactSHA256",
                str(item.get("artifact_sha256") or ""),
                "SHA-256 of the authenticated worker simulation samples.",
            ),
        ):
            _add_property(obj, property_type, name, description)
            setattr(obj, name, value)
    else:
        raise RuntimeError(f"No Robot publisher exists for output type {output_type!r}.")

    validation = dict(data)
    if output_type == "simulation":
        validation.update(
            {
                "artifact_schema": str(item.get("artifact_schema") or ""),
                "artifact_sha256": str(item.get("artifact_sha256") or ""),
                "artifact_bytes": int(item.get("artifact_bytes") or 0),
                "sample_width": int(item.get("sample_width") or 0),
            }
        )
    _add_string_property(
        obj,
        PROP_ROBOT_VALIDATION,
        "Authenticated native Robot graph, trajectory facts, and simulation diagnostics.",
    )
    setattr(
        obj,
        PROP_ROBOT_VALIDATION,
        json.dumps(
            validation,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
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


def _configure_mesh(
    obj: Any,
    item: Mapping[str, Any],
    *,
    data_key: str = "mesh_data",
    validation_property: str = PROP_MESH_VALIDATION,
) -> None:
    if str(getattr(obj, "TypeId", "") or "") != "Mesh::Feature":
        raise RuntimeError("A stable Mesh output changed native type.")
    detached = item.get("detached_mesh")
    data = item.get(data_key)
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
        validation_property,
        "Validated isolated native mesh topology and conversion diagnostics.",
    )
    setattr(
        obj,
        validation_property,
        json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
    )


def _configure_meshpart_shape(obj: Any, item: Mapping[str, Any]) -> None:
    if str(getattr(obj, "TypeId", "") or "") != "Part::Feature":
        raise RuntimeError("A stable MeshPart BREP output changed native type.")
    detached = item.get("detached_shape")
    data = item.get("meshpart_data")
    if detached is None or not isinstance(data, dict):
        raise RuntimeError("A MeshPart BREP output has no validated detached state.")
    import FreeCAD as App

    preserved_placement = App.Placement(obj.Placement)
    candidate = detached.copy()
    candidate.Placement = preserved_placement
    obj.Shape = candidate
    obj.Placement = preserved_placement
    if (
        obj.Shape.isNull()
        or not obj.Shape.isValid()
        or str(obj.Shape.ShapeType) != str(candidate.ShapeType)
        or not bool(obj.Shape.isSame(candidate))
    ):
        raise RuntimeError(
            "Published MeshPart BREP differs from isolated worker validation."
        )
    _assert_matrix(obj.Placement, preserved_placement, "MeshPart output placement")
    _add_string_property(
        obj,
        PROP_MESHPART_VALIDATION,
        "Validated isolated native MeshPart conversion diagnostics.",
    )
    setattr(
        obj,
        PROP_MESHPART_VALIDATION,
        json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
    )


def _points_kernel_facts(
    kernel: Any,
    sample_indices: list[int],
) -> dict[str, Any]:
    """Read bounded native facts without materializing the complete point array."""

    count = int(kernel.CountPoints)
    if any(
        isinstance(index, bool) or type(index) is not int or not 1 <= index <= count
        for index in sample_indices
    ):
        raise RuntimeError("Points validation contains an invalid sample index.")
    box = kernel.BoundBox
    sampled = (
        list(kernel.fromSegment([index - 1 for index in sample_indices]).Points)
        if sample_indices
        else []
    )
    return {
        "points": count,
        "bounds": {
            "minimum": [float(box.XMin), float(box.YMin), float(box.ZMin)],
            "maximum": [float(box.XMax), float(box.YMax), float(box.ZMax)],
            "size": [float(box.XLength), float(box.YLength), float(box.ZLength)],
        },
        "sample": [
            [float(point.x), float(point.y), float(point.z)] for point in sampled
        ],
        "sample_indices": list(sample_indices),
    }


def _points_bounded_facts_match(
    observed: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> bool:
    if observed.get("points") != expected.get("points"):
        return False
    if observed.get("sample_indices") != expected.get("sample_indices"):
        return False

    def vectors_match(left: Any, right: Any) -> bool:
        return (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) == len(right) == 3
            and all(
                math.isclose(
                    float(first),
                    float(second),
                    rel_tol=1.0e-9,
                    abs_tol=1.0e-7,
                )
                for first, second in zip(left, right)
            )
        )

    observed_bounds = observed.get("bounds")
    expected_bounds = expected.get("bounds")
    if not isinstance(observed_bounds, Mapping) or not isinstance(
        expected_bounds, Mapping
    ):
        return False
    if not all(
        vectors_match(observed_bounds.get(name), expected_bounds.get(name))
        for name in ("minimum", "maximum", "size")
    ):
        return False
    left_sample = observed.get("sample")
    right_sample = expected.get("sample")
    return (
        isinstance(left_sample, list)
        and isinstance(right_sample, list)
        and len(left_sample) == len(right_sample)
        and all(
            vectors_match(first, second)
            for first, second in zip(left_sample, right_sample)
        )
    )


def _ensure_points_property(
    obj: Any,
    name: str,
    property_type: str,
    description: str,
) -> None:
    if name not in _properties(obj):
        obj.addProperty(property_type, name, "Cadex", description)
    observed_type = str(obj.getTypeIdOfProperty(name) or "")
    if observed_type != property_type:
        raise RuntimeError(
            f"Stable Points output property {name!r} has native type "
            f"{observed_type!r}; expected {property_type!r}."
        )


def _configure_points(obj: Any, item: Mapping[str, Any]) -> None:
    if str(getattr(obj, "TypeId", "") or "") != "Points::Feature":
        raise RuntimeError("A stable Points output changed native type.")
    detached = item.get("detached_points")
    attributes = item.get("point_attributes")
    facts = item.get("facts")
    data = item.get("points_data")
    if (
        detached is None
        or not isinstance(attributes, dict)
        or not isinstance(facts, dict)
        or not isinstance(data, dict)
    ):
        raise RuntimeError("A Points output has no validated detached native state.")
    import FreeCAD as App

    preserved_placement = App.Placement(obj.Placement)
    obj.Points = detached
    obj.Placement = App.Placement()
    try:
        observed = _points_kernel_facts(
            obj.Points,
            list(facts.get("sample_indices") or []),
        )
    finally:
        obj.Placement = preserved_placement
    if not _points_bounded_facts_match(observed, facts):
        raise RuntimeError(
            "Published native Points state differs from isolated worker validation."
        )
    _assert_matrix(obj.Placement, preserved_placement, "Points output placement")

    property_contracts = {
        "colors": (
            "Color",
            "App::PropertyColorList",
            "Validated per-point RGBA colors.",
        ),
        "intensities": (
            "Intensity",
            "Points::PropertyGreyValueList",
            "Validated per-point scalar intensities.",
        ),
        "normals": (
            "Normal",
            "Points::PropertyNormalList",
            "Validated per-point unit normals.",
        ),
    }
    for attribute_name, (property_name, property_type, description) in (
        property_contracts.items()
    ):
        values = list(attributes.get(attribute_name) or [])
        if values or property_name in _properties(obj):
            _ensure_points_property(obj, property_name, property_type, description)
        if property_name not in _properties(obj):
            continue
        if attribute_name == "normals":
            setattr(
                obj,
                property_name,
                [App.Vector(*(float(component) for component in value)) for value in values],
            )
        else:
            setattr(obj, property_name, values)
        if len(getattr(obj, property_name)) != len(values):
            raise RuntimeError(
                f"Published Points attribute {attribute_name!r} changed length."
            )

    structured = facts.get("structured")
    for property_name in ("Width", "Height"):
        if structured is not None or property_name in _properties(obj):
            _ensure_points_property(
                obj,
                property_name,
                "App::PropertyInteger",
                "Validated structured point-cloud dimension; zero means unstructured.",
            )
        if property_name in _properties(obj):
            setattr(
                obj,
                property_name,
                int(dict(structured or {}).get(property_name.lower()) or 0),
            )
    if structured is not None and int(obj.Width) * int(obj.Height) != int(
        facts["points"]
    ):
        raise RuntimeError("Published Points structured dimensions are inconsistent.")

    _add_string_property(
        obj,
        PROP_POINTS_VALIDATION,
        "Validated isolated point-cloud source, pipeline, attributes, and native facts.",
    )
    setattr(
        obj,
        PROP_POINTS_VALIDATION,
        json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
    )


def _points_rollback_states(objects: list[Any]) -> list[dict[str, Any]]:
    """Capture complete accepted Points::Feature state for explicit rollback."""

    states = []
    for obj in objects:
        if str(getattr(obj, "TypeId", "") or "") != "Points::Feature":
            continue
        property_names = list(getattr(obj, "PropertiesList", []) or [])
        if len(property_names) > _MAX_POINTS_ROLLBACK_PROPERTIES:
            raise RuntimeError(
                f"Points object {obj.Name!r} has {len(property_names)} properties; "
                f"the rollback limit is {_MAX_POINTS_ROLLBACK_PROPERTIES}."
            )
        properties = {}
        property_bytes = 0
        controlled_properties = {}
        for name in ("Color", "Intensity", "Normal", "Width", "Height"):
            if name not in _properties(obj):
                continue
            raw = getattr(obj, name)
            if name == "Normal":
                value = [
                    (float(item.x), float(item.y), float(item.z))
                    for item in list(raw or [])
                ]
            elif name == "Color":
                value = [
                    tuple(float(component) for component in item)
                    for item in list(raw or [])
                ]
            elif name == "Intensity":
                value = [float(item) for item in list(raw or [])]
            else:
                value = int(raw)
            controlled_properties[name] = {
                "type": str(obj.getTypeIdOfProperty(name) or ""),
                "group": str(obj.getGroupOfProperty(name) or ""),
                "documentation": str(obj.getDocumentationOfProperty(name) or ""),
                "editor_modes": list(obj.getEditorMode(name) or []),
                "value": value,
            }
        for name in property_names:
            if name in {
                "Points",
                "ExpressionEngine",
                "Color",
                "Intensity",
                "Normal",
                "Width",
                "Height",
            }:
                continue
            try:
                content = bytes(obj.dumpPropertyContent(name))
            except Exception as exc:
                raise RuntimeError(
                    f"Points object {obj.Name!r} property {name!r} cannot be "
                    f"captured for rollback: {type(exc).__name__}: {exc}"
                ) from exc
            property_bytes += len(content)
            if property_bytes > _MAX_POINTS_ROLLBACK_PROPERTY_BYTES:
                raise RuntimeError(
                    f"Points object {obj.Name!r} rollback properties exceed "
                    f"{_MAX_POINTS_ROLLBACK_PROPERTY_BYTES} serialized bytes."
                )
            properties[name] = {
                "type": str(obj.getTypeIdOfProperty(name) or ""),
                "group": str(obj.getGroupOfProperty(name) or ""),
                "documentation": str(obj.getDocumentationOfProperty(name) or ""),
                "editor_modes": list(obj.getEditorMode(name) or []),
                "content": content,
            }
        kernel = obj.Points.copy()
        count = int(kernel.CountPoints)
        sample_indices = list(range(1, min(4, count) + 1))
        sample_indices.extend(
            index
            for index in range(max(1, count - 3), count + 1)
            if index not in sample_indices
        )
        states.append(
            {
                "document": obj.Document,
                "name": str(obj.Name),
                "label": str(obj.Label),
                "points": kernel,
                "facts": _points_kernel_facts(kernel, sample_indices),
                "properties": properties,
                "controlled_properties": controlled_properties,
                "expressions": [
                    [str(path), str(expression)]
                    for path, expression in list(obj.ExpressionEngine or [])
                ],
            }
        )
    return states


def _restore_points_rollback_states(states: list[dict[str, Any]]) -> list[str]:
    failures = []
    restored = []
    resolved = []
    for state in states:
        document = state["document"]
        name = str(state["name"])
        obj = document.getObject(name)
        try:
            if obj is None:
                obj = document.addObject("Points::Feature", name)
            if (
                obj is None
                or str(obj.Name) != name
                or str(obj.TypeId) != "Points::Feature"
            ):
                raise RuntimeError("native Points identity could not be restored")
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
            obj.Points = state["points"].copy()
            for property_name, captured in state["properties"].items():
                obj.restorePropertyContent(
                    property_name,
                    bytearray(captured["content"]),
                )
                for mode in list(captured["editor_modes"]):
                    obj.setPropertyStatus(property_name, str(mode))
            controlled = dict(state["controlled_properties"])
            for property_name in ("Color", "Intensity", "Normal", "Width", "Height"):
                captured = controlled.get(property_name)
                if captured is None:
                    if property_name in _properties(obj):
                        obj.removeProperty(property_name)
                    continue
                if property_name not in _properties(obj):
                    obj.addProperty(
                        str(captured["type"]),
                        property_name,
                        str(captured["group"]),
                        str(captured["documentation"]),
                    )
                if str(obj.getTypeIdOfProperty(property_name) or "") != str(
                    captured["type"]
                ):
                    raise RuntimeError(
                        f"controlled property {property_name!r} changed native type"
                    )
                value = captured["value"]
                if property_name == "Normal":
                    import FreeCAD as App

                    value = [App.Vector(*item) for item in value]
                setattr(obj, property_name, value)
                for mode in list(captured["editor_modes"]):
                    obj.setPropertyStatus(property_name, str(mode))
            for path, _expression in list(obj.ExpressionEngine or []):
                obj.setExpression(str(path).lstrip("."), None)
            for path, expression in state["expressions"]:
                obj.setExpression(str(path).lstrip("."), str(expression))
            obj.Label = str(state["label"])
            if [
                [str(path), str(expression)]
                for path, expression in list(obj.ExpressionEngine or [])
            ] != state["expressions"]:
                raise RuntimeError(
                    "restored Points expressions do not match accepted state"
                )
            if not _points_bounded_facts_match(
                _points_kernel_facts(
                    obj.Points,
                    list(state["facts"]["sample_indices"]),
                ),
                state["facts"],
            ):
                raise RuntimeError(
                    "restored native Points do not match accepted state"
                )
            restored.append(name)
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError(
            "Points operation failed and accepted state could not be fully restored: "
            f"{'; '.join(failures)}"
        )
    return restored


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


def _meshpart_shape_rollback_states(objects: list[Any]) -> list[dict[str, Any]]:
    """Capture complete accepted Part::Feature state for explicit rollback."""

    states = []
    for obj in objects:
        if str(getattr(obj, "TypeId", "") or "") != "Part::Feature":
            continue
        property_names = list(getattr(obj, "PropertiesList", []) or [])
        if len(property_names) > _MAX_MESH_ROLLBACK_PROPERTIES:
            raise RuntimeError(
                f"MeshPart object {obj.Name!r} has {len(property_names)} properties; "
                f"the rollback limit is {_MAX_MESH_ROLLBACK_PROPERTIES}."
            )
        properties = {}
        property_bytes = 0
        for name in property_names:
            if name in {"Shape", "ExpressionEngine"}:
                continue
            try:
                content = bytes(obj.dumpPropertyContent(name))
            except Exception as exc:
                raise RuntimeError(
                    f"MeshPart object {obj.Name!r} property {name!r} cannot be "
                    f"captured for rollback: {type(exc).__name__}: {exc}"
                ) from exc
            property_bytes += len(content)
            if property_bytes > _MAX_MESH_ROLLBACK_PROPERTY_BYTES:
                raise RuntimeError(
                    f"MeshPart object {obj.Name!r} rollback properties exceed "
                    f"{_MAX_MESH_ROLLBACK_PROPERTY_BYTES} serialized bytes."
                )
            properties[name] = {
                "type": str(obj.getTypeIdOfProperty(name) or ""),
                "group": str(obj.getGroupOfProperty(name) or ""),
                "documentation": str(obj.getDocumentationOfProperty(name) or ""),
                "editor_modes": list(obj.getEditorMode(name) or []),
                "content": content,
            }
        shape = obj.Shape.copy()
        if shape.isNull() or not shape.isValid():
            raise RuntimeError(
                f"MeshPart object {obj.Name!r} has no valid accepted Shape to roll back."
            )
        brep = shape.exportBrepToString()
        brep_bytes = brep.encode("utf-8")
        if len(brep_bytes) > _MAX_SHAPE_ROLLBACK_BREP_BYTES:
            raise RuntimeError(
                f"MeshPart object {obj.Name!r} accepted BREP exceeds the bounded "
                "rollback serialization limit."
            )
        states.append(
            {
                "document": obj.Document,
                "name": str(obj.Name),
                "label": str(obj.Label),
                "shape": shape,
                "shape_type": str(shape.ShapeType),
                "shape_brep_sha256": hashlib.sha256(brep_bytes).hexdigest(),
                "properties": properties,
                "expressions": [
                    [str(path), str(expression)]
                    for path, expression in list(obj.ExpressionEngine or [])
                ],
            }
        )
    return states


def _restore_meshpart_shape_rollback_states(
    states: list[dict[str, Any]],
) -> list[str]:
    failures = []
    restored = []
    resolved = []
    for state in states:
        document = state["document"]
        name = str(state["name"])
        obj = document.getObject(name)
        try:
            if obj is None:
                obj = document.addObject("Part::Feature", name)
            if (
                obj is None
                or str(obj.Name) != name
                or str(obj.TypeId) != "Part::Feature"
            ):
                raise RuntimeError("native Part identity could not be restored")
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
            obj.Shape = state["shape"].copy()
            restored_brep_sha256 = hashlib.sha256(
                obj.Shape.exportBrepToString().encode("utf-8")
            ).hexdigest()
            if (
                obj.Shape.isNull()
                or not obj.Shape.isValid()
                or str(obj.Shape.ShapeType) != state["shape_type"]
                or restored_brep_sha256 != state["shape_brep_sha256"]
            ):
                raise RuntimeError("restored native Shape does not match accepted state")
            if [
                [str(path), str(expression)]
                for path, expression in list(obj.ExpressionEngine or [])
            ] != state["expressions"]:
                raise RuntimeError(
                    "restored MeshPart expressions do not match accepted state"
                )
            restored.append(name)
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError(
            "MeshPart operation failed and accepted Part state could not be fully "
            f"restored: {'; '.join(failures)}"
        )
    return restored


def _reverse_feature_rollback_states(objects: list[Any]) -> list[dict[str, Any]]:
    """Capture stable fit-metrics carriers for explicit rollback/recreation."""

    states = []
    for obj in objects:
        if str(getattr(obj, "TypeId", "") or "") != "App::FeaturePython":
            continue
        property_names = list(getattr(obj, "PropertiesList", []) or [])
        if len(property_names) > _MAX_MESH_ROLLBACK_PROPERTIES:
            raise RuntimeError(
                f"Reverse Engineering metrics object {obj.Name!r} has too many "
                "properties for bounded rollback."
            )
        properties = {}
        property_bytes = 0
        for name in property_names:
            if name == "ExpressionEngine":
                continue
            content = bytes(obj.dumpPropertyContent(name))
            property_bytes += len(content)
            if property_bytes > _MAX_MESH_ROLLBACK_PROPERTY_BYTES:
                raise RuntimeError(
                    f"Reverse Engineering metrics object {obj.Name!r} rollback "
                    "properties exceed the bounded serialization limit."
                )
            properties[name] = {
                "type": str(obj.getTypeIdOfProperty(name) or ""),
                "group": str(obj.getGroupOfProperty(name) or ""),
                "documentation": str(obj.getDocumentationOfProperty(name) or ""),
                "editor_modes": list(obj.getEditorMode(name) or []),
                "content": content,
                "content_sha256": _property_content_sha256(content),
            }
        states.append(
            {
                "document": obj.Document,
                "name": str(obj.Name),
                "label": str(obj.Label),
                "properties": properties,
                "expressions": [
                    [str(path), str(expression)]
                    for path, expression in list(obj.ExpressionEngine or [])
                ],
            }
        )
    return states


def _restore_reverse_feature_rollback_states(
    states: list[dict[str, Any]],
) -> list[str]:
    failures = []
    restored = []
    for state in states:
        document = state["document"]
        name = str(state["name"])
        try:
            obj = document.getObject(name)
            if obj is None:
                obj = document.addObject("App::FeaturePython", name)
            if (
                obj is None
                or str(obj.Name) != name
                or str(obj.TypeId) != "App::FeaturePython"
            ):
                raise RuntimeError("native fit-metrics identity could not be restored")
            for property_name, captured in state["properties"].items():
                if property_name not in _properties(obj):
                    obj.addProperty(
                        str(captured["type"]),
                        property_name,
                        str(captured["group"]),
                        str(captured["documentation"]),
                    )
            accepted_names = set(state["properties"])
            for property_name in list(_properties(obj)):
                if (
                    property_name not in accepted_names
                    and property_name != "ExpressionEngine"
                    and str(obj.getGroupOfProperty(property_name) or "") == "Cadex"
                ):
                    obj.removeProperty(property_name)
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
            for property_name, captured in state["properties"].items():
                if _property_content_sha256(
                    bytes(obj.dumpPropertyContent(property_name))
                ) != str(captured["content_sha256"]):
                    raise RuntimeError(
                        f"restored property {property_name!r} differs from accepted state"
                    )
            if [
                [str(path), str(expression)]
                for path, expression in list(obj.ExpressionEngine or [])
            ] != state["expressions"]:
                raise RuntimeError("restored fit-metrics expressions do not match")
            restored.append(name)
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError(
            "Reverse Engineering fit-metrics state could not be fully restored: "
            + "; ".join(failures)
        )
    return restored


def _inspection_rollback_states(objects: list[Any]) -> list[dict[str, Any]]:
    """Capture every accepted Inspection object for explicit bounded rollback."""

    states = []
    for obj in objects:
        type_id = str(getattr(obj, "TypeId", "") or "")
        if type_id not in {
            "Inspection::Feature",
            "Inspection::Group",
            "App::FeaturePython",
        }:
            continue
        property_names = list(getattr(obj, "PropertiesList", []) or [])
        if len(property_names) > _MAX_INSPECTION_ROLLBACK_PROPERTIES:
            raise RuntimeError(
                f"Inspection object {obj.Name!r} has {len(property_names)} "
                "properties; the rollback limit is "
                f"{_MAX_INSPECTION_ROLLBACK_PROPERTIES}."
            )
        excluded = {"ExpressionEngine", "Label"}
        if type_id == "Inspection::Feature":
            excluded.update(_INSPECTION_FEATURE_KERNEL_PROPERTIES)
        elif type_id == "Inspection::Group":
            excluded.add("Group")
        properties = {}
        property_bytes = 0
        for name in property_names:
            if name in excluded:
                continue
            try:
                content = bytes(obj.dumpPropertyContent(name))
            except Exception as exc:
                raise RuntimeError(
                    f"Inspection object {obj.Name!r} property {name!r} cannot be "
                    f"captured for rollback: {type(exc).__name__}: {exc}"
                ) from exc
            property_bytes += len(content)
            if property_bytes > _MAX_INSPECTION_ROLLBACK_PROPERTY_BYTES:
                raise RuntimeError(
                    f"Inspection object {obj.Name!r} rollback properties exceed "
                    f"{_MAX_INSPECTION_ROLLBACK_PROPERTY_BYTES} serialized bytes."
                )
            property_type = str(obj.getTypeIdOfProperty(name) or "")
            captured = {
                "type": property_type,
                "group": str(obj.getGroupOfProperty(name) or ""),
                "documentation": str(obj.getDocumentationOfProperty(name) or ""),
                "editor_modes": list(obj.getEditorMode(name) or []),
                "content": content,
                "content_sha256": _property_content_sha256(content),
                "deferred_link": property_type.startswith("App::PropertyLink"),
            }
            if property_type == "App::PropertyFloat":
                captured["exact_value"] = float(getattr(obj, name))
            elif property_type == "App::PropertyInteger":
                captured["exact_value"] = int(getattr(obj, name))
            elif property_type == "App::PropertyBool":
                captured["exact_value"] = bool(getattr(obj, name))
            elif property_type == "App::PropertyString":
                captured["exact_value"] = str(getattr(obj, name))
            properties[name] = captured

        kernel: dict[str, Any] = {}
        if type_id == "Inspection::Feature":
            if not _inspection_feature_is_frozen(obj):
                raise RuntimeError(
                    f"Inspection feature {obj.Name!r} is not protected from "
                    "synchronous recompute."
                )
            distances = array("f", (float(value) for value in obj.Distances))
            if not 1 <= len(distances) <= _MAX_INSPECTION_ROLLBACK_DISTANCES:
                raise RuntimeError(
                    f"Inspection feature {obj.Name!r} has {len(distances)} distances; "
                    "the rollback limit is "
                    f"{_MAX_INSPECTION_ROLLBACK_DISTANCES}."
                )
            actual = getattr(obj, "Actual", None)
            nominals = list(getattr(obj, "Nominals", []) or [])
            if actual is None or not nominals:
                raise RuntimeError(
                    f"Inspection feature {obj.Name!r} has no accepted actual/nominal graph."
                )
            kernel = {
                "actual": str(actual.Name),
                "nominals": [str(item.Name) for item in nominals],
                "search_radius": float(obj.SearchRadius),
                "thickness": float(obj.Thickness),
                "distances": distances,
                "distance_sha256": hashlib.sha256(distances.tobytes()).hexdigest(),
                "frozen": True,
            }
        elif type_id == "Inspection::Group":
            kernel = {
                "members": [
                    str(item.Name) for item in list(getattr(obj, "Group", []) or [])
                ]
            }
        states.append(
            {
                "document": obj.Document,
                "name": str(obj.Name),
                "type_id": type_id,
                "label": str(obj.Label),
                "properties": properties,
                "kernel": kernel,
                "expressions": [
                    [str(path), str(expression)]
                    for path, expression in list(obj.ExpressionEngine or [])
                ],
            }
        )
    return states


def _restore_inspection_rollback_states(
    states: list[dict[str, Any]],
) -> list[str]:
    """Restore/recreate an accepted Inspection graph without native recompute."""

    import Inspection

    del Inspection
    failures: list[str] = []
    resolved: list[tuple[Any, dict[str, Any]]] = []
    for state in states:
        document = state["document"]
        name = str(state["name"])
        type_id = str(state["type_id"])
        try:
            obj = document.getObject(name)
            if obj is None:
                obj = document.addObject(type_id, name)
            if (
                obj is None
                or str(obj.Name) != name
                or str(obj.TypeId) != type_id
            ):
                raise RuntimeError(
                    f"native identity/type {type_id!r} could not be restored"
                )
            if type_id == "Inspection::Feature":
                _unfreeze_inspection_feature(obj)
            for property_name, captured in state["properties"].items():
                if property_name not in _properties(obj):
                    obj.addProperty(
                        str(captured["type"]),
                        property_name,
                        str(captured["group"]),
                        str(captured["documentation"]),
                    )
                if str(obj.getTypeIdOfProperty(property_name) or "") != str(
                    captured["type"]
                ):
                    raise RuntimeError(
                        f"property {property_name!r} changed native type"
                    )
            accepted_names = set(state["properties"])
            for property_name in list(_properties(obj)):
                if (
                    property_name not in accepted_names
                    and property_name not in _INSPECTION_FEATURE_KERNEL_PROPERTIES
                    and property_name not in {"ExpressionEngine", "Group", "Label"}
                    and str(obj.getGroupOfProperty(property_name) or "") == "Cadex"
                ):
                    obj.removeProperty(property_name)
            resolved.append((obj, state))
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    for obj, state in resolved:
        name = str(state["name"])
        try:
            for property_name, captured in state["properties"].items():
                if captured["deferred_link"]:
                    continue
                obj.restorePropertyContent(
                    property_name,
                    bytearray(captured["content"]),
                )
                if "exact_value" in captured:
                    setattr(obj, property_name, captured["exact_value"])
                for mode in list(captured["editor_modes"]):
                    obj.setPropertyStatus(property_name, str(mode))
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    for obj, state in resolved:
        name = str(state["name"])
        try:
            if str(state["type_id"]) == "Inspection::Feature":
                kernel = state["kernel"]
                actual = obj.Document.getObject(str(kernel["actual"]))
                nominals = [
                    obj.Document.getObject(str(item)) for item in kernel["nominals"]
                ]
                if actual is None or any(item is None for item in nominals):
                    raise RuntimeError("accepted actual/nominal links disappeared")
                for property_name in (
                    "Actual",
                    "Nominals",
                    "SearchRadius",
                    "Thickness",
                ):
                    obj.setPropertyStatus(property_name, "NoRecompute")
                obj.Actual = actual
                obj.Nominals = nominals
                obj.SearchRadius = float(kernel["search_radius"])
                obj.Thickness = float(kernel["thickness"])
                obj.Distances = kernel["distances"].tolist()
            for property_name, captured in state["properties"].items():
                if not captured["deferred_link"]:
                    continue
                obj.restorePropertyContent(
                    property_name,
                    bytearray(captured["content"]),
                )
                for mode in list(captured["editor_modes"]):
                    obj.setPropertyStatus(property_name, str(mode))
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    for obj, state in resolved:
        name = str(state["name"])
        try:
            if str(state["type_id"]) == "Inspection::Group":
                members = [
                    obj.Document.getObject(str(item))
                    for item in state["kernel"]["members"]
                ]
                if any(item is None for item in members):
                    raise RuntimeError("accepted group membership disappeared")
                for current in list(getattr(obj, "Group", []) or []):
                    if not any(current is member for member in members):
                        obj.removeObject(current)
                for member in members:
                    if not any(current is member for current in list(obj.Group or [])):
                        obj.addObject(member)
            for path, _expression in list(obj.ExpressionEngine or []):
                obj.setExpression(str(path).lstrip("."), None)
            for path, expression in state["expressions"]:
                obj.setExpression(str(path).lstrip("."), str(expression))
            obj.Label = str(state["label"])
            if str(state["type_id"]) == "Inspection::Feature":
                _freeze_inspection_feature(obj)
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    for obj, state in resolved:
        name = str(state["name"])
        try:
            for property_name, captured in state["properties"].items():
                if _property_content_sha256(
                    bytes(obj.dumpPropertyContent(property_name))
                ) != str(captured["content_sha256"]):
                    raise RuntimeError(
                        f"restored property {property_name!r} differs from accepted state"
                    )
            if [
                [str(path), str(expression)]
                for path, expression in list(obj.ExpressionEngine or [])
            ] != state["expressions"]:
                raise RuntimeError("restored expressions differ from accepted state")
            if str(obj.Label) != str(state["label"]):
                raise RuntimeError("restored label differs from accepted state")
            if str(state["type_id"]) == "Inspection::Feature":
                kernel = state["kernel"]
                observed = array("f", (float(value) for value in obj.Distances))
                if (
                    str(getattr(obj.Actual, "Name", "")) != kernel["actual"]
                    or [str(item.Name) for item in list(obj.Nominals or [])]
                    != kernel["nominals"]
                    or float(obj.SearchRadius) != float(kernel["search_radius"])
                    or float(obj.Thickness) != float(kernel["thickness"])
                    or len(observed) != len(kernel["distances"])
                    or hashlib.sha256(observed.tobytes()).hexdigest()
                    != kernel["distance_sha256"]
                    or not _inspection_feature_is_frozen(obj)
                ):
                    raise RuntimeError(
                        "restored native distance state differs from accepted state"
                    )
            elif str(state["type_id"]) == "Inspection::Group":
                if [str(item.Name) for item in list(obj.Group or [])] != state[
                    "kernel"
                ]["members"]:
                    raise RuntimeError(
                        "restored native group membership differs from accepted state"
                    )
            restored_state = str(
                getattr(obj, reference_contracts.PROP_DERIVED_STATE, "") or ""
            )
            if restored_state and restored_state not in {"accepted", "stale"}:
                raise RuntimeError(
                    f"restored derived state {restored_state!r} is invalid"
                )
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError(
            "Inspection operation failed and accepted native state could not be "
            f"fully restored: {'; '.join(failures)}"
        )
    return [str(state["name"]) for _obj, state in resolved]


def _robot_placement_state(value: Any) -> dict[str, list[float]]:
    return {
        "position": [float(item) for item in value.Base],
        "rotation": [float(item) for item in value.Rotation.Q],
    }


def _robot_definition_kinematics(value: Any, object_name: str) -> list[list[float]]:
    if not isinstance(value, Mapping):
        raise RuntimeError(
            f"Robot object {object_name!r} has no accepted declarative definition."
        )
    properties = value.get("properties")
    axes = properties.get("kinematics") if isinstance(properties, Mapping) else None
    if not isinstance(axes, list) or len(axes) != 6:
        raise RuntimeError(
            f"Robot object {object_name!r} has malformed accepted kinematics."
        )
    fields = (
        "a",
        "alpha",
        "d",
        "theta",
        "rotation_direction",
        "maximum_angle",
        "minimum_angle",
        "maximum_velocity",
    )
    rows = []
    for index, axis in enumerate(axes):
        if not isinstance(axis, Mapping) or set(axis) != set(fields):
            raise RuntimeError(
                f"Robot object {object_name!r} kinematic row {index} is malformed."
            )
        rows.append([float(axis[field]) for field in fields])
    return _robot_kinematic_rows(rows)


def _robot_exact_property_value(
    obj: Any, name: str, property_type: str
) -> Any | None:
    if property_type in {
        "App::PropertyFloat",
        "App::PropertyAngle",
        "App::PropertyDistance",
        "App::PropertyLength",
        "App::PropertySpeed",
    }:
        return {"kind": "float", "value": float(getattr(obj, name))}
    if property_type in {"App::PropertyInteger", "App::PropertyIntegerConstraint"}:
        return {"kind": "integer", "value": int(getattr(obj, name))}
    if property_type == "App::PropertyBool":
        return {"kind": "bool", "value": bool(getattr(obj, name))}
    if property_type in {
        "App::PropertyString",
        "App::PropertyEnumeration",
        "App::PropertyFile",
        "App::PropertyFileIncluded",
    }:
        return {"kind": "string", "value": str(getattr(obj, name))}
    if property_type in {"App::PropertyFloatList", "App::PropertyAngleList"}:
        return {
            "kind": "float_list",
            "value": [float(item) for item in getattr(obj, name)],
        }
    if property_type == "App::PropertyStringList":
        return {
            "kind": "string_list",
            "value": [str(item) for item in getattr(obj, name)],
        }
    if property_type == "App::PropertyPlacement":
        return {
            "kind": "placement",
            "value": _robot_placement_state(getattr(obj, name)),
        }
    if property_type == "App::PropertyVector":
        return {
            "kind": "vector",
            "value": [float(item) for item in getattr(obj, name)],
        }
    return None


def _restore_robot_exact_property(obj: Any, name: str, captured: Any) -> None:
    if not isinstance(captured, Mapping):
        return
    kind = str(captured.get("kind") or "")
    value = captured.get("value")
    if kind in {"float", "integer", "bool", "string", "float_list", "string_list"}:
        setattr(obj, name, value)
    elif kind == "placement":
        setattr(obj, name, _placement(value))
    elif kind == "vector":
        setattr(obj, name, _native_vector(value, f"rollback property {name}"))


def _robot_rollback_states(objects: list[Any]) -> list[dict[str, Any]]:
    """Capture every accepted Robot object except its transferable trajectory."""

    allowed = {
        "Robot::RobotObject",
        "Robot::TrajectoryObject",
        "Robot::TrajectoryDressUpObject",
        "App::FeaturePython",
    }
    states = []
    for obj in objects:
        type_id = str(getattr(obj, "TypeId", "") or "")
        if type_id not in allowed:
            raise RuntimeError(
                f"Robot program object {obj.Name!r} has unsupported native type {type_id!r}."
            )
        if type_id == "Robot::TrajectoryDressUpObject" and not _robot_dressup_is_frozen(
            obj
        ):
            raise RuntimeError(
                f"Robot dress-up {obj.Name!r} is not protected from synchronous recompute."
            )
        if type_id == "Robot::RobotObject":
            for property_name in ("RobotKinematicFile", "RobotVrmlFile"):
                if str(getattr(obj, property_name, "") or ""):
                    raise RuntimeError(
                        f"Robot object {obj.Name!r} contains an external file in "
                        f"{property_name}; XScript Robot objects must remain self-contained."
                    )
        property_names = list(getattr(obj, "PropertiesList", []) or [])
        if len(property_names) > _MAX_ROBOT_ROLLBACK_PROPERTIES:
            raise RuntimeError(
                f"Robot object {obj.Name!r} has {len(property_names)} properties; "
                f"the rollback limit is {_MAX_ROBOT_ROLLBACK_PROPERTIES}."
            )
        excluded = {"ExpressionEngine", "Label", "Trajectory"}
        if type_id == "Robot::RobotObject":
            excluded.update({"Tcp", *(f"Axis{axis}" for axis in range(1, 7))})
        properties: dict[str, dict[str, Any]] = {}
        property_bytes = 0
        for name in property_names:
            if name in excluded:
                continue
            try:
                content = bytes(obj.dumpPropertyContent(name))
            except Exception as exc:
                raise RuntimeError(
                    f"Robot object {obj.Name!r} property {name!r} cannot be captured "
                    f"for rollback: {type(exc).__name__}: {exc}"
                ) from exc
            property_bytes += len(content)
            if property_bytes > _MAX_ROBOT_ROLLBACK_PROPERTY_BYTES:
                raise RuntimeError(
                    f"Robot object {obj.Name!r} rollback properties exceed "
                    f"{_MAX_ROBOT_ROLLBACK_PROPERTY_BYTES} serialized bytes."
                )
            property_type = str(obj.getTypeIdOfProperty(name) or "")
            properties[name] = {
                "type": property_type,
                "group": str(obj.getGroupOfProperty(name) or ""),
                "documentation": str(obj.getDocumentationOfProperty(name) or ""),
                "editor_modes": list(obj.getEditorMode(name) or []),
                "content": content,
                "content_sha256": _property_content_sha256(content),
                "deferred_link": property_type.startswith("App::PropertyLink"),
                "exact_value": _robot_exact_property_value(obj, name, property_type),
            }
        definition: dict[str, Any] | None = None
        if PROP_DEFINITION in _properties(obj):
            try:
                parsed = json.loads(str(getattr(obj, PROP_DEFINITION) or ""))
            except (TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"Robot object {obj.Name!r} has malformed accepted metadata."
                ) from exc
            if isinstance(parsed, dict):
                definition = parsed
        kernel: dict[str, Any] = {}
        if type_id == "Robot::RobotObject":
            kernel = {
                "kinematics": _robot_definition_kinematics(definition, str(obj.Name)),
                "axis_positions": [
                    float(getattr(obj, f"Axis{axis}")) for axis in range(1, 7)
                ],
                "tcp": _robot_placement_state(obj.Tcp),
            }
        states.append(
            {
                "document": obj.Document,
                "name": str(obj.Name),
                "type_id": type_id,
                "label": str(obj.Label),
                "properties": properties,
                "expressions": [
                    [str(path), str(expression)]
                    for path, expression in list(obj.ExpressionEngine or [])
                ],
                "kernel": kernel,
                "frozen": type_id == "Robot::TrajectoryDressUpObject",
            }
        )
    return states


def _extract_robot_trajectories(objects: list[Any]) -> list[dict[str, Any]]:
    """Move accepted trajectories into transient holders before native deletion."""

    import Robot

    extracted: list[dict[str, Any]] = []
    try:
        for obj in objects:
            if str(getattr(obj, "TypeId", "") or "") not in _ROBOT_TRAJECTORY_TYPES:
                continue
            holder = Robot.Trajectory()
            swapped = _swap_robot_trajectory(obj, holder)
            if swapped["installed"] != {
                "waypoint_count": 0,
                "length": 0.0,
                "duration": 0.0,
            }:
                raise RuntimeError(
                    f"Robot trajectory {obj.Name!r} did not enter an empty transfer state."
                )
            extracted.append(
                {
                    "object_name": str(obj.Name),
                    "object": obj,
                    "holder": holder,
                    "accepted_summary": dict(swapped["displaced"]),
                }
            )
    except Exception as extraction_error:
        failures = []
        for entry in reversed(extracted):
            try:
                restored = _swap_robot_trajectory(entry["object"], entry["holder"])
                if restored["installed"] != entry["accepted_summary"]:
                    raise RuntimeError("restored trajectory summary differs")
            except Exception as rollback_error:
                failures.append(
                    f"{entry['object_name']}: {type(rollback_error).__name__}: "
                    f"{rollback_error}"
                )
        if failures:
            raise RuntimeError(
                f"{extraction_error} Robot trajectory extraction rollback failed: "
                + "; ".join(failures)
            ) from extraction_error
        raise
    return extracted


def _restore_robot_rollback_states(
    states: list[dict[str, Any]],
    trajectory_holders: list[dict[str, Any]],
) -> list[str]:
    """Restore/recreate an accepted Robot graph using constant-time path swaps."""

    import Robot

    del Robot

    holder_by_name: dict[str, dict[str, Any]] = {}
    for entry in trajectory_holders:
        name = str(entry["object_name"])
        if name in holder_by_name:
            raise RuntimeError(f"Robot rollback has duplicate trajectory holder {name!r}.")
        holder_by_name[name] = entry

    failures: list[str] = []
    resolved: list[tuple[Any, dict[str, Any], bool]] = []
    for state in states:
        document = state["document"]
        name = str(state["name"])
        type_id = str(state["type_id"])
        try:
            obj = document.getObject(name)
            recreated = obj is None
            if obj is None:
                obj = document.addObject(type_id, name)
            if obj is None or str(obj.Name) != name or str(obj.TypeId) != type_id:
                raise RuntimeError(f"native identity/type {type_id!r} could not be restored")
            if type_id == "Robot::TrajectoryDressUpObject":
                _unfreeze_robot_dressup(obj)
            elif type_id == "Robot::RobotObject":
                _freeze_object(obj, "Robot rollback")
            for property_name, captured in state["properties"].items():
                if property_name not in _properties(obj):
                    obj.addProperty(
                        str(captured["type"]),
                        property_name,
                        str(captured["group"]),
                        str(captured["documentation"]),
                    )
                if str(obj.getTypeIdOfProperty(property_name) or "") != str(
                    captured["type"]
                ):
                    raise RuntimeError(f"property {property_name!r} changed native type")
            accepted_names = set(state["properties"])
            protected = {
                "ExpressionEngine",
                "Label",
                "Trajectory",
                "Tcp",
                *(f"Axis{axis}" for axis in range(1, 7)),
            }
            for property_name in list(_properties(obj)):
                if (
                    property_name not in accepted_names
                    and property_name not in protected
                    and str(obj.getGroupOfProperty(property_name) or "") == "Cadex"
                ):
                    obj.removeProperty(property_name)
            if recreated and type_id in _ROBOT_TRAJECTORY_TYPES and name not in holder_by_name:
                raise RuntimeError("accepted trajectory data has no rollback holder")
            resolved.append((obj, state, recreated))
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    for obj, state, _recreated in resolved:
        name = str(state["name"])
        try:
            for property_name, captured in state["properties"].items():
                if captured["deferred_link"]:
                    continue
                obj.restorePropertyContent(property_name, bytearray(captured["content"]))
                _restore_robot_exact_property(
                    obj, property_name, captured.get("exact_value")
                )
                for mode in list(captured["editor_modes"]):
                    obj.setPropertyStatus(property_name, str(mode))
            if str(state["type_id"]) == "Robot::RobotObject":
                for axis, value in enumerate(
                    state["kernel"]["axis_positions"], start=1
                ):
                    setattr(obj, f"Axis{axis}", float(value))
                obj.setKinematic(state["kernel"]["kinematics"])
                obj.Tcp = _placement(state["kernel"]["tcp"])
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    for obj, state, _recreated in resolved:
        name = str(state["name"])
        try:
            for property_name, captured in state["properties"].items():
                if not captured["deferred_link"]:
                    continue
                obj.restorePropertyContent(property_name, bytearray(captured["content"]))
                for mode in list(captured["editor_modes"]):
                    obj.setPropertyStatus(property_name, str(mode))
            holder = holder_by_name.get(name)
            if holder is not None:
                swapped = _swap_robot_trajectory(obj, holder["holder"])
                if swapped["installed"] != holder["accepted_summary"]:
                    raise RuntimeError("restored native trajectory summary differs")
            for path, _expression in list(obj.ExpressionEngine or []):
                obj.setExpression(str(path).lstrip("."), None)
            for path, expression in state["expressions"]:
                obj.setExpression(str(path).lstrip("."), str(expression))
            obj.Label = str(state["label"])
            if str(state["type_id"]) == "Robot::TrajectoryDressUpObject":
                _freeze_robot_dressup(obj)
            elif str(state["type_id"]) == "Robot::RobotObject":
                obj.unfreeze(True)
                obj.purgeTouched()
                if obj.isFrozen():
                    raise RuntimeError("restored robot remained frozen")
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    for obj, state, _recreated in resolved:
        name = str(state["name"])
        try:
            for property_name, captured in state["properties"].items():
                if _property_content_sha256(
                    bytes(obj.dumpPropertyContent(property_name))
                ) != str(captured["content_sha256"]):
                    raise RuntimeError(
                        f"restored property {property_name!r} differs from accepted state"
                    )
            if [
                [str(path), str(expression)]
                for path, expression in list(obj.ExpressionEngine or [])
            ] != state["expressions"]:
                raise RuntimeError("restored expressions differ from accepted state")
            if str(obj.Label) != str(state["label"]):
                raise RuntimeError("restored label differs from accepted state")
            if str(state["type_id"]) == "Robot::RobotObject":
                expected_axes = state["kernel"]["axis_positions"]
                observed_axes = [
                    float(getattr(obj, f"Axis{axis}")) for axis in range(1, 7)
                ]
                if any(
                    not math.isclose(left, right, rel_tol=1.0e-10, abs_tol=1.0e-8)
                    for left, right in zip(observed_axes, expected_axes)
                ) or not _robot_placement_matches(obj.Tcp, state["kernel"]["tcp"]):
                    raise RuntimeError("restored robot axes/TCP differ from accepted state")
            if str(state["type_id"]) == "Robot::TrajectoryDressUpObject" and not (
                _robot_dressup_is_frozen(obj)
            ):
                raise RuntimeError("restored dress-up is not frozen")
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError(
            "Robot operation failed and accepted native state could not be fully "
            f"restored: {'; '.join(failures)}"
        )
    return [str(state["name"]) for _obj, state, _recreated in resolved]


_FEM_RESULT_FLOAT_LISTS = (
    "CriticalStrainRatio",
    "DisplacementLengths",
    "MassFlowRate",
    "MaxShear",
    "MohrCoulomb",
    "NetworkPressure",
    "NodeStrainXX",
    "NodeStrainXY",
    "NodeStrainXZ",
    "NodeStrainYY",
    "NodeStrainYZ",
    "NodeStrainZZ",
    "NodeStressXX",
    "NodeStressXY",
    "NodeStressXZ",
    "NodeStressYY",
    "NodeStressYZ",
    "NodeStressZZ",
    "Peeq",
    "PrincipalMax",
    "PrincipalMed",
    "PrincipalMin",
    "ReinforcementRatio_x",
    "ReinforcementRatio_y",
    "ReinforcementRatio_z",
    "Stats",
    "Temperature",
    "UserDefined",
    "vonMises",
)
_FEM_RESULT_VECTOR_LISTS = (
    "DisplacementVectors",
    "HeatFlux",
    "PS1Vector",
    "PS2Vector",
    "PS3Vector",
)
_FEM_PROPERTIES_BY_TYPE = {
    "Fem::FemAnalysis": ("Group",),
    "Fem::FemSolverObjectPython": (
        "AnalysisType",
        "MatrixSolverType",
        "GeometricalNonlinearity",
        "MaterialNonlinearity",
        "ReducedIntegration",
        "SplitInputWriter",
        "WorkingDir",
        "WorkingDirectory",
    ),
    "App::MaterialObjectPython": (
        "Category",
        "Material",
        "References",
        "MaterialName",
        "UUID",
        "Suppressed",
    ),
    "Fem::ConstraintFixed": ("References", "Suppressed"),
    "Fem::ConstraintForce": (
        "References",
        "Force",
        "Direction",
        "DirectionVector",
        "Reversed",
        "Suppressed",
    ),
    "Fem::ConstraintPressure": (
        "References",
        "Pressure",
        "Reversed",
        "Suppressed",
    ),
    "App::DocumentObjectGroup": ("Group", "CadexConstraints"),
    "Fem::FemMeshShapeBaseObjectPython": (
        "FemMesh",
        "Shape",
        "ElementOrder",
        "ElementDimension",
        "CharacteristicLengthMax",
        "CharacteristicLengthMin",
        "WorkingDirectory",
        "Suppressed",
    ),
    "Fem::FemResultObjectPython": (
        "Mesh",
        "NodeNumbers",
        *_FEM_RESULT_FLOAT_LISTS,
        *_FEM_RESULT_VECTOR_LISTS,
        "Time",
        "Eigenmode",
        "EigenmodeFrequency",
        "CadexAnalysisObjectName",
        "CadexFEMStatus",
        "CadexSolverExecuted",
        "CadexInputDeckSHA256",
    ),
}


def _fem_link_name(value: Any) -> str:
    return str(getattr(value, "Name", "") or "") if value is not None else ""


def _fem_capture_property(obj: Any, name: str) -> dict[str, Any]:
    property_type = str(obj.getTypeIdOfProperty(name) or "")
    value = getattr(obj, name)
    if property_type == "Fem::PropertyFemMesh":
        captured = value.copy()
    elif property_type in {"App::PropertyLink", "App::PropertyLinkGlobal"}:
        captured = _fem_link_name(value)
    elif property_type in {"App::PropertyLinkList", "App::PropertyLinkListGlobal"}:
        captured = [_fem_link_name(item) for item in list(value or [])]
    elif property_type in {"App::PropertyLinkSub", "App::PropertyLinkSubGlobal"}:
        if value is None:
            captured = None
        else:
            target, subelements = value
            captured = {
                "object": _fem_link_name(target),
                "subelements": [str(item) for item in list(subelements or [])],
            }
    elif property_type in {
        "App::PropertyLinkSubList",
        "App::PropertyLinkSubListGlobal",
    }:
        captured = [
            {
                "object": _fem_link_name(target),
                "subelements": [str(item) for item in list(subelements or [])],
            }
            for target, subelements in list(value or [])
        ]
    elif property_type == "App::PropertyMap":
        captured = dict(value or {})
    elif property_type == "App::PropertyVector":
        captured = [float(value.x), float(value.y), float(value.z)]
    elif property_type == "App::PropertyVectorList":
        captured = [[float(item.x), float(item.y), float(item.z)] for item in value]
    elif property_type in {
        "App::PropertyForce",
        "App::PropertyPressure",
        "App::PropertyLength",
        "App::PropertyFrequency",
        "App::PropertyTime",
        "App::PropertyQuantity",
    }:
        captured = str(value)
    elif property_type.endswith("List"):
        captured = list(value or [])
    elif isinstance(value, (str, bool, int, float)) or value is None:
        captured = value
    else:
        raise RuntimeError(
            f"Cannot capture FEM rollback property {obj.Name}.{name} of type "
            f"{property_type!r}."
        )
    return {"type": property_type, "value": captured}


def _fem_resolve_link(doc: Any, name: str, context: str) -> Any:
    if not name:
        return None
    target = doc.getObject(name)
    if target is None:
        raise RuntimeError(f"{context} target {name!r} is unavailable during rollback.")
    return target


def _fem_restore_property(doc: Any, obj: Any, name: str, state: Mapping[str, Any]) -> None:
    property_type = str(state["type"])
    value = state["value"]
    if name not in _properties(obj):
        if name.startswith("Cadex"):
            obj.addProperty(property_type, name, "Cadex", "Restored Cadex state.")
        else:
            raise RuntimeError(
                f"Restored native FEM object {obj.Name!r} has no property {name!r}."
            )
    if property_type == "Fem::PropertyFemMesh":
        restored = value.copy()
    elif property_type in {"App::PropertyLink", "App::PropertyLinkGlobal"}:
        restored = _fem_resolve_link(doc, str(value or ""), f"{obj.Name}.{name}")
    elif property_type in {"App::PropertyLinkList", "App::PropertyLinkListGlobal"}:
        restored = [
            _fem_resolve_link(doc, str(item), f"{obj.Name}.{name}") for item in value
        ]
    elif property_type in {"App::PropertyLinkSub", "App::PropertyLinkSubGlobal"}:
        restored = (
            None
            if value is None
            else (
                _fem_resolve_link(
                    doc, str(value["object"]), f"{obj.Name}.{name}"
                ),
                list(value["subelements"]),
            )
        )
    elif property_type in {
        "App::PropertyLinkSubList",
        "App::PropertyLinkSubListGlobal",
    }:
        restored = [
            (
                _fem_resolve_link(
                    doc, str(item["object"]), f"{obj.Name}.{name}"
                ),
                list(item["subelements"]),
            )
            for item in value
        ]
    elif property_type == "App::PropertyVector":
        import FreeCAD as App

        restored = App.Vector(*value)
    elif property_type == "App::PropertyVectorList":
        import FreeCAD as App

        restored = [App.Vector(*item) for item in value]
    elif property_type == "App::PropertyMap":
        restored = dict(value)
    else:
        restored = value
    setattr(obj, name, restored)


def _fem_rollback_states(objects: list[Any]) -> list[dict[str, Any]]:
    states = []
    for obj in objects:
        type_id = str(getattr(obj, "TypeId", "") or "")
        output_type = str(getattr(obj, PROP_OUTPUT_TYPE, "") or "")
        if output_type not in {
            "analysis",
            "solver",
            "material",
            "constraint",
            "load_case",
            "mesh",
            "result",
        }:
            continue
        property_names = set(_FEM_PROPERTIES_BY_TYPE.get(type_id, ()))
        property_names.update(
            name
            for name in list(getattr(obj, "PropertiesList", []) or [])
            if str(obj.getGroupOfProperty(name) or "") == "Cadex"
        )
        captured = {}
        for name in sorted(property_names):
            if name not in _properties(obj):
                continue
            property_type = str(obj.getTypeIdOfProperty(name) or "")
            if property_type in {
                "App::PropertyPythonObject",
                "App::PropertyExpressionEngine",
            }:
                continue
            captured[name] = _fem_capture_property(obj, name)
        dynamic = {}
        for name in sorted(_properties(obj)):
            if name in captured or name in {"ExpressionEngine", "Proxy"}:
                continue
            try:
                statuses = list(obj.getPropertyStatus(name) or [])
            except Exception:
                statuses = []
            # PropDynamic is status bit 21. It is intentionally returned as an
            # integer because PropertyContainerPy exposes names only for mutable
            # status flags, not the static property-type bits.
            if 21 not in statuses and "PropDynamic" not in statuses:
                continue
            property_type = str(obj.getTypeIdOfProperty(name) or "")
            if property_type in {
                "App::PropertyPythonObject",
                "App::PropertyExpressionEngine",
            }:
                continue
            dynamic[name] = {
                **_fem_capture_property(obj, name),
                "group": str(obj.getGroupOfProperty(name) or "Human"),
                "documentation": str(obj.getDocumentationOfProperty(name) or ""),
                "statuses": [
                    value
                    for value in statuses
                    if value not in {21, "PropDynamic"}
                ],
            }
        states.append(
            {
                "name": str(obj.Name),
                "label": str(obj.Label),
                "type_id": type_id,
                "output_type": output_type,
                "definition": str(getattr(obj, PROP_DEFINITION, "{}") or "{}"),
                "properties": captured,
                "dynamic_properties": dynamic,
                "expressions": [
                    (str(path), str(expression))
                    for path, expression in list(obj.ExpressionEngine or [])
                ],
            }
        )
    return states


def _fem_recreate_object(doc: Any, state: Mapping[str, Any]) -> Any:
    import ObjectsFem

    name = str(state["name"])
    type_id = str(state["type_id"])
    if type_id == "Fem::FemAnalysis":
        return ObjectsFem.makeAnalysis(doc, name)
    if type_id == "Fem::FemSolverObjectPython":
        return ObjectsFem.makeSolverCalculiXCcxTools(doc, name)
    if type_id == "App::MaterialObjectPython":
        return ObjectsFem.makeMaterialSolid(doc, name)
    if type_id == "Fem::ConstraintFixed":
        return ObjectsFem.makeConstraintFixed(doc, name)
    if type_id == "Fem::ConstraintForce":
        return ObjectsFem.makeConstraintForce(doc, name)
    if type_id == "Fem::ConstraintPressure":
        return ObjectsFem.makeConstraintPressure(doc, name)
    if type_id == "App::DocumentObjectGroup":
        return doc.addObject(type_id, name)
    if type_id == "Fem::FemMeshShapeBaseObjectPython":
        return ObjectsFem.makeMeshGmsh(doc, name)
    if type_id == "Fem::FemResultObjectPython":
        return ObjectsFem.makeResultMechanical(doc, name)
    raise RuntimeError(f"Cannot recreate unsupported native FEM type {type_id!r}.")


def _restore_fem_rollback_states(doc: Any, states: list[dict[str, Any]]) -> list[str]:
    resolved: list[tuple[Any, dict[str, Any]]] = []
    failures = []
    for state in states:
        name = str(state["name"])
        try:
            obj = doc.getObject(name)
            if obj is None:
                obj = _fem_recreate_object(doc, state)
            if str(getattr(obj, "TypeId", "") or "") != str(state["type_id"]):
                raise RuntimeError(
                    f"native type changed to {getattr(obj, 'TypeId', '')!r}"
                )
            if str(obj.Name) != name:
                raise RuntimeError(f"stable name changed to {obj.Name!r}")
            resolved.append((obj, state))
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError(f"Could not recreate FEM rollback objects: {'; '.join(failures)}")
    # Restore independent kernels/scalars first, links and groups second.
    for obj, state in resolved:
        for name, property_state in dict(state["dynamic_properties"]).items():
            if name not in _properties(obj):
                obj.addProperty(
                    str(property_state["type"]),
                    name,
                    str(property_state["group"]),
                    str(property_state["documentation"]),
                )
    for links in (False, True):
        for obj, state in resolved:
            property_states = {
                **dict(state["properties"]),
                **dict(state["dynamic_properties"]),
            }
            for name, property_state in property_states.items():
                is_link = str(property_state["type"]).startswith("App::PropertyLink")
                if is_link != links:
                    continue
                try:
                    _fem_restore_property(doc, obj, name, property_state)
                except Exception as exc:
                    failures.append(
                        f"{obj.Name}.{name}: {type(exc).__name__}: {exc}"
                    )
    for obj, state in resolved:
        try:
            obj.Label = str(state["label"])
            for path, _expression in list(obj.ExpressionEngine or []):
                obj.setExpression(str(path), None)
            for path, expression in state["expressions"]:
                obj.setExpression(str(path), str(expression))
            for name, property_state in dict(state["dynamic_properties"]).items():
                statuses = list(property_state.get("statuses") or [])
                if statuses:
                    obj.setPropertyStatus(name, statuses)
        except Exception as exc:
            failures.append(f"{obj.Name}.expressions: {type(exc).__name__}: {exc}")
    if failures:
        raise RuntimeError(
            "FEM operation failed and accepted native state could not be fully "
            f"restored: {'; '.join(failures)}"
        )
    return [str(state["name"]) for _obj, state in resolved]


def _fem_data(item: Mapping[str, Any]) -> dict[str, Any]:
    data = item.get("fem_data")
    if not isinstance(data, dict):
        raise RuntimeError(f"FEM output {item.get('name')!r} has no native readback.")
    return dict(data)


def _fem_reference_target(doc: Any, value: Mapping[str, Any], label: str) -> Any:
    reference = {
        "document_uid": str(value.get("document_uid") or ""),
        "object_name": str(value.get("object_name") or ""),
    }
    target = _reference_target(doc, reference, label)
    expected_type = str(value.get("source_type_id") or "")
    if expected_type and str(getattr(target, "TypeId", "") or "") != expected_type:
        raise RuntimeError(
            f"{label} changed native type from {expected_type!r} to "
            f"{getattr(target, 'TypeId', '')!r}."
        )
    expected_revision = str(value.get("source_revision") or "")
    if expected_revision:
        live_revision = str(
            getattr(target, contracts.PROP_PROGRAM_REVISION, "")
            or getattr(target, reference_contracts.PROP_SOURCE_REVISION, "")
            or ""
        )
        if live_revision and live_revision != expected_revision:
            raise RuntimeError(
                f"{label} changed revision after isolated FEM validation."
            )
    return target


def _fem_validation_summary(data: Mapping[str, Any]) -> dict[str, Any]:
    summary = {
        key: value
        for key, value in data.items()
        if key not in {"nodes", "elements", "result_values"}
    }
    if isinstance(data.get("facts"), Mapping):
        summary["facts"] = dict(data["facts"])
    result_values = data.get("result_values")
    if isinstance(result_values, Mapping):
        summary["result_summary"] = {
            "node_count": len(list(result_values.get("node_numbers") or [])),
            "float_fields": sorted(dict(result_values.get("float_lists") or {})),
            "vector_fields": sorted(dict(result_values.get("vector_lists") or {})),
            "scalar_value_count": int(result_values.get("scalar_value_count") or 0),
            "time": float(result_values.get("time") or 0.0),
            "eigenmode": int(result_values.get("eigenmode") or 0),
            "eigenmode_frequency": float(
                result_values.get("eigenmode_frequency") or 0.0
            ),
        }
    return summary


def _configure_fem(
    doc: Any,
    obj: Any,
    item: Mapping[str, Any],
    outputs: Mapping[str, Any],
) -> None:
    import FreeCAD as App

    output_type = str(item["type"])
    data = _fem_data(item)
    definition = _definition(item)
    properties = dict(definition.get("properties") or {})
    if output_type == "solver":
        obj.AnalysisType = str(data["analysis_type"])
        obj.MatrixSolverType = str(data["matrix_solver"])
        obj.GeometricalNonlinearity = bool(data["geometrical_nonlinearity"])
        obj.MaterialNonlinearity = bool(data["material_nonlinearity"])
        obj.ReducedIntegration = bool(data["reduced_integration"])
        obj.SplitInputWriter = False
        obj.WorkingDir = ""
        obj.WorkingDirectory = ""
    elif output_type == "material":
        obj.Category = "Solid"
        obj.Material = dict(data["material"])
        references = []
        for assignment_index, assignment in enumerate(data.get("assignments") or []):
            if not isinstance(assignment, Mapping):
                raise RuntimeError(
                    f"FEM material {item['name']!r} assignment {assignment_index} is malformed."
                )
            target = _fem_reference_target(
                doc,
                assignment["target"],
                f"FEM material {item['name']!r} assignment {assignment_index}",
            )
            subelements = [
                str(value) for value in assignment["resolved_subelements"]
            ]
            if not subelements:
                raise RuntimeError(
                    f"FEM material {item['name']!r} assignment {assignment_index} is empty."
                )
            references.append((target, subelements))
        obj.References = references
    elif output_type == "constraint":
        target = _fem_reference_target(
            doc,
            data["target"],
            f"FEM constraint {item['name']!r} target",
        )
        subelements = [str(value) for value in data["resolved_subelements"]]
        obj.References = [(target, subelements)]
        kind = str(data["kind"])
        if kind == "force":
            obj.Force = f"{float(data['magnitude']):.17g} N"
            obj.DirectionVector = App.Vector(*data["direction"])
            obj.Reversed = bool(data["reversed"])
        elif kind == "pressure":
            obj.Pressure = f"{float(data['magnitude']):.17g} MPa"
            obj.Reversed = bool(data["reversed"])
    elif output_type == "load_case":
        members = []
        for name in data["constraint_outputs"]:
            member = outputs.get(str(name))
            if member is None or str(getattr(member, "TypeId", "")) not in {
                "Fem::ConstraintFixed",
                "Fem::ConstraintForce",
                "Fem::ConstraintPressure",
            }:
                raise RuntimeError(
                    f"FEM load case {item['name']!r} constraint {name!r} is unavailable."
                )
            members.append(member)
        obj.Group = []
        _add_property(
            obj,
            "App::PropertyLinkList",
            "CadexConstraints",
            "Exact stable constraints in this XScript load case.",
        )
        obj.CadexConstraints = members
    elif output_type == "mesh":
        source = _fem_reference_target(
            doc,
            data["source"],
            f"FEM mesh {item['name']!r} source",
        )
        detached = item.get("detached_fem_mesh")
        if detached is None:
            raise RuntimeError(f"FEM mesh {item['name']!r} has no detached native mesh.")
        obj.Shape = source
        obj.FemMesh = detached
        obj.ElementOrder = "2nd" if int(data["order"]) == 2 else "1st"
        obj.WorkingDirectory = ""
        method = str(data["method"])
        if method == "gmsh":
            obj.CharacteristicLengthMax = (
                f"{float(properties['maximum_size']):.17g} mm"
            )
            obj.CharacteristicLengthMin = (
                f"{float(properties['minimum_size']):.17g} mm"
            )
        else:
            element_type = str(properties["element_type"])
            obj.ElementDimension = (
                "1D"
                if element_type.startswith("edge")
                else "2D"
                if element_type.startswith(("triangle", "quad"))
                else "3D"
            )
    elif output_type == "analysis":
        names = [
            str(data["solver_output"]),
            *[str(value) for value in data["material_outputs"]],
            *[str(value) for value in data["constraint_outputs"]],
            *[str(value) for value in data["load_case_outputs"]],
            str(data["mesh_output"]),
        ]
        members = []
        for name in names:
            member = outputs.get(name)
            if member is None:
                raise RuntimeError(
                    f"FEM analysis {item['name']!r} member {name!r} is unavailable."
                )
            if member not in members:
                members.append(member)
        obj.Group = members
    elif output_type == "result":
        mesh_name = str(data["mesh_output"])
        analysis_name = str(data["analysis_output"])
        mesh = outputs.get(mesh_name)
        analysis = outputs.get(analysis_name)
        if mesh is None or str(getattr(mesh, "TypeId", "")) != (
            "Fem::FemMeshShapeBaseObjectPython"
        ):
            raise RuntimeError(f"FEM result {item['name']!r} mesh is unavailable.")
        if analysis is None or str(getattr(analysis, "TypeId", "")) != "Fem::FemAnalysis":
            raise RuntimeError(f"FEM result {item['name']!r} analysis is unavailable.")
        values = dict(data["result_values"])
        obj.Mesh = mesh
        obj.NodeNumbers = [int(value) for value in values["node_numbers"]]
        for name, sequence in dict(values["float_lists"]).items():
            if name not in _properties(obj):
                raise RuntimeError(
                    f"Native FEM result has no validated float-list property {name!r}."
                )
            setattr(obj, name, [float(value) for value in sequence])
        for name, sequence in dict(values["vector_lists"]).items():
            if name not in _properties(obj):
                raise RuntimeError(
                    f"Native FEM result has no validated vector-list property {name!r}."
                )
            setattr(obj, name, [App.Vector(*value) for value in sequence])
        obj.Time = float(values["time"])
        obj.Eigenmode = int(values["eigenmode"])
        obj.EigenmodeFrequency = float(values["eigenmode_frequency"])
        for property_type, name, value, description in (
            (
                "App::PropertyString",
                "CadexAnalysisObjectName",
                str(analysis.Name),
                "Stable native FEM analysis object name for this result.",
            ),
            (
                "App::PropertyString",
                "CadexFEMStatus",
                str(data["status"]),
                "Authenticated worker solve or input-validation status.",
            ),
            (
                "App::PropertyBool",
                "CadexSolverExecuted",
                bool(data["solver_executed"]),
                "Whether CalculiX was actually executed in the worker.",
            ),
            (
                "App::PropertyString",
                "CadexInputDeckSHA256",
                str(data["input_deck"]["artifact_sha256"]),
                "SHA-256 of the authenticated CalculiX input deck.",
            ),
        ):
            _add_property(obj, property_type, name, description)
            setattr(obj, name, value)
        if obj not in list(analysis.Group):
            analysis.addObject(obj)
    else:
        raise RuntimeError(f"No FEM publisher exists for output type {output_type!r}.")
    _add_string_property(
        obj,
        PROP_FEM_VALIDATION,
        "Authenticated bounded native FEM graph and validation summary.",
    )
    setattr(
        obj,
        PROP_FEM_VALIDATION,
        json.dumps(
            _fem_validation_summary(data),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
    )


def _configure_object(
    doc: Any,
    obj: Any,
    item: Mapping[str, Any],
    outputs: Mapping[str, Any],
    prepared: Mapping[str, Any],
    robot_trajectory_swaps: list[dict[str, Any]],
) -> None:
    output_type = str(item["type"])
    if prepared["pack"].domain == "surface":
        _configure_surface(obj, item)
    elif prepared["pack"].domain == "mesh":
        _configure_mesh(obj, item)
    elif prepared["pack"].domain == "meshpart" and output_type == "mesh":
        _configure_mesh(
            obj,
            item,
            data_key="meshpart_data",
            validation_property=PROP_MESHPART_VALIDATION,
        )
    elif prepared["pack"].domain == "meshpart":
        _configure_meshpart_shape(obj, item)
    elif prepared["pack"].domain == "points":
        _configure_points(obj, item)
    elif prepared["pack"].domain == "reverse_engineering":
        _configure_reverse_engineering(obj, item)
    elif prepared["pack"].domain == "inspection":
        _configure_inspection(doc, obj, item, outputs)
    elif prepared["pack"].domain == "robot":
        _configure_robot(obj, item, outputs, robot_trajectory_swaps)
    elif prepared["pack"].domain == "fem":
        _configure_fem(doc, obj, item, outputs)
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
    if str(service.provider_document_revision()) != prepared["document_revision"]:
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
        if prepared["pack"].domain in {"mesh", "meshpart", "reverse_engineering"}
        else []
    )
    meshpart_shape_rollbacks = (
        _meshpart_shape_rollback_states(internal_objects)
        if prepared["pack"].domain in {"meshpart", "reverse_engineering"}
        else []
    )
    points_rollbacks = (
        _points_rollback_states(internal_objects)
        if prepared["pack"].domain == "points"
        else []
    )
    reverse_feature_rollbacks = (
        _reverse_feature_rollback_states(internal_objects)
        if prepared["pack"].domain == "reverse_engineering"
        else []
    )
    inspection_rollbacks = (
        _inspection_rollback_states(internal_objects)
        if prepared["pack"].domain == "inspection"
        else []
    )
    robot_rollbacks = (
        _robot_rollback_states(internal_objects)
        if prepared["pack"].domain == "robot"
        else []
    )
    fem_rollbacks = (
        _fem_rollback_states(internal_objects)
        if prepared["pack"].domain == "fem"
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
    robot_trajectory_swaps: list[dict[str, Any]] = []
    retired_robot_trajectories: list[dict[str, Any]] = []
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
                else _native_type(output_type, prepared["pack"].domain)
            )
            if prepared["pack"].domain == "fem":
                expected_native = str(_fem_data(item).get("native_type") or "")
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
        elif prepared["pack"].domain == "inspection":
            priority = {
                "inspection_feature": 0,
                "measurement": 1,
                "inspection_group": 2,
                "report": 3,
            }
            configure_order.sort(
                key=lambda item: priority.get(str(item["type"]), 4)
            )
        elif prepared["pack"].domain == "robot":
            priority = {"robot": 0, "trajectory": 1, "dressup": 2, "simulation": 3}
            configure_order.sort(
                key=lambda item: priority.get(str(item["type"]), 4)
            )
        elif prepared["pack"].domain == "fem":
            priority = {
                "solver": 0,
                "material": 1,
                "constraint": 2,
                "load_case": 3,
                "mesh": 4,
                "analysis": 5,
                "result": 6,
            }
            configure_order.sort(
                key=lambda item: priority.get(str(item["type"]), 7)
            )
        for item in configure_order:
            output_name = str(item["name"])
            obj = outputs[output_name]
            inspection_feature = (
                prepared["pack"].domain == "inspection"
                and str(getattr(obj, "TypeId", "")) == "Inspection::Feature"
            )
            if inspection_feature:
                _unfreeze_inspection_feature(obj)
            robot_dressup = (
                prepared["pack"].domain == "robot"
                and str(getattr(obj, "TypeId", ""))
                == "Robot::TrajectoryDressUpObject"
            )
            if robot_dressup:
                _unfreeze_robot_dressup(obj)
            obj.Label = _label(item, output_name)
            _configure_object(
                doc,
                obj,
                item,
                outputs,
                prepared,
                robot_trajectory_swaps,
            )
            _set_metadata(
                obj,
                prepared,
                output_name,
                str(item["type"]),
                _definition(item),
            )
            if inspection_feature:
                _freeze_inspection_feature(obj)
            if robot_dressup:
                _freeze_robot_dressup(obj)
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
        if prepared["pack"].domain == "robot":
            retired_robot_trajectories = _extract_robot_trajectories(retired)
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
        if prepared["pack"].domain in {
            "mesh",
            "meshpart",
            "reverse_engineering",
        }:
            rollback_failures: list[str] = []
            if mesh_rollbacks:
                try:
                    _restore_mesh_rollback_states(mesh_rollbacks)
                except Exception as rollback_error:
                    rollback_failures.append(str(rollback_error))
            if meshpart_shape_rollbacks:
                try:
                    _restore_meshpart_shape_rollback_states(
                        meshpart_shape_rollbacks
                    )
                except Exception as rollback_error:
                    rollback_failures.append(str(rollback_error))
            if reverse_feature_rollbacks:
                try:
                    _restore_reverse_feature_rollback_states(
                        reverse_feature_rollbacks
                    )
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
        if prepared["pack"].domain == "points":
            rollback_failures = []
            if points_rollbacks:
                try:
                    _restore_points_rollback_states(points_rollbacks)
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
                    f"{publication_error} Explicit Points rollback failure: "
                    f"{' | '.join(rollback_failures)}"
                ) from publication_error
        if prepared["pack"].domain == "inspection":
            rollback_failures: list[str] = []
            if inspection_rollbacks:
                try:
                    _restore_inspection_rollback_states(inspection_rollbacks)
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
                    f"{publication_error} Explicit Inspection rollback failure: "
                    f"{' | '.join(rollback_failures)}"
                ) from publication_error
        if prepared["pack"].domain == "robot":
            rollback_failures: list[str] = []
            try:
                _restore_robot_rollback_states(
                    robot_rollbacks,
                    robot_trajectory_swaps + retired_robot_trajectories,
                )
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
                    f"{publication_error} Explicit Robot rollback failure: "
                    f"{' | '.join(rollback_failures)}"
                ) from publication_error
        if prepared["pack"].domain == "fem":
            rollback_failures: list[str] = []
            if fem_rollbacks:
                try:
                    _restore_fem_rollback_states(doc, fem_rollbacks)
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
                    f"{publication_error} Explicit FEM rollback failure: "
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
        if isinstance(item.get("surface_data"), dict):
            live_outputs[name]["surface_data"] = dict(item["surface_data"])
        if isinstance(item.get("mesh_data"), dict):
            live_outputs[name]["mesh_data"] = dict(item["mesh_data"])
        if isinstance(item.get("meshpart_data"), dict):
            live_outputs[name]["meshpart_data"] = dict(item["meshpart_data"])
        if isinstance(item.get("points_data"), dict):
            live_outputs[name]["points_data"] = dict(item["points_data"])
        if isinstance(item.get("reverse_data"), dict):
            live_outputs[name]["reverse_data"] = dict(item["reverse_data"])
        if isinstance(item.get("inspection_data"), dict):
            live_outputs[name]["inspection_data"] = dict(item["inspection_data"])
        if isinstance(item.get("robot_data"), dict):
            live_outputs[name]["robot_data"] = dict(item["robot_data"])
        if isinstance(item.get("fem_data"), dict):
            live_outputs[name]["fem_data"] = _fem_validation_summary(item["fem_data"])
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
        if isinstance(item.get("surface_data"), dict):
            summary["surface_data"] = dict(item["surface_data"])
        if isinstance(item.get("mesh_data"), dict):
            summary["mesh_data"] = dict(item["mesh_data"])
        if isinstance(item.get("meshpart_data"), dict):
            summary["meshpart_data"] = dict(item["meshpart_data"])
        if isinstance(item.get("points_data"), dict):
            summary["points_data"] = dict(item["points_data"])
        if isinstance(item.get("reverse_data"), dict):
            summary["reverse_data"] = dict(item["reverse_data"])
        if isinstance(item.get("inspection_data"), dict):
            summary["inspection_data"] = dict(item["inspection_data"])
        if isinstance(item.get("robot_data"), dict):
            summary["robot_data"] = dict(item["robot_data"])
        if isinstance(item.get("fem_data"), dict):
            summary["fem_data"] = _fem_validation_summary(item["fem_data"])
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
_PROJECT_DOMAIN_ORDER = ("sketcher", "part", "partdesign", "assembly")


def _clone_output_item(item: Mapping[str, Any]) -> dict[str, Any]:
    """Deep copy of one validated output item, sharing its detached shape.

    The plain JSON evidence is copied so per-domain rewrites never mutate the
    caller's validated result; the imported ``detached_shape`` (attached by
    validation, not deep-copyable) is shared by reference.
    """

    clone = copy.deepcopy(
        {key: value for key, value in dict(item).items() if key != "detached_shape"}
    )
    if "detached_shape" in item:
        clone["detached_shape"] = item["detached_shape"]
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
        if prepared["pack"].domain in {"mesh", "meshpart", "reverse_engineering"}
        else []
    )
    meshpart_shape_rollbacks = (
        _meshpart_shape_rollback_states(objects)
        if prepared["pack"].domain in {"meshpart", "reverse_engineering"}
        else []
    )
    points_rollbacks = (
        _points_rollback_states(objects)
        if prepared["pack"].domain == "points"
        else []
    )
    reverse_feature_rollbacks = (
        _reverse_feature_rollback_states(objects)
        if prepared["pack"].domain == "reverse_engineering"
        else []
    )
    inspection_rollbacks = (
        _inspection_rollback_states(objects)
        if prepared["pack"].domain == "inspection"
        else []
    )
    robot_rollbacks = (
        _robot_rollback_states(objects)
        if prepared["pack"].domain == "robot"
        else []
    )
    fem_rollbacks = (
        _fem_rollback_states(objects)
        if prepared["pack"].domain == "fem"
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
    robot_trajectories: list[dict[str, Any]] = []
    try:
        if hasattr(doc, "openTransaction"):
            doc.openTransaction(f"Delete {prepared['pack'].title} XScript program")
            transaction_open = True
        if prepared["pack"].domain == "robot":
            robot_trajectories = _extract_robot_trajectories(objects)
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
        if meshpart_shape_rollbacks:
            try:
                _restore_meshpart_shape_rollback_states(meshpart_shape_rollbacks)
            except Exception as rollback_error:
                raise RuntimeError(
                    f"{deletion_error} Explicit MeshPart deletion rollback failure: "
                    f"{rollback_error}"
                ) from deletion_error
        if points_rollbacks:
            try:
                _restore_points_rollback_states(points_rollbacks)
            except Exception as rollback_error:
                raise RuntimeError(
                    f"{deletion_error} Explicit Points deletion rollback failure: "
                    f"{rollback_error}"
                ) from deletion_error
        if reverse_feature_rollbacks:
            try:
                _restore_reverse_feature_rollback_states(
                    reverse_feature_rollbacks
                )
            except Exception as rollback_error:
                raise RuntimeError(
                    f"{deletion_error} Explicit Reverse Engineering deletion "
                    f"rollback failure: {rollback_error}"
                ) from deletion_error
        if inspection_rollbacks:
            try:
                _restore_inspection_rollback_states(inspection_rollbacks)
            except Exception as rollback_error:
                raise RuntimeError(
                    f"{deletion_error} Explicit Inspection deletion rollback "
                    f"failure: {rollback_error}"
                ) from deletion_error
        if robot_rollbacks:
            try:
                _restore_robot_rollback_states(
                    robot_rollbacks,
                    robot_trajectories,
                )
            except Exception as rollback_error:
                raise RuntimeError(
                    f"{deletion_error} Explicit Robot deletion rollback failure: "
                    f"{rollback_error}"
                ) from deletion_error
        if fem_rollbacks:
            try:
                _restore_fem_rollback_states(doc, fem_rollbacks)
            except Exception as rollback_error:
                raise RuntimeError(
                    f"{deletion_error} Explicit FEM deletion rollback failure: "
                    f"{rollback_error}"
                ) from deletion_error
        raise
    return {"ok": True, "deleted_objects": deleted, "recompute_deferred": True}
