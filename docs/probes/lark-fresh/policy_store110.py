# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Real D8/D10 probe: the persistent dashboard explains a failed run whose
training finished, names the CLI action that stores its policy, and sees that
action's effect on the open page (ADR-326).

PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/policy_store110.py PROJECT URL RUN

``RUN`` is a ``failed`` record whose telemetry reads ``done`` and whose policy
the trainer saved under the run's ``train/`` while nothing put it in the
project store — ``lark109-engine`` (ADR-325's first attempt) on the persistent
Lark copy. The probe opens the operator URL in headless Chromium, selects the
run, records what the page says, downloads the trainer's copy through the
page, then runs the exact command the page named from the project directory
and watches the already-open page flip to ``stored`` with no reload, no record
rewrite, and no change to any earlier run file or to the accepted identity.
The dashboard service is neither restarted nor replaced. No trainer may be
active. Retains its receipt and screenshots in PROJECT/evidence.
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
        iteration=page.text('[data-metric=iteration]'), total=page.text('[data-metric=total]'),
        problems=page.text('#problems'),
        trainer_copy_path=page.text(row + ' td:nth-child(2)'),
        trainer_copy_status=page.attribute(row + ' td:nth-child(3)', 'data-status'),
        store_copy_status=page.text("#artifacts tr[data-group='project_artifacts'][data-key='policy'] td:nth-child(3)"),
    )


def main():
    p, url, name = Path(sys.argv[1]).resolve(), sys.argv[2].rstrip('/') + '/', sys.argv[3]
    ev = p / 'evidence'
    ev.mkdir(exist_ok=True)
    assert trainers() == [], 'a trainer or pytest is active; this probe needs the machine quiet'
    run = p / 'runs' / name
    record = read(run / 'run.json')
    policy_name, policy_sha = record['policy']['name'], record['policy']['sha256']
    trained = run / 'train' / policy_name
    assert record['status'] == 'failed' and trained.is_file() and sha(trained) == policy_sha
    assert not (p / 'assets' / policy_name).exists(), 'the store already holds it; nothing to demonstrate'
    manifest_before = read(p / 'script.json')
    record_bytes_before = (run / 'run.json').read_bytes()
    runs_before = inventory(p / 'runs')
    assets_before = inventory(p / 'assets')
    pid_before, active = service_pid()
    assert active == 'active'
    result = dict(schema='cadex-policy-store-evidence-v1', ok=False, project=p.name, run=name,
                  url=url, persistent_port=int(url.rsplit(':', 1)[1].rstrip('/')),
                  private_address_same_machine=True, policy_name=policy_name, policy_sha256=policy_sha,
                  accepted_revision=manifest_before['accepted_revision'], accepted_digest=manifest_before['accepted_digest'],
                  service_pid=pid_before, record_status=record['status'], record_error=record['error'],
                  record_asset_locator=record['policy']['asset'])
    try:
        with HeadlessBrowser(find_browser()) as browser:
            page = browser.page(url)
            page.evaluate('window.cadexReview.ready', await_promise=True)
            result['fresh_visit_default_run'] = page.text('#view-kind')
            page.click("#views li[data-run=%s]" % json.dumps(name))
            page.wait_for("document.getElementById('view-kind').textContent === %s" % json.dumps('RUN ' + name))
            page.wait_for("document.getElementById('telemetry').dataset.state === 'done'")
            page.wait_for("document.getElementById('view-note').textContent.includes('training itself finished')")
            before = page_state(page)
            page.screenshot(ev / 'policy-store110-before.png')
            result['page_before'] = before
            assert before['status'] == 'failed' and before['policy_store_state'] == 'unstored'
            assert 'not in the trainer' in before['note'] and before['trainer_copy_status'] == 'retained'
            command = before['policy_store'].split('next: store it: ', 1)[1].split(' · or ', 1)[0]
            assert command == 'cadex asset --project <project-dir> --put <project-dir>/runs/%s/train/%s' % (name, policy_name), command
            download = page.download("#artifacts tr[data-group='artifacts'][data-key='policy'] a[href$='download=1']")
            result['page_download'] = dict(url=download.url, bytes=download.path.stat().st_size,
                                           sha256_matches_record=sha(download.path) == policy_sha)
            assert result['page_download']['sha256_matches_record']
            # The operator runs exactly what the page said, with <project-dir>
            # filled in, from an unrelated working directory.
            argv = [str(CADEX), *[a.replace('<project-dir>', str(p)) for a in command.split()[1:]], '--json']
            started = time.monotonic()
            proc = subprocess.run(argv, cwd='/', capture_output=True, text=True, timeout=120)
            envelope = json.loads(proc.stdout)
            stored = [row for row in envelope.get('assets') or [] if row.get('sha256') == policy_sha]
            result['cli'] = dict(command=command, exit=proc.returncode, ok=envelope.get('ok'),
                                 wall_seconds=round(time.monotonic() - started, 3),
                                 stored_name=stored[0].get('name') if stored else None)
            assert proc.returncode == 0 and envelope.get('ok') is True and stored, proc.stderr[-800:]
            flip_started = time.monotonic()
            page.wait_for("document.getElementById('view-policy-store').dataset.state === 'stored'", timeout=30)
            result['page_flip_seconds'] = round(time.monotonic() - flip_started, 3)
            after = page_state(page)
            page.screenshot(ev / 'policy-store110-after.png')
            result['page_after'] = after
            assert after['kind'] == before['kind'] and after['status'] == 'failed'
            assert 'holds this policy with the recorded digest' in after['policy_store'] and 'next:' not in after['policy_store']
            assert 'training itself finished' in after['note'] and after['trainer_copy_status'] == 'retained'
            result['no_navigation'] = page.evaluate('performance.getEntriesByType("navigation").length') == 1
            # A fresh visit keeps the current-run rule and shows the stored state.
            fresh = browser.page(url)
            fresh.evaluate('window.cadexReview.ready', await_promise=True)
            result['fresh_visit_after_default_run'] = fresh.text('#view-kind')
            fresh.click("#views li[data-run=%s]" % json.dumps(name))
            fresh.wait_for("document.getElementById('view-policy-store').dataset.state === 'stored'")
            result['fresh_visit_after_policy_store'] = fresh.text('#view-policy-store')
        manifest_after = read(p / 'script.json')
        assets_after = inventory(p / 'assets')
        result.update(
            record_bytes_unchanged=(run / 'run.json').read_bytes() == record_bytes_before,
            runs_files_unchanged=inventory(p / 'runs') == runs_before, runs_files=len(runs_before),
            assets_added=sorted(set(assets_after) - set(assets_before)),
            assets_prior_unchanged=all(assets_after.get(k) == v for k, v in assets_before.items()),
            stored_asset_sha256_matches=assets_after.get(policy_name) == policy_sha,
            accepted_identity_unchanged=(manifest_after['accepted_revision'], manifest_after['accepted_digest'])
                == (manifest_before['accepted_revision'], manifest_before['accepted_digest']),
            service_pid_after=service_pid()[0], trainers_seen=trainers(),
        )
        result['ok'] = all([result['record_bytes_unchanged'], result['runs_files_unchanged'],
                            result['assets_added'] == [policy_name], result['assets_prior_unchanged'],
                            result['stored_asset_sha256_matches'], result['accepted_identity_unchanged'],
                            result['service_pid_after'] == pid_before, result['no_navigation'],
                            result['trainers_seen'] == []])
    finally:
        save(ev / 'policy-store110-evidence.json', result)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()
