# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One output definition may be a full machine's assembly (ADR-670)."""

from __future__ import annotations

import pytest

import cadex_domain_worker as worker


def _definition(size: int) -> dict:
    return {"domain": "assembly", "operation": "assembly", "output_type": "assembly",
            "arguments": [], "properties": {"note": "x" * size}}


def test_a_two_megabyte_definition_passes_and_the_cap_is_four_mebibytes():
    assert worker.MAX_DEFINITION_BYTES == 4 * 1024 * 1024
    assert worker._payload(_definition(2_000_000), serialized=True)["operation"] == "assembly"


def test_a_definition_past_the_cap_is_refused_with_its_size_and_a_way_out():
    with pytest.raises(ValueError) as refused:
        worker._payload(_definition(worker.MAX_DEFINITION_BYTES + 1), serialized=True)
    message = str(refused.value)
    assert "past the 4194304-byte cap" in message and "per joint" in message
