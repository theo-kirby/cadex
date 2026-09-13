# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The committed second-fresh-project lifecycle receipt stays consistent
with its claims.

``docs/probes/wren-fresh/lifecycle.py`` reopens a run-less agent-authored
project copy through two fresh engine processes, inspects the original on the persistent
operator server over the private-network address, and proves the earlier
Reed projects unchanged by hash inventory. ``evidence.json`` is that receipt
for ``ot5-wren``, committed without its images. The project lives outside
this checkout, so these tests hold the receipt to itself and to the documents
that cite it: an accepted revision with no runs is the current view, every
declared parameter reached the page, the model was drawn and orbited, the
poll kept the empty run state, and the previous projects were intact.
Nothing here needs a browser, an engine or the project.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from conftest import REPO_ROOT

PROBE = REPO_ROOT / "docs" / "probes" / "wren-fresh"


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads((PROBE / "evidence.json").read_text())


def test_receipt_names_a_fresh_accepted_project_with_no_runs(receipt):
    assert receipt["project"] == "ot5-wren"
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["accepted_revision"])
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["accepted_digest"])
    assert receipt["api_runs"] == 0
    state = receipt["page_state"]
    assert state["selected"] == "accepted" and state["runs"] == []
    assert not state["stale"] and state["error"] is None


def test_every_declared_parameter_reached_the_page(receipt):
    values = receipt["param_values"]
    assert receipt["params_shown"] == len(values) >= 12
    for name in ("torso_w", "thigh_len", "shin_len", "foot_len", "policy_on", "printed_density"):
        assert name in values, name
    assert values["policy_on"] == 0


def test_the_model_was_drawn_and_orbited_over_the_private_address(receipt):
    assert receipt["url_host"].endswith(":8765") and not receipt["url_host"].startswith("127.")
    model = receipt["model"]
    assert model["components"] == 8 and model["triangles"] > 0 and model["drawn_pixels"] > 1000
    assert model["style"] == "cadex-prototype-light-v1"
    orbit = receipt["orbit"]
    assert orbit["after_drag"]["yaw"] != orbit["default"]["yaw"]
    assert orbit["after_drag"]["distance"] == orbit["default"]["distance"]
    assert orbit["after_zoom"]["distance"] < orbit["after_drag"]["distance"]
    assert orbit["drawn_pixels"] > 1000
    assert receipt["private_address_same_machine"] is True
    assert set(receipt["screenshots"]) == {"persistent-accepted.png", "persistent-page.png"}


def test_two_engine_reopens_restored_the_accepted_revision(receipt):
    assert receipt["engine_reopen_scope"] == "disposable full copy; served project byte-checked"
    opens = receipt["engine_opens"]
    assert len(opens) == 2 and opens[0]["pid"] != opens[1]["pid"]
    assert all(item["matches_accepted"] is True for item in opens)
    assert receipt["retained_files"] > 0


def test_the_earlier_reed_projects_were_intact(receipt):
    intact = receipt["intact"]
    assert set(intact) >= {"ot5-biped", "ot5-biped-copy29"}
    assert all(item["unchanged"] is True and item["files"] > 0 for item in intact.values())


def test_documents_cite_the_receipt(receipt):
    readme = (PROBE / "README.md").read_text()
    operator = (REPO_ROOT / "docs" / "probes" / "operator-review" / "README.md").read_text()
    review = (REPO_ROOT / "docs" / "HEADLESS-BIPED-REVIEW.md").read_text()
    short = receipt["accepted_revision"][:12]
    assert short in readme and "ot5-wren" in readme
    assert "ot5-wren" in operator and short in operator
    assert "ot5-wren" in review and short in review


def test_inventory_excludes_only_invocation_outputs(tmp_path):
    # Load the helper without executing the real-project command-line probe.
    import ast
    import hashlib

    tree = ast.parse((PROBE / 'lifecycle.py').read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'inventory')
    namespace = {'hashlib': hashlib}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), '<inventory>', 'exec'), namespace)
    inventory = namespace['inventory']
    current = tmp_path / 'evidence' / 'current'
    previous = tmp_path / 'evidence' / 'previous'
    current.mkdir(parents=True)
    previous.mkdir()
    (previous / 'retained.png').write_bytes(b'old evidence')
    (tmp_path / 'script.py').write_text('accepted source')
    before = inventory(tmp_path, exclude=current)
    (current / 'screenshot.png').write_bytes(b'new output')
    assert inventory(tmp_path, exclude=current) == before
    (previous / 'retained.png').write_bytes(b'changed evidence')
    assert inventory(tmp_path, exclude=current) != before
    assert 'script.py' in before and 'evidence/previous/retained.png' in before


def test_retraining_comparison_uses_the_declared_seeds_and_retained_models():
    evidence = json.loads((PROBE / 'comparison-evidence.json').read_text())
    assert evidence['protocol'] == dict(seeds=list(range(5)), episode_seconds=8,
                                       control_hz=50, training_iterations=240,
                                       environments=1024, training_seed=0)
    assert evidence['original_run_files_preserved'] == 114
    assert 'not product-agent authorship' in evidence['design_authorship']
    runs = evidence['runs']
    assert set(runs) == {'wren1-checkpoint20', 'wren1-final',
                         'wren2-checkpoint20', 'wren2-final'}
    model_ids = {}
    for name, item in runs.items():
        evaluation = item['evaluation']
        assert evaluation['source_run_unchanged'] and evaluation['seed_zero_trace_identical']
        rows = evaluation['rows']
        assert [row['seed'] for row in rows] == list(range(5))
        for row in rows:
            assert row['survival_s'] == pytest.approx(row['step_count'] / 50)
            assert row['fell'] == (row['termination'] == 'fell')
            assert row['fell'] or row['survival_s'] == 8
            assert row['policy_sha256'] == item['video']['policy_sha256']
            assert row['task_sha256'] == item['video']['task_sha256']
            assert row['foot_len_mm'] == (85 if name.startswith('wren1-') else 105)
        assert len({row['model_sha256'] for row in rows}) == 1
        model_ids[name] = rows[0]['model_sha256']
        assert item['summary']['falls'] == sum(row['fell'] for row in rows)
        assert item['summary']['mean_survival_s'] == pytest.approx(sum(row['survival_s'] for row in rows)/5)
        assert item['browser']['browser_playback']
        assert item['browser']['download_sha256'] == item['video']['sha256']
        if name.startswith('wren1-'):
            assert item['browser']['fresh_selection'] == 'RUN wren2-final'
    assert model_ids['wren1-checkpoint20'] == model_ids['wren1-final']
    assert model_ids['wren2-checkpoint20'] == model_ids['wren2-final']
    assert model_ids['wren1-final'] != model_ids['wren2-final']


def test_revised_checkpoint_was_played_during_real_bounded_training():
    evidence = json.loads((PROBE / 'retraining-evidence.json').read_text())
    assert evidence['training_exit'] == evidence['observer_exit'] == 0
    # Trainer iterations are zero-based: 0..239 is the declared 240 updates.
    assert evidence['trainer_final']['iteration'] + 1 == 240
    assert evidence['trainer_final']['state'] == 'done'
    assert evidence['resource_bound']['MemoryMax'] == str(20 * 1024**3)
    mid = evidence['intermediate']
    assert mid['trainer_active_after_browser'] and mid['browser_check_exit'] == 0
    assert mid['after'] > mid['before']
    assert mid['witness']['witness_error'] < mid['witness']['witness_tolerance']
    assert evidence['live_browser']['ok'] and evidence['live_browser']['reload_count'] == 1
    assert len(evidence['live_browser']['page_iterations']) >= 7
    assert all(0 <= x['committed_to_page_s'] < 5 for x in evidence['live_browser']['first_seen'].values())
    assert evidence['policies']['wren2-final']['browser']['fresh_selection'] == 'RUN wren2-final'


def test_agent_revision_comparison_retains_both_designs_on_the_declared_seeds():
    """``report_revision.py`` output for the working copy: the product-agent's
    90 mm revision (wren66) against the 110 mm retry it was made from, each
    evaluated on seeds 0-4 from its own retained model, task and policy."""
    evidence = json.loads((PROBE / 'revision66-evidence.json').read_text())
    assert evidence['schema'] == 'wren-revision-comparison-v1'
    assert evidence['project'] == 'ot5-wren-copy54'
    assert evidence['protocol'] == dict(seeds=list(range(5)), episode_seconds=8,
                                       control_hz=50, training_iterations=240,
                                       environments=1024, training_seed=0)
    assert evidence['before_inventory_preserved'] and evidence['before_inventory_files'] == 465
    runs = evidence['runs']
    assert set(runs) == {'wren57-retry', 'wren66-checkpoint20', 'wren66-final'}
    foot = {'wren57-retry': 110, 'wren66-checkpoint20': 90, 'wren66-final': 90}
    model_ids = {}
    for name, item in runs.items():
        evaluation = item['evaluation']
        assert evaluation['run'] == name
        assert evaluation['source_run_unchanged'] and evaluation['seed_zero_trace_identical']
        rows = evaluation['rows']
        assert [row['seed'] for row in rows] == list(range(5))
        for row in rows:
            assert row['survival_s'] == pytest.approx(row['step_count'] / 50)
            assert row['fell'] == (row['termination'] == 'fell')
            assert row['fell'] or row['survival_s'] == 8
            assert row['foot_len_mm'] == foot[name] == item['params']['values']['foot_len']
            assert row['policy_sha256'] == item['video']['policy_sha256']
            assert row['task_sha256'] == item['video']['task_sha256']
        assert len({row['model_sha256'] for row in rows}) == 1
        model_ids[name] = rows[0]['model_sha256']
        assert item['summary']['falls'] == sum(row['fell'] for row in rows)
        assert item['summary']['mean_survival_s'] == pytest.approx(sum(row['survival_s'] for row in rows) / 5)
        assert item['summary']['min_displacement_x_mm'] == min(row['displacement_x_mm'] for row in rows)
        assert item['video']['sim_seconds'] == pytest.approx(rows[0]['survival_s'])
        assert item['browser']['browser_playback']
        assert item['browser']['download_sha256'] == item['video']['sha256']
        assert item['browser']['foot_len_mm'] == foot[name]
        assert item['evidence_directory'].startswith('evidence/comparison66/')
    # Each playback declares its own policy and rollout, so playback revisions
    # and digests differ; the shared identity is the trained model itself.
    assert runs['wren66-checkpoint20']['accepted_revision'] != runs['wren66-final']['accepted_revision']
    assert model_ids['wren66-checkpoint20'] == model_ids['wren66-final'] != model_ids['wren57-retry']
    assert runs['wren57-retry']['accepted_revision'] != runs['wren66-final']['accepted_revision']
    assert 'product-agent-authored revision' in runs['wren66-final']['authored_by']
    assert runs['wren57-retry']['authored_by'] is None
    # A new visit selects the latest attempt; the retry stays selectable as history.
    assert runs['wren66-final']['browser']['fresh_selection'] == 'RUN wren66-final'
    # ...and while training was active, return-to-current went to the live run.
    assert runs['wren66-checkpoint20']['browser']['returned_to_current'] == 'RUN wren66'


def test_checkpoint_provenance_receipt_matches_the_declared_runs():
    """ADR-309's persistent-URL receipt: the final playback resolves every
    checkpoint through its recorded training run, the checkpoint playback's
    frozen snapshot lists none, and the in-place retry keeps its own."""

    receipt = json.loads((PROBE / 'checkpoint67-evidence.json').read_text())
    assert receipt['schema'] == 'cadex-checkpoint-provenance-evidence-v1' and receipt['project'] == 'ot5-wren-copy54'
    runs = receipt['runs']
    final, checkpoint, retry = runs['wren66-final'], runs['wren66-checkpoint20'], runs['wren57-retry']
    assert final['default_view'] == 'RUN wren66-final' and final['relation'].startswith('CURRENT')
    assert final['checkpoint_source'] == {'state': 'resolved', 'run': 'wren66'}
    assert final['checkpoint_statuses'] == [['retained', 'wren66']] and final['checkpoint_count'] == 12
    assert checkpoint['relation'].startswith('HISTORICAL') and checkpoint['telemetry_state'] == 'stale'
    assert checkpoint['checkpoint_source'] == {'state': 'resolved', 'run': 'wren66'}
    assert checkpoint['checkpoints_reported'] is False and checkpoint['checkpoint_count'] == 0
    assert retry['relation'].startswith('HISTORICAL') and retry['checkpoint_source'] == {'state': 'none', 'run': ''}
    assert retry['checkpoint_statuses'] == [['retained', 'run']]
    assert all(run['returned_to'] == 'RUN wren66-final' for run in runs.values())


def test_restart_receipt_preserves_every_run_across_engine_reopen_and_service_restart():
    """The D6 receipt on the served working copy: two in-place engine reopens
    and one real restart of the persistent user service changed nothing a
    reader sees — the same fresh-visit default, every run's identity, curves
    and videos, the open page's selection and playing video — and the trainer
    process list was empty before and after."""

    receipt = json.loads((PROBE / 'restart69-evidence.json').read_text())
    assert receipt['schema'] == 'cadex-restart-evidence-v1' and receipt['project'] == 'ot5-wren-copy54'
    assert receipt['unit'] == 'cadex-operator-review' and receipt['url_host'].endswith(':8765')
    assert re.fullmatch(r'[0-9a-f]{64}', receipt['accepted_revision'])
    assert receipt['fresh_default_before'] == receipt['fresh_default_after'] == 'RUN wren66-final'
    assert receipt['walk_after_equals_before'] is True and receipt['api_unchanged_across_restart'] is True
    assert receipt['open_page'] == {'recovered_without_navigation': True, 'selected': 'wren66-final', 'video_kept_playing': True}
    assert receipt['trainers_before'] == receipt['trainers_after'] == []

    opens = receipt['engine_opens']
    assert len(opens) == 2 and opens[0]['pid'] != opens[1]['pid']
    assert all(o['restore'] == {'digest': receipt['accepted_digest'], 'matches_accepted': True, 'performed': True} for o in opens)
    reopen = receipt['engine_reopen']
    assert reopen['accepted_attempt_files_unchanged'] and reopen['other_files_unchanged'] and reopen['manifest_changed']
    accepted_dir = receipt['accepted_attempt']['staging'].rsplit('/', 1)[1]
    assert accepted_dir in reopen['candidate_attempts_after']
    assert len(reopen['candidate_attempts_after']) <= 4  # the pinned accepted attempt plus ATTEMPT_KEEP (ADR-045)
    assert reopen['candidate_files_added'] == reopen['candidate_files_pruned'] > 0

    restart = receipt['restart']
    assert restart['old_pid'] != restart['new_pid'] and restart['systemctl_exit'] == 0
    assert 0 < restart['answered_after_s'] < 5 and restart['stale_seen_after_s'] is not None

    current, historical = receipt['download_after']
    assert current == receipt['download_before'] and current['run'] == 'wren66-final'
    assert historical['run'] == receipt['historical_run'] != current['run']
    assert historical['accepted_revision'] != current['accepted_revision']
    assert all(re.fullmatch(r'[0-9a-f]{64}', d['sha256']) for d in (current, historical))

    runs = receipt['run_identities']
    assert len(runs) == receipt['runs'] == 15
    assert [r for r, s in runs.items() if s['relation'] == 'current'] == ['wren66-final']
    assert all(s['relation'] == 'historical' for r, s in runs.items() if r != 'wren66-final')
    assert {r for r, s in runs.items() if s['telemetry'] == 'failed'} == {'wren56-interrupt', 'wren56b-interrupt', 'wren56c-interrupt', 'wren57-interrupt'}
    assert all(len(s['points']) == 3 and min(s['points']) > 0 for s in runs.values())
    assert runs['wren66-final']['videos'] == [current['sha256']] and runs[historical['run']]['videos'] == [historical['sha256']]
    walk = receipt['page_walk']
    assert walk['accepted']['kind'] == 'ACCEPTED NOW' and set(walk) == {'accepted', *runs}
    for run, summary in runs.items():
        assert walk[run]['kind'] == 'RUN ' + run and walk[run]['telemetry'] == summary['telemetry']
        assert walk[run]['points'] == [str(n) for n in summary['points']] and walk[run]['videos'] == len(summary['videos'])
    for doc in ('RESTART.md', 'README.md'):
        assert 'restart69-evidence.json' in (PROBE / doc).read_text() or 'RESTART.md' in (PROBE / doc).read_text()
    assert 'restart69-evidence.json' in (PROBE / 'RESTART.md').read_text()
