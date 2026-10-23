"""orun12 Q1 / O3: a mirror test of an exported cat model, left against right.

Pairs every left/right body, joint, geom, actuator and equality constraint
of the MJCF by name (``_l``/``_r``, ``hl``/``hr``, ``fl``/``fr``) and compares
them mirrored through the sagittal plane (y -> -y), in the model's first
keyframe (else qpos0):

- bodies: mass, principal inertia, world position of the body and its CoM;
- joints: world anchor; world axis (a pseudo-vector, so it mirrors to
  (-x, y, -z)), with the joint's range, read in the sign convention the axis
  gives; stiffness, spring reference, damping, armature, friction loss;
- geoms: type, size, world position, friction, solref, solimp, condim;
- actuators: gear, control and force ranges, gains;
- equality constraints: type, solref, solimp, and the world anchor.

Prints each pair that differs by more than the tolerances (1% relative, 1 mm,
0.5 deg: tessellated parts differ by ~0.01%) and a count; exits 1 if any pair differs or a name has
no partner. numpy and mujoco only:

    pixi run python docs/probes/orun12/mirror.py RUN/train/cat_model-model.xml
"""

import math
import re
import sys

import mujoco
import numpy as np

SIDE = [(re.compile(r"_l(?=$|[_/])"), "_r"), (re.compile(r"hl(?=$|[_/])"), "hr"), (re.compile(r"fl(?=$|[_/])"), "fr")]
MIRROR = np.diag([1.0, -1.0, 1.0])
REL, MM, DEG = 0.01, 1.0e-3, 0.5


def partner(name):
    """The right-hand name of a left-hand one, or None if the name has no side."""
    for pat, right in SIDE:
        if pat.search(name):
            return pat.sub(right, name)
    return None


def close(a, b, tol=REL):
    a, b = np.atleast_1d(np.asarray(a, float)), np.atleast_1d(np.asarray(b, float))
    return a.shape == b.shape and bool(np.all(np.abs(a - b) <= tol * np.maximum(np.maximum(abs(a), abs(b)), 1e-9) + 1e-9))


def pairs(model, obj, count):
    names = {mujoco.mj_id2name(model, obj, i): i for i in range(count)}
    out, lonely = [], []
    for name, i in names.items():
        if not name:
            continue
        right = partner(name)
        if right is None:
            continue
        if right in names:
            out.append((name, i, names[right]))
        else:
            lonely.append(name)
    rights = {partner(n) for n, _, _ in out}
    lonely += [n for n in names if n and n not in rights and re.search(r"_r(?=$|[_/])|hr(?=$|[_/])|fr(?=$|[_/])", n)
               and not any(partner(m) == n for m in names if m)]
    return out, lonely


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    model = mujoco.MjModel.from_xml_path(argv[0])
    data = mujoco.MjData(model)
    data.qpos[:] = model.key_qpos[0] if model.nkey else model.qpos0
    mujoco.mj_forward(model, data)
    bad, lonely, checked, kinds = [], [], 0, {}

    def check(kind, name, what, ok, a, b):
        nonlocal checked
        checked += 1
        kinds.setdefault(kind, set()).add(name)
        if not ok:
            bad.append(f"{kind} {name}: {what}: L {np.round(np.atleast_1d(a), 6).tolist()} "
                       f"R {np.round(np.atleast_1d(b), 6).tolist()}")

    ps, lo = pairs(model, mujoco.mjtObj.mjOBJ_BODY, model.nbody)
    lonely += lo
    for name, l, r in ps:
        check("body", name, "mass", close(model.body_mass[l], model.body_mass[r]), model.body_mass[l], model.body_mass[r])
        check("body", name, "inertia", close(np.sort(model.body_inertia[l]), np.sort(model.body_inertia[r])),
              model.body_inertia[l], model.body_inertia[r])
        check("body", name, "position", close(MIRROR @ data.xpos[l], data.xpos[r], 0) or
              np.max(np.abs(MIRROR @ data.xpos[l] - data.xpos[r])) <= MM, data.xpos[l], data.xpos[r])
        check("body", name, "CoM", np.max(np.abs(MIRROR @ data.xipos[l] - data.xipos[r])) <= MM,
              data.xipos[l], data.xipos[r])

    ps, lo = pairs(model, mujoco.mjtObj.mjOBJ_JOINT, model.njnt)
    lonely += lo
    for name, l, r in ps:
        al, ar = MIRROR @ data.xaxis[l] * -1.0, data.xaxis[r]
        sign = 1.0 if np.dot(al, ar) >= 0 else -1.0
        check("joint", name, "axis", np.degrees(math.acos(min(1.0, abs(float(np.dot(al, ar)))))) <= DEG, al, ar)
        check("joint", name, "anchor", np.max(np.abs(MIRROR @ data.xanchor[l] - data.xanchor[r])) <= MM,
              data.xanchor[l], data.xanchor[r])
        rl = model.jnt_range[l] if sign > 0 else -model.jnt_range[l][::-1]
        check("joint", name, "range (deg, in R's sign)",
              model.jnt_limited[l] == model.jnt_limited[r] and np.max(np.abs(np.degrees(rl - model.jnt_range[r]))) <= DEG,
              np.degrees(rl), np.degrees(model.jnt_range[r]))
        for field in ("jnt_stiffness",):
            check("joint", name, field, close(getattr(model, field)[l], getattr(model, field)[r]),
                  getattr(model, field)[l], getattr(model, field)[r])
        dl, dr = model.jnt_dofadr[l], model.jnt_dofadr[r]
        for field in ("dof_damping", "dof_armature", "dof_frictionloss"):
            check("joint", name, field, close(getattr(model, field)[dl], getattr(model, field)[dr]),
                  getattr(model, field)[dl], getattr(model, field)[dr])
        ql, qr = model.jnt_qposadr[l], model.jnt_qposadr[r]
        check("joint", name, "springref (in R's sign)", close(sign * model.qpos_spring[ql], model.qpos_spring[qr]),
              sign * model.qpos_spring[ql], model.qpos_spring[qr])
        check("joint", name, "keyframe angle (in R's sign)", abs(sign * data.qpos[ql] - data.qpos[qr]) <= math.radians(DEG),
              sign * data.qpos[ql], data.qpos[qr])

    ps, lo = pairs(model, mujoco.mjtObj.mjOBJ_GEOM, model.ngeom)
    lonely += lo
    for name, l, r in ps:
        check("geom", name, "type+size", model.geom_type[l] == model.geom_type[r] and close(model.geom_size[l], model.geom_size[r]),
              model.geom_size[l], model.geom_size[r])
        check("geom", name, "position", np.max(np.abs(MIRROR @ data.geom_xpos[l] - data.geom_xpos[r])) <= MM,
              data.geom_xpos[l], data.geom_xpos[r])
        for field in ("geom_friction", "geom_solref", "geom_solimp", "geom_condim", "geom_contype", "geom_conaffinity"):
            check("geom", name, field, close(getattr(model, field)[l], getattr(model, field)[r]),
                  getattr(model, field)[l], getattr(model, field)[r])

    ps, lo = pairs(model, mujoco.mjtObj.mjOBJ_ACTUATOR, model.nu)
    lonely += lo
    for name, l, r in ps:
        check("actuator", name, "|gear|", close(np.abs(model.actuator_gear[l]), np.abs(model.actuator_gear[r])),
              model.actuator_gear[l], model.actuator_gear[r])
        for field in ("actuator_forcerange", "actuator_gainprm", "actuator_biasprm"):
            a, b = np.abs(getattr(model, field)[l]), np.abs(getattr(model, field)[r])
            check("actuator", name, "|" + field + "|", close(np.sort(a), np.sort(b)), getattr(model, field)[l], getattr(model, field)[r])
        a, b = model.actuator_ctrlrange[l], model.actuator_ctrlrange[r]
        check("actuator", name, "ctrlrange (either sign)", close(a, b) or close(-a[::-1], b), a, b)

    ps, lo = pairs(model, mujoco.mjtObj.mjOBJ_EQUALITY, model.neq)
    lonely += lo
    for name, l, r in ps:
        check("equality", name, "type+solref+solimp", model.eq_type[l] == model.eq_type[r] and close(model.eq_solref[l], model.eq_solref[r])
              and close(model.eq_solimp[l], model.eq_solimp[r]), model.eq_solref[l], model.eq_solref[r])
        bl, br = model.eq_obj1id[l], model.eq_obj1id[r]
        if model.eq_type[l] == mujoco.mjtEq.mjEQ_CONNECT:
            pl = data.xpos[bl] + data.xmat[bl].reshape(3, 3) @ model.eq_data[l][:3]
            pr = data.xpos[br] + data.xmat[br].reshape(3, 3) @ model.eq_data[r][:3]
            check("equality", name, "world anchor", np.max(np.abs(MIRROR @ pl - pr)) <= MM, pl, pr)

    print(f"{argv[0]}: {checked} left/right checks, {len(bad)} differ, {len(lonely)} without a partner")
    print("  pairs: " + ", ".join(f"{len(v)} {k}" for k, v in kinds.items()))
    for line in bad:
        print("  DIFF", line)
    for name in lonely:
        print("  ALONE", name)
    return 1 if bad or lonely else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
