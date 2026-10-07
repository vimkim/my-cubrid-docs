# PR7927 owner-index publication context

Status: publication authorized; attempt started; PR write not yet performed.
Prepared: 2026-10-07. Work-tracker: 295. Agent: codex.
Current entry point: [CBRD-27089](README.md).

## Source and target

| Field | Value |
| --- | --- |
| Ticket | CBRD-27089 |
| SOURCE_COMMIT | `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c` |
| SHORT_SHA | `4be72fc` |
| Source repository / branch | `vimkim/cubrid` / `feat/oos-deferred-write` |
| Source push remote | `vk`, fetch/push URL `https://github.com/vimkim/cubrid` |
| Target repository / operation | `CUBRID/cubrid` / update existing PR body |
| PR | [#7927](https://github.com/CUBRID/cubrid/pull/7927) |
| Existing title; proposed title | `[CBRD-27089] Defer OOS writes until destination heap selection`; unchanged |
| Existing state | OPEN, ready for review (`draft=false`); preserve |
| Base repository / branch | `CUBRID/cubrid` / `feature/oos-merge` |
| Fetched base commit | `fb567a629cdb390fff920542173fa36f454c74a0` |
| Observed remote PR head | `6b53181d31d6d6d2615b18b4f914623bb017d7c4` |
| Remote observation time | `2026-10-07T07:56:47.312018+00:00` |
| Original GitHub body SHA-256 | `c404b1756f7382ac97024bdd276d9d04ff8e08f06ea8d958468a0d1ea1669424` |
| Initial prepared body SHA-256 | `1e04627e7f1bee840e9f02b1f5f4a9cb3af739a7bc1563576fe024ab93464064` |

The original-body fingerprint hashes the decoded GitHub JSON `body` UTF-8 bytes,
without adding a newline. The prepared-body fingerprint hashes the body file's
exact UTF-8 bytes, including its terminal newline. Neither hash establishes approval.

Local source is three commits ahead of the observed remote head, which is an
ancestor of SOURCE_COMMIT: `ae36758cc`, `b039873fd`, `4be72fc20`.
The draft describes the intended local source after that normal fast-forward push,
not a claim that those three changes are already on GitHub.
Whole-PR comparison: `git diff fb567a629cdb390fff920542173fa36f454c74a0...4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`.
Follow-up comparison: `git diff 6b53181d31d6d6d2615b18b4f914623bb017d7c4...4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`.
The full PR changes 23 files; the follow-up changes seven. Existing CCI generated
changes and the JDBC checkout are unrelated working-tree changes and remain excluded.

## Draft files and local integration

| Field | Value |
| --- | --- |
| Docs repository | `vimkim/my-cubrid-docs` |
| Docs origin fetch / push | `https://github.com/vimkim/my-cubrid-docs.git` |
| Docs task branch | `docs/pr7927-publication-4be72fc` |
| Docs integration branch | `main` |
| Docs starting commit | `5b2a98ba7cc1cc9939a4e0c81c4b81c3ede19bd1` |
| body_file | `cbrd-27089/CBRD-27089-owner-index-pr-body_4be72fc_codex.md` |
| context_file | `cbrd-27089/CBRD-27089-owner-index-pr-context_4be72fc_codex.md` |
| doc_file / public explanation URL | None; the body stands alone |
| Other task file | `cbrd-27089/README.md`: links to these drafts |

Resolve worktree locations through `git worktree list` when resuming.
All paths above are repository-relative. Earlier source-identified drafts remain
untouched. This revision starts from the actual live GitHub body, retaining its
purpose, supported writer paths, loader batching, replication grouping and remaining
regression requirements. It clarifies owner/index access and shared RECDES layout,
adds the three selected refinements, and qualifies verification by source revision.
No new detailed explanation or docs push is required for this body update.

## Proposed publication operations

One later explicit confirmation may authorize exactly these operations:

1. Rebase the docs task branch onto current local `main` and fast-forward merge
   its preparation commit. Include only the body, this context and the README link
   listed above as task changes. Preserve unrelated docs work.
2. Push SOURCE_COMMIT to `vk` / `vimkim/cubrid:refs/heads/feat/oos-deferred-write`
   as a normal fast-forward, then verify the PR head matches SOURCE_COMMIT.
3. Update only the body of `CUBRID/cubrid` PR7927 with the reviewed body file's
   exact text. Preserve its title and ready-for-review status.
4. Commit verified execution receipts locally in this context, plus the README's
   publication status if necessary. Rebase and fast-forward those final record
   commits into docs `main`, verify it is clean, then remove only the merged docs
   task worktree and branch after checking for valuable files.

Docs remain local; no docs remote push is proposed. The source branch remains
available for PR review. A source rebase/base-branch merge, CI trigger and remote
reviewer replies are outside this operation list. Replies remain in the
[local Korean draft file](design/reviewer-comments-aecce0e.md).
CI attribution continues separately under work-tracker 242.

This operation list is a proposal. Confirmation must come from the conversation
once the user can review the files. At publication, reread user edits, run the
material checker without changing approved text, and record attempt fingerprints
and verified results. A changed source, GitHub body, destination or operation list
requires reconciliation and another review. Unchanged retries retain authorization.

## Claim and verification reconciliation

The approved [owner/index design](design/no-record-type-design.md) governs current
terminology. [CBRD-27089](https://jira.cubrid.org/browse/CBRD-27089) was refreshed
on 2026-10-07: its purpose is destination-heap ownership for partitioned OOS values.
Its older `heap_prepared_row` name and verification at `512b361a7` are historical,
not the current type name or new-head evidence. No JIRA update is proposed.

| Claim | Evidence and scope |
| --- | --- |
| Existing row owner, allocation association and validated payload indices | `src/storage/heap_pending_record.cpp/.hpp`, `heap_oos.cpp`; [approved design](design/no-record-type-design.md) |
| No replacement record type, unchanged shared RECDES and generic packing | Shared descriptor/storage files equal fetched base; removed marker absent from source/tests; [source contract](design/review-simplification-evidence/source-contract.json) |
| Destination writes, compact-buffer reuse and in-place finalization | `heap_oos_finalize_record`, post-routing INSERT/UPDATE and loader ordering; [refinement record](design/review-simplification.md) |
| Logical storage/fetch guards; replication rollback grouping | `heap_oos_validate_disk_record`, `locator_copyarea_add_fetch`, neighbor prefetch exclusions and `xlocator_repl_force`; [original review](design/no-record-type-review.md) |
| Grouped finalization facts, private bounded-stub decode and shared locator handoff | Three follow-up commits and [independent refinement review](design/review-simplification-review.md) |
| Current debug build/install and complete configured suite | SOURCE_COMMIT; [full log](design/review-simplification-evidence/final-ctest.log): 36/36 CTest entries, 245.43s |
| Both reorganized SQL modules | SOURCE_COMMIT; [SQL log](design/review-simplification-evidence/split-test.log): 40 GoogleTests, four CTest entries including setup/cleanup, 58.90s |
| Test relocation preserves assertions | [Mapping and body hashes](design/review-simplification-evidence/test-relocation.json): 40/40 bodies identical to `6b53181d3`; independently checked by Spec reviewer |
| Current refinement Standards/Spec findings | Zero on each axis for `6b53181d3...SOURCE_COMMIT`; original implementation review retained separately |
| Assertions-disabled boundaries and real server loader | Historical `6b53181d3` only; [original verification](design/no-record-type-verification.md), not rerun at `4be72fc20` |
| Real loader historical qualification | 600 bulk values, one 9MiB row, 800 partitioned rows, invalid-child rejection and successful next load. Fixture Python passed; supervising shell returned 1 because normal foreground master wait returns 1. Native shutdown probe confirmed command exit 0/master exit 1 |
| UPDATE cost and unchanged-chain reuse | [Comment dispositions](design/reviewer-comments-aecce0e.md): new client server adaptation vs existing client/server behavior; overall performance unmeasured. Reuse requires separate MVCC/vacuum/replication design |
| Whole SQL/shell/medium and PR7925 integration | Unverified at SOURCE_COMMIT. Older CI remains pinned evidence; medium-ordering attribution remains unresolved under 242 |

All 16 current evidence hashes and 45 historical evidence hashes were checked during
preparation. Those checks validate saved evidence integrity; no new engine build,
runtime test, release/loader rerun, CI run or benchmark occurred in preparation.
The material checker and local Markdown-link checks are the new preparation checks.

## Original GitHub body snapshot

This snapshot preserves the observed manual body for future reconciliation.
Its fingerprint above was calculated before Markdown wrapping.

```markdown
https://jira.cubrid.org/browse/CBRD-27089

## Purpose

OOS는 큰 컬럼 값을 행 밖에 저장하고, 행에는 값을 찾을 참조 정보만 남기는 방식입니다. 행과 OOS 값은 같은 heap이 소유해야 vacuum이 함께 정리할 수 있습니다.

- AS-IS: 파티션 선택 전에 OOS 값을 root heap에 기록하여, child heap에 저장된 행과 값의 소유자가 달라집니다.
- TO-BE: 목적지 heap을 정한 뒤 그 heap의 OOS 파일에 값을 기록합니다.

## Implementation

- `heap_pending_record`가 처음 만든 행 버퍼(`RECDES`)와 OOS 대상 값의 직렬화 바이트를 함께 소유합니다. 행을 버리면 두 메모리도 함께 정리됩니다.
- `heap_oos_value_ref`는 메모리 참조와 디스크 참조를 구분하며, 같은 `length()`·`read_into()` 인터페이스로 값을 읽습니다. 파티션 선택과 인덱스 호출 인터페이스는 유지합니다.
- workspace에서 받은 행은 파티션 결정 후 OOS 변환을 준비합니다. 목적지가 정해지면 OOS 값을 기록하고 기존 24바이트 stub만 실제 OID·길이·identity stamp로 덮어씁니다. 이 단계에서는 행 버퍼를 다시 만들거나 길이·컬럼 위치를 바꾸지 않습니다.
- SQL INSERT·UPDATE·파티션 이동, 중복 키 검사, client row, loader, 재분배에 적용합니다. 복제 apply는 OOS item과 소유 행을 같은 롤백 단위로 처리합니다.
- 메모리 참조는 서버에서 준비한 임시 레코드에서만 허용하고, 저장·전송 전에 임시 상태를 차단합니다. 저장 형식과 통신 형식은 유지합니다.

## Remarks

- 기존 직렬화·컬럼 읽기·최종 저장 함수를 재사용합니다. loader는 행 단위 소유 객체를 큐에 넣고, 행과 OOS 값의 합산 크기로 batch를 비웁니다. 공유 값 목록의 위치를 기억했다가 되돌리는 정리 코드는 제거했습니다.
- server loaddb의 root 입력은 파티션으로 배치하며, child 직접 입력은 범위를 검증합니다. 잘못된 child 입력을 허용하던 테스트의 기대값은 수정이 필요합니다.
- Debug 빌드와 CTest 35/35 통과. 메모리·디스크 값 일치, 동일 RECDES의 stub만 변경, workspace INSERT·파티션 이동과 목적지 소유권, 중복 키 검사, 실패 롤백, 복제 apply를 검증했습니다.
- 실제 server loaddb에서도 600행 batch, 9MiB 단일 행, 800행 파티션 배치, 잘못된 child 입력 거부 후 다음 load 성공을 확인했습니다.
- 전체 SQL·shell·medium 회귀 CI 결과와 PR #7925와의 통합 실행 결과는 아직 확인하지 않았습니다.
```

## Publication attempt and results

Preparation performed no remote writes or integration. The user subsequently
approved the saved body unchanged, preservation of title/ready status, local docs
rebase and fast-forward integration (including execution records), and merged-task
cleanup. Full exact-head CI and available-evidence analysis were separately
requested under work-tracker 242. Reviewer replies remain local drafts.

### Attempt 2026-10-07

- Started: `2026-10-07T08:35:01.395373+00:00`.
- Approved body SHA-256: `1e04627e7f1bee840e9f02b1f5f4a9cb3af739a7bc1563576fe024ab93464064` (exact file bytes).
- Pre-write GitHub body SHA-256: `c404b1756f7382ac97024bdd276d9d04ff8e08f06ea8d958468a0d1ea1669424` (decoded UTF-8 body).
- Reconciled source: local HEAD and remote PR head both `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c`.
  The already-published source was observed before this confirmation; no source
  push is necessary or performed by this attempt.
- Target remains PR7927, `vimkim/cubrid:feat/oos-deferred-write` to
  `CUBRID/cubrid:feature/oos-merge`, OPEN and ready for review. Title unchanged.
- Docs task successfully rebased onto clean local `main` at `5b2a98ba7cc1cc9939a4e0c81c4b81c3ede19bd1`.
- Material checker passed and approved body fingerprint matched. PR write and
  post-write verification remain pending at this attempt record.
- No docs remote push or reviewer reply is authorized by this publication.
