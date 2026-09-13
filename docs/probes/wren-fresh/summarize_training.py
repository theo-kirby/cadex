"""Write compact training-experiment evidence; retain raw outputs inside the project.

usage: summarize_training.py PROJECT RUN [SCHEMA]   (SCHEMA defaults to the Wren receipt schema)
Project-agnostic: the torso is the one traced component whose output name contains
``torso`` (``c_torso`` on Wren, ``torso_link`` on Lark).
"""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
name = sys.argv[2]
schema = sys.argv[3] if len(sys.argv) > 3 else 'wren-training-evidence-v1'
evidence = root / 'evidence'


def read(path):
    return json.loads(path.read_text())


def portable(value):
    if isinstance(value, dict):
        return {k: portable(v) for k, v in value.items() if k != 'url'}
    if isinstance(value, list):
        return [portable(v) for v in value]
    if isinstance(value, str):
        return value.replace(str(root.resolve()), '<project>')
    return value


result = read(evidence / (name + '-experiment-result.json'))
for phase in ('intermediate', 'final'):
    entry = result[phase]
    witness = entry.get('witness', {})
    entry['witness'] = {key: witness.get(key) for key in
                        ('witness_error', 'witness_tolerance', 'model_sha256', 'task_sha256')}
result['schema'] = schema
result['project'] = root.name
result['resource_bound'] = read(evidence / (name + '-resource-bound.json'))
if (evidence / (name + '-start-browser.json')).exists():
    result['start_browser'] = read(evidence / (name + '-start-browser.json'))
if (evidence / (name + '-active-after-video.json')).exists():
    result['active_after_video'] = read(evidence / (name + '-active-after-video.json'))
result['live_browser'] = read(evidence / (name + '-observe.json'))
result['policies'] = {}
for run_name in (name + '-checkpoint20', name + '-final'):
    run = root / 'runs' / run_name
    trace_path = run / 'rollout/assembly-simulation-trace.json'
    trace = read(trace_path)
    policy = trace['policy']
    (torso,) = [k for k in trace['frames'][0]['component_placements'] if 'torso' in k]
    first, last = [f['component_placements'][torso]['position_mm']
                   for f in (trace['frames'][0], trace['frames'][-1])]
    result['policies'][run_name] = {
        'browser': read(evidence / (run_name + '-check.json')),
        'video': read(run / 'video.json')['videos'][0],
        'episode_limit_s': 8,
        'seed': policy['seed'],
        'observed_s': trace['parameters']['end_time_s'],
        'fell': policy['termination'] == 'fell',
        'termination': policy['termination'],
        'time_limit_reached': policy['truncated'],
        'step_count': policy['step_count'],
        'displacement_mm': [b - a for a, b in zip(first, last)],
        'total_reward': policy['total_reward'],
        'policy_sha256': policy['policy_sha256'],
        'model_sha256': policy['model_sha256'],
        'task_sha256': policy['task_sha256'],
        'trace_sha256': hashlib.sha256(trace_path.read_bytes()).hexdigest(),
    }
print(json.dumps(portable(result), indent=2))
