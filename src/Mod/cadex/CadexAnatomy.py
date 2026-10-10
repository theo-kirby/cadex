# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The moving-regions block every build reply carries (ADR-613, ADR-614).

It keeps its first name, ``anatomy``, in the API, the reply and ``inspect``;
what it checks is any machine's moving regions (ADR-655) -- a steering
axle, a hitch, a lift arm, or a creature's neck and tail. The region names
come from the script, never from here. A region
is declared with ``assembly.anatomy(region, components, reason=)``
and passed to ``assembly.assembly(..., anatomy=[...])``. The assembly
worker stamps the graph facts beside the definition (``anatomy`` on the
assembly's row: the declared regions, every unsuppressed joint with its
kind, its two components and how many actuators drive it, the root
component and the world geometry), and this module turns them into the
block: per region, the joints that move it and whether one is driven; per
weld cluster, any large piece that sticks out of it while welded on, which
is what a rigid tail or a fused head looks like in the graph.

Pure standard library and graph-only: the bounding boxes are the ones the
inventory join already carries (``source_facts.bounds_mm`` through the
solved placement), so the block costs no geometry call. ``CadexInspection``
serves it as ``inspect scope=anatomy``; the CLI puts the bounded view on
every build reply and on ``look``'s measures.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


#: Coordinates each mobile joint kind has. Every other non-fixed kind
#: (distance, parallel, gears, belt, ...) is a constraint or a coupling
#: between coordinates, not a body-to-body hinge, and is left out of the
#: graph.
JOINT_DOF = {"revolute": 1, "slider": 1, "cylindrical": 2, "ball": 3}

#: A welded branch is reported when its box is at least this share of the
#: whole design's largest extent...
APPENDAGE_MIN_SHARE = 0.15
#: ...and it reaches at least this share of that extent past the box of
#: the rest of its rigid body.
APPENDAGE_PROTRUSION_SHARE = 0.08
#: ...and holds at most this share of its rigid body's solid volume.
APPENDAGE_MAX_VOLUME_SHARE = 0.5

ANATOMY_SOURCE = (
    "the accepted revision's joint graph (inspect scope=anatomy): the regions "
    "assembly.anatomy declared, every unsuppressed joint, which ones an "
    "api.actuator drives in any export or a catalog actuator drives on its "
    "axis, the weld clusters fixed joints make, "
    "and the bounding boxes the inventory already carries. Not a motion or "
    "strength check."
)

ANATOMY_NOTE = (
    "A region is articulated when a joint moves it relative to the region it "
    "hangs off (or between its own segments) and something drives that "
    "joint: an api.actuator declared on it (actuated), a catalog actuator "
    "welded to one side with its output on the joint axis (catalog drive), "
    "or either through a closed loop (loop). A region with no joint of its "
    "own is rigid; declare reason= when that is deliberate, with the "
    "measurement that says so. The verdict is complete only when every "
    "declared region is articulated, the root, or carries a reason."
)

UNDECLARED_NOTE = (
    "The script declares no moving regions. Where what the machine is "
    "depends on what moves -- a steering axle, a hitch, a lift arm, a "
    "gripper, a creature's neck or tail -- declare each region with "
    "assembly.anatomy(region, components, reason=None) and pass the list "
    "to assembly.assembly(..., anatomy=[...])."
)

NO_PUBLISHED = (
    "The accepted revision published no anatomy graph (accepted before "
    "ADR-614, or no assembly); rebuild to measure it."
)


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def world_boxes(components: Sequence[Mapping[str, Any]]) -> dict[str, tuple]:
    """Each inventory row's axis-aligned world box, from its source box and solved placement."""

    boxes: dict[str, tuple] = {}
    for row in components:
        if not isinstance(row, Mapping):
            continue
        name = str(row.get("component") or "")
        bounds = (row.get("source_facts") or {}).get("bounds_mm")
        matrix = (row.get("placement") or {}).get("matrix")
        if not name or not isinstance(bounds, Mapping):
            continue
        try:
            low = [float(v) for v in bounds["min"]][:3]
            high = [float(v) for v in bounds["max"]][:3]
        except (KeyError, TypeError, ValueError):
            continue
        if not (isinstance(matrix, (list, tuple)) and len(matrix) >= 12
                and all(_finite(v) for v in matrix[:12])):
            matrix = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        m = [float(v) for v in matrix[:12]]
        corners = []
        for k in range(8):
            p = [(low, high)[(k >> i) & 1][i] for i in range(3)]
            corners.append([m[4 * i] * p[0] + m[4 * i + 1] * p[1] + m[4 * i + 2] * p[2] + m[4 * i + 3]
                            for i in range(3)])
        boxes[name] = ([min(c[i] for c in corners) for i in range(3)],
                       [max(c[i] for c in corners) for i in range(3)])
    return boxes


#: The drives that make a region articulated: an api.actuator declared on
#: the joint, a catalog actuator on its axis, or a closed loop either drives.
DRIVEN = ("actuated", "catalog drive", "loop")
#: How far a catalog actuator's output axis may sit off a joint's axis and
#: still be read as driving it: a degree-scale aim and a millimetre-scale
#: offset, far tighter than any motor placed for another joint.
DRIVE_AXIS_ANGLE_DEGREES = 3.0
DRIVE_AXIS_OFFSET_MM = 1.5
#: Which joint kinds each output motion can drive.
DRIVE_KINDS = {"rotary": ("revolute", "cylindrical"), "linear": ("slider", "cylindrical")}


def world_drive_axes(components: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Each catalog actuator's output axis in world coordinates at the solved pose.

    ``drive_axis`` on an inventory row is in the source output's own
    coordinates (stamped beside the definition, ADR-614); the solved
    placement carries it into the world, like a mount axis.
    """

    found: dict[str, dict[str, Any]] = {}
    for row in components:
        if not isinstance(row, Mapping) or not isinstance(row.get("drive_axis"), Mapping):
            continue
        matrix = (row.get("placement") or {}).get("matrix")
        if not (isinstance(matrix, (list, tuple)) and len(matrix) >= 12
                and all(_finite(v) for v in matrix[:12])):
            matrix = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        m = [float(v) for v in matrix[:12]]
        try:
            origin = [float(v) for v in row["drive_axis"]["origin"]][:3]
            axis = [float(v) for v in row["drive_axis"]["axis"]][:3]
        except (KeyError, TypeError, ValueError):
            continue
        world_origin = [m[4 * i] * origin[0] + m[4 * i + 1] * origin[1] + m[4 * i + 2] * origin[2]
                        + m[4 * i + 3] for i in range(3)]
        world_axis = [m[4 * i] * axis[0] + m[4 * i + 1] * axis[1] + m[4 * i + 2] * axis[2]
                      for i in range(3)]
        found[str(row.get("component") or "")] = {
            "origin": world_origin, "axis": world_axis,
            "motion": str(row["drive_axis"].get("motion") or "rotary")}
    return found


def _coaxial(drive: Mapping[str, Any], line: Mapping[str, Any]) -> bool:
    try:
        a = [float(v) for v in drive["axis"]][:3]
        b = [float(v) for v in line["axis"]][:3]
        p = [float(v) for v in drive["origin"]][:3]
        o = [float(v) for v in line["origin"]][:3]
    except (KeyError, TypeError, ValueError):
        return False
    na, nb = math.sqrt(sum(v * v for v in a)), math.sqrt(sum(v * v for v in b))
    if na <= 1e-12 or nb <= 1e-12:
        return False
    a, b = [v / na for v in a], [v / nb for v in b]
    if abs(sum(x * y for x, y in zip(a, b))) < math.cos(math.radians(DRIVE_AXIS_ANGLE_DEGREES)):
        return False
    offset = [p[i] - o[i] for i in range(3)]
    along = sum(offset[i] * b[i] for i in range(3))
    radial = math.sqrt(max(sum(v * v for v in offset) - along * along, 0.0))
    return radial <= DRIVE_AXIS_OFFSET_MM


def _catalog_driver(joint: Mapping[str, Any], drives: Mapping[str, Mapping[str, Any]],
                    members: Mapping[str, Sequence[str]], clusters: Any) -> str:
    """The catalog actuator welded to one side of ``joint`` on its axis, or ``""``."""

    line = joint.get("axis")
    if not isinstance(line, Mapping) or not drives:
        return ""
    for side in joint["components"]:
        for name in members.get(clusters.find(str(side)), ()):
            drive = drives.get(name)
            if (drive and joint.get("kind") in DRIVE_KINDS.get(drive["motion"], ())
                    and _coaxial(drive, line)):
                return name
    return ""


def _union(boxes: Sequence[tuple]) -> tuple | None:
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    return ([min(b[0][i] for b in boxes) for i in range(3)],
            [max(b[1][i] for b in boxes) for i in range(3)])


def _extent(box: tuple | None) -> list[float] | None:
    return None if box is None else [round(box[1][i] - box[0][i], 3) for i in range(3)]


class _Clusters:
    """Union-find over components joined by fixed joints."""

    def __init__(self, names: Sequence[str]) -> None:
        self.parent = {name: name for name in names}

    def find(self, name: str) -> str:
        root = name
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[name] != root:
            self.parent[name], name = root, self.parent[name]
        return root

    def join(self, first: str, second: str) -> None:
        a, b = self.find(first), self.find(second)
        if a != b:
            self.parent[b] = a


def _bridges(nodes: Sequence[str], edges: Sequence[tuple[str, str, int]]) -> set[int]:
    """Edge ids that are bridges of an undirected multigraph (iterative Tarjan)."""

    adjacency: dict[str, list[tuple[str, int]]] = {node: [] for node in nodes}
    for first, second, edge in edges:
        adjacency[first].append((second, edge))
        adjacency[second].append((first, edge))
    order: dict[str, int] = {}
    low: dict[str, int] = {}
    bridges: set[int] = set()
    counter = 0
    for start in nodes:
        if start in order:
            continue
        order[start] = low[start] = counter
        counter += 1
        stack = [(start, -1, iter(adjacency[start]))]
        while stack:
            node, via, neighbours = stack[-1]
            advanced = False
            for other, edge in neighbours:
                if edge == via:
                    continue
                if other in order:
                    low[node] = min(low[node], order[other])
                    continue
                order[other] = low[other] = counter
                counter += 1
                stack.append((other, edge, iter(adjacency[other])))
                advanced = True
                break
            if advanced:
                continue
            stack.pop()
            if stack:
                parent = stack[-1][0]
                low[parent] = min(low[parent], low[node])
                if low[node] > order[parent]:
                    bridges.add(via)
    return bridges


def _protrusion(branch: tuple, core: tuple) -> tuple[float, str]:
    """How far, and toward which world direction, ``branch`` reaches past ``core``."""

    best, where = 0.0, ""
    for i, axis in enumerate("xyz"):
        for reach, sign in ((branch[1][i] - core[1][i], "+"), (core[0][i] - branch[0][i], "-")):
            if reach > best:
                best, where = reach, sign + axis
    return best, where


def _centroid(cluster: list[str], welds: list[tuple[str, str, str]]) -> str:
    """The part of a weld graph whose removal leaves the smallest largest piece."""

    adjacency: dict[str, set[str]] = {name: set() for name in cluster}
    for a, b, _joint in welds:
        adjacency[a].add(b)
        adjacency[b].add(a)

    def worst(removed: str) -> int:
        seen, largest = {removed}, 0
        for start in cluster:
            if start in seen:
                continue
            seen.add(start)
            stack, size = [start], 0
            while stack:
                node = stack.pop()
                size += 1
                for other in adjacency[node] - seen:
                    seen.add(other)
                    stack.append(other)
            largest = max(largest, size)
        return largest

    return min(cluster, key=lambda name: (worst(name), cluster.index(name)))


def _appendages(cluster: list[str], anchors: Sequence[str], welds: list[tuple[str, str, str]],
                boxes: Mapping[str, tuple], scale: float,
                volumes: Mapping[str, float] | None = None) -> list[dict[str, Any]]:
    """The welded branches of one rigid body that are large and stick out of the rest of it.

    A branch is what falls away when one fixed joint (a bridge of the weld
    graph) is cut, on the side away from ``anchors`` (the body it hangs
    off: the joint-side part of a moving body, the declared root region of
    the torso). Branches are taken top
    down: a reported one is not searched again, so a welded tail of five
    segments is one finding rather than five.
    """

    if len(cluster) < 2 or scale <= 0:
        return []
    ids = {index: weld for index, weld in enumerate(welds)}
    bridges = _bridges(cluster, [(a, b, index) for index, (a, b, _j) in ids.items()])
    adjacency: dict[str, list[tuple[str, int]]] = {name: [] for name in cluster}
    for index, (a, b, _joint) in ids.items():
        adjacency[a].append((b, index))
        adjacency[b].append((a, index))
    # The tree the anchor sees, cut only at bridges: each bridge's far side
    # is one branch; everything else stays with the side it is welded to.
    anchors = [name for name in dict.fromkeys(anchors) if name in adjacency] or cluster[:1]
    parent: dict[str, tuple[str, int] | None] = {name: None for name in anchors}
    order = list(anchors)
    for node in order:
        for other, index in adjacency[node]:
            if other not in parent:
                parent[other] = (node, index)
                order.append(other)
    children: dict[str, list[str]] = {name: [] for name in order}
    for node in order:
        if parent[node] is not None:
            children[parent[node][0]].append(node)

    def subtree(node: str) -> list[str]:
        found, pending = [], [node]
        while pending:
            item = pending.pop()
            found.append(item)
            pending.extend(children[item])
        return found

    whole = set(order)
    found: list[dict[str, Any]] = []
    pending = [child for name in anchors for child in children[name]]
    while pending:
        node = pending.pop(0)
        via = parent[node][1]
        if via in bridges:
            branch = subtree(node)
            branch_box = _union([boxes.get(name) for name in branch])
            core_box = _union([boxes.get(name) for name in whole - set(branch)])
            if branch_box is not None and core_box is not None:
                size = max(branch_box[1][i] - branch_box[0][i] for i in range(3))
                reach, direction = _protrusion(branch_box, core_box)
                # An appendage is the minority of its body: the half of a
                # torso a weld splits off is still the torso.
                minority = True
                if volumes and all(name in volumes for name in whole):
                    minority = sum(volumes[n] for n in branch) <= APPENDAGE_MAX_VOLUME_SHARE * sum(
                        volumes[n] for n in whole)
                if (minority and size >= APPENDAGE_MIN_SHARE * scale
                        and reach >= APPENDAGE_PROTRUSION_SHARE * scale):
                    found.append({
                        "components": sorted(branch),
                        "welded_to": parent[node][0],
                        "joint": ids[via][2],
                        "extent_mm": _extent(branch_box),
                        "protrudes_mm": round(reach, 3),
                        "toward": direction,
                    })
                    continue
        pending.extend(children[node])
    return found


def anatomy_summary(stamp: Any, components: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """The anatomy block from the worker's stamp and the inventory's component rows."""

    if not isinstance(stamp, Mapping):
        return {"verdict": "unavailable", "source": ANATOMY_SOURCE, "regions": [],
                "rigid_appendages": [], "actuated_dof": 0, "reason": NO_PUBLISHED}
    world = {str(name) for name in stamp.get("world_components") or []}
    names = [str(name) for name in stamp.get("components") or [] if str(name) not in world]
    if not names:
        names = sorted({str(c) for j in stamp.get("joints") or [] for c in j.get("components") or []} - world)
    known = set(names)
    joints = [dict(j) for j in stamp.get("joints") or []
              if isinstance(j, Mapping) and len(j.get("components") or []) == 2
              and set(map(str, j["components"])) <= known]
    regions = [dict(r) for r in stamp.get("regions") or [] if isinstance(r, Mapping)]
    root = str(stamp.get("root_component") or (names[0] if names else ""))

    clusters = _Clusters(names)
    for joint in joints:
        if joint.get("kind") == "fixed":
            clusters.join(*map(str, joint["components"]))
    members: dict[str, list[str]] = {}
    for name in names:
        members.setdefault(clusters.find(name), []).append(name)
    root_cluster = clusters.find(root) if root in known else (next(iter(members), ""))

    # The kinematic graph: clusters joined by mobile joints, oriented away
    # from the root by breadth-first depth.
    mobile = [j for j in joints if j.get("kind") in JOINT_DOF]
    edges = []
    for index, joint in enumerate(mobile):
        first, second = (clusters.find(str(c)) for c in joint["components"])
        if first != second:
            edges.append((first, second, index))
    adjacency: dict[str, list[tuple[str, int]]] = {key: [] for key in members}
    for first, second, index in edges:
        adjacency[first].append((second, index))
        adjacency[second].append((first, index))
    depth = {root_cluster: 0} if root_cluster else {}
    entry: dict[str, int] = {}
    queue = [root_cluster] if root_cluster else []
    for node in queue:
        for other, index in adjacency[node]:
            if other not in depth:
                depth[other] = depth[node] + 1
                entry[other] = index
                queue.append(other)
    far = len(members) + 1

    # A joint no api.actuator names is still driven when a catalog actuator
    # sits on its axis, welded into the body on one side of it: the motor a
    # design-only project placed but never declared. Declared wins.
    drives = world_drive_axes(components)
    catalog_driver: dict[int, str] = {}
    for _a, _b, index in edges:
        joint = mobile[index]
        if int(joint.get("actuators") or 0) > 0:
            continue
        found = _catalog_driver(joint, drives, members, clusters)
        if found:
            catalog_driver[index] = found

    def driven(index: int) -> bool:
        return int(mobile[index].get("actuators") or 0) > 0 or index in catalog_driver

    # Which mobile joints close a loop, and which loops an actuator drives.
    bridges = _bridges(list(members), edges)
    loop_parts = _Clusters(list(members))
    for first, second, index in edges:
        if index not in bridges:
            loop_parts.join(first, second)
    driven_loops = {loop_parts.find(clusters.find(str(mobile[i]["components"][0])))
                    for _a, _b, i in edges if i not in bridges and driven(i)}

    def drive(index: int) -> str:
        joint = mobile[index]
        if int(joint.get("actuators") or 0) > 0:
            return "actuated"
        if index in catalog_driver:
            return "catalog drive"
        if index in bridges:
            return "passive"
        side = loop_parts.find(clusters.find(str(joint["components"][0])))
        return "loop" if side in driven_loops else "passive"

    def driven_dof(index: int) -> int:
        dof = JOINT_DOF[str(mobile[index]["kind"])]
        return min(int(mobile[index].get("actuators") or 0) or (1 if index in catalog_driver else 0), dof)

    # Region ownership of clusters: the root region owns the root cluster;
    # elsewhere the region reaching nearest the root owns a shared cluster,
    # ties to the one declared first. The others in it are welded to it.
    region_names = [str(r.get("region") or "") for r in regions]
    in_cluster: dict[str, list[str]] = {}
    for region in regions:
        for name in region.get("components") or []:
            name = str(name)
            if name in known:
                key = clusters.find(name)
                bucket = in_cluster.setdefault(key, [])
                if region["region"] not in bucket:
                    bucket.append(region["region"])
    reach = {name: min((depth.get(c, far) for c, rs in in_cluster.items() if name in rs), default=far)
             for name in region_names}
    root_region = next((str(r["region"]) for r in regions
                        if root in [str(c) for c in r.get("components") or []]), None)
    owner: dict[str, str] = {}
    for key, present in in_cluster.items():
        if key == root_cluster and root_region in present:
            owner[key] = root_region
        else:
            owner[key] = min(present, key=lambda r: (reach[r], region_names.index(r)))

    assigned: dict[str, list[dict[str, Any]]] = {name: [] for name in region_names}
    parent_region: dict[str, str | None] = {}
    unassigned = 0
    for first, second, index in edges:
        a, b = first, second
        if depth.get(a, far) > depth.get(b, far):
            a, b = b, a
        child_owner = owner.get(b)
        if child_owner is None:
            unassigned += 1
            continue
        joint = mobile[index]
        row = {"joint": str(joint.get("joint") or ""), "kind": str(joint.get("kind")),
               "dof": JOINT_DOF[str(joint.get("kind"))], "drive": drive(index),
               "actuators": int(joint.get("actuators") or 0),
               "driven_dof": driven_dof(index)}
        if index in catalog_driver:
            row["driver"] = catalog_driver[index]
        if child_owner in in_cluster.get(a, []):
            row["within"] = True
        else:
            parent_region.setdefault(child_owner, owner.get(a))
        assigned[child_owner].append(row)

    rows = []
    complete = True
    for region in regions:
        name = str(region["region"])
        own = assigned[name]
        reason = region.get("reason")
        if any(j["drive"] in DRIVEN for j in own):
            status = "articulated"
        elif own:
            status = "passive only"
        elif name == root_region and owner.get(root_cluster) == name:
            status = "root"
        elif reason:
            status = "rigid"
        else:
            status = "rigid, no reason"
        if status in ("passive only", "rigid, no reason") and not reason:
            complete = False
        welded_to = sorted({owner[c] for c, present in in_cluster.items()
                            if name in present and owner[c] != name})
        row = {
            "region": name,
            "status": status,
            "components": [str(c) for c in region.get("components") or []],
            "joints": own,
            "joint_dof": sum(j["dof"] for j in own),
            "actuated_dof": sum(j["driven_dof"] for j in own),
        }
        if name in parent_region:
            row["parent_region"] = parent_region[name]
        if welded_to:
            row["welded_to"] = welded_to
        if reason:
            row["reason"] = str(reason)
        rows.append(row)

    # Welded branches that stick out, in every rigid body.
    boxes = world_boxes(components)
    volumes = {str(row.get("component")): float(row["source_facts"]["volume_mm3"])
               for row in components if isinstance(row, Mapping)
               and _finite((row.get("source_facts") or {}).get("volume_mm3"))}
    design = _union([boxes.get(name) for name in names])
    scale = max((design[1][i] - design[0][i]) for i in range(3)) if design else 0.0
    welds_by_cluster: dict[str, list[tuple[str, str, str]]] = {}
    for joint in joints:
        if joint.get("kind") == "fixed":
            a, b = map(str, joint["components"])
            welds_by_cluster.setdefault(clusters.find(a), []).append((a, b, str(joint.get("joint") or "")))
    region_of = {}
    for region in regions:
        for c in region.get("components") or []:
            region_of.setdefault(str(c), str(region["region"]))
    reasons = {str(r["region"]): r.get("reason") for r in regions}
    status_of = {row["region"]: row["status"] for row in rows}
    appendages = []
    for key, cluster in members.items():
        welds = welds_by_cluster.get(key, [])
        # What a branch hangs off: the region that owns this body, where one
        # is declared, and the part the joint into it attaches to -- or, for
        # an undeclared torso, its heaviest part (the middle of its weld
        # graph when no volume is known) rather than whichever plate the
        # script happened to place first. Only that guess is also held to
        # the minority rule: a declared or jointed anchor is a fact.
        anchors = [c for c in cluster if owner.get(key) and region_of.get(c) == owner[key]]
        guessed = False
        if key in entry:
            joint = mobile[entry[key]]
            anchors.append(next(str(c) for c in joint["components"] if clusters.find(str(c)) == key))
        elif not anchors and key == root_cluster:
            guessed = True
            anchors.append(max(cluster, key=lambda c: volumes.get(c, 0.0))
                           if any(c in volumes for c in cluster) else _centroid(cluster, welds))
        elif not anchors:
            anchors.append(cluster[0])
        for item in _appendages(cluster, anchors, welds, boxes, scale,
                                volumes if guessed else None):
            held = sorted({region_of[c] for c in item["components"] if c in region_of})
            if key == root_cluster and held and set(held) <= {root_region}:
                continue  # the torso's own body, not something hanging off it
            item["regions"] = held
            # Declared and accounted for: every region it holds is either
            # deliberately rigid (a reason) or moves (this is its mount).
            item["acknowledged"] = bool(held) and all(
                reasons.get(r) or status_of.get(r) in ("articulated", "root") for r in held)
            item["component_count"] = len(item["components"])
            appendages.append(item)
    appendages.sort(key=lambda item: -item["protrudes_mm"])

    if not regions:
        verdict = "undeclared"
    else:
        verdict = "complete" if complete else "incomplete"
    summary: dict[str, Any] = {
        "verdict": verdict,
        "source": ANATOMY_SOURCE,
        "regions": rows,
        "rigid_appendages": appendages,
        "unacknowledged_appendages": sum(1 for a in appendages if not a["acknowledged"]),
        "rigid_bodies": len(members),
        "mobile_joints": len(edges),
        "actuated_joints": sum(1 for _a, _b, i in edges if driven(i)),
        "catalog_driven_joints": len(catalog_driver),
        "joint_dof": sum(JOINT_DOF[str(mobile[i]["kind"])] for _a, _b, i in edges),
        "actuated_dof": sum(driven_dof(i) for _a, _b, i in edges),
        "root_component": root,
    }
    if regions:
        summary["undeclared_joints"] = unassigned
        summary["note"] = ANATOMY_NOTE
    else:
        summary["note"] = UNDECLARED_NOTE
    return summary


#: How many rows of each list the build reply's view carries.
VIEW_LIST_LIMIT = 12
VIEW_COMPONENT_LIMIT = 6
#: The block's scalar keys the view carries whole.
VIEW_KEYS = (
    "verdict", "revision", "assembly", "actuated_dof", "joint_dof", "mobile_joints",
    "actuated_joints", "catalog_driven_joints", "rigid_bodies", "root_component", "unacknowledged_appendages",
    "undeclared_joints", "note", "reason", "error",
)


def anatomy_view(block: Mapping[str, Any]) -> dict[str, Any]:
    """The anatomy block bounded the way a build reply shows it to the model.

    Regions keep their status, counts and joints by name; component lists
    are cut to their first few with a count. The whole block is one
    ``inspect scope=anatomy`` away.
    """

    view = {key: block[key] for key in VIEW_KEYS if key in block}

    def cut(names: Sequence[Any]) -> dict[str, Any] | list[Any]:
        names = list(names or [])
        if len(names) <= VIEW_COMPONENT_LIMIT:
            return names
        return {"first": names[:VIEW_COMPONENT_LIMIT], "count": len(names)}

    regions = []
    for row in list(block.get("regions") or [])[:VIEW_LIST_LIMIT * 2]:
        item = {key: value for key, value in row.items() if key not in ("components", "joints")}
        item["components"] = cut(row.get("components"))
        item["joints"] = ["{:s} ({:s}, {:s}{:s})".format(
            j["joint"], j["kind"], j["drive"], ": " + j["driver"] if j.get("driver") else "")
            for j in row.get("joints") or []]
        regions.append(item)
    view["regions"] = regions
    appendages = []
    for row in list(block.get("rigid_appendages") or [])[:VIEW_LIST_LIMIT]:
        item = dict(row)
        item["components"] = cut(row.get("components"))
        appendages.append(item)
    view["rigid_appendages"] = appendages
    hidden = len(block.get("rigid_appendages") or []) - len(appendages)
    if hidden > 0:
        view["rigid_appendages_omitted"] = hidden
    if block.get("verdict") not in ("unavailable",):
        view["full"] = "inspect scope=anatomy"
    return view


def anatomy_measure(block: Mapping[str, Any] | None) -> dict[str, Any]:
    """The one-line measure ``look`` adds beside the design-language proxies."""

    if not isinstance(block, Mapping):
        return {"value": "unavailable", "bar": "every declared region articulated or rigid with a reason",
                "meets": None}
    open_regions = [r["region"] for r in block.get("regions") or []
                    if r.get("status") in ("passive only", "rigid, no reason") and not r.get("reason")]
    return {
        "value": str(block.get("verdict") or "unavailable"),
        "bar": "every declared region articulated or rigid with a reason",
        "meets": None if block.get("verdict") in ("unavailable", "undeclared") else not open_regions,
        "open_regions": open_regions,
        "actuated_dof": int(block.get("actuated_dof") or 0),
        "unacknowledged_appendages": int(block.get("unacknowledged_appendages") or 0),
    }
