# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Golden per-op response shapes (Phase 9, ADR-025).

``CadexdProtocol.OP_ARG_SPECS`` pins *requests*. Nothing pinned *replies* —
and the Blender shell reads about fifty response keys, in another
repository, under another licence. A key that quietly changes name or
nesting fails at the user, not at a test.

These fixtures were recorded from a live cadexd run and reduced to shape:
every leaf is its JSON type name, so the files carry no digests, no
temporary paths and no machine state, and a diff on them means the contract
moved. Both sides of the protocol assert against the same shapes, which is
what makes "replace either side independently" true rather than assumed.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

MODULE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = MODULE_DIR / "response_schemas"
DOCS_DIR = MODULE_DIR.parents[3] / "docs"

#: Leaf type name -> a representative value of that JSON type.
_SAMPLES: dict[str, object] = {
    "str": "x",
    "int": 1,
    "float": 1.0,
    "bool": True,
    "null": None,
}


def _materialize(shape: object) -> object:
    """Turn a recorded shape document back into a concrete frame."""

    if isinstance(shape, dict):
        return {key: _materialize(value) for key, value in shape.items()}
    if isinstance(shape, list):
        return [_materialize(item) for item in shape]
    if isinstance(shape, str) and shape in _SAMPLES:
        return _SAMPLES[shape]
    raise AssertionError(f"Fixture leaf {shape!r} is not a JSON type name.")


def _fixtures() -> dict[str, dict]:
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(FIXTURE_DIR.glob("*.json"))
    }


def _frame_from(name: str) -> dict:
    """Materialize a fixture into a frame the validator can dispatch on.

    A shape document cannot carry the two *values* that select which spec
    applies — ``ok``, and for a failure whether ``failure_code`` is a
    server-level code — so the fixture's name carries them instead:
    ``<op>.json`` is a success, ``<op>.failure`` a tool-level failure,
    ``<op>.server_failure`` a server-level one. Any further suffix
    (``open_project.restored``) is just a second success variant.
    """

    frame = _materialize(_fixtures()[name])
    assert isinstance(frame, dict)
    frame["id"] = "fixture"
    variant = name.partition(".")[2]
    frame["ok"] = not variant.endswith("failure")
    if variant == "server_failure":
        from CadexdProtocol import CADEXD_PROTOCOL_ERROR

        frame["failure_code"] = CADEXD_PROTOCOL_ERROR
    return frame


def _ops() -> set[str]:
    from CadexdProtocol import OP_ARG_SPECS

    return set(OP_ARG_SPECS)


def test_every_op_has_a_response_spec_and_a_golden_fixture() -> None:
    """A served op with no pinned reply is an unpinned contract."""

    from CadexdProtocol import OP_RESPONSE_SPECS

    ops = _ops()
    assert set(OP_RESPONSE_SPECS) == ops, (
        "CadexdProtocol.OP_RESPONSE_SPECS and OP_ARG_SPECS disagree.\n"
        f"  request-only: {sorted(ops - set(OP_RESPONSE_SPECS))}\n"
        f"  response-only: {sorted(set(OP_RESPONSE_SPECS) - ops)}"
    )
    recorded = {name.split(".", 1)[0] for name in _fixtures()}
    assert recorded == ops, (
        "Every op needs a recorded response shape.\n"
        f"  missing a fixture: {sorted(ops - recorded)}\n"
        f"  fixture for no op: {sorted(recorded - ops)}"
    )


@pytest.mark.parametrize("name", sorted(_fixtures()))
def test_golden_fixture_matches_the_pinned_response_spec(name: str) -> None:
    """The recorded shape and the declared spec must not drift apart.

    They are two statements of the same contract written for two audiences:
    the spec is what the engine enforces, the fixture is what the shell was
    written against.
    """

    from CadexdProtocol import validate_response

    problems = validate_response(name.split(".", 1)[0], _frame_from(name))
    assert not problems, (
        f"Recorded response shape {name}.json no longer matches "
        f"OP_RESPONSE_SPECS:\n  " + "\n  ".join(problems)
    )


@pytest.mark.parametrize("name", sorted(_fixtures()))
def test_golden_fixtures_are_shape_only(name: str) -> None:
    """No digests, paths or machine state may leak into a committed fixture."""

    text = (FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8")
    leaves = set(re.findall(r':\s*"([^"]*)"', text))
    unexpected = sorted(leaves - set(_SAMPLES))
    assert not unexpected, (
        f"{name}.json carries recorded values, not shapes: {unexpected}. "
        "Fixtures pin structure; values are the run's business."
    )


def test_failure_envelope_is_one_shape_for_every_op() -> None:
    """The agent reads ``failure_code``/``observed``/``retry`` and acts.

    A per-op failure shape would make that reading op-specific, so the
    envelope is deliberately uniform and pinned once.
    """

    from CadexdProtocol import (
        FAILURE_RESPONSE_SPEC,
        SERVER_FAILURE_SPEC,
        validate_response,
    )

    required, _optional = FAILURE_RESPONSE_SPEC
    assert {"failure_code", "observed", "retry", "error"} <= required

    names = [n for n in _fixtures() if n.partition(".")[2].endswith("failure")]
    assert names, "At least one recorded failure envelope is required."
    for name in names:
        problems = validate_response(name.split(".", 1)[0], _frame_from(name))
        assert not problems, f"{name}.json: " + "; ".join(problems)

    # The server envelope is strictly smaller, and must not be accepted where
    # the agent expects a pipeline failure it can act on.
    server_required, _ = SERVER_FAILURE_SPEC
    assert server_required < required, (
        "A server-level failure must not satisfy the tool-level envelope; "
        "otherwise a bare protocol error reads as an actionable one."
    )


def test_every_key_the_server_sends_on_a_failure_is_declared() -> None:
    """Read cadexd's own ``failure(...)`` call sites and check them.

    The four keys ADR-055 fixed were undeclared for as long as they had
    existed, and the reason is structural: nothing compares what the *sender*
    passes against what the spec names, so an undeclared key is only ever
    caught by a test that happens to drive that exact refusal. Two such tests
    now exist in ``test_cadexd_lifecycle``; this one needs no live server and
    covers the sites no test drives, including the ``exception_type`` on a
    handler that was never made to throw.
    """

    import ast

    from CadexdProtocol import SERVER_FAILURE_SPEC

    required, optional = SERVER_FAILURE_SPEC
    declared = required | optional
    source = (MODULE_DIR.parent / "cadexd.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    sites = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "failure"
    ]
    assert sites, "cadexd.py builds server failures with failure(); it stopped."

    undeclared = sorted(
        {
            f"{keyword.arg} (cadexd.py:{node.lineno})"
            for node in sites
            for keyword in node.keywords
            if keyword.arg is not None and keyword.arg not in declared
        }
    )
    assert not undeclared, (
        "cadexd sends server-failure keys SERVER_FAILURE_SPEC does not "
        f"declare: {undeclared}. The spec is the contract — either declare "
        "the key or stop sending it."
    )


def test_a_renamed_or_dropped_response_key_is_caught() -> None:
    """The point of the fixtures, asserted directly."""

    from CadexdProtocol import validate_response

    frame = _frame_from("resolve_pin")
    assert not validate_response("resolve_pin", frame)

    dropped = {k: v for k, v in frame.items() if k != "subelements"}
    assert any("subelements" in p for p in validate_response("resolve_pin", dropped))

    renamed = dict(dropped, sub_elements=frame["subelements"])
    problems = validate_response("resolve_pin", renamed)
    assert any("subelements" in p for p in problems)
    assert any("sub_elements" in p for p in problems)


def test_nested_shell_facing_shapes_are_pinned() -> None:
    """``display`` is the shell's whole rendering input; pin it explicitly."""

    from CadexdProtocol import NESTED_RESPONSE_SPECS, validate_response

    assert "display.*" in NESTED_RESPONSE_SPECS
    assert "display.*.tessellation.counts" in NESTED_RESPONSE_SPECS

    frame = _frame_from("write_script")
    assert not validate_response("write_script", frame)

    # A renamed count key must be caught inside the nested block.
    frame["display"]["plate"]["tessellation"]["counts"]["tris"] = (
        frame["display"]["plate"]["tessellation"]["counts"].pop("triangles")
    )
    problems = validate_response("write_script", frame)
    assert any("triangles" in p for p in problems), problems


def _documented_response_keys() -> set[str]:
    """Response keys named in ``docs/INTEGRATION.md``'s response table."""

    doc = (DOCS_DIR / "INTEGRATION.md").read_text(encoding="utf-8")
    section = doc.partition("### Response shapes")[2].partition("\n## ")[0]
    keys: set[str] = set()
    for line in section.splitlines():
        if line.startswith("| `"):
            # Digits are part of a key name (``sha256``), not a separator.
            keys.update(re.findall(r"`([a-z0-9_]+)`", line.split("|")[2]))
    return keys


def test_the_protocol_document_matches_the_response_table() -> None:
    """docs/INTEGRATION.md is the contract the other repository reads.

    The request table is already enforced (``test_engine_purity_guardrails``);
    without this, the half of the contract the shell actually consumes stays
    prose.
    """

    from CadexdProtocol import OP_RESPONSE_SPECS

    implemented: set[str] = set()
    for required, optional in OP_RESPONSE_SPECS.values():
        implemented |= required | optional

    documented = _documented_response_keys()
    assert documented == implemented, (
        "docs/INTEGRATION.md's response table and OP_RESPONSE_SPECS disagree.\n"
        f"  documented but not served: {sorted(documented - implemented)}\n"
        f"  served but not documented: {sorted(implemented - documented)}"
    )
