# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Read accepted pair measurements; thresholds never rebuild geometry."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .inventory import InventoryError, _cell, _read_path


MINIMUM_CLEARANCE_MM = 0.1
# Matches the engine comparison contract; never round published measurements.
MINIMUM_COMPARISON_SLACK_MM = 1e-9
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
    intent = row.get("intent") or {}
    if intent.get("kind") == "contact":
        return "missed contact" if distance > 1e-3 else "clear"
    if intent.get("minimum_mm", minimum) - distance > MINIMUM_COMPARISON_SLACK_MM:
        return "below clearance"
    return "clear"


#: Where the fit block's numbers come from, said in the block itself so the
#: agent reading it cannot mistake it for the script's own printout.
FIT_SOURCE = (
    "engine measurements of the exact solids at the solved pose, published "
    "with the accepted revision (inspect scope=clearance). Not the script's "
    "stdout; not a swept-motion check."
)


#: Where the sweep block's numbers come from, said in the block itself for
#: the same reason the static one says it (ADR-366).
SWEEP_SOURCE = (
    "engine measurements of the exact solids at poses across each limited "
    "joint's declared range, published with the accepted revision (inspect "
    "scope=clearance path=/clearance_sweep). Other joints hold the solved "
    "pose. Not the script's stdout; missing coverage is not a passing check."
)

#: Said in the block whenever its verdict is not ``pass``: coverage is
#: evidence, and its absence is not the absence of a problem.
SWEEP_COVERAGE_NOTE = (
    "Coverage means measurements exist, not that fit passes: a joint that "
    "was not swept has been checked at one pose only. Declare "
    "sweep_step_degrees (limited hinges) and sweep_step_mm (limited sliders) "
    "on the assembly and rebuild to acquire the missing measurements."
)

#: What a sweep block says when the accepted revision published no sweep at
#: all. Since ADR-367 the engine publishes coverage on every assembly, so
#: this is a revision accepted by an older engine and nothing else -- the
#: other empty sweep, an assembly with no limited joint, says
#: :data:`SWEEP_NO_JOINTS` instead.
SWEEP_NO_PUBLISHED = "No published sweep for this accepted revision."

#: What a sweep block says when the accepted assembly has no limited joint.
SWEEP_NO_JOINTS = (
    "The accepted assembly declares no limited joint, so there is no motion "
    "to check: every joint is unlimited, suppressed or welded. A hinge or "
    "slider that is meant to move within a range has to declare "
    "angle_limits_degrees or length_limits_mm for a swept check to exist."
)


def sweep_summary(
    value: Any, *, maximum_volume: float = MAXIMUM_COMMON_VOLUME_MM3,
) -> dict[str, Any]:
    """The swept fit as a build reply carries it (ADR-366).

    ``value`` is the same ``inspect scope=clearance`` value :func:`fit_summary`
    reads, so this costs no second engine call: the published
    ``clearance_sweep`` is already in it. The block is the coverage, one
    compact row per joint carrying the three facts the charter asks for --
    minimum distance, maximum common volume and the joint value of first
    contact -- and **every** pair that interpenetrates through the motion, by
    name, the way the static block names every failing pair.

    ``verdict`` is ``pass`` only when every limited joint was swept to
    completion and no pair overlaps anywhere in its range. A joint the engine
    could not sweep -- most often because the assembly declares no step for
    its kind -- is ``incomplete`` and carries the engine's own reason.

    ``unavailable`` is the verdict when there is no joint row to judge, and
    since ADR-367 that happens for **two** different reasons, which
    ``coverage`` beside it tells apart: ``coverage`` ``unavailable`` is a
    revision accepted by an older engine, which published no sweep at all,
    and ``coverage`` ``complete`` with no joint row is a current revision
    whose assembly declares no limited joint to sweep. The raw published
    ``clearance_sweep.status`` only ever means the first. ``reason`` says
    which one in words. Neither is a pass, and neither refuses anything:
    this is advisory, like the static block beside it.
    """

    if not isinstance(value, dict):
        value = {}
    published = value.get("clearance_sweep")
    if not isinstance(published, dict):
        published = {
            "status": "unavailable", "joints": [],
            "reason": SWEEP_NO_PUBLISHED,
        }
    coverage = str(published.get("status") or "unavailable")
    joints: list[dict[str, Any]] = []
    failing: list[dict[str, Any]] = []
    complete = 0
    for joint in published.get("joints") or []:
        if not isinstance(joint, dict):
            continue
        name = str(joint.get("joint") or "")
        unit = str(joint.get("unit") or "")
        contact_key = ("first_contact_" + unit) if unit else ""
        rows = [row for row in (joint.get("pairs") or []) if isinstance(row, dict)]
        item: dict[str, Any] = {
            "joint": name,
            "kind": str(joint.get("kind") or ""),
            "unit": unit,
            "status": str(joint.get("status") or ""),
            "pairs_measured": len(rows),
        }
        for key in ("step", "sample_count", "range_" + unit, "initial_" + unit):
            if joint.get(key) is not None:
                item[key] = joint[key]
        if joint.get("reason"):
            item["reason"] = str(joint["reason"])
        if item["status"] == "complete":
            complete += 1
        minimum_distance = maximum_common = first_contact = None
        contact_pair: list[str] = []
        for row in rows:
            first, second = str(row.get("first") or ""), str(row.get("second") or "")
            distance = row.get("minimum_distance_mm")
            volume = row.get("maximum_common_volume_mm3")
            contact = row.get(contact_key) if contact_key else None
            # A distance or a volume is a magnitude; a first-contact value is
            # a joint coordinate and is negative all the time, so the sign
            # rule belongs here rather than in `_finite`.
            measured = all(_finite(v) and v >= 0 for v in (distance, volume))
            if _finite(distance) and (minimum_distance is None or distance < minimum_distance):
                minimum_distance = float(distance)
            if _finite(volume) and (maximum_common is None or volume > maximum_common):
                maximum_common = float(volume)
            if _finite(contact) and (first_contact is None or contact < first_contact):
                first_contact, contact_pair = float(contact), [first, second]
            if not measured:
                failing.append({
                    "joint": name, "first": first, "second": second,
                    "status": "unknown",
                    "minimum_distance_mm": distance,
                    "maximum_common_volume_mm3": volume,
                    "error": str(row.get("error") or "no swept measurement for this pair"),
                })
            elif volume > maximum_volume:
                overlap: dict[str, Any] = {
                    "joint": name, "first": first, "second": second,
                    "status": "intersection",
                    "minimum_distance_mm": float(distance),
                    "maximum_common_volume_mm3": float(volume),
                }
                if contact_key:
                    overlap[contact_key] = contact
                failing.append(overlap)
        item["minimum_distance_mm"] = minimum_distance
        item["maximum_common_volume_mm3"] = maximum_common
        if first_contact is not None:
            item["first_contact"] = {
                "value": first_contact, "unit": unit, "pair": contact_pair,
            }
        joints.append(item)
    if failing:
        verdict = "fail"
    elif not joints:
        verdict = "unavailable"
    elif coverage == "complete" and complete == len(joints):
        verdict = "pass"
    else:
        verdict = "incomplete"
    summary: dict[str, Any] = {
        "verdict": verdict,
        "source": SWEEP_SOURCE,
        "coverage": coverage,
        "step_degrees": published.get("step_degrees"),
        "step_mm": published.get("step_mm"),
        "joints_checked": len(joints),
        "joints_complete": complete,
        "joints": joints,
        "thresholds": {"maximum_common_volume_mm3": float(maximum_volume)},
        "failing_count": len(failing),
        "failing": failing,
    }
    if published.get("reason"):
        summary["reason"] = str(published["reason"])
    elif verdict == "unavailable" and coverage == "complete":
        summary["reason"] = SWEEP_NO_JOINTS
    if verdict != "pass":
        summary["note"] = SWEEP_COVERAGE_NOTE
    return summary


#: Where the attachment block's numbers come from, said in the block itself
#: for the same reason the other two say it (ADR-370).
ATTACHMENT_SOURCE = (
    "engine measurements of the exact solids at the solved pose for every "
    "pair joined by an unsuppressed fixed joint (inspect scope=clearance "
    "path=/attachments). A fixed joint asserts the two components are one "
    "rigid body; a measured gap between them is a connection the geometry "
    "does not make. Not the script's stdout."
)

#: Said whenever a fixed-joint pair does not touch: the finding is a measured
#: fact and a question for the design, never one of the four fit checks.
ATTACHMENT_NOTE = (
    "Reported, never a fit failure: a standoff, a shim or a captive fastener "
    "between two welded parts is a legitimate design, and only the design "
    "knows which this is. If nothing is meant to sit in the gap, the parts "
    "are held together by a joint and not by geometry -- close the gap and "
    "declare the pair a contact."
)

#: What the block says on a revision accepted before ADR-370, which published
#: no attachment report at all. Absence of the report is not absence of a gap.
ATTACHMENT_NO_PUBLISHED = (
    "No published attachment report for this accepted revision: it was "
    "accepted by an engine that measured no fixed-joint pair. Rebuild to "
    "acquire the measurements."
)


def attachment_summary(value: Any) -> dict[str, Any]:
    """What the fixed joints of an accepted design actually hold (ADR-370).

    ``value`` is the same ``inspect scope=clearance`` value :func:`fit_summary`
    reads, so like the swept block this costs no second engine call. The block
    is the count of fixed-joint pairs and **every** one whose solids do not
    meet, by name, with the joints that declare it and the measured gap.

    ``verdict`` is ``touching`` when every fixed-joint pair meets,
    ``reported`` when at least one does not, ``unknown`` when one could not
    be measured and none is open, ``none`` when the assembly declares no
    fixed joint, and ``unavailable`` when the revision published no report.
    None of them refuses anything, and none of them is counted among the fit
    failures beside it.
    """

    if not isinstance(value, dict):
        value = {}
    published = value.get("attachments")
    if not isinstance(published, list):
        return {
            "verdict": "unavailable", "source": ATTACHMENT_SOURCE,
            "pairs_checked": 0, "reported_count": 0, "reported": [],
            "reason": ATTACHMENT_NO_PUBLISHED,
        }
    rows = [row for row in published if isinstance(row, dict)]
    reported = [
        {
            "first": str(row.get("first") or ""),
            "second": str(row.get("second") or ""),
            "joints": [str(name) for name in (row.get("joints") or [])],
            "status": str(row.get("status") or ""),
            "distance_mm": row.get("distance_mm"),
            "common_volume_mm3": row.get("common_volume_mm3"),
            "reason": str(row.get("reason") or ""),
        }
        for row in rows
        if str(row.get("status") or "") != "touching"
    ]
    if any(item["status"] == "not touching" for item in reported):
        verdict = "reported"
    elif reported:
        verdict = "unknown"
    elif rows:
        verdict = "touching"
    else:
        verdict = "none"
    summary: dict[str, Any] = {
        "verdict": verdict,
        "source": ATTACHMENT_SOURCE,
        "thresholds": {"contact_tolerance_mm": 1.0e-3},
        "pairs_checked": len(rows),
        "reported_count": len(reported),
        "reported": reported,
    }
    if verdict == "none":
        summary["reason"] = (
            "The accepted assembly declares no unsuppressed fixed joint, so "
            "no pair is asserted to be one rigid body."
        )
    if reported:
        summary["note"] = ATTACHMENT_NOTE
    return summary


def _finite(number: Any) -> bool:
    """A measurement the block can compare, rather than a hole in the report."""

    return isinstance(number, (int, float)) and not isinstance(number, bool) and math.isfinite(number)


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

    ``sweep`` and ``attachments`` are the swept fit (ADR-366) and what the
    fixed joints actually hold (ADR-370), each from the same published value
    and each keeping its own verdict: a number read from any of the three
    blocks means one thing only.
    """

    if not isinstance(value, dict):
        value = {}
    pairs = [row for row in (value.get("pairs") or []) if isinstance(row, dict)]
    counts = {"clear": 0, "intersection": 0, "below clearance": 0, "unknown": 0}
    failing: list[dict[str, Any]] = []
    for row in pairs:
        status = pair_status(row, minimum, maximum_volume)
        counts[status] = counts.get(status, 0) + 1
        if status == "clear":
            continue
        item: dict[str, Any] = {
            "first": str(row.get("first") or ""),
            "second": str(row.get("second") or ""),
            "status": status,
            "distance_mm": row.get("distance_mm"),
            "common_volume_mm3": row.get("common_volume_mm3"),
        }
        if row.get("intent"):
            item["intent"] = row["intent"]
        if row.get("fit_failures"):
            item["fit_failures"] = row["fit_failures"]
        if row.get("error"):
            item["error"] = str(row["error"])
        failing.append(item)
    for world in value.get("world_geometry", []):
        counts["world geometry"] = counts.get("world geometry", 0) + 1
        failing.append({"first": world["component"], "second": "",
                        "status": "world geometry", "distance_mm": None,
                        "common_volume_mm3": None, "error": world["reason"]})
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
        # The swept half, from the same published value (ADR-366). It keeps
        # its own verdict: `verdict` above is the solved pose and stays that,
        # so a number read from either block means one thing only.
        "sweep": sweep_summary(value, maximum_volume=maximum_volume),
        # ...and what the fixed joints hold, from the same value (ADR-370).
        # Its own verdict too: a gap under a weld is a measured fact about
        # the design, not one of the four checks `verdict` above counts.
        "attachments": attachment_summary(value),
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
        if coverage == "complete" and not published.get("joints"):
            coverage += ". " + SWEEP_NO_JOINTS.rstrip(".")
        text = ("# Swept clearance measurements\n\n"
                f"Accepted revision `{value['revision']}`, assembly `{value['assembly']}`.\n\n"
                f"Coverage: {coverage}.\n\n"
                "Complete coverage means measurements exist, not that fit passes. "
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
