# Repository guidance

This repository holds documentation for pull-request work in
[`CUBRID/cubrid`](https://github.com/CUBRID/cubrid). Keep the related writing here:
code analysis, research, surveys, PR body drafts, CI analysis, detailed testcase
failure analysis, PR comment analysis, review guides, and review reply drafts.

Before CUBRID-related work, read `/home/vimkim/my-cubrid/CUBRID.md`; its personal
CUBRID policies take precedence over repository-local guidance.

## Ticket directories

- Put a ticket's documents in a top-level `CBRD-XXXXX/` directory, with its
  related PR number identified in the directory's `README.md`.
- Search for the ticket before creating a directory. Reuse its existing
  directory and spelling, including legacy lowercase `cbrd-XXXXX/` names.
  Preserve established paths and links.
- Use descriptive filenames. Add subdirectories when they help organize a
  larger investigation; their files still belong in the ticket's root index.

## README index

Each ticket directory's `README.md` is a friendly entry point and file index.
Whenever you create or update a file anywhere under that directory, update this
README in the same change. Create the README if it is missing and preserve
useful existing context and navigation.

Maintain one Markdown table row per file, including nested documents, supporting
artifacts, and the README itself. Use this schema:

```markdown
| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [README.md](README.md) | Ticket overview and file index | YYYY-MM-DD | YYYY-MM-DD | Help readers find the ticket's documents and evidence |
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
- Before committing, check that every created or modified ticket file has an
  accurate row and that its link resolves.

## PR evidence

Identify the relevant ticket, PR, and source revision in analyses that depend on
code or CI state. Record commands, results, and limitations for verification;
distinguish observed evidence from hypotheses. Keep revision-specific historical
findings identifiable when adding newer results.
