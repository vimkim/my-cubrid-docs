# CBRD-26659 후속 수리와 실패·timeout 분석

작성일은 2026-11-03, Asia/Seoul이다. TC 작성자와 리뷰어가 TDE wrapper·REPARTITION 수리, 잔여 실패 14개의 귀속, SA schema timeout의 후속 처리를 판단하도록 작성했다. Work715가 네 작업 Work716~719를 통합했다.

TDE committed·undo 2개와 수정한 REPARTITION 전체 TC가 focused native 검증에서 PASS했다. REPARTITION은 원래 default·force_outline 두 정책을 모두 실행했다. `schema_rewrites_sa`는 원문 작업을 유지하고 진단 제한만 늘린 실행에서 PASS했다. 기존 120초 TIMEOUT을 통과로 바꾸지 않는다. 과거 FAIL 14개는 모두 그대로 FAIL이며, 그중 8개는 고정 리비전의 Engine 명세 차이 또는 값 안전성 실패를 뒷받침한다. 나머지 6개의 원인은 미확정이다.

수리 두 커밋은 [정규 TC PR #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)의 `tc/pr-8128`에 `09ea46e1bb5d02dca4a253cfd0a6c7ce455f5614`로 게시했다. 실제 TC PR 병합과 상위 Work456 완료는 별도다.

## 입력과 실행 범위

| 항목 | 고정 리비전 또는 범위 |
| --- | --- |
| Engine | `vimkim/cubrid`, `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, OptDebug producer. Engine·CCI/JDBC 변경 없음. 기존 CCI/JDBC dirt 보존. |
| TC 기준 | `CUBRID/cubrid-testcases-private-ex`, `01df2600ac75180812451462b5c044cfa56b732a` |
| 게시 커밋 | TDE `212e7674720728420067afa010d34fc1b86dc6de`, REPARTITION `09ea46e1bb5d02dca4a253cfd0a6c7ce455f5614`. 실행한 후보의 변경 blob 7개와 게시본이 일치. |
| 다른 TC | public `b038c424b6a8d078671132e2369040493a5fc1f6`, heavy `d5247632b19a0905eefadee6ce39a8e1ab667c9f` 유지 |
| 명세 | [OOS 명세 `281a940`](https://github.com/vimkim/cubrid-oos-context/blob/281a940eafb5db507bce8e75a51de0ea94b4bfde/OOS-CONTEXT.md), SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63` |
| 실행 자산 | 보존 Work699/704 seed를 시도별 설치·CTP·HOME·registry·TMP·cache·slot로 복사. `cubrid-testkit` SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, CTP `9c62858b10005d721546cc007be260844033b9e9`와 보존 patch |

분석·수정은 작업별 소유 경로에서 병렬로 수행했다. DB 실행은 공용 flock과 일회용 root grant로 A 두 건, B 한 건, D 한 건 순서로 직렬화했다. 각 실행은 native shell, containment, 한 slot, `scenario_disk=on`이며 update·retry·continuation·case patch를 끈 상태다. 실제 TC 저장소의 활성·비활성 선택은 유지했다. Runner exit 0만으로 PASS를 부여하지 않았다.

A는 전체 projected shell 입력, B는 Work702의 보존 536파일 입력, D는 Work704의 13,597파일 projected 입력을 사용했다. B와 D의 모집단을 같은 전체 suite로 합산하지 않는다. C는 새 TC를 실행하지 않고 보존 실패를 분석했다.

## TDE wrapper 두 개는 원래 AES crash 검증까지 통과

[Work704](CBRD-26659-remaining21-native_e3589ae_20261103_work704_codex.md)의 두 FAIL은 wrapper가 호출한 활성 sibling 진입점이 없어 본래 crash 검증에 도달하지 못한 결과다. 실제 body는 `disabled/heavy`에 있었다.

기존 committed·undo body를 byte-identical하게 `shell/_40_guava/oos_common/crash_committed.sh`·`crash_undo.sh`로 옮겼다. AES wrapper 두 개와 일반 비활성 wrapper 두 개가 이 공용 body를 source한다. 일반·AES 선택이나 원래 body의 assertion·정리·오류 처리는 바꾸지 않았다. 이 구조는 한 TC만 선별해도 다른 TC의 `cases` 아래 파일을 요구하지 않는다.

| 원래 AES TC | native 판정 | 원문 근거 |
| --- | --- | --- |
| `tde_crash_committed` | PASS, runner 0·focused verifier 0 | journal의 baseline·recovered AES, scenario 완료, 소유 자식 정리 |
| `tde_crash_undo` | PASS, runner 0·focused verifier 0 | journal의 baseline·recovered AES, scenario 완료, 소유 자식 정리 |

두 실행 모두 44개 OK assertion 행과 정확한 단일 case dispatch·FIN·XML을 확인했다. 실행 후 소유 프로세스·관측 namespace holder·host mount·socket 잔여는 없었다.

CI keep-case의 **고정 `155c265` 버전**으로 AES·일반 committed·undo 네 진입점을 각각 선별해 wrapper와 body 생존을 확인했다. 최초 정적 시도는 live script hash 변경을 감지해 거부됐으며 보존했다. 이 네 대조를 최신 CI 전체 동작의 증거로 확대하지 않는다. 일반 NONE 진입점은 정적·선별 검증만 수행했고 새 native 실행은 하지 않았다.

## REPARTITION은 기존 root의 파일 연결과 현재 소유권을 구분

[Work702 진단](CBRD-26659-repartition-root-oos_e3589ae_20261103_work702_codex.md)에서 확인한 기존 root의 `has_oos_file==0` 조건만 REPARTITION에서 적용하지 않도록 수정했다. Root owner JSON은 계속 기록한다. 다른 partition 시나리오의 조건, 전체 값, 논리적 child membership, 실제 destination heap·OOS owner의 raw 검사는 유지했다. 기대 flag를 항상 1로 바꾸지 않았다.

수정한 원래 전체 TC는 1 PASS·0 FAIL·0 SKIP이다. default·force_outline 모두 controller exit 0이고 full values, p0·p1 membership, raw record contract, 완료 phase와 소유 정리를 통과했다. 정책별 실제 archive를 별도로 보존하고 raw parser로 재검증했다. 정상 소유자 대조는 exit 0, 실제 OOS owner를 sibling으로 바꾼 대조는 exit 1이다.

CS 관측의 예전 root 물리 레코드 두 개는 보존돼 있다. 이번 PASS는 현재 값·배치·소유권 검사의 결과이며, 예전 root의 전체 vacuum 진행·빈 page 회수·DROP 시점까지 검증한 결과가 아니다.

## 실패 14개는 8개 근거 확보와 6개 원인 미확정으로 분류

아래 판정은 전부 Engine `e3589ae`·TC `01df2600a`의 보존 실행이다. 최신 feature head나 연결 PR의 현재 수정 여부를 뜻하지 않는다. 여덟 사례는 여덟 개의 서로 다른 새 결함이라는 뜻도 아니다.

| TC | 보존 관측과 귀속 |
| --- | --- |
| `alt_stub_duplicate` | note만 할당한 UPDATE에서 payload hash는 같지만 head OID·stamp가 바뀜. 전체 24B 미할당 stub 보존 계약의 Engine 차이. 정확한 호출 경로는 미추적. |
| `alt_stub_merge` | 같은 미할당 payload의 OID·stamp 변경. MERGE 경로의 보존 계약 차이이며 호출 경로는 미추적. |
| `churn_abort_retry` | 세 cycle의 20초·2page 복귀 조건 FAIL. LSA horizon·candidate·growth gate 상태 부재로 원인 미확정. |
| `churn_insert_delete` | 동일 복귀 조건 FAIL. 관측 count를 Engine 회수 결함으로 바로 귀속하지 않음. |
| `churn_insert_update_delete` | 첫 cycle에서 chunk 1개인데 user page 113개, 복귀 조건 FAIL. Gate·관측 기준 귀속 미확정. |
| `churn_restart` | 재시작 포함 세 cycle 복귀 조건 FAIL. Hint 유실이나 회수 경로 원인 미확정. |
| `gap_compact_sa_cs` | full value는 맞지만 record flag·OOS owner 기대 실패. 물리 재작성 여부와 lazy default 기대의 귀속 미확정. |
| `notify_abort` | rollback 직후 값은 맞고, vacuum 진행 뒤 읽기에서 corrupted OOS metadata 오류. 고정 리비전의 값 안전성 실패. 실제 삭제 stack은 없음. |
| `notify_commit` | positive OOS WAL은 있으나 notification 0개. Source의 미구현 emitter와 명세의 commit notification 계약 차이. 이 사례의 후속 값·회수는 통과. |
| `notify_nodrop` | note-only UPDATE가 미할당 payload의 전체 stub identity를 바꿈. 보존 계약의 Engine 차이. |
| `record_target0` | `DB_PAGESIZE/4`와 명세의 4060B target 차이. `b12_above` HAS_OOS 불일치, 별도 stop 길이 오류도 보존. |
| `record_target10` | unfill 10%에서도 같은 target 차이와 두 물리 오류. |
| `snapshots_reclaim` | snapshot 회수·세 cycle plateau 기대 FAIL. 고정 시한·plateau와 안전한 eventual reclaim 사이의 귀속 미확정. |
| `cbrd_27237_rollback_vacuum` | rollback 직후 읽기는 통과, vacuum 뒤 원래 preimage 읽기에서 corrupted OOS metadata 오류. 값 안전성 실패이며 해당 실행의 삭제 stack은 없음. |

Target의 stored length 4048B에는 정책 비교용 MVCC reserve 16B를 더해 4064B가 된다. 4060B를 초과하지만 예전 raw quarter-page target 아래여서 두 경계 기대가 달라진다. 두 번째 stop 길이 오류의 단독 원인까지 확정한 것은 아니다. 기준 source는 [heap_file.c](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/heap_file.c#L13177), notification 예약은 [recovery.h](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/recovery.h#L206)에서 확인했다.

[CBRD-27785의 후속 target 후보](../cbrd-27785/CBRD-27785-four-record-target-pr-body_4c3c8d7_claude.md)를 연결한다. Rollback 두 사례는 CBRD-27237의 별도 추적 재현과 일치하는 증상이나, 이 실행에서 forward-walk가 해당 chain을 삭제했다는 주장은 추론이다. CBRD-27858의 sysop slot 재사용 문제와 동일시하지 않는다.

원인 미확정 다섯 회수 사례에는 page identity·LSA/horizon·vacuum candidate·pending-delete와 sweep 결정을 함께 관측하는 대조가 필요하다. Compact에는 representation ID와 실제 재작성 경로 대조가 필요하다. 현재 count만 다시 실행해 원인을 확정하지 않는다. Engine 진단 build나 별도 수리는 이번 TC 수리 범위에 넣지 않았다.

## SA schema는 원문 정상 완료 근거를 확보하고 장시간 분류 유지

기존 `schema_rewrites_sa`는 120초 외부 invocation 제한 뒤 exit 124였다. Process trace는 helper 컴파일, createdb, 순차 SA SQL 진행을 보여 준다. Runner 종료 지연이나 한 명령의 고정 120초 stall로 분류할 근거는 없다. 그 기록은 정상 완료 미확인 TIMEOUT으로 유지한다.

진단 실행에서는 원문 SHA-256 `65fb74ade41faaa677580b9cac814c18c4472ae1799f962c28ca7b4b63f02db7`, 전체 값·물리 assertion과 상태 전이를 유지했다. Native 제한만 120→750초, 외부 제한만 120→780초로 늘렸다. 내부 controller의 기존 600초 제한은 유지했다.

이 실행은 원래 journal 18개 phase와 wrapper assertion 3개를 통과했고, runner·focused verifier가 모두 0이다. Framework 설정 복원과 소유 프로세스·관측 namespace holder 종료도 확인했다. 관측한 case 166.300초·invocation 174.349초는 공유 host 한 번의 진단 시간이다. 성능 비교나 향후 완료 시간 보장이 아니다.

현재는 120초 gate 기준 장시간 TC로 분류한다. 짧은 gate에 반드시 넣어야 한다면 연속 schema state·실패 보존 assertion을 유지하는 분할을 별도로 설계한다. 이번 작업에서는 실제 timeout 설정·활성화·suite 배치를 바꾸지 않았다.

## CI와 리뷰·병합 상태

두 TC push 이후 [CI 41595701615](https://github.com/CUBRID/cubrid/actions/runs/41595701615)를 `/run all`로 한 번 시작했다. Engine은 `e3589ae`, private TC는 `09ea46e1b`, public은 `b038c424`다. 양쪽 feature testcase baseline ancestry check는 PASS했다. 기존 실행 종료와 새 trigger 부재를 확인하고 요청했으며 다섯 gha context가 같은 새 run을 가리켰다.

2026-11-03 16:36 KST 관측에서 두 build와 plan, medium shard가 SUCCESS다. SQL·shell 작업 60개는 `cubrid-arc` runner 대기 중이다. 전체 CI는 미완료이며 최종 결과를 추가할 예정이다. Plan 로그에서 Engine·public·private TC의 위 리비전 일치를 확인했다.

일반 CI가 성공해도 비활성 TC의 focused 결과, SQL 전체 자료 정합성 미인증, heavy·HA·C++와 미해결 Engine/TC 항목은 각각의 범위로 남는다. 수정한 wrapper·REPARTITION의 실제 활성·비활성 선택은 유지했으므로 CI가 이 세 TC를 새로 실행했다고 해석하지 않는다. TC PR의 실제 리뷰·병합과 QA heavy·HA 환경·주기·담당 합의가 남는다. 성능 Work544를 새 완료 조건으로 추가하지 않는다.

## 보존 근거와 재검증

원본 raw root는 `/home/vimkim/temp/cbrd26659-followups-17mm966k`다. `identity.json`, `worker-contract.md`, `plan.md`, `a-tde/`, `b-repartition/`, `c-fail14/`, `d-timeout/`, gate 기록, TC 통합·게시 proof, CI receipt·snapshot을 보존한다. 이전 Work704·702·699·691 원본은 수정하지 않았다. 소스 개발 도구의 `PRESET_MODE` 미설정·broken compile_commands 경고가 있어 직접 source·raw artifact를 읽었으며 Engine workspace를 수리하지 않았다.

[증거 재검증기](tools/verify-followups.py)는 DB를 새로 실행하지 않는다. 고정 hash의 worker 검사 도구, 원래 raw dispatch·FIN·XML·journal·archive, 정책별 owner와 잘못된 owner 대조, 14개 모집단, 원래 timeout과 연장 진단의 구분, 실행 후보와 게시 blob 일치를 확인한다. 일부 인과관계는 독립 raw 검토로 뒷받침하며 자동 검사 하나로 모든 원인을 증명하지 않는다. 검증기 PASS는 증거 일치이며 전체 TC·CI의 PASS 인증이 아니다. Raw 절대 경로와 기존 Git 객체를 보존해야 재실행할 수 있다.

```sh
python3 cbrd-26659/tools/verify-followups.py \
  --root /home/vimkim/temp/cbrd26659-followups-17mm966k \
  --testcases /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128
```

Git에는 이 보고서·TODO·README와 필요한 증거 재검증기만 남긴다. Raw 로그·JSON·실행 설치·중간 분석·감사 기록은 Git 밖에 보존한다. 다음은 원인 미확정 6개의 추가 관측, 확인된 Engine 차이의 후속 연결·원문 재검증, 장시간 배치·재활성화, 기존 SQL 정합성·HA·커버리지와 실제 TC 리뷰·병합이다.
