# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ot9 per-seed reader, against answers written before it is run.

B3 is decided by this reader, so it is pinned first. Every fixture below is
a trace built from stated angles and heights -- a tilt about Y, sometimes
under a yaw about Z that must not count -- and every expected number is
written as a literal beside it: the peak, when it happened, the lowest base
height and when, and which bar rule fails.
"""
import importlib.util
import json
import math
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / 'docs/probes/ot9/runner/balance_eval.py'
spec = importlib.util.spec_from_file_location('ot9_balance_eval', PATH)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

BASE = 'comp_chassis'
IDENTITY = [0.0, 0.0, 0.0, 1.0]
POLICY_SHA = 'a' * 64
TASK_SHA = 'b' * 64


def _mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz]


def _about(axis, degrees):
    half = math.radians(degrees) / 2.0
    vector = [0.0, 0.0, 0.0]
    vector['xyz'.index(axis)] = math.sin(half)
    return vector + [math.cos(half)]


def _pose(tilt_deg, height_mm, yaw_deg=0.0):
    return {BASE: {'position_mm': [0.0, 0.0, height_mm],
                   'rotation_xyzw': _mul(_about('z', yaw_deg), _about('y', tilt_deg))}}


def _rollout(tmp_path, poses, *, steps, termination='', truncated=True, seed=0, model_sha):
    frames = [{'frame_index': 0, 'frame_kind': 'input', 'nominal_time_s': None,
               'component_placements': poses[0]}]
    for step, pose in enumerate(poses):
        frames.append({'frame_index': step + 1, 'frame_kind': 'solver_output',
                       'nominal_time_s': step * 0.02, 'component_placements': pose})
    trace = {
        'schema': 'cadex-assembly-simulation-trace-v1', 'frames': frames,
        'dynamics': {'control_hz': 50, 'steps_per_frame': 1, 'frames_per_second': 50},
        'policy': {'seed': seed, 'step_count': steps, 'termination': termination,
                   'terminated_step': None if truncated else steps, 'truncated': truncated,
                   'total_reward': 123.5, 'policy_sha256': POLICY_SHA,
                   'model_sha256': model_sha, 'task_sha256': TASK_SHA},
    }
    path = tmp_path / f'seed-{seed}' / 'assembly-simulation-trace.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace))
    return path


@pytest.fixture
def model(tmp_path):
    path = tmp_path / 'model.xml'
    path.write_text('<mujoco/>')
    return path


def _evaluate(trace, model, **kw):
    return reader.evaluate(trace, model, base=BASE, reference_xyzw=kw.pop('reference', IDENTITY), **kw)


def test_tilt_is_measured_from_the_reference_and_ignores_yaw():
    assert reader.tilt_degrees(_about('y', 25.0), IDENTITY) == pytest.approx(25.0)
    assert reader.tilt_degrees(_about('z', 170.0), IDENTITY) == pytest.approx(0.0, abs=1e-9)
    assert reader.tilt_degrees(_mul(_about('z', 60.0), _about('y', 40.0)), IDENTITY) == pytest.approx(40.0)
    lying = _about('x', 90.0)
    assert reader.tilt_degrees(lying, lying) == pytest.approx(0.0, abs=1e-6)
    assert reader.tilt_degrees(IDENTITY, lying) == pytest.approx(90.0)


def test_a_full_upright_episode_passes_with_its_stated_peak_and_low(tmp_path, model):
    # 401 frames: 2 deg under a 90 deg yaw throughout, except 12.5 deg at step
    # 137 (2.74 s) and a dip to 101.25 mm at step 250 (5.00 s).
    poses = [_pose(2.0, 107.5, yaw_deg=90.0) for _ in range(401)]
    poses[137] = _pose(12.5, 107.5, yaw_deg=90.0)
    poses[250] = _pose(2.0, 101.25, yaw_deg=90.0)
    trace = _rollout(tmp_path, poses, steps=400, model_sha=reader.digest(model))
    report = _evaluate(trace, model)
    assert report['peak_tilt_degrees'] == pytest.approx(12.5)
    assert report['peak_tilt_time_s'] == pytest.approx(2.74)
    assert report['min_chassis_height_mm'] == pytest.approx(101.25)
    assert report['min_chassis_height_time_s'] == pytest.approx(5.0)
    assert report['duration_s'] == pytest.approx(8.0)
    assert report['steps'] == 400 and report['termination'] == ''
    assert report['policy_sha256'] == POLICY_SHA and report['task_sha256'] == TASK_SHA
    assert report['failing'] == [] and report['class'] == 'completed' and report['pass'] is True


def test_a_fall_fails_on_every_rule_it_breaks(tmp_path, model):
    # 3 deg per step for 33 steps: 99 deg at 0.66 s; height 107.5 - 1.5 mm/step
    # reaches 58.0 mm at the last frame.
    poses = [_pose(3.0 * step, 107.5 - 1.5 * step) for step in range(34)]
    trace = _rollout(tmp_path, poses, steps=33, termination='fallen', truncated=False,
                     model_sha=reader.digest(model))
    report = _evaluate(trace, model)
    assert report['peak_tilt_degrees'] == pytest.approx(99.0)
    assert report['peak_tilt_time_s'] == pytest.approx(0.66)
    assert report['min_chassis_height_mm'] == pytest.approx(58.0)
    assert report['terminated_at_s'] == pytest.approx(0.66)
    assert report['pass'] is False and report['class'] == 'completed'
    assert report['failing'] == [
        'ran 33 steps, bar 400',
        'fallen fired',
        'did not end by truncation',
        'tilted 99.000 deg at 0.660 s (limit 30 deg)',
    ]


def test_thirty_degrees_is_inside_the_bar_and_just_over_is_not(tmp_path, model):
    at = [_pose(30.0, 107.5) for _ in range(401)]
    over = [_pose(30.01, 107.5) for _ in range(401)]
    sha = reader.digest(model)
    assert _evaluate(_rollout(tmp_path, at, steps=400, seed=1, model_sha=sha), model)['pass'] is True
    assert _evaluate(_rollout(tmp_path, over, steps=400, seed=2, model_sha=sha), model)['pass'] is False


def test_a_trace_on_another_model_or_task_is_void(tmp_path, model):
    poses = [_pose(1.0, 107.5) for _ in range(401)]
    stranger = _rollout(tmp_path, poses, steps=400, seed=3, model_sha='c' * 64)
    assert _evaluate(stranger, model)['class'] == 'void'
    ours = _rollout(tmp_path, poses, steps=400, seed=4, model_sha=reader.digest(model))
    report = _evaluate(ours, model, expect_task='d' * 64)
    assert report['class'] == 'void' and report['pass'] is False


def test_a_missing_frame_is_not_every_control_step(tmp_path, model):
    poses = [_pose(1.0, 107.5) for _ in range(401)]
    trace = _rollout(tmp_path, poses, steps=400, model_sha=reader.digest(model))
    raw = json.loads(trace.read_text())
    del raw['frames'][200]
    trace.write_text(json.dumps(raw))
    assert _evaluate(trace, model)['failing'] == ['400 frames for 400 steps; expected one per step plus reset']


def test_a_smoke_trace_reads_but_never_passes(tmp_path, model):
    run = tmp_path / 'smoke'
    run.mkdir()
    samples = [{'time_s': 0.02 * i, 'placements': _pose(t, h)}
               for i, (t, h) in enumerate([(0.0, 107.5), (45.0, 90.0), (102.0, 16.0), (101.0, 16.5)])]
    (run / 'smoke-trace.json').write_text(json.dumps(samples))
    (run / 'smoke.json').write_text(json.dumps({
        'frames_per_second': 50, 'simulated_seconds': 0.06,
        'model': {'sha256': reader.digest(model)}, 'task': {'sha256': TASK_SHA},
        'checks': {'termination': {'fired': [{'label': 'fallen', 'at_s': 0.02}]}}}))
    report = _evaluate(run / 'smoke-trace.json', model)
    assert report['dialect'] == 'smoke'
    assert report['peak_tilt_degrees'] == pytest.approx(102.0)
    assert report['peak_tilt_time_s'] == pytest.approx(0.04)
    assert report['final_tilt_degrees'] == pytest.approx(101.0)
    assert report['min_chassis_height_mm'] == pytest.approx(16.0)
    assert report['termination'] == 'fallen' and report['terminated_at_s'] == pytest.approx(0.02)
    assert report['failing'][0] == 'no policy: only a policy rollout can pass'
    assert report['pass'] is False


def test_the_candidate_needs_all_ten_contract_seeds_passing():
    def row(seed, ok=True, cls='completed'):
        return {'seed': seed, 'pass': ok and cls == 'completed', 'class': cls}

    assert reader.bar()['seeds'] == list(range(10))
    assert reader.candidate_verdict([row(s) for s in range(10)])['verdict'] == 'pass'
    nine = reader.candidate_verdict([row(s) for s in range(9)])
    assert nine['verdict'] == 'incomplete' and nine['missing'] == [9]
    one_fail = reader.candidate_verdict([row(s, ok=s != 6) for s in range(10)])
    assert one_fail['verdict'] == 'fail' and one_fail['failed'] == [6]
    assert reader.candidate_verdict([row(s, cls='void' if s == 2 else 'completed')
                                     for s in range(10)])['verdict'] == 'void'
    assert reader.candidate_verdict([row(s) for s in range(10)] + [row(3)])['verdict'] == 'incomplete'


def test_the_reference_is_the_models_solved_keyframe(tmp_path):
    pytest.importorskip('mujoco')
    # A free box whose solved keyframe lies it 90 deg about X.
    q = _about('x', 90.0)
    path = tmp_path / 'lying.xml'
    path.write_text(f'''<mujoco><worldbody>
      <body name="comp_chassis" pos="0 0 0.1"><joint name="free" type="free"/>
        <geom type="box" size="0.01 0.01 0.01"/></body></worldbody>
      <keyframe><key name="solved" qpos="0 0 0.1 {q[3]} {q[0]} {q[1]} {q[2]}"/></keyframe></mujoco>''')
    base, reference = reader.reference_attitude(path)
    assert base == 'comp_chassis'
    assert reference == pytest.approx(q)


def test_the_retained_no_policy_receipt_agrees_with_the_pins_and_with_g4():
    probes = PATH.parents[2]
    contract = json.loads((probes / 'ot9/contract.json').read_text())
    receipt = json.loads((probes / 'ot9/retained/r2-robin-no-policy.json').read_text())
    g4 = json.loads((probes / 'ot8/retained/g4-robin-diagnosis.json').read_text())
    pins, base = receipt['preparation']['pins_checked'], contract['baseline']
    for key in ('script_sha256', 'accepted_revision', 'accepted_attempt', 'accepted_digest', 'geometry_digest'):
        assert pins[key] == base[key]
    assert pins['mjcf_sha256'] == base['mjcf']['sha256'] == receipt['training_bundle']['mjcf']['sha256']
    assert pins['task_sha256'] == base['task']['sha256'] == receipt['training_bundle']['task']['sha256']
    assert receipt['training_bundle']['rebuilt_digest'] == base['accepted_digest']
    fall, smoke = receipt['no_policy_rollout'], g4['before']['smoke']
    fired = smoke['checks']['termination']['fired'][0]
    assert fall['reader']['termination'] == fired['label'] == 'fallen'
    assert fall['reader']['terminated_at_s'] == fired['at_s']
    assert fall['agreement_with_g4']['reader_height_at_0_66_s_mm'] == pytest.approx(fired['value'], abs=1e-9)
    assert fall['agreement_with_g4']['reader_tilt_at_1s_degrees'] == pytest.approx(
        smoke['checks']['support']['tilt_degrees'], abs=1e-9)
    assert fall['reader']['pass'] is False


def test_the_first_training_receipt_ran_what_it_planned_on_the_pins():
    probes = PATH.parents[2]
    contract = json.loads((probes / 'ot9/contract.json').read_text())
    receipt = json.loads((probes / 'ot9/retained/r3-robin-train-1.json').read_text())
    plan, ran = receipt['plan'], receipt['training']
    assert ran['bundle']['mjcf_sha256'] == contract['baseline']['mjcf']['sha256']
    assert ran['bundle']['task_sha256'] == contract['baseline']['task']['sha256']
    assert (ran['seed'], ran['iterations_run'], ran['envs']) == (
        plan['training_seed'], plan['settings']['iterations'], plan['settings']['envs'])
    assert plan['training_seed'] not in contract['evaluation_seeds']
    # The installed policy is the one the script names and the rollout ran.
    policy = ran['policy']['sha256']
    rollout = receipt['rollout_seed_0']
    assert rollout['reader']['policy_sha256'] == policy
    assert rollout['reader']['task_sha256'] == contract['baseline']['task']['sha256']
    assert rollout['layout_check']['solver_output'] == rollout['reader']['steps'] + 1 == 401
    # One seed is a diagnostic, never the bar.
    assert rollout['reader']['seed'] == 0 and 'NOT the frozen ten-seed' in rollout['note']


def test_the_first_ten_seed_evaluation_is_every_seed_on_one_reopened_policy():
    probes = PATH.parents[2]
    contract = json.loads((probes / 'ot9/contract.json').read_text())
    trained = json.loads((probes / 'ot9/retained/r3-robin-train-1.json').read_text())
    receipt = json.loads((probes / 'ot9/retained/r4-robin-eval-1.json').read_text())
    policy = trained['training']['policy']['sha256']
    mjcf, task = contract['baseline']['mjcf']['sha256'], contract['baseline']['task']['sha256']
    # B2's missing half: a fresh process rebuilt the installed revision to the same identity.
    reopen = receipt['reopen']
    installed = trained['installation']['policy_on']
    assert (reopen['accepted_revision'], reopen['accepted_digest']) == (
        installed['accepted_revision'], installed['digest'])
    assert reopen['policy_receipt']['policy_sha256'] == reopen['stored_policy_sha256'] == policy
    assert (reopen['policy_receipt']['model_sha256'], reopen['mjcf_sha256']) == (mjcf, mjcf)
    assert (reopen['policy_receipt']['task_sha256'], reopen['task_sha256']) == (task, task)
    assert reopen['policy_receipt']['witness_error'] < reopen['policy_receipt']['witness_tolerance']
    assert reopen['trace_sha256'] == trained['rollout_seed_0']['trace_sha256']
    # B3: the verdict is recomputed from the rows against the bar, never copied.
    evaluation, the_bar = receipt['evaluation'], contract['bar']
    rows = evaluation['seeds']
    assert [r['seed'] for r in rows] == contract['evaluation_seeds'] == list(range(10))
    for r in rows:
        assert (r['policy_sha256'], r['mjcf_sha256'], r['task_sha256']) == (policy, mjcf, task)
        assert r['class'] == 'completed' and not r['void']
        assert r['frames'] == r['steps'] + 1 == the_bar['steps'] + 1
        assert r['duration_s'] == the_bar['episode_seconds']
        assert r['termination'] != the_bar['forbidden_termination']
        ok = (r['truncated'] and not r['termination'] and r['steps'] == the_bar['steps']
              and r['peak_tilt_degrees'] <= the_bar['max_tilt_degrees'])
        assert r['pass'] is ok and (r['failing'] == []) is ok
    assert len({r['trace_sha256'] for r in rows}) == 10
    assert rows[0]['trace_sha256'] == trained['rollout_seed_0']['trace_sha256']
    assert reader.candidate_verdict(rows)['verdict'] == evaluation['candidate']['verdict'] == 'pass'
