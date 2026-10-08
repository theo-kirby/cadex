# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The agent's own Status panel (ADR-607).

A project's ``status.html`` is served at ``status/panel.html`` under a
sandboxing Content-Security-Policy, only as a regular file inside the project
and under a size cap, and embedded in an ``<iframe sandbox="allow-scripts">``
with no same-origin. It fetches nothing; the page posts it a
``cadex-status-panel-v1`` message on each poll, and it draws from that.
"""

from __future__ import annotations

import os
import time

import pytest

from cadex_cli.guidance import OVERLAY
from cadex_cli.review_server import STATUS_PANEL_LIMIT, serve, serve_projects
from test_review_server import _get, _json, _open, _review_project, browser, needs_browser  # noqa: F401
from test_review_status import RUN, _biped_progress, _training_project

CSP = ("sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; "
       "style-src 'unsafe-inline'; img-src data:; font-src data:")
PANEL = "<!DOCTYPE html><html><body><p id='x'>panel</p></body></html>"


@pytest.fixture
def served(tmp_path):
    root = _review_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        yield root, server
    finally:
        server.shutdown()
        server.server_close()


def test_no_panel_is_a_404_and_says_so(served) -> None:
    root, server = served
    assert _get(server.url + "status/panel.html")[0] == 404
    assert _json(server.url + "api/project")["stage"]["panel"] == {
        "available": False, "reason": "no status.html in the project"}


def test_the_panel_is_served_sandboxed_and_nosniff(served) -> None:
    root, server = served
    (root / "status.html").write_text(PANEL)
    panel = _json(server.url + "api/project")["stage"]["panel"]
    assert panel["available"] is True and panel["bytes"] == len(PANEL)
    assert panel["url"].startswith("status/panel.html?v=")
    for url in ("status/panel.html", panel["url"]):
        status, headers, body = _get(server.url + url)
        assert status == 200 and body == PANEL.encode()
        assert headers["content-type"] == "text/html; charset=utf-8"
        assert headers["content-security-policy"] == CSP
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["referrer-policy"] == "no-referrer"
    # Nothing else of the project is reachable by a path like it.
    for other in ("status/status.html", "status/../status.html", "status.html", "status/panel.html/x"):
        assert _get(server.url + other)[0] == 404, other


def test_a_symlink_or_an_oversize_panel_is_refused(served, tmp_path) -> None:
    root, server = served
    outside = tmp_path / "secret.html"
    outside.write_text("<p>outside</p>")
    (root / "status.html").symlink_to(outside)
    assert _get(server.url + "status/panel.html")[0] == 404
    panel = _json(server.url + "api/project")["stage"]["panel"]
    assert panel["available"] is False and "refused" in panel["reason"]
    # A link to a file inside the project is refused too: only a regular file is the panel.
    (root / "status.html").unlink()
    (root / "inside.html").write_text(PANEL)
    (root / "status.html").symlink_to(root / "inside.html")
    assert _get(server.url + "status/panel.html")[0] == 404
    (root / "status.html").unlink()
    (root / "status.html").write_bytes(b" " * (STATUS_PANEL_LIMIT + 1))
    assert _get(server.url + "status/panel.html")[0] == 404
    assert "over" in _json(server.url + "api/project")["stage"]["panel"]["reason"]
    # A directory by that name is not a panel either.
    (root / "status.html").unlink()
    os.mkdir(root / "status.html")
    assert _get(server.url + "status/panel.html")[0] == 404


def test_the_app_serves_a_projects_panel_under_its_prefix(tmp_path) -> None:
    (tmp_path / "projects").mkdir()
    root = _review_project(tmp_path / "projects")
    (root / "status.html").write_text(PANEL)
    server, _thread = serve_projects(root.parent, "127.0.0.1", 0)
    try:
        status, headers, _body = _get(server.url + f"p/{root.name}/status/panel.html")
        assert status == 200 and headers["content-security-policy"] == CSP
    finally:
        server.shutdown()
        server.server_close()


def test_the_guidance_tells_the_agent_it_may_write_a_panel() -> None:
    text = " ".join(OVERLAY.split())
    for needed in ("YOU MAY GIVE THE DASHBOARD A STATUS PANEL", "status.html", "cadex-status-panel-v1",
                   "can fetch nothing", "docs/DASHBOARD.md, section 23"):
        assert needed in text, needed


#: A panel that draws from the message and reports back what it drew, and
#: whether it could reach anything on its own.
PROBE_PANEL = """<!DOCTYPE html><html><body><p id="out">waiting</p><script>
var seen = 0;
addEventListener('message', function (e) {
  var m = e.data;
  if (!m || m.type !== 'cadex-status' || m.schema !== 'cadex-status-panel-v1') return;
  seen += 1;
  document.getElementById('out').textContent = m.project + ' iteration ' + (m.training.iteration + 1)
    + ' points ' + m.training.curves.curve.length + ' runs ' + m.runs.length;
  var parentDom;
  try { parentDom = parent.document.title; } catch (err) { parentDom = 'blocked'; }
  var report = function (fetched) {
    parent.postMessage({type: 'panel-probe', text: document.getElementById('out').textContent, seen: seen,
                        fetched: fetched, parent: parentDom, origin: String(self.origin),
                        ink: m.theme.tokens['--ink'], theme: m.theme.name}, '*');
  };
  fetch('../api/project').then(function () { report('allowed'); }, function () { report('blocked'); });
});
parent.postMessage({type: 'cadex-status-ready'}, '*');
</script></body></html>"""


@needs_browser
def test_browser_the_panel_draws_from_the_message_and_reaches_nothing(tmp_path, browser) -> None:
    root = _training_project(tmp_path)
    (root / "status.html").write_text(PROBE_PANEL)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.__probes = []; addEventListener('message', function (e) {"
                      " if (e.data && e.data.type === 'panel-probe') window.__probes.push(e.data); }); true")
        page.wait_for("window.CadexStatus.tab() === 'project' && !!document.querySelector('#status-panel iframe')")
        frame = page.evaluate("(function () { var f = document.querySelector('#status-panel iframe');"
                              " return {sandbox: f.getAttribute('sandbox'), src: f.getAttribute('src'),"
                              " tabs: !document.getElementById('status-tabs').hidden}; })()")
        assert frame["sandbox"] == "allow-scripts" and frame["src"].startswith("status/panel.html?v=")
        assert frame["tabs"] is True
        page.wait_for("window.__probes.length > 0", timeout=15)
        probe = page.evaluate("window.__probes[window.__probes.length - 1]")
        assert probe["text"].startswith(root.name + " iteration 40 points 40 runs 4"), probe
        assert probe["fetched"] == "blocked" and probe["parent"] == "blocked" and probe["origin"] == "null"
        assert probe["theme"] == "dark" and probe["ink"] == "#ededed"
        # The trainer writes on: the next poll's message carries it, with no reload.
        _biped_progress(root, 99)
        page.wait_for("window.__probes.some(function (p) { return p.text.indexOf('iteration 100 ') > 0; })", timeout=15)
        # The theme follows.
        page.evaluate("window.cadexTheme.set('light')")
        page.wait_for("window.__probes.some(function (p) { return p.theme === 'light' && p.ink === '#1c1c1c'; })", timeout=10)
        # Training stays a tab away, and the panel goes when the file does.
        page.click("#status-tabs button[data-tab=training]")
        assert page.evaluate("document.getElementById('status-training').hidden") is False
        (root / "status.html").unlink()
        page.wait_for("document.getElementById('status-tabs').hidden && !document.querySelector('#status-panel iframe')",
                      timeout=10)
        page.evaluate("window.cadexTheme.set('dark')")
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_status_charts_every_measure_with_axes(tmp_path, browser) -> None:
    """ADR-606: four charts on their own axes, the best marked on reward, the
    runs listed with their outcome, and the charts follow the area's width."""

    root = _training_project(tmp_path)
    _biped_progress(root, 119, action_std_curve=[[i, 0.5 - i / 1000] for i in range(120)], action_std=0.381,
                    checkpoints=[{"path": f"walk.{i:06d}.cxpolicy", "iteration": i, "sha256": "0" * 64,
                                  "reward_per_step": 1.0} for i in (49, 99)])
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        page.evaluate("window.cadexReview.layout().reset()")
        page.wait_for("document.querySelectorAll('#status-charts .chart-line').length === 4")
        charts = page.evaluate("""(function () {
          return Array.from(document.querySelectorAll('#status-charts svg')).map(function (s) {
            return {id: s.id, ticks: s.querySelectorAll('.chart-label text').length,
                    width: s.getBoundingClientRect().width,
                    best: !!s.querySelector('.chart-best'), checkpoints: s.querySelectorAll('.chart-checkpoint').length}; });
        })()""")
        assert [c["id"] for c in charts] == ["status-reward", "status-loss", "status-episode", "status-std"]
        assert all(c["ticks"] >= 4 for c in charts), charts
        assert charts[0]["best"] and charts[0]["checkpoints"] == 2 and not charts[1]["best"]
        assert page.text("#status-std-now") == "0.381"
        rows = page.evaluate("Array.from(document.querySelectorAll('#status-runs-body tr')).map(function (r) {"
                             " return [r.dataset.run, r.dataset.current]; })")
        assert rows[0] == [RUN, "true"] and len(rows) == 4
        # Wider area, wider charts.
        before = charts[0]["width"]
        page.evaluate("window.cadexReview.layout().preset('side')")
        page.wait_for(f"document.getElementById('status-reward').getBoundingClientRect().width > {before} + 50")
        page.wait_for("(function () { var s = document.getElementById('status-reward');"
                      " return Math.abs(Number(s.getAttribute('viewBox').split(' ')[2]) - s.getBoundingClientRect().width) <= 1; })()",
                      timeout=5)
        page.evaluate("window.cadexReview.layout().reset()")
    finally:
        server.shutdown()
        server.server_close()
