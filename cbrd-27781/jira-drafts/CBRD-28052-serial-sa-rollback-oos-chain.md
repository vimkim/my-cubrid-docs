# [OOS][SERIAL] SA 모드에서 NEXT VALUE를 롤백하면 serial 행이 삭제된 OOS chain을 가리킨다

**한 줄 요약**: [CBRD-28035](https://jira.cubrid.org/browse/CBRD-28035)(serial OOS chain 누수)를 고치다가 찾은 별도 결함이다. SA 모드에서 comment가 OOS에 있는 serial에 NEXT VALUE를 실행하고 트랜잭션을 롤백하면, `_db_serial` 행은 롤백으로 지워진 OOS chain을 계속 가리킨다. 그 뒤 comment를 읽으면 `ER_HEAP_OOS_CORRUPTED_RECORD`(-1397)가 난다.

## Issue Triage

**이슈 수행 목적**: SA 모드에서 NEXT VALUE를 실행한 트랜잭션을 롤백해도 serial 행과 그 행이 가리키는 OOS chain이 서로 맞는다. 즉 롤백 뒤에도 serial의 comment를 정상으로 읽을 수 있다.

**이슈 수행 이유**: SA 모드에서 `serial_update_serial_object`는 sysop 없이 행을 갱신한다. 이 함수는 `lock_get_object_lock`이 `X_LOCK`이 아닐 때만 sysop을 시작하는데, SA 빌드의 `lock_get_object_lock`은 항상 `X_LOCK`을 돌려준다. 행 자체는 redo 전용 로그(`log_append_redo_recdes`)와 `spage_update`로 덮어쓰므로 롤백해도 되돌아가지 않는다. 반면 `heap_attrinfo_transform_to_disk`가 새 OOS chain을 쓸 때는 undo가 있는 로그(`RVOOS_INSERT`)를 남긴다. 그래서 롤백은 새 chain만 지우고 행은 그대로 두어, 행이 지워진 chain을 가리키게 된다(코드에서 추론, 로그 레코드로는 확인하지 않음). 이 결과는 `csql -S`와 단위 테스트로 재현했다.

**영향**: 4K page DB(이름이 긴 serial이면 8K page DB도)에서 serial comment를 길게 단 경우, SA 모드로 NEXT VALUE를 실행하고 롤백하면 그 serial의 comment가 손상된다. 손상 뒤 `_db_serial`에서 comment를 읽는 질의는 -1397로 실패한다. `cubrid checkdb -S`는 이 상태를 찾지 못했다(종료 코드 0). SA 모드는 `csql -S`와 standalone 유틸리티이므로 일반 서비스 경로보다 드물지만, 운영자가 SA 모드로 작업하다 롤백하는 것만으로 생긴다. 서버 모드에서는 시험한 범위에서 생기지 않았다. 기본 16K page에서는 serial 행이 OOS 기준에 닿지 않아 생기지 않는 것으로 본다(CBRD-28035에서 한 추론).

**이슈 수행 방안**: TBD - ANALYSIS 단계에서 해결 방안과 구현 범위를 결정한다.

---

## AI-Generated Context

## Description

[CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978)의 Sub-task다. OOS를 쓰는 serial 행 갱신 경로에서, SA 모드의 롤백이 행과 OOS chain을 서로 다른 상태로 되돌리는 문제를 다룬다. CBRD-28035의 수정(PR [CUBRID/cubrid#8492](https://github.com/CUBRID/cubrid/pull/8492))이나 ADR-0008(PR [CUBRID/cubrid#8434](https://github.com/CUBRID/cubrid/pull/8434))과는 독립된 결함이다.

### Repro (2026-11-11, debug 빌드)

4K page DB를 쓰면 OOS 기준이 1KB(`DB_PAGESIZE/4`)로 낮아진다. comment는 압축되지 않는 값이어야 OOS로 나간다.

```bash
cubrid createdb --db-page-size=4K --log-page-size=4K --db-volume-size=64M --log-volume-size=64M sarbdb en_US.utf8

long=$(head -c 4000 /dev/urandom | base64 -w0 | tr -dc 'A-Za-z0-9' | head -c 1000)
csql -S -u dba sarbdb -c "create serial s1 nocache comment '$long'"
csql -S -u dba sarbdb -c "select s1.next_value"
csql -S -u dba sarbdb -c "select current_val, if(comment = '$long', 'intact', 'CHANGED') from _db_serial where name = 's1'"

printf 'select s1.next_value;\n%.0s' 1 2 3 4 5 > rb.sql; echo "rollback;" >> rb.sql
csql -S -u dba sarbdb --no-auto-commit -i rb.sql

csql -S -u dba sarbdb -c "select current_val, if(comment = '$long', 'intact', 'CHANGED') from _db_serial where name = 's1'"
cubrid checkdb -S sarbdb
```

### Expected Result

롤백 뒤에도 comment를 읽는 질의가 성공하고 `'intact'`를 돌려준다.

### Actual Result

| 시점 | comment 조회 | `show heap oos of _db_serial`의 `Oos_num_recs` |
|---|---|---|
| 첫 NEXT VALUE 커밋 뒤 | `1 'intact'` | 1 |
| NEXT VALUE 5회 후 롤백 뒤 | `ERROR: Internal error: out-of-row storage record metadata is inconsistent or corrupted.` (-1397) | 1 |
| `cubrid checkdb -S` | 종료 코드 0, 오류 보고 없음 | |

위 표는 PR #8434 head `0d9732a63`에 CBRD-28035 수정을 얹은 빌드(`11.5.0.2935-61f2264`)에서 얻었다. 같은 날 다음 리비전에서도 단위 테스트(`unit_tests/oos/sql/test_oos_sql_serial.cpp`에 롤백 케이스를 더한 것)가 같은 -1397로 실패했다.

- `feature/oos-merge` `67220b7e23`, CBRD-28035 수정 없음
- `feature/oos-merge` `67220b7e23` + CBRD-28035 수정(`bee96e666`)
- PR #8434 head `0d9732a63` + CBRD-28035 수정

서버 모드는 같은 절차(NEXT VALUE 5회 후 롤백, 3회 반복)에서 OOS 레코드 1개와 정상 comment를 유지했다. CBRD-28035 브랜치와 PR #8434 위 브랜치 모두 같았다.

### 경로 (`feature/oos-merge` `67220b7e23`)

- `serial_update_serial_object`는 `lock_get_object_lock`의 결과가 `X_LOCK`이 아닐 때만 sysop을 시작한다([serial.c:1557](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/src/query/serial.c#L1557), [serial.c:1565](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/src/query/serial.c#L1565)).
- SA 빌드의 `lock_get_object_lock`은 `#if !defined (SERVER_MODE)` 분기에서 항상 `X_LOCK`을 돌려준다([lock_manager.c:8006](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/src/transaction/lock_manager.c#L8006)). 그래서 SA 모드에서는 sysop이 없다.
- 새 레코드는 `heap_attrinfo_transform_to_disk`로 만든다([serial.c:1575](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/src/query/serial.c#L1575)). 이때 OOS로 보낼 열은 `heap_attrinfo_insert_to_oos`로 새 chain에 쓰고([heap_file.c:14978](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/src/storage/heap_file.c#L14978)), chunk마다 undo가 있는 `RVOOS_INSERT`를 남긴다([oos_file.cpp:1210](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/src/storage/oos_file.cpp#L1210)).
- 행은 `log_append_redo_recdes`(redo 전용)를 남긴 뒤 `spage_update`로 덮어쓴다([serial.c:1589](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/src/query/serial.c#L1589), [serial.c:1592](https://github.com/CUBRID/cubrid/blob/67220b7e230ff1587ba5940001d72e10477a1fc4/src/query/serial.c#L1592)).
- 서버 모드에서 sysop 없이 이 경로를 타는 경우는 같은 트랜잭션이 serial을 만들거나 고친 때뿐이다. 이때는 DDL의 undo가 행 전체를 되돌리므로 문제가 드러나지 않는다(CREATE 또는 ALTER 후 NEXT VALUE, 롤백으로 확인). 서버 모드의 다른 경우에는 행 갱신과 chain 삽입이 한 sysop 안에서 함께 커밋된다. 트랜잭션 롤백은 커밋된 sysop을 되돌리지 않으므로 행과 chain이 함께 남는다(코드에서 추론).

### 범위

- OOS 코드가 없는 develop에는 해당하지 않는다.
- comment가 OOS로 나가는 serial에만 해당한다. comment는 1024바이트로 제한되므로 4K page, 또는 이름이 긴 serial의 8K page DB에서만 생긴다(CBRD-28035에서 한 추론).
- OOS가 없는 serial도 SA 모드 롤백 뒤 값이 되돌아가지 않지만, 이는 serial 값이 트랜잭션을 따르지 않는 기존 동작이며 이 이슈의 범위가 아니다.

### ANALYSIS에서 확인할 것

- 롤백 대신 SA 모드 비정상 종료 후 복구에서도 같은 상태가 생기는가?
- 문장 단위 롤백(savepoint 롤백, 오류로 인한 부분 롤백)에서도 생기는가?
- cache serial의 값 저장 경로(`serial_store_cur_val_of_serial`)와 ALTER SERIAL의 write-back도 SA 모드에서 같은 결과를 내는가?
- 이미 손상된 serial을 찾거나 고칠 방법이 필요한가? `checkdb`는 이 상태를 보고하지 않았다.

### 관련 이슈

- [CBRD-28035](https://jira.cubrid.org/browse/CBRD-28035): 같은 함수에서 이전 OOS chain을 회수하지 않는 누수. 원인이 다르며, 그 수정을 적용해도 이 결함은 남는다.
- [CBRD-27991](https://jira.cubrid.org/browse/CBRD-27991): serial을 만들거나 고친 트랜잭션을 롤백해도 서버의 serial 캐시와 NEXT VALUE 실행 계획이 남는 문제. 같은 serial 롤백 경로를 다루지만, 이 결함은 서버 캐시가 아니라 SA 모드의 행과 OOS chain 불일치다.
- [CBRD-27981](https://jira.cubrid.org/browse/CBRD-27981): snapshot 없는 OOS reader와 회수가 겹칠 수 있는지 조사한다. CBRD-28035를 찾은 계기이며, 이 결함과 문제는 다르다.
