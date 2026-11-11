# [OOS][SERIAL] serial 행 갱신마다 comment의 OOS chain이 새로 쓰이고 이전 chain은 회수되지 않는다

**한 줄 요약**: [CBRD-27981](https://jira.cubrid.org/browse/CBRD-27981) 조사 중 MVCC가 꺼진 catalog 행이 OOS를 가질 수 있는지 확인하다가 실행으로 재현한 별도 결함이다. comment가 OOS로 나간 serial은 NEXT VALUE가 `_db_serial` 행을 갱신할 때마다 OOS chain을 새로 쓰고, 이전 chain은 아무도 회수하지 않아 OOS 공간이 계속 늘어난다.

## Issue Triage

**이슈 수행 목적**: serial 행을 갱신해도 OOS chain이 늘어나지 않는다. 즉 갱신 뒤 `_db_serial`의 OOS 레코드는 행이 실제로 참조하는 것만 남는다.

**이슈 수행 이유**: serial 값을 내줄 때 `_db_serial` 행을 고치는 경로는 `heap_update`를 거치지 않는다. `heap_attrinfo_transform_to_disk`로 새 레코드를 만들고 `spage_update`로 slot을 직접 덮어쓴다. `transform_to_disk`는 OOS로 보낼 열이 있으면 그 값을 새 chain으로 쓴다. 그런데 덮어쓰기 전 레코드가 가리키던 chain을 회수하는 단계(`heap_oos_delete_unreferenced`)는 heap delete와 update 경로에만 있다. 그래서 갱신할 때마다 이전 chain이 고아로 남는다. debug 빌드에서 NEXT VALUE 50회와 100회를 실행해, OOS 레코드 수가 실행 횟수만큼 늘어나는 것을 확인했다.

**영향**: comment가 OOS로 나간 serial을 쓰는 DB는 NEXT VALUE를 쓸수록 `_db_serial`의 OOS 파일이 커진다. 실측에서는 갱신 100회에 OOS 레코드 100개(4K page 35개)가 쌓였고, 서버를 재시작해도 줄지 않았다. 버려진 chain은 non-MVCC 행의 것이라 vacuum도 회수하지 않는 것으로 보인다(소스 근거). 조회 결과는 틀리지 않는다. 행은 마지막 chain을 가리키고, comment와 현재 값은 정상으로 읽혔다. 기본 16K page에서 이 조건이 얼마나 자주 생기는지는 모른다. 그 경우 OOS로 나가려면 serial 행이 4KB를 넘어야 하고, 그러려면 다국어 comment처럼 큰 값이 필요하다.

**이슈 수행 방안**: TBD - ANALYSIS 단계에서 해결 방안과 구현 범위를 결정한다.

---

## AI-Generated Context

## Description

### 재현 (PR #8434 head `443073283`, debug 빌드, 2026-11-11)

4K page DB를 쓰면 OOS 기준이 1KB(`DB_PAGESIZE/4`)로 낮아져 쉽게 재현된다. comment는 압축되지 않는 값이어야 한다. CUBRID는 긴 문자열을 압축하므로, 같은 문자를 반복한 값은 압축된 뒤 기준을 넘지 못해 inline에 남는다.

```bash
cubrid createdb --db-page-size=4K --log-page-size=4K --db-volume-size=64M --log-volume-size=64M serialoosdb en_US.utf8
cubrid server start serialoosdb

long=$(head -c 4000 /dev/urandom | base64 -w0 | tr -dc 'A-Za-z0-9' | head -c 1000)
csql -u dba serialoosdb -c "create serial s_short nocache comment 'short'"
csql -u dba serialoosdb -c "create serial s_long nocache comment '$long'"

for s in s_short s_long; do
  for i in $(seq 1 100); do echo "select $s.next_value;"; done > next.sql
  csql -u dba serialoosdb -i next.sql > /dev/null
  csql -u dba serialoosdb -l -c "show heap oos of _db_serial" | grep -E 'Oos_num_user_pages|Oos_num_recs'
done
```

관찰한 결과는 다음과 같다. 같은 절차를 N=50으로도 실행했다.

| 시점 | `Oos_num_recs` | `Oos_num_user_pages` | `Oos_recs_sumlen` |
|---|---|---|---|
| serial 생성 직후 | 0 | 0 | 0 |
| `s_short` NEXT VALUE 100회 뒤 (대조군) | 0 | 0 | 0 |
| `s_long` NEXT VALUE 50회 뒤 (N=50 실행) | 50 | 18 | 52200 |
| `s_long` NEXT VALUE 100회 뒤 (N=100 실행) | 100 | 35 | 104400 |
| 서버 재시작 뒤 (N=100 실행) | 100 | 35 | 104400 |

- 레코드 하나는 1044바이트로, comment 1000바이트에 44바이트가 붙은 크기다. 행이 참조하는 chain은 comment 하나뿐이므로 100개 중 99개가 고아다.
- 100회 뒤 `current_val`은 100이고, comment는 처음 넣은 값과 같았다.
- serial을 만든 직후에는 같은 comment가 inline에 있었다. 첫 NEXT VALUE부터 OOS로 나갔다. 생성 경로가 왜 OOS로 보내지 않는지는 확인하지 않았다.

### 경로 (PR head `443073283`)

- `_db_serial`의 `comment`는 `varchar(1024)`다([schema_system_catalog_install.cpp:932](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/object/schema_system_catalog_install.cpp#L932)). 행 크기가 `DB_PAGESIZE/4`를 넘으면 가장 큰 가변 열부터 OOS로 보낸다([heap_file.c:13783](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/heap_file.c#L13783)).
- NOCACHE serial의 NEXT VALUE(`xserial_get_next_value_internal`, [serial.c:1446](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/query/serial.c#L1446))와 cache serial의 값 저장(`serial_store_cur_val_of_serial`, [serial.c:1086](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/query/serial.c#L1086))은 모두 `serial_update_serial_object`를 부른다.
- `serial_update_serial_object`는 `heap_attrinfo_transform_to_disk`로 레코드를 만들고([serial.c:1575](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/query/serial.c#L1575)), `spage_update`로 slot을 덮어쓴다([serial.c:1592](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/query/serial.c#L1592)).
- `heap_attrinfo_transform_to_disk_internal`은 OOS로 보낼 열이 있고 보류 버퍼가 없으면 `heap_attrinfo_insert_to_oos`로 새 chain을 바로 쓴다([heap_file.c:14905](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/heap_file.c#L14905)). 이전 레코드의 OOS 참조를 다시 쓰는 단계는 없다.
- 이전 chain을 회수하는 `heap_oos_delete_unreferenced`([heap_oos.cpp:1038](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/heap_oos.cpp#L1038))는 heap delete와 update의 non-MVCC 분기에서만 불린다. serial 경로는 이 분기를 거치지 않는다.

### 범위

- `feature/oos-merge`와 PR #8434의 base `95ff126a8`에도 같은 경로가 있다(소스 확인, 실행하지 않음). PR #8434가 만든 결함이 아니다.
- develop에는 OOS 코드가 없으므로 해당하지 않는다.
- cache serial은 cache 블록을 새로 받을 때와 남은 값을 되돌려 쓸 때만 행을 갱신한다. 그래서 같은 횟수의 NEXT VALUE라면 NOCACHE serial보다 누수가 훨씬 느릴 것으로 추정한다. 실행으로는 확인하지 않았다.

### ANALYSIS에서 확인할 것

- serial 행을 직접 갱신하는 다른 경로(`serial.c`의 write-back, ALTER SERIAL)도 같은 누수를 만드는가?
- `transform_to_disk`를 쓰면서 heap update를 거치지 않는 다른 호출자가 있는가? 있다면 같은 누수가 생기는가?
- 이미 쌓인 고아 chain을 정리할 방법이 필요한가? 예를 들어 compactdb나 checkdb가 이를 찾거나 지울 수 있는가?
