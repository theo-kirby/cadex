# orun1 — the owner's design preferences, measured

Verified against source: 2026-10-02. Provenance: `[Cadex-new]`.

The charter for orun1 is `.ouroboros/goal.md`. This file holds the
evidence it starts from: a design-only sweep the operator ran before the
run, and the owner's blind ratings of it. The run adds its own contract
and results below the marker at the end.

## The sweep

ot10 (ADR-411 to ADR-444) gave Cadex robots a finish: a light shell, round
joints, an accent and a studio render. The owner's verdict on the result
(2026-10-01) was that the robots *look* finished but are not well
*designed*: the quadruped is "a rounded box with four legs", the motor
pods on its thighs look stuck on, and most hexapods "look really bad".
Writing more rules was unlikely to capture what was missing, so the
operator measured it instead.

- **Grid.** 7 robot types × 8 design theses = 56 designs, one fresh
  project each (`sweep-<type>-<thesis>`), one design turn each, design
  only, no training. `ratings.json` → `briefs` holds every prompt word for
  word.
- **Types.** Quadruped, hexapod, biped, 5-axis arm, 3-axis arm,
  two-wheeled balancer, wildcard (body plan of the agent's choosing).
- **Theses.** (a) the servo is the joint, (b) motors in the body, (c)
  clean exposed mechanism, (d) consumer product shell, (e) panelled
  hard-surface, (f) creature anatomy, (g) minimal geometry, (h) the
  agent's own choice.
- **Every brief** asked for real catalog parts at true size, design from
  the inside out (pack the components, then shape the structure and shell
  around them), refinement with `look`, and closing DESIGN NOTES.
- **Model.** `claude-opus-5-5`, `CADEX_EFFORT=medium`, at revision
  `2c34ab64`. Turns took 3 to 67 minutes.
- **Completed.** 55 of 56. The 56th (`hexapod-h-free`) was stopped
  unfinished at the owner's request and is not rated.

## The ratings

The owner rated all 55 **blind** on 2026-10-02: designs shuffled within
each type and labelled only by type and number; the thesis and the agent's
notes appeared only after a verdict was given. The scale is Love (3),
Like (2), Meh (1), No (0). No notes were written. The renders the owner
saw are the 640 px heroes in `sweep/` (downscaled from the 1024 px
studio hero, dark prototype floor).

Totals: 4 Love, 23 Like, 25 Meh, 3 No.

| thesis | arm3 | arm5 | balancer | biped | hexapod | quadruped | wildcard | mean |
|---|---|---|---|---|---|---|---|---|
| a servo is the joint | meh | like | meh | **no** | meh | like | like | 1.29 |
| b motors in the body | like | meh | meh | like | like | like | like | 1.71 |
| c exposed mechanism | like | like | **love** | **love** | like | like | meh | **2.14** |
| d product shell | like | like | like | meh | meh | meh | meh | 1.43 |
| e hard-surface | meh | meh | like | like | meh | **love** | like | 1.71 |
| f creature | meh | meh | like | meh | meh | meh | like | 1.29 |
| g minimal | meh | **love** | meh | like | **no** | meh | like | 1.43 |
| h own choice | meh | meh | like | **no** | — | meh | meh | 1.00 |
| **type mean** | 1.38 | 1.62 | 1.75 | 1.38 | **1.14** | 1.62 | 1.62 | |

## What the ratings say

These are the operator's reading. The owner has not yet confirmed them,
and the charter marks the three it depends on as owner-revisable.

1. **The three Nos are one archetype.** `biped-a-servo-joint`,
   `hexapod-g-minimal` and `biped-h-free` are each a large, soft, rounded
   box with a dark visor and two orange dot eyes, over short legs or
   stubby limbs, with boxes hanging under it. This is the "rounded box"
   the owner described, and it is what `docs/DESIGN-LANGUAGE.md` §0
   prescribes: "one soft body primitive with a face".
2. **Faces cost points.** 47 of the 55 sets of notes mention a face, eyes or
   a visor, because §4 of the design language asks for one. Those 47 average
   1.43. The 8 without one average 2.00. None of the four Loves has eyes.
3. **The Loves show how they are built.** `balancer-c-exposed-mechanism`
   (two slotted side frames, an orange cradle carrying the electronics, a
   visible cable loop, spoked wheels), `biped-c-exposed-mechanism` (a
   stacked servo column with orange horn caps, a board deck with routed
   wires, plain flat feet), `quadruped-e-hard-surface` (a chamfered body,
   a bolted hatch of dark panels, large dark hip actuators, a sensor slot
   instead of eyes) and `arm5-g-minimal` (a clean industrial arm with no face
   and no decoration). They read as engineered machines, not characters.
4. **The design language contradicts the owner on exposure.** §1 says
   purchased hardware is "never an exposed case or a bare board". The
   highest-rated thesis is the one that exposes them.
5. **Hexapods are the weakest type** (mean 1.14), as the owner said
   before the sweep.

Caution: 55 ratings, 4 Loves and 3 Nos are a small set, and a thesis is
confounded with the agent's execution of it. Read the per-thesis means as
direction, not as measurement.

## The split

`ratings.json` assigns every design to `dev` (27) or `heldout` (28),
stratified by verdict with the seed `orun1-split-2026-10-02`: Love 2/2,
Like 12/11, Meh 13/12, No 2/1. The split was fixed before orun1 started.
How the run may use it is the charter's rule (D1).

<!-- orun1: the run's contract and results go below this line. -->

## The split, counted

The paragraph above says 27 dev and 28 held-out. Counting `ratings.json`
gives **29 dev and 26 held-out** (Love 2/2, Like 12/11, Meh 13/12, No 2/1;
the per-verdict figures above are right and their sums are not). The file
is ground truth and is not edited; every number below uses the counted
split. The held-out set has 26 designs, so 325 pairs, of which **37**
differ by two levels or more (Love × Meh 24, Love × No 2, Like × No 11).

## D1 baseline: ot10's frozen judge on the held-out set (pre-registered)

**This is the baseline, not a judge version.** It is ot10's instrument run
unchanged, so that every orun1 judge version has a number to beat. It is
measured once, its result is published whatever it is, and nothing about it
is tuned: no prompt, rubric, reference, view or aggregation changes after
the first held-out call. It is not a candidate for D1's frozen judge.

- **Judge.** `docs/probes/ot10/runner/judge.py` exactly as frozen by
  `docs/probes/ot10/README.md` (rubric sha256 `1c81caa2…`, the ten core
  references, `claude-opus-5-5`, effort `high`, three calls, median per
  trait, total 0–21). The runner is imported, not copied.
- **Inputs.** For each of the 26 held-out designs, a copy of its sweep
  project at `~/cadex-projects/orun1-ho-<id>` (the originals stay
  read-only; `cadex render` re-accepts, ADR-476). The renders are ot10's
  set: the 1024 px studio hero from `cadex render`, then the `look` views
  `iso`, `iso_back`, `front`, `right`, `top` at the look tool's size, drawn
  by the bridge's own `look` (dark prototype floor for the hero). The judge
  sees them as `candidate-N.png` only.
- **Score.** A design's score is its ot10 total (sum of the seven trait
  medians).
- **Pairwise agreement.** Over the 37 held-out pairs whose owner verdicts
  differ by two levels or more, a pair agrees when the higher-rated design
  has the strictly higher total. **A tie is a disagreement.** Ties are also
  counted and reported. The bar is 80%.
- **Love over No.** Every held-out Love's total is strictly above every
  held-out No's total (2 × 1 = 2 pairs).
- **Kendall's tau.** τ-b between owner verdict (0–3) and total over all
  325 held-out pairs, reported with the count of concordant, discordant and
  tied pairs.
- **Harness.** A judge harness failure (a reply that fails to parse twice),
  a usage limit or a refusal is not a score. Such a design is re-run; if
  it still cannot be scored, it is reported as missing and every metric
  names the pairs it drops.
- **Machinery.** `runner/render_set.py` draws one design's inputs from its
  copy. Per-design scores go to `baseline/<id>-score.json` and the summary
  to `baseline/summary.json`.
- **Status.** Run once, complete: 26 of 26 held-out designs scored, no
  harness failure, no design re-judged (commits `97ca4c14`, `c432146d` and
  this one). The first attempt to draw inputs had found that ADR-476
  stopped six held-out designs reopening; ADR-477 reverted that before any
  judge call.

### D1 baseline result

ot10's frozen judge **fails every part of D1's bar**, and on the pairs that
matter it is worse than chance: it prefers the design the owner rated lower.

| metric | ot10 judge (baseline) | D1 bar |
|---|---|---|
| pairwise agreement, owner gap ≥ 2 | **13.5%** (5 of 37; 3 ties, 29 reversed) | ≥ 80% |
| every Love above every No | **fails, 0 of 2** | holds |
| Kendall's τ-b, all held-out pairs | **−0.079** over 325 pairs (79 concordant, 98 discordant, 148 tied) | reported |

Totals (0–21) by owner verdict:

| owner | n | ot10 totals | mean |
|---|---|---|---|
| Love | 2 | 12, 14 | 13.0 |
| Like | 11 | 14, 14, 14, 16, 16, 16, 16, 17, 17, 18, 18 | 16.0 |
| Meh | 12 | 11, 12, 13, 13, 15, 15, 16, 16, 16, 17, 18, 18 | 15.0 |
| No | 1 | 18 | 18.0 |

- The held-out No (`biped-h-free`, the soft rounded box with a visor and
  dot eyes) gets 18, tied for the highest total; the two held-out Loves
  (`biped-c-exposed-mechanism` 12, `quadruped-e-hard-surface` 14) are in the
  bottom third. By kind of gap pair: Love × Meh 5 agree, 18 reversed,
  1 tied (of 24); Love × No 0 of 2; Like × No 0 of 11 (9 reversed, 2 tied).
- Reading, not measurement: ot10's rubric was written to score the finish
  ot10 prescribed (one soft body, a face, hidden hardware), which is the
  archetype the owner rejected. A judge built from it is aligned to the old
  design language, not to the owner.
- Per-design scores, trait medians and render receipts:
  `baseline/<id>-score.json`; the metric output with every reversed and
  tied pair named: `baseline/summary.json`.

## D1 judge, built on dev

The judge is built on the 29 `dev` designs only. Nothing below was chosen
by looking at a held-out design, render or score. The dev split has 406
pairs, **54** of them two levels apart (Love × Meh 26, Love × No 4,
Like × No 24).

**Form: pairwise.** The bar is pairwise, and D4's bar is a pairwise
comparison against sweep designs, so the judge answers the question the
bars ask: of these two robots, which would the owner rate higher. One call
compares one unordered pair. A design's score is the fraction of its
comparisons it won, and the D1 metrics are computed on that score with
`runner/metrics.py` unchanged.

**Inputs: the hero only.** The owner rated from one picture per design,
the studio hero on the dark floor (above, "The ratings"), so the judge sees
the same one: the 1024 px hero that `cadex render` writes from an
`orun1-dev-<id>` copy at its accepted revision (`runner/draw_set.py`, which
copies the sweep project and calls `runner/render_set.py`; the originals
stay read-only). The images reach the judge as `A-1.png` and `B-1.png`. No
design id, thesis, note, project name or verdict is in any call. The
renders are not committed; each summary records each design's accepted
revision and the hero's sha256.

**Isolation** is ot10's: a fresh `claude -p` process in an empty temporary
directory, `Read` as its only tool, no MCP, no user settings, hooks,
memory or `CLAUDE.md`, model `claude-opus-5-5` with no fallback.
**Position** is balanced: which design is shown as `A` is fixed per pair by
a hash of the version name and the two ids. A reply that does not parse is
retried once. A second failure leaves the pair unjudged and is reported.

The machinery is `runner/pairwise.py`, and `runner/test_pairwise.py` pins it.
Results are in `judge/<version>-dev/` (`pairs.jsonl` holds every verdict
with its one-sentence reason; `summary.json` holds the scores and metrics).

### Judge v1 on dev

v1's instructions describe the owner's taste from the charter and the
operator's reading above: engineered machines, hardware laid out with
order, hard-surface enclosures allowed, the mascot archetype disliked, and
no credit for finish alone.

| metric (dev) | v1 |
|---|---|
| pairwise agreement, owner gap ≥ 2 | **81.5%** (44 of 54; 0 ties, 10 reversed) |
| every Love above every No | holds (4 of 4) |
| Kendall's τ-b | 0.261 over 406 pairs |
| A picked | 48.5% |

v1 clears the bar by one pair (43 of 54 would be 79.6%), which is not a
margin. Its ten misses fall into two patterns:
- **The loved plain arm lost to detail.** `arm5-g-minimal` (Love: a clean
  arm of simple white volumes, no hardware visible) lost to four Mehs that
  show servo housings, horn rings or fastened panels. The judge's reasons
  are each some form of "B shows no actuators, fasteners or structural
  detail". v1 rewarded the *amount* of visible hardware.
- **A committed character lost to the generic box.** The two dev Nos
  (`biped-a-servo-joint`, `hexapod-g-minimal`) are the soft visor box. They
  beat three Likes that also have a face (`balancer-h-free`,
  `biped-g-minimal`, `wildcard-f-creature`, the last a fully committed frog).
  The judge's reasons say "both have faces", and v1 then preferred the one
  with more visible servos.

### Judge v2 on dev

v2 changes exactly those two things (`runner/pairwise.py`, `V2_INSTRUCTIONS`):
a resolved, intentional whole is the first criterion, and it can be reached
by an exposed mechanism, a crisp hard-surface enclosure *or* a clean minimal
form, with an explicit "do not prefer a design because more of its parts
are visible". The archetype is now named narrowly (the generic soft box
with a visor over thin or short limbs, with blocks hanging off it). A face
still counts against any design, but a committed character beats that box.
Inputs, form, model, effort and aggregation are v1's.

A **mirror replicate** ran v2 again with every pair shown the other way
round, to measure position and call noise before trusting the margin.

| metric (dev) | v2 | v2 mirrored |
|---|---|---|
| pairwise agreement, owner gap ≥ 2 | **90.7%** (49 of 54; 1 tie, 4 reversed) | **90.7%** (49 of 54; 1 tie, 4 reversed) |
| every Love above every No | holds (4 of 4) | holds (4 of 4) |
| Kendall's τ-b | 0.307 over 406 pairs | 0.298 over 406 pairs |
| A picked | 49.5% | 48.0% |

The two replicates pick the same winner on 94.6% of all 406 pairs and on
the same 49 gap pairs. The misses that remain are `arm5-g-minimal`
against three detailed Meh arms, and `biped-g-minimal` (Like) against
`biped-a-servo-joint` (No). The tie is `biped-b-motors-in-body` (Like)
against `biped-a-servo-joint`.

Caution, read before the held-out result: v2 was written after reading
v1's dev misses, so its dev figure is optimistic by construction. The
held-out measurement is the one that counts. τ-b stays near 0.3: the
judge separates the extremes better than it orders Likes and Mehs, and on
dev it rates arms higher than other types (the top seven dev scores
include five of the eleven dev arms).

Dev cost: v1 $14.36, v2 $14.66, mirror $14.62 (406 calls each, about four
seconds a call).

## D1 frozen judge: v2 (frozen before any held-out call)

**This is the judge version D1 measures, frozen 2026-10-02 before any
held-out call by it.** It is measured on the held-out set once, and the
result is published whatever it is. Any change to what follows is a new
version, needs a change motivated by dev results, and is measured once in
its own right.

- **Model:** `claude-opus-5-5`, effort `high`, no fallback model.
- **Prompt:** the system prompt is `V2_INSTRUCTIONS` in
  `runner/pairwise.py`, sha256 `0ebb596584eb1203a5706ab40c9e4799b24a0dbbf7d1d5a644eb1215d68708ab`
  (`pairwise.FROZEN`, pinned by `test_pairwise.py`). The user turn lists
  the two images under "Robot A:" and "Robot B:" and asks for the JSON
  object only. The prompt, verbatim:

> You are judging the design of two small robots, A and B, from renders. Each was designed to be 3D-printed around hobby servos, controller boards, batteries and sensors. They may be different kinds of robot (an arm, a walker, a balancer, something else). Decide which one a particular owner would rate higher. This owner's taste:
>
> - Above all they reward a resolved, intentional whole: a form where every part looks designed for its place and the robot reads as one considered object. That can be reached several ways, and each is good: an exposed, ordered mechanism (real actuators, boards, batteries and cables laid out on purpose, horns, fasteners and seams as detail); a crisp hard-surface enclosure (flat panels, chamfers, visible fastening, a sensor as a real part); or a clean, minimal form with simple, well-proportioned volumes and nothing decorative. Do not prefer a design because more of its parts, fasteners or detail are visible; a plain design loses only when it is also vague or badly proportioned.
> - Their strongest dislike is one specific archetype: a generic soft, rounded, pillow-like box as the body, with a visor slot, a face or dot eyes, over short or thin limbs, with blocks hanging off or under it. It looks neither engineered nor characterful. A face or eyes count against any design, but a fully committed character whose whole form follows one idea is better than that generic box.
> - They dislike parts that look stuck on, unsupported or arbitrary, and prefer structure and limbs whose shape looks load-carrying and purposeful.
> - Finish alone earns nothing: smooth shading, colour and a clean render do not make a design good.
>
> Judge the design, not the kind of robot, the camera or the background. Read every image with the Read tool first. Then reply with one JSON object and nothing else: {"winner": "A" or "B", "reason": "one sentence"}.

- **Inputs:** one image per design, the 1024 px studio hero `cadex render`
  writes on the dark prototype floor, drawn from an `orun1-ho-<id>` copy at
  its accepted revision by `runner/draw_set.py --split heldout`. No `look`
  view.
- **Comparison:** pairwise, one call per unordered held-out pair (325
  calls), the side shown as `A` fixed by
  `sha256("v2|<a>|<b>")[0] & 1` over the sorted ids. No mirror.
- **Aggregation:** a design's score is its fraction of judged comparisons
  won. The three D1 metrics are `runner/metrics.py`'s, on that score: a tie
  is a disagreement.
- **Harness:** a reply that does not parse is retried once; a second
  failure leaves the pair unjudged. Unjudged pairs, a usage limit or a
  refusal are not verdicts. The run resumes on exactly the missing pairs,
  and anything still unjudged is reported with the pairs it drops.
- **Guard:** `pairwise.py` refuses `--split heldout` for any version not in
  `FROZEN` with its exact hash, for a mirror, and into a directory that
  already holds a held-out result.
- **Command:**
  `pixi run python docs/probes/orun1/runner/pairwise.py --version v2 --split heldout --inputs <drawn heroes> --out docs/probes/orun1/judge/v2-heldout --jobs 8`.

### D1 held-out result: judge v2 (measured once, 2026-10-02)

Frozen v2 ran once on the held-out set, exactly as frozen above: 26 heroes
drawn by `runner/draw_set.py --split heldout` from `orun1-ho-<id>` copies at
their accepted revisions (hashes and revisions in the summary), 325 calls,
all 325 judged on the first pass with no harness failure, unjudged pair or
resume. **It meets every part of D1's bar.**

| metric (held-out) | ot10 judge (baseline) | **judge v2 (frozen)** | D1 bar |
|---|---|---|---|
| pairwise agreement, owner gap ≥ 2 | 13.5% (5 of 37; 3 ties, 29 reversed) | **97.3%** (36 of 37; 0 ties, 1 reversed) | ≥ 80% |
| every Love above every No | fails, 0 of 2 | **holds, 2 of 2** | holds |
| Kendall's τ-b, all held-out pairs | −0.079 over 325 pairs | **0.436** over 325 pairs (154 concordant, 43 discordant, 122 tied by owner only, 6 tied by judge only) | reported |
| A picked | — | 50.5% | — |

Scores (fraction of 25 comparisons won) by owner verdict:

| owner | n | v2 scores | mean |
|---|---|---|---|
| Love | 2 | 1.00, 0.80 | 0.90 |
| Like | 11 | 0.96, 0.88, 0.80, 0.76, 0.68, 0.64, 0.52, 0.44, 0.32, 0.24, 0.16 | 0.58 |
| Meh | 12 | 0.88, 0.72, 0.64, 0.60, 0.48, 0.36, 0.32, 0.28, 0.24, 0.12, 0.04, 0.00 | 0.39 |
| No | 1 | 0.12 | 0.12 |

- The held-out Loves rank first (`quadruped-e-hard-surface`, 1.00, won
  every comparison) and joint fifth (`biped-c-exposed-mechanism`, 0.80). The
  held-out No (`biped-h-free`) is fourth from the bottom at 0.12.
- The one reversed gap pair is `biped-c-exposed-mechanism` (Love) against
  `arm3-h-free` (Meh, 0.88). It is reversed by the **aggregation**, not by
  the call: on that pair's own call the judge picked the Love. The Meh arm
  won more of its other comparisons. This is the dev caution about arms
  repeating: v2 rates a clean arm higher than the owner does.
- Caveats, not excuses: the held-out extremes are small (2 Loves, 1 No, so
  "Love above No" is two pairs), and τ-b counts the 122 pairs the owner
  rated level as neither concordant nor discordant. The judge orders the
  middle (Like against Meh) less well than the extremes, as on dev.
- Cost $11.88 (325 calls). Every call and its reason: `judge/v2-heldout/pairs.jsonl`;
  the metric output, inputs' hashes and revisions: `judge/v2-heldout/summary.json`.
- **v2 is the judge D4 uses.** It was measured on the held-out set once. No
  later version is needed for D1, and the held-out set has now been used
  for its one purpose: nothing may be tuned on it.

## D2: the design language, rewritten from these ratings

`docs/DESIGN-LANGUAGE.md` is rewritten on A1–A3 (ADR-479). Each rule cites
sweep ids with their verdicts here, or the charter, or is marked as
judgement. The four contradicted rules are removed by ADR-480 (the face),
ADR-481 (the single soft primitive), ADR-482 ("never an exposed case or a
bare board") and ADR-483 ("split lines only"). ot10's rubric is retired as the
authority by ADR-484. The overlay the product agent reads
(`src/Mod/cadex/CadexAgentGuidance.md`) teaches the same rules as an
inside-out procedure in six steps. It quotes no rating, id, render or judge
text, and `cli/tests/test_turn_loop.py` holds that against every id and image
name in `ratings.json`. The language cites held-out designs as evidence only
after D1's judge was frozen and measured: nothing D1 counts was chosen from
them.
