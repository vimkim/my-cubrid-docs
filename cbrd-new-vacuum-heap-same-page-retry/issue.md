# [VACUUM] release 빌드의 vacuum_heap 이 페이지 오류 뒤 같은 heap 페이지를 끝없이 다시 처리한다

**한 줄 요약**: [PR #8417 리뷰 댓글](https://github.com/CUBRID/cubrid/pull/8417#discussion_r4490086205)이 별도 등록을 요청한 기존 결함으로, release 빌드의 `vacuum_heap` 일반 오류 분기가 다음 페이지로 넘어가지 않아 오류가 반복되는 동안 vacuum worker 가 같은 페이지에 묶이는 문제를 다룬다.

## Issue Triage

**이슈 수행 목적**: release 빌드에서 heap 페이지 하나의 vacuum 이 실패해도 worker 가 같은 페이지를 제자리에서 반복하지 않고, 블록 처리를 계속하거나 블록을 나중에 다시 처리하도록 남긴다.

**이슈 수행 이유**: `vacuum_heap` 의 release 일반 오류 분기는 셧다운이 아니면 오류를 지우고 `continue` 한다. 이때 `page_ptr = obj_ptr` 를 건너뛰므로 다음 반복이 같은 페이지의 `vacuum_heap_page` 를 다시 호출한다. PR #8417 리뷰어(hornetmj)가 이 문제를 지적하며 별도 이슈 등록을 요청했다. 같은 루프는 CBRD-26715 에서 이미 분석되었으나, 당시에는 OOS 조회 한 경로만 우회했다. develop 에도 같은 분기가 있어 OOS 와 무관한 기존 결함이다.

**영향**: 오류가 계속 재발하는 동안 해당 vacuum worker 는 블록을 끝내지 못한다. 실패가 지속되면 셧다운 전까지 무한 루프가 된다. CBRD-26715 에서는 이 루프로 같은 오류가 서버 에러 로그에 90,000회 이상 반복되고 CI 가 45분 타임아웃으로 실패했다. 현재 남은 진입 경로의 발생 빈도는 확인하지 않았다.

**이슈 수행 방안**: TBD - ANALYSIS 단계에서 해결 방안과 구현 범위를 결정한다.

---

## AI-Generated Context

## Description

vacuum worker 는 로그 블록 하나에서 모은 heap 객체를 VFID 와 OID 순으로 정렬한 뒤, `vacuum_heap` 에서 heap 페이지 단위로 `vacuum_heap_page` 를 호출한다. 루프의 증감식은 비어 있고, 정상 경로는 루프 끝의 `page_ptr = obj_ptr;` 로 다음 페이지에 넘어간다.

`vacuum_heap_page` 가 오류를 반환하면 일반 오류 분기로 들어온다. debug 빌드는 `vacuum_check_shutdown_interruption` 의 assertion 에서 중단한다. release 빌드(`NDEBUG`)는 셧다운이 아니면 다음 처리를 한다. [PR #8417 head 의 분기](https://github.com/CUBRID/cubrid/blob/1f9f09f362390e10ed06d80f9aae3ae2e361b2d2/src/query/vacuum.c#L1624-L1645)

```c
#if defined (NDEBUG)
	  if (!thread_p->shutdown)
	    {
	      // unexpected case
	      // debug crashes; ... clean as much as possible   (원문 일부 생략)
	      er_clear ();
	      error_code = NO_ERROR;
	      continue;          /* page_ptr = obj_ptr; 를 건너뛴다 */
	    }
#endif // not DEBUG
```

주석은 "가능한 한 많이 정리한다"는 의도를 밝힌다. 그러나 `continue` 가 페이지 전진을 건너뛰므로, 다음 반복은 같은 `page_ptr` 로 같은 페이지를 다시 처리한다. 같은 오류가 다시 나면 같은 분기로 돌아온다. 오류가 일시적이면 해소될 때까지 재시도가 이어지고, 지속적이면 셧다운이 오기 전까지 루프를 벗어나지 못한다. 그동안 이 블록의 나머지 페이지와 다른 heap 은 처리되지 않는다.

### 진입 경로 예: REC_BIGONE 의 overflow 파일 조회

리뷰어가 제시한 예다. `vacuum_heap_prepare_record` 는 `REC_BIGONE` 레코드의 overflow VFID 가 없으면 `heap_ovf_find_vfid` 로 heap 헤더 페이지에서 이를 읽는다. 조건부 래치가 실패하면 heap 페이지를 놓고 무조건 래치로 다시 기다린다. 이 조회도 실패하면 `assert_release (false)` 뒤 `ER_FAILED` 를 반환한다. [PR #8417 head 의 REC_BIGONE 준비](https://github.com/CUBRID/cubrid/blob/1f9f09f362390e10ed06d80f9aae3ae2e361b2d2/src/query/vacuum.c#L2195-L2222)

```
vacuum_heap (release, 셧다운 아님)
  └ vacuum_heap_page (페이지 P)
      └ vacuum_heap_prepare_record
          └ REC_BIGONE: heap_ovf_find_vfid (헤더 대기) 실패 → ER_FAILED
  └ 일반 오류 분기: er_clear → continue
      page_ptr 그대로 → 다시 페이지 P → 다시 헤더 대기 → ...
```

리뷰어 설명에 따르면, 헤더가 오래 잡혀 있으면 worker 는 래치 타임아웃마다 같은 페이지를 다시 시도한다. 헤더 읽기 오류처럼 계속되는 실패라면 무한 루프가 된다. 이 두 조건은 소스 분기로 확인했으며, 실행으로 재현하지는 않았다. 일반 오류 분기는 오류 코드를 구분하지 않으므로, `vacuum_heap_page` 의 다른 실패도 같은 동작을 한다. 그 경로 목록은 ANALYSIS 에서 정리한다.

### 기존 이력과 이번 이슈의 범위

- [CBRD-26715](https://jira.cubrid.org/browse/CBRD-26715)는 이 루프의 메커니즘을 이미 분석했다. 당시 OOS 플래그 거짓 양성으로 `heap_oos_find_vfid` 가 실패했고, 위 `continue` 가 `page_ptr = obj_ptr` 를 건너뛰어 release 빌드에서만 같은 페이지를 반복했다. 수정은 OOS 조회 실패를 경고로 바꾸어 오류를 반환하지 않게 한 우회였고, 루프 자체는 그대로 남았다.
- 그 우회는 OOS 값 누수로 이어져 [CBRD-27933](https://jira.cubrid.org/browse/CBRD-27933)(PR #8417)이 되었다. PR #8417 은 OOS 조회 실패를 `ER_VACUUM_OOS_LOOKUP_DEFERRED` 로 바꾸고, 해당 heap 의 남은 페이지를 건너뛴 뒤 블록을 나중에 다시 처리하게 한다. `ER_OUT_OF_VIRTUAL_MEMORY` 도 별도로 루프를 끝낸다. 이 두 오류 외의 일반 오류 분기는 바뀌지 않았다.
- 리뷰어는 이 상황이 PR #8417 의 단위 테스트 `UnrelatedHeapVacuumedWhileHeaderLookupKeepsFailing` 이 막으려는 "실패한 페이지를 제자리에서 다시 시도해 다른 heap 에 가지 못하는" 상황과 같다고 지적했다. 그 테스트는 OOS 조회 경로만 검증한다.

## Test Build

소스 확인만 했으며, 바이너리를 실행하지 않았다.

| 기준 | 커밋 | 일반 오류 분기 | 페이지 전진 |
|---|---|---|---|
| PR #8417 head (`feature/oos-merge` 대상) | `1f9f09f36` | [vacuum.c:1624-1643](https://github.com/CUBRID/cubrid/blob/1f9f09f362390e10ed06d80f9aae3ae2e361b2d2/src/query/vacuum.c#L1624-L1643), `continue` 는 1638행 | [1645행](https://github.com/CUBRID/cubrid/blob/1f9f09f362390e10ed06d80f9aae3ae2e361b2d2/src/query/vacuum.c#L1645) |
| `feature/oos-merge` | `d52b1889e` | [vacuum.c:1600-1619](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L1600-L1619), `continue` 는 1614행 | [1621행](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L1621) |
| `develop` | `dcbab24d0` | [vacuum.c:1553-1572](https://github.com/CUBRID/cubrid/blob/dcbab24d083ab948b991b6f4cf594018122e1775/src/query/vacuum.c#L1553-L1572), `continue` 는 1567행 | [1574행](https://github.com/CUBRID/cubrid/blob/dcbab24d083ab948b991b6f4cf594018122e1775/src/query/vacuum.c#L1574) |

`develop` 에도 같은 분기와 같은 `REC_BIGONE` 실패 반환([vacuum.c:2084-2097](https://github.com/CUBRID/cubrid/blob/dcbab24d083ab948b991b6f4cf594018122e1775/src/query/vacuum.c#L2084-L2097))이 있다. 따라서 이 결함은 OOS 브랜치에서 생긴 것이 아니다. 이 분기는 2018년 커밋 `2cf06f690`([CBRD-22121](https://jira.cubrid.org/browse/CBRD-22121), PR #1106)에서 들어왔다. 출시 버전 바이너리에서 실제로 재현되는지는 확인하지 않았다.

## Repro

실행한 재현은 없다. 아래는 제안 절차다.

1. release 빌드에서 `REC_BIGONE` 레코드가 있는 테이블을 만들고, 그 레코드를 DELETE 하여 vacuum 대상으로 만든다.
2. 장애 주입으로 vacuum 의 `heap_ovf_find_vfid` 무조건 래치 조회가 계속 실패하게 하거나, heap 헤더 페이지를 오래 잡는다.
3. 같은 로그 블록에 다른 heap 의 vacuum 대상도 함께 만든다.
4. vacuum worker 가 같은 페이지의 오류를 반복 기록하는지, 다른 heap 이 vacuum 되지 않는지 확인한다.

장애 주입 방법은 정해지지 않았다. PR #8417 의 `unit_tests/oos/test_oos_real_vacuum_server.cpp` 가 OOS 조회에 쓰는 헤더 점유 방식을 참고할 수 있다.

## Expected Result

- release 빌드에서 heap 페이지 하나의 일반 오류가 worker 를 같은 페이지에 묶지 않는다.
- 일시적 오류로 끝내지 못한 정리는 블록을 완료로 표시하지 않거나 다른 방식으로 나중에 다시 처리된다. 정리를 생략한 채 블록이 완료되지 않는다.
- 같은 블록의 다른 페이지와 다른 heap 의 vacuum 은 진행된다.
- 셧다운 시 동작은 지금과 같이 유지된다.

## Actual Result

소스 분석 기준으로, 셧다운이 아닌 release 빌드에서 `vacuum_heap_page` 가 다시 실패하는 동안 같은 페이지를 반복 처리한다. CBRD-26715 에서는 같은 루프가 OOS 조회 실패로 실제 발생해 에러 로그가 90,000회 이상 반복되었다. 이번 진입 경로(`REC_BIGONE` 등)로는 관찰하지 않았다.

## Analysis Questions

- `vacuum_heap_page` 가 일반 오류 분기로 반환할 수 있는 오류를 정리하고, 일시적 오류와 지속적 오류를 구분할 수 있는지 확인한다.
- 실패한 페이지를 건너뛰고 계속할지, heap 을 건너뛸지, 블록을 나중에 다시 처리하도록 남길지 정한다. 건너뛴 정리가 블록 완료로 사라지면 CBRD-27933 과 같은 누수 위험이 생기므로, 블록 완료 표시와 함께 검토한다.
- PR #8417 의 `ER_VACUUM_OOS_LOOKUP_DEFERRED` 처리와 블록 재실행 주기 제한을 일반 오류에 적용할 수 있는지 확인한다.
- 지속적 오류에서 worker 가 다른 블록으로 진행하는 정책과 진단 로그의 양을 정한다.
- vacuum worker 의 무조건 래치 대기에 실제 타임아웃이 적용되는지 확인하여, 헤더 점유 시 재시도 주기를 확정한다.
