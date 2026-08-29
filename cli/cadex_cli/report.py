# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""What a run says when it finishes: the ``--json`` envelope and the prose.

Two audiences, one source. A person wants to know what was built and where
the files went; a pipeline wants the revision to guard its next call, the
digest to tell whether the geometry actually moved, and the parameters it is
about to sweep. Both are derived from the same :class:`RunReport`, so the
human line can never say something the JSON does not.

The digest is the thing worth pointing at twice: it is the engine's content
hash of the model, it is stable across runs, and it is what a pipeline
should compare. Do not compare exported files — STEP embeds a timestamp
(see :mod:`cadex_cli.export`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import sys
from typing import Any, Mapping, TextIO

from . import CLI_SCHEMA
from .export import ExportedOutput

#: Exit codes, so a pipeline can branch on *why* rather than on stderr.
EXIT_OK = 0
EXIT_FAILURE = 1  # the engine or the agent could not do it
EXIT_USAGE = 2  # the command was wrong
EXIT_REJECTED = 3  # the engine refused the script it was given


@dataclass
class RunReport:
    """Everything a finished run knows, in one place."""

    ok: bool = False
    project_root: str = ""
    #: The revision the *next* write must be guarded with.
    revision: str = ""
    accepted_revision: str = ""
    digest: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    outputs: list[ExportedOutput] = field(default_factory=list)
    session_id: str = ""
    model: str = ""
    engine: dict[str, str] = field(default_factory=dict)
    out_dir: str = ""
    error: str = ""
    #: Free-form notes worth printing but not worth a field of their own.
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": CLI_SCHEMA,
            "ok": bool(self.ok),
            "project_root": self.project_root,
            "revision": self.revision,
            "accepted_revision": self.accepted_revision,
            "digest": self.digest,
            "params": self.params,
            "outputs": [output.to_json() for output in self.outputs],
            "session_id": self.session_id,
        }
        if self.model:
            payload["model"] = self.model
        if self.engine:
            payload["engine"] = self.engine
        if self.out_dir:
            payload["out_dir"] = self.out_dir
        if self.notes:
            payload["notes"] = list(self.notes)
        if self.error:
            payload["error"] = self.error
        return payload


def params_from_script(script: Mapping[str, Any] | None) -> dict[str, Any]:
    """The effective parameter values: declared defaults under stored values.

    ``inspect scope=script`` reports specs and values separately, and the
    values map holds only what has been *set*. A pipeline wants the value a
    rebuild would actually use, which is the default until something
    overrides it.
    """

    block = (script or {}).get("params") or {}
    values = dict(block.get("values") or {})
    effective: dict[str, Any] = {}
    for spec in block.get("specs") or []:
        if not isinstance(spec, Mapping):
            continue
        name = str(spec.get("name") or "")
        if not name:
            continue
        effective[name] = values.get(name, spec.get("default"))
    for name, value in values.items():
        effective.setdefault(str(name), value)
    return effective


def apply_modeling_reply(report: RunReport, reply: Mapping[str, Any]) -> None:
    """Fold an accepted modelling reply's identity into the report."""

    report.revision = str(
        (reply.get("model_state") or {}).get("next_write_expected_revision") or ""
    ) or report.revision
    report.accepted_revision = str(reply.get("accepted_revision") or "") or (
        report.accepted_revision
    )
    report.digest = str(reply.get("digest") or "") or report.digest


def emit(report: RunReport, *, as_json: bool, stream: TextIO | None = None) -> None:
    """Print the report, one way or the other."""

    out = stream if stream is not None else sys.stdout
    if as_json:
        out.write(json.dumps(report.to_json(), indent=2, sort_keys=True) + "\n")
        out.flush()
        return
    for line in human_lines(report):
        out.write(line + "\n")
    out.flush()


def human_lines(report: RunReport) -> list[str]:
    """The prose summary, as lines."""

    lines: list[str] = []
    if report.error:
        lines.append(f"error: {report.error}")
    if report.digest:
        lines.append(f"model  {report.digest[:16]}  ({report.project_root})")
    elif report.project_root:
        lines.append(f"model  ({report.project_root})")
    if report.params:
        rendered = ", ".join(
            f"{name}={_short(value)}" for name, value in sorted(report.params.items())
        )
        lines.append(f"params {rendered}")
    written = [output for output in report.outputs if output.files]
    for output in written:
        files = "  ".join(path for _, path in sorted(output.files.items()))
        lines.append(f"wrote  {output.name}  {files}")
    skipped = [output for output in report.outputs if output.skipped]
    for output in skipped:
        lines.append(f"  --   {output.name}: {output.skipped}")
    for note in report.notes:
        lines.append(f"note   {note}")
    if report.revision:
        lines.append(f"next   expected_revision {report.revision[:16]}")
    return lines


def _short(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)
