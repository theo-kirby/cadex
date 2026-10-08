# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The home page (ADR-605): `cadex app`'s index as the home of a viewer.

``/api/projects`` keeps its four top-level keys and gives each project a
card: counts, the latest evaluation's verdict, a thumbnail (the presentation
hero, a passing evaluation's hero, a film sheet's first frame, or the
concept sheet), the stage as Status would read it from the newest run, and
when anything last moved. The page puts the project that moved last in a
spotlight and every project in a grid of cards, newest first, and follows on
its poll.
"""

from __future__ import annotations

import json
import time

from cadex_cli import review_server
from cadex_cli.review_server import serve_projects
from test_app import _projects
from test_review_evaluation import _heroes, _passing
from test_review_record import REVISION_B
from test_review_server import _get, _json, _rewrite_record, _telemetry, browser, needs_browser  # noqa: F401


CARD_KEYS = {"name", "url", "accepted", "runs", "revisions", "evaluations", "latest_evaluation",
             "thumbnail", "stage", "active_at"}


def _listing(server) -> dict:
    return {entry["name"]: entry for entry in _json(server.url + "api/projects")["projects"]}


def test_each_project_carries_its_card(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(review_server, "CARD_TTL_S", 0.0)
    projects = _projects(tmp_path)
    biped = projects / "biped"
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        listing = _json(server.url + "api/projects")
        assert set(listing) == {"schema", "root", "projects", "served_at"}
        cards = {entry["name"]: entry for entry in listing["projects"]}
        assert all(set(card) == CARD_KEYS for card in cards.values())
        empty = cards["empty"]
        assert (empty["revisions"], empty["evaluations"], empty["latest_evaluation"], empty["thumbnail"],
                empty["active_at"]) == (0, 0, None, None, None)
        assert empty["stage"]["state"] == "idle" and empty["stage"]["run"] is None
        # The biped's runs are recorded: it has moved, and its newest run is the one read.
        assert cards["biped"]["active_at"] and cards["biped"]["stage"]["run"] in ("first", "second", "broken")

        # A passing evaluation with its heroes: the verdict, and the hero as the picture.
        _heroes(_passing(biped, revision=REVISION_B))
        card = _listing(server)["biped"]
        assert card["evaluations"] == 1
        assert {k: card["latest_evaluation"][k] for k in ("name", "verdict", "passed", "seeds")} == {
            "name": "steady", "verdict": "pass", "passed": 2, "seeds": 2}
        thumb = card["thumbnail"]
        assert thumb["source"] == "evaluation" and thumb["url"].startswith("p/biped/evaluation/steady/hero.png?v=")
        status, headers, body = _get(server.url + thumb["url"])
        assert status == 200 and headers["content-type"] == "image/png" and body.startswith(b"\x89PNG")

        # Training: the newest run's iteration of its total, on the next listing.
        run = biped / "runs" / "second"
        _rewrite_record(run, status="running", recorded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        (run / "train").mkdir(exist_ok=True)
        _telemetry(biped, 6, run="second")
        stage = _listing(server)["biped"]["stage"]
        assert (stage["state"], stage["run"], stage["iteration"], stage["total"]) == ("training", "second", 6, 10)
    finally:
        server.shutdown()
        server.server_close()


def test_a_card_is_reused_until_what_it_reads_moves(tmp_path) -> None:
    """Many projects stay cheap to list: an unchanged project is not read
    again inside :data:`CARD_TTL_S`, and a change to what it reads is seen
    on the next listing however young the card."""

    projects = _projects(tmp_path)
    reads = []
    original = review_server.project_card
    review_server.project_card = lambda root, name: reads.append(name) or original(root, name)
    try:
        directory = review_server.ProjectsDirectory(projects)
        review_server._CARD_MEMO.clear()
        directory.listing()
        directory.listing()
        assert sorted(reads) == ["biped", "empty"]
        _passing(projects / "biped", revision=REVISION_B)
        card = {p["name"]: p for p in directory.listing()["projects"]}["biped"]
        assert reads.count("biped") == 2 and card["latest_evaluation"]["verdict"] == "pass"
    finally:
        review_server.project_card = original


def test_an_unreadable_project_does_not_fail_the_listing(tmp_path, monkeypatch) -> None:
    projects = _projects(tmp_path)
    review_server._CARD_MEMO.clear()

    def broken(root, name):
        if name == "biped":
            raise ValueError("bad record")
        return original(root, name)
    original = review_server.project_card
    monkeypatch.setattr(review_server, "project_card", broken)
    cards = {p["name"]: p for p in review_server.ProjectsDirectory(projects).listing()["projects"]}
    assert cards["biped"]["stage"]["reason"].startswith("unreadable: bad record")
    assert cards["empty"]["stage"]["state"] == "idle"


HOME = """(function () {
  function q(s) { return document.querySelector(s); }
  return {spotlight: q('#spotlight').hidden ? null : q('#spotlight-link').textContent,
          spotlight_href: q('#spotlight-link').getAttribute('href'),
          spotlight_img: (q('#spotlight-media img') || {}).src || null,
          cards: Array.from(document.querySelectorAll('#projects li')).map(function (li) {
            var img = li.querySelector('.thumb img');
            return {name: li.dataset.project, stage: li.dataset.stage, href: li.querySelector('a').getAttribute('href'),
                    img: img ? img.getAttribute('src') : null, placeholder: !!li.querySelector('.thumb svg.placeholder'),
                    chips: Array.from(li.querySelectorAll('.chip')).map(function (c) { return c.textContent; }),
                    bar: !!li.querySelector('.progress')}; }),
          scroll: document.documentElement.scrollWidth, inner: innerWidth};
})()"""


@needs_browser
def test_browser_home_spotlights_the_latest_and_follows_live(tmp_path, browser, monkeypatch) -> None:
    monkeypatch.setattr(review_server, "CARD_TTL_S", 0.0)
    projects = _projects(tmp_path)
    biped = projects / "biped"
    _heroes(_passing(biped, revision=REVISION_B))
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        page = browser.page(server.url)
        page.wait_for("document.querySelectorAll('#projects li').length === 2 && !document.getElementById('spotlight').hidden")
        home = page.evaluate(HOME)
        assert home["spotlight"] == "biped" and home["spotlight_href"] == "p/biped/"
        assert "/evaluation/steady/hero.png" in home["spotlight_img"]
        biped_card, empty_card = home["cards"]
        assert (biped_card["name"], biped_card["href"]) == ("biped", "p/biped/")
        assert biped_card["img"].startswith("p/biped/evaluation/steady/hero.png") and "pass 2/2" in biped_card["chips"]
        assert empty_card["placeholder"] and empty_card["img"] is None and empty_card["chips"] == ["idle"]
        # The page's poll carries a run starting to train: a chip and a bar, no reload.
        run = biped / "runs" / "second"
        _rewrite_record(run, status="running", recorded_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        _telemetry(biped, 4, run="second")
        page.wait_for("document.querySelector(\"#projects li[data-project='biped']\").dataset.stage === 'training'",
                      timeout=15)
        assert page.evaluate(HOME)["cards"][0]["bar"] is True
        assert page.text("#spotlight-stage") == "training"
        # A filter narrows the grid and hides the spotlight; it is kept in the URL.
        page.evaluate("var f = document.getElementById('projects-filter'); f.value = 'emp';"
                      " f.dispatchEvent(new Event('input')); true")
        filtered = page.evaluate(HOME)
        assert [c["name"] for c in filtered["cards"]] == ["empty"] and filtered["spotlight"] is None
        assert page.evaluate("location.search") == "?q=emp"

        phone = browser.page("about:blank")
        phone.send("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        phone.send("Page.navigate", {"url": server.url})
        phone.wait_for("document.querySelectorAll('#projects li').length === 2")
        small = phone.evaluate(HOME)
        assert small["scroll"] <= 390
        gutter = phone.evaluate("document.querySelector('#projects li').getBoundingClientRect().left")
        assert gutter == 16
    finally:
        server.shutdown()
        server.server_close()
