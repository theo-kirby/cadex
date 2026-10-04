---
node_id: 72072bdd-b2e8-5cb8-9008-8703a72db27f
slug: mild-wood-8803
title: 'orun2 subtraction: the staged engine payload stops carrying LLVM and clang (ADR-531)'
created_at: '2026-10-04T09:13:09+00:00'
parents:
- hidden-glacier-9870
summary: ''
---
## What
The staged engine payload stops carrying LLVM and clang (ADR-531). `package/engine/build_engine_payload.sh` deletes `lib/libLLVM*`, `lib/libclang*`, `lib/libLTO.so*`, `lib/libRemarks.so*` and `lib/clang` on both staging paths, and its leak gate refuses `libLLVM*`/`libclang*`. Its header no longer says the Blender shell carries the payload. Two tests are in `test_headless_import_guardrails.py`: a static one pins the prune and the gate, and a packaged one (under `CADEX_ENGINE_ROOT`) checks a staged payload. REPORT defect 6, the §3 removals table, §1's footprint note and `docs/cadex-release-packaging.md` carry the numbers.

## Why
The critic's unit: REPORT defect 6, the unchanged installed footprint. I re-checked `nvidia-smi` first, as asked. It still "couldn't communicate with the NVIDIA driver", so the W1 GPU walk on `orun2-w1-robin` could not run, and I took the footprint subtraction instead. I picked the payload rather than `pixi.toml` because the owner deferred the pixi GUI-era dependency audit to the next run. The `.pixi` env is untouched.

## Method
- Ran `readelf -d` over every ELF in a payload staged at `68b60f26`, which gave 10,127 NEEDED entries. The LLVM/clang family is needed only by itself, and no other payload library names it as a string (no dlopen).
- Checked the env's `conda-meta` to see what pulls each library in. `qt6-main` pulls libllvm20, libclang-cpp20.1 and libclang13 (Qt doc/translation tools). `pyside6` pulls libclang13 (the shiboken generator). The `clang` compiler pulls libllvm21, libclang-cpp21.1 and compiler-rt. So these are GUI tooling plus the build compiler, and nothing uses them at run time.
- Staged the same tree with the old script (git stash) and with the new one, and measured each with `du -sb`.

## Result
- **Payload size.** 3,258,031,078 B and 40,916 files before, 2,588,443,821 B and 40,578 files after. That is −669,587,257 B (−20.6%).
- **Packaged gate.** `CADEX_ENGINE_ROOT=<restaged payload>` pytest of `test_cadexd_lifecycle.py`, the guardrails and `test_licensing_compliance.py`: 39 passed, 0 skipped. This includes the new packaged test.
- **Engine suite.** `pixi run test-engine`: 2575 passed, 57 skipped.
- **CLI suite.** Run CPU-only (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`): 1420 passed, 1 skipped (20 min 27 s).

Still open:
- The payload still copies node, perl, opencv, pcl and `lib/gcc`.
- The `.pixi` env (5.65 GB) is unchanged; the owner deferred that audit.
- W1's 5090 leg still waits on the driver (REPORT defect 5).

The tail now has 1 unreconciled record.

Dispatch closed: 1 unit — staged payload drops LLVM/clang (−669.6 MB, −20.6%), ADR-531, defect 6 updated

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 9af3580dc6565a5ae3e4fe76d64dc0ef9992dd60

## State Impact

- target: forest-wind-0342 — The staged engine payload no longer carries LLVM/clang (libLLVM 20/21, libclang-cpp, libclang 13, libLTO, libRemarks, lib/clang), which no payload ELF links; the leak gate refuses them (ADR-531). Staged size 3,258,031,078 B -> 2,588,443,821 B (-20.6%); packaged gate green.
