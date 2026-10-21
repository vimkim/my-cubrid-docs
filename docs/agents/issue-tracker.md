# Issue tracker: Local Markdown

Specs and engineering tickets live as Markdown files under `.scratch/`.

## Conventions

- One effort per directory: `.scratch/<feature-slug>/`
- Spec: `spec.md`
- Map: `map.md`
- Tickets: `issues/<NN>-<slug>.md`, numbered from `01`
- Write one file per ticket.
- Record triage state in a `Status:` line using `triage-labels.md`.
- Append discussion under `## Comments`.

## Skill operations

When a skill says “publish to the issue tracker,” write the corresponding
local Markdown file. When it says “fetch the relevant ticket,” read the
referenced local file.

## Progress tracking

Work-tracker records durable effort status; local files hold the detailed
specification and tickets. Reference existing work-tracker IDs in the spec
and map, and reuse those entries.

Local ticket numbers are scoped to their effort directory. They are
distinct from work-tracker IDs and CUBRID JIRA keys.

Promote documents with lasting reader value from `.scratch/` according to
the repository's document-selection rules.

## Wayfinding

- Blocking edge: `Blocked by: NN, NN`
- Claim: set `Status: claimed` before starting.
- Resolve: add `## Answer`, set `Status: resolved`, and update the map.
