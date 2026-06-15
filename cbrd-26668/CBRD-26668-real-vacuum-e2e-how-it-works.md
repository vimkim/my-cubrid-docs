# CBRD-26668 — Real Vacuum E2E 테스트가 *어떻게* 동작하나 (`test_oos_real_vacuum_server.cpp`)

> 대상 파일: `unit_tests/oos/test_oos_real_vacuum_server.cpp`
> 브랜치: `oos-vacuum` (base: `origin/feat/oos`)
> 이 문서의 목적: OOS 회수(reclamation)의 **진짜 vacuum 경로**를 끝에서 끝까지(E2E) 검증하는 테스트가 *어떻게* 굴러가는지 — 진짜 서버를 단위 테스트 안에서 부팅하고, vacuum 데몬을 깨우고, 카탈로그 없이 진짜 MVCC 로그를 만드는 **메커니즘** — 을 정리한다.
> 짝 문서: **무엇을** 검증하는지(테스트 케이스·커버리지)는 [`CBRD-26668-real-vacuum-e2e-what-it-tests.md`](./CBRD-26668-real-vacuum-e2e-what-it-tests.md) 를 보라. 엔진 코드 자체는 [`CBRD-26668-code-review-explanation.md`](./CBRD-26668-code-review-explanation.md).

---

## 1. 진짜 vacuum이 거치는 파이프라인 (the chain under test)

leaf 테스트와 mock 테스트가 건너뛰는 부분이 바로 이 사슬이다. real 테스트는 맨 위(`heap_*_logical`)만 직접 부르고, 나머지는 엔진이 알아서 흘러가게 둔다.

```
  MVCC heap DML
  (heap_insert_logical / heap_delete_logical / heap_update_logical)
        │   ← 테스트가 직접 호출하는 유일한 지점
        ▼
  MVCC op 로그 레코드 생성 (vacuum 정보를 담음)
        │
        ▼
  로그 블록 완성 (block 경계를 넘겨야 vacuum이 볼 수 있음)
        │   ← unittestdb는 vacuum_log_block_pages=4 로 만들어 블록을 작게,
        │     테스트는 블록이 실제로 "닫힐" 때까지 filler를 채움
        ▼
  vacuum_wakeup_master_daemon()
        │   ← csql ';vacuum' 과 SQL VACUUM 문이 SERVER_MODE에서 쓰는 바로 그 진입점
        ▼
  vacuum master → worker → vacuum_heap
        │
        ▼
  vacuum_heap_oos_delete_within_sysop() → oos_delete()   ← 여기서 OOS 청크가 실제로 사라진다
```

- **왜 "블록이 닫혀야" 하나?** vacuum data 엔트리는 로그가 **블록 경계를 넘을 때만** 만들어진다. 관심 있는 MVCC op이 들어 있는 블록이 닫히기 전에는 master 데몬이 그 op을 영영 볼 수 없다.
- 게다가 master는 append head(로그 끝)에서 **한 페이지 이내**인 엔트리는 거부한다("too close to end of log", `vacuum_master_task::is_cursor_entry_ready_to_vacuum`). 그래서 테스트는 append head를 관심 블록보다 **두 블록 뒤로** 밀어버린다(`close_log_block_containing` 참고).

---

## 2. 테스트 인프라 (어떻게 "진짜 서버"를 단위 테스트 안에서 돌리나)

### 2.1 `ServerModeEnv` — in-process SERVER_MODE 부팅

`test_oos_server_common.hpp` 의 `ServerModeEnv`(GoogleTest global environment)가 **`cub_server`와 동일한 init 시퀀스**(`net_server_start` 미러)를 네트워크 계층만 빼고 그대로 수행한다.

```
er_init → cubthread::initialize(thread_p) → msgcat_init → tz_load
   → sysprm_load_and_init("unittestdb") → sync/critical-section init
   → boot_restart_server(... "unittestdb" ...) → logtb_assign_tran_index
```

중요한 점 두 가지:
- **SERVER_MODE에서는 `vacuum_boot()`가 무조건 실행**된다. 즉 vacuum master 데몬과 워커 풀이 테스트 내내 **실제로 살아 있다**(`vacuum_disable=yes`가 아닌 한). 이게 E2E 테스트가 성립하는 전제다.
- 부팅 직후 `thread_p`는 system tran(0)이라 sysop이 금지된다. 그래서 `logtb_assign_tran_index`로 **워커 트랜잭션을 하나 배정**해야 `oos_create_file` 등이 허용된다.

### 2.2 `unittestdb` 와 작은 로그 블록 (CTest fixture)

`unit_tests/oos/CMakeLists.txt` 의 `oos_setup_db` 테스트가 fixture(`OOS_DB`)로 동작한다.

- createdb **이전에** `cubrid.conf` 에 `[@unittestdb]` 섹션을 추가하고 `vacuum_log_block_pages=4`(최소값; 기본 31)를 박아 넣는다. 이 값은 **createdb 시점에 DB에 고정(frozen)** 되므로 순서가 중요하다. unittestdb에만 한정되어 다른 DB엔 영향 없다.
- 작은 블록 = filler를 적게 넣어도 블록이 빨리 닫힘 → real-vacuum 테스트가 빠르게 진행. (단, 테스트 코드 자체는 블록 크기에 무관하게 *블록이 실제로 닫힐 때까지* 루프를 돌므로 어떤 블록 크기에서도 정확하다.)
- 정리는 `oos_cleanup_db`(FIXTURES_CLEANUP)가 `cubrid deletedb`로 수행.
- real-vacuum 테스트는 데몬을 폴링하므로 `RUN_SERIAL TRUE`, **`TIMEOUT 120`**(다른 server-mode 테스트는 60)으로 여유를 더 줬다.

### 2.3 폴링 헬퍼

vacuum은 비동기다. 테스트는 조건이 만족될 때까지 데몬을 *깨우며* 폴링한다.

| 헬퍼 | 역할 |
|---|---|
| `current_log_blockid()` | 현재 append head가 속한 로그 블록 ID |
| `close_log_block_containing(blockid)` | 4KB filler row를 계속 insert/commit 하며 append head를 `blockid + 2`까지 밀어 관심 블록을 확실히 닫음 (guard 20000회) |
| `wait_for_vacuum(pred, timeout_sec)` | `pred()`가 참이 될 때까지 100ms마다 `vacuum_wakeup_master_daemon()`을 호출하며 대기 |
| `oos_live_recs()` | `oos_get_stats_by_vfid().num_recs` — **체인의 각 청크가 1 레코드**로 카운트됨. 그래서 `== 0`이면 "체인 전체가 회수됨"을 의미(머리만 지워진 게 아님) |

---

## 3. 카탈로그 없이 진짜 MVCC 로그를 만드는 트릭 (the clever part)

real 테스트의 가장 까다로운 부분은 **"사용자 클래스(스키마) 없이 진짜 vacuum 가능한 MVCC 로그 레코드를 만드는 법"** 이다. `OosRealVacuum::SetUp()`이 쓰는 기법:

1. **`db_user`의 클래스 OID를 빌린다.** `xheap_create`는 TDE 알고리즘을 읽으려고 클래스 레코드를 실제로 읽는다. 따라서 OID가 진짜 레코드로 resolve 되어야 한다. `db_user`는 MVCC-enabled 시스템 클래스(단지 `root`/`_db_serial`/`_db_collation`/`db_ha_apply_info`만 MVCC-disabled)라 **진짜 vacuum-처리 가능한 MVCC 로그**가 나온다.
2. **하지만 생성 이후엔 catalog-free.** vacuum은 클래스 OID를 heap 페이지 체인에서, HFID를 파일 디스크립터(`vacuum_heap_get_hfid_and_file_type`)에서, OOS VFID를 heap 헤더 페이지(`heap_oos_find_vfid`)에서 읽는다. 스키마가 필요 없다.
3. **scancache 사전 성형(pre-shaping).** 빌린 클래스 OID는 hfid 캐시에서 `db_user`의 *진짜* heap을 가리키므로, DML이 `heap_get_class_info`를 타면 엉뚱한 heap으로 간다. 그래서 `node.class_oid`, `file_type`, `mvcc_disabled_class=false`, `page_latch=X_LOCK`를 직접 세팅해 그 경로를 우회한다.
4. **`cache_last_fix_page = false`.** 연산 사이에 페이지를 고정(fix)한 채로 두면 vacuum 워커가 같은 페이지에 write latch를 못 잡는다. 테스트가 폴링하는 동안 워커가 일할 수 있도록 페이지를 절대 붙잡지 않는다.

> **RECDES 레이아웃 한 가지 차이**: leaf 테스트와 바이너리 layout은 같지만, real 테스트의 heap recdes는 데이터 영역을 `2 * OR_MVCCID_SIZE`만큼 더 잡는다(`MVCC_HEADER_SPARE`). 진짜 heap DML을 타기 때문이다 — `heap_insert_adjust_recdes_header`가 insert MVCCID를 위해 헤더를 in-place로 키우고(여분 영역이 있다고 assert), MVCC update 경로는 prev-version LSA를 위해 한 번 더 키울 수 있다. VOT 오프셋은 VOT 시작점 기준 상대값이라 헤더가 커져도 유효하다.

---

## 4. 빌드 & 실행

```bash
# 유닛 테스트 포함 빌드 + 전체 ctest 실행 (가장 흔한 방법)
just build-test

# real-vacuum E2E 테스트만 실행 (OOS_DB fixture가 자동으로 unittestdb 생성/정리)
ctest --test-dir "$CUBRID_BUILD_DIR" -R test_oos_real_vacuum_server --output-on-failure --verbose
```

- 유닛 테스트를 켜려면 `-DUNIT_TESTS=ON`로 구성돼야 한다(`./build.sh -m debug -c "-DUNIT_TESTS=ON"` 또는 프로젝트의 preset/justfile).
- `OOS_DB` fixture가 `unittestdb`를 만들고(이때 `vacuum_log_block_pages=4`가 박힘) 끝나면 지운다. 단독 실행해도 fixture가 함께 끌려온다.
- real 테스트는 `RUN_SERIAL`, `TIMEOUT 120`. 데몬 폴링이라 머신이 느리면 시간이 걸릴 수 있다.

---

## 5. 핵심 요약 (TL;DR — 메커니즘)

- 이 테스트는 **단위 테스트 프로세스 안에서 진짜 SERVER_MODE 서버를 부팅**한다(`ServerModeEnv`). SERVER_MODE라서 `vacuum_boot()`가 돌고 master 데몬·워커 풀이 테스트 내내 살아 있다 — 이게 E2E가 성립하는 전제다.
- 테스트가 직접 부르는 건 **MVCC DML(`heap_*_logical`) 하나뿐**. 그 뒤의 **로그 블록 완성 → master 데몬 wake → worker → `vacuum_heap_oos_delete_within_sysop` → `oos_delete`** 는 전부 진짜 엔진이 한다.
- vacuum이 op을 "보게" 만들려면 **로그 블록이 닫혀야** 하므로, `vacuum_log_block_pages=4`(unittestdb 한정) + filler insert로 append head를 관심 블록 **+2**까지 밀어 강제로 닫는다. 그다음 `wait_for_vacuum`이 데몬을 깨우며 폴링한다.
- 스키마 없이 진짜 MVCC 로그를 만들려고 **`db_user` 클래스 OID를 빌리고**(MVCC-enabled라 vacuum 가능), scancache를 사전 성형해 잘못된 heap 참조를 피하고, `cache_last_fix_page=false`로 페이지를 절대 붙잡지 않아 워커가 latch를 잡게 한다.
- **무엇을** 검증하는지(TC-R1~R4·커버리지 매트릭스)는 [`CBRD-26668-real-vacuum-e2e-what-it-tests.md`](./CBRD-26668-real-vacuum-e2e-what-it-tests.md).
