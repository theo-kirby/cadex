# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Read accepted pair measurements; thresholds never rebuild geometry."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .inventory import InventoryError, _ask, _cell, _read_path
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


def fit_deferred(client: Any) -> bool:
    """True when the accepted build skipped the fit (ADR-876). One page."""

    reply = _ask(client, {"scope": "clearance", "target": "", "path": "", "offset": 0, "limit": 50})
    value = reply.get("value")
    return isinstance(value, dict) and value.get("deferred") is True


def read_fit_or_unavailable(client: Any) -> dict[str, Any]:
    """:func:`read_fit` for a build that was just accepted; never raised.

    The build was accepted whatever happens here, and a reply that fails
    because its *measurement* could not be read would refuse a design for a
    reason the design did not cause. So a read failure is the block itself,
    ``verdict: unavailable`` with the reason (ADR-346).
    """

    try:
        return read_fit(client)
    except Exception as exc:  # any failure is a fit the agent cannot see
        return {
            "verdict": "unavailable",
            "source": "",
            "pairs_checked": 0,
            "failing_count": 0,
            "failing": [],
            "error": f"fit measurements could not be read: {exc}",
        }


# -- the verdict brief (ADR-689) ---------------------------------------------

#: The most failing rows each list of the brief names; past it, a count.
VERDICT_BRIEF_LIMIT = 8
#: ...and the most advisory rows (findings that fail nothing).
VERDICT_BRIEF_ADVISORY_LIMIT = 4
#: Where every row the brief cut is, said once in the brief.
VERDICT_BRIEF_REST = (
    "Every row: inspect scope=clearance path=/pairs, /panels (each row carries its "
    "verdict and findings), /clearance_sweep/joints, /components, /attachments; "
    "`cadex clearance` writes docs/clearance.md. Never rebuild only to read these."
)


def _number(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    return f"{float(value):.4g}"


def _capped(brief: dict[str, Any], key: str, rows: list[str], limit: int) -> None:
    """``rows`` under ``key``, at most ``limit``, with ``<key>_more`` past it."""

    if not rows:
        return
    brief[key] = rows[:limit]
    if len(rows) > limit:
        brief[key + "_more"] = len(rows) - limit


def _pair_phrase(row: dict[str, Any]) -> str:
    status = str(row.get("status") or "")
    head = f"{row.get('first')} ∩ {row.get('second')}: {status}"
    if row.get("error"):
        return f"{head} ({row['error']})"
    volume, distance = row.get("common_volume_mm3"), row.get("distance_mm")
    if status == "intersection":
        return f"{head} {_number(volume)} mm³"
    return f"{head} {_number(distance)} mm"


def _swept_phrase(row: dict[str, Any]) -> str:
    status = str(row.get("status") or "")
    head = f"{row.get('first')} ∩ {row.get('second')} through {row.get('joint')}: {status}"
    volume = row.get("maximum_common_volume_mm3")
    if isinstance(volume, (int, float)) and volume > 0:
        return f"{head} {_number(volume)} mm³"
    return f"{head} min {_number(row.get('minimum_distance_mm'))} mm"


def verdict_brief(fit: dict[str, Any] | None, *, limit: int = VERDICT_BRIEF_LIMIT,
                  advisory: int = VERDICT_BRIEF_ADVISORY_LIMIT) -> dict[str, Any]:
    """The fit block as a few lines an agent can act on (ADR-689).

    Every verdict and count is the whole block's; only the rows are cut, the
    worst ``limit`` failing ones per list (``advisory`` for findings that fail
    nothing) with ``<list>_more`` counting the rest. Each row is one string:
    who, what verdict, and the block's own one-line reason. Nothing is
    re-judged -- this reads :func:`fit_summary`'s block and nothing else, so
    the MCP build reply and ``cadex script --json`` say the same thing.
    """

    fit = fit if isinstance(fit, dict) else {}
    verdict = str(fit.get("verdict") or "unavailable")
    brief: dict[str, Any] = {"revision": str(fit.get("revision") or "")[:12], "fit": verdict}
    if verdict in {"unavailable", "deferred"}:
        brief["reason"] = str(fit.get("error") or fit.get("note") or "no fit was measured")
        return brief
    brief["pairs_checked"] = int(fit.get("pairs_checked") or 0)
    brief["failing_pairs"] = int(fit.get("failing_count") or 0)
    _capped(brief, "pairs", [_pair_phrase(row) for row in FIT_REPORT._worst_first(
        fit.get("failing")) if isinstance(row, dict)], limit)

    sweep = fit.get("sweep")
    if isinstance(sweep, dict):
        checked = int(sweep.get("joints_checked") or 0)
        skipped = int(sweep.get("joints_skipped") or 0) + int(sweep.get("joints_passive") or 0)
        block: dict[str, Any] = {
            "verdict": str(sweep.get("verdict") or ""),
            "joints_swept": int(sweep.get("joints_complete") or 0),
            "joints_limited": checked - skipped,
            "failing_pairs": int(sweep.get("failing_count") or 0),
        }
        if block["verdict"] == "unavailable":
            block["reason"] = str(sweep.get("reason") or sweep.get("note") or "")
        _capped(block, "unswept", [
            f"{joint.get('joint')}: {joint.get('status')}, {joint.get('reason') or 'no reason given'}"
            for joint in (sweep.get("joints") or [])
            if isinstance(joint, dict)
            and joint.get("status") not in ("complete", "passive", "skipped")], limit)
        _capped(block, "pairs", [_swept_phrase(row) for row in FIT_REPORT._worst_first(
            sweep.get("failing")) if isinstance(row, dict)], limit)
        brief["sweep"] = block

    panels = fit.get("panels")
    if isinstance(panels, dict) and int(panels.get("panel_count") or 0):
        block = {
            "verdict": str(panels.get("verdict") or ""),
            "panel_count": int(panels.get("panel_count") or 0),
            "failing": int(panels.get("failing_count") or 0),
            "advisory": int(panels.get("reported_count") or 0),
        }

        def panel(row: dict[str, Any]) -> str:
            line = f"{row.get('component')}: {', '.join(row.get('findings') or [])}"
            return line + (f" -- {row['detail']}" if row.get("detail") else "")

        _capped(block, "failing_panels", [panel(row) for row in panels.get("failing") or []
                                          if isinstance(row, dict)], limit)
        _capped(block, "advisory_panels", [panel(row) for row in panels.get("reported") or []
                                           if isinstance(row, dict)], advisory)
        if panels.get("motion_note"):
            block["motion_note"] = str(panels["motion_note"])
        brief["panels"] = block

    mounting = fit.get("mounting")
    if isinstance(mounting, dict) and int(mounting.get("purchased_count") or 0):
        block = {
            "verdict": str(mounting.get("verdict") or ""),
            "purchased": int(mounting.get("purchased_count") or 0),
            "held": int(mounting.get("held_count") or 0),
        }
        _capped(block, "not_held", [
            f"{row.get('component')}: {row.get('status')} -- {row.get('detail') or ''}".rstrip(" -")
            for row in mounting.get("reported") or [] if isinstance(row, dict)], limit)
        brief["mounting"] = block

    attachments = fit.get("attachments")
    if isinstance(attachments, dict) and int(attachments.get("pairs_checked") or 0):
        block = {
            "verdict": str(attachments.get("verdict") or ""),
            "welded_pairs": int(attachments["pairs_checked"]),
            "not_touching": int(attachments.get("reported_count") or 0),
        }
        _capped(block, "gaps", [
            f"{row.get('first')} -- {row.get('second')} ({', '.join(row.get('joints') or [])}): "
            f"{row.get('status')} {_number(row.get('distance_mm'))} mm"
            # The widest gap first: it is the weld least likely to be a shim.
            for row in sorted((row for row in attachments.get("reported") or []
                               if isinstance(row, dict)),
                              key=lambda row: -(row["distance_mm"] if isinstance(
                                  row.get("distance_mm"), (int, float)) else math.inf))],
            advisory)
        brief["attachments"] = block

    blocks = [brief] + [value for value in brief.values() if isinstance(value, dict)]
    # Pointed at only when the brief named a row: a clean build needs no map.
    if any(isinstance(item, list) for block in blocks for item in block.values()):
        brief["rest"] = VERDICT_BRIEF_REST
    return brief


def verdict_lines(brief: dict[str, Any]) -> list[str]:
    """The brief as the prose report prints it, one finding a line."""

    if not brief:
        return []
    lines: list[str] = []

    def rows(block: dict[str, Any], key: str) -> None:
        lines.extend(f"  {row}" for row in block.get(key) or [])
        if block.get(key + "_more"):
            lines.append(f"  ... and {block[key + '_more']} more")

    verdict = str(brief.get("fit") or "")
    if verdict in {"unavailable", "deferred"}:
        lines.append(f"fit    {verdict}: {brief.get('reason') or ''}")
        return lines
    lines.append("fit    {:s}  {:d} failing of {:d} pair(s)  (revision {:s})".format(
        verdict, int(brief.get("failing_pairs") or 0), int(brief.get("pairs_checked") or 0),
        str(brief.get("revision") or "")))
    rows(brief, "pairs")
    sweep = brief.get("sweep")
    if isinstance(sweep, dict):
        if sweep.get("verdict") == "unavailable":
            lines.append(f"sweep  unavailable: {sweep.get('reason') or ''}")
        else:
            lines.append("sweep  {:s}  {:d} of {:d} joint(s) swept, {:d} failing pair(s)".format(
                str(sweep.get("verdict")), int(sweep.get("joints_swept") or 0),
                int(sweep.get("joints_limited") or 0), int(sweep.get("failing_pairs") or 0)))
        rows(sweep, "unswept")
        rows(sweep, "pairs")
    panels = brief.get("panels")
    if isinstance(panels, dict):
        lines.append("panels {:s}  {:d} of {:d} failing, {:d} advisory".format(
            str(panels.get("verdict")), int(panels.get("failing") or 0),
            int(panels.get("panel_count") or 0), int(panels.get("advisory") or 0)))
        rows(panels, "failing_panels")
        rows(panels, "advisory_panels")
    mounting = brief.get("mounting")
    if isinstance(mounting, dict):
        lines.append("mount  {:s}  {:d} of {:d} purchased part(s) held".format(
            str(mounting.get("verdict")), int(mounting.get("held") or 0),
            int(mounting.get("purchased") or 0)))
        rows(mounting, "not_held")
    attachments = brief.get("attachments")
    if isinstance(attachments, dict) and attachments.get("not_touching"):
        lines.append("welds  {:s}  {:d} of {:d} welded pair(s) not touching (advisory)".format(
            str(attachments.get("verdict")), int(attachments.get("not_touching") or 0),
            int(attachments.get("welded_pairs") or 0)))
        rows(attachments, "gaps")
    if brief.get("rest"):
        lines.append(f"       {brief['rest']}")
    return lines


def judge_panel_rows(value: Any, fit: dict[str, Any] | None) -> Any:
    """``inspect scope=clearance`` panel rows with the fit's verdict on each (ADR-689).

    ``value`` is the page an ``inspect`` of ``/panels`` or ``/panels/N``
    returned: a list of rows or one row, each naming its ``component``. The
    engine publishes what each panel measures; whether that fails is
    :func:`panel_summary`'s judgement, made on this side (the service never
    imports the fit code, ADR-445). Each row gains that judgement --
    ``verdict`` (``fail``, ``reported`` or ``pass``), ``findings`` and the
    one-line ``detail`` -- read from ``fit``'s panel block, never re-judged.
    A row the block does not name is left as published.
    """

    panels = (fit or {}).get("panels") if isinstance(fit, dict) else None
    if not isinstance(panels, dict):
        return value
    judged: dict[str, tuple[str, dict[str, Any]]] = {}
    for key, verdict in (("failing", "fail"), ("reported", "reported"), ("fitted", "pass")):
        for item in panels.get(key) or []:
            if isinstance(item, dict) and item.get("component"):
                judged[str(item["component"])] = (verdict, item)

    def judge(row: Any) -> Any:
        if not isinstance(row, dict) or str(row.get("component") or "") not in judged:
            return row
        verdict, item = judged[str(row["component"])]
        row = {**row, "verdict": verdict, "findings": list(item.get("findings") or [])}
        for key in ("detail", "mounted", "held_by", "floating_at_mm", "colliding_with",
                    "colliding_in_motion", "closest_in_motion"):
            if key in item:
                row[key] = item[key]
        return row

    if isinstance(value, list):
        return [judge(row) for row in value]
    return judge(value)


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
                "A joint reported `passive` is a joint of a closed loop with no limits of "
                "its own: the loop is swept from its limited joints and re-closed at every "
                "sample, so it moved with them and their rows hold what it moved (ADR-621). "
                "Missing or incomplete coverage is not a passing check. "
                "Other joints stay at the solved pose, except a swept loop's own; first contact is the first "
                "sample from the lower limit within 0.001 mm, not an interpolated event.\n\n"
                "Pair minima are in mm, maximum common volumes in mm³ and timings in "
                "seconds. Each joint names its own `unit`: hinge ranges, initial "
                "values and `first_contact_degrees` are in degrees at `step_degrees`; "
                "slider ranges, initial values and `first_contact_mm` are in mm at "
                "`step_mm`. Each joint's `pairs` are the pairs it moves that were measured "
                "exactly; `pairs_rigid` counts the pairs it does not move (their numbers are "
                "the solved-pose report's), and `pairs_culled` the moving pairs bound past "
                "their floor, the least bound `culled_minimum_distance_mm` (ADR-692). "
                "The published report follows "
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

    allowances = FIT_REPORT.thread_allowances(value)
    for row in value["pairs"]:
        row["status"] = pair_status(row, minimum, maximum_volume)
        if row["status"] == "intersection" and FIT_REPORT._threaded(
                row, allowances, row.get("common_volume_mm3")):
            # A bolt's thread in a printed part, no deeper than it reaches (ADR-492).
            row["status"] = "threaded"
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
