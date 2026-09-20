# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The MJCF-agreement probe, against answers stated before it is run.

ADR-393's defect wrote a welded body's parent-relative transform as its exact
inverse. Nothing static could see it: the tool that can is this composition of
the body tree down to world, and a measurement tool that is itself unchecked
is not evidence. So the fixtures here are hand-written MJCF whose world poses
are arithmetic anyone can redo: a child 20 mm along its parent's +X, turned
90 degrees about Z, and the same child written the inverted way.
"""
import importlib.util
import json
import math
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / 'docs/probes/ot7/runner/mjcf_agreement.py'
spec = importlib.util.spec_from_file_location('ot7_mjcf_agreement', PATH)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

#: A quarter turn as MJCF writes it: ``(w, x, y, z)``.
QUARTER_TURN_Z = '0.7071067811865476 0 0 0.7071067811865475'
QUARTER_TURN_Z_REVERSED = '0.7071067811865476 0 0 -0.7071067811865475'

#: The host sits 100 mm along world +X, unrotated; the part it carries sits
#: 20 mm further along the host's own +X and is turned a quarter turn about Z.
#: So the part's world pose is 120 mm out, turned a quarter turn -- which is
#: what the solved placements below say, independently of any MJCF.
HOST_WORLD = [1, 0, 0, 100.0, 0, 1, 0, 0.0, 0, 0, 1, 0.0, 0, 0, 0, 1]
PART_WORLD = [0, -1, 0, 120.0, 1, 0, 0, 0.0, 0, 0, 1, 0.0, 0, 0, 0, 1]

#: Inverting ``(Rz(90), (20, 0, 0))`` gives ``(Rz(-90), (0, 20, 0))`` -- the
#: shape ADR-393's swapped connector frame produced. Composed onto the host it
#: puts the part at ``(100, 20, 0)`` instead of ``(120, 0, 0)``: 28.284 mm out
#: and turned the wrong way by half a turn.
INVERTED_POSITION_ERROR_MM = math.sqrt(20.0 ** 2 + 20.0 ** 2)


def model(tmp_path, part_pos, part_quat):
    text = (
        '<mujoco model="fixture"><worldbody>'
        '<body name="host" pos="0.1 0 0">'
        f'<body name="part" pos="{part_pos}" quat="{part_quat}"/>'
        '</body></worldbody></mujoco>'
    )
    path = tmp_path / 'fixture-model.xml'
    path.write_text(text)
    return path


def result(tmp_path, placements):
    path = tmp_path / 'result.json'
    path.write_text(json.dumps({'validations': {'assembly': {
        'component_placements': {
            name: {'matrix': matrix} for name, matrix in placements.items()}}}}))
    return path


def test_a_body_tree_that_matches_its_solve_agrees_exactly(tmp_path):
    """The composition is the arithmetic in this file's header, to the bit."""
    report = probe.agreement(
        model(tmp_path, '0.02 0 0', QUARTER_TURN_Z),
        result(tmp_path, {'host': HOST_WORLD, 'part': PART_WORLD}))
    summary = probe.verdict(report)
    assert summary['agrees'] is True
    assert (summary['bodies'], summary['measured'], summary['disagreeing']) == (2, 2, 0)
    assert summary['worst']['position_error_mm'] == pytest.approx(0, abs=1e-9)
    for row in report['rows']:
        assert row['orientation_error_degrees'] == pytest.approx(0, abs=1e-9)


def test_an_inverted_parent_relative_frame_is_caught_with_its_number(tmp_path):
    """ADR-393's defect shape, on placements the solve did not move."""
    report = probe.agreement(
        model(tmp_path, '0 0.02 0', QUARTER_TURN_Z_REVERSED),
        result(tmp_path, {'host': HOST_WORLD, 'part': PART_WORLD}))
    summary = probe.verdict(report)
    assert summary['agrees'] is False
    assert summary['disagreeing_bodies'] == ['part']
    assert summary['worst']['body'] == 'part'
    assert summary['worst']['position_error_mm'] == pytest.approx(
        INVERTED_POSITION_ERROR_MM, abs=1e-9)
    assert summary['worst']['orientation_error_degrees'] == pytest.approx(180.0, abs=1e-6)
    host = next(row for row in report['rows'] if row['body'] == 'host')
    assert host['position_error_mm'] == pytest.approx(0, abs=1e-9)


def test_a_body_with_no_solved_placement_is_never_a_pass(tmp_path):
    """Missing evidence is missing evidence, not agreement."""
    report = probe.agreement(
        model(tmp_path, '0.02 0 0', QUARTER_TURN_Z),
        result(tmp_path, {'host': HOST_WORLD}))
    summary = probe.verdict(report)
    assert summary['agrees'] is False
    assert summary['disagreeing'] == 0
    assert summary['missing_placements'] == ['part']
    assert [row['status'] for row in report['rows'] if row['body'] == 'part'] == ['no_placement']


def test_the_tolerance_is_what_decides_a_borderline_body(tmp_path):
    """A tenth of a micron out passes the default and fails a tighter one."""
    nudged = list(PART_WORLD)
    nudged[3] += 1.0e-7
    paths = (model(tmp_path, '0.02 0 0', QUARTER_TURN_Z),
             result(tmp_path, {'host': HOST_WORLD, 'part': nudged}))
    assert probe.verdict(probe.agreement(*paths))['agrees'] is True
    assert probe.verdict(probe.agreement(*paths), tolerance_mm=1.0e-9)['agrees'] is False
