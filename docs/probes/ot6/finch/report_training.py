# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Write the compact D6 receipt for one bounded Finch training run.

usage: pixi run python report_training.py PROJECT RUN URL EVAL_ROOT OUT_DIR
Reads what the driver (train.py), the evaluator (evaluate.py, its scratch
projects under EVAL_ROOT as <project>-eval-<RUN>-{c,f}) and the persistent
dashboard already produced; computes nothing about the policy itself. Writes
OUT_DIR/training.json (under the charter's 16 KB cap) and one decoded frame
per retained video beside it (under 200 KB each), and copies each scratch
evaluation's evidence into the project so the receipt's numbers stay
reproducible from project-local files. Full telemetry, traces, videos and
logs stay in the project directory and are cited by path and digest.
"""
import hashlib, json, shutil, statistics, subprocess, sys, urllib.request
from pathlib import Path
from cadex_cli.review_server import default_run

project = Path(sys.argv[1]).resolve(); run = sys.argv[2]; url = sys.argv[3].rstrip('/')
eval_root = Path(sys.argv[4]).resolve(); out = Path(sys.argv[5]).resolve()
ev = project / 'evidence'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
portable = lambda s: s.replace(str(project), '<project>').replace(str(Path.home()), '<home>')

result = read(ev / (run + '-experiment-result.json'))
progress = read(project / 'runs' / run / 'train/progress.json')
timeline = read(ev / (run + '-timeline.json'))
bound = read(ev / (run + '-resource-bound.json'))
observe = read(ev / (run + '-observe.json'))
record = read(project / 'runs' / run / 'run.json')


def playback(phase, name, eval_dir):
    entry = result[phase]
    r = project / 'runs' / name
    trace_path = r / 'rollout/assembly-simulation-trace.json'
    trace = read(trace_path); pol = trace['policy']
    (base,) = [k for k in trace['frames'][0]['component_placements'] if k.startswith('pelvis')]
    first, last = [f['component_placements'][base]['position_mm'] for f in (trace['frames'][0], trace['frames'][-1])]
    video = read(r / 'video.json')['videos'][0]
    check = read(ev / (name + ('-recheck' if phase == 'intermediate' else '') + '-check.json'))
    comparison = read(eval_dir / 'evidence/comparison.json')
    keep = project / 'evidence' / ('comparison-' + run) / eval_dir.name
    if not keep.exists():
        shutil.copytree(eval_dir / 'evidence', keep)
    rows = comparison['rows']
    assert rows[0]['policy_sha256'] == pol['policy_sha256'] == video['policy_sha256'] == entry['policy_sha256']
    assert comparison['seed_zero_trace_identical'] and comparison['source_run_unchanged']
    movie = r / video['path']
    assert sha(movie) == video['sha256'], movie
    frame = out / ('video-' + name + '.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(video['sim_seconds'] / 2), '-i', str(movie),
                    '-frames:v', '1', '-vf', 'scale=640:-1', str(frame)], check=True)
    assert frame.stat().st_size <= 200 * 1024, frame.stat().st_size
    return {
        'run': name, 'playback_revision': check.get('view_revision') or record.get('accepted_revision'),
        'policy_sha256': pol['policy_sha256'], 'model_sha256': pol['model_sha256'], 'task_sha256': pol['task_sha256'],
        'trace_sha256': sha(trace_path), 'seed': pol['seed'], 'step_count': pol['step_count'],
        'observed_s': trace['parameters']['end_time_s'], 'termination': pol['termination'], 'fell': pol['termination'] == 'fell',
        'time_limit_reached': pol['truncated'], 'total_reward': pol['total_reward'],
        'pelvis_displacement_mm': [round(b - a, 3) for a, b in zip(first, last)],
        'witness': {k: entry['witness'].get(k) for k in ('witness_error', 'witness_tolerance')},
        'trainer_iterations_before_after': [entry['before'], entry['after']], 'trainer_active_after_browser': entry['trainer_active_after_browser'],
        'browser_check_exit': entry['browser_check_exit'], 'render_seconds': entry['render_seconds'],
        'video': {k: video.get(k) for k in ('path', 'sha256', 'frames', 'fps', 'duration_seconds', 'sim_seconds', 'style', 'renderer', 'width', 'height', 'showing', 'accepted_revision')},
        'video_frame': {'png': frame.name, 'sha256': sha(frame), 'bytes': frame.stat().st_size, 'at_sim_s': video['sim_seconds'] / 2},
        'browser': {k: check.get(k) for k in ('fresh_selection', 'is_default', 'expected_default', 'historical_selection', 'returned_to_current', 'decoded_frames', 'download_sha256', 'style', 'components')},
        'seeds': {
            'schema': comparison['schema'], 'seeds': comparison['seeds'], 'episode_seconds': comparison['episode_seconds'], 'control_hz': comparison['control_hz'],
            'fall_below_mm': comparison['fall_below_mm'],
            'displacement_x_mm': {'mean': round(statistics.mean(r['displacement_x_mm'] for r in rows), 2), 'min': round(min(r['displacement_x_mm'] for r in rows), 2), 'max': round(max(r['displacement_x_mm'] for r in rows), 2)},
            'survival_s': {'mean': round(statistics.mean(r['survival_s'] for r in rows), 3), 'min': min(r['survival_s'] for r in rows), 'max': max(r['survival_s'] for r in rows)},
            'falls': sum(1 for r in rows if r['fell']), 'stood_full_episode': sum(1 for r in rows if not r['fell'] and r['truncated']),
            'mean_total_reward': round(statistics.mean(r['total_reward'] for r in rows), 2),
            'per_seed': [{'seed': r['seed'], 'dx_mm': round(r['displacement_x_mm'], 1), 'survival_s': r['survival_s'], 'fell': r['fell']} for r in rows],
            'evidence': portable(str(keep)),
        },
    }


def intervals_summary(lo, hi):
    rows = [round(b['updated_at'] - a['updated_at'], 3) for a, b in zip(timeline, timeline[1:])
            if a['updated_at'] and b['updated_at'] and a['updated_at'] >= lo and b['updated_at'] <= hi]
    return {'count': len(rows), 'median_s': round(statistics.median(rows), 3) if rows else None, 'max_s': max(rows, default=None)}


mid = result['intermediate']
if 'failure' in mid:
    # The driver's own checkpoint publication failed at the video render; the hand-rendered
    # publication on the fixed recorder, made while the trainer was active, stands in for it.
    manual = read(ev / (run + '-checkpoint20-manual-publication.json'))
    manual['driver_failure'] = mid['failure']
    mid = result['intermediate'] = manual
pairs = [(a, b) for a, b in zip(timeline, timeline[1:]) if a['updated_at'] and b['updated_at']]
boundary = lambda a, b: a['iteration'] % 20 in (0, 19) or b['iteration'] % 20 == 19
plain = sorted(round(b['updated_at'] - a['updated_at'], 3) for a, b in pairs if not boundary(a, b))
api = json.load(urllib.request.urlopen(url + '/api/project', timeout=10))
curve = [{'iteration': s['iteration'], 'reward_per_step': round(s['reward_per_step'], 4) if s['reward_per_step'] is not None else None,
          'episode_steps': s['episode_steps']} for s in timeline if s['iteration'] is not None and (s['iteration'] % 20 == 19 or s['iteration'] == 0)]
receipt = {
    'schema': 'finch-training-evidence-v1', 'project': project.name, 'run': run, 'operator_url_source': 'environment (private address, not committed)',
    'accepted_revision': result['accepted_revision'], 'digest': result['digest'], 'geometry': result['geometry'],
    'task': {k: record['params']['values'][k] for k in ('episode_steps', 'control_hz', 'fall_frac', 'thigh_len', 'shin_len')},
    'fall_below_mm': record['params']['values']['fall_frac'] * (record['params']['values']['thigh_len'] + record['params']['values']['shin_len']),
    'requested': record['requested'], 'trainer_exit': result['training_exit'], 'training_wall_seconds': result['training_wall_seconds'],
    'trainer_final': result['trainer_final'], 'best': {'iteration': progress['best_iteration'], 'reward_per_step': progress['best_reward_per_step']},
    'reward_curve_every_20': curve, 'memory': result['memory'], 'resource_bound': bound,
    'live_browser': {'persistent_server': observe['persistent_server'], 'default_view_kind': observe.get('default_view_kind'), 'model_components': observe.get('model_components'),
                     'reload_count': observe.get('reload_count'), 'samples': len(observe.get('samples', [])),
                     'first_seen_max_committed_to_page_s': max((x['committed_to_page_s'] for x in observe.get('first_seen', {}).values()), default=None),
                     'first_seen_count': len(observe.get('first_seen', {}))},
    'observer_exit': result['observer_exit'],
    'update_intervals': {'note': 'every trainer-committed update interval over the whole run; boundary = the compile at update 0 and each checkpoint step (every 20th update)',
                         'count': len(pairs), 'plain': {'count': len(plain), 'median_s': statistics.median(plain), 'min_s': plain[0], 'max_s': plain[-1]},
                         'boundary': [{'iteration': b['iteration'], 'seconds': round(b['updated_at'] - a['updated_at'], 1)} for a, b in pairs if boundary(a, b) and b['updated_at'] - a['updated_at'] > 10],
                         'concurrent_loads_during_run': ['checkpoint rollout and record', 'one checkpoint video render (3.5 s)', 'two persistent-dashboard browser checks', 'the 14-test cli/tests/test_video.py suite']},
    'checkpoint_publication': {'driver_failure': mid.get('driver_failure'), 'note': mid.get('note')},
    'render_overhead': {'note': mid['overhead']['note'], **{k: mid['overhead'][k] for k in ('before_window', 'during_window', 'after_window')},
                        'concurrent_renders': 1, 'render_seconds': mid['render_seconds']} if 'overhead' in mid else {'failure': mid.get('failure')},
    'checkpoint20': playback('intermediate', run + '-checkpoint20', eval_root / (project.name + '-eval-' + run + '-c')),
    'final': playback('final', run + '-final', eval_root / (project.name + '-eval-' + run + '-f')),
    'earlier_run_records_unchanged': bool(result['preserved_records']) or result['preserved_records'] == {},
    'dashboard_at_end': {'project': api['project'], 'accepted_revision': api['accepted']['revision'], 'runs': api['runs'], 'served_at': api['served_at'],
                         'fresh_visit_selects': default_run(api)},
}
text = json.dumps(receipt, indent=1) + '\n'
assert len(text.encode()) <= 16 * 1024, len(text)
(out / 'training.json').write_text(text)
print('receipt', len(text), 'bytes')
