# Frozen-design evidence runner

Verified against source: 2026-09-14. [Cadex-new]

This is the critic-requested F5–F7 fallback while F4's provider is unavailable
(ADR-354). It has **not run a design attempt**. The documented provider reset
is 2026-09-14 at 20:20 America/New_York; this unit began at 17:44, before it.
F4 remains open and its seed and repair prompt are unchanged.

Run one design, in a new external project, using the existing pixi environment:

```bash
pixi run python docs/probes/ot7/runner/run.py heron \
  "$PROJECTS/ot7-heron" --model claude-fable-5
```

`PROJECTS` must name the operator's external `cadex-projects` directory.
Use `robin` or `plover` for the other frozen designs. The runner checks all
four prompt digests against the freeze before creating the project. The create
prompt and the three continuations are the complete schedule. Each slot is
persisted before dispatch. Existing projects are refused, including interrupted
ones: this command does not resume attempts or reset a consumed budget.

Each design change is made by the ordinary product-agent turn. The collector
uses the CLI's turn-factory seam to save the provider stream and suppress the
CLI's automatic no-tool follow-up, whose text is outside the frozen schedule.
A blocked follow-up stops the attempt. The ordinary stale-session recovery may
retry the same frozen text; its returned stream is preserved by the CLI.
No script, parameter or accepted-state writer exists in this runner.

Under `evidence/`, `attempt.json` records the design, model, prompt digests,
continuation counts, elapsed time and process status. Each `turn-N/` retains:

- A verbatim frozen prompt and the provider `transcript.jsonl`, with digests.
- The CLI JSON envelope and stderr, including errors and printed claims.
- `clearance.json`: all published static pairs and the raw swept report,
  including missing or incomplete coverage and per-joint timings.
- `fit.json`: the product's static verdict, failure count and every failing
  pair, read independently from the accepted measurements after the turn.
- `inventory.json`: the accepted catalog inventory.

Artifact paths in each row are relative to its `turn-N/` directory; smoke
artifact paths are relative to `evidence/smoke/`. Every listed file carries its
byte size and SHA-256. The manifest is project-local, and may exceed the 16 KB
limit for committed receipts. Publish only a compact receipt citing it.

The runner uses all three continuations even if an earlier static report
passes: a static pass says nothing about missing swept coverage. It adds no
second swept checker and claims no design passes. The final report author must
assess the retained swept extrema against intent and account for missing
coverage. Provider errors, timeouts and launch failures stop further prompts;
an ordinary rejected design (CLI exit 3) can receive the next frozen
continuation. Interrupted attempts retain their consumed slots and evidence;
missing transcript or measurement files mean unavailable evidence, never zero
failures. The runner must not be restarted against another project to hide
such an attempt.

Each model call has a 30-minute process bound; each measurement read has a
five-minute bound. Timeout kills the child process group. One final one-second
holding smoke is attempted even for failing designs, with a 240-second internal
budget and a 300-second process bound. Its full receipts and logs stay in
`evidence/smoke/`. A process exit of zero alone is not a passing smoke: read the
receipt's verdict. No policy is trained. The collector does not change engine,
CLI, protocol, acceptance or dashboard behavior.

`cli/tests/test_ot7_runner.py` exercises a permanently failing design through
all four slots, refuses a restart before any fifth dispatch, checks refusal and
timeout stops, rejects changed prompts, blocks the automatic follow-up, checks
evidence hashes and kills a timed-out child. These are runner fixtures, not
F5–F7 design results.

## Seeded repair (F4)

Iteration 25 added `repair` while the documented reset was still ahead
(18:02 New York time; ADR-354). No provider call was made in that unit.
After the reset, collect the single frozen repair call on the preserved seed:

```bash
pixi run python docs/probes/ot7/runner/run.py repair \
  "$PROJECTS/ot7-heron-repair" --model claude-fable-5
```

This mode requires an existing seed. It checks the script hash and first
accepted revision against the original refusal receipt, the preserved accepted
digest, working revision, and empty parameter/board/cage/mount/net overrides.
It neither copies nor writes a design. It exclusively creates
`evidence/f4-repair/`; an existing directory refuses redispatch, including an
interrupted call. Earlier provider refusals remain in their original evidence
directories and must be included in the final accounting.

The runner first reads all accepted clearance pages with `restore=False`,
retaining `before/clearance.json`, `before/fit.json` and their hashes. A failed
read, missing report or changed script/metadata stops before any provider call.
It then dispatches only `repair.prompt.txt`, without `--resume`, under the same
30-minute bound and automatic-follow-up guard as design attempts. It records
one consumed continuation, the provider stream, elapsed time, after-fit report
and before/after accepted metadata and script hashes. The before artifacts are
relative to `before/`, and turn artifacts to `turn-0/`, within `f4-repair/`.
A refusal still retains after measurements. No smoke or additional continuation
is run for F4. Missing evidence never means passing fit, and CLI exit status
alone does not establish a completed design turn or a successful repair.

Known-answer fixtures preserve a seed through collection, supply seven before
failures and zero after failures, verify the sole frozen prompt and fresh
session, reject changed seed identity, and stop on missing/failed/mutating
before reads. They prove collection behavior only; F4's actual repair remains
open until a product-agent turn supplies the measurements.

Iteration 27 additionally exercises `child_measure` through the real paginated
inspect reader and product fit summary. A known-answer fixture places an
overlap and missed contact on a later page, plus a world-plane failure, and
requires all three findings and their exact numbers in `fit.json`. It checks
that nested swept extrema, first-contact angle, incomplete coverage and runtime
survive unchanged in `clearance.json`, along with catalog inventory. An error
on the later page must raise without writing a partial fit report. The session
must use `restore=False` and issue only inspect requests. These are synthetic
collector tests, not measurements of Heron or an F4 repair result. The provider
reset was still ahead at 18:17 New York time; no provider call was made.

Iteration 28 adds a nested-pagination fixture: the swept joint array has two
pages, and the joint on its later page has a two-page pair array. Only the last
pair page carries the worst overlap (12 mm³) and first contact (30 degrees).
The real collector must preserve both joint rows, both pair rows, their exact
extrema and timings in `clearance.json`. This is synthetic collection evidence,
not a design result. At 18:29 New York time the reset remained ahead, so this
unit made no provider call.

## Real preserved-seed measurement (iteration 29)

The real `--child-measure` process now has an integration receipt:
[`repair-measurement.json`](../retained/repair-measurement.json). It read
`ot7-heron-repair` with `restore=False`, exited zero in 0.164 seconds, and
preserved both the script identity and the complete metadata bytes. The
project-local files are under `evidence/iteration29-measurement/`; the receipt
lists every artifact's size and SHA-256. Assertions verified those hashes,
105 distinct pairs, 15 inventory components, and the same accepted revision
in the clearance, fit and inventory reports.

The measured baseline has **15 failing entries**: eight intersecting pairs,
six below-clearance pairs, and one world-geometry failure on `comp_base`.
The shoulder servo overlaps its base by 248.20162986795066 mm³. The shoulder
horn is 0.19999999999999732 mm from the upper arm; the elbow horn is
0.19999999999993 mm from the forearm. These gaps are present in the collected
measurements but do not fail the default 0.1 mm clearance rule: this old seed
declares no contact intent. A zero-failure summary alone therefore cannot
establish that the repair resolved those disconnected attachments.

Swept coverage is explicitly unavailable on this accepted revision. This read
does not rebuild geometry, measure new poses, or prove real swept pagination.
It establishes integration with the retained published measurements. At
18:40 America/New_York the documented 20:20 provider reset was still ahead;
no provider call or design edit occurred, and `evidence/f4-repair/` remains
unconsumed. After reset, use the repair command above and compare its guarded
before-read with this retained baseline; dispatch only the frozen repair
prompt. F4 remains open, and earlier refusals remain part of its accounting.
