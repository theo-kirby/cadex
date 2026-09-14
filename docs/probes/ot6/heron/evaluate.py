# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Evaluate one of Heron's retained policies over the declared seed set, in a
fresh scratch project, via the public CLI (D8, ADR-328).

Usage: pixi run python evaluate.py SOURCE SCRATCH RUN [SEEDS] [TIP]
This is the Robin evaluator (``../robin/evaluate.py``) with Heron's facts: the
measured body is the forearm, whose component frame the script authored AT
THE TIP (project ADR-003), so its ``position_mm`` in every retained frame is
the tip; the target and tolerance are the run's own recorded effective
parameters (``target_x``, ``target_z``, ``reach_tol``); the termination rule
is read from the retained task bundle (``tip_z`` below ``tip_floor``). Each
seed reports the reach error at episode end, the largest and mean error over
the final second, the smallest error over the episode and when the tip first
came within tolerance; success is the script's own stated bar, within
``reach_tol`` at episode end AND over the whole final second. The operator's
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
tip_component = sys.argv[5] if len(sys.argv) > 5 else 'comp_forearm'
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
target = (values['target_x'], 0.0, values['target_z']); tol = values['reach_tol']
task = read(run / record['artifacts']['task_bundle'])
(floor_rule,) = [t for t in task['termination'] if t['expression'] == 'tip_z' and t['below'] is not None]
tip_floor_mm = floor_rule['below']
assert tip_floor_mm == values['tip_floor']
asset = re.search(r'weights="([^"]+)"', script).group(1)
assert Path(asset).name == asset
asset_path = source / 'assets' / asset
assert sha(asset_path) == policy['policy_sha256']
scratch.mkdir(parents=True)
evidence = scratch / 'evidence'; evidence.mkdir()


def error_mm(position_mm):
    return math.dist(position_mm, target)


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
    end_s = trace['parameters']['end_time_s']
    assert end_s <= episode_s + 1e-9
    assert abs(end_s - pol['step_count'] / hz) < 1e-9
    if seed == 0:
        assert trace == reference, 'Seed zero must reproduce retained trace exactly'
    (body,) = [k for k in trace['frames'][0]['component_placements'] if k.startswith(tip_component)]
    # Timed frames only: the trace's untimed input frame is the declared placement before the first step.
    timed = [(f['nominal_time_s'], f['component_placements'][body]['position_mm']) for f in trace['frames'] if f['nominal_time_s'] is not None]
    assert timed and abs(timed[-1][0] - end_s) < 1e-6, (timed[-1][0], end_s)
    errors = [(t, error_mm(pos)) for t, pos in timed]
    final_second = [e for t, e in errors if t >= end_s - 1.0 - 1e-9]
    within = [t for t, e in errors if e <= tol]
    end_error = errors[-1][1]
    terminated = pol['terminated_step'] is not None and not pol['truncated']
    rows.append(dict(run=name, seed=seed, tip=body, target_mm=list(target), reach_tol_mm=tol,
                     tip_start_mm=[round(x, 3) for x in timed[0][1]], tip_end_mm=[round(x, 3) for x in timed[-1][1]],
                     end_error_mm=end_error, final_second_max_error_mm=max(final_second), final_second_mean_error_mm=sum(final_second) / len(final_second),
                     min_error_mm=min(e for _, e in errors), first_within_tol_s=within[0] if within else None,
                     success=(not terminated) and end_error <= tol and max(final_second) <= tol,
                     survival_s=end_s, terminated=terminated, termination=pol['termination'], terminated_step=pol['terminated_step'],
                     truncated=pol['truncated'], step_count=pol['step_count'], total_reward=pol['total_reward'],
                     policy_sha256=pol['policy_sha256'], model_sha256=pol['model_sha256'],
                     task_sha256=pol['task_sha256'], trace_sha256=sha(trace_path)))
    print(json.dumps(rows[-1]), flush=True)
assert {str(p.relative_to(run)): sha(p) for p in run.rglob('*') if p.is_file()} == before
assert sha(asset_path) == policy['policy_sha256']
result = dict(schema='heron-reach-seeds-v1', run=name, seeds=list(range(seeds)),
              episode_seconds=episode_s, control_hz=hz, target_mm=list(target), reach_tol_mm=tol, tip_floor_mm=tip_floor_mm,
              tip_source='the forearm component frame, authored at the tip (project ADR-003)',
              tip_floor_source='the run\'s retained task bundle, termination on tip_z',
              success_rule='not terminated, end error <= reach_tol, and every error over the final second <= reach_tol',
              source_run_unchanged=True,
              seed_zero_trace_identical=True, rows=rows)
(evidence / 'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
