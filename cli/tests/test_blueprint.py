# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The blueprint composer (ADR-516): a dimensioned multi-view drawing sheet.

The owner kept the shell's composer as a headless tool (orun2 owner notes).
``CadexStudio.blueprint_sheet`` draws it -- line views on one shared scale,
overall extents and declared measurements, numbered callouts keyed in a
parts list, a title block -- the bridge's ``draw_blueprint`` stores it
through ``put_blueprint``, versioned by name, and the dashboard lists it
under Drawings. Proved without an engine for the composer and the bridge,
then against a real engine in headless Chromium.
"""

from __future__ import annotations

import base64
import json
import struct
import zlib

import pytest

from cadex_cli.__main__ import main
from cadex_cli.bridge import Bridge
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.report import EXIT_OK
from cadex_cli.review_server import blueprint_listing, serve_projects
from cadex_cli.studio import STUDIO as studio
from fake_cadexd import FakeCadexd, inspect_reply
from test_look import _box, _mesh, _reply
from test_review_server import _get, _json, _open, browser, needs_browser  # noqa: F401

FIT = {'failing': [{'first': 'c_floor', 'second': '', 'status': 'world geometry'}]}


def _plate_reply(tmp_path, measurements=()):
    """One unplaced 60x40x10 mm part, with declared measurement entries beside it."""
    revision = 'b' * 64
    display = {'plate': {'artifact_kind': 'brep', 'artifact_path': '/staging/plate.brep', 'placement': None,
                         'tessellation': _mesh(tmp_path, 'plate', *_box((60, 40, 10)))}}
    for name, record in measurements:
        display[name] = {'artifact_kind': None, 'artifact_path': None, 'placement': None,
                         'tessellation': None, 'measurement': record}
    return {'ok': True, 'revision': revision, 'accepted_revision': revision, 'digest': 'e' * 64,
            'display': display}


HEIGHT = {'kind': 'extent', 'label': 'overall height', 'text': '10.00 mm', 'value_mm': 10.0,
          'anchors_mm': [[30.0, 20.0, 0.0], [30.0, 20.0, 10.0]]}
BORE = {'kind': 'diameter', 'label': 'bore', 'text': '\N{DIAMETER SIGN}6.00 mm', 'value_mm': 6.0,
        'center_mm': [30.0, 20.0, 10.0], 'radius_mm': 3.0, 'normal': [0.0, 0.0, 1.0], 'anchors_mm': None}


def _rgb(data):
    """Decode one of the studio's own PNGs (8-bit RGB, filter 0 rows) to a flat byte string."""
    width, height = _size(data)
    raw = zlib.decompress(data[data.index(b'IDAT') + 4:data.index(b'IEND') - 8])
    stride = 3 * width + 1
    return b''.join(raw[r * stride + 1:(r + 1) * stride] for r in range(height))


def _size(data):
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    return struct.unpack('>2I', data[16:24])


def test_the_recipe_refuses_with_the_fix_and_defaults_to_third_angle():
    recipe = studio.blueprint_recipe({'name': '  gearbox   overview '})
    assert recipe == {'schema': studio.BLUEPRINT_RECIPE_SCHEMA, 'name': 'gearbox overview',
                      'views': ['top', 'iso', 'front', 'right'], 'callouts': True,
                      'dimensions': True, 'notes': ''}
    for bad, words in (({}, 'needs a name'), ({'name': 'x' * 61}, 'needs a name'),
                       ({'name': 'a', 'views': ['side']}, 'views is 1 to 4'),
                       ({'name': 'a', 'views': ['top'] * 2}, 'distinct'),
                       ({'name': 'a', 'views': ['top', 'iso', 'front', 'right', 'iso_back']}, '1 to 4'),
                       ({'name': 'a', 'callouts': 'all'}, 'callouts is'),
                       ({'name': 'a', 'dimensions': 1}, 'dimensions is'),
                       ({'name': 'a', 'notes': 'n' * 401}, 'notes is'),
                       ({'name': 'a', 'theme': 'blue'}, 'unknown blueprint key')):
        with pytest.raises(studio.StudioError, match=words):
            studio.blueprint_recipe(bad)


def test_a_sheet_shares_one_scale_and_dimensions_the_overall_extents(tmp_path):
    data, facts = studio.blueprint_report(_reply(tmp_path), FIT, None, {'name': 'body and pin'},
                                          project='orun2-pin', version=3, date='2026-10-03')
    assert _size(data) == (studio.WIDTH, studio.HEIGHT)
    assert facts['views'] == ['top', 'iso', 'front', 'right'] and facts['version'] == 3
    # The floor is environment: the extents are the body and the pin only.
    overall = {(d['view'], d['axis']): d['mm'] for d in facts['dimensions'] if d['source'] == 'overall'}
    assert overall == {('top', 'X'): 35.0, ('top', 'Y'): 20.0, ('front', 'X'): 35.0, ('front', 'Z'): 30.0,
                       ('right', 'Y'): 20.0, ('right', 'Z'): 30.0}
    # One scale: the largest projected span fills the cell, every view drawn at it.
    side = min((studio.WIDTH - 3 * 24 - 384) // 2, (studio.HEIGHT - 48) // 2) - 2 * 64
    largest = max(max(v['span_mm']) for v in facts['view_spans'].values())
    assert facts['scale_px_per_mm'] == pytest.approx(side / (largest * 1.04), abs=1e-3)
    # Callouts are numbered balloons on the iso view, both parts named.
    assert [(c['number'], c['name'], c['view']) for c in facts['callouts']] == [
        (1, 'c_body', 'iso'), (2, 'c_pin', 'iso')]
    # On the dark floor, with ink in every view's cell.
    pixels = _rgb(data)
    width = studio.WIDTH
    paper = tuple(studio.PAPER)
    assert tuple(pixels[3 * (width * 2 + 2):3 * (width * 2 + 2) + 3]) == paper
    for view in facts['views']:
        x, y, w, h = facts['view_spans'][view]['cell']
        inked = sum(1 for j in range(y + 40, y + h - 40, 3) for i in range(x + 40, x + w - 40, 3)
                    if tuple(pixels[3 * (j * width + i):3 * (j * width + i) + 3]) != paper)
        assert inked > 100, view


def test_declared_measurements_are_drawn_once_where_they_read(tmp_path):
    reply = _plate_reply(tmp_path, [('bore', BORE), ('height', HEIGHT)])
    _data, facts = studio.blueprint_report(reply, None, None, {'name': 'plate', 'views': ['front', 'top']})
    declared = [d for d in facts['dimensions'] if d['source'] == 'declared']
    # Both read in front: the height is vertical there, and the bore's
    # diameter lies in the paper's plane. Each is drawn once.
    assert sorted((d['output'], d['view'], d['mm']) for d in declared) == [
        ('bore', 'front', 6.0), ('height', 'front', 10.0)]
    assert facts['measurements'] == {'declared': 2, 'drawn': 2, 'listed_only': 0, 'why_listed': ''}
    # A height seen end-on in the top view is not drawn there.
    _data, facts = studio.blueprint_report(reply, None, None, {'name': 'plate', 'views': ['top']})
    assert [d['output'] for d in facts['dimensions'] if d['source'] == 'declared'] == ['bore']
    assert facts['measurements']['listed_only'] == 1
    assert facts['measurements']['why_listed'] == 'no orthographic view shows it legibly'
    # A single part draws no balloons: there is nothing to tell apart.
    assert facts['callouts'] == []


def test_a_placed_design_lists_its_measurements_instead_of_drawing_them(tmp_path):
    reply = _reply(tmp_path)
    reply['display']['height'] = {'artifact_kind': None, 'artifact_path': None, 'placement': None,
                                  'tessellation': None, 'measurement': HEIGHT}
    _data, facts = studio.blueprint_report(reply, FIT, None, {'name': 'pin', 'callouts': ['c_pin']})
    assert not [d for d in facts['dimensions'] if d['source'] == 'declared']
    assert facts['measurements']['drawn'] == 0 and facts['measurements']['listed_only'] == 1
    assert 'part frame' in facts['measurements']['why_listed']
    assert [c['name'] for c in facts['callouts']] == ['c_pin']
    with pytest.raises(studio.StudioError, match='unknown callout c_floor'):
        studio.blueprint_report(reply, FIT, None, {'name': 'pin', 'callouts': ['c_floor']})


def _stored(entries):
    return {'ok': True, 'name': entries[-1]['file'], 'bytes': entries[-1]['bytes'],
            'sha256': entries[-1]['sha256'], 'revision': entries[-1]['revision'], 'blueprints': entries}


def test_bridge_draws_stores_and_revises_a_sheet_by_name(tmp_path):
    entries, puts = [], []

    def put(args):
        data = open(args['source_path'], 'rb').read()
        puts.append((args, data))
        version = 1 + sum(1 for e in entries if e['name'] == args['name'])
        entries.append({'ordinal': len(entries) + 1, 'name': args['name'], 'version': version,
                        'revision': 'a' * 64, 'digest': 'd' * 64, 'file': f'{len(entries) + 1:04d}-sheet.png',
                        'bytes': len(data), 'sha256': 's' * 64, 'created_at': '', 'label': args['label'],
                        'outputs': [], 'meta': args['meta']})
        return _stored(entries)

    def inspect(args):
        if args.get('scope') == 'blueprint':
            named = [e for e in entries if e['name'] == args.get('target')]
            if not named:
                return {'ok': False, 'error': 'No stored blueprint matches', 'failure_code': 'NOT_FOUND'}
            return inspect_reply(args, named[-1])
        return inspect_reply(args, {})

    client = FakeCadexd(replies={'put_blueprint': put})
    original = client.request

    def request(op, args=None, **kwargs):
        if op == 'inspect' and (args or {}).get('scope') == 'blueprint':
            client.calls.append((op, dict(args or {})))
            return inspect(dict(args or {}))
        return original(op, args, **kwargs)

    client.request = request
    with Bridge(client, project_root=tmp_path / 'orun2-pin') as bridge:
        bridge.state.last_accepted = _reply(tmp_path)
        bridge.state.last_fit = FIT
        result = bridge.call('draw_blueprint', {'name': 'pin sheet', 'notes': 'first issue',
                                                'views': ['iso', 'front']})
        assert result['is_error'] is False, result
        text, image = result['content']
        facts = json.loads(text['text'])
        assert facts['stored'] == 'blueprints/0001-sheet.png' and facts['version'] == 1
        assert facts['recipe'] == {'name': 'pin sheet', 'views': ['iso', 'front'], 'callouts': True,
                                   'dimensions': True, 'notes': 'first issue'}
        args, data = puts[-1]
        assert args['name'] == args['label'] == 'pin sheet' and args['meta']['schema'] == studio.BLUEPRINT_RECIPE_SCHEMA
        assert base64.b64decode(image['data']) == data and _size(data) == (studio.WIDTH, studio.HEIGHT)
        # Drawn again by name: the next version, and the keys left out come from the stored recipe.
        result = bridge.call('draw_blueprint', {'name': 'pin sheet', 'dimensions': False})
        facts = json.loads(result['content'][0]['text'])
        assert facts['version'] == 2 and facts['recipe']['views'] == ['iso', 'front']
        assert facts['recipe']['notes'] == 'first issue' and facts['recipe']['dimensions'] is False
        assert facts['dimensions'] == []
        assert [c.op for c in bridge.state.calls[-2:]] == ['draw_blueprint'] * 2
        # Refusals reach the model and store nothing.
        for bad in ({}, {'name': 'x', 'theme': 'blue'}, {'name': 'x', 'views': ['side']},
                    {'name': 'x', 'callouts': ['c_nothing']}):
            refused = bridge.call('draw_blueprint', bad)
            assert refused['is_error'] is True, bad
        assert len(puts) == 2


def test_the_dashboard_lists_stored_sheets_newest_first_and_serves_only_those(tmp_path, monkeypatch):
    import cadex_cli.review_server as review_server
    root = tmp_path / 'p'
    (root / 'blueprints').mkdir(parents=True)
    (root / 'blueprints' / '0001-plate.png').write_bytes(b'\x89PNG\r\n\x1a\nold')
    (root / 'blueprints' / '0002-plate.png').write_bytes(b'\x89PNG\r\n\x1a\nnew')
    (root / 'blueprints' / 'stray.png').write_bytes(b'\x89PNG\r\n\x1a\n')
    entries = [{'file': '0001-plate.png', 'name': 'plate', 'version': 1, 'revision': 'a' * 64},
               {'file': '0002-plate.png', 'name': 'plate', 'version': 2, 'revision': 'b' * 64},
               {'file': '../escape.png', 'name': 'x', 'version': 1, 'revision': 'b' * 64}]
    (root / 'blueprints' / 'blueprints.json').write_text(json.dumps({'schema': 'cadex-blueprint-v1',
                                                                      'entries': entries}))
    monkeypatch.setattr(review_server, 'read_accepted_identity',
                        lambda _root: {'available': True, 'revision': 'b' * 64})
    listing = blueprint_listing(root)
    assert [(s['file'], s['version'], s['relation']) for s in listing['sheets']] == [
        ('0002-plate.png', 2, 'current'), ('0001-plate.png', 1, 'earlier')]
    project = review_server.ReviewProject(root)
    assert project.blueprint_file('0002-plate.png') == root / 'blueprints' / '0002-plate.png'
    assert project.blueprint_file('stray.png') is None and project.blueprint_file('../escape.png') is None
    assert blueprint_listing(tmp_path / 'empty')['available'] is False


# -- against a real engine -----------------------------------------------

BORED = """
plate  = part.box(60, 40, 10)
bored  = part.cut(plate, part.cylinder(3, 20))
height = part.measurement(bored, kind="extent", axis="z", label="overall height")
bore   = part.measurement(bored, kind="diameter", at={"geometry_type": "Cylinder", "radius": 3.0})
result = {"bored": bored, "height": height, "bore": bore}
"""


@pytest.fixture
def bored_app(engine, tmp_path, capsys):
    projects = tmp_path / "projects"
    source = tmp_path / "bored.py"
    source.write_text(BORED, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(projects / "orun2-bored"), "--json"]) == EXIT_OK
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield projects / "orun2-bored", server
    finally:
        server.shutdown()
        server.server_close()


def _draw(engine, root, arguments):
    with CadexdClient(engine) as client:
        opened = open_project(client, root)
        revision = str((opened.get("model_state") or {}).get("next_write_expected_revision") or "")
        bridge = Bridge(client, project_root=root, initial_revision=revision)
        result = bridge.call("draw_blueprint", arguments)
    assert result["is_error"] is False, result
    return json.loads(result["content"][0]["text"]), base64.b64decode(result["content"][1]["data"])


@needs_browser
def test_browser_shows_a_drawn_and_revised_sheet_from_a_real_engine(engine, bored_app, browser) -> None:
    root, server = bored_app
    facts, data = _draw(engine, root, {"name": "bored plate", "notes": "A quarter bore at the corner."})
    assert facts["version"] == 1 and facts["stored"].startswith("blueprints/0001-bored-plate")
    overall = {(d["view"], d["axis"]): d["mm"] for d in facts["dimensions"] if d["source"] == "overall"}
    assert overall[("front", "X")] == pytest.approx(60.0, abs=0.01)
    assert overall[("front", "Z")] == pytest.approx(10.0, abs=0.01)
    assert overall[("top", "Y")] == pytest.approx(40.0, abs=0.01)
    # The engine's own numbers, drawn: the extent and the bore's diameter.
    declared = {d["output"]: d for d in facts["dimensions"] if d["source"] == "declared"}
    assert declared["height"]["mm"] == pytest.approx(10.0) and declared["bore"]["mm"] == pytest.approx(6.0)
    assert facts["measurements"]["declared"] == 2 and facts["measurements"]["drawn"] == 2
    assert (root / facts["stored"]).read_bytes() == data
    # Versioned with the project, and readable through the engine's own inspect.
    revised, _ = _draw(engine, root, {"name": "bored plate", "views": ["front", "top"]})
    assert revised["version"] == 2 and revised["recipe"]["notes"] == "A quarter bore at the corner."
    index = json.loads((root / "blueprints" / "blueprints.json").read_text())
    assert [(e["name"], e["version"]) for e in index["entries"]] == [("bored plate", 1), ("bored plate", 2)]
    assert index["entries"][-1]["meta"]["views"] == ["front", "top"]

    page = _open(browser, server.url + "p/orun2-bored/")
    page.wait_for("document.querySelectorAll('#drawing-list li[data-file]').length === 2", timeout=30)
    files = page.evaluate("Array.from(document.querySelectorAll('#drawing-list li[data-file]'))"
                          ".map(li => [li.dataset.file, li.dataset.relation, li.textContent])")
    assert [f[0] for f in files] == [index["entries"][1]["file"], index["entries"][0]["file"]]
    assert all(f[1] == "current" for f in files) and "bored plate v2" in files[0][2]
    page.wait_for("document.getElementById('drawing-latest').naturalWidth > 0", timeout=30)
    assert page.evaluate("document.getElementById('drawing-latest').naturalWidth") == studio.WIDTH
    sheet = page.download('#drawing-list li[data-file] a[download]', timeout=30)
    assert sheet.path.read_bytes() == (root / "blueprints" / index["entries"][1]["file"]).read_bytes()
    assert _get(server.url + "p/orun2-bored/blueprint/blueprints.json")[0] == 404
    assert _json(server.url + "p/orun2-bored/api/project")["drawings"]["sheets"][0]["version"] == 2
