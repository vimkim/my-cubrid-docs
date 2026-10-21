# Repository guidance

This repository holds documentation for pull-request work in
[`CUBRID/cubrid`](https://github.com/CUBRID/cubrid). Keep the related writing here:
code analysis, research, surveys, PR body drafts, CI analysis, detailed testcase
failure analysis, PR comment analysis, review guides, and review reply drafts.

Before CUBRID-related work, read `/home/vimkim/my-cubrid/CUBRID.md`; its personal
CUBRID policies take precedence over repository-local guidance.

## Document selection

- Keep documents with lasting value for a ticket or PR reader: substantive
  analysis or research, accepted designs and specifications, review guides,
  CI or failure reports, and PR bodies or review replies prepared for use.
  Select by content and reader value; a `.md` extension alone is insufficient.
- Keep scratch notes, intermediate drafts, session transcripts, raw CI
  downloads, build/test logs, generated inventories, and caches in ignored
  local paths. Summarize useful results, revisions, commands, and limitations
  in the selected documents. Promote important documents out of `.scratch/`
  into their durable location before committing.
- Supporting files qualify only when needed to read, render, or substantiate
  a selected document, such as a diagram, interactive-document assets, or a
  small decisive evidence excerpt. Justify each retained supporting path;
  collecting an artifact does not by itself justify tracking it. Repository
  guidance and ignore configuration are also valid task changes.

## Ticket directories

- Put a ticket's documents in a top-level `CBRD-XXXXX/` directory, with its
  related PR number identified in the directory's `README.md`.
- Search for the ticket before creating a directory. Reuse its existing
  directory and spelling, including legacy lowercase `cbrd-XXXXX/` names.
  Preserve established paths and links.
- Use descriptive filenames. Add subdirectories when they help organize a
  larger investigation; important Markdown documents there belong in the
  ticket's root index.

## Analysis placement

- Put analyses of CUBRID subsystems, architecture, build tooling, and performance
  that serve readers across tickets under `code-analysis/<topic>/`. Use short,
  stable topic names, such as `pgbuf`, `build`, or `lock-manager`; reuse an
  existing topic before creating another. `code-analysis/README.md` is the
  navigation entry for these topics.
- Put an analysis whose main purpose is a ticket or PR decision in that ticket's
  existing directory. Link shared subsystem explanations from there. Extend the
  shared explanation when it has independent reader value; keep the ticket's
  findings and disposition with the ticket.
- Search both the ticket directories and `code-analysis/` before writing. Read
  relevant existing reports and their revision limits; update or extend the
  appropriate report instead of creating a competing explanation of the same
  scope and revision.
- Keep a single report in a descriptive Markdown file. Use a revision or dated
  subdirectory when separating multiple analyses of the same topic. Preserve
  established revision and author suffixes when reusing existing paths.
- Treat `code-analysis/pgbuf/` and `code-analysis/build/` as the destinations for
  the former `pgbuf-analysis/` and `build-analysis/` collections. Add future
  subsystem analyses within `code-analysis/` rather than creating more
  top-level analysis directories.

## Analysis writing

Apply these requirements when creating or substantively revising an analysis:

- Start with the question, intended reader, scope, and principal finding. State
  what the evidence establishes and which questions remain open.
- Identify the source repository and exact commit for each codebase examined.
  Record relevant branch, build mode, local modifications, and instrumentation
  when they affect the findings. Include the analysis date in `Asia/Seoul` and
  related ticket or PR identifiers when applicable.
- Explain the responsibilities and caller contract before implementation
  details. Cover the relevant structures, ownership and lifetime, main execution
  paths, and failure handling. For concurrency or storage claims, explain the
  synchronization, invariants, and recovery boundaries needed to assess them.
- Support behavioral claims with revision-pinned source links or repository
  paths and line references tied to the stated commit. Distinguish source
  findings, runtime observations, inferences, and proposals. Keep historical
  findings at their original revision; a newer report must identify what was
  revalidated before applying them to a newer revision.
- For experiments, record the inputs, commands, configuration, observed
  results, and limitations needed to reproduce the conclusion. Retain concise
  evidence in the report; apply Document selection to supporting files.
- Scale the format to the question. Markdown is the default; use diagrams,
  tables, or HTML when they materially help the reader. Comparisons with other
  systems and multi-chapter books are additions for an established need.
- Finish by updating the topic or ticket index and checking links to retained
  documents and supporting files.

## Analysis moves

- When reorganizing existing analyses, preserve source revisions and historical
  conclusions. Update repository-relative links, reader-facing path references,
  and affected indexes together; leave source-worktree paths and recorded
  experiment environments intact.
- Account for every moved file under Document selection. For explicitly
  requested cleanup of previously tracked working material, preserve useful
  local copies in an ignored path before removing their tracked copies. Check
  incoming links and rendering assets before committing the move.

## README index

Each ticket or analysis topic directory's `README.md` is a curated navigation
guide to its important Markdown documents, including those in subdirectories.
Update it in the same change when an important document is created, modified,
moved, or removed. Changes to supporting or local working files alone do not
require an index update. Create the README if missing when adding an important
document.
The collection index at `code-analysis/README.md` links topic indexes or existing
report entry points; each topic index lists its important Markdown documents.

Maintain one table row per selected important Markdown document. A row for the
README itself is optional. When revising an existing index, trim artifact-only
rows while preserving useful context and navigation. Link necessary supporting
files from the relevant document rather than giving each artifact an index row.
Use this schema:

```markdown
| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [review-guide.md](review-guide.md) | PR background and reviewer navigation | YYYY-MM-DD | YYYY-MM-DD | Help reviewers understand the change |
```

- Link each file with a path relative to its index README. Keep each row on
  one source line and descriptions brief and useful to a reader new to the PR.
- Record dates as `YYYY-MM-DD` in `Asia/Seoul`. A new file starts with the same
  creation and modification date; subsequent edits preserve its creation date
  and original creation reason and update its modification date.
- For existing files, use documented dates or Git history when available.
  Mark unavailable dates as `Unknown` rather than inventing them.
- Update existing rows rather than duplicating them. Refresh descriptions and
  links when a file's contents or location change. Update the README's own
  modification date once per change.
- Before committing, check that every selected important Markdown document has
  an accurate row and that index links resolve to files included in the repository.

## Commit and local merge checks

Apply Document selection to the entire incoming task branch, including work
produced by other agents or skills.

1. Stage explicit paths. Inspect `git diff --cached --name-status` and
   `git diff --cached`; every staged file must qualify under Document selection.
2. Keep excluded local material with narrowly scoped `.gitignore` rules; verify
   them with `git check-ignore -v -- <paths>`. Check `git ls-files -- <paths>`
   because ignore rules do not untrack files. For excluded artifacts introduced
   by this task, preserve useful local copies and remove them from the task's
   tracked changes. Previously merged material needs a separate, explicitly
   requested cleanup rather than incidental removal.
3. Before handing the branch back, inspect both
   `git diff --name-status main...HEAD` and
   `git log --format= --name-status main..HEAD`. Review every incoming path and
   its contents, including files added and later deleted in task commits. If
   excluded artifacts are already committed, prepare curated task commits so
   those artifacts do not enter main's history; a later deletion is insufficient.
   Preserve the original branch and useful local artifacts while preparing them.
4. Report the selected documents, reasons for retained supporting/configuration
   files, and checks. Follow the user's confirmation workflow for local
   integration. After rebasing onto the current `main`, repeat the full selection
   audit immediately before `git merge --ff-only`. Merge only when every incoming
   path qualifies and document links resolve to retained repository files.
5. Inspect ignored files before removing the merged task worktree and preserve
   valuable local working material outside it.

## PR evidence

Identify the relevant ticket, PR, and source revision in analyses that depend on
code or CI state. Record commands, results, and limitations for verification;
distinguish observed evidence from hypotheses. Keep revision-specific historical
findings identifiable when adding newer results.
