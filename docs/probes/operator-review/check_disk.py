# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Check per-run disk use (ADR-322) on the PERSISTENT dashboard.

usage: check_disk.py PROJECT URL OUT.json
Never starts or stops a server. Reads the run list, takes the reader's own
fresh-visit rule for the default run, opens the page headlessly, waits for
the disk panel, and holds what it shows to an independent walk of that run's
directory (each inode once, no symlink followed) and to the record's own
shared project references. Then selects an older historical video run,
plays its video, polls, and checks the selection, playback and count stayed;
then returns to current. Writes a compact receipt without images.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from cdp_browser import HeadlessBrowser, find_browser
from cadex_cli.review_server import default_run

project = Path(sys.argv[1]).resolve()
url = sys.argv[2].rstrip("/") + "/"
out = Path(sys.argv[3])


def apparent(top: Path) -> tuple[int, int]:
    seen, total, files = set(), 0, 0
    for directory, _dirs, names in os.walk(top):
        for name in names:
            path = os.path.join(directory, name)
            if os.path.islink(path):
                continue
            stat = os.lstat(path)
            if (stat.st_dev, stat.st_ino) in seen:
                continue
            seen.add((stat.st_dev, stat.st_ino))
            total += stat.st_size
            files += 1
    return total, files


def get(path: str):
    with urllib.request.urlopen(url + path, timeout=30) as response:
        return json.load(response)


review = get("api/project")
assert all("disk" not in run for run in review["runs"]), "the run list must not carry disk use"
default = default_run(review)
assert default != "accepted"
detail = get("api/run/" + default)
disk = detail["disk"]
assert disk["schema"] == "cadex-run-disk-use-v1" and disk["state"] == "counted", disk
independent = apparent(project / "runs" / default)
assert (disk["bytes"], disk["files"]) == independent, (disk["bytes"], disk["files"], independent)
shared = {key: item for key, item in disk["references"]["project_artifacts"].items()
          if item["status"] == "retained" and not item["in_run"]}
for key, item in shared.items():
    assert item["bytes"] == (project / item["path"]).stat().st_size
    for other in item["shared_with"]:
        other_record = json.loads((project / "runs" / other / "run.json").read_text())
        assert item["path"] in other_record["project_artifacts"].values(), (key, other)
assert disk["shared_bytes"] == sum(item["bytes"] for item in shared.values())
historical = [run for run in review["runs"] if run["run"] != default and run["videos"]
              and run["relation"] == "historical"]
older = historical[-1]["run"] if historical else None
receipt = {
    "adr": "ADR-322", "url": url, "project": project.name,
    "checked_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "runs": len(review["runs"]), "list_has_disk": False,
    "default_run_rule": default,
    "default_disk": {"bytes": disk["bytes"], "files": disk["files"], "by_dir": disk["by_dir"],
                     "hardlinked_entries": disk["hardlinked_entries"], "skipped_count": disk["skipped_count"],
                     "independent_walk": {"bytes": independent[0], "files": independent[1]},
                     "shared": {key: {"path": item["path"], "bytes": item["bytes"], "shared_with": item["shared_with"]}
                                for key, item in shared.items()},
                     "shared_bytes": disk["shared_bytes"]},
    "runs_total_bytes": sum(get("api/run/" + run["run"])["disk"]["bytes"] for run in review["runs"]),
}
with HeadlessBrowser(find_browser()) as browser:
    started = time.monotonic()
    page = browser.page(url)
    page.evaluate("window.cadexReview.ready", await_promise=True)
    assert page.text("#project-name") == project.name + " — review"
    assert page.text("#view-kind") == "RUN " + default
    page.wait_for("document.getElementById('disk').dataset.state === 'counted'")
    receipt["ready_seconds"] = round(time.monotonic() - started, 2)
    assert page.attribute("#disk-summary", "data-bytes") == str(disk["bytes"])
    assert page.attribute("#disk-summary", "data-files") == str(disk["files"])
    assert page.attribute("#disk-summary", "data-shared-bytes") == str(disk["shared_bytes"])
    dirs = dict(page.evaluate("Array.from(document.querySelectorAll('#disk-dirs li[data-dir]')).map(n => [n.dataset.dir, +n.dataset.bytes])"))
    assert dirs == {key: item["bytes"] for key, item in disk["by_dir"].items()}, (dirs, disk["by_dir"])
    shown_shared = page.evaluate("Array.from(document.querySelectorAll('#disk-shared li[data-key]')).map(n => [n.dataset.key, n.dataset.shared, +n.dataset.bytes])")
    assert {item[0]: item[2] for item in shown_shared} == {key: item["bytes"] for key, item in shared.items()}
    sizes = page.evaluate("Array.from(document.querySelectorAll('#artifacts tbody tr')).map(n => [n.dataset.group, n.dataset.key, n.querySelector('td:nth-child(4)').dataset.size])")
    for group, key, size in sizes:
        sized = disk["references"]["project_docs"] if (group, key) == ("artifacts", "project_docs") else disk["references"][group][key]
        expected = str(sized["bytes"]) if sized["status"] == "retained" else {"missing": "missing", "refused": "refused"}.get(sized["status"], "none")
        assert size == expected, (group, key, size, expected)
    receipt["default_view"] = {"run": default, "revision": page.text("#view-revision"), "relation": page.text("#view-relation")[:40],
                               "summary": page.text("#disk-summary"), "size_cells": len(sizes),
                               "video_label_has_size": any(unit in page.text("#videos") for unit in (" KB", " MB"))}
    if older:
        page.click("#views li[data-run='%s']" % older)
        page.wait_for("document.getElementById('view-kind').textContent === " + json.dumps("RUN " + older))
        page.wait_for("document.getElementById('disk').dataset.state === 'counted'")
        older_disk = get("api/run/" + older)["disk"]
        assert page.attribute("#disk-summary", "data-bytes") == str(older_disk["bytes"])
        assert (older_disk["bytes"], older_disk["files"]) == apparent(project / "runs" / older)
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2", timeout=30)
        page.evaluate("window.playing = document.querySelector('#videos video'); playing.muted = true; playing.loop = true; playing.play()", await_promise=True)
        page.wait_for("playing.currentTime > 0.1")
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        assert page.text("#view-kind") == "RUN " + older
        assert page.evaluate("playing === document.querySelector('#videos video') && !playing.paused")
        assert page.attribute("#disk-summary", "data-bytes") == str(older_disk["bytes"])
        receipt["historical_view"] = {"run": older, "relation": page.text("#view-relation")[:40],
                                      "bytes": older_disk["bytes"], "files": older_disk["files"],
                                      "shared_with": {key: item["shared_with"] for key, item in older_disk["references"]["project_artifacts"].items()
                                                      if item["status"] == "retained" and not item["in_run"]},
                                      "playback_kept_through_two_polls": True, "count_kept": True}
    page.click("#current-run")
    page.wait_for("document.getElementById('view-kind').textContent === " + json.dumps("RUN " + default))
    page.wait_for("document.getElementById('disk').dataset.state === 'counted'")
    receipt["route_back_to_current"] = page.evaluate("window.cadexReview.state().disk.bytes") == disk["bytes"]
out.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
