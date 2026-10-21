# Documentation procedures

Read the relevant section when directed by [AGENTS.md](AGENTS.md#required-procedures).
Document selection and placement are defined in [repository guidance](AGENTS.md).

## Analysis writing

Apply these requirements when creating or substantively revising an analysis:

- Start with the question, intended reader, scope, and principal finding. State
  what the evidence establishes and which questions remain open.
- Identify the source repository and exact commit for each codebase examined,
  including the relevant source revision for CI evidence. Include the analysis
  date in `Asia/Seoul` and related ticket or PR identifiers when applicable.
  Record relevant branch, build mode, local modifications, and instrumentation
  when they affect the findings.
- Explain the responsibilities and caller contract before implementation
  details. Cover the relevant structures, ownership and lifetime, main execution
  paths, and failure handling. For concurrency or storage claims, explain the
  synchronization, invariants, and recovery boundaries needed to assess them.
- Support behavioral claims with revision-pinned source links or repository
  paths and line references tied to the stated commit. Distinguish source
  findings, runtime observations, inferences, and proposals. Keep historical
  findings at their original revision; a newer report must identify what was
  revalidated before applying them to a newer revision.
- For experiments and verification, record the inputs, commands, configuration,
  observed results, and limitations needed to reproduce the conclusion. Retain
  concise evidence in the report; select supporting files under
  [What belongs in Git](AGENTS.md#what-belongs-in-git).
- Scale the format to the question. Markdown is the default; use diagrams,
  tables, or HTML when they materially help the reader. Comparisons with other
  systems and multi-chapter books are additions for an established need.

## Analysis moves

- When reorganizing existing analyses, preserve source revisions and historical
  conclusions. Update repository-relative links, reader-facing path references,
  and affected indexes together; leave source-worktree paths and recorded
  experiment environments intact.
- Account for every moved file under
  [What belongs in Git](AGENTS.md#what-belongs-in-git). For explicitly requested
  cleanup of previously tracked working material, preserve useful local copies
  in an ignored path before removing their tracked copies. Check incoming links
  and rendering assets before committing the move.

## README index

Each ticket or analysis topic directory's `README.md` is a curated navigation
guide to its important Markdown documents, including those in subdirectories.
Changes to supporting or local working files alone do not require an index update.
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

Apply [What belongs in Git](AGENTS.md#what-belongs-in-git) to the entire incoming
task branch, including work produced by other agents or skills.

1. Stage explicit paths. Inspect `git diff --cached --name-status` and
   `git diff --cached`; every staged file must qualify for retention. Check
   document and supporting-file links against retained repository files.
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
