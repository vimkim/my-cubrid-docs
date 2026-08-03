# CUBRID 로그 매니저 동적 분석: append → flush 실측 (printf 트레이스)

> 기준 소스: `~/gh/cb/log-manager-analysis` 워크트리 (master 4cfc8370e, 11.5.x)
> 빌드: `debug_gcc` 프리셋, CS 모드 (`cub_server logtestdb` + `csql -C`)
> 선행 문서: [cubrid-log-manager-overview_4cfc837_claude.md](./cubrid-log-manager-overview_4cfc837_claude.md) (정적 분석)
> 계획 문서: [log-manager-dynamic-analysis-plan_4cfc837_claude.md](./log-manager-dynamic-analysis-plan_4cfc837_claude.md)
> 작성: Claude (2026-07-28, 실측 트레이스 기반)

---

## 1. 요약 (TL;DR)

`src/transaction/`의 append→flush 경로 8곳에 트레이스를 심고 CS 모드 워크로드를 실행해, 정적 분석 문서의 핵심 주장을 전부 실측으로 확인했다.

| 질문 | 판정 | 한 줄 근거 |
|------|------|-----------|
| Q1. 커밋 스레드가 직접 flush하나? | **아니오 — 데몬 위임+대기** | 워커는 `DAEMON_WAKEUP_CALL` 후 `FLUSH_WAIT`, flush/fsync는 전부 데몬 tid가 수행 |
| Q2. prior list는 언제 드레인되나? | **flush 직전, 소비자가 일괄 드레인** | 명시적 tx의 INSERT 3건 동안 drain 없음(list_size만 증가), 커밋 flush에서 한 번에 drain |
| Q3. autocommit INSERT 1건의 레코드 시퀀스? | **UNDOREDO 계열 5건 + LOG_COMMIT** | S1 트레이스 전문 (§4.1) |
| Q4. 그룹 커밋이 fsync를 병합하나? | **예 — 8커밋 → 1 fsync** | 단, 커밋 지연이 ~1000ms로 급증 (§4.5, §5.1) |
| Q5. LSA 3좌표(prior→append→nxio)가 순서대로 전진하나? | **예** | S1에서 세 좌표의 전진을 같은 타임라인에서 관찰 (§4.1) |

예상 밖의 발견 2가지:

1. **그룹 커밋 모드의 실측 커밋 지연이 interval(10ms)이 아니라 ~1000ms였다.** 원인은 코드로 추적됨 (§5.1).
2. **ROLLBACK은 flush를 기다리지 않고**, 워커가 자기 로그를 되읽기 위해 prior list를 직접 드레인하는 경로가 관찰됐다 (§4.3).

## 2. 방법

### 2.1 계측 지점 (T1~T8)

`src/transaction/logmgr_trace.hpp`(임시 헤더, 부록 A)를 추가하고 아래에 한 줄씩 삽입했다. 이벤트는 µs 타임스탬프 + OS tid와 함께 `/tmp/cubrid_logmgr_trace.log`에 기록된다.

| 이벤트 | 위치 (함수) | 의미 |
|--------|-------------|------|
| `PRIOR_APPEND` | `log_append.cpp` `prior_lsa_next_record_internal()` | 로그 레코드 1건 생성, prior LSA 할당, prior list 삽입 |
| `PRIOR_LIST_MAXED` | 〃 (list_size ≥ 로그버퍼 크기 분기) | 리스트 초과로 데몬 강제 wakeup |
| `PRIOR_DRAIN` / `PRIOR_DRAIN_DONE` | `log_page_buffer.c` `logpb_prior_lsa_append_all_list()` | prior list를 통째로 떼어 로그 페이지 버퍼에 복사 |
| `FLUSH_START` / `FLUSH_END` | `log_page_buffer.c` `logpb_flush_all_append_pages()` | 더티 로그 페이지 디스크 기록 구간 |
| `FSYNC` | 〃 (fileio_synchronize 직전) | 활성 로그 볼륨 fsync |
| `FLUSH_REQ` / `FLUSH_WAIT` / `FLUSH_WAIT_DONE` | `log_page_buffer.c` `logpb_flush_pages()` | 커밋 스레드의 flush 요청과 대기 |
| `COMMIT_FLUSH_REQ` / `COMMIT_DURABLE` | `log_manager.c` `log_change_tran_as_completed()` | 커밋 flush 요청 전/후 (durable 확정 지점) |
| `DAEMON_WAKEUP_CALL` | `log_manager.c` `log_wakeup_log_flush_daemon()` | 데몬 깨우기 요청 (`log_Flush_has_been_requested = true`) |
| `DAEMON_FLUSH_EXEC` / `DAEMON_BROADCAST` | `log_manager.c` `log_flush_execute()` | 데몬의 실제 flush 수행과 그룹 커밋 waiter broadcast |

### 2.2 시나리오

| # | 워크로드 | 트레이스 라인 수 |
|---|----------|------------------|
| S0 | `CREATE TABLE t1(i INT PRIMARY KEY, s VARCHAR(64))` | 109 (레코드 91건 — DDL은 sysop 덩어리) |
| S1 | autocommit `INSERT` 1건 | 19 |
| S2 | autocommit off, `INSERT` 3건 + `COMMIT` | 24 |
| S3 | `UPDATE` 1건 + `ROLLBACK` | 5 |
| S4 | 동시 커밋 2세션 | 38 |
| S5a | 동시 커밋 8세션 (기본 설정) | 222 |
| S5b | 동시 커밋 8세션 + `group_commit_interval_in_msecs=10` | 93 |
| S6 | `log_buffer_size=4M`으로 축소 후 단일 tx 대량 INSERT(더블링 14회, ~65k행) | 74,434 |

## 3. 등장 스레드

트레이스의 tid는 두 부류로 명확히 갈린다. 예: S1에서

- **워커 스레드** (`tid=1514003`): SQL을 실행하는 스레드. 레코드 생성(`PRIOR_APPEND`)과 flush **요청/대기**만 한다.
- **log-flush 데몬** (`tid=1513636`): drain→write→fsync→broadcast를 **전담**한다. `log_flush_daemon_init()`이 만드는 `"log-flush"` 데몬이다.

## 4. 시나리오별 실측

### 4.1 S1 — autocommit INSERT 1건: 커밋의 전체 수명 0.84ms

트레이스 전문 (타임스탬프는 초.µs):

```
.130220 tid=워커  PRIOR_APPEND  trid=21 rectype=LOG_MVCC_UNDOREDO_DATA lsa=176|5352 list_size=0
.130344 tid=워커  PRIOR_APPEND  trid=21 rectype=LOG_UNDO_DATA          lsa=176|5472 list_size=178
.130364 tid=워커  PRIOR_APPEND  trid=21 rectype=LOG_UNDOREDO_DATA      lsa=176|5560 list_size=326
.130396 tid=워커  PRIOR_APPEND  trid=21 rectype=LOG_MVCC_UNDOREDO_DATA lsa=176|5736 list_size=558
.130499 tid=워커  PRIOR_APPEND  trid=21 rectype=LOG_UNDOREDO_DATA      lsa=176|5880 list_size=766
.130534 tid=워커  PRIOR_APPEND  trid=21 rectype=LOG_COMMIT             lsa=176|6016 list_size=954
.130548 tid=워커  COMMIT_FLUSH_REQ   trid=21 commit_lsa=176|6016
.130556 tid=워커  FLUSH_REQ  flush_lsa=176|6016 async=0 group=0 need_wait=1 need_wakeup_LFT=1
.130563 tid=워커  DAEMON_WAKEUP_CALL
.130579 tid=워커  FLUSH_WAIT  nxio_lsa=176|5352 < flush_lsa=176|6016
.130604 tid=데몬  DAEMON_FLUSH_EXEC
.130616 tid=데몬  PRIOR_DRAIN       drained_bytes=1058 append_lsa_before=176|5352
.130630 tid=데몬  PRIOR_DRAIN_DONE  append_lsa_after=176|6056
.130634 tid=데몬  FLUSH_START  nxio_lsa=176|5352 append_lsa=176|6056 num_toflush=1
.130703 tid=데몬  FSYNC
.131026 tid=데몬  FLUSH_END    flushed_pages=1 nxio_lsa=176|6056
.131049 tid=데몬  DAEMON_BROADCAST
.131056 tid=워커  FLUSH_WAIT_DONE  nxio_lsa=176|6056 >= flush_lsa=176|6016
.131063 tid=워커  COMMIT_DURABLE   trid=21 commit_lsa=176|6016
```

읽어낼 수 있는 것:

- **레코드 시퀀스 (Q3)**: heap/인덱스 변경을 기술하는 UNDOREDO 계열 5건(힙 MVCC insert + PK B-tree 관련) 뒤에 `LOG_COMMIT`. INSERT 1건 = 로그 레코드 6건, 약 1KB (`drained_bytes=1058`).
- **역할 분담 (Q1)**: 워커는 데몬을 깨우고(`need_wakeup_LFT=1`) `gc_cond`에서 잔다. drain·write·fsync는 전부 데몬. 워커는 `nxio_lsa >= commit_lsa`가 되어야 깨어나 커밋을 확정한다.
- **LSA 3좌표 (Q5)**: 레코드 생성 시점의 prior LSA(176|5352~6016) → drain 후 `append_lsa`(176|6056) → flush 후 `nxio_lsa`(176|6056). "메모리 목록 → 페이지 버퍼 → 디스크"의 3단 좌표가 순서대로 따라온다.
- **소요 시간**: 커밋 요청→durable 0.5ms (전체 INSERT 0.84ms), 그중 fsync 0.32ms. 즉 **동기 커밋 비용의 대부분이 fsync**다.

### 4.2 S2 — 명시적 트랜잭션: drain은 커밋까지 미뤄진다 (Q2)

INSERT 3건을 치는 동안 `PRIOR_DRAIN`이 **한 번도 발생하지 않았다**. 레코드 9건이 prior list에 쌓이며 `list_size`가 170→1766 bytes로 단조 증가하고, `COMMIT` 레코드 직후 데몬 flush에서 **일괄 drain**(1870 bytes)됐다. 워크로드가 작아 `PRIOR_LIST_MAXED`(리스트가 로그버퍼 크기를 넘으면 생산자가 데몬을 깨우고 1ms 양보하는 백프레셔)는 관찰되지 않았다 — 대량 트랜잭션에서만 발동하는 경로다.

### 4.3 S3 — ROLLBACK: flush를 기다리지 않는다

```
PRIOR_APPEND  trid=31 LOG_MVCC_UNDOREDO_DATA lsa=176|7264   ← UPDATE 본체
PRIOR_DRAIN   drained_bytes=236 (tid=워커!)                  ← 워커가 직접 드레인
PRIOR_DRAIN_DONE
PRIOR_APPEND  trid=31 LOG_COMPENSATE lsa=176|7448            ← undo 실행 기록
PRIOR_APPEND  trid=31 LOG_ABORT      lsa=176|7560
(끝 — FLUSH_REQ / FSYNC 없음)
```

- **보상 레코드**: 롤백은 UNDO 데이터를 적용하며 `LOG_COMPENSATE`를 남긴다 (redo-only; 복구 중 재롤백 방지).
- **워커가 직접 drain한 이유**: 롤백은 자기가 방금 쓴 로그를 **되읽어야** 하는데, 그 레코드가 아직 prior list에만 있으면 로그 페이지를 읽을 수 없다. 로그 페이지 fetch 경로가 LOG_CS 아래에서 `logpb_prior_lsa_append_all_list()`를 호출해 먼저 메모리 목록을 페이지 버퍼로 밀어넣는다.
- **`LOG_ABORT`는 flush를 기다리지 않았다.** `log_change_tran_as_completed()`는 abort에 대해 체크포인트 진행 중일 때만 flush한다(코드에 "aborters도 기다리게 해야 하지 않나"라는 TODO 주석 존재). 실제로 S3의 ABORT 레코드는 **다음 트랜잭션(S4)의 커밋 flush에 편승**해서야 디스크에 갔다 — S4 첫 drain의 `append_lsa_before=176|7448`(ABORT 잔류분 포함)이 그 증거. 크래시로 ABORT가 유실돼도 복구가 어차피 미완료 tx를 롤백하므로 정합성 문제가 없다.

### 4.4 S4/S5a — 동시 커밋 (기본 설정): 커밋당 fsync, 겹치면 자연 병합

기본 설정(`group_commit_interval_in_msecs=0`)에서 커밋마다 `need_wakeup_LFT=1`로 데몬을 깨워 **커밋당 fsync 1회**가 원칙. 다만 S5a(8세션 동시)에서는 **8커밋에 fsync 7회** — 마지막 fsync 직후 `COMMIT_DURABLE`이 두 건(trid=68, 69) 연달아 찍혔다. 즉 flush가 진행되는 사이에 도착한 커밋은 같은 flush로 함께 durable된다. **그룹 커밋을 꺼도 부하가 겹치면 소극적 병합이 일어난다.**

### 4.5 S5b — 그룹 커밋 ON: fsync 8→1, 그러나 지연 ~1000ms (Q4)

`group_commit_interval_in_msecs=10` 설정 후 8세션 동시 커밋:

- 모든 `FLUSH_REQ`가 `group_commit=1 need_wait=1 need_wakeup_LFT=0` — **아무도 데몬을 깨우지 않고** 전원 `gc_cond` 대기.
- 8커밋 전부 **단일 fsync**(`total_sync_count=1`) 후 20µs 안에 일제히 `COMMIT_DURABLE`.
- 그러나 첫 커밋 요청(50.5276)부터 durable(51.5283)까지 **약 1001ms**. interval 10ms가 아니다.

### 4.6 S6 — prior list 백프레셔 (`PRIOR_LIST_MAXED`) 실측

`log_buffer_size`를 4M으로 낮추고 한 트랜잭션에서 ~13MB의 로그(레코드 약 7만 건)를 생산했다.

- `PRIOR_LIST_MAXED` **6회 발동**, 발동 시 list_size는 4,194,308~4,194,662 bytes — **임계치(4MB) 초과분이 최대 ~350 bytes**에 불과.
- 워커의 데몬 wakeup 후 **~109µs 만에** 데몬이 `PRIOR_DRAIN`으로 4MB 리스트를 통째로 비움. 이후 212페이지 write+fsync(~25ms)는 워커의 생산과 **병행** 진행.
- 발동 간격은 ~0.3–0.4초(워커가 4MB를 다시 채우는 시간) — 데몬이 여유 있게 따라잡음.
- 커밋 전에 fsync 9회 발생 — **미커밋 데이터도 로그 디스크에 내려간다**(WAL의 정상 동작; 복구 시 undo).

**"1ms sleep으로 충분한가"에 대한 답**: 백프레셔가 버텨야 하는 시간은 느린 **디스크 write까지가 아니라 빠른 drain까지**다. drain은 리스트 unlink + 페이지 버퍼 복사라 µs~ms 단위이고, 디스크 I/O는 drain 이후 생산과 겹쳐 진행되므로 1ms 양보로 충분했다. 단, 이는 데몬이 스케줄링되고 페이지 버퍼에 여유가 있다는 전제이며, 데몬 기아/디스크 정체가 길어지는 병리적 상황에서는 레코드당 1ms 스로틀 외에 하드 상한이 없다(하류의 로그 페이지 버퍼 확보 경로가 2차 방벽).

## 5. 심층 분석

### 5.1 그룹 커밋 1초 지연의 코드 경로

실측 타임라인: 마지막 `FLUSH_REQ`(50.5447) 후 정확히 1초 뒤 **waiter 스레드가** `DAEMON_WAKEUP_CALL`(51.5277)을 하고 나서야 데몬이 flush했다. 코드로 재구성하면:

1. `logpb_flush_pages()`: 그룹 커밋이면 첫 iteration에서 `need_wakeup_LFT=false`로 `pthread_cond_timedwait(gc_cond, 1000ms)` 진입.
2. log-flush 데몬의 looper 주기는 `log_get_log_group_commit_interval()`이 interval(10ms)로 설정 — **데몬은 10ms마다 깨어나긴 한다.**
3. 그러나 태스크 본체 `log_flush_execute()`의 첫 줄 게이트가 `!log_Flush_has_been_requested → return`. 이 플래그는 `log_wakeup_log_flush_daemon()`만 세우는데, 그룹 커밋 waiter는 첫 iteration에서 이를 호출하지 않는다.
4. 결국 waiter의 **1000ms timedwait 타임아웃**이 만료된 뒤 루프 2회째에 `need_wakeup_LFT=true`로 데몬을 깨워서야 flush 실행.

즉 이 빌드(11.5 develop)에서 순수 그룹 커밋 워크로드의 커밋 지연 하한은 interval이 아니라 **waiter 타임아웃(1초)** 이 지배한다. (커밋 스레드가 perm page를 fix하고 있는 경우 등 `need_wakeup_LFT`가 승격되는 예외 경로는 있음.) 스루풋 관점(fsync 병합)은 의도대로 동작하지만 지연 관점은 직관과 다르므로, 그룹 커밋 파라미터를 실서비스에 켤 때 반드시 인지해야 할 동작이다. 잠재적 개선 여지(또는 의도 확인 필요)로 기록한다.

### 5.2 prior list의 생산자/소비자 구조 (실측 종합)

```
워커들(생산자):  prior_lsa_mutex 하에 레코드 생성 + 리스트 연결      ← PRIOR_APPEND
                 (리스트가 로그버퍼 크기 초과 시에만 데몬 wakeup + 1ms 양보)
소비자(둘뿐):    ① log-flush 데몬: flush 직전 일괄 drain             ← 대부분의 PRIOR_DRAIN
                 ② 로그를 되읽어야 하는 스레드(예: 롤백): fetch 전 drain ← S3에서 관찰
```

정적 문서의 서술("드레인은 flush 경로에서")이 맞고, 여기에 ②의 읽기-유발 drain이 실측으로 추가됐다.

### 5.3 fsync 관점의 커밋 비용

S1 기준 동기 커밋 0.5ms 중 fsync가 0.32ms(64%). 동시 커밋 시 fsync 횟수가 곧 처리량 상한을 결정하며(S5a: 8커밋/7fsync, S5b: 8커밋/1fsync), CUBRID의 그룹 커밋은 이 fsync를 줄이는 대신 지연을 희생하는 구조임이 수치로 확인된다.

## 6. 정적 문서 대비 정정/보강 사항

| 항목 | 결과 |
|------|------|
| 5장 prior list 흐름 | 실측 일치. "읽기 유발 drain"(롤백 등) 보강 (§4.3, §5.2) |
| 7장 그룹 커밋 | fsync 병합은 일치. **지연 특성(≈1s) 추가 필요** (§5.1) |
| 9장 트랜잭션 수명주기 | commit은 flush 대기, abort는 비대기 — 실측 일치 + ABORT 레코드가 후속 flush에 편승함을 확인 |

## 7. 열린 질문 (grill 세션에서 제기)

### 7.1 커밋 대기 탈출 조건의 등호 케이스

`logpb_flush_pages()`의 대기 탈출 조건은 `nxio_lsa >= flush_lsa`(커밋 레코드의 **시작** LSA 기준)이다. `nxio_lsa == commit_lsa`는 정의상 "커밋 레코드 직전까지만 디스크에 있음"을 뜻하므로, 등호 탈출은 커밋 레코드가 디스크에 없는데 durable로 판정하는 것이 된다. 일반 경로에서는 flush가 커밋 레코드를 포함하므로 nxio가 레코드 끝(strict `>`)으로 점프해 문제가 없지만, 다음 인터리빙의 도달 가능성은 배제하지 못했다:

```
T1 데몬: prior list drain (리스트 끝 = Y)
T2 워커: 커밋 레코드 append (commit_lsa = Y)     ← 이번 drain에 미포함
T3 데몬: write+fsync, nxio = Y
T4 워커: nxio(Y) < flush_lsa(Y) 거짓 → 대기 없이 durable 판정 (커밋 레코드는 아직 메모리)
```

방어 장치의 존재 여부 확인 또는 재현 실험(즉시-리턴 케이스 계측)이 후속 과제. 확인되면 JIRA 질문거리.

**보강 증거 (grill Q4)**: WAL 검사 `logpb_need_wal()`(log_page_buffer.c:11281)은 `LSA_LE(nxio, page_lsa)` — 즉 **등호를 "아직 디스크에 없음"으로 보수적으로 취급**한다. 같은 좌표의 같은 경계를 커밋 대기(`>=` 탈출)와 WAL 검사(`<=` 재flush)가 반대로 다루고 있어, 커밋 대기 쪽 등호 처리의 의도성이 더 의심스럽다.

## 8. 한계

- debug 빌드(assert 활성)라 절대 시간은 release보다 느릴 수 있다. 상대적 구조(누가 무엇을 언제)는 유효.
- 단일 로그 페이지 규모의 워크로드 — `PRIOR_LIST_MAXED`, 다중 페이지 flush, 아카이빙, 체크포인트, 복구는 범위 외 (후속 실험 후보).
- 레코드의 rcvindex(RVHF_*, RVBT_*)까지는 트레이스하지 않아 §4.1의 heap/btree 귀속은 레코드 타입 기반 추정.

## 부록 A — 계측 재현 방법

워크트리에 비커밋 상태로 유지 중 (`git diff`: log_append.cpp +8, log_manager.c +10, log_page_buffer.c +25, logmgr_trace.hpp 신규).

1. `src/transaction/logmgr_trace.hpp`: `LOGMGR_TRACE(evt, fmt, ...)` 매크로 — `clock_gettime` µs 타임스탬프 + `gettid` + 한 줄 fprintf/fflush를 `/tmp/cubrid_logmgr_trace.log`에 append. 각 파일의 `memory_wrapper.hpp` **앞**에 include.
2. 삽입 지점은 §2.1 표의 함수들. 각 지점 한 줄 호출.
3. `just build` 후 `cubrid server start`, 시나리오 실행 전후로 트레이스 파일의 라인 수를 기록해 구간 분리.
4. 시나리오별 원본 트레이스: 세션 스크래치패드 `trace_S0~S5b*.log` (본문 인용으로 재현 가능).
