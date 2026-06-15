# CBRD-26668 — Real Vacuum E2E 테스트 분석 (`test_oos_real_vacuum_server.cpp`)

> 대상 파일: `unit_tests/oos/test_oos_real_vacuum_server.cpp`
> 브랜치: `oos-vacuum` (base: `origin/feat/oos`)
> 이 문서의 목적: OOS 회수(reclamation)의 **진짜 vacuum 경로**를 끝에서 끝까지(E2E) 검증하는 테스트가 *무엇을, 어떻게, 왜* 검증하는지 정리한다. 같은 폴더의 `CBRD-26668-code-review-explanation.md`(엔진 코드 리뷰 가이드)와 짝을 이루는, **테스트 쪽** 가이드다.

---

## 0. 한눈에 보기 (Executive Summary)

OOS 회수가 제대로 동작한다는 걸 증명하려면 결국 **"진짜 vacuum이 돌았을 때 죽은 OOS 청크가 사라지는가"** 를 봐야 한다. 그런데 vacuum은 혼자 도는 게 아니라 **여러 층(layer)을 거치는 파이프라인**이다. 그래서 이 디렉터리는 같은 동작("죽은 OOS 청크를 회수한다")을 **3단 피라미드**로 나눠 검증한다. 각 단계는 바로 아랫단보다 "진짜 코드"를 한 겹씩 더 사용한다.

| 테스트 파일 | 무엇을 직접 호출? | 무엇을 가짜로 두나? | 증명하는 것 |
|---|---|---|---|
| `test_oos_mock_vacuum_server.cpp` | `oos_delete()` 를 직접 호출 | vacuum 로직 **전부** (사람이 손으로 delete) | OOS 파일의 삭제·공간 회수 *말단* 동작 |
| `test_oos_vacuum_server.cpp` | `vacuum_heap_oos_delete()` (leaf 함수) | 로그·데몬·워커 (직접 RECDES를 만들어 leaf에 투입) | "heap recdes → OOS OID 추출 → 삭제" *leaf 로직* |
| **`test_oos_real_vacuum_server.cpp`** | **MVCC DML만 호출하고 나머진 진짜 vacuum이 처리** | **아무것도 가짜로 두지 않음 (E2E)** | **MVCC→로그→데몬→워커→회수** 전체 사슬 |

> **비유**: 같은 "쓰레기 수거"를 세 단계로 검증한다. ① 쓰레기를 손으로 직접 소각장에 던져 소각로가 태우는지 본다(mock). ② 수거차의 *압축기* 부품만 떼어내 쓰레기를 직접 넣어보고 압축되는지 본다(leaf). ③ **봉투를 길가에 내놓고, 진짜 수거차가 와서 가져가는지** 본다(real E2E). 이 문서는 ③번에 대한 것이다.

핵심 한 줄: **이 테스트는 vacuum master 데몬이 실제로 깨어나, 닫힌 로그 블록을 찾아내고, 워커를 통해 죽은 heap 슬롯의 OOS를 끝까지(모든 청크·모든 체인) 회수하는지를, 그리고 "아직 보고 있는 트랜잭션이 있으면 회수하지 않는지"를 검증한다.**

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
  vacuum_heap_oos_delete() → oos_delete()   ← 여기서 OOS 청크가 실제로 사라진다
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

## 4. 테스트 케이스별 커버리지 (TC-R1 ~ TC-R4)

fixture `OosRealVacuum`는 테스트마다 진짜 heap + 거기 붙은 OOS 파일을 만들고(`xheap_create` → `heap_oos_find_vfid`), 끝나면 `xheap_destroy`한다. 공통 헬퍼: `insert_row_with_oos()`(OOS payload + 그걸 가리키는 heap row를 넣고 commit), `delete_row_and_close_block()`(heap row를 MVCC-delete, commit, 블록을 닫음), `expect_oos_gone()`(OOS OID가 읽기 불가임을 확인).

### TC-R1 — `SingleRowDeleteDrainsCompletely`
- **시나리오**: 4096B OOS 1개를 가진 row 1개 INSERT → DELETE → 블록 닫고 vacuum 대기.
- **검증**: `oos_live_recs() == 0` 이 되고, 해당 OID가 읽기 불가.
- **커버하는 코드 경로**: 가장 기본적인 **REMOVE 경로** — 죽은 REC_HOME 슬롯을 vacuum이 물리적으로 지우면서 그 슬롯이 가리키던 OOS도 함께 회수(`vacuum_heap_oos_delete`).

### TC-R2 — `MultiChunkChainsDrainCompletely`
- **시나리오**: 멀티-청크 2개를 만든다 — (a) `max_chunk + 100`B(2청크 보장), (b) 160KB(16KB 페이지에서 ~10페이지). 둘 다 DELETE.
- **검증**: 삭제 전 `oos_live_recs() >= 3`(2+2 청크 이상), 삭제 후 `== 0`. `oos_live_recs()`가 청크 단위라서 **체인 전체**가 회수됐음을 증명(머리 청크만 지우는 버그를 잡음).
- **커버하는 코드 경로**: REMOVE 경로의 **체인 walk 삭제**(`oos_delete`가 체인을 내부적으로 따라가며 모든 청크 free).

### TC-R3 — `UpdateStaleVersionDrainsNewSurvives`
- **시나리오**: row INSERT(old OOS) → 새 OOS를 만들고 heap row를 그쪽으로 MVCC UPDATE → 블록 닫고 대기.
- **검증**: `oos_live_recs()`가 **정확히 1 row 분량으로 복귀**(old만 회수, new는 생존). old OID는 읽기 불가, new OID는 여전히 읽기 가능하며 길이도 일치.
- **커버하는 코드 경로**: **Forward-walk 경로**(`RVHF_UPDATE_NOTIFY_VACUUM`). UPDATE된 살아있는 슬롯은 더 이상 old OID를 가리키지 않고, old OID는 undo 로그 이미지에만 남아 있다. vacuum이 그 이미지를 읽어 회수하는지를 검증한다 — REMOVE 경로와 구분되는 **별개의 회수 경로**.

### TC-R4 — `SnapshotBlocksReclaimThenDrains`  ← "stale"의 정의를 검증
- **시나리오**: row INSERT → **delete 이전 시점의 스냅샷을 가진 reader 트랜잭션**을 연다(`logtb_assign_tran_index` + `TRAN_REPEATABLE_READ`, tran index를 worker↔reader로 스위칭) → row DELETE → 블록 닫음.
- **검증 (2단계)**:
  1. **grace window(3초)** 동안 vacuum이 회수하면 **안 됨**(`EXPECT_FALSE(drained_early)`). 살아있는 스냅샷에 보이는 OOS는 여전히 읽기 가능해야 함.
  2. reader를 abort/release한 뒤(`log_abort` + `logtb_release_tran_index`) 다시 폴링하면 **그제야 회수**되어야 함.
- **커버하는 것**: vacuum의 **MVCC 정확성** — "stale(회수 가능)"은 *시간*이 아니라 *가시성*의 문제다. **살아있는 어떤 트랜잭션도 더는 볼 수 없을 때만** 회수해야 한다. 이게 OOS 회수가 데이터 유실을 일으키지 않음을 보장하는 핵심 안전 속성이다.

---

## 5. 커버리지 매트릭스 (무엇을 보장하고, 무엇은 아닌가)

| 검증 축 | TC-R1 | TC-R2 | TC-R3 | TC-R4 |
|---|:--:|:--:|:--:|:--:|
| DELETE 후 REMOVE 경로 회수 | ✅ | ✅ | — | ✅ |
| 멀티-청크 체인 **완전** 회수 | — | ✅ | — | — |
| UPDATE old-version forward-walk 회수 | — | — | ✅ | — |
| 신버전/생존 데이터 보존 | — | — | ✅ | (✅) |
| MVCC 가시성(스냅샷이 회수 차단) | — | — | — | ✅ |
| master 데몬 wake→worker 실제 구동 | ✅ | ✅ | ✅ | ✅ |

**명시적으로 다루지 않는(또는 다른 테스트가 담당하는) 부분:**
- **Eager(즉시) 청소 경로**(`heap_oos_delete_unreferenced`, SA_MODE/non-MVCC) — 이건 SA_MODE 테스트(`test_oos_delete` 등) 영역. real 테스트는 MVCC 지연 경로 전용.
- **REC_RELOCATION forward 슬롯**과 함께 가는 회수의 디스크 레이아웃 세부 — leaf 테스트(`test_oos_vacuum_server`)와 코드 리뷰 가이드 §6/§7이 담당.
- **공간 재사용/페이지 바운드**(누수 없이 free space가 실제로 줄어드는지) — mock/leaf 테스트의 `*ReclaimAndReuse`, `MultiUpdate*` 케이스가 `file_get_num_user_pages`/`spage_get_free_space`로 검증. real 테스트는 "사라졌는가"(`oos_live_recs`/읽기 실패)에 집중.
- **크래시/복구(recovery) 시 회수의 멱등성** — 이 파일 범위 밖(멀티페이지 로깅 설계는 별도).
- **동시 다중 reader/writer 경합** — TC-R4는 단일 reader 1개만 사용.

> 요약: real 테스트는 **"진짜 vacuum이 정말 돈다 + MVCC 의미상 옳게 회수한다"** 를 증명하고, **"회수의 디스크 레벨 정확성/공간 회수"** 는 leaf·mock 테스트가 받친다. 셋이 합쳐져야 회수 동작 전체가 커버된다.

---

## 6. 빌드 & 실행

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

## 7. 핵심 요약 (TL;DR)

- `test_oos_real_vacuum_server.cpp`는 OOS 회수의 **유일한 진짜 E2E 테스트**다: MVCC DML만 호출하고, **로그 블록 완성 → master 데몬 wake → worker → `vacuum_heap_oos_delete` → `oos_delete`** 전체를 진짜 엔진이 수행하게 둔다.
- 4개 케이스가 (R1) 단일 삭제 완전 회수, (R2) 멀티-청크 체인 완전 회수, (R3) UPDATE old-version forward-walk 회수+신버전 보존, (R4) **스냅샷이 회수를 차단했다가 해제 시 회수**(=MVCC "stale" 정의)를 커버한다.
- 영리한 부분: **db_user OID를 빌려 catalog-free로 진짜 MVCC 로그를 생성**, scancache 사전 성형으로 잘못된 heap 참조 회피, 작은 로그 블록(`vacuum_log_block_pages=4`) + filler로 블록을 강제로 닫아 데몬이 보게 만듦.
- 디스크 레벨 공간 회수/leaf 로직은 형제 테스트(`test_oos_vacuum_server`, `test_oos_mock_vacuum_server`)가 담당 — 3단 피라미드로 함께 읽어야 전체 그림이 보인다.
