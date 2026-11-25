# CBRD-28095 PR draft context

Resume metadata for the PR body draft. This file is not uploaded.

## Source

| Field | Value |
| --- | --- |
| Ticket | [CBRD-28095](https://jira.cubrid.org/browse/CBRD-28095) |
| Source commit | `f3c1284ff4088d703d621f9c76d96877b74bfd33` |
| Source branch | `CBRD-28095` (local only) |
| Base | `develop` at `bfb59bdd13` (`origin/develop`, fetched 2026-11-25) |
| Source push remote | `vk` = `github.com/vimkim/cubrid` |
| Observed remote head | Branch does not exist on `vk` (checked 2026-11-25) |
| Existing PR | None found in `CUBRID/cubrid` for `CBRD-28095` (checked 2026-11-25) |
| Related PR draft | `cbrd-28091/pr-body.md` (same function, independent branch; `git merge-tree` of both branches is clean) |

## Target

| Field | Value |
| --- | --- |
| Target repository | `CUBRID/cubrid` |
| Operation | `create` |
| Proposed title | `[CBRD-28095] Fix coll_name overflow in catcls_get_db_collation` |
| Head | `vimkim:CBRD-28095` |
| Base | `develop` |
| Status | Draft |
| Assignee | `vimkim` |

## Documents

| Role | Path |
| --- | --- |
| PR body | `cbrd-28095/pr-body.md` |
| Context | `cbrd-28095/pr-context.md` |
| Explanation | None |
| Docs task branch | `cbrd-28091-28095-pr-body` |
| Docs integration branch | `main` (`origin` = `github.com/vimkim/my-cubrid-docs`) |

## Verification evidence (2026-11-25, source `f3c1284ff4`)

- `debug_gcc` configure, build, and install: success; no new warnings in `catalog_class.c`.
- gdb injection, `csql -S -u dba testdb` (SA mode): replace `lang_str` of
  collation id 5 (`utf8_en_ci`) with the 32-char
  `utf8_aaaaaaaaaaaaaaaaaaaaaaaaaaa` before its length is computed.
  - Control (unfixed `coll_name` code, CBRD-28091 build on the same base):
    `lang_str_len=32`, at the next row `codeset=0`, `strlen(coll_name)=32`,
    byte at `coll_name+32` = `0x00`.
  - Fixed: `lang_str_len=31`, at the next row `codeset=5`,
    `strlen(coll_name)=31`, byte at `coll_name+32` = `0x05` (codeset intact).
  - Both runs end with the expected "Names of collation with id 5 do not
    match" restart error, because the injected name differs from the loaded
    collation (as recorded in the JIRA issue).
  - Without injection: `select count(*) from _db_collation` returns 10.
- `ctest`: not run; no configured test covers `catcls_get_db_collation ()`.
- `cubrid-static-check bfb59bdd13..f3c1284ff4`: cppcheck 0, clang-tidy
  (bugprone) 0, new clones 0, complexity flags 0. No dispositions needed.

## Proposed publication operations (require explicit confirmation)

1. Docs: same docs integration as the CBRD-28091 draft (one operation).
2. Source: `git push vk CBRD-28095` (new branch, no force).
3. GitHub: `gh pr create --draft --repo CUBRID/cubrid --base develop
   --head vimkim:CBRD-28095` with the proposed title,
   `cbrd-28095/pr-body.md` as the body, and assignee `vimkim`.

## Publication record

Confirmed by the user in conversation on 2026-11-25.

- Docs: `cbrd-28091-28095-pr-body` fast-forwarded into `main` and pushed to
  `origin` (`98021a7..be49bb7`).
- Source: `git push vk CBRD-28095` created the branch; remote head verified
  equal to `f3c1284ff4`.
- GitHub: created draft PR [CUBRID/cubrid#8737](https://github.com/CUBRID/cubrid/pull/8737)
  (base `develop`, head `vimkim:CBRD-28095`, assignee `vimkim`).
- Published body SHA-256 `8e6a0bec6628c851e6680ddea64e43c70ad12abab70988d0776265084dc68c64`, equal to `cbrd-28095/pr-body.md`.
