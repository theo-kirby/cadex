# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The fit and inventory blocks every build reply carries (ADR-447).

Pure functions from published ``inspect`` values to the blocks an agent reads
after each build: ``fit_summary`` (the static fit, ADR-346, with the swept fit,
ADR-366, and what fixed joints hold, ADR-370) from ``inspect scope=clearance``,
and ``inventory_summary`` (catalog identity, ADR-362, appearance, ADR-413, and
printed edges, ADR-415) from ``inspect scope=inventory``; and ``fit_view`` and
``inventory_view``, the two blocks bounded the way a build reply shows them to
the model (ADR-435). Engine code shared by
the CLI and the shell, on ``CadexStudio``'s terms (ADR-445): the CLI loads it by
path; the shell reaches it through ``CadexStudio``'s process entry. The service
never imports it. Formerly ``cli/cadex_cli/clearance.py`` and ``inventory.py``;
moved unchanged.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


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
    if intent.get("kind") == "attached":
        # A pair an unsuppressed fixed joint welds (ADR-372). The default gap
        # is for two parts that merely stand near each other, and these two
        # are declared one rigid body: meeting face to face is the
        # declaration, not a clearance that has closed. Whether the weld's
        # solids meet at all is the attachment block's own fact, never this
        # one's. The engine publishes `minimum_mm` 0.0 beside the kind, so a
        # reader that predates this reaches the same verdict.
        return "clear"
    if intent.get("minimum_mm", minimum) - distance > MINIMUM_COMPARISON_SLACK_MM:
        # A culled row's distance is a lower bound (ADR-423): under a floor
        # the engine never saw, it decides nothing either way.
        return "unknown" if row.get("culled") else "below clearance"
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

#: Said whenever the sweep drives a part into world geometry (ADR-420).
SWEEP_WORLD_NOTE = (
    "Reported, never a swept fit failure: these pairs involve world geometry "
    "(a declared floor or plane), and each joint is swept with the body "
    "held still, so a leg reaching below its stance meets the ground. If "
    "the motion is meant to clear the ground at that pose, narrow the "
    "joint's range; the printed and purchased pairs are judged in failing."
)

#: Said whenever a part rests on world geometry at the solved pose (ADR-427).
FIT_WORLD_NOTE = (
    "Reported, never a static fit failure: these parts stand on world "
    "geometry (a declared floor or plane) closer than the minimum gap, with "
    "no common volume, which is what standing on it means. A part that "
    "interpenetrates world geometry at the solved pose still fails."
)

#: What a sweep block says when the accepted revision published no sweep at
#: all. Since ADR-367 the engine publishes coverage on every assembly, so
#: this is a revision accepted by an older engine and nothing else -- the
#: other empty sweep, an assembly with no limited joint, says
#: :data:`SWEEP_NO_JOINTS` instead.
SWEEP_NO_PUBLISHED = "No published sweep for this accepted revision."

#: What a sweep block says when every limited joint the assembly declares is
#: suppressed (ADR-371). Complete coverage of nothing swept is not a pass:
#: the mechanism declares motion and then holds it still.
SWEEP_ALL_SUPPRESSED = (
    "Every limited joint the accepted assembly declares is suppressed, so "
    "the solver ignores it and there is no motion to check. Unsuppress the "
    "joint that is meant to move for a swept check to exist."
)

#: What a sweep block says when the accepted assembly has no limited joint.
#: Since ADR-375 an unlimited joint that could move has a row of its own, so
#: this empty sweep is the assembly whose every joint is welded or suppressed
#: -- never one with an unchecked wheel in it.
SWEEP_NO_JOINTS = (
    "The accepted assembly declares no limited joint, so there is no motion "
    "to check: every joint it declares is welded or suppressed. A hinge or "
    "slider that is meant to move within a range has to declare "
    "angle_limits_degrees or length_limits_mm for a swept check to exist."
)


def sweep_summary(
    value: Any, *, minimum: float = MINIMUM_CLEARANCE_MM,
    maximum_volume: float = MAXIMUM_COMMON_VOLUME_MM3,
) -> dict[str, Any]:
    """The swept fit as a build reply carries it (ADR-366).

    ``value`` is the same ``inspect scope=clearance`` value :func:`fit_summary`
    reads, so this costs no second engine call: the published
    ``clearance_sweep`` is already in it. The block is the coverage, one
    compact row per joint carrying the three facts the charter asks for --
    minimum distance, maximum common volume and the joint value of first
    contact -- and **every** pair that interpenetrates through the motion, by
    name, the way the static block names every failing pair.

    Those three facts are read over the pairs this joint actually moves, and
    ``pairs_moving`` says how many that was (ADR-374). A pair rigid across
    the sweep repeats its solved-pose measurement at every sample: a welded
    horn touching its link would otherwise hold the joint's minimum at
    0.0 mm and claim first contact at the bottom of the range, which is the
    weld rather than anything the motion did. ``failing`` spans every pair
    that overlaps, because an overlap is an overlap.

    **A gap the motion closes fails here too** (ADR-378). Before this the
    block measured every pair's minimum distance through the range and held
    it against nothing: only interpenetration and an unmeasured pair could
    fail, so a hinge that drives two parts from 10.75 mm apart to 0.04 mm --
    a quarter of the gap the solved-pose block holds every undeclared pair
    to -- read ``pass`` with the 0.04 mm printed beside it. The four checks
    the charter asks for were applied at one pose and the sweep reported
    numbers nobody judged. A swept row now fails ``below clearance`` when
    the pair's own minimum -- its declared ``clearances=`` value, or
    ``minimum`` for a pair with nothing declared -- is not met somewhere in
    the range.

    The rule is deliberately the narrowest one that closes the hole, so the
    swept block stays strictly additive to the static one and no count it
    ever published moves:

    - Only a pair this joint moves is judged. A rigid pair repeats its
      solved-pose number, which the static block already judged.
    - Only a pair the static block calls **clear** is judged. A pair that
      already fails at the solved pose is named there; repeating it here
      would say nothing new about the motion.
    - A pair declared ``contact``, or welded by a fixed joint and so carrying
      the implied ``attached`` intent (ADR-372), is exempt, exactly as it is
      at the solved pose: parts a design asks to touch are not held to a gap.

    **A finding against world geometry is reported, never failed**
    (ADR-420). A pair one side of which the static block names world
    geometry -- a declared floor, a collision plane, ``world=True`` -- goes
    to ``world_geometry`` with the engine's reason, and neither
    ``failing_count`` nor the verdict counts it. Each joint is swept with
    the rest of the body held at the solved pose, so a standing leg's knee
    drives its foot into the ground by construction; that is the stance,
    not a fit between two parts. A printed or a purchased pair still fails.

    A swept pair with no solved-pose row is judged by none of this, because
    there is no intent and no solved verdict to read. On a published value
    that cannot happen -- the engine builds every swept row from the same
    baseline it publishes as ``pairs`` -- so it only reaches a caller that
    hands this function a sweep on its own.

    ``verdict`` is ``pass`` only when every limited joint was swept to
    completion and no pair overlaps or closes below its minimum anywhere in
    its range. A joint the engine could not sweep -- most often because the
    assembly declares no step for its kind -- is ``incomplete`` and carries
    the engine's own reason.

    A ``skipped`` joint row is a **suppressed** joint (ADR-371), which is not
    a coverage hole: the solver ignores it, so it has no range to be swept
    through and nothing about it is missing. It is counted in
    ``joints_skipped``, apart from ``joints_complete``, and the verdict is
    judged over the joints that are left -- so one suppressed joint beside a
    swept one no longer holds the whole block at ``incomplete``.

    ``unavailable`` is the verdict when there is no joint row to judge, and
    since ADR-367 that happens for **two** different reasons, which
    ``coverage`` beside it tells apart: ``coverage`` ``unavailable`` is a
    revision accepted by an older engine, which published no sweep at all,
    and ``coverage`` ``complete`` with no joint row is a current revision
    whose assembly declares no limited joint to sweep. The raw published
    ``clearance_sweep.status`` only ever means the first. A third case joins
    them since ADR-371: every limited joint the assembly declares is
    suppressed, so the block has rows and still judges none. ``reason`` says
    which one in words. None is a pass, and none refuses anything:
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
    # The solved-pose rows of the same published value, keyed by pair. They
    # carry the intent the engine resolved -- a declared `clearances=`
    # minimum, a declared contact, or the `attached` a fixed joint implies
    # (ADR-372) -- and the verdict the static block reached, which is what
    # keeps the swept check below strictly additive to it (ADR-378).
    static: dict[frozenset[str], dict[str, Any]] = {}
    for row in value.get("pairs") or []:
        if isinstance(row, dict):
            static[frozenset((str(row.get("first") or ""),
                              str(row.get("second") or "")))] = row
    # Components the static block names world geometry -- a declared floor,
    # a collision plane, a bench marked ``world=True`` -- by name, with the
    # engine's reason (ADR-420). A swept finding against one of them is the
    # environment, not the design: a knee swept with the body held still
    # drives its foot into the floor it stands on, which is physically true
    # and says nothing about whether two printed parts fit. Such a finding
    # is published under ``world_geometry`` beside ``failing`` and never in
    # it, exactly as the static block keeps the floor out of its pair
    # checks. Every other pair, printed or purchased, still fails here.
    world: dict[str, str] = {}
    for row in value.get("world_geometry") or []:
        if isinstance(row, dict) and row.get("component"):
            world[str(row["component"])] = str(row.get("reason") or "")
    joints: list[dict[str, Any]] = []
    failing: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []

    def report(finding: dict[str, Any]) -> None:
        against = [side for side in (finding["first"], finding["second"]) if side in world]
        if against:
            finding["world_geometry"] = {"component": against[0], "reason": world[against[0]]}
            advisory.append(finding)
        else:
            failing.append(finding)

    complete = skipped = 0
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
        elif item["status"] == "skipped":
            # A suppressed joint is not a coverage hole (ADR-371): the solver
            # ignores it, so there is no range it could have been swept
            # through. It is counted apart from the joints this block judges.
            skipped += 1
        minimum_distance = maximum_common = first_contact = None
        contact_pair: list[str] = []
        moving = 0
        for row in rows:
            first, second = str(row.get("first") or ""), str(row.get("second") or "")
            distance = row.get("minimum_distance_mm")
            volume = row.get("maximum_common_volume_mm3")
            contact = row.get(contact_key) if contact_key else None
            # Only a pair this joint actually moves says anything about this
            # joint (ADR-374). A pair rigid across the sweep -- a welded horn
            # and its link, two parts of the same subtree -- repeats its
            # solved-pose measurement at every sample, so it would otherwise
            # pin the joint's minimum at the weld's 0.0 mm and name first
            # contact at the bottom of the range, hiding the contact the
            # motion causes. Its gap is the static and attachment blocks'
            # fact, measured at the pose where it means something. A row
            # from a revision accepted before ADR-374 carries no flag and
            # counts as moving, so an older receipt reads as it always did.
            moves = row.get("relative_motion")
            moves = True if moves is None else bool(moves)
            moving += 1 if moves else 0
            # A distance or a volume is a magnitude; a first-contact value is
            # a joint coordinate and is negative all the time, so the sign
            # rule belongs here rather than in `_finite`.
            measured = all(_finite(v) and v >= 0 for v in (distance, volume))
            if moves and _finite(distance) and (minimum_distance is None or distance < minimum_distance):
                minimum_distance = float(distance)
            if moves and _finite(volume) and (maximum_common is None or volume > maximum_common):
                maximum_common = float(volume)
            if moves and _finite(contact) and (first_contact is None or contact < first_contact):
                first_contact, contact_pair = float(contact), [first, second]
            if not measured:
                report({
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
                report(overlap)
            elif moves:
                # A gap the motion closes (ADR-378). The pair's own minimum
                # is whatever the solved pose held it to, so the two blocks
                # cannot disagree about what "clear" means; the only new fact
                # is the pose it was measured at.
                solved = static.get(frozenset((first, second)))
                intent = (solved.get("intent") or {}) if solved else {}
                exempt = intent.get("kind") in {"contact", "attached"}
                clear = bool(solved) and pair_status(
                    solved, minimum, maximum_volume) == "clear"
                floor = float(intent.get("minimum_mm", minimum))
                if (clear and not exempt
                        and floor - distance > MINIMUM_COMPARISON_SLACK_MM):
                    closed: dict[str, Any] = {
                        "joint": name, "first": first, "second": second,
                        "status": "below clearance",
                        "minimum_distance_mm": float(distance),
                        "maximum_common_volume_mm3": float(volume),
                        "minimum_mm": floor,
                        "distance_mm": solved.get("distance_mm"),
                    }
                    if intent:
                        closed["intent"] = intent
                    if contact_key:
                        closed[contact_key] = contact
                    report(closed)
        # Counted apart so `pairs_measured - pairs_moving` is answerable, the
        # way `joints_skipped` sits beside `joints_complete` (ADR-371): the
        # three numbers below are read over these pairs and no others.
        item["pairs_moving"] = moving
        item["minimum_distance_mm"] = minimum_distance
        item["maximum_common_volume_mm3"] = maximum_common
        if first_contact is not None:
            item["first_contact"] = {
                "value": first_contact, "unit": unit, "pair": contact_pair,
            }
        joints.append(item)
    judged = len(joints) - skipped
    if failing:
        verdict = "fail"
    elif not judged:
        # No joint this block can judge: no limited joint at all, every one of
        # them suppressed (ADR-371), or no published sweep. None is a pass.
        verdict = "unavailable"
    elif coverage == "complete" and complete == judged:
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
        # Suppressed joints, counted apart so the other two counts stay
        # answerable: joints_checked - joints_complete - joints_skipped is
        # the coverage that is actually missing (ADR-371).
        "joints_skipped": skipped,
        "joints": joints,
        "thresholds": {"minimum_clearance_mm": float(minimum),
                       "maximum_common_volume_mm3": float(maximum_volume)},
        "failing_count": len(failing),
        "failing": failing,
        # Findings against world geometry (ADR-420): measured, named, and
        # never counted in `failing_count` or the verdict.
        "world_geometry_count": len(advisory),
        "world_geometry": advisory,
    }
    if advisory:
        summary["world_geometry_note"] = SWEEP_WORLD_NOTE
    if published.get("reason"):
        summary["reason"] = str(published["reason"])
    elif verdict == "unavailable" and coverage == "complete":
        summary["reason"] = SWEEP_ALL_SUPPRESSED if skipped else SWEEP_NO_JOINTS
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
    minimum distance and common volume -- never a prefix of them. A pair the
    assembly welds carries the ``attached`` intent the engine published for
    it (ADR-372) and is not held to ``minimum``: flush-mounted hardware is
    what a fixed joint asks for, and the gap under a weld is the
    ``attachments`` block's fact rather than a failing check here. A welded
    pair the design *also* gives a ``clearances=`` minimum is judged by
    that minimum, exactly as an unwelded pair is (ADR-380): a fixed joint
    holds a relative pose and does not require the solids to touch, so
    "rigidly held, and at least 0.5 mm apart" is one coherent design.
    The charter (ADR-341) asks for every failing pair in the reply itself,
    and a pointer at the scope is not the same thing: an agent that has to
    page through a second tool to learn its 41st failure will not. A pair
    the engine could not measure is failing here too -- an unknown is not a fit -- and
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
    # A part resting on world geometry is standing, not a closed gap
    # (ADR-427): a foot on the floor at 0.0 mm with no common volume is the
    # stance, as a leg swept into the floor is (ADR-420). Only the minimum
    # gap is waived. An interpenetration at the solved pose is the pose the
    # simulation starts from and still fails, and so does an unmeasured pair.
    world = {str(row["component"]): str(row.get("reason") or "")
             for row in value.get("world_geometry") or []
             if isinstance(row, dict) and row.get("component")}
    resting: list[dict[str, Any]] = []
    for row in pairs:
        status = pair_status(row, minimum, maximum_volume)
        against = [side for side in (str(row.get("first") or ""),
                                     str(row.get("second") or "")) if side in world]
        if status == "below clearance" and against:
            counts["world geometry contact"] = counts.get("world geometry contact", 0) + 1
            resting.append({
                "first": str(row.get("first") or ""),
                "second": str(row.get("second") or ""),
                "status": status,
                "distance_mm": row.get("distance_mm"),
                "common_volume_mm3": row.get("common_volume_mm3"),
                "world_geometry": {"component": against[0], "reason": world[against[0]]},
            })
            continue
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
        # Parts standing on world geometry (ADR-427): named, never failing.
        "world_geometry_contact_count": len(resting),
        "world_geometry_contacts": resting,
        # The swept half, from the same published value (ADR-366). It keeps
        # its own verdict: `verdict` above is the solved pose and stays that,
        # so a number read from either block means one thing only.
        "sweep": sweep_summary(value, minimum=minimum,
                               maximum_volume=maximum_volume),
        # ...and what the fixed joints hold, from the same value (ADR-370).
        # Its own verdict too: a gap under a weld is a measured fact about
        # the design, not one of the four checks `verdict` above counts.
        "attachments": attachment_summary(value),
    }
    if resting:
        summary["world_geometry_note"] = FIT_WORLD_NOTE
    if verdict == "unavailable":
        summary["note"] = (
            "No published assembly with pair measurements: fit is measured "
            "between assembly components, and this revision places none. A "
            "design of separate parts that are meant to fit together has to "
            "place them with assembly.component for the check to exist."
        )
    return summary


#: Where the inventory block's counts come from, said in the block itself
#: so the agent reading it cannot mistake it for the script's own claim
#: about which parts it took from the catalog.
INVENTORY_SOURCE = (
    "the published inventory of the accepted revision (inspect "
    "scope=inventory): one row per placed assembly component, with a catalog "
    "row only where the placed output is what a lib.* generator built. Not "
    "the script's stdout. Advisory, not a fit check: a printed part is "
    "expected here, a purchased part is not."
)


def printed_edges(
    components: Sequence[Mapping[str, Any]], uncatalogued: Sequence[str]
) -> dict[str, Any]:
    """P2's inputs summed over the printed components (ADR-415).

    Every placed component whose output no ``lib.*`` generator built as-is
    counts once per placement: two legs from one output are two printed
    solids. The engine reports each output's solid edge length and the
    sharp convex part of it (``sharp_edges``); a printed output without
    that fact (a mesh, or a revision built before it existed) is named
    under ``unmeasured`` rather than counted as smooth. An edge the engine
    could not evaluate counts towards the total and never as sharp, so
    ``unresolved_edges`` says how far the share is a lower bound.
    ``by_component`` keeps each measured placement's own figures, so the
    proxy can leave out the world geometry the fit names (ADR-424).
    """

    printed = set(uncatalogued)
    total = sharp = 0.0
    unresolved = 0
    measured: list[str] = []
    unmeasured: list[str] = []
    by_component: dict[str, dict[str, Any]] = {}
    for row in components:
        if str(row.get("source_output") or "") not in printed:
            continue
        name = str(row.get("component") or "")
        facts = (row.get("source_facts") or {}).get("sharp_edges")
        if not isinstance(facts, Mapping):
            unmeasured.append(name)
            continue
        own = {
            "edge_length_mm": float(facts.get("edge_length_mm") or 0.0),
            "sharp_convex_length_mm": float(facts.get("sharp_convex_length_mm") or 0.0),
            "unresolved_edges": int(facts.get("unresolved_edges") or 0),
        }
        total += own["edge_length_mm"]
        sharp += own["sharp_convex_length_mm"]
        unresolved += own["unresolved_edges"]
        measured.append(name)
        by_component[name] = own
    return {
        "edge_length_mm": round(total, 3),
        "sharp_convex_length_mm": round(sharp, 3),
        "unresolved_edges": unresolved,
        "measured": sorted(measured),
        "unmeasured": sorted(unmeasured),
        "by_component": dict(sorted(by_component.items())),
    }


def inventory_summary(value: Any) -> dict[str, Any]:
    """The catalog identity of a build as its reply carries it (ADR-362).

    ``value`` is an ``inspect scope=inventory`` value. The block is the
    component count, how many components place a catalog part, the catalog
    roll-up by ``family/part_number``, and the name of **every** placed
    output that no ``lib.*`` generator built as-is -- a hand-modelled
    bracket, but also a servo body the script drilled after taking it from
    the catalog, since a cut catalog body is no longer the catalog part.
    The block is advisory: it names no failure and refuses nothing. What
    ``derived_catalog_sources`` names the ones the engine can prove are a
    modified purchase rather than a printed part -- the catalog body their
    base was cut from (ADR-381). What
    it removes is the blind spot ot7's F5 measured over four turns, an
    agent that reported every purchased part as catalog hardware while
    the published inventory listed its servos and horns as uncatalogued,
    because nothing in its reply carried catalog identity. ``available``
    is false when the accepted revision publishes no assembly.
    """

    if not isinstance(value, Mapping):
        value = {}
    components = [
        row for row in list(value.get("components") or []) if isinstance(row, Mapping)
    ]
    counts = {
        str(key): int(count)
        for key, count in dict(value.get("catalog_counts") or {}).items()
    }
    catalogued = sum(counts.values())
    uncatalogued = sorted({
        str(item) for item in list(value.get("uncatalogued_sources") or [])
    })
    derived = [
        {
            "source_output": str(row.get("source_output") or ""),
            "family": str(row.get("family") or ""),
            "part_number": str(row.get("part_number") or ""),
        }
        for row in list(value.get("derived_catalog_sources") or [])
        if isinstance(row, Mapping)
    ]
    derived.sort(key=lambda row: row["source_output"])
    assembly = str(value.get("assembly") or "")
    summary: dict[str, Any] = {
        "available": bool(assembly),
        "source": INVENTORY_SOURCE,
        "revision": str(value.get("revision") or ""),
        "assembly": assembly,
        "component_count": len(components),
        "catalogued_count": catalogued,
        "uncatalogued_count": max(len(components) - catalogued, 0),
        "catalog_counts": dict(sorted(counts.items())),
        "uncatalogued_sources": uncatalogued,
        "derived_catalog_sources": derived,
        # What the script declared about how each part looks (ADR-413):
        # component -> role for the components that declare one, and the
        # role colours the assembly set. Undeclared parts are drawn by
        # supplier (purchased mechanism, printed shell).
        "appearance": {
            str(row.get("component") or ""): str(row["appearance"])
            for row in components if row.get("appearance")
        },
        "palette": {
            str(role): str(colour)
            for role, colour in dict(value.get("palette") or {}).items()
        },
        "printed_edges": printed_edges(components, uncatalogued),
    }
    if not assembly:
        summary["note"] = (
            "No published assembly: catalog identity is read per placed "
            "assembly component, and this revision places none."
        )
    elif uncatalogued:
        note = (
            "Each name under uncatalogued_sources is a placed output no lib.* "
            "generator built as-is. Printed parts belong here. A purchased "
            "part listed here has lost its catalog identity -- usually "
            "because the script cut, drilled or re-clocked the catalog body "
            "-- and is not catalog hardware whatever the script prints."
        )
        if derived:
            note += (
                " derived_catalog_sources names the ones the engine can "
                "prove are exactly that: "
                + ", ".join(
                    "{:s} (cut from {:s}/{:s})".format(
                        row["source_output"], row["family"], row["part_number"]
                    )
                    for row in derived
                )
                + ". Place the untouched catalog body as the component and "
                "put the cut in the printed part that receives it."
            )
        summary["note"] = note
    return summary


# --- The blocks as the model sees them: bounded, never re-judged (ADR-435) ---

#: The most rows any one list in a build reply's model view carries
#: (ADR-435): failing pairs, world-geometry contacts, unswept joints,
#: per-output details, the sharpest printed parts. Past it the list is the
#: worst rows first, with its full count and where the rest are read.
BUILD_VIEW_LIST_LIMIT = 12


def _cut(block: dict[str, Any], key: str, rows: list[Any], where: str) -> None:
    """Put ``rows`` under ``key``, cut to the limit, saying what was cut."""

    block[key] = rows[:BUILD_VIEW_LIST_LIMIT]
    if len(rows) > BUILD_VIEW_LIST_LIMIT:
        block[key + "_omitted"] = len(rows) - BUILD_VIEW_LIST_LIMIT
        block[key + "_rest"] = where


def _worst_first(rows: Any) -> list[Any]:
    """Pair findings ordered worst first; a stable sort, so ties keep order.

    Unmeasured and world-geometry rows (no numbers) lead, then the largest
    common volume, then the smallest distance: the order a designer fixes
    them in.
    """

    def number(row: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = row.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    def severity(row: Any) -> tuple[int, float, float]:
        if not isinstance(row, dict):
            return (1, 0.0, 0.0)
        volume = number(row, "common_volume_mm3", "maximum_common_volume_mm3")
        distance = number(row, "distance_mm", "minimum_distance_mm")
        if volume is None and distance is None:
            return (0, 0.0, 0.0)
        return (1, -(volume or 0.0), distance if distance is not None else 0.0)

    return sorted(list(rows or []), key=severity)


def fit_view(fit: dict[str, Any]) -> dict[str, Any]:
    """The fit block as the model sees it: bounded, never re-judged (ADR-435).

    Verdicts, counts and thresholds are the whole block's. Each list keeps
    its worst :data:`BUILD_VIEW_LIST_LIMIT` rows with a count of the rest
    and the ``inspect scope=clearance`` path that holds them. The swept
    half lists only the joints that were not swept to completion: a
    complete joint is in ``joints_complete``, and its failing pairs are in
    ``sweep.failing`` by joint name.
    """

    view = dict(fit)
    _cut(view, "failing", _worst_first(fit.get("failing")),
         "inspect scope=clearance path=/pairs (and /world_geometry)")
    if "world_geometry_contacts" in fit:
        _cut(view, "world_geometry_contacts", _worst_first(fit.get("world_geometry_contacts")),
             "inspect scope=clearance path=/pairs")
    sweep = fit.get("sweep")
    if isinstance(sweep, dict):
        swept = dict(sweep)
        joints = [joint for joint in (sweep.get("joints") or [])
                  if not (isinstance(joint, dict) and joint.get("status") == "complete")]
        _cut(swept, "joints", joints, "inspect scope=clearance path=/clearance_sweep/joints")
        swept["joints_note"] = (
            "Only joints not swept to completion are listed; every joint's row, "
            "first contact included, is inspect scope=clearance "
            "path=/clearance_sweep/joints."
        )
        _cut(swept, "failing", _worst_first(sweep.get("failing")),
             "inspect scope=clearance path=/clearance_sweep/joints")
        if "world_geometry" in sweep:
            _cut(swept, "world_geometry", _worst_first(sweep.get("world_geometry")),
                 "inspect scope=clearance path=/clearance_sweep/joints")
        view["sweep"] = swept
    attachments = fit.get("attachments")
    if isinstance(attachments, dict) and "reported" in attachments:
        held = dict(attachments)
        _cut(held, "reported", _worst_first(attachments.get("reported")),
             "inspect scope=clearance path=/attachments")
        view["attachments"] = held
    return view


def inventory_view(inventory: dict[str, Any]) -> dict[str, Any]:
    """The inventory block as the model sees it: bounded (ADR-435).

    ``appearance`` becomes a count per role and ``printed_edges`` keeps the
    parts with the most sharp convex edge -- the ones worth a fillet -- and
    its totals; every row is ``inspect scope=inventory``.
    """

    view = dict(inventory)
    appearance = inventory.get("appearance")
    if isinstance(appearance, dict):
        roles: dict[str, int] = {}
        for role in appearance.values():
            roles[str(role)] = roles.get(str(role), 0) + 1
        view["appearance"] = dict(sorted(roles.items()))
        view["appearance_note"] = (
            "Components declaring each role; which component declares which is "
            "inspect scope=inventory path=/components."
        )
    for key in ("uncatalogued_sources", "derived_catalog_sources"):
        if isinstance(inventory.get(key), list):
            _cut(view, key, list(inventory[key]), "inspect scope=inventory path=/components")
    edges = inventory.get("printed_edges")
    if isinstance(edges, dict):
        held = {key: value for key, value in edges.items() if key not in {"by_component", "measured"}}
        held["measured_count"] = len(edges.get("measured") or [])
        by_component = edges.get("by_component")
        if isinstance(by_component, dict):
            sharpest = sorted(
                by_component.items(),
                key=lambda item: -float((item[1] or {}).get("sharp_convex_length_mm") or 0.0)
                if isinstance(item[1], dict) else 0.0,
            )
            rows = [{"component": name, **(row if isinstance(row, dict) else {})}
                    for name, row in sharpest]
            _cut(held, "sharpest", rows, "inspect scope=inventory path=/components")
        if isinstance(edges.get("unmeasured"), list):
            _cut(held, "unmeasured", list(edges["unmeasured"]),
                 "inspect scope=inventory path=/components")
        view["printed_edges"] = held
    return view
