# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The fit and inventory blocks every build reply carries (ADR-447).

Pure functions from published ``inspect`` values to the blocks an agent reads
after each build: ``fit_summary`` (the static fit, ADR-346, with the swept fit,
ADR-366, what fixed joints hold, ADR-370, and what holds each purchased
part, ADR-486) from ``inspect scope=clearance``,
and ``inventory_summary`` (catalog identity, ADR-362, appearance, ADR-413, and
printed edges, ADR-415) from ``inspect scope=inventory``; and ``fit_view`` and
``inventory_view``, the two blocks bounded the way a build reply shows them to
the model (ADR-435). Engine code on
``CadexStudio``'s terms (ADR-445): the CLI loads it by path. The service
never imports it. Formerly ``cli/cadex_cli/clearance.py`` and ``inventory.py``;
moved unchanged.
"""
from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence


MINIMUM_CLEARANCE_MM = 0.1
# Matches the engine comparison contract; never round published measurements.
MINIMUM_COMPARISON_SLACK_MM = 1e-9
MAXIMUM_COMMON_VOLUME_MM3 = 1.0e-6


#: ISO 261 minor diameters by nominal diameter (mm), the depth a bolt's
#: thread reaches; equal to ``CadexCatalog.METRIC_THREADS`` (a test holds
#: them equal), copied because this module is loaded by path and imports
#: nothing of the engine's.
THREAD_MINOR_DIAMETER_MM = {
    1.6: 1.221, 2.0: 1.567, 2.5: 2.013, 3.0: 2.459,
    4.0: 3.242, 5.0: 4.134, 6.0: 4.917, 8.0: 6.647,
}
_BOLT_PART_NUMBER = re.compile(r"^m(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)-")


def thread_allowances(value: Any) -> dict[frozenset, float]:
    """How much each bolt may share with each printed part: its thread (ADR-492).

    A bolt in a tapped hole overlaps the printed part by the thread it cuts:
    the ring between the hole and the bolt's nominal diameter, along its
    shank. That is engagement, not a collision, and it is bounded: the
    thread reaches no deeper than its minor diameter, so a bolt may share at
    most ``pi/4 (d^2 - minor^2) L`` with a printed part. A bolt driven
    through solid material, or into a pilot smaller than its minor
    diameter, shares more and still fails as an intersection. Keyed by the
    pair of component names; read from the published ``components``, so a
    revision that published none allows nothing.
    """

    if not isinstance(value, Mapping):
        return {}
    rows = [row for row in value.get("components") or []
            if isinstance(row, Mapping) and row.get("component")]

    def catalog(row: Mapping[str, Any]) -> Mapping[str, Any]:
        found = row.get("catalog") or row.get("catalog_derived_from") or {}
        return found if isinstance(found, Mapping) else {}

    printed = [str(r["component"]) for r in rows
               if not r.get("catalog") and not r.get("catalog_derived_from")
               or catalog(r).get("family") in PRINTED_FAMILIES]
    allowances: dict[frozenset, float] = {}
    for row in rows:
        if row.get("catalog_derived_from") or catalog(row).get("family") != "bolt":
            continue
        match = _BOLT_PART_NUMBER.match(str(catalog(row).get("part_number") or ""))
        minor = THREAD_MINOR_DIAMETER_MM.get(float(match.group(1))) if match else None
        if minor is None:
            continue
        nominal, length = float(match.group(1)), float(match.group(2))
        ring = math.pi / 4.0 * (nominal * nominal - minor * minor) * length
        for other in printed:
            allowances[frozenset((str(row["component"]), other))] = ring * (1.0 + 1e-3)
    return allowances


def _threaded(row: Mapping[str, Any], allowances: Mapping[frozenset, float],
              volume: Any) -> bool:
    """A bolt's overlap with a printed part that its own thread accounts for."""

    allowance = allowances.get(frozenset((str(row.get("first") or ""),
                                          str(row.get("second") or ""))))
    return allowance is not None and _finite(volume) and volume <= allowance


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
    # A bolt threaded into a printed part at the solved pose (ADR-492) may
    # share up to its thread with that part through the motion too; a bolt
    # that only meets a part as a joint moves holds no such allowance.
    allowances = {key: allowance for key, allowance in thread_allowances(value).items()
                  if key in static and _threaded(
                      static[key], {key: allowance},
                      static[key].get("common_volume_mm3"))
                  and static[key]["common_volume_mm3"] > maximum_volume}
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
            elif volume > maximum_volume and not _threaded(
                    {"first": first, "second": second}, allowances, volume):
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


#: Where the mounting block's facts come from, said in the block itself
#: (ADR-486).
MOUNTING_SOURCE = (
    "engine facts of the accepted revision (inspect scope=clearance): the "
    "pair distances at the solved pose, each catalog part's mounting-hole "
    "axes and each bolt's axis carried through its solved placement, and "
    "which printed parts were cut with a part's own .bay(). Not the "
    "script's stdout, and not a load or strength check."
)

#: Said whenever a purchased part is not held.
MOUNTING_NOTE = (
    "Every purchased part is held by a printed part: by screws (a lib.bolt "
    "component on one of its mounting-hole axes, touching it and a printed "
    "part), by a bay (a printed part cut with this part's own .bay() at its "
    "placement), by press fit (a bearing or bushing touching a printed "
    "part) or on a drive's output (a horn or wheel touching its servo or "
    "motor, which is held), and a tyre on the rim of a wheel that is held. "
    "A bolt counts only if it fits the hole: its "
    "thread where the hole is tapped (spec mount_thread), no larger than the "
    "hole where it is a clearance hole. It counts only if its shank threads "
    "into something: a printed part's tap-drill hole, the part's own tapped "
    "hole, a nut or a heat-set insert. A head resting on a printed part with "
    "the shank in an open cavity holds nothing. Contact alone, or sitting inside a printed "
    "part's envelope, holds nothing: place the screws as lib.bolt "
    "components through its spec mount holes, or cut its .bay() from the "
    "part that carries it."
)

#: Placed but never checked: what holds a part rather than what is held.
FASTENER_FAMILIES = frozenset({"bolt", "nut", "washer", "heat_insert"})
#: Catalogued shapes that are printed, not bought: they hold, like any
#: printed part.
PRINTED_FAMILIES = frozenset({"gear", "rack", "rack_and_pinion"})
#: Held by being pressed into a printed bore.
PRESS_FIT_FAMILIES = frozenset({"bearing", "bushing", "joint"})
#: Held on the output of a drive, which must itself be held.
OUTPUT_FAMILIES = frozenset({"servo_horn", "wheel"})
DRIVE_FAMILIES = frozenset({"servo", "gearmotor", "bldc", "qdd"})
#: Held on the rim of a wheel, which must itself be held (ADR-489).
RIM_FAMILIES = frozenset({"tyre"})
RIM_HOLDERS = frozenset({"wheel"})
#: A bay that is a swept well rather than a seat: it holds nothing.
WELL_FAMILIES = frozenset({"wheel"})

MOUNT_CONTACT_MM = 0.5
#: A bolt's shank must share at least this much volume with what it
#: threads into (ADR-492): a printed part's tap-drill hole, the held part's
#: own tapped hole, a nut or an insert. An M2 in its 1.6 mm tap drill cuts
#: about 1.1 mm^3 per mm of depth, so this is a tenth of a millimetre of
#: thread -- far above the kernel's noise, far below any real engagement.
THREAD_ENGAGEMENT_MM3 = 0.1
#: What a bolt may thread into besides a printed part or the held part.
THREADED_FAMILIES = frozenset({"nut", "heat_insert"})
MOUNT_AXIS_RADIUS_MM = 0.5
MOUNT_AXIS_ANGLE_DEGREES = 5.0


def _matrix(row: Mapping[str, Any]) -> list[float] | None:
    matrix = (row.get("placement") or {}).get("matrix")
    if isinstance(matrix, (list, tuple)) and len(matrix) >= 12 and all(
            _finite(v) for v in matrix[:12]):
        return [float(v) for v in matrix[:12]]
    return None


def _apply(matrix: Sequence[float], point: Sequence[float], *, vector: bool = False) -> list[float]:
    w = 0.0 if vector else 1.0
    return [matrix[4 * i] * point[0] + matrix[4 * i + 1] * point[1]
            + matrix[4 * i + 2] * point[2] + matrix[4 * i + 3] * w for i in range(3)]


#: The size facts a published axis may carry (ADR-488): a tapped hole's
#: thread, a clearance hole's diameter, a bolt's nominal diameter.
SIZE_FACTS = ("thread_dia_mm", "hole_dia_mm", "bolt_dia_mm")


def _world_axes(row: Mapping[str, Any], matrix: Sequence[float]) -> list[tuple]:
    axes = []
    for axis in row.get("mount_axes") or []:
        try:
            origin = [float(v) for v in axis["origin"]][:3]
            direction = _apply(matrix, [float(v) for v in axis["axis"]][:3], vector=True)
        except (KeyError, TypeError, ValueError):
            continue
        length = math.sqrt(sum(v * v for v in direction))
        sizes = {key: float(axis[key]) for key in SIZE_FACTS
                 if _finite(axis.get(key)) and axis[key] > 0}
        if len(origin) == 3 and length > 1e-12:
            axes.append((_apply(matrix, origin), [v / length for v in direction], sizes))
    return axes


def _misfit(hole: Mapping[str, float], bolt: Mapping[str, float]) -> str | None:
    """Why a bolt on a hole's axis cannot be in it, or None if it can.

    A tapped hole takes only its own thread; a clearance hole takes any
    bolt no larger than itself. A side with no size facts (a revision
    accepted before ADR-488) is judged by its axis alone.
    """

    size = bolt.get("bolt_dia_mm")
    if size is None:
        return None
    if "thread_dia_mm" in hole:
        if abs(size - hole["thread_dia_mm"]) > 1e-6:
            return f"an M{size:g} bolt in an M{hole['thread_dia_mm']:g} tapped hole"
    elif "hole_dia_mm" in hole and size > hole["hole_dia_mm"] + 1e-6:
        return f"an M{size:g} bolt through a {hole['hole_dia_mm']:g} mm hole"
    return None


def _on_axis(hole: tuple, bolt: tuple) -> bool:
    """A bolt's axis line runs through a mounting hole, both ways round."""

    (p, a), (o, d) = hole[:2], bolt[:2]
    cross = [a[1] * d[2] - a[2] * d[1], a[2] * d[0] - a[0] * d[2], a[0] * d[1] - a[1] * d[0]]
    if math.sqrt(sum(v * v for v in cross)) > math.sin(math.radians(MOUNT_AXIS_ANGLE_DEGREES)):
        return False
    offset = [p[i] - o[i] for i in range(3)]
    along = sum(offset[i] * d[i] for i in range(3))
    radial = math.sqrt(max(sum(v * v for v in offset) - along * along, 0.0))
    return radial <= MOUNT_AXIS_RADIUS_MM


def _same_pose(first: Sequence[float], second: Sequence[float]) -> bool:
    return all(abs(first[i] - second[i]) <= (1e-3 if i % 4 == 3 else 1e-6) for i in range(12))


def _world_box(row: Mapping[str, Any], matrix: Sequence[float]) -> tuple | None:
    bounds = (row.get("source_facts") or {}).get("bounds_mm")
    if not isinstance(bounds, Mapping):
        return None
    try:
        low, high = [float(v) for v in bounds["min"]], [float(v) for v in bounds["max"]]
    except (KeyError, TypeError, ValueError):
        return None
    corners = [_apply(matrix, [(low, high)[(k >> i) & 1][i] for i in range(3)]) for k in range(8)]
    return ([min(c[i] for c in corners) for i in range(3)],
            [max(c[i] for c in corners) for i in range(3)])


def mounting_summary(value: Any) -> dict[str, Any]:
    """What holds each purchased part of an accepted design (ADR-486).

    ``value`` is the same ``inspect scope=clearance`` value :func:`fit_summary`
    reads. Every placed catalog part that is bought (not a fastener, not a
    printed generator's gear or rack) gets one row naming the printed parts
    that hold it and by what: ``screws``, ``bay``, ``press fit``,
    ``output`` or ``rim`` (a tyre on its wheel). A part held by none of those is reported as ``contact
    only``, ``inside shell`` (no contact, but within a printed part's
    envelope) or ``held by nothing``; ``unknown`` when it has no solved
    placement or no measurement. ``verdict`` is ``pass`` when every
    purchased part is held, ``reported`` when one is not, ``none`` when the
    design places no purchased part, and ``unavailable`` when the revision
    published no components. Like the attachment block it refuses nothing
    and is counted among no fit failure.
    """

    if not isinstance(value, Mapping):
        value = {}
    published = value.get("components")
    if not isinstance(published, list):
        return {
            "verdict": "unavailable", "source": MOUNTING_SOURCE,
            "purchased_count": 0, "held_count": 0, "reported_count": 0,
            "reported": [], "held": [],
            "reason": (
                "No published components for the mounting check: the revision "
                "was accepted by an engine that published none, or places no "
                "assembly. Rebuild to acquire them."
            ),
        }
    rows = [row for row in published if isinstance(row, Mapping) and row.get("component")]
    # Every catalog row an ADR-486 engine published carries mount_axes, an
    # empty list where the part has no holes: without it there are no facts
    # to judge, and judging anyway would call every screwed part loose.
    if any(row.get("catalog") and "mount_axes" not in row for row in rows):
        return {
            "verdict": "unavailable", "source": MOUNTING_SOURCE,
            "purchased_count": 0, "held_count": 0, "reported_count": 0,
            "reported": [], "held": [],
            "reason": (
                "The accepted revision was built by an engine that published "
                "no mounting facts. Accept a new revision to acquire them."
            ),
        }

    def family(row: Mapping[str, Any]) -> str:
        catalog = row.get("catalog") or row.get("catalog_derived_from") or {}
        return str(catalog.get("family") or "") if isinstance(catalog, Mapping) else ""

    printed = {str(r["component"]) for r in rows
               if not r.get("catalog") and not r.get("catalog_derived_from")
               or family(r) in PRINTED_FAMILIES}
    bolts = {str(r["component"]): r for r in rows if family(r) == "bolt"}
    purchased = [r for r in rows if str(r["component"]) not in printed
                 and family(r) not in FASTENER_FAMILIES]
    by_name = {str(r["component"]): r for r in rows}
    touching: dict[str, set[str]] = {}
    # What each bolt's shank threads into: a positive common volume.
    bites: dict[str, set[str]] = {}
    unmeasured: set[str] = set()
    for pair in value.get("pairs") or []:
        if not isinstance(pair, Mapping):
            continue
        first, second = str(pair.get("first") or ""), str(pair.get("second") or "")
        distance, volume = pair.get("distance_mm"), pair.get("common_volume_mm3")
        if pair.get("error") or not _finite(distance) or not _finite(volume):
            unmeasured.update((first, second))
            continue
        if volume > MAXIMUM_COMMON_VOLUME_MM3 or (
                distance <= MOUNT_CONTACT_MM and not pair.get("culled")):
            touching.setdefault(first, set()).add(second)
            touching.setdefault(second, set()).add(first)
        if volume >= THREAD_ENGAGEMENT_MM3:
            for bolt_name, other in ((first, second), (second, first)):
                if bolt_name in bolts:
                    bites.setdefault(bolt_name, set()).add(other)

    def label(row: Mapping[str, Any]) -> str:
        catalog = row.get("catalog") or row.get("catalog_derived_from") or {}
        return "{}/{}".format(catalog.get("family") or "", catalog.get("part_number") or "")

    results: dict[str, dict[str, Any]] = {}
    for row in purchased:
        name = str(row["component"])
        kind = family(row)
        item: dict[str, Any] = {"component": name, "part": label(row)}
        if row.get("catalog_derived_from"):
            item["modified"] = True
        matrix = _matrix(row)
        contacts = touching.get(name, set())
        held_by_printed = sorted(contacts & printed)
        if matrix is None:
            item.update(status="unknown", by=None, holders=[],
                        detail="No solved placement was published for this component.")
            results[name] = item
            continue
        # Screws: a bolt on one of its hole axes, touching it and a printed
        # part, whose shank threads into something (ADR-492): a printed part
        # holds by its own thread (a common volume with the shank), or is
        # clamped under the head when the thread is this part's own tapped
        # hole, a nut or an insert.
        holes = _world_axes(row, matrix)
        screwed: dict[str, list[str]] = {}
        misfits: list[str] = []
        unthreaded: list[str] = []
        holes_used = 0
        for hole in holes:
            used = False
            for bolt_name in sorted(contacts & set(bolts)):
                bolt = bolts[bolt_name]
                bolt_matrix = _matrix(bolt)
                if bolt_matrix is None:
                    continue
                into = sorted(touching.get(bolt_name, set()) & printed)
                on = [axis for axis in _world_axes(bolt, bolt_matrix) if _on_axis(hole, axis)]
                if not into or not on:
                    continue
                bitten = bites.get(bolt_name, set())
                threaded = sorted(bitten & printed)
                # The catalog models a part's tapped hole as an open bore, so
                # a bolt that reaches one (it touches the part, on the axis)
                # is in its thread with no common volume to show for it.
                if not threaded and ("thread_dia_mm" in hole[2] or name in bitten or any(
                        family(by_name[b]) in THREADED_FAMILIES
                        for b in bitten if b in by_name)):
                    threaded = into
                reason = _misfit(hole[2], on[0][2])
                if reason:
                    misfits.append(f"{bolt_name}: {reason}")
                elif not threaded:
                    if bolt_name not in unthreaded:
                        unthreaded.append(bolt_name)
                else:
                    into = threaded
                    used = True
                    for holder in into:
                        screwed.setdefault(holder, [])
                        if bolt_name not in screwed[holder]:
                            screwed[holder].append(bolt_name)
            holes_used += used
        source = str(row.get("source_output") or "")
        bays = sorted(
            str(other["component"]) for other in rows
            if str(other["component"]) in printed and source
            and source in (other.get("houses") or [])
            and _matrix(other) is not None and _same_pose(_matrix(other), matrix)
        ) if kind not in WELL_FAMILIES else []
        if misfits:
            item["misfits"] = misfits
        if unthreaded:
            item["unthreaded"] = unthreaded
        if screwed:
            bolts_used = sorted({b for names in screwed.values() for b in names})
            item.update(status="held", by="screws", holders=sorted(screwed), detail=(
                f"{holes_used} of {len(holes)} mounting holes carry a bolt "
                f"({', '.join(bolts_used)}) into a printed part."))
        elif bays:
            item.update(status="held", by="bay", holders=bays, detail=(
                "Seated in its own .bay(), cut from the holder at this part's placement."))
        elif kind in PRESS_FIT_FAMILIES and held_by_printed:
            item.update(status="held", by="press fit", holders=held_by_printed,
                        detail="Pressed into a printed part it touches.")
        elif kind in OUTPUT_FAMILIES and any(family(by_name[c]) in DRIVE_FAMILIES
                                             for c in contacts if c in by_name):
            drives = sorted(c for c in contacts if c in by_name
                            and family(by_name[c]) in DRIVE_FAMILIES)
            item.update(status="held", by="output", holders=drives,
                        detail="On the output of " + ", ".join(drives) + ".")
        elif kind in RIM_FAMILIES and any(family(by_name[c]) in RIM_HOLDERS
                                          for c in contacts if c in by_name):
            wheels = sorted(c for c in contacts if c in by_name
                            and family(by_name[c]) in RIM_HOLDERS)
            item.update(status="held", by="rim", holders=wheels,
                        detail="On the rim of " + ", ".join(wheels) + ".")
        elif held_by_printed:
            item.update(status="contact only", by=None, holders=held_by_printed, detail=(
                "Touches a printed part, but no bolt runs through its mounting "
                "holes and no printed part was cut with its .bay() at its placement."
                if holes else
                "Touches a printed part, but no printed part was cut with its "
                ".bay() at its placement, and nothing else fastens it there."))
        elif name in unmeasured and not contacts:
            item.update(status="unknown", by=None, holders=[],
                        detail="A pair with this component was not measured.")
        else:
            inside: list[str] = []
            box = _world_box(row, matrix)
            if box is not None:
                centre = [(box[0][i] + box[1][i]) / 2.0 for i in range(3)]
                for other in rows:
                    other_name = str(other["component"])
                    other_matrix = _matrix(other)
                    if other_name not in printed or other_matrix is None:
                        continue
                    shell = _world_box(other, other_matrix)
                    if shell and all(shell[0][i] <= centre[i] <= shell[1][i] for i in range(3)):
                        inside.append(other_name)
            if inside:
                item.update(status="inside shell", by=None, holders=sorted(inside), detail=(
                    "Touches no printed part; it only sits within the envelope "
                    "of " + ", ".join(sorted(inside)) + "."))
            else:
                item.update(status="held by nothing", by=None, holders=[],
                            detail="Touches no printed part, and no printed part encloses it.")
        if misfits and item["status"] != "held":
            item["detail"] += (" Bolts on its hole axes that do not fit, so hold "
                               "nothing: " + "; ".join(misfits) + ".")
        if unthreaded:
            item["detail"] += (" Bolts on its hole axes whose shank threads into "
                               "nothing (no printed thread, tapped hole, nut or "
                               "insert), so hold nothing: " + ", ".join(unthreaded) + ".")
        results[name] = item
    # A horn or wheel is held only if the drive it rides on is, and a tyre
    # only if its wheel is: wheels first, so a loose motor frees its tyre.
    for riding, where in (("output", "On the output of "), ("rim", "On the rim of ")):
        for item in results.values():
            if item.get("by") == riding:
                loose = [d for d in item["holders"]
                         if (results.get(d) or {}).get("status") != "held"]
                if loose:
                    item.update(status="held by nothing", by=None, detail=(
                        where + ", ".join(loose) + ", which is not itself held."))
    ordered = [results[str(r["component"])] for r in purchased]
    reported = [i for i in ordered if i["status"] not in {"held", "unknown"}]
    unknown = [i for i in ordered if i["status"] == "unknown"]
    held = [i for i in ordered if i["status"] == "held"]
    if reported:
        verdict = "reported"
    elif unknown:
        verdict = "unknown"
    elif held:
        verdict = "pass"
    else:
        verdict = "none"
    summary: dict[str, Any] = {
        "verdict": verdict,
        "source": MOUNTING_SOURCE,
        "thresholds": {
            "contact_mm": MOUNT_CONTACT_MM,
            "thread_engagement_mm3": THREAD_ENGAGEMENT_MM3,
            "axis_radius_mm": MOUNT_AXIS_RADIUS_MM,
            "axis_angle_degrees": MOUNT_AXIS_ANGLE_DEGREES,
        },
        "purchased_count": len(ordered),
        "held_count": len(held),
        "reported_count": len(reported) + len(unknown),
        "reported": reported + unknown,
        "held": held,
    }
    if reported or unknown:
        summary["note"] = MOUNTING_NOTE
    if verdict == "none":
        summary["reason"] = "The accepted assembly places no purchased part."
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
    allowances = thread_allowances(value)
    threaded = 0
    for row in pairs:
        status = pair_status(row, minimum, maximum_volume)
        if status == "intersection" and _threaded(row, allowances, row.get("common_volume_mm3")):
            # A bolt's thread in a printed part (ADR-492): engagement, and
            # no deeper than the thread reaches.
            threaded += 1
            status = "clear"
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
        # Bolt-in-printed-part overlaps within the thread's depth (ADR-492),
        # counted among `clear`.
        "threaded_count": threaded,
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
        # ...and what holds each purchased part (ADR-486): its own verdict,
        # counted among no fit failure, like the attachment block.
        "mounting": mounting_summary(value),
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
        # Which component placed which catalog row: what the studio draws a
        # fastener as metal and a board as a PCB by (ADR-603).
        "catalog_by_component": {
            str(row.get("component") or ""): {
                "family": str(row["catalog"].get("family") or ""),
                "part_number": str(row["catalog"].get("part_number") or ""),
            }
            for row in components if isinstance(row.get("catalog"), Mapping)
        },
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
    mounting = fit.get("mounting")
    if isinstance(mounting, dict) and "reported" in mounting:
        block = dict(mounting)
        _cut(block, "reported", list(mounting.get("reported") or []),
             "inspect scope=clearance path=/components")
        _cut(block, "held", list(mounting.get("held") or []),
             "inspect scope=clearance path=/components")
        view["mounting"] = block
    return view


def inventory_view(inventory: dict[str, Any]) -> dict[str, Any]:
    """The inventory block as the model sees it: bounded (ADR-435).

    ``appearance`` becomes a count per role and ``printed_edges`` keeps the
    parts with the most sharp convex edge -- the ones worth a fillet -- and
    its totals; every row is ``inspect scope=inventory``.
    """

    view = dict(inventory)
    # Per component, and the catalog_counts roll-up already says it: the
    # renderer reads the full block, the model is spared the list (ADR-603).
    view.pop("catalog_by_component", None)
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
