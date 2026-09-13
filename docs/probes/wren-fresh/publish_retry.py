# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Verify and publish a completed retry; observe arrival on the persistent URL.

PYTHONPATH=cli:cli/tests pixi run python publish_retry.py PROJECT RUN URL HISTORY
The original training record/script/view remain retained. No training is launched.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from cadex_cli.video import atomic_json, render
from cadex_cli.walk import review_from_outputs
from cdp_browser import HeadlessBrowser, find_browser

root = Path(sys.argv[1]).resolve()
name, url, historical = sys.argv[2:]
run = root / 'runs' / name
out = root / 'evidence' / (name + '-publication60')
out.mkdir(exist_ok=False)
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original = read(run / 'run.json')
assert original['status'] == 'ok' and not original['artifacts']['trace']
assert original['params']['values']['foot_len'] == 110
protected = {str(p.relative_to(root)): sha(p) for p in (root / 'runs').rglob('*')
             if p.is_file() and run not in p.parents}
training_files = {str(p.relative_to(run)): sha(p) for p in run.rglob('*') if p.is_file()}
shutil.copyfile(run / 'run.json', run / 'training-run.json')
policy = run / 'train' / (name + '.cxpolicy')
digest = sha(policy)

def cli(label, *args):
    result = subprocess.run(['./cadex', '--project', str(root), *map(str, args), '--json'],
                            capture_output=True, text=True, timeout=300)
    (out / (label + '.json')).write_text(result.stdout)
    (out / (label + '.stderr')).write_text(result.stderr)
    assert result.returncode == 0, (label, result.stderr, result.stdout)
    reply = json.loads(result.stdout)
    assert reply['ok'], reply
    return reply

with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    assert page.text('#view-kind') == 'RUN ' + name
    assert page.text('#project-name') == root.name + ' — review'
    page.click("#views li[data-run='%s']" % historical)
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    old_revision = page.text('#view-revision')
    page.evaluate("window.playing=document.querySelector('#videos video'); playing.muted=true; playing.loop=true; playing.play()", await_promise=True)
    page.wait_for('playing.currentTime > 0.1')
    cli('asset', 'asset', '--put', policy, '--name', policy.name)
    source = (root / 'script.py').read_text()
    source, replacements = re.subn(r'weights="[^"]+",\s*sha256="[a-f0-9]+"',
                                   'weights=' + json.dumps(policy.name) + ', sha256=' + json.dumps(digest), source)
    assert replacements == 1
    script = out / 'playback-source.py'
    script.write_text(source)
    cli('declare', 'script', '--set', script)
    envelope = cli('rollout', 'params', '--set', 'policy_on=1', '--out', run / 'rollout')
    cli('render', 'render')
    receipt = read(run / 'rollout/wren_policy-policy.json')
    assert receipt['witness_error'] < receipt['witness_tolerance']
    trace = read(run / 'rollout/assembly-simulation-trace.json')
    assert trace['policy']['policy_sha256'] == digest
    for filename in ('wren_model-model.xml', 'wren_walk-task.json'):
        assert (run / 'rollout' / filename).read_bytes() == (run / 'train' / filename).read_bytes()
    shutil.copyfile(root / 'script.py', run / 'playback-script.py')
    shutil.copytree(root / 'review/render', run / 'render')
    review = review_from_outputs(envelope['outputs'])
    atomic_json(run / 'review.json', review)
    # Enrich this attempt, preserving its training inputs and chronological position.
    record = json.loads(json.dumps(original))
    record['model'] = dict(accepted_revision=envelope['accepted_revision'], digest=envelope['digest'],
                           identity_source='verified rollout envelope; training identity retained in training-run.json')
    record['params']['values'] = envelope['params']
    record['policy'] = dict(name=policy.name, sha256=digest, asset='assets/' + policy.name)
    record['project_artifacts'].update(policy='assets/' + policy.name, render=f'runs/{name}/render')
    record['artifacts'].update(script='playback-script.py', trace='rollout/assembly-simulation-trace.json', review='review.json')
    record['legs'].append(dict(leg='rollout', exit=0, accepted_revision=envelope['accepted_revision'], digest=envelope['digest']))
    record['rollout'] = dict(trace=record['artifacts']['trace'], seed=trace['policy']['seed'], total_reward=review.get('total_reward'))
    record['training']['source_record'] = 'training-run.json'
    atomic_json(run / 'run.json', record)
    video = render(root, name)
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.text('#view-kind') == 'RUN ' + historical
    assert page.text('#view-revision') == old_revision
    assert page.evaluate("playing===document.querySelector('#videos video') && !playing.paused")
    assert name in page.text('#current-run')
    page.screenshot(out / 'historical-preserved.png')
    page.click('#current-run')
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
    assert page.text('#view-kind') == 'RUN ' + name
    assert page.text('#view-revision') == envelope['accepted_revision']
    page.screenshot(out / 'current-video.png')
    result = dict(run=name, training_model=original['model'], playback_model=record['model'],
                  policy_sha256=digest, witness=receipt, video=video, historical=historical,
                  historical_revision=old_revision, historical_player_preserved=True,
                  model_and_task_bytes_match_training=True, private_address_same_machine=True,
                  persistent_server=True)
subprocess.run(['pixi', 'run', 'python', str(Path(__file__).with_name('check_video.py')), str(root), name, url],
               env=dict(os.environ, PYTHONPATH='cli:cli/tests'), check=True, timeout=180)
assert all(sha(root / p) == value for p, value in protected.items())
assert all(sha(run / p) == value for p, value in training_files.items() if p != 'run.json')
assert sha(run / 'training-run.json') == training_files['run.json']
result.update(protected_historical_files=len(protected), retained_training_files=len(training_files),
              check=read(root / 'evidence' / (name + '-check.json')))
atomic_json(out / 'result.json', result)
print(json.dumps(result, indent=2))
