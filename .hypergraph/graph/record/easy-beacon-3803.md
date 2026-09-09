---
node_id: c799f401-5737-5c0f-856c-7d0e797853ba
slug: easy-beacon-3803
title: Generated review files stay local and policy exclusions follow Git precedence
created_at: '2026-09-08T20:18:22+00:00'
parents:
- square-light-7067
summary: ''
---
## What

Fresh project scaffolds now ignore generated project-root review/ output.
Documented explicit policy/run exclusions using ordinary Git precedence and
pinned retention with a disposable real-Git regression and lifecycle assertions.

## Why

Follows square-light-7067 and the overseer's artifact-retention priority,
advancing mission 1/2 and the charter's tested headless walk and headless-review
criteria. Assumption: preserve Git semantics and existing user configurations;
automatic untracking would discard a user's explicit index/history intent.
The reported quill force-add was not a force-add: commit_project uses add -A,
and the root !assets/*.cxpolicy negation beats .git/info/exclude. The run
exclusion worked; root review SVG/JSON had no applicable exclusion at all.

## Method

Read quill ignore configuration and acbcb6e commit contents without changing
that project. The regression initializes a disposable project with defaults,
reproduces the local-exclude/root-negation conflict, then applies the documented
root override. It inspects the committed tree, local output contents, historical
policy contents, default asset retention, docs/source, and explicitly staged
working content. It failed on the previous scaffold because review SVG/JSON
entered the tree; after adding /review/ it passed. CLI/scaffold docs explain
existing-repository migration by explicit user edits and forward untracking,
without changing existing configuration automatically. ADR-262 and ROADMAP
record the changed default. Real render, section and walk assertions now require
local output availability and absence from Git, retaining their geometry checks.

## Result

Validation: `pixi run python -m pytest cli/tests -q` passed all 241 tests
(no skips) in 227.05 s; output is local at
/tmp/cadex-iteration30-cli-final.log. The first full run had 234 passes and
seven expected failures asserting generated previews were tracked; after
updating those retention expectations the full rerun is green. Targeted new
regression: 1 passed / 24 deselected after its demonstrated pre-fix failure.
`git diff --check` passed. No engine/payload/shell code changed, so no build
or packaged gate was required.

No real project history was changed, no generated dump was committed, and no
new rehearsal or provider turn was dispatched. Existing root policy exclusions
must follow the default negation; local excludes cannot override it. Tracked or
explicitly staged outputs still enter commits under the documented add -A
contract. Quill's prior forward correction already has the root override and
/review/ rule. A new run/policy name requires its own exclusions before dispatch.
This repairs the missing fresh-project review exclusion and provides a tested
retention recipe; it does not silently migrate earlier project repositories.
The walk/review criteria already have working evidence; no new mechanism/mode
claim is made. Next is seed and exported-task objective identity in comparisons,
including legacy evidence handling and action-scaling caveats, before another
rehearsal. No parked criterion opened; reconcile remains a separate role.
Dispatch closed: 1 unit — keep generated review files local and pin project retention.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 74da4c85ebcfa53f2697da1f1075fd98abd601ee

## State Impact

- target: chilly-union-8972 — Fresh scaffolds ignore generated review files; real Git regression pins explicit root policy exclusions, local output retention, committed docs/source, default stored policies and preserved tracked/pre-staged content. Existing repositories retain configuration; quill failure was ignore precedence, not force-add.
- target: calm-peak-5247 — Walk retention recipe and scaffold explain root exclusions for run and policy outputs; full CLI suite passes with review artifacts local and project reports versioned by default. Seed/objective identity remains next.
