# Repository guidance

This repository holds lasting CUBRID analysis and PR documentation.

Before CUBRID-related work, read `/home/vimkim/my-cubrid/CUBRID.md`.
Its personal policies override repository-local guidance.

## What belongs in Git

- Keep substantive analysis, research, accepted designs, review guides,
  CI/failure reports, and PR bodies or review replies prepared for use.
- Keep scratch notes, intermediate drafts, transcripts, raw downloads,
  logs, generated inventories, and caches in ignored local paths.
  Summarize useful evidence in durable documents; promote selected documents
  out of scratch paths before committing.
- Retain supporting files only when needed to read, render, or substantiate
  a selected document. Justify each retained supporting path.
  Repository guidance and ignore configuration also qualify.

## Where documents belong

- Search ticket directories and `code-analysis/` before writing.
  Read relevant reports and their revision limits; extend an existing
  report when its scope matches.
- Put ticket-specific documents in top-level `CBRD-XXXXX/` directories.
  Reuse existing directories and spelling, including lowercase names.
  Identify related PRs in the directory's `README.md`.
- Put shared subsystem, architecture, build, and performance analyses in
  `code-analysis/<topic>/`. Reuse short, stable topic names.
  Keep ticket decisions with the ticket and link shared explanations.
- Use descriptive filenames and one Markdown file per report.
  Use revision or dated subdirectories when needed; preserve established
  revision and author suffixes.

## Required procedures

Read the relevant section of `DOCUMENTATION.md` before the named action:

- **Create or substantively revise an analysis:** follow
  [Analysis writing](DOCUMENTATION.md#analysis-writing) for scope,
  source revisions, evidence, technical explanation, and experiments.
- **Move existing analyses:** follow
  [Analysis moves](DOCUMENTATION.md#analysis-moves) to preserve historical
  findings, experiment records, links, and rendering assets.
- **Create, modify, move, or remove an important Markdown document:**
  update its ticket or topic README in the same change, following
  [README index](DOCUMENTATION.md#readme-index).
  Create a missing index; keep `code-analysis/README.md` navigable.
- **Commit, hand back a branch, or merge locally:** follow
  [Commit and local merge checks](DOCUMENTATION.md#commit-and-local-merge-checks).
  Audit the entire incoming history, including other agents' changes.
  Preserve valuable local material before cleanup.

These procedures supplement the inherited Git workflow.
