# CUBRID 로그 매니저 동적 분석 Plan (append→flush)

> 기준 소스: `~/gh/cb/log-manager-analysis` 워크트리 (master 4cfc8370e 기반, 브랜치 `log-manager-analysis`)
> 선행 문서: [cubrid-log-manager-overview_4cfc837_claude.md](./cubrid-log-manager-overview_4cfc837_claude.md) (정적 분석)
> 작성: Claude (2026-07-28)

---

## 1. 목표

기존 정적 분석 문서가 서술한 **로그 append → prior list drain → 페이지 버퍼 → 디스크 flush(fsync)** 경로를,
실제 코드에 printf 트레이스를 심고 **CS 모드 csql 워크로드**를 실행해 **실측 타임라인으로 검증·보강**한다.

최종 산출물:

1. **동적 분석 보고서** — `my-cubrid-docs/log-manager/cubrid-log-manager-append-flush-dynamic-analysis_4cfc837_claude.md` (한국어)
2. 검증된 두 문서를 도메인 모델로 삼는 **grill 이해 세션** (`/grill-with-docs`, 이후 사용자가 `/grill-me` 직접 수행)

## 2. 검증 질문 (보고서가 답해야 할 것)

| # | 질문 | 정적 문서의 주장 (검증 대상) |
|---|------|------------------------------|
| Q1 | 커밋하는 워커 스레드는 로그를 **직접 flush**하는가, **flush 데몬에 위임하고 대기**하는가? | 데몬 가용 시 위임+대기 (`logpb_flush_pages`) |
| Q2 | prior list는 **언제** 드레인되는가? | flush 직전 + 리스트 크기 초과 시 (`LOG_PRIOR_LSA_LIST_MAX_SIZE`) |
| Q3 | autocommit INSERT 1건이 만드는 **로그 레코드 시퀀스**는 실제로 무엇인가? | sysop + undoredo + … + `LOG_COMMIT` |
| Q4 | **그룹 커밋**: 동시 커밋 N개가 fsync 1회로 병합되는가? | `group_commit_interval_in_msecs` > 0일 때 병합 |
| Q5 | LSA(prior_lsa → append.lsa → nxio_lsa)는 각 단계에서 **어떻게 전진**하는가? | 3단 좌표가 순서대로 따라감 |

## 3. 단계별 계획

### Phase 0 — 준비

- [ ] 워크트리 빌드 확인: `just build` (ccache 기반, cubrid-build 스킬 워크플로우)
- [ ] 테스트 DB 생성 (`cubrid createdb`), `cubrid server start` 후 `csql -C`(CS 모드) 접속 확인
- [ ] 트레이스 출력 목적지 확인: cub_server는 데몬이므로 stdout이 아닌 **전용 트레이스 파일**(append 모드, fflush)로 기록

### Phase 1 — 트레이스 계측

공용 헤더 `src/transaction/logmgr_trace.hpp` 를 추가하고(마이크로초 타임스탬프 + tid + 이벤트 한 줄 기록), 아래 포인트에 삽입:

| # | 위치 | 이벤트 | 기록 내용 |
|---|------|--------|-----------|
| T1 | `log_append.cpp` `prior_lsa_next_record_internal()` | 레코드 생성·prior list 삽입 | tranid, rectype 이름, 할당된 LSA |
| T2 | `log_append.cpp:1529` 부근 | 리스트 초과로 데몬 wakeup / 직접 drain | 리스트 크기 |
| T3 | `log_page_buffer.c` `logpb_prior_lsa_append_all_list()` | prior list drain | 드레인한 노드 수, prior_lsa |
| T4 | `log_page_buffer.c` `logpb_flush_all_append_pages()` | flush 시작/완료 | 쓴 페이지 수, nxio_lsa 전/후, fsync 여부 |
| T5 | `log_page_buffer.c` `logpb_flush_pages()` | 커밋 스레드의 flush 요청·대기·기상 | 요청 LSA, 대기/직접수행 분기 |
| T6 | `log_manager.c` `log_append_commit_log(_with_lock)()` | COMMIT 레코드 append | tranid, commit_lsa |
| T7 | `log_manager.c` flush 데몬 태스크 (`log_flush_daemon_*`) | 데몬 기상/수면 | 기상 사유(주기/wakeup) |
| T8 | `log_manager.c` `log_wakeup_log_flush_daemon()` | 데몬 깨우기 | 호출 스레드 |

계측 원칙: 삽입은 한 줄 매크로 호출로 최소화, PR 대상이 아니므로 워크트리에만 유지(커밋하지 않음).

### Phase 2 — 재빌드 + 워크로드 실행

`just build` 후 서버 재시작, 시나리오별로 트레이스 파일을 구분 수집:

| 시나리오 | 내용 | 관찰 목표 |
|----------|------|-----------|
| S1 | autocommit ON, INSERT 1건 | Q3, Q1: 최소 단위 커밋의 전체 경로 |
| S2 | autocommit OFF, INSERT 3건 후 COMMIT | Q2, Q5: 레코드 축적과 드레인 시점 |
| S3 | UPDATE 후 ROLLBACK | 보상(compensate) 레코드와 abort 경로 |
| S4 | 두 세션 동시 커밋 (csql 2개 백그라운드) | Q4: fsync 병합 |
| S5 | (선택) `group_commit_interval_in_msecs` 변경 후 S4 재실행 | Q4 파라미터 영향 |

### Phase 3 — 트레이스 분석

- 시나리오별 트레이스를 타임라인으로 재구성 (µs 단위, 스레드별 구분)
- Q1~Q5 각각에 대해 **실측 근거 라인**을 인용해 판정
- 정적 문서와 어긋나는 부분이 있으면 코드 재확인 후 문서 정정 목록 작성

### Phase 4 — 보고서 작성

- `cubrid-log-manager-append-flush-dynamic-analysis_4cfc837_claude.md` 작성 (한국어)
  - 실측 타임라인 다이어그램, Q1~Q5 판정표, 시나리오별 트레이스 발췌, 계측 diff 요약
- 기존 overview 문서와 상호 링크, 필요 시 overview 문서 정정

### Phase 5 — grill 이해 세션

- `/grill-with-docs` 실행: 두 문서를 도메인 모델로 삼아 용어·주장 검증, 문서 인라인 갱신
- `/grill-me`는 이 세션에 등록되지 않은 커맨드이므로 **사용자가 직접 호출** (두 문서를 자료로 지정)

## 4. 원복 정책

- 계측 코드(`logmgr_trace.hpp` + 삽입 라인)는 분석용 워크트리에만 두고 **커밋하지 않는다**.
- 보고서에 계측 diff를 부록으로 남겨 재현 가능하게 한다.
