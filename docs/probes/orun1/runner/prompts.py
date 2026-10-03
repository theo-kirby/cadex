# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""D4's plain prompts, frozen before any D4 generation (orun1 charter, D4).

One prompt per type. Each names the type, its joint count and "design
only", and says nothing about style: the style must come from the
product's guidance. ``docs/probes/orun1/README.md`` quotes them verbatim
and ``test_prompts.py`` pins both copies to ``FROZEN_SHA256``. Changing a
word is a change to a frozen artefact and earns its own record.

Each key is a sweep category (``ratings.json`` → ``designs[].category``):
the design a prompt produces is judged against that category's sweep
designs the owner rated Like or Love (``versus.py``).
"""

from __future__ import annotations

import hashlib

PROMPTS = {
    'quadruped': 'Design a quadruped walking robot with 12 joints, three per leg. Design only: '
                 'no training task, policy or rollout.',
    'hexapod': 'Design a hexapod walking robot with 18 joints, three per leg. Design only: '
               'no training task, policy or rollout.',
    'biped': 'Design a biped walking robot with 6 joints, three per leg (hip, knee, ankle). Design only: '
             'no training task, policy or rollout.',
    'arm5': 'Design a desktop robot arm with 5 joints and a gripper. Design only: '
            'no training task, policy or rollout.',
    'arm3': 'Design a desktop robot arm with 3 joints and a simple end effector. Design only: '
            'no training task, policy or rollout.',
    'balancer': 'Design a two-wheeled self-balancing robot with 2 joints, one driven wheel each side. Design only: '
                'no training task, policy or rollout.',
    'wildcard': 'Design a snake robot with 8 joints. Design only: '
                'no training task, policy or rollout.',
}

#: The product agent's settings for every D4 turn: the sweep's (README, "The sweep").
MODEL = 'claude-opus-5-5'
EFFORT = 'medium'

FROZEN_SHA256 = 'f69ab5c825da46bfb2cca46a35fe695a3fab4255bf10d723ce9ad70206360884'


def prompts_sha256() -> str:
    return hashlib.sha256('\n'.join(f'{k}\t{PROMPTS[k]}' for k in sorted(PROMPTS)).encode('utf-8')).hexdigest()
