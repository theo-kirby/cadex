# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ot8 balance diagnosis, against answers written before it is run.

G4 asks whether a failing smoke is a geometry mismatch, a design defect or a
missing controller, and a measurement tool that is itself unchecked is not
evidence. So the fixture here is a hand-written MJCF whose every answer is
arithmetic anyone can redo: two spheres resting on the floor 100 mm apart
along Y, a mass above them, and one motor per sphere about the same Y axis.

The whole-body centre of mass, the moment of inertia about the contact line,
the gravity torque about it and the unstable eigenvalue are all stated below
as numbers before the tool is asked for them. The verdict is then exercised
on both sides of its one decision: a model whose motors dwarf the holding
torque is a control requirement, and the same model with small motors is a
design defect.
"""
import importlib.util
import json
import math
from pathlib import Path

import pytest

mujoco = pytest.importorskip('mujoco')

PATH = Path(__file__).resolve().parents[2] / 'docs/probes/ot8/runner/balance_diagnosis.py'
spec = importlib.util.spec_from_file_location('ot8_balance_diagnosis', PATH)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

#: The fixture, in metres. A sphere of radius R whose centre sits at z = R
#: touches the floor at z = 0, so both contacts land on the line y = +-0.05.
RADIUS = 0.1
HALF_TRACK = 0.05
BASE_MASS = 1.0
WHEEL_MASS = 0.1
#: The base's own centre of mass, in the base body's frame. The base body sits
#: at z = RADIUS, so this is 0.01 m off the contact line and 0.2 m above it.
BASE_COM = (0.01, 0.0, 0.1)
#: A sphere's principal inertia, 2/5 m r^2, written out so the sum below is
#: readable rather than derived twice.
WHEEL_INERTIA = 0.4 * WHEEL_MASS * RADIUS ** 2
BASE_INERTIA = (0.01, 0.02, 0.03)

TOTAL_MASS = BASE_MASS + 2 * WHEEL_MASS
#: (1.0 * 0.01) / 1.2 and (1.0 * 0.2 + 0.2 * 0.1) / 1.2
COM_X = BASE_MASS * BASE_COM[0] / TOTAL_MASS
COM_Z = (BASE_MASS * (RADIUS + BASE_COM[2]) + 2 * WHEEL_MASS * RADIUS) / TOTAL_MASS
#: Parallel axis about the Y line through (0, *, 0): each body's own Iyy plus
#: m times its squared distance from that line in the XZ plane.
INERTIA_Y = (
    BASE_INERTIA[1] + BASE_MASS * (BASE_COM[0] ** 2 + (RADIUS + BASE_COM[2]) ** 2)
    + 2 * (WHEEL_INERTIA + WHEEL_MASS * RADIUS ** 2)
)
GRAVITY = 9.81
HOLDING_NM = TOTAL_MASS * GRAVITY * COM_X
EIGENVALUE = math.sqrt(TOTAL_MASS * GRAVITY * COM_Z / INERTIA_Y)


def fixture(tmp_path, torque):
    """The fixture model, with ``torque`` N.m of limit on each wheel motor."""

    wheels = ''.join(
        f'<body name="wheel_{side}" pos="0 {sign * HALF_TRACK} 0">'
        f'<joint name="axle_{side}" type="hinge" axis="0 1 0"/>'
        f'<inertial pos="0 0 0" mass="{WHEEL_MASS}" '
        f'diaginertia="{WHEEL_INERTIA} {WHEEL_INERTIA} {WHEEL_INERTIA}"/>'
        f'<geom name="wheel_{side}/collision0" type="sphere" size="{RADIUS}"/>'
        '</body>'
        for side, sign in (('l', 1), ('r', -1))
    )
    motors = ''.join(
        f'<general name="axle_{side}/motor" joint="axle_{side}" forcelimited="true" '
        f'forcerange="-{torque} {torque}"/>'
        for side in ('l', 'r')
    )
    text = (
        '<mujoco model="fixture"><compiler angle="radian" autolimits="false"/>'
        '<size nkey="1"/><worldbody>'
        f'<geom name="{probe.FLOOR_GEOM}" size="0 0 0.1" type="plane"/>'
        f'<body name="base" pos="0 0 {RADIUS}">'
        f'<inertial pos="{BASE_COM[0]} {BASE_COM[1]} {BASE_COM[2]}" mass="{BASE_MASS}" '
        f'diaginertia="{BASE_INERTIA[0]} {BASE_INERTIA[1]} {BASE_INERTIA[2]}"/>'
        '<joint name="base/free" type="free"/>'
        f'{wheels}</body></worldbody>'
        f'<actuator>{motors}</actuator>'
        '<keyframe><key name="solved"/></keyframe></mujoco>'
    )
    path = tmp_path / 'fixture-model.xml'
    path.write_text(text, encoding='utf-8')
    return path


def measured(path):
    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    return model, data, probe.mechanism(model, data)


def test_two_contacts_are_a_line_not_a_polygon(tmp_path):
    _model, _data, facts = measured(fixture(tmp_path, 1.0))
    assert facts['support']['kind'] == 'line'
    assert facts['support']['distinct_points'] == 2
    assert facts['support']['span_mm'] == pytest.approx(2 * HALF_TRACK * 1000.0, abs=1e-6)
    # The line runs along Y, so the axis the machine topples about is Y and
    # the lever arm is measured along X.
    assert abs(facts['support']['direction'][1]) == pytest.approx(1.0, abs=1e-9)


def test_the_static_numbers_are_the_arithmetic(tmp_path):
    _model, _data, facts = measured(fixture(tmp_path, 1.0))
    assert facts['mass_kg'] == pytest.approx(TOTAL_MASS, rel=1e-12)
    assert abs(facts['lever_arm_mm']) == pytest.approx(COM_X * 1000.0, rel=1e-9)
    assert facts['height_above_support_mm'] == pytest.approx(COM_Z * 1000.0, rel=1e-9)
    assert facts['inertia_about_support_kg_m2'] == pytest.approx(INERTIA_Y, rel=1e-9)
    assert facts['holding_torque_nmm'] == pytest.approx(HOLDING_NM * 1000.0, rel=1e-6)
    assert facts['unstable_eigenvalue_per_s'] == pytest.approx(EIGENVALUE, rel=1e-6)
    assert facts['time_constant_s'] == pytest.approx(1.0 / EIGENVALUE, rel=1e-6)


def test_only_actuators_about_the_topple_axis_count(tmp_path):
    _model, _data, facts = measured(fixture(tmp_path, 1.0))
    assert facts['declared_torque_nmm'] == pytest.approx(2000.0, rel=1e-9)
    assert [row['actuator'] for row in facts['authority']['actuators']] == [
        'axle_l/motor', 'axle_r/motor']
    assert facts['authority']['ignored'] == []
    assert facts['torque_margin'] == pytest.approx(2.0 / HOLDING_NM, rel=1e-6)


def test_the_free_response_grows_at_the_predicted_rate(tmp_path):
    model, data, facts = measured(fixture(tmp_path, 1.0))
    replay = probe.replicate(model, data, seconds=1.0, fps=50)
    assert replay['tilt'][0]['tilt_degrees'] == pytest.approx(0.0, abs=1e-9)
    assert replay['final_tilt_degrees'] > 15.0
    # The eigenvalue is the rigid fixed-pivot idealisation; the model also
    # rolls on its contacts and pivots at its axles, so the measured
    # departure is the same exponential in the same rate class rather than
    # the same number. On the balancer it came in at 9.53 against 11.59; the
    # fixture's free-spinning wheels put it on the other side. What the check
    # is for is that the replay departs exponentially at that rate class, so
    # the fall is the model's own physics rather than an artefact.
    assert EIGENVALUE / 3.0 < replay['measured_growth_rate_per_s'] < 3.0 * EIGENVALUE


def test_a_torque_motor_is_commanded_zero_so_the_rollout_is_free(tmp_path):
    model, data, _facts = measured(fixture(tmp_path, 1.0))
    # The smoke's hold mode holds a position servo and nothing else; these
    # are plain torque motors, so the replay leaves ctrl where it found it.
    assert list(data.ctrl) == [0.0, 0.0]


def test_verdict_names_the_missing_controller_when_authority_is_there(tmp_path):
    model_path = fixture(tmp_path, 1.0)
    _model, _data, facts = measured(model_path)
    report = {'mechanism': facts,
              'smoke': {'components_pass': True, 'initial_pose_agrees': True}}
    answer = probe.verdict(report)
    assert answer['verdict'] == 'missing_feedback_control'
    assert any('no static margin' in reason for reason in answer['reasons'])


def test_verdict_names_the_design_when_the_motors_cannot_hold_it(tmp_path):
    #: 0.0981 N.m is what holding the fixture's own lean costs, so a motor
    #: pair at 0.05 N.m each is inside the margin and the design is the defect.
    _model, _data, facts = measured(fixture(tmp_path, 0.05))
    report = {'mechanism': facts,
              'smoke': {'components_pass': True, 'initial_pose_agrees': True}}
    answer = probe.verdict(report)
    assert answer['verdict'] == 'design_defect'
    assert facts['torque_margin'] < probe.AUTHORITY_MARGIN


def test_a_failing_exact_geometry_check_is_named_before_any_dynamics(tmp_path):
    _model, _data, facts = measured(fixture(tmp_path, 1.0))
    report = {'mechanism': facts,
              'smoke': {'components_pass': False, 'initial_pose_agrees': True}}
    assert probe.verdict(report)['verdict'] == 'geometry_mismatch'


def test_standing_depth_follows_the_load(tmp_path):
    compliance = probe.contact_compliance(fixture(tmp_path, 1.0))
    depths = [row['standing_depth_mm'] for row in compliance['loads']]
    assert depths == sorted(depths)
    assert depths[0] > 0.0
    assert depths[-1] > 2 * depths[0]
    # Every load is measured at the same pose, so the depths compare.
    tilts = [row['tilt_degrees'] for row in compliance['loads']]
    assert max(tilts) - min(tilts) < 1.0


def test_the_control_contract_is_the_task_and_the_instability(tmp_path):
    task = {
        'episode': {'control_hz': 50, 'control_interval_s': 0.02, 'episode_seconds': 8.0,
                    'reset_keyframe': 'solved'},
        'observations': [{'channels': ['a', 'b']}, {'channels': ['c']}],
        'actions': [{'actuator': 'axle_l/motor', 'low': -1.0, 'high': 1.0, 'unit': 'nmm'}],
        'termination': [{'expression': 'z', 'below': 75.25}],
    }
    contract = probe.control_contract(task, EIGENVALUE)
    assert contract['reads'] == ['a', 'b', 'c']
    assert contract['control_hz'] == 50
    assert contract['samples_per_e_fold'] == pytest.approx(1.0 / (EIGENVALUE * 0.02), rel=1e-9)
    assert contract['tilt_growth_per_interval'] == pytest.approx(math.exp(EIGENVALUE * 0.02), rel=1e-9)
    assert contract['must_hold'] == task['termination']


def test_the_report_is_one_json_document(tmp_path):
    model_path = fixture(tmp_path, 1.0)
    task_path = tmp_path / 'fixture-task.json'
    task_path.write_text(json.dumps({'episode': {'control_interval_s': 0.02}}), encoding='utf-8')
    smoke_path = tmp_path / 'smoke.json'
    smoke_path.write_text(json.dumps({'verdict': 'fail', 'mode': 'hold', 'seconds': 1.0,
                                      'failing': ['support: ...'],
                                      'checks': {'components': {'pass': True,
                                                                'initial_pose_agrees': True}}}),
                          encoding='utf-8')
    out = tmp_path / 'diagnosis.json'
    assert probe.main([str(model_path), '--task', str(task_path), '--smoke', str(smoke_path),
                       '--out', str(out)]) == 0
    report = json.loads(out.read_text())
    assert report['schema'] == 'ot8-balance-diagnosis-v1'
    assert report['verdict'] == 'missing_feedback_control'
    assert report['model']['sha256'] == probe.digest(model_path)
    assert report['smoke']['verdict'] == 'fail'
