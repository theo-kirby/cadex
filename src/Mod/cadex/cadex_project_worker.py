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

    Entries are sorted by output name; solved placements are rounded to 1e-9
    so OCCT noise below modeling tolerance cannot flip the digest.

    A BREP output is its exported shape and a mesh output is its vertex set;
    both are identified by that and nothing else, because for those two the
    bytes *are* the whole output. Everything else is identified by its
    canonical definition — the recipe — **and, if it retained an artifact, by
    that artifact's bytes as well** (ADR-068).

    The bytes clause is an addition rather than a substitution, and that is
    the deliberate part. Before it, a *simulation trace* — an artifact this
    engine had spent a slice proving byte-reproducible across processes — was
    identified only by the graph that asked for it. Two projects whose
    scripts matched but whose traces came from different solver versions had
    the same digest, and `open_project` asserts digest equality, so the
    difference passed in silence. Adding the bytes rather than swapping them
    in makes the change strictly monotonic: everything that moved the digest
    before still moves it, so no edit that used to be visible becomes
    invisible.

    The clause is keyed on *having an artifact* rather than on a roster of
    known kinds, so an output kind invented later joins the digest by writing
    a file rather than by someone remembering to add it here. `mesh` is the
    single exception and is excluded by name, for the reason given below.
    """

    entries = []
    for item in outputs:
        entry: dict[str, Any] = {
            "output_name": str(item.get("name") or ""),
            "domain": str(item.get("domain") or ""),
            "output_type": str(item.get("type") or ""),
        }
        artifact = str(item.get("artifact_path") or "")
        kind = str(item.get("artifact_kind") or "")
        if artifact and kind == "brep":
            entry["shape_sha256"] = _file_sha256(root / artifact)
        elif artifact and kind == "mesh" and item.get("geometry_sha256"):
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
            # `kind != "mesh"` and not `geometry_sha256 is None`: a decimate
            # tree is approximating and run-dependent *by construction*, so
            # its bytes are the last thing that should identify it. Excluding
            # the kind rather than the missing fingerprint is what keeps that
            # true.
            if artifact and kind != "mesh":
                entry["artifact_sha256"] = _file_sha256(root / artifact)
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


def _wiring_registry(nets: Any, result: dict[str, Any]) -> list[dict[str, Any]]:
    """Every resolved terminal set, joined to its port and its output (ADR-065).

    The run has already resolved each set once and memoised it; publishing
    that registry is what lets the shell draw a harness at all, and it cannot
    drift from the geometry that was actually built. Re-deriving it host-side
    would reach declared layouts only — a ``holes=`` selector needs the shape.

    Both joins come free. ``port`` is the ``nets(ports=...)`` name, matched on
    the same memo key the worker resolves by; ``output`` is the ``result``
    key whose payload *is* the set's component. A component that is neither a
    declared port nor a declared output still yields a node, unnamed — that
    is the legacy harness, and it is exactly what the read-only view draws.

    Derived data, computed after the digest and never fed into it: a port the
    script declares but never wires is resolved here and its failure reported,
    never raised.
    """

    from cadex_domain_api import _json_value
    from cadex_part_worker import (
        published_terminal_sets,
        resolve_terminal_set_for_publication,
        terminal_set_key,
    )

    port_by_key: dict[str, str] = {}
    for port_name, terminal_set in list(getattr(nets, "ports", []) or []):
        payload = _json_value(
            {
                "component": terminal_set.component,
                "layout": dict(terminal_set.layout),
            }
        )
        # Resolve before reading the registry: an unwired port has not been
        # resolved by the run, and an unwired board is precisely the node the
        # editor needs in order to rewire onto it.
        resolve_terminal_set_for_publication(payload)
        port_by_key.setdefault(terminal_set_key(payload), port_name)

    output_by_payload: dict[str, str] = {}
    for name, value in result.items():
        try:
            output_by_payload.setdefault(_canonical_json(_payload(value)), str(name))
        except (TypeError, ValueError):
            continue

    registry: list[dict[str, Any]] = []
    for entry in published_terminal_sets():
        component = entry.get("component")
        try:
            output = output_by_payload.get(_canonical_json(component), "")
        except (TypeError, ValueError):
            output = ""
        registry.append(
            {
                "port": port_by_key.get(str(entry.get("key") or ""), ""),
                "output": output,
                "domain": str((component or {}).get("domain") or ""),
                "kind": str((entry.get("layout") or {}).get("kind") or ""),
                "terminals": list(entry.get("terminals") or []),
            }
        )
    return registry


def _validate_request(request: dict[str, Any]) -> tuple[str, dict, dict, dict, list]:
    """Structural checks shared by an accepting run and a preview."""

    if request.get("schema") != SCHEMA:
        raise ValueError(
            f"Unsupported project worker schema: {request.get('schema')!r}."
        )
    source = str(request.get("source") or "")
    inputs = request.get("inputs")
    api_contracts = request.get("api_contracts")
    param_values = request.get("param_values")
    # Absent rather than empty on a request written before ADR-065, and a
    # full row list rather than a patch when present -- that is what lets the
    # editor add and delete wires.
    net_values = request.get("net_values") or []
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
    if not isinstance(net_values, list):
        raise TypeError("net_values must be an array of connection rows.")
    return source, inputs, api_contracts, param_values, net_values


def _staged_globals(
    api_contracts: dict[str, Any],
    param_values: dict[str, Any],
    inline_sources: dict[str, dict[str, Any]],
    net_values: Any = None,
) -> tuple[dict[str, Any], ParamsCollector, Any]:
    """One API object per capability domain, plus the declared-table vocabulary.

    ``params``/``num`` declare the sliders and ``nets``/``wire`` declare the
    connections (ADR-065); both are tables the script states and something
    outside it currently sets.
    """

    from CadexNets import NetsCollector, wire

    collector = ParamsCollector(param_values)
    nets = NetsCollector(net_values)
    globals_by_name: dict[str, Any] = {
        "params": collector,
        "num": num,
        "nets": nets,
        "wire": wire,
    }
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
    return globals_by_name, collector, nets


def _run(request: dict[str, Any], root: Path) -> dict[str, Any]:
    import FreeCAD as App

    source, inputs, api_contracts, param_values, net_values = _validate_request(request)

    output_directory = root / "outputs"
    output_directory.mkdir(parents=True, exist_ok=False)

    # part.shape_from_mesh materializes a nested mesh value, which resolves
    # mesh.import_file names against <root>/assets. build_part_shape takes
    # neither a root nor the mesh kernel, so both are bound once here — this
    # module is staged into the sandbox, so it may own that edge (ADR-043).
    from cadex_mesh_worker import canonical_mesh_from_payload, composed_placement
    from cadex_part_worker import (
        configure_part_assets,
        reset_part_shape_memo,
    )

    configure_part_assets(root, canonical_mesh_from_payload, composed_placement)

    inline_sources: dict[str, dict[str, Any]] = {}
    globals_by_name, collector, nets = _staged_globals(
        api_contracts, param_values, inline_sources, net_values
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
        # data and must never feed the content digest (Phase 5.1). The wiring
        # registry is derived data on exactly the same footing (ADR-065).
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
            "net_specs": nets.specs,
            "wiring": _wiring_registry(nets, result),
            "digest": digest,
            "validations": validations,
            "component_sources": component_sources,
        }
    finally:
        App.closeDocument(document.Name)
        # In the `finally`, not at entry. A warm worker (ADR-055) that
        # leaked this across requests would answer with geometry built from
        # the *previous* parameter values, under a digest self-consistent
        # with it -- the worst failure this codebase can have. Clearing on
        # the way out makes that impossible rather than unlikely.
        reset_part_shape_memo()


class PreviewUnavailable(Exception):
    """This script cannot be answered by a placement-only reply.

    Not an error: the caller falls back to the accepting path, which is the
    real answer anyway. Carries the reason so the shell can say why, and so a
    test can tell "the preview declined" from "the preview broke".
    """


def _definition_fingerprints(
    grouped: dict[str, dict[str, Any]],
) -> dict[str, str]:
    """SHA-256 of each **non-assembly** output's canonical definition.

    The definition is the complete build recipe — it is what
    :func:`compute_project_digest` hashes for every output that has no
    artifact bytes of its own — so two runs whose definitions are pairwise
    identical build pairwise identical geometry. That is the entire basis for
    answering a parameter change with placements alone, and it is a *dynamic*
    test rather than a static classifier: there is no dependency graph to
    consult (``p.width`` evaluates to a bare float, and ``DomainValue`` keeps
    no parameter provenance), and a parameter can be pose-only at one value
    and topology-changing at the next.

    Assembly outputs are excluded, and must be: a component's placement is an
    argument of its own definition, so including them would make every moved
    component read as a changed definition and nothing would ever be
    previewable.
    """

    fingerprints: dict[str, str] = {}
    for domain, outputs in grouped.items():
        if domain == "assembly":
            continue
        for name, value in outputs.items():
            canonical = _canonical_json(_payload(value)).encode("utf-8")
            fingerprints[name] = hashlib.sha256(canonical).hexdigest()
    return fingerprints


def _preview_references(
    inline_sources: dict[str, dict[str, Any]],
    grouped: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Bind each component source to a shape built in this process.

    The accepting path matches component sources to declared outputs by their
    canonical definition and then hands the solver a staged BREP; this
    matches them the same way and hands the solver the shape itself.
    ``build_part_shape`` is memoised by content (ADR-053), so across the
    previews of one drag the parts that did not change are not rebuilt —
    which is what makes the second preview of a drag cheaper than the first.
    """

    from cadex_part_worker import build_part_shape

    index: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for domain in ("part", "partdesign"):
        for name, value in grouped[domain].items():
            payload = _payload(value)
            index.setdefault(_canonical_json(payload), (name, domain, payload))

    entries: list[dict[str, Any]] = []
    component_sources: dict[str, str] = {}
    for token, payload in inline_sources.items():
        matched = index.get(_canonical_json(payload))
        if matched is None:
            raise PreviewUnavailable(
                "a component source is not a declared part output of this script"
            )
        name, domain, matched_payload = matched
        if domain != "part":
            # A PartDesign source is a native Body history, built by
            # validate_and_build_partdesign against a document rather than by
            # build_part_shape, so there is no memoised shape to bind and no
            # cheap way to make one. Declining is honest and costs one
            # debounced rebuild.
            raise PreviewUnavailable(
                f"component source {name!r} is built by partdesign"
            )
        component_sources[token] = name
        entries.append(
            {
                "document_uid": INLINE_SOURCE_UID,
                "object_name": token,
                "shape": build_part_shape(matched_payload),
                "label": name,
                "type_id": "Part::Feature",
                "source_kind": "shape",
                "published_interfaces": {},
            }
        )
    return entries, component_sources


def _run_preview(request: dict[str, Any], root: Path) -> dict[str, Any]:
    """Answer one parameter change with solved placements and nothing else.

    A read-only oracle (ADR-055). It execs the script, decides whether the
    change was pose-only, and if it was, builds the component shapes and runs
    the native assembly solve. It does **not** export BREP, compute shape
    facts, tessellate, hash anything, compute a digest, or publish — and it
    writes no file at all, which is the invariant the whole design rests on:
    every byte the project store ever accepts still comes from a cold
    ``--safe-mode`` run with a fresh attempt directory.

    The memo is deliberately **not** reset here, unlike the accepting path's
    ``finally``. Persisting it across the previews of one generation is the
    point; it is safe because the memo key is *content*, so a different
    parameter value is a different key rather than a stale hit. Bounding it
    is the warm worker's job — it clears on a generation change and respawns
    on a request count.
    """

    import FreeCAD as App

    source, inputs, api_contracts, param_values, net_values = _validate_request(request)
    baseline = request.get("baseline")
    if baseline is not None and not isinstance(baseline, dict):
        raise TypeError("baseline must be an object when present.")

    from cadex_mesh_worker import canonical_mesh_from_payload, composed_placement
    from cadex_part_worker import configure_part_assets

    configure_part_assets(root, canonical_mesh_from_payload, composed_placement)

    inline_sources: dict[str, dict[str, Any]] = {}
    globals_by_name, _collector, _nets = _staged_globals(
        api_contracts, param_values, inline_sources, net_values
    )

    document = App.newDocument(
        "XScriptProjectPreview", "XScript Project Preview", True, True
    )
    try:
        result, _stdout, _budget = _execute_project_source(
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
        fingerprints = _definition_fingerprints(grouped)

        def declined(reason: str) -> dict[str, Any]:
            return {
                "ok": True,
                "schema": SCHEMA,
                "domain": "project",
                "mode": "preview",
                "previewable": False,
                "reason": reason,
                "placements": {},
                "definitions_fingerprint": fingerprints,
            }

        if baseline is None:
            # The generation's first exec: there is nothing to compare
            # against, so this run *is* the baseline. It still returns the
            # fingerprints, which is how the caller acquires one.
            return declined("no baseline for this generation")
        expected = baseline.get("definitions_fingerprint")
        if not isinstance(expected, dict):
            raise TypeError("baseline.definitions_fingerprint must be an object.")
        changed = sorted(
            name
            for name in set(expected) | set(fingerprints)
            if expected.get(name) != fingerprints.get(name)
        )
        if changed:
            # The honest answer, and the common one: a parameter feeding
            # `part.box(p.width, ...)` really did change that box's
            # definition, and a placement-only reply would be a lie. Returned
            # before any shape is built, so declining is cheap.
            return declined(
                "these definitions changed, so the geometry did too: "
                + ", ".join(changed[:8])
            )
        if not grouped["assembly"]:
            return declined("this script declares no assembly outputs")

        from cadex_assembly_worker import (
            configure_assembly_references,
            validate_and_solve_assembly,
        )

        references, _component_sources = _preview_references(
            inline_sources, grouped
        )
        configure_assembly_references(root, references, from_shapes=True)
        assembly_items = [
            {"name": name, "type": str(_payload(value).get("output_type") or "")}
            for name, value in grouped["assembly"].items()
        ]
        validate_and_solve_assembly(
            document,
            dict(grouped["assembly"]),
            assembly_items,
            None,
            skip_derived=True,
        )
        placements: dict[str, list[float]] = {}
        for item in assembly_items:
            matrix = item.get("solved_placement_matrix")
            if isinstance(matrix, list):
                placements[str(item["name"])] = [float(value) for value in matrix]
        return {
            "ok": True,
            "schema": SCHEMA,
            "domain": "project",
            "mode": "preview",
            "previewable": True,
            "placements": placements,
            "definitions_fingerprint": fingerprints,
        }
    except PreviewUnavailable as exc:
        return {
            "ok": True,
            "schema": SCHEMA,
            "domain": "project",
            "mode": "preview",
            "previewable": False,
            "reason": str(exc),
            "placements": {},
            "definitions_fingerprint": {},
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
        mode = str(request.get("mode") or "accept")
        if mode not in {"accept", "preview"}:
            raise ValueError(f"Unsupported project worker mode: {mode!r}.")
        payload = (
            _run_preview(request, root) if mode == "preview" else _run(request, root)
        )
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
