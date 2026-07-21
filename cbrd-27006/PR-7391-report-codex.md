# PR #7391 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7391](https://github.com/CUBRID/cubrid/pull/7391)  
**제목:** [CBRD-27006] Improve OOS recdes locality  
**작성자:** vimkim  
**HEAD SHA:** `3f40e134d0c5b3578fe60de6f1d9f5ca8d12f698`  
**리뷰 일시:** 2026-07-21

> **TL;DR — Approve:** 현재 HEAD에서 재현 가능하고 PR이 새로 만든 correctness 결함을 찾지 못했다.
> 링크된 Greptile P1 코멘트는 `thread_p->oos_oids`의 소비 직후 정리와 오류 경로 정리를 놓친
> 오탐이다. OOS 집중 테스트 23개와 빌드가 통과했다.

## Summary

이 PR은 한 heap record에 속한 single-chunk OOS 값을 가능한 한 같은 OOS page에 배치하고,
같은 head page의 OOS read를 한 page fix로 묶는다. 검토 범위는 write/read locality뿐 아니라
publication state 수명, master replication log 순서, slave apply OID fixup, partial failure를 포함했다.

- **Verdict:** Approve
- **Actionable findings:** 없음
- **Already-commented issue:** Greptile P1 1건은 오탐
- **HEAD 안정성:** native review 전후 모두 원격 PR HEAD와 로컬 HEAD가 `3f40e13`으로 일치

## Findings

재현 가능하고 PR이 새로 유입한 결함은 발견하지 못했다.

## Existing Comments

### `discussion_r3614337787`: false positive

Greptile은 OOS group A 처리 후 `thread_p->oos_oids`가 남아서 group B에 A의 OID가 섞이고,
잘못된 OID가 B의 heap record에 기록될 수 있다고 지적했다. 현재 제어 흐름에서는 이 시나리오가
성립하지 않는다.

1. `xlocator_repl_force()` 진입 시 accumulator를 비운다
   (`src/transaction/locator_sr.c:7024`).
2. `LC_FLUSH_INSERT_OOS` 항목은 뒤따르는 heap INSERT/UPDATE가 사용할 slave-local head OID를
   의도적으로 누적한다.
3. heap row에서 `locator_fixup_oos_oids_in_recdes()`가 OID를 소비한 뒤, loop tail이
   non-OOS operation에 대해 accumulator를 비운다
   (`src/transaction/locator_sr.c:7185-7188`). 따라서 다음 OOS group은 빈 상태에서 시작한다.
4. OID 개수가 맞지 않으면 fixup은 `ER_HA_GENERIC_ERROR`를 반환하고
   (`src/transaction/locator_sr.c:14215-14239`), caller는 실제 INSERT/UPDATE 실행 전에
   `exit_on_error`로 이동한다 (`src/transaction/locator_sr.c:7093-7097`).
5. fatal path도 accumulator를 다시 비운다
   (`src/transaction/locator_sr.c:7205-7209`).

따라서 코멘트가 주장한 "B가 A의 OID로 기록되는 corruption"은 발생하지 않는다. 개수가
초과하면 row mutation 전에 실패하고, 정상 cardinality이면 row 처리 직후 group state가 정리된다.
코멘트의 제안처럼 fixup 함수 내부에서 무조건 clear하면 accumulator ownership이 producer/consumer
양쪽으로 분산되므로 현재 outer force-area 경계에서 정리하는 편이 더 명확하다.

## Risk Audit

### Replication group boundary

client-side `locator_repl_mflush()`는 OOS item 뒤에 heap row가 올 때 copy area가 부족하더라도 flush하지
않고 copy area를 확장한다. 즉 OOS group과 해당 heap row는 같은 `xlocator_repl_force()` 호출에 들어간다.
slave는 group 도중 OOS item이 실패하면 전체 pending group을 fatal 처리하고 OID state를 지운다.

### Cardinality and mutation order

fixup은 부족한 OID와 남는 OID를 모두 오류로 처리한다. 남는 OID가 발견되는 시점에는 일부 inline
stub가 메모리 `RECDES`에 쓰였을 수 있지만, 실제 heap INSERT/UPDATE 전이며 outer top operation이
abort되므로 저장 데이터 corruption으로 이어지지 않는다.

### Publication lifetime

현재 HEAD는 logical heap-record OOS 준비 시작에서 worker OID list와 transaction LSA queue를 함께
reset하고, scalar/batch insert 실패 시 partial publication을 지운다. lazy OOS file header WAL은 value
publication queue에서 제외되어 첫 OOS row의 OID/LSA pairing도 유지된다.

### Remaining non-blocking trade-off

batch insert와 grouped lazy Resolve는 선택된 여러 OOS payload를 동시에 메모리에 보유하므로 peak
memory가 scalar path보다 커질 수 있다. 이는 문서화된 설계 trade-off이며 현재 변경의 correctness
결함으로 분류하지 않았다.

## JIRA Context

CBRD-27006의 목표는 한 heap record의 여러 OOS 값에 대해 write/read page locality를 개선하는 것이다.
현재 구현은 attribute order, per-value OID, 기존 multi-chunk chain, on-disk 및 replication log format을
유지하며 이 범위와 일치한다.

## Verification

- `codex review --base origin/feat/oos`: actionable correctness regression 없음
- 로컬 CUBRID build: 성공
- focused OOS tests: 23/23 통과
- PR prerequisite gate: review 전후 통과, HEAD `3f40e134d0c5b3578fe60de6f1d9f5ca8d12f698`
- GitHub comment/thread와 기존 리뷰 피드백 대조: 신규 finding 없음

## Suggested Reply

```text
I don't think this can carry group A's OIDs into group B. The OOS items intentionally
accumulate until the following heap INSERT/UPDATE consumes them. After that non-OOS item,
xlocator_repl_force() clears thread_p->oos_oids at the loop tail (lines 7185-7188).
If exact cardinality fails, locator_fixup_oos_oids_in_recdes() returns an error and the
caller jumps to exit_on_error before the heap row is inserted/updated; that path also
clears the accumulator (lines 7205-7209). So the claimed B-with-A-OID corruption does
not occur. I would keep cleanup at the force-area/group boundary rather than make the
fixup helper own accumulator lifetime.
```
