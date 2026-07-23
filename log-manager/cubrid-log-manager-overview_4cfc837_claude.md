# CUBRID 로그 매니저 (WAL) 동작 원리

> 기준 소스: cubrid/cubrid `master` (4cfc8370e, 2026-07 기준 11.5.x 개발 브랜치)
> 모든 파일 경로는 별도 표기가 없으면 `src/transaction/` 기준이다.
> 작성: Claude (5개 영역 병렬 소스 분석 기반 종합)

---

## 목차

1. [로그 매니저가 하는 일](#1-로그-매니저가-하는-일)
2. [핵심 좌표계: LSA](#2-핵심-좌표계-lsa)
3. [온디스크 구조: 로그 페이지, 활성 로그, 아카이브](#3-온디스크-구조-로그-페이지-활성-로그-아카이브)
4. [로그 레코드의 구조와 종류](#4-로그-레코드의-구조와-종류)
5. [로그 기록 경로 (append path): prior list](#5-로그-기록-경로-append-path-prior-list)
6. [로그 페이지 버퍼와 디스크 플러시](#6-로그-페이지-버퍼와-디스크-플러시)
7. [그룹 커밋과 로그 플러시 데몬](#7-그룹-커밋과-로그-플러시-데몬)
8. [WAL 규칙의 강제: 데이터 버퍼와의 연동](#8-wal-규칙의-강제-데이터-버퍼와의-연동)
9. [트랜잭션 수명주기와 로그](#9-트랜잭션-수명주기와-로그)
10. [시스템 오퍼레이션(sysop)과 시스템 트랜잭션](#10-시스템-오퍼레이션sysop과-시스템-트랜잭션)
11. [체크포인트](#11-체크포인트)
12. [아카이빙과 아카이브 삭제 정책](#12-아카이빙과-아카이브-삭제-정책)
13. [크래시 복구: analysis → redo → undo](#13-크래시-복구-analysis--redo--undo)
14. [로그의 다른 소비자들: Vacuum, HA, CDC](#14-로그의-다른-소비자들-vacuum-ha-cdc)
15. [관련 파라미터 요약](#15-관련-파라미터-요약)
16. [파일별 역할 지도](#16-파일별-역할-지도)

---

## 1. 로그 매니저가 하는 일

CUBRID는 **WAL(Write-Ahead Logging)** 방식의 로그 매니저를 갖는다. 원칙은 하나다:

> **데이터 페이지를 디스크에 쓰기 전에, 그 변경을 기술하는 로그 레코드가 먼저 디스크에 있어야 한다.**

이 원칙 위에서 로그 매니저는 다음을 담당한다.

- **원자성(Atomicity)**: 롤백/크래시 시 undo 정보로 변경을 되돌린다.
- **지속성(Durability)**: 커밋 시점에 로그가 디스크에 있으면, 데이터 페이지가 아직 안 써졌어도 redo로 재현할 수 있다.
- **크래시 복구**: 재시작 시 analysis → redo → undo 3단계로 일관된 상태를 복원한다.
- **부가 소비자 지원**: Vacuum(MVCC 청소), HA 복제(copylogdb/applylogdb), CDC가 모두 이 로그를 읽는다.

전체 흐름을 그림 하나로 요약하면:

```
 워커 스레드들                                        디스크
┌───────────────┐  prior_lsa_mutex   ┌─────────────┐  LOG_CS   ┌───────────┐ fileio_write ┌──────────────┐
│ log_append_*()│ ─────────────────► │ prior list  │ ────────► │ 로그 페이지 │ ───────────► │ 활성 로그     │
│ (레코드 생성)  │  LOG_PRIOR_NODE    │ (메모리 목록) │  드레인    │ 버퍼(직접매핑)│   + fsync    │ (_lgat, 링)  │
└───────────────┘                    └─────────────┘           └───────────┘              └──────┬───────┘
                                                                     ▲                          │ 링이 다 차면
                                                          로그 플러시 데몬(LFT)                    ▼
                                                          그룹 커밋 브로드캐스트              ┌──────────────┐
                                                                                           │ 아카이브       │
                                                                                           │ (_lgar000...) │
                                                                                           └──────────────┘
```

---

## 2. 핵심 좌표계: LSA

**LSA(Log Sequence Address)** 는 "무한히 이어지는 로그"에서 특정 로그 레코드의 위치를 가리키는 주소다.

```c
/* log_lsa.hpp:35-63 */
struct log_lsa
{
  std::int64_t pageid:48;   /* 로그 페이지 번호 (6바이트) */
  std::int64_t offset:16;   /* 페이지 내 오프셋 (2바이트) */
};
```

- 전체가 정확히 **8바이트**이며, 비교 연산은 `pageid` 우선, 같으면 `offset` 순 — 즉 LSA 대소 비교가 곧 로그 시간 순서다 (`log_lsa.hpp:129-133`).
- `NULL_LSA = {-1, -1}`. null 판정은 `pageid == -1`만 본다 (`log_lsa.hpp:97-101`).
- `pageid`는 **논리(logical) 페이지 번호**로 DB 생성 이후 단조 증가한다. 실제 디스크 위치(물리 페이지)로는 별도 매핑을 거친다(§3.3).

LSA는 로그 매니저 전역에서 통용되는 화폐 같은 존재다. 데이터 페이지 헤더에도 "이 페이지에 마지막으로 반영된 로그 레코드의 LSA"가 찍히고(§8), 트랜잭션 디스크립터에도 여러 LSA 커서가 있다(§9.1).

### 시스템 전체에서 중요한 LSA 3형제

| 이름 | 위치 | 의미 |
|------|------|------|
| `prior_lsa` | `log_Gl.prior_info.prior_lsa` | 다음 로그 레코드가 배정받을 **논리적** 위치. 레코드 생성 단계에서만 전진 |
| `append_lsa` | `log_Gl.hdr.append_lsa` | 로그 페이지 버퍼에 실제로 복사된 **물리적** append 위치 |
| `nxio_lsa` | `log_Gl.append.nxio_lsa` (atomic) | **아직 디스크에 안 써진 가장 낮은 LSA** = 디스크 플러시 프런티어. WAL 판정과 그룹 커밋 대기가 모두 이 값을 본다 |

`prior_lsa ≥ append_lsa ≥ nxio_lsa` 순으로 앞서 나가며, 세 값의 간극이 곧 "메모리에만 있는 로그"의 양이다.

---

## 3. 온디스크 구조: 로그 페이지, 활성 로그, 아카이브

### 3.1 로그 페이지 레이아웃

```c
/* log_storage.hpp:62-86 */
struct log_hdrpage {              /* 각 로그 페이지의 헤더 */
  LOG_PAGEID logical_pageid;      /* 논리 페이지 번호 */
  PGLENGTH   offset;              /* 이 페이지에서 시작하는 첫 레코드의 오프셋 */
  short      flags;               /* TDE 암호화 플래그 */
  int        checksum;            /* CRC32 체크섬 */
};
struct log_page {
  LOG_HDRPAGE hdr;
  char        area[1];            /* 레코드 데이터 (가변) */
};
```

- 페이지 크기는 `LOG_PAGESIZE`(런타임 전역, 최대 16K). 레코드가 실리는 영역은 `LOGAREA_SIZE = LOG_PAGESIZE - sizeof(LOG_HDRPAGE)` (`log_impl.h:121`).
- `hdr.offset`은 앞 페이지가 손상됐을 때 이 페이지에서 파싱을 재개할 수 있게 하는 복구용 힌트다 (`log_storage.hpp:66-69`).
- 레코드는 페이지 경계를 자유롭게 넘어 **여러 페이지에 걸칠 수 있다**(spanning). 순회는 레코드 헤더의 `forw_lsa`/`back_lsa` 체인으로 한다.
- `sizeof(LOG_PAGE)`를 쓰면 안 된다는 경고가 소스에 명시돼 있다 — 반드시 `LOG_PAGESIZE` 매크로를 쓴다 (`log_storage.hpp:74-78`).

### 3.2 활성 로그 볼륨(`_lgat`)과 LOG_HEADER

활성 로그는 **물리 페이지 0번을 헤더로 예약한 순환(ring) 버퍼**다. 논리 페이지는 무한히 증가하지만 물리적으로는 `npages`개 슬롯을 돌려 쓴다.

헤더(`LOG_HEADER`, `log_storage.hpp:112-226`)의 주요 필드:

| 그룹 | 필드 | 의미 |
|------|------|------|
| 식별 | `magic`, `db_creation`, `db_release`, `db_iopagesize`, `db_logpagesize` | DB 재기동 시 지오메트리/호환성 검증 |
| append | `fpageid` | **물리 슬롯 1번에 매핑되는 논리 페이지** — 링 매핑의 앵커 |
| | `append_lsa`, `eof_lsa` | 현재 append 꼬리 |
| | `npages` | 활성 로그 페이지 수(헤더 제외) |
| 복구 | `chkpt_lsa` | 크래시 복구의 analysis 시작점 |
| | `smallest_lsa_at_last_chkpt` | 마지막 체크포인트 때 가장 오래된 활성 트랜잭션의 시작 LSA |
| | `is_shutdown` | 정상 종료 여부 |
| 아카이브 | `nxarv_pageid`, `nxarv_phy_pageid`, `nxarv_num` | 다음에 아카이브할 논리/물리 페이지와 아카이브 번호 |
| | `last_arv_num_for_syscrashes`, `last_deleted_arv_num` | 시스템 크래시 복구에 필요한 최소 아카이브, 삭제된 마지막 아카이브 |
| MVCC/Vacuum | `mvcc_next_id`, `mvcc_op_log_lsa`, `oldest_visible_mvccid`, `newest_block_mvccid`, `does_block_need_vacuum`, `vacuum_last_blockid` | Vacuum 로그 블록 추적(§14.1) |
| 트랜잭션 | `next_trid` | 다음 발급할 TRID |
| HA/백업 | `ha_server_state`, `bkup_level0/1/2_lsa`, `bkinfo[]` | HA 상태, 백업 수준별 LSA |

### 3.3 논리 → 물리 페이지 매핑 (링 구조)

`logpb_to_physical_pageid()` (`log_page_buffer.c:4948-4979`):

```
논리 == LOGPB_HEADER_PAGE_ID(-9)  →  물리 0 (헤더 전용)
그 외:
  tmp = 논리 - fpageid          # 앵커 기준 상대 위치
  tmp %= npages                 # 링 래핑 (음수 보정 포함)
  tmp += 1                      # 물리 0번(헤더)을 건너뜀
  →  물리 1 .. npages
```

append가 물리 슬롯 1번에 다시 도달하면(한 바퀴), `hdr.fpageid += npages`로 앵커를 전진시키고 헤더를 플러시한다 (`log_page_buffer.c:2677-2683`). 다음 append 페이지가 아직 아카이브 안 된 페이지의 물리 슬롯을 덮으려 하면 그 전에 아카이빙이 발동한다(§12).

### 3.4 아카이브 볼륨(`_lgar###`)과 파일 이름

- 아카이브 헤더 `LOG_ARV_HEADER` (`log_storage.hpp:230-257`): `fpageid`(이 아카이브의 물리 1번에 해당하는 논리 페이지), `npages`, `arv_num`.
- 파일 이름 (`src/storage/file_io.c`):
  - 활성 로그: `<logpath>/<dbname>_lgat`
  - 로그 정보: `<dbname>_lginf`
  - 아카이브: `<dbname>_lgar%03d` (예: `_lgar000`), 백그라운드 아카이빙 임시본은 `_lgar_t`
- 로그류 볼륨은 음수 volid를 쓴다 (`log_volids.hpp`): 활성 로그 `-2`, 아카이브 `-20`, 백그라운드 아카이브 `-21`, DWB `-22` 등.

---

## 4. 로그 레코드의 구조와 종류

### 4.1 공통 레코드 헤더

```c
/* log_record.hpp:145-153 */
struct log_rec_header {
  LOG_LSA prev_tranlsa;  /* 같은 트랜잭션의 이전 레코드 (롤백/undo 순회용) */
  LOG_LSA back_lsa;      /* 로그 스트림상 바로 앞 레코드 */
  LOG_LSA forw_lsa;      /* 로그 스트림상 바로 다음 레코드 */
  TRANID  trid;
  LOG_RECTYPE type;
};
```

체인이 두 종류라는 점이 중요하다.

- `back_lsa`/`forw_lsa`: **로그 전체**의 양방향 체인 — 순차 스캔(복구 analysis/redo, CDC)이 사용.
- `prev_tranlsa`: **트랜잭션별** 역방향 체인 — 롤백과 복구 undo가 사용.

레코드 본문은 `type`에 따라 헤더 바로 뒤에 이어진다.

### 4.2 레코드 타입 그룹 (`log_record.hpp:35-142`)

| 그룹 | 타입 | 용도 |
|------|------|------|
| 데이터 변경 | `LOG_UNDOREDO_DATA`, `LOG_UNDO_DATA`, `LOG_REDO_DATA`, `LOG_DIFF_UNDOREDO_DATA` | 물리적 페이지 변경. DIFF는 undo/redo 이미지를 XOR-diff 압축한 변형 |
| MVCC 데이터 변경 | `LOG_MVCC_UNDOREDO_DATA`, `LOG_MVCC_UNDO_DATA`, `LOG_MVCC_REDO_DATA`, `LOG_MVCC_DIFF_UNDOREDO_DATA` | 위와 같되 MVCCID + vacuum 체인 정보 추가 |
| postpone | `LOG_POSTPONE`, `LOG_RUN_POSTPONE`, `LOG_COMMIT_WITH_POSTPONE` | 커밋 시점까지 미루는 redo 작업(예: 파일 삭제 확정) |
| 보상(CLR) | `LOG_COMPENSATE` | undo를 수행했음을 기록하는 redo-only 레코드 — undo 자체를 크래시-안전하게 만든다 |
| 종료 | `LOG_COMMIT`, `LOG_ABORT` | 트랜잭션 종결 + 타임스탬프(`LOG_REC_DONETIME`, PITR용) |
| sysop | `LOG_SYSOP_END`, `LOG_SYSOP_START_POSTPONE`, `LOG_SYSOP_ATOMIC_START` | 중첩 최상위 작업(§10) |
| 체크포인트/세이브포인트 | `LOG_START_CHKPT`, `LOG_END_CHKPT`, `LOG_SAVEPOINT` | §11, §9.3 |
| 더미 | `LOG_END_OF_LOG`, `LOG_DUMMY_CRASH_RECOVERY`, `LOG_DUMMY_OVF_RECORD`, `LOG_DUMMY_HEAD_POSTPONE`, `LOG_DUMMY_GENERIC` 등 | 로그 꼬리 표시, 오버플로 시작 표시, 강제 플러시 등 |
| 2PC | `LOG_2PC_PREPARE`, `LOG_2PC_START`, ... | 분산 트랜잭션 |
| 복제/CDC | `LOG_REPLICATION_DATA`, `LOG_REPLICATION_STATEMENT`, `LOG_SUPPLEMENTAL_INFO` | HA 논리 복제(DML/DDL), CDC 보조 정보 |

### 4.3 주요 본문 구조체

모든 데이터 변경 레코드는 공통 위치자 `LOG_DATA`를 갖는다 (`log_record.hpp:156-163`):

```c
struct log_data {
  LOG_RCVINDEX rcvindex;  /* 어떤 복구 함수를 쓸지 (RV_fun 인덱스) */
  PAGEID pageid;          /* 대상 페이지 */
  PGLENGTH offset;        /* 페이지 내 슬롯/오프셋 */
  VOLID volid;
};
```

- `LOG_REC_UNDOREDO`: `{LOG_DATA data; int ulength; int rlength;}` — undo/redo 이미지가 뒤따른다.
- `LOG_REC_MVCC_UNDOREDO`: 위에 `MVCCID mvccid` + `LOG_VACUUM_INFO {prev_mvcc_op_log_lsa, vfid}` 추가 — **모든 MVCC 연산 레코드를 역방향 단일 연결 리스트로 묶는 vacuum 체인**(§14.1).
- `LOG_REC_COMPENSATE`: `{LOG_DATA; LOG_LSA undo_nxlsa; int length;}` — `undo_nxlsa`는 "이 다음에 undo할 레코드"로, 롤백 재개 시 이미 보상된 구간을 건너뛰게 한다.
- `LOG_REC_SYSOP_END`: `lastparent_lsa`(sysop 시작 직전 LSA), `type`(커밋/중단/논리 undo 등 6종), 타입별 union(내장 undo 이미지, `compensate_lsa`, `run_postpone` 등).

### 4.4 rcvindex와 RV_fun 테이블

로그 레코드는 "무엇이 바뀌었나"의 바이트만 담고, "어떻게 적용/되돌리나"는 **복구 함수 테이블**이 담당한다.

- `LOG_RCVINDEX` enum이 모듈별 접두사(RVHF_ 힙, RVBT_ B-tree, RVDK_ 디스크...)로 정의됨 (`src/storage/recovery.h:36-192`). 구버전 DB 복구 호환성을 위해 **새 항목은 항상 맨 뒤에 추가**한다.
- 전역 배열 `RV_fun[]` (`src/storage/recovery.c:54`): 항목마다 `{undofun, redofun, dump 함수들}`.
- 복구/롤백은 레코드의 `rcvindex`로 이 테이블을 찾아 `LOG_RCV{pgptr, offset, length, data, mvcc_id, reference_lsa}`를 넘겨 호출한다.
- `rcvindex`의 성질에 따라 동작이 갈린다: `LOG_IS_MVCC_OPERATION()`이면 MVCC 레코드 변형 사용, `LOG_MAY_CONTAIN_USER_DATA()`이면 TDE 암호화 대상, `LOG_ISUNSAFE_TO_SKIP_RCVINDEX()`이면 임시 페이지라도 로깅 생략 불가.

---

## 5. 로그 기록 경로 (append path): prior list

CUBRID append 경로의 핵심 설계는 **레코드 생성과 페이지 버퍼 기록의 분리**다. 워커 스레드가 큰 락(LOG_CS)을 잡고 페이지 버퍼에 직접 쓰는 대신, 두 단계로 나눈다.

```
[1단계: 레코드 생성]  워커 스레드, prior_lsa_mutex (짧게)
   malloc된 LOG_PRIOR_NODE에 레코드 구성 → prior list에 연결, prior_lsa 전진

[2단계: 페이지 복사]  플러시 주체, LOG_CS (배치)
   prior list 전체를 떼어 로그 페이지 버퍼에 복사 → append_lsa 전진
```

### 5.1 자료구조

- `LOG_PRIOR_NODE` (`log_append.hpp:90-109`): 레코드 헤더 + `data_header`/`udata`(undo)/`rdata`(redo) 세 blob + `start_lsa` + TDE 플래그.
- `log_prior_lsa_info` (`log_append.hpp:111-129`, 인스턴스 `log_Gl.prior_info`): `prior_lsa`(다음 레코드가 받을 LSA), `prior_list_header/tail`, `list_size`(누적 바이트), `prior_flush_list_header`(드레인 중 목록), `prior_lsa_mutex`.

`prior_lsa`는 실제 페이지를 건드리지 않고 **오프셋 산술만으로** 전진한다 — 레코드가 페이지에 안 들어가면 다음 페이지로 넘기는 정렬 계산까지 전부 산술이다 (`log_append.cpp:1891-1923`).

### 5.2 대표 흐름: undo/redo 레코드 하나의 일생

진입점은 `log_append_undoredo_data2()` 등 (`log_manager.c:1893-2496`) → 전부 `log_append_undoredo_crumbs()`로 수렴 (`log_manager.c:2085`):

1. **레코드 타입 결정**: `LOG_IS_MVCC_OPERATION(rcvindex)`이면 `LOG_MVCC_UNDOREDO_DATA`, 아니면 `LOG_UNDOREDO_DATA` (`:2094`).
2. **로깅 생략 판정**:
   - 전역 `log_No_logging`이면 skip (`:2118`).
   - `log_can_skip_undo_logging()` (`log_manager.c:4293`): vacuum 시스템 워커이거나 **임시 페이지**면 undo 생략 → redo-only로 강등 (`:2153`).
   - `log_can_skip_redo_logging()` (`:4344`): 임시 페이지면 redo도 생략.
3. **prior node 생성**: `prior_lsa_alloc_and_copy_crumbs()` (`log_append.cpp:409`) → `prior_lsa_gen_undoredo_record_from_crumbs()` (`:650`):
   - undo/redo 길이가 임계값(`log_Zip_min_size_to_compress`, 기본 255바이트) 이상이면 **LZ4 압축** (`log_compress.c:82-84`).
   - undo/redo 둘 다 크면 redo를 undo와 **XOR-diff** 후 압축하고 타입을 `LOG_DIFF_UNDOREDO_DATA`로 승격 (`:777-813`).
   - MVCC 타입이면 `tdes->mvccinfo`에서 MVCCID를 채움 (`:938-963`).
4. **TDE**: 사용자 데이터를 담을 수 있는 rcvindex이고 대상 페이지가 TDE 대상이면 노드에 암호화 플래그 (`log_manager.c:2171`).
5. **리스트 연결**: `prior_lsa_next_record()` (`log_append.cpp:1552`) → `prior_lsa_next_record_internal()` (`:1356`):
   - `prior_lsa_mutex` 획득. `start_lsa = prior_info.prior_lsa` 배정.
   - **트랜잭션 체인 갱신**: `prev_tranlsa = tdes->tail_lsa`, 그리고 `tdes->tail_lsa/head_lsa/undo_nxlsa`를 새 LSA로 (`:1598-1628`).
   - **MVCC 체인 갱신**: MVCC 레코드면 `vacuum_info.prev_mvcc_op_log_lsa = hdr.mvcc_op_log_lsa`, 헤더의 `mvcc_op_log_lsa`를 이 레코드로 전진 (`:1386-1428`, §14.1).
   - sysop 시작/종료, commit-with-postpone 등의 특수 레코드는 복구 커서(`tdes->rcv.*`)를 여기서 기록 (`:1429-1480`).
   - 노드를 `prior_list_tail`에 연결, `list_size` 누적.
6. **페이지 LSA 스탬프**: append 후 `pgbuf_set_lsa(addr->pgptr, start_lsa)`로 **데이터 페이지에 이 로그의 LSA를 찍는다** (`log_manager.c:2185`) — WAL 순서 보장과 redo 멱등성의 근간(§8, §13.2).

### 5.3 prior list → 페이지 버퍼 드레인

`prior_lsa_next_record_internal()` 끝에서 `list_size ≥ logpb_get_memsize()`이면 (`log_append.cpp:1518-1545`):

- SERVER_MODE 정상 운영: **로그 플러시 데몬을 깨우고** 1ms 양보 — 비동기 위임.
- SA_MODE/복구 중: 직접 `LOG_CS_ENTER → logpb_prior_lsa_append_all_list() → LOG_CS_EXIT`.

`logpb_prior_lsa_append_all_list()` (`log_page_buffer.c:3106`)는 LOG_CS 아래에서 `prior_lsa_mutex`를 잠깐 잡아 리스트 전체를 떼어낸 뒤(뮤텍스 해제), 노드를 하나씩 `logpb_append_next_record()` (`:2981`)로 페이지 버퍼에 복사하고 `hdr.append_lsa`를 전진시킨다. 복사가 끝난 노드는 즉시 해제된다.

> **정리**: 워커는 `prior_lsa_mutex`만 짧게 잡고, 비싼 페이지 복사는 LOG_CS 아래에서 배치로 — 이것이 다중 스레드 append 확장성의 핵심이다.

---

## 6. 로그 페이지 버퍼와 디스크 플러시

### 6.1 직접 매핑(direct-mapped) 버퍼

로그 페이지 버퍼(`log_Pb`, `log_page_buffer.c:244-279`)는 데이터 버퍼 풀과 달리 **해시도 LRU도 래치도 없다**. 슬롯 인덱스가 그냥 `pageid % num_buffers`다 (`logpb_get_log_buffer_index()`, `:380-384`).

- 슬롯 충돌 시 기존 페이지가 **dirty면 assert로 죽는다** (`:851-867`) — WAL 순서상 dirty 로그 페이지가 교체 대상이 되는 일은 설계상 없어야 하기 때문.
- 헤더 페이지는 전용 버퍼(`header_buffer`)를 따로 갖는다.
- 버퍼 수는 `log_buffer_size` 파라미터(`PRM_ID_LOG_NBUFFERS`).

### 6.2 플러시 경로: `logpb_flush_all_append_pages()`

플러시의 심장은 `logpb_flush_all_append_pages()` (`log_page_buffer.c:3232-3943`)다. 순서가 정교하다.

1. **EOF 마커**: `LOG_END_OF_LOG` 레코드를 붙여 복구가 로그 꼬리를 찾을 수 있게 한다 (`:3443-3456`).
2. **2단계 순서화 쓰기** (`:3355-3381` 주석): `nxio_lsa`가 위치한 페이지(=디스크 관점에서 로그의 최전선)는 **가장 마지막에** 쓴다.
   - 1단계: nxio 페이지를 제외한 dirty 페이지들을 논리·물리 모두 연속인 구간(run) 단위로 모아 기록 (`:3552-3645`).
   - 2단계: nxio 페이지 하나를 단독 기록 (`:3648-3697`).
   - 이렇게 하면 중간에 죽어도 "프런티어 페이지가 갱신됐는데 그 뒤 페이지가 없는" 반쪽 상태가 생기지 않는다.
3. **페이지별 CRC + TDE**: 기록 직전 페이지 체크섬 계산, 필요 시 스크래치 버퍼에 암호화 후 기록 (`:2808-2835`).
4. **fsync 1회**: 모든 쓰기 후 `fileio_synchronize()` 한 번 (`:3709-3722`). `PRM_ID_SUPPRESS_FSYNC`로 간헐 생략 가능.
5. **nxio_lsa 전진**: fsync 성공 후에야 `set_nxio_lsa(append_lsa)` (`:3804`) — 이 시점부터 그룹 커밋 대기자와 WAL 판정이 "여기까지 디스크에 있다"고 믿을 수 있다.

### 6.3 미완성 레코드의 이중 쓰기 (partial append)

레코드가 페이지에 걸쳐 있는 채로 플러시해야 할 때, 미완성 레코드가 디스크에 그대로 노출되면 복구가 쓰레기를 읽는다. 그래서 `partial_append` 상태 기계(`:217-228`)가:

1. 미완성 레코드가 시작되는 페이지를 **복사본**으로 뜨고,
2. 복사본의 해당 레코드 헤더를 `LOG_END_OF_LOG` + null `forw_lsa`로 덮어 그 복사본을 디스크에 쓰고 (`:3413-3423`),
3. 버퍼 안의 원본은 그대로 유지 — 이후 레코드가 완성되면 원본 헤더로 다시 쓰고 재동기화한다 (`:3750-3792`).

즉 디스크의 로그 꼬리는 항상 "완결된 레코드 + EOF"로 끝난다.

---

## 7. 그룹 커밋과 로그 플러시 데몬

커밋은 `logpb_flush_pages(commit_lsa)`로 "내 커밋 레코드까지 디스크에 갈 때까지" 기다린다 (`log_page_buffer.c:3980`). 동작은 두 파라미터의 조합으로 4가지 (`:3972-3977`):

| `log_async_commit` | 그룹 커밋(interval > 0) | 동작 |
|---|---|---|
| off | off | 플러시 데몬 깨우고 **대기** (사실상 즉시 플러시) |
| off | on | 데몬을 직접 깨우지 않고 `gc_cond`에서 **집단 대기** — 데몬이 주기적으로 플러시 후 broadcast |
| on | off | 데몬만 깨우고 **대기 없이 리턴** (커밋 유실 허용) |
| on | on | 대기 없이 리턴, 플러시는 그룹 주기로 |

- 대기 루프 (`:4067-4090`): `nxio_lsa < flush_lsa`인 동안 `pthread_cond_timedwait(gc_cond, 1000ms)` 반복. 별도 카운터 없이 **nxio_lsa 폴링**으로 판정한다.
- **로그 플러시 데몬**(`log_Flush_daemon`, `log_manager.c:363`): `log_flush_execute()` (`:10376-10397`)가 `logpb_flush_pages_direct()` 후 `pthread_cond_broadcast(gc_cond)` — 한 번의 fsync로 대기 중인 커밋 전부를 풀어주는 것이 그룹 커밋의 본질이다.
- 데이터 페이지를 fix한 채 커밋 대기에 들어가는 경우엔 교착 방지를 위해 데몬을 직접 깨우는 쪽으로 전환한다 (`:4062`).

---

## 8. WAL 규칙의 강제: 데이터 버퍼와의 연동

WAL은 로그 매니저 혼자 지키는 게 아니라 **데이터 페이지 버퍼(pgbuf)가 로그 매니저에게 물어보는** 구조로 강제된다.

1. 데이터 페이지가 변경될 때마다 `pgbuf_set_lsa()`로 페이지 헤더에 해당 로그 레코드의 LSA가 찍힌다(§5.2의 6).
2. pgbuf가 dirty 데이터 페이지를 디스크에 쓰기 직전, `logpb_need_wal(&page_lsa)` (`log_page_buffer.c:11255`) — 즉 `nxio_lsa <= page_lsa`인지 — 를 검사한다 (`src/storage/page_buffer.c:4013`).
3. 로그가 아직 안 나갔으면 `logpb_flush_log_for_wal()` (`log_page_buffer.c:4161`)로 **로그를 먼저 플러시**시킨다 (`page_buffer.c:4094, 4156` 등).

이 순환(로그 LSA를 페이지에 찍고 → 페이지를 쓰기 전 로그를 확인)이 "로그가 항상 데이터보다 먼저"를 기계적으로 보장한다.

---

## 9. 트랜잭션 수명주기와 로그

### 9.1 LOG_TDES의 LSA 커서들

트랜잭션 디스크립터 `log_tdes` (`log_impl.h:475-591`)에는 로그 순회용 커서가 여럿 있다.

| 필드 | 의미 |
|------|------|
| `head_lsa` / `tail_lsa` | 트랜잭션의 첫/마지막 로그 레코드. **`tail_lsa`가 NULL이면 "아무것도 안 바꾼 트랜잭션"** — 커밋/롤백 전 경로의 분기 기준 |
| `undo_nxlsa` | 다음에 undo할 레코드. 롤백 중 CLR이 추가되므로 tail과 분리 |
| `posp_nxlsa` | 커밋 시 실행할 첫 postpone 레코드 |
| `savept_lsa` | 마지막 세이브포인트 (레코드끼리 `prv_savept`로 역방향 체인) |
| `topop_lsa` / `topops` 스택 | 열려 있는 sysop들 (§10) |
| `tail_topresult_lsa` | 마지막 sysop 종결 LSA — postpone/롤백이 중첩 구간을 건너뛸 때 사용 |
| `rcv.*` | 복구 전용 커서: `sysop_start_postpone_lsa`, `tran_start_postpone_lsa`, `atomic_sysop_start_lsa` |

### 9.2 커밋 흐름 (`log_commit_local`, `log_manager.c:5159`)

```
TRAN_ACTIVE
  │  ① MVCC 완료/LOB 정리 등 "아직 로그를 쓰는" 마무리 작업
  ▼
TRAN_UNACTIVE_WILL_COMMIT        ← undo_nxlsa를 NULL로 (이제 절대 undo되지 않음)
  │  ② postpone 실행 (있으면): LOG_COMMIT_WITH_POSTPONE 기록 후
  │     postpone 캐시(메모리) 우선, 실패 시 로그 forward 스캔(log_do_postpone)
  ▼
(TRAN_UNACTIVE_COMMITTED_WITH_POSTPONE 경유 가능)
  │  ③ LOG_COMMIT 레코드 append (+복제 정보)
  │  ④ 락 해제  ← 커밋 레코드 append 직후, "플러시 전"에 푼다
  ▼
TRAN_UNACTIVE_COMMITTED
  │  ⑤ logpb_flush_pages(commit_lsa)에서 그룹 커밋 대기 (여기가 지속성 지점)
  ▼
log_complete: 새 TRID 발급, MVCC 전역 상태 갱신
```

- 변경이 없으면(`tail_lsa` NULL) 커밋 레코드 없이 락만 풀고 종료 (`:5237-5258`).
- **postpone**이란 "undo가 불가능해서 커밋 확정 후에만 실행할 수 있는 작업"(대표적으로 파일 실제 삭제)이다. 실행 시마다 `LOG_RUN_POSTPONE`(원본 postpone을 가리키는 `ref_lsa` 포함)이 남아 중복 실행을 막는다. `log_postpone_cache`(`log_postpone_cache.cpp`)는 postpone redo 데이터를 메모리에 캐시해 커밋 때 로그 재독을 생략하는 최적화다.

### 9.3 롤백 흐름 (`log_abort_local`, `log_manager.c:5277`)

```
TRAN_UNACTIVE_ABORTED (선진입)
  → log_rollback():  undo_nxlsa에서 시작해 prev_tranlsa 체인을 역방향 순회
      - 각 레코드: RV_fun[rcvindex].undofun 실행 + LOG_COMPENSATE(CLR) 기록
      - LOG_COMPENSATE를 만나면: 그 undo_nxlsa로 점프 (이미 보상된 구간 스킵)
      - 커밋된 sysop의 LOG_SYSOP_END를 만나면: lastparent_lsa로 점프 (통째로 스킵)
      - 락 타임아웃 무한대로 설정 — undo 도중 실패하면 DB가 깨지므로
  → MVCC 완료 → 락 해제 (커밋과 달리 undo가 끝난 "뒤"에 해제)
```

- **세이브포인트 부분 롤백**(`log_abort_partial`, `:5557`)은 롤백 구간을 sysop으로 감싸서 수행한다: `log_sysop_start` → `lastparent_lsa`를 세이브포인트 LSA로 조정 → `log_sysop_abort`. 트랜잭션은 계속 활성 상태로 남는다.
- 커밋은 락을 플러시 전에 풀고, 롤백은 undo 완료 후에 푸는 비대칭에 주의.

---

## 10. 시스템 오퍼레이션(sysop)과 시스템 트랜잭션

### 10.1 sysop (nested top action)

**sysop**은 "바깥 트랜잭션의 운명과 무관하게, 그 자체로 원자적으로 완결되어야 하는 변경 묶음"이다. 대표 사용처: B-tree 분할/병합, 파일 할당/해제, 카탈로그 갱신. 바깥 트랜잭션이 나중에 롤백되어도 B-tree 분할 자체는 유지된다(논리적 내용은 별도 undo로 되돌림).

- `log_sysop_start()` (`log_manager.c:3599`): `tdes->topops` 스택에 `lastparent_lsa = tail_lsa`를 푸시.
- `log_sysop_commit()` (`:3915`): sysop postpone 실행 후 `LOG_SYSOP_END(COMMIT)` 기록. 이후 바깥 트랜잭션의 롤백은 이 구간을 `lastparent_lsa` 점프로 통째로 건너뛴다.
- `log_sysop_abort()` (`:4038`): `lastparent_lsa`까지만 부분 롤백 후 `LOG_SYSOP_END(ABORT)`.
- **논리 undo 부착**: `log_sysop_end_logical_undo()` (`:3940`) — "이 sysop 전체를 되돌리는 방법"을 undo 이미지로 `LOG_SYSOP_END`에 내장한다(물리 위치를 특정할 수 없는 연산용). MVCC 연산이면 `LOGICAL_MVCC_UNDO`로 vacuum 체인에도 편입.
- `log_sysop_attach_to_outer()` (`:4097`): sysop을 독립 완결시키지 않고 부모(바깥 sysop 또는 트랜잭션)에 흡수 — postpone 잔량도 부모에게 이관되어 운명을 같이한다.
- `log_sysop_start_atomic()` (`:3665`): `LOG_SYSOP_ATOMIC_START` 마커를 남겨, 크래시 시 복구가 postpone 마무리 전에 이 sysop 전체를 먼저 롤백하도록 한다.

### 10.2 시스템 트랜잭션 (`log_system_tran.cpp`)

사용자 트랜잭션에 속하지 않고 로그를 남기는 주체(대표: **vacuum 워커**, 복구)를 위한 별도 tdes다.

- `LOG_SYSTEM_WORKER_FIRST_TRANID`부터 시작하는 **음수 TRID** 사용, 프리리스트로 풀링 (`:35-39`).
- sysop 스택이 빌 때마다 LSA 커서를 리셋 (`on_sysop_end`, `:143-171`) — 시스템 워커의 "트랜잭션"은 사실상 자기완결적 sysop들의 연속이다.
- 복구 중에는 로그에서 만난 시스템 TRID를 `rv_get_or_alloc_tdes()`로 재생성해 redo/undo에 사용 (`:232`).

---

## 11. 체크포인트

체크포인트의 목적은 **복구 시작점(`chkpt_lsa`)을 전진**시켜 복구 시간과 필요한 로그 보존량을 줄이는 것이다. `logpb_checkpoint()` (`log_page_buffer.c:6901-7406`), 체크포인트 데몬이 주기(`checkpoint_interval_in_secs`) 또는 로그 증가량(`checkpoint_every_npages`)으로 구동.

흐름:

1. 로그 플러시 후 `LOG_START_CHKPT` 기록 → 이 LSA가 새 `chkpt_lsa` 후보 (`:6988-6994`).
2. **`pgbuf_flush_checkpoint()`** (`:7011`): LSA ≤ 후보인 dirty 데이터 페이지들을 플러시하고, **플러시하지 못한 가장 작은 LSA를 `chkpt_redo_lsa`로 회수** — 이것이 복구 redo 시작점이다.
3. `fileio_synchronize_all` (`:7018`).
4. **트랜잭션 테이블 스냅샷**: TR_TABLE_CS + `prior_lsa_mutex` 아래에서 활성 트랜잭션별 `LOG_INFO_CHKPT_TRANS`(각종 LSA 커서 포함, `:6807`)와 진행 중 commit-postpone sysop(`LOG_INFO_CHKPT_SYSOP`, `:6857`)을 모아 `LOG_END_CHKPT` 레코드에 담는다 (`:7158-7177`). 시스템 tdes도 포함.
5. 헤더 갱신: `hdr.chkpt_lsa`, `hdr.smallest_lsa_at_last_chkpt`, `chkpt_redo_lsa` 저장 후 헤더 플러시 (`:7210-7227`). 모든 데이터 볼륨 헤더에도 체크포인트 LSA를 기록 (`:7242-7267`).
6. 시스템 크래시 복구에 더 이상 필요 없는 아카이브 번호를 계산해 둔다 (`:7281-7367`).

> 참고: 이 브랜치에는 `checkpoint_info.cpp`(체크포인트 리팩터링 버전)는 없다 — 고전적 `logpb_checkpoint()` 구현이다.

---

## 12. 아카이빙과 아카이브 삭제 정책

### 12.1 아카이브 생성

활성 로그는 링이므로, 다음 append 페이지가 **아직 아카이브 안 된 페이지의 물리 슬롯**에 도달하면(`LOGPB_AT_NEXT_ARCHIVE_PAGE_ID`, `log_page_buffer.c:157`) 덮어쓰기 전에 `logpb_archive_active_log()` (`:5650-5989`)가 실행된다:

1. append 페이지 강제 플러시.
2. `LOG_ARV_HEADER{arv_num, fpageid, npages}` 구성 후 아카이브 볼륨 생성.
3. 활성 로그 페이지들을 청크 단위(`fileio_write_pages`)로 복사, fsync.
4. 헤더 갱신: `nxarv_num++`, `nxarv_pageid = 마지막+1`, `nxarv_phy_pageid` 재계산.

**백그라운드 아카이빙**(`log_background_archiving=yes`)을 켜면 매 플러시 때 임시 파일 `_lgar_t`에 페이지를 미리 복사해 두었다가(`logpb_write_toflush_pages_to_archive`, `:2867`), 아카이브 시점에 rename만 하므로 아카이빙 순간의 I/O 폭주가 없다.

### 12.2 아카이브 삭제 — 4중 보류 조건

`logpb_remove_archive_logs_exceed_limit()` (`:5992`)가 `log_max_archives`를 초과한 아카이브를 지우되, 다음 소비자들이 아직 필요로 하는 것은 지우지 않는다:

| 보류 주체 | 메커니즘 |
|------|------|
| **Vacuum** | `vacuum_is_safe_to_remove_archives()`가 false면 전면 보류; `vacuum_min_log_pageid_to_keep()`이 담긴 아카이브부터는 보존 (`:6016-6107`) |
| **CDC/플래시백** | `cdc_find_lsa_in_progress()` 진행 중이면 이번 사이클 전체 연기 (`:6031-6044`) |
| **HA 로그 복사** | `logwr_get_min_copied_fpageid()` — 스탠바이가 아직 복사 못 한 아카이브 보존 (`:6051-6070`). `force_remove_log_archives`로 강제 무시 가능 |
| **시스템 크래시 복구** | `last_arv_num_for_syscrashes` 이전까지만 삭제 (`:6087`) |

---

## 13. 크래시 복구: analysis → redo → undo

서버 재시작 시 `log_recovery()` (`log_recovery.c:739`)가 LOG_CS 아래에서 실행된다. 시작점은 헤더의 `chkpt_lsa`.

```
chkpt_lsa ──► [1. ANALYSIS: 전방 스캔]  트랜잭션 테이블 복원, 로그 꼬리(EOF/손상) 확정
chkpt_redo_lsa ──► [2. REDO: 전방 스캔, 병렬]  모든 변경 재적용 (커밋 여부 무관)
             ◄── [3. UNDO: 후방 스캔]  미완 트랜잭션 되돌리기 (CLR 기록하며)
그 후: 미완 postpone 마무리 → 2PC 처리 → 새 체크포인트
```

### 13.1 Analysis (`log_recovery_analysis`, `:2595`)

`chkpt_lsa`부터 `forw_lsa` 체인으로 전방 순회하며 레코드 타입별로 트랜잭션 상태를 재구성한다 (`log_rv_analysis_record`, `:2386`).

- 처음 보는 TRID → tdes 할당, 기본 상태는 "크래시로 일방 중단됨(UNILATERALLY_ABORTED)". `LOG_COMMIT`/`LOG_ABORT`를 만나면 완결 처리 후 해제.
- **`LOG_END_CHKPT`를 만나면** (그것이 analysis 첫 구간일 때) 체크포인트에 담긴 트랜잭션 테이블 스냅샷을 통째로 복원하고, redo 시작점을 `chkpt.redo_lsa`(체크포인트 당시 가장 오래된 dirty 페이지 LSA)로 낮춘다 (`:1838-2062`).
- `LOG_COMPENSATE` → `undo_nxlsa` 갱신, `LOG_COMMIT_WITH_POSTPONE` → postpone 상태 복원, sysop 마커들 → `rcv.*` 커서 복원.
- **손상된 꼬리 감지**: 페이지 체크섬(`logpb_page_check_corruption`, `:2769`), 부분 플러시된 4K 블록 검출, "레코드가 초기값(0xff) 블록으로 이어짐" 검사, LSA 역행 루프 감지 (`:2769-2953`). 미디어 크래시면 `log_recovery_resetlog`로 로그를 그 지점에서 절단.

### 13.2 Redo (`log_recovery_redo`, `:3259`)

`chkpt_redo_lsa`부터 로그 끝까지 **커밋 여부와 무관하게 전부** 재적용한다(repeating history).

- **멱등성 규칙**: 대상 페이지를 fix한 뒤 `page_lsa ≥ record_lsa`면 이미 반영된 것이므로 skip (`log_rv_fix_page_and_check_redo_is_needed`, `:496-525`). 적용했다면 `pgbuf_set_lsa`로 페이지 LSA를 레코드 LSA로 갱신 — §5.2에서 append 때 페이지에 LSA를 찍는 이유가 바로 이 비교다.
- **병렬 redo** (`log_recovery_redo_parallel.cpp`): 워커 `MAX(16, 코어 수)`개. **VPID 해시로 워커를 고정 배정**(`vpid_hash % task_count`, `:628`)하므로 같은 페이지의 redo는 항상 같은 워커에서 LSA 순서대로 실행된다. 볼륨 생성/확장 같은 전역 연산만 메인 스레드에서 동기 실행.
- MVCC 레코드를 만나면 `mvcc_next_id`를 전진시키고 vacuum용 `mvcc_op_log_lsa`를 복원한다 (`:3501-3540`).
- redo 종료 후: 미완 atomic sysop 롤백(`log_recovery_abort_all_atomic_sysops`, `:3927`) → **커밋됐지만 postpone이 안 끝난 트랜잭션의 postpone 마무리**(`log_recovery_finish_all_postpone`, `:3930` → `:4251`).

### 13.3 Undo (`log_recovery_undo`, `:4426`)

미완(UNILATERALLY_ABORTED 등) 트랜잭션들을 되돌린다. 특이한 점은 **모든 대상 트랜잭션을 통틀어 가장 큰 `undo_nxlsa`부터** 하나씩 undo하는 전역 역순 인터리브 방식이라는 것 (`:4491`).

- 각 undo는 CLR(`LOG_COMPENSATE`)을 남기므로 undo 도중 또 죽어도 안전하다 — 재복구 시 CLR은 undo하지 않고 그 `undo_nxlsa`로 점프한다 (`:4778`).
- `LOG_SYSOP_END(LOGICAL_UNDO/LOGICAL_MVCC_UNDO)`는 내장된 논리 undo를 실행한 뒤 `lastparent_lsa`로 점프 (`:4789-4843`).
- `prev_tranlsa`가 NULL에 도달하면 `log_complete(LOG_ABORT)`로 종결 (`:4956`). 2PC prepared 트랜잭션은 코디네이터 결정을 위해 남겨둔다.

---

## 14. 로그의 다른 소비자들: Vacuum, HA, CDC

### 14.1 Vacuum — MVCC 연산 체인과 로그 블록

Vacuum은 죽은 MVCC 버전을 청소하기 위해 **로그를 데이터 소스로** 쓴다.

- 모든 MVCC 연산 레코드는 append 시점에 `vacuum_info.prev_mvcc_op_log_lsa`로 직전 MVCC 연산을 가리키는 **전역 역방향 체인**에 연결된다 (`log_append.cpp:1386-1428`). 체인 머리는 `log_Gl.hdr.mvcc_op_log_lsa`.
- 로그를 고정 페이지 수(`vacuum_log_block_pages`) 단위의 **블록**으로 나누고, 블록 경계를 넘을 때마다 `vacuum_produce_log_block_data()` (`src/query/vacuum.c:2893`)가 `{blockid, start_lsa(블록 내 마지막 MVCC 레코드), oldest/newest MVCCID}` 엔트리를 락프리 버퍼로 발행한다.
- Vacuum 마스터는 `newest_mvccid < 전역 oldest_visible_mvccid`가 된(= 모든 스냅샷에서 청소 가능해진) 블록만 작업으로 만들고, 워커가 `start_lsa`에서 체인을 역추적하며 레코드를 처리한다 (`vacuum.c:3338-3396`).
- 아직 vacuum 안 된 블록이 있는 아카이브는 삭제되지 않는다(§12.2).

### 14.2 HA — 물리 로그 배송(copylogdb) + 논리 재생(applylogdb)

- **copylogdb**(스탠바이 측): `logwr_get_log_pages` 요청을 반복해 서버에서 로그 페이지를 받아 스탠바이 자신의 활성 로그/아카이브 파일로 저장한다 (`log_writer.c:640, 1513`). 모드는 SYNC/SEMISYNC/ASYNC.
- **서버 측**: 연결마다 로그 라이터 엔트리(LWT)가 등록되고 (`log_writer.c:2124`), 로그 플러시 스레드(LFT)와 조건변수로 핸드셰이크한다 — LFT가 플러시를 완료하면 대기 중인 LWT들을 깨워 새로 flush된 페이지를 전송하게 하고, 마지막 LWT가 끝나면 LFT를 다시 풀어준다 (`log_page_buffer.c:3470-3911`, `log_writer.c:2519`). 즉 SYNC 복제는 로그 플러시 경로에 직접 끼어든다.
- **applylogdb**: 배송된 로그의 `LOG_REPLICATION_DATA/STATEMENT` 레코드를 해석해 **SQL로 재실행**한다 (`log_applier.c:524-529, 1568`). 물리 redo가 아닌 논리 재생이므로 스키마/버전이 다소 달라도 복제가 가능하다.

### 14.3 CDC

`src/api/cubrid_log.c`의 클라이언트 API가 서버의 CDC 데몬(`cdc_loginfo_producer_execute`, `log_manager.c:11069`)과 세션을 맺고, 데몬이 로그를 전방 순회하며 DML/DDL 변경 스트림을 재구성해 보낸다. Vacuum처럼 자기가 아직 읽어야 할 로그 페이지(`cdc_min_log_pageid_to_keep`, `:14071`)를 공표해 아카이브 삭제를 막는다.

---

## 15. 관련 파라미터 요약

| 파라미터 (cubrid.conf) | 내부 ID | 역할 |
|------|------|------|
| `log_buffer_size` | `PRM_ID_LOG_NBUFFERS` | 로그 페이지 버퍼 수 (§6.1) |
| `group_commit_interval_in_msecs` | `PRM_ID_LOG_GROUP_COMMIT_INTERVAL_MSECS` | >0이면 그룹 커밋 활성 + 플러시 데몬 주기 (§7) |
| `async_commit` | `PRM_ID_LOG_ASYNC_COMMIT` | 커밋 시 플러시 대기 생략 (§7) |
| `checkpoint_interval_in_mins/secs` | `PRM_ID_LOG_CHECKPOINT_INTERVAL_SECS` | 체크포인트 주기 (§11) |
| `checkpoint_every_size` | `PRM_ID_LOG_CHECKPOINT_NPAGES` | 로그 증가량 기반 체크포인트 트리거 (§11) |
| `log_max_archives` | `PRM_ID_LOG_MAX_ARCHIVES` | 보관할 아카이브 수 상한 (§12.2) |
| `force_remove_log_archives` | `PRM_ID_FORCE_REMOVE_LOG_ARCHIVES` | HA 복사 대기 무시하고 삭제 (§12.2) |
| `log_background_archiving` | `PRM_ID_LOG_BACKGROUND_ARCHIVING` | 점진적 아카이빙 (§12.1) |
| `vacuum_log_block_pages` | `PRM_ID_VACUUM_LOG_BLOCK_PAGES` | vacuum 로그 블록 크기 (§14.1) |
| (내부) | `PRM_ID_SUPPRESS_FSYNC` | fsync 간헐 생략 (§6.2) |

---

## 16. 파일별 역할 지도

| 파일 | 역할 |
|------|------|
| `log_lsa.hpp/.cpp` | LSA 타입과 비교 연산 |
| `log_storage.hpp` | 로그 페이지/활성 로그 헤더/아카이브 헤더 온디스크 구조 |
| `log_record.hpp` | 레코드 헤더, LOG_RECTYPE, 모든 레코드 본문 구조체 |
| `log_append.cpp/.hpp` | prior list, 레코드 생성(prior_lsa_gen_*), 트랜잭션/MVCC 체인 연결 |
| `log_manager.c` (~15K줄) | append 진입 API(log_append_*), 커밋/롤백/postpone/sysop/세이브포인트, 데몬 정의, CDC 프로듀서 |
| `log_page_buffer.c` (~12K줄) | 로그 페이지 버퍼, 플러시, 그룹 커밋 대기, WAL 판정, 아카이빙, 체크포인트, 헤더 I/O |
| `log_compress.c/.h` | LZ4 압축 + undo/redo XOR-diff |
| `log_postpone_cache.cpp/.hpp` | 커밋 postpone의 메모리 캐시 최적화 |
| `log_recovery.c` | 복구 오케스트레이션 + analysis/redo/undo 3단계 |
| `log_recovery_redo.hpp` / `_parallel.cpp/.hpp` | redo 적용 게이트(페이지 LSA 비교), VPID 해시 기반 병렬 redo |
| `log_system_tran.cpp/.hpp` | 시스템 트랜잭션(음수 TRID) 풀 |
| `log_tran_table.c` / `log_impl.h` | 트랜잭션 테이블, log_tdes, log_Gl 전역, TRAN_STATE |
| `log_global.c` | `log_Gl` 전역 인스턴스 |
| `log_writer.c/.h` | HA 로그 배송 (서버 LWT + copylogdb 클라이언트 양쪽) |
| `log_applier.c` | applylogdb — 복제 로그의 SQL 재생 |
| `log_2pc.c` | 2단계 커밋 |
| `src/storage/recovery.h/.c` | RV_fun 복구 함수 테이블, LOG_RCVINDEX |
| `src/query/vacuum.c` | 로그 블록 기반 vacuum (로그 소비자) |
| `src/api/cubrid_log.c` | CDC 클라이언트 API (로그 소비자) |

---

## 부록: 자주 헷갈리는 포인트

- **LSA 세 개(prior/append/nxio)는 층이 다르다.** prior는 "예약", append는 "메모리 기록", nxio는 "디스크 보장". 커밋 지속성과 WAL 판정은 오직 nxio_lsa 기준이다.
- **로그 버퍼는 데이터 버퍼와 완전히 다른 설계다.** 해시/LRU/래치 없는 직접 매핑 — 로그는 접근 패턴이 순차적이고, WAL 순서상 dirty 페이지 교체가 발생할 수 없기 때문.
- **커밋의 락 해제는 디스크 플러시보다 먼저다.** 커밋 레코드가 로그 버퍼에 들어간 순간 락을 풀고, 그 뒤 그룹 커밋 대기를 한다. 롤백은 반대로 undo가 다 끝나야 락을 푼다.
- **redo는 커밋 여부를 따지지 않는다**(repeating history). 미커밋 변경도 일단 전부 재적용한 뒤 undo 단계에서 되돌린다.
- **CLR(compensate)은 redo-only다.** undo의 undo는 없다. 복구가 몇 번을 반복돼도 각 변경은 정확히 한 번만 되돌려진다.
- **아카이브 삭제는 max_archives만으로 결정되지 않는다.** vacuum/HA/CDC/크래시 복구 4자가 모두 동의해야 지워진다.
