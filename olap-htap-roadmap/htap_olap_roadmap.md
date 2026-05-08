# CUBRID OLAP/HTAP 확장 로드맵 제안

> **대상**: 팀장 / 의사결정권자
> **작성일**: 2026-05-08
> **작성자**: 김대현
> **사전 리뷰**: _미지정 — 본 v1 발행 후 동료 1~2명 사전 리뷰 예정. 합의/이견 사항은 부록 C에 기록 예정._
> **상태**: 초안, 결정 요청

---

## TL;DR

- CUBRID는 OLTP에 강하지만 OLAP 워크로드(대용량 집계·컬럼 분석)에는 약합니다.
- 자체 컬럼너 엔진을 처음부터 만드는 길(옵션 E, 18~30개월 + MVCC와의 충돌 리스크)을 회피하고, **외부에서 시작해 안쪽으로 들어오는 4단계 로드맵**(Phase 1 REST API → Phase 2 in-memory 테이블 → Phase 3 테이블스페이스 → Phase 4 DuckDB 임베드)을 제안합니다.
- 자체 컬럼너 엔진 대신 검증된 DuckDB(MIT 라이선스)를 임베드하는 이유는 정량 비교가 아니라 ROI 정성 판단입니다. *DuckDB는 외부 벤치마크(예: H2O.ai db-benchmark, ClickBench)에서 검증된 OLAP 성능을 제공하며, 자체 컬럼너 엔진을 다년에 걸쳐 신규 개발하는 것보다 도입 ROI가 높다고 판단합니다.*
- 시니어 1명 기준 누적 13개월 + Phase 사이 검증 버퍼 2주 × 3 = 1.5개월. **누적 14.5~26.5개월**(하한 시나리오 14.5개월, 상한 시나리오 26.5개월). 각 Phase는 단독 출시 가능하므로 어느 시점에서 멈춰도 부분 가치가 남습니다.
- 팀장 결정이 필요한 항목: (1) 로드맵 승인, (2) Phase 2 메모리 테이블 6가지 스펙, (3) 인력 배정, (4) AI-assisted 개발 사용 전제 동의, (5) Phase 4 진입 게이트(DuckDB 라이선스/보안 재검토 시점) 동의.

---

## Executive Summary

CUBRID에 OLAP 가속과 운영 유연성을 위한 4개 확장 기능을 단계적으로 도입할 것을 제안합니다.

| Phase | 기능 | MVP 기간 | 검증 버퍼 | 누적 |
|---|---|---:|---:|---:|
| 1 | REST API 서버 | 1~2개월 | +2주 | 1.5~2.5개월 |
| 2 | In-memory 테이블 (recovery 없음) | 3~5개월 | +2주 | 5~8개월 |
| 3 | 테이블스페이스 | 6~12개월 | +2주 | 11.5~20.5개월 |
| 4 | DuckDB 임베드 (FOREIGN/EXTERNAL TABLE) | 3~6개월 | — | 14.5~26.5개월 |

> *누계 산식 주석*: "누적" 컬럼은 (각 Phase MVP 기간) + (Phase 1·2·3 종료 후 각 +2주 검증 버퍼) 합산이며, Phase 4 종료 후에는 검증 버퍼가 없다. 즉 14.5개월 = 1.5(P1+버퍼) + 3.5(P2+버퍼) + 6.5(P3+버퍼) + 3(P4), 26.5개월 = 2.5 + 5.5 + 12.5 + 6 (각 하한/상한 합).

**의도적으로 제외한 항목**:
- 네이티브 컬럼너 저장구조 (단독 18~30개월, 리스크 매우 높음)
- MySQL식 pluggable storage engine (24개월+, 그 자체로 사용자 가치 0)

**총 공수**: 시니어 1명 풀타임, AI-assisted 개발 전제 기준 누적 14.5~26.5개월 (Phase 사이 검증 버퍼 1.5개월 포함). AI-assisted 미사용 시 약 17.4~37.1개월(+20~40% 가산)로 변동 — §4.2 핵심 가정 및 §5.3 결정 항목 참조.

> **인건비/토큰 비용 등 TCO 항목은 부록 D**로 분리. 본 문서의 표면 결정 변수는 일정과 인력이며, TCO는 결정 변수에 포함되지만 인건비 단가가 사내 기밀이므로 본 문서에 수치를 적시하지 않고 별도 회의에서 검토함.

**팀장 결정 요청**:
1. 본 로드맵 승인 또는 수정
2. Phase 2 in-memory 테이블의 핵심 스펙 6건 (본문 §5.2)
3. 인력 배정: 1명 전담 vs. 다른 작업과 병행
4. AI-assisted 개발(Claude Opus 등) 사용 전제 동의 (§5.3)
5. Phase 4 외부 의존성 게이트 동의 (Phase 3 종료 시점에 DuckDB 라이선스/보안 재검토 후 진입 결정, 기각 시 옵션 G/H로 fallback — §5.4)

---

## 1. 배경

### 1.1 현재 CUBRID의 위치
- Row-oriented OLTP 엔진. MVCC + WAL + B-tree 기반의 견고한 트랜잭션 처리.
- OLAP 워크로드(대용량 집계, 컬럼 기반 분석) 처리 시 page buffer 미스, full heap scan 비용이 큼.
- 최근 PR들 (#7040 parallel heap scan, #7050 join selectivity, #7074 SQL_TRACE_EXECUTION_PLAN)은 OLTP 엔진 안에서의 OLAP 개선 노력.

### 1.2 시장/사용자 요구
- HTAP(Hybrid Transactional/Analytical Processing) 수요 증가
- ETL staging, 캐싱 lookup, 분석용 임시 데이터셋 활용 케이스 증가
- 기업 환경에서 운영 분리(테이블스페이스), 외부 통합(REST API) 요구

### 1.3 본 제안의 원칙
- **단계적 가치 입증**: 각 Phase가 독립적으로 사용자 가치 제공
- **수단이 목적이 되는 작업 회피**: pluggable storage engine처럼 인프라 자체가 목적이 되는 작업은 배제
- **외부 검증 활용**: 자체 컬럼너 엔진 대신 외부 벤치마크에서 검증된 DuckDB 활용
- **가역성 확보 전략**: Phase 1~2는 기존 코드 영향이 작은 *추가* 기능으로 설계하여 롤백 비용을 낮추고, Phase 3~4는 외부/추상 경계(테이블스페이스 메타, EXTERNAL TABLE)를 활용해 추후 제거·교체 가능하도록 함.

---

## 2. 옵션 비교

### 2.1 검토한 N개 옵션 중 최종 4개 채택

| # | 기능 | MVP | 프로덕션 | 리스크 | 채택 여부 |
|---|---|---:|---:|---|:---:|
| A | REST API 서버 | 1~2mo | 2~4mo | 낮음 | ✅ Phase 1 |
| B | In-memory 테이블 | 3~5mo | 4~8mo | 낮음 | ✅ Phase 2 |
| C | 테이블스페이스 | 6~12mo | 12~18mo | 중간 | ✅ Phase 3 |
| D | DuckDB 임베드 | 3~6mo | 6~12mo | 중간 | ✅ Phase 4 |
| E | 네이티브 컬럼너 | 18~30mo | 36mo+ | 매우 높음 | ❌ §2.3 |
| F | Pluggable storage | 24mo+ | 48mo+ | 매우 높음 | ❌ §2.4 |
| G | Materialized view 강화 | 2~4mo | 4~6mo | 낮음 | ⏸ 보류 — Phase 2와 일부 중복 효용. Phase 2 출시 후 사용 패턴 보고 재평가. **Phase 4 게이트 기각 시 fallback 후보 1**(§5.4). |
| H | Apache Arrow/Parquet 외부 테이블 | 4~8mo | 8~12mo | 중간 | ⏸ 보류 — Phase 4 DuckDB가 Parquet 읽기를 내장하므로 우선순위 하향. **Phase 4 게이트 기각 시 fallback 후보 2**(§5.4). |
| I | 파티셔닝 개선 | 3~6mo | 6~9mo | 중간 | ⏸ 보류 — OLTP 트랙(별도 PR)에서 진행 중인 영역과 겹침. 본 OLAP 로드맵 범위 외. |
| J | ClickHouse 연동 | 3~6mo | 6~12mo | 중간 | ❌ 기각 — Apache 2.0 라이선스는 호환되나 ClickHouse는 별도 *서버* 프로세스 모델로 임베드가 어렵고, 운영 노드가 늘어남. DuckDB(임베디드)와 비교 시 통합 비용 큼. |

> "검토한 N개 옵션" 중 본 로드맵에 채택한 것은 A/B/C/D 4건. E/F/J는 기각, G/H/I는 보류로 표기.

### 2.2 일정·산정 가정 (단일 산식)

본 로드맵 전체에서 일정 추정은 **시니어 1명, 주 40시간 풀타임, AI-assisted 개발(Claude Opus 등) 사용 가정**을 기준으로 합니다.

- 모듈별 LOC 추정 → 유사 모듈 또는 과거 PR LOC 앵커와 비교 → 1주당 평균 200~300 LOC를 가정해 환산.
- ±50% 오차를 전 항목에 일관 적용 (그래서 표의 모든 셀이 범위 형태).
- **LOC 환산과 일정 사이의 보정 항**: Phase 2의 코어 LOC 2,500~4,600을 200~300 LOC/주로 환산하면 8~23주이지만, 공식 일정은 12~20주. 차액은 통합 비용(타 모듈과의 인터페이스 디버깅), 코드 리뷰 라운드, 회귀 테스트, 보안/감사 점검의 보정치를 포함한 결과임. **Phase별 보정치는 통합 침습도에 따라 차등 적용**: Phase 1=2~3주(외부 모듈, 코어 변경 0줄), Phase 2=4~6주(코어 침습 — schema/scan/locator), Phase 3=6~10주(storage 침습 — file/disk/backup), Phase 4=4~6주(외부 라이브러리 통합).
- 첫 Phase(REST API) 종료 후 실측을 반영해 후속 Phase 추정을 재산정.
- AI-assisted 미사용 시 본 일정에 약 +20~40%(범위는 모듈 복잡도 의존)를 가산해야 한다고 가정. 이 가산을 적용하면 누적 14.5~26.5개월이 약 17.4~37.1개월로 늘어남(하한은 14.5×1.20, 상한은 26.5×1.40). 본 가산은 *공식 일정*에는 포함하지 않고 §4.2 핵심 가정과 §5.3 결정 매트릭스에 별도 항목으로 분리.

### 2.3 제외 사유: 네이티브 컬럼너 (옵션 E)

**기각 사유**:
- 손대야 하는 모듈: `storage/` 전반, `query/`, `transaction/mvcc.c`, `log_*.c`, optimizer cost model — 사실상 엔진 재설계.
- MVCC와 컬럼너는 본질적으로 충돌 (delta store + base store 패턴이 사실상 필수).
- 산업 선례: MariaDB ColumnStore, Citus columnar, Postgres ZedStore 모두 다년 프로젝트.
- **DuckDB 임베드(옵션 D)가 외부 벤치마크에서 검증된 OLAP 성능을 신규 개발 없이 제공하므로 ROI가 높음.** 자체 컬럼너 엔진을 다년에 걸쳐 신규 개발하기보다 DuckDB 도입 후 사용 사례를 측정해 진짜 필요한지 재평가하는 편이 합리적.

### 2.4 제외 사유: Pluggable Storage Engine (옵션 F)

**기각 사유**:
- 그 자체로는 사용자 기능이 아님 — 인프라 작업.
- CUBRID storage 계층은 heap/btree/page_buffer/MVCC/WAL과 깊게 결합. 핸들러 API 추출은 *수십 개월 단위*로 추정되며 정확한 산정 자체가 별도 과제. (참고: MariaDB의 pluggable storage engine 도입은 5.1 → 5.5에 걸쳐 다년 프로젝트로 진행되었음.)
- "Phase 2 메모리 테이블 + Phase 4 DuckDB"는 케이스별 통합으로 충분 — 일반화 불필요.

---

## 3. Phase별 계획

### Phase 1: REST API 서버 (1~2개월)

**목표**: HTTP 기반 SQL 실행 인터페이스 제공.

**구현 방식**:
- CUBRID 코어 *외부*에 별도 프로세스로 구현 (Go 또는 Node.js)
- 기존 broker 위에 CCI 클라이언트로 접속, JSON 직렬화
- 코어 코드 0줄 변경

**주요 기능**:
- `POST /sql` — SQL 실행, JSON 결과
- `POST /prepared/{name}` — prepared statement 캐시
- 기본 인증 (basic auth, JWT)
- connection pool

**산출물**: 별도 Git repo, Docker 이미지, 간단 운영 매뉴얼.

**리스크**: 매우 낮음. CCI 안정성에 의존.

**보안/감사**:
- 인증: basic auth + JWT, TLS 종단(리버스 프록시 또는 자체 TLS) 필수.
- 감사: 모든 `POST /sql` 요청을 access log에 SQL 해시 + 사용자 + 타임스탬프로 기록.
- 규정: 본 컴포넌트는 *broker 앞단*이므로 broker 레벨 권한/감사 정책을 우회하지 않도록 권한 체크 위임 모델로 설계.

**성공 기준**:
- 단일 노드에서 1,000 req/s 처리 시 p95 latency 100ms 이하 (단순 `SELECT 1` 기준 측정). 본 수준은 broker 단독 부하의 약 80% 수준을 목표로 한 것이며, **broker 단독 한계가 1,250 req/s 미만(즉 보정 후 1,000 req/s 도달 불가)일 때만** "broker 단독 측정치 × 0.8"로 자동 보정 적용. broker 단독이 1,250 req/s 이상이면 1,000 req/s 절대치를 그대로 적용한다(자기충족적 성공 기준 방지).
- 10만 req 부하 테스트 통과 (memory leak 없음, 24시간 soak).
- 보안 점검: 외부 모의해킹 1회 통과 또는 OWASP top 10 self-checklist 통과.

---

### Phase 2: In-memory 테이블 (3~5개월) — *본 로드맵의 단일 최대 작업이자 단일 최대 위험 지점*

**목표**: WAL/recovery 없이 메모리에만 존재하는 빠른 조회용 테이블.

**용도 (PK 기반 사용에 한정)**:
- PK 기반 캐싱 lookup table (애플리케이션 레벨 hot key 캐시)
- single-key dimension 테이블 (작은 코드 테이블, 룩업용 사전)
- (참고) ETL staging, OLAP 중간 결과, 분석 임시 데이터셋 등 *secondary index 또는 풀스캔이 필요한* 사용처는 본 Phase 2 범위 외 — secondary index를 §5.2 결정 항목으로 올려 팀장이 "+4~8주 감수" 명시 동의 시 별도 확장 트랙으로 처리.

**스펙 (확정 사항)**:

| 항목 | 결정 |
|---|---|
| 가시성 | Global (모든 세션 공유) |
| 영속성 | 카탈로그는 영속, 데이터는 서버 재시작 시 wipe |
| DML | INSERT/UPDATE/DELETE 전체, *autocommit-per-statement* (트랜잭션 ROLLBACK 영향 밖) |
| 인덱스 | PRIMARY KEY hash only |
| OOM 정책 | `ER_MEMORY_TABLE_FULL` 에러 |
| 동시성 | RW lock per table (`std::shared_mutex`) |
| MVCC | 없음 (dirty read 허용) — *상세 가이드 아래* |
| HA/Backup | skip — *운영 제약 박스 아래* |
| DDL | `CREATE MEMORY TABLE foo (...);` |

**Phase 2 제약 사항 (운영자/사용자 가시)**:
1. **재시작 후 데이터 부재**: 서버 재시작/장애 후 메모리 테이블 데이터는 사라지며 카탈로그(스키마)만 남음. 애플리케이션은 재기동 시 재적재 책임을 갖는다.
2. **HA 미통합**: 메모리 테이블은 노드 간 복제되지 않음. 다중 노드 구성에서는 노드별 데이터가 다를 수 있음 (read-only/캐시 용도 권장).
3. **DML 시 손실 가능성 사용자 책임**: 진행 중 DML 도중 서버 장애 발생 시 부분 결과가 유실될 수 있음. WAL이 없으므로 partial write에 대한 보호 장치도 없음.
4. **Failover 시 동작**: HA 페일오버 시 새 master 노드의 메모리 테이블은 빈 상태에서 시작. 애플리케이션이 이를 인지해야 함 (Phase 2 출시 가이드 문서에 절차 포함).
5. **트랜잭션 의미론**: 메모리 테이블에 대한 INSERT/UPDATE/DELETE는 *autocommit-per-statement*로 동작. 즉 각 DML 문이 즉시 메모리에 반영되며, 둘러싼 트랜잭션의 ROLLBACK으로 되돌릴 수 없음. 디스크 테이블과 메모리 테이블을 같은 트랜잭션에서 변경한 뒤 ROLLBACK 시 디스크 테이블만 되돌려지고 메모리 테이블 변경은 그대로 남음. 이는 §5.2 결정안에 포함.

**dirty read 허용의 가시 범위와 가이드**:
- JOIN/서브쿼리에서 메모리 테이블이 포함될 경우 결과가 비결정적일 수 있음. 동일 SQL을 두 번 실행했을 때 결과 행 수가 달라질 수 있음(다른 세션의 진행 중 INSERT/UPDATE 가시).
- 권장 사용 패턴: (a) bulk load 후 read-only 조회, (b) 단일 writer + 다중 reader, (c) eventual consistency 허용 캐시 lookup.
- 권장 회피 패턴: 다중 writer 동시 INSERT/UPDATE 후 정합성 가정 쿼리.
- 본 제약은 §4.1 리스크 표(R-D)에 등재.

**기존 인프라 재사용 포인트** (사전 조사 결과):
- `csql_grammar.y:1403`의 미사용 `TEMPORARY` 토큰은 본 작업 반대 방향(세션 로컬). `MEMORY` 신규 토큰을 도입하고 `CREATE TABLE` 룰(`csql_grammar.y:2541-2600`) 옆에 별도 룰 추가가 깔끔.
- `SM_CLASS_TYPE` (`class_object.h:294-300`, 3종)에 4번째 타입을 추가하기보다 `SM_CLASS_FLAG`(`class_object.h:304-312`) 비트로 표시하는 편이 영향 범위 작음.
- **`SM_CLASS_FLAG` 비트 고갈 사전 점검**: 현재 `SM_CLASS_FLAG`는 5비트가 사용 중(`SM_CLASSFLAG_SYSTEM`/`_WITHCHECKOPTION`/`_LOCALCHECKOPTION`/`_REUSE_OID`/`_AUDIT` 등). 다음 가용 비트에 `SM_CLASSFLAG_MEMORY_TABLE = 32`를 배치 가능. 단 카탈로그 직렬화(`disk_class` 디스크 표현, `or_*` 직렬화 함수)에서 플래그 필드 폭이 32비트 이상인지 사전 점검 필수 — Phase 2 Week 1 catalog 작업 첫 항목으로 명시.
- `SCAN_TYPE` (`scan_manager.h:75-94`, 16종 switch dispatch)에 `S_MEMORY_TABLE_SCAN` 한 항목만 추가하고 `scan_next_*` 분기에 핸들러 추가.
- `list_file`(qfile_* API)의 `TEMP_FILE_MEMBUF_NORMAL` spill 정책은 재사용하지 않음 — 메모리 테이블은 본질적으로 spill 금지.
- Session 인프라(`session.{h,c}`)의 prepared statement 등록/해제 패턴을 메모리 테이블 카탈로그 hot reload에 차용.

**아키텍처** (요약):

```
SQL → Parser → Schema Manager (catalog 플래그)
              ↓
     ┌──────────────────────────────────────┐
     │ Memory Store (신규 모듈)              │
     │  - chunk-based 행 저장 (64KB chunk)   │
     │  - global hash registry               │
     │  - PK hash index                      │
     │  - RW lock                            │
     │  - scan source 추상화 인터페이스      │
     │    (Phase 4 DuckDB 재사용 대비)        │
     └──────────────────────────────────────┘
              ↓
     Scan Manager (S_MEMORY_TABLE_SCAN 추가)
```

**작업 분해** (총 약 2,500~4,600 LOC, 신뢰구간 — 표 합계의 라운딩 마진 약 +400 LOC 포함 가능):

| 모듈 | 라인 추정 | 비교 앵커 | 주요 파일 |
|---|---:|---|---|
| Parser (`MEMORY` 키워드, 룰) | 60~120 | 최근 DDL 토큰 1건 PR 기준 | `csql_grammar.y`, `parse_tree.h` |
| Catalog (`SM_CLASSFLAG_MEMORY_TABLE`) | 100~200 | `SM_CLASS_FLAG` 비트 추가 패턴 | `class_object.h`, `schema_manager.c` |
| Memory store 신규 모듈 | 900~1,500 | MySQL HEAP engine 코어 규모 참고 | `src/storage/memory_table.{hpp,cpp}` |
| Scan source 추상화 레이어 | 100~200 | (신규, Phase 4 시너지 위함) | `src/storage/scan_source.hpp` |
| INSERT/UPDATE/DELETE 분기 | 300~500 | `locator_attribute_info_force()` 진입 직전 카탈로그 플래그 체크로 일괄 분기 | `qexec_*`, `locator_*.c` |
| Scan 통합 | 250~450 | 기존 `S_HEAP_SCAN`/`S_INDX_SCAN` 디스패치 규모 | `scan_manager.{h,c}` |
| Optimizer 비용 모델 | 30~80 | 단순 const cost 진입 | `query_planner.c` |
| Lifecycle (startup/DROP/tx) | 150~300 | `boot_sr.c` 후크 추가 패턴 | `boot_sr.c`, `session.c` |
| Error 코드 (6곳) | 25~40 | 최근 신규 에러 코드 PR 평균 | `error_code.h`, `dbi_compat.h`, `cubrid.msg` ×2, CCI |
| INFORMATION_SCHEMA | 60~120 | system catalog view 1건 추가 규모 | `schema_system_catalog_*.cpp` |
| 시스템 파라미터 | 30~60 | 신규 sysparam 1건 추가 규모 | `system_parameter.{h,c}` |
| 테스트 | 500~1,000 | 신규 모듈 SQL/유닛/소크 테스트 | `unit_tests/`, `tests/` |

> 모든 LOC는 ±50% 오차 가정. 표 합산 상한은 4,570 LOC이며 라운딩 마진 약 +400 LOC를 포함해 보수적으로 **2,500~4,600 LOC 신뢰구간**으로 표기.
> LOC → 일정 환산 시 200~300 LOC/주 산식만 적용하면 8~23주가 나오고, 공식 일정 12~20주는 통합·리뷰·회귀 보정 4~6주를 더한 결과(§2.2 보정 항).

**일정 — 하한 시나리오 (3개월, 12주)**:
- Week 1: Catalog 플래그 + Grammar (catalog 작업 첫 항목으로 `SM_CLASS_FLAG` 비트 폭/직렬화 점검)
- Week 2-3: 메모리 스토어 코어 + INSERT
- Week 4: PK hash index
- Week 5: UPDATE/DELETE
- Week 6-7: Scan 통합 (scan source 추상화 포함)
- Week 8: Lifecycle (DROP, 트랜잭션 통합)
- Week 9: HA/backup skip 검증, 카탈로그 노출, sysparam
- Week 10-11: 성능 측정, regression
- Week 12: 리뷰 대응 버퍼

**일정 — 상한 시나리오 (5개월, 20주)**:
- Week 1-2: Catalog 플래그 + Grammar (catalog 작업 첫 항목으로 `SM_CLASS_FLAG` 비트 폭/직렬화 점검)
- Week 3-6: 메모리 스토어 코어 + INSERT
- Week 7-8: PK hash index
- Week 9-10: UPDATE/DELETE
- Week 11-13: Scan 통합 + scan source 추상화
- Week 14: Lifecycle
- Week 15-16: HA/backup skip 검증, 카탈로그 노출, sysparam
- Week 17-18: 성능 측정, regression
- Week 19-20: 리뷰 대응 + 보안/감사 점검 버퍼

**DML 분기 위치 (한 문장 결정)**:
- DML 분기는 `locator_attribute_info_force()` 진입 *전* 단계에서 카탈로그 플래그(`SM_CLASSFLAG_MEMORY_TABLE`)를 체크해 일괄 분기한다. 이는 page buffer/heap 경로를 진입하기 *전* 단일 지점에서 우회를 보장한다.

**설계 결정안 (사용자 가시 항목)**:

1. **트랜잭션 atomicity (CREATE 후 ROLLBACK)** — *결정안*: CREATE는 *비트랜잭션* DDL로 분류. CREATE 실행 즉시 카탈로그 등록 + 메모리 레지스트리 등록. ROLLBACK 시 카탈로그는 자동 되돌리되 메모리 레지스트리는 commit 콜백으로 함께 정리. *대안*: 모든 DDL을 트랜잭션 내로 — 채택 안 함(기존 CUBRID DDL 모델과 충돌).
2. **DROP 중 동시 SCAN** — *결정안*: per-table `std::shared_mutex` + reference count, deferred free. 동시 SCAN이 끝날 때까지 메모리 회수 지연. *대안*: epoch-based reclamation — 채택 안 함(현 단계 단순성 우선).
3. **PK 키 정규화** — 구현 단계 결정. 기본은 `btree_compare_key` 재사용으로 두고 Phase 4 호환성 확인 시점에 재검토.
4. **카탈로그 영속/데이터 휘발 모델의 사용자 혼란** — *결정안*: (a) `INFORMATION_SCHEMA.MEMORY_TABLES` 뷰 노출, (b) `CREATE MEMORY TABLE` DDL 실행 시 클라이언트로 휘발성 경고 메시지 1회 송출, (c) 운영 가이드 문서에 "재기동 후 재적재 책임" 명시. *대안*: 데이터 영속 모드 추가 — 채택 안 함(Phase 2 범위 외).
5. **SERVER_MODE 한정 vs SA_MODE 지원** — 구현 단계 결정. 1차 SERVER_MODE 전용으로 진행하고 SA_MODE 지원은 Phase 2 종료 후 별도 평가.
6. **DML 트랜잭션 의미론(autocommit-per-statement)** — *결정안*: 메모리 테이블의 INSERT/UPDATE/DELETE는 각 문 단위로 즉시 확정되며 둘러싼 트랜잭션의 ROLLBACK 영향 밖. 따라서 디스크 테이블과 메모리 테이블을 같은 트랜잭션에서 변경한 뒤 ROLLBACK하면 디스크 테이블만 되돌려진다. *근거*: WAL/undo 없이 트랜잭션 atomicity를 보장하려면 별도 in-memory undo 로그가 필요한데, 본 Phase 2 범위(저비용/단순) 밖. *대안*: in-memory undo로 ROLLBACK 지원 — 채택 안 함, +6~10주 비용. *사용자 가시화*: `CREATE MEMORY TABLE` DDL 시 1회 경고 + 운영 가이드 명시.

**리스크**:
- **중**: 첫 buffer-pool-우회 코드 경로 → 이후 다른 기능이 비슷한 패턴을 따라할 때 표준이 됨. 신중히 설계.
- **저**: 기존 트랜잭션 처리 영향 없음 (메모리 테이블은 트랜잭션 외부).

**보안/감사**:
- 권한: 일반 테이블과 동일한 GRANT/REVOKE 모델 적용.
- 감사: `CREATE MEMORY TABLE`/`DROP` DDL은 기존 DDL audit 트랙에 포함.
- 데이터 보호: 메모리 테이블은 디스크에 기록되지 않으므로 디스크 암호화 정책 영향 밖. 단, 코어 덤프 생성 시 메모리 내용이 노출될 수 있어 운영 가이드에 명시.

**성공 기준**:
- 측정 조건 가정: 단일 노드, 64GB 메모리, **행 크기 약 50바이트**(단순 `(id BIGINT PK, value VARCHAR(32))` 스키마), **1천만 행** 적재 (총 데이터 약 500MB + hash index 약 200MB로 64GB 메모리 내 충분 수용).
- *Read-side*: 1천만 행 적재 후 PK 단일 조회 p95 latency 1ms 이하.
- *Write-side (단일 writer)*: INSERT throughput **≥ 50,000 rows/s** (단일 writer 세션, 사전 적재된 빈 테이블 → PK 충돌 없음 가정).
- *Write-side (혼합 부하)*: 동시 writer 4명 + reader 16명 부하 시 **PK 단일 조회 p99 latency ≤ 5ms**, INSERT p99 latency ≤ 5ms (RW lock contention 검증 — 본 항목으로 dirty read·lock starvation을 동시에 측정).
- 더 큰 규모(1억 행) 시험은 행 크기 100바이트 이하 가정·64GB 단일 노드에서 별도 트랙(Phase 2 종료 후)으로 측정 — 본 v1 성공 기준에 포함하지 않음.
- OOM 시 `ER_MEMORY_TABLE_FULL` 정상 반환, 후속 트랜잭션 정상 동작 (회복 테스트).
- regression: 기존 SQL 회귀 테스트 100% 통과.
- soak: 24시간 random DML 부하 후 메모리 누수 없음.

---

### Phase 3: 테이블스페이스 (6~12개월)

**목표**: Oracle/Postgres 스타일 테이블스페이스 제공. 운영자가 테이블/인덱스를 특정 디바이스/볼륨 그룹에 배치 가능.

**우선순위 정정**:
- Phase 3는 Phase 2와 결합도가 낮으므로, 사용자 수요(운영팀의 볼륨 분리 요구)가 우선이라면 Phase 2 이후 Phase 4보다 먼저 출시 가능.
- Phase 4 DuckDB 임베드 시 "DuckDB 데이터 위치"를 테이블스페이스로 자연스럽게 표현 가능 *하다는 가설*은 Phase 4 진입 시 재검증.
- **본 Phase의 LOC/세부 분해는 Phase 2 종료 후 별도 상세 plan 문서로 작성** — 이하 견적은 *간략 견적*임을 라벨링.

**간략 견적 (모듈 수준)**:

| 모듈 | 라인 추정 (간략) | 주요 파일 |
|---|---:|---|
| DDL (`CREATE/ALTER/DROP TABLESPACE`) | 200~400 | `csql_grammar.y`, `parse_tree.h` |
| Catalog (`_db_tablespace`) | 200~400 | `schema_system_catalog_*.cpp`, `schema_manager.c` |
| Storage 매핑 | 800~1,500 | `file_manager.c`, `disk_manager.c`, `boot_sr.c` |
| `ALTER TABLE ... TABLESPACE` 이관 | 400~800 | `locator_*.c`, `heap_*.c` |
| 백업/복구 인지 | 300~600 | `cubrid_backupdb`, `log_compress.c` 인접 |
| 권한 (tablespace privilege) | 100~300 | `authenticate.c` |
| 테스트 | 500~1,000 | `tests/`, `unit_tests/` |

> 합계 신뢰구간 2,500~5,000 LOC (Phase 2와 비슷한 규모) — *간략 견적*. 정밀 견적은 Phase 2 종료 후.

**리스크**: 중. 기존 볼륨 시스템과의 호환성, 백업 도구 영향.

**보안/감사**:
- 신규 권한: `CREATE/DROP TABLESPACE`는 DBA 권한, `ALTER TABLE ... TABLESPACE`는 테이블 owner 권한.
- 감사: 모든 TABLESPACE DDL은 audit log 1급 이벤트로 기록.

**성공 기준**:
- 동일 테이블의 다른 tablespace 이관 후 데이터/인덱스 무손실.
- 백업/복구가 tablespace 인식 (cross-tablespace 백업 1회 통과).
- 권한 분리: 비DBA 사용자가 TABLESPACE DDL 실행 시 거부.

---

### Phase 4: DuckDB 임베드 (3~6개월)

**목표**: 컬럼너 OLAP 엔진을 외부 테이블 형태로 통합.

**구현 방식**:
- `pl_engine/`의 Java PL JNI 브릿지 패턴 참고
- DuckDB(MIT 라이선스)를 CMake에 통합, 별도 trust boundary
- `DB_VALUE` ↔ DuckDB type 변환 레이어
- `CREATE EXTERNAL TABLE foo ... ENGINE=DUCKDB` 또는 Phase 3 테이블스페이스 활용
- `scan_manager`에 `S_EXTERNAL_TABLE_SCAN` 추가

**Phase 2와의 시너지 (검증 게이트 형태)**:
- Phase 2 작업 분해에 `scan source 추상화 레이어 (~100~200 LOC)` 항목을 명시적으로 포함했음. 본 시너지의 가설은 *행 단위 vs 배치 단위*, *lifetime 모델 차이*에도 불구하고 다음 *공통 시그니처*를 만족하는지로 검증함:
  1. `init(scan_source_t *self, scan_context_t *ctx)` — 스캔 컨텍스트 초기화.
  2. `next_record(scan_source_t *self, DB_VALUE *out_row, int out_row_capacity, int *out_row_count)` — 행 단위 폴(폴 호출당 1행 또는 N행 배치 모두 허용; DuckDB 측은 내부 vector(보통 1024행)에서 행 단위로 변환·반환).
  3. `seek(scan_source_t *self, scan_position_t pos)` — (선택) 재시작 또는 PK lookup용.
  4. `close(scan_source_t *self)` — 자원 해제.
  5. `get_stats(scan_source_t *self, scan_stats_t *out)` — (선택) optimizer 비용 모델 입력.
- DuckDB의 C API(`duckdb_query`, `duckdb_fetch_chunk`)는 위 시그니처에서 `next_record`를 vector → 행 단위 어댑터로 만족 가능(부록 A.2). 만족 불가가 판명되면 본 시너지 주장을 철회하고 Phase 4 일정에 추상화 신규 설계 +2~4주 가산.
- Phase 4 진입 시 Phase 2의 추상화를 *그대로 재사용 가능한지* 사전 점검 게이트를 둠.

**간략 견적 (모듈 수준)**:

| 모듈 | 라인 추정 (간략) | 주요 파일 |
|---|---:|---|
| CMake/빌드 통합 | 100~200 | `CMakeLists.txt` |
| `EXTERNAL TABLE` DDL | 150~300 | `csql_grammar.y` |
| Type 변환 레이어 | 600~1,200 | 신규 `src/storage/duckdb_bridge.{hpp,cpp}` |
| Scan 통합 | 300~600 | `scan_manager.{h,c}` (Phase 2 추상화 재사용) |
| 트랜잭션 매핑 | 400~800 | (eventual consistency 가정 시) |
| 백업/HA 통합 | 200~500 | (read-only replica로 한정 시) |
| 테스트 | 500~1,000 | — |

> 합계 신뢰구간 2,300~4,600 LOC. 정밀 견적은 Phase 3 종료 후.

**핵심 결정 (본 문서에서 미리 결정)**:
- **트랜잭션 일관성 모델**: *eventual consistency 가정으로 추정.* 본 문서에서 "eventual consistency"의 의미를 다음과 같이 적시한다 — (a) CUBRID 트랜잭션 commit 시 DuckDB로의 반영은 *비동기*이며, (b) **동일 세션 read-after-write도 보장하지 않음**(즉 같은 세션에서 INSERT 직후 SELECT를 DuckDB로 보낸 경우 결과가 비결정적). 이 의미는 §5.4 결정 항목으로 별도 명시. 강일관성(strict consistency, 2PC + log shipping) 필요 시 일정 가산은 약 2~3배로 추정하되, 본 추정치는 *유사 사례 정성 추정*이며 Phase 4 진입 게이트에서 PoC를 통해 재검증할 의무 항목으로 등재.
- **백업 정책**: DuckDB 데이터 파일 별도 백업 디렉터리. CUBRID 백업 도구는 메타데이터만 일관 보장, 실데이터는 외부 도구 의존(가이드 제공).
- **HA**: 1차 출시는 read-only replica로 한정. multi-master 동기화는 본 로드맵 범위 외.

**미결정 사항 (Phase 4 진입 게이트에서 결정)**:
- DuckDB 라이선스/보안/CVE 재검토 (게이트 항목, §5.4 참고).
- 통합 회귀 테스트의 OLTP 트랙과의 결합 시점.

**리스크**: 중. 외부 라이브러리 의존, 라이선스 검토 필요 (DuckDB는 MIT, CUBRID는 Apache 2.0 — 호환).

**보안/감사**:
- DuckDB 프로세스/스레드는 CUBRID 코어와 동일 trust boundary로 시작하되, Phase 4 종료 시점에 별도 sandbox 분리 검토.
- DuckDB CVE 추적: NVD/GitHub Advisory 자동 모니터링 (정책 §4.1 R-G 참고).
- EXTERNAL TABLE DDL은 DBA 권한.

**성공 기준 (단계별 통과/베타/출시 철회)**:
- TPC-H scale factor 10 워크로드, 대표 쿼리 5종(**컬럼너 우위 워크로드 3종 Q1·Q6·Q14 + 조인 워크로드 2종 Q3·Q12**) 평균 기준 **DuckDB 경유 시 기존 row store 대비 분석 쿼리 수행 시간**:
  - **≥50% 단축 → GA 출시 통과**.
  - **30~50% 단축 → 베타 출시**(피드백 수집 후 GA 재평가).
  - **<30% 단축 → Phase 4 GA 보류, 통합 재설계 또는 출시 철회**(§5.4 fallback 옵션 G/H 검토 진입).
- DuckDB CVE 발생 시 패치 가용 시간 7일 이내 적용 가능한 빌드 파이프라인 검증.
- 트랜잭션 매핑 회귀: eventual consistency 가정 하 데이터 정합성 점검 1회.

---

## 4. 리스크 및 가정

### 4.1 주요 리스크

| ID | 리스크 | 영향 | 대응 (주체 / 산출물) |
|---|---|---|---|
| R-A | 인력 이탈/병행 작업 증가로 일정 지연 | 큼 | *주체*: 팀장 / *산출물*: 인력 배정 확정 문서. Phase 단위 독립 출시 가능 — 어느 Phase에서 멈춰도 부분 가치. |
| R-B | Phase 2의 buffer-pool 우회 패턴이 향후 기술부채 | 중 | *주체*: Phase 2 lead / *산출물*: scan source 추상화 설계 리뷰 회의록 + 인터페이스 헤더(`scan_source.hpp`). |
| R-C | Phase 4 DuckDB 라이선스/배포 이슈 | 중 | *주체*: 라이선스 검토 담당(법무 또는 _미지정 — §5 상단 안내대로 팀장이 지정해야 할 항목_) / *산출물*: 라이선스 검토 보고서 (Phase 3 종료 시점). |
| R-D | OLAP 사용자 수요 예상보다 작음 → ROI 미달 | **큼** | *주체*: 제품 PM(_미지정 — §5 상단 안내대로 팀장이 지정해야 할 항목_) / *산출물*: Phase 1·2 출시 후 사용 사례 수집 보고서. **결정 게이트**: Phase 1·2 출시 후 사용 사례 미달(6개월 내 메모리 테이블 *활성 사용처* < 3건) 시 Phase 3 진입 *보류*. **활성 사용처 정의** = (a) 외부 고객사 1곳 또는 (b) 사내 별도 팀 1곳에서 *동시 충족*: 단일 메모리 테이블당 **1만 행 이상 적재** + **일 1만 쿼리 이상** 실행을 30일 평균으로 유지. 26.5개월 인력 투자 회수가 사업 리스크 핵심 변수이므로 별도 게이트로 격상. |
| R-E | 컬럼너 요구가 강해짐 → DuckDB로 부족 | 작음 | *주체*: 작성자 / *산출물*: Phase 4 후 사용 패턴 분석 노트, 옵션 E 재검토 결정. |
| R-F | 메모리 OOM 시 회복 불완전 (`ER_MEMORY_TABLE_FULL` 후 후속 트랜잭션 영향) | 중 | *주체*: Phase 2 lead / *산출물*: OOM 회복 테스트 시나리오 + 통과 보고서. |
| R-G | DuckDB CVE 발생 시 대응 지연 | 중 | *주체*: 보안 담당(_미지정 — §5 상단 안내대로 팀장이 지정해야 할 항목_) / *산출물*: CVE 모니터링 정책 문서 + 7일 패치 SLA. |
| R-H | dirty read 컴플레인 (사용자가 결과 비결정성에 항의) | 중 | *주체*: 제품 PM / *산출물*: 메모리 테이블 사용 가이드 (회피/권장 패턴), CREATE 시 클라이언트 경고 메시지. |
| R-I | 백업 도구 호환성(특히 Phase 3 tablespace 도입 후) | 중 | *주체*: Phase 3 lead / *산출물*: 백업/복구 회귀 테스트 매트릭스 + 통과 보고서. |
| R-J | 기존 DB의 마이그레이션(Phase 3 tablespace, Phase 4 EXTERNAL TABLE 도입 후) | 중 | *주체*: Phase 3/4 lead / *산출물*: 마이그레이션 가이드 + dry-run 스크립트. |
| R-K | CUBRID 본류 변경과의 conflict (장기 작업 동안 master가 앞서감) | 중 | *주체*: 작성자 / *산출물*: 격주 master 머지 정책 + 머지 로그. |
| R-L | 보안/감사/규정 (전 Phase 공통, PII·메모리 노출 포함) | 중 | *주체*: 보안 담당 / *산출물*: (a) **메모리 테이블에 PII 저장 금지 정책 1매**(GDPR/개인정보보호법 노출 방지), (b) **swap·hibernation 차단 운영 가이드**(메모리 테이블 데이터의 swap 디스크 노출/hibernate 디스크 덤프 노출 방지: `swapoff` 또는 `vm.swappiness=0`, hibernate 비활성화), (c) §3 각 Phase의 "보안/감사" 박스 충족 여부 체크리스트, (d) (a)(b)는 Phase 2 출시 전 보안 담당이 별도 트랙으로 검토·승인. |

### 4.2 핵심 가정
- 시니어 엔지니어 1명을 본 로드맵에 풀타임 또는 평균 50% 이상 배정 가능.
- **Phase 4 종료 후 운영 핸드오프 +2~4주**(인수인계, 운영팀 교육, 온콜 룰 정립). 본 핸드오프 기간은 §6.1 운영 계획에 일정으로 산입하며, 누적 14.5~26.5개월 *외*에 추가됨을 명시(즉 핸드오프 포함 시 14.5~27.5개월).
- 외부 라이브러리 도입 (Phase 4) 라이선스/보안 승인 가능 (Phase 3 종료 시점에 게이트 통과 필요).
- 각 Phase 사이 2주 검증 버퍼 확보 가능 (총 1.5개월).
- *AI-assisted 개발(Claude Opus 등) 사용 가능*: 사용 시 본 일정(누적 14.5~26.5개월) 그대로. **미사용 시 일정 +20~40% 가산 가정**(약 17.4~37.1개월) — 모듈 복잡도 의존. 이 가산은 §2.2의 가정에서 다루고 본 공식 일정에는 반영하지 않으며, §5.3 결정 매트릭스에 *별도 결정 항목*으로 등재해 팀장이 "AI-assisted 사용 전제 동의" 여부를 명시 결정하도록 분리.

### 4.3 제외된 작업
- Windows-specific 최적화 (Phase 2~3에서 Linux 우선)
- 기존 row store 성능 튜닝 — *별도 트랙으로 OLTP 성능 PR(예: #7040, #7050, #7074 등)에서 진행 중*. 본 로드맵 Phase 2/4 출시 시점에 통합 회귀 테스트 1회 수행.
- HA/replication 통합 (메모리 테이블/외부 엔진은 의도적으로 skip)
- Java PL과의 통합 (Phase 4 후 검토)

---

## 5. 팀장 결정 요청 사항

각 결정 항목에 대해 (a) *결정 시 즉시 비용/일정 영향*, (b) *기각 시 대안*, (c) *결정 후 후속 액션*을 매트릭스로 제시.

> **본 §5의 _미지정_ 항목 처리 원칙**: 본 문서에서 _미지정_으로 표기된 책임자(인력 배정 승인자, R-C 라이선스 검토 담당, R-D 제품 PM, R-G 보안 담당, R-L 보안 담당)는 *팀장 본인이 본 로드맵 승인과 동시에 지정해야 할 항목*으로 간주한다. 본 문서 발행 시점에 미지정인 채로 남는 항목은 팀장의 후속 지정 액션을 §5.1/5.3의 후속 액션으로 명시 위임함.

### 5.1 로드맵 전체

| 결정 | 승인 시 영향 | 기각 시 대안 | 후속 액션 |
|---|---|---|---|
| 본 4-Phase 로드맵 승인 | 즉시 Phase 1 PoC 착수, 14.5~26.5개월 인력 락인 | 옵션 G(materialized view 강화) 단일 Phase로 축소 또는 Phase 1만 우선 진행 | Phase 1 kick-off 회의 1회 + R-C/R-D/R-G/R-L 책임자 지정 |
| 옵션 E/F 제외 동의 | 자체 컬럼너/pluggable 미진행 | 옵션 E 단독 진행 시 18~30개월 + 매우 높은 리스크 감수 | (해당 없음) |
| Phase 순서 변경 (예: 3 우선) | Phase 3가 Phase 2보다 먼저 출시 — 운영 유연성 우선 | 본 순서 유지 | 우선 Phase의 상세 plan v2 작성 |

### 5.2 Phase 2 핵심 스펙

> **단위/누계 안내**: 아래 "+/-주" 표기는 Phase 2 *단독* 일정에 대한 증감이며, 12~20주 한도를 초과하는 항목은 절대값 형태로 함께 기재. 누계는 Phase 2 검증 버퍼(2주)를 우선 소진하고, 그래도 부족분은 Phase 3 시작이 1~2개월 지연되는 형태로 흡수됨.

| 결정 | 승인 시 영향 | 기각 시 대안 | 후속 액션 |
|---|---|---|---|
| 가시성 = Global | 단일 메모리 영역, 구현 단순 | Session-local 변경 시 +2~4주 (Phase 2 12~20주 → 14~24주, 검증 버퍼 일부 소진), prepared statement 모델과 결합 필요 | 카탈로그 플래그 비트 정의 시작 |
| DML = INSERT/UPDATE/DELETE 전체 | 일반 테이블과 사용 경험 일치 | Read-only로 축소 시 -3~6주 단축 (Phase 2 9~17주로 축소) | DML 분기 위치 PoC |
| 인덱스 = PK hash only | 메모리 hash table 단일 경로, 단순 | Secondary index 추가 시 **+4~8주** → Phase 2 16~28주로 *확장* (검증 버퍼 소진 후 Phase 3 시작 약 1개월 지연). 단, ETL staging/OLAP 중간 결과/분석 임시 데이터셋 등 풀스캔·secondary index 필요 use case를 살리려면 본 옵션이 필요 — 팀장 "+4~8주 감수" 명시 동의 시 본 문서 v2에서 Phase 2 용도 목록 확장. | hash index 모듈 설계 (현 결정) / use case 확대 시 secondary index 모듈 설계로 전환 |
| OOM = 에러 반환 | 운영 단순, 사용자 가시 명확 | LRU eviction 시 **+6~10주** → Phase 2 18~30주로 확장 (검증 버퍼 소진 + Phase 3 시작 1~2개월 지연) + 사용자 모델 복잡화 | `ER_MEMORY_TABLE_FULL` 코드 추가 |
| DML 트랜잭션 의미론 = autocommit-per-statement (ROLLBACK 영향 밖) | WAL 없음 일관, 구현 단순 | 트랜잭션-aware in-memory undo 도입 시 **+6~10주** → Phase 2 18~30주로 확장 | 운영 가이드 1매 + 클라이언트 경고 메시지 |
| Use case 범위 = PK 기반 캐시/dimension에 한정 | 인덱스 결정과 정합 | 풀스캔·secondary index 필요 use case 포함 시 위 secondary index 결정과 함께 +4~8주 감수 동의 필요 | 운영 가이드에 권장/회피 use case 명시 |

### 5.3 인력/일정

| 결정 | 승인 시 영향 | 기각 시 대안 | 후속 액션 |
|---|---|---|---|
| 시니어 1명 풀타임 배정 | 본 일정대로 진행 | 50% 배정 시 일정 약 2배. 25% 배정 시 Phase 1만 권장. | 인력 배정 합의 문서 (작성자: 팀장 지정 — 본 §5 상단 안내) |
| 검토 위임 대상 지정 | 대상 동료의 Phase 2 설계 리뷰 참여 | 작성자 단독 진행 (리스크 R-B 가산) | 검토자 지정(팀장 본인) 후 사전 리뷰 1회 |
| **AI-assisted 개발(Claude Opus 등) 사용 전제 동의** | 본 일정(14.5~26.5개월) 그대로 적용 | AI-assisted 미사용 결정 시 **+20~40% 가산** → 누적 17.4~37.1개월. 본 가산이 인력/일정 결정 변수의 핵심 swing factor임. | 사용 결정 시: 토큰 비용 실측 트랙(부록 D) 가동. 미사용 결정 시: 본 문서 v2에서 모든 일정·LOC 표를 +20~40% 가산판으로 재발행. |

### 5.4 외부 의존성 게이트 (Phase 4)

| 결정 | 승인 시 영향 | 기각 시 대안 | 후속 액션 |
|---|---|---|---|
| Phase 3 종료 시점에 DuckDB 라이선스/보안 재검토 후 진입 결정 (게이트) | Phase 4 진입 시점에 한 번 더 의사결정 가능 (사전승인 강제 아님) | **게이트 기각 시 fallback (작성자 권고 기본 순서, 상호배타 아님)**: 우선 **옵션 G** materialized view 강화(+2~4mo MVP)를 1순위로 채택해 Phase 2 자산 위에서 OLAP 가속 가치를 부분 회수하고, **옵션 G로 수요 미충족(예: 출시 3~6개월 내 컬럼너 형식 외부 데이터 통합 요구가 신규로 식별)일 때만 옵션 H** Apache Arrow/Parquet 외부 테이블(+4~8mo MVP)을 추가 채택한다. 두 옵션 모두 Phase 1·2·3 자산을 그대로 활용 가능. | Phase 3 종료 1개월 전 라이선스 검토 보고서 작성 (R-C). 게이트 기각이 가시화되면 옵션 G를 §5.1 신규 결정 안건으로 우선 상정, 옵션 H는 G 출시 후 수요 재평가 시점에 별도 안건으로 상정. |
| **Phase 4 일관성 모델 = eventual consistency** (동일 세션 read-after-write 비보장) | 본 일정(3~6mo) 적용. CUBRID commit → DuckDB 반영은 비동기. | strict consistency(2PC + log shipping) 시 일정 약 2~3배(9~18mo) — Phase 4 진입 게이트 PoC에서 검증. read-after-write 단일 세션 보장만 추가하는 중간 옵션 시 +2~4mo. | "eventual = 동일 세션 read-after-write 비보장"을 운영 가이드 + EXTERNAL TABLE DDL 1회 경고로 사용자 가시화. |

### 5.5 시장 포지션 (참고용)

본 로드맵 완수 후 CUBRID의 *기능 보유 여부* 비교 (✓=지원, ✗=미지원, ◐=부분/외부 의존). 본 표는 **기능 보유 여부만** 비교하며, 임베디드 OLAP과 별도 서버 OLAP의 *아키텍처 적합성*은 비교하지 않음. 따라서 DuckDB의 "Tablespace ✗"는 카테고리상 부적용에 가까우나 표시 일관성을 위해 ✗로 두고, 카테고리 차이는 표 하단 주석으로 분리.

| 기능 | CUBRID (본 로드맵 후) | PostgreSQL | MariaDB | DuckDB (임베디드 OLAP) | ClickHouse (별도 서버 OLAP) |
|---|:---:|:---:|:---:|:---:|:---:|
| Row store OLTP + MVCC | ✓ | ✓ | ✓ | ✗ | ✗ |
| Memory/temp table | ✓ | ✓ | ✓ | ✓ | ✓ (Memory engine 명시 지원) |
| Tablespace | ✓ | ✓ | ✓ | ✗ (임베디드 단일 파일 모델) | ◐ (`storage_policies` 기반 multi-volume — tablespace 유사) |
| Columnar OLAP | ◐ (DuckDB 임베드) | ◐ (Citus columnar 등 확장) | ◐ (ColumnStore 별도 엔진) | ✓ | ✓ |
| HTAP 단일 인스턴스 | ◐ (Phase 4 후) | ◐ | ◐ | ✗ | ✗ |
| REST API | ✓ (Phase 1) | ◐ (PostgREST 외부) | ◐ (외부) | ✗ | ◐ (HTTP interface) |

> 본 표는 *기능 보유 여부*만 보여주며, DuckDB는 임베디드 분석 엔진 카테고리, ClickHouse는 별도 OLAP 서버 카테고리로 아키텍처 위치가 다르다. CUBRID/PostgreSQL/MariaDB는 RDBMS 카테고리에서 비교한다. 정량 벤치마크는 Phase 4 출시 시점에 별도 측정.

---

## 6. 다음 단계

본 문서 승인 시:

1. **Week 0~2**: 본 로드맵 사내 공유 + 의견 수렴 + 문서 v2 개정 (현실적인 의견 수렴 기간). 동시에 §5 _미지정_ 책임자(인력 배정 승인자, R-C/R-D/R-G/R-L 담당) 지정.
2. **Week 3~4**: Phase 1 REST API 서버 PoC 시작.
3. **Week 5~**: Phase 2 in-memory 테이블 설계 상세화 + 코드 작업 시작.
4. **각 Phase 종료 시**: 사용 지표 (테이블 수, 쿼리 수, 메모리 사용량 등) 수집 → 다음 Phase 진입 여부 재검토 게이트.
5. **각 Phase 사이 2주 검증 버퍼**: 회귀 테스트, 보안/감사 점검, 사전 리뷰 합의.

### 6.1 출시 후 운영 계획

각 Phase의 출시 *후* 운영을 본 문서가 명시적으로 다룸:

- **모니터링**: Phase 1은 access log + Prometheus 메트릭(`/metrics`). Phase 2는 `INFORMATION_SCHEMA.MEMORY_TABLES` + 메모리 사용량 sysparam. Phase 3은 tablespace별 디스크 사용량 카탈로그 뷰. Phase 4는 DuckDB 데이터 디렉터리 사용량 + 쿼리 latency 히스토그램.
- **문서화**: 각 Phase 출시와 함께 운영 매뉴얼 1장. Phase 2/4는 사용 가이드(권장/회피 패턴) 1장 추가.
- **지원 채널**: 신규 기능에 대한 사내 1차 지원 채널 지정 (담당: 팀장 지정 — §5 상단 안내). 외부 사용자 issue 트래킹은 기존 GitHub Issues 유지.
- **CVE/보안**: DuckDB 도입 후 NVD/GitHub Advisory 자동 모니터링 + 7일 패치 SLA (R-G).

---

## 부록 A. 참고 자료

- CUBRID 코드베이스: `/home/vimkim/gh/cb/develop`
- 관련 PR:
  - #7040 [CBRD-26707] parallel heap scan
  - #7050 [CBRD-26712] join selectivity 개선
  - #7074 [CBRD-26410] SQL_TRACE_EXECUTION_PLAN 성능 개선
- 사전 조사한 코드 위치 (본 줄번호는 v1 작성 시점(2026-05-08)의 develop 브랜치 기준이며 PR 작업 착수 시 재확인):
  - `csql_grammar.y:1403` — 미사용 `TEMPORARY` 토큰 (본 작업과 방향 다름, 재사용 안 함)
  - `csql_grammar.y:2541-2600` — `CREATE TABLE` 룰 (옆에 `CREATE MEMORY TABLE` 룰 추가 위치)
  - `src/query/scan_manager.h:75-94` — `SCAN_TYPE` enum (16종 switch dispatch)
  - `src/object/class_object.h:294-300` — `SM_CLASS_TYPE` (3종)
  - `src/object/class_object.h:304-312` — `SM_CLASS_FLAG` (5비트 사용 중, 다음 가용 비트에 `SM_CLASSFLAG_MEMORY_TABLE = 32` 배치 가능; 직렬화 폭은 32비트 이상 사전 점검 필요)
  - `src/query/list_file.{h,c}` — `qfile_*` API, `TEMP_FILE_MEMBUF_NORMAL` spill 정책
  - `src/session/session.{h,c}` — prepared statement 패턴 차용 대상
- 산업 선례:
  - MySQL HEAP/MEMORY engine — 본 Phase 2 디자인 참고 대상
  - Postgres unlogged tables — 비슷하지만 디스크 사용
  - MariaDB ColumnStore, Citus columnar, Postgres ZedStore — 옵션 E 산업 선례 (대규모 프로젝트)
  - MariaDB pluggable storage engine 도입 (5.1 → 5.5) — 옵션 F 산업 선례 (다년 프로젝트)

### 부록 A.1 DuckDB의 RDBMS 임베드 안정성 사례 (참고)

본 부록은 *공식 인용*이 아닌 작성자가 식별한 사례 목록임. Phase 4 진입 게이트(§5.4)에서 운영 사례 1차 자료를 정식 수집할 예정. 본 표 제목을 *RDBMS 통합* 주장에서 *임베드 안정성*으로 좁혔으며, RDBMS 통합 사례(`pg_duckdb`, `duckdb_fdw`)를 별도 행으로 추가했다.

| 사례 | 통합 방식 | 운영 결과 (요약, 작성자 관찰) |
|---|---|---|
| `pg_duckdb` (PostgreSQL extension, MotherDuck/DuckDB Labs 운영) | PostgreSQL 내부에 DuckDB를 extension으로 임베드, 분석 쿼리를 DuckDB 엔진으로 위임 | RDBMS-내부 임베드 패턴 1차 사례. CUBRID Phase 4의 직접 참고 대상. |
| `duckdb_fdw` (PostgreSQL Foreign Data Wrapper) | DuckDB를 FDW로 노출, EXTERNAL TABLE 형태로 통합 | EXTERNAL TABLE 모델의 사전 사례 — 본 Phase 4 DDL 모델과 유사. |
| DuckDB 자체 CLI/임베드 라이브러리 | 단일 프로세스 임베드 | 데이터 분석 도구 표준 임베드 사례 — 메모리 모델·파일 포맷 안정. RDBMS 통합 사례는 아니며 임베드 안정성의 정황 증거. |
| MotherDuck (관리형 DuckDB) | DuckDB를 클라우드 서비스로 래핑 | 동일 엔진을 호스팅 형태로 제공 — 단일 노드 OLAP 검증. RDBMS 통합 사례는 아님. |
| Python `duckdb` 패키지 | C++ 라이브러리를 Python 바인딩으로 임베드 | 데이터 사이언스 표준 — 안정성·성능 광범위 검증. RDBMS 통합 사례는 아님. |
| _Phase 4 진입 시점 1차 자료 수집 예정 (담당: 팀장 지정 — §5 상단 안내)_ | — | — |

> 위 표는 v1 작성 시점의 **간접 정보 기반 요약**이며 정확한 통합 방식·운영 지표는 Phase 4 진입 게이트에서 1차 자료(공식 문서/사례 발표)로 검증한다. 첫 두 행(`pg_duckdb`, `duckdb_fdw`)이 RDBMS 통합 사례, 나머지는 임베드 안정성의 정황 증거이다.

### 부록 A.2 scan_source 추상화의 공통 시그니처와 DuckDB 적합성 근거

Phase 2의 `scan_source.hpp`가 Phase 4 DuckDB 통합에 그대로 재사용 가능한지의 가설을 검증하기 위한 공통 시그니처와 DuckDB 측 매핑.

**공통 시그니처 (스케치)**:

```cpp
// src/storage/scan_source.hpp 예상 시그니처 (구현 시 재확정).
struct scan_source_vtable
{
  int (*init) (scan_source_t *self, scan_context_t *ctx);
  // out_row: 단일 행 또는 N행 배치(out_row_capacity로 협상),
  // out_row_count: 실제 채워진 행 수, 0이면 EOF.
  int (*next_record) (scan_source_t *self, DB_VALUE *out_row,
                      int out_row_capacity, int *out_row_count);
  int (*seek)       (scan_source_t *self, scan_position_t pos);   /* 선택 */
  int (*get_stats)  (scan_source_t *self, scan_stats_t *out);     /* 선택 */
  int (*close)      (scan_source_t *self);
};
```

**DuckDB 매핑 (가설)**:
- `init` → `duckdb_open` + `duckdb_connect` + `duckdb_query`로 결과 핸들 확보.
- `next_record` → `duckdb_fetch_chunk`로 vector(보통 1024행)를 수령한 뒤 vector → 행 단위 어댑터로 변환. 호출자가 단일 행을 요구하면 내부 vector 캐시에서 1행씩 송출, 배치를 요구하면 vector 통째로 변환.
- `seek` → DuckDB는 임의 seek가 없으므로 (a) 결과 핸들 재실행 또는 (b) 본 메서드를 *지원 안 함* 플래그로 두어 행 lifetime 차이를 감춤.
- `get_stats` → DuckDB EXPLAIN ANALYZE 결과 또는 catalog statistics 매핑.
- `close` → `duckdb_destroy_result` + 연결 정리.

**시너지 주장의 조건**:
- 위 매핑이 Phase 4 진입 게이트 PoC에서 작동하면 추상화 그대로 재사용. 시그니처 부적합(예: `seek` 필수성 발견, `next_record`의 lifetime 모델 비호환) 발견 시 Phase 2 추상화 시너지 주장은 *철회*하고 Phase 4 일정에 추상화 신규 설계 +2~4주를 가산한다(§Phase 4 게이트 절).

## 부록 B. 용어

- **HTAP**: Hybrid Transactional/Analytical Processing
- **OLTP**: Online Transaction Processing
- **OLAP**: Online Analytical Processing
- **MVCC**: Multi-Version Concurrency Control
- **WAL**: Write-Ahead Logging
- **PAX**: Partition Attributes Across (하이브리드 행/열 페이지 레이아웃)

## 부록 C. 사전 리뷰 / 합의·이견

- 사전 리뷰 예정 — 리뷰어 _미지정 — §5 상단 안내대로 팀장 본인이 지정해야 할 항목_.
- v1 발행 후 동료 1~2명 사전 리뷰를 실시하고, 합의 사항/이견 사항을 본 부록에 추가 기록한다.
- 본 부록이 비어 있는 한 본 문서는 *작성자 단독 의견*임을 명시.

## 부록 D. TCO 추정 (참고)

> **TCO는 결정 변수에 포함되지만**, 인건비 단가 등이 사내 기밀이므로 본 문서에 수치를 적시하지 않으며 *별도 회의에서 검토*한다. 본 부록은 결정 회의의 입력으로 사용할 산식과 데이터 수집 계획만 정리한다.

**산식**:
- 인건비 = 시니어 1명 × 14.5~26.5개월 (Phase 사이 검증 버퍼 1.5개월 포함). 회사 내부 인건비 단가는 별도 회의에서 의사결정자가 직접 입력.
- 토큰 비용 (AI-assisted 사용 시) = 시간당 추정 토큰 비용 × 실제 active AI 사용 시간. 정확한 산식은 첫 Phase 종료 후 *실측치*로 갱신.
- v1 시점에서는 토큰 비용에 대한 사전 추정치를 *제시하지 않음* — 산식의 자기일관성을 확보하지 못한 채로 표에 노출하면 결정에 노이즈가 됨.
- 첫 Phase(REST API, 1~2개월) 종료 시 실측 토큰 사용량을 부록 D에 갱신한 뒤, 이후 Phase에 일관 산식을 적용한다.
- AI-assisted 미사용 결정(§5.3) 시 인건비가 +20~40% 증가하므로 본 산식의 인건비 항을 17.4~37.1개월로 갱신.

**TCO 비중 정성 평가**: 인건비가 압도적 비중일 것으로 정성 추정되며 토큰 비용은 한 자릿수 % 이하로 정성 추정. 본 정성 추정은 별도 회의에서 사내 단가 입력 후 정량 확인 대상.

> **§5.3 결정 swing의 좁힘 안내**: 위 정성 추정이 사실로 확인되면 토큰 비용은 결정 변수가 아니므로 AI-assisted 사용은 일정 단축(20~40%) 면에서 거의 항상 우월한 선택이 된다. 따라서 §5.3의 "AI-assisted 사용 전제 동의" 결정은 *비용 trade-off* 문제가 아니라 **(a) 미사용 시 일정 정확도(+20~40% 가산판으로 일정 재발행) + (b) 인건비/리소스 trade-off**에 한정된 결정으로 좁혀진다. v1 정성 추정이 Phase 1 종료 후 실측에서 뒤집힐 경우 본 안내를 v2에서 갱신한다.

---

*문서 끝.*
