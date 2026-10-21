# Work456 ticket03: SHOW 대상·인자·권한과 관측 범위

2026-10-21, Asia/Seoul. PR8128 작성자·리뷰어와 최종 ticket16 담당자를 위한 실행 보고다. [승인 ticket03](supplement-tickets/issues/03-show-targets-and-permissions.md)의 O09–O11 의무를 대상으로 한다. 최종 native shell 실행은 정확히 **2개 실행, 1 PASS, 1 FAIL, 0 skip**이다. 일반 대상·권한·거부 후 보존 사례는 통과했다. 파티션 사례는 올바른 leaf 소유권 기대를 유지한 채 여섯 SHOW 대상 형식에서 실패한다. 이 FAIL은 passing coverage에 포함하지 않는다.

기존 [01 관측기](ticket01-baseline-and-observer-20261021.md), [연산 목록](supplement-operation-inventory-work456-20261021.md), [C++ 목록](supplement-cpp-inventory-work456-20261021.md)과 함께 읽는다. 두 신규 사례는 기존 JDBC 파일을 수정하지 않는 독립 전달이며, production 수정·게시·CI는 수행하지 않았다.

| 식별자 | 최종 실행 기준 |
| --- | --- |
| Source | `CUBRID/cubrid` `d13aebf6428a68c2852d16df143d1da203d86dea`, `task/work456-03-source`, clean |
| Build/profile | Linux, 64-bit OptDebug, DB/log I/O page 16 KiB. 일치하는 ticket14 설치본을 전용 `work456-ticket03/optdebug` prefix로 복사했다. 새 build는 없다. `d13`은 visible-version C++ test 두 개만 추가한 기준이다. |
| Installation identity | 모든 native preflight에서 installed `d13aebf`, `commit_match=yes`, mismatch 예외 없음. 최종 install manifest 273개 파일, SHA-256 `3dc6bed32c1df83cdbbbb29c2d5b91ee992dc440d06df997241939c2c4aca2f6` |
| Private TC | `813547aa4a3ca32a150e86458ab1f034e8371ced`; 구현 `c722a4610`, integration `fe90357a9`를 받은 merge `13acb0803`, entrypoint mode commit `813547aa4`. `task/work456-03-private`, clean |
| Public TC | `410ba5d2ce3151054b11f8443d2da9966a5eafff`, `task/work456-03-public`, 변경 없음 |
| CTP assets | `9c62858b10005d721546cc007be260844033b9e9`; 기존 tracked 수정 5개와 untracked JDBC/result/config를 보존했다. CTP는 asset만 제공하며 실행기는 native testkit이다. 547개 source asset manifest SHA-256 `f91de04a10e0a5d73aaafd33e577942135582c030e52612af05c28657493bc1c` |
| Native runner | `cubrid-testkit dev`, Go build revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified build. 실행 binary SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a` |
| JDK | Temurin `8.0.462+8`; 이 사례는 CSQL을 사용하며 JDBC coverage를 주장하지 않는다. |
| Final config | `parallel_slots=1`, `scenario_disk=on`, feedback=file, retry=0, update=false, continue=false, exclusions 없음. `shell.conf` SHA-256 `a2737ba9d845215985fbd546ec132519c62bbaabcc5bff572343370bff960614` |

**독립 oracle과 두 SHOW 종류.** OOS 규범 전체를 읽은 fingerprint는 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`다. 개별 HAS_OOS와 OOS file aggregate의 구분, heap별 소유권, 24-byte chunk header는 승인 계약에서 가져왔다. [SHOW metadata](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/parser/show_meta.c#L386)는 `SHOW HEAP OOS OF identifier`와 `SHOW ALL HEAP OOS OF identifier`를 각각 DBA 전용으로 등록한다. [문법](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/parser/csql_grammar.y#L7473)에는 이 두 형식의 직접 WHERE/LIKE filter나 EXACT/APPROX suffix가 없다. 해당 조합은 미실행이나 skip이 아니라 실제 syntax rejection으로 확인했다.

권한 기대는 승인된 O11과 로컬 manual `3b6ae97bfbdc664b010ffa933ded5a05b291ae03`의 `en/sql/query/show.rst:645` 및 위 metadata의 `only_for_dba=true`에 따른다. manual의 영문·국문 SHOW 문서에는 OOS 전용 항목이 없으므로 새로운 OOS 문법과 객체 계약의 증거는 exact-revision parser/metadata다. `select.rst:84–85`의 명시적 `ALL` 계층 읽기와 `show.rst:1119`의 partition `ALL` 의미는 구분했다. [공통 heap scan](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/storage/heap_file.c#L19990)은 partitioned root의 ALL에만 partition heap들을 추가하며 일반 상속 자손을 열거하지 않는다.

**혼합 heap과 안정된 통계.** `show_rows(id PRIMARY KEY,note DEFAULT 77 NOT NULL,payload BIT VARYING STORAGE PREFER_INLINE COMMENT ...)`에는 두 committed 행만 있다. id1/note101은 literal `X'19ab23cd45ef'`; id2/note202는 `a1×1701 || b2×1703 || c3×1703`의 5,107-byte 값이다. SQL equality로 앞·중간·끝을 포함한 전체 값과 행 수를 검사한다. 각 거부 뒤에는 같은 heap의 실제 `SELECT_RECORD_INFO`를 다시 읽어 `(volume,page,slot)`, REC_HOME type, insert/delete id, note, 전체 값 동등성 및 HAS_OOS를 함께 검증한다.

| 현재 저장 행 | 물리 slot | REC type / flags | HAS_OOS | 논리 값 |
| --- | --- | --- | --- | --- |
| id1, note101 | `(1,641,1)` | `2 / 1` | clear | 전체 equality 1 |
| id2, note202 | `(1,641,2)` | `2 / 9` | set | 전체 equality 1 |

이는 실제 해당 invocation의 동일한 unpartitioned heap에서 관측한 결과다. Expand된 사본이나 크기·정책·SHOW로 개별 플래그를 추정하지 않았다. 이 관측기의 qualification은 현재 REC_HOME에 한정한다. 파티션·relocation·undo/version-chain의 개별 플래그 판정으로 확대하지 않는다.

통계의 독립 기대는 [VARBIT 직렬화 길이](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/base/object_representation.h#L2340)와 승인된 24-byte chunk header에서 계산했다. `align4(5+5107)+24 = 5136`이다. 최종 `show_rows`는 class OID `(0|195|2)`, heap HFID `(641,1,640)`, OOS VFID `(1,704)`, user pages 2(header+data), records 1, sumlen 5,136, physical bytes 32,688, unused bytes 27,552였다. no-file 대상은 OOS VFID의 두 field가 NULL이고 모든 file/page/record/byte 수치가 0이다.

[OOS 통계 스캔](https://github.com/CUBRID/cubrid/blob/d13aebf6428a68c2852d16df143d1da203d86dea/src/storage/oos_file.cpp#L3826)은 busy/deallocated page를 건너뛸 수 있다. 이 exact 비교는 초기 commit 뒤 쓰기·회수를 하지 않는 단일 fixture, `vacuum_disable=yes`, `enable_string_compression=no`에서 수행했다. 두 SHOW 형식 및 DBA group member의 결과를 같은 초기 통계와 비교했고, 변동하는 workload 수치를 고정 수치의 성공 근거로 삼지 않았다.

**일반 계약 사례: PASS.** `shell/_40_guava/cbrd_26659_show_contract/cases/cbrd_26659_show_contract.sh`가 다음을 실제 실행했다.

| 대상/행위 | 두 SHOW 형식의 검증 |
| --- | --- |
| qualified mixed table, empty eligible table, bracket-quoted table | 정확한 table/class/HFID, file 유무, 14개 column, live chunks/slot bytes, page/physical/unused 산술 |
| 일반 superclass / subclass | parent는 자기 heap만, child는 자기 OOS heap만 반환. ALL도 자손을 포함하지 않음. 별도 `SELECT FROM ALL show_parent`는 전체 값 두 행을 읽음 |
| system `db_root` / user view / system view `db_class` / missing class | 실제 system class는 no-file 진단 허용; 두 view는 `ER_OBJ_NOT_A_CLASS(-217)`의 class-object error, 없는 class는 unknown-class error |
| 누락 OF/대상, numeric, NULL, string, 복수 대상 | 각 형식에서 문법 오류; 결과 행 반환 없음 |
| EXACT, APPROX, 직접 LIKE, 직접 WHERE | 각 형식에서 지원하지 않는 문법으로 명시적 거부; filter coverage를 임의 지원으로 계산하지 않음 |
| 일반 사용자, SELECT grant 전후 | SELECT 전에는 데이터 접근 거부, grant 뒤 전체 값 두 행 읽기 허용. SHOW는 grant 전후 두 종류 모두 DBA-only error이며 결과 행 없음 |
| DBA 및 DBA group member | 두 SHOW 종류 모두 정확한 동일 file/통계 반환 |

이 사례에는 정확히 **31개 거부 assertion**이 있다: 각 형식 3개 객체 + 10개 인자/문법 + grant 전 권한 거부로 28개, 데이터 SELECT 거부 1개, grant 뒤 SHOW 거부 2개다. 거부마다 전체 값·물리 레코드 JSON·전체 SHOW CREATE TABLE DDL·view 정의와 전체 view 값·없는 객체의 catalog 부재·SHOW aggregate를 다시 비교했다. default/PK/정책/comment도 DDL의 일부로 보존한다. 최종 artifact의 181개 JSON block과 모든 31개 보존 snapshot이 독립 audit에서 일치했다.

**파티션 소유권 사례: FAIL 유지.** `shell/_40_guava/cbrd_26659_show_partitions/cases/cbrd_26659_show_partitions.sh`는 두 leaf에 서로 다른 id/note와 같은 구별 가능한 전체 5,107-byte 값을 삽입했다. root SELECT는 정확히 두 행, p0/p1의 직접 SELECT는 각각 올바른 한 행을 반환했다. SHOW의 class OID/HFID가 실제 root/leaf를 구별하며, 이 aggregate 관측은 파티션 행의 HAS_OOS qualification을 주장하지 않는다.

| 실제 heap | 승인 기대 `(has,chunks,slot bytes)` | 최종 관측 | 식별자 |
| --- | --- | --- | --- |
| partition root `show_part` | `(0,0,0)` | `(1,2,10272)` | class `(0|195|2)`, HFID `(577,1,576)`, OOS `(1,768)` |
| `show_part__p__p0` | `(1,1,5136)` | `(0,0,0)` | class `(0|195|5)`, HFID `(641,1,640)`, OOS 없음 |
| `show_part__p__p1` | `(1,1,5136)` | `(0,0,0)` | class `(0|195|7)`, HFID `(705,1,704)`, OOS 없음 |

일반 root SHOW, root ALL SHOW, 각 leaf의 일반/ALL SHOW까지 **6개 물리 assertion을 모두 실행**하고 여섯 FAIL을 남긴 뒤 testcase를 실패시켰다. root ALL은 이름순 root+p0+p1 3개 행을 반환했으므로 행 열거와 소유권 통계의 판정도 구분한다. 올바른 leaf 기대를 root의 결함 출력으로 바꾸지 않았다. 별도 수리 경로는 [partition-owner PR7927](https://github.com/CUBRID/cubrid/pull/7927)/Work393이다. 이 보고는 현재 revision에서의 소유권 불일치와 그 수리 범위의 연결이며, PR7927의 최신 상태나 내부 원인이 같다는 확정은 아니다.

**기존 SA C++ 네 사례: 모두 retain.** ticket14가 보존한 source `1ef86a7efa34002e971b1b30bcf5d451e9db441b`의 별도 fixture-aware CTest invocation `test_oos_sql_show`를 재대조했다. required=discovered=started=console PASS=GTest XML PASS가 아래 네 ID와 정확히 일치한다. rc0, missing/skip/fail 없음, 해당 invocation 후 owned processes 없음. 이는 위 d13의 CS CSQL 실행과 별도 receipt다.

| exact case ID | 유지하는 assertion과 mode 구별 |
| --- | --- |
| `OosSqlShow.HeapWithoutOosReportsZeroStats` | SA/direct DB API의 integer/NULL typed column 추출, no-file zero stats, DB_PAGESIZE |
| `OosSqlShow.HeapWithOosReportsPositiveStats` | SA의 live positive file/chunks/length와 physical/unused 산술 |
| `OosSqlShow.ShowAllHeapOosRunsForNonPartitionedClass` | SA에서 ordinary-class ALL dispatch와 file 존재 |
| `OosSqlShow.ShowAllHeapOosReportsPartitionRows` | SA의 partition 결과 iteration, row_count>1, OOS heap_count>=1. 각 leaf 소유권은 보장하지 않으며 결함 root file만 있어도 통과할 수 있음 |

SQL text나 결과가 비슷해도 SA/direct API boundary는 CS shell로 대체하지 않았다. C++ 삭제·이관은 없고, 새 C++ target도 없다. full302 receipt SHA-256은 `d55d4243db537e6c8c5338ffd15d8f41429e76391f04d18990b367cbbb585b9e`; 독립 4-ID audit는 raw `cpp-show-audit.json`이다.

**실행·판정·격리.** source의 `cub-workenv init --no-db`로 전용 선택을 준비했다. 각 invocation은 install/CTP/HOME/registry/TMP/config를 새 attempt에 복사했고 copied registry를 보존한 뒤 비어 있는 registry를 만들었다. 실행은 다음 native family뿐이다.

```sh
TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c "$ATTEMPT/conf/shell.conf"
```

runner가 생성한 slot 안에서 두 사례를 순차 실행했다. 최종 사례의 PID/IPC/mount/network namespace는 각각 `4026537224/4026537223/4026537222/4026537225`로 host와 다름을 검증했다. 두 사례는 같은 serial slot을 순차 재사용했다. 각 testcase가 `w456show` DB를 새로 생성하고 삭제하므로 두 사례에 같은 숫자 OID가 나타나도 DB 사이의 객체 동일성을 뜻하지 않는다. shell framework의 port 1568 설정은 이 network namespace 안에 있으며 workenv의 host allocation과 혼동하지 않는다. framework의 service/kill cleanup도 이 격리 안에서 실행됐다. controller는 등록된 자기 child/session만 다뤘고 구성 복원, owned server 부재, DB 삭제, registry entry와 fixture directory 부재를 검사했다. 최종·negative 모두 host에서 attempt prefix의 native process가 남지 않았다. source integration의 unrelated CCI dirt와 shared CTP 수정은 보존했다. native B lease는 실행 완료 후 반환했다.

최종 expected-cases 2개는 dispatch ALL, dispatch FIN, XML의 file identity와 정확히 일치한다. status는 total/executed2, success1, fail1, skip0이다. 일반 사례 XML은 failure/skip/error가 없고 파티션 XML에만 failure가 있다. 원래 verifier는 이 1 FAIL을 올바르게 거부한다. runner exit0을 PASS로 바꾸지 않았다. 최종 경과는 36.690s이며 XML case time은 일반 28.122s, 파티션 7.135s다. 이 수치는 shell 운용 비용이며 성능 판정이 아니다.

| retained attempt | native 실행/성공/실패/skip | 판정과 한계 |
| --- | --- | --- |
| `red01` | `1/0/1/0` | TDD red: controller 없음. DB 실행이나 passing coverage 없음 |
| `green01` | `1/0/1/0` | 처음 leaf의 올바른 기대가 실패. 뒤 matrix를 가리지 않도록 파티션을 독립 testcase로 분리 |
| `green02` | `1/0/1/0` | 잘못 지정한 `_db_root`를 실제 system class `db_root`로 수정한 fixture 오류 |
| `green03` | `1/0/1/0` | view error의 정확한 message를 source -217에 맞춘 harness 수정 |
| `green04` | `1/0/1/0` | hierarchy logical SELECT를 manual의 명시적 `ALL`로 수정한 fixture 오류 |
| `green05` | `1/0/1/0` | SELECT denial의 parser message를 source message에 맞춘 harness 수정 |
| `green06` | `2/1/1/0` | 일반 matrix PASS; 독립 파티션 6 assertion FAIL |
| `green07` | `2/1/1/0` | view/catalog 보존 추가. 같은 파티션 FAIL |
| `green08` | `2/1/1/0` | testcase parser를 유지되는 awk/jq shell 의존성으로 검증. 같은 파티션 FAIL |
| `final01` | `2/1/1/0` | commit813547aa4, namespace/config identity 포함 최종 receipt |
| `negative-stat` | `1/0/1/0` | 별도 corpus의 최초 SHOW 기대만 5136→5137. 실제 값5136을 정확히 NOK로 판정; verifier도 거부 |

모든 invocation의 runner status는 0이었으며 native verdict verifier는 모두의 실패를 거부했다. negative의 틀린 literal은 TC에 커밋하지 않았다. 초기 중간 시도는 input hash와 실패 로그를 보존하며 완성된 필수 coverage로 계산하지 않는다. 마지막 committed run과 별도 negative corpus가 최종 주장의 근거다.

Raw evidence root는 `/home/vimkim/temp/work456-implementation/ticket03`이다. 각 attempt의 `preflight.log`, `inputs.json`, `environment.json`, `expected-cases.txt`, `conf/shell.conf`, `command.json`, `run.log`, `exit.status`, `verify.log`와 `CTP/result/shell/current_runtime_logs/{test-shell.xml,test_status.data,dispatch_tc_ALL.txt,dispatch_tc_FIN_local.txt,feedback.log,test_local.log}`을 보존했다. source/install/TC/CTP의 `revisions-final01.json`, install/CTP manifests, `testkit-build.txt`, `attempts.json`, `doctor-final.log`, `cpp-show-audit.json`도 같은 root에 있다. 독립 최종 reconciliation `independent-audit.json` SHA-256은 `2b8170bf36dd4bd1111bc675d6ed9cfcd0429740e57921230b2aa324768551a6`; 최종 XML SHA-256은 `f3554f83d7b9c83cc950e4cfe8115d67eb7049bf3cec66bca8132bbcc1441c72`이다. 큰 로그와 자동 생성 inventory는 문서 Git에 넣지 않았다.

**전달 범위.** `bash -n`, ShellCheck, explicit task diff와 native artifact reconciliation을 수행했다. 전용 source worktree에는 build directory와 compile database를 만들지 않아 LSP/build validation의 그 두 항목은 준비되지 않았다. 이 작업은 소스 build나 LSP에 의존하지 않았고 matching installation preflight로 실행 기준을 확정했다. 필수 SHOW 인자·권한 조합의 미실행/skip은 없으며 파티션은 실행된 엔진 FAIL이다. 파티션 행의 개별 플래그 관측은 본 aggregate 계약의 증거로 주장하지 않는다. 최종 ticket16은 두 신규 shell 사례와 별도 SA4 receipt를 분리하여 합산하고 이 FAIL 및 별도 수리 연결을 유지해야 한다. 이 전달은 CI-ready/all-green, engine repair 완료, performance/HA qualification을 뜻하지 않는다.

최종 실행 뒤 live TC05 integration을 own branch로 받았다. handoff private tip은 `c81615ec4b213b8a906139222877537385b31caa`, public tip은 `754dfffd83f7b3a14e13e8a5b965ccf4f2ae2920`이다. `post-merge-input-audit.json`에서 최종 실행에 사용한 다섯 신규 파일과 shared helper를 포함한 모든 input hash가 그대로임을 확인했다. 새 통합 revision 전체를 다시 실행한 것으로 표현하지 않는다. Source는 계속 `d13aebf64`다.
