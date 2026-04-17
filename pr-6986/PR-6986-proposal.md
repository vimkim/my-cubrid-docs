# OOS Vacuum L1 누수 — 팀 논의용 제안서

**작성자:** Daehyun Kim (vimkim)
**작성일:** 2026-04-17
**관련 PR:** [CUBRID/cubrid#6986](https://github.com/CUBRID/cubrid/pull/6986) — [CBRD-26668] Wire vacuum to clean up OOS records after DELETE/UPDATE
**관련 JIRA:** CBRD-26668 (본 PR), CBRD-26517 (OOS 메인)
**상태:** 의사결정 필요

---

## 1. Executive Summary

PR #6986의 vacuum 연동으로 OOS 레코드가 대부분 정상 회수되지만, **"UPDATE가 OOS 컬럼을 non-OOS 값으로 교체 → DELETE"** 패턴에서 구버전 OOS 레코드가 영구 누수된다. 이는 일시적으로 가드를 제거했을 때 partition 테스트 성능 회귀를 유발한 것을 되돌리면서 의식적으로 수용한 한계다.

본 문서는 이 한계를 **유지할지**, **이번 M2에서 해결할지**, 또는 **후속 마일스톤으로 연기할지**를 결정하기 위한 네 가지 옵션을 제시한다.

---

## 2. Problem

### 2.1 누수 시나리오

```sql
-- 1. OOS 컬럼에 큰 값 삽입 → OOS_A 생성
INSERT INTO t VALUES (1, REPEAT(X'AA', 4096));

-- 2. OOS 컬럼을 non-OOS 길이로 교체 → 현재 heap 레코드에 OOS 플래그 없어짐
UPDATE t SET oos_col = 'small' WHERE id = 1;

-- 3. 삭제
DELETE FROM t WHERE id = 1;

-- 4. vacuum 실행
--    - 현재 레코드 OOS 플래그 없음 → oos_vfid 미설정
--    - prev_version 체인 순회 가드 (!VFID_ISNULL) short-circuit
--    - undo log에 있는 OOS_A 영구 누수
```

### 2.2 왜 단순히 "현재 레코드 has_oos 확인"만으로는 불가능한가

MVCC UPDATE는 구버전의 OOS OID를 **undo log 레코드 안**에 보존한다. 현재 heap 슬롯의 recdes에는 **최신 버전의 OOS OID만** 존재. 따라서 구버전 OOS를 회수하려면 `prev_version_lsa` 체인을 따라 undo log 페이지를 직접 읽어야 한다 (`logpb_fetch_page` + `log_get_undo_record`).

### 2.3 왜 지금 가드를 그대로 둘 수 없는가 (사용자 관점)

- PR 설명은 "DELETE/UPDATE 시 OOS 레코드를 즉시 삭제하지 않고 Vacuum이 정리"라고 **포괄적으로** 기술. 실제 동작은 일부 경로 누수.
- OOS 주 목적은 **파일이 무한히 커지는 것을 방지**하는 것인데, 엣지 케이스지만 실제로 발생 가능한 누수 경로가 남는 것은 설계 의도와 모순.
- 코드에는 이 한계가 주석으로 "Known limitation"으로만 기술됨. **운영 관점에서 추적/경보 메커니즘 없음**.

### 2.4 왜 가드를 단순히 제거할 수 없는가 (성능 관점)

커밋 `0748432eb`가 가드 없이 chain walk를 추가했다가 **커밋 `899d5b633`로 즉시 롤백**. 이유:
- OOS 파일이 없는 일반 테이블에서도 모든 MVCC UPDATE 레코드에 대해 chain walk 발동.
- 버전당 `logpb_fetch_page` + `LOG_CS_ENTER/EXIT` 비용 발생.
- `sql/_01_object/_09_partition/_001_create/cases/1189.sql` 등 catalog churn 테스트가 CI 타임아웃.

---

## 3. Impact Assessment

### 3.1 누수 발생 빈도 (추정)

| 조건 | 추정 빈도 | 비고 |
|---|---|---|
| OOS 컬럼 있는 테이블 | 중간 | 대용량 VARBIT/VARCHAR 보관 테이블 |
| UPDATE로 해당 컬럼을 **non-OOS 길이로** 교체 | 낮음 | `UPDATE SET big_col = ''` / NULL / 작은 값 |
| 위 UPDATE 직후 DELETE | 낮음 | 연속적인 두 DML 패턴 |
| **세 조건 동시** | **매우 낮음** | 특정 워크로드(로그 수명 관리, 일괄 purge 등)에서 발생 가능 |

### 3.2 누수 크기

- 누수 1건당: **OOS 컬럼 값 크기** (수 KB ~ 수십 KB).
- 회복 불가 조건: **테이블 전체 재생성** 또는 **heap 파일 drop**까지.
- OOS 파일의 unused page는 추후 다른 INSERT에 재사용될 수 있으므로 **즉각적 디스크 증가량은 제한적**. 그러나 **영구적으로 free 상태의 page**가 누적됨.

### 3.3 운영 위험

- 현재 **모니터링/탐지 수단 없음**: OOS 파일 크기와 heap 파일 live row 수의 불일치를 자동으로 감지하지 않음.
- 대용량 테이블에서 오랜 기간 누적되면 **OOS 파일이 heap보다 현저히 커지는** 현상 가능.

---

## 4. Options

### Option A — Status Quo (현재 가드 유지)

**내용:** 현재 코드 그대로 머지. PR 설명과 주석에 한계 명시. JIRA 후속 티켓 생성.

**장점:**
- 추가 개발 비용 0.
- 성능 회귀 없음.
- M2 일정 영향 없음.

**단점:**
- 누수 엣지 케이스 영구 잔존 (heap 재생성까지).
- 운영 모니터링 부재.
- PR 설명과 실 동작 괴리.

**공수:** 문서 수정만 (1인일).

**M2 포함 가능:** ✅

---

### Option B — Page 단위 `has_oos_file` 캐싱 (경량 수정)

**내용:** `VACUUM_HEAP_HELPER`에 tri-state 캐시 추가. `vacuum_heap_page` 처리 시작 시 heap 헤더에서 OOS 파일 존재 여부를 **한 번만** 조회 후 page의 모든 레코드에서 재사용. 가드를 `!VFID_ISNULL(oos_vfid)` → `has_oos_file == PRESENT` 로 교체.

```c
enum { OOS_FILE_UNKNOWN, OOS_FILE_NONE, OOS_FILE_PRESENT } oos_file_state;
```

**장점:**
- 누수 해결 (엣지 케이스 포함 모든 MVCC 경로 커버).
- **성능 회귀 없음**: catalog 테이블은 page당 1회 heap 헤더 READ latch만 추가 발생 (거의 항상 buffer hit).
- 코드 변경 범위 작음 (vacuum.c 한정).
- 기존 포맷 변경 없음 → recovery/replication 호환.

**단점:**
- page당 1회 heap 헤더 latch는 이론적으로 0은 아님 — 극한 micro-benchmark에서 측정 필요.
- 구조체 필드 추가로 vacuum 관련 코드 리뷰 재진행.

**공수:** 2-3인일 (구현 + 단위 테스트 + CI 회귀 검증).

**M2 포함 가능:** ✅ (**권장**)

**M2 일정 영향:** 마일스톤 마감 4/17 기준 여유 있음.

---

### Option C — MVCC 헤더에 `HAS_PREV_OOS` 플래그 추가

**내용:** MVCC 헤더 flag 비트에 `HAS_PREV_OOS`를 추가 (현재 reserved bit 4 사용). UPDATE 시 **구 레코드가 `HAS_OOS` 또는 `HAS_PREV_OOS` 중 하나라도 가지면** 새 레코드에 `HAS_PREV_OOS` 설정. vacuum은 이 플래그를 보고 chain walk 여부 결정.

```
v1: HAS_OOS=1, HAS_PREV_OOS=0  (최초 INSERT)
v2: HAS_OOS=0, HAS_PREV_OOS=1  ← UPDATE 시 v1 플래그들 OR해서 설정
v3: HAS_OOS=0, HAS_PREV_OOS=1  ← 계속 전파
DELETE v3: vacuum이 HAS_PREV_OOS 감지 → chain walk → v1의 OOS_A 회수
```

**장점:**
- 누수 근본 해결.
- 성능 회귀 없음 (heap 헤더 조회조차 불필요 — 현재 레코드 헤더만 확인).
- 런타임 비용 최소 (flag bit 체크 1회).

**단점:**
- MVCC 헤더 포맷 변경 → **기존 DB 호환성 이슈 가능**.
- `heap_update_adjust_recdes_header`, `or_mvcc_get_header` 등 flag 전파 로직 여러 지점 수정.
- `OR_GET_MVCC_FLAG` 관련 마스크 점검 필요.
- replication log, CDC, flashback에서 플래그 처리 추가 필요.
- 테스트 범위 확대: MVCC 헤더 관련 기존 테스트 모두 점검.

**공수:** 5-8인일 (구현 + 포맷 호환성 검토 + 테스트 확장 + replication 확인).

**M2 포함 가능:** ⚠️ 빠듯함. M2 일정 연장 또는 M3로 연기 검토.

---

### Option D — 구버전 OOS OID를 새 current record에 직접 embed

**내용:** UPDATE 시 교체되는 구버전 OOS OID들을 새 heap 레코드의 **"pending-delete" 영역**에 그대로 보존. vacuum은 **현재 레코드만 읽고** pending-delete 목록까지 회수. chain walk 완전 제거.

```
v2 = [ MVCC_header | VOT | fixed | var(새 OOS_B) | pending_delete: [OOS_A] ]
```

**장점:**
- chain walk 완전 제거 → 성능 및 정확성 양쪽 최적.
- `prev_version_lsa` 체인 순회 복잡도 제거.
- undo log I/O 불필요.

**단점:**
- **heap 레코드 포맷 대규모 변경**: 새 섹션 추가, VOT 확장, recovery/replication/serialization 전면 수정.
- 재귀적 UPDATE 체인에서 pending-delete 목록이 쌓이면 레코드 크기 증가 (N번 UPDATE = N*16B).
- 기존 DB와 호환성 migration 필요.
- 구현 범위가 "PR 단위"가 아닌 "마일스톤 단위" 작업.

**공수:** 15-25인일 (설계 + 구현 + migration + 광범위 테스트).

**M2 포함 가능:** ❌ (**M3 또는 M4 후보**)

---

## 5. Comparison Matrix

| 기준 | A. Status Quo | B. Page 캐싱 | C. HAS_PREV_OOS 비트 | D. Embed |
|---|---|---|---|---|
| 누수 해결 | ❌ | ✅ | ✅ | ✅ |
| 성능 회귀 없음 | ✅ | ✅ | ✅ | ✅ |
| 포맷 변경 없음 | ✅ | ✅ | ❌ (헤더) | ❌ (레코드) |
| 구현 공수 | 1인일 | 2-3인일 | 5-8인일 | 15-25인일 |
| M2 포함 가능 | ✅ | ✅ | ⚠️ | ❌ |
| Replication 영향 | 없음 | 없음 | 있음 | 크게 있음 |
| 운영 추적성 | 없음 | 없음 | 플래그로 추적 가능 | 메타데이터 명시적 |
| 향후 확장성 | — | 제한적 | 중간 | 높음 |

---

## 6. Recommendation

### 6.1 단기 (M2 내)

**Option B (Page 단위 `has_oos_file` 캐싱)** 채택 권장.

근거:
1. **누수를 실제로 해결**하면서 **성능 회귀 위험 최소**.
2. 공수 2-3인일로 M2 마감 내 수용 가능.
3. 포맷 변경 없어 recovery/replication 추가 검토 불필요.
4. 이후 Option C/D로의 진화 경로를 닫지 않음 (가드 로직 단일 지점이라 교체 용이).

### 6.2 중장기 (M3+)

**Option C 또는 D 재평가.** 운영 투입 후 실제 OOS 워크로드 특성에 따라 결정:
- catalog-heavy 워크로드만 문제 → B로 충분.
- OOS UPDATE 체인이 매우 긴 실사용 케이스 발견 → D 검토.
- MVCC 헤더 비트 여유 있고 플래그 전파 인프라 성숙 → C 채택.

### 6.3 공통 권장 (어느 옵션이든)

- **OOS 파일 크기 모니터링 지표 추가**: `heap_live_rows` vs `oos_file_pages` 비율 노출. pstat 또는 admin view로 확인 가능하게.
- **PR 설명/JIRA 업데이트**: 현재 "모든 OOS 정리" 표현을 실제 동작에 맞게 수정.

---

## 7. Discussion Points for 팀장님

다음 항목에 대한 의견 요청:

1. **M2 일정 vs. 엣지 케이스 누수**
   - Option B는 M2 내 해결 가능하나 2-3일 추가 작업 + 재리뷰 필요. M2 마감 유지와 trade-off 판단 필요.
   - 또는 A로 머지하고 Option B를 M2.1 핫픽스로 즉시 후속 투입?

2. **운영 위험 수준 평가**
   - 이 엣지 케이스가 실제 CUBRID 주요 고객 워크로드에서 발생할 빈도/크기에 대한 **도메인 전문가 판단** 필요.
   - 특히 log 관리, audit table, session table 등 "write-heavy + OOS column + 짧은 수명" 테이블이 있는지.

3. **포맷 변경 수용 여부**
   - MVCC 헤더 비트 추가(Option C)는 CUBRID 전반에 파급. 언젠가 도입하려면 M2와 M3 중 어느 시점이 적절한가?
   - 장기 로드맵에서 OOS 관련 다른 포맷 변경 예정 사항(CDC, CHAR OOS 등)과 묶어서 진행할 기회가 있는가?

4. **모니터링 지표 우선순위**
   - Option 선택과 별개로 OOS 파일 크기 monitoring은 투입하는 것이 좋다고 판단. 별도 티켓으로 분리할지, 이번 PR/M2 내 포함할지?

5. **CBRD-26668 PR 설명 수정**
   - "모든 unreachable OOS 정리"에서 실제 범위를 명시하는 표현으로 업데이트. 팀 관례상 PR 재등록이 필요한가, 설명 보강만으로 충분한가?

---

## 8. 결정 요청

본 제안서의 **Option 선택** 및 **M2/M3 일정 배치**에 대한 의사결정을 요청합니다. 논의 후 채택된 옵션에 따라 PR #6986 재작업 또는 후속 티켓 생성을 진행하겠습니다.

---

## Appendix: Related Commits and Documents

- **원인 커밋**: `0748432eb` — P1 수정에서 가드 누락
- **회귀 수정 커밋**: `899d5b633` — 현재 가드 추가
- **분석 문서**:
  - `PR-6986-report.md` — 코드 리뷰 보고서 (L1-L4 누수 경로 분석)
  - `PR-6986-perf-regression-report.md` — 성능 회귀 원인 분석
- **관련 JIRA**: CBRD-26668 (M2 vacuum 연동), CBRD-26517 (OOS 메인)

---

**검토 요청 대상:** 팀장
**검토 요청 기한:** PR #6986 머지 전
