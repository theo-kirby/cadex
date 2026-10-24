# Goal: leon I in four styles — soft, sleek, organic, crisp — for the owner to choose

Verified against source: 2026-10-24. Operator charter for orun20, a 24 h
design-only run. It follows orun19 (`.ouroboros/history/orun19.md`, merged at
`d2b161ca`).

## Mission

Leon I (`~/cadex-projects/leon`, tag `leon-i`) works as a mechanism. Its shell
does not yet look the way the owner wants. Too many panel outlines end in sharp
corners, the nose comes to a hard point, and the ears are beveled polygons rather
than round. This run builds the same robot in four aesthetic styles and puts them
side by side, so the owner can pick one, or parts of several.

1. **Soft / rounded (required).**
   - Every panel's outline corner is rounded: the corner of the shape, not the
     bend in the panel's surface.
   - The face's corners are rounded too: the nose tip, the muzzle, the brow and
     the jaw.
   - The ears are round half-discs, not beveled facets.
2. **Sleek / streamlined.** Fewer, larger panels, with long continuous surfaces
   and tight seams, along a cheetah's lines.
3. **Organic / anatomical.** Panels shaped like the muscles under them
   (shoulder, haunch, ribcage), and a sculpted, softer face.
4. **Crisp / refined faceted.** Keep today's faceted language but make it
   deliberate: consistent chamfers and bevels, no needle points, and a geometric
   face done well.
5. **A comparison the owner can choose from.** All four, plus leon I, from
   identical cameras, with their numbers in one table.

If the loop achieves only one thing, it is **the soft / rounded leon**, built
clean and shown beside leon I.

## The machine

- **Leon I is the base:** `~/cadex-projects/leon` at tag `leon-i`, script
  `~/leon-queue/leon_i5.py`. It is leo v06 (sphere feet, heel pads, no fore
  wrists) plus three changes:
  - an AK10-9 spine pitch drive;
  - flank panels on the saddle;
  - the v06 thigh panels.

  Its clearance baseline:
  - static: 6 known pairs (the hind rod/crank/meta contacts and the knee's
    missed contact);
  - swept: 0;
  - panels: pass.

  It weighs 31.3 kg, with 24 drives (revision `092997dd`). It is in the leon project's
  `DECISIONS.md` ADR-002.
- **The mechanism is frozen.** These stay exactly as leon I has them:
  - joints, their axes and limits;
  - drives and links;
  - collision geometry;
  - the MJCF's joints and actuators.

  A style changes only:
  - shell panels and their formers, posts and screws;
  - the face's and ears' shell parts;
  - tail and leg covers;
  - colours and finish, if a style calls for them.
- **What the owner said about form:**
  - Form follows function, never "look engineered".
  - Curved panels are good when they wrap the mechanism. Cosmetic shells over
    nothing are a defect.
  - Styles are options over one general base, not fixed rules.

## Done criteria

- [ ] **K1. The comparison kit.**
  - One command renders any leon project from fixed cameras on the dark floor
    (the dashboard's palette, `docs/DASHBOARD.md`):
    - hero three-quarter;
    - side;
    - front;
    - three-quarter rear;
    - top;
    - a head close-up.
  - It also assembles a labelled grid of several projects per camera
    (`cadex hero-grid` where it fits).
  - The run's page carries leon I's set.
- [ ] **K2. Corner measures.**
  - Each build reports two numbers:
    - the share of sharp edges (the concept sheet's "sharp edges");
    - the smallest outline-corner radius on its shell panels, with a count of
      corners under 4 mm.
  - Both are measured on leon I as the baseline.
- [ ] **S1. Soft / rounded leon** (`~/cadex-projects/leon-soft`).
  - Every shell panel's outline corners are rounded to at least 6 mm, or as
    much as the panel's width allows. The report names each panel kept
    smaller and why.
  - The nose tip and the face's corners are rounded. No point of the face
    shell is sharper than a 4 mm radius.
  - The ears are round half-discs, at least 10 mm in radius at the tip.
  - The panel surfaces keep wrapping the mechanism.
  - The sharp-edge share falls well below leon I's.
- [ ] **S2. Sleek / streamlined leon** (`~/cadex-projects/leon-sleek`).
  - It has fewer panels than leon I and longer runs between seams.
  - The report gives the panel count and the longest panel against leon I.
- [ ] **S3. Organic / anatomical leon** (`~/cadex-projects/leon-organic`).
  - Its panels follow the muscle groups under them.
  - Its face is sculpted rather than faceted.
  - The report says which muscle each panel stands for.
- [ ] **S4. Crisp / refined faceted leon** (`~/cadex-projects/leon-crisp`).
  - Its bevels and chamfers are consistent, one or two sizes used
    throughout.
  - It has no needle points.
  - Its face is geometric and deliberate.
- [ ] **G1. Every style passes leon I's gates.**
  - Each style is a clean, accepted build.
  - Clearance does not regress against leon I:
    - static: only leon I's 6 known pairs;
    - swept: 0;
    - panels: pass.
  - The MJCF's joints, limits and actuators are identical to leon I's
    (diffed).
  - Total mass is within ±5% of leon I's.
  - It stands, with no NaN: the keyframe holds 3 s on the balls.
- [ ] **C1. The comparison.**
  - It covers leon I and the four styles, from K1's cameras, with head
    close-ups.
  - It has a table of each style's numbers:
    - mass;
    - panel count;
    - sharp-edge share;
    - smallest corner radius;
    - clearance;
    - build time.
  - It is on the run's page, and committed as PNG under
    `docs/probes/orun20/`.
- [ ] **R1. The report.** `docs/probes/orun20/REPORT.md` gives:
  - what each style changed;
  - what the engine or the script needed to do it;
  - what was tried and dropped;
  - which pieces of each style could combine, with the owner's choice left
    open.

## Horizon ladder

- **short-term:**
  1. K1: the camera set and grid, rendered for leon I and on the run's page.
  2. K2: measure leon I's sharp edges and corner radii.
  3. Copy leon I into the four style projects, the way leon was copied from
     leo:
     - its script from `~/leon-queue/leon_i5.py` (or tag `leon-i`);
     - its `agent.json`, `.gitignore` and `docs/`;
     - fresh history, with the first build as that project's baseline.
  4. Soft, first: find how to round a panel's outline corners. Pick the
     cheapest thing that works:
     - rounded region outlines in the script (the regions are boxes today);
     - an option on `part.skin`;
     - fillets on the cut panel.

     Prove it on one panel, then roll it out.
  5. Soft: round the nose tip and the face's corners, then turn the ears into
     round half-discs.
- **medium-term:**
  1. S1 to completion and G1 on it, then C1's first comparison: leon I beside
     soft.
  2. S2, S3 and S4, each built and through G1, one change at a time.
  3. C1 with all five.
  4. Anything that proves general (rounded outlines, round ears) goes into the
     engine or `CadexAgentStyle.creature.md` as an option, never a rule, with
     an ADR.
- **long-term:**
  1. A second round on each style, after reading the comparison: fix what
     reads worst in each.
  2. Mixes: the soft face on the sleek body, the organic haunch on the soft
     body. Each mix is a project of its own, if the styles' pieces combine.
  3. R1, kept current.
  4. Keep every gate green, every doc true, `STATE.md` folded.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries.
  - The repository carries no GPL or AGPL code.
  - `CadexDynamics.py` stays unreachable from `cadexd` (ADR-102).
- Never commit any of the following:
  - secrets or private hostnames;
  - build outputs;
  - full transcripts;
  - policy binaries, checkpoints or rollout traces;
  - fetched third-party files.
- Do not hand-edit `STATE.md`, `PLAN.md` or state claims.

**This run:**
- **Projects the run writes:** `~/cadex-projects/leon-soft`, `leon-sleek`,
  `leon-organic`, `leon-crisp`, and any mix project it creates
  (`leon-mix-*`).
  - `~/cadex-projects/leon`, `leo` and every other project are read-only.
- **The mechanism is frozen** (The machine, above). A change that would move a
  joint, a drive, a link or a collision shape is out of scope: report it, and
  do not make it.
- **No training, and no GPU work.** This is a design run.
- **Builds.**
  - A leon build takes 12–15 minutes and goes to the background.
  - A first build in a fresh project takes longer, with no part cache.
  - At most two builds run at once (each FreeCADCmd is capped at 16 GB:
    `ulimit -v 16000000`).
  - The project's `agent.json` timeout stays at most 3600 s.
  - OCCT fillets on curved shells have refused or segfaulted before (leo's
    domed-face lab). Prefer constructions that are round by shape (rounded
    outlines, tori, spheres, rounded sketches) where a fillet fails, and
    record each failure.
- **Engine changes are allowed** when a style needs one.
  - Each gets an ADR from ADR-792, the engine and CLI suites, and
    `pixi run build-engine`.
  - The protocol and tool surface stay a contract (AGENTS.md).
- **Images:**
  - every render is on the dark floor;
  - committed images are PNG, ≤ 300 KB each, under `docs/probes/orun20/`;
  - full-size renders stay in the projects' `review/` folders.
- **The dashboard stays read-only.** The actor may serve it on 127.0.0.1;
  it never runs `tailscale serve` or binds a public address.
- No role starts, stops or restarts the loop or signals its process. Kill
  stray processes by PID, never with a broad `pkill` pattern.

## Owner notes

- **The run's page is the owner's view.** The scribe keeps it, showing:
  - each style's newest hero and head close-up beside leon I's;
  - the C1 table.

  The owner chooses from it, so it has to show the styles, not describe them.
- **Gates run in the foreground** and finish within the shell's 10-minute
  limit.
- **Lean suites (ADR-725).** Add a test only for a contract or a regression
  that actually happened.
- **Useful from before:**
  - leo's head lab notes (`~/cadex-projects/leo/DECISIONS.md`, and the leo
    memory): sphere-cap domed faces failed in OCCT. Face crease radii 26/18/14
    were the owner's accepted "rounder" face on leo v01.
  - `cadex clearance` and `--sweep`, and `docs/probes/orun13/clearance_diff.py`,
    diff a build against leon I.
  - The stand check: load the MJCF, hold the keyframe 3 s, check for NaN and
    that the balls carry the weight.

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion. The order is K1, K2, S1, G1 on
  S1, then S2–S4, C1, R1.
- Taste calls inside a style's brief are the run's to make. Make them
  visibly, so the owner can compare them, and say which were made.
- Code and accepted artifacts outrank docs.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: wait for capacity.
- Never invent a measurement, never weaken a criterion to pass, and never
  wait for a human.

## Exhaustion policy

`report_done`.
- Once every criterion has evidence and the comparison is on the page, work
  the long-term rung: a second round on each style, then mixes.
- Write R1 and claim done when the second round is in, or when two rounds in
  a row on the weakest style fail to improve it.
- Two consecutive critic acceptances stop the run.
- If the stop arrives first, report how far each criterion got. Do not
  redefine success.

## Quality bar

- At every accepted commit that touches code, run:
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count.
- **A style is reported with:**
  - its accepted revision;
  - G1's numbers against leon I;
  - its renders from K1's cameras.
- **The critic looks at the pictures.** For every style claimed, it opens the
  newest hero and head close-up and checks that they show what the claim
  says: rounded corners where rounded is claimed, a round ear where round is
  claimed.
- **The critic checks numbers at their source:** the build's verdicts and the
  MJCF diff.

## Reconcile

- The scribe folds every five work iterations, or at three unfolded
  records:
  - impacts applied;
  - statuses set with evidence;
  - `STATE.md` rendered;
  - `ouroboros mem check` clean.
- Earlier runs' open claims stay open and untouched.
- Unattended roles never edit this charter.
