# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project digest's entry material, and the geometric identity of a shape.

Two digests over one output set, built from the same entries so they can only
ever disagree about *one* thing — how a BREP output is identified.

``cadex-project-digest-v1`` identifies a BREP output by its exported bytes.
That is the accepted-state guard and it does not change here: every stored
``accepted_digest`` keeps its meaning, and nothing re-accepts changed geometry.

``cadex-project-geometry-digest-v1`` identifies the same output by what the
kernel measures on the shape instead — counts, the exact vertex set, the exact
edge-length and face-area multisets, the bounding box, the total area — plus
its canonical definition, the recipe that asked for it. It drops one more
thing the byte digest keeps: a **derived** output's artifact bytes, which are
a function of the model *and the engine that exported it* (ADR-396).

It exists because the bytes are not a function of the inputs alone. ``part.offset`` is OCCT's
``BRepOffset_MakeOffset``, and it writes a different geometry table every
process for an identical solid (ADR-389, ``docs/probes/ot7/DIGEST-DRIFT.md``),
so a project that used it could never be reopened. This digest is consulted
only when the byte digest disagrees, and only to say whether the disagreement
is the serialization or the model.

Measured, on the offset solid that started this, across four processes: the
vertex set, the edge-length multiset, the face-area multiset, the counts, the
bounding box and the total area are **bit-identical every time**, and the
volume is not (it moves in the last two digits). So volume is excluded by
name, and nothing here is rounded — the mesh fingerprint's rule (ADR-016),
for the mesh fingerprint's reason: a rounded quantity has boundaries to flip
across, and an exact one does not.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from typing import Any, Callable

DIGEST_SCHEMA = "cadex-project-digest-v1"
GEOMETRY_DIGEST_SCHEMA = "cadex-project-geometry-digest-v1"
_PLACEMENT_DECIMALS = 9


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def file_sha256(path: Path) -> str:
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


def shape_geometry_fingerprint(shape: Any) -> str:
    """SHA-256 over the kernel measurements that survive re-serialization.

    Order-insensitive by construction: every multiset is sorted, so the only
    way two shapes fingerprint alike is that the kernel measures them alike.
    Volume is absent on purpose -- it is the one quantity measured to drift
    between processes for an identical solid.
    """

    digest = hashlib.sha256()
    digest.update(GEOMETRY_DIGEST_SCHEMA.encode("ascii"))
    digest.update(
        struct.pack(
            "<5q",
            len(shape.Vertexes),
            len(shape.Edges),
            len(shape.Faces),
            len(shape.Shells),
            len(shape.Solids),
        )
    )
    for point in sorted(
        (float(v.X), float(v.Y), float(v.Z)) for v in shape.Vertexes
    ):
        digest.update(struct.pack("<3d", *point))
    for length in sorted(float(edge.Length) for edge in shape.Edges):
        digest.update(struct.pack("<d", length))
    for area in sorted(float(face.Area) for face in shape.Faces):
        digest.update(struct.pack("<d", area))
    box = shape.BoundBox
    digest.update(
        struct.pack(
            "<7d",
            float(box.XMin),
            float(box.YMin),
            float(box.ZMin),
            float(box.XMax),
            float(box.YMax),
            float(box.ZMax),
            float(shape.Area),
        )
    )
    return digest.hexdigest()


def brep_geometry_fingerprint(path: Path) -> str:
    """:func:`shape_geometry_fingerprint` of a serialized BREP artifact.

    ``Part`` is imported here rather than at module scope so this module
    stays pure for everything that only wants the byte digest -- the same
    rule the rest of the engine's kernel-touching helpers follow.
    """

    import Part

    shape = Part.Shape()
    shape.read(str(path))
    return shape_geometry_fingerprint(shape)


def _entries(
    root: Path,
    outputs: list[dict[str, Any]],
    brep_entry: Callable[[dict[str, Any], Path], dict[str, str]],
    *,
    derived_artifact_bytes: bool = True,
) -> list[dict[str, Any]]:
    """The shared entry material for both digests.

    ``derived_artifact_bytes`` is the *only* thing the two digests disagree
    about besides BREP identity. With it, a non-BREP output that retained a
    file is identified by its definition **and** those bytes (ADR-068);
    without it, by its definition alone (ADR-396).
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
            entry.update(brep_entry(item, root / artifact))
        elif artifact and kind == "mesh" and item.get("geometry_sha256"):
            # Vertex-set fingerprint, not artifact bytes: the native set
            # operations re-triangulate coplanar regions non-deterministically
            # while the vertex set stays exact. Approximating mesh outputs
            # (decimate trees) carry no fingerprint and fall through to the
            # canonical-definition hash (see cadex_mesh_worker, ADR-016).
            entry["mesh_sha256"] = str(item["geometry_sha256"])
        else:
            entry["payload_sha256"] = hashlib.sha256(
                canonical_json(item.get("definition") or {}).encode("utf-8")
            ).hexdigest()
            # `kind != "mesh"` and not `geometry_sha256 is None`: a decimate
            # tree is approximating and run-dependent *by construction*, so
            # its bytes are the last thing that should identify it. Excluding
            # the kind rather than the missing fingerprint is what keeps that
            # true.
            if derived_artifact_bytes and artifact and kind != "mesh":
                entry["artifact_sha256"] = file_sha256(root / artifact)
        placement = _round_placement(item.get("solved_placement_matrix"))
        if placement is not None:
            entry["placement"] = placement
        entries.append(entry)
    entries.sort(key=lambda entry: entry["output_name"])
    return entries


def project_digest(root: Path, outputs: list[dict[str, Any]]) -> str:
    """SHA-256 over the canonical description of all serialized outputs.

    Entries are sorted by output name; solved placements are rounded to 1e-9
    so OCCT noise below modeling tolerance cannot flip the digest.

    A BREP output is its exported shape and a mesh output is its vertex set;
    both are identified by that and nothing else, because for those two the
    bytes *are* the whole output. Everything else is identified by its
    canonical definition -- the recipe -- **and, if it retained an artifact,
    by that artifact's bytes as well** (ADR-068).

    The bytes clause is an addition rather than a substitution, and that is
    the deliberate part. Before it, a *simulation trace* -- an artifact this
    engine had spent a slice proving byte-reproducible across processes --
    was identified only by the graph that asked for it. Two projects whose
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

    This digest is unchanged by ADR-396: the clause is dropped only from
    :func:`project_geometry_digest`, which is consulted *after* this one has
    already said no.
    """

    entries = _entries(
        root,
        outputs,
        lambda _item, path: {"shape_sha256": file_sha256(path)},
    )
    material = canonical_json({"schema": DIGEST_SCHEMA, "outputs": entries})
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def project_geometry_digest(root: Path, outputs: list[dict[str, Any]]) -> str:
    """The same material, with each BREP output measured instead of read.

    A BREP entry carries two hashes rather than one: the kernel fingerprint
    *and* the canonical definition. The definition is what a script edit
    moves, so this digest is not a weaker guard that happens to ignore
    serialization -- a hand-edited script fails it on the recipe before the
    geometry is even consulted.

    A **derived** output -- an MJCF model, a training task, a trace, a render
    -- is identified here by its canonical definition and nothing else
    (ADR-396). ``project_digest`` still carries its bytes, and must: there,
    the bytes are what distinguishes two traces from two solver versions
    (ADR-068). Here, the engine version is precisely what this digest exists
    to forgive. An accepted MJCF export that a later engine writes *better*
    -- ADR-393's inverted weld frame -- is byte-different and model-identical,
    and asking it to match its own bytes shut `ot7-plover-e` against
    ``open_project`` for good. The design is still pinned: a derived artifact
    is a function of the definitions, the BREP shapes and the solved
    placements, all three of which this digest compares exactly, so nothing a
    *script* can change becomes invisible.
    """

    def brep_entry(item: dict[str, Any], path: Path) -> dict[str, str]:
        return {
            "shape_geometry_sha256": brep_geometry_fingerprint(path),
            "payload_sha256": hashlib.sha256(
                canonical_json(item.get("definition") or {}).encode("utf-8")
            ).hexdigest(),
        }

    entries = _entries(root, outputs, brep_entry, derived_artifact_bytes=False)
    material = canonical_json(
        {"schema": GEOMETRY_DIGEST_SCHEMA, "outputs": entries}
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def staged_geometry_digest(staging: Path) -> str:
    """:func:`project_geometry_digest` of one retained attempt directory.

    An attempt keeps its ``result.json`` next to the ``outputs/`` it names,
    which is what makes an *already accepted* project comparable without
    having stored anything new at accept time. That matters more than it
    sounds: the projects this has to rescue were accepted before this code
    existed.
    """

    payload = json.loads((staging / "result.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{staging}/result.json must contain one JSON object.")
    outputs = payload.get("outputs")
    if not isinstance(outputs, list):
        raise ValueError(f"{staging}/result.json declares no output list.")
    return project_geometry_digest(staging, outputs)
