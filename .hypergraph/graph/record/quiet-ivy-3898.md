---
node_id: 3c1cf9f1-45d0-51e7-8cb6-39f1244f45f7
slug: quiet-ivy-3898
title: 'orun2 D3: a run''s page shows its records and the artifacts they name — /r/<run>/linked/ (ADR-518)'
created_at: '2026-10-04T00:34:07+00:00'
parents:
- curious-flint-4836
summary: ''
---
## What

D3's open gap — each run shows "the artifacts its records point to
(renders, reports, probe pages)" — closed on the run page (ADR-518, commit
`b3c2616c`).

- `cli/cadex_cli/review_server.py` (`OuroborosRuns`): `records()` reads the
  checkout's `.hypergraph/graph/record/*.md` whose `## Repo` names the
  run's branch (frontmatter parsed by hand, cached on the directory's
  mtime), places each in the first iteration whose last step is not older
  than it (`null` = the current one), and lists the `docs/...` paths its
  text names — the file, or a named directory's own files — under ADR-515's
  suffix, segment and no-symlink rules, 24 per record. `api/run` carries
  `records`; each iteration gains `records` (slugs). `linked_file()` serves
  `/r/<run>/linked/<path>` only for a named file, a named directory's
  child, or a file in a `docs/probes/<dir>/` a record names a path in (so a
  linked README's images load), with `sandbox` and `nosniff`.
- `run.html` / `run.js`: a **Records** card under Probes — iteration badge,
  title, slug and time, images as a gallery, other files linked, a markdown
  file opened in place in `#linked-doc` with `markdown.js`; each iteration
  row's commit cell links its records. `review.css`: the markdown styles
  now apply to any `article.markdown`.
- Docs: ADR-518; `docs/DASHBOARD.md` (the Records card and route).

## Why

The critic's message for iteration 36: first write iteration 35's missing
record (done: `curious-flint-4836`, this node's parent, with both suites'
evidence), then resume D3 (`swift-nest-0229`) at its highest open gap —
run pages showing the artifacts their records point to, with a browser test
replacing `~/orun1-review/build.py`. ADR-515 had said plainly that
record-linked artifacts outside `docs/probes/<run>/` were unreachable.
build.py's page had, beyond ADR-515's README: each D4 trial's hero, the
design language the run rewrote, the live status and critic log (already
ADR-513). orun1's records name every committed trial hero, the design
language and the README.

The critic also said "after that, reconcile". A work iteration may not
reconcile; the tail is now three records (`sweet-arrow-0695`,
`curious-flint-4836`, this), which meets the charter's reconcile trigger,
so the next iteration should be the reconcile.

## Method

- Read build.py (read-only, outside the repo) for what it showed and where
  each part came from; surveyed what paths the 848 records name; checked
  orun1's 22 records against its `iterations.jsonl` (each maps to a
  plausible iteration: e.g. `deep-cove-1130` → #28, `little-shade-0096` →
  #33).
- Mapping by commit was rejected: a record's `commit:` is the work commit
  and the loop's commit is the one after.
- Eyeballed the real orun1 run page in headless Chromium (screenshot not
  committed): heroes on the dark floor, links, badges.

## Result

- **True now:** `/r/<run>/` lists the run's records under the iteration
  each landed in, with the renders, reports and probe pages they name, from
  the repo alone. On the real checkout orun1 shows 22 records and 92 linked
  files; first `api/run` ~76 ms, cached ~6 ms.
- **Tests:** `cli/tests/test_app.py`, three new:
  `test_a_runs_records_name_their_iteration_and_artifacts` (mapping incl.
  the current iteration, named file vs directory children vs deeper,
  trailing period, HTML/symlink/missing/non-`docs/` never listed, headers,
  allowed probe-dir siblings, 14 refused paths incl. encoded `..`, another
  run's records, a record without `## Repo`, live pickup, nothing written);
  `test_records_outside_a_checkout_are_refused`; and in headless Chromium
  `test_browser_shows_orun1s_records_and_what_they_point_to_from_the_repo`:
  orun1's committed records + `docs/probes/orun1`, `docs/probes/ot10`,
  `docs/DESIGN-LANGUAGE.md` in a checkout — every record under its own
  iteration, the t1-hexapod hero loaded via `linked/`, every committed d4
  trial hero shown, an iteration row linking `golden-bay-7992`,
  DESIGN-LANGUAGE.md opened in place with its title and sections, the orun1
  README opened with its nine-row ratings table, closed. `test_app.py`: 22
  passed.
- **Gates:** `pixi run test-engine`: 2594 passed, 56 skipped. `pixi run
  python -m pytest cli/tests` (GPU hidden, alongside the engine suite):
  1394 passed, 1 skipped (`CADEX_REVIEW_HOST`), 1 failed —
  `test_review_lifecycle.py::test_restarting_the_dashboard_keeps_the_review_and_leaves_training_alone`
  read `RUN sample` for `RUN second`; it passed alone with and without this
  change and with its whole file. It is a **load-dependent flake** (a live
  training producer races the default-run pick) in code this unit does not
  touch; named here so a later iteration can harden it. No engine,
  protocol or payload change, so no build and no packaged gate.
- **D3 status:** runs are listed beside projects (ADR-513) with
  iterations, verdicts, charter criteria (ADR-514), probe material
  (ADR-515) and now record-linked artifacts (ADR-518), and orun1's material
  renders from the repo alone. CLI agent turns as "runs" beside projects
  are the remaining D3 question for the critic.
- **Not covered:** paths outside `docs/` (project-relative renders such as
  `review/render/hero.png` live in `~/cadex-projects`, not the repo);
  build.py's per-trial win/loss table is linked as `summary.json`, not drawn.
- **Unreconciled tail:** three records — reconcile is due next.

Dispatch closed: 1 unit — a run's page shows its records and the renders, reports and probe pages they name (ADR-518), with iteration 35's missing record written first

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: b3c2616caede422671196d555ed1bced8d2768f6

## State Impact

- target: swift-nest-0229 — each run page now lists the run's hypergraph records under the iteration each landed in, with the docs/ renders, reports and probe pages they name served read-only under /r/<run>/linked/ (ADR-518); orun1's 22 records show every committed trial hero, DESIGN-LANGUAGE.md and the README from the repo alone, browser-tested, retiring ~/orun1-review/build.py
