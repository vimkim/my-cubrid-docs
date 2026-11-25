# CBRD-28091 PR draft context

Resume metadata for the PR body draft. This file is not uploaded.

## Source

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28091](https://jira.cubrid.org/browse/CBRD-28091) |
| Source commit | `b6c1823f5484205c32eacc1de4fb9c33ab4b24d2` |
| Source branch | `CBRD-28091` (local only) |
| Base | `develop` at `bfb59bdd13` (`origin/develop`, fetched 2026-11-25) |
| Source push remote | `vk` = `github.com/vimkim/cubrid` |
| Observed remote head | Branch does not exist on `vk` (checked 2026-11-25) |
| Existing PR | None found in `CUBRID/cubrid` for `CBRD-28091` (checked 2026-11-25) |
| Related PR draft | `cbrd-28095/pr-body.md` (same function, independent branch; `git merge-tree` of both branches is clean) |

## Target

| Field | Value |
| --- | --- |
| Target repository | `CUBRID/cubrid` |
| Operation | `create` |
| Proposed title | `[CBRD-28091] Fix realloc failure check in catcls_get_db_collation` |
| Head | `vimkim:CBRD-28091` |
| Base | `develop` |
| Status | Draft |
| Assignee | `vimkim` |

## Documents

| Role | Path |
| --- | --- |
| PR body | `cbrd-28091/pr-body.md` |
| Context | `cbrd-28091/pr-context.md` |
| Explanation | None |
| Docs task branch | `cbrd-28091-28095-pr-body` |
| Docs integration branch | `main` (`origin` = `github.com/vimkim/my-cubrid-docs`) |

## Verification evidence (2026-11-25, source `b6c1823f54`)

- `debug_gcc` configure, build, and install: success; no new warnings in `catalog_class.c`.
- gdb fault injection, `csql -S -u dba testdb` (SA mode), breakpoints in
  `catcls_get_db_collation ()`: set `max_coll_cnt` 256 -> 2, skip the
  `db_private_realloc ()` call and set its result to NULL.
  - Control (unfixed realloc code, CBRD-28095 build on the same base):
    `*db_collations=(nil)` after the check, SIGSEGV in `memset`,
    `curr_coll = 0x98`, old buffer `0x55555565aca8` lost.
  - Fixed: `error=-3`, `*db_collations` equals the old buffer
    (`0x55555565aca8`, first name `iso88591_bin`), `boot_restart_server ()`
    frees it (boot_sr.c:2649), restart ends with "Out of virtual memory:
    unable to allocate 304 memory bytes.", exit code 1, no crash.
  - Without injection: `select count(*) from _db_collation` returns 10.
- `ctest`: not run; no configured test covers `catcls_get_db_collation ()`.
- `cubrid-static-check bfb59bdd13..b6c1823f54`: cppcheck 0, clang-tidy
  (bugprone) 0, new clones 0, complexity flags 0 (`catcls_get_db_collation`
  CCN 29, length 203 -> 208). No dispositions needed.

## Proposed publication operations (require explicit confirmation)

1. Docs: rebase `cbrd-28091-28095-pr-body` onto `main`, `git merge --ff-only`,
   push `main` to `origin`, remove the docs task worktree and branch
   (shared with the CBRD-28095 draft).
2. Source: `git push vk CBRD-28091` (new branch, no force).
3. GitHub: `gh pr create --draft --repo CUBRID/cubrid --base develop
   --head vimkim:CBRD-28091` with the proposed title,
   `cbrd-28091/pr-body.md` as the body, and assignee `vimkim`.

## Publication record

Not started.
