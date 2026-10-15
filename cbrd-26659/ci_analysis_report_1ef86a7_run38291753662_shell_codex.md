# PR8128 최신 shell 병합 차단 평가

작성: 2026-10-15, Asia/Seoul. Work Item383 → 실제 OOS 병합 목표 Item371(10월 16일).
대상: [CUBRID/cubrid#8128](https://github.com/CUBRID/cubrid/pull/8128), Engine `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, [run38291753662 / attempt1](https://github.com/CUBRID/cubrid/actions/runs/38291753662).

## 판단과 우선순위

**Shell은 7 fail이며 병합 준비 완료가 아니다.** 비CDC 5건은 차단으로 유지하고, CDC 2건은 합의된 연기와 별도 승인 대상으로 구분한다. 앞선 SQL14 수리의 제외 규칙은 최종 OOS 병합 면제 규칙이 아니다. 평가 완료는 결함 수정이나 최종 전체 QA 완료를 뜻하지 않는다.

현재 HEAD의 수집 증거는 완전하다. **이번 exact-base 조회는 시간 구간 안에 이력 다운로드를 끝내지 못해 미확정**이다. 따라서 일곱 건 모두 현재 PR의 공식 baseline 비교 분류는 `uncomparable` 이며, 이 보고서는 Engine 회귀를 확정하지 않는다. 아래 역사적 기준 실행은 독립 검증한 문맥으로만 사용한다.

새로 실패한 `bug_bts_6279` 는 **테스트의 광범위한 프로세스 검색이 실행용 shell까지 종료한 것이 빈 결과의 유력 원인**이다. 실제 `kill -9` 대상에 `.localexec…sh` PID가 들어 있고, 복구 후 비교·최종 판정에 도달한 증거가 없다. 엔진 복구 회귀로 분류할 근거는 확보되지 않았다. 가장 바로 조치할 수 있는 항목은 이 TC의 PID 선택이다.

데이터 안전성 우선순위는 `rollback_vacuum` 이다. 다만 이번 CI가 직접 남긴 것은 controller exit1까지다. 과거 로컬의 post-vacuum corruption을 이번 실행의 확정 원인으로 옮기지 않는다. 다음 필수 입력은 해당 실행의 controller/journal과 실제 실패한 명령 출력이다. `snapshots_reclaim`, `utility_sa_physical` 도 같은 증거 공백이 있다.

담당은 아래의 **권고 역할**이며 새 담당자 배정이나 외부 연락을 수행한 기록이 아니다. 소스·TC 수정, DB 재현, CI trigger/rerun, 원격 게시와 병합은 이번 평가에 포함하지 않았다. Item324/332/338의 완료와 다른 세션의 Item372는 유지한다.

## 고정한 입력과 검증

2026-10-15 실행 시작의 단일 `cubrid-ci status` 에서 HEAD와 shell check가 retained item338 수집본과 일치했다. PR은 OPEN/draft, head repository `vimkim/cubrid`, head branch `CBRD-26659-oos-testcases-handover`, target `feature/oos-merge`, review verdict 없음이다. 로컬 Engine HEAD도 같은 SHA다.

| 항목 | 확인한 값 |
| --- | --- |
| Collector | `cubrid-ci 0.2.0 (16d7252122d1, release)`; doctor 정상 |
| Head collection | 기존 item338의 `2026-10-12T19:10:13.765156035Z` 수집을 재사용; 새 head collect 없음 |
| Matching observation | `20261012T191006.790341524Z-3528024-0`; 요청은 세 suite, binary 미요청, terminal `complete` |
| 분석 범위 | `test_shell` 만 분석; SQL/medium은 기존 summary의 상태·건수·무결성만 확인 |
| Public TC, SQL/medium | `df8596dd999e825b1ec9812a735bbe01e50ac715` / `tc/pr-8128` |
| Private TC, shell | `9a075340f6ee02741f2578117aebf1a5f9aa54bb` / `tc/pr-8128` |
| 소비한 Engine build | 전 61 shard가 위 Engine SHA, Debug, namespace `pr`, **생산 run38271660063 / attempt1** |
| Suite 실행 | 세 suite 모두 run38291753662 / attempt1. 생산 run과 소비 run을 구분한다 |
| CTP 입력 | Head/직전 run의 validated `collect.log` 는 `CTP_SHA=44e3f97c788ad82091d5b66d728852f3279b1e86` 을 기록 |

Command-result/manifest v2와 observation request/result v1을 스키마 검증하고, 저장된 command 결과와 유일한 observation 및 manifest가 완전히 같은지 확인했다. Suite-summary/raw-index/failure v2도 검증했다. 요청·PR·SHA·run/attempt·suite identity, 모든 선언 경로의 containment와 존재, summary digest, **780 raw 파일**(shell616/SQL136/medium28)의 길이·SHA-256, 61 shard의 `build.read`/`tc.read`, retained acquisition과 binary0 budget을 대조했다. 실패 metadata는 summary record와 일치하고 선언된 message/diff가 모두 존재한다.

Shell 50개 JUnit을 별도로 읽어 **3309개 고유 경로**와 7 failure를 대조했다. 각 failure 본문은 정규화된 `message.txt` 와 같았다. Counts는 `3309 = 3272 + 7 + 0 + 30`, `3309 = 3279 + 0 + 30` 으로 맞는다. 정상 수집된 red 결과이며 collector 실패가 아니다. Report-mode gate는 head `full` 을 허용한다.

| Suite/체크 | 상태 | Planned/tests | Run | Pass | Fail | Error | Skip | Unrun |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test_shell | completed / FAIL | 3309 | 3279 | 3272 | 7 | 0 | 30 | 0 |
| test_sql | completed / PASS, 문맥만 | 17489 | 17489 | 17489 | 0 | 0 | 0 | 0 |
| test_medium | completed / PASS, 문맥만 | 975 | 975 | 975 | 0 | 0 | 0 | 0 |

세 suite의 링크는 위 선택 run의 attempt1이다. 현재 build debug/release와 code-style/cppcheck/license/memory-monitor-check/pr-style은 SUCCESS다. Static check run은38271343335이며 suite run과 구분한다. 다른 provider의 `not_observed` 를 실패나 통과로 바꾸지 않았다.

## 현재 실패 7건

모든 경로는 private repository 상대 경로이며 실제 verdict는 `failure` 다. `direct` 는 이 PR의 TC 전달이 해당 검증을 직접 추가했다는 관계이며 Engine 회귀 확정이라는 뜻이 아니다. Confidence는 관측과 원인 추정을 분리한다. 근거 E1–E7은 마지막 절에 둔다.

| ID / shard / 초 | 전체 testcase 경로 | 이번 관측·분류 | Exact-base 분류 | PR 관계 / 신뢰도 |
| --- | --- | --- | --- | --- |
| F1 / 22 / 51.686 | `shell/_06_issues/_11_2h/bug_bts_6279/cases/bug_bts_6279.sh` | `blank result`; PID 선택에 실행용 shell 포함. TC 실행 중단 유력 [E1] | `uncomparable`; 현재 완료 baseline 없음 | `unlikely` Engine 회귀; 관측 높음, 중단 원인 높음/미재현 |
| F2 / 06 / 10.518 | `shell/_40_guava/cbrd_27237_rollback_vacuum/cases/cbrd_27237_rollback_vacuum.sh` | abort controller exit1; 내부 실패 단계 미수집 [E2] | `uncomparable`; 현재 완료 baseline 없음 | `direct` 새 검증, Engine 원인 `unknown`; verdict 높음, 현재 원인 미확정 |
| F3 / 11 / 9.741 | `shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/cbrd_26659_snapshots_reclaim.sh` | snapshot controller exit1; page-return 단계 도달 미확인 [E3] | `uncomparable`; 현재 완료 baseline 없음 | `direct` 새 검증, Engine 원인 `unknown`; verdict 높음, 현재 원인 미확정 |
| F4 / 18 / 7.430 | `shell/_40_guava/cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh` | ownership/descriptor oracle 14 NOK, logical/cleanup 등21 OK [E4] | `uncomparable`; 현재 완료 baseline 없음 | `direct` 새 검증; 물리 배치 결함 `plausible`, 관측 높음/원인 중간 |
| F5 / 39 / 19.110 | `shell/_40_guava/cbrd_26659_utility_sa_physical/cases/cbrd_26659_utility_sa_physical.sh` | source 검증·LOB transfer OK 뒤 controller status1; destination 내부 출력 없음 [E5] | `uncomparable`; 현재 완료 baseline 없음 | `direct` 새 검증; SA 배치 가설 `plausible`, 관측 높음/원인 중간 |
| F6 / 48 / 97.820 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | subcheck2/3 NOK; delete1/700, update0/2400, extractor `rc=-10`, corruption0 [E6] | `uncomparable`; 현재 완료 baseline 없음 | PR Engine 변경 관계 `unlikely`; 상세 관측 높음, deferred gap 귀속 중간 |
| F7 / 43 / 261.520 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | subcheck1 NOK; 4K/8K/16K `EXTRACT_ERR=2/4/3`, `FIND_OK=30` 씩, corruption0 [E7] | `uncomparable`; 현재 완료 baseline 없음 | PR Engine 변경 관계 `unlikely`; 상세 관측 높음, deferred gap 귀속 중간 |

## 원인 판단과 반증 조건

### F1: DB 이름 substring이 테스트 실행용 shell과 충돌

**관측.** 정확한 TC 소스는 `db_name=6279` 를 사용하고 `ps ux | grep $db_name | grep -v grep | grep -v *.sh` 결과의 PID를 모두 `xkill_pid` 에 넘긴다. 실제 glob은 `bug_bts_6279.sh` 로 확장됐다. E1의 188–213행은 다음을 보여 준다.

```text
root 9278 ... sh /tmp/.localexec1850058627924403801.sh 2>&1
root 9445 ... cub_server 6279
root 9448 ... cub_pl 6279
+ DBNumber='9278
9445
9448'
+ kill -9 9278 9445 9448
```

위 `ps` 세 줄의 중간 resource/time 열만 줄였다. `.localexec1850058627924403801.sh` 의 숫자에도 `6279` 가 들어간다. DB 프로세스 외의 실행 shell을 선택한 사실은 직접 관측이다. 로그는 `++ cat 1.txt` 에서 끝나며 `after kill`, restart, 두 번째 query, `write_ok`/`write_nok`, `finish` 기록이 없다. Runner는 실제로 빈 `.result` 를 실패 처리했다.

**추정·미확인.** 실행용 shell 종료로 후속 실행·판정 수집이 중단됐다는 설명의 신뢰도는 높다. 전체 부모 관계·wait status·`1.txt` 와 `2.txt` 는 없으므로 재현으로 확정한 원인은 아니다. 초기 SQL에는 unique-constraint 오류도 있지만 이후 kill 지점까지 계속 실행했으며, 이 오류만으로 빈 결과의 직접 원인을 정하지 않는다. 복구 후 값 비교는 검증되지 않았다.

기록된 CTP revision의 [LocalInvoker.java:49](https://github.com/CUBRID/cubrid-testtools/blob/44e3f97c788ad82091d5b66d728852f3279b1e86/CTP/common/src/com/navercorp/cubridqa/common/LocalInvoker.java#L49)는 `.localexec` 임시 파일을 만들고83행에서 `sh <temp> 2>&1` 로 실행한다. [LOCAL 실행 경로:191](https://github.com/CUBRID/cubrid-testtools/blob/44e3f97c788ad82091d5b66d728852f3279b1e86/CTP/shell/src/com/navercorp/cubridqa/shell/common/SSHConnect.java#L191)와 [case 실행:308](https://github.com/CUBRID/cubrid-testtools/blob/44e3f97c788ad82091d5b66d728852f3279b1e86/CTP/shell/src/com/navercorp/cubridqa/shell/main/Test.java#L308)은 이 설명을 뒷받침한다. [결과 수집:522](https://github.com/CUBRID/cubrid-testtools/blob/44e3f97c788ad82091d5b66d728852f3279b1e86/CTP/shell/src/com/navercorp/cubridqa/shell/main/Test.java#L522)는 빈 결과를 재조회한 뒤 두 `blank result` NOK를 만든다. 따라서 이 문구는 원인 미상의 collector 경고가 아니라 실제 CTP testcase verdict다. 코드는 local repository의 해당 Git object로 읽었으며 source 설명이 process ancestry 실측을 대신하지는 않는다.

**반증·다음 조치.** 동일 시점의 process ancestry/exit 기록에서 PID9278이 실행 체인과 무관하고 실제 테스트가 restart와 최종 판정을 마친 것으로 확인되면 중단 가설을 폐기한다. TC/QA 담당은 별도 수리에서 실행파일·정확한 DB 인자·생성 시점으로 소유 PID를 제한하고, DB 이름을 포함한 launcher 이름도 선택하지 않는지 검증해야 한다. 이후 정확한 before/after 결과가 비어 있지 않은지 포함해 원래 recovery 검증을 통과시킨다. 이번 보고서는 TC를 바꾸거나 재현하지 않았다.

### F2·F3: 과거 결함 후보와 이번 controller 실패를 구분

**관측.** 정확한 두 wrapper는 shared `snapshot_controller.sh` 를 각각 `--scenario abort` 와 `--scenario snapshot` 으로 실행하고 stdout/stderr를 `oos11.controller.log` 에 보낸다. 이번에는 각각 exit1이며 wrapper의 configuration restore는 OK다. 제한시간300/420초를 소진한 관측도, 과거의 controller127 관측도 아니다. **현재 raw index에는 controller/journal/내부 CSQL·SHOW·vacuum dump가 없다.** 외부 설정 복원 성공은 모든 내부 cleanup이나 scenario 성공을 증명하지 않는다.

**추정·미확인.** [2026-10-12 변환 검증](ci-replan/shell-conversion-results-20261012.md)의 별도 로컬 실행은 F2에서 vacuum barrier 뒤 pre-image corruption, F3에서 chunk4/37316 drain 뒤 pages9 유지와 downstream churn 미도달을 기록했다. 이는 후속 가설을 정하는 역사적 근거다. 현재 exit1이 같은 위치·원인이라는 결론은 보류한다. [규범 명세 §3·§4](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md)는 rollback pre-image의 live chain과 MVCC 안전성을 요구하고, 안전하게 비워진 page의 반환을 chunk 삭제와 구분한다. 명세 자체는 이번 실행의 실패 단계나 현재 티켓 해결 상태를 증명하지 않는다.

**반증·다음 조치.** F2의 이번 journal이 vacuum barrier 전에 setup/session/값 확인에서 실패했다면 현재 corruption 전이는 기각한다. F3가 drain 전에 실패했거나 안전하게 빈 page 조건을 충족하지 않았다면 page-return 원인 전이는 기각한다. QA/CI 담당이 해당 run/shard의 `oos11.controller.log`, `oos11.journal.log`, 실패 command stdout/stderr, process/cleanup receipt를 먼저 확보한다. 없다면 별도 승인된 동일 입력 focused native 재현을 설계한다. OOS storage 담당은 F2의 `rollback_vacuum_reached` 이후 exact pre-image, F3의 high/final SHOW·mutation LSA·vacuum progress·survivor 값을 확인한 뒤 수리 경로를 정한다. F2를 데이터 안전성 P0, F3를 물리 회수 P1로 권고하며 둘 다 차단을 유지한다.

### F4: 논리 성공과 물리 oracle 실패가 함께 존재

**관측.** E4의 첫39행에 route/forced 경로의 exact values와 duplicate rejection이 OK인 반면 root/child의 class/file/chunk 검증12개와 descriptor 검증2개가 NOK다. Cleanup과 설정 복원도 OK다. 정확한 `observe_partition` 의 메시지 `destination ownership mismatch` 는 shared observer의 class/file/chunks 파싱·검사 전체가 실패했을 때 출력된다. 그 문구만으로 VFID 소유권 하나를 확정 원인으로 좁힐 수 없다.

**추정·미확인.** 과거 retained CBRD-27089 물리 배치 후보와 일관되지만 원시 SHOW·parse diagnostic·diagdb가 없어 현재 구현 결함의 위치는 미확정이다. 논리 값 PASS는 해당 물리 조건을 대신하지 않는다.

**반증·다음 조치.** 원시 SHOW/diagdb가 올바른 destination class/VFID와 chunk 모델을 입증하고 parser만 거부했다면 Engine 물리 배치 가설을 폐기한다. TC/QA 담당은 `oos08.*show.log`, parse logs, `oos08.partition-diag.log` 를 확보하고 OOS storage 담당이 root/child 소유 관계를 대조한다. Oracle 오류는 필요성이 검증된 경우에만 별도 TC 수리로 다룬다. P1 비CDC 차단이며 이전 SQL repair 제외는 면제가 아니다.

### F5: SA destination의 실패 단계가 숨겨짐

**관측.** Source exact values/schema·OOS4/37316·checkdb, unload 후 동일 검증, 새 destination 생성과 해시가 다른 두 외부 LOB의 transfer가 OK다. 이후 controller exit1, 내부 자원 cleanup과 framework 설정 복원은 OK다. 이번 메시지에는 loaded physical SHOW나 실패 명령의 상세가 없다. Framework의 `cubrid.conf.org` 없음 경고도 있으나 최종 원본 대비 `cubrid.conf` 비교는 OK다.

정확한 wrapper20–27행은 controller 전체 출력을 `oos12.controller.log` 에 돌린 뒤 `PASS `/`FAIL ` 로 시작하는 줄만 결과에 옮긴다. Shared `oos_runtime.sh:7` 의 `rt_fail` 은 `OOS controller failed:` 로 출력하므로 그 진단은 이 필터를 통과하지 않는다. 이는 generic status만 보이는 구조를 설명하며, 원인을 특정하거나 collector 손실을 입증하지 않는다.

**추정·미확인.** 정확한 controller는 `loaddb -S --no-logging` 뒤 destination의 values/schema/physical 모델을 검사한다. 과거 로컬의 `loaded.physical status5`, destination OOS file 없음과 부합하지만, 이번에는 load/start/값 검사 등 중간 다른 단계의 실패도 배제하지 못한다. 현재 ordinary CSQL SA schema testcase의 PASS와 SA utility physical 결과는 별개다.

**반증·다음 조치.** 이번 command ledger가 physical 검사보다 앞선 loader/start 실패를 보이거나 실제 destination physical 모델이4/37316이면 SA 배치 원인 전이를 폐기한다. QA/TC 담당은 `oos12.controller.log`, `oos12.commands.log`, load summary, loaded values/schema/SHOW/owner 출력을 확보한다. Loader/OOS 담당은 확인된 단계에 따라 수리한다. P1 비CDC 차단; logical SA PASS로 물리 배치 PASS를 부여하지 않는다.

### F6·F7: 합의된 CDC 연기, 상세 변화는 그대로 기록

**관측.** F6는 delete/update extraction `rc=-10` 과 target 건수 미달이며 corruption counter는0이다. F7는 세 page size 모두 extraction error가 있고 find 실패와 corruption counter는0이다. Counter0은 전체 데이터 안전성 보증이 아니다. 직전 run의 F6 delete0/700 및 F7 errors1/1/0을 현재 값으로 재사용하지 않았다.

**판단·미확인.** [ADR-0005](/home/vimkim/gh/cubrid-oos-context/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md)는 이 두 TC를 활성 상태로 visibly failing하게 유지한다. 현재 extraction signature는 연기된 OOS history gap과 일관되며, 세부 코드 원인은 재현하지 않았다. 이 결정이 비CDC 다섯 건을 덮지 않는다.

**반증·다음 조치.** Driver/engine trace가 다른 log source·driver·설정 오류를 원인으로 입증하면 deferred gap의 동일 원인 추정을 수정한다. CDC 담당은 상세 오류를 후속 redesign에 보존하고, maintainer/admin은 [실행 계약](../feature-oos-merge/merge-readiness/execution-contract.md)에 따라 **이 두 건만의 예외**를 별도로 판단한다. 두 건에 대한 예외 확보 증거는 이번 평가에 없으며 답안·assertion·discovery를 바꾸지 않는다.

## Exact merge-base와 직전 실행 비교

현재 HEAD에 대해 `cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/8128 --suite test_shell --data-dir /home/vimkim/tmp/pr8128-shell-383/baseline --json` 을 **한 번** 실행했다. 기존 head observation은 세 suite 요청이지만, 이번 분석·baseline 요청은 shell만 선택했다. 재수집·CI trigger·다른 실행으로의 fallback은 하지 않았다.

Pinned resolution request는 `2026-10-15T11:24:17.545978028Z` 에 PR8128의 head `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, head ref `CBRD-26659-oos-testcases-handover`, target ref `feature/oos-merge`, target tip `fb567a629cdb390fff920542173fa36f454c74a0` 을 기록했다. **Target tip을 이번에 확정된 merge base로 바꾸어 쓰지 않는다.** 새 전용 cache의 Git 이력 다운로드가 약42분 동안 끝나지 않아, 약45분 첫 분석 구간을 마칠 때 이 작업 소유 fetch만 SIGTERM으로 중단했다. GitHub run/job 취소는 아니다.

Collector는 **exit3, `kind=unavailable`, `diagnostic=unavailable`** 을 반환했다. 구체 진단은 `Git fetch failed (signal: 15 (SIGTERM)); merge-base history unresolved` 다. 이는 분석 구간을 지키기 위한 **로컬 수집 중단**이며 provider 장애나 testcase 실패 판정이 아니다. 이번 baseline은 suite acquisition 이전 단계에서 멈췄으므로 완료 manifest/command-result v3와 observation v2 쌍, 선택된 baseline run/attempt, baseline suite verdict가 없다. 현재 head의 검증은 독립적으로 유효하다.

| 현재 HEAD의 공식 비교 집계 | 건수 | 범위 |
| --- | ---: | --- |
| Head failures | 7 | 검증된 현재 실패 전체 |
| also_observed_on_base | 0 | 이번 현재-head 관계에서 입증된 건수; 역사적 공통 증상 부재라는 뜻이 아님 |
| additional_on_head | 0 | 이번 관계에서 입증된 건수; baseline PASS를 가정하지 않음 |
| uncomparable | 7 | 현재 관계의 완료 baseline이 없음 |
| base_only | 미확정 | 이번 관계의 선택·coverage가 없어0건으로 세지 않음 |

집계는 `7 = 0 + 0 + 7` 이다. Report-mode 입력은 baseline `unavailable`, head mode `full`, comparison scope `none`, regression conclusions 불허다. 다음 증거 담당은 후속 평가에서 기존 collector Git cache 활용 등으로 현재 pinned 관계의 해석과 terminal baseline 증거를 확보해야 한다. 같은 TC revision·설정·signature를 대조한 뒤에만 공식 비교 분류를 갱신한다.

### 독립 검증한 역사적 기준 실행: 현재 관계를 대신하지 않음

Retained commit bundle은 Engine `fb567a629cdb390fff920542173fa36f454c74a0`, [run36570256001 / attempt1](https://github.com/CUBRID/cubrid/actions/runs/36570256001), Debug 생산 build36570061594 / attempt1이다. Private TC는 `c4b9d482fbd491a68510b2552df2c3cac91911fc` / `tc/pr-7990` 이다. Manifest/command-result v3와 유일한 observation request/result v2, shell summary/raw-index/failure v2, raw hashes·shard provenance·JUnit을 독립 검증했다. Observation은 `20261012T102933.402345975Z-1175235-0` 이다. **그 baseline 관계의 head는 이전 `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`** 이므로 현재 `1ef86a7` 관계의 terminal 결과로 대체하지 않는다.

역사적 shell은 planned/tests3289, run3259, pass3254, fail5, error0, skip30, unrun0이다. 실패 다섯 경로는 CDC27064/27075, `hide_cubrid_replay`, `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh`, `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh` 다. 마지막 두 경로와 replay는 현재 JUnit에서 각각 PASS다. 이를 현재 PR의 공식 `base_only` 집계나 수리 완료로 세지 않는다.

역사적 F1 record는 shard41에서 PASS76.507초다. F2–F5는 역사적 TC tree와 실행 모두에 없다. 역사적 F6에는 delete23/700·update0/2400 및 `rc=-10`, F7에는 extraction errors4/4/4와 corruption0이 기록돼 있다. 현재의 각 수치와 구분하며 동일한 코드 원인이나 OOS 악화 부재를 확정하지 않는다. F1/CDC 두 case의 **디렉터리 전체**는 위 TC SHA와 현재 SHA 사이에 같은 Git objects다. 네 신규 OOS case의 부재를 역사적 통과로 바꾸지 않는다.

역사적 collect log의 CTP는 `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` 로 현재의 `44e3f97c788ad82091d5b66d728852f3279b1e86` 과 다르다. 두 revision의 Git tree diff는 `CTP/common/script/util_compat_test.sh` 하나이며, F1의 launcher/LOCAL 연결/테스트 실행·결과 수집/init/helper 여섯 blob은 같다. `util_compat_test` 의 직접 참조는 shell/common Java 소스에서 찾지 못했다. 이는 관련 source 입력 비교이며 image/JAR/전체 설정·shard 인접성의 동등성 증명은 아니다. 노드·프로세스명·실행 배치 차이는 그대로 남긴다.

### 직전 동일 엔진 실행

직전 동일 엔진 run38271660063 / attempt1도 기존 저장 command와 유일한 terminal observation, schema·raw hashes·shard identity·JUnit 건수까지 독립 검증했다. F1은 shard46에서 **PASS,74.620초**였다. 현재는 shard22다. 여섯 재발 경로는 추출된 diff가 각각 byte-identical이지만 CDC 상세 메시지의 target/error 건수는 다르다. 이는 반복 관측이며 전체 원인 동일성 증명이 아니다.

직전 private TC `a2054f965a20241b87dc9577585ccc8a8cb6ab97` 과 현재 TC 사이에 F1 디렉터리3파일, F2–F7 case 디렉터리, 사용된 `oos_common`/`oos_utility` 기존 helper는 동일하다. `oos_schema.sh` 추가는 새 schema 검증용이며 이를 기존 helper 변경으로 세지 않았다. CTP 기록도 동일하다. 동일 Engine/생산 build여도 shard 배치·인접 TC·프로세스명·노드 환경은 통제되지 않았다.

현재 `hide_cubrid_replay` 는 shard21에서 **PASS,60.969초**다. 이전의 `qa8.answer` 실패가 사라진 데 수리 credit을 부여하지 않으며 과거 원인도 확정하지 않는다. 새 schema SA/CS 두 shell case는 각각 shard47/15에서 PASS다. 이 관측은 전체 SA loader 또는 물리 재현기 통과를 뜻하지 않는다.

## 병합 판단과 후속 작업

| 우선순위 | 담당 역할 | 다음 작업과 종료 증거 |
| --- | --- | --- |
| P0 데이터 안전성 | QA/CI → OOS storage | F2 현 실행 controller/journal 확보. Vacuum barrier 후 exact pre-image 성공 또는 실제 실패 단계·원인·수리 후 회귀 증거 필요 |
| P0 즉시 가능한 TC 조치 | TC/QA | F1의 launcher substring 선택 제거를 별도 수리. 소유 DB PID만 종료하고 원래 recovery 비교·최종 verdict 완료 증거 필요 |
| P1 물리 검증 | OOS storage + TC/QA/loader | F3/F4/F5 원시 물리·command 증거 확보, 각각 안전한 page-return/partition destination/SA destination의 원인 분리와 후속 검증 |
| 별도 예외 승인 | CDC 담당 + maintainer/admin | F6/F7 활성 실패 유지; 두 건에 한정한 합의된 예외의 확보 여부 기록 |
| 비교 증거 보완 | CI 증거 담당 | 현재 pinned PR/head/target의 exact merge-base와 완료 shell baseline 확보; 현재 미확정을 PASS나 회귀로 바꾸지 않음 |
| 인간 TC 검토·통합 | PR 작성자/리뷰어 | Public TC#3688/private TC#4365에 대한 인간 검토·merge/close 정책 확인. 본 평가는 TC gate 해제 증거를 만들지 않음 |

소스·TC 수리와 검증은 후속 지시로 분리한다. 이 보고서의 로컬 문서 commit·main 통합과 원격 게시도 별도 단계다. 현재 평가만으로 PR8128이나 최종 PR7990의 병합 가능성을 선언하지 않는다.

이번 read-only 확인에서 [public TC#3688](https://github.com/CUBRID/cubrid-testcases/pull/3688)과 [private TC#4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)는 모두 OPEN draft이며 `tc/pr-8128` → `feature/oos-merge`다. Live head는 위에서 검증한 public/private TC SHA와 같다. Engine check snapshot에는 `Check TC PRs`가 `not_observed`다. Context 부재를 개인 정책상 TC 검토·병합 요건의 해제로 해석하지 않는다.

## 근거 위치와 재검증

Head bundle root `H`:
`/home/vimkim/tmp/sc338-ci/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b`.
Shell suite directory `S` 는 `H/providers/github-actions/runs/38291753662/attempts/1/test_shell` 이다.

| 근거 | 보존한 파일/내용 |
| --- | --- |
| Head identity/observation | `H/manifest.json`, `H/observations/20261012T191006.790341524Z-3528024-0/{request,result}.json`; 원 command는 `/home/vimkim/tmp/sc338/ci-collection.json` |
| E1 | `S/failures/shell_06_issues_11_2h_bug_bts_6279_cases_bug_bts_6279_sh-4f618eb085/` 의 metadata/message/diff; 원 JUnit `S/raw/shards/22/test-shell.xml` |
| E2 | `S/failures/shell_40_guava_cbrd_27237_rollback_vacuum_cases_cbrd_27237_rollback_vacuum_sh-50405a0016/` 의 metadata/message/diff |
| E3 | `S/failures/shell_40_guava_cbrd_26659_snapshots_reclaim_cases_cbrd_26659_snapshots_reclaim_s-eb029bc997/` 의 metadata/message/diff |
| E4 | `S/failures/shell_40_guava_cbrd_26659_partition_owner_cases_cbrd_26659_partition_owner_sh-f4eb1b3422/` 의 metadata/message/diff |
| E5 | `S/failures/shell_40_guava_cbrd_26659_utility_sa_physical_cases_cbrd_26659_utility_sa_physic-ae6f63879c/` 의 metadata/message/diff |
| E6 | `S/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/` 의 metadata/message/diff; message4–26행 상세 건수 |
| E7 | `S/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/` 의 metadata/message/diff; message4–10행 page-size별 상세 |
| 이번 평가 scratch | `/home/vimkim/tmp/pr8128-shell-383/`: status/pr-identity, `head-validated.json`, `head-cases.json`, `previous-validated.json`, `previous-cases.json`, `previous-comparison.json`, `exact-source-objects.json`, assessment/report-mode, validation scripts |
| 이번 baseline 중단 | Scratch의 `base-result.json`, `base-exit.txt`, `base-local-stop.json`; `baseline/baseline-resolutions/resolution-yLmF3e/{request,result}.json` 에 pinned 입력과 unavailable 진단 |
| 역사적 기준 문맥 | `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0`; scratch의 `historical-base-validated.json`, `historical-base-cases.json`, `historical-base-source-comparison.json`, `ctp-input-equality.json` |
| 이전 완료와 결정 | [SQL repair 범위](ci-repair/README.md), [결과](ci-repair/repair-results.md), [shell 변환의 로컬 원인/한계](ci-replan/shell-conversion-results-20261012.md), [최종 OOS 판단 계약](../feature-oos-merge/merge-readiness/execution-contract.md) |

TC 소스는 canonical local private `develop` repository에서 `git show 9a075340f6ee02741f2578117aebf1a5f9aa54bb:<full-path>` 로 읽고 Git blob 존재를 일곱 건 모두 확인했다. 현재 checkout 파일이나 JUnit의 floating `blob/develop` 링크를 exact source 대신 사용하지 않았다. OOS 명세는 완독 전후 SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65` 가 같았고 마지막 갱신일은2026-10-08이다. 관련 티켓의 현재 JIRA workflow state는 조회하지 않았으므로 이 보고서는 해결/미해결 상태 변경을 주장하지 않는다.

재검증은 scratch의 `validate_bundle.py` 를 `/usr/bin/python3` 로 기존 `ci-collection.json` 에 실행하고, `audit_shell.py` 로 complete JUnit과 failure 본문·건수를 대조한다. `report_mode.py` 는 검증 사실만 입력받는다. Raw bundles/logs·생성 inventories는 문서 Git 이력에 넣지 않는다.

[E1]: /home/vimkim/tmp/sc338-ci/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b/providers/github-actions/runs/38291753662/attempts/1/test_shell/failures/shell_06_issues_11_2h_bug_bts_6279_cases_bug_bts_6279_sh-4f618eb085/message.txt

[E2]: /home/vimkim/tmp/sc338-ci/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b/providers/github-actions/runs/38291753662/attempts/1/test_shell/failures/shell_40_guava_cbrd_27237_rollback_vacuum_cases_cbrd_27237_rollback_vacuum_sh-50405a0016/message.txt

[E3]: /home/vimkim/tmp/sc338-ci/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b/providers/github-actions/runs/38291753662/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_snapshots_reclaim_cases_cbrd_26659_snapshots_reclaim_s-eb029bc997/message.txt

[E4]: /home/vimkim/tmp/sc338-ci/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b/providers/github-actions/runs/38291753662/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_partition_owner_cases_cbrd_26659_partition_owner_sh-f4eb1b3422/message.txt

[E5]: /home/vimkim/tmp/sc338-ci/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b/providers/github-actions/runs/38291753662/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_utility_sa_physical_cases_cbrd_26659_utility_sa_physic-ae6f63879c/message.txt

[E6]: /home/vimkim/tmp/sc338-ci/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b/providers/github-actions/runs/38291753662/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt

[E7]: /home/vimkim/tmp/sc338-ci/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b/providers/github-actions/runs/38291753662/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/message.txt
