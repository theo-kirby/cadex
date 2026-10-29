# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The CAD's MJCF measured beside the concept's, each difference over 5% or 10 mm flagged.

The route trains a concept first and builds the CAD to its frozen numbers
(``cadex_concept.py``); this says how close the CAD came. Either side may be
the engine's export, a training model cut from it (``cadex_training_model.py``
keeps masses, inertias and joints) or a concept model, so it also compares a
concept with a cut, or a cut with its own export.

Nothing is named for one robot. Both models are compiled and read at their
build pose (``qpos0``: a Cadex export and a concept model put every joint's
zero at home):

- the **feet** are the ``touch`` sensors' sites (the export and the concept
  write one per foot, centred on the foot);
- a foot's **leg** is rooted at its body's highest jointed ancestor whose
  subtree holds that foot and no other, and named by that root body; the rest
  is the **trunk**. A joint-free body above the root (a drive housing bolted to
  the pelvis) moves with the trunk and counts there; a cut fuses such bodies,
  and a joint-free foot into its shin, but never the root, so the legs read
  the same on an export and its cut;
- the **joints** are the hinges and slides an actuator drives.

Rows match by name: legs by their root body, joints by joint name. A leg or joint in
only one model is listed as unmatched and not compared. Measured:

- **mass**: the total, the trunk's and each leg's subtree;
- **centre of mass**: the whole robot's;
- **legs**: hip height (the first pitch joint's anchor height; a pitch joint is
  a hinge whose world axis is mostly along y), reach (the summed segments from
  it, joint to joint and the last to the foot), bend (one less hip-to-foot over
  reach) and the foot's x from the hip: ``cadex_concept.py``'s own report,
  with the touch site as the foot point;
- **joints**: each driven joint's world anchor; its load, the inertia of the
  subtree it carries about its own axis through its anchor; its ``armature``.

A difference is flagged when it is over 5% of the concept's value, or for a
position over 10 mm. It prints one table and exits 0, or 2 when the two models
share no leg or no driven joint; it judges nothing else.

    python training/cadex_cad_vs_concept.py CONCEPT.xml CAD.xml [--json OUT]

Needs ``mujoco`` and ``numpy`` (the training venv); the standard library at
module scope (ADR-084).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

REL = 0.05
POS_M = 0.010


def _subtree(m, root: int) -> list[int]:
    out = []
    for b in range(m.nbody):
        c = b
        while c > 0 and c != root:
            c = int(m.body_parentid[c])
        if c == root:
            out.append(b)
    return out


def feet(m) -> list[int]:
    """The touch sensors' sites, in sensor order."""

    import mujoco as mj

    return [int(m.sensor_objid[s]) for s in range(m.nsensor)
            if int(m.sensor_type[s]) == mj.mjtSensor.mjSENS_TOUCH]


def leg_roots(m, sites: list[int]) -> dict[int, int]:
    """Each foot site's leg root: its body's highest jointed ancestor whose subtree holds no other
    foot (the foot's own body when none is jointed)."""

    bodies = {s: int(m.site_bodyid[s]) for s in sites}
    out = {}
    for s, f in bodies.items():
        others = {b for t, b in bodies.items() if t != s}
        root = b = f
        while b > 0 and not others & set(_subtree(m, b)):
            if int(m.body_jntnum[b]) > 0:
                root = b
            b = int(m.body_parentid[b])
        out[s] = root
    return out


def driven_joints(m) -> list[int]:
    """The hinge and slide joints an actuator drives, in actuator order."""

    import mujoco as mj

    out = []
    for a in range(m.nu):
        if int(m.actuator_trntype[a]) == mj.mjtTrn.mjTRN_JOINT:
            j = int(m.actuator_trnid[a][0])
            if int(m.jnt_type[j]) in (mj.mjtJoint.mjJNT_HINGE, mj.mjtJoint.mjJNT_SLIDE) and j not in out:
                out.append(j)
    return out


def axis_inertia(m, d, joint: int) -> float:
    """The subtree's inertia about the joint's world axis through its anchor (kg m^2)."""

    import numpy as np

    a = d.xaxis[joint] / np.linalg.norm(d.xaxis[joint])
    p = d.xanchor[joint]
    total = 0.0
    for b in _subtree(m, int(m.jnt_bodyid[joint])):
        R = d.ximat[b].reshape(3, 3)
        I_world = R @ np.diag(m.body_inertia[b]) @ R.T
        r = d.xipos[b] - p
        perp = r - np.dot(r, a) * a
        total += float(a @ I_world @ a) + float(m.body_mass[b]) * float(perp @ perp)
    return total


def leg(m, d, site: int, root: int) -> dict[str, Any]:
    """``cadex_concept.py``'s leg report, read from a compiled model, the chain stopping at
    the leg's root body so a trunk joint (a spine's pitch) is never in it."""

    import mujoco as mj
    import numpy as np

    chain = []
    b = int(m.site_bodyid[site])
    while b > 0:
        for j in range(m.njnt - 1, -1, -1):
            if int(m.jnt_bodyid[j]) == b and int(m.jnt_type[j]) == mj.mjtJoint.mjJNT_HINGE \
                    and abs(float(d.xaxis[j][1])) > 0.5:
                chain.append(j)
        if b == root:
            break
        b = int(m.body_parentid[b])
    chain.reverse()
    if not chain:
        return {"pitch_joints": []}
    at = [d.xanchor[j].copy() for j in chain] + [d.site_xpos[site].copy()]
    reach = sum(float(np.linalg.norm(at[k + 1] - at[k])) for k in range(len(at) - 1))
    hip_to_foot = float(np.linalg.norm(at[-1] - at[0]))
    return {"pitch_joints": [mj.mj_id2name(m, mj.mjtObj.mjOBJ_JOINT, j) for j in chain],
            "hip_height_m": float(at[0][2]), "reach_m": reach,
            "bend": 1.0 - hip_to_foot / reach if reach > 0 else 0.0,
            "foot_x_from_hip_m": float(at[-1][0] - at[0][0])}


def measure(path: Path) -> dict[str, Any]:
    import mujoco as mj

    text = Path(path).read_text()
    m = mj.MjModel.from_xml_path(str(path))
    d = mj.MjData(m)
    mj.mj_forward(m, d)
    name = lambda kind, i: mj.mj_id2name(m, kind, i)  # noqa: E731
    total = float(m.body_mass.sum())
    roots = leg_roots(m, feet(m))
    legs = {}
    for s, r in roots.items():
        legs[name(mj.mjtObj.mjOBJ_BODY, r)] = {
            "foot_site": name(mj.mjtObj.mjOBJ_SITE, s),
            "mass_kg": float(m.body_mass[_subtree(m, r)].sum()), **leg(m, d, s, r)}
    com = sum(float(m.body_mass[b]) * d.xipos[b] for b in range(m.nbody)) / total
    joints = {}
    for j in driven_joints(m):
        joints[name(mj.mjtObj.mjOBJ_JOINT, j)] = {
            "anchor_m": [float(v) for v in d.xanchor[j]], "load_inertia_kgm2": axis_inertia(m, d, j),
            "armature_kgm2": float(m.dof_armature[int(m.jnt_dofadr[j])])}
    return {"model": str(path), "model_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "mass_kg": total, "trunk_mass_kg": total - sum(v["mass_kg"] for v in legs.values()),
            "com_m": [float(v) for v in com], "legs": legs, "joints": joints}


def _row(what: str, concept: float, cad: float, unit: str, pos: bool = False) -> dict[str, Any]:
    diff = cad - concept
    rel = diff / concept if abs(concept) > 1e-12 else math.inf if abs(diff) > 0 else 0.0
    flag = abs(diff) > POS_M if pos else abs(rel) > REL
    return {"what": what, "concept": concept, "cad": cad, "diff": diff, "rel": rel, "unit": unit, "flag": flag}


def compare(concept: dict, cad: dict) -> list[dict[str, Any]]:
    rows = [_row("mass", concept["mass_kg"], cad["mass_kg"], "kg"),
            _row("trunk mass", concept["trunk_mass_kg"], cad["trunk_mass_kg"], "kg")]
    for i, axis in enumerate("xyz"):
        rows.append(_row(f"CoM {axis}", concept["com_m"][i], cad["com_m"][i], "m", pos=True))
    for k in concept["legs"]:
        if k not in cad["legs"]:
            continue
        a, b = concept["legs"][k], cad["legs"][k]
        rows.append(_row(f"leg {k} mass", a["mass_kg"], b["mass_kg"], "kg"))
        if "reach_m" in a and "reach_m" in b:
            rows += [_row(f"leg {k} hip height", a["hip_height_m"], b["hip_height_m"], "m", pos=True),
                     _row(f"leg {k} reach", a["reach_m"], b["reach_m"], "m", pos=True),
                     _row(f"leg {k} bend", a["bend"], b["bend"], ""),
                     _row(f"leg {k} foot x from hip", a["foot_x_from_hip_m"], b["foot_x_from_hip_m"], "m",
                          pos=True)]
    for name, a in concept["joints"].items():
        if name not in cad["joints"]:
            continue
        b = cad["joints"][name]
        for i, axis in enumerate("xyz"):
            rows.append(_row(f"{name} anchor {axis}", a["anchor_m"][i], b["anchor_m"][i], "m", pos=True))
        rows += [_row(f"{name} load inertia", a["load_inertia_kgm2"], b["load_inertia_kgm2"], "kg m2"),
                 _row(f"{name} armature", a["armature_kgm2"], b["armature_kgm2"], "kg m2")]
    return rows


def unmatched(concept: dict, cad: dict) -> dict[str, list[str]]:
    return {"legs_concept_only": [k for k in concept["legs"] if k not in cad["legs"]],
            "legs_cad_only": [k for k in cad["legs"] if k not in concept["legs"]],
            "joints_concept_only": [k for k in concept["joints"] if k not in cad["joints"]],
            "joints_cad_only": [k for k in cad["joints"] if k not in concept["joints"]]}


def table(rows: list[dict]) -> str:
    out = ["| what | concept | CAD | CAD - concept | % | over 5% / 10 mm |", "|---|---|---|---|---|---|"]
    for r in rows:
        scale = 1000.0 if r["unit"] == "m" else 1.0
        unit = "mm" if r["unit"] == "m" else r["unit"]
        pct = "—" if not math.isfinite(r["rel"]) else f"{100.0 * r['rel']:+.1f}"
        out.append(f"| {r['what']} ({unit}) | {scale * r['concept']:.4g} | {scale * r['cad']:.4g} | "
                   f"{scale * r['diff']:+.4g} | {pct} | {'**yes**' if r['flag'] else ''} |")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("concept", type=Path)
    ap.add_argument("cad", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    concept, cad = measure(a.concept), measure(a.cad)
    rows = compare(concept, cad)
    missing = unmatched(concept, cad)
    print(table(rows))
    print(f"{sum(r['flag'] for r in rows)} of {len(rows)} rows differ by over 5% (positions 10 mm)")
    for k, v in missing.items():
        if v:
            print(f"unmatched {k.replace('_', ' ')}: {', '.join(v)}")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"concept": concept, "cad": cad, "unmatched": missing, "rows": rows},
                                     indent=1) + "\n")
    shared = set(concept["legs"]) & set(cad["legs"]), set(concept["joints"]) & set(cad["joints"])
    return 0 if all(shared) else 2


if __name__ == "__main__":
    sys.exit(main())
