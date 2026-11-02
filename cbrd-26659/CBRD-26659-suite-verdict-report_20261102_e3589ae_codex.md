# CBRD-26659 테스트 종류별 성공·실패·타임아웃 현황

자료 수집 기준은 2026-11-02, 최종 검토일은 2026-11-03, Asia/Seoul이다. 사용자와 QA·리뷰어가 "이제 실패하거나 통과하지 못한 테스트가 없는가"를 판단하기 위한 Work697 보고서다. OOS 관련 SQL·shell·shell_heavy·shell_perf·HA와 일반 CI의 medium, C++ 실행 근거를 대조했다. 새 테스트·벤치마크·CI는 실행하지 않았다.

**아직 전부 통과한 상태로 볼 수 없다.** HA의 마지막 전체 native 선택은 2 PASS·2 FAIL이다. 비활성 shell의 과거 실패 61개 중 고유 사례 2개만 현 Engine에서 native PASS를 확인했고 나머지 59개는 현재 native 판정이 없다. 실행 명령 종료 timeout 두 시도의 원인도 남아 있다. 정식 OOS performance TC는 편입·실행 근거가 없고, 최신 SQL 전체 자료는 집계 불일치로 검증이 거부됐다.

최신 일반 CI의 다섯 gha context는 SUCCESS다. 이는 그 실행이 선택한 사례의 CI 상태다. 비활성 사례, heavy·performance·HA의 별도 선택이나 자료 무결성까지 통과했다는 뜻은 아니다.

## 1. 현재 등록 수와 결과를 읽는 기준

아래 등록 수는 서로 다른 논리 TC 수다. 일반 저장소의 heavy·HA 보존 사본을 목적지의 같은 TC와 다시 더하지 않는다. SQL 파일·answer 한 쌍은 TC 하나다. CTest 실행 파일 수와 GoogleTest 함수 수는 이 단위에 더하지 않는다.

| 종류 | OOS 관련 등록 수 | 현재 선택 |
| --- | ---: | --- |
| SQL | 28 | 정규 28쌍, 비활성 0쌍 |
| 일반 shell | 95 | 일반 CI 활성 31개, 비활성 64개. 비활성은 과거 FAIL 61개와 장시간 PASS 3개 |
| shell_heavy | 38 | 별도 heavy 위치에서 활성 38개. 일반 저장소의 `disabled/heavy` 38개는 같은 TC |
| HA | 6 | 전용 HA 저장소에 활성 4개, 비활성 엔진 결함 재현 2개 |
| shell_perf | 식별된 정식 OOS 인도분 0 | Work544의 승인·구현·performance 편입이 남음 |
| Medium | OOS 전용 분모 미확정 | 전용 OOS 표식의 항목은 식별하지 못함. 일반 CI 전체 결과는 아래에 별도 기재 |
| C++ | 현재 실행 분모 미확정 | 현재 리비전의 전체 native unit 판정 자료를 확보하지 못함 |

SQL과 세 shell 계열의 고유 기능 TC는 **167개**, 그중 shell 계열은 **139개**다. 이 수는 등록 inventory이며 전부 실행했거나 통과한 수가 아니다. 과거 OOS cohort에는 `cbrd_27237_rollback_vacuum`도 들어 있다. `cbrd_26659` 이름 prefix만 검색하면 138개만 찾아 하나를 놓치므로, 비활성 manifest와 이관 목록을 함께 대조했다.

`미실행`은 명시된 선택에서 실행하지 않았음을 뜻한다. `미확인`은 현재 입력에 대한 충분한 판정 근거가 없음을 뜻한다. 과거 FAIL은 과거 관측으로 보존하며 현재 FAIL로 자동 이월하지 않는다. 반복 실행의 PASS나 다른 경로의 사본은 고유 TC 수를 늘리지 않는다.

## 2. 종류별 확보한 판정

각 행은 적힌 실행·선택만을 판정한다. 실행 시점과 TC 리비전이 달라 이 표의 PASS·FAIL을 하나의 전체 실행 결과로 합산하지 않는다. `0 기록`은 그 선택에서 timeout 판정이 기록되지 않았다는 뜻이다.

| 종류와 판정 대상 | 실행된 선택 | PASS | FAIL | Timeout | 남은 한계 |
| --- | ---: | ---: | ---: | --- | --- |
| OOS SQL, 마지막 개별 검증 자료 | 28 | 28 | 0 | 0 기록 | CI 41031622190 shard09, public `b038c424`. 최신 CI의 SQL 전체 집계는 별도로 거부됨 |
| OOS 일반 shell, 최신 일반 CI | 31 | 31 | 0 | 0 기록 | 비활성 64개는 이 선택 밖에 있음 |
| 비활성 과거 shell FAIL cohort | 61개 중 현재 native 검증 2개 | 2 | 나머지 현재 FAIL 수 미확인 | 아래 실행 명령 timeout 2시도 | 59개 현재 native 미확인. 이 중 policy helper 그룹 38개 |
| 비활성 장시간 shell | 현재 재검증 0개 | 과거 3 | 현재 미확인 | 현재 미확인 | `schema_sa`, `dml_transitions`, `large_keys` |
| shell_heavy, 마지막 전체 native | 38 | 38 | 0 | 0 기록 | TC `631e3fd`의 2026-10-29 qualification. 현재 `d5247632b` 전체 재실행을 뜻하지 않음 |
| shell_heavy, 현재 head 집중 검증 | AES committed crash 1 | 1 | 0 | 0 | 앞의 38개 중 같은 case의 AES 분기. 39번째 TC가 아님 |
| HA, 마지막 전체 native | 활성 4 | 2 | 2 | 전체 TC timeout 0 기록 | 비활성 결함 재현 2개와 전용 다중 호스트 job은 이 선택 밖에 있음 |
| shell_perf | 정식 OOS 인도분 실행 0 | 미확인 | 미확인 | 미확인 | 실행 0건을 PASS 또는 실패 0건으로 판정하지 않음 |
| Medium, 최신 일반 CI 전체 | 975 | 975 | 0 | 0 기록 | 전체 CUBRID medium이며 OOS 전용 975개가 아님 |
| C++ 전체 native unit | 현재 완전한 실행 자료 미확인 | 미확인 | 미확인 | 미확인 | 선언 수를 실행 PASS 수로 대체하지 않음 |

### SQL

공개 TC `b038c424`의 OOS 28개는 CI 41031622190 shard09에서 개별 PASS를 확인했다. 그 shard의 배정·완료·summary·JUnit 468개도 일치했다. 과거 실패했던 `cbrd_26659_oos_record_boundaries`, `cbrd_26659_oos_sql05_bigone`, `cbrd_26659_oos_sql09_lob_maxcols`는 답안 오류 번호 네 곳을 고친 뒤 native 3 PASS로 복원됐고 이 28개에 포함된다. [SQL 복원 보고서](CBRD-26659-sql3-restoration_20261030_b038c42_codex.md)가 범위와 원문을 보존한다.

현재 SQL testcase head도 같은 `b038c424`다. 다만 이번 최신 CI 수집은 SQL suite 전체 자료를 검증하지 못했으므로, 위 과거 개별 PASS를 최신 실행의 인증된 SQL 전체 집계로 바꾸지 않는다.

### 일반 shell과 비활성 사례

최신 일반 CI의 XML과 실제 활성 목록을 대조해 OOS 31개가 모두 PASS임을 확인했다. 비활성 64개는 일반 CI의 30 SKIP에 들어가는 사례가 아니다. 애초 선택 root 밖에 보존돼 있어 이 CI가 실행하지 않는다.

과거 FAIL 61개 중 현 Engine에서 고유 native PASS가 확인된 것은 `cbrd_26659_show_contract`와 `cbrd_26659_gap_ctas_cs` 두 개다. SHOW의 반복 검증, CTAS의 `ctas03`·`fixed02` 반복 성공을 새 사례로 더하지 않는다. 나머지 59개는 현재 native 판정이 없고, 그중 policy helper 누락 증상 그룹의 나머지 38개도 미검증이다. 과거 61개의 이름·리비전·증상은 [분류 보고서](CBRD-26659-shell61-classification_20261030_e3589ae_codex.md)에 있다. Helper 이동은 [policy](CBRD-26659-policy-helper-relocation_20261031_6334dc6_codex.md), [metadata](CBRD-26659-policy-metadata-relocation_20261102_41eae6a9c_codex.md), [TDE](CBRD-26659-tde-helper-relocation_20261102_work691_codex.md)의 검증 범위대로 적용한다.

`tde_crash_committed`·`tde_crash_undo` wrapper의 sibling 진입점 결합도 남아 있다. Helper가 선별 뒤 살아남는다는 검증이 wrapper 전체의 독립 실행이나 재활성화를 증명하지 않는다.

### Heavy

[Heavy 이전 보고서](CBRD-26659-shell-heavy-pr-context_631e3fd_codex.md)의 전체 native 결과는 38 PASS·0 FAIL·0 SKIP이며 각 case의 120초 제한에서 timeout을 관측하지 않았다. 현재 head는 `d5247632b`다. 이후 공용 helper 이동과 WAL 호출 경로 변경이 있었으므로 과거 전체 qualification과 현재 head의 실행 범위를 구분한다. 기존 38 PASS 근거를 취소하는 것은 아니며, 전체 38개를 현재 head로 다시 실행했다고 주장하지 않는다.

현재 head에서는 [TDE Work691](CBRD-26659-tde-helper-relocation_20261102_work691_codex.md)의 원문 committed crash를 AES 설정으로 실행했다. Owner 제외 선별 입력 35개, 1 PASS·11 assertion과 복구 전후 AES helper receipt를 확인했다. 이 한 건은 기존 38개에 포함되는 case의 추가 조건 검증이다. Heavy를 일반 CI가 실행했다는 근거로 쓰지 않는다.

### HA

HA 현재 head는 `ae2bcec1f6a68fb76e90c0a9d50fec4b3463ca51`다. 마지막 전체 native `ha-native-05-final`의 구현 입력 hash가 현재 구현과 일치한다. Commit 전에 준비된 입력을 실행했으므로 commit 자체를 당시 직접 checkout해 실행했다고 표현하지 않는다.

| 활성 HA case | 마지막 전체 native 결과 | 관측 |
| --- | --- | --- |
| `cbrd_26659_ha_async` | PASS | 해당 선택에서 통과 |
| `cbrd_26659_ha_failover` | PASS | 해당 선택에서 통과 |
| `cbrd_26659_ha_queue` | FAIL | 동시 트랜잭션 이후 master barrier UPDATE 실패 |
| `cbrd_26659_ha_replication` | FAIL | `key.locate`·`key.rekey`에서 master 연결 실패와 후속 기대값 불일치 |

Runner exit는 0이어도 XML과 artifact 검증에는 FAIL 2개가 있다. 이 둘의 원인은 미확정이다. 이전 선택·경로에서 PASS한 관측을 가져와 마지막 전체 선택의 FAIL을 지우지 않는다. [HA 이전·검증 보고서](CBRD-26659-oos-ha-suite-pr-context_ae2bcec_codex.md)에 시도별 차이가 있다. 1,200초 native testcase 제한과 내부 HA 대기를 구분하며, 전용 다중 호스트 HA job의 실행 근거는 확보하지 못했다.

### Performance와 C++

정식 OOS 성능 regression TC의 승인·performance 편입은 Work544에서 별도 관리한다. 고정 private `shell_perf` 트리의 경로·텍스트를 OOS, out-of-row, CBRD-26659·27785·27788 표식으로 조사했으나 인도된 OOS 항목을 식별하지 못했다. 이 검색과 Work544 pending 기록에 한정한 결과다. 이름·표식이 없는 TC까지 의미 분석한 결과는 아니다. 기존 [성능 수락 기준](../cbrd-27785/CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md)과 [실험 자료](../CBRD-27788/README.md)는 정식 `shell_perf` TC 실행·편입과 구분한다. 이 보고서는 새 성능 수치를 측정하거나 과거 수치로 회귀 PASS를 판정하지 않는다.

과거 C++ 인벤토리의 302개 GoogleTest 선언·29개 등록 바이너리는 [이전 리비전의 소스 수량](supplement-cpp-inventory-work456-20261021.md)이다. 당시 ticket01의 OOS C++ 실행 수는 0이었다. 현재 `e3589ae`의 `unit_tests/oos` tree는 그 이전 tree와 달라, 이를 현재 수량이나 전체 PASS로 전용하지 않는다. 현재 완전한 C++ native 실행 판정은 미확인이다. Medium 역시 표식으로 식별되는 OOS 전용 분모가 없으므로 일반 medium 전체 975개와 OOS testcase 수를 구분한다.

## 3. 실제 실패와 timeout의 종류

| 사례 | 판정 범위 | 남은 내용 |
| --- | --- | --- |
| `ha_queue`, `ha_replication` | 마지막 전체 HA native에서 FAIL 2개 | 최초 연결 실패의 원인 분석과 원래 기대값으로 재검증 |
| `ha_flush_boundary` | 별도 과거 엔진 결함 재현 FAIL | CBRD-27800의 slave OOS 손상 재현. 현재 HA 최종 4개 선택에는 미포함 |
| `ha_composite_key` | 별도 과거 엔진 결함 재현 FAIL | CBRD-27801의 applylogdb assertion과 후속 30초 barrier 대기 실패. 현재 HA 최종 선택에는 미포함 |
| `gap_ctas_cs`의 `ctas02` | 전체 native invocation timeout | TC 성공 산출물 뒤 130.013초에 명령 종료. 이후 `ctas03`은 정상 종료 PASS |
| `gap_ctas_cs`의 `fixed01` | 전체 native invocation timeout | TC 성공 산출물 뒤 130.157초에 명령 종료. 이후 `fixed02`는 정상 종료 PASS |
| `schema_sa`, `dml_transitions`, `large_keys` | 과거 장시간 PASS 3개 | 현재 리비전 재확인·분할·heavy 배치 판단 미완료 |

HA 활성 FAIL 2개와 비활성 엔진 결함 재현 2개는 서로 다른 선택의 결과다. 이를 "마지막 HA 실행 4 FAIL"로 합산하지 않는다. 두 연결 실패가 두 엔진 결함과 같은 원인이라는 근거도 없다. [HA 결함 분석](ci-replan/ha-queue.md)은 해당 재현의 Engine·관측 범위를 보존한다.

`ctas02`·`fixed01` 두 시도는 하나의 고유 TC에 관한 실행 명령 timeout이다. 준비·TC·정리 전체에 120초와 종료 유예 10초를 둔 실행이 끝나지 않은 것이며, testcase 자체의 assertion FAIL이나 testcase 실행 구간 timeout으로 바꾸어 세지 않는다. 이후 정상 종료가 앞선 종료 지연의 원인을 설명하지는 않는다. 과거 `large_keys`의 381.773초 PASS도 긴 실행 관측이며 그 자체가 timeout 판정은 아니다.

Metadata SHOW의 앞선 두 준비 환경 NOK와 CTAS의 첫 준비 실패도 각각의 원본 보고서에 남아 있다. 후속 정상 종료와 이전 실패 시도를 구분하며, 준비·관측 도구의 실패나 parser 음성 fixture를 새 제품 testcase FAIL 수로 더하지 않는다.

일반 CI의 옛 `cbrd_25977-16` 표기는 testcase 이름이 아니라 `cbrd_25977`의 assertion 16 실패였다. 최신 CI의 정규 경로 `shell/_40_guava/cbrd_25977/cases/cbrd_25977.sh`는 PASS다. 과거 worker 기대 `2,3,4`와 관측 `2,4` 차이의 원인 확정이나 수리 근거가 생긴 것은 아니다. 이 사례는 OOS 167개 cohort에 더하지 않는다.

## 4. 최신 일반 CI 전체 결과와 무결성 경고

**최신 SQL suite는 수집 무결성 오류로 인증하지 못했다.** 이 절은 부분적으로 검증된 자료에 대한 경고 보고이며 회귀·원인 귀속 결론을 내리지 않는다. [CI 41431239377 attempt1](https://github.com/CUBRID/cubrid/actions/runs/41431239377)은 GitHub에서 SUCCESS이고 다섯 gha context도 SUCCESS다.

| 일반 CI suite 전체 | 배정 | 실제 실행 | PASS | FAIL·ERROR | SKIP | 근거 판정 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `test_shell` | 3,521 | 3,491 | 3,491 | 0 | 30 | 완전한 summary·XML·raw hash 검증 |
| `test_medium` | 975 | 975 | 975 | 0 | 0 | 완전한 summary·XML·raw hash 검증 |
| `test_sql` | 전체 인증 보류 | 전체 인증 보류 | 전체 인증 보류 | 전체 인증 보류 | 전체 인증 보류 | shard01 workflow와 JUnit 수 불일치로 거부 |

Shell·medium의 미실행 배정 `unrun`은 각각 0이다. Shell의 30 SKIP은 이 CI가 실제로 skip으로 보고한 사례이며, 비활성 OOS 64개와 다르다. 이 선택의 실패·오류가 0이라는 사실을 suite 밖의 사례에 적용하지 않는다.

이번 실제 수집의 SQL shard01은 `shard.done` 배정 3,533개와 JUnit·summary의 3,531개가 다르다. Summary의 `fail:0`이나 GitHub SUCCESS를 신뢰해 이 차이를 무시하지 않았다. [기존 CTP 집계 분석](CBRD-26659-sql-count-discrepancy_20261030_run40837919358_codex.md)의 후속 수리·전체 자료 정합성 검증은 여전히 남는다.

`cubrid-ci 0.2.0 (dd290e9f7b9b, release)`로 상태 snapshot 한 번과 exact-head collection 한 번을 수행했다. 수집 종료값은 4이고 SQL 상태는 `collection_failed`, 오류는 `integrity/identity_or_integrity`다. 요청·종료 observation, command result, manifest와 shell·medium summary·raw index의 schema 및 hash·합계·입력 SHA를 검증했다. `report_mode.py` 결과는 `warning`, `regression_conclusions_allowed=false`, `comparison_scope=none`이다. 다른 endpoint나 이전 bundle로 실패한 SQL suite를 대체하지 않았다. 이번 보고서는 실패 귀속·회귀 비교를 하지 않으므로 merge-base 비교와 testcase-history 수집은 수행하지 않았다.

| Acquisition scope | 보존된 shard | 취득 실패 | 미시도 | 해석 |
| --- | ---: | ---: | ---: | --- |
| Medium | 1 | 0 | 0 | suite summary 검증 완료 |
| Shell | 50 | 0 | 0 | suite summary 검증 완료 |
| SQL | 10 | 0 | 0 | 원문 응답은 보존됐지만 이후 집계 무결성 검증에서 거부 |

Binary/core 수집은 요청하지 않았고 소비 byte는 0이다. 원문이 보존됐다는 사실은 SQL suite PASS 인증이 아니다.

## 5. 리비전과 재검토 근거

| 입력 | 고정 리비전 |
| --- | --- |
| Engine PR #8128 | `e3589ae42d42b04eb020e1ae43e165b01d31b12a` |
| Public SQL·medium | `b038c424b6a8d078671132e2369040493a5fc1f6` |
| 일반 private-ex | `01df2600ac75180812451462b5c044cfa56b732a` |
| Heavy private-ex | `d5247632b19a0905eefadee6ce39a8e1ab667c9f` |
| HA private | `ae2bcec1f6a68fb76e90c0a9d50fec4b3463ca51` |

Collector snapshot은 2026-11-02 23:36:22 KST, 종료 command는 23:38:33 KST다. Collector가 검증한 shell·medium shard 모두 Engine `e3589ae`와 각 TC revision에 대응한다. 과거 full heavy는 `631e3fd3cbc202cec45b56ae6cec7e4f1c86e2f1`, 과거 SQL 개별 검증도 위 public `b038c424`에 묶여 있다. HA는 현재 구현 입력 hash와 마지막 native 입력을 대조했다. 문서 작성 전 조회한 네 TC PR은 OPEN이다. PR OPEN과 실행 PASS, 실제 리뷰·병합은 각각 다른 상태다.

[재검토 도구](tools/verify-suite-status-report.py)는 현재 inventory 분모, cohort 중복, collector observation·schema·raw hash와 shell·medium XML 합계, OOS 활성 31개의 개별 PASS, HA 선택의 2 PASS·2 FAIL과 원문 hash를 대조한다. SQL 무결성 거부와 warning gate도 그대로 요구한다. 테스트나 CI를 새로 실행하지 않는다.

```bash
python3 cbrd-26659/tools/verify-suite-status-report.py \
  --evidence /home/vimkim/temp/cbrd26659-suite-status-hax5uc3p \
  --output /home/vimkim/temp/cbrd26659-suite-status-hax5uc3p/review-result-new.json
```

현재 원문과 분석 중간 자료는 `/home/vimkim/temp/cbrd26659-suite-status-hax5uc3p`에 보존한다. `regular`, `heavy`, `ha`, `perf`의 `records.json`은 사례별 상세 근거다. `verified-suite-status-final.json`과 `report-mode-assessment.json`은 이번 검증 결과다. Collector 원본은 반환된 `output_dir` 아래에 있으며 `matching-observation.txt`가 이번 요청과 정확히 일치하는 observation을 가리킨다. Raw log·inventory·worker 초안·transcript는 Git에 넣지 않는다. Git에는 이 보고서, 색인 갱신, 이를 재검토하는 데 필요한 검증 도구만 남긴다.

남은 실행·수리·운영·리뷰 항목은 [TODO 체크리스트](CBRD-26659-todo-checklist_20261029_codex.md)를 따른다. 이 보고서는 TC·Engine을 수정하거나 실패를 해결한 작업이 아니며 Work456·Work544 전체를 완료 처리하지 않는다.
