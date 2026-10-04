---
node_id: 7a499027-314e-52f3-8b9f-29a9ec83b026
slug: placid-ocean-8336
title: 'orun2 subtraction: the staged engine payload stops carrying OpenCV, PCL, Node and Perl (ADR-532)'
created_at: '2026-10-04T09:42:56+00:00'
parents:
- mild-wood-8803
summary: ''
---
## What

The staged engine payload stops carrying OpenCV, PCL, Node and Perl (ADR-532). `package/engine/build_engine_payload.sh` now deletes `lib/libopencv*`, `lib/libpcl*`, `lib/libnode.*`, `lib/node_modules`, `lib/perl5`, `share/perl5`, `share/opencv4`, `share/pcl-*`, `site-packages/cv2` and its two `opencv_python*` dist-info stubs, on both staging paths. The leak gate refuses the libraries, `cv2`, `lib/node_modules` and `lib/perl5`. Two tests are added to `test_headless_import_guardrails.py`: a static one pins the prune and the gate, and a packaged one (under `CADEX_ENGINE_ROOT`) checks a staged payload. ADR-532 is written, `docs/cadex-release-packaging.md` is updated, and REPORT §1, §3 and defect 6 are updated.

## Why

The critic said to run `nvidia-smi` first and do W1 step 7 if the driver loads. It did not load ("couldn't communicate with the NVIDIA driver"), so I took the fallback the critic named: apply ADR-531's readelf/conda-meta method to the next payload slice, which is node, perl, opencv and pcl. `lib/gcc` and `.pixi` were left alone, as instructed. This is long-term rung 3 (further subtraction), plus REPORT defect 6.

## Method

- Ran `readelf -d` over all 1,764 ELFs of the payload staged at `7cdf79a9` and built a NEEDED map.
  - No ELF outside each family links `libopencv*`, `libpcl*` or `libnode*`. The one exception is `site-packages/cv2/.../cv2.cpython-311-*.so`.
  - No ELF in `bin/`, `lib/*.so*` or `Mod/` contains any of those names as a dlopen string.
- Imports: the only `import cv2` in payload `.py` files is `Mod/Assembly/CommandCreateSimulation.py:1155`. That is the GUI's video export, reached only via `InitGui.py`/`Gui.addCommand`, so headless never loads it. No `"cv2"` string import appears anywhere else. `cli/`, `training/` and `analysis/` do not import it. Films are encoded by `cli/cadex_cli/video.py` with system `ffmpeg`.
- conda-meta says why each slice is there:
  - `opencv` and `pcl` are direct `pixi.toml` deps with no conda dependent;
  - `nodejs` comes in through `pyright`;
  - `perl` comes in through `git`.
  - The payload's `bin/` has only FreeCADCmd, CadexGeometryWorker and python, so there is no node or perl interpreter.
- Measured by staging the same tree twice: first with the old script (stashed), then with the new one.
- Ran a NEEDED-resolution pass on the new payload. Nothing new is unresolved. The unresolved list is the same system libc set, the pre-existing pruned Qt GUI libs and one absolute sqlite path. All of these predate this unit.

## Result

- **Size:** 2,588,443,821 B / 40,578 files → **2,213,397,834 B / 36,594 files**. That is −375,045,987 B (−14.5%). Together with ADR-531 the payload is −32.1% against 3,258,031,078 B.
- **Packaged gate:** `CADEX_ENGINE_ROOT=<restaged payload>` pytest of `test_cadexd_lifecycle.py` + guardrails + `test_licensing_compliance.py`: **41 passed**, 0 skipped. This includes the new packaged test.
- **Engine suite:** `pixi run test-engine`: **2576 passed, 58 skipped**. That is +1 static test, and +1 packaged test that skips without an engine root.
- **CLI suite (GPU hidden):** **1420 passed, 1 skipped** (run before the doc edits; `test_project_docs.py` re-run after them: 40 passed).
- **Concern for the next slice:** nine libraries lost their last NEEDED user with this prune and were deliberately not swept up: `libQt6Test`, `libavif`, `libboost_iostreams`, `libbrotlidec`, `libbrotlienc`, `libcares`, `libjasper`, `libuv`, `libwebpdecoder`. Each needs its own dlopen/ctypes check before pruning. `share/` also still carries git-core, postgres/mysql samples, gtk and other dev material that the same method could audit.
- `share/licenses/opencv4` stays in the payload. It is a harmless extra licence text.
- **W1 step 7 is still blocked on the NVIDIA driver.** It is the one open criterion.

Dispatch closed: 1 unit — payload stops carrying OpenCV/PCL/Node/Perl (ADR-532), −375 MB, gates green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 27381a446f0ff1f5f9c339211976cc92d293eaa7

## State Impact

- target: forest-wind-0342 — The staged engine payload no longer carries OpenCV (libs, cv2), PCL, Node (libnode, npm) or Perl (lib/perl5), which no payload ELF or module uses; the leak gate refuses them (ADR-532). Staged size 2,588,443,821 B -> 2,213,397,834 B (-14.5%; -32.1% with ADR-531); packaged gate green.
