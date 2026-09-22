# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""B4's two readings: contact compression, and the final design against the baseline.

The compression reader is pinned against a one-sphere model and a trace
built from stated heights and turns. Every expected depth is written as a
literal beside its pose, so the rotation of the sphere's offset is checked
as well as the subtraction. The B4 receipt is then held to its own files.
Fit, swept fit and inventory must be unchanged from the ot8 baseline, and
the compression must stay apart from the geometry intersections.
"""
import importlib.util
import json
import math
from pathlib import Path

import pytest

PROBES = Path(__file__).resolve().parents[2] / 'docs/probes'
PATH = PROBES / 'ot9/runner/contact_compression.py'
spec = importlib.util.spec_from_file_location('ot9_contact_compression', PATH)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

MODEL = """<mujoco>
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.1" pos="0 0 0.002"/>
    <body name="wheel" pos="0 0 0">
      <freejoint/>
      <geom name="wheel/collision0" type="sphere" size="0.005" pos="0 0.010 0.007"/>
    </body>
  </worldbody>
  <keyframe><key name="solved"/></keyframe>
</mujoco>
"""


def _half_turn_about_x(degrees):
    half = math.radians(degrees) / 2.0
    return [math.sin(half), 0.0, 0.0, math.cos(half)]


def _trace(tmp_path, poses):
    frames = [{'frame_index': 0, 'frame_kind': 'input', 'nominal_time_s': None, 'component_placements': {}}]
    for index, (time_s, z_mm, quat) in enumerate(poses, start=1):
        frames.append({'frame_index': index, 'frame_kind': 'solver_output', 'nominal_time_s': time_s,
                       'component_placements': {'wheel': {'position_mm': [3.0, -4.0, z_mm],
                                                          'rotation_xyzw': quat}}})
    path = tmp_path / 'assembly-simulation-trace.json'
    path.write_text(json.dumps({'frames': frames}))
    return path


def test_the_floor_the_spheres_and_the_keyframe_gap(tmp_path):
    pytest.importorskip('mujoco')
    model = tmp_path / 'model.xml'
    model.write_text(MODEL)
    floor = reader.floor_and_spheres(model)
    assert floor['floor_z_mm'] == pytest.approx(2.0)
    [sphere] = floor['spheres']
    assert sphere['geom'] == 'wheel/collision0' and sphere['body'] == 'wheel'
    assert sphere['radius_mm'] == pytest.approx(5.0)
    assert sphere['local_mm'] == pytest.approx([0.0, 10.0, 7.0])
    # At qpos0 the centre is at z = 7 mm, the floor at 2 mm and the radius 5 mm, so the sphere just touches.
    assert floor['keyframe_contact_dist_mm']['wheel/collision0'] == pytest.approx(0.0, abs=1e-9)


def test_compression_is_radius_minus_the_rotated_centre_height(tmp_path):
    floor = {'floor_z_mm': 2.0, 'spheres': [
        {'geom': 'wheel/collision0', 'body': 'wheel', 'local_mm': [0.0, 10.0, 7.0], 'radius_mm': 5.0}]}
    level = [0.0, 0.0, 0.0, 1.0]
    trace = _trace(tmp_path, [
        # centre z = body z + 7; compression = 5 - (centre - 2)
        (0.02, -0.25, level),                     # centre 6.75 -> 0.25 mm
        (0.04, -1.5, level),                      # centre 5.5  -> 1.5 mm, the peak
        (1.00, -0.6, level),                      # centre 6.4  -> 0.6 mm
        # a quarter turn about +X takes (0, 10, 7) to (0, -7, 10): centre z = body z + 10
        (1.02, -3.4, _half_turn_about_x(90.0)),   # centre 6.6  -> 0.4 mm
        (1.04, 1.0, level),                       # centre 8.0  -> -1.0 mm, a gap above the floor
    ])
    result = reader.compression(trace, floor, settled_after_s=1.0)
    assert result['frames'] == 5
    assert result['peak']['compression_mm'] == pytest.approx(1.5)
    assert (result['peak']['geom'], result['peak']['at_s']) == ('wheel/collision0', 0.04)
    settled = result['settled']
    assert settled['samples'] == 3
    assert settled['max_mm'] == pytest.approx(0.6)
    assert settled['median_mm'] == pytest.approx(0.4)
    assert settled['min_mm'] == pytest.approx(-1.0)


def test_the_final_design_is_the_baseline_design_measured_again():
    contract = json.loads((PROBES / 'ot9/contract.json').read_text())
    receipt = json.loads((PROBES / 'ot9/retained/r5-robin-fit.json').read_text())
    evaluation = json.loads((PROBES / 'ot9/retained/r4-robin-eval-1.json').read_text())
    final, baseline, comparison = receipt['final'], receipt['baseline'], receipt['comparison']
    pins = contract['baseline']
    # The baseline read is ot8-robin's own accepted pin and the files the g4 receipt hashed.
    assert (baseline['accepted_revision'], baseline['accepted_digest'], baseline['script_sha256']) == (
        pins['accepted_revision'], pins['accepted_digest'], pins['script_sha256'])
    g4 = {a['path']: a['sha256'] for a in json.loads(
        (PROBES / 'ot8/retained/g4-robin-diagnosis.json').read_text())['artifacts']}
    hashed = {a['path']: a['sha256'] for a in baseline['artifacts']}
    assert hashed['fit.json'] == g4['before/fit.json']
    assert hashed['inventory.json'] == g4['before/inventory.json']
    # The final read is the revision the last B3 seed left accepted, on the pinned model and task.
    last_seed = evaluation['evaluation']['seeds'][-1]
    assert final['accepted_revision'] != baseline['accepted_revision']
    assert receipt['project_store']['accepted_equals_working'] is True
    assert final['mjcf_sha256'] == baseline['mjcf_sha256'] == pins['mjcf']['sha256'] == last_seed['mjcf_sha256']
    assert final['task_sha256'] == baseline['task_sha256'] == pins['task']['sha256'] == last_seed['task_sha256']
    # B4's bar, on the final design: zero failing static checks, complete swept fit on both wheels.
    for side in (final, baseline):
        static = side['static_fit']
        assert static['verdict'] == 'pass' and static['failing_count'] == 0
        assert static['counts']['intersection'] == 0 and static['counts']['unknown'] == 0
        assert static['counts']['clear'] == static['pairs_checked'] == 378
        swept = side['swept_fit']
        assert (swept['verdict'], swept['coverage'], swept['failing_count']) == ('pass', 'complete', 0)
        assert sorted(j['joint'] for j in swept['joints']) == ['joint_wheel_l_axle', 'joint_wheel_r_axle']
        assert all(j['status'] == 'complete' and j['maximum_common_volume_mm3'] == 0.0 for j in swept['joints'])
        assert (swept['joints_complete'], swept['joints_skipped']) == (2, 0)
        assert side['attachments']['reported_count'] == 0
        inventory = side['inventory']
        assert inventory['derived_catalog_sources'] == []
        assert inventory['catalogued_components'] + len(inventory['uncatalogued_sources']) == inventory['component_count']
        assert [row['catalog'] for row in inventory['catalog_provenance']] == sorted(inventory['catalog_counts'])
        assert all(row['sources'] and row['count'] == inventory['catalog_counts'][row['catalog']]
                   for row in inventory['catalog_provenance'])
    # Unchanged, and measured so: every measurement equal once revision and timing are set aside.
    assert comparison['equal_after_normalisation'] == {
        'clearance.json': True, 'fit.json': True, 'inventory.json': True}
    for key in ('static_fit', 'swept_fit', 'attachments', 'inventory'):
        assert final[key] == baseline[key]
    assert comparison['mjcf_identical'] is True
    assert comparison['mass_kg']['final'] == comparison['mass_kg']['baseline']
    assert sorted(comparison['parameter_changes']) == ['policy_on', 'rollout_seed']
    assert len(comparison['script_diff']) == 2 and all('assembly.policy(' in line for line in comparison['script_diff'])
    # Compression is the contact spring, reported beside the fit and never as an intersection.
    contact = receipt['contact_compression']
    assert [row['seed'] for row in contact['seeds']] == contract['evaluation_seeds']
    assert all(gap == 0.0 for gap in contact['keyframe_contact_dist_mm'].values())
    for row in contact['seeds']:
        assert row['frames'] == 401
        assert abs(row['settled_median_mm'] - contact['baseline']['settled_mm']) < 0.01
        assert row['peak_at_s'] <= 0.1
    assert 'not a geometry intersection' in contact['classification']
