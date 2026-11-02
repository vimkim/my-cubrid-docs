# CBRD-26659 REPARTITION 실패 원인과 루트 OOS 파일 연결

작성일은 2026-11-03, Asia/Seoul이다. OOS 작성자와 TC 리뷰어가 `partition_existing.root_has_no_oos` 실패의 Engine·TC 귀속과 후속 수정 범위를 판단하도록 작성했다. 범위는 원래 TC 재현, 정책별 증거 보존, 최소 SQL과 대조 실험, 명세·소스 대조다.

**이번 FAIL의 직접 원인은 기존 OOS 파일이 있던 heap을 파티션 루트로 바꾼 뒤에도 파일 연결이 남을 수 있다는 상태를 TC가 허용하지 않는 것이다.** `Has_oos_file`은 heap header의 OOS VFID 연결을 나타내며, 레코드의 `HAS_OOS`나 OOS chunk 수가 아니다. SA 대조는 루트의 OOS 레코드가 0이어도 같은 파일 연결과 `Has_oos_file=1`이 남는 상태를 실제로 확인했다. 명세는 파티션 전환 직후 연결을 반드시 없애라고 요구하지 않는다. 따라서 이 predicate의 실패를 Engine chain 누수의 증거로 사용할 수 없다.

원래 TC는 그대로 FAIL이다. Engine이나 실제 TC 저장소의 코드·기대값·활성 상태를 고치지 않았고, TC 수정 후 원래 전체 검사가 통과한다고 인증하지 않는다.

## 정확한 리비전과 증거 범위

| 구성요소 | 값과 범위 |
| --- | --- |
| Engine | `vimkim/cubrid`, `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, OptDebug producer. 기존 CCI/JDBC dirt 보존. |
| TC | `CUBRID/cubrid-testcases-private-ex:tc/pr-8128`, `01df2600ac75180812451462b5c044cfa56b732a`. 저장소는 clean 유지. |
| 원래 실패 | [Work699의 37 PASS·1 FAIL](CBRD-26659-policy38-native_e3589ae_20261103_work699_codex.md) 중 `cbrd_26659_partition_repartition`. |
| 명세 | `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`, 문서 수정일 2026-10-27. 전체 읽기 전후 SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`. Snapshot 보존. |
| 실행 도구 | testkit SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, explicit native shell·containment. 기존 설치를 업데이트하지 않았다. |
| 자산 | Work699의 고정 producer·CTP seed·TC corpus를 복사했다. 각 호출의 설치·registry·HOME·TMP·slot root가 독립적이다. |

모든 실행은 한 slot과 `scenario_disk=on`, 정확히 한 expected case를 사용했다. 원래 TC 재현은 입력을 바꾸지 않았다. 최소화와 대조는 scratch의 entry·controller 두 경로만 진단용으로 바꾸고 patch·설정을 기록했다. 이 진단 변형의 결과는 실제 TC 수정이나 suite 통과 실적이 아니다.

## 원래 두 정책의 FAIL과 회수한 자료

`replay02`에서 원래 TC를 다시 실행했다. Runner exit 0, native 1 FAIL, focused verifier exit 1이며, 각 정책의 유일한 controller assertion 실패는 `partition_existing.root_has_no_oos`였다. `default`와 `force_outline` 모두 루트 `Has_oos_file=1`, `Oos_num_recs=2`였다. 값·배치·raw ownership에 대한 다른 원래 controller 검사는 추가 FAIL을 내지 않았다.

이번에는 외부 관측기가 소유 process의 `/proc/<pid>/root`와 cwd를 통해 namespace 종료 전 부가 자료를 복사했다. TC entry·helper·oracle는 바꾸지 않았다. 정책별 tar는 각각 116개 member를 가지며, 파일 SHA-256이 TC가 출력한 hash와 일치한다. 두 `root_owner.json`을 archive에서 직접 추출해 대조했다.

| 정책 | 보존 archive SHA-256 |
| --- | --- |
| default | `67a6671b0c1bfbe6fa3ffab09067d3cd966629a55869b3dbce2c0234707356a9` |
| force_outline | `bec0a6aaf3ef5a76a95e41f93a7707156e4b31f884528d2db385e1f6be664143` |

Work699에서 없던 부가 owner 자료는 이번 별도 실행에서 확보했다. 과거 시도에 그 파일이 있었다고 소급해서 주장하지 않는다.

## 최소화와 대조가 구분한 것

원래 세 행에서 한 행으로 줄인 뒤, `note`, PK, 복잡한 payload 구성, 두 번째 partition을 순서대로 제거해도 같은 predicate가 실패했다. 각 제거 뒤 native 결과와 정리를 확인했다. 남은 핵심은 두 컬럼, OOS로 저장되는 한 행, 한 range partition이다.

실제로 실행한 최소 SQL의 핵심은 다음과 같다. 원래 진단에서는 격리 DB와 개별 CSQL 호출로 실행했다.

```sql
create table partition_rows(id int, payload bit varying storage default);
insert into partition_rows values(2, cast(repeat('a1',5000) as bit varying));
commit;
show heap oos of partition_rows;
alter table partition_rows partition by range(id)
  (partition p0 values less than maxvalue);
show heap oos of partition_rows;
show heap oos of partition_rows__p__p0;
```

최소 red signal이 나온 뒤 4개 가설을 기록했다. 파일 연결과 데이터 존재를 혼동한 oracle, MVCC 회수 대기만의 영향, eager chain 정리 결함, 잘못된 SHOW·parser 관측을 구분했다. SA 변경은 최소 CS와 mode만 다르며, 작은 값 대조는 최소 CS와 payload만 다르다. 모든 대조는 목적지의 한 행과 전체 payload 일치도 확인했다.

| 진단 | 루트 전환 전 Has / records | 루트 전환 후 Has / records | 목적지 Has / records | 원래 predicate 결과 |
| --- | --- | --- | --- | --- |
| CS, 큰 값, `mre06r` | 1 / 1 | 1 / 1 | 1 / 1 | FAIL |
| SA, 같은 큰 값, `mre07` | 1 / 1 | 1 / 0 | 1 / 1 | FAIL |
| CS, 작은 값, `mre08r` | 0 / 0 | 0 / 0 | 0 / 0 | PASS |

SA에서 루트의 class OID·HFID·OOS VFID는 전환 전후 같았고, 목적지 VFID는 달랐다. 원본 OOS chunk 정리와 heap-header 파일 연결 유지가 별개임을 보여 준다. 작은 값에서는 그 파일이 처음부터 할당되지 않았다. Raw SHOW와 parser 결과도 일치했다.

MVCC 대기는 CS의 물리 chunk 통계에 영향을 줄 수 있지만 이 flag 실패의 단독 원인은 아니다. SA에서 chunk 수가 0이어도 flag가 1이기 때문이다. 이 결과는 모든 CS vacuum 경로나 reclaim의 정확성을 인증하는 대조가 아니다.

## 소스와 명세가 설명하는 경로

아래 소스 위치는 모두 Engine `e3589ae` 기준이다.

| 역할 | 소스 근거와 사실 |
| --- | --- |
| 기존 테이블의 파티션 전환 | `src/query/execute_schema.c:6967`의 `PT_APPLY_PARTITION`이 분배 작업으로 이어진다. `:5834`는 `UPDATE ... SET key=key`를 실행한다. heap 자체 교체가 아니다. |
| 행 이동 | `src/transaction/locator_sr.c:5453`의 이동 경로는 목적지 `locator_insert_force()` 성공 뒤 원본 `locator_delete_force_for_moving()`을 호출한다. |
| SA 원본 chain 정리 | `src/storage/heap_file.c:24293`은 non-MVCC home DELETE 전에 `heap_oos_delete_unreferenced()`를 호출한다. `src/storage/heap_oos.cpp:994` 이후는 source VFID의 chain을 삭제한다. |
| SHOW의 파일 조회 | `src/storage/heap_oos.cpp:1193`은 `heap_oos_find_vfid(..., false)`로 기존 연결을 읽는다. SHOW가 새 파일을 만들어 낸 관측이 아니다. |
| flag와 통계 | `src/storage/oos_file.cpp:3843`은 VFID가 있으면 먼저 `has_oos_file=1`을 설정한다. 이후 data page의 slot을 세어 `num_recs`를 기록한다. 두 필드는 독립적이다. |
| 연결의 생성·reset·파괴 | `src/storage/heap_file.c:4985`는 생성 시 NULL 초기화, `:5383`은 heap reuse 시 reset, `:13309`는 lazy 생성한 VFID 저장이다. `:5553`과 `:5616`의 heap 파괴 경로는 `oos_remove_file()`을 호출한다. 조사한 전환 경로에는 header 연결을 NULL로 만드는 호출이 없다. |

명세 §4의 file association은 heap당 최대 하나의 OOS 파일과 heap header의 VFID 저장을 정한다. §4의 MVCC와 reclaim은 chunk 삭제, 빈 page 회수, 파일 연결을 구분한다. §5는 heap DROP 시 연결 파일 파괴를 요구한다. 기존 heap을 파티션 루트로 바꿀 때 즉시 `Has_oos_file=0`으로 만들라는 요구는 찾지 못했다.

[보강 spec](supplement-spec-work456-20261021.md)과 [ticket08](supplement-tickets/issues/08-schema-and-partition-ownership.md)도 실제 destination heap과 물리 소유권의 검증을 요구한다. 파일 연결 자체가 없어야 한다는 assertion과 현재 destination record의 chain owner가 맞아야 한다는 요구를 동일하게 취급하지 않는다.

## 후속 TC 수정 제안

직접 원인이 있는 위치는 TC `01df2600a`의 `shell/_40_guava/oos_common/oos08_partitions.sh:118`이다. `children08()`의 공통 `.has_oos_file==0` 검사가 기존 데이터가 있던 `repartition`에도 적용된다. 이 시나리오는 원래부터 partitioned인 빈 root와 달리 이미 OOS 파일을 가진 heap에서 시작한다.

수정 범위는 이 기존-root 시나리오의 oracle로 제한하는 것을 제안한다. 전환 전후 root association·통계는 증거로 남기고, 즉시 파일 부재를 요구하는 조건을 제거하거나 해당 상태에 맞게 재정의한다. `Has_oos_file==1`로 고정하는 답안 변경도 제안하지 않는다. 작은 값 대조처럼 애초에 할당하지 않은 상태도 유효하기 때문이다.

전체 값 비교, 실제 child heap 배치, raw OOS chain의 destination ownership 검사는 그대로 유지해야 한다. 다른 partition 시나리오의 검사까지 일괄 삭제하지 않는다. 수정 후에는 원래 두 정책을 모두 포함한 TC를 다시 실행해 그 전체 verdict와 정리를 확인해야 한다. 이번 작업은 이 TC 수정을 구현하지 않았다.

## 시도 보존과 한계

| 시도 | 관측과 처리 |
| --- | --- |
| `replay01` | 외부 sampler가 작성 중 gzip을 읽다 EOFError로 중단했다. Runner exit을 잃었으므로 전체 시도는 INCONCLUSIVE다. Raw TC FAIL과 오류 이후 현재 소유 process 0개 관측만 보존한다. |
| `replay02` | EOF를 일시적 sampling 상태로 처리한 새 시도다. 원래 TC FAIL, runner 0, 두 정책 archive/JSON hash 검증과 정리 완료. |
| `mre01`부터 `mre06` | 하나씩 줄인 모든 입력에서 같은 root predicate FAIL. 각 실행의 관측과 patch 보존. |
| `mre07` | SA의 chunk 수 0·association 1 대조. 같은 predicate FAIL이며 정리 완료. |
| `mre08` | 대상 predicate는 통과했지만 진단 controller가 완료 marker를 생략해 framework 전체는 FAIL. 유효한 green control로 세지 않는다. |
| `mre06r`, `mre08r` | 원래 framework 완료 protocol을 복원한 별도 red/green pair다. 큰 값 FAIL, 작은 값 PASS이며 각각 정리 완료. 이전 실패 기록은 유지한다. |

보존 root는 `/home/vimkim/temp/w702-9n8to_43`이다. `decisions.tsv`, `workflow.md`, 원래 두 policy archive·owner JSON, 각 attempt의 preflight·입력 patch·native log·XML·runner exit·정리 기록, `hypotheses.md`, `source-flow.json`, `spec-snapshot.md`, `conclusion.json`과 증거 검증 결과를 남긴다. Raw corpus·설치·inventory·prototype는 Git 밖의 이 root에 둔다.

이번 대조에서 SA root의 empty data page가 eventual reclaim되는지, CS의 모든 오래된 version chain이 vacuum으로 회수되는지는 확인하지 않았다. `Oos_num_recs=0`은 일반적인 동시 실행 중 통계에서는 busy page skip의 영향도 받을 수 있다. 이번 SA 자료는 격리한 동일 DB의 순차 호출과 eager-delete 소스를 함께 대조한 것이며 모든 회수 불변식의 증명이 아니다. DROP 동작도 실제 실행하지 않았으며 해당 경로 설명은 소스 근거다.

증거 검증기의 늦은 namespace 검사에서도 별도 관측 오류를 확인했다. 처음에는 PID 1055808이 귀속 확인 전에 종료해 원인을 확정하지 못했다. 이후 검사는 이미 끝난 Work702 namespace 번호와 같지만 설치·slot 경로가 독립 Work704인 process들을 잡았다. 저장된 PID 세대와 비교했고, 그 시작 시각은 해당 Work702 시도가 끝난 뒤였다. Namespace 번호만으로 장시간 뒤 소유권을 판정할 수 없다는 실제 반례다.

새 진단 검증기와 [기존 Work699 검증기](tools/verify-policy38-native.py)는 PID·start tick 세대와 정확한 설치·slot 경로로 작업 소유권을 함께 확인하도록 수정했다. 명확히 다른 작업의 번호 재사용은 별도로 기록하고, 작업 소유 또는 귀속 미확인 holder는 계속 실패로 처리한다. 두 검증기 모두 실제 artifact 검증을 통과했고 Work699의 37 PASS·1 FAIL도 유지됐다. 추가로 각 작업 경로를 가진 무해한 Python sleep process를 하나씩 띄워 두 검증기가 해당 PID 때문에 실패하는 것을 확인한 뒤 직접 종료했다. DB나 testkit을 새로 실행한 검사는 아니다. 다른 작업 process는 변경하지 않았다.

승인받은 Work699 문서 4파일은 `aed9e358e705cc099e88547c164d253dcee51d03`으로 `main`에 통합·push했고 원격 일치·clean destination·해당 task worktree/branch 정리를 확인했다. 이 새 진단 보고서는 별도 local task commit이며 그 통합·게시 승인은 아직 받지 않았다.

[증거 검증기](tools/verify-repartition-diagnosis.py)는 TC를 다시 실행하지 않고 정책별 archive, 원래 FAIL, 최소 red/green·SA 대조, protocol 오류 보존, source flag 계산과 정리 근거를 재확인한다.

```sh
python3 cbrd-26659/tools/verify-repartition-diagnosis.py \
  --root /home/vimkim/temp/w702-9n8to_43 \
  --engine /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover
```
