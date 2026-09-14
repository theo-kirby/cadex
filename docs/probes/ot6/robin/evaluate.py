# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Evaluate one of Robin's retained policies over the declared seed set, in a
fresh scratch project, via the public CLI (D7, ADR-328).

Usage: pixi run python evaluate.py SOURCE SCRATCH RUN [SEEDS] [BASE]
This is the Finch evaluator (``../finch/evaluate.py``) with Robin's facts: the
floating base is the chassis (BASE defaults to ``comp_chassis``, the trace's key for the component the script names ``chassis``, matched as a
prefix of the trace's component key), the fall threshold is read from the
run's own retained task bundle rather than recomputed from limb lengths, and
each seed also reports the chassis pitch -- the balance measurement the task
penalises -- as the largest |pitch| over the episode and the pitch at its
last frame, from the retained trace's chassis quaternion. The operator's
project is read-only. Only the named immutable run and its content-verified
policy asset supply inputs; today's accepted values are unused. SEEDS
(default 10) evaluates rollout seeds 0..SEEDS-1 through the script's
``rollout_seed`` parameter.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

source, scratch = map(lambda p: Path(p).resolve(), sys.argv[1:3])
name = sys.argv[3]
seeds = int(sys.argv[4]) if len(sys.argv) > 4 else 10
base = sys.argv[5] if len(sys.argv) > 5 else 'comp_chassis'
assert Path(name).name == name and not scratch.exists()
assert source != scratch and source not in scratch.parents
run = source / 'runs' / name
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
before = {str(p.relative_to(run)): sha(p) for p in run.rglob('*') if p.is_file()}
record = read(run / 'run.json')
reference = read(run / 'rollout/assembly-simulation-trace.json')
policy = reference['policy']
script = (run / record['artifacts']['script']).read_text()
# Bake the RECORDED effective parameters into the scratch script defaults.
for key, value in record['params']['values'].items():
    script, count = re.subn(r'\b' + re.escape(key) + r'=num\([^,]+,',
                            key + '=num(' + repr(value) + ',', script)
    assert count == 1, key
assert record['params']['values']['policy_on'] == 1
values = record['params']['values']
episode_s = values['episode_steps'] / values['control_hz']; hz = values['control_hz']
task = read(run / record['artifacts']['task_bundle'])
(fell_rule,) = [t for t in task['termination'] if t['expression'] == 'chassis_z' and t['below'] is not None]
fall_below_mm = fell_rule['below']
asset = re.search(r'weights="([^"]+)"', script).group(1)
assert Path(asset).name == asset
asset_path = source / 'assets' / asset
assert sha(asset_path) == policy['policy_sha256']
scratch.mkdir(parents=True)
evidence = scratch / 'evidence'; evidence.mkdir()


def pitch_degrees(rotation_xyzw):
    """Rotation about the lateral (Y) axis from the chassis quaternion -- the
    expression the task's reward penalises: asin(2*(qw*qy - qz*qx))."""
    qx, qy, qz, qw = rotation_xyzw
    return math.degrees(math.asin(max(-1.0, min(1.0, 2.0 * (qw * qy - qz * qx)))))


def cli(label, *args):
    r = subprocess.run(['./cadex', '--project', str(scratch), *map(str, args), '--json'],
                       capture_output=True, text=True, timeout=180)
    (evidence / (label + '.json')).write_text(r.stdout)
    (evidence / (label + '.stderr')).write_text(r.stderr)
    assert r.returncode == 0, (label, r.stderr, r.stdout[-1000:])
    result = json.loads(r.stdout); assert result['ok']
    return result

cli('asset', 'asset', '--put', asset_path, '--name', asset)
rows = []
assert 'rollout_seed' in record['params']['values']
for seed in range(seeds):
    path = evidence / f'seed{seed}.py'
    seeded, count = re.subn(r'\brollout_seed=num\([^,]+,', f'rollout_seed=num({float(seed)!r},', script)
    assert count == 1
    path.write_text(seeded)
    out = evidence / f'seed{seed}'
    envelope = cli(f'seed{seed}', 'script', '--set', path, '--out', out)
    trace_path = out / 'assembly-simulation-trace.json'
    trace = read(trace_path); pol = trace['policy']
    for key in ('policy_sha256', 'model_sha256', 'task_sha256'):
        assert pol[key] == policy[key], (name, seed, key)
    assert pol['seed'] == seed
    assert trace['parameters']['end_time_s'] <= episode_s + 1e-9
    assert abs(trace['parameters']['end_time_s'] - pol['step_count'] / hz) < 1e-9
    if seed == 0:
        assert trace == reference, 'Seed zero must reproduce retained trace exactly'
    (body,) = [k for k in trace['frames'][0]['component_placements'] if k.startswith(base)]
    placements = [f['component_placements'][body] for f in trace['frames']]
    first, last = placements[0]['position_mm'], placements[-1]['position_mm']
    pitches = [pitch_degrees(pl['rotation_xyzw']) for pl in placements]
    rows.append(dict(run=name, seed=seed, base=body,
                     displacement_x_mm=last[0]-first[0], survival_s=trace['parameters']['end_time_s'],
                     max_abs_pitch_deg=max(abs(x) for x in pitches), final_pitch_deg=pitches[-1],
                     final_height_mm=last[2],
                     # Robin's one termination rule (chassis_z below the threshold) is unlabelled, so the trace
                     # names it 'termination' rather than 'fell': a fall is any termination that is not the time limit.
                     fell=pol['termination'] is not None and not pol['truncated'], termination=pol['termination'],
                     truncated=pol['truncated'], step_count=pol['step_count'], total_reward=pol['total_reward'],
                     policy_sha256=pol['policy_sha256'], model_sha256=pol['model_sha256'],
                     task_sha256=pol['task_sha256'], trace_sha256=sha(trace_path)))
    print(json.dumps(rows[-1]), flush=True)
assert {str(p.relative_to(run)): sha(p) for p in run.rglob('*') if p.is_file()} == before
assert sha(asset_path) == policy['policy_sha256']
result = dict(schema='robin-common-seeds-v1', run=name, seeds=list(range(seeds)),
              episode_seconds=episode_s, control_hz=hz, fall_below_mm=fall_below_mm,
              fall_below_source='the run\'s retained task bundle, termination on chassis_z',
              source_run_unchanged=True,
              seed_zero_trace_identical=True, rows=rows)
(evidence / 'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
