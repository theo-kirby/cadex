# SPDX-License-Identifier: LGPL-2.1-or-later

"""Which outputs are parts a person means to print (ADR-156).

A project can build an assembly and could not hand one to a slicer. The
missing step is small and it is not geometry: **which** of the outputs a
script publishes are parts you intend to print, and where the STLs go.

So this is the sixth stored spec/value pair in ``script.json``, and the
first one whose specs the **script does not declare**. Every other table —
parameters, nets, boards, mounts, cages — is declared by a call in
``script.py`` and overridden by the store. There is no ``printable(...)``
global and there will not be one, for one reason: marking a part printable
changes no geometry. Routing it through ``set_params`` would fold it into
the content revision (``project_script_revision``) and buy a full rebuild
for every tick of a checkbox.

What plays the part of a declaration instead is the **accepted output
roster**: every geometry output the last accepted run published is a
candidate, and the stored values are the ones ticked. That is a better fit
than a script global anyway — the ``result`` dict already declares the
outputs, and printability is metadata *about* an output rather than a new
declared entity.

Everything else is the pattern the other five tables already have: the spec
cache is flat JSON, the stored values replace wholesale, and a name the
script no longer publishes is **pruned rather than refused** (ADR-039) —
loudly on request, silently on drift.

Like ``CadexCage``, ``CadexBoards``, ``CadexMounts`` and ``CadexNets``, this
module **imports nothing from FreeCAD and touches no kernel object**, so it
is exercised by the stubbed pytest suite exactly as it runs in the service.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

__all__ = [
    "EXPORTABLE_KINDS",
    "MAX_PRINTABLE",
    "MAX_PRINTABLE_NAME_CHARS",
    "PrintableError",
    "allocate_file_name",
    "canonical_printable_rows",
    "declared_printables",
    "effective_printables",
    "prune_printable_rows",
    "roster_from_outputs",
    "stl_file_name",
]

#: The artifact kinds an STL can be written from. A ``brep`` output is
#: tessellated on the way out; a ``mesh`` output already is one. Every other
#: output kind — a solver diagnostic, a measurement, a rollout — has no
#: surface to print and is not a candidate at all.
EXPORTABLE_KINDS = ("brep", "mesh")

#: Marks in one project. A project with more printable parts than this is
#: not a print job, and the cap keeps one bad list out of the store.
MAX_PRINTABLE = 256

#: The longest output name the worker itself accepts (``_group_result_by_domain``).
MAX_PRINTABLE_NAME_CHARS = 128

#: What a name may not carry once it becomes half of a filename. The export
#: sanitises anyway, but a control character in the *store* is a bug in
#: whatever wrote it rather than something to be quietly cleaned up.
_FORBIDDEN_CHARS = frozenset({"/", "\\", "\x00"})


class PrintableError(ValueError):
    """A printable mark that could not be stated, or could not be applied."""

    def __init__(
        self, message: str, *, details: Mapping[str, Any] | None = None
    ) -> None:
        self.details = dict(details or {})
        super().__init__(str(message))


# ---------------------------------------------------------------------------
# the roster: what the accepted run published


def roster_from_outputs(items: Any) -> dict[str, Any]:
    """The spec cache, built from one worker report's ``outputs`` list.

    Keeps the outputs that have a surface — :data:`EXPORTABLE_KINDS` — and
    records only ``name`` and ``artifact_kind``, because those are the two
    things the export needs and everything else in an output record is the
    run's business rather than the store's.
    """

    outputs: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in list(items or []):
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "")
        kind = str(item.get("artifact_kind") or "")
        if not name or name in seen or kind not in EXPORTABLE_KINDS:
            continue
        seen.add(name)
        outputs.append({"name": name, "artifact_kind": kind})
    return {"outputs": outputs}


def declared_printables(specs: Mapping[str, Any] | None) -> dict[str, str]:
    """``{output name: artifact_kind}`` from a stored ``print_specs`` block."""

    result: dict[str, str] = {}
    for entry in list((specs or {}).get("outputs") or []):
        if not isinstance(entry, Mapping):
            continue
        name = str(entry.get("name") or "")
        kind = str(entry.get("artifact_kind") or "")
        if name and kind in EXPORTABLE_KINDS:
            result[name] = kind
    return result


# ---------------------------------------------------------------------------
# the canonical row


def canonical_printable_rows(rows: Any, *, what: str) -> list[str]:
    """Validate a full mark list into canonical JSON, or refuse it.

    A row is a **name**, not an object: there is exactly one thing to say
    about an output here and an object with one key in it would be a table
    pretending to have a shape it does not have. Order is preserved and
    repeats are dropped, so the list a panel sends back is stored as the list
    it meant.
    """

    if isinstance(rows, (str, bytes, Mapping)) or not isinstance(
        rows, (list, tuple)
    ):
        raise PrintableError(
            f"{what} must be a list of output names; received {rows!r}"
        )
    if len(rows) > MAX_PRINTABLE:
        raise PrintableError(
            f"{what} holds {len(rows)} marks; a project marks at most "
            f"{MAX_PRINTABLE} parts printable"
        )
    result: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, str):
            raise PrintableError(
                f"{what}[{index}] must be an output name; received {row!r}"
            )
        name = row.strip()
        if not name:
            raise PrintableError(f"{what}[{index}] is empty")
        if len(name) > MAX_PRINTABLE_NAME_CHARS:
            raise PrintableError(
                f"{what}[{index}] is {len(name)} characters; an output name is "
                f"at most {MAX_PRINTABLE_NAME_CHARS}"
            )
        if _FORBIDDEN_CHARS & set(name) or any(ord(ch) < 0x20 for ch in name):
            raise PrintableError(
                f"{what}[{index}] {name!r} carries a path separator or a "
                "control character; an output name carries neither"
            )
        if name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def prune_printable_rows(
    rows: Sequence[Any], specs: Mapping[str, Any] | None
) -> list[str]:
    """Drop marks the accepted roster no longer publishes (ADR-039).

    Silent, and deliberately so: a script that stops publishing a part has
    not made an error, it has changed its mind, and a store that wedged on
    that is what ADR-039 was written about. The *requested* unknown name is
    the loud case, and it is refused by the op rather than here.
    """

    roster = declared_printables(specs)
    result: list[str] = []
    for row in list(rows or []):
        name = str(row or "").strip()
        if name in roster and name not in result:
            result.append(name)
    return result


def effective_printables(
    specs: Mapping[str, Any] | None, values: Any
) -> list[str]:
    """The marks as they stand: stored, validated, pruned against the roster.

    There is no declared half to fall back on — nothing is printable until
    somebody says so — which makes this the whole answer rather than a merge.
    """

    if not values:
        return []
    return prune_printable_rows(
        canonical_printable_rows(values, what="printable values"), specs
    )


# ---------------------------------------------------------------------------
# names on disk


def stl_file_name(name: str) -> str:
    """One output name as a slicer-friendly ``.stl`` filename.

    An output name is nearly always already a filename — the worker caps it
    at 128 characters and the model writes ``result["bracket"]`` — but it is
    not *guaranteed* to be one, and a name is turned into a path here rather
    than at the call site so there is one place that decides.
    """

    clean = str(name or "").strip()
    safe = "".join(
        ch if (ch.isalnum() or ch in "._-") else "_" for ch in clean
    ).strip("._-")
    if not safe:
        safe = "part"
    return f"{safe[:MAX_PRINTABLE_NAME_CHARS]}.stl"


def allocate_file_name(base: str, taken: Any) -> str:
    """``base``, or the next free ``<stem>-NNN`` beside it.

    Both halves of "keep both" use this: the ``conflict="keep_both"`` branch
    steps past what is already on disk, and one run steps past what it has
    itself just claimed when two output names sanitise to one filename.
    """

    claimed = set(str(item) for item in (taken or ()))
    if base not in claimed:
        return base
    stem, _, suffix = str(base).rpartition(".")
    stem = stem or base
    for ordinal in range(2, MAX_PRINTABLE + 2):
        candidate = "{:s}-{:03d}.{:s}".format(stem, ordinal, suffix or "stl")
        if candidate not in claimed:
            return candidate
    raise PrintableError(
        f"{base!r} already has {MAX_PRINTABLE} copies beside it; clear the "
        "print folder rather than keeping another"
    )
