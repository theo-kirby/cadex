# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The fresh biped's committed lifecycle report stays consistent with its evidence.

``docs/probes/reed-lifecycle/report.json`` is generated from the real Reed
project by ``docs/probes/reed-lifecycle/report.py``; the project itself lives
outside this checkout, so these tests hold the *committed* report to what the
repository can check: every identity it cites agrees with itself and with the
persistent-URL check it carries, the common-seed comparison is recomputable
from the committed evaluation rows, every document, probe, test, ADR and
record node it links exists, and the report's README discloses each run whose
retained model view is incomplete. Nothing here needs an engine, a browser or
the project.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re

import pytest

from conftest import REPO_ROOT

LIFECYCLE = REPO_ROOT / "docs" / "probes" / "reed-lifecycle"


def _load_generator():
    spec = importlib.util.spec_from_file_location("reed_lifecycle_report", LIFECYCLE / "report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads((LIFECYCLE / "report.json").read_text())


@pytest.fixture(scope="module")
def readme() -> str:
    return (LIFECYCLE / "README.md").read_text()


def test_every_video_carries_its_runs_policy_and_revision(report):
    for run in report["runs"]:
        for video in run["videos"]:
            assert video["policy_sha256"] == run["policy_sha256"], (run["run"], video["index"])
            assert video["accepted_revision"] == run["accepted_revision"], (run["run"], video["index"])
            assert video["seed"] == run["rollout_seed"], (run["run"], video["index"])
            assert video["frames"] > 0 and video["sim_seconds"] > 0


def test_persistent_operator_check_agrees_with_the_run_it_selected(report):
    check = report["persistent_operator_check"]
    assert check["project"] == report["project"]
    by_name = {run["run"]: run for run in report["runs"]}
    assert set(check["current"]["runs"]) == set(by_name)
    selected = by_name[check["run"]]
    assert check["current"]["selected"] == check["run"]
    assert check["current"]["relation"] == "current"
    assert check["current"]["revision"] == selected["accepted_revision"] == report["accepted"]["revision"]
    assert check["video_sha256"] == selected["videos"][0]["sha256"]
    assert check["playback_preserved_on_poll"] and check["return_to_current"]
    assert check["historical_run"] in by_name and check["historical_run"] != check["run"]


def test_common_seed_comparison_is_recomputable_from_committed_rows(report):
    generator = _load_generator()
    recomputed = generator.common_seed_comparison()
    committed = report["common_seed_comparison"]
    assert recomputed["seeds"] == committed["seeds"] == list(range(10))
    assert recomputed["episode_limit_s"] == committed["episode_limit_s"]
    assert recomputed["designs"] == committed["designs"]
    by_name = {run["run"]: run for run in report["runs"]}
    for name, design in committed["designs"].items():
        assert design["policy_sha256"] == by_name[name]["policy_sha256"], name
        assert design["falls"] + design["survivors"] == len(design["seeds"])
        assert len(design["observed_s"]) == len(design["forward_displacement_mm"]) == len(design["seeds"])
    for name in committed["not_evaluated_on_common_seeds"]:
        assert name in by_name and name not in committed["designs"]


def test_summarize_seed_rows_refuses_mixed_policies():
    generator = _load_generator()
    row = {"seed": 0, "fell": True, "time_limit_reached": False, "observed_s": 0.5,
           "displacement_mm": [1.0, 0.0, 0.0], "episode_limit_s": 8, "policy_sha256": "a"}
    other = dict(row, seed=1, policy_sha256="b")
    with pytest.raises(ValueError):
        generator.summarize_seed_rows([row, other])
    summary = generator.summarize_seed_rows([row, dict(row, seed=1, fell=False, time_limit_reached=True,
                                                       observed_s=8.0, displacement_mm=[3.0, 0.0, 0.0])])
    assert (summary["falls"], summary["survivors"]) == (1, 1)
    assert summary["mean_observed_s"] == 4.25 and summary["mean_forward_displacement_mm"] == 2.0


def test_evidence_index_links_resolve(report):
    adr_headings = set(re.findall(r"^## (ADR-\d+)", (REPO_ROOT / "docs" / "DECISIONS.md").read_text(), re.M))
    records = REPO_ROOT / ".hypergraph" / "graph" / "record"
    assert set(report["evidence_index"]) == {f"D{n}" for n in range(1, 9)}
    for criterion, entry in report["evidence_index"].items():
        for key in ("docs", "probes", "tests"):
            for relative in entry[key]:
                assert (REPO_ROOT / relative).is_file(), (criterion, relative)
        for adr in entry["adrs"]:
            assert adr in adr_headings, (criterion, adr)
        for slug in entry["records"]:
            assert (records / f"{slug}.md").is_file(), (criterion, slug)


def test_readme_discloses_every_incomplete_or_absent_model_view(report, readme):
    for run in report["runs"]:
        view = run["view"]
        if view["kind"] == "none" or view["meshes_missing"]:
            assert f"`{run['run']}`" in readme, run["run"]
        if view["kind"] == "training snapshot":
            assert f"`{run['run']}`" in readme, run["run"]
    # The disclosed counts in prose are the report's counts, not remembered ones.
    for name, retained in (("probe3", 4), ("shin55", 5)):
        run = next(r for r in report["runs"] if r["run"] == name)
        assert run["view"]["meshes_retained"] == retained and run["view"]["components"] == 8
        assert f"{retained} of 8" in readme, name
