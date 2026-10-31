# DASHBOARD.md — The dashboard, Cadex's only UI

Verified against source: 2026-10-30. [Cadex-new]

This is the design specification for the dashboard: the pages `cadex app`
and `cadex review` serve (`cli/cadex_cli/review_server.py` and
`review_static/`, ADR-286), the second of Cadex's three parts (ADR-500) and
its only UI since the Blender shell was deleted (ADR-498). It replaced
`docs/REVIEW-DESIGN.md` (ADR-501). It is the
contract the pages are held to: the page follows the spec, and when the page
has to change, the spec changes in the same commit. Since ADR-725 no test
holds the page to it but the read-only rule (§18), the remote-viewing
defaults (§22) and the browser keys (`docs/CLI.md`); the rest is checked by
running the page. What the server *reads* — the routes, the permitted-paths
rule — is `docs/CLI.md`; this document is about what the pages show, how
they are laid out, typed and coloured, and why.

The dashboard stays light (charter A2): a standard-library Python server,
vanilla JS and the vendored three.js — no npm, no bundler, no build step,
no front-end framework. The project directory is the truth (A3): the page
reads it and writes nothing (ADR-537). The agent working the project -- any
agent, through the CLI or `cadex mcp` -- changes it, and the page follows.

**The pages are cut to the minimum (ADR-533).** On 2026-10-04 the owner had
every panel removed that watching and steering a design does not need, to be
added back one at a time as the need shows. What is left is two pages: the
index of projects and a project. The server's read routes are unchanged, so
every API the removed panels read — runs, telemetry, videos, evaluations,
exports, sections, drawings, documents — still answers (comments and notes
went with the owner channel, ADR-538), and
the CLI and the agent still use them; adding a panel back is page work only. The sections the cut emptied are gone from this file and
kept in its history; the ones that remain keep their numbers, so a `§`
reference elsewhere still lands. §7–§9, the measured ot6 record of the page
before and after the first spec, are in `docs/probes/ot6/DESIGN-RECORD.md`.

**The project page is the app (ADR-534).** The same day the owner asked for
the page to stop being a dashboard and be the app, in Blender's design
language: the screen is tiled by **areas**, each showing one **editor** —
the 3D viewport, Version (ADR-770), Status (ADR-572), Training (ADR-732),
the 2D viewport, the Outliner (ADR-676,
§25), Activations and Network (ADR-727, ADR-728, §27) and Settings
(ADR-728, §28) — and each area can be resized, moved, split, maximized or
closed (§12). There is a light theme
beside the dark one (§4), and the 3D viewport draws shaded by default or as
a wireframe diagram (§10; called hairline until ADR-602). Still no build step: `layout.js` tiles the
screen, `theme.js` picks the theme, and both are plain scripts.

**The settings are a menu bar (ADR-539).** File, Revisions and View sit in the status bar along the bottom (ADR-728) as dropdowns that open upwards. What has no place there, for now the heat colours, is the Settings editor (§28, ADR-728). The default screen is the 3D viewport over a strip of Version, beside a column of the Outliner over Status over Training (§12; ADR-676, ADR-732, ADR-770).

**The page is read-only (ADR-537).** The owner's interface is now an agent
of their choice -- Claude Code, Codex, Pi -- driving the engine through the
CLI and `cadex mcp`, with this page beside it as the view. The Chat editor,
the parameter sliders and the revision verdicts are gone, and the server
has no write route (§18).

## 1. Purpose

The app answers one question for one person: **what does the design look
like now?** The reader is the owner, at a desk or on a phone, watching what
the agent produced while it works; they steer it in the agent's own
interface and never model by hand (VISION's non-goals). The page writes
nothing (§18), on a server bound to 127.0.0.1 (§22).

- **The model is the subject.** The 3D viewport is the largest area in the
  default layout and the first tab on a phone; nothing is drawn over its
  model but its status lines at the bottom left (ADR-557) and, in its top
  right corner, the navigation gizmo (§5, ADR-726), which folds away
  (ADR-770). Which version it shows, and when in its rollout, is the
  **Version** editor's, a strip under it (ADR-770; its header's from ADR-728).
- **The layout is the reader's.** Every editor lives in an area the reader
  can move and size; the layout is kept in their browser, not the project.
- **Nothing that is not needed.** No identity block, no hashes in the
  chrome. The status bar says which project and which revision.

## 2. Hierarchy

**Home** (`/`, `projects.html`, ADR-605): the home of a viewer, not a
directory listing. A sticky top bar carries the name, the project count
(`#projects-count`), a filter (`#projects-filter`, kept in the URL as
`?q=`), **live** or **offline** (`#freshness`) and the light/dark toggle.
Below it, `#spotlight` puts the project that moved last (`active_at`) large:
its picture at 16:9 beside its name (`#spotlight-link`, `--fs-3`), its stage
chip (`#spotlight-stage`), its latest evaluation's verdict, a training
progress bar, a line saying what it is doing or what failed, its counts and
**Open project**; it is shown on the first page with no filter. Then
**Projects** (`#projects`), a grid of cards (`li[data-project][data-stage]`,
each one link to `p/<name>/`), at least 232 px wide, as many to a row as fit:
the picture at 4:3, the name and how long ago it moved, the stage chip and the
verdict chip (`pass 8/8` in `--ok`, `fail 0/8` in `--bad`), a progress bar
while it trains, the line, and its revisions, runs and evaluations. A card's
stage is read from the run written last, by its `run.json` or else its
trainer's `progress.json`; a directory under `runs/` with neither is never the
card's run, as it is never the page's (ADR-851). The
picture is the presentation hero, else the newest passing evaluation's hero,
else the first frame of the newest film sheet (the sheet cropped to its
first tile, its time label cut), else the concept sheet, else a drawn
placeholder (an isometric box on a dot grid); renders sit on the dark floor
in both themes, so a picture's mat is `#141414` whatever the theme. 24 to a
page, most recently active first and then by name; **Newer** and **Older**
page through them (`#pager`, `?page=N`). It polls `api/projects` every 5 s,
and a card is rebuilt only when what it shows changed.

**Project** (`p/<name>/` under the index, or the root under `cadex review`; every URL it uses is relative to it, ADR-551): the screen over
the status bar (`#screen[data-mode]`), which `layout.js` tiles with areas
(`.area[data-area][data-editor]`, §12). Each editor's markup is parked in
`#editor-shelf`; an area takes its `.editor-tools` into its header and its
`.editor-body` below.

| Editor | `data-editor` | Element hooks (stable) | What it is for |
|---|---|---|---|
| **Status bar** | — | `#top`, `#home`, `#project-name`, `#accepted-line`, `#freshness[data-state]`, `#theme-toggle` | Along the bottom of the window, as Blender has it (ADR-728; the top bar before it, and still `#top`): a link home (hidden under `cadex review`), the project's name, the accepted revision's ordinal and date, the menu bar, **live** or **offline**, and a light/dark toggle. |
| **3D viewport** | `view3d` | `#view3d-style button[data-style]`, `#view3d-look`, `#model-fit`, `#play-follow[aria-pressed]`, `#view3d-trail`, `#view3d-primitives[aria-pressed]`, `#view3d-heat[aria-pressed]`, `#model[data-gizmo]`, `#model-status[data-state]`, `#viewer`, `#view3d-gizmo[data-view]`, `#view3d-gizmo-toggle[aria-pressed]`, `.gizmo-end[data-end]` | The accepted model or a run's, shaded or wireframe, under the header's lighting menu (§10); orbit, pan (shift- or middle-drag, two fingers) and zoom by pointer or touch (§5); **Fit**. `#model-status` says why no model is drawn (loading, missing with its reason in `--warn`, an error in `--bad`), and for a trainer's run what its model is (`data-tier`, ADR-838): `concept: its primitives are the design`, or `training model: CAD on its bodies, primitives outlined` when the run was cut from the accepted CAD export, the accepted parts drawn solid on each body and the trained primitives as `#35c4ff` outlines over them. It sits at the bottom left of the view on an opaque `--surface`, because the floor is dark in both themes (ADR-557). Which model is shown, its scrubbers and the rollout's timeline are the **Version** editor's (ADR-770; below). **Follow** and the **Trail** menu sit in the header after Fit, each the viewport's own. **Follow** (`#play-follow`, ADR-693, remembered as `cadex.follow`) makes the view travel with the design while a rollout or a checkpoint plays: the camera's target and the key light with its shadow move with the design's centre (the mean of its shown solids' box centres, each carried by its pose, Hann-smoothed over about half a second either way and narrowed symmetrically at the ends so it never trails), by that centre's motion, so the person's orbit, zoom and pan stay theirs and a running machine can be watched close up. Turning it on, or a new rollout while it is on, puts the target on the design. **Trail** (`#view3d-trail`, ADR-770, the first viewport's remembered as `cadex.trail`; off by default) draws where the design has been on the rollout shown, up to the moment shown, on the ground under it (the course's own surface where there is one, else the mat): **line**, **dashed**, **dots** (a disc each fifth of the design's width travelled) and a broad translucent **ribbon** follow the design's centre as Follow tracks it; **footprints** leaves a dot where each foot came down: a solid touches down when its lowest point comes within 1.5% of the design's height (at least 2 mm) of the ground and lifts off at 2.5 times that, each stance marks its middle frame's contact patch, and of the solids that touch together (a paw, its toes, its shin: within a print's width and a quarter second) the one on the ground most often keeps the footfall. Its colour is Settings' (§28): white by default, or a ramp by age. The trail is beside the model: it sizes, picks and outlines nothing, and the wireframe diagram and occlusion leave it out. **Go-to-point targets** (ADR-839): a rollout whose playback carries `goto` (a `training/cadex_goto.py` episode) draws its points on the ground under the design, each coloured by its commanded speed over the episode's own range (slowest `#4fd1a5`, then `#ffd166`, fastest `#ff7a45`): the point lit at the moment shown at full strength with a beacon over it, the ones to come dim, the ones done faint. A point's disc is the 0.15 m hold zone and its outer line the 0.3 m reach; while a point with a hold is held, a ring between them fills clockwise from the top as the hold runs. `#play-goto`, beside the clock, says the lit point (`point 2/8 · walk 0.59 m/s · hold 3.0 s 50%`, then `all 8 points done`). A gate course's gates (ADR-902) are each one circle of the gate's own `radius_m`, all one colour (`#f2f2ea`), each `speed_mps` the speed made on its leg (`cadex_goto.py race`, ADR-955), and `#play-goto` reads `gate 3/12 · last leg 0.84 m/s`, then `all 12 gates`. Like the trail it sizes, picks and outlines nothing. **Primitives** (`#view3d-primitives`, ADR-901), offered only while the model shown is a training model with CAD on its bodies, outlines the primitives its bodies trained as over that CAD (on by default, as ADR-838 drew them) or hides them so the CAD reads alone; each viewport's own, the first's remembered as `cadex.primitives`, and kept across model loads. **Activations** (`#view3d-heat`, ADR-770) paints the rollout's motor loads on the parts they move in this viewport (§27). **The axes** fold away (ADR-770): a caret under the gizmo, shown while the pointer is over the view, hides it (`#model[data-gizmo="off"]`), and a caret tab in the view's top right brings it back; each viewport's own, the first's remembered as `cadex.gizmo`. **Checkpoints** (ADR-545): while a run is the model shown, each of its checkpoints the engine rolled out (ADR-544), or the trainer rolled out beside it (`<out>.<tag>.rollout-trace.json` in a hand-started run's seed directory, ADR-851), is a stop in the **stop picker** (ADR-901; a dropdown before it, ADR-733, and a scrubber before that), newest first, each named by its iteration and reward per step, with the run's own rollout as the newest once it has one; a page left open adds that `final policy` stop on the poll after the walk lands its rollout, with no reload (ADR-554). The newest loops, its option marked `newest`; the stage's run lists them from `/api/project`'s `stage.checkpoints`, any other from `/api/checkpoints/<run>`, read when it is picked and every 15 s while it runs or has rollouts pending (ADR-790), and a run that ended since ADR-790 has its final policy as its newest numbered stop; iterations are one-based, as Training counts; `#checkpoints` has `data-follow="true"` while it follows new ones. Picking an older one keeps it while newer ones land; moving back to the newest end follows again. A failed rollout plays nothing, leaves the model at rest and says why in `#checkpoint-status` in `--bad`; the same line counts checkpoints still rolling out. A hand-started run's checkpoints with no trace (trained before ADR-851, or with `--view-seconds 0`) are never pending: `/api/checkpoints/<run>`'s `reason` counts them. While that run is training the viewport turns to it on its own, unless a source was picked by hand this visit. **Films** (ADR-901): the whole episodes something other than the run's trainer filmed under it (a project's judge's `judge-export/best/s3/view/trace.json`, read from `/api/films/<run>` when the run is picked and every 30 s after) are stops beside its checkpoints, played on the run's own model from `/api/playback/film/<run>/<film>`; a go-to-point episode draws its points and fills `#play-goto` as any other does. A picked film loops and stays picked as checkpoints land, until a checkpoint is picked or the run no longer lists it (`#checkpoints[data-follow="false"]` meanwhile, and its label reads **Film**); a run with films and no checkpoint keeps its own rollout as a stop. **The stop picker** (ADR-901): `#checkpoint-pick` is a button naming the stop shown with its length and points; it opens `#checkpoint-menu`, a popover over the area that would clip it, on the side of the button with more room and at most 440 px wide inside a 16 px gutter, so a phone takes it whole. It holds a filter, `#checkpoint-filter`, and `#checkpoint-list`, a listbox: the checkpoints newest first under **Checkpoints**, then each directory's films under its path with their count (`judge-export/best · 10`, then `s0`…`s9` in natural order), each option (`[role="option"][data-stop][aria-selected]`, `data-stop` a checkpoint's stem, `final`, or `film:<film>`) with its length and, for a go-to-point episode, its points, in `--ink-2`; the stop shown is in `--select`, a failed one in `--bad`. Typing filters: every word must appear in the stop's group and name, a group with nothing left folds, and `#checkpoint-empty` says when nothing matches. The arrow keys, or a letter, on the button open it (the letter starts the filter); in it, ↑ ↓ and Page Up/Down move the active option (`.active`, the filter's `aria-activedescendant`), Enter or a click picks and closes it, back on the button, as Escape does; a click outside closes it too. **Gait references** (ADR-703), a source group offered for each accepted task whose bundle carries a reference (`/api/project`'s `references`, `reference:<task>`): the accepted model posed by the task's generated stride, from `/api/playback/reference/<task>`, which repeats the one stride a stride further on each time for about 4 s. It loops from the start as soon as it is in, on the same timeline and with the same Follow. It is the motion the task asks for, not one simulated, so the owner judges the intended gait before anything trains. **Revision history** (ADR-547), a source offered once anything is accepted: each stored revision is a stop on `#revision-timeline`, oldest to newest, drawn from the model kept when it was accepted (ADR-546). The newest is shown and followed (`data-follow="true"`); picking an older one keeps it, and the newest end follows again. Unchanged parts are drawn in `--paper-ink`, parts whose digest changed against the revision before in `--info`, and that previous revision is a ghost in `--ink-2` at 22% opacity wherever it differs (a part kept as it was, where it was, is not drawn twice; a wireframe diagram leaves the ghost out). `#revision-status` names the changed parts and the revision compared against. A revision whose model was not kept (`data-state="missing"`) draws nothing and says why in `--warn`; the revision after it draws with no ghost and says there is nothing to compare with. |
| **Version** | `version` | `#editor-version`, `#view3d-source`, `#version`, `#revision-timeline[data-follow][data-state][data-ordinal]`, `#revision-pick`, `#revision-label`, `#checkpoints[data-follow][data-state]`, `#checkpoint-pick[aria-expanded]`, `#checkpoint-menu`, `#checkpoint-filter`, `#checkpoint-list [role="option"][data-stop][aria-selected]`, `#checkpoint-empty`, `#playback`, `#play-toggle`, `#play-time`, `#play-clock`, `#revision-status`, `#checkpoint-status` | Which version of the design every 3D viewport shows, and when in its rollout (ADR-770), once for all of them, as Blender keeps one timeline under its viewports: the source menu in the header (the accepted model, the revision history, a run, a gait reference), and in the body the revision scrubber or the run's stop picker (its checkpoints and films, ADR-901), the rollout's timeline (**Play**, the time scrubber, the clock) and their notes (`#revision-status`, `#checkpoint-status`). With nothing to play it says so. They were the 3D viewport's (the pickers in its header, ADR-728; the timeline across its foot, ADR-733) until ADR-770; what each control does is the 3D viewport's row above. |
| **Status** | `status` | `#editor-status`, `#status-stage[data-stage]`, `#status[data-stage]`, `#status-line`, `#status-progress`, `#status-run`, `#status-panel`, `#status-warning`, `#status-activity[data-state]`, `#status-activity-line`, `#status-activity-log`, `#status-activity-list` | Drawn by `status.js` (ADR-606). What the project is doing (ADR-542, the first panel back after ADR-533; how training is going was here until ADR-732), an editor of its own since ADR-572, beside the 3D viewport rather than over its model: a stage chip in the area's header — **idle**, **designing** (a revision accepted, or the newest call in the activity log made, in the last 10 min, its line `the agent's <tool> call` when nothing was accepted; a newest call that trained or evaluated does not count, ADR-851), **training** (iteration of total and ETA), **evaluating**, **stopped** in `--warn` (the newest run was stopped on request, through `train_stop` or a walk's Ctrl-C or `SIGTERM`; its line is the stop's reason, ADR-559; a run stopped before ADR-559, whose record says `failed` but whose supervisor's `training-status.json` says `stopped`, reads stopped too, ADR-574) or **failed** (a run that failed, or a walk or supervisor killed mid-run whose record still says `running` under a lock nobody holds, ADR-559) — and, in its body, one line (`--fs-1`) with a progress bar while training, the run it reads (named when there are several), which Training charts (ADR-732) And the trainer's collapse `warning` in `--warn` (or, while the run is still recorded as live, that its telemetry has been quiet for over 30 s; never under a run whose record has ended, ADR-574). Read from `/api/project`'s `stage` on the page's own poll. **The agent's activity** (ADR-550), from `/api/project`'s `activity` (ADR-549): one mono line under the run with the newest `cadex mcp` call or `cadex` command on the project (`cadex script`, `cadex clearance`, …, ADR-836), its argument summary and how long ago (`data-state="active"`), or `failed: <detail>` in `--bad` (`"error"`); a call still in flight reads `<tool> <args> · running <how long>` in `--info` (`"running"`, ADR-553), never idle, and an in-flight `evaluate` (or `cadex evaluate`, ADR-851) makes the stage **evaluating**, its line `the agent's evaluate call is running` for the whole call, never an evaluation directory's id (ADR-555); a call whose server died before it returned reads `did not return` in `--bad`; once no call has returned for 5 min and none is in flight it reads `agent idle · last call <tool> <ago>` in `--ink-2` (`"idle"`); with no log it shows the reason (`"none"`). `recent calls` opens the newest five, each with its UTC clock time, failures in `--bad`. It never collapses: an area is sized by its edges, and on a phone it is a tab. With no runs it is one line, `idle`. **Project** (ADR-607): when the project has a `status.html`, the agent's own panel shows in `#status-panel` (§23) under the stage line and the activity, filling the rest of the area (a Training/Project switch until ADR-732). |
| **Training** | `training` | `#editor-training`, `#training-run`, `#training-cards-button`, `#training-cards-menu`, `#training-cards-reset`, `#training[data-max]`, `#training-head`, `#training-line`, `#training-progress[data-live]`, `#training-board[data-arranging]`, `#training-pinned[data-empty]`, `#training-cards`, `.card[data-card][data-off][data-max]`, `#training-reward-now`, `#training-best`, `#training-loss-now`, `#training-episode-now`, `#training-std-now`, `#training-eta`, `#training-reward`, `#training-loss`, `#training-episode`, `#training-std`, `#training-eval`, `#training-eval-verdict`, `#training-eval-list`, `#training-runs`, `#training-runs-body` | Drawn by `status.js` from the same poll; an editor of its own since ADR-732, in Status from ADR-606 until then. The run the Version editor's source picks, else the run Status reads (ADR-790): a picked run that is not Status's is read whole from `api/run/<run>` and again when its record moves, its charts from its curves. It is named in the area's header (`run <name>`, `run <name> · <state>` when picked, or `no runs`), and in its body: **the run's line and bar** (ADR-770), Status's own while it trains (`iteration 12 / 100 · ETA 32 min` over the `--info` bar with its sheen), and once it has ended how far it got and how it ended on a bar in `--ink-2` that no longer moves; **cards** (ADR-770), one grid of 104 px columns 8 px apart holding the stats and the charts alike: a card's title drags it to a new place among the others (onto the strip at the top to pin it, where it stays while the rest scrolls; a dashed **Drop here to pin** shows there while dragging if nothing is pinned), its corner resizes it in whole columns across and pixels down (a stat 48 px at least, its number growing with it; a chart's plot 80 px at least), and its tools, top right on hover, pin it, hide it, and, on a chart, **maximize** it to fill the editor until it is pressed again or Escape; the header's **Cards** menu (a popover, `Cards · 2 hidden` when any are) shows a hidden card again and **Reset cards** returns the default — six stats, each one column and 64 px, then the four charts, three columns and a 132 px plot; the arrangement is this browser's (`cadex.training.cards`). The cards are: stats for reward per step, the best reward and its iteration, loss, episode length, action std and (while training) ETA; **four charts**, one measure each on its own axes and never two on one (ADR-606): reward per step, loss, episode length and action std by iteration (one-based), from `stage.training.spark`, the x axis running to the run's total while it trains, so the unrun part shows, and to the last iteration it reached once it has ended; y ticks with a `--rule` grid, x ticks, the samples as a faint 1 px `--accent` line under a 2 px `--accent` line of their rolling mean (a window of 1/12 of the samples, so a batch whose episodes end together reads as its trend), on reward the best iteration as a `--ok` dot on a dashed rule labelled `best <value> @ <iteration>` and each reported checkpoint as a tick on the axis; hover puts a crosshair and the iteration and value on the nearest sample; a measure the run did not report says so; the charts redraw at their card's size when the area or the card resizes; **Latest evaluation**, its verdict chip, task, policy, age and how the episodes ended, then a row per predicate (its bound, a seeds-passed meter in `--ok`/`--warn`/`--bad`, its median) from `api/evaluation/<name>`, read once per evaluation; **Runs**, newest first (at most 40; a directory under `runs/` with no `run.json` whose trainer wrote a `progress.json`, under `train/`, a seed's directory or a stage's seed, is a run too, its status the trainer's own and its model the trainer's `view/`, ADR-835, ADR-837): name, label and the agent's stated reason (ellipsized), iterations, best reward, its change from the previous run with a best (`--ok` up, `--bad` down), the outcome chip (done, stopped, failed, running) and the verdict of its evaluation (one of its own policy's by digest, else the first evaluation made between it and the next run); the run Status reads is shaded; below 420 px the iterations column goes. With no runs its body is empty. |
| **2D viewport** | `view2d` | `#view2d-source`, `#view2d-fit`, `#sheet-stage[data-kind]`, `#sheet-empty` | The project's drawings and presentation images (pan, zoom, double-click to fit), its documents (markdown, drawn as text only), each evaluation's film, newest first (a passed evaluation's hero and print-bed hero first, as images, ADR-570; then its shove video, `· shoves`, with the pushes and the ending captioned below it in `--ink-2` mono, ADR-571; then each filmed seed's rollout video, which plays in place with controls, muted and looping, and its filmstrip and detail sheets as images; ADR-541), and each run's training curves (reward, loss, episode length, action std) as plots. |
| **Outliner** | `outliner` | `#editor-outliner`, `#outliner`, `#outliner-filter`, `#outliner-group`, `#outliner-show-all`, `#outliner-tree`, `#outliner-summary` | Every part of the model the 3D viewport shows, grouped by type or role, to show, hide, isolate, select and frame (§25, ADR-676). |
| **Activations** | `activations` | `#editor-activations`, `#activations-views button[data-view]`, `#activations[data-match][data-gauges][data-bars][data-drivers]`, `#activations-status[data-state]`, `#activations-motors`, `#activations-bars`, `#activations-detail` | What the motors are doing at the moment the 3D viewport's rollout shows (§27, ADR-727): a gauge per motor, the same as a bar a row, the inputs that drive the picked motor, each view on its own switch, and **Show in viewport**, which paints each motor's parts by its load. |
| **Network** | `network` | `#editor-network`, `#network-views button[data-view]`, `#network[data-layers][data-paths][data-max]`, `#network-status[data-state]`, `#network-layers`, `#network-paths`, `.net-view[data-view] .view-max[data-max][aria-pressed]` | The rollout's policy network (§27, ADR-728): its layers as a heat map, and the strongest paths through them to the picked motor, each on its own switch. Each view's corner button (shown on hover) maximizes it to fill the editor, the other view and the status line stepping aside, and restores it (ADR-770); each panel's own, for the page's life. |
| **Pose** | `pose` | `#editor-pose`, `#pose-on[aria-pressed]`, `#pose-rest`, `#pose-sweep[aria-pressed]`, `#pose-mirror`, `#pose-status[data-state]`, `#pose-saved`, `#pose-name`, `#pose-copy`, `#pose-download`, `#pose-joints .pose-joint[data-joint][data-stop][data-picked]` | The model moved by its joints through their ranges, as view state (§29, ADR-969); a pose leaves the page only as JSON for `cadex pose save`. |
| **Settings** | `settings` | `#editor-settings`, `#settings`, `#settings-heat-preset`, `#settings-heat-count button[data-count]`, `#settings-heat-low`, `#settings-heat-mid`, `#settings-heat-high`, `#settings-heat-preview`, `#settings-heat-reset` | This browser's preferences (§28, ADR-728): for now the heat colours the Activations and Network editors and Show in viewport paint in. |
| **Menu bar** | — | `#menubar`; `#file-panel` (`#project-select`, `#project-open`, `#project-all`); `#revision-panel` (`#revision-list li[data-revision][data-ordinal][data-current]`, `#revision-empty`); `#view-panel` (`#theme-choice`, `#style-choice`, `#look-choice`, `#occlusion`, `#detail`, `#mesh-lines`, `#mesh-strength`, `#reflections`, `#layout-reset`, `#layout-presets button[data-preset]`) | File, Revisions and View in the status bar, each a `<details class="menu">` dropdown opening upwards (ADR-539, ADR-728): open another project; the revision trail, read-only (§18), where a row (`data-retained` says whether its model was kept) opens that revision on the 3D viewport's revision timeline — a view, never a restore; the theme, the render style, the lighting, ambient occlusion and surface detail, the wireframe's mesh lines (on or off, and a strength slider) and the shaded solids' reflections (a strength slider), each this browser's own (§10), and the layout: Reset, and eight one-click presets (§12). One opens at a time; a click outside or Escape closes it, and with one open, hovering another opens that one. On a phone the dropdown spans the screen between the gutters. |

The element ids and `data-*` attributes above are the page's stable hooks:
keep them when the page changes, and change this table with them. No test
checks them since ADR-725.

## 3. Type scale

One family, one scale, one line height.

| Token | Size | Weight | Use |
|---|---|---|---|
| `--fs-0` | 12 px | 400 | captions, chips, monospace identities, table footers |
| `--fs-1` | 14 px | 400 | body, table cells, controls; section headings (`h2`) at 600 |
| `--fs-2` | 17 px | 600 | the page title (`h1`) in the status bar (the top bar on the home page) |
| `--fs-3` | 22 px | 600 | the home page's spotlight name (`#spotlight-name`, ADR-605) and a document's `#` heading in the 2D viewport |

The bar's title is `--fs-2` at 600 and a menu name `--fs-1` at
400; the scale does not change with the width.

- **Family**: `--font: system-ui, "Segoe UI", "Helvetica Neue", Arial, sans-serif`;
  identities in `--mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace`
  at `--fs-0`. No web font is loaded: the page must render on a private network
  with no outbound fetch.
- **Line height** 1.45 throughout. Numbers use `font-variant-numeric:
  tabular-nums` so stat rows and tables align.
- **Headings are sentence case, never uppercase**, and carry no number.
- The scale is the same at both breakpoints. Phone readability comes from
  layout (§6), not from shrinking the type: nothing on the page is smaller than
  12 px at any width, and the viewport meta stays `width=device-width,
  initial-scale=1` so the phone renders CSS pixels 1:1 and never zooms out to
  fit.

## 4. Palette

**Dark by default, light on request (ADR-534).** The chrome tokens below are
the dark theme, chosen so that the page background *is* the scene background:
the viewport is a window onto the same near-black place the videos are
captured in. The environment module keeps its one dark palette (ADR-331):
the shaded viewport and every capture stay in it whatever the theme, as a
Blender viewport keeps its own colour under a light interface.

The light theme overrides the same token names under
`:root[data-theme="light"]`: `--bg` #cfcfcf, `--surface` #f4f4f4,
`--surface-2` #e6e6e6, `--surface-3` #d9d9d9, `--rule` #c4c4c4,
`--rule-strong` #a8a8a8, `--ink` #1c1c1c, `--ink-2` #5c5c5c, `--accent`
#262626, `--ok` #18794a, `--warn` #8a6100, `--bad` #b42318, `--info`
#0b7285. Two tokens beyond the table follow the theme too: `--select` (a
pressed button, the drop hint) and `--paper` / `--paper-ink` (the wireframe
diagram, §10). `theme.js` sets `data-theme` before the first paint from the
browser's stored choice — dark, light or the system's — and every page
loads it.

The base is the greyscale of the `neural-whoop` reference studio (its `:root`
dark set) and of the one `PALETTE` in
`cli/cadex_cli/review_static/environment.js`, which carries the reference's
dark tile and scene values and nothing else (ADR-331).

| Token | Value | Used for | Equals |
|---|---|---|---|
| `--bg` | `#141414` | page background | `PALETTE.scene.bg` (`0x141414`) — chrome and viewport share it |
| `--surface` | `#1b1b1b` | an area's body | reference `--panel` |
| `--surface-2` | `#242424` | controls, table heads, code blocks, curve backgrounds | reference `--panel-2`; between the mat's tiles `#1c1c1c` / `#232323` and its major line |
| `--surface-3` | `#2c2c2c` | hover, the selected run | reference `--panel-3` |
| `--rule` | `#3a3a3a` | every border and heading rule | reference `--line`; also the mat's major grid line |
| `--rule-strong` | `#4a4a4a` | focus and the selected run's border | reference `--line-strong` |
| `--ink` | `#ededed` | body text | reference `--fg` |
| `--ink-2` | `#9a9a9a` | captions, labels, secondary text | reference `--muted` |
| `--accent` | `#dcdcdc` | links, the curve stroke, the current-run mark | reference `--accent`. Greyscale: colour is reserved for status. |
| `--ok` | `#8be0b0` | ok / completed / live / retained | reference `--issue-ok` |
| `--warn` | `#ffe08a` | pending / stale / unknown / truncated | reference `--far-fg` |
| `--bad` | `#ff9d9d` | failed / missing / refused / error | reference `--stop-fg` |
| `--info` | `#6ff0f0` | the *current* relation chip and the training-in-progress state | reference `--go-fg` |

Status chips use the status colour as ink on a tinted `--surface-2`
(`color-mix(in srgb, <status> 18%, var(--surface-2))`), never as a solid fill,
so a page full of chips stays quiet. A historical run's chip is `--ink-2` on
`--surface-2`: history is neutral, not a warning. The component swatches in the
model list keep the eight-colour `PALETTE` of `review_scene.js`, because those
colours identify parts and appear in the videos too.

Contrast: `--ink` on `--bg` is 15.7:1, `--ink-2` on `--surface` is 6.1:1,
and every status colour on `--surface-2` is at least 7.8:1, so each text
token clears WCAG AA at `--fs-0`.

The stylesheet declares these colour tokens on `:root` (beside `--select`,
`--paper`, `--paper-ink` and the type, spacing and shape tokens). A design
test pinned the table to the environment module's dark scene background and
read every token back from the rendered page until ADR-725; now a change to
one changes the other two by hand. The chrome is at these values (ot6 record), and
so is the viewport (§10): the environment module has one palette, the videos
are captured in the same scene, and the viewport's sky *is* `--bg`.

## 5. Spacing and shape

A 4 px base: `--s1` 4, `--s2` 8, `--s3` 12, `--s4` 16, `--s5` 24, `--s6` 32.

- Page gutter `--s5` at desk, `--s3` on phone (`--s4` on the home page,
  ADR-605). Sections are separated by a `--rule` hairline, not boxed in
  cards; the home page's projects are the exception, a card each with a
  `--radius` corner and a `--rule` border that turns `--rule-strong` on
  hover.
- **Shape**: `--radius-sm` 8 px on controls, `--bw` 1.5 px borders.
- **Controls**: minimum 40 × 40 px hit area on touch (`@media (pointer:
  coarse)`), 32 px on desk; `--surface-2` fill, `--rule` border, `--surface-3`
  on hover, `--rule-strong` on focus. No native chrome on buttons.
- **Scrubbers** (the revision row and the playback row in the Version
  editor, ADR-770): a slider never gets narrower than `--scrub`,
  160 px, and is a `--tool` touch target tall. Where its label does not fit
  beside it, it wraps under it (ADR-556), cut short with an ellipsis if it
  is longer than the row (its full text in its title); a row that does not
  fit beside the other tools takes a header row of its own. The rows read the same
  tokens in both themes.
- **Areas** have a 6 px radius (`--radius-area`) and a 4 px gap (`--gap`)
  between them on `--bg`; an area's header is 32 px on `--surface-2`, its
  controls 24 px; tools that do not fit on one row wrap onto another,
  32 px more each, rather than being clipped.
- **The viewport** fills its area's body, with `touch-action: none`
  so a one-finger drag orbits instead of scrolling the page. The canvas
  backing store follows the box, so the model is never stretched. **Orbit
  is by pointer events** (ADR-330): one pointer orbits, two fingers
  pinch-zoom, the wheel zooms, and the canvas captures the pointer so a drag
  that leaves it still orbits. **Pan** (ADR-561): shift-drag or middle-drag
  slides the view so the point under the pointer follows it; on touch, two
  fingers dragged together pan by their midpoint while their spread zooms.
  **Fit** restores the framing, target included, framing the
  design's bounding sphere; a part the engine calls world geometry (a task
  floor, `world=True`) is drawn but sizes nothing (ADR-525).
- **The navigation gizmo** (ADR-726, `gizmo.js`), after Blender's: the
  model's X, Y and Z axes as the camera sees them, 88 px in the viewport's
  top right corner, turning as it orbits. A positive end is a ball lettered
  in `#141414` on a stem, a negative end a ring; nearer ends are drawn over
  farther ones, and a faint disc shows behind it on hover. It is greyscale
  (ADR-728; Blender's red, green and blue until then): balls `#c9c9c9`, stems
  and rings `#8f8f8f` on `#2a2a2a`, the same in both themes because the
  viewport is dark in both; the letters say which axis is which.
  A click on an end glides the camera round to look along that axis (+X
  Right, −Y Front, +Z Top with Y up, and so on), keeping its target and
  distance; a click on the view already shown (`data-view`) turns to the
  opposite one. The glide is eased over about 0.4 s and instant under
  `prefers-reduced-motion`; a press or wheel on the canvas takes the camera
  back mid-glide. It works while a rollout plays and the view follows it
  (ADR-729): Follow moves the target, the gizmo the direction. A snap is a
  press and a release on the same end, and the ends are restacked only when
  their depth order changes, so a view redrawn every frame keeps an end
  under the pointer. Fit stays instant. An orbit that starts from a snapped
  top or bottom view keeps its pitch rather than jumping back to the
  usual ±1.5 rad limit.
  It folds away (ADR-770), as an area's header does: a 22 × 14 px caret
  tab under it on `--surface-2`, shown while the pointer is over the view,
  hides it; folded, the tab sits in the view's top right, clear of a
  collapsed header's, and brings it back.
- **Motion** (ADR-726) is small and says something is alive: the **live**
  word in `#freshness` carries a `currentColor` dot that breathes on a
  2.4 s cycle; a progress bar (Status, the home page) has a sheen running
  along it; a home page picture pushes in to 104 % over 0.6 s under the
  pointer. All of it stops under `prefers-reduced-motion`.

## 6. Breakpoints

One.

| Range | Layout |
|---|---|
| **≥ 700 px** (desk; 1400 is the reference width) | The screen, tiled by areas (§12), over a 32 px status bar (ADR-728). The page never scrolls; each editor scrolls on its own. |
| **< 700 px** (phone; 400 × 850 is the reference size) | One editor fills the screen, the 3D viewport first, and a tab bar at the bottom picks it: **3D**, **Status**, **Training**, **2D**, **Parts** (the Outliner), **Motors** (Activations), **Network** and **Settings**, each by its `data-short`; the bar scrolls sideways when they do not fit. **Version** has no tab: the 3D tab carries it under the viewport, as tall as its controls and at most 40% of the screen (ADR-770), so a rollout is picked and played beside the model it moves. `--s3` gutters below 600 px. |

**Touch** (ADR-770). Where nothing hovers (`(hover: none)`), what a pointer
would reveal on hover stays shown: a chart card's tools and every card's
resize corner (20 px), the axes caret (32 × 20 px) and a Network view's
maximize. A stat card is too narrow for its tools beside its title, so a tap
on it shows them over its top right, and a tap elsewhere puts them away. A
card's title takes a one-finger drag rather than scrolling the editor
(`touch-action: none`). Checked at 390 × 844 under touch emulation on
`cat-bound`: no horizontal overflow; the 3D tab showing the viewport over
Version with its checkpoint and Play row; the axes caret, a stat's tools, a
chart's maximize and a Network view's maximize each worked by a tap, and a
card moved by a touch drag.

The home page is a grid of cards at most 1440 px wide, one column below
600 px with 16 px gutters; its spotlight stacks its picture over its text
below 800 px.

Invariants at every width, checked on the rendered page at 1400 × 900 and
at 400 × 850 with touch emulation (by a design test until ADR-725):

1. **No horizontal page overflow**: `document.documentElement.scrollWidth <=
   innerWidth`, achieved by `min-width: 0` and fixed table layout, never by
   `overflow-x: hidden` on the body.
2. **The layout viewport is the device width**: `innerWidth === 400` at phone
   size. The ot6 record shows what happens when it is not.
3. **The screen fills the window**: from the top edge down to the status bar, and the
   page does not scroll. At desk the default layout's three areas, the 3D
   viewport and the Outliner over Status, tile it without overlapping, as
   any split layout's do; on a phone the one area is the 3D viewport and the
   canvas is the full `innerWidth`.
4. **The palette tokens of §4 are the computed values** on the rendered page,
   in the default dark theme; the light theme survives a reload.
5. **Type never drops below 12 px**, and `h1`/`h2`/body compute to §3.

## 7–9. The ot6 before/after record

The measured record of the page before and after the first spec (ot6,
2026-09) is frozen evidence, kept in
[`probes/ot6/DESIGN-RECORD.md`](probes/ot6/DESIGN-RECORD.md).

## 10. The viewport: dark only, shared with the capture

**Render styles (ADR-534, ADR-602).** The 3D viewport draws **shaded** by
default — the lit stage below, the one every capture uses — or
**wireframe** (called **hairline** until ADR-602; a stored `hairline` choice
opens as wireframe and is rewritten): a diagram of silhouettes and creases
in `--paper-ink` on flat `--paper`, with no floor, shadow or fog. The bold
lines are one screen-space pass in `review_scene.js` (`setStyle`): the
solids' view normals (each facet's own, so smooth shading never softens a
crease) and depth are drawn offscreen at twice the canvas's resolution (at
most 16 Mpx), ink goes wherever either jumps between neighbouring pixels —
depth for silhouettes, inked on the nearer side only, and a normal turn of
more than about 37° for creases — with a hard threshold, and the canvas takes
the mean of each 2×2 block, so a line is one crisp pixel with its
stair-steps smoothed. A tessellated fillet, whose facets turn by less, stays
clean of ink.

**Mesh lines (ADR-602).** Under the bold lines the wireframe can draw a soft
layer of the tessellation itself: every edge where two facets turn by more
than 2° (`MESH_LINES.angle`), so a curved face shows its facets and a flat
one stays clean, drawn over a depth-only prepass of the solids so a line
behind a solid is hidden, and mixed into the paper at a **strength** of the
ink (default 0.12, 0–1). They are on by default; View → **Mesh lines** turns
them off and its slider sets the strength (`setMeshLines`). The edges are
built the first time they are drawn and kept with the solid.

**Materials (ADR-601, ADR-676).** A shaded solid is a physical material over
its role colour (the role colours are unchanged), lit by the look's room,
key and fill (below). Its normals are crease-angle normals: at each
vertex the facets within 40° of each other (the engine's `CREASE_DEGREES`)
are averaged, weighted by their corner angles, so a fillet, a bore or a ball
reads smooth and an edge that turns further stays crisp. The finish comes
from the manifest's `finish` (`printed`, `purchased`, `hardware`, `board`;
without one, `purchased` when the supplier says so, else `printed`):
printed plastic a satin roughness 0.46; purchased bodies a satin plastic
(0.45) with a faint clearcoat; hardware metal by catalog family — bolts,
screws, nuts and standoffs black oxide, washers, bearings, bushings, shafts
and dowels bright steel, heat-set inserts brass; boards a satin solder mask
(`#1f6b3c` when the part has no colour). The plastics take 0.9 of the room
(ADR-601 had 0.4, with a hemisphere light flooding every face alike; that
flood was most of why a part looked flat), the metals all of it. A board
whose manifest carries its
own `board` geometry (the chip's box and the pads' centres and diameters, mm,
in the mesh's frame) is coloured facet by facet: a facet wholly in the
chip's box near-black, one wholly within a pad's radius plus 0.6 mm (across
the board's face) tin, the rest the mask; a facet is coloured whole, so a
long one never smears. The floor takes no reflection. View →
**Reflections** scales every finish's reflection 0–2× (default 1×,
`setReflections`); under a matcap it has nothing to scale and is disabled.

**Looks (ADR-676).** The header's **Lighting** menu (and View → Lighting)
picks how the solids take light, after Blender's viewport shading
(`shading.js`, `setLook`):

- four **lighting setups** — **Studio** (the default, and every capture's),
  **Softbox** (a large overhead panel and bright walls: low contrast, soft
  shadow), **Dramatic** (a dark room, a low warm key, a cool rim) and
  **Daylight** (a warm sun and a blue sky over a brown ground). Each is a
  procedural room of emissive panels prefiltered once into an environment
  map — seen in reflections and, as image-based light, in every face's
  ambient — plus a directional key (which casts the shadow) and a fill, a
  small flat hemisphere and bounce, a tone-mapping exposure, and a lift for
  the mat (it glows a little by its own texture) so it reads alike under
  every setup;
- two **matcaps** — **Aluminium** and **Clay**: every part in the one
  material, whatever its finish or role colour, from a sphere of that
  material rendered once in its own room into a half-float texture and
  looked up by the view-space normal. Shadows, the mat and occlusion are
  unchanged.

**Ambient occlusion (ADR-676).** Where two surfaces meet, or a part stands on
the mat, less of the room reaches it: after the frame is drawn, the solids'
view normals and their linear distance from the camera are drawn again, into a
float target at CSS resolution, and each sample's position is rebuilt along its
ray at that distance. (Rebuilt from the depth buffer instead, with the near plane
at a fraction of the camera's distance, the far floor stepped by metres and
striped the mat.) Sixteen samples
round each pixel within a radius of 0.12 of the design's size (never more
than 0.08 of the camera's distance, so a close-up does not darken half the
frame) measure how much of its hemisphere is closed, a depth-aware blur
smooths it, and the frame is multiplied by it. Past three times the camera's
distance it fades out. View →
**Ambient occlusion** turns it off (`setOcclusion`).

**Surface detail (ADR-676).** A CAD skin is perfectly smooth and one flat
value, which is much of what looks fake. Each finish's shader (patched in
`shading.js`, on the part's own frame so the detail moves with it) adds: on
printed parts, **layer lines** 0.2 mm apart across the part's own Z, a
0.035 mm bead each; a faint **grain** (a value noise a few microns high); a
slow **drift** in roughness (±0.16 printed, ±0.1–0.12 otherwise) and in
colour (±6 % printed, ±2–4 % otherwise). Every feature fades out before it
is too small to draw (where it spans less than a few pixels), so nothing
aliases or shimmers; from a fit view it is mostly the drift that shows, and
the lines appear as the camera closes in. View → **Surface detail** turns it
off (`setDetail`); one shared uniform, so the switch costs no recompile.

**Shadows (ADR-676).** The key's shadow is a variance shadow map, blurred
(radius 10, 16 samples), so its edge softens with distance from what casts
it, as under a softbox, instead of ADR-601's hard cut-out. The shadow camera
hugs the design — ±1.7 of its radius across, its depth range four radii
either side of it — so the map keeps its precision at any scale and never
streaks.

**The selection (ADR-676).** The parts the Outliner (§25) has selected are
ringed in `#58a6ff`, two pixels wide (at most four on a high-DPI screen):
full strength where the part is in view and a third of it where another
part hides it. They are drawn alone into a mask, through the solids that
may hide them, and the ring is drawn round the mask over the frame. A
selected part also glows faintly (a matcap one is tinted). A capture never
selects anything.

The style, the mesh lines, the reflections and the look are this browser's
(`cadex.render`, `cadex.meshlines`, `cadex.meshlines.strength`,
`cadex.reflections`, `cadex.look`, `cadex.occlusion`, `cadex.detail`); a
capture never uses them and draws shaded in Studio with occlusion and detail
on, at the default strength.

The environment module behind the viewport and the video capturer has one
palette, the reference's dark one (ADR-331); the light palette and its theme
setter are gone from the code rather than parked behind a switch. Its scene
background is `--bg`, so the model sits in the same near-black place the
page is, and the videos are captured in it. Measured on the persistent
operator dashboard on 2026-09-13, serving `ot5-lark-copy85` with
`lark98-final` re-rendered in the dark look: viewport and capture page
byte-identical at the same pose and camera; the decoded first frame within
1.1 of 255 of the viewport; the reference's own unmodified scene modules,
dark theme, over the same solids at the same cameras, equal in mean
luminance to 0.1. The frames, the numbers and the written assessment —
floor and grid, horizon and fog, palette, lighting and shadows, materials,
framing, camera — are `docs/probes/ot6/look/README.md`, with the composite
[side-by-side.png](probes/ot6/look/side-by-side.png).

**The grid is anchored to the world (ADR-343).** The mat's major lines sit
on whole metres in world space, with a block corner on the origin, whatever
the floor's size. The floor grows with the fog as the camera pulls back, and
until 2026-09-14 its texture was laid from the plane's corner. Zooming out
past a 24 m floor slid the grid under the model, by 0.26 of a 2 m block at
twice the fit distance and 0.51 at four times, so a *1 METER* line was not
where a metre is. A size change now rescales the plane and re-offsets the
texture without repainting it.

**The grid is true size (ADR-600).** One square a metre on a side, at every
zoom and every framing: `floor.js` exports `GRID_PITCH = 1` and
`LINE_FRACTION = 5/256` (the line's width as a share of the pitch), paints
the 2 m checker block once at 2048 texels with its *1 METER* and
*PROTOTYPE* labels, and never repaints it. The finer mesh that stepped with
the framing (5 → 10 → 20 cm) and the half-pitch dots are gone: zooming
showed them as layers of grid sliding over one another.

**The floor is the design's own (ADR-600).** World geometry — a task's
floor, slab or wall, a part the manifest marks `world` — is never drawn
beside a design, in the viewport or in a scene-style capture (`video.py`
passes the flag). The mat lies at the top of that geometry, so the design
stands on the mat as it stands on its floor; with none, under the design's
lowest point; and when the world geometry rises more than a floor could
above the design's lowest point (2 mm or 2 % of its height), under the
design. The mat is pushed back in depth (polygon offset) rather than
lowered, so a part resting on it never z-fights. A model that is nothing but
world geometry is drawn as it is. `stats().floor` reports `z_mm`, `source`
(`world` or `design`), `pitch_mm`, and the mat's `centre_mm` and `size_mm`;
`stats().hidden_world` names the parts not drawn.

**The ground never ends (ADR-742).** The mat is centred on the camera's
target, not on the origin, and moves with it on every draw: a followed
rollout carries the mat along under it, its grid still on the world's whole
metres. It is as large as the fade asks (four times the fog's far distance)
and, when the design has run away from a camera that does not follow, large
enough to reach the design with 6 m to spare; the far plane grows with it.
So a playback or a film that runs 50 m, in any direction, followed or not,
is over drawn ground at every frame, and the mat's edge stays past the fade
(`cli/tests/test_dashboard_ground.py`). Moving it repaints nothing: one
plane is moved and scaled and its texture re-offset.

**The course is drawn as one ground (ADR-734, ADR-743).** A model that
stands on a declared course (ADR-714, ADR-716) is drawn on it, as a single
surface sampled from the served course: at each sample the highest box top
or dome over that point, or the plane where neither is. A dome (a mogul,
ADR-744) is a sphere's centre and radius, and its top is the sphere's. A box's top is read exactly
along the vertical through its own rotation and extents, so a ramp turned
to its grade and a turned rock are drawn where their tops are. The samples
run every 25 mm (coarser over a large course, at most `TERRAIN.samples`),
and on both sides of every box corner's x and y, 0.5 mm apart, so a step's
face is a wall and not a ramp; a box turned about x or y (a ramp, a rock's
stone, ADR-745) adds the lines where its faces meet the ground under it, so
its crease is drawn where it is. There are no box objects, no slab and no
edge lines: one mesh, in the mat's own prototype material and palette
(`floor.js`, `prototypeMaterial`), its grid anchored to the world's whole
metres on every facet, with crease normals so a wall's edge stays crisp and
a gentle rise reads smooth. A box course's surface runs 500 mm past its
extent and ends at its plane, where the mat lies, so the course and the
mat meet without a seam and the mat carries the ground on to the horizon
(ADR-742). An engine course runs out 50 m past its extent (ADR-745): the
surface is sampled finely over the extent and whatever stands within 10 m
of it (`TERRAIN.reach_mm`), every 2.5 m (`TERRAIN.far_mm`) over the flat
run-out beyond, which is exact there since it is planar between its walls,
and is eased to the plane over 1.5 m past the run-out's end; where a course
ends at its plane the surface ends and the mat is the ground. A heightfield is drawn on its own vertices and eased down to the
mat over 1.5 m. `groundAt(x_mm, y_mm)` reads the drawn height off the
surface's own triangles, and `stats().terrain.surface` gives the mesh
count, sample columns and rows, triangles and extent
(`cli/tests/test_dashboard_ground.py` holds a step, a ramp, a rock and a
mogul to the highest box or dome top within 5 mm at 1,000 points, and, on
10 held-out engine courses with every kind, the drawn height to MuJoCo's
own ray onto the placed course within 5 mm at 1,000 points, past the extent
included, ADR-745). The ground is the stage, not
the design: it sizes, picks and outlines nothing, and casts no shadow,
since a self-shadowed course would not match the mat it meets. Fit takes in 300 mm of it behind the design and 1.5 m ahead along +x,
where courses run, and a course appearing where there was none is fitted. `setTerrain(block)` draws it. The block is a model's
`collision.terrain`, which the server reads from the export's world body (course 0
of a pool), until a playback carries a `terrain` of its own. A rollout,
checkpoint or evaluation trace names the course its episode stood on, so an
evaluation seed is shown on its held-out course. With a course the mat lies
at a box course's plane, the ground beyond its extent, or 50 mm under a
heightfield's lowest point (`stats().floor.source` is `terrain`), and
`stats().terrain` names the kind, the box and dome counts and the course. An
evaluation's film draws the same one ground under the solids (ADR-746):
`film.terrain_surface` is a port of `sampleSurface` (`SURFACE` is
`TERRAIN`'s sampling), held to `groundAt` at every point the held-out test
compares, and `film.Ground` draws it in tiles of 48 cells, prepared on
demand with a ring so normals are smoothed across tile edges, choosing per
shot the tiles under the window and inside the mat's fade at a stride
that keeps a cell about a pixel tall. The renderer paints it with the mat
itself (`CadexStudio.GROUND`): each point the checker and line the mat
has there, faded as the mat fades, lit relative to level ground, so level
ground at the plane is the mat and a wall or slope reads by its light
(`docs/probes/orun8/g1-film-frame.png`, `g1-film-every-kind.png`). Its
seed row's `terrain` names it.

**The clip planes follow the shot (ADR-600).** The camera's near plane is
0.002 of its distance to the target and its far plane is 1.5× the floor's
size (`STAGE_LOOK.farFloorMul`), so the depth buffer's precision scales with
the shot and the floor, its fade and the design never clip, pop or z-fight
at any zoom; `stats().clip` reports both. They used to be 0.001 of the
design's radius and a fixed 800 m, a ratio of millions that let the mat
and a design's own floor fight at the contact.

**The follow camera and the timer (ADR-332).** A recording's camera is the
reference's follow rig, computed by the shared scene module (`follow`) from
the subject's centre at every sampled solved pose and recorded into the
video's `framing`: the subject's standing height — its vertical extent at the
first solved pose — fills a declared **0.22** of the frame height, so the
standoff is one number for the whole clip and apparent size is fixed by
construction; the camera keeps the viewer's yaw and pitch (the horizon never
moves) and translates with a Hann-smoothed copy of the track, half-window
0.4 s, the subject resting 0.06 of the half-frame below centre for headroom;
the subject may lead that anchor by 0.26 of the half-frame in either screen
axis before an `l·tanh(d/l)` limiter pulls the anchor after it, so a whip
cannot carry it out of frame. The viewport's default fit is unchanged: it is
an inspection fit, and the same `follow` is available to it for a shot.

The timer is the reference's caption pill: panel `rgba(20,22,26,.72)`, line
`rgba(244,245,247,.22)`, ink `--ink`, the page's `--font` at 3.2 % of the
frame height and never below `--fs-0`, tabular numerals letter-spaced 0.12 em,
4.2 % of the height in from the bottom-left corner. It is drawn inside the
WebGL frame after the stage, so the capture's PNG and the viewport bake the
same pixels; it shows simulation seconds, and it is hidden while the viewport
is at rest. Measured on the persistent dashboard with `lark98-final`
re-rendered: the viewport at the recording's camera, pose and clock is within
1.24 of 255 of every decoded frame checked and byte-identical to the capture
page; the rig's apparent size is 0.2198–0.2201 across the clip; the frames
and the assessment are the second half of
[docs/probes/ot6/look/README.md](probes/ot6/look/README.md), composite
[follow-side-by-side.png](probes/ot6/look/follow-side-by-side.png).

## 12. The screen: areas and editors (ADR-534)

After Blender's screen. The screen is a tree: a split (`row` or `col`, with
each child's share) or an area showing one editor. The default is the 3D
viewport over 72% of the width, over a strip of **Version** (14% of that
column, ADR-770), with the **Outliner** (§25) over **Status**
over **Training** to its right, 30%, 20% and 50% of that column, as Blender
has its Outliner over its Properties (ADR-732; before it, the Outliner over
Status, ADR-676; before that, Status
alone beside the viewport, ADR-572, and before that one 3D viewport,
ADR-539); split an area to bring in the 2D viewport. The viewport's look and the layout live in the menu bar (§2); this browser's other preferences are the Settings editor (§28, ADR-728).

- **Resize**: drag the 4 px gutter between two areas; it moves that boundary
  only, and no area goes below 120 px.
- **Pick the editor**: the dropdown at the left of an area's header. Most
  editors show at most once, so picking one already shown swaps the two
  areas. The **3D viewport**, **Activations** and **Network** may show more
  than once (ADR-729): picking one already shown opens another copy of it.
- **Move**: drag an area's header (its grip, the dotted strip at its left
  end, or any empty part of it) onto another area. A drop on an edge docks it
  on that side, splitting the target; a drop in the middle swaps the two. A
  preview covers where it will land and names it: **Swap**, **Dock left**,
  **Dock right**, **Dock above** or **Dock below** (ADR-573).
- **Presets** (ADR-573): View → Layout in the menu bar lays the screen out
  afresh in one click — **single**, **side by side**, **stacked**, **2 over
  1**, **1 over 2**, **three columns**, **three rows** and **quad** — each
  area an equal share, filled in reading order with the 3D viewport, Version, Status,
  Training, the 2D viewport and the Outliner, so quad shows the first four. An editor shows
  at most once; an area left without one is **empty**: it has only its
  editor picker and a line saying so, and picking an editor there moves that
  editor in. Showing an editor (a link to a film, say) fills an empty area
  before it splits one.
- **Collapse** (ADR-731): the caret (^) first among the buttons at the right
  of the header hides the header, so the editor fills the whole area; a small
  caret tab in the area's top right corner, on `--surface-2`, brings it
  back. Each area keeps its own; the header goes with the area when it moves
  and stays collapsed when the area is maximized. A phone's single editor has
  no collapse.
- **Split, maximize, close**: the next four buttons at the right of the header.
  A split of a 3D viewport, Activations or Network opens a copy of it beside
  the area; any other split opens an editor not shown yet, and with every
  one shown there is nothing to split. Maximize (or Ctrl+Space over the area)
  gives the area the whole screen until it is pressed again. The last area
  cannot close.
- **Kept**: the layout is this browser's (`localStorage`
  `cadex.layout.v7`, empty areas and copies included (an area's `copy`, 0
  being the editor's own, and `collapsed` when its header is collapsed); `v6` had no Version editor, so a layout kept before ADR-770 opens as the new default, `v5` had no Training editor, so a layout kept before ADR-732 opens as the new default, `v4` had no Outliner, so a layout kept before ADR-676 opens as the new default, `v3` had no Status editor, and earlier keys held the Chat and an older Settings editor); View → Layout → **Reset** in the menu bar returns the
  default. A browser that refuses storage gets the default every visit.

An editor's markup is never rebuilt by a layout change: the area moves the
editor's own elements, so a canvas keeps its WebGL context. Below 700 px there is no tiling (§6), and a phone shows each editor's own, not its copies.

**Copies** (ADR-729, `viewports.js`). A copy is made from the editor's
markup as the page first had it, the first time an area asks for it, and
kept while the page is open, so closing and reopening it keeps its camera.
Every id in a copy becomes a `data-ref`, so the page's hooks (§2) still name
the editor's own, and the stylesheet's rules for those elements name both
(`:is(#x, [data-ref="x"])`).

- **3D viewports** show one model on one timeline. Every viewport has its
  own viewer, camera, gizmo (shown or folded away), style (Shaded or
  Wireframe in its header) and lighting (its header's menu), and its own
  **Follow** and **Trail** style; the model, the ghost, the poses, the
  trail's course, the hidden and selected parts and the heat are every
  viewport's, and the meshes are fetched once for all of them. The source,
  the scrubbers and the timeline are the one Version editor's (ADR-770); a
  copy's status line is the first viewport's, mirrored. A copy starts with
  the first's trail and gizmo. The View menu's
  render style and lighting set every viewport, and the first's are the
  ones this browser keeps; its mesh lines, reflections, occlusion and
  surface detail are every viewport's.
- **Activations and Network** copies draw the one rollout and network: the
  picked motor and a hovered neuron are shared, while each panel's views
  (Gauges, Bars, Drivers; Layers, Paths) are its own. Whether the loads are
  painted on the model is each 3D viewport's own switch (ADR-770). The first
  panel of each kind keeps its views in this browser.

## 15. Policy videos are drawn in the studio look (ADR-431)

Under ot10's W1, a run's video is drawn by default in the design's studio
look (`python -m cadex_cli.video --project P --run R`, `--style studio`).
It uses the hero view and the design's own materials, on the dark prototype
mat (§16) with a contact shadow, and has a timer at the bottom left. It is
drawn on the CPU with no browser. The run's record lists it with its style
(`studio`, or the scene's `cadex-prototype-dark-v1`) under `api/run/<run>`'s
`videos`, and the server serves it at `video/run/<run>/<i>`; the page's
Videos tab went with ADR-533, and the 2D viewport lists evaluation films,
not run videos (§2). The dark viewport and its capture (§10) are unchanged, and
`--style scene` still records in them. Since ADR-444 a studio clip stands on
the same floor as the viewport, so its grid is anchored at the world origin
and the robot's stride and any foot slip read against it.

A studio clip stands on the design's floor (ADR-432). When the render
summary names an environment, that environment is not drawn, and the shadow
falls on its top face. So a robot whose solids sink through the floor
(the rollout collides on proxies) is drawn sinking, rather than floating
above a shadow at the lowest reach. The clip draws the rollout's own solids
within a triangle budget, and says how many it read and drew.

## 16. One scene for every image (ADR-444)

Under ot10's A8, every image Cadex presents is drawn in the viewport's dark
scene: the studio hero, the four review views, `look`, the concept sheet
(`cadex render`) and the studio video (§15). The floor is the prototype mat §10 draws —
`PALETTE.scene.bg` `#141414`, tiles `#1c1c1c` / `#232323` and the `#3a3a3a`
major line — and the sheet's chrome is this page's `--ink`, `--ink-2` and
`--rule`.

**One source.** The engine's `CadexStudio.PALETTE` (ADR-445) is the table
every image is drawn with, in the CLI and the dashboard's server. A browser cannot
import Python, so `review_static/environment.js` (`PALETTE`) and
`review_static/review.css` (`:root`) carry the same colours. Change a
colour in the engine and in both files together (no test checks the copies
since ADR-725); no CLI module carries a scene colour of its own.

**The floor.** The CPU renderer (`CadexStudio._floor`) intersects each
orthographic ray with the floor plane: a checker one pitch square, the
line on every multiple of the pitch anchored at the world origin, and each
line's pixel coverage computed from the floor footprint of the pixel, which
antialiases it. The pitch is **1 m at every framing** (`GRID_PITCH_MM`,
ADR-604), the viewport's `GRID_PITCH`, and the line is the same 5/256 of
it (`LINE_FRACTION`): the hero, the review views, `look`, the sheets, the
print-bed hero, the evaluation's overview and detail filmstrips, rollout
and shove videos all stand on true-size squares, so a 300 mm robot covers
a third of one and its size reads. (Until ADR-604 the pitch followed the
framed span down a 10 mm–10 m ladder, so a square was 50 mm in one image
and 500 mm in the next.) The mat fades into the background between 0.75×
and 1.9× the framed extent from the point under the image centre. A level
view (`front`, `right`) sees no floor and draws the background. No minor
lines and no baked labels: at a hero's framing they are noise.

**Where the mat lies, and what is not drawn.** The design's own floor —
the world geometry its fit names — is never drawn in any engine image or
video; the mat is laid at its top face (`world_top` for stills; the
collision plane, else the world's top, for films and studio videos, §15),
and at the design's lowest point only when it declares none. Every path
leaves it out: `look` and `render` (`exclude`), the hero and the sheet
(`_scene`), the print bed (printed parts only), films and shove videos
(`retained_solids`' world set) and studio videos (the render summary's
`environment`).

**What parts are made of** (ADR-603, `docs/DESIGN-LANGUAGE.md` §2): each
part's finish class — `printed`, `purchased`, `hardware`, `board` — comes
from its catalog family. The renderer shades a finish as `(specular,
exponent, metal, sheen)`: key, fill and rim light, a reflection of a small
studio (a soft overhead light, a softbox on the key side, the dark mat
below), metal as a tinted mirror under a hard highlight, and a board
painted per subsample (mask, chip box, tinned pads) from where the point
lies in the catalog board's frame. `/api/model/accepted` gives the viewport
the same facts per component: `finish`, `catalog` (`{family,
part_number}` or `null`), `board` (`null`, or `{width_mm, length_mm,
thickness_mm, chip: {origin, size}, pads: [{origin, dia_mm}], frame}` in
the part's own mesh frame, mm), with `color` the finish's base colour for
hardware and boards.

**The shadow** is the measured contact shadow (§15, ADR-432), deepened for a
dark floor — it may take a tile to 20 % of its brightness (was 45 %). On
`ot10-quadruped-3`'s hero the tiles at its feet fall from 28–35 to 6.

**Not changed.** The judge: A1's frozen procedure keeps its rubric, and no
probe is re-scored (ADR-444). The viewport and its capture (§10) are the
source, not a consumer, and are unchanged.

Before/after: `docs/probes/ot10/a8-*.png`.

## 18. Read-only: the agent changes the project, the page follows (ADR-537)

The server answers GET and HEAD and nothing else: any other method, on any
route, is 501, and the served page carries no token. The page's 2 s poll of
`api/project` notices when the accepted revision moves -- a `cadex params`,
a `write_script` through `cadex mcp`, a `cadex revision restore` -- and
reloads the model then. `cli/tests/test_dashboard_read_only.py` holds this:
every method but GET and HEAD is refused under both servers with the project
unchanged, and an open page follows a `cadex params` run to the rebuilt model.
The Revisions menu keeps `#revision-list`, the stored trail
newest first, numbered by ordinal, **current** for the accepted one and when
it was accepted for the rest; each row carries `data-revision`,
`data-ordinal` and `data-current`.

What the page once wrote is the CLI's alone now, where an agent reaches it:
`cadex params --set` for the slider (ADR-503), the person's own agent
through `cadex mcp` for the chat (ADR-504, ADR-538), `cadex revision
reject|restore` (ADR-506), `cadex export` (ADR-509) and `cadex section`.
The comment channel (ADR-505) and `cadex revision accept` are gone with the
owner channel (ADR-538). The listings those commands leave -- exports and
sections -- still answer under `api/project`.

## 22. Remote viewing: `tailscale serve` in front of 127.0.0.1

The dashboard binds `127.0.0.1` by default (`cadex app`, `cadex review`,
`serve_projects` and `serve` all default to it), so nothing off the machine
reaches it. To watch from a phone or another computer on your
tailnet, leave it on loopback and put Tailscale's HTTPS proxy in front of
it, on the same machine:

```bash
pixi run app                     # 127.0.0.1:8765
tailscale serve --bg 8765        # https://<machine>.<tailnet>.ts.net/ -> 127.0.0.1:8765
tailscale serve status           # what is being served
```

Only devices on your tailnet can open that URL, and Tailscale terminates TLS.
It may be mounted at a sub-path too (ADR-551): every URL the pages fetch or
link, every URL the server builds into a response (`mesh`, `url`, a project's
`p/<name>/`) and the redirect from `p/<name>` to `p/<name>/` is relative to
the page, so a proxy that forwards `/some/prefix/<rest>` to `/<rest>` and
rewrites nothing serves the whole dashboard.
`tailscale serve --set-path /name` hands `/name` and `/name/` to the server
alike, and at `/name` every relative URL would resolve outside the mount, so
both pages first add a missing trailing slash to a path whose last segment
is not a file (an inline script ahead of `theme.js`). Only the abandoned
first load's preload fetches stray. Both
pages declare an empty icon, so not even the browser's own `/favicon.ico`
probe escapes it. There is nothing to write behind the proxy
(§18), but the page still shows the whole project to whoever opens it. Do not use `tailscale funnel`, which publishes to the internet, and do not
pass `--host 0.0.0.0`.
`--host <tailscale address>` (`docs/CLI.md`) binds the tailnet address
directly without TLS, and is the older path. Cadex's own runs never start
`tailscale serve`. It is a step the owner takes.
`cli/tests/test_dashboard_read_only.py` checks that this section names the
loopback default, `tailscale serve --bg 8765`, `tailscale funnel` and
`0.0.0.0`, and that `serve`, `serve_projects`, `cadex app` and `cadex review`
all default to `127.0.0.1`.

**Over a remote link the model is the weight (ADR-535).** An accepted model
is one binary STL per component, 28 MB for a 45-part arm, and each one was
sent uncompressed with `no-store` and rebuilt per request. That request
re-derived the whole model manifest, hashing every BREP of the attempt, so
one load cost about 2 s of server CPU and 28 MB on the wire, every time the
model was opened or moved. Now:
- the manifest is remembered until the project manifest, the attempt's
  `result.json` (both by content) or its tessellation and trace (by stat)
  move;
- each converted mesh is kept by its tessellation's content hash, and that
  hash is its `ETag` (`Cache-Control: no-cache`), so a browser revalidates and
  a part a rebuild did not touch answers 304;
- any JSON, text or STL response of 1 KB or more is gzipped for a client
  that accepts it. That arm is 9.3 MB, and the projects listing 100 KB
  instead of 1.1 MB.

The page aborts a load a newer one supersedes, tries a failed request twice
more, keeps the last model drawn until the next is complete, and retries a
failed load on later polls with a growing wait. A slow model never holds up
the 2 s project poll.

Measured on a link emulated at 30 Mbit/s and 40 ms (Chromium, the 45-part
arm): first load 9.1 s → 3.9 s, reopening the same model 8.2 s → 0.8 s.

## 23. The agent's Status panel (ADR-607)

Cadex's own Training editor charts what every machine has: reward, loss, episode
length, action std, evaluations, runs. What only one machine has -- the
ball's distance from its circle per run, a linkage's crank angle against its
foot path, the margin each predicate cleared by -- the agent working the
project may draw itself, in **`status.html`** at the project's root. The
agent writes it with its own file tools; there is no tool for it, and the
page never writes it.

**How it is served.** `status/panel.html` serves the file whole, a regular
file and no symlink, at most 512 KB, under `Content-Security-Policy: sandbox
allow-scripts; default-src 'none'; script-src 'unsafe-inline'; style-src
'unsafe-inline'; img-src data:; font-src data:` with `X-Content-Type-Options:
nosniff`. The page embeds it in `<iframe sandbox="allow-scripts">` --
never `allow-same-origin` -- so it runs in an opaque origin: it cannot read
the dashboard, its storage or its cookies, cannot navigate the page, open
popups or submit forms, and cannot fetch anything at all, the project's own
files included. Everything it shows arrives in a message.

**The message.** On each of the page's 2 s polls, when the frame loads, when
the theme changes, and whenever the panel posts `{type:
"cadex-status-ready"}` to its parent, the page posts:

```js
{
  type: "cadex-status", schema: "cadex-status-panel-v1",
  project: "<name>", served_at: "<ISO time>",
  theme: { name: "dark" | "light",
           tokens: { "--bg", "--surface", "--surface-2", "--surface-3", "--rule", "--rule-strong",
                     "--ink", "--ink-2", "--accent", "--ok", "--warn", "--bad", "--info", "--select",
                     "--font", "--mono", "--fs-0", "--fs-1", "--fs-2", "--fs-3" } },  // computed values
  accepted: { available, revision, digest, updated_at } | null,
  revisions: [ { ordinal, revision, saved_at } ],           // newest first, at most 64
  stage: { state, reason, since, run, runs },               // as Status reads it
  training: null | {                                        // the run Status reads
    state, reason, iteration, total, eta_s, wall_time_s, reward_per_step, loss, episode_steps,
    action_std, best_iteration, best_reward_per_step, warning, label, age_s,
    curves: { curve, loss_curve, episode_steps_curve, action_std_curve },  // [[iteration, value]]
    resolution: "full" | "sketch",  // full: the trainer's histories (<= 512 points), read from
                                    // api/run/<run> at most every 10 s; sketch: <= 128 points
    checkpoints: [ { iteration, reward_per_step } | { iteration, path, status } ] },
  runs: [ { run, status, outcome, mode, recorded_at, label, reason, telemetry_state, iteration,
            total, reward_per_step, best_reward_per_step, best_iteration, wall_time_s,
            policy_sha256 } ],                              // oldest first
  evaluations: [ { name, verdict, passed, seeds, failing, terminations, task_output, task_label,
                   policy_output, policy_sha256, evaluated_at, relation,
                   summary? } ],  // oldest first; the newest carries its report's summary --
                                  // predicates [{id, metric, min, max, passed, failed_seeds,
                                  // value: {min, median, max}}], terminations, reward -- once read
  params: { specs, values?, ... } | null,                   // the newest run's recorded params
  activity: [ { t, tool, args, outcome, detail } ]          // the agent's newest calls
}
```

Iterations are zero-based in the message, as the trainer writes them;
Status shows them one-based. Fields are added under the same schema; a
panel ignores what it does not know, and a field that changes meaning gets a
new schema.

**Style guide.** A panel sits inside Status, so it should read as part of it.

- *Palette.* Use the message's `theme.tokens` and nothing else: set each as
  a custom property on `document.documentElement` when a message arrives,
  and style with `var(--ink)` and so on, so the panel follows dark and light.
  Page background `--surface`, a block `--surface-2` with an 8 px radius,
  text `--ink`, secondary text `--ink-2`, gridlines `--rule`, axes
  `--rule-strong`. Data is `--accent`, one line or one bar colour.
  `--ok`, `--warn`, `--bad` and `--info` are status (passed, marginal,
  failed, in progress), never "series 2", and each comes with a word or a
  label, never colour alone.
- *Type.* `--font` at `--fs-1` (14 px) for body and `--fs-0` (12 px) for
  axes, captions and table text; headings at 600 weight, sentence case, no
  uppercase; `--mono` for identifiers (run names, predicate ids). Nothing
  under 12 px; `font-variant-numeric: tabular-nums` on numbers.
- *Charts.* Inline SVG drawn at the frame's width (`clientWidth`), redrawn on
  `resize`. One measure per chart and one y axis: two measures of different
  scale are two charts, never a dual axis. Recessive gridlines, tick labels
  on both axes, a 2 px line, no chart junk. Mark what matters with a label
  (the best, the bound, the target), not only a colour. A table beside a
  chart is welcome; a single number can be a tile.
- *Layout.* 12 px padding; blocks stacked with 12 px gaps; nothing wider
  than the frame (it can be 320 px), no horizontal scroll.
- *Behaviour.* Draw only from the message. Keep the last message and
  redraw from it; post `{type: "cadex-status-ready"}` once at startup.
  No timers that run when nothing arrives. Images only as `data:` URIs.

**A skeleton** to start from:

```html
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<style>
  html, body { margin: 0; background: var(--surface); color: var(--ink); font: 400 var(--fs-1)/1.45 var(--font); }
  body { padding: 12px; } h2 { font-size: var(--fs-1); margin: 0 0 4px; }
  section { background: var(--surface-2); border-radius: 8px; padding: 8px 10px; margin-bottom: 12px; }
  svg { display: block; width: 100%; } .grid { stroke: var(--rule); }
  .label { fill: var(--ink-2); font: var(--fs-0) var(--font); } .line { fill: none; stroke: var(--accent); stroke-width: 2; }
</style></head>
<body>
<section><h2>Best reward per run</h2><svg id="chart" height="140"></svg></section>
<script>
let last = null;
function draw(msg) {
  for (const [name, value] of Object.entries(msg.theme.tokens)) document.documentElement.style.setProperty(name, value);
  const runs = msg.runs.filter(r => r.best_reward_per_step != null), svg = document.getElementById('chart');
  const W = svg.clientWidth, H = 140, L = 40, B = 20, hi = Math.max(...runs.map(r => r.best_reward_per_step), 1e-9);
  const x = i => L + (i + 0.5) * (W - L) / Math.max(runs.length, 1), y = v => H - B - v / hi * (H - B - 8);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = [0, hi / 2, hi].map(v => `<line class="grid" x1="${L}" x2="${W}" y1="${y(v)}" y2="${y(v)}"/>`
      + `<text class="label" x="${L - 4}" y="${y(v) + 4}" text-anchor="end">${v.toPrecision(2)}</text>`).join('')
    + `<polyline class="line" points="${runs.map((r, i) => x(i) + ',' + y(r.best_reward_per_step)).join(' ')}"/>`
    + runs.map((r, i) => `<text class="label" x="${x(i)}" y="${H - 4}" text-anchor="middle">${r.run}</text>`).join('');
}
addEventListener('message', e => {
  if (e.data && e.data.type === 'cadex-status' && e.data.schema === 'cadex-status-panel-v1') draw(last = e.data);
});
addEventListener('resize', () => last && draw(last));
parent.postMessage({ type: 'cadex-status-ready' }, '*');
</script>
</body></html>
```

`cadex guidance` tells the agent it may write one and points here.

## 25. The Outliner (ADR-676)

After Blender's Outliner: every part of the model the 3D viewport shows, to
show, hide, isolate, select and frame. It is an editor like the others
(`outliner.js`), above Status by default (§12), and **Parts** on a phone's
tab bar. The task's world geometry is not listed: it is never drawn beside a
design (ADR-600, §10).

- **Groups.** By **type** — printed parts, purchased parts, hardware, boards,
  from the manifest's `finish` — by appearance **role** (shell, mechanism,
  accent, and *No role*), or **none**, from the menu in the Outliner's bar.
  A group folds by its arrow and shows its count; **Hardware** starts folded,
  since a robot's screws run to a hundred rows. A click on a group's name
  selects all of it.
- **Rows.** Each part's eye, its colour, its name, and on the right its
  catalog family and part number (or its finish) and its role. A click
  selects it; **Shift** or **Ctrl** (**Cmd**) adds or removes it, and Shift
  after a click selects the run between; a double click frames it. The
  summary under the tree counts the parts, the hidden and the selected, or
  names the one part selected.
- **Eyes.** A part's eye hides it, a group's eye all of the group;
  **Ctrl** on an eye **isolates** that part or group, hiding everything
  else; the eye in the bar shows every part again. A hidden part leaves the
  selection, is not drawn, does not cast a shadow and cannot be picked, and
  **Fit** frames what is still shown.
- **The viewport.** A click on a solid selects its row (Shift, Ctrl or Cmd
  adds or removes it; a click on empty floor clears the selection), and the
  row scrolls into view, its group unfolding. The selection is outlined in
  the viewport (§10).
- **Keys**, with the pointer over the 3D viewport or the Outliner and no
  field focused, as in Blender: **H** hides the selection, **Shift+H** hides
  everything else, **Alt+H** shows everything, **F** frames the selection
  (or everything), **Esc** clears the selection.
- **Filter.** The field in the bar narrows the rows to names containing
  what is typed.

What is hidden and selected is the viewer's (`setHidden`, `select`,
`parts`, `fitTo` in `review_scene.js`), kept by part name, so it outlives
the agent's next write: a part of the same name is still hidden in the next
revision, a run's model or the revision timeline. It is the page's own and
lasts as long as the page; nothing is written (§18). The grouping and the
folded groups are this browser's (`cadex.outliner.group`,
`cadex.outliner.folded`).

## 26. The hero folder (ADR-677)

`cadex hero --project DIR` writes a project's presentation into `DIR/hero/`.
It runs only when a person or their agent runs it; nothing schedules it. Every
image and video in it except the sheet is drawn by this page's own scene
(`review_scene.js`, §10) in headless Chromium, on `hero.html`: the 3D
viewport's renderer on the prototype mat, with its baked "PROTOTYPE" and "1 METER" text, and
none of the page's chrome. Python drives the page a frame
at a time and FFmpeg encodes. Chromium draws on the GPU through ANGLE over Vulkan, with its 2D canvas in software,
when it has one (`--software` forces SwiftShader, about thirty times slower).

| File | What it is |
|---|---|
| `still-studio.png`, `still-softbox.png`, `still-dramatic.png`, `still-aluminium.png`, `still-wireframe.png` | The accepted design at 2560×1440, drawn at twice that and filtered down. Each is a lighting setup or matcap (§10) from its own three-quarter view, through a 30° lens rather than the viewport's 55° so the design keeps its proportions. Each is framed by the design's own outline (`screenBox`), centred and filling 80% of the frame. |
| `dashboard.png` | This page at 1920×1080 CSS pixels, scale 2. The 3D viewport (the accepted design, fitted) is on the left half and Training is on the right, showing the charts. It is set through the layout key, as a person's own layout would be. |
| `sheet.png` | The concept sheet `cadex render` draws (ADR-430), of the accepted revision. It is copied when a render already drew it. Otherwise the CLI opens the engine for the design's fit and inventory and draws it from the retained accepted attempt, without a rebuild. With `--no-engine` it is reported missing instead. |
| `rollout.mp4` | The chosen rollout at 1920×1080 and 30 fps, with the clock. The camera is this page's follow rig (§10), framed so the design's standing height is 42% of the frame. The last pose is held for 0.8 s. |
| `hero-landscape.mp4`, `hero-square.mp4` | 1920×1080 and 1080×1080, 30 fps, H.264. **The turn** is one revolution in 12 s at constant speed through the 30° lens. Meanwhile the camera cranes down from 36° to 21° above the floor and pushes in by 12%, both eased. It is framed so that every view of that move fills 90% of the frame, centred. It starts in Clay. At 2.7 s a diagonal edge sweeps from the top left to Aluminium, at 5.9 s to the wireframe, and at 9.1 s to the design's own materials (Studio). Each wipe takes 0.55 s, eased in and out (cubic), and the edge turns from 38° to 16° off vertical as it crosses. The edge is drawn additively: a white core, a cyan fringe behind it and an amber one ahead, a narrow band of light, a glint running along it, and a flash over what it has just uncovered. **The rollout** follows: its first 6 s, without the clock. **The training curves** come last: reward per step (with the best marked) and loss, drawn left to right over 3 s and then held, side by side or stacked to fit the frame. A 0.6 s crossfade joins the parts. |
| `hero-wireframe-landscape.mp4`, `hero-wireframe-square.mp4` | The same move in the wireframe alone, in 6 s. |
| `view-hero.png`, `view-side.png`, `view-front.png`, `view-rear.png`, `view-top.png`, `view-head.png` | **The views (ADR-792)**, made only when asked for (`--only views`): fixed cameras, so that projects or revisions compare shot for shot. The design's front is the direction, in plan, from its centre to its focus parts' centre: the parts whose names match `--focus` (default a creature's head: `head`, `skull`, `jaw`, `muzzle`, `ear` and the like, each at the start of the name or after `_`). Yaw from the front and pitch above the floor: hero three-quarter 0.75 rad and 0.42, side π/2 and 0.08, front 0 and 0.12, three-quarter rear π−0.75 and 0.42, top π/2 and 1.45, and the head close-up 0.6 and 0.2, framed by the focus parts' outline alone (`screenBox(names)`) at 70%; the others are framed by the whole design at 80–85%. 1920×1080, drawn at twice that, in Studio on the dark mat. No focus part is an error for the views alone. |
| `hero.json` | What was made, from which revision, run and checkpoint, with each camera and the renderer. Each item that was not made is listed with its reason. |

**Banding.** Every frame carries a fixed dither, a level and a half either way, so the dark sky
and the fog's fade do not step once they are 8 bits a channel. The frames go to FFmpeg as PNG, and
x264 encodes with `tune grain` and `aq-mode=3` at crf 15, so the dither is not smoothed back into
bands.

**A grid of projects.** `cadex hero-grid A B C D --out FILE.png [--still NAME] [--columns N] [--tile-width PX]`
tiles one still or view from each project's hero folder, two to a row by default, in the order given (left
to right, top to bottom), labels each tile top left with its project's name in the page's ink on a
translucent mat, scales the tiles to `--tile-width` when given, and fills a missing last tile with the mat. The Cadex checkout ignores
`showcase/`, where such grids are kept.

**Which rollout.** The candidates are each run's own rollout and every
checkpoint rollout the engine made while the run trained (ADR-544). The one
whose episode lasted longest is chosen, and the newest among equals, a run's
own rollout after its checkpoints. `--run NAME` limits the choice to that
run. The curves are that run's, or else the newest run's that has any.

**Each item stands alone.** One that cannot be made, such as a project with no
run (no rollout or curves), no Chromium or a busy engine, is named in
`hero.json` and the rest are made. The folder's `.gitignore` keeps all of it
out of the project's history, because it is drawn again on request.
`--only stills,dashboard,sheet,rollout,video,views` makes a subset; a bare run makes all but the views.

## 27. Activations and Network (ADR-727, ADR-728)

Two editors (`activations.js`, one state between them) that follow whatever
rollout the 3D viewport is playing (a checkpoint's, a run's own) frame by
frame, through the same `seek`, so pausing, scrubbing and looping move them
too. They are in no preset; an area's editor menu opens them. **Activations**
is the motors; **Network** is the policy, given an area of its own so it can
be read large (ADR-728). Each view in either is a switch in its header
(`button[data-view]`, `aria-pressed`), kept by this browser
(`localStorage` `cadex.activations.views`): Gauges, Bars and Drivers;
Layers and Paths. Gauges, Drivers, Layers and Paths start on, Bars off.

**Gauges.** A gauge per actuated joint, in the trace's channel order: a 270°
arc over the joint's command range, the needle where the joint is, a
`--info` dot at the command the rollout recorded and a ring at the command
the network gives for this frame. The arc fills from zero to the needle in
the heat colours, by the joint's effort against its rating; under it the
angle and the load as `% rated`. A gauge past its rating is outlined in its
heat. A click picks the motor.

**Bars.** The same reading a row per motor, laid sideways for a long list:
the name, the command range as a track filled from zero to the joint in its
heat with a tick at zero, the recorded command a `--info` dot and the
network's a ring, then the angle and the load. A row past its rating is
outlined in `--bad`; a click picks the motor.

**The heat colours** are `heat.js`'s, picked in Settings (§28): two or
three colours, idle to peak, mixed in sRGB; by default blue `#2f6bff`
fading through white `#f2f2f2` into faint red and on to dark red `#9e0b1f`.
A load `u = |effort| / rated` lands on them at `1 − e^(−k·u)` with `k` set
so the rating is at 0.8: a load rises along a curve and saturates towards
the peak rather than clipping, and a motor at its rating already reads red.
The legend under the status line marks idle, rated and peak in the chosen
colours, and every view and the viewport repaint when they change.

**Drivers.** For the picked motor, the six inputs that drive it most (input
× gradient), with their shares, warm where an input pushes the command up
and cool where it pulls it down.

**Layers** (Network). A canvas on the dark mat: the inputs, each hidden
layer folded into a block of cells, and the motor commands, each cell in the
heat colours by its |activation| against its layer's 95th percentile over
the rollout (inputs by |z| / 3, outputs by |tanh|). For the picked motor,
the last hidden layer's sixteen strongest contributions (activation ×
weight) are drawn as curves to its output, warm up and cool down, and the
input column shows input × gradient. A press on a motor's output cell picks
it.

**Paths** (Network). For the picked motor, a node-link reading of the same
network: the eight units in each column (the inputs, then each hidden
layer) that move its command most (activation × gradient), largest first
from the top and sized by it, each filled in the heat colours by its
activity and ringed warm or cool by the sign of its pull; links between
consecutive columns carry what flows along them to the command (the lower
unit's activation × the weight × the upper unit's gradient), thick and
strong for the largest, warm or cool, and a link under a twentieth of its
pair's largest is left out. The inputs are named on the left, the motor and
its command on the right.

Hovering a hidden neuron in Layers or Paths silences it for one pass: each
gauge and bar shows `Δ`, the change in its command, and takes its heat from
that, as a viewport does while its Activations switch is on.

**Activations in the 3D viewport** (`#view3d-heat`, each 3D viewport's own
header switch, ADR-770; the Activations editor's **Show in viewport** until
then, which painted every viewport at once) paints each motor's parts in
its heat (`review_scene.js` `setHeat`): the body its joint sits in and what
is welded to it, and over that its own housing, from the MJCF's body tree
(`parts` in `api/policy/...`). Shaded, every other part turns a quiet grey
(`#4a4e56`) and the selection still glows; as a wireframe diagram (ADR-728)
a heated part's face is washed in its colour and its lines are drawn in it,
over the same paper and ink, and the rest stay the diagram they were. The
heat follows a change over about 0.12 s rather than flickering. Off, every
part has its own colour back. The loads are worked out once, by the
Activations core, whichever editors are shown; each viewport takes them or
not, so one can show the heat while another beside it shows the design's
own colours.

**A reconstruction, and it says so.** The network is the rollout's own
policy (`api/policy/checkpoint/<run>/<stem>` or `api/policy/run/<run>`, §2c
of `docs/CLI.md`), run in the page. Its inputs are rebuilt from the trace by
each one's kind in the task bundle: joint positions, velocities and efforts
as recorded; an IMU's orientation from its part's pose and its rate from the
poses a frame either side; the gait clock from the time and the bundle's
period, unless the clock follows the command (ADR-752, `clock` null), when
it is held like an input of another kind. An input of another kind is held at the normaliser's mean and named
in the status line. A trace is kept at 25 fps while the policy runs faster
behind a slew limit, so the status line gives how well frame *k*'s rebuilt
command matches the command frame *k + 1* recorded (Pearson r over the
rollout, per motor in each gauge's tooltip): about 0.8 on the orun7 cat. A
policy that is not an MLP, or whose weights do not match its layers, is not
offered, and the editor shows the motors alone.

## 28. Settings (ADR-728)

An editor (`settings.js`) for this browser's own preferences: they change
how the page draws and never the project (ADR-537), and they are kept in
`localStorage`. The viewport's look and the layout stay in the View menu
(§2); Settings holds what has no place there.

**Activation colours** (`heat.js`, `cadex.heat`): a preset
(`#settings-heat-preset`) — **Blue–white–red** (the default), **Green–red**
(green, amber, red), **Viridis** (purple, teal, yellow, which reads in
greyscale and to most colour-blind eyes) and **Blue–red** (two colours) —
or **Custom**: two or three colours (`#settings-heat-count`) picked with
the browser's colour pickers, low, middle and high. Touching a picker makes
the theme Custom; **Reset** returns the default. A preview bar shows the
ramp, and the Activations and Network editors and every viewport showing
Activations repaint at once.

**Trail colour** (`trailcolours.js`, `cadex.trail.colours`, ADR-770): the
colour of the trail a 3D viewport draws (§2): **One colour**
(`#settings-trail-solid`, white by default), or by **Age**
(`#settings-trail-mode`): a ramp from the oldest of the trail shown to the
newest, at the design, through a preset (`#settings-trail-preset`) —
**Fade in** (dark grey to white, the default ramp), **Ice**, **Ember**,
**Viridis** and **Cool to warm** — or two or three colours
(`#settings-trail-count`) picked by hand, oldest, middle and newest, as
the activation colours are. By age the ramp stretches over the trail as far
as it is shown, so the newest end is always the last colour. **Reset**
returns white; a preview bar shows the colour or the ramp.

## 29. Pose (ADR-969)

An editor (`pose.js`) that moves the model shown by its joints, to see the
range each one has and what poses the design can reach. Posing is view
state, like the camera: it never writes the script, and **Rest** puts every
joint back where the model was built (ADR-537).

**What it reads.** The model's MJCF export, the one its collision proxies
come from: `collision.kinematics` on `api/model/accepted` and
`api/model/run/<run>` (`review_server.py` `mjcf_kinematics`). It carries
every body with its parent and its frame (`pos_mm`, `rotation_xyzw`), every
joint with its `type`, `axis`, anchor (`pos_mm`), `range` (radians for a
hinge, metres for a slide; `null` when it is not limited), `ref`, whether a
motor drives it (`actuated`) and its value at the `solved` keyframe
(`rest`); the joint couplings (`<equality><joint>`: `joint`, `driver`,
`polycoef`) and the closed loops (`<equality><connect>`: two bodies and a
point on each, in mm). A model that sets a frame other than by `pos` and
`quat`, uses `<default>` classes, or has a joint the editor cannot read is
`available: false` with its `reason`, and the editor says it. A revision
from the history carries no export, so it is not posed.

**The walk.** The page walks the tree itself, MuJoCo's way: each body's
frame in its parent's, then each of its joints about its anchor. Each root
body is held where the model shown rests it, so a robot is posed where it
stands. A coupled joint follows its driver by the polynomial
(`y − y₀ = Σ cᵢ (x − x₀)ⁱ`, chains resolved in turn). A closed loop is closed
again after every move by its passive joints — those on the two bodies'
paths up to where they meet that no motor drives and nothing couples —
with damped least squares on the gap and a numerical Jacobian, each step
held inside the joints' stops; when the gap left exceeds 0.5 mm the status
says how far apart the linkage is (`data-state="warn"`). When the model
shown rests more than 1 mm from its export's rest (a run's model rests at
its trace's first frame), the status says so and the pose is the export's.

**The rows** (`#pose-joints`): one per hinge and slide, in the export's
order: its name (a button that picks it and lights the parts it moves in
every viewport, the Outliner's selection coming back when it is unpicked),
what moves it — `motor`, `passive`, `follows <joint>` or `linkage` — a
slider over its range (±180°, or ±100 mm, where it has none; disabled for
a joint that follows or closes a linkage), its value in degrees or mm (in
`--warn` at a stop, `data-stop="true"`) and its stops. Moving any slider
poses the model: **Pose** (`#pose-on`) is pressed, playback stops and
leaves the model where the joints put it, and pressing **Play** or Pose
again leaves posing and puts back the frame the rollout was at.

**Sweep** (`#pose-sweep`) swings the picked joint from stop to stop and back
every 3 s, coupled joints and linkages following, until it is pressed again
or a slider moves. **Mirror** (`#pose-mirror`) moves a joint's partner on
the other side with it — the name with each `l`/`r`, `left`/`right` or
leg token (`fl`/`fr`, `hl`/`hr`, `rl`/`rr`) swapped — the same way when the
two axes, at rest, are mirror images in the XZ plane and the other way when
they are opposed.

**Saved poses.** `#pose-saved` lists `/api/project`'s `poses`, the ones
`cadex pose save` stored under `poses/` (`docs/CLI.md`); picking one sets
every joint it names that the model has (the status counts the rest) and
puts its name in `#pose-name`. **Copy** (`#pose-copy`) puts the pose on the
clipboard as `cadex-pose-v1` JSON — `name` from `#pose-name`, `note`,
`joints` (every hinge and slide, radians or metres, to 1e-6) and `model`
(the export's `source` and `sha256`) — and **Download** (`#pose-download`)
saves the same as `<name>.json`; where the clipboard is not offered (a page
not served over HTTPS or from localhost) Copy downloads. The status then
says the command that stores it. The page keeps nothing of a pose in the
browser.

