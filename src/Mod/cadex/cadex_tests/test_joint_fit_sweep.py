# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import math
import pytest
from test_swept_clearance import _api, _solid
import test_clearance_scope as kernel


@pytest.mark.parametrize('key', ['sweep_step_degrees', 'sweep_step_mm'])
def test_sampling_declaration(key):
    api = _api()
    a = api.component(_solid())
    assert key not in api.assembly([a]).properties
    assert api.assembly([a], **{key: 5}).properties[key] == 5
    other = 'sweep_step_mm' if key == 'sweep_step_degrees' else 'sweep_step_degrees'
    assert other not in api.assembly([a], **{key: 5}).properties
    for value in (0, -1, True, float('nan'), float('inf')):
        with pytest.raises(ValueError):
            api.assembly([a], **{key: value})


_DRIVER = r'''
import json, sys
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
from cadex_assembly_worker import _measure_clearance, _measure_joint_sweeps
D = App.newDocument('HingeSweep')
fixed = D.addObject('Part::Feature','fixed')
fixed.Shape = Part.makeSphere(1, App.Vector(0,10,0))
source = D.addObject('Part::Feature','source')
source.Shape = Part.makeSphere(1, App.Vector(10,0,0))
source.Placement = App.Placement(App.Vector(13,-7,3), App.Rotation(App.Vector(1,0,0),23))
moving = D.addObject('App::Link','moving')
moving.LinkedObject = source
solved = App.Placement(App.Vector(), App.Rotation(App.Vector(0,0,1),20))
moving.Placement = solved.multiply(source.Placement.inverse())
D.recompute()
components = {'fixed':fixed, 'moving':moving}
data = {'fixed':{'grounded':True},'moving':{'grounded':False}}
joints = {'hinge':{'kind':'revolute','suppressed':False,'parameters':{},
    'angle_limits_degrees':[20,90], 'length_limits_mm':None,
    'connectors':[{'component_output':'fixed','local_frame':{'matrix':list(App.Matrix().A)}},
                  {'component_output':'moving','local_frame':{'matrix':list(source.Placement.toMatrix().A)}}]}}
baseline = _measure_clearance(components)
before = list(moving.Placement.toMatrix().A)
DEG = {'sweep_step_degrees': 1}
report = _measure_joint_sweeps(components,data,joints,baseline,DEG,True)
assert before == list(moving.Placement.toMatrix().A)
assert _measure_clearance(components) == baseline
bad = [dict(baseline[0], distance_mm=999)]
disagreement = _measure_joint_sweeps(components,data,joints,bad,DEG,True)
capped = _measure_joint_sweeps(components,data,joints,baseline,{'sweep_step_degrees': 0.1},True)
pair_cap = _measure_joint_sweeps(components,data,joints,baseline * 2001,DEG,True)
closed = dict(joints, closure=dict(joints['hinge'], angle_limits_degrees=None))
closed_report = _measure_joint_sweeps(components,data,closed,baseline,DEG,True)
import cadex_assembly_worker as worker
worker._SWEEP_JOINT_SECONDS = 0.001
timeout = _measure_joint_sweeps(components,data,joints,baseline,DEG,True)
worker._SWEEP_JOINT_SECONDS = 90
worker._SWEEP_TOTAL_SECONDS = 0
exhausted = _measure_joint_sweeps(components,data,joints,baseline,DEG,True)
worker._SWEEP_TOTAL_SECONDS = 180
open_ended = {'hinge': dict(joints['hinge'], angle_limits_degrees=[20, None])}
open_report = _measure_joint_sweeps(components,data,open_ended,baseline,DEG,True)
undeclared = _measure_joint_sweeps(components,data,joints,baseline,{'sweep_step_mm': 1},True)
frozen = {'hinge': dict(joints['hinge'], suppressed=True)}
suppressed = _measure_joint_sweeps(components,data,frozen,baseline,DEG,True)
mixed = _measure_joint_sweeps(components,data,
    dict(joints, frozen=dict(joints['hinge'], suppressed=True)),baseline,DEG,True)
joints['hinge']['kind'] = 'cylindrical'
unsupported = _measure_joint_sweeps(components,data,joints,baseline,{'sweep_step_degrees': 1, 'sweep_step_mm': 1},True)
print('CLEARANCE-FRAME ' + json.dumps(dict(report=report, disagreement=disagreement,
    capped=capped, unsupported=unsupported, timeout=timeout, exhausted=exhausted, pair_cap=pair_cap,
    closed=closed_report, open_ended=open_report, undeclared=undeclared,
    suppressed=suppressed, mixed=mixed)))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason='Needs real OCCT')
def test_known_angle_solved_agreement_and_incomplete_coverage(tmp_path, monkeypatch):
    monkeypatch.setattr(kernel, '_FRAME_DRIVER', _DRIVER)
    result = kernel._drive_frame(tmp_path)
    report = result['report']
    assert report['status'] == 'complete', report
    assert report['step_degrees'] == 1 and report['step_mm'] is None
    joint = report['joints'][0]
    assert joint['solved_pose_agreement']
    assert (joint['kind'], joint['unit'], joint['step']) == ('revolute', 'degrees', 1)
    assert joint['range_degrees'] == [20, 90] and abs(joint['initial_degrees'] - 20) < 1e-6
    analytic = 90 - math.degrees(2 * math.asin(0.1))
    assert analytic <= joint['pairs'][0]['first_contact_degrees'] <= analytic + 1
    assert joint['pairs'][0]['maximum_common_volume_mm3'] > 4
    assert 0 < joint['elapsed_seconds'] <= report['per_joint_seconds']
    for name, reason in [('disagreement', 'disagreement'), ('capped', 'pose budget'),
                         ('unsupported', 'hinges and sliders are supported, not cylindrical'),
                         ('timeout', 'runtime budget'), ('exhausted', 'total runtime budget'),
                         ('pair_cap', 'pair budget'), ('closed', 'closed'),
                         ('open_ended', 'open-ended'),
                         ('undeclared', 'sweep_step_degrees is not declared')]:
        assert result[name]['status'] == 'incomplete', result[name]
        assert reason in result[name]['joints'][0]['reason']
    assert result['undeclared']['step_mm'] == 1 and result['undeclared']['step_degrees'] is None
    assert result['unsupported']['joints'][0]['unit'] is None
    # A suppressed joint is not a coverage hole (ADR-371): the solver ignores
    # it, so it has no range to sweep, its row is `skipped` rather than
    # `incomplete`, and the assembly's coverage stays complete. Before this it
    # was handed to the child, which refused it as an unsupported *kind*, and
    # coverage could never be complete again.
    suppressed = result['suppressed']
    assert suppressed['status'] == 'complete', suppressed
    frozen = suppressed['joints'][0]
    assert frozen['status'] == 'skipped' and 'suppresses this revolute joint' in frozen['reason']
    # No child process ran for it: the bounded call is what stamps elapsed
    # seconds, and there are no pairs because nothing was measured.
    assert 'elapsed_seconds' not in frozen and 'pairs' not in frozen
    # ...and one suppressed joint beside a swept one costs the swept one
    # nothing.
    mixed = result['mixed']
    assert mixed['status'] == 'complete', mixed
    assert [(j['joint'], j['status']) for j in mixed['joints']] == [
        ('hinge', 'complete'), ('frozen', 'skipped')]


_SLIDER_DRIVER = r'''
import json, sys
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
from cadex_assembly_worker import _measure_clearance, _measure_joint_sweeps
D = App.newDocument('SliderSweep')
fixed = D.addObject('Part::Feature','fixed')
fixed.Shape = Part.makeSphere(1, App.Vector(10,0,0))
source = D.addObject('Part::Feature','source')
source.Shape = Part.makeSphere(1, App.Vector(10,0,0))
source.Placement = App.Placement(App.Vector(13,-7,3), App.Rotation(App.Vector(1,0,0),23))
moving = D.addObject('App::Link','moving')
moving.LinkedObject = source
solved = App.Placement(App.Vector(0,0,8), App.Rotation())
moving.Placement = solved.multiply(source.Placement.inverse())
D.recompute()
components = {'fixed':fixed, 'moving':moving}
data = {'fixed':{'grounded':True},'moving':{'grounded':False}}
joints = {'slide':{'kind':'slider','suppressed':False,'parameters':{},
    'angle_limits_degrees':None, 'length_limits_mm':[-4,10],
    'connectors':[{'component_output':'fixed','local_frame':{'matrix':list(App.Matrix().A)}},
                  {'component_output':'moving','local_frame':{'matrix':list(source.Placement.toMatrix().A)}}]}}
baseline = _measure_clearance(components)
before = list(moving.Placement.toMatrix().A)
MM = {'sweep_step_mm': 0.75}
report = _measure_joint_sweeps(components,data,joints,baseline,MM,True)
assert before == list(moving.Placement.toMatrix().A)
assert _measure_clearance(components) == baseline
# The other side of the joint as the tree parent: the same physical sweep
# with the connector order reversed must find the same overlap.
swapped = {'slide': dict(joints['slide'], connectors=list(reversed(joints['slide']['connectors'])),
                         length_limits_mm=[-10, 4])}
data_swapped = {'fixed':{'grounded':False},'moving':{'grounded':True}}
mirrored = _measure_joint_sweeps(components,data_swapped,swapped,baseline,MM,True)
bad = [dict(baseline[0], common_volume_mm3=5)]
disagreement = _measure_joint_sweeps(components,data,joints,bad,MM,True)
capped = _measure_joint_sweeps(components,data,joints,baseline,{'sweep_step_mm': 0.1},True)
undeclared = _measure_joint_sweeps(components,data,joints,baseline,{'sweep_step_degrees': 1},True)
import cadex_assembly_worker as worker
worker._SWEEP_JOINT_SECONDS = 0.001
timeout = _measure_joint_sweeps(components,data,joints,baseline,MM,True)
worker._SWEEP_JOINT_SECONDS = 90
print('CLEARANCE-FRAME ' + json.dumps(dict(report=report, mirrored=mirrored, disagreement=disagreement,
    capped=capped, undeclared=undeclared, timeout=timeout, baseline=baseline)))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason='Needs real OCCT')
def test_slider_known_position_solved_agreement_and_incomplete_coverage(tmp_path, monkeypatch):
    """Two unit spheres on a slider: contact begins 2 mm before concentric.

    The fixed sphere sits at (10, 0, 0); the moving one starts 8 mm above it
    along the slide axis and the range runs from -4 mm to 10 mm, so from the
    lower limit the spheres first touch at -2 mm and coincide at 0 mm.
    """
    monkeypatch.setattr(kernel, '_FRAME_DRIVER', _SLIDER_DRIVER)
    result = kernel._drive_frame(tmp_path)
    report = result['report']
    assert report['status'] == 'complete', report
    assert report['step_mm'] == 0.75 and report['step_degrees'] is None
    joint = report['joints'][0]
    assert (joint['joint'], joint['kind'], joint['unit'], joint['step']) == ('slide', 'slider', 'mm', 0.75)
    assert joint['solved_pose_agreement']
    assert joint['range_mm'] == [-4, 10] and abs(joint['initial_mm'] - 8) < 1e-6
    assert joint['sample_count'] == math.ceil(14 / 0.75) + 1 == 20
    pair = joint['pairs'][0]
    assert 'first_contact_degrees' not in pair
    assert -2 <= pair['first_contact_mm'] <= -2 + 0.75
    assert pair['minimum_distance_mm'] <= 1e-3
    # Coincidence is at 0 mm, which -4 + 0.75k never samples; the nearest
    # sample is -0.25 mm, where two unit spheres share the analytic lens
    # volume pi (4r + d) (2r - d)^2 / 12 with d = 0.25.
    lens = math.pi * (4 + 0.25) * (2 - 0.25) ** 2 / 12
    assert abs(pair['maximum_common_volume_mm3'] - lens) < 1e-3
    assert abs(result['baseline'][0]['distance_mm'] - 6) < 1e-6
    assert 0 < joint['elapsed_seconds'] <= report['per_joint_seconds']
    mirrored = result['mirrored']['joints'][0]
    assert mirrored['status'] == 'complete', mirrored
    assert abs(mirrored['initial_mm'] + 8) < 1e-6
    assert abs(mirrored['pairs'][0]['maximum_common_volume_mm3'] - pair['maximum_common_volume_mm3']) < 1e-6
    # The coordinate changes sign with connector order, so the overlap band
    # [-2, 2] is entered at -2 mm from the lower limit in both orderings.
    assert -2 <= mirrored['pairs'][0]['first_contact_mm'] <= -2 + 0.75
    for name, reason in [('disagreement', 'disagreement'), ('capped', 'pose budget'),
                         ('undeclared', 'sweep_step_mm is not declared'), ('timeout', 'runtime budget')]:
        assert result[name]['status'] == 'incomplete', result[name]
        assert reason in result[name]['joints'][0]['reason']
