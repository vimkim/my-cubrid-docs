# Ticket05 — 트랜잭션과 거부된 DML의 즉시 원자성

작성일 2026-10-08 (Asia/Seoul). CBRD-26659, 엔진
`fb567a629cdb390fff920542173fa36f454c74a0`. 현재 소스 작업 브랜치에는
연결된 PR이 없다. 승인된 구현 티켓05의 R10, R11, R12 제약조건 부분을
구현하며, 엔진 수정이나 외부 게시를 포함하지 않는다.

실행 전 literal 모델과 oracle를 독립 검토한 뒤 native 검증했다. SQL의
세 case와 별도 shell companion을 정확한 실행 목록으로 선택하며, 실행
결과뿐 아니라 owned cleanup을 만족해야 성공으로 인정했다. 최종 native
SQL은 정확한 3/3, shell은 1/1로 통과했고 필수 assertion·cleanup token을
모두 실행했다. 이 티켓의 mandatory acceptance에 미충족 항목은 없다.

## 전달 파일과 독립 기대값

공개 저장소의 `sql/_36_guava/cbrd_26659/` 에 세 SQL/answer 쌍을 추가한다.

| Case | 검증하는 동작 |
| --- | --- |
| `cbrd_26659_oos_sql05_transactions` | multichunk·inline·single-chunk pre-image를 함께 사용한 INSERT/UPDATE/DELETE rollback, multichunk DELETE rollback, savepoint 앞의 UPDATE 보존, 뒤의 혼합 DML 취소, COMMIT 후 정확한 행 집합 |
| `cbrd_26659_oos_sql05_constraints` | PK/secondary UNIQUE INSERT·UPDATE, NOT NULL INSERT·UPDATE, 다중 행 statement 취소, 실패 전 같은 트랜잭션의 성공 보존, 실패 후 성공적인 쓰기, 지원되는 view CHECK OPTION의 논리 결과·스키마 보존 |
| `cbrd_26659_oos_sql05_bigone` | OOS+bigone INSERT·UPDATE 오류와 미변경 pre-image, ordinary non-OOS bigone 성공, 고정 12500B residual의 합법적인 OOS slotted-record 대조군과 후속 UPDATE |

private 저장소는
`shell/_40_guava/cbrd_26659_transactions/cases/cbrd_26659_transactions.sh` 와
`setup.sql`, `transactions.sql`, `verify_transactions.py` 를 추가한다.
[전체 10개 testcase 파일 manifest](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket05/delivery-manifest.json)는
각 relative path와 SHA256을 기록한다. 공개 세 `.sql`의 동일 stem
`.answer`가 각각 `answers/`에 있다. public worker는
`task/oos-05-transactions-errors`, private worker는
`task/oos-05-transactions-physical`이며 docs worker는
`docs/oos-05-transactions-errors`다. 기존 `oos_common/oos_observe.py` 를 사용하며 shared helper는 수정하지 않는다.

값 모델은 실행 전에 외부 Python의 literal byte 조각으로 정의했다. 20003,
3000, 4207, 33001, 23003, 21003, 25003, 1000, 34003B의 구분되는
head/middle/tail 패턴을 사용한다. `DISK_SIZE=ALIGN(5+N,4)` 는 현재 VARBIT
serializer의 prefix/padding에서 도출했으며, MD5는 lowercase hex 문자열을
독립적으로 해시했다. 각 행의 전체 값·길이·digest·tag·ID와 scalar를 함께
검사하고 정확한 행 수를 별도로 검사한다. 과거 결과 파일을 answer 생성
입력으로 쓰지 않았다.


아래 A–J는 후술한 행 상태 표에서 쓰는 독립 literal 값이다. 각 fragment는
hex byte이며 SQL cast의 해석과 lowercase hex MD5 규칙을 적용했다.

| 값 | head/middle/tail fragment | octets | DISK_SIZE | MD5 |
| --- | --- | ---: | ---: | --- |
| A | 12×7001,34×6501,56×6501 | 20003 | 20008 | `127967dc901ebb2776d754d2257cadf3` |
| B | aa,bb,cc 각×1000 | 3000 | 3008 | `4d99190ee568772b70b0244abddbaa00` |
| C | d1×1401,e2×1403,f3×1403 | 4207 | 4212 | `5a43433dc26414a3625551ee8fc23cd2` |
| D | 78×11001,9a×11000,bc×11000 | 33001 | 33008 | `ec5759eaa4472233734552dfd216c552` |
| E | 21×8001,43×7501,65×7501 | 23003 | 23008 | `82ee427e0bec12f832eb46c8c56d538a` |
| F | 31,53,75 각×7001 | 21003 | 21008 | `d4f9b32b4104e5e958cfa40e4eeb1ae1` |
| G | 41×9001,63×8001,85×8001 | 25003 | 25008 | `d017efffa18d3cab7589a1b16ae1f201` |
| H | ab,cd 각×500 | 1000 | 1008 | `06e4fbcd09df9054a001eb5a04ee288e` |
| I | ef,01 각×500 | 1000 | 1008 | `7f86fcb3989df88e24c2f3c2fb0b3b57` |
| J | 89×12001,ab×11001,cd×11001 | 34003 | 34008 | `a89c11484aa04f04154a7f6a6b2052db` |

Tags는 11/22/33/44 byte를 각각 300번 반복한 별도 값이다. Fixed
BIT140000의 padded-one은 17500 octets와 MD5
`34a214a2ad74c12fb048983648439e81`, BIT100000의 padded-one은 12500
octets와 `9968bd39c8d205517eaa9e21811c9817`이다.

상세 실행 전 모델과 검토 근거는
[oracle.md](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket05/oracle.md),
[literal-model.json](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket05/literal-model.json)
에 보존한다. [root의 독립 검토](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket05/root-oracle-review.md)와
[별도 계산값](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket05/root-independent-values.json)이
초기 public `6b48ef9ad` / private `c78e88c7c`를 실행 전에 승인했다. 첫 clean
시도에서 발견한 실행 prerequisite를 소스로 다시 검토하여
[수정 oracle](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket05/oracle-revision2.md)의
public `bbe4c64da` / private `284da2d87`를 새 실행 전에 재승인했다.
Shell lifecycle 수정은 `381fc38e7` 및 `f98f74a44`의 전체 delta와 로그 prefix
소스를 추가 검토하고 revision3로 재승인했다. root의 같은 검토 문서에
승인 이력이 있다. 결과 캡처를 golden으로 쓰지 않았다. 이 raw 근거들은 문서 저장소에 커밋하지 않는다.

## 현재 오류·지원 범위

현재 OOS+bigone 오류는 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE=-1384` 이다.
[error_code.h:1785](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/base/error_code.h:1785),
[chain 생성 전 guard](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/heap_file.c:13801)
를 근거로 삼는다. CBRD-27403, 과거 `-1375/-1382` answer와 normative 문서의
오래된 숫자는 현재 oracle로 사용하지 않는다.

직접 서버의 단일 행 DML에서 UNIQUE는 `print_key_value_on_unique_error=no` 기본값으로
`ER_BTREE_UNIQUE_FAILED=-670` 을 기대한다. true이면 `-886` 이 되므로 선택한
configuration에 override가 없는지 별도로 확인한다.
[기본 설정](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/base/system_parameter.c:3136),
[분기](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/btree.c:32606).
선택된 JDBC SQL profile의 `ha_mode=yes`에서는 다중 행 UNIQUE UPDATE의
B-tree insertion conflict가 `ER_REPL_MULTI_UPDATE_UNIQUE_VIOLATION=-975`를
낸다. [충돌과 visible object 검사](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/btree.c:32627)를
근거로 이 경로의 실패 원자성만 검증하며, 내부 행 방문 순서나 HA transport를
추론하지 않는다. 다중 행 PK INSERT 실패는 별도 TEST8에서 검증한다.

직접 서버 NOT NULL DML은 `ER_NULL_CONSTRAINT_VIOLATION=-631` 이다.
[UPDATE predicate](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/query_executor.c:10713).
UPDATE는 `CASE WHEN uniq=100 THEN NULL ELSE required END`를 사용해
행 의존 RHS가 서버 predicate에서 실패하도록 한다. literal NULL은
[XASL constant 검사](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/parser/xasl_generation.c:23055)에서
먼저 `-494`로 거절될 수 있으므로 실행 중 rollback 증거로 쓰지 않는다.

테이블 schema의 CHECK는 현재 소스가 파싱하지만 강제하지 않는다.
[execute_schema.c](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/execute_schema.c:12360).
따라서 table CHECK enforcement credit은 없다. 지원되는 view
`WITH CHECK OPTION` 은 `ER_PT_EXECUTE=-495` 로 검증하되 client-template
경로의 논리 결과로만 기록한다. 기본 OID reuse=true인 table을 기반으로 한
view는 수정할 수 없으므로 base에 `DONT_REUSE_OID`를 명시했다.
[view prerequisite](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/parser/view_transform.c:1261)를
충족시키는 schema 선택이며 system parameter 변경은 없다. private positive
fixture도 같은 OID option을 사용한다.
[check option 평가](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/parser/view_transform.c:14833),
[오류 변환](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/parser/query_result.c:312).

## 실제 proof의 구분

공개 JDBC SQL의 정확한 논리 결과와 private CS companion의 물리 관측은
서로 다른 실행이다. Companion은 공개 실행을 관측하지 않는다.
16KiB I/O page에서 transaction/constraint positive fixture는 각각
3 chunks/24292 slot bytes, 합법적인 residual은 1 chunk/1032 bytes,
ordinary NULL bigone은 OOS file 없음이 독립 기대값이다.
활성 트랜잭션의 mixed writer는 기존 3 chunks에 UPDATE 2개와 INSERT 3개가
더해져 8 chunks/80428 slot bytes가 된다. quiescent SHOW를 엄격하게
파싱하고 같은 CS session에서 8개 독립 transaction 값 결과를 검증한다. 두 SHOW와
8개 값 결과의 정확한 10개 block을 요구한다. 누락·빈 값·추가 block·오류는
실패하며 baseline만으로 public의 개별 실패 실행을 관측했다고 주장하지 않는다.

## 검증·cleanup·시간

모든 attempt의 복사·준비·preflight·실행·검증·cleanup은 공유
`validation.lock`을 독점했다. 대기 시간은 측정에 포함하지 않았다.
`TESTKIT_SLOT_VOLATILE`은 unset, native containment와 한 slot을 사용했다.
source-matching optdebug `11.5.0.2637-fb567a6`, Java8, matching JDBC
`0f5e56c7eaed0ebeb1eba3a8bba5a5db513e7eec455498d268e2205d48c02576`을
명시했다. 공용 optdebug build 129.45s는 root의 공유 준비 비용으로 분리한다.
[install identity](/home/vimkim/tmp/oos-developer-regressions-20261008/install-identity.json),
[SQL a03 identities](/home/vimkim/tmp/oos306-sql05-a03/identities.json)에
source·testcase·CTP·script/config/JDBC hashes를 보존했다. host debug_gcc와
기존 CCI header 변경을 보존했으며 엔진을 수정하지 않았다.

SQL은 native `testkit sql` / JDBC `test_default.xml`로 16KiB DB/log,
64MiB DB/log volume을 사용했다. `autocommit=true`, `holdcas=off`,
`server-message=off`, `insert_execution_mode=default`, unique-error 설정
기본 no를 사용한다. SQL profile은 HA=yes이며 해당 다중 UNIQUE 오류를
별도로 기대한다. private companion은 CS lifecycle/profile의 별도 실행이다.

| Retained attempt | 엄격한 판정 | 준비 s | runner setup·실행·teardown s | 검증·owned cleanup 포함 s | case 측정 s |
| --- | --- | ---: | ---: | ---: | ---: |
| [sql05-a01](/home/vimkim/tmp/oos306-sql05-a01) | 의도적인 wrong MD5 control: 정확한 1 case 실패, `verify.exit=1`, `cleanup.exit=0` | 1.0314 | 83.7407 | 84.2397 | bigone 0.119 |
| [sql05-a02](/home/vimkim/tmp/oos306-sql05-a02) | 초기 prerequisite mismatch: 정확한 3 case 중 2 pass/1 fail, `verify.exit=1`, `cleanup.exit=0` | 1.2141 | 91.9398 | 92.4738 | bigone 0.110, constraints 0.163, transactions 0.081 |
| [sql05-a03](/home/vimkim/tmp/oos306-sql05-a03) | 수정 oracle의 정확한 3 case 모두 pass, fail/skip 0, `verify.exit=0`, `cleanup.exit=0` | 1.0390 | 84.4074 | 84.9025 | bigone 0.111, constraints 0.162, transactions 0.077 |
| [sh05-a01](/home/vimkim/tmp/oos306-sh05-a01) | DB 이름의 로그 prefix 제한 위반으로 setup 실패, 정확한 1 case fail/skip 0, 행동 증거 없음 | 1.0239 | 41.2288 | 41.6110 | native 39.342; script 11.8171 |
| [sh05-a02](/home/vimkim/tmp/oos306-sh05-a02) | 수정 lifecycle의 정확한 1 case pass, fail/skip 0, `verify.exit=0`, driver 전체 exit0 | 1.0357 | 9.7529 | 10.1365 | native 8.546; script 8.3006 |

SQL a01은 복사한 answer의 첫 fixed-BIT MD5 한 곳만 0 digest로 바꿨다.
[negative-control-proof.json](/home/vimkim/tmp/oos306-sql05-a01/negative-control-proof.json)은
actual과 원래 독립 answer가 그 한 차이 외에 동일하고 source answer를
변경하지 않았음을 기록한다. runner exit0에도 fail을 검출했다.
SQL a02에서는 literal-NULL semantic preemption, HA UNIQUE identity와
REUSE_OID view prerequisite를 잘못 가정했다. source로 경로를 다시 검토한
revision2가 이를 수정했으며 a02를 full-set pass로 계산하지 않았다.

Shell a01의 `oos05_transactions`는 18자였다. source
[log prefix 검사](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/transaction/log_page_buffer.c:6975)의
길이 제한에서 `-84`가 발생하여 table 생성 전 실패했다. private
`381fc38e7`는 9자인 `oos05_txn`으로 수정하고, testcase가 mkdir한 디렉터리만
생성 실패 때 정리하도록 ownership flag를 추가했다. `f98f74a44`는 기존
등록 이름을 mkdir 전에 거절하며 registry 복구도 ownership flag를 요구한다.
독립 값·오류·chunk 모델은 변경하지 않았다.
[revision3 lifecycle note](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket05/oracle-revision3-shell-lifecycle.md)에
실행 전 수정 근거를 보존한다.

모든 SQL 시도의 정상 stop/deletedb 메시지, 빈 registry, 사라진 DB directory,
accessible owned native process 없음, runtime config 원복과 짧은 TMP 제거를
확인했다. locale 준비 파일은 정상 native teardown 뒤의 차이를 보존하고
복사 원본으로 원복했다. SQL artifact verdict와 cleanup verdict를 따로
기록하고 둘 다 통과해야 성공이다. Shell a01에서도 native containment가
실패한 fixture workspace를 제거했으며 registry/database root/slot root는
비었고 config·testcase hash가 원복됐다. case trap의 디렉터리 retention NOK와
행동 token 부재를 보존하므로 이를 fixture cleanup 성공이나 행동 pass로
과장하지 않는다. `/proc`에는 읽을 수 없거나 경합한 타 사용자 PID가 있어,
process absence 범위는 접근 가능한 attempt-install 프로세스와 slot ownership에
한정한다. timeout 시도는 실제 발생하지 않았으며 모든 새 command는
`timeout --kill-after=5s`로 bounded completion을 갖는다.

SQL a03의 exact identities는
[verify.log](/home/vimkim/tmp/oos306-sql05-a03/verify.log), 해당 result root의
`linux_sql_64bit.xml`, `summary.xml`과 case 결과에 보존한다.
Shell a02는
[verify.log](/home/vimkim/tmp/oos306-sh05-a02/verify.log),
[feedback.log](/home/vimkim/tmp/oos306-sh05-a02/CTP/result/shell/current_runtime_logs/feedback.log)과
`case-logs/_40_guava/cbrd_26659_transactions/cases/case/`의 모든 SHOW·열 개
result segment·catalog·stop/deletedb·timing 로그가 proof다. 필수 12 token이
모두 나타나고 엄격한 parser가 통과했다. Native case-log collector는 JSON을
제외하므로 retained raw output을 동일한 독립 verifier로 lock 안에서 다시
파싱한 JSON을
[retained-observation-proof](/home/vimkim/tmp/oos306-sh05-a02/retained-observation-proof)에
보존한다. 추가 DB 실행이나 golden 생성은 아니다.
[cleanup.json](/home/vimkim/tmp/oos306-sh05-a02/cleanup.json)은 owned server
정상 stop·deletedb·schema/catalog0 token, accessible attempt-install process 없음,
비어 있는 registry/database/slot root, 모든 config 복구와 testcase hash 불변을
기록한다. Shell driver는 이 gate와 artifact verdict를 함께 만족해야 exit0이다.

`bash -n`, verifier AST/Python compile, testkit `check-cases`, testcase SQL diff
whitespace 검사를 통과했다. answer의 기존 고정 폭 출력 공백은 유지했다.
현재 public/private integration을 worker에 merge한 뒤 이 티켓의 10개 파일과
공유 observer가 검토/검증한 내용 그대로임을 hash로 확인했다. 문서 integration도
worker에 반영했다. 다른 worker의 공유 coverage/README는 직접 수정하지 않았다.

## Coverage delta와 남는 계약

| Coverage | 전달 phase와 독립 결과 | 실제 proof 범위 |
| --- | --- | --- |
| R10 | transactions TEST1–5: committed1A/2B/3C, mixed1E/2B/4D→rollback 원상태, DELETE1→rollback 복구, savepoint 앞1F 보존/뒤 혼합 DML 취소, 최종 COMMIT1F/3E/4D; constraints TEST8–10: statement 취소·earlier INSERT3D 보존·후속 UPDATE3J commit | exact JDBC 논리 값/행 수; 별도 CS base·writer 물리 배치와 8개 값 phase |
| R11 | bigone TEST1–5: ordinary NULL bigone 성공, OOS INSERT/UPDATE `-1384`와 old fixed/NULL/marker 보존, 합법적인 후속 DML, 12500B fixed residual의 H→I 성공 | 현재 오류와 전 필드 논리 보존; 별도 CS ordinary0/0/0·residual1/1/1032 |
| R12 제약 부분 | constraints TEST1–12: positive eligible data; PK/secondary UNIQUE 단일 행 `-670`, NULL INSERT·row-dependent UPDATE `-631`, HA 다중 UPDATE `-975`, 지원 view CHECK OPTION `-495`, untouched survivor·schema5 attrs/3 NOT NULL·valid follow-up | 지원 경로의 즉시 rejected-write atomicity와 논리 schema 결과; 별도 CS positive constraint3/24292 |

공개 TEST6/TEST12 및 shell catalog0/teardown은 fixture/session cleanup에
대응한다. R10은 immediate single-session COMMIT/ROLLBACK/savepoint와
statement atomicity로 한정한다. R12를 trigger/OOS client-template physical
insertion 증거로 확대하지 않는다.

R20/CBRD-27237의 aborted UPDATE 뒤 vacuum은 별개이며 이 티켓으로 닫지
않는다. vacuum eligibility/completion, physical leak, reclaim, chain ownership,
retry, unchanged-chain reuse, recovery/restart durability, HA transport는 이 proof에 없다.
normative 4060/current4086 target 불일치 구간을 피한 fixture이므로 target
conformance credit도 없다. 공유 coverage/README index 수정은 merger가
담당하며 이 문서의 delta를 전달한다.
