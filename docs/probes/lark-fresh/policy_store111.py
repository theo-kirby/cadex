# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Real D5/D8/D10 probe: the persistent dashboard lists a completed run whose
policy was never stored as a problem carrying the store command, and sees that
command's effect on the open page (ADR-327).

PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/policy_store111.py PROJECT URL RUN [RUN ...]

Each ``RUN`` is an ``ok`` record whose policy the trainer saved under the
run's ``train/`` while nothing put it in the project store — ``lark96-restart``
and ``lark109-engine2`` on the persistent Lark copy, recorded by the bounded
drivers before they stored through the CLI. The probe opens the operator URL
in headless Chromium, selects each run, records the problem line and the
policy-store row, runs the exact command the problem line named from an
unrelated working directory and watches the already-open page drop the problem
and flip to ``stored`` with no reload, no record rewrite, the run still
``completed``, and no change to any earlier run file or the accepted identity.
The dashboard service is neither restarted nor replaced by this probe. No
trainer may be active. Retains its receipt and screenshots in PROJECT/evidence.
"""
import json
from pathlib import Path
import subprocess
import sys
import time

from interruption import inventory, read, save, sha, trainers
from cdp_browser import HeadlessBrowser, find_browser

SERVICE = 'cadex-operator-review'
CADEX = Path(__file__).resolve().parents[3] / 'cadex'


def service_pid():
    out = subprocess.check_output(['systemctl', '--user', 'show', SERVICE, '-p', 'MainPID', '-p', 'ActiveState'], text=True)
    values = dict(line.split('=', 1) for line in out.strip().splitlines())
    return int(values['MainPID']), values['ActiveState']


def page_state(page):
    row = "#artifacts tr[data-group='artifacts'][data-key='policy']"
    return dict(
        kind=page.text('#view-kind'), status=page.text('#view-status'), note=page.text('#view-note'),
        policy_store=page.text('#view-policy-store'),
        policy_store_state=page.attribute('#view-policy-store', 'data-state'),
        telemetry_state=page.attribute('#telemetry', 'data-state'),
        problems=page.evaluate("Array.from(document.querySelectorAll('#problems li')).map(function (li) { return li.textContent; })"),
        trainer_copy_path=page.text(row + ' td:nth-child(2)'),
        trainer_copy_status=page.attribute(row + ' td:nth-child(3)', 'data-status'),
        store_copy_status=page.text("#artifacts tr[data-group='project_artifacts'][data-key='policy'] td:nth-child(3)"),
    )


def main():
    p, url, names = Path(sys.argv[1]).resolve(), sys.argv[2].rstrip('/') + '/', sys.argv[3:]
    assert names, 'name at least one run'
    ev = p / 'evidence'
    ev.mkdir(exist_ok=True)
    assert trainers() == [], 'a trainer or pytest is active; this probe needs the machine quiet'
    records = {}
    for name in names:
        record = read(p / 'runs' / name / 'run.json')
        trained = p / 'runs' / name / 'train' / record['policy']['name']
        assert record['status'] == 'ok' and trained.is_file() and sha(trained) == record['policy']['sha256'], name
        assert not (p / 'assets' / record['policy']['name']).exists(), 'the store already holds %s; nothing to demonstrate' % name
        records[name] = record
    manifest_before = read(p / 'script.json')
    record_bytes_before = {name: (p / 'runs' / name / 'run.json').read_bytes() for name in names}
    runs_before = inventory(p / 'runs')
    assets_before = inventory(p / 'assets')
    pid_before, active = service_pid()
    assert active == 'active'
    result = dict(schema='cadex-policy-store-evidence-v2', ok=False, project=p.name, runs=names,
                  url=url, persistent_port=int(url.rsplit(':', 1)[1].rstrip('/')),
                  private_address_same_machine=True,
                  accepted_revision=manifest_before['accepted_revision'], accepted_digest=manifest_before['accepted_digest'],
                  service_pid=pid_before, per_run={})
    try:
        with HeadlessBrowser(find_browser()) as browser:
            page = browser.page(url)
            page.evaluate('window.cadexReview.ready', await_promise=True)
            result['fresh_visit_default_run'] = page.text('#view-kind')
            for name in names:
                record = records[name]
                policy_name, policy_sha = record['policy']['name'], record['policy']['sha256']
                row = dict(policy_name=policy_name, policy_sha256=policy_sha, record_status=record['status'],
                           record_asset_locator=record['policy']['asset'])
                page.click("#views li[data-run=%s]" % json.dumps(name))
                page.wait_for("document.getElementById('view-kind').textContent === %s" % json.dumps('RUN ' + name))
                page.wait_for("Array.from(document.querySelectorAll('#problems li')).some(function (li) { return li.textContent.startsWith('policy_store:'); })")
                before = page_state(page)
                page.screenshot(ev / ('policy-store111-%s-before.png' % name))
                row['page_before'] = before
                assert before['status'] == 'completed' and before['policy_store_state'] == 'unstored'
                assert before['trainer_copy_status'] == 'retained'
                (problem,) = [line for line in before['problems'] if line.startswith('policy_store:')]
                command = problem.split('; store it: ', 1)[1]
                expected = 'cadex asset --project <project-dir> --put <project-dir>/runs/%s/train/%s' % (name, policy_name)
                assert command == expected, command
                assert ('next: store it: ' + command) in before['policy_store']
                # The operator runs exactly what the problem line said, with
                # <project-dir> filled in, from an unrelated working directory.
                argv = [str(CADEX), *[a.replace('<project-dir>', str(p)) for a in command.split()[1:]], '--json']
                started = time.monotonic()
                proc = subprocess.run(argv, cwd='/', capture_output=True, text=True, timeout=120)
                envelope = json.loads(proc.stdout)
                stored = [entry for entry in envelope.get('assets') or [] if entry.get('sha256') == policy_sha]
                row['cli'] = dict(command=command, exit=proc.returncode, ok=envelope.get('ok'),
                                  wall_seconds=round(time.monotonic() - started, 3),
                                  stored_name=stored[0].get('name') if stored else None)
                assert proc.returncode == 0 and envelope.get('ok') is True and stored, proc.stderr[-800:]
                flip_started = time.monotonic()
                page.wait_for("document.getElementById('view-policy-store').dataset.state === 'stored'", timeout=30)
                page.wait_for("!Array.from(document.querySelectorAll('#problems li')).some(function (li) { return li.textContent.startsWith('policy_store:'); })", timeout=30)
                row['page_flip_seconds'] = round(time.monotonic() - flip_started, 3)
                after = page_state(page)
                page.screenshot(ev / ('policy-store111-%s-after.png' % name))
                row['page_after'] = after
                assert after['kind'] == before['kind'] and after['status'] == 'completed'
                assert 'holds this policy with the recorded digest' in after['policy_store'] and 'next:' not in after['policy_store']
                assert after['trainer_copy_status'] == 'retained' and after['note'] == before['note']
                result['per_run'][name] = row
            result['no_navigation'] = page.evaluate('performance.getEntriesByType("navigation").length') == 1
            # A fresh visit keeps the current-run rule and shows the stored state.
            fresh = browser.page(url)
            fresh.evaluate('window.cadexReview.ready', await_promise=True)
            result['fresh_visit_after_default_run'] = fresh.text('#view-kind')
            for name in names:
                fresh.click("#views li[data-run=%s]" % json.dumps(name))
                fresh.wait_for("document.getElementById('view-kind').textContent === %s" % json.dumps('RUN ' + name))
                fresh.wait_for("document.getElementById('view-policy-store').dataset.state === 'stored'")
                result['per_run'][name]['fresh_visit_after_policy_store'] = fresh.text('#view-policy-store')
                result['per_run'][name]['fresh_visit_after_problems'] = fresh.evaluate(
                    "Array.from(document.querySelectorAll('#problems li')).map(function (li) { return li.textContent; })")
        manifest_after = read(p / 'script.json')
        assets_after = inventory(p / 'assets')
        expected_assets = sorted(records[name]['policy']['name'] for name in names)
        result.update(
            record_bytes_unchanged=all((p / 'runs' / name / 'run.json').read_bytes() == record_bytes_before[name] for name in names),
            runs_files_unchanged=inventory(p / 'runs') == runs_before, runs_files=len(runs_before),
            assets_added=sorted(set(assets_after) - set(assets_before)),
            assets_prior_unchanged=all(assets_after.get(k) == v for k, v in assets_before.items()),
            stored_assets_sha256_match=all(assets_after.get(records[name]['policy']['name']) == records[name]['policy']['sha256'] for name in names),
            accepted_identity_unchanged=(manifest_after['accepted_revision'], manifest_after['accepted_digest'])
                == (manifest_before['accepted_revision'], manifest_before['accepted_digest']),
            service_pid_after=service_pid()[0], trainers_seen=trainers(),
        )
        result['ok'] = all([result['record_bytes_unchanged'], result['runs_files_unchanged'],
                            result['assets_added'] == expected_assets, result['assets_prior_unchanged'],
                            result['stored_assets_sha256_match'], result['accepted_identity_unchanged'],
                            result['service_pid_after'] == pid_before, result['no_navigation'],
                            result['trainers_seen'] == [],
                            all(not any(line.startswith('policy_store:') for line in row['fresh_visit_after_problems'])
                                for row in result['per_run'].values())])
    finally:
        save(ev / 'policy-store111-evidence.json', result)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()
