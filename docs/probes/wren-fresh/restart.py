# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""D6 on the served working project: engine reopen in place, then a real
restart of the persistent operator service, with the whole review compared
before and after through the private-network URL.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/restart.py \\
    URL PROJECT EVIDENCE_NAME [--unit cadex-operator-review]

Order: inventory and API snapshot; a page opened BEFORE anything happens walks
every run; two fresh engine processes restore the served project in place;
`systemctl --user restart UNIT` restarts the dashboard while that page stays
open; the page must recover without navigation on the run it had selected,
with the video element it was playing; a fresh page then walks every run
again and its records must equal the first walk exactly; the current and one
historical video download with their recorded digests. Never starts a
trainer; asserts the trainer process list is unchanged. Writes
PROJECT/evidence/EVIDENCE_NAME/restart.json and screenshots beside it.
"""
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from cadex_cli.client import CadexdClient, open_project
from cadex_cli.engine import resolve_engine
from cdp_browser import HeadlessBrowser, find_browser

args = sys.argv[1:]
unit = 'cadex-operator-review'
if '--unit' in args:
    i = args.index('--unit')
    unit = args[i + 1]
    del args[i:i + 2]
url, project, name = args
url = url.rstrip('/') + '/'
root = Path(project).resolve()
out = root / 'evidence' / name
out.mkdir(parents=True, exist_ok=True)
MODEL_SETTLED = "['loaded','missing','error'].includes(document.getElementById('model-status').dataset.state)"


def inventory():
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts and not p.is_relative_to(out)}


def identity():
    state = json.loads((root / 'script.json').read_text())
    return {k: state[k] for k in ('accepted_revision', 'accepted_digest', 'accepted_attempt', 'accepted_contract')}


def api_snapshot():
    data = json.loads(urllib.request.urlopen(url + 'api/project', timeout=30).read())
    data.pop('served_at')
    for run in data['runs']:
        run['telemetry'].pop('age_s', None)
    return data


def stable_accepted(data):
    return {k: v for k, v in data['accepted'].items() if k != 'updated_at'}


def run_summary(data):
    return {run['run']: {'outcome': run['outcome'], 'relation': run['relation'], 'status': run['status'],
                         'revision': run['model']['accepted_revision'], 'digest': run['model']['digest'],
                         'telemetry': run['telemetry']['state'], 'iteration': run['telemetry']['iteration'],
                         'points': [run['telemetry']['samples'][k] for k in ('curve', 'loss_curve', 'episode_steps_curve')],  # list summary (ADR-321)
                         'videos': [(v['sha256'], v['policy_sha256'], v['seed'], v['sim_seconds']) for v in run['videos']]}
            for run in data['runs']}


def unit_pid():
    return subprocess.check_output(['systemctl', '--user', 'show', unit, '-p', 'MainPID', '--value'], text=True).strip()


def trainers():
    found = subprocess.run(['pgrep', '-f', 'training/cadex_train.py'], capture_output=True, text=True).stdout.split()
    return sorted(pid for pid in found if pid != str(__import__('os').getpid()))


def walk(page):
    """Select every run and the accepted view; record what the page shows for each."""
    seen = {}
    for view in ['accepted'] + page.evaluate('window.cadexReview.state().runs'):
        page.evaluate('window.cadexReview.select(%s)' % json.dumps(view), await_promise=True)
        page.wait_for(MODEL_SETTLED, timeout=60)
        seen[view] = {k: page.text('#' + k) for k in ('view-kind', 'view-revision', 'view-digest', 'view-relation', 'view-status')}
        seen[view]['telemetry'] = page.attribute('#telemetry', 'data-state')
        seen[view]['iteration'] = page.text('[data-metric=iteration]') if view != 'accepted' else None
        seen[view]['points'] = [page.attribute('[data-history=%s]' % k, 'data-points') for k in ('curve', 'loss_curve', 'episode_steps_curve')] if view != 'accepted' else None
        seen[view]['model'] = page.attribute('#model-status', 'data-state')
        seen[view]['components'] = page.text('#model-components')
        seen[view]['foot_len'] = page.text("#params tr[data-param='foot_len'] td:nth-child(2)")
        seen[view]['videos'] = page.evaluate("Array.from(document.querySelectorAll('#videos li[data-video]')).map(n => n.textContent)")
        seen[view]['video_notes'] = page.evaluate("Array.from(document.querySelectorAll('#videos li:not([data-video])')).map(n => n.textContent)")
        seen[view]['checkpoints'] = page.evaluate("document.querySelectorAll('#checkpoints li').length")
    return seen


def play_and_download(page, run):
    page.evaluate('window.cadexReview.select(%s)' % json.dumps(run), await_promise=True)
    page.wait_for("document.querySelector('#videos video')?.readyState >= 2", timeout=30)
    page.evaluate("window.testVideo=document.querySelector('#videos video'); testVideo.muted=true; testVideo.loop=true; testVideo.play()", await_promise=True)
    page.wait_for('testVideo.currentTime > 0.1')
    video = json.loads((root / 'runs' / run / 'video.json').read_text())['videos'][0]
    assert video['policy_sha256'][:12] in page.text('#videos')
    download = page.download('#videos a')
    assert download.received_bytes == download.total_bytes == (root / 'runs' / run / video['path']).stat().st_size
    digest = hashlib.sha256(download.path.read_bytes()).hexdigest()
    assert digest == video['sha256'], (run, digest)
    return {'run': run, 'sha256': digest, 'policy_sha256': video['policy_sha256'], 'seed': video['seed'],
            'sim_seconds': video['sim_seconds'], 'accepted_revision': video['accepted_revision'],
            'duration_seconds': page.evaluate('testVideo.duration')}


before = inventory()
manifest = identity()
api_before = api_snapshot()
summary_before = run_summary(api_before)
current = [r['run'] for r in api_before['runs'] if r['relation'] == 'current']
assert len(current) == 1, current
current = current[0]
historical = [r for r in summary_before if summary_before[r]['videos'] and r != current and summary_before[r]['relation'] == 'historical'][-1]
receipt = {'project': root.name, 'url_host': url.split('//')[1].split('/')[0], 'evidence': name, 'unit': unit,
           'accepted_revision': manifest['accepted_revision'], 'accepted_digest': manifest['accepted_digest'],
           'accepted_attempt': manifest['accepted_attempt'], 'retained_files': len(before),
           'runs': len(summary_before), 'current_run': current, 'historical_run': historical,
           'run_summary': summary_before, 'api_sha256_before': hashlib.sha256(json.dumps(api_before, sort_keys=True).encode()).hexdigest(),
           'trainers_before': trainers(), 'engine_opens': [], 'restart': {}}
assert receipt['trainers_before'] == [], 'a trainer is running; this probe restarts nothing during training'

with HeadlessBrowser(find_browser()) as browser:
    # A page opened before anything happens, and kept open across it all.
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    page.wait_for(MODEL_SETTLED, timeout=60)
    assert page.text('#project-name') == root.name + ' — review'
    receipt['fresh_default_before'] = page.text('#view-kind')
    assert receipt['fresh_default_before'] == 'RUN ' + current, receipt['fresh_default_before']
    walk_before = walk(page)
    assert walk_before['accepted']['view-revision'] == manifest['accepted_revision']
    assert walk_before['accepted']['view-digest'] == manifest['accepted_digest']
    for run, summary in summary_before.items():
        assert walk_before[run]['view-revision'] == summary['revision'], run
        assert walk_before[run]['points'] == [str(n) for n in summary['points']], run
        assert len(walk_before[run]['videos']) == len(summary['videos']), run
    receipt['walk_before'] = walk_before
    receipt['download_before'] = play_and_download(page, current)
    page.evaluate("window.lifecycleMarker = 'opened before engine reopen and dashboard restart'")

    # Engine: two fresh cadexd processes restore the served project in place.
    for _ in range(2):
        with CadexdClient(resolve_engine()) as client:
            pid = client._process.pid
            reply = open_project(client, root, restore=True)
        assert reply['restore']['matches_accepted'] is True, reply
        assert identity() == manifest, 'restore changed accepted identity'
        receipt['engine_opens'].append({'pid': pid, 'restore': {k: v for k, v in reply['restore'].items() if k != 'outputs'}})
    assert receipt['engine_opens'][0]['pid'] != receipt['engine_opens'][1]['pid']
    after_engine = inventory()
    changed = sorted(k for k in set(before) | set(after_engine) if before.get(k) != after_engine.get(k))
    # A restore publishes a fresh candidate attempt and prunes older unpinned
    # ones (ADR-045, ATTEMPT_KEEP); the accepted attempt is pinned (ADR-303).
    # Only the manifest's non-identity fields and unpinned attempt directories
    # may differ; runs, assets, documents and the accepted attempt may not.
    candidates = 'script_artifacts/' + manifest['accepted_revision'] + '/attempt-'
    accepted_dir = manifest['accepted_attempt']['staging'] + '/'
    def is_candidate(path):
        return path.startswith(candidates) and not path.startswith(accepted_dir)
    unexpected = [k for k in changed if k != 'script.json' and not is_candidate(k)]
    assert not unexpected, unexpected
    attempt_dirs = lambda inv: sorted({k.split('/')[2] for k in inv if k.startswith(candidates)})
    receipt['engine_reopen'] = {
        'scope': 'served project, in place',
        'accepted_attempt_files_unchanged': all(before[k] == after_engine.get(k) for k in before if k.startswith(accepted_dir)),
        'manifest_changed': 'script.json' in changed,
        'candidate_attempts_before': attempt_dirs(before), 'candidate_attempts_after': attempt_dirs(after_engine),
        'candidate_files_added': sum(1 for k in changed if is_candidate(k) and k not in before),
        'candidate_files_pruned': sum(1 for k in changed if is_candidate(k) and k not in after_engine),
        'candidate_bytes_after': sum((root / k).stat().st_size for k in after_engine if is_candidate(k) and k != accepted_dir),
        'other_files_unchanged': True}
    assert receipt['engine_reopen']['accepted_attempt_files_unchanged']
    page.evaluate('window.cadexReview.refresh()', await_promise=True)
    assert page.text('#view-revision') == summary_before[current]['revision']
    assert page.evaluate("testVideo === document.querySelector('#videos video') && !testVideo.paused")
    api_engine = api_snapshot()
    assert run_summary(api_engine) == summary_before
    assert stable_accepted(api_engine) == stable_accepted(api_before)
    receipt['engine_reopen']['manifest_updated_at'] = [api_before['accepted']['updated_at'], api_engine['accepted']['updated_at']]

    # Dashboard: restart the transient user service while the page is open.
    old_pid = unit_pid()
    started = time.monotonic()
    restart = subprocess.Popen(['systemctl', '--user', 'restart', unit], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    stale_seen = None
    polls = 0
    while restart.poll() is None or time.monotonic() - started < 1.0:
        assert time.monotonic() - started < 60, 'service restart timed out'
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        polls += 1
        time.sleep(0.05)
        if stale_seen is None and page.attribute('#freshness', 'data-state') == 'stale':
            stale_seen = round(time.monotonic() - started, 2)
    assert restart.returncode == 0, restart.stdout.read()
    answered = None
    while answered is None:
        try:
            urllib.request.urlopen(url + 'api/project', timeout=5).read()
            answered = round(time.monotonic() - started, 2)
        except OSError:
            assert time.monotonic() - started < 60, 'the restarted service never answered'
            time.sleep(0.1)
    new_pid = unit_pid()
    assert new_pid not in ('', '0', old_pid), (old_pid, new_pid)
    page.wait_for("document.getElementById('freshness').dataset.state === 'live'", timeout=15)
    receipt['restart'] = {'old_pid': old_pid, 'new_pid': new_pid, 'answered_after_s': answered, 'stale_seen_after_s': stale_seen,
                          'polls_during_restart': polls, 'systemctl_exit': restart.returncode,
                          'nrestarts': subprocess.check_output(['systemctl', '--user', 'show', unit, '-p', 'NRestarts', '--value'], text=True).strip()}
    # The open page: same document, same selection, same video element, still playing.
    assert page.evaluate('window.lifecycleMarker') == 'opened before engine reopen and dashboard restart'
    assert page.evaluate("performance.getEntriesByType('navigation').length") == 1
    state = page.evaluate('window.cadexReview.state()')
    assert state['selected'] == current and state['revision'] == summary_before[current]['revision'] and state['error'] is None
    assert sorted(state['runs']) == sorted(summary_before)
    assert page.evaluate("testVideo === document.querySelector('#videos video') && !testVideo.paused && testVideo.readyState >= 2")
    page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
    page.wait_for(MODEL_SETTLED, timeout=60)
    assert page.text('#view-revision') == manifest['accepted_revision']
    page.evaluate('window.cadexReview.select(%s)' % json.dumps(current), await_promise=True)
    page.wait_for("document.getElementById('view-revision').textContent === " + json.dumps(summary_before[current]['revision']))
    page.screenshot(out / 'open-page-after-restart.png')
    receipt['open_page'] = {'recovered_without_navigation': True, 'selected': current, 'video_kept_playing': True}

    # The server's view after restart, then a fresh page walks everything again.
    api_after = api_snapshot()
    receipt['api_sha256_after'] = hashlib.sha256(json.dumps(api_after, sort_keys=True).encode()).hexdigest()
    assert run_summary(api_after) == summary_before
    assert api_after == api_engine, 'the restart changed the served review'
    assert stable_accepted(api_after) == stable_accepted(api_before) and api_after['decisions'] == api_before['decisions']
    receipt['api_unchanged_across_restart'] = True
    fresh = browser.page(url)
    fresh.evaluate('window.cadexReview.ready', await_promise=True)
    fresh.wait_for(MODEL_SETTLED, timeout=60)
    receipt['fresh_default_after'] = fresh.text('#view-kind')
    assert receipt['fresh_default_after'] == receipt['fresh_default_before']
    walk_after = walk(fresh)
    differences = {v: (walk_before[v], walk_after[v]) for v in walk_before if walk_before[v] != walk_after[v]}
    assert not differences, json.dumps(differences, indent=1)[:4000]
    receipt['walk_after_equals_before'] = True
    receipt['download_after'] = [play_and_download(fresh, current), play_and_download(fresh, historical)]
    assert receipt['download_after'][0] == receipt['download_before']
    assert fresh.text('#view-relation').startswith('HISTORICAL')
    fresh.click('#current-run')
    fresh.wait_for("document.getElementById('view-kind').textContent === " + json.dumps('RUN ' + current))
    fresh.evaluate("document.querySelector('#videos').scrollIntoView()")
    fresh.screenshot(out / 'fresh-page-after-restart.png')

receipt['trainers_after'] = trainers()
assert receipt['trainers_after'] == receipt['trainers_before']
final = inventory()
assert final == after_engine, sorted(k for k in set(final) | set(after_engine) if final.get(k) != after_engine.get(k))
assert identity() == manifest
receipt['retained_files_unchanged_across_restart'] = True
receipt['private_address_same_machine'] = True
receipt['screenshots'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.png'))}
(out / 'restart.json').write_text(json.dumps(receipt, indent=2) + '\n')
compact = {k: v for k, v in receipt.items() if k not in ('walk_before', 'run_summary')}
compact['schema'] = 'cadex-restart-evidence-v1'
compact['run_identities'] = {r: {'relation': s['relation'], 'outcome': s['outcome'],
                              'telemetry': s['telemetry'], 'iteration': s['iteration'],
                              'revision': s['revision'], 'points': s['points'],
                              'videos': [v[0] for v in s['videos']]} for r, s in summary_before.items()}
compact['page_walk'] = {r: {'kind': s['view-kind'], 'relation': s['view-relation'],
                          'telemetry': s['telemetry'], 'points': s['points'],
                          'model': s['model'], 'foot_len': s['foot_len'],
                          'videos': len(s['videos'])} for r, s in walk_before.items()}
print(json.dumps(compact, indent=2))
