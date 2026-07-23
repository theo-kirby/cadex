#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Approve or check FreeCAD GUI visual baseline captures.

The comparison is intentionally tolerant of expected visual evolution:

* screenshots are compared with documented pixel thresholds, not exact hashes;
* existing layout findings are allowlisted by stable fingerprints;
* fixed findings are accepted;
* new layout findings fail until they are fixed or explicitly approved.
"""

from __future__ import annotations

import argparse
import html
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat


DEFAULT_MAX_CHANGED_RATIO = 0.03
DEFAULT_MAX_RMS = 8.0
BASELINE_IMAGE_DIR_SUFFIX = ".baseline-images"
PLACEHOLDER_TEXT = {"todo", "tbd", "n/a", "none", "placeholder"}


def non_placeholder_text(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() not in PLACEHOLDER_TEXT


def policy_failures(policy: dict[str, Any]) -> list[dict[str, Any]]:
    failures = []
    try:
        max_changed_ratio = float(policy.get("max_changed_ratio", DEFAULT_MAX_CHANGED_RATIO))
    except (TypeError, ValueError):
        failures.append({"kind": "manifest_policy", "field": "max_changed_ratio", "message": "must be numeric"})
        max_changed_ratio = DEFAULT_MAX_CHANGED_RATIO
    try:
        max_rms = float(policy.get("max_rms", DEFAULT_MAX_RMS))
    except (TypeError, ValueError):
        failures.append({"kind": "manifest_policy", "field": "max_rms", "message": "must be numeric"})
        max_rms = DEFAULT_MAX_RMS

    if max_changed_ratio > DEFAULT_MAX_CHANGED_RATIO:
        failures.append(
            {
                "kind": "manifest_policy",
                "field": "max_changed_ratio",
                "actual": max_changed_ratio,
                "maximum": DEFAULT_MAX_CHANGED_RATIO,
            }
        )
    if max_rms > DEFAULT_MAX_RMS:
        failures.append(
            {
                "kind": "manifest_policy",
                "field": "max_rms",
                "actual": max_rms,
                "maximum": DEFAULT_MAX_RMS,
            }
        )
    if policy.get("new_findings_fail") is not True:
        failures.append(
            {
                "kind": "manifest_policy",
                "field": "new_findings_fail",
                "message": "new layout findings must fail",
            }
        )
    if policy.get("baseline_images_are_portable") is not True:
        failures.append(
            {
                "kind": "manifest_policy",
                "field": "baseline_images_are_portable",
                "message": "baseline image paths must be portable",
            }
        )
    return failures


def approval_failures(approval: dict[str, Any] | None) -> list[dict[str, Any]]:
    failures = []
    if not isinstance(approval, dict):
        return [{"kind": "manifest_approval", "field": "approval", "message": "approval metadata is required"}]
    for field in ("reviewer", "note", "approved_utc", "source_capture_dir"):
        if not non_placeholder_text(approval.get(field)):
            failures.append(
                {
                    "kind": "manifest_approval",
                    "field": field,
                    "message": "approval field is required and must not be placeholder text",
                }
            )
    approved_utc = str(approval.get("approved_utc") or "").strip()
    if approved_utc:
        try:
            parsed = datetime.fromisoformat(approved_utc.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                failures.append(
                    {
                        "kind": "manifest_approval",
                        "field": "approved_utc",
                        "message": "approval timestamp must include timezone",
                    }
                )
        except ValueError:
            failures.append(
                {
                    "kind": "manifest_approval",
                    "field": "approved_utc",
                    "message": "approval timestamp must be ISO-8601",
                }
            )
    return failures


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value[:120]


def finding_fingerprint(finding: dict[str, Any]) -> str:
    widget = finding.get("widget", {})
    parts = [
        finding.get("kind", ""),
        widget.get("class", ""),
        widget.get("object_name", ""),
        normalize_text(widget.get("text", "")),
    ]
    raw = "\n".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


SCENE_IDENTITY_KEYS = (
    "name",
    "file",
    "workbench",
    "capture",
    "command",
    "edit_object",
    "select_object",
    "new_document",
)

VARIANT_IDENTITY_ENV_KEYS = (
    "QT_SCALE_FACTOR",
    "QT_FONT_DPI",
)


def scene_context_identity(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return the workflow identity, excluding harness mechanics.

    The identity should change when the represented workflow changes, but not
    when capture timing, validation probes, or cleanup behavior changes.
    """

    scene_config = metadata.get("scene_config") or {}
    variant = metadata.get("variant") or {}
    variant_env = variant.get("env") or {}
    identity_scene = {
        key: scene_config.get(key)
        for key in SCENE_IDENTITY_KEYS
        if key in scene_config
    }
    if "python" in scene_config:
        identity_scene["python_sha256"] = hashlib.sha256(
            str(scene_config.get("python", "")).encode("utf-8")
        ).hexdigest()[:16]

    identity_variant = {
        key: variant.get(key)
        for key in ("name", "preference_pack", "font_scale")
        if key in variant
    }
    identity_env = {
        key: variant_env.get(key)
        for key in VARIANT_IDENTITY_ENV_KEYS
        if key in variant_env
    }
    if identity_env:
        identity_variant["env"] = identity_env

    return {
        "scene": identity_scene,
        "variant": identity_variant,
        "active_workbench": metadata.get("active_workbench"),
    }


def scene_context_fingerprint(metadata: dict[str, Any]) -> str:
    raw = json.dumps(scene_context_identity(metadata), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def safe_image_name(scene: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", scene).strip("._")
    return f"{name or 'scene'}.png"


def manifest_relative_path(manifest_path: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(manifest_path.parent.resolve()))
    except ValueError:
        return str(path)


def resolve_manifest_path(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return manifest_path.parent / path


def image_metrics(baseline_path: Path, current_path: Path) -> dict[str, Any]:
    with Image.open(baseline_path).convert("RGB") as baseline:
        with Image.open(current_path).convert("RGB") as current:
            if baseline.size != current.size:
                return {
                    "same_size": False,
                    "baseline_size": list(baseline.size),
                    "current_size": list(current.size),
                    "changed_ratio": 1.0,
                    "rms": math.inf,
                }
            diff = ImageChops.difference(baseline, current)
            stat = ImageStat.Stat(diff)
            rms = math.sqrt(sum(value * value for value in stat.rms) / len(stat.rms))
            histogram = diff.convert("L").histogram()
            unchanged = histogram[0]
            total = baseline.size[0] * baseline.size[1]
            changed_ratio = (total - unchanged) / total
            return {
                "same_size": True,
                "baseline_size": list(baseline.size),
                "current_size": list(current.size),
                "changed_ratio": changed_ratio,
                "rms": rms,
            }


def artifact_path(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def display_path(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return str(Path(path).resolve())
    except OSError:
        return path


def scene_artifacts(
    baseline_screenshot: Path | None,
    current_screenshot: Path | None,
    diff_image: Path | None = None,
    current_metadata: Path | None = None,
) -> dict[str, str]:
    artifacts = {}
    if baseline_screenshot is not None:
        artifacts["baseline_screenshot"] = str(baseline_screenshot)
    if current_screenshot is not None:
        artifacts["current_screenshot"] = str(current_screenshot)
    if diff_image is not None:
        artifacts["diff_image"] = str(diff_image)
    if current_metadata is not None:
        artifacts["current_metadata"] = str(current_metadata)
    return artifacts


def review_index_paths(diff_dir: Path | None) -> dict[str, str | None]:
    if diff_dir is None:
        return {"json": None, "html": None}
    return {
        "json": str(diff_dir / "review-index.json"),
        "html": str(diff_dir / "review-index.html"),
    }


def review_record_for_failure(failure: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene": failure.get("scene"),
        "kind": failure.get("kind"),
        "baseline_screenshot": display_path(failure.get("baseline_screenshot")),
        "current_screenshot": display_path(failure.get("current_screenshot")),
        "diff_image": display_path(failure.get("diff_image")),
        "current_metadata": display_path(failure.get("current_metadata")),
        "metrics": failure.get("metrics"),
        "policy": failure.get("policy"),
        "count": failure.get("count"),
        "examples": failure.get("examples", []),
        "approved": failure.get("approved"),
        "current": failure.get("current"),
    }


def write_review_index(
    diff_dir: Path | None,
    report: dict[str, Any],
    failures: list[dict[str, Any]],
) -> dict[str, str | None]:
    paths = review_index_paths(diff_dir)
    if diff_dir is None:
        return paths
    diff_dir.mkdir(parents=True, exist_ok=True)
    records = [review_record_for_failure(failure) for failure in failures]
    summary = {
        "schema": "freecad-gui-visual-review-index-v1",
        "result": report.get("result"),
        "failure_count": len(records),
        "manifest": report.get("manifest"),
        "capture_dir": report.get("capture_dir"),
        "diff_dir": report.get("diff_dir"),
        "policy": report.get("policy"),
        "approval_command": report.get("approval_command"),
        "failures": records,
    }
    write_json(Path(paths["json"]), summary)

    rows = []
    for item in records:
        def link(path: str | None, label: str) -> str:
            if not path:
                return ""
            return f'<a href="{html.escape(path)}">{html.escape(label)}</a>'

        metric_text = ""
        metrics = item.get("metrics") or {}
        if metrics:
            metric_text = html.escape(
                f"changed={metrics.get('changed_ratio')} rms={metrics.get('rms')}"
            )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('scene') or ''))}</td>"
            f"<td>{html.escape(str(item.get('kind') or ''))}</td>"
            f"<td>{metric_text}</td>"
            f"<td>{link(item.get('baseline_screenshot'), 'baseline')}</td>"
            f"<td>{link(item.get('current_screenshot'), 'current')}</td>"
            f"<td>{link(item.get('diff_image'), 'diff')}</td>"
            f"<td>{link(item.get('current_metadata'), 'metadata')}</td>"
            "</tr>"
        )
    html_text = """<!doctype html>
<meta charset="utf-8">
<title>FreeCAD GUI Visual Review</title>
<style>
body {{ font-family: sans-serif; margin: 24px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }}
th {{ background: #eee; }}
code {{ white-space: pre-wrap; }}
</style>
<h1>FreeCAD GUI Visual Review</h1>
<p><strong>Result:</strong> {result} &nbsp; <strong>Failures:</strong> {failure_count}</p>
<p><strong>Manifest:</strong> <code>{manifest}</code></p>
<p><strong>Capture:</strong> <code>{capture}</code></p>
<p><strong>Approval command:</strong> <code>{approval}</code></p>
<table>
<thead><tr><th>Scene</th><th>Kind</th><th>Metrics</th><th>Baseline</th><th>Current</th><th>Diff</th><th>Metadata</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
""".format(
        result=html.escape(str(report.get("result"))),
        failure_count=len(records),
        manifest=html.escape(str(report.get("manifest"))),
        capture=html.escape(str(report.get("capture_dir"))),
        approval=html.escape(str(report.get("approval_command"))),
        rows="\n".join(rows),
    )
    Path(paths["html"]).write_text(html_text, encoding="utf-8")
    return paths


def scene_map(capture_dir: Path) -> dict[str, dict[str, Any]]:
    summary = read_json(capture_dir / "summary.json")
    if summary.get("result") != "ok":
        raise ValueError(
            f"Capture {capture_dir} is not approvable/checkable: result={summary.get('result')!r}"
        )
    scenes = {}
    for item in summary.get("scenes", []):
        if "metadata" not in item:
            continue
        metadata = read_json(Path(item["metadata"]))
        scenes[item["scene"]] = {
            "summary": item,
            "metadata": metadata,
            "metadata_path": Path(item["metadata"]),
            "screenshot": Path(item["screenshot"]),
        }
    return scenes


def approve(
    capture_dir: Path,
    manifest_path: Path,
    max_changed_ratio: float,
    max_rms: float,
    baseline_image_dir: Path | None,
    reviewer: str,
    note: str,
) -> None:
    approval = {
        "reviewer": reviewer.strip(),
        "note": note.strip(),
        "approved_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_capture_dir": str(capture_dir),
    }
    approval_errors = approval_failures(approval)
    if approval_errors:
        raise ValueError(f"Invalid approval metadata: {approval_errors}")
    if baseline_image_dir is None:
        baseline_image_dir = manifest_path.with_suffix("").with_name(
            manifest_path.with_suffix("").name + BASELINE_IMAGE_DIR_SUFFIX
        )
    if not baseline_image_dir.is_absolute():
        baseline_image_dir = manifest_path.parent / baseline_image_dir
    baseline_image_dir.mkdir(parents=True, exist_ok=True)

    scenes = {}
    for scene, data in scene_map(capture_dir).items():
        metadata = data["metadata"]
        findings = metadata.get("findings", [])
        baseline_screenshot = baseline_image_dir / safe_image_name(scene)
        shutil.copy2(data["screenshot"], baseline_screenshot)
        scenes[scene] = {
            "screenshot": manifest_relative_path(manifest_path, baseline_screenshot),
            "source_capture_screenshot": str(data["screenshot"]),
            "screen_size": metadata.get("screen_size"),
            "active_workbench": metadata.get("active_workbench"),
            "scene_context_identity": scene_context_identity(metadata),
            "scene_context_fingerprint": scene_context_fingerprint(metadata),
            "approved_findings": {
                finding_fingerprint(finding): {
                    "kind": finding.get("kind"),
                    "class": finding.get("widget", {}).get("class"),
                    "object_name": finding.get("widget", {}).get("object_name"),
                    "text": normalize_text(finding.get("widget", {}).get("text", "")),
                }
                for finding in findings
            },
        }
    manifest = {
        "format": 2,
        "approval": approval,
        "policy": {
            "max_changed_ratio": max_changed_ratio,
            "max_rms": max_rms,
            "exact_pixels_required": False,
            "missing_approved_findings_are_ok": True,
            "new_findings_fail": True,
            "baseline_images_are_portable": True,
            "baseline_image_dir": manifest_relative_path(manifest_path, baseline_image_dir),
        },
        "scenes": scenes,
    }
    write_json(manifest_path, manifest)


def check(capture_dir: Path, manifest_path: Path, diff_dir: Path | None) -> int:
    manifest = read_json(manifest_path)
    policy = manifest.get("policy", {})
    try:
        max_changed_ratio = float(policy.get("max_changed_ratio", DEFAULT_MAX_CHANGED_RATIO))
    except (TypeError, ValueError):
        max_changed_ratio = DEFAULT_MAX_CHANGED_RATIO
    try:
        max_rms = float(policy.get("max_rms", DEFAULT_MAX_RMS))
    except (TypeError, ValueError):
        max_rms = DEFAULT_MAX_RMS
    baseline_scenes = manifest.get("scenes", {})
    current_scenes = scene_map(capture_dir)

    failures = policy_failures(policy) + approval_failures(manifest.get("approval"))
    results = []
    for scene, baseline in sorted(baseline_scenes.items()):
        current = current_scenes.get(scene)
        baseline_screenshot = resolve_manifest_path(manifest_path, baseline["screenshot"])
        if current is None:
            failures.append(
                {
                    "scene": scene,
                    "kind": "missing_scene",
                    **scene_artifacts(baseline_screenshot, None),
                }
            )
            continue

        current_screenshot = current["screenshot"]
        current_metadata = current["metadata_path"]
        diff_image = diff_dir / f"{scene}.diff.png" if diff_dir else None
        artifacts = scene_artifacts(
            baseline_screenshot,
            current_screenshot,
            diff_image,
            current_metadata,
        )
        expected_context = baseline.get("scene_context_fingerprint")
        expected_identity = baseline.get("scene_context_identity")
        current_context = scene_context_fingerprint(current["metadata"])
        if expected_context and expected_context != current_context:
            failures.append(
                {
                    "scene": scene,
                    "kind": "scene_context_changed",
                    "approved": expected_context,
                    "current": current_context,
                    **artifacts,
                }
            )
        if not expected_context:
            failures.append(
                {
                    "scene": scene,
                    "kind": "missing_scene_context_fingerprint",
                    **artifacts,
                }
            )
        if not expected_identity:
            failures.append(
                {
                    "scene": scene,
                    "kind": "missing_scene_context_identity",
                    **artifacts,
                }
            )

        metrics = image_metrics(baseline_screenshot, current_screenshot)
        if diff_dir and metrics["same_size"]:
            with Image.open(baseline_screenshot).convert("RGB") as base:
                with Image.open(current_screenshot).convert("RGB") as cur:
                    diff_dir.mkdir(parents=True, exist_ok=True)
                    ImageChops.difference(base, cur).save(diff_image)
        elif diff_image is not None:
            artifacts.pop("diff_image", None)

        image_failed = (
            not metrics["same_size"]
            or metrics["changed_ratio"] > max_changed_ratio
            or metrics["rms"] > max_rms
        )
        if image_failed:
            failures.append(
                {
                    "scene": scene,
                    "kind": "image_changed",
                    "metrics": metrics,
                    "policy": {
                        "max_changed_ratio": max_changed_ratio,
                        "max_rms": max_rms,
                    },
                    **artifacts,
                }
            )

        approved = set((baseline.get("approved_findings") or {}).keys())
        current_findings = current["metadata"].get("findings", [])
        current_fingerprints = {finding_fingerprint(finding): finding for finding in current_findings}
        new_findings = sorted(set(current_fingerprints) - approved)
        if new_findings:
            failures.append(
                {
                    "scene": scene,
                    "kind": "new_layout_findings",
                    "count": len(new_findings),
                    **artifacts,
                    "examples": [
                        {
                            "fingerprint": fp,
                            "finding": current_fingerprints[fp],
                        }
                        for fp in new_findings[:10]
                    ],
                }
            )

        results.append(
            {
                "scene": scene,
                "image": metrics,
                **artifacts,
                "scene_context_fingerprint": {
                    "approved": expected_context,
                    "current": current_context,
                },
                "scene_context_identity": scene_context_identity(current["metadata"]),
                "approved_scene_context_identity": expected_identity,
                "approved_finding_count": len(approved),
                "current_finding_count": len(current_findings),
                "new_finding_count": len(new_findings),
            }
        )

    extra_scenes = sorted(set(current_scenes) - set(baseline_scenes))
    for scene in extra_scenes:
        current = current_scenes[scene]
        failures.append(
            {
                "scene": scene,
                "kind": "unapproved_new_scene",
                **scene_artifacts(None, current["screenshot"], current_metadata=current["metadata_path"]),
            }
        )

    approval_command = (
        "Review baseline_screenshot/current_screenshot/diff_image artifacts, then run "
        f"{Path(__file__).name} approve --capture-dir {capture_dir} --manifest {manifest_path} "
        "--reviewer '<name>' --approval-note '<why this visual change is intentional>'"
    )
    report = {
        "result": "failed" if failures else "ok",
        "failure_count": len(failures),
        "manifest": str(manifest_path),
        "capture_dir": str(capture_dir),
        "diff_dir": artifact_path(diff_dir),
        "policy": {
            "max_changed_ratio": max_changed_ratio,
            "max_rms": max_rms,
            "new_findings_fail": policy.get("new_findings_fail"),
            "baseline_images_are_portable": policy.get("baseline_images_are_portable"),
        },
        "approval": manifest.get("approval"),
        "approval_command": approval_command,
        "failures": failures,
        "scene_results": results,
    }
    report["review_index"] = write_review_index(diff_dir, report, failures)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    approve_parser = sub.add_parser("approve", help="Create/update an approved manifest")
    approve_parser.add_argument("--capture-dir", type=Path, required=True)
    approve_parser.add_argument("--manifest", type=Path, required=True)
    approve_parser.add_argument(
        "--baseline-image-dir",
        type=Path,
        help=(
            "Directory for approved baseline screenshots. Defaults to a sibling "
            "<manifest-stem>.baseline-images directory."
        ),
    )
    approve_parser.add_argument("--max-changed-ratio", type=float, default=DEFAULT_MAX_CHANGED_RATIO)
    approve_parser.add_argument("--max-rms", type=float, default=DEFAULT_MAX_RMS)
    approve_parser.add_argument("--reviewer", required=True, help="Human reviewer approving this visual baseline")
    approve_parser.add_argument("--approval-note", required=True, help="Reason this visual baseline is approved")

    check_parser = sub.add_parser("check", help="Check a capture against an approved manifest")
    check_parser.add_argument("--capture-dir", type=Path, required=True)
    check_parser.add_argument("--manifest", type=Path, required=True)
    check_parser.add_argument("--diff-dir", type=Path)

    args = parser.parse_args()
    try:
        if args.command == "approve":
            approve(
                args.capture_dir,
                args.manifest,
                args.max_changed_ratio,
                args.max_rms,
                args.baseline_image_dir,
                args.reviewer,
                args.approval_note,
            )
            return 0
        if args.command == "check":
            return check(args.capture_dir, args.manifest, args.diff_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        print(
            json.dumps(
                {
                    "result": "failed",
                    "failure_count": 1,
                    "failures": [{"kind": type(exc).__name__, "message": str(exc)}],
                },
                indent=2,
            )
        )
        return 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
