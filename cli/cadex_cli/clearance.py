# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Read accepted pair measurements; thresholds never rebuild geometry."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .inventory import InventoryError, _cell, _read_path


MINIMUM_CLEARANCE_MM = 0.1
MAXIMUM_COMMON_VOLUME_MM3 = 1.0e-6


def pair_status(row: dict[str, Any], minimum: float, maximum_volume: float) -> str:
    distance, volume = row.get("distance_mm"), row.get("common_volume_mm3")
    if row.get("error") or any(
        not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0
        for v in (distance, volume)
    ):
        return "unknown"
    if volume > maximum_volume:
        return "intersection"
    if distance < minimum:
        return "below clearance"
    return "clear"


#: Where the fit block's numbers come from, said in the block itself so the
#: agent reading it cannot mistake it for the script's own printout.
FIT_SOURCE = (
    "engine measurements of the exact solids at the solved pose, published "
    "with the accepted revision (inspect scope=clearance). Not the script's "
    "stdout; not a swept-motion check."
)


def fit_summary(
    value: Any, *,
    minimum: float = MINIMUM_CLEARANCE_MM,
    maximum_volume: float = MAXIMUM_COMMON_VOLUME_MM3,
) -> dict[str, Any]:
    """The measured fit as a build reply carries it (ADR-346).

    ``value`` is an ``inspect scope=clearance`` value. The block is the
    check counts and **every** pair that is not clear, by name, with its
    minimum distance and common volume -- never a prefix of them. The
    charter (ADR-341) asks for every failing pair in the reply itself, and
    a pointer at the scope is not the same thing: an agent that has to page
    through a second tool to learn its 41st failure will not. A pair the engine
    could not measure is failing here too -- an unknown is not a fit -- and
    carries the engine's reason. ``verdict`` is ``pass`` only when every
    pair was measured and every pair is clear; ``unavailable`` when the
    accepted revision publishes no assembly at all, which is a script with
    nothing to fit rather than one that fails.
    """

    if not isinstance(value, dict):
        value = {}
    pairs = [row for row in (value.get("pairs") or []) if isinstance(row, dict)]
    counts = {"clear": 0, "intersection": 0, "below clearance": 0, "unknown": 0}
    failing: list[dict[str, Any]] = []
    for row in pairs:
        status = pair_status(row, minimum, maximum_volume)
        counts[status] += 1
        if status == "clear":
            continue
        item: dict[str, Any] = {
            "first": str(row.get("first") or ""),
            "second": str(row.get("second") or ""),
            "status": status,
            "distance_mm": row.get("distance_mm"),
            "common_volume_mm3": row.get("common_volume_mm3"),
        }
        if row.get("error"):
            item["error"] = str(row["error"])
        failing.append(item)
    available = bool(value.get("available")) or bool(pairs)
    if not available:
        verdict = "unavailable"
    elif failing:
        verdict = "fail"
    else:
        verdict = "pass"
    summary: dict[str, Any] = {
        "verdict": verdict,
        "source": FIT_SOURCE,
        "revision": str(value.get("revision") or ""),
        "assembly": str(value.get("assembly") or ""),
        "pose": str(value.get("pose") or ""),
        "thresholds": {
            "minimum_clearance_mm": float(minimum),
            "maximum_common_volume_mm3": float(maximum_volume),
        },
        "pairs_checked": len(pairs),
        "counts": counts,
        "failing_count": len(failing),
        "failing": failing,
    }
    if verdict == "unavailable":
        summary["note"] = (
            "No published assembly with pair measurements: fit is measured "
            "between assembly components, and this revision places none. A "
            "design of separate parts that are meant to fit together has to "
            "place them with assembly.component for the check to exist."
        )
    return summary


def read_fit(
    client: Any, *,
    minimum: float = MINIMUM_CLEARANCE_MM,
    maximum_volume: float = MAXIMUM_COMMON_VOLUME_MM3,
) -> dict[str, Any]:
    """Read the published clearance scope, every page, and summarise it."""

    value = _read_path(client, {"scope": "clearance", "target": ""}, "")
    if not isinstance(value, dict) or value.get("ok") is False:
        raise InventoryError(str(value))
    return fit_summary(value, minimum=minimum, maximum_volume=maximum_volume)


def write_clearance(
    client: Any, root: Path | str, *, target: str = "",
    minimum: float = MINIMUM_CLEARANCE_MM,
    maximum_volume: float = MAXIMUM_COMMON_VOLUME_MM3,
) -> tuple[Path, dict[str, Any]]:
    for value in (minimum, maximum_volume):
        if not math.isfinite(value) or value < 0:
            raise ValueError("Clearance and volume thresholds must be finite and nonnegative.")
    value = _read_path(client, {"scope": "clearance", "target": target}, "")
    if not isinstance(value, dict) or value.get("ok") is False:
        raise InventoryError(str(value))
    text = ("# Clearance and intersection\n\n"
            "<!-- Generated by `cadex clearance`; overwritten on every run. -->\n\n"
            f"Accepted revision `{value['revision']}`, assembly `{value['assembly']}`.\n"
            "Initial solved pose only; this is not a swept-motion check.\n\n"
            f"Minimum clearance: {minimum:g} mm; maximum common volume: {maximum_volume:g} mm³.\n"
            "Distance below the minimum or volume above the maximum is flagged.\n\n")
    if not value.get("available"):
        text += "Measurements unavailable: no published assembly or no pair measurements; rebuild if needed.\n\n"
    text += "| first | second | distance (mm) | common volume (mm³) | verdict | detail |\n|---|---|---|---|---|---|\n"

    def component(row: dict[str, Any], side: str) -> str:
        catalog = row.get(side + "_catalog") or {}
        identity = (
            "/".join(str(catalog.get(key) or "") for key in ("family", "part_number"))
            if catalog else "uncatalogued"
        )
        return _cell(f"{row[side]} ({row.get(side + '_label', row[side])}; {identity})")

    for row in value["pairs"]:
        row["status"] = pair_status(row, minimum, maximum_volume)
        distance = row.get("distance_mm")
        volume = row.get("common_volume_mm3")
        text += (f"| {component(row, 'first')} | {component(row, 'second')} | "
                 f"{distance if distance is not None else '—'} | {volume if volume is not None else '—'} | "
                 f"{row['status']} | {_cell(row.get('error'))} |\n")
    path = Path(root) / "docs" / "clearance.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, value


#: How far a tessellated world bound may disagree with a kernel distance before
#: the disagreement is a defect rather than float32 resolution. The render's
#: bounds come from `f32` tessellation vertices at up to ~1e3 mm, so ~1e-4 mm of
#: slack is inherent; 1e-3 mm keeps a margin over it and is still four orders of
#: magnitude tighter than the smallest finding the report has ever named.
BOUNDS_TOLERANCE_MM = 1.0e-3


def bounds_agreement(
    pairs: list[dict[str, Any]], objects: dict[str, Any] | None, *,
    tolerance_mm: float = BOUNDS_TOLERANCE_MM,
) -> dict[str, Any]:
    """Check each measured pair against the render's independent world bounds.

    The clearance numbers come from the kernel, through ``App::Link`` placement
    composition (ADR-241). The render's ``bounds_mm`` come from a different
    path entirely — placed tessellation vertices, transformed in this process.
    Two implications hold between them whatever the geometry is, and neither
    holds if a component is measured in the wrong frame:

    1. **Distance is at least the axis-aligned separation.** If the two boxes
       are disjoint along some axis by ``g``, no point of one is within ``g``
       of the other, so ``distance_mm >= g``.
    2. **Common volume fits inside the box overlap.** The intersection of two
       solids lies inside the intersection of their bounding boxes.

    Two comparisons per pair, both stated as inequalities that a correct
    report satisfies with room to spare, and that the pre-ADR-241 frame defect
    violated by three orders of magnitude. This is agreement between two
    surfaces, **not** validation of either: a check that passes says the two
    paths tell the same story, not that the story is true. Boxes are padded by
    ``tolerance_mm`` on every side, so one knob governs both comparisons.

    A pair whose components the render did not draw, or whose measurement is
    unknown, is skipped rather than failed — there is nothing to compare.
    """

    if not math.isfinite(tolerance_mm) or tolerance_mm < 0:
        raise ValueError("Bounds tolerance must be finite and nonnegative.")
    objects = objects or {}
    if not objects:
        return {"status": "unavailable", "reason": "no rendered object bounds",
                "tolerance_mm": tolerance_mm, "comparisons": 0, "failures": []}
    compared = skipped = 0
    failures: list[dict[str, Any]] = []
    worst_distance_mm = worst_volume_mm3 = 0.0
    for row in pairs:
        boxes = [objects.get(row.get(side, "")) or {} for side in ("first", "second")]
        bounds = [box.get("bounds_mm") for box in boxes]
        distance, volume = row.get("distance_mm"), row.get("common_volume_mm3")
        if (
            row.get("status") == "unknown"
            or any(
                not isinstance(box, list) or len(box) != 2
                or any(not isinstance(c, (int, float)) or not math.isfinite(c)
                       for corner in box for c in corner)
                for box in bounds
            )
            or not all(isinstance(v, (int, float)) and math.isfinite(v)
                       for v in (distance, volume))
        ):
            skipped += 1
            continue
        (lo_a, hi_a), (lo_b, hi_b) = bounds
        overlap = [
            min(hi_a[axis], hi_b[axis]) - max(lo_a[axis], lo_b[axis]) + 2 * tolerance_mm
            for axis in range(3)
        ]
        # Disjoint along any one axis is enough to separate the boxes, and
        # the widest such separation is the strongest lower bound on distance.
        gap_mm = max(0.0, -min(overlap))
        ceiling_mm3 = 1.0
        for extent in overlap:
            ceiling_mm3 *= max(0.0, extent)
        compared += 2
        for kind, excess in (
            ("distance", gap_mm - float(distance)),
            ("volume", float(volume) - ceiling_mm3),
        ):
            if excess <= 0:
                continue
            if kind == "distance":
                worst_distance_mm = max(worst_distance_mm, excess)
            else:
                worst_volume_mm3 = max(worst_volume_mm3, excess)
            failures.append({
                "components": [row["first"], row["second"]], "check": kind,
                "reported": float(distance if kind == "distance" else volume),
                "bound": gap_mm if kind == "distance" else ceiling_mm3,
                "excess": excess,
            })
    return {
        "status": "fail" if failures else ("pass" if compared else "unavailable"),
        "tolerance_mm": tolerance_mm,
        "comparisons": compared,
        "pairs_compared": compared // 2,
        "pairs_skipped": skipped,
        "failure_count": len(failures),
        "failures": failures[:16],
        "worst_distance_excess_mm": worst_distance_mm,
        "worst_volume_excess_mm3": worst_volume_mm3,
    }
