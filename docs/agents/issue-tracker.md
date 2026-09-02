# Issue tracker: Local Markdown

Issues and specs for this repo live as Markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`
- Triage state is recorded as a `Status:` line near the top of each issue file
- Comments and conversation history append under `## Comments`

## Publishing

When a skill says “publish to the issue tracker,” create a file under `.scratch/<feature-slug>/`.

When a skill says “fetch the relevant ticket,” read the referenced local Markdown file.

## Wayfinding

- Map: `.scratch/<effort>/map.md`
- Child ticket: `.scratch/<effort>/issues/NN-<slug>.md`
- Blocking edge: `Blocked by: NN, NN`
- Claim: set `Status: claimed`
- Resolve: add `## Answer`, set `Status: resolved`, and update the map
