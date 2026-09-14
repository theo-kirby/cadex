# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import math
import pytest
from test_swept_clearance import _api, _solid
import test_clearance_scope as kernel


def test_sampling_declaration():
    api = _api()
    a = api.component(_solid())
    assert 'sweep_step_degrees' not in api.assembly([a]).properties
    assert api.assembly([a], sweep_step_degrees=5).properties['sweep_step_degrees'] == 5
    for value in (0, -1, True, float('nan'), float('inf')):
        with pytest.raises(ValueError):
            api.assembly([a], sweep_step_degrees=value)


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
report = _measure_joint_sweeps(components,data,joints,baseline,1,True)
assert before == list(moving.Placement.toMatrix().A)
assert _measure_clearance(components) == baseline
bad = [dict(baseline[0], distance_mm=999)]
disagreement = _measure_joint_sweeps(components,data,joints,bad,1,True)
capped = _measure_joint_sweeps(components,data,joints,baseline,0.1,True)
pair_cap = _measure_joint_sweeps(components,data,joints,baseline * 2001,1,True)
closed = dict(joints, closure=dict(joints['hinge'], angle_limits_degrees=None))
closed_report = _measure_joint_sweeps(components,data,closed,baseline,1,True)
import cadex_assembly_worker as worker
worker._SWEEP_JOINT_SECONDS = 0.001
timeout = _measure_joint_sweeps(components,data,joints,baseline,1,True)
worker._SWEEP_JOINT_SECONDS = 90
worker._SWEEP_TOTAL_SECONDS = 0
exhausted = _measure_joint_sweeps(components,data,joints,baseline,1,True)
worker._SWEEP_TOTAL_SECONDS = 180
joints['hinge']['kind'] = 'slider'
unsupported = _measure_joint_sweeps(components,data,joints,baseline,1,True)
print('CLEARANCE-FRAME ' + json.dumps(dict(report=report, disagreement=disagreement,
    capped=capped, unsupported=unsupported, timeout=timeout, exhausted=exhausted, pair_cap=pair_cap, closed=closed_report)))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason='Needs real OCCT')
def test_known_angle_solved_agreement_and_incomplete_coverage(tmp_path, monkeypatch):
    monkeypatch.setattr(kernel, '_FRAME_DRIVER', _DRIVER)
    result = kernel._drive_frame(tmp_path)
    report = result['report']
    assert report['status'] == 'complete', report
    joint = report['joints'][0]
    assert joint['solved_pose_agreement']
    analytic = 90 - math.degrees(2 * math.asin(0.1))
    assert analytic <= joint['pairs'][0]['first_contact_degrees'] <= analytic + 1
    assert joint['pairs'][0]['maximum_common_volume_mm3'] > 4
    for name, reason in [('disagreement','disagreement'),('capped','pose budget'),
                         ('unsupported','hinges'), ('timeout','runtime budget'), ('exhausted','total runtime budget'), ('pair_cap','pair budget'), ('closed','closed')]:
        assert result[name]['status'] == 'incomplete'
        assert reason in result[name]['joints'][0]['reason']
