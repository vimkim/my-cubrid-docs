# CBRD-26357: engine PR #7990 body context (revision `dcbf09e`)

Prepared: 2026-10-27, Asia/Seoul. Agent: `claude`.
Status: prepared; publication record below.
This context does not establish publication permission.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | https://jira.cubrid.org/browse/CBRD-26357 |
| Operation | `update` existing body |
| Target repository | `CUBRID/cubrid` |
| PR | https://github.com/CUBRID/cubrid/pull/7990 |
| Existing title | `[CBRD-26357] Add out-of-row overflow storage` |
| Title operation | Preserve |
| PR state | `OPEN`, draft=`false` |
| Draft/ready operation | Preserve |
| Source repository | `CUBRID/cubrid` |
| Source branch | `feature/oos-merge` |
| SOURCE_COMMIT | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Observed remote head | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Base branch | `develop` |
| Previous body revision | [CBRD-26357-oos-engine-pr-body_4408135_claude.md](CBRD-26357-oos-engine-pr-body_4408135_claude.md) ([context](CBRD-26357-oos-engine-pr-context_4408135_claude.md)) |
| Original decoded GitHub body SHA-256 | `0c309c7b9fc6143a684626dc93b3efafb74311f42fa493eb08d633c88a5dff74` (equal to the previous body file) |

## Saved material

- Body: [CBRD-26357-oos-engine-pr-body_dcbf09e_claude.md](CBRD-26357-oos-engine-pr-body_dcbf09e_claude.md).
- Explanation, edited in place (the body links its existing public URL): [CBRD-26357-oos-engine_5a70787_claude.md](CBRD-26357-oos-engine_5a70787_claude.md), `https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-oos-engine_5a70787_claude.md`.
- Docs task branch: `docs/pr7990-engine-pr-body-dcbf09e`. Integration branch: `main` of `vimkim/my-cubrid-docs`.

## Scope of this revision

Requested on 2026-10-27 through the delegating session, after reviewer shparkcubrid's [review 5662427700](https://github.com/CUBRID/cubrid/pull/7990#pullrequestreview-5662427700) and the new head. The [CDC reply](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6435671972) promised to record the CDC decision in the body.

New commits since `4408135c0`:

| Commit | Change |
| --- | --- |
| `1e8701b4f` | Engine. `disk_format()` stamps `DISK_STORAGE_FORMAT_REVISION` (1) into the first volume header field formerly `reserved0` (now `storage_format`). `boot_restart_server` and `xboot_emergency_patch` check it right after mounting volume 0 and refuse other values with new error `ER_BO_INCOMPATIBLE_STORAGE_FORMAT` (-1392). `deletedb` does not check. `PAGE_OOS` and `PERF_PAGE_OOS` move to the end of their page-type ranges. New CTest `test_oos_storage_format_guard` with two fixture items. |
| `d8ed97f77` | Review repair: diagdb prints `storage_format`; `static_assert`s pin the stamp offset and the `PAGE_TYPE`/`PERF_PAGE_TYPE` mirror; the guard test also covers `emergency_patchlog`. |
| `dcbf09e4f` | Test scripts only: fixture ownership compares normalized `databases.txt` fields. |

Body changes (other lines unchanged):

| Bullet | Change |
| --- | --- |
| Implementation, `테스트` | CTest item count 41 to 44 (three items added by `1e8701b4f`). Added so the count agrees with the 42/42 result plus two excluded items. |
| Remarks, `검증` | Keeps the `5a70787` gha-ci result. States that two of the five later commits change the engine. Local OOS CTest 42/42 at `dcbf09e` (`test_oos_real_vacuum_server` and `test_oos_workspace` not run). Cross-build refusal check. No new gha-ci result is claimed. |
| Remarks, `호환성` | Replaces "시작할 때 이런 DB를 거부하지 않습니다." with the boot rejection (-1392, volume header stamp, deletedb still works) and two limitations: one-way only; an old-format backup is restored by restoredb and then refused at startup. |
| Remarks, `범위 밖` | Records the QA agreement: `cbrd_27064`, `cbrd_27075` move to `_25_unstable` in private-ex #4210 (gha-ci `test_shell` skips them), still run in the QA regression; OOS + CDC is implemented in CBRD-26939. |
| Remarks, new `리뷰 대응` | Links the [tracking comment](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6435674702). |

Explanation changes: status note (head `dcbf09e4f`, five commits after `5a70787fe`, the engine change, `path:line` stays at `5a70787fe`), `호환성` (`PAGE_OOS` now appended; boot rejection; -86 for released 11.4 and older; limitations), two Test Plan rows (`dcbf09e4f` CTest 42/42; cross-build refusal), and the CDC row of `알려진 미해결 사항`.

## Evidence used

- `git show` and `git diff 4408135c0..dcbf09e4f` in the source repository; `gh pr view 7990` metadata and body on 2026-10-27.
- Review-response evidence (local, not tracked): the CTest log of the 42/42 run (source `1e8701b4f` plus the working-tree changes later committed as `d8ed97f77` and `dcbf09e4f`; `test_oos_real_vacuum_server` and `test_oos_workspace` not run), the cross-build log (develop build `11.5.0.2635`: the pre-guard PR engine asserts in `pgbuf_check_page_ptype_internal`; the guarded engine refuses with -1392 in csql `-S`, checkdb `-S`, upgradedb, and server start; deletedb succeeds), the posted tracking comment and CDC reply.
- Source reading at `dcbf09e4f`: `logpb_restore` runs before `boot_mount` and the format check in `boot_restart_server`; the -86 check (`ER_LOG_INCOMPATIBLE_DATABASE`) runs earlier, in `logpb_find_header_parameters` called through `log_get_io_page_size`.

## Proposed operations

1. Commit the body, this context, the explanation edits, and the README rows on the docs task branch; rebase onto `main`, fast-forward `main`, and push `origin main`.
2. Verify the explanation is served at its public URL with the new content.
3. Update the body of PR #7990 with `gh pr edit 7990 --repo CUBRID/cubrid --body-file <body>`. Keep the title and draft/ready state.
4. Verify the published body SHA-256 equals the body file SHA-256 and record the result here.

No source push, PR comment, CI trigger, or code change.

## Publication record

- Authorized for this revision (body update, docs commit, integration into `main`, and push) on 2026-10-27, through the delegating session.
