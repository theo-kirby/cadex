"""One real GPU training run on the product-agent's Wren design, with a
checkpoint video published while training is active, the PERSISTENT operator
dashboard observed (never a temporary server), renderer overhead measured from
the trainer's own committed iteration intervals, and a retained final video.

usage: pixi run python train.py PROJECT RUN URL [AUTHORED_BY]   (PYTHONPATH=cli:cli/tests)
AUTHORED_BY names who authored the accepted design under training; it defaults
to the original Wren creation and is recorded in run.json and each playback review.
Nothing here writes the trainer's progress snapshot; browser or render failure
is recorded and leaves the trainer running under its own timeout.
"""
from pathlib import Path
import glob, hashlib, json, os, re, shutil, statistics, subprocess, sys, threading, time
from cadex_cli.review_server import retain_training_view
from cadex_cli.session import project_lock
from cadex_cli.review_record import write_run_record
from cadex_cli.walk import review_from_outputs, write_review
p = Path(sys.argv[1]).resolve(); name = sys.argv[2]; url = sys.argv[3]
authored_by = sys.argv[4] if len(sys.argv) > 4 else 'product-agent-authored Wren; accepted creation with provider-limit exit'
repo = Path.cwd(); ev = p / 'evidence'; run = p / 'runs' / name; train = run / 'train'
train.mkdir(parents=True, exist_ok=False)
def read(x): return json.loads(x.read_text())
def sha(x): return hashlib.sha256(x.read_bytes()).hexdigest()
def save(x, v): x.write_text(json.dumps(v, indent=2) + '\n')
def cli(label, *args):
    with (ev / (label + '.stderr')).open('w') as err:
        r = subprocess.run(['./cadex', '--project', str(p), *map(str, args), '--json'], stdout=subprocess.PIPE, stderr=err, text=True, timeout=300)
    (ev / (label + '.json')).write_text(r.stdout)
    assert r.returncode == 0, (label, r.returncode)
    e = json.loads(r.stdout); assert e['ok'], e
    return e
old = {d.name: sha(d / 'run.json') for d in sorted((p / 'runs').iterdir()) if (d / 'run.json').is_file()}
e = cli(name + '-export', 'params', '--set', 'policy_on=0', '--out', train)
assert e['params']['policy_on'] == 0.0, e['params']
m = read(p / 'script.json'); source = (p / 'script.py').read_text(); shutil.copyfile(p / 'script.py', run / 'script.py')
geometry = {n: sha(train / n) for n in ('wren_model-model.xml', 'wren_walk-task.json')}
cli(name + '-training-render', 'render')
with project_lock(p):
    retain_training_view(p, run)
assert read(run / 'training-view.json')['model']['available']
assert len(read(run / 'training-view.json')['model']['components']) == 8
base = dict(project_root=p, mode='offboard-checkpoint-experiment', accepted_revision=e['accepted_revision'], digest=e['digest'], params=e['params'], param_specs=m['param_specs'], specs_source='successful CLI export', identity_source='successful params export envelope', requested={'iterations': 240, 'envs': 1024, 'seed': 0, 'checkpoint_every': 20, 'timeout_seconds': 1800, 'authored_by': authored_by}, task_bundle=train / 'wren_walk-task.json', task_sha256=sha(train / 'wren_walk-task.json'), model_xml=train / 'wren_model-model.xml')
write_run_record(run, status='running', snapshot_docs=True, **base)
unit = 'cadex-' + name
cmd = ['systemd-run', '--user', '--scope', '--unit=' + unit, '-p', 'MemoryMax=20G', 'timeout', '--signal=TERM', '--kill-after=20s', '1800', str(Path.home() / 'cadex-train-venv/bin/python'), 'training/cadex_train.py', str(train / 'wren_walk-task.json'), '--out', str(train / (name + '.cxpolicy')), '--iterations', '240', '--envs', '1024', '--seed', '0', '--checkpoint-every', '20']
env = dict(os.environ, XLA_PYTHON_CLIENT_MEM_FRACTION='0.45')
log = (ev / (name + '-trainer.log')).open('w'); proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
launched_at = time.time()
samples = []; memory = {'host_peak_bytes': 0, 'gpu_peak_mib': 0, 'samples': 0}; stop = threading.Event()
def monitor():
    tick = 0
    while not stop.wait(.25):
        tick += 1
        try:
            q = read(train / 'progress.json')
            if q.get('iteration') is not None and (not samples or q['iteration'] != samples[-1]['iteration']):
                samples.append({k: q.get(k) for k in ('iteration', 'updated_at', 'state', 'reward_per_step', 'loss', 'episode_steps')}); save(ev / (name + '-timeline.json'), samples)
        except (ValueError, OSError):
            pass
        if tick % 4 == 0:
            for path in glob.glob('/sys/fs/cgroup/user.slice/**/' + unit + '.scope/memory.current', recursive=True):
                try:
                    memory['host_peak_bytes'] = max(memory['host_peak_bytes'], int(Path(path).read_text()))
                except (OSError, ValueError):
                    pass
        if tick % 20 == 0:
            try:
                used = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5).stdout.strip().splitlines()[0]
                memory['gpu_peak_mib'] = max(memory['gpu_peak_mib'], int(used)); memory['samples'] += 1
            except Exception:
                pass
threading.Thread(target=monitor, daemon=True).start()
obsenv = dict(os.environ, PROJECT=str(p), RUN=name, URL=url, WINDOW_S='180', UPDATES='6', PYTHONPATH='cli:cli/tests')
start = time.time()
while not (train / 'progress.json').exists() or read(train / 'progress.json').get('iteration', -1) < 3:
    assert proc.poll() is None, 'trainer exited early'
    assert time.time() - start < 300
    time.sleep(.5)
bounds = subprocess.check_output(['systemctl', '--user', 'show', unit + '.scope',
                                  '-p', 'MemoryCurrent', '-p', 'MemoryPeak', '-p', 'MemoryMax',
                                  '-p', 'ActiveState'], text=True)
save(ev / (name + '-resource-bound.json'), dict(line.split('=', 1) for line in bounds.strip().splitlines()))
obslog = (ev / (name + '-observer.log')).open('w')
observer = subprocess.Popen(['pixi', 'run', 'python', str(Path(__file__).with_name('observe.py'))], env=obsenv, stdout=obslog, stderr=subprocess.STDOUT)
observer_exit = observer.wait(timeout=300)
save(ev / (name + '-observer-exit.json'), {'exit': observer_exit, 'trainer_active_after_observer': proc.poll() is None})

def intervals(lo, hi):
    out = []
    for a, b in zip(samples, samples[1:]):
        if a['updated_at'] is None or b['updated_at'] is None: continue
        if a['updated_at'] >= lo and b['updated_at'] <= hi:
            out.append({'iteration': b['iteration'], 'seconds': round(b['updated_at'] - a['updated_at'], 3), 'checkpoint_boundary': (a['iteration'] % 20 == 0 or b['iteration'] % 20 == 0)})
    return out
def summary(rows):
    plain = [r['seconds'] for r in rows if not r['checkpoint_boundary']]
    return {'count': len(rows), 'median_s': round(statistics.median([r['seconds'] for r in rows]), 3) if rows else None,
            'median_excluding_checkpoint_boundaries_s': round(statistics.median(plain), 3) if plain else None, 'max_s': max([r['seconds'] for r in rows], default=None)}

def playback(policy, pname, active):
    before = read(train / 'progress.json'); started = time.time()
    if active: assert proc.poll() is None and before['state'] == 'training'
    digest = sha(policy)
    cli(pname + '-asset', 'asset', '--put', policy, '--name', policy.name)
    script = re.sub(r'weights="[^"]+",\s*sha256="[a-f0-9]+"', 'weights=' + json.dumps(policy.name) + ', sha256=' + json.dumps(digest), source)
    scriptpath = ev / (pname + '-script.py'); scriptpath.write_text(script)
    cli(pname + '-declare', 'script', '--set', scriptpath)
    r = p / 'runs' / pname
    e = cli(pname + '-rollout', 'params', '--set', 'policy_on=1', '--out', r / 'rollout')
    cli(pname + '-render', 'render')
    receipt = read(r / 'rollout/wren_policy-policy.json'); assert receipt['witness_error'] < receipt['witness_tolerance']
    t = read(r / 'rollout/assembly-simulation-trace.json'); assert t['policy']['policy_sha256'] == digest
    for n in ('wren_model-model.xml', 'wren_walk-task.json'): assert (r / 'rollout' / n).read_bytes() == (train / n).read_bytes()
    shutil.copyfile(p / 'script.py', r / 'script.py'); shutil.copytree(p / 'review/render', r / 'render')
    (r / 'train').mkdir(); shutil.copyfile(train / 'progress.json', r / 'train/progress.json')
    review = review_from_outputs(e['outputs']); review['render'] = {'path': f'runs/{pname}/render'}
    review['provenance'] = {'source_run': name, 'checkpoint': policy.name, 'training_active_at_start': active, 'design_authored_by': authored_by}
    legs = [{'leg': 'rollout', 'exit': 0, 'accepted_revision': e['accepted_revision'], 'digest': e['digest']}]
    write_review(r, review=review, legs=legs, training={}, params=e['params'])
    write_run_record(r, project_root=p, status='ok', mode='checkpoint-playback' if active else 'final-policy-playback', legs=legs, accepted_revision=e['accepted_revision'], digest=e['digest'], params=e['params'], param_specs=read(p / 'script.json')['param_specs'], specs_source='successful rollout envelope', requested=review['provenance'], policy_name=policy.name, policy_sha256=digest, task_bundle=r / 'rollout/wren_walk-task.json', task_sha256=sha(train / 'wren_walk-task.json'), model_xml=r / 'rollout/wren_model-model.xml', trace=r / 'rollout/assembly-simulation-trace.json', review=review, snapshot_docs=True)
    if active:
        # Render only once the trainer is back in ordinary iterations after the
        # checkpoint publication, so the window measures throughput, not the checkpoint.
        wait_start = time.time()
        while read(train / 'progress.json')['iteration'] < 23:
            assert proc.poll() is None and time.time() - wait_start < 600
            time.sleep(.5)
    render_before = read(train / 'progress.json'); render_start = time.time()
    subprocess.run(['pixi', 'run', 'python', '-m', 'cadex_cli.video', '--project', str(p), '--run', pname], check=True, env=dict(os.environ, PYTHONPATH='cli'), timeout=600)
    render_end = time.time(); render_after = read(train / 'progress.json')
    video = read(r / 'video.json')['videos'][0]
    check = subprocess.run(['pixi', 'run', 'python', str(Path(__file__).with_name('check_video.py')), str(p), pname, url] + (['--not-default'] if active else []), env=obsenv, timeout=180)
    after = read(train / 'progress.json')
    if active: assert proc.poll() is None and after['state'] == 'training'
    result = {'run': pname, 'start': started, 'end': time.time(), 'before': before['iteration'], 'after': after['iteration'], 'trainer_active_after_browser': proc.poll() is None, 'browser_check_exit': check.returncode,
              'render_start': render_start, 'render_end': render_end, 'render_seconds': round(render_end - render_start, 3), 'render_before': render_before['iteration'], 'render_after': render_after['iteration'],
              'video': {k: video.get(k) for k in ('path', 'sha256', 'frames', 'duration_seconds', 'sim_seconds', 'style', 'renderer', 'render_seconds')},
              'witness': receipt, 'policy_sha256': digest}
    if active:
        result['overhead'] = {'note': 'trainer-committed iteration intervals; the render window is wall clock around the video render only',
                              'before_window': summary(intervals(render_start - 90, render_start)), 'during_window': summary(intervals(render_start, render_end)), 'after_window': None,
                              'during_rows': intervals(render_start, render_end)}
    save(ev / (pname + '-publication.json'), result)
    assert check.returncode == 0, 'browser video check failed'
    return result
try:
    checkpoint = train / (name + '.000020.cxpolicy')
    while not checkpoint.exists():
        assert proc.poll() is None, 'trainer exited before checkpoint 20'
        time.sleep(.5)
    try:
        mid = playback(checkpoint, name + '-checkpoint20', True)
    except Exception as exc:
        mid = {'failure': repr(exc), 'training_still_active': proc.poll() is None}
        save(ev / (name + '-checkpoint-failure.json'), mid)
    trainer_exit = proc.wait(timeout=1900)
    finished_at = time.time()
    # Complete the after-window now that the trainer has committed more iterations.
    if 'overhead' in mid:
        mid['overhead']['after_window'] = summary(intervals(mid['render_end'], mid['render_end'] + 90))
        save(ev / (name + '-checkpoint20-publication.json'), mid)
    assert trainer_exit == 0, 'trainer failed'
    assert read(train / 'progress.json')['state'] == 'done'
    cli(name + '-final-asset', 'asset', '--put', train / (name + '.cxpolicy'), '--name', name + '.cxpolicy')
    write_run_record(run, status='ok', legs=[{'leg': 'train', 'exit': 0, 'accepted_revision': e['accepted_revision'], 'digest': e['digest']}], policy_name=name + '.cxpolicy', policy_sha256=sha(train / (name + '.cxpolicy')), **base)
    final = playback(train / (name + '.cxpolicy'), name + '-final', False)
    assert all(sha(p / 'runs' / n / 'run.json') == v for n, v in old.items()), 'an earlier run record changed'
    progress = read(train / 'progress.json')
    save(ev / (name + '-experiment-result.json'), {'run': name, 'geometry': geometry, 'accepted_revision': e['accepted_revision'], 'digest': e['digest'], 'intermediate': mid, 'final': final, 'preserved_records': old, 'training_exit': trainer_exit,
        'training_wall_seconds': round(finished_at - launched_at, 3), 'trainer_final': {k: progress.get(k) for k in ('iteration', 'state', 'reward_per_step', 'loss', 'episode_steps', 'seconds', 'device')}, 'memory': memory, 'observer_exit': observer_exit})
finally:
    stop.set()
    if proc.poll() is None: print('Trainer continues under independent 1800 second timeout', flush=True)
    log.close()
print('experiment complete', flush=True)
