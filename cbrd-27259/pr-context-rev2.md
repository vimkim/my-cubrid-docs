# CBRD-27259 PR body revision 2 context

Prepared 2026-11-05 (Asia/Seoul). This file records the proposal. It is not an approval record. The first revision and its publication record are in [pr-context.md](pr-context.md).

## Source and target

| Item | Value |
| --- | --- |
| Ticket | CBRD-27259 |
| Source commit | `9ae07b9491b1393841ecb0f3579752a598bf68ec` (adds the non-OOS `REC_BIGONE` notification on top of `e19d8c613`; replaced the unpushed `aa951eebf`) |
| Source repository and branch | `vimkim/cubrid` (remote `vk`), `CBRD-27259-storage-force-inline` |
| Observed remote head | `e19d8c613c581cde2350474fe3451c60ecb04c66` (2026-11-05) |
| Base | `CUBRID/cubrid` `feature/oos-merge` |
| Target repository | `CUBRID/cubrid` |
| Operation | `update` of https://github.com/CUBRID/cubrid/pull/8416 (open, draft) |
| Existing title | `[CBRD-27259] Add STORAGE FORCE_INLINE and fixed-type STORAGE DEFAULT` (unchanged) |
| Original GitHub body SHA-256 | `8894bd68e1609b87d5bbb5df4d3877d24362bb8361212a3c6f81e136d356d259` |

## Documents

| Item | Value |
| --- | --- |
| Docs task branch | `docs/CBRD-27259-pr-rev2` |
| Docs integration branch | `main` |
| Body | `cbrd-27259/pr-body-rev2.md` |
| Context | `cbrd-27259/pr-context-rev2.md` |

## Proposed publication operations

1. Docs: rebase `docs/CBRD-27259-pr-rev2` onto local `main`, merge with `git merge --ff-only`, and push `main` to `origin`. Files: `cbrd-27259/README.md`, `cbrd-27259/pr-body-rev2.md`, `cbrd-27259/pr-context-rev2.md`.
2. Source: after CI run https://github.com/CUBRID/cubrid/actions/runs/42015351873 completes, `git push vk CBRD-27259-storage-force-inline` to publish the source commit above.
3. PR: `gh pr edit 8416 --repo CUBRID/cubrid --body-file cbrd-27259/pr-body-rev2.md`, with no title, base, or status change.

After the source push, one `/run all` runs CI on the new head, as the user chose on 2026-11-05.

## Conversation record

- 2026-11-05: the user asked for a warning on non-OOS `REC_BIGONE` for every user-table row ("사용자 테이블 행 전부", "경고만 남기고 저장") and for CI on the new head after the current run ("현재 run 완료 후 실행").
- 2026-11-05: the user approved the first version of this revision ("1. 승인"), then asked for the report to reach the log with default parameters ("평상시에도 문제가 생기면 로그에 남게 하고 싶은데"). The body changed to notification wording, so it returns to review; the approved version is commit `defe2ce`.

## Publication record

Not started.
