# `part.offset` makes a project that can never be reopened

Verified against source: 2026-09-19. [Cadex-new]

**Fixed by ADR-389.** Everything below is the measurement that motivated
the fix and still reproduces; what has changed is the consequence. A byte
mismatch is no longer the end of a project — `open_project` re-measures the
two retained attempts and opens when the model agrees, reporting
`matched_by: "geometry"`. The section "What this blocks" is superseded.

**Confirmed on the design it was written for, in iteration 159.** A copy of
`ot7-robin-c` — the project the refusal below shut — now answers
`./cadex clearance` with its **276 static pairs** and exits 0. F6's frozen
`continue-1` is unblocked; it was not dispatched in that iteration only
because the five-hour window read 63 % against the runner's 45 % gate.

Robin's F6 continuation was dispatched on Opus and never reached the model.
The CLI refused in six seconds, before a provider session existed:

```
Could not open <project>: The restore pass digest does not match the accepted digest.
```

`open_project`'s restore pass (`src/Mod/cadex/cadexd.py:487`) re-runs the
stored script and compares the rebuilt project digest against the accepted
one. For `ot7-robin-c` it never matches, and it never matches *differently
each time*, so the project is shut for good. The accepted digest is
`0a6fe0f5…`; three rebuilds of the same bytes produced `e9ffa272…` in the
project itself, then `908ed881…` and `7d2a5051…` in two untouched copies.

This is not a changed design, and the guard is not wrong to refuse on what it
can see. The geometry is identical; only its serialization order is not.

## What actually differs

`compute_project_digest` (`src/Mod/cadex/cadex_project_worker.py:164`)
identifies a BREP output by its exported bytes. Of Robin's 26 outputs, exactly
two differ between rebuilds — `wheel_l` and `wheel_r` — and they differ at the
same byte length (16,927). The differing records are the geometry table:
the same curves, in a different order.

Both wheels, and nothing else in the design, pass through one operation:

```python
cutter = part.offset(seg, p.bore_clear / 2.0, output_type="solid")
```

## Isolated

A minimal script through the real `cadexd`, three separate processes each:

| script | digests over three processes |
|---|---|
| `part.offset(cylinder, 0.15, output_type="solid")` | `ad7a46c2…`, `f1d2ecd2…`, `eed4f4fe…` — three different |
| `part.cut(part.fuse([box, cylinder]), cylinder)` | `260f3221…` three times — stable |

`part.offset` is `TopoShape.makeOffsetShape`, i.e. OCCT's
`BRepOffset_MakeOffset` (`cadex_part_worker.py:4221`). Heron, which uses no
`part.offset`, resumed through three continuations without trouble.

## The shape is the same; the bytes are not

Measured directly against the kernel, on the same offset, three processes:

- volume `232.666456132` mm³ every time;
- 5 faces, 7 edges, 4 vertices every time;
- the edge-length multiset identical to 1e-6 every time;
- **4 of the 5 individual faces export to different bytes each run.**

So the instability is *inside* each face, not in the order faces are held.
Rebuilding the solid from its faces sorted by centre of mass and area — the
obvious canonicalization — does **not** stabilize the digest. That approach is
a dead end at the shape level.

## What this blocks, and what it does not

- **F6 and F7 were blocked** for any design that reaches for `part.offset`:
  an accepted design using it could not be reopened, so no continuation could
  run. ADR-389 lifts that; a copy of `ot7-robin-c` exports again.
- **Nothing that is open today breaks.** Heron, Finch and the retained ot6
  designs use no `part.offset`; their digests are byte-stable and their
  projects open.
- The accepted-state guard is doing its job as specified. What was wrong is
  that byte equality was being asked to stand for geometric equality, for an
  operation whose bytes are not a function of its inputs alone. ADR-389 adds
  `cadex-project-geometry-digest-v1` beside the byte digest rather than
  replacing it — the same entries, with a BREP output identified by its
  canonical definition plus the kernel measurements that *are* stable
  (measured: the exact vertex set, edge-length and face-area multisets,
  counts, bounds and area; never volume). No stored `accepted_digest` moved,
  so no migration was needed.
- **The same fault has a second door, and ADR-396 shut it.** `part.offset`'s
  bytes are not a function of its inputs *within one engine*; a **derived**
  output's bytes — an MJCF model, a training task, a trace, a render — are not
  a function of its inputs *across engine versions*. ADR-393 fixed the MJCF
  exporter's welded-body pose and thereby shut `ot7-plover-e`, whose design was
  provably unchanged: 2 of 90 outputs moved, both derived, with every BREP
  artifact, definition and solved placement identical. So
  `cadex-project-geometry-digest-v1` stopped reading those bytes too, and the
  project opens with `matched_by: "geometry"`. `cadex-project-digest-v1` still
  reads them, still refuses, and is still the accepted-state guard.

## Reproducing it

```bash
pixi run python docs/probes/ot7/runner/run.py reclassify <project>   # the accounting
./cadex export --project <copy-of-ot7-robin-c> --out /tmp/out --json  # the refusal
```

Then read `latest_candidate.digest` in the copy's `script.json`: it is a new
value after every run, and never the `accepted_digest` beside it.
