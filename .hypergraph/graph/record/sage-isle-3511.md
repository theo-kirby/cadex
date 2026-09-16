---
node_id: ac2399b9-ffe8-5936-9b78-8183bd3147d4
slug: sage-isle-3511
title: 'A scheduled reset is not proof the org-level refusal lifts: the F6/F7 gate is qualified'
created_at: '2026-09-16T16:53:41+00:00'
parents:
- crimson-nest-6583
summary: ''
---
## What

The closing report's gate subsection no longer says the provider refusal
*opens* at `2026-09-18T14:00:00Z`. That epoch is the rejected window's
`resets_at` — a scheduled window reset — while the binding condition in the
refusal receipt is `overage.disabled_reason: "org_level_disabled"`, an
organisation-level setting on this account that no window reset is evidence
about.

`docs/probes/ot7/REPORT.md` now carries, in commit `50a0305a`:

- the subsection retitled **The gate cannot open before this run's own stop**,
  opening with the statement that it bounds the refusal from below — when the
  block *cannot* have lifted, not when it will;
- the epoch relabelled as the gate's **earliest possible opening**, with the
  `org_level_disabled` field named as the binding condition, the plain sentence
  that a probe after that epoch may well be refused again, and the rule that
  only an unrefused probe is evidence the refusal lifted;
- the conclusion qualified: under the current limits and stop rules F6 and F7
  are **expected** to end unattempted with all eight slots unspent — still not
  exhaustion;
- the lede sentence and the "what finishing them takes" paragraph rewritten to
  match, the latter now keyed to an unrefused probe rather than to a clock.

This record's State Impact carries the same correction onto `narrow-dune-9454`
and `rapid-grove-9687`, whose impacts from `crimson-nest-6583` asserted that
the refusal "lifts at 2026-09-18T14:00:00Z". It does not; that is the earliest
it could.

No product code, no prompt, no probe, no slot, no run lifecycle, no reconcile.

## Why

This is exactly what the critic's message asked for, and it is a correction to
my own previous unit rather than to someone else's: `crimson-nest-6583` and the
subsection it landed both read a scheduled reset as proof of restored capacity.
The arithmetic in that subsection is unchanged and still holds — the two clocks
do not overlap, and they overlap less if the refusal outlasts its window — but
the claim resting on it was one step stronger than the receipt supports.

F10 asks the report to "name what remains open, claiming nothing a record does
not carry". A dated promise the evidence does not carry is the failure mode
that criterion exists to prevent, so fixing it advances F10 by the same logic
that motivated the subsection in the first place.

I did what the critic asked and nothing else. After this correction the
instruction is to hold: no probe, no frozen prompt, no reconcile, no lifecycle,
cadence, model or prompt change. This record is the mandatory one for the
dispatch, not a waiting record.

## Method

Read-only first:

- `docs/probes/ot7/attempts/f6-window-refusal.json` — `overage.status
  "rejected"`, `overage.disabled_reason "org_level_disabled"`, `in_use false`;
  `rate_limit_type "seven_day_overage_included"`; HTTP 429 "You've reached your
  Fable limit". The second probe twenty minutes later read `status "allowed"`,
  `five_hour` 2 % — and was refused anyway, which is the same lesson in the
  other direction: the window numbers are not the refusal.
- `grep` for the org-level readings across the record graph — `idle-crow-9434`,
  `pale-garden-4669`, `mellow-sky-2112`, `tidy-nest-3309`, `soft-creek-6253`
  all name the organisation-level limit as the binding one; none of them, read
  again, claims the reset lifts it. The overclaim entered with
  `crimson-nest-6583` and its subsection.
- `grep` over `cli/tests`, `src/Mod/cadex/cadex_tests` and the ot7 runner for a
  test pinning the report's headings or its path: none, so the retitle breaks
  nothing. The only internal reference is the lede's anchor link, updated in
  the same edit.

Then one edit to one file, applied with a Python string replacement so each old
passage had to match exactly, and committed alone.

Not run: no suite, because no product code, test or fixture changed and the
edit is one prose file under `docs/probes`. No window probe — the critic's hold
forbids one and it would spend a collector read for a number that cannot change
the conclusion.

## Result

The report's F6/F7 ending is now stated at the strength its receipts support:
the refusal is organisation-level, `2026-09-18T14:00:00Z` is the earliest it
*could* lift, only an unrefused probe would show that it had, and under the
current limits and stop rules both designs are expected to end this run
unattempted with all eight create and continuation slots unspent. Not
exhausted: the charter's exhaustion policy needs a prompt to have reached the
model, and neither design has spent one.

F6 (`narrow-dune-9454`) and F7 (`rapid-grove-9687`) stay blocked with four
slots each. F10 (`first-snow-5587`) stays open; the report is more nearly true
than it was, and critic acceptance of done remains unmet.

For the next iteration: the standing instruction is to hold — no probe, no
frozen prompt, no redundant reconcile, no lifecycle, cadence, model or prompt
change — and to resume F6 only on concrete restored-capacity evidence, which
means an unrefused `run.py window --model claude-fable-5`, not a clock reading.
The unreconciled tail is now three nodes (`vast-crow-3111`,
`crimson-nest-6583`, this one), past the charter's three-record threshold; the
critic's hold explicitly rules out a reconcile pass, so the next reconcile is
the critic's call and not a backlog anyone should clear on their own.

Dispatch closed: 1 unit — the closing report's gate subsection now reads its
own receipt: an org-level refusal with a scheduled reset that bounds it from
below, so F6 and F7 are expected, not certain, to end unattempted with all
eight slots unspent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 50a0305a35322ca7b768121d4ade2cf04c4c2541

## State Impact

- target: first-snow-5587 — REPORT.md's gate subsection is retitled 'The gate cannot open before this run's own stop' and qualified (commit 50a0305a): 2026-09-18T14:00:00Z is the rejected window's resets_at and therefore the earliest the refusal could lift, not a dated opening; the binding condition is overage.disabled_reason 'org_level_disabled', an organisation-level setting no window reset is evidence about; only an unrefused probe is evidence the refusal lifted; and under the current limits and stop rules F6 and F7 are expected, not certain, to end unattempted. F10 stays open and no done claim is made.
- target: narrow-dune-9454 — Correction to crimson-nest-6583's impact: the org-level claude-fable-5 refusal does NOT lift at 2026-09-18T14:00:00Z. That epoch is the rejected window's scheduled resets_at and bounds the refusal from below only; the receipt's binding field is overage.disabled_reason 'org_level_disabled'. F6 stays blocked with all four slots unspent, is expected under current limits and stop rules to end ot7 unattempted rather than exhausted, and resumes only on an unrefused window probe, not on a clock.
- target: rapid-grove-9687 — Same correction behind F6: the 2026-09-18T14:00:00Z epoch is a scheduled window reset, not proof the org-level Fable refusal lifts. F7 stays blocked with all four slots unspent and is expected to end ot7 unattempted rather than exhausted; its frozen create prompt (b95f98b7...) and three continuations remain available to a future run.
