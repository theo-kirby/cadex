---
node_id: 7c32cdf9-cef7-5649-a02f-cb4961e37578
slug: eager-garden-8009
title: Audit translation updater and qualify only the deleted GUI writer
created_at: '2026-09-07T04:52:37+00:00'
parents:
- hollow-reef-8734
summary: ''
---
## What

Complete the offline dependency audit of src/Tools/updatecrowdin.py in docs/TRANSLATION-UPDATER-AUDIT.md. Update ADR-232, the inherited ledger and the audit ROADMAP checkbox. Qualify exactly one later subtractive boundary: the deleted GUI Translator.cpp writer, its two internal dispatch call sites and exclusive PySide import. No implementation.

## Why

Follow hollow-reef-8734 and short rank 1 for mission 3, round-glacier-2865 and green-sea-3991. The current plan selects this audit; the overseer's reconciliation message is for the separate owning roles, not permission for an actor to reconcile. Assume external maintenance use is unknown and retain the tool plus App/Base resources. Accessory delivery remains blocked with no new candidate search. Whole-tool deletion is unsupported by the evidence.

## Method

Read actor and hypergraph-record skills, STATE, PLAN, the parent bet, VISION and source/docs. Static AST/literal inspection only of the updater: enumerate 27 locations and all command branches; read writer bodies, App CMake, SetupQt, Application, TranslationQtBridge and Base translation exposure. Search tracked references, CMake/pixi/package rules and existing release build/install outputs. Do not import or execute the updater, inspect credentials, contact any network service or write translation resources. Record reproduction paths, compatibility cost, separate disable/delete stages and future retained-translation/build/gate requirements. No state, plan or charter edits.

## Result

App and Base retain 39 TS files each. Two duplicate App rows have both paths; Base has a directory but no QRC and still copies TS because it does not generate QM here. The other 24 rows lack both destinations. Upload discovers sources independently. Headless App compiles both translation families and installs the Qt bridge. The sole GUI writer target is deleted; exactly two internal call sites and no tracked external caller were found. External users are unmeasured: retirement removes their GUI-registration side effect. No whole-tool, resource/Qt, gather or location cleanup qualifies. Next: short rank 2's evidence-only disposition and later bounded bet, before any implementation; preserve separate disable/delete commits.

Validation: licensing suite 10 passed / 1 skipped in 0.22 s; packaged-license skip is CADEX_ENGINE_ROOT unset. Diff check passed; export and explicit record/state graph check passed with zero violations/warnings before minting, and will be repeated for the new node. Initial check invocation omitted required cache arguments and exited 2; corrected invocation passed. No full engine suite, build, packaged lifecycle, shell gate or runtime translation probe; documentation-only evidence makes no such claim. Inherited source, manifest and fork delta are unchanged. The supplied one-record tail becomes two with this unit; reconciliation remains with the maintainer.

Dispatch closed: 1 unit — offline updater audit qualifies only the deleted GUI translator writer for a later bet.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 2caba553eed38d6bc544bdd94e9fc70fba4906d5

## State Impact

- target: round-glacier-2865 — Offline updater audit qualifies only the deleted GUI translator writer and two call sites plus exclusive import; App/Base translation consumers remain live, external usage unknown; later bet and separate disable/delete required.
- target: green-sea-3991 — Updater audit changes no inherited source or manifest and claims no delta reduction; only a bounded future writer removal is qualified.
