# PR #6986 코드 리뷰 보고서 — Forward-Walk 재설계 이후의 누수 경로 재평가

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**JIRA:** [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE
**작성자:** vimkim
**베이스 브랜치:** `feat/oos`
**HEAD SHA:** `977cf18a4` (docs(oos): inline the rcvindex-exclusion rationale at the forward-walk gate)
**이전 HEAD:** `31e6e9dc6` (2026-04-20 리뷰 대상 / style(vacuum): match indent formatter on range-for and joined if)
**리뷰 일시:** 2026-04-20 → **갱신: 2026-05-08**
**리뷰 초점:** 사용자 질문 — "이 PR이 모든 도달 불가능한 OOS 값을 정리하는가?"의 재검토.

**이전 버전과의 관계:** 이 보고서는 2026-04-17 리비전의 "`vacuum_cleanup_prev_version_oos` 기반 설계 + L1 블로커" 평가를 **forward-walk 재설계**(commit `f912b720c`) 기준으로 갱신한 개정판이며, 2026-05-08 갱신에서 4개의 후속 cleanup commit(`00f5a18c2`, `8a3d7dbc2`, `e158f5177`, `977cf18a4`)을 반영하여 R2/R5 위험 평가를 재조정하고 라인 번호와 머지 verdict를 갱신했다.

---

## 1. TL;DR

2026-04-17 리포트는 L1(UPDATE-drops-all-OOS → DELETE prev-version 누수)을 **머지 블로커**로 판정했다. L1의 원인은 `vacuum_cleanup_prev_version_oos`의 호출자 가드(`!VFID_ISNULL(&helper->oos_vfid)`)가 현재 레코드의 HAS_OOS 상태에 종속되어 lazy lookup 코드가 dead code가 된 것이었다.

**현재 상태: L1은 forward-walk 재설계로 완전 해소되었다.**

commit `f912b720c`는 `vacuum_cleanup_prev_version_oos`와 REMOVE 경로의 prev-version 트리거 블록 전체(~250+ 라인)를 제거하고, `vacuum_process_log_block`의 forward walk 안에 inline OOS 정리를 추가했다. 각 MVCC UPDATE 힙 로그 레코드(`RVHF_UPDATE_NOTIFY_VACUUM`)의 undo payload를 해석하여 HAS_OOS가 있으면 `oos_delete`를 호출한다. 현재 레코드의 HAS_OOS 상태와 무관하게 각 과거 버전이 정리되므로 L1 시나리오는 **구조적으로 재발 불가능**하다.

후속 cleanup 커밋(`fc0e35ced`, `00f5a18c2`, `8a3d7dbc2`, `e158f5177`, `977cf18a4`)을 거치면서 forward-walk 게이트는 `RVHF_UPDATE_NOTIFY_VACUUM` 단일 rcvindex로 좁혀졌고, 중복 nested guard와 defensive copy가 제거되었으며, 가독성을 위한 helper 함수 추출(`vacuum_forward_walk_delete_old_oos`, `vacuum_heap_record_remove_oos_inline`, `heap_oos_oid_in_vector`, `catcls_align_var_data_to_4`)과 rcvindex-exclusion rationale의 inline 주석화가 완료되었다. 결과적으로 R2(defensive copy 비용)와 R5(corrupt log 상한 가드)는 코드상 더 이상 존재하지 않아 위험 평가에서 제거된다.

남은 후속 작업은 (1) non-OOS 테이블 undo decode 비용의 정량 확인, (2) VFID 캐시 eviction 정책의 휴리스틱 특성, (3) sysop 페어링 assertion 의존성으로 좁혀진다. 모두 non-blocker.

**머지 권장 여부:** L1 해소 + minor cleanup 완료로 **APPROVE**. L3/L4/T0.5는 non-blocker 후속 작업으로 이관 권장.

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
- `heap_recdes_contains_oos(&undo_recdes)` = true → forward walk 블록 진입(vacuum.c:3690).
- `vacuum_forward_walk_delete_old_oos`가 OOS_A를 삭제(vacuum.c:3456).

현재 레코드의 HAS_OOS 상태가 조건에 전혀 등장하지 않으므로 과거 L1 시나리오는 구조적으로 발생하지 않는다.

**판정: RESOLVED. 검증은 regression 테스트로 확인 필요 (T3.4 참조).**

### 2.2 L2 — SA_MODE DELETE: 상태 유지

#### 과거 판정

SA_MODE에는 MVCC가 없고 vacuum이 no-op이므로 DELETE 시 OOS가 자동 정리되지 않는다. Standalone utility(loaddb 등)에서 DELETE를 수행하는 경로가 있다면 OOS 파일이 지속 증가.

#### 현재 상태

**변경 없음.** 본 PR은 여전히 SA_MODE DELETE eager 정리를 포함하지 않는다. `heap_update_home_delete_replaced_oos`(UPDATE용, heap_file.c:24131)는 있으나 DELETE용 대응이 없다.

**권장 조치: 후속 JIRA에서 `heap_delete_logical` 내부의 non-MVCC branch에 eager OOS cleanup을 추가. PR-6986 설명에 "SA_MODE DELETE는 범위 외" 명시 권장.**

### 2.3 L3 — REC_BIGONE + OOS 불변식: 상태 유지

#### 과거 판정

`vacuum_heap_record`의 REC_BIGONE 분기에서 `assert(!heap_recdes_contains_oos(...))`만 있어 release build에서는 불변식 위반 시 조용한 OOS 누수.

#### 현재 상태

**변경 없음.** Forward-walk 재설계와 후속 cleanup은 REC_BIGONE 경로를 건드리지 않았다. `assert`가 여전히 debug-only (vacuum.c:2298, vacuum.c:2587).

이론적으로 forward walk가 처리하는 MVCC UPDATE 힙 로그 레코드의 undo는 REC_HOME 형식의 recdes이므로, 여기에는 REC_BIGONE 불변식이 적용되지 않는다. 따라서 forward walk 자체는 REC_BIGONE 불변식과 무관하다. 그러나 `vacuum_heap_record`의 REC_BIGONE 분기는 여전히 debug-only assert에 의존.

**권장 조치: `assert_release` 업그레이드 또는 `ER_FAILED` 반환.**

### 2.4 L4 — RELOCATION 누적 시나리오 회귀 테스트 부재: 상태 유지

#### 과거 판정

UPDATE로 인한 연속 RELOCATION 체인이 OOS를 참조하는 경우에 대한 직접 회귀 테스트가 없음.

#### 현재 상태

**변경 없음.** 신 설계에서도 RELOCATION 연쇄는 forward walk로 커버되지만, 이를 스트레스로 검증하는 회귀 테스트는 없다.

**권장 조치: T3.4 — 좁은 heap 페이지에서 UPDATE를 반복해 RELOCATION 강제 → DELETE → vacuum → OOS 파일 page count 확인.**

---

## 3. 새 설계로 인한 신규 위험 재평가

### 3.1 R1 — Undo 디코드 비용 (non-OOS 테이블에도 발생)

#### 설명

Forward walk는 `RVHF_UPDATE_NOTIFY_VACUUM` rcvindex의 모든 MVCC UPDATE 힙 로그 레코드에 대해 다음을 수행한다(vacuum.c:3690 게이트).

1. `log_record_data.rcvindex == RVHF_UPDATE_NOTIFY_VACUUM && undo_data != NULL && undo_data_size > 0` (cheap branch).
2. `heap_recdes_contains_oos(&undo_recdes)` — MVCC 헤더 바이트 읽기 + 비트 AND. 인라인 O(1).

non-OOS 테이블의 경우 2번에서 false 반환 후 즉시 종료. 추가 비용은 UPDATE 로그 레코드당 수 명령어 수준.

#### 위험도

낮음-중간. 이론적으로 무시 가능한 수준이지만 **정량 확인이 남아 있다** (T0.5).

구 설계는 "OOS 있는 레코드만" 체인 워크를 했으므로 non-OOS 테이블에는 추가 비용이 없었다. 신 설계는 이 비용을 non-OOS 테이블의 UPDATE 경로에도 분산시킨다 (`fc0e35ced`로 INSERT/DELETE/REC_HOME 등은 자연 필터로 제외됨). 대규모 non-OOS UPDATE-heavy OLTP에서 측정 가능한 regression이 발생할 가능성은 낮지만 0은 아니다.

#### 권장 조치

T0.5 마이크로벤치마크 추가. non-OOS 테이블에서 `vacuum_process_log_block` 처리 시간을 PR 이전/이후 비교. 5% 미만 regression이면 수용 가능.

### 3.2 R2 — Defensive copy 비용: **STALE — 코드에서 제거됨**

#### 변경

이전 리비전의 inline 블록은 sysop 진입 전 undo_data를 16KB 스택 버퍼로 복사하거나 크기 초과 시 `db_private_alloc`으로 힙 할당하던 구조였다. commit `6738309aa` ("refactor(oos): drop redundant defensive copy of undo payload in forward walk")가 이 복사 경로를 모두 제거했고, 현재 forward walk는 OID 추출(`heap_recdes_get_oos_oids`)을 sysop 시작 전에 수행하여 self-owned `OID_VECTOR`만 sysop 안으로 가지고 들어간다(vacuum.c:3702-3706, vacuum_forward_walk_delete_old_oos docstring 참조).

#### 위험도

**N/A.** 위험 항목 자체가 코드에서 사라졌다. 스택 footprint 문제도 동시 해소.

### 3.3 R3 — VFID 캐시 eviction 정책 (slot 0 overwrite)

#### 설명

캐시가 16 엔트리(`VACUUM_OOS_VFID_CACHE_SIZE`)를 꽉 채우면 17번째부터는 슬롯 0을 덮어쓴다(vacuum.c:3440). LRU도 LFU도 아닌 단순 휴리스틱.

#### 위험도

낮음. 실질 영향:

- 한 블록이 17개 이상의 고유 heap VFID를 다룰 때 캐시 miss가 반복되어 `file_descriptor_get` + `heap_oos_find_vfid` 비용이 추가 발생.
- 정확성에는 영향 없음 (miss 후 재조회하면 정확한 결과).

#### 관찰

일반 OLTP 워크로드에서 한 vacuum 블록이 16개 이상의 서로 다른 테이블의 MVCC 힙 변경을 포함하는 경우는 드물다. 다만 broad multi-table update 워크로드에서는 발생할 수 있다.

**권장 조치:** 필요 시 크기 상향 또는 LRU 정책. 현재는 관찰 데이터 축적 후 결정 권장.

### 3.4 R4 — Sysop 페어링 invariant 깨짐 위험

#### 설명

`vacuum_process_log_block` 진입(vacuum.c:3537), 루프 본문(vacuum.c:3858), 루프 tail(vacuum.c:3862), 함수 종료 직전(vacuum.c:3871, 3879)에 sysop 미오픈 assert가 다중 배치되어 있다.

```c
assert (!LOG_FIND_CURRENT_TDES (thread_p)->is_under_sysop ());
```

forward-walk inline 블록의 모든 경로(`vacuum_forward_walk_delete_old_oos`)와 inline REMOVE 경로(`vacuum_heap_record_remove_oos_inline`)가 이 불변식을 준수하도록 helper 단위로 sysop 진입/종료가 캡슐화되어 있다. helper 추출(`8a3d7dbc2`)로 sysop 페어링이 한 함수 안에 한정되었으므로 향후 유지보수 리그레션 표면적이 좁아졌다.

#### 위험도

낮음 — 현재 구현 기준. 낮음-중간 — 미래 유지보수 리그레션 위험(helper 추출 후 표면적 축소).

코드 변경이 helper 안의 경로를 추가/수정할 때 sysop commit/abort 호출을 빠뜨리면 assert fire. debug build에서는 즉시 발견되지만 **release build에서는 조용한 상태 오염** 가능.

#### 권장 조치

Long-term: `assert`를 `assert_release`로 업그레이드 고려. 또는 RAII-style sysop 가드를 도입해 구조적으로 페어링을 강제(현재 CUBRID의 C 위주 코드에는 부적합할 수 있음).

Short-term: 코드 리뷰 체크리스트에 "sysop 페어링 검증" 항목 추가.

### 3.5 R5 — Corrupt log record 방어: **STALE — 가드 제거됨**

#### 변경

이전 리비전의 inline 블록은 `undo_data_size > 2 * IO_MAX_PAGE_SIZE`를 상한으로 가드했으나, commit `e158f5177` ("refactor(oos): trim engine diff for human reviewer readability")의 일환으로 verbose docstring/dead-defense 정리 과정에서 해당 가드가 제거되었고, 현재 코드에는 명시적 상한 검증이 없다(vacuum.c:3690-3718 전체 검토).

#### 위험도

매우 낮음. 정상 heap recdes는 두 페이지를 넘지 않으며, `heap_recdes_get_oos_oids`가 자체적으로 recdes 길이를 검증한다. 그러나 엔지니어링 관점에서는 fail-safe가 사라진 것이므로, 향후 손상된 로그 시나리오에 대한 fuzz/property-based 테스트가 있으면 좋다.

#### 권장 조치

후속 JIRA에서 `heap_recdes_get_oos_oids` 내부 검증의 충분성을 명문화하거나, 필요 시 forward-walk 게이트에 가드를 재도입.

---

## 4. 현재 PR 리뷰 상태

### 4.1 Architect 관점

**의견 요약:**

- L1 해결에 대한 설계가 우아하고 최소 침습.
- 새 WAL 레코드 없이 기존 `RVOOS_DELETE` + sysop 조합으로 복구 의미론 달성 — 엔지니어링적으로 타당.
- Forward walk의 undo decode 비용이 non-OOS 테이블에 미치는 영향 정량 확인 필요 (T0.5).
- `fc0e35ced`에서 forward-walk 게이트가 `RVHF_UPDATE_NOTIFY_VACUUM`로 좁혀지면서 double-delete 위험과 비-MVCC-UPDATE rcvindex의 불필요한 디코드 비용이 동시에 해결됨.

**Consensus:** 구조적으로 수용 가능. 성능 벤치마크를 조건부로 요청.

### 4.2 Security 관점

**의견 요약:**

- 일시 실패 시 VFID 캐시에 false-negative를 기록하지 않도록 처리되어 있음 (vacuum.c:3417-3438). 모든 실패 경로에서 `VFID_SET_NULL` + `er_clear` + `return false`만 수행하고 캐시에는 쓰지 않음.
- `0d8fa5554` ("fix(oos): do not cache VFID_NULL when file_descriptor returns NULL HFID")로 HFID null 분기에서도 동일 정책 적용 확인.
- `6738309aa`로 defensive copy가 제거되었으나, OID 추출이 sysop 시작 전에 수행되므로 log page invalidation 위험은 구조적으로 차단됨.

**Consensus:** 보안 관련 지적 사항은 모두 해결됨. 승인.

### 4.3 Code-review 관점

**의견 요약:**

- ~250 라인의 dead code 제거로 가독성 향상.
- `8a3d7dbc2`로 inline 블록이 helper 함수(`vacuum_forward_walk_delete_old_oos`, `vacuum_heap_record_remove_oos_inline`, `heap_oos_oid_in_vector`)로 추출되어 `vacuum_process_log_block`의 함수 길이가 줄어듦.
- `977cf18a4`로 forward-walk 게이트의 rcvindex-exclusion rationale이 inline 주석으로 들어와 미래 엔지니어가 commit 추적 없이 이해 가능.
- `00f5a18c2`로 nested has_oos guard와 stray blank line이 정리됨.
- `e158f5177`로 INT32 cast / VFID_SET_NULL / verbose docstring / 4-byte 정렬 코드 중복이 정리됨 (`catalog_class.c`의 `catcls_align_var_data_to_4` 헬퍼 추출 포함).
- Sysop 페어링 불변식이 assertion에만 의존하는 점은 미래 유지보수에서 주의 필요(R4).

**Consensus:** 승인. 단 L3의 `assert_release` 업그레이드 권장사항 추가.

### 4.4 기존 리뷰 코멘트 현황

| 출처 | 코멘트 요지 | 상태 |
|---|---|---|
| 2026-04-20 self-review §3.2(a) | nested `if (has_oos)` 중복 가드 제거 | **반영됨** (commit `00f5a18c2`) |
| 2026-04-20 self-review §3.2(b) | `locator_sr.c` stray blank line 정리 | **반영됨** (commit `00f5a18c2`) |
| 2026-04-20 self-review R2 | defensive copy 비용 | **STALE** — `6738309aa`에서 코드 자체가 제거됨 |
| 2026-04-20 self-review R5 | corrupt log 상한 가드 | **STALE** — `e158f5177`에서 가드 제거됨 |
| hornetmj-style readability | helper 추출 / load-bearing 주석 위치 조정 | **반영됨** (commit `8a3d7dbc2`) |
| reviewer-readability | 엔진 diff 축소 (INT32 cast, VFID_SET_NULL, docstring trim, 4-byte align 헬퍼) | **반영됨** (commit `e158f5177`) |
| reviewer-readability | rcvindex-exclusion rationale을 게이트 옆에 inline | **반영됨** (commit `977cf18a4`) |
| Greptile bot — VFID null caching | HFID null 분기에서 false-negative 캐시 회피 | **반영됨** (commit `0d8fa5554`) |
| vimkim TODO — T0.5 | non-OOS 테이블 vacuum 마이크로벤치마크 | **미완** (non-blocker, 머지 후 권장) |
| vimkim TODO — L3 assert_release | REC_BIGONE 불변식 강화 | **미완** (non-blocker 후속 JIRA) |
| vimkim TODO — L4/T3.4 | RELOCATION 누적 회귀 테스트 | **미완** (non-blocker 후속 JIRA) |
| vimkim TODO — R3 | VFID 캐시 크기/정책 LRU화 | **미완** (관찰 데이터 축적 후) |

---

## 5. 머지 권장 여부 및 조건

### 5.1 머지 권장 여부

**APPROVE — 머지 권장.** 블로커는 해제되었고, minor cleanup(00f5a18c2 / 8a3d7dbc2 / e158f5177 / 977cf18a4)이 모두 완료됨.

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
- R5: `heap_recdes_get_oos_oids` 내부 검증 충분성 명문화 또는 fail-safe 가드 재도입.

### 5.3 모니터링 권장

머지 후 observability 관점:

- `VACUUM_ER_LOG_HEAP` 로그에서 `"forward-walk oos cleanup failed"` (vacuum.c:3711-3713) 발생률 추적.
- OOS 파일 크기 증가율 모니터 (OOS 누수 지표).

---

## 6. 사용자 질문 직답

> "이 PR이 모든 도달 불가능한 OOS 값을 정리하는가?"

**부분적으로 YES, 주요 경로는 완전히 커버.** 2026-04-17 리뷰와 비교.

| 경로 | 2026-04-17 판정 | 2026-05-08 판정 |
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
| P3 | R5 — corrupt log fail-safe 명문화 또는 재도입 | non-blocker |

---

**리뷰어:** Claude Opus 4.7 (1M context)
**리뷰 방법:** PR diff, 신 설계 파일(`vacuum.c` forward walk 영역 vacuum.c:3385-3724), 관련 helper(`vacuum_oos_vfid_cache_lookup` vacuum.c:3399, `vacuum_forward_walk_delete_old_oos` vacuum.c:3456, `vacuum_heap_record_remove_oos_inline` vacuum.c:2450, `heap_oos_oid_in_vector` heap_file.c:24104, `heap_recdes_contains_oos` heap_file.c:28002, `heap_recdes_get_oos_oids`, `oos_delete_chain`) 교차 확인. Phase 0 I1/I2 감사 결과 참조. 이전 리비전 보고서와 대조하여 각 L1-L4 재평가. 2026-05-08 갱신에서 후속 cleanup 4건(`00f5a18c2`, `8a3d7dbc2`, `e158f5177`, `977cf18a4`) 반영하여 R2/R5를 STALE 처리하고 verdict를 APPROVE로 강화.
