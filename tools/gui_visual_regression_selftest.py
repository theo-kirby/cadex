#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Self-test the GUI visual regression approval/check workflow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Any

from PIL import Image


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_scene(
    capture_dir: Path,
    name: str,
    color: tuple[int, int, int],
    findings: list[dict[str, Any]] | None = None,
    scene_config: dict[str, Any] | None = None,
) -> None:
    capture_dir.mkdir(parents=True, exist_ok=True)
    image_path = capture_dir / f"{name}.png"
    metadata_path = capture_dir / f"{name}.json"
    Image.new("RGB", (32, 32), color).save(image_path)
    write_json(
        metadata_path,
        {
            "scene": name,
            "screenshot": str(image_path),
            "screen_size": [32, 32],
            "active_workbench": "SelfTestWorkbench",
            "scene_config": scene_config or {"name": name, "file": "selftest-a.FCStd"},
            "variant": {},
            "findings": findings or [],
        },
    )


def write_summary(capture_dir: Path, names: list[str]) -> None:
    write_json(
        capture_dir / "summary.json",
        {
            "result": "ok",
            "scene_count": len(names),
            "scenes": [
                {
                    "scene": name,
                    "screenshot": str(capture_dir / f"{name}.png"),
                    "metadata": str(capture_dir / f"{name}.json"),
                }
                for name in names
            ],
        },
    )


def run_json(command: list[str], expect_returncode: int | None = None) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {
            "result": "invalid_json",
            "raw_output": completed.stdout,
        }
    if expect_returncode is not None and completed.returncode != expect_returncode:
        payload.setdefault("failures", []).append(
            {
                "kind": "unexpected_returncode",
                "expected": expect_returncode,
                "actual": completed.returncode,
            }
        )
    return completed.returncode, payload


def failure_kinds(report: dict[str, Any]) -> set[str]:
    return {failure.get("kind") for failure in report.get("failures", [])}


def report_has_review_artifacts(report: dict[str, Any]) -> bool:
    required_top_level = ["manifest", "capture_dir", "diff_dir", "policy", "approval_command", "review_index"]
    if any(not report.get(key) for key in required_top_level):
        return False
    review_index = report.get("review_index") or {}
    if not all(review_index.get(key) for key in ("json", "html")):
        return False
    if not all(Path(review_index[key]).exists() for key in ("json", "html")):
        return False
    for failure in report.get("failures", []):
        if failure.get("kind") == "image_changed":
            return all(
                failure.get(key)
                for key in ["baseline_screenshot", "current_screenshot", "diff_image", "policy"]
            )
    return True


def build_finding(kind: str = "possible_text_clipping", text: str = "probe") -> dict[str, Any]:
    return {
        "kind": kind,
        "widget": {
            "class": "QLabel",
            "object_name": "selftest_label",
            "text": text,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=Path("/tmp/freecad-visual-regression-selftest"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/freecad-test-results/gui-visual-regression-selftest.json"))
    args = parser.parse_args()

    script = Path(__file__).resolve().with_name("gui_visual_regression.py")
    work_dir = args.work_dir
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    baseline = work_dir / "baseline-capture"
    manifest = work_dir / "approved.json"
    diff_dir = work_dir / "diffs"
    make_scene(baseline, "scene-a", (255, 255, 255), [build_finding()])
    write_summary(baseline, ["scene-a"])

    approve = subprocess.run(
        [
            sys.executable,
            str(script),
            "approve",
            "--capture-dir",
            str(baseline),
            "--manifest",
            str(manifest),
            "--reviewer",
            "visual regression self-test",
            "--approval-note",
            "Self-test baseline approval metadata.",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    scenarios: dict[str, dict[str, Any]] = {
        "identical_passes": {"expect_ok": True, "capture": "identical"},
        "small_image_drift_passes": {"expect_ok": True, "capture": "small-drift"},
        "large_image_change_fails": {"expect_failure_kind": "image_changed", "capture": "large-change"},
        "new_layout_finding_fails": {"expect_failure_kind": "new_layout_findings", "capture": "new-finding"},
        "missing_scene_fails": {"expect_failure_kind": "missing_scene", "capture": "missing-scene"},
        "extra_scene_fails": {"expect_failure_kind": "unapproved_new_scene", "capture": "extra-scene"},
        "harness_metadata_change_passes": {"expect_ok": True, "capture": "harness-change"},
        "scene_context_change_fails": {
            "expect_failure_kind": "scene_context_changed",
            "capture": "context-change",
        },
    }

    captures = {
        "identical": (["scene-a"], [("scene-a", (255, 255, 255), [build_finding()])]),
        "small-drift": (["scene-a"], [("scene-a", (254, 255, 255), [build_finding()])]),
        "large-change": (["scene-a"], [("scene-a", (0, 0, 0), [build_finding()])]),
        "new-finding": (
            ["scene-a"],
            [("scene-a", (255, 255, 255), [build_finding(), build_finding("zero_size", "new")])],
        ),
        "missing-scene": ([], []),
        "extra-scene": (
            ["scene-a", "scene-b"],
            [
                ("scene-a", (255, 255, 255), [build_finding()]),
                ("scene-b", (255, 255, 255), []),
            ],
        ),
        "harness-change": (
            ["scene-a"],
            [
                (
                    "scene-a",
                    (255, 255, 255),
                    [build_finding()],
                    {
                        "name": "scene-a",
                        "file": "selftest-a.FCStd",
                        "wait_ms": 9999,
                        "fit_view": False,
                        "coverage": ["renamed-coverage-bucket"],
                        "required_visible_text_contains": ["probe"],
                        "close_after_capture": True,
                    },
                )
            ],
        ),
        "context-change": (
            ["scene-a"],
            [
                (
                    "scene-a",
                    (255, 255, 255),
                    [build_finding()],
                    {"name": "scene-a", "file": "different-source.FCStd"},
                )
            ],
        ),
    }

    results = {}
    for name, spec in scenarios.items():
        capture_name = spec["capture"]
        names, scene_defs = captures[capture_name]
        capture_dir = work_dir / capture_name
        for scene_def in scene_defs:
            scene_name, color, findings, *rest = scene_def
            scene_config = rest[0] if rest else None
            make_scene(capture_dir, scene_name, color, findings, scene_config=scene_config)
        write_summary(capture_dir, names)
        rc, report = run_json(
            [
                sys.executable,
                str(script),
                "check",
                "--capture-dir",
                str(capture_dir),
                "--manifest",
                str(manifest),
                "--diff-dir",
                str(diff_dir / name),
            ]
        )
        ok = False
        if spec.get("expect_ok"):
            ok = rc == 0 and report.get("result") == "ok" and report.get("failure_count") == 0
        else:
            expected_kind = spec["expect_failure_kind"]
            ok = rc == 1 and expected_kind in failure_kinds(report)
            if expected_kind == "image_changed":
                ok = ok and report_has_review_artifacts(report)
        results[name] = {
            "ok": ok,
            "returncode": rc,
            "expected": {key: value for key, value in spec.items() if key != "capture"},
            "result": report.get("result"),
            "failure_count": report.get("failure_count"),
            "failure_kinds": sorted(kind for kind in failure_kinds(report) if kind),
            "has_review_artifacts": report_has_review_artifacts(report),
        }

    lax_manifest = work_dir / "lax-approved.json"
    shutil.copy2(manifest, lax_manifest)
    lax_data = json.loads(lax_manifest.read_text(encoding="utf-8"))
    lax_data["policy"]["max_changed_ratio"] = 1.0
    lax_data["policy"]["max_rms"] = 999.0
    write_json(lax_manifest, lax_data)

    capture_dir = work_dir / "identical"
    rc, report = run_json(
        [
            sys.executable,
            str(script),
            "check",
            "--capture-dir",
            str(capture_dir),
            "--manifest",
            str(lax_manifest),
            "--diff-dir",
            str(diff_dir / "lax_manifest_policy_fails"),
        ]
    )
    expected_kind = "manifest_policy"
    results["lax_manifest_policy_fails"] = {
        "ok": rc == 1 and expected_kind in failure_kinds(report),
        "returncode": rc,
        "expected": {"expect_failure_kind": expected_kind},
        "result": report.get("result"),
        "failure_count": report.get("failure_count"),
        "failure_kinds": sorted(kind for kind in failure_kinds(report) if kind),
    }

    no_context_manifest = work_dir / "no-context-approved.json"
    shutil.copy2(manifest, no_context_manifest)
    no_context_data = json.loads(no_context_manifest.read_text(encoding="utf-8"))
    for scene in (no_context_data.get("scenes") or {}).values():
        scene.pop("scene_context_fingerprint", None)
    write_json(no_context_manifest, no_context_data)
    rc, report = run_json(
        [
            sys.executable,
            str(script),
            "check",
            "--capture-dir",
            str(capture_dir),
            "--manifest",
            str(no_context_manifest),
            "--diff-dir",
            str(diff_dir / "missing_scene_context_fingerprint_fails"),
        ]
    )
    expected_kind = "missing_scene_context_fingerprint"
    results["missing_scene_context_fingerprint_fails"] = {
        "ok": rc == 1 and expected_kind in failure_kinds(report),
        "returncode": rc,
        "expected": {"expect_failure_kind": expected_kind},
        "result": report.get("result"),
        "failure_count": report.get("failure_count"),
        "failure_kinds": sorted(kind for kind in failure_kinds(report) if kind),
    }

    no_identity_manifest = work_dir / "no-identity-approved.json"
    shutil.copy2(manifest, no_identity_manifest)
    no_identity_data = json.loads(no_identity_manifest.read_text(encoding="utf-8"))
    for scene in (no_identity_data.get("scenes") or {}).values():
        scene.pop("scene_context_identity", None)
    write_json(no_identity_manifest, no_identity_data)
    rc, report = run_json(
        [
            sys.executable,
            str(script),
            "check",
            "--capture-dir",
            str(capture_dir),
            "--manifest",
            str(no_identity_manifest),
            "--diff-dir",
            str(diff_dir / "missing_scene_context_identity_fails"),
        ]
    )
    expected_kind = "missing_scene_context_identity"
    results["missing_scene_context_identity_fails"] = {
        "ok": rc == 1 and expected_kind in failure_kinds(report),
        "returncode": rc,
        "expected": {"expect_failure_kind": expected_kind},
        "result": report.get("result"),
        "failure_count": report.get("failure_count"),
        "failure_kinds": sorted(kind for kind in failure_kinds(report) if kind),
    }

    no_approval_manifest = work_dir / "no-approval-approved.json"
    shutil.copy2(manifest, no_approval_manifest)
    no_approval_data = json.loads(no_approval_manifest.read_text(encoding="utf-8"))
    no_approval_data.pop("approval", None)
    write_json(no_approval_manifest, no_approval_data)
    rc, report = run_json(
        [
            sys.executable,
            str(script),
            "check",
            "--capture-dir",
            str(capture_dir),
            "--manifest",
            str(no_approval_manifest),
            "--diff-dir",
            str(diff_dir / "missing_approval_metadata_fails"),
        ]
    )
    expected_kind = "manifest_approval"
    results["missing_approval_metadata_fails"] = {
        "ok": rc == 1 and expected_kind in failure_kinds(report),
        "returncode": rc,
        "expected": {"expect_failure_kind": expected_kind},
        "result": report.get("result"),
        "failure_count": report.get("failure_count"),
        "failure_kinds": sorted(kind for kind in failure_kinds(report) if kind),
    }

    reapproved_manifest = work_dir / "reapproved-large-change.json"
    reapprove = subprocess.run(
        [
            sys.executable,
            str(script),
            "approve",
            "--capture-dir",
            str(work_dir / "large-change"),
            "--manifest",
            str(reapproved_manifest),
            "--reviewer",
            "visual regression self-test",
            "--approval-note",
            "Self-test intentional visual update approval.",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    rc, report = run_json(
        [
            sys.executable,
            str(script),
            "check",
            "--capture-dir",
            str(work_dir / "large-change"),
            "--manifest",
            str(reapproved_manifest),
            "--diff-dir",
            str(diff_dir / "reapproved_large_change_passes"),
        ]
    )
    reapproved_data = json.loads(reapproved_manifest.read_text(encoding="utf-8")) if reapproved_manifest.exists() else {}
    results["reapproved_large_change_passes"] = {
        "ok": (
            reapprove.returncode == 0
            and rc == 0
            and report.get("result") == "ok"
            and report.get("failure_count") == 0
            and bool(reapproved_data.get("approval"))
        ),
        "returncode": rc,
        "approve_returncode": reapprove.returncode,
        "expected": {"expect_ok_after_approval": True},
        "result": report.get("result"),
        "failure_count": report.get("failure_count"),
        "failure_kinds": sorted(kind for kind in failure_kinds(report) if kind),
        "manifest_has_approval_metadata": bool(reapproved_data.get("approval")),
    }

    reapproved_finding_manifest = work_dir / "reapproved-new-finding.json"
    reapprove_finding = subprocess.run(
        [
            sys.executable,
            str(script),
            "approve",
            "--capture-dir",
            str(work_dir / "new-finding"),
            "--manifest",
            str(reapproved_finding_manifest),
            "--reviewer",
            "visual regression self-test",
            "--approval-note",
            "Self-test intentional layout finding approval.",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    rc, report = run_json(
        [
            sys.executable,
            str(script),
            "check",
            "--capture-dir",
            str(work_dir / "new-finding"),
            "--manifest",
            str(reapproved_finding_manifest),
            "--diff-dir",
            str(diff_dir / "reapproved_new_layout_finding_passes"),
        ]
    )
    reapproved_finding_data = (
        json.loads(reapproved_finding_manifest.read_text(encoding="utf-8"))
        if reapproved_finding_manifest.exists()
        else {}
    )
    approved_findings = (
        next(iter((reapproved_finding_data.get("scenes") or {}).values()), {})
        .get("approved_findings")
        or {}
    )
    results["reapproved_new_layout_finding_passes"] = {
        "ok": (
            reapprove_finding.returncode == 0
            and rc == 0
            and report.get("result") == "ok"
            and report.get("failure_count") == 0
            and bool(reapproved_finding_data.get("approval"))
            and len(approved_findings) >= 2
        ),
        "returncode": rc,
        "approve_returncode": reapprove_finding.returncode,
        "expected": {"expect_new_layout_finding_ok_after_approval": True},
        "result": report.get("result"),
        "failure_count": report.get("failure_count"),
        "failure_kinds": sorted(kind for kind in failure_kinds(report) if kind),
        "manifest_has_approval_metadata": bool(reapproved_finding_data.get("approval")),
        "approved_finding_count": len(approved_findings),
    }

    manifest_data = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    failures = [name for name, result in results.items() if not result["ok"]]
    report = {
        "schema": "freecad-gui-visual-regression-selftest-v1",
        "result": "ok" if approve.returncode == 0 and not failures else "failed",
        "approve_returncode": approve.returncode,
        "manifest_format": manifest_data.get("format"),
        "manifest_absolute_screenshot_count": sum(
            Path(scene.get("screenshot", "")).is_absolute()
            for scene in (manifest_data.get("scenes") or {}).values()
        ),
        "manifest_missing_context_fingerprint_count": sum(
            not scene.get("scene_context_fingerprint")
            for scene in (manifest_data.get("scenes") or {}).values()
        ),
        "manifest_missing_context_identity_count": sum(
            not scene.get("scene_context_identity")
            for scene in (manifest_data.get("scenes") or {}).values()
        ),
        "manifest_has_approval_metadata": bool(manifest_data.get("approval")),
        "scenario_count": len(results),
        "failed_scenarios": failures,
        "scenarios": results,
    }
    write_json(args.output, report)
    return 0 if report["result"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
