# SPDX-License-Identifier: LGPL-2.1-or-later

"""Which outputs are parts a person means to print (ADR-156, ADR-158).

A project can build an assembly and could not hand one to a slicer. The
missing step is small and it is not geometry: **which** of the outputs a
script publishes are parts you intend to print, and where the STLs go.

The tick is **not stored here** (ADR-158). It was, for one slice — a sixth
spec/value pair in ``script.json`` and an op to write it — and it should not
have been: a print mark is a decision about a *view* of the model, like a
selection or a camera, not a property of the model. The shell keeps its
ticks and names the parts it wants in the ``export_printable`` call, so this
module holds only what the engine actually needs to answer that call:

- the **roster** — which of an accepted run's outputs have a surface at all,
  read off the accepted worker report rather than out of the store, so there
  is exactly one source for it and nothing to keep in step;
- the **validation** of a requested list of names;
- and the **names on disk** the export writes under.

There is no ``printable(...)`` script global and there never was. Nothing
the AI writes decides what a person prints.

Like ``CadexCage``, ``CadexBoards``, ``CadexMounts`` and ``CadexNets``, this
module **imports nothing from FreeCAD and touches no kernel object**, so it
is exercised by the stubbed pytest suite exactly as it runs in the service.
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = [
    "EXPORTABLE_KINDS",
    "MAX_PRINTABLE",
    "MAX_PRINTABLE_NAME_CHARS",
    "PrintableError",
    "allocate_file_name",
    "canonical_printable_rows",
    "printable_roster",
    "stl_file_name",
]

#: The artifact kinds an STL can be written from. A ``brep`` output is
#: tessellated on the way out; a ``mesh`` output already is one. Every other
#: output kind — a solver diagnostic, a measurement, a rollout — has no
#: surface to print and is not a candidate at all.
EXPORTABLE_KINDS = ("brep", "mesh")

#: Parts in one print job. A job with more parts than this is not a print
#: job, and the cap keeps one bad list out of the export.
MAX_PRINTABLE = 256

#: The longest output name the worker itself accepts (``_group_result_by_domain``).
MAX_PRINTABLE_NAME_CHARS = 128

#: What a name may not carry once it becomes half of a filename. The export
#: sanitises anyway, but a control character in a *requested* name is a bug
#: in whatever asked rather than something to be quietly cleaned up.
_FORBIDDEN_CHARS = frozenset({"/", "\\", "\x00"})


class PrintableError(ValueError):
    """A print job that could not be stated, or could not be written."""

    def __init__(
        self, message: str, *, details: Mapping[str, Any] | None = None
    ) -> None:
        self.details = dict(details or {})
        super().__init__(str(message))


# ---------------------------------------------------------------------------
# the roster: what the accepted run published


def printable_roster(items: Any) -> dict[str, str]:
    """``{output name: artifact_kind}`` for the outputs that have a surface.

    Built from one worker report's ``outputs`` list — the accepted report,
    at both call sites — because that is the only record of which outputs
    are artifact-backed, and deriving it rather than caching it is what
    makes "the panel's candidates" and "what the export will accept" the
    same list by construction rather than by discipline.
    """

    roster: dict[str, str] = {}
    for item in list(items or []):
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "")
        kind = str(item.get("artifact_kind") or "")
        if not name or name in roster or kind not in EXPORTABLE_KINDS:
            continue
        roster[name] = kind
    return roster


# ---------------------------------------------------------------------------
# the requested job


def canonical_printable_rows(rows: Any, *, what: str) -> list[str]:
    """Validate a requested list of names into canonical JSON, or refuse it.

    A row is a **name**, not an object: there is exactly one thing to say
    about an output here and an object with one key in it would be a table
    pretending to have a shape it does not have. Order is preserved and
    repeats are dropped, so the list a panel sends is the job it meant.
    """

    if isinstance(rows, (str, bytes, Mapping)) or not isinstance(
        rows, (list, tuple)
    ):
        raise PrintableError(
            f"{what} must be a list of output names; received {rows!r}"
        )
    if len(rows) > MAX_PRINTABLE:
        raise PrintableError(
            f"{what} holds {len(rows)} names; one print job writes at most "
            f"{MAX_PRINTABLE} parts"
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
