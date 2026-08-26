# Handoff: PR #7630 teaching session

## Next-session purpose

Run a stateful `/teach` course that helps the user understand CUBRID PR #7630 well enough to explain and defend the review without notes. This is a learning task, not a request to modify the PR.

Use a dedicated teaching workspace, such as:

`/home/vimkim/gh/my-cubrid-docs/learning/pr-7630-page-latches`

Do not run `/teach` from the CUBRID source worktree. The skill creates `MISSION.md`, `RESOURCES.md`, `lessons/`, `reference/`, `learning-records/`, `assets/`, and `NOTES.md` in its current directory.

## Authoritative artifacts

- Reviewed source worktree: `/home/vimkim/gh/cb/review-CBRD-27198-unconditional`
- Exact reviewed PR head: `1185f16d7e5f540ffdad4509cbd061ef0535f4df`
- PR: https://github.com/CUBRID/cubrid/pull/7630
- Published review report: `/home/vimkim/gh/my-cubrid-docs/cbrd-27198/PR-7630-report_1185f16_codex.md`
- Published report URL: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27198/PR-7630-report_1185f16_codex.md
- Review summary comment: https://github.com/CUBRID/cubrid/pull/7630#issuecomment-5365094372
- Author's later architecture response: https://github.com/CUBRID/cubrid/pull/7630#issuecomment-5365130299

Read the report instead of reproducing its review evidence in the teaching workspace. Use the exact commit above as the source baseline, even if the live PR head later changes.

## Current state

The review is complete. Its decision was `REJECT`, with one blocking finding and no non-blocking findings. The implementation correctly addresses zero-wait structural-page fixes, but `force_latch_wait` currently maps every original wait policy to `LK_INFINITE_WAIT`. This changes the timeout classification for positive finite values. The full evidence and required correction are in the published report.

The report said the architectural reviewer question had no author answer. That statement became stale after publication: the author later replied at the URL above. The reply accepts that `lock_timeout` is conceptually lock-oriented but argues that full latch-policy separation is too broad for this PR. This does not resolve the concrete positive-timeout blocking finding.

No source changes are requested. Do not rerun the PR review unless the user explicitly asks for an exact-head re-review.

## Teaching mission

The user wants durable understanding, not another large explanation. Build short lessons with retrieval practice and tight feedback. The target capability is to explain the review in a real reviewer conversation.

By the end, the user should be able to:

1. Distinguish transaction locks, page latches, page fixes, latch modes, and conditional versus unconditional latch requests.
2. Trace `LK_ZERO_WAIT`, `LK_FORCE_ZERO_WAIT`, positive finite values, and `LK_INFINITE_WAIT` through the relevant page-buffer paths.
3. Explain why the original `lock_timeout=0` failure was an immediate rejection, not an elapsed page-latch timeout.
4. Explain what the per-thread `force_latch_wait` flag changes and why it is stored in `THREAD_ENTRY` rather than shared `LOG_TDES` state.
5. Demonstrate the blocking regression with a concrete event timeline.
6. State the smallest correct behavioral fix: override only the two no-wait values and preserve positive and already-infinite values.
7. Separate the broad architectural question from the concrete blocking defect.
8. Answer skeptical reviewer questions without reading the report.

Start with a short diagnostic quiz. Use its results to select the first lesson. Do not assume knowledge of CUBRID latch internals. Prefer plain, short sentences and consistent domain terms. Use source links with line anchors in every lesson.

## Useful source anchors

- `src/storage/AGENTS.md`: lock versus latch terminology and page-buffer protocol
- `src/transaction/lock_manager.h:55`: wait-policy sentinel values
- `src/storage/page_buffer.c:2273`: unconditional-to-conditional demotion
- `src/storage/page_buffer.c:5357`: `pgbuf_set_force_latch_wait`
- `src/storage/page_buffer.c:7284`: actual page-latch wait calculation
- `src/storage/page_buffer.c:7375`: timeout classification and error paths
- `src/storage/page_buffer.c:16922`: `pgbuf_find_current_wait_msecs`
- `src/storage/disk_manager.c:3233`: volume-header scoped override
- `src/storage/disk_manager.c:3510`: sector-table scoped override
- `src/base/system_parameter.c:5308`: separate page-latch timeout

## Suggested skills

- Call `/teach` first. It is the main flow for this multi-session learning goal.
- Call `/wait-what` only when a lesson explanation does not land and needs a plain-language re-pitch.
- Use `/domain-modeling` only if the user is blocked by overloaded terms and the teaching glossary needs sharper CUBRID language.

## Suggested first invocation

```text
/teach My mission is to understand CUBRID page latches well enough to explain and defend my review of PR #7630 in a reviewer discussion.

Use the authoritative artifacts and exact reviewed commit from the handoff. Teach me through short interactive lessons. Start with a diagnostic retrieval quiz. Do not assume I understand CUBRID latch internals.
```
