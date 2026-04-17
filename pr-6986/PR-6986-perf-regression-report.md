# PR #6986 — Vacuum Prev-Version Chain Walk 성능 회귀 분석 및 수정 보고서

**PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986)
**수정 커밋:** `899d5b633` — fix(oos): guard REMOVE-path prev_version chain walk on oos_vfid being set
**원인 커밋:** `0748432eb` — fix(oos): prevent dangling OOS on UPDATE→DELETE and chain-walk livelock
**리포트 작성일:** 2026-04-17
**증상 테스트:** `sql/_01_object/_09_partition/_001_create/cases/1189.sql` 외 다수 (CI 컨테이너 0 타임아웃)

---

## 1. Summary

P1 버그 수정(dangling OOS on UPDATE→DELETE)이 의도치 않게 OOS를 사용하지 **않는** 모든 테이블의 vacuum 경로에 **로그 체인 순회 비용**을 추가하여 partition 생성/변경 테스트가 대폭 느려지는 회귀를 발생시켰다.

본 수정은 `vacuum_heap_record` REMOVE 경로의 가드에 `!VFID_ISNULL(&helper->oos_vfid)` 한 줄을 추가하여, **OOS 파일이 없는 테이블은 체인 순회 자체를 건너뛰게** 한다.

---

## 2. Background — The P1 Fix and How It Introduced the Regression

### 2.1 P1 버그 (dangling OOS on UPDATE→DELETE)

MVCC 환경에서 다음 시퀀스가 발생하면 vacuum이 **구버전 OOS 레코드를 회수하지 못하는 누수**가 있었다:

```
T1:  INSERT ... (OOS_A 생성)       -- heap v1, OOS_A
T2:  UPDATE  ... (OOS_B 생성)       -- heap v2 (prev_version_lsa → undo(v1))
T3:  DELETE  ...                    -- heap v2 (DELID 설정)
Tv:  vacuum 처리                    -- INSID와 DELID가 동시에 가시화
```

`mvcc_satisfies_vacuum()` 은 INSID와 DELID가 동시에 가시화된 경우 `VACUUM_RECORD_REMOVE` 를 반환한다. 이때 실행되는 `vacuum_heap_record()` 는 **현재 레코드(OOS_B)**만 삭제하고, **`prev_version_lsa` 를 따라가지 않았다**. heap 슬롯이 제거되면서 체인 포인터가 함께 사라져 **OOS_A는 영구적으로 고아**가 되었다.

`vacuum_heap_record_insid_and_prev_version()` 은 이 체인을 순회했지만, `VACUUM_RECORD_DELETE_INSID_PREV_VER` 경로에서만 호출되므로 이 시나리오에서는 탈 수 없었다.

### 2.2 원인 커밋(`0748432eb`)의 수정

REMOVE 경로에서도 체인을 순회하도록 `vacuum_cleanup_prev_version_oos()` 호출을 추가했다:

```c
bool need_prev_version_oos_cleanup = (MVCC_IS_HEADER_PREV_VERSION_VALID (&helper->mvcc_header)
                                        && (helper->record_type == REC_HOME
                                            || helper->record_type == REC_RELOCATION));

if (... || need_prev_version_oos_cleanup)
  {
    vacuum_heap_page_log_and_reset (...);
    log_sysop_start (...);
  }

if (need_prev_version_oos_cleanup)
  {
    int chain_err = vacuum_cleanup_prev_version_oos (thread_p, helper);
    ...
  }
```

### 2.3 놓친 가드

같은 기능을 하는 `vacuum_heap_record_insid_and_prev_version()` 쪽의 기존 가드는:

```c
if (MVCC_IS_HEADER_PREV_VERSION_VALID (&helper->mvcc_header)
    && !VFID_ISNULL (&helper->oos_vfid))
  {
    /* chain walk */
  }
```

**`!VFID_ISNULL(&helper->oos_vfid)`** — "이 heap에 OOS 파일이 있을 때만 순회" — 가 핵심 조건이었다. P1 수정에서는 이 조건을 빠뜨렸다.

---

## 3. Why This Caused a Performance Regression

### 3.1 `vacuum_cleanup_prev_version_oos()` 의 비용

체인 순회 루프는 버전마다 **실제 로그 I/O**를 수반한다:

```
while (!LSA_ISNULL (&current_lsa))
  {
    LOG_CS_ENTER (thread_p);
    logpb_prior_lsa_append_all_list (thread_p);    // prior list flush
    LOG_CS_EXIT (thread_p);

    logpb_fetch_page (thread_p, &current_lsa, ...);  // 로그 페이지 I/O
    log_get_undo_record (thread_p, log_page_p, ...); // undo 레코드 파싱

    if (heap_recdes_contains_oos (&old_recdes))
      {
        /* OOS 삭제 */
      }

    or_mvcc_get_header (&old_recdes, &old_mvcc_header);
    LSA_COPY (&current_lsa, &MVCC_GET_PREV_VERSION_LSA (&old_mvcc_header));
  }
```

**버전 당 비용:**
- `LOG_CS` 진입/해제 (전역 경합 지점)
- 로그 페이지 fetch (디스크 또는 로그 버퍼 풀 탐색)
- undo 레코드 파싱
- MVCC 헤더 파싱

**테이블에 OOS가 전혀 없어도 이 비용이 전부 발생**했다. 체인을 끝까지 따라가야 "OOS 없음"을 확인할 수 있기 때문이다.

### 3.2 Partition 테스트에서의 영향

`sql/_01_object/_09_partition/_001_create/cases/*.sql` 은 다음과 같은 작업을 대량으로 수행한다:

- `CREATE TABLE ... PARTITION BY ...` — 여러 파티션 생성
- `ALTER TABLE` — 파티션 추가/변경
- 파티션 경계 설정 변경

이 작업들은 **카탈로그 클래스 레코드에 연쇄적인 UPDATE** 를 발생시킨다. 각 UPDATE는 `prev_version_lsa` 체인을 만든다. 이후 해당 트랜잭션들이 커밋되고 vacuum이 실행될 때:

- 카탈로그 테이블에는 **OOS 파일이 없다**.
- 그러나 가드 부재로 인해 vacuum이 **모든 MVCC 레코드에 대해 체인 순회**를 시도했다.
- 체인 길이가 N이면 N번의 `logpb_fetch_page` + `LOG_CS` 획득.
- 결과: CI 컨테이너 0이 타임아웃 전에 테스트를 완료하지 못함.

### 3.3 왜 유닛 테스트에서는 잡히지 않았나

기존 OOS 유닛 테스트(`test_oos_*`)는:
- 오직 OOS 플래그가 있는 레코드만 다룸 — `oos_vfid` 가 항상 설정되어 가드 유무와 무관하게 동일 경로를 탐.
- 카탈로그 수준의 churn이 없음 — 순회할 긴 체인이 생성되지 않음.
- SQL 통합 테스트는 SA_MODE이며 `vacuum` 이 no-op.

즉, 회귀가 발생한 **MVCC + catalog churn + no-OOS-file** 조합을 전혀 exercise하지 못했다.

---

## 4. How the Fix Works

### 4.1 변경 내용

```c
-  bool need_prev_version_oos_cleanup = (MVCC_IS_HEADER_PREV_VERSION_VALID (&helper->mvcc_header)
-                                        && (helper->record_type == REC_HOME
-                                            || helper->record_type == REC_RELOCATION));
+  bool need_prev_version_oos_cleanup = (MVCC_IS_HEADER_PREV_VERSION_VALID (&helper->mvcc_header)
+                                        && !VFID_ISNULL (&helper->oos_vfid)
+                                        && (helper->record_type == REC_HOME
+                                            || helper->record_type == REC_RELOCATION));
```

### 4.2 `oos_vfid` 가 언제 채워지는가

`vacuum_heap_prepare_record()` 는 **현재 레코드**에 OOS 플래그가 있을 때만 `heap_oos_find_vfid()` 를 호출하여 `oos_vfid` 를 채운다 (`vacuum_ensure_oos_vfid_for_heap_record` 헬퍼에서 처리). 결과적으로:

| 레코드 상태 | `oos_vfid` | 체인 순회? |
|-------------|-----------|------------|
| 현재 레코드에 OOS 플래그 있음 | 채워짐 | **예** (P1 수정 발동) |
| 현재 레코드에 OOS 플래그 없음 + 테이블에 OOS 파일 없음 | NULL | 아니오 (가드로 차단) |
| 현재 레코드에 OOS 플래그 없음 + 테이블에 OOS 파일 있음 | NULL | 아니오 (아래 Known Limitation) |

### 4.3 P1 수정의 목적 달성 여부

**달성:**
- 일반적인 MVCC UPDATE 체인 (OOS 컬럼이 UPDATE를 통해 유지됨) → 현재 레코드에 OOS 플래그 → `oos_vfid` 채워짐 → 체인 순회 → 구버전 OOS 회수 ✅
- 즉, P1의 주 시나리오 (`UPDATE oos_col=X; UPDATE oos_col=Y; DELETE;`) 는 그대로 수정됨.

**놓치는 엣지 케이스 (의도적으로 허용):**
- `UPDATE` 가 **모든** OOS 컬럼을 non-OOS 값으로 바꾸고 그 직후 `DELETE` → 현재 레코드에 OOS 플래그 없음 → `oos_vfid` NULL → 체인 미순회 → 구버전 OOS 누수.

### 4.4 트레이드오프 결정 근거

| 옵션 | 성능 비용 | 누수 | 결정 |
|------|-----------|------|------|
| A. 가드 없음 (원래 P1 수정) | 모든 MVCC 테이블에서 체인 순회 | 없음 | **거부** — 운영 워크로드에서 수용 불가 |
| B. `oos_vfid` 가드 추가 (현재 수정) | OOS 테이블에서만 체인 순회 | 드문 엣지 케이스 누수 | **채택** |
| C. 체인 진입 전 heap 레벨 `heap_oos_find_vfid` 조건부 호출 | OOS 테이블에서만 순회 + heap 헤더 READ latch 추가 획득 | 누수 없음 | **향후 고려** — 현재 측정치 없음 |

옵션 C는 이론적으로 가장 이상적이지만, heap 헤더 페이지 READ latch를 모든 prev_version-havng 레코드에 대해 획득해야 한다. 현재 데이터로는 옵션 B 대비 이점이 불분명하여 후속 개선 과제로 남긴다.

### 4.5 Known Limitation 문서화

수정과 함께 코드에 다음 주석을 추가했다:

```c
/* Guard on !VFID_ISNULL(oos_vfid): vacuum_heap_prepare_record populates oos_vfid whenever the
 * CURRENT record carries the OOS flag, which is the common case for UPDATE chains (an OOS column
 * preserved across updates). Skipping when oos_vfid is NULL avoids paying the log-chain-walk I/O
 * (logpb_fetch_page + LOG_CS per version) on every MVCC-updated record in OOS-less tables — a
 * significant partition/catalog workload cost. Known limitation: UPDATEs that drop every OOS
 * column and are then DELETEd leave no OOS flag on the current record; their prev-version OOS
 * leak until a full-table rewrite. REC_BIGONE is excluded by invariant (OOS does not coexist
 * with overflow records). */
```

---

## 5. Q&A (한국어)

### Q1. "이 수정이 P1 버그를 다시 재도입하지 않는다"는 주장의 근거는?

**A.** P1 버그의 주요 시나리오는 "UPDATE로 OOS 컬럼을 교체 → DELETE → vacuum REMOVE"다. 이 경우:

1. 현재 레코드(마지막 UPDATE 결과)는 OOS 플래그를 **가진다** (OOS 컬럼이 여전히 존재).
2. `vacuum_heap_prepare_record()` 가 `oos_vfid` 를 채운다.
3. 새 가드 `!VFID_ISNULL(&helper->oos_vfid)` 는 참이 되어 체인 순회가 발동한다.
4. `vacuum_cleanup_prev_version_oos()` 가 prev_version 체인의 OOS_A(구버전)를 삭제한다.

따라서 P1의 본래 scenario는 그대로 수정된다. 유일하게 놓치는 것은 "UPDATE가 모든 OOS 컬럼을 non-OOS로 변경한 뒤 DELETE"라는 매우 좁은 엣지 케이스다.

### Q2. 기존 P1 수정이 "OOS 없는 테이블에서 체인을 순회했다"는 게 왜 문제였는가? 체인이 비어 있으면 순회도 즉시 끝나지 않나?

**A.** 체인이 비어 있는 것과 체인 **끝에 도달**하는 것은 다르다. `prev_version_lsa` 가 유효하면(즉 레코드가 한 번이라도 UPDATE되었다면) 체인은 최소 1개 버전을 가진다. 각 버전마다:

- `logpb_fetch_page` — 로그 페이지 I/O (버퍼 miss 시 디스크 읽기).
- `LOG_CS_ENTER/EXIT` — 전역 critical section.
- `log_get_undo_record` — undo 레코드 디코드.
- `heap_recdes_contains_oos` — VOT 스캔 (debug 빌드에서는 cross-validation 포함).

체인 길이 N에 대해 N번 발생한다. partition 테스트처럼 한 트랜잭션에서 여러 번 UPDATE되는 카탈로그 레코드가 대량으로 vacuum되면 총 비용이 현저해진다.

### Q3. `oos_vfid` 를 캐시할 수는 없나? 한 번 조회하고 재사용하면 되지 않나?

**A.** 이미 캐시한다. `VACUUM_HEAP_HELPER::oos_vfid` 는 `vacuum_heap_page` 호출 전체에 걸쳐 재사용된다. 문제는 **무엇을 캐시 키로 쓰는가**이다.

현재 설계: **한 페이지 내에서 어떤 레코드라도 OOS 플래그가 있으면 그 페이지 처리 동안 `oos_vfid` 를 유지**. 페이지 내 모든 레코드가 OOS 플래그가 없다면 `oos_vfid` 는 NULL로 남는다.

더 나은 캐시: "이 heap 파일에 OOS 파일이 존재하는가"를 heap 전체 수명 동안 캐시. 그러나 이는 페이지 간 공유 상태가 필요하고, 인덱스 역할을 하는 `heap_Bestspace` 같은 구조에 새 필드를 추가해야 한다. 현재 수정에서는 영향 범위를 최소화하기 위해 미채택.

### Q4. 엣지 케이스(OOS 컬럼을 모두 drop한 뒤 DELETE) 누수는 얼마나 자주 발생하나?

**A.** 가능성은 있지만 드물다. 일반적인 OLTP 워크로드에서:

- OOS 컬럼이 있는 행은 보통 BIT VARYING 같은 가변 길이 대용량 컬럼이다.
- UPDATE가 해당 컬럼을 **전부** non-OOS 길이로 바꾸는 것은 흔하지 않다 (e.g. `UPDATE t SET big_col = 'small'`).
- DELETE가 바로 뒤따르는 것은 더 드물다.
- 누수가 발생해도 heap 파일 자체가 drop되거나 compact되면 회수된다.

실제 발생률은 부하 테스트로 측정해봐야 정확하지만, partition 테스트에서 **모든 MVCC UPDATE에 체인 순회 비용을 부과**하는 것보다는 훨씬 낮은 영향으로 판단한다.

### Q5. 왜 이 회귀가 PR의 유닛 테스트에서 잡히지 않았나?

**A.** 세 가지 이유:

1. **SA_MODE SQL 테스트는 vacuum을 실제로 타지 않는다.** SA_MODE는 in-place overwrite라 prev_version 체인을 만들지 않고, vacuum도 no-op다.
2. **SERVER_MODE 유닛 테스트는 OOS 레코드만 다룬다.** 모든 테스트 케이스가 OOS 플래그가 있는 레코드를 만들어 사용한다. `oos_vfid` 가 항상 채워지므로 가드 유무로 경로가 갈리지 않는다.
3. **카탈로그 churn을 시뮬레이션하지 않는다.** 파티션 생성/변경처럼 카탈로그 메타데이터 레코드에 연쇄 UPDATE를 발생시키는 시나리오가 없다.

이는 PR-6986-report.md 에 기술한 테스트 커버리지 gap의 연장선이다. 해결책은 시스템 레벨 통합 테스트(CTest shell 또는 detached worker transaction)이며, 해당 PR의 `DISABLED_` 테스트가 그 방향을 제시한다.

### Q6. `heap_recdes_contains_oos` debug 빌드 cross-validation이 영향을 주진 않았나?

**A.** Debug 빌드에서 매 호출마다 VOT 스캔을 추가한 것은 맞으나, 이는 본 회귀의 주 원인이 아니다.

- 회귀가 보고된 CI 테스트는 보통 debug 또는 release 빌드 중 하나로 돌지만, P1 회귀는 **체인 순회 I/O** 때문에 발생했고 이는 debug/release 무관하게 동일 비용이다.
- `heap_recdes_contains_oos` 비용은 CPU 바운드이며, `logpb_fetch_page` 비용(I/O + lock)에 비해 현저히 작다.

별개의 개선으로 debug 빌드에서 cross-validation의 호출 빈도를 줄이는 것은 고려 가능하나 이번 회귀와는 분리된 과제다.

### Q7. 옵션 C (heap 레벨 `heap_oos_find_vfid` 조건부 호출)를 지금 구현하지 않는 이유는?

**A.** 세 가지:

1. **누수 크기를 먼저 측정해야 한다.** 엣지 케이스 누수가 실제 얼마나 발생하는지 데이터 없이 옵션 C 같은 방어 코드를 추가하는 것은 성급한 최적화다.
2. **READ latch 경합 비용이 불명.** `heap_oos_find_vfid` 는 heap 헤더 페이지를 READ latch로 고정한다. 모든 prev_version-having 레코드에 대해 호출하면 heap 헤더 latch 경합이 새 병목이 될 수 있다.
3. **수정 범위 최소화.** CI를 unblock하기 위한 수정이 우선이고, 엣지 케이스는 후속 이슈에서 다룰 수 있다.

JIRA에 후속 티켓으로 추적할 수 있다.

### Q8. 나중에 이 가드를 되돌려야 하는 조건은?

**A.** 다음 중 하나가 사실로 판명되면:

1. **엣지 케이스 누수가 실제 운영에서 유의미하게 발생** (예: monitoring이 OOS 파일 크기 증가를 감지).
2. **옵션 C의 heap 헤더 latch 비용이 무시할 만한 수준**으로 측정됨.
3. **OOS 파일의 존재 여부를 heap 메타데이터에 캐시**하는 별도 개선이 들어감 — 이 경우 `oos_vfid` 대신 더 확실한 가드를 쓸 수 있다.

### Q9. `VACUUM_RECORD_DELETE_INSID_PREV_VER` 경로(INSID cleanup)는 왜 같은 가드를 예전부터 가지고 있었나?

**A.** INSID cleanup은 P1 버그 **이전부터 존재**했고, 당시 설계자가 이미 "OOS 파일이 없으면 순회 의미 없음"을 인지해 가드를 넣었다. P1 수정 시 REMOVE 경로에도 같은 체인 순회를 추가하면서 **INSID 쪽의 가드 패턴을 그대로 복사해야 했는데** 이를 놓쳤다.

이번 수정은 두 경로의 가드를 일치시켜 대칭성을 회복한다.

### Q10. Git bisect로 이 회귀를 어떻게 찾을 수 있었나?

**A.** 회귀 지점은 명확히 `0748432eb` (P1 수정)이다. 확인 방법:

```bash
# 0748432eb 이전에서는 REMOVE 경로에 chain walk 없음
git checkout 0748432eb^
# partition 테스트 실행 → 정상

# 0748432eb에서 chain walk 추가, 가드 없음
git checkout 0748432eb
# partition 테스트 실행 → 느려짐 (체인 I/O)

# 899d5b633에서 가드 추가
git checkout 899d5b633
# partition 테스트 실행 → 정상 복귀 예상
```

현재 로컬에서 partition 통합 테스트 인프라를 실행할 수 없어 CI 결과로 검증한다 (`/run sql medium` 트리거 완료).

---

## 6. Follow-up Items

| # | 항목 | 우선순위 | 설명 |
|---|------|----------|------|
| 1 | CI에서 수정 확인 | **높음** | `/run sql medium` 결과 확인 후 partition 테스트 정상화 검증 |
| 2 | 엣지 케이스 누수 모니터링 | 중간 | 실제 운영에서 `UPDATE → drop-all-OOS → DELETE` 패턴의 누수 빈도 측정 |
| 3 | 옵션 C 타당성 재평가 | 낮음 | 모니터링 데이터 기반으로 heap-level VFID 체크 도입 여부 결정 |
| 4 | SERVER_MODE 통합 테스트 인프라 | 중간 | PR 리포트에서 지적한 테스트 gap 해소 — 이번 회귀를 미리 잡을 수 있었던 시나리오 |

---

## 7. Commit References

- `0748432eb` — P1 수정 (원인 커밋)
- `899d5b633` — 성능 회귀 수정 (본 수정)

---

> 🤖 Generated by Claude Code (Opus 4.7, 1M context)
