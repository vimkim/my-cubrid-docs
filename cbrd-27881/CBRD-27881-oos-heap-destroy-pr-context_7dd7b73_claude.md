# CBRD-27886 oos-heap-destroy PR draft context

- Ticket: CBRD-27886 (sub-task of CBRD-27881)
- SOURCE_COMMIT: 7dd7b7369b15ed26bfc24c56abd448f38eabbd66 (same tree as 8f4e201d; message re-keyed and qualified)
- Agent: claude
- Source repository and branch: vimkim/cubrid, `CBRD-27881-oos-heap-destroy`
- Base: `feature/oos-merge` (tip dcbf09e4f2 at preparation)
- Observed remote head before publication: branch absent on `vk` (new PR)
- Target repository: CUBRID/CUBRID
- Operation: create
- Proposed title: `[CBRD-27886] Share one OOS file cleanup helper in heap destroy`
- Docs task branch: `docs/CBRD-27881-oos-refactor`; integration branch: `main`
- Body: `cbrd-27881/CBRD-27881-oos-heap-destroy-pr-body_7dd7b73_claude.md`
- Context: `cbrd-27881/CBRD-27881-oos-heap-destroy-pr-context_7dd7b73_claude.md`
- No explanation document.

## Proposed operations

1. Push `CBRD-27881-oos-heap-destroy` to the `vk` remote (github.com/vimkim/cubrid), no force.
2. `gh pr create --repo CUBRID/CUBRID --draft --base feature/oos-merge --head vimkim:CBRD-27881-oos-heap-destroy --assignee vimkim --title "<title>" --body-file <body>`, no earlier than 04:56 KST (PR 4 opens at 03:56).
3. After the tc branch sync, `cubrid-pr-tc-base-check-oos --pr N`, then one `/run all`.
4. Keep docs commits local on the task branch; integrate into `main` and push during the CBRD-27881 final write-up.

## Authorization

The user wrote on 2026-11-03 at about 00:20 KST, before going to sleep:
"만약 좋은 후보가 나오면, draft PR을 생성해줘. 1시간마다 하나씩만 생성하고, subagent로 코드리뷰를 마친 뒤 고칠 점이 없으면 /run all 을 날려줘."
At 02:01 the user suggested one CBRD-27881 sub-task per PR; CBRD-27886 was created for this PR.

## Verification evidence before publication

- Owner (sonnet): 44/44 OOS ctest before and after; gdb hits from `xheap_destroy` in 16 test binaries; manual DONT_REUSE_OID drop reached `xheap_destroy_newly_created`. Disclosed one contract-violation-only difference.
- Review lane (opus, independent): PASS at 8f4e201d. Ruled the difference reachable in release only with a corrupt heap header page (pgbuf vpid mismatch, NDEBUG), and the new behavior no worse (old leaked heap and OOS file; new leaks only the OOS file). SA/SERVER, debug/NDEBUG warning sets equal to base; indent unchanged; clean merge-tree with #8350, #8299, #8369. Nit: qualify "behavior unchanged" in the commit message.
- Gate lane (sonnet, independent): PASS at 8f4e201d. Recompile with ccache disabled, 0 warnings; 44/44 OOS ctest; DONT_REUSE_OID table with FORCE_OUTLINE value dropped under gdb through `xheap_destroy_newly_created` → helper returned 0; `cubrid diagdb -d 1` showed the OOS files gone.
- Coordinator: re-keyed to CBRD-27886 and qualified the message (7dd7b736, message only).

## Execution record

- 04:57 KST: published with scratchpad/publish_pr.sh: pushed to `vk` (remote head 7dd7b7369b15ed26bfc24c56abd448f38eabbd66); created draft PR https://github.com/CUBRID/cubrid/pull/8371 (assignee vimkim); remote body matches the body file apart from trailing blank lines; TC branch sync SUCCESS; `cubrid-pr-tc-base-check-oos --pr 8371` exit 0; posted `/run all` (https://github.com/CUBRID/cubrid/pull/8371#issuecomment-6587075465); gha-ci run https://github.com/CUBRID/cubrid/actions/runs/41514923165 picked up all five contexts.
