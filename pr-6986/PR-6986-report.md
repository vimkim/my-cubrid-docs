# PR #6986 코드 리뷰 보고서 — Forward-Walk 재설계 이후의 누수 경로 재평가

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**JIRA:** [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE
**작성자:** vimkim
**베이스 브랜치:** `feat/oos`
**HEAD SHA:** `31e6e9dc6` (style(vacuum): match indent formatter on range-for and joined if)
**이전 HEAD:** `6d41132a7` (2026-04-17 리뷰 대상)
**리뷰 일시:** 2026-04-20
**리뷰 초점:** 사용자 질문 — "이 PR이 모든 도달 불가능한 OOS 값을 정리하는가?"의 재검토.

**이전 버전과의 관계:** 이 보고서는 2026-04-17 리비전의 "`vacuum_cleanup_prev_version_oos` 기반 설계 + L1 블로커" 평가를 **forward-walk 재설계**(commit `f912b720c`) 기준으로 갱신한 개정판이다. L1은 재설계로 해결되었고 새로운 위험 영역이 등장했다.

---

## 1. TL;DR

2026-04-17 리포트는 L1(UPDATE-drops-all-OOS → DELETE prev-version 누수)을 **머지 블로커**로 판정했다. L1의 원인은 `vacuum_cleanup_prev_version_oos`의 호출자 가드(`!VFID_ISNULL(&helper->oos_vfid)`)가 현재 레코드의 HAS_OOS 상태에 종속되어 lazy lookup 코드가 dead code가 된 것이었다.

**현재 상태: L1은 forward-walk 재설계로 완전 해소되었다.**

commit `f912b720c`는 `vacuum_cleanup_prev_version_oos`와 REMOVE 경로의 prev-version 트리거 블록 전체(~250+ 라인)를 제거하고, `vacuum_process_log_block`의 forward walk 안에 inline OOS 정리를 추가했다. 각 MVCC 힙 로그 레코드(`RVHF_UPDATE_NOTIFY_VACUUM`, `RVHF_MVCC_DELETE_MODIFY_HOME`)의 undo payload를 해석하여 HAS_OOS가 있으면 `oos_delete`를 호출한다. 현재 레코드의 HAS_OOS 상태와 무관하게 각 과거 버전이 정리되므로 L1 시나리오는 **구조적으로 재발 불가능**하다.

다만 재설계는 새로운 위험 영역을 도입했다. (1) non-OOS 테이블에 대해서도 undo decode 비용이 추가되어 성능 regression 가능성, (2) defensive copy 비용, (3) VFID 캐시 eviction 정책의 휴리스틱 특성, (4) sysop 페어링 assertion 의존성. 이 중 (1)은 정량 확인이 남아 있고, 나머지는 현재 구현에서 관리 가능한 수준으로 평가된다.

**머지 권장 여부:** L1 해소로 **머지 블로커는 해제**된다. L3/L4/T0.5는 non-blocker 후속 작업으로 이관 권장.

---

## 2. 2026-04-17 보고서의 L1-L4 재평가

### 2.1 L1 — prev-version 체인 가드의 dead-code 함정: **RESOLVED**

#### 과거 판정

`vacuum_cleanup_prev_version_oos`의 호출자 가드가 `!VFID_ISNULL(&helper->oos_vfid)`를 요구했으나, `oos_vfid`는 현재 레코드가 HAS_OOS를 가질 때만 설정되었다. 따라서 "현재 레코드는 HAS_OOS 없는데 undo chain에는 OOS가 있는" 시나리오에서 함수 호출 자체가 차단되어 내부 lazy lookup이 dead code가 되었다.

누수 시나리오:

```sql
INSERT INTO t VALUES (1, REPEAT(X'AA', 4096));   -- HAS_OOS=1, OOS_A
UPDATE t SET oos_col = NULL WHERE id = 1;         -- HAS_OOS=0
DELETE FROM t WHERE id = 1;                       -- undo(DELETE)에 HAS_OOS=0 recdes
```

REMOVE 시점 현재 레코드의 HAS_OOS=0 → `oos_vfid`=NULL → 체인 워커 호출 차단 → OOS_A 누수.

#### 현재 상태

`vacuum_cleanup_prev_version_oos`와 관련 가드/호출부 전부가 `f912b720c`에서 제거되었다. 신 설계는 다음과 같이 이 시나리오를 처리한다.

- `vacuum_process_log_block`이 UPDATE의 MVCC 힙 로그 레코드(`RVHF_UPDATE_NOTIFY_VACUUM`)를 처리할 때, undo payload=v1(HAS_OOS=1, OOS_A) 을 recdes로 해석.
- `heap_recdes_contains_oos(&undo_recdes)` = true → forward walk 블록 진입.
- `vacuum_forward_walk_delete_oos`가 OOS_A를 삭제.

현재 레코드의 HAS_OOS 상태가 조건에 전혀 등장하지 않으므로 과거 L1 시나리오는 구조적으로 발생하지 않는다.

**판정: RESOLVED. 검증은 regression 테스트로 확인 필요 (T3.4 참조).**

### 2.2 L2 — SA_MODE DELETE: 상태 유지

#### 과거 판정

SA_MODE에는 MVCC가 없고 vacuum이 no-op이므로 DELETE 시 OOS가 자동 정리되지 않는다. Standalone utility(loaddb 등)에서 DELETE를 수행하는 경로가 있다면 OOS 파일이 지속 증가.

#### 현재 상태

**변경 없음.** 본 PR은 여전히 SA_MODE DELETE eager 정리를 포함하지 않는다. `heap_update_home_delete_replaced_oos`(UPDATE용)는 있으나 DELETE용 대응이 없다.

**권장 조치: 후속 JIRA에서 `heap_delete_logical` 내부의 non-MVCC branch에 eager OOS cleanup을 추가. PR-6986 설명에 "SA_MODE DELETE는 범위 외" 명시 권장.**

### 2.3 L3 — REC_BIGONE + OOS 불변식: 상태 유지

#### 과거 판정

`vacuum_heap_record`의 REC_BIGONE 분기에서 `assert(!heap_recdes_contains_oos(...))`만 있어 release build에서는 불변식 위반 시 조용한 OOS 누수.

#### 현재 상태

**변경 없음.** Forward-walk 재설계는 REC_BIGONE 경로를 건드리지 않았다. `assert`가 여전히 debug-only.

이론적으로 forward walk가 처리하는 MVCC 힙 로그 레코드의 undo는 REC_HOME 형식의 recdes이므로, 여기에는 REC_BIGONE 불변식이 적용되지 않는다(주석 vacuum.c:3654 `undo_recdes.type = REC_HOME`). 따라서 forward walk 자체는 REC_BIGONE 불변식과 무관하다. 그러나 `vacuum_heap_record`의 REC_BIGONE 분기는 여전히 debug-only assert에 의존.

**권장 조치: `assert_release` 업그레이드 또는 `ER_FAILED` 반환.**

### 2.4 L4 — RELOCATION 누적 시나리오 회귀 테스트 부재: 상태 유지

#### 과거 판정

UPDATE로 인한 연속 RELOCATION 체인이 OOS를 참조하는 경우에 대한 직접 회귀 테스트가 없음.

#### 현재 상태

**변경 없음.** 신 설계에서도 RELOCATION 연쇄는 forward walk로 커버되지만, 이를 스트레스로 검증하는 회귀 테스트는 없다.

**권장 조치: T3.4 — 좁은 heap 페이지에서 UPDATE를 반복해 RELOCATION 강제 → DELETE → vacuum → OOS 파일 page count 확인.**

---

## 3. 새 설계로 인한 신규 위험 평가

### 3.1 R1 — Undo 디코드 비용 (non-OOS 테이블에도 발생)

#### 설명

Forward walk는 **모든** MVCC 힙 로그 레코드에 대해 다음을 수행한다.

1. `undo_data != NULL && undo_data_size > 0` 체크 (cheap).
2. `heap_recdes_contains_oos(&undo_recdes)` — MVCC 헤더 바이트 읽기 + 비트 AND. 인라인 O(1).

non-OOS 테이블의 경우 2번에서 false 반환 후 즉시 종료. 추가 비용은 로그 레코드당 수 명령어 수준으로 추정.

#### 위험도

낮음-중간. 이론적으로 무시 가능한 수준이지만 **정량 확인이 남아 있다** (T0.5).

구 설계는 "OOS 있는 레코드만" 체인 워크를 했으므로 non-OOS 테이블에는 추가 비용이 없었다. 신 설계는 이 비용을 non-OOS 테이블에도 분산시킨다. 대규모 non-OOS 워크로드(예: 수백만 UPDATE의 OLTP)에서 측정 가능한 regression이 발생할 가능성은 낮지만 0은 아니다.

#### 권장 조치

T0.5 마이크로벤치마크 추가. non-OOS 테이블에서 `vacuum_process_log_block` 처리 시간을 PR 이전/이후 비교. 5% 미만 regression이면 수용 가능.

### 3.2 R2 — Defensive copy 비용

#### 설명

Inline 블록은 sysop 진입 전 undo_data를 스택 버퍼(`IO_MAX_PAGE_SIZE`, 16KB)로 복사하거나 크기 초과 시 `db_private_alloc`으로 힙 할당한다(vacuum.c:3672-3690).

- 스택 버퍼: 16KB 스택 공간 소비. 일반적인 heap recdes 크기(수 KB)에는 충분.
- 힙 할당: undo_data_size > 16KB인 OOS recdes에서 발생. 대용량 OOS (예: 160KB) 삭제 시 1회 `db_private_alloc` + `db_private_free_and_init`.

#### 위험도

낮음. 복사는 HAS_OOS=1인 경우에만 수행되며, 스택 경로가 일반 사례이므로 힙 할당은 드물다.

#### 주의점

스택 경로의 `undo_copy_stack[IO_MAX_PAGE_SIZE]`는 함수 진입마다 할당되는 스택 공간 16KB. `vacuum_process_log_block` 프레임에 VFID 캐시(16 × 2 VFID ≈ 256 bytes) + 기타 지역변수까지 합쳐 스택 footprint가 증가한다. 스레드 스택이 충분해야 하며 (CUBRID 기본 vacuum 워커 스택 크기는 안전 범위), 재귀 없이 선형 호출이라 overflow 위험은 없다고 판단.

**권장 조치:** 스택 크기를 모니터링. 필요 시 heap alloc-only 경로로 전환 고려(성능 손실).

### 3.3 R3 — VFID 캐시 eviction 정책 (slot 0 overwrite)

#### 설명

캐시가 16 엔트리를 꽉 채우면 17번째부터는 슬롯 0을 덮어쓴다(vacuum.c:3402-3407). LRU도 LFU도 아닌 단순 휴리스틱.

#### 위험도

낮음. 실질 영향:

- 한 블록이 17개 이상의 고유 heap VFID를 다룰 때 캐시 miss가 반복되어 `file_descriptor_get` + `heap_oos_find_vfid` 비용이 추가 발생.
- 정확성에는 영향 없음 (miss 후 재조회하면 정확한 결과).

#### 관찰

일반 OLTP 워크로드에서 한 vacuum 블록이 16개 이상의 서로 다른 테이블의 MVCC 힙 변경을 포함하는 경우는 드물다. 다만 broad multi-table update 워크로드에서는 발생할 수 있다.

**권장 조치:** 필요 시 크기 상향 또는 LRU 정책. 현재는 관찰 데이터 축적 후 결정 권장.

### 3.4 R4 — Sysop 페어링 invariant 깨짐 위험

#### 설명

`vacuum_process_log_block`의 loop tail(vacuum.c:3864)과 함수 종료 시점(vacuum.c:3885)에 assert.

```c
assert (!LOG_FIND_CURRENT_TDES (thread_p)->is_under_sysop ());
```

inline OOS 블록의 모든 경로가 이 불변식을 준수하도록 구성되어 있다(자세한 경로 분석은 `PR-6986-QnA.md` Q6 참조).

#### 위험도

낮음 — 현재 구현 기준. 중간 — 미래 유지보수 리그레션 위험.

코드 변경이 inline 블록 내 경로를 추가/수정할 때 sysop commit/abort 호출을 빠뜨리면 assert fire. debug build에서는 즉시 발견되지만 **release build에서는 조용한 상태 오염** 가능.

#### 권장 조치

Long-term: `assert`를 `assert_release`로 업그레이드 고려. 또는 RAII-style sysop 가드를 도입해 구조적으로 페어링을 강제(현재 CUBRID의 C 위주 코드에는 부적합할 수 있음).

Short-term: 코드 리뷰 체크리스트에 "sysop 페어링 검증" 항목 추가.

### 3.5 R5 — Corrupt log record 방어

#### 설명

Inline 블록은 `undo_data_size > 2 * IO_MAX_PAGE_SIZE`를 상한으로 가드하여 손상된 로그 레코드에서 메모리 오남용을 차단(vacuum.c:3661-3665).

```c
if (undo_data_size > 2 * IO_MAX_PAGE_SIZE)
  {
    assert_release (false);
    goto oos_cleanup_done;
  }
```

`assert_release`이므로 debug/release 모두에서 발동하며 abort가 아닌 skip 후 계속 진행 (vacuum block 처리가 전체 실패하지 않음).

#### 위험도

매우 낮음. 정상 heap recdes는 두 페이지를 넘지 않으며, 이 상한은 실질적으로 fail-safe 역할.

---

## 4. 현재 PR 리뷰 상태

### 4.1 Architect 관점

**의견 요약:**

- L1 해결에 대한 설계가 우아하고 최소 침습.
- 새 WAL 레코드 없이 기존 `RVOOS_DELETE` + sysop 조합으로 복구 의미론 달성 — 엔지니어링적으로 타당.
- Forward walk의 undo decode 비용이 non-OOS 테이블에 미치는 영향 정량 확인 필요 (T0.5).

**Consensus:** 구조적으로 수용 가능. 성능 벤치마크를 조건부로 요청.

### 4.2 Security 관점

**의견 요약:**

- 일시 실패 시 VFID 캐시에 false-negative를 기록하지 않도록 수정된 점(vacuum.c:3374-3381) 확인됨. 이전 초안에서 지적된 문제 해결.
- Defensive copy가 log page buffer invalidation 위험을 방어함. v2 Risk 테이블 항목 해결.
- Corrupt log 상한 가드(`2 * IO_MAX_PAGE_SIZE`)가 추가된 점 확인.

**Consensus:** 보안 관련 지적 사항은 모두 해결됨. 승인.

### 4.3 Code-review 관점

**의견 요약:**

- ~250 라인의 dead code 제거로 가독성 향상.
- Inline 블록이 `vacuum_process_log_block` 안에서 조금 크지만, 현재 주석이 의도를 명확히 설명하고 있어 수용 가능.
- Sysop 페어링 불변식이 assertion에만 의존하는 점은 미래 유지보수에서 주의 필요.

**Consensus:** 승인. 단 L3의 `assert_release` 업그레이드 권장사항 추가.

---

## 5. 머지 권장 여부 및 조건

### 5.1 머지 권장 여부

**YES — 머지 권장.** 블로커는 해제되었다.

### 5.2 머지 조건 (선택적)

**Merge before (required):**

- 없음. 현재 코드 그대로 머지 가능.

**Merge before (strongly recommended):**

- T0.5 마이크로벤치마크 실행 및 regression이 5% 이내임을 확인.

**Merge after (non-blocker, 후속 JIRA):**

- L2: SA_MODE DELETE eager cleanup.
- L3: REC_BIGONE 불변식을 `assert_release`로 업그레이드.
- L4 / T3.4: RELOCATION 누적 회귀 테스트.
- T3.2 / T3.3: crash inject 및 sysop 페어링 스트레스 테스트.
- R3: VFID 캐시 크기/정책 관찰 데이터 축적 후 결정.

### 5.3 모니터링 권장

머지 후 observability 관점:

- `VACUUM_ER_LOG_HEAP` 로그에서 `"forward-walk oos_delete failed"` (vacuum.c:3710)와 `"failed to allocate ... for undo copy"` (vacuum.c:3683) 발생률 추적.
- OOS 파일 크기 증가율 모니터 (OOS 누수 지표).

---

## 6. 사용자 질문 직답

> "이 PR이 모든 도달 불가능한 OOS 값을 정리하는가?"

**부분적으로 YES, 주요 경로는 완전히 커버.** 2026-04-17 리뷰와 비교.

| 경로 | 2026-04-17 판정 | 2026-04-20 판정 |
|---|---|---|
| MVCC UPDATE 체인 + DELETE (OOS 유지) | 부분 커버 | **완전 커버** (forward walk) |
| UPDATE-drops-all-OOS → DELETE (L1) | **누수** (블로커) | **완전 커버** (forward walk) |
| SA_MODE DELETE (L2) | 누수 (범위 외) | 누수 (범위 외) |
| REC_BIGONE + OOS (L3) | 조용한 누수 가능 | 조용한 누수 가능 |
| RELOCATION 누적 (L4) | 테스트 부재 | 테스트 부재 |

가장 심각했던 L1이 해결되었고, 나머지는 non-blocker 수준. "모든" 경로를 커버한다고 말하려면 L2(SA_MODE DELETE)가 해결되어야 하나, 이는 PR 범위 외로 분리되어 있다.

---

## 7. 권장 조치 우선순위

| Priority | 조치 | 머지 블로커? |
|---|---|---|
| P1 | T0.5 non-OOS 테이블 vacuum 마이크로벤치마크 | 권장 (블로커 아님) |
| P2 | L3 — REC_BIGONE + OOS 불변식 `assert_release` 업그레이드 | non-blocker |
| P2 | L4 / T3.4 — RELOCATION 누적 회귀 테스트 | non-blocker |
| P2 | R4 — sysop 페어링 테스트 스트레스 | non-blocker |
| P3 | L2 — SA_MODE DELETE eager cleanup (후속 JIRA) | 범위 외 |
| P3 | R3 — VFID 캐시 크기/정책 관찰 | non-blocker |

---

**리뷰어:** Claude Opus 4.7 (1M context)
**리뷰 방법:** PR diff, 신 설계 파일(`vacuum.c` forward walk 영역 vacuum.c:3337-3724), 관련 함수들(`heap_recdes_contains_oos`, `heap_recdes_get_oos_oids`, `oos_delete_chain`) 교차 확인. Phase 0 I1/I2 감사 결과 참조. 이전 리비전 보고서와 대조하여 각 L1-L4 재평가.
