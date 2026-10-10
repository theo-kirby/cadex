---
node_id: a36a0b47-6219-559a-ab50-32d203ca847b
slug: modest-canyon-9174
title: Owner answers to the docs audit; stale strings fixed
created_at: '2026-10-10T12:38:07+00:00'
parents:
- solemn-ivy-5988
summary: ''
---
## What

Carried out the owner's answers to the docs audit (`docs/DOCS-AUDIT.md` §4), and fixed the small code bugs it listed in §3 (ADR-629).

## Why

The owner decided:

- The unused protocol ops stay.
- The `~/arch/woof.cadex` citation goes; that project is gone.
- The knee-actuator-inside-the-thigh item is dropped: "we shouldnt have hard rules like that. we need to be more open and flexible."

## Method

- **Guidance:** removed ACTUATORS INSIDE THE LIMB from the `printed-legged-robot` style, from its test pin and from the DESIGN-LANGUAGE lesson table.
- **ORGANIC.md:** no longer cites the wolf project as live.
- **Code fixes:**
  - `test_panels` now skips when there is no engine build.
  - The project-docs scaffold no longer claims walk continuation is not automated.
  - Removed stale shell-era help text and docstrings from `__main__.py`, `session.py`, `analysis/search.py` and `training/cadex_train.py`.
  - Corrected the shared `--project` help.
  - Fixed the `covers nothing` wording to say what the worker actually tests: overlap with the shell's box grown by 5 mm.
  - Corrected the creature style header comment.
- **Docs:** added ADR-629, and marked items 2, 7 and 8 RESOLVED in DOCS-AUDIT.

## Result

- `pixi run test-engine`: 2778 passed, 61 skipped. An earlier run under load had one transient failure, and it did not recur.
- `cli/tests`: 1259 passed, 1 skipped.

The payload version mismatch (§3 item 1), the inherited CMake message (item 2) and CI (item 12) remain open.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 091e962aafc8add2df0b17241433438835d0e222

## State Impact

- target: pale-arrow-4660 — the printed-legged-robot style no longer places the knee actuator inside the thigh; actuator placement is the design's own call (ADR-629)
