# CBRD-28095 PR body revision 2 context

Resume metadata for the revised body of the existing PR. This file is not
uploaded. Revision 1 (`pr-body.md`, `pr-context.md`) stays as published.

## Source

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28095](https://jira.cubrid.org/browse/CBRD-28095) |
| Source commit | `bfb6a0e57c1d986814f14390ebcac9e24d3470f4` |
| Previous source commit | `f3c1284ff4088d703d621f9c76d96877b74bfd33` (revision 1) |
| Source branch | `CBRD-28095` on `vk` = `github.com/vimkim/cubrid` |
| Observed remote head | `bfb6a0e57c` (pushed 2026-11-25 by this task, user request "음 넣고 ci 다시 돌리자.") |
| Base | `develop` at `bfb59bdd13` |

## Target

| Field | Value |
| --- | --- |
| Target repository | `CUBRID/cubrid` |
| Operation | `update` |
| PR | [CUBRID/cubrid#8737](https://github.com/CUBRID/cubrid/pull/8737), open, draft |
| Existing title | `[CBRD-28095] Fix coll_name overflow in catcls_get_db_collation` |
| Proposed title | `[CBRD-28095] Fix string copy bounds in catcls_get_db_collation` |
| Original body SHA-256 | `8e6a0bec6628c851e6680ddea64e43c70ad12abab70988d0776265084dc68c64` (checked 2026-11-25, equals `pr-body.md`) |

## Documents

| Role | Path |
| --- | --- |
| PR body | `cbrd-28095/pr-body-rev2.md` |
| Context | `cbrd-28095/pr-context-rev2.md` |
| Docs task branch | `cbrd-28095-pr-body-rev2` |
| Docs integration branch | `main` (`origin` = `github.com/vimkim/my-cubrid-docs`) |

## Verification evidence (2026-11-25, source `bfb6a0e57c`)

- `debug_gcc` build and install: success.
- checksum injection (gdb, `csql -S`, collation id 5, 40-char checksum,
  `assert (str_len == 32)` skipped by `jump`, sentinel `0x7f7f7f7f` written
  to the next element's `coll_id`):
  - Control (`f3c1284ff4` build, checksum unfixed): `strlen(checksum)=40`
    in a 33-byte array, next element `coll_id=0x58585858` ("XXXX").
  - Fixed: `strlen(checksum)=32`, next element `coll_id=0x7f7f7f7f`.
  - Both end with "Collation 'utf8_en_ci' with id 5 has changed" (expected).
- coll_name injection rerun on `bfb6a0e57c`: `lang_str_len=31`, `codeset=5`.
- Without injection: `_db_collation` count 10.
- `git merge-tree` of `CBRD-28091` and `bfb6a0e57c`: clean.
- CI: `/run all` at 2026-11-25T10:24:54Z
  (https://github.com/CUBRID/cubrid/pull/8737#issuecomment-7159662235),
  run 45594765535; previous-head run 45567225552 cancelled.
  `cubrid-pr-tc-base-check` reported FAIL before the trigger (tc/pr-8737
  behind TC develop by 4 public / 7 private commits; all of them test engine
  commits after the engine base `bfb59bdd13`).

## Proposed publication operations (require explicit confirmation)

1. Docs: rebase `cbrd-28095-pr-body-rev2` onto `main`, `git merge --ff-only`,
   push `main` to `origin`, remove the docs task worktree and branch.
2. GitHub: `gh pr edit 8737 --repo CUBRID/cubrid --body-file
   cbrd-28095/pr-body-rev2.md --title "[CBRD-28095] Fix string copy bounds in
   catcls_get_db_collation"` (title change only if approved). Draft status kept.

## Publication record

Confirmed by the user in conversation on 2026-11-25 ("좋아.").

- Docs: `cbrd-28095-pr-body-rev2` fast-forwarded into `main` and pushed
  (`dce0a1b..76b03ee`).
- GitHub: `gh pr edit 8737` updated the body and title. Verified live title
  `[CBRD-28095] Fix string copy bounds in catcls_get_db_collation`, draft
  kept, head `bfb6a0e57c`, body SHA-256
  `6fa9bce9976409f089562d6666050f8e5c3a1335c8fe740e2258179495669355`
  (equal to `pr-body-rev2.md`).
