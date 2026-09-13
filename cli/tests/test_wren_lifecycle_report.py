# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hold Wren's user-facing lifecycle claims to retained evidence, without training."""
import json
import re

from conftest import REPO_ROOT

ROOT = REPO_ROOT / 'docs/probes/wren-fresh'


def test_report_links_all_criteria_and_resolves_local_evidence():
    text = (ROOT / 'LIFECYCLE.md').read_text()
    assert set(re.findall(r'\| \*\*(D\d+) —', text)) == {f'D{i}' for i in range(1, 12)}
    for link in re.findall(r'\]\(([^)]+)\)', text):
        assert (ROOT / link.split('#')[0]).is_file(), link
    assert '12 updates' in text and 'unequal training budgets' in text
    assert 'wren71 has no five-seed' in text
    assert 'Wren missing/partial/failed video repeat' in text
    assert 'not a new equivalent-framing assessment' in text


def test_comparison_rows_match_browser_models_policies_and_videos():
    receipt = json.loads((ROOT / 'lifecycle72-evidence.json').read_text())
    prose = (ROOT / 'LIFECYCLE.md').read_text()
    for filename in ('comparison-evidence.json', 'revision66-evidence.json'):
        evidence = json.loads((ROOT / filename).read_text())
        for name, run in evidence['runs'].items():
            if name not in receipt['views']:
                continue
            view = receipt['views'][name]
            assert view['revision'] == run['accepted_revision']
            assert view['digest'] == run['accepted_digest']
            assert view['policy_sha256'] == run['video']['policy_sha256']
            assert view['video_sha256'] == run['video']['sha256']
            rows = run['evaluation']['rows']
            assert [r['seed'] for r in rows] == list(range(5))
            assert all(r['policy_sha256'] == view['policy_sha256'] for r in rows)
            displacement = sum(r['displacement_x_mm'] for r in rows) / len(rows)
            row = next(line for line in prose.splitlines() if line.startswith('| ' + name + ' |'))
            columns = [s.strip() for s in row.strip('|').split('|')]
            assert float(columns[1]) == view['foot_len_mm']
            assert float(columns[2].replace('−', '-')) == round(displacement, 3)
            assert int(columns[4]) == sum(r['fell'] for r in rows)
            mean, minimum = map(float, columns[3].split('/'))
            assert mean == sum(r['survival_s'] for r in rows) / len(rows)
            assert minimum == min(r['survival_s'] for r in rows)


def test_current_repeat_is_separate_from_historical_comparison():
    receipt = json.loads((ROOT / 'lifecycle72-evidence.json').read_text())
    repeat = json.loads((ROOT / 'training71-evidence.json').read_text())
    assert receipt['current'] == 'wren71-final'
    assert receipt['run_count'] == 18
    assert set(receipt['views']) == {'wren1-final', 'wren2-final', 'wren57-retry',
                                     'wren66-checkpoint20', 'wren66-final', 'wren71-final'}
    assert {v['style_sha256'] for v in receipt['views'].values()} == {
        '27893221b3c6cf784d62c16fdaa5c88d1beb031bcb195e5f34e1598ea56e5b0c'}
    assert receipt['persistent_private_address_same_machine']
    assert receipt['return_to_current'] and receipt['navigations'] == 1
    assert receipt['run_asset_files_unchanged'] > 465
    for name, view in receipt['views'].items():
        assert view['components'] == 8
        assert view['orbit_zoom'] and view['playback_download_poll_preserved']
        assert view['relation'] == ('current' if name == receipt['current'] else 'historical')
        assert 'DECISIONS.md' in view['documents']
        assert len(view['style_sha256']) == 64
        assert len(set(view['history_points'].values())) == 1
    assert receipt['views']['wren57-retry']['history_points']['curve'] == 12
    assert receipt['views']['wren66-final']['history_points']['curve'] == 240
    current = receipt['views'][receipt['current']]
    assert current['revision'] == repeat['completion_browser']['view-revision']
    assert current['history_points']['curve'] == 240


def test_wren_video_faults_preserve_history_and_operator():
    receipt = json.loads((ROOT / 'video75-evidence.json').read_text())
    assert receipt['current'] == 'wren71-final'
    assert receipt['prior'] == 'wren66-final'
    assert receipt['operator_unchanged'] and receipt['same_machine_private_address']
    assert receipt['original_files_unchanged'] == receipt['copy_restored_files'] > 703
    assert receipt['baseline'] == receipt['restored'] == receipt['operator']
    assert receipt['operator']['playback_poll_preserved']
    historical = json.loads((ROOT / 'lifecycle72-evidence.json').read_text())['views']['wren66-final']
    assert [f['fault'] for f in receipt['faults']] == ['missing', 'partial', 'failed']
    for fault, label in zip(receipt['faults'], ['missing', 'digest mismatch', 'injected encoder failure']):
        assert fault['http_status'] == 404
        assert fault['unavailable'] and fault['cli_guidance']
        assert label in fault['label'] and 'Retry the CLI video command' in fault['label']
        assert fault['prior']['playback_poll_preserved']
        assert fault['prior']['revision'] == historical['revision']
        assert fault['prior']['policy_sha256'] == historical['policy_sha256']
        assert fault['prior']['download_sha256'] == historical['video_sha256']
    assert set(receipt['screenshots']) == {'missing.png', 'partial.png', 'failed.png'}
