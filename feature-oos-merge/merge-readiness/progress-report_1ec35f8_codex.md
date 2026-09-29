# OOS 진행 상황과 테스트 실패 보고

확인일: 2026-09-29. 작업 221. **현재 기술적 머지 준비는 미완료다.**

QA 자료 갱신과 전체 실패 목록 정리, develop 통합 후보의 debug/release 빌드와 focused isolation 검증까지 진행했다. 선행 기능 수정, 원인 불명 테스트, 전체 검증 증거가 남아 있다. 실제 develop 머지와 테스트 실행기 수정은 이번 작업에 포함하지 않는다.

## 끝난 일과 남은 일

| 구분 | 현재 상태 |
|---|---|
| 기존 조사 | 비CDC 추가 후보 46행/35개 테스트 조사 및 S04 원본 20개 하위 사례의 6회 실행 완료. 원인 확정이나 전체 검증 완료는 아님 |
| QA 새 자료 | feature `1ec35f8`, develop `e1c3db1` 자료를 다시 수집. 비CDC 추가 후보는 식별된 항목 기준 48행. 새 장시간 테스트 3행 추가, 기존 CCI 1행은 공통 실패로 이동 |
| develop 통합 준비 | 현재 develop `f1bd99ed43a134383bc0be1d766a6f121601a499`를 별도 worktree에 실제 merge commit `fb567a629cdb390fff920542173fa36f454c74a0`으로 통합. 원격 PR은 아직 `1ec35f8` |
| 로컬 검증 | 통합 후보 debug/release 빌드·설치 완료. debug/release CTest 각각 35/35 통과. 원본 isolation 사례는 두 모드 모두 1/1 통과 |
| 기능 선행 조건 | PR #7927은 OPEN, PR #7462도 OPEN. 현재 PR #7990 코드에는 raw DB_PAGESIZE/4와 vacuum forward-walk가 남아 있음. commit-conditional OOS 알림 발행 구현 확인 안 됨 |
| 전체 검증 | HA release·shell_ext, RQG 비교, shell_long 세부 누락 등 차단 유지. 새 통합 후보의 QA·CI 증거는 아직 없음 |
| 외부 승인 | CDC 두 건의 maintainer/admin 예외 확보 여부 미확인. 기술적 준비와 별도로 표시 |

CBRD-27230/27237은 실시간 JIRA 조회에서도 Open이다. 오래된 이슈 본문의 20바이트 stub 등은 현행 OOS 명세의 24바이트 기준을 대체하지 않는다. rollback/vacuum 결함은 과거 런타임 재현 기록과 현재 경로 잔존을 구분하며, 이번 실행에서 재현했다고 주장하지 않는다.

## PR CI 검증

PR #7990의 현재 원격 head는 `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21`이고 draft, REVIEW_REQUIRED다. 현재 head의 CI는 medium 975 통과, SQL 17470 통과, shell 3256 통과·2실패·30 skip이다. shell 실패는 합의된 CDC 두 건이다. 과거 `bug_bts_13242`를 현재 실패로 반복 기재하지 않는다.

최초 수집기 결과는 필수 observation 및 summary hash가 없어 warning이었다. 이 기록을 보존하고, 기존 수집기 소스 `45944012aaaa`를 빌드해 별도 빈 저장소에 다시 수집했다. 수집기·테스트 실행기 소스 수정은 없다. 새 증거는 exact-head, schema, observation, summary/raw hash, shard 및 집계를 검증해 **full** 분석 모드가 됐다. [#7990 검증 보고서](ci-verified-pr7990_1ec35f8_codex.md).

선행 PR #7927의 현재 head `34a9072`도 같은 절차로 검증했다. medium 3건, SQL 1건, shell 10건이 실패한다. 이 중 CDC는 2건이며 나머지 12건은 증상과 처리 과제가 남아 있다. 오래된 head의 통과 기록으로 대체하지 않는다. [#7927 전체 실패표](ci-verified-pr7927_34a9072_codex.md).

이 CI 결과는 새 통합 후보 `fb567a6`의 CI가 아니다. 후보 게시와 해당 head의 새 검증이 필요하다.

## 통합 후보의 로컬 검증

현재 develop을 실제 merge commit으로 통합했다. 충돌이 없었고 Standards/Spec 병렬 검토에서 새 통합 지적은 각각 0건이다. 이는 develop의 모든 변경을 재검토했거나 전체 준비를 완료했다는 뜻이 아니다. [통합 검토](integration-review_fb567a6_codex.md).

I01의 원본 `reorganization_select_01.ctl`과 answer를 public testcase `89d4ec2`에서 그대로 사용했다. debug와 release에서 각각 1개를 실행해 성공 1, 실패 0, skip 0을 확인했다. 원래 기대값의 100000행과 그룹 결과를 유지했다. 병렬/hash 실행 경로를 따로 관측하지 않았으므로 I01의 전체 수용 조건은 아직 완료가 아니다. [로컬 검증 근거](local-validation_fb567a6_codex.md).

## 실패 처리 원칙

원인 불명 또는 비교 미완료인 비CDC 항목은 차단이다. develop에서도 같은 조건과 증상으로 재현되고 OOS 악화가 없다는 증거가 있어야 기존 결함으로 분류한다. 필수 체크나 데이터 안전성 검증을 막는 기존 결함은 계속 차단이다. 테스트 이름의 중복, QA 자동 라벨 또는 로그의 추정 설명만으로 원인을 확정하지 않는다.

CDC의 cbrd_27064와 cbrd_27075는 활성 상태의 실패를 유지한다. QA의 다른 CDC 항목도 숨기지 않고 별도 원장에 남기며, 자동으로 이 두 건의 maintainer 예외 범위에 포함하지 않는다.

## 기존 46개 후보의 처리표

동일 처리 단위로 묶은 23개 그룹이다. 정확한 suite/테스트 식별자와 모든 최신 원본 페이지는 아래 상세 원장에 있다. 신뢰도는 관측 사실과 원인 판단을 구분한다.

| 그룹·기존 행 수 | 관측 실패 | develop 비교·분류 | 신뢰도 | 처리 결정·남은 일 | 증거 |
|---|---|---|---|---|---|
| C01 · 1 | 두 번째 클라이언트 로그가 비어 있음 | develop에도 동일 테스트 실패 | 증상 동등성 미확정 | 차단 유지. 양쪽 worker 종료·연결·오류 로그 비교 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| C02 · 2 | CCI 시간 초과 또는 빈 결과 | 원인 불명 | 낮음 | 차단 유지. 완료된 develop 비교 및 broker·driver·호출 단계 확인 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| H01 · 1 | 대체 호스트 Java 테스트 FAIL | 원인 불명 | 낮음 | 차단 유지. 실패 assertion과 failover·driver 증거 확보 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| H02 · 1 | HA 모드 변경·연결 실패 | 원인 불명 | 낮음~중간 | 차단 유지. 동일 topology에서 전환과 서버 오류 확인 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| H03 · 1 | heartbeat에 예상하지 않은 노드 표시 | 환경 차이 후보 | 관측 높음 | 차단 유지. 초기 구성과 실제 membership 검증 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| H04 · 2 | HA online index 두 테스트 실패 | 기능 회귀 후보 | 낮음 | 차단 유지. master/replica 출력·행·인덱스 일관성 확보 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| H05 · 1 | heap header의 물리 offset +8 차이 | 기대값 차이 후보 | 레이아웃 설명 높음 | 차단 유지. 전체 HA 소스와 논리 검증 후 정확한 offset만 수정 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| H06 · 1 | HA 테스트 실패 | 기능 회귀 후보 | 낮음 | 차단 유지. 전체 assertion·master/replica 결과 확보 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| H07 · 7 | HA 복제 debug 7개 추가 후보 | 원인 불명 | 낮음 | 차단 유지. 각 사례의 master/replica 출력·schema·locale 확보 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| I01 · 2 | 병렬 GROUP BY 서버 종료 | develop 수정이 로컬 후보에 통합됨 | 원본 focused 사례 두 모드 통과, 경로 관측 미완료 | 차단 유지. 원격 통합·병렬/hash 경로 증거·최종 head 전체 검증 필요 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| I02 · 1 | 동시 DML affected-row 메시지 순서 차이 | 순서 차이 후보 | 중간~높음 | 차단 유지. client별 결과·barrier·최종 행과 인덱스 유지 확인 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| J01 · 1 | JDBC testBlob01 Java heap 부족 | 환경·driver 후보 | 중간 | 차단 유지. JVM heap·실행 순서·LOB 보존과 메모리 귀속 확인 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| P01 · 1 | 47000행은 맞으나 시간 차 8초가 >8 조건 실패 | 성능 판정 미완료 | 증상 높음 | 차단 유지. 동일 host·버전·설정 반복 측정; 임계값 유지 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| P02 · 1 | 일본어 prefix-key 결과 파일 불일치 | 기능 회귀 후보 | 낮음 | 차단 유지. 전체 diff·collation·계획·그룹 결과 비교 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| Q01 · 1 | AUTO_INCREMENT 예상값과 실제 21 차이 | 기능 회귀 후보 | 원인 낮음 | 차단 유지. serial cache·카탈로그·세션 상태를 고정해 재현 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| Q02 · 1 | 행 결과는 같으나 SHOW TRACE 누락 | 원인 불명 | trace 경로 후보 중간 | 차단 유지. CCI 버전·세션·문장 순서·trace 생성과 소비 확인 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| R01 · 1 | vacuum·인덱스 경로 코어와 checkdb 실패 | 원인 불명·비교 미완료 | OOS 원인 낮음 | 차단 유지. 원본 코어·일치 바이너리·DB/WAL·워크로드 확보 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| S01 · 2 | 오류 진단 기본 목록 차이 | 기대값 차이 후보 | 소스·출력 일치 높음 | 차단 유지. 정확한 기본값만 반영할 테스트 수정 및 양 모드 검증 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| S02 · 8 | DBLink 계획의 마스킹된 cost 자릿수 차이 | 표현 차이 후보 | 일부 debug 증거 높음 | 차단 유지. 모든 backend·모드의 값·DML·계획 조건 보존 확인 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| S03 · 6 | DBLink 결과·오류·테이블 상태 차이 | 기능 회귀 후보 | 원인 낮음 | 차단 유지. 외부 DB 버전과 초기 상태 고정 후 실패문 재현 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| S04 · 2 | 원본 card 기대값 불일치; 로컬 두 브랜치 모두 실패 | 원인 불명 | 증상 높음, OOS 원인 미확정 | 차단 유지. 200000 기대 조건과 99986/100000 차이를 별도 조사; 실행기 증거 한계 유지 | [기존 분석](../qa-qualification/s04-reproduction_1ec35f8_codex.md) |
| S05 · 1 | loaddb 중단 테스트에서 적재가 먼저 완료됨 | 타이밍 차이 후보 | 중간 | 차단 유지. 실제 적재 중 신호 전달과 부분 적재 조건 확인 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |
| S06 · 1 | SSL 설정의 중첩 SQL 실행 시간 초과 | 원인 불명 | 낮음 | 차단 유지. 내부 실행 로그·정확한 자산·정지 단계 확보 | [기존 분석](../qa-qualification/qa_source_triage_1ec35f8_codex.md) |

## 새로 확인한 범위

- shell_heavy의 cbrd_21362와 _51_merge_range_01: 시간 초과/빈 결과가 관측됐다. QA는 기존 이슈 라벨을 붙였지만 develop 결과가 없어 기존 결함 확정으로 취급하지 않는다.
- shell_long의 bug_bts_5775: 실패가 확인됐으나 원인은 미확정이다. summary는 실패 4건, 수집된 상세는 1건이어서 3건의 식별자가 부족하다.
- CCI bug_bts_7941: 새 develop 결과에도 같은 테스트가 실패한다. 증상 동등성은 아직 검증하지 않았다.
- unit release/debug는 양쪽 모두 4/4로 갱신됐다. 이 결과가 전체 OOS unit 또는 최종 통합 후보의 검증을 대신하지 않는다.

## 전체 QA 범위

숫자는 포털 순서대로 전체 / 실행 / 성공 / 실패다. 실행 수와 성공+실패가 다른 항목은 완료로 간주하지 않는다. skip 등 포털 집계 규칙과 추가 세부 자료가 필요하다. 과거 비교 기준은 e1c3db1이고, 최신 develop f1bd99e와 구분한다.

| Suite | feature | develop | 증거 상태 |
|---|---|---|---|
| sql | 17470 / 17470 / 17470 / 0 | 17470 / 17470 / 17470 / 0 | 완료 여부·증상 비교 필요 |
| sql_debug | 17470 / 17470 / 17470 / 0 | 17470 / 17470 / 17470 / 0 | 완료 여부·증상 비교 필요 |
| medium | 975 / 975 / 975 / 0 | 975 / 975 / 975 / 0 | 완료 여부·증상 비교 필요 |
| medium_debug | 975 / 975 / 975 / 0 | 975 / 975 / 975 / 0 | 완료 여부·증상 비교 필요 |
| sql_by_cci | 17470 / 17470 / 17459 / 11 | 17470 / 17470 / 17461 / 9 | 완료 여부·증상 비교 필요 |
| shell | 3489 / 3459 / 3435 / 24 | 3489 / 3459 / 3444 / 15 | 완료 여부·증상 비교 필요 |
| shell_debug | 3489 / 3459 / 3438 / 21 | 3489 / 3459 / 3449 / 10 | 완료 여부·증상 비교 필요 |
| shell_heavy | 100 / 100 / 98 / 2 | NO RESULT (OR RUNNING) | 결과 없음/비교 미완료 — 차단 |
| shell_long | 82 / 82 / 22 / 4 | NO RESULT (OR RUNNING) | 결과 없음/비교 미완료 — 차단 |
| cci | 322 / 322 / 320 / 2 | 322 / 322 / 321 / 1 | 완료 여부·증상 비교 필요 |
| cci_debug | 322 / 322 / 321 / 1 | 322 / 322 / 322 / 0 | 완료 여부·증상 비교 필요 |
| ha_shell | 373 / 373 / 365 / 8 | 373 / 373 / 370 / 3 | 완료 여부·증상 비교 필요 |
| ha_repl | NO RESULT (OR RUNNING) | 17470 / 17274 / 17272 / 2 | 결과 없음/비교 미완료 — 차단 |
| ha_repl_debug | 17470 / 17274 / 17266 / 8 | 17470 / 17274 / 17271 / 3 | 완료 여부·증상 비교 필요 |
| shell_perf | 58 / 58 / 55 / 3 | 58 / 58 / 57 / 1 | 완료 여부·증상 비교 필요 |
| isolation | 6790 / 6772 / 6771 / 1 | 6790 / 6772 / 6772 / 0 | 완료 여부·증상 비교 필요 |
| isolation_debug | 6790 / 6772 / 6770 / 2 | 6790 / 6772 / 6772 / 0 | 완료 여부·증상 비교 필요 |
| jdbc | 2528 / 2528 / 2524 / 4 | 2528 / 2528 / 2524 / 4 | 완료 여부·증상 비교 필요 |
| RQG | 99 / 99 / 97 / 1 | NO RESULT (OR RUNNING) | 결과 없음/비교 미완료 — 차단 |
| cdc_repl | 3327 / 3043 / 2996 / 47 | 3327 / 3043 / 2996 / 47 | 완료 여부·증상 비교 필요 |
| shell_ext | NO RESULT (OR RUNNING) | NO RESULT (OR RUNNING) | 결과 없음/비교 미완료 — 차단 |
| unittest | 4 / 4 / 4 / 0 | 4 / 4 / 4 / 0 | 완료 여부·증상 비교 필요 |
| unittest_debug | 4 / 4 / 4 / 0 | 4 / 4 / 4 / 0 | 완료 여부·증상 비교 필요 |

## 이어서 할 일

1. 로컬 통합 후보 `fb567a6`의 최초 source push 승인을 처리한 뒤 exact-head CI를 실행한다. I01은 원본 isolation 두 모드에서 통과했지만 병렬/hash 경로 검증 전까지 해결로 표시하지 않는다.
2. 선행 기능 PR의 실제 수정·리뷰·검증 상태를 확인해 통합 준비를 진행한다. rollback/vacuum 데이터 손실 조건은 별도 기능 수정과 회귀 검증이 필요하다.
3. 전체 실패 원장의 각 항목을 증거에 따라 처리한다. 자료가 부족한 항목은 부족한 파일·환경을 정확히 기록하고, 진행 가능한 다른 항목을 계속 처리한다.
4. 최종 통합 커밋의 전체 Linux QA와 필수 CI 근거를 확보한다. 과거 커밋의 성공은 새 커밋의 성공을 대신하지 않는다.

## 증거와 재현 정보

- [최신 실패 원장](failure-ledger_1ec35f8_codex.md): 추가 후보·공통 실패·CDC를 모두 보존한다.
- [QA 수집·비교 데이터](evidence/qa-refreshed.json): 원본 run 및 page 경로, suite 집계와 집계 불일치 포함.
- [최초 CI 자료 검증 한계](evidence/ci-validation.json) 및 [새 자료 검증](evidence/ci-clean-validation.json).
- [실행 계약](execution-contract.md): 실제 develop 머지와 실행기 수정 제외.
- [기존 QA 보고서](../qa-qualification/README.md).
- [PR #7990](https://github.com/CUBRID/cubrid/pull/7990), [선행 PR #7927](https://github.com/CUBRID/cubrid/pull/7927), [이전 target PR #7462](https://github.com/CUBRID/cubrid/pull/7462).

새 QA 원본은 `/home/vimkim/gh/cubrid-qahome-fetcher/runs/20260929-210608-1ec35f8`와 `20260929-210608-e1c3db1`이다. 기존 run과 원본 실행 로그는 수정하지 않았다. 보고서 작성·수집은 새로운 테스트 실행을 의미하지 않는다.
