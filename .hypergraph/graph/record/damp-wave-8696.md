---
node_id: 63b37bdf-1025-595d-9bc8-9aee184c196c
slug: damp-wave-8696
title: 'C1: orun3 closing report written, done claimed for critic review'
created_at: '2026-10-05T15:52:01+00:00'
parents:
- soft-comet-8840
summary: ''
---
## What

C1: wrote the closing report, `docs/probes/orun3/REPORT.md`. It has a criterion table with records for V1–V4, P1, W1 and C1, and five sections:

- §1, V2's training cost and disk per trace;
- §2, V3's bytes per revision;
- §3, W1's never-reloaded page, with all ten `w1-*.png` and their byte sizes;
- §4, ADR-542 to ADR-553;
- §5, the remaining defects.

§6 claims done for critic review. No owner box is ticked.

## Why

The critic named C1 as the unit after W1's re-run. **Deviation:** the critic asked me to reconcile first, folding tiny-bloom-2937 and soft-comet-8840 and moving lucky-prairie-0215 to working. This dispatch's instructions forbid the reconcile skill and every state-graph write in a work iteration, "no exceptions". The dispatch rule outranks the critic's message here, so I did not reconcile. I am naming it as due in §6 of the report and below. As the critic asked, I did not fix the three defects inside C1; they are listed with their evidence.

## Method

Every figure was copied from its source, not re-measured:

- V2's cost table and disk figures from ADR-544 (snowy-water-3502), and the page cost from ADR-545;
- V3's bytes from ADR-546 and ADR-548 (brisk-dune-8872);
- W1's figures from soft-comet-8840 and solemn-fox-1118.

PNG sizes come from `ls -la`. ADR titles come from `docs/DECISIONS.md`. The per-revision figure is derived: 9 kept revisions, 7,126 B of blobs plus 28,201 B of index, is 35,327 B. That gives ≈792 B of blobs per revision, or ≈3,925 B with its index row, against ≈11,400 B for a full copy. I ran `test_project_docs.py` and `test_licensing_compliance.py`: 39 passed, 1 skipped. No code changed, so the full suites from soft-comet-8840 (2585/58 and 1172/1) still describe the tree.

## Result

**What is true now:**

- `docs/probes/orun3/REPORT.md` exists, verified at `0b1e5264`.
- **Figures in the report:**
  - V2 cost: +0.08% mean iteration wall time with rollouts on (off-2/on-2), so under 0.1%, against the 5% bar.
  - V2 disk: 38.7–329.5 KB per trace, 224.7 KB mean, 2.47 MB for 11 checkpoints.
  - V3: ≈3,925 B per kept revision including the index row, against ≈11,400 B for a copy. For nine revisions that is 35,327 B against 102,612 B.
- **Remaining defects listed with evidence:**
  1. The final-policy stop is missing on a never-reloaded page.
  2. The evaluating line names the evaluation directory.
  3. Progress stalls for 37–39 s before each checkpoint.
- **Also listed as open:** the four unrebuildable stale-policy revisions, and the unworked long-term rungs (phone width, light theme, binary meshes).
- **Done is claimed for critic review.** The owner holds every checkbox.

**Concerns for the next iteration:**

- **Reconcile is overdue.** It should fold tiny-bloom-2937, soft-comet-8840 and this record, move lucky-prairie-0215 (W1) and twilight-badger-2743 (C1) to working, then export and check. That needs a maintainer pass, not a work iteration.
- After the done claim, the next work unit is a long-term rung. The best candidate is defect 1 (the final-policy stop on a live page), then defect 2.
- No new dependency.

Dispatch closed: 1 unit — C1 closing report written (V2 cost +0.08%, disk 224.7 KB/trace mean; V3 ≈3.9 KB/revision vs 11.4 KB copy; ADR-542..553; W1's 10 PNGs; 3 defects named), done claimed for critic review; reconcile not run (forbidden in a work iteration)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 816af97398db21441610c4495afca118cdc30e86

## State Impact

- target: twilight-badger-2743 — C1's report exists at docs/probes/orun3/REPORT.md: V2 cost +0.08% (under 0.1%) and 224.7 KB mean per trace, V3 ≈3.9 KB per revision against 11.4 KB per copy, ADR-542..553, W1's screenshots, three remaining defects; done claimed for critic review, no box ticked
