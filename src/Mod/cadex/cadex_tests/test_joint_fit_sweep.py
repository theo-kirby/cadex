# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import ast
import math
import re
from pathlib import Path

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


_WELD_DRIVER = r'''
import json, math, sys
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
from cadex_assembly_worker import _measure_clearance, _measure_joint_sweeps
D = App.newDocument('WeldSweep')
fixed = D.addObject('Part::Feature','fixed')
fixed.Shape = Part.makeSphere(1, App.Vector(0,10,0))
source = D.addObject('Part::Feature','source')
source.Shape = Part.makeSphere(1, App.Vector(10,0,0))
source.Placement = App.Placement(App.Vector(13,-7,3), App.Rotation(App.Vector(1,0,0),23))
moving = D.addObject('App::Link','moving')
moving.LinkedObject = source
solved = App.Placement(App.Vector(), App.Rotation(App.Vector(0,0,1),20))
moving.Placement = solved.multiply(source.Placement.inverse())
# Welded to `moving` and touching it exactly: the horn against its link.
centre = App.Vector(10 * math.cos(math.radians(20)), 10 * math.sin(math.radians(20)), 2.0)
carried = D.addObject('Part::Feature','carried')
carried.Shape = Part.makeSphere(1, centre)
D.recompute()
components = {'fixed':fixed, 'moving':moving, 'carried':carried}
data = {'fixed':{'grounded':True},'moving':{'grounded':False},'carried':{'grounded':False}}
identity = {'matrix': list(App.Matrix().A)}
joints = {'hinge':{'kind':'revolute','suppressed':False,'parameters':{},
    'angle_limits_degrees':[20,70], 'length_limits_mm':None,
    'connectors':[{'component_output':'fixed','local_frame':dict(identity)},
                  {'component_output':'moving','local_frame':{'matrix':list(source.Placement.toMatrix().A)}}]},
    'weld':{'kind':'fixed','suppressed':False,'parameters':{},
    'angle_limits_degrees':None, 'length_limits_mm':None,
    'connectors':[{'component_output':'moving','local_frame':dict(identity)},
                  {'component_output':'carried','local_frame':dict(identity)}]}}
baseline = _measure_clearance(components)
report = _measure_joint_sweeps(components,data,joints,baseline,{'sweep_step_degrees': 1},True)
print('CLEARANCE-FRAME ' + json.dumps(dict(report=report, baseline=baseline)))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason='Needs real OCCT')
def test_welded_pair_is_marked_as_holding_still_through_the_sweep(tmp_path, monkeypatch):
    """A welded pair repeats its solved-pose measurement at every sample (ADR-374).

    Three unit spheres: `fixed` at 90 deg on a radius-10 circle, `moving`
    hinged from 20 to 70 deg on the same circle, and `carried` welded to
    `moving` and touching it. Nothing ever contacts through the motion --
    `fixed` meets `moving` only at 78.5 deg and `carried` only at 90 deg,
    both outside the range -- yet `moving` and `carried` read 0.0 mm apart at
    every sample, because the weld holds them there. `relative_motion` is the
    row saying which of the two facts it carries.
    """

    monkeypatch.setattr(kernel, '_FRAME_DRIVER', _WELD_DRIVER)
    result = kernel._drive_frame(tmp_path)
    report = result['report']
    assert report['status'] == 'complete', report
    # The weld declares no limits, so it is not a swept joint of its own.
    assert [joint['joint'] for joint in report['joints']] == ['hinge']
    joint = report['joints'][0]
    assert joint['status'] == 'complete' and joint['solved_pose_agreement']
    rows = {(row['first'], row['second']): row for row in joint['pairs']}
    assert set(rows) == {('fixed', 'moving'), ('fixed', 'carried'), ('moving', 'carried')}
    assert rows['fixed', 'moving']['relative_motion'] is True
    assert rows['fixed', 'carried']['relative_motion'] is True
    # Both sides ride the swept subtree, so the hinge cannot change this pair.
    assert rows['moving', 'carried']['relative_motion'] is False
    # ...and this is why the flag has to exist: the weld reports the range's
    # own floor as "first contact" and 0.0 mm as its minimum, every time.
    weld = rows['moving', 'carried']
    assert weld['first_contact_degrees'] == 20
    assert weld['minimum_distance_mm'] <= 1e-3
    assert weld['maximum_common_volume_mm3'] <= 1e-6
    # Neither moving pair ever touches: the chord between two radius-10
    # centres 20 deg apart is 20 sin(10 deg), and the radii take 2 mm off it.
    for key in (('fixed', 'moving'), ('fixed', 'carried')):
        assert rows[key]['first_contact_degrees'] is None, rows[key]
        assert rows[key]['maximum_common_volume_mm3'] == 0.0
    assert abs(rows['fixed', 'moving']['minimum_distance_mm']
               - (20 * math.sin(math.radians(10)) - 2)) < 1e-6
    assert abs(rows['fixed', 'carried']['minimum_distance_mm']
               - (math.sqrt(204 - 200 * math.sin(math.radians(70))) - 2)) < 1e-6


#: Where the swept row's shape is decided, and where the contract says so.
_WORKER = Path(__file__).resolve().parents[1] / 'cadex_assembly_worker.py'
_CONTRACT = Path(__file__).resolve().parents[4] / 'docs' / 'INTEGRATION.md'


def _published_pair_row_keys():
    """Constant keys `_sweep_joint` puts on every swept pair row, from source.

    Read with `ast` rather than by running the sweep, because the sweep needs
    a real kernel and this contract does not: the shape of the row is decided
    by one dict literal, and a renamed or deleted key is visible there.
    """
    worker = ast.parse(_WORKER.read_text(encoding='utf-8'))
    func = next(node for node in ast.walk(worker)
                if isinstance(node, ast.FunctionDef) and node.name == '_sweep_joint')
    assign = next(node for node in ast.walk(func)
                  if isinstance(node, ast.Assign)
                  and any(getattr(t, 'id', None) == 'rows' for t in node.targets))
    literal = assign.value.elt if isinstance(assign.value, ast.ListComp) else assign.value
    assert isinstance(literal, ast.Dict), ast.dump(assign.value)
    return {key.value for key in literal.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)}


def _published_sweep_section():
    """The section of `docs/INTEGRATION.md` that describes a published sweep."""
    doc = _CONTRACT.read_text(encoding='utf-8')
    section = doc.partition('### Published joint sweeps')[2]
    assert section, 'docs/INTEGRATION.md has no published-sweep section'
    return section.partition('\n### ')[0].partition('\n## ')[0]


def test_the_protocol_document_carries_the_swept_row_motion_flag():
    """The flag is protocol, so the document that is the contract is tested.

    The engine's own guard for `relative_motion` needs a real kernel and skips
    without one, and the sentence that documents it landed a commit after the
    behaviour did (ADR-374) — a thing forgotten once is worth a guard. Two
    facts held against each other, both headless: `_sweep_joint` puts the flag
    on every pair row, and the section the other half of the protocol reads
    names that key *and* says it is absent on a revision accepted before it
    existed, which is the whole reason an older receipt still reads correctly.
    """
    keys = _published_pair_row_keys()
    assert 'relative_motion' in keys, (
        '_sweep_joint no longer publishes `relative_motion` on every pair row; '
        f'it publishes {sorted(keys)}. Renaming it is a protocol change: move '
        'docs/INTEGRATION.md and cli/cadex_cli/clearance.py in the same change.')

    section = _published_sweep_section()
    prose = ' '.join(section.split())
    named = set(re.findall(r'`([a-z0-9_]+)`', prose))
    assert 'relative_motion' in named, (
        "docs/INTEGRATION.md's published-sweep section does not name "
        '`relative_motion`, which every swept pair row carries (ADR-374).')

    sentences = [s for s in re.split(r'(?<=\.) ', prose) if 'relative_motion' in s]
    absent = [s for s in sentences
              if re.search(r'\babsent\b|\bnot present\b|\bomitted\b', s)
              and re.search(r'\bbefore\b|\bolder\b', s)]
    assert absent, (
        "docs/INTEGRATION.md's published-sweep section names `relative_motion` "
        'but no sentence says it is **absent** on a revision accepted before '
        'ADR-374. That absence is behaviour — a reader counts an unflagged row '
        'as moving — so it belongs in the contract, in a sentence naming the '
        f'key. Sentences that name it: {sentences}')


def test_a_joint_that_can_move_and_declares_no_limits_is_named_as_missing_coverage():
    """Known answer: a wheel nobody bounded is a coverage hole, not silence.

    Before ADR-375 a joint declaring neither limit was dropped by the loop's
    first line, so it reached no row at all: a two-wheeled chassis whose one
    limited hinge swept clean read `complete` beside two wheels that had been
    measured at the solved pose and nowhere else. The two joints that really
    hold no range keep their silence -- a weld, whose pair the attachment
    report measures (ADR-370), and a suppressed joint the assembly also left
    unlimited.
    """

    from cadex_assembly_worker import _measure_joint_sweeps

    def joint(kind, limits=None, suppressed=False):
        return {'kind': kind, 'suppressed': suppressed, 'parameters': {}, 'connectors': [],
                'angle_limits_degrees': limits, 'length_limits_mm': None}

    report = _measure_joint_sweeps({}, {}, {
        'wheel_left': joint('revolute'),
        'wheel_right': joint('revolute'),
        'slide': joint('slider'),
        'ball': joint('ball'),
        'weld': joint('fixed'),
        'parked': joint('revolute', suppressed=True),
        'parked_hinge': joint('revolute', limits=[0, 90], suppressed=True),
    }, [], {'sweep_step_degrees': 5, 'sweep_step_mm': 1}, True)

    # Every joint that could move and was not bounded is named; the weld and
    # the suppressed unlimited joint are not rows at all.
    assert [(j['joint'], j['status']) for j in report['joints']] == [
        ('wheel_left', 'incomplete'), ('wheel_right', 'incomplete'),
        ('slide', 'incomplete'), ('ball', 'incomplete'),
        ('parked_hinge', 'skipped')]
    assert report['status'] == 'incomplete', report
    # ...and the reason names the declaration that would have it swept, per
    # kind, without claiming a step is missing when one was declared.
    assert 'declare angle_limits_degrees' in report['joints'][0]['reason']
    assert 'declare length_limits_mm' in report['joints'][2]['reason']
    for row in report['joints'][:2]:
        assert 'declares no limits' in row['reason'] and 'solved pose only' in row['reason']
    # An unlimited joint of a kind no sweep supports says that instead: no
    # limit it could declare would have it swept.
    assert 'not ball' in report['joints'][3]['reason']
    # Nothing was measured: no child process, no geometry, no pairs.
    assert all('pairs' not in row and 'elapsed_seconds' not in row for row in report['joints'])
    # An assembly whose every joint is welded or suppressed-and-unlimited is
    # still complete coverage of an empty set (ADR-367).
    quiet = _measure_joint_sweeps({}, {}, {'weld': joint('fixed'),
                                           'parked': joint('revolute', suppressed=True)},
                                  [], {'sweep_step_degrees': 5}, True)
    assert quiet['status'] == 'complete' and quiet['joints'] == []


_GRAZE_DRIVER = r'''
import json, sys
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
from cadex_assembly_worker import _measure_clearance, _measure_joint_sweeps
D = App.newDocument('Graze')
fixed = D.addObject('Part::Feature','fixed')
fixed.Shape = Part.makeSphere(1, App.Vector(0, 12.04, 0))
moving = D.addObject('Part::Feature','moving')
moving.Shape = Part.makeSphere(1, App.Vector(10, 0, 0))
moving.Placement = App.Placement(App.Vector(), App.Rotation(App.Vector(0,0,1), 20))
D.recompute()
components = {'fixed': fixed, 'moving': moving}
data = {'fixed': {'grounded': True}, 'moving': {'grounded': False}}
joints = {'hinge': {'kind':'revolute','suppressed':False,'parameters':{},
  'angle_limits_degrees':[20,90],'length_limits_mm':None,
  'connectors':[{'component_output':'fixed','local_frame':{'matrix':list(App.Matrix().A)}},
                {'component_output':'moving','local_frame':{'matrix':list(App.Matrix().A)}}]}}
baseline = _measure_clearance(components)
report = _measure_joint_sweeps(components, data, joints, baseline,
                               {'sweep_step_degrees': 1}, True)
print('CLEARANCE-FRAME ' + json.dumps(dict(baseline=baseline, report=report)))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason='Needs real OCCT')
def test_a_hinge_that_grazes_closes_a_gap_the_solved_pose_cannot_see(tmp_path, monkeypatch):
    """Known answer: 10.7516 mm clear at the solved pose, 0.04 mm in the range.

    Two unit spheres. The fixed centre sits 12.04 mm from the hinge axis and
    the moving centre 10 mm from it, so at 90 degrees the centres are exactly
    2.04 mm apart and the surfaces close to 0.04 mm without ever touching.
    The solved pose is 20 degrees, where they are 10.7516 mm apart -- clear by
    two orders of magnitude.

    This is the measurement ADR-378's check reads. Nothing here judges it:
    the engine reports the minimum and the client holds it against the pair's
    minimum, which is the split ADR-366 set up. What the fixture pins is that
    a real sweep produces a close approach with *zero* common volume, so a
    block that can only fail on interpenetration is blind to it by
    construction rather than by accident.
    """

    monkeypatch.setattr(kernel, '_FRAME_DRIVER', _GRAZE_DRIVER)
    result = kernel._drive_frame(tmp_path)
    (solved,) = result['baseline']
    assert solved['common_volume_mm3'] == 0
    assert solved['distance_mm'] == pytest.approx(
        math.hypot(10 * math.cos(math.radians(20)) - 0,
                   10 * math.sin(math.radians(20)) - 12.04) - 2, abs=1e-9)
    assert solved['distance_mm'] == pytest.approx(10.751594, abs=1e-6)
    report = result['report']
    assert report['status'] == 'complete'
    (joint,) = report['joints']
    assert joint['status'] == 'complete' and joint['sample_count'] == 71
    assert joint['range_degrees'] == [20, 90]
    (pair,) = joint['pairs']
    assert pair['relative_motion'] is True
    assert pair['minimum_distance_mm'] == pytest.approx(0.04, abs=1e-9)
    # Never touching, so the sweep names no first contact and the pair has no
    # common volume anywhere in the range.
    assert pair['maximum_common_volume_mm3'] == 0
    assert pair['first_contact_degrees'] is None
