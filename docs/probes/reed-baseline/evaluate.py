"""Evaluate retained Reed policies through the public CLI in an independent copy.

Run from the repository root; generated traces stay in the destination project.
The source project must have no active writer during the copy and evaluation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(root):
    return {str(p.relative_to(root)): sha(p) for p in root.rglob('*')
            if p.is_file() and '.git' not in p.relative_to(root).parts}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--run', action='append', help='Retained run to evaluate; repeatable.')
    parser.add_argument('--evidence-directory', default='baseline-seeds')
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    assert source != destination and source not in destination.parents
    before = manifest(source)
    shutil.copytree(source, destination)  # Refuse overwriting an existing project.
    assert Path(args.evidence_directory).name == args.evidence_directory
    evidence = destination / 'evidence' / args.evidence_directory
    evidence.mkdir()
    rows = []
    for name in args.run or ('probe3-checkpoint20', 'probe3-final'):
        assert Path(name).name == name
        script_path = source / 'runs' / name / 'script.py'
        if not script_path.is_file():
            script_path = source / 'evidence' / (name + '-script.py')
        script = script_path.read_text()
        assert script.count('seed=0)') == 1
        reference = json.loads((source / 'runs' / name / 'rollout' /
                                'assembly-simulation-trace.json').read_text())
        for seed in range(10):
            changed = evidence / f'{name}-seed{seed}.py'
            changed.write_text(script.replace('seed=0)', f'seed={seed})'))
            out = evidence / f'{name}-seed{seed}'
            command = ['./cadex', 'script', '--project', str(destination),
                       '--set', str(changed), '--out', str(out), '--json']
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            (out.with_suffix('.stdout.json')).write_text(result.stdout)
            (out.with_suffix('.stderr')).write_text(result.stderr)
            assert result.returncode == 0, result.stderr
            receipt = json.loads(result.stdout)
            assert receipt['ok'] and receipt['params']['policy_on'] == 1
            trace_path = out / 'assembly-simulation-trace.json'
            trace = json.loads(trace_path.read_text())
            policy = trace['policy']
            for key in ('policy_sha256', 'model_sha256', 'task_sha256'):
                assert policy[key] == reference['policy'][key], key
            assert policy['seed'] == seed
            assert not policy['truncated'] or trace['parameters']['end_time_s'] == 8
            if seed == 0:
                assert trace == reference, 'Seed zero must reproduce the retained trace'
            first, last = [f['component_placements']['torso_link']['position_mm']
                           for f in (trace['frames'][0], trace['frames'][-1])]
            row = {'policy': name, 'seed': seed, 'episode_limit_s': 8,
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
                   'trace_sha256': sha(trace_path),
                   'accepted_revision': receipt['accepted_revision']}
            rows.append(row)
            print(json.dumps(row), flush=True)
    assert manifest(source) == before, 'Source project changed'
    summary = {'schema': 'reed-baseline-evaluation-v1', 'seeds': list(range(10)),
               'episode_limit_s': 8, 'source_unchanged': True,
               'seed_zero_traces_reproduced': True, 'rows': rows}
    (evidence / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
