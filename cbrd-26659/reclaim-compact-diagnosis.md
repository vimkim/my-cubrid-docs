# CBRD-26659 회수·compact 실패의 원인 관측

2026-11-04, Asia/Seoul. TC 작성자와 리뷰어가 원인 미확정 6건의 후속 처리를 판단하도록 작성했다. Work756은 [Work715·718의 인계](follow-up-results.md)에서 이어진 진단이다.

새 진단에서 회수 후보의 LSA gate 거부와 SA compact의 OOS 배치 우회를 확인했다. 회수 실패를 단순한 시간 부족이나 누수로 일괄 분류하지 않는다. 원래 14 FAIL과 120초 TIMEOUT, 실제 TC 리뷰·병합의 미완료 상태는 유지한다. 아래 결과는 새 진단의 원인이며, horizon 기록이 없는 과거 실행의 각 페이지 원인을 소급해 증명하지 않는다.

## 기준과 관측 방법

| 항목 | 고정 입력과 범위 |
| --- | --- |
| Engine | `vimkim/cubrid`의 `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, OptDebug 보존 설치본. PR #8128의 head는 `CBRD-26659-oos-testcases-handover`, base는 `feature/oos-merge`다. |
| TC | 원래 `01df2600ac75180812451462b5c044cfa56b732a`의 보존 projected corpus. 이번 실행의 진단 변경은 attempt별 입력과 patch로 보존했다. 게시 TC `09ea46e1b`를 수정하지 않았다. |
| 명세 | [OOS-CONTEXT.md](https://github.com/vimkim/cubrid-oos-context/blob/281a940eafb5db507bce8e75a51de0ea94b4bfde/OOS-CONTEXT.md), SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`. |
| 실행 | Native `cubrid-testkit` shell, containment, 한 slot, `scenario_disk=on`. 시도별 설치·CTP·HOME·registry·TMP·cache·corpus를 분리하고 공용 flock으로 직렬 실행했다. |
| 관측 | GDB에서 설치본의 심볼과 gate 입력을 읽고, 종료한 서버의 정확한 파일 allocation과 16KiB raw page를 대조했다. 진단 SA boot는 vacuum을 비활성화하고 원래 설정을 복원했다. |
| 원본 보존 | `/home/vimkim/temp/w704-rjVY4qVI`와 `/home/vimkim/temp/cbrd26659-followups-17mm966k`는 변경하지 않았다. 기존 CCI/JDBC dirt도 보존했다. |

`testkit` SHA-256은 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`다. 각 preflight는 source/install commit 일치와 containment를 확인했다. 소스 도구 검사는 `PRESET_MODE` 미설정과 기존의 깨진 `compile_commands.json` 링크를 보고했다. 직접 소스와 설치본의 심볼을 사용했다.

## 회수는 chunk 삭제와 page 반환을 나눠 관측

Chunk 삭제는 slot을 비운다. Page 반환은 별도의 작업이다. Vacuum은 삭제로 완전히 비워진 VPID를 모아 sysop commit과 home page unfix 뒤 `oos_reclaim_empty_pages`에 전달한다. [후보 생성](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/oos_file.cpp#L3394)과 [REMOVE의 호출 경계](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/query/vacuum.c#L1970)를 확인했다.

한 reclaim 호출은 active transaction과 system tdes의 head를 읽고, scan 전에 채취한 append LSA로 제한한 horizon을 계속 사용한다. 빈 페이지의 `page_lsa < horizon`이 성립해야 반환할 수 있다. READ 검사를 통과한 뒤 header WRITE latch와 page WRITE fix 아래에서도 재검사한다. Fast path에는 rollback CLR equality 예외가 적용되지 않는다. [Horizon](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/oos_file.cpp#L1439), [gate와 재검사](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/oos_file.cpp#L1512), [후보별 고정 sample 사용](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/oos_file.cpp#L1754)을 근거로 한다.

Horizon이 나중에 전진해도 그 batch가 유예한 페이지를 타이머로 다시 시도하지 않는다. 후속 bitmap sweep은 target OOS 파일의 페이지 할당 지점에서 실행된다. 다른 table의 log filler와 반복 SHOW는 이 지점의 실행을 보장하지 않는다. [Pending-delete 상태](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/oos_file.cpp#L1288)와 [성장 지점](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/oos_file.cpp#L2006)을 확인했다.

### 빈 페이지와 gate 입력의 실제 대조

정지 후 allocation roster와 raw page를 독립 decoder로 읽었다. Sticky header와 file-table page를 제외한 빈 data page를 셌다. 각 VPID의 raw page LSA가 기록된 gate 입력과 같고, 그 입력이 실제 비교식을 거부할 때만 연결했다. 최종 reclaim enum을 관측했다고 표현하지 않는다.

| 원래 TC | 새 진단 | Raw 빈 data page | 같은 VPID·page LSA의 gate 거부 | 판별 결과 |
| --- | --- | --- | --- | --- |
| `churn_insert_delete` | a12, 첫 cycle와 성장 대조 | 20 | 20 | 원래 20초 반환 조건은 FAIL. 빈 페이지 전부의 유예를 확인했다. |
| `churn_insert_update_delete` | a03, 첫 cycle | 191 | 191 | 이전 UPDATE 세대와 마지막 DELETE 뒤 남은 빈 페이지 전부를 연결했다. |
| `churn_restart` | a04, 첫 cycle | 89 | 89 | 첫 실패는 이름 붙인 cycle 종료 후 restart보다 앞선다. Hint 유실로 귀속하지 않는다. |
| `snapshots_reclaim` | a06, 원래 snapshot과 세 churn cycle | snapshot 5, 마지막 churn 15 | 각각 5, 15 | Snapshot 감소·churn plateau의 FAIL과 실제 유예를 함께 확인했다. |
| `churn_abort_retry` | a11과 a15, 첫 cycle | a11은 11, a15는 8 | 각각 9, 6 | 나머지 두 VPID는 rollback undo 호출과 성장 경로 진입을 별도로 확인했다. 최종 reclaim enum은 미관측이다. |

표의 빈 페이지 수는 SHOW의 `unused_bytes`에서 추정한 값이 아니다. 예를 들어 a03은 sticky 1개, live data 1개, empty data 191개로 user page 193개를 구성한다. a04는 같은 방식으로 91개다. SHOW의 user page 수에는 sticky header가 포함되며, record 합계는 conditional fix를 사용하는 별도 scan이므로 동시 실행 중 완전한 page census로 취급하지 않는다. [SHOW 구현](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/oos_file.cpp#L3834)을 근거로 한다.

Sampling 이후 기록한 `active_heads`로 horizon을 제한한 transaction을 특정하지 않는다. 해당 probe는 system index 0도 출력하지만 실제 [최소 LSA scan](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/log_tran_table.c#L4552)은 그 index와 NULL transaction ID를 제외한다. Sampling 때의 실제 append clamp와 head 목록은 확보하지 못했다.

### 성장 대조는 20개 페이지의 재사용 순서를 확인

a12는 첫 cycle의 원래 20초 assertion과 정확한 survivor 검사를 끝낸 뒤 raw census를 저장했다. 이 시점에는 22 user page 중 sticky 1개와 live data 1개를 제외한 20개가 비어 있었다. 서버를 재시작하고 별도 barrier를 commit한 뒤 16,000B 값 140개를 각각 commit했다. 이 대조는 원래 세 cycle TC를 대체하지 않는다.

이후 raw census는 live chunk 141개, user page 142개, 빈 data page 0개다. 기존 sector 2개에서 3개로 증가했다. 원래 빈 VPID 20개 모두 다시 점유됐고, 그 page LSA는 barrier `198|13640` 이상이면서 새 sector의 첫 live page LSA `209|1496`보다 작다. 전체 값·MD5·물리 flag 검사도 통과했다.

따라서 이 대조에서는 기존 빈 공간이 새 sector의 레코드보다 먼저 재사용됐다. 특정 growth-sweep 호출이나 각 deallocation의 최종 enum을 직접 기록한 증거는 아니다. Bestspace를 통한 재사용과 sweep을 통한 반환·재할당의 비중도 이 자료로 나누지 않는다.

### Abort의 추가 두 페이지

a11의 VPID `1|1312`, `1|1313`은 batch horizon보다 오래된 LSA를 가지지만 candidate 목록과 gate 기록에 없다. 이 두 페이지를 source line breakpoint로 좁힌 a13·a14에서는 지정한 VPID와 callback 출력이 달랐다. 해당 residual 기록은 전부 제외했다. 명시적 frame 선택으로도 불일치가 해소되지 않아, 원인을 stale frame으로 확정하지 않는다.

a15는 함수 symbol의 진입을 관측했다. 두 VPID 각각에서 record 1개를 가진 `oos_rv_redo_delete` 호출을 확인했고 stack에는 `log_rollback`이 있다. [Recovery table](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/transaction/recovery.c#L881)은 이 함수를 `RVOOS_INSERT`의 undo로 연결한다. [실제 callback](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/oos_file.cpp#L3672)은 slot을 삭제하고 reclaim hint를 갱신한다.

이어지는 insert의 성장 경로에서 두 VPID 각각의 `oos_try_reclaim_page_internal` 진입을 세 번 기록했다. Caller는 `oos_reclaim_sweep_step`, horizon은 `182|14448`, rollback CLR hint는 `183|8288`이다. 정지 후 raw census에서 두 페이지는 모두 비어 있고 page LSA는 각각 `182|14640`, `182|14576`이다. 두 LSA 모두 관측한 horizon보다 크며 equality 예외도 충족하지 않는다.

이 결과는 rollback에서 남은 빈 페이지가 성장 경로에 도달했으나 당시 LSA 조건으로는 반환할 수 없었다는 설명을 뒷받침한다. 뒤이은 vacuum batch가 이 두 VPID를 새 삭제 후보로 전달하지 않은 사실과도 일치한다. 단, 성장 함수 진입 시 page LSA와 실제 latch·최종 reclaim enum을 함께 기록하지 못했다. 마지막 비교는 이후 raw LSA와 진입 horizon을 연결한 추론이다. a15의 나머지 빈 페이지 6개는 같은 VPID·raw LSA의 실제 gate 입력 거부와 직접 연결된다.

### 회수 요구사항에 대한 판단

명세는 모든 완전히 빈 data page의 eventual return과, 안전하게 회수 가능한 빈 페이지가 있을 때 새 sector를 예약하지 않을 것을 요구한다. 20초나 고정 plateau는 규정하지 않는다. 구현 주석의 "idle files are never shrunk"로 이 요구를 축소하지 않는다.

이번 관측은 안전 gate에서의 유예와 이후 재시도 조건을 설명한다. 성장 대조 한 건은 실제 재사용 순서를 뒷받침한다. 일반적인 eventual-return 적합성이나 모든 concurrency 조건의 성장 불변식을 인증하지 않는다. 후속 처리는 idle 유예 페이지의 재방문 요구를 엔진과 TC에서 어떻게 검증할지 명확히 하는 것이다. 기존 조건을 단순히 완화하거나 timeout만 늘려 PASS로 바꾸지 않는다.

## SA compact는 현재 representation을 inline으로 재작성

동일한 fixture는 3000B payload를 가진 row에 2500B default column을 lazy ADD한다. 원래 저장된 representation은 1이며 논리 SELECT는 추가 default를 제공한다. 진단은 별도 SQL로 `t_reprid`, `t_length`, `t_flags`를 읽어 기존 parser 입력을 유지했다.

| 동작 | 물리 representation | 저장 길이 | Flags | HAS_OOS와 owner |
| --- | --- | --- | --- | --- |
| ADD 뒤, compact 이전 | 1 | 3040B | 1 | 없음 |
| a08 SA compact | 2 | 5544B | 0 | 없음. 원래 두 assertion은 FAIL. |
| 같은 row의 일반 UPDATE | 2 | 2576B | 13 | 있음. 전체 값과 owner 검사 통과. |
| a10 새 fixture의 CS compact | 2 | 2576B | 13 | 있음. 해당 진단 control은 native PASS. |

a08은 같은 OID에서 representation과 실제 길이가 바뀌었고 전체 값도 맞았다. 물리 재작성 자체가 없었다는 가설은 배제했다. SA writer는 `desc_obj_to_disk`로 현재 형식의 일반 값을 직렬화한 뒤 `heap_update_logical`을 직접 호출한다. Attribute-layer OOS layout planner를 거치지 않는다. CS 경로는 representation이 다르면 attribute update를 수행한다. [SA writer](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/executables/compactdb.c#L655), [직렬화](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/loaddb/load_object.c#L490), [CS rewrite](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/compactdb_sr.c#L257), [일반 DML 변환](https://github.com/CUBRID/cubrid/blob/e3589ae42d42b04eb020e1ae43e165b01d31b12a/src/storage/heap_file.c#L14194)을 확인했다.

이 차이가 새 진단의 물리 결과를 설명한다. 원래 `gap_compact_sa_cs`는 계속 FAIL이다. a10은 동일 값과 stale representation을 가진 새 fixture에서 wrapper의 mode만 CS로 바꾼 대조다. 원래 SA TC의 PASS로 합산하지 않는다. 이 fixture는 기존 OOS stub에서 시작하지 않으므로 compact의 모든 Expand·stub 처리까지 검증하지 않는다.

명세의 demotion은 INSERT와 UPDATE에 명시돼 있다. Compact의 내부 lazy-default rewrite에도 같은 배치를 요구하는지는 별도 계약 판단이다. SA 경로 차이를 엔진 수리 대상으로 삼을지, TC의 물리 기대를 조정할지는 이 계약을 명확히 한 뒤 결정한다. 이번 작업에서는 어느 쪽도 변경하지 않았다.

## 관측 영향과 실패 시도의 보존

GDB는 log level을 변경하고 breakpoint에서 프로세스를 멈춘다. 일부 최적화된 frame에서는 gate 인자를 읽지 못했다. 불완전한 행은 거부 근거로 사용하지 않았다. Raw VPID와 LSA의 일치까지 요구하여 다른 frame의 값을 잘못 연결하는 일을 막았다.

| 시도 | 관측 결과와 한계 |
| --- | --- |
| a02 | 무계측 원문 세 cycle의 `churn_insert_delete` FAIL을 재현했다. 값·최종 phase·정리는 정상이다. |
| a05 | 추가 관측 열을 기존 parser에 넣어 compact 전에 중단됐다. 진단 입력 오류로 보존했다. |
| a07 | 원문 세 cycle은 FAIL. Host GDB의 target-file 읽기 실패로 gate 증거를 얻지 못했다. |
| a08, a10 | 별도 물리 SQL과 DML·CS 대조. SA 원래 assertion은 FAIL, CS control은 PASS. |
| a09 | Horizon sampling 전에도 멈춘 첫-cycle 변형은 2 page로 복귀했다. 관측이 timing을 바꿀 수 있음을 확인했다. |
| a01 | 전역 page-gate breakpoint가 abort 뒤 INSERT를 늦춰 내부 40초 command 제한에 도달했다. 원인 진단의 완료 근거로 쓰지 않는다. |
| a03, a04, a11, a12 | 첫 cycle의 기존 20초 조건을 유지했다. 추가 cycle을 생략한 진단이며 원래 전체 TC의 대체 판정이 아니다. a12는 이후 별도 pressure 대조를 수행했다. |
| a06 | 원래 snapshot과 세 churn cycle 뒤에 두 raw census를 추가했다. |
| a13 | 표적 조건과 callback의 VPID가 달랐다. Residual-page 기록은 원인 근거에서 제외했다. |
| a14 | Frame 선택과 raw page identity를 추가했으나 callback의 target 불일치가 남았다. Residual 원인 근거로 쓰지 않는다. |
| a15 | Undo와 성장 reclaim 함수의 실제 진입으로 두 VPID를 관측했다. Return probe는 결과를 확보하지 못했으므로 최종 enum은 주장하지 않는다. |

진단 invocation 제한은 a02·a05의 120초, 이후의 240초를 구분한다. 원래 TC의 120초 verdict를 변경한 것이 아니다. 완료한 각 invocation은 소유 프로세스·관측 namespace holder가 없고 testcase 설정을 복원했음을 확인했다.

## 재검증과 남은 작업

Raw root는 `/home/vimkim/temp/cbrd26659-unknown6-hj1otgcl`다. 입력 inventory, 진단 patch, attempt별 identity·config·preflight, GDB JSONL·probe, native dispatch·FIN·status·XML, journal·cleanup, allocation JSON과 raw page binary를 Git 밖에 보존했다. [재검증기](tools/verify-reclaim-compact.py)는 DB를 실행하지 않는다.

```sh
python3 cbrd-26659/tools/verify-reclaim-compact.py \
  --root /home/vimkim/temp/cbrd26659-unknown6-hj1otgcl
```

검증기는 원문 source identity와 config, 단일 dispatch·FIN·XML·status, 정리 결과, 물리 page header·slot·LSA·allocation roster, gate 입력, compact 물리 결과와 pressure의 재사용 순서를 대조한다. 출력의 `retained_evidence_crosscheck`는 증거 정합성 판정이며 전체 TC의 PASS 인증이 아니다. Raw root가 보존돼 있어야 재실행할 수 있다.

Raw binary 한 바이트를 잘라낸 음성 대조에서 검증기는 exit 1로 거부했다. Compact의 물리 관측값이 달라지면 실패하며, 불완전한 gate sample과 a13·a14의 target 불일치 자료를 원인 증거로 승격하지 않는다.

남은 사항은 horizon을 제한한 실제 undo source와 abort 두 페이지의 latch·최종 enum, idle eventual return과 compact rewrite의 계약·TC 처리 결정, 기존 Engine 차이의 후속 연결, 실제 TC 리뷰·병합이다. QA의 heavy·장시간·HA 환경·주기·담당 합의와 다른 기존 TODO도 유지한다. 정규 Engine·TC 저장소의 수정·push와 CI trigger는 하지 않았다.

`Fix Root Causes`는 count 대신 gate와 실제 페이지를 연결하는 선택에 적용했다. `Prove It Works`는 raw binary와 실행 결과를 대조하는 선택에 적용했다. `Build the Lever`와 `Model the Domain`은 고정된 case·attempt 표로 재검증기를 구성하는 선택에 적용했다. `Sequence Work into Verifiable Units`는 source 조사, serial native 관측, 대조, 문서 검증의 순서에 적용했다. `Guard the Context Window`는 두 source 조사와 독립 합성으로 큰 자료를 나눈 선택에 적용했다. `Attack the Premise`는 관측이 중립적이라는 전제를 버리고 timing 대조와 raw identity 검사를 추가하는 선택에 적용했다.
