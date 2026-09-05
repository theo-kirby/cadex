---
node_id: 02e3eb53-ee9b-5a31-9823-698b228ced6c
slug: idle-arrow-2946
title: Installed the native Blender recipe build locally
created_at: '2026-09-05T11:33:28+00:00'
parents:
- simple-bramble-8616
summary: ''
---
## What

Installed the verified native Blender recipe build into the standard macOS Applications location at the owner's explicit request.

## Why

Follows simple-bramble-8616: the implementation and application build were complete, but the previously installed application had not yet been updated.

## Method

Ran `bash package/app/build_app.sh install`, using its incremental bundle copy and Launch Services registration. Compared the installed executable, shell cadexd client and bundled Blender evaluator against the verified build with `cmp`.

## Result

Installation and all three byte comparisons exited 0. No application was launched or running user session replaced. This is the existing local-install arrangement; the bundled engine continues to resolve libraries from the checkout. No product source changed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 14d484ccb51bbbc25bd58c4e3f48df998586e1cb

## State Impact

none: Local installation of an already verified build; no product architecture or frontier change.
