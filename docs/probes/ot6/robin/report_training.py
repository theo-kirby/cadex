"""Write the compact D7 receipt for one bounded Robin training run.

usage: pixi run python report_training.py PROJECT RUN URL EVAL_ROOT OUT_DIR
This is the Finch receipt writer (``../finch/report_training.py``) with
Robin's facts: the base is the chassis, the fall threshold comes from the
retained task bundle (termination on ``chassis_z``) rather than from limb
lengths, the task keys are Robin's, and each seed set also carries the
chassis pitch the evaluator measured. Reads what the driver (train.py), the
evaluator (evaluate.py, its scratch projects under EVAL_ROOT as
<project>-eval-<RUN>-{c,f}) and the persistent dashboard already produced;
computes nothing about the policy itself. Writes OUT_DIR/training.json
(under the charter's 16 KB cap) and one decoded frame per retained video
beside it (under 200 KB each), and copies each scratch evaluation's evidence
into the project so the receipt's numbers stay reproducible from
project-local files. Full telemetry, traces, videos and logs stay in the
project directory and are cited by path and digest.
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
# The training run's record carries only the one parameter the export set (policy_on=0); the
# task's declared numbers are the effective values recorded on each playback run, which the
# driver verified rolled the training run's own task bundle, byte for byte.
playbacks = {phase: read(project / 'runs' / (run + '-' + phase) / 'run.json') for phase in ('checkpoint20', 'final')}
TASK_KEYS = ('episode_steps', 'control_hz', 'fall_frac', 'wheel_dia', 'track', 'chassis_h', 'bay_h')
task_values = {k: playbacks['final']['params']['values'][k] for k in TASK_KEYS}
assert all(p['params']['values'][k] == task_values[k] for p in playbacks.values() for k in TASK_KEYS)
assert all(sha(project / 'runs' / p['run'] / p['artifacts']['task_bundle']) == sha(project / 'runs' / run / record['artifacts']['task_bundle']) for p in playbacks.values())
task_bundle = read(project / 'runs' / run / record['artifacts']['task_bundle'])
(fell_rule,) = [t for t in task_bundle['termination'] if t['expression'] == 'chassis_z' and t['below'] is not None]
fall_below_mm = fell_rule['below']


def playback(phase, name, eval_dir):
    entry = result[phase]
    r = project / 'runs' / name
    playback_record = read(r / 'run.json')
    playback_revision = playback_record['model']['accepted_revision']
    trace_path = r / 'rollout/assembly-simulation-trace.json'
    trace = read(trace_path); pol = trace['policy']
    (base,) = [k for k in trace['frames'][0]['component_placements'] if k.startswith('comp_chassis')]
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
        'run': name, 'playback_revision': playback_revision, 'browser_saw_revision': check['accepted_revision'] == playback_revision,
        'policy_sha256': pol['policy_sha256'], 'model_sha256': pol['model_sha256'], 'task_sha256': pol['task_sha256'],
        'trace_sha256': sha(trace_path), 'seed': pol['seed'], 'step_count': pol['step_count'],
        'observed_s': trace['parameters']['end_time_s'], 'termination': pol['termination'], 'fell': pol['termination'] is not None and not pol['truncated'],
        'time_limit_reached': pol['truncated'], 'total_reward': pol['total_reward'],
        'chassis_displacement_mm': [round(b - a, 3) for a, b in zip(first, last)],
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
            'max_abs_pitch_deg': {'mean': round(statistics.mean(r['max_abs_pitch_deg'] for r in rows), 2), 'min': round(min(r['max_abs_pitch_deg'] for r in rows), 2), 'max': round(max(r['max_abs_pitch_deg'] for r in rows), 2)},
            'final_pitch_deg': {'mean': round(statistics.mean(r['final_pitch_deg'] for r in rows), 2), 'min': round(min(r['final_pitch_deg'] for r in rows), 2), 'max': round(max(r['final_pitch_deg'] for r in rows), 2)},
            'falls': sum(1 for r in rows if r['fell']), 'balanced_full_episode': sum(1 for r in rows if not r['fell'] and r['truncated']),
            'mean_total_reward': round(statistics.mean(r['total_reward'] for r in rows), 2),
            'per_seed_columns': ['seed', 'dx_mm', 'survival_s', 'max_abs_pitch_deg', 'final_pitch_deg', 'fell'],
            'per_seed': [[r['seed'], round(r['displacement_x_mm'], 1), r['survival_s'], round(r['max_abs_pitch_deg'], 1), round(r['final_pitch_deg'], 1), r['fell']] for r in rows],
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
# The run before this one, if it diverged: the trainer's own final numbers and error, the checkpoints it
# retained and the status its run record carries; the driver above asserted that record unchanged.
diverged = None
for earlier in sorted(result['preserved_records']):
    rec = read(project / 'runs' / earlier / 'run.json'); prog_path = project / 'runs' / earlier / 'train/progress.json'
    if rec['status'] == 'failed' and prog_path.is_file() and read(prog_path)['state'] == 'failed':
        prog = read(prog_path); fail = read(ev / (earlier + '-experiment-result.json'))
        requested_then = dict(rec['training']['requested'])
        if 'learning_rate' not in requested_then:   # robin1 ran before the driver recorded the rate; it used the trainer's default
            requested_then['learning_rate'] = 3.0e-4; requested_then['learning_rate_source'] = 'trainer default (--learning-rate not passed); the driver did not yet record it'
        requested_then.pop('authored_by')   # identical to this run's, above; the run record carries it in full
        diverged = {'run': earlier, 'record_status': rec['status'], 'requested': requested_then,
                    'trainer_final': fail['trainer_final'], 'error': prog['error'].split('. ')[0] + '.', 'error_in_full': portable(str(prog_path)), 'checkpoints_retained': fail['checkpoints_retained'],
                    'scope_journal': fail['scope_journal'], 'checkpoint20_published_while_active': (project / 'runs' / (earlier + '-checkpoint20') / 'video.json').is_file()}
receipt = {
    'schema': 'robin-training-evidence-v1', 'project': project.name, 'run': run, 'operator_url_source': 'environment (private address, not committed)',
    'accepted_revision': result['accepted_revision'], 'digest': result['digest'], 'geometry': result['geometry'],
    'record_agrees': record['model']['accepted_revision'] == result['accepted_revision'] and record['model']['digest'] == result['digest'] and record['status'] == 'ok',
    'task': task_values, 'task_values_source': 'effective parameters recorded on both playback runs, whose task bundles are byte-identical to the training run\'s',
    'fall_below_mm': fall_below_mm, 'fall_below_source': 'the training run\'s retained task bundle, termination on chassis_z',
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
