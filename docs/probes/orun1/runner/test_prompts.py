# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""D4's frozen prompts and its versus bookkeeping, pinned without a model call.

    pixi run python -m pytest docs/probes/orun1/runner/test_prompts.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import metrics  # noqa: E402
import prompts  # noqa: E402
import versus  # noqa: E402

README = Path(__file__).resolve().parents[1] / 'README.md'
STYLE = ('shell', 'exposed', 'panel', 'mechanism', 'minimal', 'creature', 'face', 'colour', 'color',
         'clean', 'beautiful', 'look', 'aesthetic', 'style', 'engineered', 'friendly', 'catalog')


def test_the_prompts_are_byte_for_byte_what_was_frozen():
    assert prompts.prompts_sha256() == prompts.FROZEN_SHA256
    assert (prompts.MODEL, prompts.EFFORT) == ('claude-opus-5-5', 'medium')


def test_the_readme_quotes_every_frozen_prompt_and_its_hash():
    text = README.read_text(encoding='utf-8')
    assert prompts.FROZEN_SHA256 in text
    for name, prompt in prompts.PROMPTS.items():
        assert f'| {name} | {prompt} |' in text


def test_one_prompt_per_sweep_type_each_naming_its_joints_and_design_only_and_no_style():
    ratings = json.loads(metrics.RATINGS.read_text(encoding='utf-8'))
    assert set(prompts.PROMPTS) == {d['category'] for d in ratings['designs']}
    for prompt in prompts.PROMPTS.values():
        assert re.search(r'\b\d+ joints\b', prompt)
        assert 'Design only' in prompt
        assert not [w for w in STYLE if w in prompt.lower()]


def test_every_type_has_like_or_love_opponents_and_d1_judged_their_heroes():
    recorded = versus.recorded_hashes()
    for category in prompts.PROMPTS:
        rivals = versus.opponents(category)
        assert rivals and set(rivals) <= set(recorded)
    assert versus.opponents('balancer') == {
        'balancer-c-exposed-mechanism': 'dev', 'balancer-d-product-shell': 'heldout',
        'balancer-e-hard-surface': 'heldout', 'balancer-f-creature': 'heldout', 'balancer-h-free': 'dev'}
