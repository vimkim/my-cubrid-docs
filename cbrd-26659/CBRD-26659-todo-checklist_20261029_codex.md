# CBRD-26659 TODO checklist

작성 기준은 2026-10-29, 갱신 기준은 2026-11-03, Asia/Seoul이다. [현황보고](CBRD-26659-status-report_20261029_e3589ae_codex.md)를 기준으로 남은 작업을 하나씩 실행하고 결과를 기록한다. 초기 heavy 이관·검증과 후속 재현 결과를 반영하며, 실제 TC PR 병합과 남은 실패·timeout 처리는 미완료다.

체크 표시는 해당 항목의 산출물과 검증 근거가 확보되었음을 뜻한다. 로컬 준비, PR 게시, 실제 병합은 각각 구분한다. 성능 비교는 이 체크리스트의 완료 조건에 포함하지 않는다.

## 1. PASS한 shell TC 38개를 shell_heavy로 이관

대상은 Engine `e3589ae`·private-ex TC `479035a45`의 [CI 40643373124](https://github.com/CUBRID/cubrid/actions/runs/40643373124)에서 PASS했고 20초를 초과한 비HA TC 38개다. 현재 원본은 [PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)의 `02d023932`다. 당시 관측 시간은 21.218초부터 53.566초까지다.

- [x] 38개 원본 경로와 hash를 현재 TC 파일에 대조한다.
- [x] 이관 목적지가 `cubrid-testcases-private-ex/shell_heavy`임을 확인한다.
- [x] 상대 경로·native helper를 포함한 공용 의존 파일 34개의 정적 범위를 조사한다.
- [x] 별도 heavy PR의 head·base와 기존 PR #4365의 일반 CI 제외 방식을 확정한다.
- [x] heavy에 TC·fixture·공용 helper를 구성하고 원문·mode 일치를 확인한다.
- [x] 기존 일반 shell에는 OOS 진입점 31개만 남도록 38개를 별도 보존 경로로 이동한다.
- [x] 과거 실패·장시간 비활성 66개와 HA 제외 4개, 재현에 필요한 기존 helper·fixture를 보존한다.
- [x] 일반·heavy 실행 탐색 결과가 각각 31개·38개이고 중복·누락이 없는지 확인한다.
- [x] 대표 TC 1개를 먼저 native runner로 실행하고 판정·정리를 확인한다.
- [x] 이관한 전체 38개를 직렬 실행하고 각 TC에 120초 제한을 적용한다.
- [x] 실행 목록·완료 목록·assertion·summary·XML을 대조하여 PASS·FAIL·시간 초과를 기록한다.
- [x] 검증 결과에 맞는 별도 PR 본문과 게시 대상을 파일로 준비한다.
- [x] 검토한 게시 범위의 승인을 받은 뒤 heavy draft PR과 기존 PR의 변경을 게시한다.
- [x] 일반 CI 제외 검증을 1회 실행하고 종료 결과를 기록한다. 실패 시 임의 수정·재실행하지 않는다.
- [x] SQL shard 01의 workflow 처리 3,533개와 JUnit·summary 3,531개 차이를 조사한다. [분석](CBRD-26659-sql-count-discrepancy_20261030_run40837919358_codex.md)에서 CTP 중첩 디렉터리 집계 누락을 실제 코드로 재현했다.
- [ ] CTP 집계·JUnit 순회를 별도 수정한 뒤 원래 두 TC의 실행 근거와 SQL 전체 자료 정합성을 확인한다. 기존 SQL 수집 실패와 전체 PASS 미인증 상태는 유지한다.
- [ ] QA 담당자와 heavy 실행 위치·주기·담당을 정하고 실제 TC PR 검토·병합을 확인한다.

38개 이관에 과거 실패 61개, 이전부터 비활성인 PASS 3개, HA TC를 섞지 않는다. 기존 CUBRID `gha-ci`의 suite 목록에는 `shell_heavy`가 없으므로 일반 CI에서 제외한 사실과 heavy 실행 경로가 확보된 사실을 구분한다.

## 2. 과거 실패 TC를 재현하고 원인을 분류

- [x] 과거 SQL FAIL 3개와 shell FAIL 61개의 전체 목록·원본 경로·관측 리비전을 확보한다.
- [x] SQL `cbrd_26659_oos_record_boundaries`를 재현하고 최초 실패와 원인을 기록한다.
- [x] SQL `cbrd_26659_oos_sql05_bigone`을 재현하고 최초 실패와 원인을 기록한다.
- [x] SQL `cbrd_26659_oos_sql09_lob_maxcols`를 재현하고 최초 실패와 원인을 기록한다.
- [x] SQL 3개의 원본 NOK를 TC 답안의 오류 번호 불일치로 분류하고 [현재 재현 근거](CBRD-26659-disabled-sql-reproduction_20261030_e3589ae_codex.md)를 연결한다.
- [x] 답안 3개의 오류 번호 4곳을 현재 상수에 맞추고 실제 native 3 PASS·정리를 확인한 뒤 정규 경로에 복원한다. [복구 보고서](CBRD-26659-sql3-restoration_20261030_b038c42_codex.md)에 기존 감시의 실제 120초 중단 검증과 이전 설명 정정을 기록했다.
- [x] 복원 TC push 뒤 한 번 시작한 [CI 41031622190](https://github.com/CUBRID/cubrid/actions/runs/41031622190)의 FAILURE와 검증 범위를 기록한다. 복원 3개는 shard 09에서 PASS로 관측됐다. Shell 1건 실패와 SQL 전체 집계 불일치는 남아 있으며 추가 수정·push·재실행은 하지 않았다.
- [ ] CI 41031622190의 `cbrd_25977-16` 실패를 별도 분석한다. 기대한 worker `2·3·4`와 관측 `2·4`의 차이는 확인했으나 원인은 미확정이다. 사람의 다음 지시 후 진행한다.
- [x] shell 61개를 관측한 공통 실패 증상으로 묶되 각 TC의 개별 결과를 유지한다. [분류·첫 대표 보고서](CBRD-26659-shell61-classification_20261030_e3589ae_codex.md)에 원본 리비전과 사례별 61개 목록을 기록했다. 인과 순서와 원인 확정은 별도다.
- [x] 첫 대표 `show_contract`를 원문 그대로 현재 native 환경에서 실행한다. 1 PASS·0 FAIL·0 SKIP과 8 assertion·정리를 확인했다. 과거 `CUBRID_TMP` 미정의 오류는 재현되지 않았으며 엔진 수정 효과로 귀속하지 않는다.
- [x] 가장 큰 39개 `policy_ddl.sh` 누락 그룹의 대표를 재현해 파일 배치·정리·선행 TC 영향과 policy assertion을 구분한다. [조사 보고서](CBRD-26659-policy-helper-pruning_20261030_e3589ae_codex.md)에 원본 shard 목록의 helper 삭제 재현과 현재 `gap_ctas_cs` 1 PASS를 기록했다. 당시 이미지 원본이 없어 과거 원인은 강한 추론이며, 전체 39개 원인 확정은 아니다.
- [x] 공용 policy helper를 개별 TC의 `cases` 밖으로 옮기고 모든 호출자·shard 선별 후 입력을 검증한다. [수리·검증 보고서](CBRD-26659-policy-helper-relocation_20261031_6334dc6_codex.md)에 일반 7곳·heavy 복사본 1곳의 경로 변경, 수정 전 helper 삭제·수정 후 보존 대조, 선별 후 원문 대표 1 PASS를 기록했다. Checker bytes·mode·assertion과 일반 31개·heavy 38개 선택은 유지했다.
- [x] 다른 TC의 `cases` 아래 `policy_metadata.sh`·`tde_observe.sh` 의존성을 실제 scenario 호출별로 확인하고 후속 수리 범위를 정한다. [Work654 감사](CBRD-26659-helper-dependency-audit_20261031_6334dc6_codex.md)에서 metadata 소비자의 비활성 상태, AES 조건부 TDE 호출, 미호출 lifecycle 정의와 wrapper의 별도 sibling 의존성을 구분했다. 실제 선별 24회·합성 parser 대조이며 TC 실행이나 수리 완료는 아니다.
- [x] 일반 metadata helper를 `oos_common`으로 이동하고 호출 경로 4곳을 정리한다. [Work662 보고서](CBRD-26659-policy-metadata-relocation_20261102_41eae6a9c_codex.md)에 byte-identical 이동, parser 독립 기대값 17개, 같은 기본 gate의 수정 전 네 누락·수정 후 생존, 선별 후 입력 64개의 원문 SHOW 1 PASS를 기록했다. 준비 환경 NOK 두 시도는 보존하며 원래 parser·assertion·비활성 선택을 유지했다. 정규 TC head `41eae6a9c`에 게시했다.
- [x] Metadata 수리 게시 후 한 번 시작한 [CI 41394321292](https://github.com/CUBRID/cubrid/actions/runs/41394321292)의 SUCCESS와 다섯 gha context SUCCESS를 기록한다. Plan의 private `41eae6a9c`·public `b038c424`를 확인했다. 긴 runner 대기 뒤 사용자가 지시한 추가 3시간 창 안에 종료했다. TC Merge Gate context는 표시되지 않으며 두 TC PR은 OPEN이다. SQL 전체 정합성 미인증과 실제 TC 리뷰·병합은 별도다. 추가 TC·source 수정·push·재실행은 하지 않았다.
- [x] 일반·heavy TDE helper와 AWK를 함께 공용 위치로 옮기고 JSON source·모든 호출 경로를 정리한다. [Work691 보고서](CBRD-26659-tde-helper-relocation_20261102_work691_codex.md)에 동일 gate의 수정 전 7개 owner 제외 누락·수정 후 실제 선별 18회 통과, 네 명령의 독립 parser 104쌍, 선별 후 원문 committed AES crash 1 PASS·11 assertion·최종 commit 대응을 기록했다. 일반 `01df2600a`·heavy `d5247632b`에 게시했고 활성·비활성 선택과 assertion은 유지했다. Undo·일반 비활성 소비자 전체의 native 검증으로 확대하지 않는다. 암호화 wrapper의 별도 sibling 의존성은 여전히 미해결이다.
- [x] TDE 수리 게시 후 한 번 시작한 [CI 41431239377](https://github.com/CUBRID/cubrid/actions/runs/41431239377)의 SUCCESS와 다섯 gha context SUCCESS를 기록한다. Plan의 Engine `e3589ae`·public `b038c424`·private `01df2600a`를 확인했고 최종 job은 성공 71개·skip 1개다. TC Merge Gate context는 표시되지 않으며 자동 TC PR 두 개와 heavy PR은 OPEN이다. SQL 전체 정합성 미인증과 실제 TC 리뷰·병합은 별도다. 추가 TC/source 수정·push·CI 재실행은 하지 않았다.
- [x] Helper 수리 게시 후 한 번 시작한 [CI 41175186516](https://github.com/CUBRID/cubrid/actions/runs/41175186516)의 SUCCESS와 5개 gha context SUCCESS를 기록한다. Plan에서 public `b038c424`·private `6334dc6`을 확인했다. 이전 SQL 전체 집계 미인증과 TC PR 검토·병합은 별도다. 추가 TC 수정·push·CI 재실행은 하지 않았다.
- [ ] `ctas02`의 TC 완료 후 native 명령 timeout 원인을 추가 분석한다. 결과 파일은 성공이지만 130.013초에 exit -9로 끝나 미완료다. 추가 관측 `ctas03`은 56.908초에 정상 종료해 원래 지연을 재현하지 못했다. Work647의 선별 후 `fixed01`에서도 종료 지연을 관측했고 `fixed02`는 40.879초에 정상 종료했다. 첫 실패를 미완료로 유지하며 원인 확정이나 runner 수리 credit은 주지 않는다.
- [x] policy helper 그룹 잔여 38개를 Engine `e3589ae`·TC `01df2600a`에서 직렬 검증한다. [Work699 보고서](CBRD-26659-policy38-native_e3589ae_20261103_work699_codex.md)에 37 PASS·1 FAIL·0 TIMEOUT과 전부의 종료·정리를 기록했다. REPARTITION의 두 정책은 `root_has_no_oos`에서 실패하며 Engine·TC 귀속은 미확정이다.
- [x] REPARTITION의 root_has_no_oos 실패를 조사하고 정책별 owner 증거를 확보한다. [Work702 진단](CBRD-26659-repartition-root-oos_e3589ae_20261103_work702_codex.md)은 SA records0·Has1과 최소 red/green을 통해 기존 root의 파일 연결을 즉시 없애야 한다는 TC 조건의 범위 오류로 분류했다. 원래 TC는 아직 FAIL이다.
- [ ] REPARTITION의 기존-root oracle 수정안을 검토하고 원래 두 정책의 전체 TC를 재검증한다. 값·실제 destination ownership 검사는 유지하고 다른 partition 시나리오의 조건을 일괄 삭제하지 않는다.
- [x] 기존 61개 분류에서 policy 그룹 밖의 잔여 21개를 원문 실행하고 판정한다. [Work704 보고서](CBRD-26659-remaining21-native_e3589ae_20261103_work704_codex.md)에 Engine `e3589ae`·TC `01df2600a`의 4 PASS·16 FAIL·외부 명령 TIMEOUT 1개와 초기 별도 INCONCLUSIVE 시도를 기록했다. 미착수는 0개지만 timeout TC의 정상 완료는 미확인이다. 서로 다른 리비전의 대표와 이 결과를 한 번의 전체 suite 실행으로 합산하지 않는다.
- [ ] Work704의 assertion·controller FAIL 14개를 현재 관측별로 분석하고 Engine·TC·환경 귀속을 확인한다. 기존 미정의 변수 증상을 현재 원인으로 자동 이월하지 않는다.
- [ ] TDE committed·undo wrapper 두 개의 누락 sibling 진입점 의존성을 수리하고 원래 AES crash 검증에 도달하는지 확인한다. Work704의 두 FAIL은 본래 crash 검증에 도달하지 못했다.
- [ ] `schema_rewrites_sa`의 외부 120초 invocation deadline을 분석하고 정상 완료 근거와 장시간 실행·분할 필요성을 확인한다. Work704는 exit 124·123.322초이며 native testcase 자체 timeout 판정은 미확인이다.
- [ ] `serialized_chunks`의 PASS와 별도로 `cubrid.conf.org` 누락 framework 복원 진단을 확인한다. Disposable 시도의 프로세스·namespace 정리와 framework 설정 복원은 구분한다.
- [ ] 각 실패를 엔진·TC·환경 문제 또는 원인 미확정으로 분류하고 근거를 연결한다.
- [ ] 확인한 엔진 결함에 후속 이슈와 재현 TC를 연결한다.
- [ ] TC 문제는 올바른 기대값을 유지하여 수정하고 PASS·자원 정리를 확인한다.
- [ ] 실패가 해결된 TC의 재활성화 여부와 일반·heavy 실행 위치를 정한다.

과거 FAIL을 현재 리비전의 FAIL로 단정하지 않는다. 전체 목록은 현황보고의 [실패 TC 현황](CBRD-26659-status-report_20261029_e3589ae_codex.md#3-실패-tc-현황)에 연결되어 있다.

2026-10-30 Work625의 Engine `e3589ae`·public TC `45e21ad` 원본 재현 판정은 0 PASS·3 NOK다. 답안의 `Error:-1384`와 현재 `Error:-1388` 차이 4곳 외에는 실제 출력이 바이트 단위로 일치한다. 당시 답안 수정·재활성화·게시는 하지 않았다. 이후 Work634에서 네 오류 번호를 수정해 실제 3 PASS를 확인하고 public TC `b038c424`로 정규 28쌍·비활성 0쌍 상태를 게시했다. 기존 감시는 부분 시작 로그를 관측했으며, 합성 제어에서 실제 120.046초 중단을 검증했다. 완료 신호라고 해석한 이전 설명은 정정했다. CI 41031622190은 FAILURE이며 shell 3,490 PASS·1 FAIL·30 SKIP, medium 975 PASS다. SQL shard 09의 OOS 28개·복원 3개는 PASS로 관측됐으나 SQL 전체는 shard 01의 3,533/3,531건 불일치로 검증 보류다.

## 3. 이전부터 비활성인 PASS 3개와 2분 초과 TC를 처리

- [ ] `cbrd_26659_schema_sa`의 과거 PASS 81.389초를 현재 리비전에서 확인하고 heavy 이관 여부를 정한다.
- [ ] `cbrd_26659_dml_transitions`의 과거 PASS 101.085초를 현재 리비전에서 확인하고 heavy 이관 여부를 정한다.
- [ ] `cbrd_26659_large_keys`의 단계별 진행을 관측한다. 과거 결과는 381.773초 PASS다.
- [ ] 120초에 도달한 TC의 마지막 단계·실행 명령·프로세스·서버 오류 로그를 확보하고 별도 정리 결과를 기록한다.
- [ ] 정상 장시간 실행, 분할 대상, 엔진 결함, TC 결함 또는 원인 미확정으로 분류한다.
- [ ] 분할 대상은 독립 실행·기대값·정리를 유지하는 TC로 나누고 각각 검증한다.
- [ ] 긴 실행 자체가 필요한 TC는 필요성·실행 주기·담당과 검증 결과를 명시한다.

## 4. HA draft PR의 남은 실패와 엔진 후속 이슈를 확인

- [x] [HA PR #1666](https://github.com/CUBRID/cubrid-testcases-private/pull/1666)에 활성 4개와 비활성 재현 2개를 게시한다.
- [x] 최종 native 결과 2 PASS·2 FAIL과 전용 다중 호스트 HA job 미실행 상태를 기록한다.
- [ ] `ha_queue`의 master barrier UPDATE 연결 실패 원인을 분석한다.
- [ ] `ha_replication`의 master 연결 실패와 이후 기대값 불일치 원인을 분석한다.
- [ ] [CBRD-27800](https://jira.cubrid.org/browse/CBRD-27800)의 record buffer 재사용 결함 수정 후 원래 재현 TC로 확인한다.
- [ ] [CBRD-27801](https://jira.cubrid.org/browse/CBRD-27801)의 복합 기본 키 UPDATE 결함 수정 후 원래 재현 TC로 확인한다.
- [ ] QA와 HA 실행 환경·검토 범위를 정하고 대상 PR의 검토·병합을 확인한다.

연결 실패의 원인을 위 두 엔진 결함으로 단정하지 않는다.

## 5. 커버리지 검토와 이슈 완료

- [ ] [피드백별 TC 대응표](CBRD-26659-feedback-testcase-coverage-report_20261027_codex.md)와 요구사항별 실행 근거를 최종 대조한다.
- [ ] 정책 구문·SHOW·유틸리티, 사용자 연산과 `HAS_OOS`, C++ 내부 계약, 경계·limit+1, 저장 효율·회수·단편화, 큰 PK·UNIQUE·FK의 남은 공백과 후속 처리 범위를 확인한다.
- [ ] 활성 PASS, 비활성 FAIL, 시간 초과, 미실행·원인 미확정 항목을 구분하여 QA·리뷰어에게 전달한다.
- [ ] 실제 실행 선택과 분석 결과에 맞게 PR 본문·JIRA·현황보고를 갱신한다.
- [ ] 대상 TC PR의 리뷰 승인과 실제 merge commit을 기록한다. 미해결 항목은 리뷰어가 수락한 후속 이슈를 연결한다.
- [ ] 위 근거로 CBRD-26659의 완료 범위를 확인한다. PR OPEN이나 로컬 PASS만으로 완료 처리하지 않는다.

## 실행 기록

| 날짜 | 작업 | 결과와 다음 단계 |
| --- | --- | --- |
| 2026-10-29 | 현황보고와 첫 이관 대상 확인 | 38개는 일반 shell에 남아 있다. helper 의존성을 보존하는 별도 heavy PR 준비를 시작했다. |
| 2026-10-29 | 이관 구성과 정적 검증 | 로컬에서 heavy 38개·지원 파일 34개를 구성하고, 기존 38개를 `disabled/heavy`로 보존했다. 일반 31개와 기존 제외 70개를 포함한 원문·mode 검사는 PASS다. 게시 전 상태다. |
| 2026-10-29 | 대표 TC 검증 | Engine `e3589ae` optdebug, 격리한 native 실행에서 새 heavy 위치의 `utility_sa`가 1 PASS·0 FAIL·0 SKIP이다. 전체 38개는 TC당 120초 제한으로 직렬 검증 중이다. |
| 2026-10-29 | 전체 heavy 검증과 게시 준비 | 동일 Engine의 격리한 native 전체 실행이 38 PASS·0 FAIL·0 SKIP으로 종료했다. 모두 120초 안에 완료했고 실행·완료 목록과 summary·XML이 일치한다. 로컬 이관 준비는 완료했으며 PR 게시·CI·리뷰·병합은 남아 있다. |
| 2026-10-29 | PR 게시와 일반 CI 시작 | 승인 후 [heavy draft PR #4627](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4627)을 생성하고 기존 [PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)에 제외 커밋·본문을 게시했다. 전체 [CI 40837919358](https://github.com/CUBRID/cubrid/actions/runs/40837919358)을 1회 시작했으며 종료 결과를 기다린다. |
| 2026-10-29 | 일반 CI 종료와 증거 검증 | 같은 CI가 SUCCESS로 종료했다. Build debug·release와 shell·SQL·medium의 5개 context가 모두 SUCCESS다. 증거 검증은 shell 3,491 PASS·0 FAIL·30 SKIP, medium 975 PASS·0 FAIL·0 SKIP이다. SQL은 GitHub 성공이지만 shard 01의 workflow 3,533개와 JUnit·summary 3,531개가 달라 수집기가 무결성 오류로 거부했다. SQL 전체 PASS 건수의 검증 완료는 보류하며 추가 수정·재실행은 하지 않았다. |
| 2026-10-30 | SQL 2건 집계 차이 조사 | `cbrd-27556`의 두 결과 행을 식별했다. 실제 CTP 코드에서 직접 TC와 하위 TC가 공존할 때 합계·JUnit이 하위 TC를 누락하는 현상을 재현했다. 구조만 바꾼 대조군은 모두 집계된다. 조사 항목은 완료했으나 CTP 수리·원래 두 TC의 독립 실행 확인·SQL 전체 정합성 검증은 남았다. CI 재실행이나 엔진·TC·CTP 수정은 하지 않았다. |
| 2026-10-30 | 비활성 SQL 3개 현재 재현·원인 분류 | 원본 입력·답안의 native 결과는 3 NOK이며 모두 TC 시간 120초 미만이다. 같은 오류 상수의 과거 번호 `-1384`와 현재 `-1388` 차이 총 4곳이 전부임을 확인했다. 준비 실패는 별도 보존했다. 답안 수정과 실제 PASS 검증·재활성화는 남아 있다. |
| 2026-10-30 | SQL 3개 수정·검증·복원 | 오류 번호 4곳을 고친 뒤 원래 SQL로 native 3 PASS·0 FAIL·0 SKIP을 확인했다. 정규 28쌍·비활성 0쌍으로 복원해 PR #3688의 `b038c424`에 게시했다. 기존 감시는 실제 120초 중단에 성공했으며 완료 로그부터 시작한다는 이전 설명을 정정했다. CI 41031622190은 1회 실행 후 FAILURE다. 복원 3개는 CI에서도 PASS로 관측됐으나 `cbrd_25977-16` 실패와 SQL 전체 집계 정합성 문제는 남았다. 추가 수정·재실행은 하지 않았다. |
| 2026-10-30 | shell 61개 분류와 첫 대표 재현 | Work637에서 서로 다른 과거 두 실행의 61개를 사례별로 보존했다. 43개는 경로가 명시된 shell 파일 누락, 5개는 `CUBRID_TMP` 미정의 증상을 포함한다. 원문 `show_contract`는 현재 native 1 PASS·0 FAIL·0 SKIP이며 전체 명령 45.572초에 종료했다. 별도 명령 120초 제한은 준비·TC·정리를 포함하고 10초 종료 유예를 둔다. 나머지 60개 현재 실행과 근본 원인 확정은 남았으며 TC·엔진·CI는 바꾸지 않았다. |
| 2026-10-30 | policy helper 39개 그룹 조사와 대표 재현 | Work640에서 과거 Git의 helper 존재와 원본 shard 13 목록에 따른 삭제·보존 대조를 확인했다. 실제 과거 이미지 bytes는 미확보여서 선별 시 삭제는 강한 추론이다. `ctas01`은 준비 실패, `ctas02`는 성공 TC 결과 뒤 전체 명령 timeout, `ctas03`은 원문 `gap_ctas_cs`의 native 1 PASS다. 27개 TC assertion·26개 controller 검사·정리를 확인했다. 원래 timeout 원인은 미확정이다. 그룹 38개, 전체 과거 shell 중 59개 현재 검증이 남았다. 수리·재활성화·CI 재실행은 하지 않았다. |
| 2026-10-31 | 공용 policy helper 이동과 선별 후 대표 검증 | Work647에서 일반 7곳·heavy 1곳을 새 공용 위치로 전환하고 동일 checker를 이동했다. 실제 keep의 수정 전 삭제·수정 후 보존을 검증했다. Native `fixed01`은 성공 TC 결과 뒤 전체 timeout으로 미완료이고 `fixed02`는 전체 40.879초의 1 PASS다. 일반 `6334dc6`·heavy `81e6072`를 각 TC PR head에 게시했다. CI 41175186516은 1회 실행 후 SUCCESS이며 5개 gha context도 모두 SUCCESS다. SQL 전체 증거 정합성과 TC PR 검토·병합은 별도다. 비활성 TC 복원·나머지 38개 실행·종료 지연 원인 확정은 남았다. |
| 2026-10-31 | 남은 공용 helper 의존성 감사 | Work654에서 metadata·TDE 실제 scenario 분기와 전이 의존성을 조사했다. 복사 fixture의 실제 선별 24회에서 owner 제외 11개는 helper 누락·parser exit 127, owner 선택 대조 13개는 보존·exit 0이다. AWK·JSON 누락 대조도 실패를 확인했다. Metadata 일반 이동을 먼저, TDE 일반·heavy 이동을 다음 단위로 제안했다. TC·Engine·CI는 바꾸거나 실행하지 않았으며 수리·대표 native 검증은 남았다. |
| 2026-11-02 | Metadata helper 이동과 선별 후 SHOW 검증 | Work662에서 일반 helper와 호출 인자 네 곳을 이동하고 원래 parser·선택·assertion을 유지했다. 독립 parser 17개와 실제 선별 gate의 수정 전 실패·수정 후 PASS, 입력 64개의 원문 SHOW 1 PASS를 확인했다. 앞선 두 준비 환경 NOK를 보존하고 실제 runner의 tmp 경로를 짧게 구성했다. 정규 TC `41eae6a9c`를 게시했고 한 번 실행한 CI 41394321292와 다섯 gha context는 SUCCESS로 종료했다. TDE 이동·재활성화·나머지 TC 현재 검증과 사람의 TC PR 리뷰·병합은 남는다. 추가 TC·source 수정·push·CI 재실행은 하지 않았다. |

[신규 heavy PR 본문](CBRD-26659-shell-heavy-pr-body_631e3fd_codex.md)과 [기존 PR #4365 갱신 본문](CBRD-26659-shell-heavy-exclusion-pr-body_a229e19_codex.md)은 검토·승인한 내용 그대로 게시했다. Heavy import `631e3fd`와 일반 CI 제외 `a229e19`의 원격 head를 확인했다. [게시 범위와 검증 기록](CBRD-26659-shell-heavy-pr-context_631e3fd_codex.md)에 본문 식별값과 CI 경과를 보존한다.

정적 검증은 [이관 대조 스크립트](tools/verify-heavy-transfer.py)로 다시 실행할 수 있다. `--regular`에는 기존 PR checkout, `--heavy`에는 별도 heavy PR checkout을 전달한다. 스크립트는 고정된 원본 커밋 `02d023932`와 실제 파일을 비교한다. 정적 대조는 실행 PASS나 heavy의 정기 실행을 증명하지 않는다.
