# CBRD-26659 policy 그룹 밖 잔여 shell 21개 native 검증

작성일은 2026-11-03, Asia/Seoul이다. OOS 작성자와 TC 리뷰어가 과거 shell FAIL 중 마지막 미검증 21개의 현재 결과와 후속 조치를 판단하도록 작성했다. Work704는 원문 실행·판정·증거 확보이며 상위 Work456의 전체 완료와 구분한다.

**21개 원문 실행의 판정은 4 PASS·16 FAIL·1 TIMEOUT·0 SKIP이며 미착수는 0개다.** 16 FAIL은 assertion·controller 실패 14개와 sibling 진입점 누락으로 본래 crash 검증에 도달하지 못한 wrapper 2개다. TIMEOUT 1개는 외부 native invocation deadline이며 TC의 정상 완료를 확인한 것이 아니다. 첫 전체 shell 관측 1개는 별도 INCONCLUSIVE 시도로 보존한다.

20개 완료 시도의 runner exit는 0이고 timeout 시도는 124다. Focused verifier는 PASS 4개만 0이며 나머지 17개는 1이다. 모든 시도에서 작업 소유 프로세스와 관측 namespace holder의 종료를 확인했고 최종 생존 검사도 0이다. **증거 검증기 PASS는 21개 TC의 전체 PASS를 뜻하지 않는다.**

## 모집단과 리비전

[과거 실패 61개](CBRD-26659-shell61-classification_20261030_e3589ae_codex.md)에서 앞선 `show_contract`·`gap_ctas_cs` 두 대표와 [Work699](CBRD-26659-policy38-native_e3589ae_20261103_work699_codex.md)의 38개를 제외한 21개다. Work699의 REPARTITION FAIL은 이미 실행한 사례로 제외한다. 해당 원인 조사는 Work702에서 다루며 이번 실행 대상에서 제외했다. 이번 21개는 이전 shell_heavy 이관 38개와 별도 집합이며 `cbrd_27237_rollback_vacuum`도 포함한다.

| 입력 | 고정 값과 범위 |
| --- | --- |
| Engine | `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, PR #8128의 OptDebug producer |
| TC | `01df2600ac75180812451462b5c044cfa56b732a`, private-ex PR #4365의 `tc/pr-8128` |
| Runtime 자산 | Work699의 보존 `seed`를 별도로 복사했다. 실행마다 설치·CTP·HOME·registry·TMP·cache·slot root를 분리했다. |
| Source/install 확인 | 매 시도에서 commit 일치 preflight와 기존 producer의 runtime fingerprint 6개를 확인했다. Commit mismatch 예외를 사용하지 않았다. |
| testkit | 설치 바이너리 SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, version `cubrid-testkit dev` |
| CTP 자산 | Work699가 보존한 `9c62858b10005d721546cc007be260844033b9e9` 및 당시 수정 snapshot이다. 현재 CTP checkout의 새 상태로 바꾸지 않았다. |

TC Git 객체의 전체 `shell/` 13,576개 입력과 선택한 비활성 진입점 21개를 합한 13,597개를 보존했다. 선택 진입점만 원래 `shell/.../cases/<name>.sh` 위치로 투영했다. 다른 비활성 진입점을 추가 복원하지 않았고, 기대값·assertion·helper bytes를 바꾸지 않았다. 실제 TC 저장소의 활성·비활성 상태도 유지했다.

## 첫 전체 shell 시도와 실행 범위 조정

첫 시도 `/home/vimkim/temp/w21-2vhMkkum/a01`은 전체 shell scenario와 기대 목록 한 건을 사용했다. 실제 선택·실행은 `alt_stub_duplicate` 한 건이었지만, 실행기는 선택 밖의 macro SKIP 21개도 summary·XML에 포함했다. XML은 22개였고 strict focused verifier가 `total case count is 22, expected 1`로 거부했다. 대상 TC 자체의 XML은 FAIL이다. 이 시도를 통과로 바꾸거나 삭제하지 않았다.

새 root `/home/vimkim/temp/w704-rjVY4qVI`에서 전체 입력을 그대로 보존하고 scenario만 요청 TC들이 있는 `shell/_40_guava`로 좁혔다. Macro 설정·원문·기대값·timeout은 유지했다. 같은 첫 TC를 새 시도로 확인한 뒤 나머지 20개를 직렬 실행했다. 초기 한 시도와 이후의 고유 21개 결과를 중복 TC로 합산하지 않는다.

## 실행과 판정

각 시도는 `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <attempt>/conf/shell.conf`를 사용한다. 한 slot, `scenario_disk=on`, exact file selection과 file feedback이며 update·retry·continuation·case patch는 껐다. Native testcase 제한은 120초이며 외부 native invocation도 120초, 종료 유예는 별도 10초다. 외부 제한은 native slot 준비·TC·정리를 포함하고, 그 전의 설치 복사·preflight는 별도다.

PID·IPC·mount·user·network의 private namespace를 관측했다. 실행 후에는 해당 설치를 사용하는 작업 소유 프로세스와 관측한 namespace holder가 남지 않았는지 확인한 뒤 다음 TC로 진행한다. Work702와 설치·결과·cache·registry·network 상태를 공유하지 않는다.

PASS는 runner exit 0만으로 정하지 않는다. Expected·dispatch·FIN, status·feedback·JUnit·test log, assertion과 strict focused verifier를 대조한다. FAIL도 정확한 TC 하나의 XML과 dispatch·FIN·실행 수를 확인한다. Timeout은 testcase assertion FAIL과 외부 명령 deadline을 구분한다. 준비·판정 근거가 불완전하면 INCONCLUSIVE이며 PASS에 포함하지 않는다.

## 개별 결과

| 번호 | TC | 판정 | 명령 경과초 | runner exit | 정리 |
| --- | --- | --- | ---: | ---: | --- |
| 01 | `cbrd_26659_alt_stub_duplicate` | FAIL | 40.501 | 0 | 관측 자원 없음 |
| 02 | `cbrd_26659_alt_stub_merge` | FAIL | 37.353 | 0 | 관측 자원 없음 |
| 03 | `cbrd_26659_churn_abort_retry` | FAIL | 96.671 | 0 | 관측 자원 없음 |
| 04 | `cbrd_26659_churn_insert_delete` | FAIL | 96.044 | 0 | 관측 자원 없음 |
| 05 | `cbrd_26659_churn_insert_update_delete` | FAIL | 106.922 | 0 | 관측 자원 없음 |
| 06 | `cbrd_26659_churn_restart` | FAIL | 110.859 | 0 | 관측 자원 없음 |
| 07 | `cbrd_26659_gap_compact_sa_cs` | FAIL | 35.255 | 0 | 관측 자원 없음 |
| 08 | `cbrd_26659_notify_abort` | FAIL | 76.449 | 0 | 관측 자원 없음 |
| 09 | `cbrd_26659_notify_commit` | FAIL | 57.106 | 0 | 관측 자원 없음 |
| 10 | `cbrd_26659_notify_nodrop` | FAIL | 44.483 | 0 | 관측 자원 없음 |
| 11 | `cbrd_26659_qualified_reuse` | PASS | 32.835 | 0 | 관측 자원 없음 |
| 12 | `cbrd_26659_record_target0` | FAIL | 29.200 | 0 | 관측 자원 없음 |
| 13 | `cbrd_26659_record_target10` | FAIL | 31.040 | 0 | 관측 자원 없음 |
| 14 | `cbrd_26659_schema_rewrites_sa` | TIMEOUT | 123.322 | 124 | 관측 자원 없음 |
| 15 | `cbrd_26659_serialized_chunks` | PASS | 31.611 | 0 | 관측 자원 없음 |
| 16 | `cbrd_26659_show_partitions` | PASS | 9.262 | 0 | 관측 자원 없음 |
| 17 | `cbrd_26659_snapshots_reclaim` | FAIL | 26.857 | 0 | 관측 자원 없음 |
| 18 | `cbrd_26659_tde_crash_committed` | FAIL | 6.948 | 0 | 관측 자원 없음 |
| 19 | `cbrd_26659_tde_crash_undo` | FAIL | 6.960 | 0 | 관측 자원 없음 |
| 20 | `cbrd_26659_tde_storage` | PASS | 33.820 | 0 | 관측 자원 없음 |
| 21 | `cbrd_27237_rollback_vacuum` | FAIL | 51.348 | 0 | 관측 자원 없음 |

통과한 네 TC는 `qualified_reuse`, `serialized_chunks`, `show_partitions`, `tde_storage`다. 이 네 원문의 native 판정을 확인했지만 실제 TC 저장소의 비활성 상태는 그대로다. 앞선 두 대표·Work699와 입력 경계가 다르므로 과거 FAIL 61개에 대한 한 번의 동일 입력 전체 실행으로 합산하지 않는다.

## 관측한 실패와 한계

| 분류 | 사례 수 | 현재 원문 관측 | 후속 판단 |
| --- | ---: | --- | --- |
| Alternative stub | 2 | `alt_stub_duplicate`·`alt_stub_merge`에서 `unassigned alternative write whole24Bstub contract failed`, `retained_whole_stub` 실패. 값·stored bytes·재조회 검사는 통과 | Stub contract·검사 기대값과 Engine 동작 대조 |
| 반복 작업·재시작 | 4 | `churn_abort_retry`, `churn_insert_delete`, `churn_insert_update_delete`, `churn_restart`의 세 cycle에서 모두 `empty_page_return` 실패 | 회수 기대값·관측 기준과 Engine 동작 대조 |
| Compact | 1 | `gap_compact_sa_cs`의 `materialized.current_record_flags`·`materialized.owner_presence` 실패. Full values·owner mapping·checkdb 검사는 통과 | 값 결과와 물리 상태의 차이 규명 |
| Notification | 3 | Abort는 `after_vacuum_values` 누락·실패, commit은 notification records 0인데 present 기대, nodrop은 `retained_whole_stub=false` | 세 관측을 같은 원인으로 단정하지 않고 각각 대조 |
| Record target | 2 | `record_target0`·`record_target10`의 boundary controller exit 1. 보존 진단의 마지막 완료 `diagdb` 명령 자체는 exit 0 | 정확한 실패 guard·snapshot과 Engine/TC 귀속 확인 |
| Snapshot·reclaim | 1 | `snapshots_reclaim`의 snapshot page reclaim·churn reclaim/plateau·three-cycle plateau 검사 실패 | 공간 회수 기준과 실제 유지·재사용 상태 대조 |
| TDE wrapper | 2 | Committed·undo wrapper line 5가 호출하는 sibling shell 진입점이 없음 | TC 호출 경로·공용 진입점 의존성 수리 필요. 이번에는 미수리 |
| Rollback/vacuum | 1 | `cbrd_27237_rollback_vacuum`의 `abort_after_vacuum_values` 실패 | 원래 pre-image 기대와 실제 결과·실행 순서 대조 |

합계는 FAIL 16개다. TDE wrapper 두 개는 현재 `01df2600a`에서 `../../cbrd_26659_crash_committed/cases/cbrd_26659_crash_committed.sh`와 대응 undo 경로를 호출한다. 전체 shell Git 입력에도 해당 활성 파일은 없고, 원문 body는 `disabled/heavy/.../*.sh.disabled`로 보존돼 있다. 이번 projection은 선택 21개만 복원하므로 그 별도 body를 임의 활성화해 실패를 가리지 않았다. 두 wrapper는 본래 AES crash 검증에 도달하지 못했다. 원문 heavy crash를 AES로 실행한 [Work691의 1 PASS](CBRD-26659-tde-helper-relocation_20261102_work691_codex.md)와 이 wrapper FAIL은 다른 실행 범위다.

이번 `notify_abort`·`notify_commit`·`notify_nodrop`·`show_partitions`에서는 과거의 `CUBRID_TMP: unbound variable` 오류가 관측되지 않았다. 앞의 세 개는 다른 assertion에서 FAIL이고 마지막은 PASS다. `tde_storage`도 PASS이며 이전 helper 누락의 원인 확정이나 수정 credit으로 자동 귀속하지 않는다.

`serialized_chunks`는 status·feedback·XML·원래 assertion과 focused verifier에서 PASS지만, framework 종료 출력에는 `cubrid.conf.org`가 없어 복사하지 못했다는 진단이 남아 있다. 이를 숨기지 않는다. 이번 설치는 시도별 disposable이며 소유 프로세스·namespace가 남지 않았지만, 이 관측으로 framework 설정 복원 문제까지 해결됐다고 판정하지 않는다. 같은 누락 메시지만으로 과거 FAIL의 원인을 설명할 수도 없다.

### 외부 명령 TIMEOUT

`schema_rewrites_sa`는 외부 120초 deadline 뒤 123.322초에 runner exit 124로 끝났다. JUnit의 case 경과는 118.740초이며 failure 항목이 있지만 완료된 assertion FAIL로 중복 합산하지 않는다. 시도 관측에는 실제 shell script process가 있고, 종료 후 소유 process·namespace holder는 없다. Native testcase 자체의 120초 제한에 도달했다는 근거와 원래 작업의 정상 완료 근거는 확보하지 못했다. 더 긴 실행·분할 필요성과 지연 원인은 후속이다.
원래 TC의 검사 실패와 Engine 결함 판정은 다르다. 값 검사와 물리 상태·소유권 검사가 다른 결과를 보이면 각각 기록한다. 이 실행만으로 데이터 손상·누수·새 회귀를 확정하거나 기대값을 바꾸지 않는다. 과거 helper·변수 누락 증상을 현재 원인으로 자동 이월하지 않는다.

## 보존 근거와 재검증

실제 시도 root는 `/home/vimkim/temp/w704-rjVY4qVI`다. `manifest.json`, `input-inventory.json`, `baseline.json`, `seed/`, `prepare.py`·`run.py`·`collect.py`·`serial.py`, `a01/` 이후의 시도와 `results.json`을 보존한다. 초기 full-shell 시도는 `/home/vimkim/temp/w21-2vhMkkum/a01`에 남아 있다. 판단 기록은 `/home/vimkim/temp/cbrd26659-suite-status-hax5uc3p/decisions.tsv`의 Work704 구간이다.

각 시도에는 source/install preflight·identity, 실행 환경·config·expected list, 명령과 종료값, native output·result archive·case logs·verdict artifacts, namespace 관측·정리 결과를 보존한다. 부가 controller 출력·snapshot의 존재는 실제 파일이 확인된 범위에서만 인정한다.

[증거 검증기](tools/verify-remaining21-native.py)는 testcase를 새로 실행하지 않고 고정 모집단·Git 입력 bytes와 mode, runtime hash, 개별 raw 판정과 정리를 대조한다. 전체 corpus 입력은 Git blob identity와 SHA-256으로 대조하며 소스·TC를 수정하지 않는다.

```sh
python3 cbrd-26659/tools/verify-remaining21-native.py \
  --root /home/vimkim/temp/w704-rjVY4qVI \
  --testcases /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128
```

Raw log·snapshot·설치·생성 inventory·중간 분석은 Git 밖에 보존한다. 최종 `final-proof.json`은 13,597개 입력과 21개 결과, 초기 관측, 최종 자원 종료를 검증했다. 근거 verifier는 CTP 결과의 dispatch·FIN·status·XML과 focused verdict를 대조하며 초기 입력 mode·Git blob identity·SHA-256도 확인한다.

Git에는 이 보고서, 체크리스트·색인 갱신과 근거 재검증에 필요한 도구만 남긴다. 이 결과는 위 고정 리비전의 focused 검증이며 다른 최신 Engine head, 일반 CI 전체, heavy·HA·성능·C++ 전체를 인증하지 않는다. TC 재활성화·Engine/TC 수리·push·CI·PR 변경은 이번 작업에 포함하지 않는다.
