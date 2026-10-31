# CBRD-26659 남은 공용 helper 의존성과 선별 취약점

작성일은 2026-10-31, Asia/Seoul이다. TC 작성자와 QA 리뷰어가 `policy_metadata.sh`·`tde_observe.sh`의 후속 수리 범위를 정할 수 있도록 작성했다. 질문은 해당 helper를 실제로 사용하는 시나리오와, 소유 TC를 선택하지 않은 shard에서 필요한 파일의 생존 여부다. 관련 PR은 [Engine #8128](https://github.com/CUBRID/cubrid/pull/8128), [일반 TC #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365), [heavy TC #4627](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4627)이다.

**소스에서 두 helper에 도달하는 경로를 확인했고, 현재 파일을 복사한 fixture에서 소유 TC를 제외하면 helper가 삭제되는 것을 확인했다.** 일반 suite의 관련 진입점은 모두 비활성이다. Heavy crash 두 TC는 `OOS_CRASH_ENCRYPTION=AES`일 때만 TDE helper를 호출한다. 기본 `NONE` 실행을 이 경로의 검증으로 계산하지 않는다. 함수 정의만 남은 partition-lifecycle 경로도 호출 근거에서 제외했다.

이번 Work654는 의존성 조사와 최소 수리 제안까지다. Engine·TC 파일, 활성 선택, PR 본문은 변경하지 않았다. TC·DB·native runner·CI를 실행하지 않았다. 실행한 것은 실제 `keep case` 24회와 합성 진단 입력에 대한 parser 검사다. 후속 helper 이동이나 비활성 TC의 복원은 아직 구현하지 않았다.

## 조사 리비전과 helper 계약

| 구분 | 저장소와 고정 리비전 | 로컬 branch·상태 |
| --- | --- | --- |
| R, 일반 TC | `CUBRID/cubrid-testcases-private-ex`, `6334dc6cd74683ca6ba10439372a21bd36b453d3` | `tc/pr-8128`, clean |
| H, heavy TC | `vimkim/cubrid-testcases-private-ex`, `81e60724a30431282c08ae1f677bf8cefb3d95d7` | `CBRD-26659-oos-shell-heavy`, clean. PR의 원격 head ref `tc/pr-8128`과 구분 |
| 파일 선별 소스 | `CUBRID/cubridci`, `155c265eb6e3deef49ce828e6f2b5846d3a9abf5` | Git blob의 `docker/ci/docker-entrypoint.sh`를 그대로 실행 |
| Engine | `vimkim/cubrid`, `e3589ae42d42b04eb020e1ae43e165b01d31b12a` | 변경 없음. 기존 `cubrid-cci`·`cubrid-jdbc` dirt 보존 |

이하 R 경로는 `shell/_40_guava`, H 경로는 `shell_heavy/_40_guava`를 기준으로 한다. 비활성 경로는 R의 정규 경로 앞에 `disabled/failing/`, `disabled/heavy/`, `disabled/long_running/`을 붙이고 파일명 뒤에 `.disabled`가 붙은 형태다. H 안에 남아 있는 과거 일반 `shell` tree는 조사·수리 대상으로 계산하지 않았다.

[`policy_metadata.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/6334dc6cd74683ca6ba10439372a21bd36b453d3/shell/_40_guava/cbrd_26659_policy_contract/cases/policy_metadata.sh#L4)는 CSQL 출력 파일 하나를 받아 전체 quoted DDL field를 JSON 문자열로 만든다. 비어 있는 입력과 ERROR/FATAL을 거부하며 row marker와 `CREATE TABLE:` field가 각각 하나여야 한다. DDL의 속성·default·constraint·comment·table option을 유지한다. 다른 저장소 파일은 읽지 않는다. 이름이 비슷한 `oos_utility/policy_roundtrip.sh`의 함수 `policy_metadata`는 이미 공용 위치로 이동한 `policy_ddl.sh`를 사용하므로 이번 helper의 호출자로 계산하지 않는다.

[`tde_observe.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/6334dc6cd74683ca6ba10439372a21bd36b453d3/shell/_40_guava/cbrd_26659_tde_wal/cases/tde_observe.sh#L4)는 `identity`, `wal`, `parameters`, `owned` 명령을 받는다. 시작 시 항상 `"$here/../../oos_common/oos_json.sh"`를 source한다. `owned`는 추가로 같은 디렉터리의 `tde_headers.awk`를 실행하고 저장된 heap·OOS·class identity와 algorithm을 대조한다. 따라서 Bash 파일만 이동해서는 의존성이 닫히지 않는다. R과 H의 TDE helper·AWK·JSON helper는 각각 바이트가 같고 mode는 `100644`다.

| 파일 | 바이트 | SHA-256 |
| --- | ---: | --- |
| R `policy_metadata.sh` | 525 | `1d5df9878f4b3a5048b5458171043e513a69a4454e3744b448284b322d5ea048` |
| R·H `tde_observe.sh` | 4,023 | `6c191ad586f15ccdfeaa391872ae3b302564ddb74e9d70cbf6cf038e772fb3a2` |
| R·H `tde_headers.awk` | 1,714 | `1e1bf36310bacf53bb4540f9381d50ace1fb2576769f9698dc619172fbc50e97` |
| R·H `oos_json.sh` | 287 | `6321b5122661bd975f6be89be6c3aa6a1343f255c711de6864045bf1d064faa3` |

## 시나리오별 호출 경로

다음은 고정 리비전의 제어 흐름을 읽은 결과다. 해당 시나리오가 앞선 단계들을 통과하면 도달하는 경로이며, 이번 감사에서 TC를 실행했다는 뜻은 아니다. M은 `cbrd_26659_policy_contract/cases/policy_metadata.sh`, T는 `cbrd_26659_tde_wal/cases/tde_observe.sh`다.

| 진입점·상태 | helper에 도달하는 경로 | 조건·후속 의존성 |
| --- | --- | --- |
| R `schema_rewrites_sa`, `disabled/long_running` | `oos08_controller SA schema` → `oos08_schema` → `ddl_snapshot` → M | rejection 전후의 네 호출 |
| R `schema_rewrites_cs`, `disabled/failing` | 같은 경로의 CS 실행 | 같은 네 호출 |
| R `partition_partition_rejection`, `disabled/failing` | `oos08_controller` → `partition_rejection` → `ddl_snapshot` → M | `default`·`force_outline` 각각 세 호출 |
| R `show_contract`, `disabled/failing` | `snapshot`·`preserve` → `metadata` → M | 최초 snapshot과 rejection 보존 검사 |
| R `policy_contract`, `disabled/failing` | 자기 controller의 `metadata` → M | 같은 `cases`를 소유하는 대조군 |
| R `tde_storage`, `disabled/failing` | 직접 `T owned` | NONE·AES 둘 다 검사. AWK·JSON helper 필요 |
| R `crash_committed`·`crash_undo`, `disabled/heavy` | `oos_crash` → `T owned` | AES일 때 baseline·recovered에서 호출. 기본 NONE에서는 호출 안 함 |
| R `tde_crash_committed`·`tde_crash_undo`, `disabled/failing` | AES 설정 → sibling crash 진입점을 source → 위 경로 | sibling 정규 `.sh`도 현재 없음. Wrapper만 복원하면 helper보다 먼저 막힘 |
| R `tde_wal`, `disabled/heavy` | 자기 진입점에서 T의 네 명령 | 같은 `cases` 소유. `owned`는 AWK도 필요 |
| H `crash_committed`·`crash_undo`, 활성 | `oos_crash` → `T owned` | AES 옵션일 때만 교차 TC 의존성에 도달 |
| H `tde_wal`, 활성 | 자기 진입점에서 T의 네 명령 | 같은 `cases`를 소유하는 대조군 |

Schema의 source dispatch는 [`oos08_controller.sh:96–103`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/6334dc6cd74683ca6ba10439372a21bd36b453d3/shell/_40_guava/oos_common/oos08_controller.sh#L96), 실제 metadata 호출은 [`oos08_schema.sh:55–68`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/6334dc6cd74683ca6ba10439372a21bd36b453d3/shell/_40_guava/oos_common/oos08_schema.sh#L55)과 [`oos08_partitions.sh:288–301`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/6334dc6cd74683ca6ba10439372a21bd36b453d3/shell/_40_guava/oos_common/oos08_partitions.sh#L288)에서 확인했다. SHOW는 [`show_controller.sh:76–119`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/6334dc6cd74683ca6ba10439372a21bd36b453d3/shell/_40_guava/cbrd_26659_show_contract/cases/show_controller.sh#L76)의 `snapshot → metadata` 호출을 따른다.

반대로 `attributes`와 다른 partition branch에는 `ddl_snapshot` 호출이 없다. [`cbrd_26659_partition_lifecycle_common/controller.sh:83–99`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/6334dc6cd74683ca6ba10439372a21bd36b453d3/shell/_40_guava/cbrd_26659_partition_lifecycle_common/controller.sh#L83)는 함수를 정의하지만 source하는 `lifecycle.sh`의 add/drop·promote 경로는 이를 호출하지 않는다. 정의나 이름 일치만으로 영향 TC를 늘리지 않았다.

AES guard는 R·H의 `oos_crash.sh:198–202,256–260`에 있다. [H baseline 호출](https://github.com/vimkim/cubrid-testcases-private-ex/blob/81e60724a30431282c08ae1f677bf8cefb3d95d7/shell_heavy/_40_guava/oos_common/oos_crash.sh#L198)은 `encryption=AES`일 때만 T를 사용한다. R의 암호화 wrapper 두 개는 각각 4행에서 AES를 설정하고 5행에서 다른 TC의 정규 `.sh`를 source한다. [Committed wrapper](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/6334dc6cd74683ca6ba10439372a21bd36b453d3/disabled/failing/shell/_40_guava/cbrd_26659_tde_crash_committed/cases/cbrd_26659_tde_crash_committed.sh.disabled#L4)와 undo wrapper의 sibling 진입점은 `disabled/heavy`에 보존돼 있으며 정규 위치에는 없다. H에는 이 wrapper들이 없다.

## 실제 case 선별과 parser 대조

[재현 스크립트](tools/verify-cross-case-helper-dependencies.py)는 두 TC 리비전의 category 전체를 `git archive`로 새 fixture에 복사한다. 비활성 입력은 원본 bytes·mode를 확인해 fixture의 정규 위치에만 투영한다. 암호화 wrapper fixture에는 별도 sibling 진입점도 투영해 그 파일의 생존을 함께 관측한다. 실제 저장소의 선택이나 파일은 바꾸지 않는다.

실행한 [선별 소스](https://github.com/CUBRID/cubridci/blob/155c265eb6e3deef49ce828e6f2b5846d3a9abf5/docker/ci/docker-entrypoint.sh#L1045)는 선택된 진입점의 부모 `cases`만 남긴다. 별도 controller의 참조를 추적하지 않는다. 실행 파일의 SHA-256은 `55965b9c36c67c4f4330b7954202ea292eb617b9139f9bfa46a6f27d283557d2`로 대조했다. 각 목록은 **새로 만든 집중 선택 목록**이다. 과거 shard 목록이나 현재 heavy 운영 설정의 복제가 아니다.

| 대조 | fixture 수 | 관측 결과 |
| --- | ---: | --- |
| 위 표의 교차 소유자 소비자, owner 제외 | 11 | `keep case`는 모두 exit 0. 선택한 진입점은 남고 helper는 삭제. 합성 parser 호출은 선별 전 exit 0, 선별 후 파일 누락으로 exit 127 |
| 같은 소비자에 owner도 선택한 대조군 | 11 | helper 보존. 합성 parser는 선별 전후 exit 0 |
| R policy-contract·H TDE-WAL의 자기 소유자 대조군 | 2 | 자기 `cases`와 helper 보존. 합성 parser는 선별 전후 exit 0 |
| H TDE owner 복사본에서 AWK만 제거 | 1 | `owned` parser exit 5 |
| H TDE owner 복사본에서 JSON helper만 제거 | 1 | `owned` parser exit 1 |

앞의 24개가 실제 `keep case` 실행 수다. 마지막 두 행은 별도 파일 누락 대조이며 선별 횟수에 포함하지 않는다. 11개는 fixture 구성 수이며 고유 실패 TC 수나 과거 실패 원인 수가 아니다. R/H의 같은 crash 이름과 R wrapper의 조건부 경로를 따로 대조했다.

Metadata parser에는 직접 만든 한 행 DDL을 넣었다. TDE `owned` parser에는 heap·OOS header 두 개와 그에 맞는 고정 identity JSON을 넣었다. 관측 DB 값으로 기대값을 만들지 않았고 DB를 사용하지도 않았다. 이 결과는 파일 가용성과 해당 합성 입력의 parser 동작을 증명한다. 실제 TC의 선행 단계·SQL 의미·암호화·recovery 성공을 증명하지 않는다.

TDE helper가 삭제되는 fixture에서는 같은 `cases`의 AWK도 삭제되고 공용 `oos_json.sh`는 남았다. R 암호화 wrapper 두 fixture에서는 투영한 sibling crash 진입점도 삭제됐다. 따라서 helper만 이동해도 이 wrapper들의 독립 실행 문제가 모두 해결된다고 말할 수 없다. Owner를 추가 선택한 대조군은 삭제 메커니즘을 구분하기 위한 실험이며 수리안이 아니다.

## 최소 수리와 후속 검증 제안

먼저 **metadata helper 한 개의 일반 suite 이동**을 별도 단위로 권한다. 기존 공용 디렉터리에 새 경로 `oos_common/policy_metadata.sh`를 두고 helper bytes·mode는 유지한다. R의 다음 네 파일에서 경로만 바꾼다. 앞의 세 파일은 도달 가능한 호출자이고, 마지막 파일은 현재 미호출 정의의 오래된 경로를 함께 없애기 위한 변경이다.

- `oos_common/oos08_controller.sh:86`.
- `cbrd_26659_show_contract/cases/show_controller.sh:79`.
- `cbrd_26659_policy_contract/cases/policy_controller.sh:62`.
- `cbrd_26659_partition_lifecycle_common/controller.sh:86`.

이 단위의 검증은 이전·새 parser의 출력·종료값 일치, 잘못된 row·DDL field 수와 ERROR/FATAL 거부, owner 제외 후 파일 생존, 원문 SHOW-contract 대표의 격리 native 실행으로 구성한다. 대표 한 개의 PASS를 schema·partition 전체 PASS로 확대하지 않는다. 비활성 저장 위치와 assertion은 유지하고 필요한 원문 투영은 scratch에서만 한다.

그 다음 **TDE helper와 AWK의 일반·heavy 이동**을 별도 단위로 다룬다. 두 파일을 해당 suite의 `oos_common`에 함께 옮긴다. TDE helper의 source를 `"$here/oos_json.sh"`로 바꾸고, 같은 디렉터리의 `"$here/tde_headers.awk"` 참조는 유지한다. R/H의 crash controller 두 호출, R의 비활성 `tde_storage`, R 비활성·H 활성 `tde_wal` 호출 경로를 함께 바꾼다. H의 과거 일반 `shell` tree와 최초 이관 TSV는 유지하고 기존 공용 README에 변경 날짜·현재 위치를 덧붙인다.

| TDE 배치안 | 평가 |
| --- | --- |
| 기존 공용 디렉터리에 helper·AWK 배치 | 기존 평면 배치와 맞는다. source 한 곳의 상대 경로 변경이 필요하다. 권고안 |
| `oos_common/tde/`를 새로 만들고 두 파일 배치 | helper의 기존 두 단계 상대 source를 유지할 수 있지만 새 디렉터리 구조가 생긴다. 이번 범위에서는 필요성이 작다 |
| 소유 TC를 shard에 강제로 추가하거나 helper 복사본 유지 | 선택 결합 또는 중복을 남겨 공용 소유권 문제를 보존한다. 채택하지 않음 |

TDE 후속 검증은 네 명령 전체와 `owned`의 NONE·AES·잘못된 identity·중복/누락 header·복수 JSON 문서 거부를 포함한다. 이후 owner가 없는 선별 입력에서 실제 AES crash 대표를 검증해야 한다. 기본 NONE crash나 `owned` 합성 성공을 AES native 실행의 대용으로 쓰지 않는다. R 암호화 wrapper들의 sibling 진입점 결합은 별도 수리·복원 결정을 남긴다.

후속 구현을 진행할 때 TC head 게시와 그 변경에 대한 한 번의 CI는 기존 CUBRID 정책을 따른다. 이번 조사에서 과거 CI를 다시 실행하지 않는다. [전체 체크리스트](CBRD-26659-todo-checklist_20261029_codex.md)의 나머지 38개 정책 그룹 검증, native 종료 지연, SQL 전체 집계 정합성, heavy·HA 운영, 사람의 TC PR 검토·병합도 미완료다.

## 재현 자료와 보존 범위

```sh
python3 cbrd-26659/tools/verify-cross-case-helper-dependencies.py \
  --regular /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --heavy /home/vimkim/gh/cubrid-testcases-private-ex/CBRD-26659-oos-shell-heavy \
  --ci-source /home/vimkim/gh/cubrid-dockerfiles-cubridci \
  --artifacts /home/vimkim/temp/cbrd-26659-helper-dependency-audit-20261031
```

원본 결과는 위 artifacts root의 `pruning-proof/audit-towozgn5/result.json`, 요약은 `proof-summary.json`이다. 각 fixture의 선택 목록·투영 원본과 hash·선별 stdout/stderr·parser stdout/stderr를 함께 보존했다. `baseline.json`, `audit-input.json`, append-only `decisions.tsv`도 같은 root에 둔다. 생성 JSON·fixture·로그·대화는 Git에 넣지 않는다. 문서에는 이 보고서, 체크리스트·색인, 결론을 다시 확인하는 데 필요한 검증 스크립트만 보존한다.

현재 관측은 확보한 선별 소스의 파일 삭제 동작을 증명한다. 과거 worker image digest·실제 bytes나 모든 과거 실패의 원인을 확정하지 않는다. Heavy의 실제 운영 환경에서 `keep case`를 쓰는지도 이 실험으로 확정하지 않는다. 조사 중 TC 두 checkout의 HEAD와 clean 상태는 그대로였다.
