"""Finch on the environment's floor: the free-base export, stepped by a stock
MuJoCo (ADR-335, charter D6's prerequisite).

Usage: pixi run python docs/probes/ot6/finch/free_base_probe.py PROJECT OUT

Reads the accepted attempt's exported MJCF and its manifest, opens the file
with MuJoCo alone, and runs two short rollouts from the solved keyframe: one
with the servos holding their zero targets (ctrl = 0) and one with actuation
disabled, so the mechanism is free to collapse. Records the pelvis height and
the deepest floor penetration through both, and which geoms touched the
environment's floor. Writes OUT/free_base.json. Nothing here rebuilds or
re-accepts anything, and nothing here trains.
"""
import hashlib, json, sys
from pathlib import Path
import mujoco

project, out = Path(sys.argv[1]), Path(sys.argv[2])
sj = json.loads((project / 'script.json').read_text())
accepted = sj['accepted_attempt']
staging = project / accepted['staging']
result = json.loads((staging / 'result.json').read_text())
outs = {o['name']: o for o in result['outputs']}
solve = result['validations']['assembly']
model_out = outs['finch_model']
xml_path = staging / 'outputs' / 'finch_model-model.xml'
xml = xml_path.read_bytes()
dyn = model_out['assembly_data']['dynamics']
FLOOR = dyn['environment']['floor']['geom']

model = mujoco.MjModel.from_xml_string(xml.decode('utf-8'))
data = mujoco.MjData(model)
key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, 'solved')
pelvis = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'pelvis_link')
floor = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, FLOOR)
free = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(model.njnt)
        if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE]


def gname(i):
    return mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(i))


def rollout(label, seconds, disable_actuation, shove_m_s=0.0):
    mujoco.mj_resetDataKeyframe(model, data, key)
    model.opt.disableflags &= ~int(mujoco.mjtDisableBit.mjDSBL_ACTUATION)
    if disable_actuation:
        model.opt.disableflags |= int(mujoco.mjtDisableBit.mjDSBL_ACTUATION)
    data.ctrl[:] = 0.0
    if shove_m_s:
        # A forward velocity on the free joint's translational rows: the
        # shove that shows the base is free to fall, since the straight-leg
        # pose is a balanced equilibrium a symmetric integrator never leaves.
        address = int(model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, free[0])])
        data.qvel[address] = shove_m_s
    mujoco.mj_forward(model, data)
    step = float(model.opt.timestep)
    every = max(1, int(round(0.1 / step)))
    samples, touched, deepest, min_pelvis = [], set(), 0.0, 1e9
    n = int(round(seconds / step))
    for i in range(n + 1):
        if i % every == 0:
            samples.append([round(i * step, 3), round(float(data.xpos[pelvis][2]) * 1000.0, 3)])
        for c in range(int(data.ncon)):
            con = data.contact[c]
            if floor in (con.geom1, con.geom2):
                touched.add(gname(con.geom2 if con.geom1 == floor else con.geom1))
                deepest = min(deepest, float(con.dist))
        min_pelvis = min(min_pelvis, float(data.xpos[pelvis][2]))
        if i < n:
            mujoco.mj_step(model, data)
    up = data.xmat[pelvis].reshape(3, 3)[:, 2]
    return {
        'label': label, 'seconds': seconds, 'actuation': 'disabled' if disable_actuation else 'ctrl = 0 (servos hold their zero targets)',
        'shove_m_s': shove_m_s,
        'pelvis_z_mm': samples, 'pelvis_z_final_mm': samples[-1][1], 'pelvis_z_min_mm': round(min_pelvis * 1000.0, 3),
        'pelvis_up_z_final': round(float(up[2]), 4),
        'deepest_floor_penetration_mm': round(-deepest * 1000.0, 4),
        'touched_the_floor': sorted(touched),
    }


mujoco.mj_resetDataKeyframe(model, data, key)
mujoco.mj_forward(model, data)
receipt = {
    'project': 'ot6-finch', 'revision': accepted['revision'],
    'script_sha256': hashlib.sha256((project / 'script.py').read_bytes()).hexdigest(),
    'mjcf': {'path': str(xml_path.relative_to(project)), 'sha256': hashlib.sha256(xml).hexdigest(), 'bytes': len(xml),
             'manifest_sha256': model_out['artifact_sha256']},
    'solve': {'status': solve['status'], 'verdict': solve['solver_verdict'], 'grounded_components': solve['grounded_components'],
              'free_base': solve['free_base'], 'component_count': solve['component_count'], 'joint_count': solve['joint_count']},
    'model': {'nbody': int(model.nbody), 'nq': int(model.nq), 'nv': int(model.nv), 'ngeom': int(model.ngeom), 'nu': int(model.nu),
              'free_joints': free, 'floor': dyn['environment']['floor'],
              'floor_geom_body': mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(model.geom_bodyid[floor])),
              'grounded_components': dyn['grounded_components'], 'timestep_s': float(model.opt.timestep),
              'gravity_m_s2': [float(v) for v in model.opt.gravity]},
    'solved_pose': {'pelvis_z_mm': round(float(data.xpos[pelvis][2]) * 1000.0, 3),
                    'initial_contacts': sorted({tuple(c['component_outputs']) for c in dyn['initial_contacts']}),
                    'initial_contact_count': len(dyn['initial_contacts']),
                    'worst_initial_distance_mm': min(c['distance_mm'] for c in dyn['initial_contacts'])},
    'rollouts': [rollout('held', 2.0, False), rollout('passive', 2.0, True), rollout('shoved', 4.0, True, shove_m_s=0.3)],
    'assessment': None,
}
held, passive, shoved = receipt['rollouts']
checks = {
    'nothing_grounded': solve['grounded_components'] == [] and dyn['grounded_components'] == [],
    'pelvis_is_the_free_base': solve['free_base'] == 'pelvis_link' and free == ['pelvis_link/free'],
    'floor_is_the_worlds': receipt['model']['floor_geom_body'] == 'world',
    'soles_rest_on_the_floor_at_t0': receipt['solved_pose']['initial_contacts'] == [('world', 'shin_l_link'), ('world', 'shin_r_link')],
    'held_stands_2s': abs(held['pelvis_z_final_mm'] - receipt['solved_pose']['pelvis_z_mm']) < 5.0 and held['pelvis_up_z_final'] > 0.99,
    'passive_stays_on_the_floor': passive['pelvis_z_min_mm'] > 0.0,
    'shoved_falls_onto_the_floor_not_through_it': shoved['pelvis_z_final_mm'] < held['pelvis_z_final_mm'] - 20.0 and shoved['pelvis_z_min_mm'] > 0.0,
    'impact_penetration_under_5mm': max(r['deepest_floor_penetration_mm'] for r in receipt['rollouts']) < 5.0,
}
receipt['checks'] = checks
receipt['assessment'] = ('all hold' if all(checks.values()) else 'FAILED: ' + ', '.join(k for k, v in checks.items() if not v))
out.mkdir(parents=True, exist_ok=True)
(out / 'free_base.json').write_text(json.dumps(receipt, indent=1) + '\n')
print(json.dumps({k: receipt[k] for k in ('revision', 'solve', 'checks', 'assessment')}, indent=1))
print('held', held['pelvis_z_mm'][::5], held['pelvis_up_z_final'], held['deepest_floor_penetration_mm'], held['touched_the_floor'])
print('passive', passive['pelvis_z_mm'][::5], passive['pelvis_up_z_final'], passive['deepest_floor_penetration_mm'], passive['touched_the_floor'])
print('shoved', shoved['pelvis_z_mm'][::5], shoved['pelvis_up_z_final'], shoved['deepest_floor_penetration_mm'], shoved['touched_the_floor'])
sys.exit(0 if all(checks.values()) else 1)
