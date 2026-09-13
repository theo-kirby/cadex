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
