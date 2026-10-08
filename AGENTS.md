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

## README index

Each ticket directory's `README.md` is a curated navigation guide to its
important Markdown documents, including those in subdirectories. Update it in
the same change when an important document is created, modified, moved, or
removed. Changes to supporting or local working files alone do not require an
index update. Create the README if missing when adding an important document.

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

- Link each file with a path relative to the ticket README. Keep each row on
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
