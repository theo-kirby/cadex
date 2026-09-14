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
