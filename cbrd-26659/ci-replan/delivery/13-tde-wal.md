# Ticket13: OOS TDE 파일 귀속, WAL 플래그와 재시작 값

2026-10-08, 소스 `fb567a629cdb390fff920542173fa36f454c74a0`. 새 private shell 케이스 1개가 native contained OptDebug 실행에서 **실행 1 / 성공 1 / 실패 0 / 건너뜀 0**, 주장 30개 모두 OK로 통과했다. 암호화된 lazy OOS 파일의 소유자/알고리즘, 실제 OOS 사용자 데이터 WAL 플래그, SA DELETE/INSERT 이후 정상 재시작 값을 확인한다. **기존 NONE OOS 파일의 AES 적용은 아직 미검증이고, 암호문/평문 부재 검사도 미확보다.** R27 전체 암호화 계약을 충족했다는 결론은 아니다.

선택 케이스는 `shell/_40_guava/cbrd_26659_tde_wal/cases/cbrd_26659_tde_wal.sh` 하나다. 같은 디렉터리의 `setup.sql`, `values.sql`, `tde_observe.py`와 기존 `shell/_40_guava/oos_common/oos_observe.py`를 사용한다. `init test` → `write_ok`/`write_nok` → `finish` 관례를 유지하고, 이름이 일치하는 `cases/*.sh`로 발견된다. 생성 답안이나 engine hook은 없다. 기존 `tbl_enc_08/14`의 파일 진단, `log_enc_04`의 TDE 플래그 관찰 방식을 강화했으며 이 기존 케이스들은 변경하지 않았다.

## 검토된 독립 모델

실행 전 [oracle.md](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket13/oracle.md)와 [independent-model.json](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket13/independent-model.json)을 저장했다. 검토자는 값/해시/직렬화/청크를 별도로 계산하고 [root-oracle-review.md](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket13/root-oracle-review.md)에서 실제 파일과 실행 범위를 승인했다. 최초 승인 커밋은 `de946132e`, 지원 범위 수정 승인 커밋은 `55bfbb69a`다. 결과를 캡처해 기대값으로 만들지 않았다.

스키마는 작은 plain 메타데이터 표 `oos_model`과 `(id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING)` 표 두 개다. `oos_lazy`는 큰 값 쓰기 전에 `ENCRYPT=AES`, `oos_existing`은 항상 NONE이다. 임시 ID0의 payload/tag가 각각 정확히 1바이트임을 확인하고 COMMIT/DELETE/COMMIT하여 실제 heap을 할당한 뒤 OOS 파일 부재를 관찰한다. 24바이트 이하 직렬화 값은 OOS 후보가 아니며 영구 값 모델에는 ID0가 없다.

| ID | 순서가 있는 payload 바이트 구간 | payload 바이트 | 직렬화 바이트 | 청크 | tag 바이트×300 | payload MD5(소문자 hex 텍스트) |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 2 | d1×1401, e2×1403, f3×1403 | 4207 | 4212 | 1 | 22 | `5a43433dc26414a3625551ee8fc23cd2` |
| 3 | 12×7001, 34×6501, 56×6501 | 20003 | 20008 | 2 | 33 | `127967dc901ebb2776d754d2257cadf3` |
| 4 | 78×11001, 9a×11000, bc×11000 | 33001 | 33008 | 3 | 44 | `ec5759eaa4472233734552dfd216c552` |

전체 payload/tag 등식과 독립 literal digest를 함께 확인한다. 매 단계 row_count/matched_rows/value_ok/digest_ok가 모두 2이고 tag 합계는 600이다. 초기 두 표의 ID2/3 합계 payload는 24210바이트, OOS 청크 3개/슬롯 바이트 `4212+20008+3×24=24292`다. SA에서 lazy ID3를 삭제하고 ID4를 INSERT SELECT한 뒤 lazy는 ID2/4, payload 합계 37208, 청크 4개/슬롯 바이트 `4212+33008+4×24=37316`이다. existing은 끝까지 ID2/3의 정확한 원래 값을 보존한다.

## 실제 관찰 범위

| 주장 번호 / 단계 | 독립 기대와 실제 증거 | 인정되는 범위 |
| --- | --- | --- |
| 1–6: 준비/inline 대조 | 실제 `cubrid_rel`의 optdebug, 소유한 비어 있던 키 디렉터리의 새 키, 일반/숨김 paramdump, 두 heap의 OOS 파일 부재 | 요구된 진단 분기와 TDE 설정이 실행됨; legacy OK/skip 대체 없음 |
| 7–12: 초기 값/물리 파일 | 정확한 ID2/3 값과 3/24292 SHOW, full diagdb 파일 헤더와 SHOW VFID/class OID/HFID가 같은 소유자, lazy AES와 existing NONE | 이 fixture의 암호화된 lazy OOS 생성과 plain 파일 공존 |
| 13–14: SA WAL | 이미 생성된 lazy 파일에 대한 DELETE의 `RVOOS_DELETE` 플래그 **2개**, INSERT의 `RVOOS_INSERT` 플래그 **3개**; 각각 분리된 실제 `csql.err`를 `.log`로 보존 | 사용자 chunk WAL prior-node 암호화 플래그; 새 OOS metadata-header INSERT와 혼동하지 않음 |
| 15–23: SA 값/CS reopen | lazy ID2/4의 전체 값, existing ID2/3 생존 값, 4/37316 및 3/24292, 양쪽 class/heap/OOS 식별자 불변, AES/NONE 유지 | 정상 서버 재시작을 통한 읽기/값/알고리즘 메타데이터 보존 |
| 24: 범위 기록 | `oos13.scope.log`가 기존 파일 적용/암호문/HA 미검증을 명시 | 커버리지 크레딧을 추가하는 주장이 아님 |
| 25–30: 정리 | 소유 서버 부재, DB 삭제 성공 분기, 등록/fixture/keystore 부재, 설정 복원 | 정상 실행 및 실패 실행의 소유 리소스 정리 |

실제 a04에서 lazy는 class OID `0|195|5`, heap VFID `1|768`, HFID `769|1|768`, OOS VFID `1|960`이었다. existing은 class `0|195|7`, heap `1|896`, HFID `897|1|896`, OOS `1|1024`였다. 초기/재시작 diagdb는 각각 78개 full file header를 파싱했고, saved SHOW의 해당 식별자와 연결했다. 식별자의 숫자를 지우지 않는다. 이 숫자는 해당 실행의 영수증이며 portable 기대값은 파일 간 정확한 관계다.

WAL 분류의 소스 근거는 [tde.h:107](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/tde.h:107)의 `LOG_MAY_CONTAIN_USER_DATA` 및 RVOOS 두 항목, [log_manager.c:2241](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/transaction/log_manager.c:2241)의 사용자 데이터/페이지 알고리즘 조건, [log_append.cpp:1602](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/transaction/log_append.cpp:1602)의 실제 진단 직후 `node->tde_encrypted=true` 설정이다. `oos_log_insert_physical`/`oos_log_delete_physical`은 전체 chunk redo/undo 이미지를 기록한다. [source-diagnostic-hashes.json](/home/vimkim/tmp/oos-developer-regressions-20261008/ticket13/source-diagnostic-hashes.json)에 관련 소스 9개 해시를 보존했다. 이 증거는 디스크 암호문을 직접 읽은 결과가 아니다.

## 시도와 보존된 판정

모든 시도는 `/home/vimkim/tmp/oos-developer-regressions-20261008/validation.lock`을 배타적으로 잡은 뒤 준비/복사/DB/native 실행/판정/정리를 수행했다. native shell만 사용하고 CTP fallback이나 `TESTKIT_SLOT_VOLATILE`은 사용하지 않았다.

| 시도 경로 | 결과 / 원인 | runner / case / 준비 시간(초) |
| --- | --- | --- |
| `/home/vimkim/tmp/oos306-sh13-a01` | 1 실행, fail1/skip0; full-header 파서가 제품 시스템 파일 유형 `VACUUM DATA`의 공백을 거부. 의도한 ARIA 음성 대조로 인정하지 않음 | 10.414 / 8.918 / 2.113 |
| `/home/vimkim/tmp/oos306-sh13-a02` | 초기 lazy의 기대 AES만 복사본에서 ARIA로 변경. 정확한 owned OOS 알고리즘 검사에서 거부, 1 실행/fail1/skip0, helper 거부와 실패 정리 통과. 검토된 원본은 수정하지 않음 | 10.185 / 8.677 / 2.093 |
| `/home/vimkim/tmp/oos306-sh13-a03` | 원래 existing NONE→AES 계획의 ALTER ENCRYPT가 문법 거부됨. 초기 값/파일 AES/NONE 관찰은 통과했으나 WAL 단계에 도달하지 못함. 기존 파일 암호화에 커버리지 없음 | 13.355 / 11.868 / 1.141 |
| `/home/vimkim/tmp/oos306-sh13-a04` | 승인된 지원 범위 원본: exact1/성공1/fail0/skip0, 30개 연속 번호 주장 모두 OK, helper/cleanup 각각 0 | **30.313 / 20.567 / 3.110** |

a04의 잠금 취득 후 invocation/검증/복원은 31.392초이며 준비 복사/설정 3.110초는 별도다. 잠금 대기와 root의 최초 build 129.45초는 testcase 시간에 넣지 않았다. SQL 케이스를 이 티켓에서 실행하지 않았고 SQL 시간과 합치지 않았다. 최종 전체 shell 집합 비용은 Ticket14에서 별도로 측정한다.

각 시도에는 identity/preflight/config/command/source hashes/run/status/verify/cleanup/time 영수증이 있다. 실제 runner는 `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`이며 preflight의 source/install commit match와 containment=available이 확인되었다. CTP Git `9c62858b10005d721546cc007be260844033b9e9`의 기존 수정 상태는 identities.json에 보존되며 pristine upstream 자산으로 가정하지 않는다. a02의 `negative-control-confirmed.log`, a04의 `retained-proof-verification.json`이 상세 검증을 연결한다. a04 raw case evidence는 `CTP/result/shell/case-logs/_40_guava/cbrd_26659_tde_wal/cases/case/`에 **85개 파일**로 남아 있다. `.log`를 사용해 native capture의 지원 확장자 필터를 통과하며 SHOW/diagdb, 일반·숨김 paramdump, SA TDE 원본, 값/식별자 proof를 실제 보존했음을 확인했다. `deletedb` 성공 stdout은 비어 있을 수 있으므로 해당 원본 로그의 존재, guarded status=0의 assertion26 및 정리 상태를 사용한다.

## 설정과 정리

source-matching OptDebug `11.5.0.2637-fb567a6`, root가 준비한 install/JDBC, Java8, CTP assets를 각 시도의 전용 복사본으로 묶었다. shell은 CS SQL + 명시적인 SA WAL 단계, 데이터/로그 페이지 16KiB, 데이터/로그 볼륨 64MiB, `tde_default_algorithm=AES`, `er_log_tde=yes`, `enable_string_compression=no`, 절대 경로의 소유 `tde_keys_file_path`를 썼다. er_log_tde는 PRM_HIDDEN이므로 `paramdump --dump-flag 8` 원본도 필수다. public JDBC/HA fixture의 물리 상태를 관찰한 것으로 주장하지 않는다.

DB 이름 `oos13_tde`는 9자다. 기존 등록을 먼저 거부하고 각 mkdir 성공과 create 시도를 별도로 기록한다. 새 key 내용은 출력하지 않는다. timeout에는 kill-after=5s를 적용하며 실제 `ready=1`을 엄격히 파싱한다. EXIT/TERM/INT 정리는 정확한 DB argument를 가진 소유 `cub_server`만 정지하고, 필요한 경우 제한된 TERM/KILL을 사용한다. DB/키 디렉터리는 소유권과 등록 제거를 확인한 뒤만 삭제한다. 실패 a01/a02/a03과 정상 a04 모두 소유 정리와 native slot/outer registry/config/process 리소스 조건이 확인되었다. a03의 cleanup.exit는 1인데, 이는 실패로 실행되지 않은 필수 WAL/완료 log token이 없기 때문이며 리소스 조건은 모두 통과했다. a01/a02/a04는 cleanup.exit=0이다. timeout 강제 종료 분기를 실제 실행했다는 크레딧은 없다. 호스트의 원래 Debug 설정, workenv, CCI dirt는 변경하지 않았다.

## R27/R28 전달 판정

**R27 부분 검증:** lazy AES OOS 파일의 exact owner/algorithm, 기존 NONE 파일 공존/생존 값, 실제 사용자 데이터 RVOOS INSERT/DELETE encrypted-flag, 정상 reopen의 전체 값/통계/식별자, owned TDE 정리와 비용을 확인했다. 암호화된 실제 페이지/WAL 바이트나 plaintext absence, crash redo/undo는 증명하지 않았다.

**R27 미충족 기준 — 기존 파일의 알고리즘 적용:** `ALTER TABLE … ENCRYPT`는 [csql_grammar.y:19978](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/parser/csql_grammar.y:19978)의 CREATE option만 지원하며 legacy `tbl_enc_03/result.anser`도 ALTER의 문법 거부를 기대한다. `xfile_apply_tde_to_class_files`에는 기존 OOS 적용 분기가 있지만 CREATE는 클래스 알고리즘을 [execute_schema.c:10300](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/execute_schema.c:10300)에서 큰 값 쓰기 전에 설정한다. 마지막 적용 호출은 [execute_schema.c:10426](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/query/execute_schema.c:10426), 같은 알고리즘은 [file_manager.c:6027](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/src/storage/file_manager.c:6027)에서 바로 반환한다. 파티션 경로도 클래스 알고리즘을 새 heap에 먼저 설정한다. 승인된 SQL/utility 경계에서 NONE→AES 기존 OOS 경로를 확인하지 못했으므로 해당 필수 기준은 **OPEN / UNVERIFIED capability gap**이다. 기존 NONE 대조가 이 기준을 대신하지 않는다. 이 정책/경로 요구를 삭제하거나 private API hook으로 녹색화하지 않았다.

**R28 미검증:** ordinary HA의 contained 두 노드/transport 준비 후속 작업은 유지한다. 이 티켓은 단일 DB fixture이고 복제 값/queue alignment에 크레딧이 없다. 지원된 자동화 전달은 끝났지만 위 물리 암호화 계약 전체의 미충족 기준은 계속 coverage disposition으로 남는다.

Private worker는 `/home/vimkim/gh/cubrid-testcases-private-ex/oos-13-tde-wal`, 브랜치 `task/oos-13-tde-wal`이다. 기본 구현 `39484efe1`, heap 초기화 `a7b284a85`, 숨김 설정/준비 predicate `de946132e`, 제품 파일 유형 파서 수정 `498503e7e`, 지원 범위 `55bfbb69a`를 보존했다. a04 실행 후 현재 private integration `2442246a1`을 worker merge `523f6e652`에 포함했고, 선택 케이스/공유 observer 해시는 동일하다. 문서 worker는 `docs/oos-13-tde-wal`; root/merger가 shared coverage와 README index를 반영한다. 새 public testcase, engine 수정, push/JIRA/GHA 실행은 없다.
