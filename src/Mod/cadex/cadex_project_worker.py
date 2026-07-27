# SPDX-License-Identifier: LGPL-2.1-or-later

"""Windowless worker executing ONE multi-domain project script.

The project domain runs the whole project script in a single sandboxed pass
with every capability API staged (``sketcher``, ``part``, ``partdesign``,
``mesh``, ``assembly``) plus the ``params``/``num`` parameter vocabulary. The
script's ``result`` dictionary may mix outputs from every domain; the worker
groups them by domain and evaluates in the fixed order sketcher → part →
partdesign → mesh → assembly, reusing each domain's existing evaluator and
serializer. One
execution produces one output set, one parameter-spec collection, and one
content digest over the serialized artifacts.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
from collections.abc import Mapping
import io
import json
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Any

from cadex_domain_api import DomainValue, create_domain_api
from cadex_domain_worker import (
    MAX_STDOUT_CHARS,
    MAX_PART_OUTPUT_SUBELEMENT_DETAILS,
    PART_OUTPUT_SUBELEMENT_DETAIL_BUDGET,
    _DocumentView,
    _SAFE_BUILTINS,
    _immutable_input,
    _payload,
    _serialize_output,
    _write_json,
    _resource_limits,
)
from cadex_project_api import (
    EVALUATION_ORDER,
    INLINE_SOURCE_UID,
    ParamsCollector,
    create_project_assembly_api,
    num,
)
from cadex_tessellation import generate_display_artifacts, validate_display_request

REQUEST_ENV = "CADEX_XSCRIPT_DOMAIN_REQUEST"
RESULT_ENV = "CADEX_XSCRIPT_DOMAIN_RESULT"
SCHEMA = "cadex-xscript-project-worker-v1"
DIGEST_SCHEMA = "cadex-project-digest-v1"
_PLACEMENT_DECIMALS = 9


def _execute_project_source(
    *,
    source: str,
    document_name: str,
    document_objects: list[dict[str, str]],
    inputs: dict[str, Any],
    globals_by_name: dict[str, Any],
    max_operations: int,
    max_seconds: float,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Sandboxed single-pass exec with one API object per capability domain."""

    started = time.monotonic()
    operations = 0
    source_filename = "<cadex-project-xscript>"

    def trace(frame: Any, event: str, _arg: Any):
        nonlocal operations
        if frame.f_code.co_filename != source_filename:
            # Not the user's program. Returning `trace` here made Python
            # line-trace every frame of every call the script makes --
            # the whole cadex_*_api payload-construction path, on every
            # single line. Returning None declines local tracing for that
            # frame; the counter is unchanged by construction, because it
            # only ever incremented for source frames anyway, and a
            # callback back into source code still gets a fresh `call`
            # event at the global hook.
            return None
        if event in {"line", "call"}:
            operations += 1
            if operations > max_operations:
                raise RuntimeError(
                    f"XScript exceeded its {max_operations} operation budget."
                )
            if time.monotonic() - started > max_seconds:
                raise TimeoutError(
                    f"XScript exceeded its {max_seconds:g} second source budget."
                )
        return trace

    namespace: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "__name__": "__cadex_project_program__",
        "doc": _DocumentView(document_name, document_objects),
        "inputs": _immutable_input(inputs),
    }
    namespace.update(globals_by_name)
    output = io.StringIO()
    previous_trace = sys.gettrace()
    try:
        sys.settrace(trace)
        with redirect_stdout(output):
            exec(
                compile(source, source_filename, "exec"),
                namespace,
                namespace,
            )
    finally:
        sys.settrace(previous_trace)
    result = namespace.get("result")
    if not isinstance(result, dict):
        raise TypeError("A project script must assign a dictionary to result.")
    return (
        result,
        output.getvalue()[-MAX_STDOUT_CHARS:],
        {
            "operations": operations,
            "max_operations": max_operations,
            "elapsed_seconds": time.monotonic() - started,
            "max_seconds": max_seconds,
        },
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _round_placement(values: Any) -> Any:
    if not isinstance(values, (list, tuple)):
        return None
    rounded = []
    for value in values:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            rounded.append(round(float(value), _PLACEMENT_DECIMALS))
        else:
            return None
    return rounded


def compute_project_digest(root: Path, outputs: list[dict[str, Any]]) -> str:
    """SHA-256 over the canonical description of all serialized outputs.

    Entries are sorted by output name; BREP-backed outputs contribute the
    SHA-256 of their exported artifact, everything else the SHA-256 of its
    canonical definition JSON; solved placements are rounded to 1e-9 so OCCT
    noise below modeling tolerance cannot flip the digest.
    """

    entries = []
    for item in outputs:
        entry: dict[str, Any] = {
            "output_name": str(item.get("name") or ""),
            "domain": str(item.get("domain") or ""),
            "output_type": str(item.get("type") or ""),
        }
        artifact = str(item.get("artifact_path") or "")
        if artifact and str(item.get("artifact_kind") or "") == "brep":
            entry["shape_sha256"] = _file_sha256(root / artifact)
        elif (
            artifact
            and str(item.get("artifact_kind") or "") == "mesh"
            and item.get("geometry_sha256")
        ):
            # Vertex-set fingerprint, not artifact bytes: the native set
            # operations re-triangulate coplanar regions non-deterministically
            # while the vertex set stays exact. Approximating mesh outputs
            # (decimate trees) carry no fingerprint and fall through to the
            # canonical-definition hash (see cadex_mesh_worker, ADR-016).
            entry["mesh_sha256"] = str(item["geometry_sha256"])
        else:
            entry["payload_sha256"] = hashlib.sha256(
                _canonical_json(item.get("definition") or {}).encode("utf-8")
            ).hexdigest()
        placement = _round_placement(item.get("solved_placement_matrix"))
        if placement is not None:
            entry["placement"] = placement
        entries.append(entry)
    entries.sort(key=lambda entry: entry["output_name"])
    material = _canonical_json({"schema": DIGEST_SCHEMA, "outputs": entries})
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _group_result_by_domain(
    result: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {domain: {} for domain in EVALUATION_ORDER}
    for name, value in result.items():
        clean = str(name)
        if not clean or len(clean) > 128:
            raise ValueError("Every result key must be a short output name.")
        payload = _payload(value)
        domain = str(payload.get("domain") or "")
        if domain not in grouped:
            raise ValueError(
                f"Output {clean!r} came from unsupported domain {domain!r}; "
                f"project scripts compose {', '.join(EVALUATION_ORDER)}."
            )
        grouped[domain][clean] = value
    return grouped


def _resolve_inline_sources(
    root: Path,
    inline_sources: dict[str, dict[str, Any]],
    artifact_by_definition: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Turn same-script component sources into staged reference entries.

    Every component source must match a DECLARED part/partdesign output of the
    same script: publication links live components to the published output
    objects, so an undeclared source would have no stable live identity.
    Returns the staged reference entries plus ``{token: output_name}`` so the
    publisher can rewrite each token to the live published object.
    """

    entries: list[dict[str, Any]] = []
    component_sources: dict[str, str] = {}
    for token, payload in inline_sources.items():
        key = _canonical_json(payload)
        matched = artifact_by_definition.get(key)
        if matched is None:
            domain = str(payload.get("domain") or "part")
            raise ValueError(
                f"A {domain} component source must also be returned as an "
                "output of this script so its shape is built, serialized, and "
                "published under a stable output name."
            )
        artifact_path = str(matched["artifact_path"])
        output_name = str(matched.get("name") or token)
        component_sources[token] = output_name
        entries.append(
            {
                "document_uid": INLINE_SOURCE_UID,
                "object_name": token,
                "artifact_path": artifact_path,
                "brep_sha256": _file_sha256(root / artifact_path),
                "label": output_name,
                "type_id": "Part::Feature",
                "source_kind": "shape",
                "published_interfaces": {},
            }
        )
    return entries, component_sources


def _stamp_source_output(
    item: dict[str, Any], component_sources: Mapping[str, str]
) -> None:
    """Name the declared output whose geometry a component instances.

    A ``component_link`` output carries a solved placement and no geometry of
    its own; the shape it places is a separate declared output. Nothing in
    the response said *which* one, so a consumer holding a solved assembly
    had a set of matrices and no way to know what to put at them -- see
    ADR-049. The token → output-name map already exists (it is what lets the
    publisher rewrite each token to a live object); this only writes it down
    where the response can carry it.

    Left absent rather than null when there is no match, so the key is a
    positive signal and every non-component entry keeps exactly the shape it
    has today.
    """

    if str(item.get("type") or "") != "component_link":
        return
    arguments = list((item.get("definition") or {}).get("arguments") or [])
    if not arguments or not isinstance(arguments[0], Mapping):
        return
    source = component_sources.get(str(arguments[0].get("object_name") or ""))
    if source:
        item["source_output"] = str(source)


def _run(request: dict[str, Any], root: Path) -> dict[str, Any]:
    import FreeCAD as App

    if request.get("schema") != SCHEMA:
        raise ValueError(
            f"Unsupported project worker schema: {request.get('schema')!r}."
        )
    source = str(request.get("source") or "")
    inputs = request.get("inputs")
    api_contracts = request.get("api_contracts")
    param_values = request.get("param_values")
    if not isinstance(inputs, dict):
        raise TypeError("inputs must be an object.")
    if not isinstance(api_contracts, dict) or set(api_contracts) != set(
        EVALUATION_ORDER
    ):
        raise TypeError(
            "api_contracts must carry exports/output_types for every domain."
        )
    if not isinstance(param_values, dict):
        raise TypeError("param_values must be an object.")

    output_directory = root / "outputs"
    output_directory.mkdir(parents=True, exist_ok=False)

    # part.shape_from_mesh materializes a nested mesh value, which resolves
    # mesh.import_file names against <root>/assets. build_part_shape takes
    # neither a root nor the mesh kernel, so both are bound once here — this
    # module is staged into the sandbox, so it may own that edge (ADR-043).
    from cadex_mesh_worker import canonical_mesh_from_payload
    from cadex_part_worker import configure_part_assets

    configure_part_assets(root, canonical_mesh_from_payload)

    inline_sources: dict[str, dict[str, Any]] = {}
    collector = ParamsCollector(param_values)
    globals_by_name: dict[str, Any] = {"params": collector, "num": num}
    for domain in EVALUATION_ORDER:
        contract = api_contracts[domain]
        exports = list(contract.get("exports") or [])
        output_types = list(contract.get("output_types") or [])
        if domain == "assembly":
            globals_by_name[domain] = create_project_assembly_api(
                exports, output_types, inline_sources
            )
        else:
            globals_by_name[domain] = create_domain_api(
                domain, exports, output_types
            )

    document = App.newDocument(
        "XScriptProjectCandidate", "XScript Project Candidate", True, True
    )
    try:
        result, stdout, budget = _execute_project_source(
            source=source,
            document_name=str(request.get("document_name") or "XScriptDocument"),
            document_objects=list(request.get("document_objects") or []),
            inputs=inputs,
            globals_by_name=globals_by_name,
            max_operations=int(request.get("max_operations") or 400_000),
            max_seconds=float(request.get("max_seconds") or 300.0),
        )
        if not result:
            raise ValueError("A project script must return at least one output.")
        grouped = _group_result_by_domain(result)

        shape_detail_limit = max(
            16,
            min(
                MAX_PART_OUTPUT_SUBELEMENT_DETAILS,
                PART_OUTPUT_SUBELEMENT_DETAIL_BUDGET // max(1, len(result)),
            ),
        )

        outputs: list[dict[str, Any]] = []
        validations: dict[str, Any] = {}
        artifact_by_definition: dict[str, dict[str, Any]] = {}
        # validate_and_build_partdesign numbers its own artifacts 0..N-1;
        # start the shared counter after them so file names never collide.
        output_index = len(grouped["partdesign"])

        def serialize(name: str, value: Any, domain: str) -> dict[str, Any]:
            nonlocal output_index
            payload = _payload(value)
            item = _serialize_output(
                root,
                output_index,
                {"name": name, "type": str(payload.get("output_type") or "")},
                value,
                max_shape_subelements=shape_detail_limit,
            )
            output_index += 1
            item["domain"] = domain
            return item

        # sketcher — one native solve per sketch output; each item carries its
        # own solver validation so native sketch publication can verify it
        sketch_validations = []
        for name, value in grouped["sketcher"].items():
            from cadex_sketcher_worker import validate_and_solve_sketch

            item = serialize(name, value, "sketcher")
            validation = validate_and_solve_sketch(document, {name: value}, [item])
            item["sketch_validation"] = validation
            sketch_validations.append(validation)
            outputs.append(item)
        if sketch_validations:
            validations["sketcher"] = sketch_validations

        # part — direct BREP serialization
        for name, value in grouped["part"].items():
            item = serialize(name, value, "part")
            outputs.append(item)
            artifact_by_definition[_canonical_json(item["definition"])] = item

        # partdesign — native Body histories through the existing builder
        if grouped["partdesign"]:
            from cadex_partdesign_worker import validate_and_build_partdesign

            expected = [
                {"name": name, "type": "solid"} for name in grouped["partdesign"]
            ]
            built, partdesign_validation = validate_and_build_partdesign(
                document,
                dict(grouped["partdesign"]),
                expected,
                root,
                max_shape_subelements=shape_detail_limit,
            )
            validations["partdesign"] = partdesign_validation
            for item in built:
                item["domain"] = "partdesign"
                outputs.append(item)
                artifact_by_definition[_canonical_json(item["definition"])] = item

        # mesh — native Mesh/MeshPart kernels; artifacts are hashed binaries
        for name, value in grouped["mesh"].items():
            from cadex_mesh_worker import serialize_mesh_output

            payload = _payload(value)
            item = serialize_mesh_output(
                root,
                output_index,
                {"name": name, "type": str(payload.get("output_type") or "")},
                value,
            )
            output_index += 1
            item["domain"] = "mesh"
            outputs.append(item)

        # assembly — same-script sources become staged references, then the
        # existing native assembly candidate build/solve runs unchanged
        component_sources: dict[str, str] = {}
        if grouped["assembly"]:
            from cadex_assembly_worker import (
                configure_assembly_references,
                validate_and_solve_assembly,
            )

            references, component_sources = _resolve_inline_sources(
                root, inline_sources, artifact_by_definition
            )
            configure_assembly_references(root, references)
            assembly_outputs = []
            for name, value in grouped["assembly"].items():
                item = serialize(name, value, "assembly")
                _stamp_source_output(item, component_sources)
                assembly_outputs.append(item)
                outputs.append(item)
            validations["assembly"] = validate_and_solve_assembly(
                document,
                dict(grouped["assembly"]),
                assembly_outputs,
                root,
            )

        # Digest first, display second: display artifacts are opt-in derived
        # data and must never feed the content digest (Phase 5.1).
        digest = compute_project_digest(root, outputs)
        display_request = validate_display_request(request.get("display"))
        if display_request is not None:
            generate_display_artifacts(root, outputs, display_request)
        return {
            "ok": True,
            "schema": SCHEMA,
            "domain": "project",
            "outputs": outputs,
            "stdout": stdout,
            "budget": budget,
            "param_specs": collector.specs,
            "digest": digest,
            "validations": validations,
            "component_sources": component_sources,
        }
    finally:
        App.closeDocument(document.Name)


def main() -> int:
    result_path = Path(os.environ[RESULT_ENV]).resolve()
    try:
        request_path = Path(os.environ[REQUEST_ENV]).resolve()
        root = request_path.parent
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise TypeError("Project worker request must be an object.")
        _resource_limits(request)
        payload = _run(request, root)
    except BaseException as exc:
        payload = {
            "ok": False,
            "exception_type": exc.__class__.__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(limit=40),
        }
        details = getattr(exc, "details", None)
        if isinstance(details, dict):
            payload["details"] = details
    _write_json(result_path, payload)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
