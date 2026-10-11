"""The record slugs in the project's governor graph, for tests that check a report's citations.

The graph lives in the main checkout's Flywheel repository (`.flywheel/`) and is
read through the `governor` CLI. A checkout without either has no graph to resolve, so
`record_slugs()` returns None and those checks skip.
"""

from __future__ import annotations

import functools
import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Where the old Hypergraph working copy kept record files; older reports still link there.
LEGACY_RECORDS = REPO / ".hypergraph" / "graph" / "record"


@functools.cache
def record_slugs() -> frozenset[str] | None:
    if shutil.which("governor") is None:
        return None
    try:
        out = subprocess.run(["governor", "snapshot"], cwd=REPO, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode:
        return None
    nodes = json.loads(out.stdout).get("nodes", {}).values()
    slugs = frozenset(n["slug"] for n in nodes if n.get("kind") == "record" and n.get("live", True))
    return slugs or None


def is_record_link(target: Path) -> bool:
    """A link into the old record working copy, which no checkout has any more."""
    return LEGACY_RECORDS in target.resolve().parents
