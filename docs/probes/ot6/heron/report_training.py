"""Write the compact D8 receipt for one bounded Heron training run.

usage: pixi run python report_training.py PROJECT RUN URL EVAL_ROOT OUT_DIR
This is the Robin receipt writer (``../robin/report_training.py``) with
Heron's facts: the measured body is the forearm whose frame is the tip, the
termination rule comes from the retained task bundle (``tip_z`` below
``tip_floor``), the task keys are Heron's, and each seed set carries the
reach error at episode end and over the final second, the smallest error,
when the tip first came within tolerance, successes and terminations as the
evaluator measured them. Reads what the driver (train.py), the evaluator
(evaluate.py, its scratch projects under EVAL_ROOT as
<project>-eval-<RUN>-{c,f}) and the persistent dashboard already produced;
computes nothing about the policy itself. Writes OUT_DIR/training.json
(under the charter's 16 KB cap) and one decoded frame per retained video
beside it (under 200 KB each), and copies each scratch evaluation's evidence
into the project so the receipt's numbers stay reproducible from
project-local files. Full telemetry, traces, videos and logs stay in the
project directory and are cited by path and digest.
"""
import hashlib, json, math, shutil, statistics, subprocess, sys, urllib.request
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
# The training run's record carries only the one parameter the export set (policy_on=0); the
# task's declared numbers are the effective values recorded on each playback run, which the
# driver verified rolled the training run's own task bundle, byte for byte.
playbacks = {phase: read(project / 'runs' / (run + '-' + phase) / 'run.json') for phase in ('checkpoint20', 'final')}
TASK_KEYS = ('episode_steps', 'control_hz', 'target_x', 'target_z', 'reach_scale', 'reach_tol', 'tip_floor', 'upper_len', 'fore_len', 'z_shoulder', 'push_n_lo', 'push_n_hi', 'push_dur', 'ctrl_cost_w', 'tip_vel_w')
task_values = {k: playbacks['final']['params']['values'][k] for k in TASK_KEYS}
assert all(p['params']['values'][k] == task_values[k] for p in playbacks.values() for k in TASK_KEYS)
assert all(sha(project / 'runs' / p['run'] / p['artifacts']['task_bundle']) == sha(project / 'runs' / run / record['artifacts']['task_bundle']) for p in playbacks.values())
task_bundle = read(project / 'runs' / run / record['artifacts']['task_bundle'])
(floor_rule,) = [t for t in task_bundle['termination'] if t['expression'] == 'tip_z' and t['below'] is not None]
tip_floor_mm = floor_rule['below']
assert tip_floor_mm == task_values['tip_floor']
target = [task_values['target_x'], 0.0, task_values['target_z']]; tol = task_values['reach_tol']
stat = lambda rows, key: {'mean': round(statistics.mean(r[key] for r in rows), 2), 'min': round(min(r[key] for r in rows), 2), 'max': round(max(r[key] for r in rows), 2)}


def playback(phase, name, eval_dir):
    entry = result[phase]
    r = project / 'runs' / name
    playback_record = read(r / 'run.json')
    playback_revision = playback_record['model']['accepted_revision']
    trace_path = r / 'rollout/assembly-simulation-trace.json'
    trace = read(trace_path); pol = trace['policy']
    (tip,) = [k for k in trace['frames'][0]['component_placements'] if k.startswith('comp_forearm')]
    timed = [f['component_placements'][tip]['position_mm'] for f in trace['frames'] if f['nominal_time_s'] is not None]
    first, last = timed[0], timed[-1]
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
        'run': name, 'playback_revision': playback_revision, 'browser_saw_revision': check['accepted_revision'] == playback_revision,
        'policy_sha256': pol['policy_sha256'], 'model_sha256': pol['model_sha256'], 'task_sha256': pol['task_sha256'],
        'trace_sha256': sha(trace_path), 'seed': pol['seed'], 'step_count': pol['step_count'],
        'observed_s': trace['parameters']['end_time_s'], 'termination': pol['termination'], 'terminated': pol['terminated_step'] is not None and not pol['truncated'],
        'time_limit_reached': pol['truncated'], 'total_reward': pol['total_reward'],
        'tip_start_mm': [round(x, 2) for x in first], 'tip_end_mm': [round(x, 2) for x in last], 'end_error_mm': round(math.dist(last, target), 2),
        'witness': {k: entry['witness'].get(k) for k in ('witness_error', 'witness_tolerance')},
        'trainer_iterations_before_after': [entry['before'], entry['after']], 'trainer_active_after_browser': entry['trainer_active_after_browser'],
        'browser_check_exit': entry['browser_check_exit'], 'render_seconds': entry['render_seconds'],
        'video': {k: video.get(k) for k in ('path', 'sha256', 'frames', 'fps', 'duration_seconds', 'sim_seconds', 'style', 'renderer', 'width', 'height', 'showing', 'accepted_revision')},
        'video_frame': {'png': frame.name, 'sha256': sha(frame), 'bytes': frame.stat().st_size, 'at_sim_s': video['sim_seconds'] / 2},
        'browser': {k: check.get(k) for k in ('fresh_selection', 'is_default', 'expected_default', 'historical_selection', 'returned_to_current', 'decoded_frames', 'download_sha256', 'style', 'components')},
        'seeds': {
            'schema': comparison['schema'], 'seeds': comparison['seeds'], 'episode_seconds': comparison['episode_seconds'], 'control_hz': comparison['control_hz'],
            'target_mm': comparison['target_mm'], 'reach_tol_mm': comparison['reach_tol_mm'], 'tip_floor_mm': comparison['tip_floor_mm'], 'success_rule': comparison['success_rule'],
            'end_error_mm': stat(rows, 'end_error_mm'), 'final_second_max_error_mm': stat(rows, 'final_second_max_error_mm'),
            'final_second_mean_error_mm': stat(rows, 'final_second_mean_error_mm'), 'min_error_mm': stat(rows, 'min_error_mm'),
            'survival_s': {'mean': round(statistics.mean(r['survival_s'] for r in rows), 3), 'min': min(r['survival_s'] for r in rows), 'max': max(r['survival_s'] for r in rows)},
            'successes': sum(1 for r in rows if r['success']), 'terminations': sum(1 for r in rows if r['terminated']),
            'ever_within_tol': sum(1 for r in rows if r['first_within_tol_s'] is not None), 'full_episode': sum(1 for r in rows if r['truncated'] and not r['terminated']),
            'mean_total_reward': round(statistics.mean(r['total_reward'] for r in rows), 2),
            'per_seed_columns': ['seed', 'end_error_mm', 'final_second_max_error_mm', 'min_error_mm', 'first_within_tol_s', 'survival_s', 'success', 'terminated'],
            'per_seed': [[r['seed'], round(r['end_error_mm'], 1), round(r['final_second_max_error_mm'], 1), round(r['min_error_mm'], 1), r['first_within_tol_s'], r['survival_s'], r['success'], r['terminated']] for r in rows],
            'evidence': portable(str(keep)),
        },
    }


def intervals_summary(lo, hi):
    rows = [round(b['updated_at'] - a['updated_at'], 3) for a, b in zip(timeline, timeline[1:])
            if a['updated_at'] and b['updated_at'] and a['updated_at'] >= lo and b['updated_at'] <= hi]
    return {'count': len(rows), 'median_s': round(statistics.median(rows), 3) if rows else None, 'max_s': max(rows, default=None)}


pairs = [(a, b) for a, b in zip(timeline, timeline[1:]) if a['updated_at'] and b['updated_at']]
boundary = lambda a, b: a['iteration'] % 20 in (0, 19) or b['iteration'] % 20 == 19


def enclosing(lo, hi):
    """The one trainer-committed interval that contains the whole render window, if any, beside
    every other checkpoint step of the run: when the render is shorter than the step it fell
    inside, no interval lies within the window and this is the measurement of its impact."""
    inside = [(a, b) for a, b in pairs if a['updated_at'] <= lo and b['updated_at'] >= hi]
    if not inside:
        return {}
    ((a, b),) = inside
    steps = [round(y['updated_at'] - x['updated_at'], 1) for x, y in pairs if boundary(x, y) and y['updated_at'] - x['updated_at'] > 10 and y is not b]
    return {'enclosing_interval': {'iteration': b['iteration'], 'seconds': round(b['updated_at'] - a['updated_at'], 3), 'checkpoint_boundary': boundary(a, b),
                                   'other_checkpoint_steps_s': steps}}


mid = result['intermediate']
assert 'failure' not in mid, mid   # the driver's own checkpoint publication must have succeeded
plain = sorted(round(b['updated_at'] - a['updated_at'], 3) for a, b in pairs if not boundary(a, b))
api = json.load(urllib.request.urlopen(url + '/api/project', timeout=10))
curve = [[s['iteration'], round(s['reward_per_step'], 4) if s['reward_per_step'] is not None else None, round(s['episode_steps'], 1)]
         for s in timeline if s['iteration'] is not None and s['iteration'] >= 0 and (s['iteration'] % 20 == 19 or s['iteration'] == 0)]
# Any earlier run of this project that failed: its record status, the trainer's own error and final
# numbers, and whether its checkpoint video was published while it was active. The driver above asserted
# every earlier record unchanged. None when no earlier run failed.
diverged = None
for earlier in sorted(result['preserved_records']):
    rec = read(project / 'runs' / earlier / 'run.json'); prog_path = project / 'runs' / earlier / 'train/progress.json'
    if rec['status'] == 'failed' and prog_path.is_file() and read(prog_path)['state'] == 'failed':
        prog = read(prog_path)
        requested_then = dict(rec['training']['requested']); requested_then.pop('authored_by', None)
        diverged = {'run': earlier, 'record_status': rec['status'], 'requested': requested_then,
                    'trainer_final': {k: prog.get(k) for k in ('iteration', 'state', 'reward_per_step', 'loss', 'episode_steps', 'seconds', 'device')},
                    'error': prog['error'].split('. ')[0] + '.', 'error_in_full': portable(str(prog_path)),
                    'checkpoint20_published_while_active': (project / 'runs' / (earlier + '-checkpoint20') / 'video.json').is_file()}
receipt = {
    'schema': 'heron-training-evidence-v1', 'project': project.name, 'run': run, 'operator_url_source': 'environment (private address, not committed)',
    'accepted_revision': result['accepted_revision'], 'digest': result['digest'], 'geometry': result['geometry'],
    'record_agrees': record['model']['accepted_revision'] == result['accepted_revision'] and record['model']['digest'] == result['digest'] and record['status'] == 'ok',
    'task': task_values, 'task_values_source': 'effective parameters recorded on both playback runs, whose task bundles are byte-identical to the training run\'s',
    'target_mm': target, 'reach_tol_mm': tol, 'tip_floor_mm': tip_floor_mm, 'tip_floor_source': 'the training run\'s retained task bundle, termination on tip_z',
    'requested': record['training']['requested'], 'trainer_exit': result['training_exit'], 'training_wall_seconds': result['training_wall_seconds'],
    'trainer_final': result['trainer_final'], 'best': {'iteration': progress['best_iteration'], 'reward_per_step': progress['best_reward_per_step']},
    'reward_curve_every_20': {'columns': ['iteration', 'reward_per_step', 'episode_steps'], 'rows': curve}, 'memory': result['memory'], 'resource_bound': bound,
    'live_browser': {'persistent_server': observe['persistent_server'], 'default_view_kind': observe.get('default_view_kind'),
                     'model_state': observe.get('model_state'), 'model_components_listed': observe.get('model_components', '').count('mesh retained'),
                     'reload_count': observe.get('reload_count'), 'samples': len(observe.get('samples', [])),
                     'first_seen_max_committed_to_page_s': max((x['committed_to_page_s'] for x in observe.get('first_seen', {}).values()), default=None),
                     'first_seen_count': len(observe.get('first_seen', {}))},
    'observer_exit': result['observer_exit'],
    'update_intervals': {'note': 'every trainer-committed update interval over the whole run; boundary = the compile at update 0 and each checkpoint step (every 20th update)',
                         'count': len(pairs), 'plain': {'count': len(plain), 'median_s': statistics.median(plain), 'min_s': plain[0], 'max_s': plain[-1]},
                         'boundary': [{'iteration': b['iteration'], 'seconds': round(b['updated_at'] - a['updated_at'], 1)} for a, b in pairs if boundary(a, b) and b['updated_at'] - a['updated_at'] > 10],
                         'concurrent_loads_during_run': ['checkpoint policy declaration (script --set), rollout and record', 'one checkpoint video render', 'the observer and one persistent-dashboard browser check']},
    'render_overhead': {'note': mid['overhead']['note'], **{k: mid['overhead'][k] for k in ('before_window', 'during_window', 'after_window')},
                        'concurrent_renders': 1, 'render_seconds': mid['render_seconds'], **enclosing(mid['render_start'], mid['render_end'])},
    'checkpoint20': playback('intermediate', run + '-checkpoint20', eval_root / (project.name + '-eval-' + run + '-c')),
    'final': playback('final', run + '-final', eval_root / (project.name + '-eval-' + run + '-f')),
    'diverged_run': diverged,
    'earlier_run_records': {'count': len(result['preserved_records']),
                            'note': 'run records present before the training run; the driver asserts each is byte-identical afterwards, which over an empty set proves nothing'},
    # Identity rows, not the served records: the full /api/project document is 36 KB.
    'dashboard_at_end': {'project': api['project'], 'accepted_revision': api['accepted']['revision'], 'served_at': api['served_at'],
                         'runs': [{k: r.get(k) for k in ('run', 'status', 'mode', 'relation')} | {'policy_sha256': (r.get('policy') or {}).get('sha256'),
                                   'accepted_revision': (r.get('model') or {}).get('accepted_revision'), 'videos': len(r.get('videos') or [])} for r in api['runs']],
                         'fresh_visit_selects': default_run(api)},
}
text = json.dumps(receipt, indent=1) + '\n'
assert len(text.encode()) <= 16 * 1024, (len(text), {k: len(json.dumps(v)) for k, v in receipt.items()})
(out / 'training.json').write_text(text)
print('receipt', len(text), 'bytes')
