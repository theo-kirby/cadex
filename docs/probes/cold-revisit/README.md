# Fresh arm walk and cold project revisit

Verified against source: 2026-09-08. [Cadex-new].

A fresh hinged-arm walk and six subsequent public CLI commands passed in
separate processes against the same external project. This is standing
maintenance of the delivered lifecycle and headless-review criteria, following
`modest-grotto-1192`; it introduces no feature or recovery path.

Reproduce from the repository root with the built engine and training venv
from `training/SETUP.md`, choosing a fresh project outside this checkout:

```bash
project=$(mktemp -d)/hinged-arm
./cadex script --project "$project" --set examples/lifecycle/hinged-arm/script.py --json
JAX_PLATFORMS=cpu .venv/bin/python docs/probes/named-angle/fresh-walk/monitor.py \
  ./cadex walk --project "$project" --out "$project/runs/baseline" \
  --trainer-python "$PWD/.venv/bin/python" --iterations 1 --envs 4 --seed 0 \
  --timeout 600 --json
./cadex script --project "$project"
./cadex asset --project "$project" --json
./cadex inventory --project "$project" --json
./cadex clearance --project "$project" --json
./cadex render --project "$project" --json
./cadex section --project "$project" --plane XZ --offset-mm 3.125 --json
```

Wait for each command to exit before starting the next. No producing session
was retained and no cache or asset was deleted. The monitor samples the entire
walk's process tree every 0.2 s, terminates above 2.9 GB or 850 s, and reported
exit 0, 16.80 s and peak sampled RSS 1,056,636,928 bytes. This is a sampled
maximum, not an instantaneous maximum. The trainer also had its 600 s timeout.
The CLI gate overlapped the walk; timings are observations, not benchmarks.
Training and rollout numbers are in PROGRESS.md and runs/baseline/review.json.

`audit.json` identifies the baseline commit and the final project commit.
Read the script returned by the public command and compare it with script.py;
hash assets before and after; compare accepted_revision/accepted_digest from
script.json after every command with the baseline rollout identity. All six
commands exited 0 and preserved both fields. The restored policy receipt's
SHA-256 equals review.json; the restored trace is byte-identical to the
baseline exported rollout trace. No policy/checkpoint/trace bytes are retained
in this evidence directory.

The four standalone SVGs equal the committed baseline SVGs byte for byte.
The section SVG also equals its baseline. Render and section object geometry,
revision and digest equal the walk's review; wrapper/path fields and timings
differ as expected. Inventory and clearance markdown remain byte-identical.
The section writes its revision-addressed summary again with fresh timings;
`baseline-section-summary.json` retains the original committed summary and
review.json keeps the original walk measurements. This is expected output
refresh, not lost geometry or stale success.

All five SVGs were rasterized with inspection-only CairoSVG and visually
inspected. Blue base and orange arm appear in all named views with legible
captions and expected initial placement. The XZ section at Y=3.125 mm contains
two closed contours, 360 and 640 mm², meeting at Z=6 mm. Inventory names two
synthetic uncatalogued components. Clearance names base–swing, 0 mm distance,
0 mm³ common volume, one offending pair and zero unknown pairs. Zero common
volume does not make the contact clear. These remain initial-pose tessellation
reviews, not exact sections or swept-motion safety; toy policy verification
does not demonstrate useful control.

Cold restore restages accepted attempts and prunes older transient attempts;
this is documented in docs/CLI.md's project persistence section. Inventory's
inspection itself does not request a rebuild, but its ordinary session does
restore the model. Render and section explicitly acquire rebuilt display.
Review commands append their normal PROGRESS rows and commit. Architecture,
decisions and script bytes survived the commands unchanged; PROGRESS additions
were expected. After inspection the agent copied the existing example sensor
notes, recorded this evidence in project ADR-002/PROGRESS.md, normalized project
paths in prose, and committed them. Every retained project file matches that
final commit byte for byte and the source project is clean.

No runtime behavior, scaffold convention, payload, shell or protocol changed.
No build or packaged gate is claimed. GUI remains documented-only and remote
training scripted-only; neither was executed. No persistence defect was found,
so the plan's conditional repair is not actionable. This bounded direction is
exhausted and should be re-planned without repeating the walk or promoting
Later criteria.

Full built-engine CLI gate: `pixi run python -m pytest cli/tests -q
--basetemp <fresh-temp-directory>` — **195 passed, zero skipped, 218.91 s**,
exit 0. Full output is retained in cli-gate.log. git diff --check and the
hypergraph export/check gate passed.
