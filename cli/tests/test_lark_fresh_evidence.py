# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The committed third-fresh-project create/save/reopen receipt stays
consistent with its claims.

``docs/probes/lark-fresh/create_reopen.py`` takes a project that one
``cadex -p`` turn created and accepted, records what the persistent operator
server and a headless browser show for it, reopens it in place through two
fresh engine processes, and checks the open page after a poll and a fresh
visit against that record. ``evidence.json`` is that receipt for
``ot5-lark``, committed without its images. The project lives outside this
checkout, so these tests hold the receipt to itself and to the documents that
cite it: a fresh accepted design with no runs and no reference to an earlier
project, every declared parameter and component on the page, identical
served meshes, placements and viewer statistics before and after the reopen,
and the earlier projects untouched. Nothing here needs a browser, an engine
or the project.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from conftest import REPO_ROOT

PROBE = REPO_ROOT / "docs" / "probes" / "lark-fresh"
HEX64 = r"[0-9a-f]{64}"
DECLARED = ("torso_w", "torso_d", "torso_h", "thigh_len", "shin_len", "limb_w",
            "foot_len", "foot_w", "foot_t", "hip_spacing", "printed_density", "policy_on")


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads((PROBE / "evidence.json").read_text())


def test_one_fresh_agent_turn_created_and_accepted_the_project(receipt):
    assert receipt["project"] == "ot5-lark"
    assert re.fullmatch(HEX64, receipt["accepted_revision"])
    assert re.fullmatch(HEX64, receipt["accepted_digest"])
    creation = receipt["creation"]
    assert creation["exit"] == 0 and creation["session_id"]
    assert creation["finished"] > creation["started"]
    assert creation["foreign_references_in_script"] is False
    assert creation["runs"] == 0 and creation["policies"] == 0
    assert re.fullmatch(HEX64, creation["prompt_sha256"])
    state = receipt["page_state"]
    assert state["selected"] == "accepted" and state["runs"] == []
    assert not state["stale"] and state["error"] is None


def test_every_declared_parameter_reached_the_page(receipt):
    values = receipt["param_values"]
    assert set(receipt["declared_params"]) >= set(DECLARED)
    assert values["policy_on"] == 0
    for view in ("before_reopen", "after_reopen_poll", "after_reopen_fresh_visit"):
        assert receipt[view]["params_shown"] == len(values) >= 12


def test_components_and_meshes_are_the_same_before_and_after_the_reopen(receipt):
    before = receipt["before_reopen"]
    served = receipt["served_model"]
    assert served["revision"] == receipt["accepted_revision"]
    assert served["digest"] == receipt["accepted_digest"]
    assert sorted(before["components"]) == sorted(served["components"])
    assert len(served["components"]) >= 7
    for component in served["components"].values():
        assert re.fullmatch(HEX64, component["mesh_sha256"])
        assert len(component["placement"]["position_mm"]) == 3
        assert len(component["placement"]["rotation_xyzw"]) == 4
    assert before["stats"]["components"] == len(served["components"])
    assert before["stats"]["triangles"] > 0 and before["drawn_pixels"] > 1000
    assert before["stats"]["style"] == "cadex-prototype-light-v1"
    for view in ("after_reopen_poll", "after_reopen_fresh_visit"):
        after = receipt[view]
        assert after["components"] == before["components"]
        assert after["stats"] == before["stats"]
        assert after["decisions"] == before["decisions"]
        assert after["documents"] == before["documents"]
        assert after["drawn_pixels"] > 1000
    assert receipt["served_model_unchanged_after_reopen"] is True
    assert receipt["viewport_png_identical"] is True


def test_two_in_place_engine_reopens_kept_the_accepted_identity(receipt):
    assert receipt["engine_reopen_scope"] == "in place; retained accepted artifacts byte-checked"
    opens = receipt["engine_opens"]
    assert len(opens) == 2 and opens[0]["pid"] != opens[1]["pid"]
    assert all(item["matches_accepted"] is True for item in opens)
    assert receipt["retained_attempt_files"] > 0
    changed = receipt["files_changed_by_reopen"]
    assert changed["accepted_attempt_files"] == 0 and changed["source_history_document_files"] == 0
    assert receipt["staging_dir_is_accepted_revision"] is True
    assert receipt["retained_files"] > receipt["retained_attempt_files"]


def test_the_model_was_orbited_over_the_private_address(receipt):
    assert receipt["url_host"].endswith(":8765")
    assert not receipt["url_host"].startswith(("127.", "localhost", "[::1]"))
    assert receipt["private_address_same_machine"] is True
    orbit = receipt["orbit"]
    assert orbit["after_drag"]["yaw"] != orbit["default"]["yaw"]
    assert orbit["after_drag"]["distance"] == orbit["default"]["distance"]
    assert orbit["after_zoom"]["distance"] < orbit["after_drag"]["distance"]
    assert set(receipt["screenshots"]) == {"before-reopen-accepted.png", "before-reopen-page.png",
                                           "after-reopen-accepted.png", "after-reopen-page.png", "pre-fix-page.png"}
    assert receipt["screenshots"]["before-reopen-accepted.png"] == receipt["screenshots"]["after-reopen-accepted.png"]


def test_the_dashboard_defects_after_creation_are_recorded_with_their_remedy(receipt):
    after = receipt["after_creation"]
    pre = after["pre-fix"]
    assert pre["api_model"]["available"] is False
    assert pre["api_model"]["reason"] == "accepted attempt's staging does not belong to the accepted revision"
    assert pre["staging_dir_revision"] != receipt["accepted_revision"]
    assert pre["attempt_result_digest"] == receipt["accepted_digest"]
    assert pre["staging_has_display"] is False
    assert pre["page"]["model_state"] == "missing" and pre["page"]["components_listed"] == 0
    assert pre["page"]["params_shown"] == len(receipt["param_values"])
    fixed = after["post-fix-pre-render"]
    assert fixed["available"] is False and fixed["reason"] == "accepted attempt retained no tessellation"
    render = after["render"]
    assert render["ok"] and render["exit"] == 0
    assert render["accepted_revision_unchanged"] and render["digest_unchanged"]


def test_the_earlier_projects_were_intact(receipt):
    intact = receipt["intact"]
    assert set(intact) >= {"ot5-wren-copy54", "ot5-wren", "ot5-biped"}
    assert all(item["unchanged"] is True and item["files"] > 0 for item in intact.values())


def test_documents_cite_the_receipt(receipt):
    readme = (PROBE / "README.md").read_text()
    operator = (REPO_ROOT / "docs" / "probes" / "operator-review" / "README.md").read_text()
    review = (REPO_ROOT / "docs" / "HEADLESS-BIPED-REVIEW.md").read_text()
    short = receipt["accepted_revision"][:12]
    for text in (readme, operator, review):
        assert "ot5-lark" in text and short in text


def test_the_probe_rejects_scripts_that_name_an_earlier_project():
    import ast

    tree = ast.parse((PROBE / "create_reopen.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "FOREIGN")
    foreign = re.compile(ast.literal_eval(node.value.args[0]), re.IGNORECASE)
    assert foreign.search("link('ot5-wren', ...)")
    assert foreign.search("# ported from Reed")
    assert foreign.search("mg_legs") and foreign.search("cdx-rl/checkpoints")
    assert not foreign.search("lark = assembly.assemble(...)  # torso, thigh, shin, foot")
    assert not foreign.search('assembly.policy(walk_task, weights="walk.cxpolicy")')


def test_lark_checkpoint_was_played_during_real_bounded_training():
    """``training-evidence.json`` is the receipt of Lark's first real GPU run.

    ``docs/probes/lark-fresh/train.py`` trains the accepted Lark design
    offboard under the declared bounds, publishes checkpoint 20 as a verified
    rollout and video while the trainer is still iterating, observes the
    persistent operator page over the private address as it updates, and
    retains the final policy's video. The receipt is held to those claims:
    real device, exit 0, the declared 240 updates, the 20 GB host bound, a
    witness-verified checkpoint whose browser check passed with the trainer
    still active, at least seven live page updates without a reload and each
    within five seconds of the trainer's commit, and both policies measured on
    the same seed and episode limit with decoded, downloaded videos. Nothing
    here needs a browser, an engine, a GPU or the project.
    """
    evidence = json.loads((PROBE / "training-evidence.json").read_text())
    assert evidence["schema"] == "lark-training-evidence-v1"
    assert evidence["project"] == "ot5-lark" and evidence["run"] == "lark1"
    assert set(evidence["geometry"]) == {"lark_model-model.xml", "walk_task-task.json"}
    assert evidence["training_exit"] == evidence["observer_exit"] == 0
    final = evidence["trainer_final"]
    # Trainer iterations are zero-based: 0..239 is the declared 240 updates.
    assert final["iteration"] + 1 == 240 and final["state"] == "done" and final["device"] == "gpu"
    assert evidence["resource_bound"]["MemoryMax"] == str(20 * 1024**3)
    assert evidence["memory"]["host_peak_bytes"] < 20 * 1024**3
    assert evidence["training_wall_seconds"] < 1800
    mid = evidence["intermediate"]
    assert mid["run"] == "lark1-checkpoint20"
    assert mid["trainer_active_after_browser"] and mid["browser_check_exit"] == 0
    assert mid["before"] < 20 <= mid["render_before"] <= mid["render_after"] <= mid["after"]
    assert mid["witness"]["witness_error"] < mid["witness"]["witness_tolerance"]
    assert mid["overhead"]["during_window"]["count"] >= 1
    live = evidence["live_browser"]
    assert live["ok"] and live["reload_count"] == 1 and live["orbit_zoom"]
    assert live["default_view_kind"] == "RUN lark1"
    assert len(live["page_iterations"]) >= 7
    assert all(0 <= x["committed_to_page_s"] < 5 for x in live["first_seen"].values())
    policies = evidence["policies"]
    assert set(policies) == {"lark1-checkpoint20", "lark1-final"}
    for name, policy in policies.items():
        assert re.fullmatch(HEX64, policy["policy_sha256"])
        assert policy["seed"] == 0 and policy["episode_limit_s"] == 8
        assert 0 < policy["observed_s"] <= 8
        assert policy["fell"] == (policy["termination"] == "fell")
        assert policy["fell"] != policy["time_limit_reached"]
        browser = policy["browser"]
        assert browser["browser_playback"] and browser["decoded_frames"] == policy["video"]["frames"]
        assert browser["download_sha256"] == policy["video"]["sha256"]
        assert browser["policy_sha256"] == policy["policy_sha256"]
        assert abs(browser["simulation_seconds"] - policy["observed_s"]) < 1e-6
        assert browser["style"] == "cadex-prototype-light-v1"
    assert policies["lark1-checkpoint20"]["browser"]["fresh_selection"] == "RUN lark1"
    assert policies["lark1-final"]["browser"]["fresh_selection"] == "RUN lark1-final"
    assert policies["lark1-final"]["browser"]["historical_selection"] == "lark1-checkpoint20"
    assert policies["lark1-final"]["policy_sha256"] != policies["lark1-checkpoint20"]["policy_sha256"]
    assert "training-evidence.json" in (PROBE / "README.md").read_text()


def test_lark_revision_retraining_played_its_checkpoint_during_real_training():
    """``training84-evidence.json`` is the receipt of ``lark2``, the retraining
    of the product agent's 45 mm-torso revision under the ``lark1`` bounds:
    the agent's revision as the training identity, a different model and task
    from ``lark1``, exit 0 on the GPU, live page updates within five seconds,
    a checkpoint published while the trainer was active, and both policies
    surviving the full seed-0 episode with decoded, downloaded videos."""
    evidence = json.loads((PROBE / "training84-evidence.json").read_text())
    first = json.loads((PROBE / "training-evidence.json").read_text())
    assert evidence["schema"] == "lark-training-evidence-v1"
    assert evidence["project"] == "ot5-lark" and evidence["run"] == "lark2"
    assert evidence["accepted_revision"] != first["accepted_revision"]
    assert evidence["digest"] != first["digest"]
    assert set(evidence["geometry"]) == set(first["geometry"])
    assert all(evidence["geometry"][k] != first["geometry"][k] for k in first["geometry"])
    assert evidence["training_exit"] == evidence["observer_exit"] == 0
    final = evidence["trainer_final"]
    assert final["iteration"] + 1 == 240 and final["state"] == "done" and final["device"] == "gpu"
    assert evidence["resource_bound"]["MemoryMax"] == str(20 * 1024**3)
    assert evidence["memory"]["host_peak_bytes"] < 20 * 1024**3
    assert evidence["training_wall_seconds"] < 1800
    mid = evidence["intermediate"]
    assert mid["run"] == "lark2-checkpoint20"
    assert mid["trainer_active_after_browser"] and mid["browser_check_exit"] == 0
    assert mid["before"] < 20 <= mid["render_before"] <= mid["render_after"] <= mid["after"]
    assert mid["witness"]["witness_error"] < mid["witness"]["witness_tolerance"]
    live = evidence["live_browser"]
    assert live["ok"] and live["reload_count"] == 1 and live["default_view_kind"] == "RUN lark2"
    assert len(live["page_iterations"]) >= 7
    assert all(0 <= x["committed_to_page_s"] < 5 for x in live["first_seen"].values())
    policies = evidence["policies"]
    assert set(policies) == {"lark2-checkpoint20", "lark2-final"}
    for policy in policies.values():
        assert re.fullmatch(HEX64, policy["policy_sha256"])
        assert policy["seed"] == 0 and policy["episode_limit_s"] == 8
        assert policy["observed_s"] == 8 and not policy["fell"] and policy["time_limit_reached"]
        browser = policy["browser"]
        assert browser["browser_playback"] and browser["decoded_frames"] == policy["video"]["frames"]
        assert browser["download_sha256"] == policy["video"]["sha256"]
        assert browser["policy_sha256"] == policy["policy_sha256"]
        assert browser["style"] == "cadex-prototype-light-v1"
    assert policies["lark2-checkpoint20"]["browser"]["fresh_selection"] == "RUN lark2"
    assert policies["lark2-final"]["browser"]["fresh_selection"] == "RUN lark2-final"
    assert policies["lark2-final"]["browser"]["historical_selection"] == "lark2-checkpoint20"


def test_lark_agent_revision_comparison_uses_the_declared_ten_seeds():
    """``revision84-evidence.json``: all four retained Lark policies evaluated
    on the project's declared seeds 0-9 from their own retained model, task
    and policy, with the 125 pre-revision run/asset files preserved. The
    report format is the one Wren's revision introduced, so its schema keeps
    that name."""
    evidence = json.loads((PROBE / "revision84-evidence.json").read_text())
    assert evidence["schema"] == "wren-revision-comparison-v1"
    assert evidence["project"] == "ot5-lark"
    assert evidence["protocol"] == dict(seeds=list(range(10)), episode_seconds=8, control_hz=50,
                                        training_iterations=240, environments=1024, training_seed=0)
    assert evidence["before_inventory_preserved"] and evidence["before_inventory_files"] == 125
    runs = evidence["runs"]
    assert set(runs) == {"lark1-checkpoint20", "lark1-final", "lark2-checkpoint20", "lark2-final"}
    torso = {"lark1-checkpoint20": 70, "lark1-final": 70, "lark2-checkpoint20": 45, "lark2-final": 45}
    model_ids = {}
    for name, item in runs.items():
        evaluation = item["evaluation"]
        assert evaluation["run"] == name
        assert evaluation["source_run_unchanged"] and evaluation["seed_zero_trace_identical"]
        rows = evaluation["rows"]
        assert [row["seed"] for row in rows] == list(range(10))
        for row in rows:
            assert row["survival_s"] == pytest.approx(row["step_count"] / 50)
            assert row["fell"] == (row["termination"] == "fell")
            assert row["fell"] or row["survival_s"] == 8
            assert row["policy_sha256"] == item["video"]["policy_sha256"]
            assert row["task_sha256"] == item["video"]["task_sha256"]
        assert item["params"]["values"]["torso_h"] == torso[name]
        assert len({row["model_sha256"] for row in rows}) == 1
        model_ids[name] = rows[0]["model_sha256"]
        assert item["summary"]["falls"] == sum(row["fell"] for row in rows)
        assert item["summary"]["mean_survival_s"] == pytest.approx(sum(row["survival_s"] for row in rows) / 10)
        assert item["summary"]["min_displacement_x_mm"] == min(row["displacement_x_mm"] for row in rows)
        assert item["video"]["sim_seconds"] == pytest.approx(rows[0]["survival_s"])
        assert item["browser"]["browser_playback"]
        assert item["browser"]["download_sha256"] == item["video"]["sha256"]
        assert item["evidence_directory"].startswith("evidence/comparison84/")
    assert model_ids["lark1-checkpoint20"] == model_ids["lark1-final"]
    assert model_ids["lark2-checkpoint20"] == model_ids["lark2-final"] != model_ids["lark1-final"]
    assert len({item["accepted_revision"] for item in runs.values()}) == 4
    for name in ("lark2-checkpoint20", "lark2-final"):
        assert "product-agent-authored revision: torso_h 70->45" in runs[name]["authored_by"]
    for name in ("lark1-checkpoint20", "lark1-final"):
        assert runs[name]["authored_by"].startswith("product-agent-authored Lark")
    # The measured outcome the documents claim: the revision survives every
    # declared seed; the first design's final policy fell on all of them.
    assert runs["lark1-final"]["summary"]["falls"] == 10
    assert runs["lark2-checkpoint20"]["summary"]["falls"] == runs["lark2-final"]["summary"]["falls"] == 0
    assert runs["lark2-final"]["browser"]["fresh_selection"] == "RUN lark2-final"
    assert runs["lark2-checkpoint20"]["browser"]["returned_to_current"] == "RUN lark2"
    readme = (PROBE / "REVISION84.md").read_text()
    assert "revision84-evidence.json" in readme and "training84-evidence.json" in readme


def test_lark_copy_is_independent_with_the_original_unavailable():
    """``copy85-evidence.json`` is the D7 receipt on Lark: the whole project
    was copied, the persistent operator service switched to the copy, the
    original path renamed away for the entire copy-only CLI edit, two fresh
    engine restores and both browser checks, and every original file proved
    byte-identical afterwards. Both servers showed the same six retained runs
    with their own revisions, digests, parameters, curves, meshes and videos."""
    receipt = json.loads((PROBE / "copy85-evidence.json").read_text())
    assert receipt["ok"] and receipt["original"] == "ot5-lark" and receipt["copy"] == "ot5-lark-copy85"
    assert receipt["source_files"] > receipt["retained_files"] >= 250
    assert re.fullmatch(HEX64, receipt["source_inventory_sha256"])
    assert re.fullmatch(HEX64, receipt["retained_sha256"])
    assert receipt["source_unavailable_during_edit_restore_browser"] is True
    assert receipt["original_unchanged"] is True
    assert receipt["copy_revision"] != receipt["original_revision"]
    assert receipt["copy_digest"] != receipt["original_digest"]
    assert receipt["changes"] == {"foot_len": [80.0, 90.0], "policy_on": [1.0, 0.0]}
    assert receipt["product_agent_authorship"] is False and receipt["retraining"] is False
    assert receipt["persistent_url_host"].endswith(":8765")
    assert not receipt["persistent_url_host"].startswith(("127.", "localhost", "[::1]"))
    assert receipt["persistent_private_address_same_machine"] is True
    assert receipt["default_run"] == "lark2-final"
    second, persistent = receipt["second_server"], receipt["persistent_server"]
    assert second == persistent
    assert set(persistent) == {"lark1", "lark1-checkpoint20", "lark1-final",
                               "lark2", "lark2-checkpoint20", "lark2-final"}
    assert len({run["revision"] for run in persistent.values()}) == 6
    for name, run in persistent.items():
        assert re.fullmatch(HEX64, run["revision"]) and re.fullmatch(HEX64, run["digest"])
        assert run["foot_len"] == 80.0
        assert all(run["curves"][h] > 0 for h in ("curve", "loss_curve", "episode_steps_curve"))
        assert len(run["mesh_sha256"]) == 8
        assert ("video" in run) == name.endswith(("-checkpoint20", "-final"))
        if "video" in run:
            assert run["playback_download_poll"] is True
            assert re.fullmatch(HEX64, run["video"]["sha256"])
            assert re.fullmatch(HEX64, run["video"]["policy_sha256"])
            assert run["video"]["seed"] == 0 and 0 < run["video"]["sim_seconds"] <= 8
    assert persistent["lark2-final"]["revision"] == receipt["original_revision"]
    assert persistent["lark1-final"]["curves"]["curve"] == persistent["lark2-final"]["curves"]["curve"] == 240
    assert persistent["lark1-checkpoint20"]["curves"]["curve"] < 240
    assert set(receipt["screenshots"]) == {"second-accepted.png", "persistent-accepted.png"}
    for text in ((PROBE / "COPY85.md").read_text(),
                 (REPO_ROOT / "docs" / "probes" / "operator-review" / "README.md").read_text()):
        assert "ot5-lark-copy85" in text and receipt["copy_revision"][:12] in text


def test_lark_copy_interruption_retry_and_video_on_the_persistent_url():
    """``interruption86-evidence.json`` is Lark's D8 receipt on the working
    copy: a real GPU attempt interrupted by SIGINT after committed updates,
    shown failed with retry guidance and no substituted video; a successful
    new attempt with a saved policy; that policy's verified, playable,
    downloadable video; older results and the historical interruption still
    selectable; and the original project byte-identical after the copy's
    retraining (D7). Both gate suites finished before either trainer started
    and the trainer-exclusion guard observed exactly one trainer per attempt."""
    receipt = json.loads((PROBE / "interruption86-evidence.json").read_text())
    assert receipt["schema"] == "lark-interruption-evidence-v1"
    assert receipt["project"] == "ot5-lark-copy85" and receipt["original"] == "ot5-lark"
    assert receipt["persistent_url_host"].endswith(":8765")
    assert not receipt["persistent_url_host"].startswith(("127.", "localhost", "[::1]"))
    assert receipt["persistent_private_address_same_machine"] and receipt["persistent_server"]
    assert receipt["server_restarted"] is False
    gates = receipt["gates_before_launch"]
    assert gates["cli-suite"]["exit"] == gates["engine-suite"]["exit"] == gates["experiment"]["exit"] == 0
    assert gates["cli-suite"]["finished"] <= gates["engine-suite"]["started"]
    assert gates["engine-suite"]["finished"] <= gates["experiment"]["started"]
    attempts = receipt["attempts"]
    assert set(attempts) == {"lark86-interrupt", "lark86-retry"}
    interrupt, retry = attempts["lark86-interrupt"], attempts["lark86-retry"]
    assert receipt["signal"]["signal"] == "SIGINT" and receipt["signal"]["iteration"] >= 5
    assert interrupt["exit"] != 0 and interrupt["state"] == "failed"
    assert interrupt["error"].startswith("KeyboardInterrupt")
    assert interrupt["final_iteration"] == receipt["signal"]["iteration"] < interrupt["requested_iterations"]
    assert all(n == interrupt["final_iteration"] + 1 for n in interrupt["curve_samples"].values())
    assert "Controlled interruption" in interrupt["note"] and "start a new cadex walk" in interrupt["note"]
    assert interrupt["terminal_browser"] == {"telemetry_state": "failed", "status": "failed",
                                             "retry_guidance_shown": True, "videos_shown": 0, "reload_count": 1}
    assert retry["exit"] == 0 and retry["state"] == "done" and retry["error"] is None
    assert retry["final_iteration"] + 1 == retry["requested_iterations"]
    assert all(n == retry["requested_iterations"] for n in retry["curve_samples"].values())
    assert retry["terminal_browser"]["telemetry_state"] == "done" and retry["terminal_browser"]["status"] == "completed"
    for name, attempt in attempts.items():
        assert attempt["device"] == "gpu" and attempt["components"] == 8
        assert attempt["fresh_selection"] == "RUN " + name
        assert len(attempt["page_samples"]) >= 3
        assert 0 < attempt["host_peak_bytes"] < attempt["memory_max_bytes"] == 20 * 1024**3
        assert attempt["elapsed_s"] < attempt["timeout_seconds"] == 900
        assert attempt["accepted_revision"] == receipt["copy_accepted_before"]["revision"]
        assert attempt["model_sha256"] == interrupt["model_sha256"] and attempt["task_sha256"] == interrupt["task_sha256"]
        guard = attempt["exclusion"]
        assert guard["violation"] is None and guard["max_trainers"] == 1 and len(guard["observed_pids"]) == 1
        assert guard["scans"] > 1000 and guard["max_scan_gap_seconds"] < 0.5
        assert len(attempt["screenshots"]) == 2
    assert interrupt["exclusion"]["observed_pids"] != retry["exclusion"]["observed_pids"]
    video = receipt["retry_video"]
    assert video["run"] == "lark86-retry-video" and video["source_run"] == "lark86-retry"
    assert video["mode"] == "final-policy-playback"
    assert re.fullmatch(HEX64, video["policy_sha256"]) and video["witness_error"] < video["witness_tolerance"]
    assert video["accepted_revision"] != receipt["copy_accepted_before"]["revision"]
    assert video["accepted_revision"] == receipt["copy_accepted_after"]["revision"]
    assert receipt["copy_accepted_before"]["policy_on"] == 0 and receipt["copy_accepted_after"]["policy_on"] == 1
    assert receipt["copy_accepted_before"]["foot_len"] == receipt["copy_accepted_after"]["foot_len"] == 90
    movie, browser, trace = video["video"], video["browser"], video["trace"]
    assert re.fullmatch(HEX64, movie["sha256"]) and movie["style"] == "cadex-prototype-light-v1"
    assert movie["seed"] == 0 and 0 < movie["sim_seconds"] <= 8 and movie["accepted_revision"] == video["accepted_revision"]
    assert browser["decoded_frames"] == movie["frames"] and browser["download_sha256"] == movie["sha256"]
    assert browser["fresh_selection"] == browser["returned_to_current"] == "RUN lark86-retry-video"
    assert abs(browser["simulation_seconds"] - trace["observed_s"]) < 1e-9
    assert trace["fell"] == (trace["termination"] == "fell") and trace["fell"] != trace["time_limit_reached"]
    assert trace["seed"] == 0
    assert receipt["old_videos_checked_after_each"] == ["lark1-checkpoint20", "lark1-final",
                                                        "lark2-checkpoint20", "lark2-final"]
    historical = receipt["historical_interruption"]
    assert historical["selectable"] and historical["status"] == "failed" and historical["videos_shown"] == 0
    assert historical["survived_refresh"] and re.fullmatch(HEX64, historical["screenshot"])
    assert receipt["returned_to_current"] == receipt["fresh_visit_after_completion"]["view_kind"] == "RUN lark86-retry-video"
    assert receipt["prior_run_files_preserved"] >= 246 and receipt["prior_asset_files_preserved"] >= 4
    assert receipt["original_unchanged_after_copy_retraining"] and receipt["original_checked_independently"]
    assert 0 < receipt["original_files_excluding_git"] < receipt["original_files_including_git"]
    assert receipt["gait_claim"] is False and receipt["product_agent_authorship"] is False
    for text in ((PROBE / "INTERRUPTION86.md").read_text(),
                 (REPO_ROOT / "docs" / "probes" / "operator-review" / "README.md").read_text()):
        assert "lark86-retry-video" in text and video["accepted_revision"][:12] in text


def test_lark_video_checks_resolve_training_runs_and_siblings_by_identity_not_name():
    """``lineage88-evidence.json`` is the checker's receipt on the persistent
    working-copy URL after its run-name dependency was removed (ADR-316):
    the fresh visit's expected selection is the reader's own rule, the
    training run behind each video is the run retaining the policy bytes,
    the historical run selected afterwards is a sibling by policy identity
    when one exists and the latest other historical video otherwise, and
    the component count comes from the run's own trace. Both videos decoded
    whole, played through polls and downloaded hash-equal; the server was
    not restarted and no trainer was active."""

    receipt = json.loads((PROBE / "lineage88-evidence.json").read_text())
    assert receipt["project"] == "ot5-lark-copy85" and receipt["persistent_server_restarted"] is False
    assert receipt["trainer_active"] is False and receipt["run_names_consulted_by_checker"] is False
    assert receipt["checker"] == "docs/probes/wren-fresh/check_video.py"
    assert "--not-default" in receipt["commands"][1] and "--label lineage88" in receipt["commands"][0]
    checks = receipt["checks"]
    assert set(checks) == {"lark86-retry-video", "lark1-final"}
    for run, check in checks.items():
        assert check["persistent_server"] and check["browser_playback"] and check["url"] == receipt["url"]
        assert check["url"].endswith(":8765/") and check["private_address_same_machine"]
        assert check["expected_default"] == "lark86-retry-video"
        assert check["fresh_selection"] == check["returned_to_current"] == "RUN lark86-retry-video"
        assert check["is_default"] is (run == "lark86-retry-video")
        assert check["components"] == 8 and check["components_source"].startswith("first frame")
        assert len(check["params_checked"]) == 20 and "foot_len" in check["params_checked"]
        assert re.fullmatch(HEX64, check["download_sha256"]) and re.fullmatch(HEX64, check["policy_sha256"])
        assert check["decoded_frames"] > 0 and check["decoded_frames_differ"]
        assert abs(check["encoded_seconds"] - (check["decoded_frames"] / 10)) < 0.01
        assert check["lineage"]["source_agrees"] is True
        assert check["lineage"]["origin"]["kind"] == "final"
        assert check["lineage"]["origin"]["run"] == check["lineage"]["recorded_source_run"]
        assert check["lineage"]["origin"]["also_retained_by"] == []
    video = checks["lark86-retry-video"]
    assert video["lineage"]["origin"]["run"] == "lark86-retry" and video["lineage"]["playbacks"] == []
    assert video["historical_selection"] == "lark2-final"
    assert video["historical_source"] == "latest other historical video run"
    assert video["foot_len_mm"] == 90.0 and video["decoded_frames"] == 81 and video["simulation_seconds"] == 8.0
    final = checks["lark1-final"]
    assert final["lineage"]["origin"]["run"] == "lark1"
    assert [(s["run"], s["kind"], s["iteration"], s["videos"], s["relation"]) for s in final["lineage"]["playbacks"]] == [
        ("lark1-checkpoint20", "checkpoint", 19, 1, "historical")]
    assert final["historical_selection"] == "lark1-checkpoint20"
    assert final["historical_source"] == "same training run by policy identity"
    assert final["foot_len_mm"] == 80.0
    # The receipt cites the videos iteration 86's receipt recorded, unchanged.
    earlier = json.loads((PROBE / "interruption86-evidence.json").read_text())
    assert video["download_sha256"] == earlier["retry_video"]["video"]["sha256"]
    assert video["policy_sha256"] == earlier["retry_video"]["policy_sha256"]


def test_lark_encoder_failure_during_real_training_kept_the_trainer_and_the_earlier_video():
    """``render98-evidence.json`` is Lark's D4 render-failure isolation receipt
    on the working copy: a real GPU run published its checkpoint video, an
    ordinary re-render then failed at encoding (a temporary ffmpeg exiting 73
    on that subprocess's PATH only), the page showed the failure with retry
    guidance while the verified recording stayed available, live updates kept
    arriving without reload, an earlier design's video still played, the
    retry with the real encoder recovered, and the sole trainer kept its PID
    and finished. The observer's bookkeeping defect is recorded, not hidden."""
    receipt = json.loads((PROBE / "render98-evidence.json").read_text())
    assert receipt["schema"] == "lark-render-failure-evidence-v1"
    assert receipt["project"] == "ot5-lark-copy85" and receipt["original"] == "ot5-lark"
    assert receipt["persistent_server"] and receipt["private_address_same_machine"]
    assert receipt["server_restarted"] is False and receipt["second_device_test"] is False
    assert receipt["persistent_url_host"].endswith(":8765")
    assert not receipt["persistent_url_host"].startswith(("127.", "localhost", "[::1]"))
    runs = receipt["training_run"], receipt["checkpoint_run"], receipt["final_run"]
    assert runs == ("lark98", "lark98-checkpoint20", "lark98-final")
    assert receipt["prior_run"] == "lark2-final" and receipt["prior_run"] not in runs
    # One trainer, unchanged across the fault and the history checks.
    trainer = receipt["trainer"]
    assert trainer["count"] == 1 and trainer["pid_unchanged"]
    assert trainer["before"] == trainer["after_fault_and_history"]
    assert trainer["before"][0]["pid"] > 0 and trainer["before"][0]["start_ticks"].isdigit()
    # The ordinary renderer failed at encoding and published its own failure.
    assert receipt["fault"] == "encoder exits 73" and receipt["render_exit"] == 1
    assert 0 < receipt["failure_seconds"] < 60
    assert "FFmpeg encoding failed" in receipt["render_stderr_tail"]
    failure = receipt["failure_receipt"]
    assert failure["state"] == "failed" and failure["retained_videos"] == 1
    assert failure["video_sha256"] == receipt["first_publication"]["video_sha256"]
    label = receipt["failure_label"]
    assert "Recorded video render: failed" in label and "FFmpeg encoding failed" in label
    assert "Retry the CLI video command" in label and "Video files: available (1/1 retained)" in label
    # The verified recording and an earlier design's video stayed playable.
    retained = receipt["retained_checkpoint_during_fault"]
    assert retained["download_sha256"] == failure["video_sha256"] and retained["playback_poll_preserved"]
    assert retained["policy_sha256"] == receipt["policies"]["checkpoint"]
    prior = receipt["prior_playback_during_fault"]
    assert prior["download_sha256"] == receipt["prior_video_sha256"] and prior["playback_poll_preserved"]
    assert prior["revision"] != retained["revision"] and prior["policy_sha256"] != retained["policy_sha256"]
    # Training advanced on the page without a reload, then through recovery to completion.
    observations = receipt["page_observations"]
    assert len(observations) == 4 and all(o["telemetry_state"] == "training" for o in observations)
    shown = [o["page_iteration"] for o in observations]
    assert shown == sorted(shown) and len(set(shown)) == 4
    assert all(o["reward_points"] == o["loss_points"] == o["page_iteration"] + 1 for o in observations)
    its = receipt["iterations"]
    assert its["checkpoint_published_at"] < its["before_fault"] < its["after_fault_checks"] < its["after_recovery"] < its["final"] == 239
    assert len([i for i in shown if i > its["before_fault"]]) >= 3
    # Recovery: the real encoder produced a second retained file, decoded whole.
    recovered, recovered_receipt = receipt["recovered"], receipt["recovered_receipt"]
    assert recovered_receipt["state"] == "ready" and len(recovered_receipt["retained_files"]) == 2
    assert recovered["download_sha256"] == recovered_receipt["video_sha256"] != failure["video_sha256"]
    assert recovered["decoded_frames"] == receipt["first_publication"]["frames"] == 81
    assert recovered["decoded_frames_differ"] and recovered["seed"] == 0
    assert recovered["style"] == "cadex-prototype-light-v1" and recovered["components"] == 8
    assert recovered["fresh_selection"] == recovered["returned_to_current"] == "RUN lark98"
    assert recovered["is_default"] is False and recovered["expected_default"] == "lark98"
    assert recovered["lineage"]["origin"]["kind"] == "checkpoint" and recovered["lineage"]["source_agrees"]
    assert receipt["first_publication"]["browser_check_exit"] == 0
    # The bounded trainer completed on its own.
    result = receipt["training_result"]
    assert result["training_exit"] == 0 and result["observer_exit"] == 0
    assert result["trainer_final"]["state"] == "done" and result["trainer_final"]["device"] == "gpu"
    assert result["training_wall_seconds"] < receipt["requested"]["timeout_seconds"] == 1800
    assert 0 < result["memory"]["host_peak_bytes"] < receipt["requested"]["memory_max_bytes"] == 20 * 1024**3
    assert int(receipt["resource_bound"]["MemoryMax"]) == 20 * 1024**3
    for witness in receipt["witnesses"].values():
        assert witness["witness_error"] < witness["witness_tolerance"]
    assert re.fullmatch(HEX64, receipt["policies"]["final"]) and receipt["policies"]["final"] != receipt["policies"]["checkpoint"]
    final = receipt["final_browser"]
    assert final["fresh_selection"] == final["returned_to_current"] == "RUN lark98-final" and final["is_default"]
    assert final["historical_selection"] == "lark98-checkpoint20" and final["policy_sha256"] == receipt["policies"]["final"]
    assert final["decoded_frames"] == 81 and final["browser_playback"] and re.fullmatch(HEX64, final["download_sha256"])
    assert receipt["fresh_visit_after_completion"] == "RUN lark98-final"
    # Nothing earlier changed, and the defect is on the record.
    assert receipt["preserved_records"] == {"count": 10, "unchanged": True}
    assert receipt["prior_runs_assets_evidence_changed"] == []
    assert all(not path.startswith(("runs/", "assets/", "evidence/")) for path in receipt["files_changed_outside_lark98"])
    assert receipt["observer_final_step_exit"] == 1 and "FileNotFoundError" in receipt["recovery_check_note"]
    assert receipt["gait_claim"] is False and receipt["product_agent_authorship"] is False
    assert all(re.fullmatch(HEX64, digest) for digest in receipt["project_local_evidence"].values())
    for text in ((PROBE / "RENDER98.md").read_text(), (PROBE / "LIFECYCLE.md").read_text()):
        assert "render98-evidence.json" in text
    assert "lark98" in (REPO_ROOT / "docs" / "probes" / "operator-review" / "README.md").read_text()


def test_render_failure_observer_takes_the_prior_run_as_an_argument():
    """The shared observer names no fixture run: the earlier run whose video
    must stay playable during the fault is its fourth argument."""
    source = (REPO_ROOT / "docs" / "probes" / "wren-fresh" / "render_failure.py").read_text()
    assert "wren71" not in source and "lark2" not in source
    assert "project, training_run, url, prior = sys.argv[1:]" in source
    assert "'--label', 'render-recovery'" in source and "-render-recovery-check.json" in source


def test_lark_operator_dashboard_serves_a_bounded_run_list_after_the_restart():
    """Iteration 99 (ADR-321): the persistent Lark server was restarted with
    no trainer active onto the summary-list server, and a headless browser on
    the private address saw the current run's full detail, its playing and
    hash-equal video, a historical run's own histories, and an idle poll that
    adds the same number of nodes on either view."""
    receipt = json.loads((PROBE / "scale99-evidence.json").read_text())
    assert receipt["project"] == "ot5-lark-copy85" and receipt["url"].startswith("http://100.")
    assert receipt["runs"] == 13 and receipt["list_has_histories"] is False
    assert receipt["list_telemetry_bytes_max"] < 1500
    default = receipt["default_view"]
    assert receipt["default_run_rule"] == default["run"] == "lark98-final"
    assert re.fullmatch(HEX64, default["revision"]) and default["relation"].startswith("CURRENT")
    assert default["points"] == {"curve": 240, "loss_curve": 240, "episode_steps_curve": 240}
    assert default["checkpoints_retained"] == 12 and default["components"] == 8
    assert receipt["download_sha256_matches"] is True
    historical = receipt["historical_view"]
    assert historical["run"] == historical["detail_run"] == "lark1-final"
    assert historical["shown_revision"] == historical["revision"] != default["revision"]
    assert historical["relation"].startswith("HISTORICAL") and historical["points"] == 240
    for poll in (receipt["idle_poll"], receipt["historical_idle_poll"]):
        # The served list is the records (pretty-printed, ~13 KB each on Lark);
        # the telemetry summaries are a small bounded share of it.
        assert poll["project_bytes"] < 20_000 * receipt["runs"] and poll["detail_bytes"] > 10_000
        assert receipt["list_telemetry_bytes_max"] * receipt["runs"] < 0.1 * poll["project_bytes"]
    assert receipt["idle_poll"]["nodes_added"] == receipt["historical_idle_poll"]["nodes_added"]
    assert receipt["route_back_to_current"] is True
    assert "scale99-evidence.json" in (REPO_ROOT / "docs" / "probes" / "operator-review" / "README.md").read_text()


def test_disk100_receipt_shows_per_run_disk_use_on_the_persistent_dashboard() -> None:
    """Iteration 100 (ADR-322): the persistent private-network dashboard
    serves per-run disk use with its run detail and never in its list; the
    default run's count equals an independent walk of its directory, the
    policy asset it shares with its training run is sized once and named as
    shared, a historical checkpoint run kept its own count and playing video
    through two polls, and the route back to current works."""
    receipt = json.loads((PROBE / "disk100-evidence.json").read_text())
    assert receipt["adr"] == "ADR-322" and receipt["project"] == "ot5-lark-copy85"
    assert receipt["url"].startswith("http://100.") and receipt["list_has_disk"] is False
    assert receipt["runs"] == 13 and receipt["default_run_rule"] == "lark98-final"
    disk = receipt["default_disk"]
    assert (disk["bytes"], disk["files"]) == (disk["independent_walk"]["bytes"], disk["independent_walk"]["files"])
    assert disk["bytes"] == sum(entry["bytes"] for entry in disk["by_dir"].values())
    assert disk["files"] == sum(entry["files"] for entry in disk["by_dir"].values())
    assert disk["hardlinked_entries"] == 0 and disk["skipped_count"] == 0
    assert disk["shared"]["policy"]["shared_with"] == ["lark98"]
    assert disk["shared_bytes"] == disk["shared"]["policy"]["bytes"] > 0
    assert receipt["runs_total_bytes"] > 10 * disk["bytes"]
    default = receipt["default_view"]
    assert default["run"] == "lark98-final" and re.fullmatch(HEX64, default["revision"])
    assert default["relation"].startswith("CURRENT") and default["summary"].startswith("Disk use: ")
    assert "under runs/lark98-final/" in default["summary"] and default["size_cells"] == 13
    assert default["video_label_has_size"] is True
    historical = receipt["historical_view"]
    assert historical["run"] == "lark98-checkpoint20" and historical["relation"].startswith("HISTORICAL")
    assert historical["bytes"] > 0 and historical["playback_kept_through_two_polls"] is True
    assert historical["count_kept"] is True and receipt["route_back_to_current"] is True
    assert "disk100-evidence.json" in (REPO_ROOT / "docs" / "probes" / "operator-review" / "README.md").read_text()
