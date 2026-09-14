# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Evaluate one of Finch's retained policies over the declared seed set, in a
fresh scratch project, via the public CLI (D6, ADR-328).

Usage: pixi run python evaluate.py SOURCE SCRATCH RUN [SEEDS] [BASE]
This is the Wren/Lark evaluator (``../../wren-fresh/compare.py``) with the
base named rather than found by the word "torso": Finch's floating base is
``pelvis_link`` (BASE defaults to ``pelvis``), and the episode length and
control rate are read from the run's recorded parameters instead of being
assumed to be 8 s at 50 Hz. The operator's project is read-only. Only the
named immutable run and its content-verified policy asset supply inputs;
today's accepted values are unused. SEEDS (default 10) evaluates rollout
seeds 0..SEEDS-1 through the script's ``rollout_seed`` parameter.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

source, scratch = map(lambda p: Path(p).resolve(), sys.argv[1:3])
name = sys.argv[3]
seeds = int(sys.argv[4]) if len(sys.argv) > 4 else 10
base = sys.argv[5] if len(sys.argv) > 5 else 'pelvis'
assert Path(name).name == name and not scratch.exists()
assert source != scratch and source not in scratch.parents
run = source / 'runs' / name
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
before = {str(p.relative_to(run)): sha(p) for p in run.rglob('*') if p.is_file()}
record = read(run / 'run.json')
reference = read(run / 'rollout/assembly-simulation-trace.json')
policy = reference['policy']
# A run published in place after training (publish_retry.py) keeps its training
# script beside the playback one; the record names which script declared the
# policy the retained trace actually ran.
script = (run / record['artifacts']['script']).read_text()
# Bake the RECORDED effective parameters into the scratch script defaults.
# This avoids inheriting today's foot dimension or disabled-policy setting.
for key, value in record['params']['values'].items():
    script, count = re.subn(r'\b' + re.escape(key) + r'=num\([^,]+,',
                            key + '=num(' + repr(value) + ',', script)
    assert count == 1, key
assert record['params']['values']['policy_on'] == 1
values = record['params']['values']
episode_s = values['episode_steps'] / values['control_hz']; hz = values['control_hz']
asset = re.search(r'weights="([^"]+)"', script).group(1)
assert Path(asset).name == asset
asset_path = source / 'assets' / asset
assert sha(asset_path) == policy['policy_sha256']
scratch.mkdir(parents=True)
evidence = scratch / 'evidence'; evidence.mkdir()

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
seeded_by_param = 'rollout_seed' in record['params']['values']
assert seeded_by_param or script.count('seed=0)') == 1
for seed in range(seeds):
    path = evidence / f'seed{seed}.py'
    if seeded_by_param:
        seeded, count = re.subn(r'\brollout_seed=num\([^,]+,', f'rollout_seed=num({float(seed)!r},', script)
        assert count == 1
    else:
        seeded = script.replace('seed=0)', f'seed={seed})')
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
    (torso,) = [k for k in trace['frames'][0]['component_placements'] if k.startswith(base)]
    first, last = [f['component_placements'][torso]['position_mm']
                   for f in (trace['frames'][0], trace['frames'][-1])]
    rows.append(dict(run=name, seed=seed, base=torso,
                     displacement_x_mm=last[0]-first[0], survival_s=trace['parameters']['end_time_s'],
                     fell=pol['termination']=='fell', termination=pol['termination'],
                     truncated=pol['truncated'], step_count=pol['step_count'], total_reward=pol['total_reward'],
                     policy_sha256=pol['policy_sha256'], model_sha256=pol['model_sha256'],
                     task_sha256=pol['task_sha256'], trace_sha256=sha(trace_path)))
    print(json.dumps(rows[-1]), flush=True)
assert {str(p.relative_to(run)): sha(p) for p in run.rglob('*') if p.is_file()} == before
assert sha(asset_path) == policy['policy_sha256']
result = dict(schema='finch-common-seeds-v1', run=name, seeds=list(range(seeds)),
              episode_seconds=episode_s, control_hz=hz, fall_below_mm=values['fall_frac'] * (values['thigh_len'] + values['shin_len']),
              source_run_unchanged=True,
              seed_zero_trace_identical=True, rows=rows)
(evidence / 'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
