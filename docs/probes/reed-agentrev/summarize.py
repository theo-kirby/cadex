"""Compact, path-free evidence for the product-agent shin55 revision experiment.

usage: python3 docs/probes/reed-agentrev/summarize.py PROJECT [SEEDS_PROJECT] > evidence.json
Reads only retained project-local receipts; never trains, renders or serves.
"""
import json
import statistics
import sys
from pathlib import Path

project = Path(sys.argv[1]).resolve()
seeds = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
ev = project / 'evidence'


def read(path):
    return json.loads(path.read_text()) if path.is_file() else None


agent = read(ev / 'agentrev-agent.json') or {}
result = read(ev / 'shin55-experiment-result.json') or {}
observe = read(ev / 'shin55-observe.json') or {}
mid = result.get('intermediate') or read(ev / 'shin55-checkpoint20-publication.json') or {}
final = result.get('final') or {}
out = {
    'schema': 'reed-agentrev-evidence-v1',
    'project': project.name,
    'authorship': {
        'model': agent.get('model'), 'ok': agent.get('ok'), 'error': agent.get('error'),
        'accepted_revision': agent.get('accepted_revision'), 'digest': agent.get('digest'),
        'changed_parameter': {'shin_len': {'before': 80.0, 'after': (agent.get('params') or {}).get('shin_len')}},
        'policy_on_after_turn': (agent.get('params') or {}).get('policy_on'),
        'project_decision': 'ADR-007 in the project DECISIONS.md; docs/design-specs.md carries the shin-length entry',
    },
    'training': {
        'run': result.get('run'), 'accepted_revision': result.get('accepted_revision'), 'digest': result.get('digest'),
        'geometry': result.get('geometry'), 'training_exit': result.get('training_exit'),
        'training_wall_seconds': result.get('training_wall_seconds'), 'trainer_final': result.get('trainer_final'),
        'memory': result.get('memory'), 'preserved_earlier_records': sorted((result.get('preserved_records') or {}).keys()),
    },
    'persistent_dashboard_during_training': {
        'url': observe.get('url'), 'ok': observe.get('ok'), 'project_name': observe.get('project_name'),
        'default_view_on_fresh_visit': observe.get('default_view_kind'), 'current_run_label': observe.get('current_run_label'),
        'view_relation': observe.get('view_relation'), 'model_state': observe.get('model_state'), 'orbit_zoom': observe.get('orbit_zoom'),
        'page_iterations': observe.get('page_iterations'), 'reload_count': observe.get('reload_count'),
        'committed_to_page_s': {k: v['committed_to_page_s'] for k, v in (observe.get('first_seen') or {}).items()},
    },
    'checkpoint_video_while_training': {k: mid.get(k) for k in ('run', 'before', 'after', 'trainer_active_after_browser', 'browser_check_exit', 'render_seconds', 'render_before', 'render_after', 'video', 'policy_sha256', 'overhead', 'failure')},
    'final_video': {k: final.get(k) for k in ('run', 'browser_check_exit', 'render_seconds', 'video', 'policy_sha256')},
    'witness': {name: {k: (d.get('witness') or {}).get(k) for k in ('witness_error', 'witness_tolerance')} for name, d in (('checkpoint20', mid), ('final', final))},
}
for name in ('shin55-checkpoint20', 'shin55-final'):
    check = read(ev / (name + '-check.json'))
    if check:
        out.setdefault('browser_video_checks', {})[name] = check
for key, name in (('persistent_dashboard_after_training', 'shin55-operator-final.json'),
                  ('persistent_dashboard_after_restart', 'shin55-operator-restart.json')):
    operator = read(ev / name)
    if operator:
        out[key] = operator
if seeds is not None:
    summary = read(seeds / 'evidence' / 'shin55-seeds' / 'summary.json')
    if summary:
        rows = summary['rows']
        out['ten_seed_evaluation'] = {
            'seeds_project': seeds.name, 'seeds': summary['seeds'], 'episode_limit_s': summary['episode_limit_s'],
            'source_unchanged': summary['source_unchanged'], 'seed_zero_trace_reproduced': summary['seed_zero_traces_reproduced'],
            'falls': sum(r['fell'] for r in rows), 'survivors': sum(r['time_limit_reached'] for r in rows),
            'mean_observed_s': round(statistics.mean(r['observed_s'] for r in rows), 3),
            'mean_forward_displacement_mm': round(statistics.mean(r['displacement_mm'][0] for r in rows), 3),
            'observed_s': [r['observed_s'] for r in rows],
            'forward_displacement_mm': [round(r['displacement_mm'][0], 3) for r in rows],
            'policy_sha256': rows[0]['policy_sha256'], 'model_sha256': rows[0]['model_sha256'], 'task_sha256': rows[0]['task_sha256'],
        }
print(json.dumps(out, indent=2))
