<!--
Record node content template. Headings are exact — the checker parses them (SPEC I2).
Title (backend field, not in content): short past-tense summary of the unit of work.
Summary (backend field): one sentence, or empty.
-->

## What

One paragraph: the unit of work this node records. Past tense, concrete.

## Why

Causal link to the parent node(s): what result/decision led here. If this opens a new
independent workstream branched from the root, say so.

## Method

Enough detail for a third party to reproduce or audit: commands, parameters, data,
environment. Point at attached artifacts by title where they carry the load.

## Result

What actually happened, including failures. Numbers over adjectives. Interpretation
goes here too — what this result means, what it rules out.

## Repo

- repo: <repo_url or none>
- branch: <branch_name>
- commit: <head_commit_sha>

## State Impact

<!-- EITHER one or more impact lines: -->
- target: <state-slug> — <delta: status flip / new claim / new negative knowledge / supersession>
- target: NEW <kebab-name> — <delta: what the new state node covers and its initial status>
<!-- OR exactly one none-line with a non-empty reason: -->
none: <why this changes nothing about current state>
