# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Read accepted pair measurements; thresholds never rebuild geometry."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .inventory import InventoryError, _cell, _read_path
from .studio import FIT_REPORT


# The fit block itself is engine code shared with the shell (ADR-447);
# this module reads the published value and writes the report.
MINIMUM_CLEARANCE_MM = FIT_REPORT.MINIMUM_CLEARANCE_MM
MINIMUM_COMPARISON_SLACK_MM = FIT_REPORT.MINIMUM_COMPARISON_SLACK_MM
MAXIMUM_COMMON_VOLUME_MM3 = FIT_REPORT.MAXIMUM_COMMON_VOLUME_MM3
pair_status = FIT_REPORT.pair_status
FIT_SOURCE = FIT_REPORT.FIT_SOURCE
SWEEP_SOURCE = FIT_REPORT.SWEEP_SOURCE
SWEEP_COVERAGE_NOTE = FIT_REPORT.SWEEP_COVERAGE_NOTE
SWEEP_WORLD_NOTE = FIT_REPORT.SWEEP_WORLD_NOTE
FIT_WORLD_NOTE = FIT_REPORT.FIT_WORLD_NOTE
SWEEP_NO_PUBLISHED = FIT_REPORT.SWEEP_NO_PUBLISHED
SWEEP_ALL_SUPPRESSED = FIT_REPORT.SWEEP_ALL_SUPPRESSED
SWEEP_NO_JOINTS = FIT_REPORT.SWEEP_NO_JOINTS
sweep_summary = FIT_REPORT.sweep_summary
ATTACHMENT_SOURCE = FIT_REPORT.ATTACHMENT_SOURCE
ATTACHMENT_NOTE = FIT_REPORT.ATTACHMENT_NOTE
ATTACHMENT_NO_PUBLISHED = FIT_REPORT.ATTACHMENT_NO_PUBLISHED
attachment_summary = FIT_REPORT.attachment_summary
fit_summary = FIT_REPORT.fit_summary


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
    sweep: bool = False,
) -> tuple[Path, dict[str, Any]]:
    for value in (minimum, maximum_volume):
        if not math.isfinite(value) or value < 0:
            raise ValueError("Clearance and volume thresholds must be finite and nonnegative.")
    value = _read_path(client, {"scope": "clearance", "target": target}, "")
    if not isinstance(value, dict) or value.get("ok") is False:
        raise InventoryError(str(value))
    if sweep:
        published = value.get("clearance_sweep") or {
            "status": "unavailable", "joints": [],
            "reason": SWEEP_NO_PUBLISHED,
        }
        value["clearance_sweep"] = published
        coverage = str(published.get("status", "unavailable"))
        # Complete coverage of nothing is not the same statement as a swept
        # mechanism, and since ADR-367 it is what an assembly with no limited
        # joint publishes. Say which one this is, the way the reply's block
        # already does, so the two surfaces cannot disagree.
        rows = [row for row in (published.get("joints") or []) if isinstance(row, dict)]
        if coverage == "complete" and not rows:
            coverage += ". " + SWEEP_NO_JOINTS.rstrip(".")
        elif coverage == "complete" and all(row.get("status") == "skipped" for row in rows):
            # Complete coverage of joints that were all suppressed (ADR-371)
            # is not a swept mechanism either, and the reply's block says so.
            coverage += ". " + SWEEP_ALL_SUPPRESSED.rstrip(".")
        text = ("# Swept clearance measurements\n\n"
                f"Accepted revision `{value['revision']}`, assembly `{value['assembly']}`.\n\n"
                f"Coverage: {coverage}.\n\n"
                "Complete coverage means measurements exist, not that fit passes. "
                "A joint reported `skipped` is suppressed: the solver ignores it, so it "
                "holds no range to sweep and its absence is not missing coverage. "
                "Missing or incomplete coverage is not a passing check. "
                "Other joints stay at the solved pose; first contact is the first "
                "sample from the lower limit within 0.001 mm, not an interpolated event.\n\n"
                "Pair minima are in mm, maximum common volumes in mm³ and timings in "
                "seconds. Each joint names its own `unit`: hinge ranges, initial "
                "values and `first_contact_degrees` are in degrees at `step_degrees`; "
                "slider ranges, initial values and `first_contact_mm` are in mm at "
                "`step_mm`. The published report follows "
                "unchanged, including incomplete reasons and runtime bounds. "
                "This command never builds or accepts geometry.\n\n"
                "```json\n" + json.dumps(published, indent=2, ensure_ascii=False) + "\n```\n")
        path = Path(root) / "docs" / "clearance-sweep.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path, value
    text = ("# Clearance and intersection\n\n"
            "<!-- Generated by `cadex clearance`; overwritten on every run. -->\n\n"
            f"Accepted revision `{value['revision']}`, assembly `{value['assembly']}`.\n"
            "Initial solved pose only; this is not a swept-motion check.\n\n"
            f"Minimum clearance: {minimum:g} mm; maximum common volume: {maximum_volume:g} mm³.\n"
            f"Distance below the minimum by more than {MINIMUM_COMPARISON_SLACK_MM:g} mm "
            "or volume above the maximum is flagged. Raw measurements are unchanged.\n\n")
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
        intent = row.get("intent") or {}
        detail = row.get("error") or (
            "contact within 0.001 mm" if intent.get("kind") == "contact" else
            "welded by " + ", ".join(intent.get("joints") or ["a fixed joint"])
            if intent.get("kind") == "attached" else
            f"declared minimum {intent['minimum_mm']:g} mm, and welded by "
            + ", ".join(intent["joints"])
            if intent.get("kind") == "clearance" and intent.get("joints") else
            f"declared minimum {intent['minimum_mm']:g} mm" if intent else ""
        )
        text += (f"| {component(row, 'first')} | {component(row, 'second')} | "
                 f"{distance if distance is not None else '—'} | {volume if volume is not None else '—'} | "
                 f"{row['status']} | {_cell(detail)} |\n")
    for world in value.get("world_geometry", []):
        text += f"\nWorld geometry: {_cell(world['component'])} — {_cell(world['reason'])}.\n"
    # What the fixed joints hold (ADR-370), beside the four checks and never
    # counted among them.
    attachments = attachment_summary(value)
    if attachments["verdict"] == "unavailable":
        text += f"\nFixed-joint attachments: {attachments['reason']}\n"
    elif attachments["verdict"] != "none":
        text += (f"\nFixed-joint attachments: {attachments['pairs_checked']} pair(s) measured, "
                 f"{attachments['reported_count']} not touching or unmeasured "
                 f"({attachments['verdict']}).\n")
        for item in attachments["reported"]:
            gap = item["distance_mm"]
            measured = f", {gap} mm apart" if gap is not None else ""
            text += (f"\n- {_cell(item['first'])} — {_cell(item['second'])} "
                     f"({_cell(', '.join(item['joints']))}): {item['status']}"
                     f"{measured}. {_cell(item['reason'])}\n")
        if attachments.get("note"):
            text += f"\n{attachments['note']}\n"
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
