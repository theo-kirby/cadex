# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dashboard works unchanged under a path prefix (ADR-551, orun3 P1).

Every URL the page fetches or links, and every URL the server builds into a
response, is relative to the page. A reverse proxy that mounts the dashboard
at ``/some/prefix/`` and rewrites nothing, neither bodies nor headers, is
then enough to host it: a request that escapes the prefix is a defect, and
the proxy below records each one.
"""

from __future__ import annotations

import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Any, Iterator
import urllib.parse

import pytest

from cadex_cli.review_server import serve, serve_projects
from test_app import _projects
from test_review_record import REVISION_B
from test_review_server import (
    _get, _json, _model_state, _open, _review_project, _stage_accepted, browser, needs_browser,  # noqa: F401
)

PREFIX = "/some/prefix/"


class _Proxy(ThreadingHTTPServer):
    """Forwards ``PREFIX<rest>`` to ``upstream/<rest>`` byte for byte; anything
    outside the prefix is a 404 and is kept in :attr:`strays`."""

    daemon_threads = True

    def __init__(self, upstream_port: int) -> None:
        self.upstream_port = upstream_port
        self.strays: list[str] = []
        super().__init__(("127.0.0.1", 0), _ProxyHandler)
        self.url = f"http://127.0.0.1:{self.server_address[1]}{PREFIX}"


class _ProxyHandler(BaseHTTPRequestHandler):
    server: _Proxy

    def log_message(self, *_args: Any) -> None:
        pass

    def _forward(self, method: str) -> None:
        if not self.path.startswith(PREFIX):
            self.server.strays.append(self.path)
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        upstream = http.client.HTTPConnection("127.0.0.1", self.server.upstream_port, timeout=30)
        try:
            upstream.request(method, "/" + self.path[len(PREFIX):],
                             headers={k: v for k, v in self.headers.items() if k.lower() != "host"})
            response = upstream.getresponse()
            body = response.read()
        finally:
            upstream.close()
        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in ("connection", "transfer-encoding", "server", "date"):
                self.send_header(key, value)
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._forward("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._forward("HEAD")


def _proxied(server) -> _Proxy:
    proxy = _Proxy(server.server_address[1])
    threading.Thread(target=proxy.serve_forever, name="prefix-proxy", daemon=True).start()
    return proxy


def _urls(value: Any, key: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _urls(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from _urls(v, key)
    elif isinstance(value, str) and key in ("url", "mesh"):
        yield key, value


def test_no_server_built_url_is_root_absolute(tmp_path) -> None:
    projects = _projects(tmp_path)
    _stage_accepted(projects / "biped", REVISION_B)
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        base = server.url + "p/biped/"
        documents = [_json(server.url + "api/projects"), _json(base + "api/project"),
                     _json(base + "api/model/accepted")]
        documents += [_json(base + "api/model/run/" + run["name"])
                      for run in documents[1]["runs"] if run.get("name")]
        found = [pair for document in documents for pair in _urls(document)]
        assert any(key == "mesh" for key, _ in found) and any(key == "url" for key, _ in found)
        assert [pair for pair in found if pair[1].startswith("/")] == []
        # Without its trailing slash the page redirects relative to itself.
        status, headers, _body = _get_no_redirect(server.url + "p/biped")
        assert (status, headers["location"]) == (301, "biped/")
    finally:
        server.shutdown()
        server.server_close()


def _get_no_redirect(url: str) -> tuple[int, dict[str, str], bytes]:
    parts = urllib.parse.urlsplit(url)
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=10)
    try:
        connection.request("GET", parts.path)
        response = connection.getresponse()
        return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
    finally:
        connection.close()


@needs_browser
def test_browser_loads_a_project_from_the_index_under_a_prefix(tmp_path, browser) -> None:
    projects = _projects(tmp_path)
    _stage_accepted(projects / "biped", REVISION_B)
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    proxy = _proxied(server)
    try:
        index = browser.page(proxy.url)
        index.wait_for("document.querySelectorAll('#projects li').length === 2")
        link = index.evaluate("document.querySelector(\"#projects li[data-project='biped'] a\").href")
        assert link == proxy.url + "p/biped/"
        # The bare project path redirects inside the prefix, not out of it.
        project = _open(browser, proxy.url + "p/biped")
        assert project.evaluate("location.pathname") == PREFIX + "p/biped/"
        assert project.text("#project-name") == "biped"
        assert _model_state(project) == "loaded"
        assert project.evaluate("window.cadexReview.viewer().stats()")["components"] >= 1
        # The File menu lists the other projects through the same prefix.
        project.wait_for("document.querySelectorAll('#project-select option').length === 2")
        assert project.evaluate("new URL(document.getElementById('home').href).pathname") == PREFIX
        assert proxy.strays == []
    finally:
        proxy.shutdown()
        proxy.server_close()
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_loads_a_single_project_review_under_a_prefix(tmp_path, browser) -> None:
    root = _review_project(tmp_path)
    _stage_accepted(root, REVISION_B)
    server, _thread = serve(root, "127.0.0.1", 0)
    proxy = _proxied(server)
    try:
        page = _open(browser, proxy.url)
        assert _model_state(page) == "loaded"
        assert page.evaluate("window.cadexReview.viewer().stats()")["components"] >= 1
        # `cadex review` has no index to go home to, prefix or not.
        assert page.evaluate("document.getElementById('home').hidden") is True
        assert proxy.strays == []
    finally:
        proxy.shutdown()
        proxy.server_close()
        server.shutdown()
        server.server_close()
