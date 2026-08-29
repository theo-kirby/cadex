# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The shared-sub-expression memo's correctness properties (ADR-053).

The geometry half is proved by digest equality against a live engine (see
the ADR). What is testable here without FreeCAD is the part that would be a
*correctness* bug rather than a performance one: the key, and the reset.
"""

from __future__ import annotations

import cadex_part_worker as worker


def _payload(width: float) -> dict:
    return {
        "domain": "part",
        "operation": "box",
        "output_type": "solid",
        "arguments": [width, 20, 4],
        "properties": {},
    }


def test_the_key_is_content_not_identity() -> None:
    assert worker._memo_key(_payload(10)) == worker._memo_key(_payload(10))
    assert worker._memo_key(_payload(10)) != worker._memo_key(_payload(11))


def test_the_key_ignores_dict_ordering() -> None:
    """Two spellings of one definition are one cache entry."""

    first = {"domain": "part", "operation": "box", "arguments": [1, 2, 3]}
    second = {"arguments": [1, 2, 3], "operation": "box", "domain": "part"}
    assert worker._memo_key(first) == worker._memo_key(second)


def test_the_key_uses_the_repository_s_one_content_key_idiom() -> None:
    """Same construction as cadex_project_api.inline_source_token."""

    from cadex_project_api import inline_source_token

    payload = _payload(10)
    assert worker._memo_key(payload) == inline_source_token(payload)


def test_the_memo_resets() -> None:
    """The property a warm worker depends on.

    A memo leaked across requests answers with geometry built from the
    *previous* parameter values, under a digest that is self-consistent with
    it. That is why the reset lives in the request's ``finally`` and not at
    its entry -- an early return or a raised exception must not be able to
    skip it.
    """

    worker._SHAPE_MEMO["src-whatever"] = (object(), {})
    assert worker._SHAPE_MEMO
    worker.reset_part_shape_memo()
    assert not worker._SHAPE_MEMO


def test_the_reset_is_called_from_a_finally() -> None:
    """Pinned deliberately: at entry instead would be a correctness bug."""

    import inspect
    import cadex_project_worker

    source = inspect.getsource(cadex_project_worker._run)
    assert "reset_part_shape_memo()" in source
    finally_index = source.rindex("finally:")
    assert source.index("reset_part_shape_memo()", finally_index) > finally_index, (
        "reset_part_shape_memo must run in _run's finally, so a raising or "
        "early-returning request cannot leak shapes into the next one."
    )


def test_the_memo_is_capped() -> None:
    assert worker._SHAPE_MEMO_LIMIT > 0
