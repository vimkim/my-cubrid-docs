# CBRD-27981 조사: snapshot 없는 OOS reader와 tail-first 회수의 겹침

- 질문: MVCC snapshot 없이 OOS chain을 읽는 호출자가 회수 도중의 chain을 읽을 수 있는가? 읽을 수 있다면, head stamp만 확인하는 reader가 연속 chunk에서 다른 chain의 바이트를 돌려줄 수 있는가?
- 독자: [CBRD-27981](https://jira.cubrid.org/browse/CBRD-27981)을 triage하거나 닫을지 정할 사람, 그리고 PR [#8434](https://github.com/CUBRID/cubrid/pull/8434) 리뷰어.
- 범위: 회수 경로 세 가지를 다룬다. (a) vacuum REMOVE sysop의 postpone 회수, (b) `RVOOS_NOTIFY_VACUUM` 처리, (c) non-MVCC 연산의 commit 회수. reader는 서버 쪽 OOS 읽기 진입점에 이르는 모든 호출자를 대상으로 한다.
- 기준: `CUBRID/cubrid` PR #8434 head [`94ed2ea46`](https://github.com/CUBRID/cubrid/commit/94ed2ea463f17694db33a283b56fdeb42856e835)(base `feature/oos-merge` `95ff126a8`). 소스만 읽었고, 빌드와 실행은 하지 않았다.
- 조사일: 2026-11-11(Asia/Seoul).
- 추가 조사(같은 날): 남은 질문 1을 PR head [`443073283`](https://github.com/CUBRID/cubrid/commit/443073283d89e4511b2fa9a5b6a16898770f7e65)에서 확인했다. 이번에는 debug 빌드로 실행한 결과도 포함한다. 결과는 아래 "추가 조사: MVCC가 꺼진 catalog 행"에 있고, 결론의 (c) 항목을 그에 맞게 고쳤다.

## 결론

(a)와 (b)에서는 회수 중인 chain과 겹칠 수 있는 snapshot 없는 reader를 찾지 못했다. 이 판정은 `94ed2ea46`의 소스 판독에 근거한다. (c)에서는 겹칠 수 있는 조합 하나가 원리상 성립한다. 이 판정은 `443073283`의 소스 판독과 실행에 근거하고, 경합 자체는 재현하지 않았다.

- **(a) vacuum REMOVE**: OOS 회수는 vacuum이 heap home page의 WRITE latch를 쥔 동안 끝난다. 다음 두 종류의 reader는 모두 home page latch를 쥔 채 OOS를 읽는다.
  - snapshot 없이 heap 레코드를 OOS 값으로 펼치는 reader(`HEAP_RECDES_CONSUME_RAW_BYTES`)
  - 레코드를 그대로 두고 attribute layer에서 OOS 값을 읽는 reader(`HEAP_RECDES_DONT_CONSUME_RAW_BYTES`)

  따라서 이 reader들은 회수 전의 온전한 chain을 보거나, slot이 이미 비어 레코드를 보지 못한다.
- **(b) `RVOOS_NOTIFY_VACUUM`**: 이 경로가 회수하는 chain은 UPDATE가 버린 이전 버전의 chain이다. heap slot의 현재 레코드는 이 chain을 가리키지 않는다. latch를 놓은 뒤 OOS를 읽는 유일한 snapshot 없는 경로는 instance X lock을 쥐고 있어 동시 UPDATE를 막는다.
- **(c) non-MVCC commit 회수**: `db_ha_apply_info`에서 다음 조합이 원리상 성립한다.
  - `copied_log_path`(`varchar(4096)`)가 길면 행이 `DB_PAGESIZE/4`를 넘어 OOS를 가진다.
  - 이 클래스에 대한 SELECT는 cached scan 대상이고 instance lock을 걸지 않는다. 그래서 page 복사본에 남은 이전 OOS 참조로 읽을 수 있다.
  - applylogdb의 counter UPDATE는 바뀌지 않은 `copied_log_path`도 새 chain으로 쓰고, 이전 chain을 commit 때 회수한다(실행으로 확인).

  serial은 SELECT가 instance S lock을 걸어 막히는 것으로 추론한다. collation은 OOS를 가질 수 없다. 실제 위험은 낮다. 경로가 page의 1/4을 넘어야 하고, 16K page에서는 약 4KB가 필요하기 때문이다.

`oos_read_within_page` 주석은 일반 fix를 쓰는 근거로 "head의 identity를 확인했으므로 chain이 살아 있다"고 적는다. 위 결론에 따르면 이 근거는 head stamp가 아니다. 실제 근거는 호출자 쪽의 보호, 즉 home page latch, instance lock, A'다.

## 배경: 회수와 reader가 어긋날 수 있는 지점

### reader는 head만 확인한다

- `oos_read`는 head 페이지를 해제 허용 방식으로 fix하고 head chunk의 identity stamp를 확인한다. 그다음 head 페이지를 놓고 연속 chunk를 읽는다([oos_file.cpp:2898-2948](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/oos_file.cpp#L2898-L2948)).
- 연속 chunk는 `oos_read_within_page`가 일반 `pgbuf_fix(OLD_PAGE)`로 읽는다([oos_file.cpp:2777-2799](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/oos_file.cpp#L2777-L2799)).
- `oos_read_across_pages`는 chunk 순번과 전체 길이만 비교하고, 링크의 `next_chunk_stamp`는 비교하지 않는다([oos_file.cpp:2803-2843](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/oos_file.cpp#L2803-L2843)).

R7이 지적한 이 상태는 리뷰 시점과 같다.

### 회수는 tail부터 한 chunk씩 지운다

`oos_delete_chain`은 chain의 chunk를 모은 뒤 뒤에서부터 지운다([oos_file.cpp:3582](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/oos_file.cpp#L3582)). 각 chunk의 페이지는 그 chunk를 지우는 동안만 WRITE로 fix한다([oos_file.cpp:3589](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/oos_file.cpp#L3589)). 회수 도중에는 head가 남아 있고 뒤 chunk는 이미 지워진 상태가 생긴다. reader가 이 상태에서 head를 확인하면 검사를 통과하고, 지워졌거나 재사용된 연속 slot을 읽는다.

따라서 reader가 회수 시작 전에 chain 참조를 얻었고 회수 도중에 chain을 읽는다면 문제가 된다. 아래에서 회수 경로마다 이런 reader가 있는지 본다.

## 회수 경로별 판정

### (a) vacuum REMOVE의 postpone 회수

vacuum은 레코드를 지우는 sysop 안에서 heap slot을 비우고 회수 intent를 postpone으로 남긴 뒤 sysop을 commit한다. intent는 sysop commit 때 실행된다.

- REC_HOME에서는 home page를 `DONT_FREE`로 dirty 처리한 채 intent를 남기고 commit한다([vacuum.c:2735-2754](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/query/vacuum.c#L2735-L2754)).
- REC_RELOCATION에서는 forward page를 먼저 놓는다. home page는 commit할 때까지 쥐고 있다([vacuum.c:2674-2693](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/query/vacuum.c#L2674-L2693)).

따라서 home page latch를 쥐고 레코드를 본 reader는 두 경우 중 하나만 겪는다. vacuum이 아직 손대지 않아 chain이 온전하거나, slot이 이미 비어 레코드가 없다. 연속 chunk만 지워진 상태는 home page latch가 풀리기 전에 끝난다.

이 보호는 reader가 OOS를 다 읽을 때까지 home page latch를 놓지 않아야 성립한다. 호출자별 확인은 아래 표에 있다. snapshot reader는 이 경로와 겹치지 않는다. REMOVE 대상은 delete MVCCID가 oldest visible보다 오래된 레코드이고, 이런 레코드는 모든 snapshot에서 보이지 않기 때문이다.

### (b) `RVOOS_NOTIFY_VACUUM` 처리

vacuum은 UPDATE의 MVCCID가 모든 활성 snapshot보다 오래된 뒤에만 알림을 처리한다. 처리할 때 heap page는 fix하지 않는다([vacuum.c:3867-3872](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/query/vacuum.c#L3867-L3872), [vacuum_oos.cpp:218-236](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/query/vacuum_oos.cpp#L218-L236)).

회수 대상은 UPDATE가 버린 chain이다. 이 chain은 UPDATE 이후 heap slot의 현재 레코드에서 참조되지 않는다. snapshot 없는 reader가 이 chain을 읽으려면 UPDATE 전에 레코드를 복사해야 한다. 또 UPDATE commit과 vacuum 처리가 끝날 때까지 그 복사본의 OOS를 읽지 않고 있어야 한다. UPDATE는 home page WRITE latch가 필요하므로, latch를 쥔 채 읽는 reader는 이 순서를 만들 수 없다. latch 밖에서 읽는 경로는 아래 표의 `locator_attribute_info_force` 하나다. 이 경로는 instance X lock을 쥐고 있어 다른 트랜잭션의 UPDATE가 끼어들 수 없다.

### (c) non-MVCC 연산의 commit 회수

non-MVCC heap DELETE·UPDATE는 버린 chain의 회수를 트랜잭션(또는 감싼 sysop)의 commit postpone으로 남긴다([heap_oos.cpp:1015-1054](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/heap_oos.cpp#L1015-L1054)). SERVER 모드에서 non-MVCC 연산은 두 가지다([heap_file.c:169-174](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/heap_file.c#L169-L174)).

- MVCC가 꺼진 클래스의 연산. root, serial, collation, ha_apply_info가 해당한다([mvcc.c:683-709](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/transaction/mvcc.c#L683-L709)).
- `UPDATE_INPLACE_*` 연산.

이 회수는 heap page latch 밖, commit 시점에 실행된다. snapshot 검사는 MVCC가 꺼진 클래스에 적용되지 않으므로, snapshot을 가진 reader도 이 경로에서는 A'의 보호를 받지 않는다. 그래서 (c)에 대한 질문은 이렇게 바뀐다. latch를 놓은 뒤 이런 행의 OOS를 읽는 reader가 있는가?

- `UPDATE_INPLACE_*`는 `redistribute_partition_data`, catalog, TDE, boot 같은 DDL·관리 경로에서 호출된다(`locator_sr.c:13309`, `catalog_class.c:3954`, `tde.c:653`, `boot_sr.c:6200`). 이 경로들은 클래스에 강한 lock을 쥐고 있어 같은 클래스의 query scan과 겹치지 않는다고 추론한다(INFERRED, 호출자별 lock 모드는 다시 확인하지 않았다).
- MVCC가 꺼진 클래스의 행이 OOS를 가지려면 레코드가 `DB_PAGESIZE/4`를 넘어야 한다([heap_file.c:13180-13219](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/heap_file.c#L13180-L13219)). class 레코드(root)는 이 직렬화를 거치지 않는다. 나머지 세 catalog의 행이 이 크기를 넘을 수 있는지는 schema를 확인하지 않았다.
- ADR-0008의 B6 행은 "eager cleanup에는 동시 reader가 없다"고 가정한다. 위 두 항목이 확인되면 이 가정이 성립한다.

아래 "추가 조사"에서 두 번째 항목을 확인했다. serial과 ha_apply_info의 행은 OOS를 가질 수 있고, ha_apply_info에서는 겹침 조합이 원리상 성립한다. 따라서 B6의 가정은 ha_apply_info에서 성립하지 않는다.

SA_MODE에서는 모든 연산이 non-MVCC이다. 다만 클라이언트가 하나이고 vacuum이 reader와 동시에 돌지 않으므로 겹침이 없다고 판단한다(INFERRED).

## 호출자 표

OOS를 읽는 서버 쪽 진입점은 셋이다.

- heap 레코드 펼치기 `heap_record_replace_oos_oids`. `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`이면 아무것도 읽지 않는다([heap_oos.cpp:593-598](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/heap_oos.cpp#L593-L598)).
- attribute layer의 `heap_oos_read_grouped_payloads`(`heap_file.c:11696`).
- `heap_oos_value_ref` 읽기(`heap_oos_value_ref.cpp:122`). 참조는 호출 안에서만 살고, 호출 밖에 남는 지연 참조는 없다.

`heap_get_visible_version_internal`은 scan cache에 snapshot과 `snapshot_fnc`가 있고 클래스가 MVCC 대상일 때만 가시성을 검사한다([heap_file.c:27898-27922](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/heap_file.c#L27898-L27922)).

`heap_next`는 레코드를 가져오는 동안 `cache_last_fix_page`를 true로 강제한다. 함수가 끝날 때는 원래 값이 false인 경우에만 page를 놓는다([heap_file.c:8018-8027](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/heap_file.c#L8018-L8027), [8073-8076](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/heap_file.c#L8073-L8076)). `heap_next_1page`도 같다. 따라서 scan cache를 `cache_last_fix_page = true`로 시작한 호출자는 다음 `heap_next`를 부를 때까지 home page를 쥐고 있다.

표의 "OOS 읽을 때 latch"는 reader가 OOS를 읽는 동안 heap home page latch를 쥐고 있는지를 뜻한다. 판정 열의 "보호"는 세 회수 경로 모두와 겹치지 않는다는 뜻이다.

| 호출자 | snapshot | OOS를 읽는 곳 | OOS 읽을 때 latch | 판정 |
|---|---|---|---|---|
| `xlocator_fetch_all`: unloaddb `--latest-image`, `LC_FETCH_CURRENT_VERSION` ([locator_sr.c:2895-2896](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/transaction/locator_sr.c#L2895-L2896)) | NULL | `heap_next(COPY, CONSUME_RAW_BYTES)` 안의 펼치기([2948-2949](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/transaction/locator_sr.c#L2948-L2949)) | 쥠. home page와 forward page를 fix한 채 펼친다(`heap_file.c:27895-27896`, `7623`, `7645`) | 보호 |
| `xlocator_upgrade_instances_domain`(ALTER로 타입 변경) | NULL | `xlocator_lock_and_fetch_all`의 CONSUME 펼치기 | 쥠 | 보호. oldest visible을 고정하고 먼저 vacuum한다(`locator_sr.c:12587-12591`) |
| `redistribute_partition_data` | NULL | COPY 뒤 attribute layer(`locator_sr.c:13277`, `13292`) | home page를 쥠. `spage_next_record`로 PEEK한 page의 watcher를 루프 동안 유지한다(`13234`) | 보호. oldest visible을 고정하고 먼저 vacuum한다(`13157-13183`) |
| CREATE INDEX(offline, SERVER): `btree_sort_get_next`, `btree_sort_get_next_parallel` | NULL. delete MVCCID가 한 번 읽은 `oldest_visible_mvccid`보다 오래된 레코드만 건너뛴다([btree_load.c:6282](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/btree_load.c#L6282)) | `heap_next(PEEK, DONT_CONSUME)`([6205-6207](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/btree_load.c#L6205-L6207)) 뒤 filter([6297](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/btree_load.c#L6297))와 key 생성([6325](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/btree_load.c#L6325)) | 쥠. scan cache를 `true`로 시작한다([btree_sort.c:1119](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/btree_sort.c#L1119), [1281](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/btree_sort.c#L1281)) | 보호 |
| CREATE INDEX(SA_MODE, FK 있음) | NULL | `cache_last_fix_page = !has_fk`라서 COPY로 읽고 latch 밖에서 attribute를 읽는다([btree_load.c:1579-1583](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/btree_load.c#L1579-L1583)) | 놓음 | 보호(SA_MODE, 동시 회수 없음, INFERRED) |
| CREATE INDEX(online) | 있음(`btree_load.c:7466`) | `heap_next(COPY, DONT_CONSUME)` 뒤 attribute layer | 쥠(`7527`) | snapshot reader. 범위 밖 |
| `locator_attribute_info_force`(UPDATE·DELETE 적용) | NULL(`locator_sr.c:7835-7843`에서 snapshot을 비움) | `heap_get_last_version`이나 `locator_lock_and_get_object`의 COPY(DONT_CONSUME) 뒤 attribute layer(UPDATE는 fall-through로 `7886`) | 놓음 | 보호. instance X lock을 쥐고 삭제된 레코드는 거른다(`7825`, `LOG_ERROR_IF_DELETED`). (b)·(c)의 동시 UPDATE를 막는다 |
| `locator_lock_and_get_object_internal`의 다른 호출자(FK 검사 `4454`, `4796` 등) | NULL 가능 | 모두 DONT_CONSUME. 값은 위 `locator_attribute_info_force`로 읽는다 | - | 위와 같다 |
| catalog scan(`catalog_class.c:4972`, `5401`, `5582`), `sp_get_code_attr`, dblink catalog | NULL | `heap_next`/`heap_get_visible_version(PEEK, DONT_CONSUME)` 뒤 attribute layer | 쥠(PEEK이므로 page가 fix되어 있어야 한다) | 보호(INFERRED) |
| `heap_get_class_record`, catalog 레코드 COPY(`catalog_class.c:4009` 등) | NULL | class·catalog 레코드는 OOS를 만드는 직렬화를 거치지 않는다 | - | 해당 없음(INFERRED) |
| query heap scan(cached scan 포함, CBRD-27041) | root class 말고는 snapshot이 있다([scan_manager.c:4369-4376](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/query/scan_manager.c#L4369-L4376)) | cached scan은 page 복사본에서 레코드를 읽고 latch를 놓는다([heap_file.c:6645-6656](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/heap_file.c#L6645-L6656), [27779-27786](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/heap_file.c#L27779-L27786)) | 놓음 | MVCC 클래스: (a)는 snapshot이, (b)는 A'가 막는다. MVCC가 꺼진 클래스: serial은 instance S lock이 막는다(INFERRED). ha_apply_info는 (c)와 겹칠 수 있다(아래 "추가 조사") |

다음 경로는 다시 따라가지 않았다. 이전 조사([reclaim-engine-facts Q4](https://github.com/vimkim/my-cubrid-docs/blob/main/oos/reclaim-engine-facts.md#q4-readers-that-dereference-oos-stubs-without-an-mvcc-snapshot), `dcbf09e4f`)에서 OOS 값을 읽지 않거나 snapshot reader로 분류되었다.

- checkdb, `heap_dump`
- 통계 sampling(`histogram_sampler_sr.cpp:2705`, PEEK)
- dirty snapshot reader

이전 조사는 `btree_load`가 latch를 놓은 COPY에서 OOS를 읽는다고 추론했다(INFERRED). `94ed2ea46`의 SERVER 경로에서는 그렇지 않다. scan cache를 `cache_last_fix_page = true`로 시작하므로 PEEK으로 읽고 page를 쥔다. COPY로 읽는 경우는 SA_MODE의 FK 인덱스뿐이다.

## 추가 조사: MVCC가 꺼진 catalog 행 (`443073283`)

### OOS를 가질 수 있는 행

| 클래스 | OOS 후보 열 | OOS 가능 여부 |
|---|---|---|
| `_db_serial` | `string` 열 4개(식별자, 최대 255자)와 `comment varchar(1024)`([schema_system_catalog_install.cpp:932](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/object/schema_system_catalog_install.cpp#L932)) | 가능. 4K page DB에서 압축되지 않는 1000바이트 comment로 실행 확인 |
| `_db_ha_apply_info` | `copied_log_path varchar(4096)`([schema_system_catalog_install.cpp:962](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/object/schema_system_catalog_install.cpp#L962)) | 가능. 4K page DB에서 압축되지 않는 1000바이트 경로로 실행 확인 |
| `_db_collation` | 32자 열뿐이다 | 불가 |

OOS 기준은 레코드 길이가 `DB_PAGESIZE/4`를 넘는지다([heap_file.c:13783](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/storage/heap_file.c#L13783)). 4K page에서는 1KB, 16K page에서는 4KB다. 이 길이는 압축 뒤 크기다. 같은 문자를 반복한 값은 압축되어 기준을 넘지 못하므로, 실험에는 무작위 문자열을 썼다.

### cached scan과 lock

- `_db_serial`이나 `_db_ha_apply_info`를 읽는 일반 SELECT도 cached scan 대상이다. 조건은 순차 scan, SELECT, select lock 불필요뿐이고, MVCC가 꺼진 클래스를 빼는 조건은 없다([query_executor.c:10789](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/query/query_executor.c#L10789)).
- heap scan은 MVCC가 꺼진 클래스 가운데 serial에만 SELECT 때 instance S lock을 건다. 코드 주석도 "S_SELECT is currently handled only for serial"이라고 적는다([scan_manager.c:5607-5680](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/query/scan_manager.c#L5607-L5680)).
  - cached scan이면 page를 쥐지 않은 상태라 lock을 무조건 잡고 레코드를 다시 읽는다.
  - serial을 바꾸는 트랜잭션은 instance X lock을 commit까지 쥐고, 회수 postpone은 lock을 풀기 전에 끝난다.
  - 따라서 serial reader는 회수가 끝난 뒤의 새 레코드를 읽는다고 추론한다(INFERRED). OOS 값을 이 재읽기 뒤에 읽는지는 따라가지 않았다.
- `_db_ha_apply_info`에 대한 SELECT는 lock을 걸지 않는다.

### ha_apply_info UPDATE는 매번 chain을 회수한다 (실행 확인)

applylogdb는 `copied_log_path`를 그대로 두고 counter와 시각만 바꾸는 UPDATE를 반복한다([log_applier.c:1923](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/transaction/log_applier.c#L1923), [2135](https://github.com/CUBRID/cubrid/blob/443073283d89e4511b2fa9a5b6a16898770f7e65/src/transaction/log_applier.c#L2135)). 같은 형태의 UPDATE를 debug 빌드(4K page)에서 한 트랜잭션으로 실행하고, `SHOW HEAP OOS OF _db_ha_apply_info`로 OOS 레코드 수를 셌다. `_db_ha_apply_info`에 쓰려면 `csql --sysadm`이 필요하다.

| 시점 | `Oos_num_recs` |
|---|---|
| 1000바이트 경로로 INSERT 뒤 | 1 |
| counter UPDATE 뒤, commit 전 | 2 |
| commit 뒤 | 1 |

UPDATE는 바뀌지 않은 OOS 열도 새 chain으로 쓰고, 이전 chain은 commit postpone에서 회수된다. commit 뒤에도 경로 값은 처음 넣은 값과 같았다.

### (c)의 겹침 조합

다음 순서를 막는 장치를 찾지 못했다. 경합 자체는 재현하지 않았다.

1. SELECT가 `_db_ha_apply_info`의 page를 복사하고 latch를 놓는다. 복사본의 레코드는 이전 chain을 가리킨다.
2. applylogdb의 UPDATE가 commit하면서 이전 chain을 tail부터 회수한다.
3. SELECT가 복사본의 이전 참조로 OOS를 읽는다. head stamp 검사는 회수 도중이면 통과하고, 연속 chunk에서는 지워졌거나 재사용된 slot을 읽을 수 있다.

실제 위험은 낮다. 경로가 page의 1/4을 넘어야 한다. 16K page에서는 약 4KB로 Linux 경로 최대 길이(4096)에 가깝고, 4K나 8K page DB에서도 1-2KB 경로가 필요하다.

### 함께 찾은 별도 결함

serial 행 갱신 경로(`serial_update_serial_object`)는 `heap_update`를 거치지 않고 레코드를 직접 덮어쓴다. comment가 OOS로 나간 serial은 갱신마다 새 chain이 생기고 이전 chain은 회수되지 않는다. 이 경로는 회수를 하지 않으므로 (c)와 겹치지 않는다. 누수는 [CBRD-28035](https://jira.cubrid.org/browse/CBRD-28035)로 따로 등록했다.

## 남은 질문

1. ~~MVCC가 꺼진 클래스의 행이 OOS를 가질 수 있는가?~~ 위 "추가 조사"에서 답했다. serial과 ha_apply_info는 가질 수 있고, ha_apply_info에서는 (c)와 cached scan이 겹칠 수 있다. 경합 재현은 ANALYSIS로 넘긴다.
2. `UPDATE_INPLACE_*` 호출자(`redistribute_partition_data`, catalog, TDE, boot)가 쥐는 class lock이 같은 클래스의 query scan을 막는가? 이 보고서는 막는다고 추론했다.
3. reader가 home page latch를 쥔 채 OOS를 읽는다는 판정 가운데 일부는 PEEK 의미에서 추론했다. 확인하려면 debug 빌드에서 `oos_read` 진입 시 home page fix 여부를 assert로 확인하는 실험이 필요하다.

## 이슈 처리 방향

- CBRD-27981은 "겹치는 호출자 없음"으로 닫을 수 없다. `db_ha_apply_info`의 cached scan과 applylogdb UPDATE의 commit 회수가 원리상 겹친다. 실제 위험은 낮다.
- R7의 보강(연속 chunk에서 `next_chunk_stamp` 비교, 해제 허용 fix)은 이 조합을 reader 쪽에서 막는다. 호출자 쪽 보호를 넓히는 방법도 있다. 예를 들어 MVCC가 꺼진 클래스를 cached scan에서 빼거나, ha_apply_info SELECT에도 instance lock을 거는 것이다. 어느 쪽으로 할지, 경합을 debug 빌드에서 재현할지는 ANALYSIS에서 정한다.
- 결론과 상관없이 `oos_read_within_page`의 주석([oos_file.cpp:2777-2779](https://github.com/CUBRID/cubrid/blob/94ed2ea463f17694db33a283b56fdeb42856e835/src/storage/oos_file.cpp#L2777-L2779))은 실제 근거인 호출자 쪽 보호를 적도록 고칠 대상이다.
