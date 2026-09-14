# Robin — recovery through alternate Claude models (D7)

Verified against source: 2026-09-14. [Cadex-new]

**Robin still has no accepted balancer.** All three recovery attempts through
the product CLI's existing `--model` option returned the provider's session
limit before producing a repaired design. The selections were `opus`, `sonnet`
and `haiku`; the CLI reports those same model arguments, not resolved model
versions. [model-recovery.json](model-recovery.json) carries timestamps,
statuses, accepted identity, dashboard observations and external log digests.
This establishes that changing these model selections did not bypass the limit
at the time tested; it does not establish future availability.

Each attempt supplied the same complete recovered candidate and repair prompt
from the preceding iteration. The prompt explicitly asks the product agent to
correct the reset-floor penetration and submit the complete source, then
measure the fits and inventory before training. Commands ran from the checkout,
with paths below relative to the operator's external `cadex-projects` directory:

```bash
PROJECTS="$HOME/cadex-projects"
for MODEL in opus sonnet haiku; do
  timeout --signal=TERM --kill-after=10s 1800 ./cadex --model "$MODEL" \
    --project "$PROJECTS/ot6-robin" \
    --out "$PROJECTS/ot6-robin-src/$MODEL-out" --json \
    -p "$(cat "$PROJECTS/ot6-robin-src/resume.prompt.txt")"
done
```

Each invocation exited 1 with `You've hit your session limit`, reporting a
10:10 pm America/New_York reset. No wait for that clock was performed. The
accepted revision remains `f5f0533481457549b2f07637a9ac825a5bb32ca7270dafdb504c8adf5c7e16b4`,
and the accepted contract contains only `probe_motor`. The rejected complete
candidate remains uncorrected and unaccepted. No measured fits, finished
inventory, training or new videos resulted. The actor did not author a
replacement design or change provider infrastructure.

Before the first invocation and after the last, the persistent operator page
at `http://<private-address>:8765/` loaded `finch1-final` at both 1400×900 and
400×850 (touch emulation). All four visits showed 29 tessellated components,
95,212 triangles, zero horizontal overflow, advancing video playback and the
same 155,239-byte video download with SHA-256
`f57c4c3bb2b3ce565d1feefa411c88879c92d4efe0561d45d3dddc9e995cb6f7`.
The retained browser probe from iteration 16 was reused with only its output
filename changed. The server was left running on Finch because Robin is still
only a probe. These visits check the experiment boundary; they are not another
D9 regression unit. No full suites or build were repeated for this evidence-only
change; the receipt size and privacy checks were run.

The critic's requested acceptance, inventory and measured fits could not be
completed because all tested alternate selections were refused. D7 remains
open. Its next design attempt must still go through the product agent, submit
the whole repaired candidate and establish the fits before the operator page
moves to Robin. Repeating full regression suites does not resolve this blocker.
