<!--
State node content template. Written ONLY by reconcile (SPEC I3).
First non-blank line MUST be the Status line (SPEC I6).
Title (backend field): the component/capability name, present tense.
-->

Status: working | open | broken | blocked | superseded

## Current

What is true now about this component, as short claims. Every claim cites the record
node(s) that establish it inline: `... retry-on-409 works [rec: quiet-snow-3839].`
If status is `superseded`, name the replacing state node here. If `blocked`, name the
blocker.

## Negative knowledge

- [scope: <where this applies> | confidence: low|medium|high | evidence: <record-slug>, <record-slug>] <what does not work and why>
- [scope: general — <area> | confidence: high | evidence: <slug> | decision: <decision-record-slug>] <generalization — requires its own decision record (SPEC I7)>

None yet. <!-- use this line alone when the section is empty -->

## Provenance

- <record-slug> — <why this record node informs this state node>
- <record-slug> — <why>
