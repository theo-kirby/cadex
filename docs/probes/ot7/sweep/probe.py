# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Read-only F3 experiment; run with pixi Python, not a product command.

Usage: pixi run python docs/probes/ot7/sweep/probe.py PROJECT OUT
FreeCAD children read accepted BREPs, never execute the project script.
"""
import hashlib
import itertools
import json
import math
import subprocess
import sys
import time
from pathlib import Path

STEP = 5.0
SECONDS = 180
MAX_POSES = 73
REPO = Path(__file__).resolve().parents[4]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def samples(low, high, step):
    assert math.isfinite(low) and math.isfinite(high) and low <= high
    assert math.isfinite(step) and step > 0
    n = math.ceil((high - low) / step)
    assert n + 1 <= MAX_POSES, 'pose budget exceeded'
    return [min(low + i * step, high) for i in range(n + 1)]


def measure(a, b):
    assert a.Solids and b.Solids and not a.isNull() and not b.isNull()
    distance = float(a.distToShape(b)[0])
    volume = float(a.common(b).Volume) if a.BoundBox.intersect(b.BoundBox) else 0.0
    assert math.isfinite(distance) and distance >= 0
    assert math.isfinite(volume) and volume >= 0
    return distance, volume


def fixture():
    import FreeCAD as App
    import Part
    # Two unit spheres, their centres on the same radius-10 circle.
    # Their first contact is analytically 90 - 2 asin(1/10) degrees.
    fixed = Part.makeSphere(1, App.Vector(0, 10, 0))
    moving = Part.makeSphere(1, App.Vector(10, 0, 0))
    # Include a rotated/translated source placement and a nonzero solved angle.
    source_frame = App.Placement(App.Vector(13, -7, 3), App.Rotation(App.Vector(1, 0, 0), 23))
    source = moving.copy()
    source.Placement = source_frame.multiply(source.Placement)
    solved = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), 20))
    component = solved.multiply(source_frame.inverse())
    actual = source.copy()
    actual.Placement = component.multiply(source.Placement)
    expected = moving.copy()
    expected.Placement = solved.multiply(moving.Placement)
    assert actual.distToShape(expected)[0] < 1e-8
    assert abs(actual.common(expected).Volume - moving.Volume) < 1e-7
    first = None
    for value in samples(20, 90, 1):
        delta = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), value - 20))
        actual.Placement = delta.multiply(component).multiply(source.Placement)
        distance, volume = measure(fixed, actual)
        if first is None and distance <= 1e-3:
            first = value
    analytic = 90 - math.degrees(2 * math.asin(0.1))
    assert analytic <= first <= analytic + 1, (analytic, first)
    try:
        samples(0, 360, 1)
    except AssertionError:
        pass
    else:
        raise AssertionError('pose budget was not enforced')
    assert parse_result('ProcesSWEEP-RESULT {"status":"complete"}\nmore', 0) == {'status': 'complete'}
    assert parse_result('no result', 0) == {'status': 'error', 'exit': 0}
    return {'analytic_first_contact_degrees': analytic, 'measured_first_contact_degrees': first,
            'step_degrees': 1, 'placement_agreement': True, 'pose_cap_test': True, 'parser_checks': True}


def snapshot(project):
    accepted = json.loads((project / 'script.json').read_text())['accepted_attempt']
    staging = project / accepted['staging']
    outputs = {o['name']: o for o in json.loads((staging / 'result.json').read_text())['outputs']}
    return accepted, staging, outputs


def sweep(project, joint_name):
    import FreeCAD as App
    import Part
    sys.path.insert(0, str(REPO / 'src/Mod/cadex'))
    from CadexDynamics import extract_tree, joint_transform, joint_coordinates
    accepted, staging, outputs = snapshot(project)
    links = {n: o for n, o in outputs.items() if o['type'] == 'component_link'}
    joints = []
    for name, output in outputs.items():
        if output['type'] != 'joint':
            continue
        j = output['assembly_data']
        joints.append({**j, 'name': name, 'connectors': [
            {'component': c['component_output'], 'local_matrix': c['local_frame']['matrix']}
            for c in j['connectors']]})
    tree = extract_tree([{'name': n, 'grounded': o['assembly_data']['grounded']}
                         for n, o in links.items()], joints)
    assert not tree['closures'] and not tree['couplings'] and not tree['static_joints'], 'tree-only experiment'
    joint = next(j for j in joints if j['name'] == joint_name)
    assert joint['kind'] == 'revolute' and not joint['suppressed'], 'hinge-only experiment'
    body = next(b for b in tree['bodies'] if b['joint'] == joint_name)
    descendants = {body['name']}
    for b in tree['bodies']:
        if b['parent'] in descendants:
            descendants.add(b['name'])
    poses = {n: App.Placement(App.Matrix(*o['solved_placement_matrix'])) for n, o in links.items()}
    shapes, source_poses = {}, {}
    for name, link in links.items():
        source = outputs[link['source_output']]
        assert source['artifact_kind'] == 'brep', 'BREP-only experiment'
        shape = Part.Shape()
        shape.read(str(staging / source['artifact_path']))
        source_poses[name] = shape.Placement
        shape.Placement = poses[name].multiply(source_poses[name])
        shapes[name] = shape
    assembly = outputs[joint['assembly_output']]
    baseline = {frozenset((r['first'], r['second'])): r for r in assembly['clearance']}
    cached = {}
    max_distance_error = max_volume_error = 0.0
    for a, b in itertools.combinations(shapes, 2):
        distance, volume = measure(shapes[a], shapes[b])
        row = baseline[frozenset((a, b))]
        de, ve = abs(distance - row['distance_mm']), abs(volume - row['common_volume_mm3'])
        max_distance_error, max_volume_error = max(max_distance_error, de), max(max_volume_error, ve)
        assert de < 1e-4 and ve < 1e-3, (a, b, de, ve)
        cached[a, b] = distance, volume
    connectors = joint['connectors']
    a, b = [c['component'] for c in connectors]
    transform = joint_transform(links[a]['solved_placement_matrix'], connectors[0]['local_matrix'],
                                links[b]['solved_placement_matrix'], connectors[1]['local_matrix'])
    coords = joint_coordinates('revolute', transform, context=joint_name)
    assert coords['residual_mm'] < 1e-4 and coords['residual_radians'] < 1e-6
    initial = math.degrees(coords['values'][0])
    parent_side = 0 if a == body['parent'] else 1
    frame = poses[body['parent']].multiply(App.Placement(App.Matrix(*connectors[parent_side]['local_matrix'])))
    values = samples(*joint['angle_limits_degrees'], STEP)
    rows = {(a, b): {'first': a, 'second': b, 'minimum_distance_mm': None,
                     'maximum_common_volume_mm3': None, 'first_contact_degrees': None}
            for a, b in cached}
    start = time.monotonic()
    calls = 0
    for value in values:
        angle = (value - initial) * (1 if parent_side == 0 else -1)
        turn = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), angle))
        delta = frame.multiply(turn).multiply(frame.inverse())
        for n in descendants:
            shapes[n].Placement = delta.multiply(poses[n]).multiply(source_poses[n])
        for (a, b), row in rows.items():
            if (a in descendants) == (b in descendants):
                distance, volume = cached[a, b]
            else:
                distance, volume = measure(shapes[a], shapes[b])
                calls += 1
            if row['minimum_distance_mm'] is None or distance < row['minimum_distance_mm']:
                row['minimum_distance_mm'] = distance
            if row['maximum_common_volume_mm3'] is None or volume > row['maximum_common_volume_mm3']:
                row['maximum_common_volume_mm3'] = volume
                row['maximum_volume_degrees'] = value
            if row['first_contact_degrees'] is None and distance <= 1e-3:
                row['first_contact_degrees'] = value
    return {'joint': joint_name, 'revision': accepted['revision'], 'status': 'complete',
            'step_degrees': STEP, 'range_degrees': joint['angle_limits_degrees'],
            'initial_degrees': initial, 'sample_count': len(values), 'moving_components': sorted(descendants),
            'sweep_seconds': time.monotonic() - start, 'exact_pair_queries': calls,
            'baseline_pairs': len(cached), 'baseline_max_distance_error_mm': max_distance_error,
            'baseline_max_volume_error_mm3': max_volume_error, 'pairs': list(rows.values())}


def child(args):
    result = fixture() if args[0] == 'fixture' else sweep(Path(args[0]), args[1])
    print('SWEEP-RESULT ' + json.dumps(result))


def parse_result(stdout, exit_code):
    # OCCT's native progress stream can prefix our marker on the same line.
    if 'SWEEP-RESULT ' not in stdout:
        return {'status': 'error', 'exit': exit_code}
    return json.JSONDecoder().raw_decode(stdout.split('SWEEP-RESULT ', 1)[1])[0]


def collect(out):
    """Recover completed measurements from retained native logs, without rerunning."""
    summary = json.loads((out / 'summary.json').read_text())
    for job in summary['jobs']:
        name = job['name']
        result = parse_result((out / f'{name}.log').read_text(), None)
        assert result.get('status', 'complete') == 'complete', name
        result['child_wall_seconds'] = job['child_wall_seconds']
        (out / f'{name}.json').write_text(json.dumps(result, indent=2) + '\n')
        job.update(status='complete', sha256=digest(out / f'{name}.json'))
    summary['collected_from_logs'] = True
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')


def main(project, out):
    out.mkdir(parents=True, exist_ok=True)
    accepted, staging, outputs = snapshot(project)
    tracked = [project / 'script.py', project / 'script.json', staging / 'result.json']
    tracked += [staging / o['artifact_path'] for o in outputs.values() if o.get('artifact_kind') == 'brep']
    before = {str(p.relative_to(project)): digest(p) for p in tracked}
    jobs = [('fixture', ['fixture'])] + [(n, [str(project), n]) for n, o in outputs.items()
            if o['type'] == 'joint' and o['assembly_data'].get('angle_limits_degrees') is not None]
    summary = {'revision': accepted['revision'], 'seconds_cap_per_child': SECONDS,
               'pose_cap': MAX_POSES, 'input_sha256': before, 'jobs': []}
    for name, args in jobs:
        code = f"import sys; __file__={str(Path(__file__).resolve())!r}; sys.argv={['probe', '--child', *args]!r}; exec(open({str(Path(__file__).resolve())!r}).read())"
        start = time.monotonic()
        try:
            proc = subprocess.run([str(REPO / 'build/release/bin/FreeCADCmd'), '-c', code],
                                  capture_output=True, text=True, timeout=SECONDS, check=False)
            (out / f'{name}.log').write_text(proc.stdout + '\n' + proc.stderr)
            result = parse_result(proc.stdout, proc.returncode)
        except subprocess.TimeoutExpired as exc:
            (out / f'{name}.log').write_bytes((exc.stdout or b'') + (exc.stderr or b''))
            result = {'status': 'timeout', 'seconds_cap': SECONDS}
        result['child_wall_seconds'] = time.monotonic() - start
        (out / f'{name}.json').write_text(json.dumps(result, indent=2) + '\n')
        summary['jobs'].append({'name': name, 'status': result.get('status', 'complete'),
                                'child_wall_seconds': result['child_wall_seconds'],
                                'sha256': digest(out / f'{name}.json')})
        print(json.dumps(summary['jobs'][-1]), flush=True)
    assert before == {str(p.relative_to(project)): digest(p) for p in tracked}, 'accepted inputs changed'
    summary['accepted_inputs_unchanged'] = True
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    assert all(j['status'] == 'complete' for j in summary['jobs']), 'incomplete experiment; see receipts'


if __name__ == '__main__':
    if sys.argv[1] == '--collect':
        collect(Path(sys.argv[2]))
    elif sys.argv[1] == '--child':
        child(sys.argv[2:])
    else:
        main(Path(sys.argv[1]), Path(sys.argv[2]))
