# CBRD-26659 policy helper 그룹 잔여 38개 native 검증

작성일은 2026-11-03, Asia/Seoul이다. OOS 작성자와 TC 리뷰어가 policy helper 이동 후 미검증이던 38개의 현재 결과와 다음 조치를 판단하도록 작성했다. Work699는 로컬 검증과 결과 분류까지이며, 상위 Work456의 완료와 구분한다.

**38개를 각각 한 번씩 직렬 실행한 결과는 37 PASS·1 FAIL·0 SKIP·0 TIMEOUT·0 미실행이다.** FAIL은 `cbrd_26659_partition_repartition`이다. 모든 runner가 exit 0으로 종료했지만 이 TC의 원래 assertion은 실패했고 focused verifier가 이를 거부했다. 각 실행의 관측된 작업 소유 프로세스와 private namespace holder는 종료 후 모두 0이며, 최종 생존 검사도 0이다. Engine·TC 기대값 변경이나 CI 실행은 하지 않았다.

## 모집단과 정확한 실행 리비전

[과거 shell 61개 분류](CBRD-26659-shell61-classification_20261030_e3589ae_codex.md)의 G01은 `policy_ddl.sh` 누락 증상이 있던 39개다. [공용 helper 이동 검증](CBRD-26659-policy-helper-relocation_20261031_6334dc6_codex.md)에서 TC `6334dc6`의 `gap_ctas_cs` 한 개가 이미 검증되었으므로 제외했다. 이번 38개는 그 잔여 집합이며 shell_heavy 이관 38개와는 별도 집합이다. 과거 실패의 원인이 모두 같다는 뜻은 아니다.

| 구성요소 | 고정한 값 | 범위와 수정 상태 |
| --- | --- | --- |
| Engine | `e3589ae42d42b04eb020e1ae43e165b01d31b12a` | Work456의 OptDebug producer. 실행 소스 checkout의 기존 CCI/JDBC dirt를 보존했다. |
| TC | `01df2600ac75180812451462b5c044cfa56b732a` | `CUBRID/cubrid-testcases-private-ex:tc/pr-8128`, PR #4365. 시작 시 clean이며 이 실행에서 수정하지 않았다. |
| 설치 | `/home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID` | 이전 producer와 runtime 6개 fingerprint가 같다. 각 attempt에 독립 복사했다. |
| testkit | `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a` | 설치 바이너리 SHA-256, version은 `cubrid-testkit dev`. 새 설치·업데이트나 legacy runner 대체는 없다. |
| CTP 자산 | `9c62858b10005d721546cc007be260844033b9e9` + 기존 수정 | 실제 사용한 자산 snapshot과 status·diff를 `seed/`에 보존했다. |

기본 debug 설치는 `1ef86a7`을 보고하여 source/install preflight가 거부했다. 이 설치를 사용하거나 mismatch 예외를 적용하지 않았다. 이후 모든 attempt에서 `e3589ae` producer와 소스의 일치 검사를 통과했다. 이번 결과는 현재 대화의 PR #8347 head나 최신 통합 head의 검증이 아니다.

## 실행과 판정 방법

고정 TC Git 객체에서 입력을 복사하고 비활성 진입점 38개만 scratch corpus의 원래 `shell/.../cases/<name>.sh` 경로로 투영했다. 진입점 bytes는 과거 manifest와 모두 같고, 원래 assertion·helper bytes·내부 timeout은 바꾸지 않았다. 공용 helper를 포함한 현재 입력 536개의 bytes·mode와 Git 객체 대응을 기록했다. 실제 TC 저장소의 활성·비활성 선택은 유지했다.

각 native 호출마다 설치·CTP·HOME·registry·TMP·cache·slot root를 분리했다. `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell`을 사용했다. 한 slot, `scenario_disk=on`, 정확히 한 expected case, file feedback이며 update·retry·continuation·case patch는 껐다. Native testcase timeout과 외부 invocation 제한은 각각 120초다. 외부 제한은 준비·TC·정상 정리를 포함하며, 종료 유예는 별도 10초다. 이번 실행에서는 이 제한에 걸린 TC가 없다.

판정은 runner 종료값과 별도로 expected·dispatch·FIN, status·feedback·JUnit·test log와 assertion 결과를 대조했다. 마지막 증거 검증은 모집단, 536개 입력, 실행 identity와 runtime fingerprint, raw native 판정, 최종 작업 소유 프로세스·관측 namespace를 다시 확인했다. 증거 검증 통과는 FAIL TC가 PASS라는 뜻이 아니다.

## 개별 결과

Attempt 번호는 보존 root의 `a01`부터 `a38`까지다. 정리는 각 attempt에서 관측한 작업 소유 프로세스와 private pid·ipc·mnt·user namespace holder가 없음을 뜻한다.

| 번호 | TC | 판정 | runner exit | focused verifier exit | 정리 |
| --- | --- | --- | --- | --- | --- |
| 01 | `cbrd_26659_gap_ctas_sc` | PASS | 0 | 0 | 정상 |
| 02 | `cbrd_26659_gap_load_cs_cs` | PASS | 0 | 0 | 정상 |
| 03 | `cbrd_26659_gap_load_cs_sc` | PASS | 0 | 0 | 정상 |
| 04 | `cbrd_26659_gap_load_sa_cs` | PASS | 0 | 0 | 정상 |
| 05 | `cbrd_26659_gap_load_sa_nolog_cs` | PASS | 0 | 0 | 정상 |
| 06 | `cbrd_26659_gap_load_sa_nolog_sc` | PASS | 0 | 0 | 정상 |
| 07 | `cbrd_26659_gap_load_sa_sc` | PASS | 0 | 0 | 정상 |
| 08 | `cbrd_26659_gap_replace_select_cs` | PASS | 0 | 0 | 정상 |
| 09 | `cbrd_26659_gap_replace_select_sc` | PASS | 0 | 0 | 정상 |
| 10 | `cbrd_26659_gap_unload_sa_cs` | PASS | 0 | 0 | 정상 |
| 11 | `cbrd_26659_gap_unload_sa_sc` | PASS | 0 | 0 | 정상 |
| 12 | `cbrd_26659_partition_add_drop_list` | PASS | 0 | 0 | 정상 |
| 13 | `cbrd_26659_partition_add_drop_range` | PASS | 0 | 0 | 정상 |
| 14 | `cbrd_26659_partition_hash_coalesce` | PASS | 0 | 0 | 정상 |
| 15 | `cbrd_26659_partition_hash_resize` | PASS | 0 | 0 | 정상 |
| 16 | `cbrd_26659_partition_move` | PASS | 0 | 0 | 정상 |
| 17 | `cbrd_26659_partition_partition_rejection` | PASS | 0 | 0 | 정상 |
| 18 | `cbrd_26659_partition_promote_list` | PASS | 0 | 0 | 정상 |
| 19 | `cbrd_26659_partition_promote_range` | PASS | 0 | 0 | 정상 |
| 20 | `cbrd_26659_partition_remove` | PASS | 0 | 0 | 정상 |
| 21 | `cbrd_26659_partition_reorganize_list` | PASS | 0 | 0 | 정상 |
| 22 | `cbrd_26659_partition_reorganize_list_merge` | PASS | 0 | 0 | 정상 |
| 23 | `cbrd_26659_partition_reorganize_range` | PASS | 0 | 0 | 정상 |
| 24 | `cbrd_26659_partition_reorganize_range_merge` | PASS | 0 | 0 | 정상 |
| 25 | `cbrd_26659_partition_repartition` | FAIL | 0 | 1 | 정상 |
| 26 | `cbrd_26659_partition_route_hash` | PASS | 0 | 0 | 정상 |
| 27 | `cbrd_26659_partition_route_list` | PASS | 0 | 0 | 정상 |
| 28 | `cbrd_26659_partition_route_range` | PASS | 0 | 0 | 정상 |
| 29 | `cbrd_26659_policy_contract` | PASS | 0 | 0 | 정상 |
| 30 | `cbrd_26659_schema_attributes_cs` | PASS | 0 | 0 | 정상 |
| 31 | `cbrd_26659_schema_attributes_sa` | PASS | 0 | 0 | 정상 |
| 32 | `cbrd_26659_schema_rewrites_cs` | PASS | 0 | 0 | 정상 |
| 33 | `cbrd_26659_utility_compact_cs` | PASS | 0 | 0 | 정상 |
| 34 | `cbrd_26659_utility_compact_sa` | PASS | 0 | 0 | 정상 |
| 35 | `cbrd_26659_utility_policy_cs` | PASS | 0 | 0 | 정상 |
| 36 | `cbrd_26659_utility_policy_sa` | PASS | 0 | 0 | 정상 |
| 37 | `cbrd_26659_utility_policy_sa_nolog` | PASS | 0 | 0 | 정상 |
| 38 | `cbrd_26659_utility_policy_unload_sa` | PASS | 0 | 0 | 정상 |

## REPARTITION 실패와 남은 원인 판단

`a25`는 1 FAIL이며 runner exit 0, focused verifier exit 1이다. `default`와 `force_outline`의 별도 controller log에서 각각 유일한 실패는 `partition_existing.root_has_no_oos`다. TC `01df2600a`의 `shell/_40_guava/oos_common/oos08_partitions.sh:118`은 `.has_oos_file==0`을 검사한다. 마지막 정책의 보존된 `SHOW HEAP OOS` stdout은 루트 `dba.partition_rows`의 `Has_oos_file: 1`을 보여 준다.

관측 분류는 **루트의 OOS 파일 존재에 대한 TC 기대와 현재 Engine 관측의 불일치, 귀속 미확정**이다. Helper 경로 누락이나 timeout으로 판정하지 않는다. 이번 자료만으로 데이터 손상·메모리 누수·새 회귀라고 확정하지 않는다. [과거 ticket08](ticket08-schema-and-partition-ownership-20261021.md)의 소유권 실패는 Engine `d13aebf`의 별도 기록이므로 같은 내부 원인으로 합치지 않는다.

두 controller log와 JUnit 실패 본문, 마지막 정책의 `root_owner.stdout.log`는 보존됐다. 반면 controller가 출력한 `$CUBRID/oos08_evidence/*.tar.gz` 두 경로와 `root_owner.json`의 실제 파일은 attempt 및 native 결과 묶음에 없다. 두 정책의 archive owner snapshot을 읽었다고 주장하지 않는다. FAIL 판정의 원본 근거는 남아 있으나, 이 부가 자료 부재가 상세 원인 분석의 한계다.

다음 조치는 파티션 전환 뒤 루트 OOS 파일의 생명주기 계약과 이 기대값을 대조하여 Engine·TC 귀속을 정하는 것이다. 이번 작업에서 기대값 수정·재활성화·수리·추가 재실행·push·CI·PR 조작은 하지 않았다.

## 보존 자료와 재검증

- 실행 root는 `/home/vimkim/temp/w699-86n0wyna`다. `manifest.json`·`input-inventory.json`, `seed/`, `a01/`부터 `a38/`, `results.json`, `failure-a25.json`, `final-proof.json`을 보존한다.
- 각 attempt에는 `identity.json`, `preflight.log`, `environment.json`, `expected-cases.txt`, `conf/shell.conf`, `command.json`, `run.log`, `exit.status`, `verify.log`·`.status`, `observation.json`, `result.json`과 CTP 원본 결과가 있다.
- append-only 판단 기록과 workflow는 `/mnt/nvme/data-5/tmp/CBRD-26659-Work699-policy38-20261102/`에 있다. 초기 preflight 실패, 증거 추출 실패와 그 정정도 남긴다.
- [증거 검증기](tools/verify-policy38-native.py)는 이 보고서의 모집단·입력·판정·정리 근거를 다시 확인하므로 함께 보존한다. Raw log·snapshot·설치·생성 inventory는 Git 밖에 둔다.

다음은 TC를 실행하지 않는 실제 증거 재검증 명령이다.

```sh
python3 cbrd-26659/tools/verify-policy38-native.py \
  --root /home/vimkim/temp/w699-86n0wyna \
  --testcases /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128
```

아래는 기존 증거를 덮어쓰지 않는 단일 TC 재실행 예다. Engine checkout이 같은 `e3589ae`이고 고정 testkit이 남아 있어야 한다. `25`는 위 표의 REPARTITION이며 다른 번호도 같은 방식이다.

```sh
TASK_REPLAY_ROOT=$(mktemp -d /home/vimkim/temp/w699-replay-XXXXXXXX)
cp -a --reflink=auto /home/vimkim/temp/w699-86n0wyna/{seed,corpus,manifest.json,input-inventory.json,prepare.py,run.py,collect.py} "$TASK_REPLAY_ROOT/"
direnv exec /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover python3 "$TASK_REPLAY_ROOT/prepare.py" 25
python3 "$TASK_REPLAY_ROOT/run.py" 25
python3 "$TASK_REPLAY_ROOT/collect.py" 25
```

이 재실행 명령은 보고서의 보존된 첫 시도와 별도 실행이다. 첫 FAIL을 후속 PASS로 지우지 않는다. 이전 대표 1개와 이번 38개를 같은 리비전의 39 PASS로 합산하지 않으며, 과거 shell 61개 전체·일반 CI·heavy·HA나 상위 Work456의 완료를 인증하지 않는다.
