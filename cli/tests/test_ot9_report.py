# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""B5: the closing report says what the receipts say.

The report's seed table, accepted identity and run list are recomputed from
the retained receipts, so a number edited on the page alone fails here. The
final reopen receipt must rebuild the revision B4 measured, on the policy,
model and task the evaluation ran, and reproduce seed 9's trace exactly.
"""
import json
import re
from pathlib import Path

OT9 = Path(__file__).resolve().parents[2] / 'docs/probes/ot9'


def _load(name):
    return json.loads((OT9 / 'retained' / name).read_text())


def _report():
    return (OT9 / 'REPORT.md').read_text()


def test_the_seed_table_is_the_evaluation_receipt():
    rows = _load('r4-robin-eval-1.json')['evaluation']['seeds']
    table = [line for line in _report().splitlines() if re.match(r'^\| \d \| ', line)]
    assert len(table) == len(rows) == 10
    for line, r in zip(table, rows):
        expected = '| %d | %.1f s | %s | %.3f° @ %.2f s | %.2f mm | %.2f | %.0f mm | `%s` |' % (
            r['seed'], r['duration_s'], 'truncated' if r['truncated'] else r['termination'],
            r['peak_tilt_degrees'], r['peak_tilt_time_s'], r['min_chassis_height_mm'],
            r['total_reward'], r['chassis_xy_drift_max_mm'], r['trace_sha256'][:8])
        assert line == expected


def test_the_final_reopen_rebuilds_what_b4_measured_on_the_evaluated_identity():
    contract = json.loads((OT9 / 'contract.json').read_text())
    final = _load('r6-robin-final.json')['reopen']
    fit = _load('r5-robin-fit.json')['final']
    evaluation = _load('r4-robin-eval-1.json')
    seed9 = evaluation['evaluation']['seeds'][9]
    assert final['exit_code'] == 0
    assert (final['accepted_revision'], final['accepted_digest']) == (
        final['expected']['accepted_revision'], final['expected']['accepted_digest'])
    assert final['accepted_revision'] == seed9['accepted_revision']
    assert final['accepted_digest'] == seed9['accepted_digest']
    assert (fit['accepted_revision'], fit['accepted_digest']) == (
        final['accepted_revision'], final['accepted_digest'])
    assert (fit['mjcf_sha256'], fit['task_sha256']) == (final['mjcf_sha256'], final['task_sha256'])
    mjcf, task = contract['baseline']['mjcf']['sha256'], contract['baseline']['task']['sha256']
    receipt = final['policy_receipt']
    assert receipt == {k: evaluation['reopen']['policy_receipt'][k] for k in receipt}
    assert receipt['policy_sha256'] == final['stored_policy_sha256'] == seed9['policy_sha256']
    assert (receipt['model_sha256'], final['mjcf_sha256']) == (mjcf, mjcf)
    assert (receipt['task_sha256'], final['task_sha256']) == (task, task)
    assert receipt['witness_error'] < receipt['witness_tolerance']
    assert final['trace_sha256'] == seed9['trace_sha256']
    assert final['reader']['pass'] and final['reader']['peak_tilt_degrees'] == seed9['peak_tilt_degrees']


def test_the_report_names_every_identity_run_and_the_checkpoint_choice():
    report = _report()
    final = _load('r6-robin-final.json')['reopen']
    trained = _load('r3-robin-train-1.json')['training']
    for digest in (final['accepted_revision'], final['accepted_digest'], final['stored_policy_sha256'],
                   final['mjcf_sha256'], final['task_sha256'], final['policy_receipt']['sha256']):
        assert f'`{digest}`' in report
    for receipt in ('r2-robin-no-policy.json', 'r3-robin-train-1.json',
                    'r4-robin-eval-1.json', 'r5-robin-fit.json', 'r6-robin-final.json'):
        assert f'(retained/{receipt})' in report
    assert trained['policy']['checkpoint'].startswith('final iteration')
    assert trained['best_checkpoint']['installed'] is False
    assert trained['best_checkpoint']['sha256'][:8] in report
    assert '**interrupted**' in report and 'No mechanical, task or reward change' in report


def test_the_suite_counts_on_the_page_are_the_receipt():
    regressions = _load('r6-robin-final.json')['regressions']
    for key in ('engine', 'cli'):
        suite = regressions[key]
        assert suite['failed'] == 0
        assert f"`{suite['command']}`: {suite['passed']} passed, {suite['skipped']} skipped" in _report()
