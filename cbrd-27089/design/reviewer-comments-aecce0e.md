# PR7927 partial UPDATE feedback assessment

Work-tracker: 284. Source inspection on 2026-10-07 compares head
`aecce0e1216a813771621c13112c8f27d43df22e` with merge base
`fb567a629cdb390fff920542173fa36f454c74a0`. This is static source attribution;
it contains no new performance measurements or runtime vacuum reproduction.
The local follow-up removes the temporary record type and raw-address stubs,
with the final source revision identified by [current verification](no-record-type-verification.md).
The requested [summary snapshot](no-record-type-evidence/requested-summary.json),
[inline snapshot](no-record-type-evidence/requested-inline.json), and
[PR metadata](no-record-type-evidence/pr-metadata.json) were fetched again on
2026-10-07; the remote head remains aecce0e. Both comments are attributable to
that remote revision, not to an unpushed local commit.

The [Greptile summary](https://github.com/CUBRID/cubrid/pull/7927#issuecomment-6022333419)
and [inline comment](https://github.com/CUBRID/cubrid/pull/7927#discussion_r4198779522)
concern the same partial UPDATE cost. The summary reports no merge-blocking
finding; the inline recommendation proposes unchanged-chain reuse. The replies
below are local drafts and have not been published or used to resolve a thread.

Static claims can be checked in the [pinned source excerpts](no-record-type-evidence/reviewer-source-attribution.json).

## Attribution

| Concern | Finding at the pinned source |
| --- | --- |
| Client copy-area server adaptation | Added by this PR: an all-attribute DB_VALUE decode, reserialization and selected-value OOS insertion after routing. |
| Client full-row fetch, serialization and transmission | Existing behavior. Incoming rows ordinarily already contain full inline values; the new adapter does not inherently read the old chain again from disk. |
| Server DB_VALUE UPDATE recreates unassigned OOS values | Existing at the exact baseline. The PR defers insertion while retaining the fresh-chain ownership policy. |
| Finalization recopies or rebuilds the whole row | It uses the retained payload buffers and patches the existing 24-byte stubs. Existing physical OOS chunk/page copies still occur. |
| Overall performance regression | Unmeasured. Added server adaptation must be acknowledged, but its total cost relative to full inline/overflow heap storage is not established. |
| Immediate unchanged-chain reuse | Unsafe as an isolated change under the current vacuum and replication contracts. |

Client serialization/fetch evidence is unchanged across the comparison:
`src/object/transform_cl.c:635-647,756-759,852-886`,
`src/transaction/locator_cl.c:4374`, and `locator_sr.c:2339-2344`.
Current copy-area force supplies `from_copyarea=true` and no changed-attribute
IDs (`locator_sr.c:7450-7452`); UPDATE calls adaptation/finalization at
`6090-6096`. `heap_prepare_oos_record` starts an all-attribute cache and reads
all values (`heap_file.c:13293-13300`). Baseline UPDATE instead proceeded from
routing to index maintenance and heap update (`locator_sr.c` at the baseline:
`6041-6048,6104-6105`). Thus the complete inline comment cannot be dismissed as
inherited server UPDATE behavior.

The server DB_VALUE baseline reads uninitialized attributes and creates chains
(`heap_file.c` at the baseline: `13768,13816`). Current preparation retains the
selected serialized allocations; finalization passes those buffers to insertion
and patches stubs (`heap_pending_record.cpp:49-71`, `heap_oos.cpp:203-226`).
Its allocation retention is approximately compact-record allocation plus selected
serialized payload bytes plus buffer-descriptor capacity. Those serialized
payload allocations already existed on the server DB_VALUE path, but are newly
added by client copy-area adaptation. Retention duration is a separate cost.

## Why reuse is a separate design

Current vacuum extracts and deletes all OOS references from the UPDATE undo
image (`vacuum.c:3576-3579`, `vacuum_oos.cpp:278-281,331-336,173-182`). It does
not subtract chains still referenced by the live post-image. Reusing an old stub
would therefore make the live row reference a chain selected for reclamation.
Identity-stamp matching identifies the same chain; it does not establish
reclamation eligibility.

Undo and snapshot readers still require the old row and its live chains
(`heap_file.c:25005-25011,18480-18489,27112-27147`). The forward-walk has no
commit/abort filter in its dispatcher (`vacuum.c:4200-4239`). The reserved
`RVOOS_NOTIFY_VACUUM` slot has no emitter (`recovery.h:206-209`,
`recovery.c:905-911`). These files have no PR diff against the pinned baseline.
Historical CBRD-27237 reproduction evidence remains historical; it is not a
new runtime result for this head.

The accepted CBRD-27230 direction replaces the forward-walk with commit-conditional
dropped-chain notifications and changes ownership and replication for reuse.
That design is absent at this head. Current replica fixup expects newly inserted
chain references for every OOS stub (`locator_sr.c:14397-14433`). The copy-area
input also lacks statement-level unassigned-column metadata, and partition
movement must continue creating chains owned by the destination heap.

Recommended disposition: acknowledge added client adaptation costs, retain
fresh-chain semantics during this pending-state refactor, and handle reuse with
the complete CBRD-27230 ownership/vacuum/replication contract. Keep CBRD-27237
rollback/vacuum verification as an independent correctness requirement.

## Disposition at the local follow-up

| Exact concern | Disposition | Evidence and consequence |
| --- | --- | --- |
| Summary: high-risk storage refactor, no identified blocker, partial UPDATE cost | Acknowledge the risk and cost; no merge approval inferred from the bot summary. | Exact summary snapshot above; local build/loader/guard and two-axis review results are separate from the historical CI package. |
| Inline: ordinary-column client UPDATE decodes and serializes all columns | Accepted as newly introduced server adaptation work. | Copy-area input provides the full inline row and no assigned-column metadata; `heap_prepare_oos_record` initializes an all-attribute cache and reads values. |
| Inline: unchanged OOS values receive fresh chains | Accepted behavior, with path-specific attribution. | New for client copy-area server adaptation; existing for server DB_VALUE UPDATE at the pinned baseline. Destination movement continues writing destination-owned chains. |
| Inline: every UPDATE entails full payload read/write and memory copy | Qualify source and mechanism. | Client fetch/serialization and physical OOS writes already copy bytes; adaptation adds server decode/serialization and retention. Finalization retains payload buffers and patches stubs; it does not rebuild a full row. An additional old-chain disk read is not inherent when input is already inline. |
| Inline: reuse unchanged references | Defer to the complete ownership/vacuum/replication design. | Current vacuum deletes undo-image chains without subtracting live post-image references, and replica fixup expects fresh-chain publication. Identity matching does not make shared-chain reclamation safe. |

The local refactor retains the same all-attribute copy-area conversion and
fresh-chain policy. It adds class-representation validation on OOS logical writes
and ownerless/completed finalization; this validation walk has an unmeasured cost
and is not presented as an UPDATE optimization. Owner-index resolution replaces
raw-pointer decoding. Export checks reject residual stubs, including an inherited
optional prefetch path now skipped for OOS neighbors. These changes address
lifetime and publication safety, not the requested reuse optimization.

Current CI evidence at the remote head is preserved in the
[exact aecce0e report](../ci_analysis_report_aecce0e_codex.md). Its medium-ordering
attribution remains unresolved, and local engine checks do not replace company
regressions. No new benchmark or unchanged-chain/vacuum qualification is claimed.

## Draft inline reply

확인했습니다. client copy-area 경로에는 이 PR에서 모든 속성의 DB_VALUE 변환과
서버 측 재직렬화·OOS 적재가 추가되므로, 지적하신 비용은 실제로 있습니다. 다만
client의 전체 행 fetch·직렬화·전송은 기존에도 있었고, 서버 DB_VALUE UPDATE의
미할당 OOS 재적재도 기존 동작입니다. 현재 finalization은 보관한 payload를 그대로
사용하고 24바이트 stub만 제자리에서 바꾸며, 전체 행을 다시 만들지는 않습니다.
전체 성능 영향은 baseline 비교 측정 없이 단정하지 않겠습니다. 현재 로컬 변경은
REC_OOS_PENDING을 제거하고 기존 owner와 payload index를 명시적으로 전달합니다.
OOS 행의 저장 경계 검증 비용도 추가되므로 이를 UPDATE 성능 개선으로 제시하지
않겠습니다. 이 변경은 아직 원격 PR head에 반영하지 않았습니다.

변경 없는 체인 재사용은 CBRD-27230 설계와 함께 다루는 것이 맞습니다. 현재 vacuum은
UPDATE undo image의 체인을 모두 회수하므로 stub만 재사용하면 live 행의 체인까지
삭제할 수 있습니다. commit 조건부 회수와 복제 marker/fixup 변경이 함께 필요하며,
client copy-area에는 미할당 속성 정보도 없습니다. partition 이동 시에는
destination heap 소유 체인을 계속 새로 만들어야 합니다. 이 비용과 후속 범위를
명확히 기록하고, CBRD-27237의 rollback/vacuum 검증 요구도 유지하겠습니다.

## Draft summary response

부분 UPDATE 비용 지적을 inline comment와 함께 검토했습니다. 새로 추가된 client
copy-area 변환 비용과 기존 서버 UPDATE의 OOS 재적재를 구분했으며, 변경 없는 체인
재사용은 vacuum 소유권·복제 계약까지 함께 바뀌어야 하는 CBRD-27230 범위로 다루는
것이 맞습니다. CBRD-27237의 rollback/vacuum 정확성 검증은 별도로 유지합니다.
