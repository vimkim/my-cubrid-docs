# CBRD-26950 재현 스크립트 — 실행 방법과 결과 리포트

- **작성일**: 2026-08-05
- **대상 스크립트**: `cbrd-26950/cbrd-26950-poc.sh`
- **재현 기준 커밋**: `07fef9d48` (`feat/oos` + `origin/develop` 머지), `debug_gcc` 프리셋
- **작성 도구**: Claude Code (Opus 5) — CUBRID 소스 무변경
- **판정**: **재현됨.** 최종 기본값으로 3회 연속 재현, 매회 "재삭제된 OOS OID 수 = 판독 불가해진 살아있는 행 수"가 정확히 일치.
- **결함 분석 본문**: `cbrd-26950/2026-07-31-CBRD-26950-vacuum-oos-slot-reuse-verification.md`

---

## 1. 이 스크립트가 무엇을 하는가

vacuum 이 죽은 행의 OOS 청크를 회수한 뒤, 그 슬롯을 **다른 살아있는 행** 이 재사용한 상태에서 같은 로그 블록을 재주행하면, vacuum 이 남의 데이터를 지운다 — 이것을 실제로 발생시키고 증명한다.

핵심은 **소스 수정도, fault-injection 훅도, 디버거도 필요 없다** 는 점이다. 스톡 `debug_gcc` 빌드에 `cubrid server stop` 하나만 쓴다. (원래 분석 문서 §8 은 훅이 필요하다고 봤으나 오판이었다. 자세한 정정은 본문 Q4.)

티켓이 지목한 세 조건을 각각 **강제** 한다. 우연에 맡기는 부분은 vacuum 회수 속도 하나뿐이고, 그것도 진행률 기반 정지로 흡수한다.

| # | 조건 | 스크립트가 강제하는 방법 |
|---|---|---|
| ① | **신원 없는 probe** — `oos_chunk_exists()` 는 "슬롯이 차 있나"만 보고 "내 청크인가"는 못 본다 (`oos_record_header` 에 owner OID·generation 없음) | 조건 ②③이 성립하면 자동으로 발동 |
| ② | **슬롯 재사용** — OOS 페이지는 `ANCHORED` 라 해제된 slotid 가 다음 `oos_insert` 에 그대로 재할당된다 | vacuum 이 회수하는 **동시에** 같은 크기 페이로드로 INSERT 하는 세션 6개를 붙인다 |
| ③ | **블록 재시도** — 완주하지 못한 블록은 `start_lsa` 가 전진하지 않아 불변 undo image 부터 통째로 재주행된다 | backlog 를 남긴 상태에서 `cubrid server stop` → worker 가 다음 로그 엔트리에서 블록을 버린다 |

---

## 2. 전제 조건

- **debug 빌드여야 한다.** 관측 지점인 `$CUBRID/log/oos.log` 가 `!NDEBUG` 전용이다 (`oos_log.hpp`). release 빌드에서는 아무 증거도 남지 않는다.
- `$CUBRID`, `$CUBRID_DATABASES` 가 그 빌드를 가리켜야 하고 `csql` 이 PATH 에 있어야 한다. 스크립트가 시작할 때 검사한다.
- 디스크 여유 약 1GB (OOS 데이터 약 250MB + 로그 볼륨 512MB).
- 포트 21950 이 비어 있어야 한다 (`PORT` 로 변경 가능).

스크립트는 **전용 DB(`oos26950`)와 전용 `cubrid.conf` 를 직접 만들어 `CUBRID_CONF_FILE` 로 주입** 한다. 설치본의 `conf/cubrid.conf` 를 고치지 않으므로 같은 빌드의 다른 DB(`testdb` 등)에는 영향이 없다.

---

## 3. 실행 방법

```bash
cd /path/to/cubrid-worktree      # $CUBRID 환경이 로드된 워크트리
~/gh/my-cubrid-docs/cbrd-26950/cbrd-26950-poc.sh
```

인자는 없고 모든 조절값은 환경변수다. 기본값으로 **약 3분** 걸리며, 대부분이 1단계 INSERT 시간이다.

```bash
# 더 큰 부하로 확실하게
ROWS=40000 cbrd-26950-poc.sh

# 다른 포트·DB 이름으로
PORT=22222 DB=oosbug cbrd-26950-poc.sh
```

### 3-1. 환경변수

| 변수 | 기본값 | 의미 |
|---|---|---|
| `ROWS` | 20000 | 1단계에서 넣는 OOS 적재 행 수. **이 값이 vacuum backlog 규모** 이며, 종료 지연(약 1.5초) 동안 vacuum 이 다 비우지 못할 만큼 커야 한다 |
| `R3_WRITERS` | 6 | 재사용용 INSERT 세션 수. vacuum 회수 속도를 따라가야 최근 해제된 슬롯까지 재사용된다 |
| `R3_ROWS` | 20000 | writer 1개당 INSERT 문 상한. 종료 시 클라이언트가 끊기므로 실제로는 훨씬 적게 들어간다 |
| `STOP_AT_PCT` | 30 | vacuum 이 전체 체인의 이 비율을 회수하면 서버를 정지시킨다 |
| `BLOCK_PAGES` | 128 | `vacuum_log_block_pages`. 블록 하나가 2MB 로그 분량이 되어 중간에 걸릴 만큼 오래 걸린다 |
| `PAYLOAD_UNITS` | 4996 | 페이로드 크기 (`8 + 2*4996` hex → **5000바이트**). OOS 트리거 문턱(`DB_PAGESIZE/4` ≈ 4086B)을 넘긴다 |
| `VERIFY_CHUNK` | 250 | 검증 문장 하나가 담당하는 id 범위 |
| `DB` / `PORT` | `oos26950` / 21950 | DB 이름과 포트 |
| `ER_LOG_VACUUM` | 4163 | `er_log_vacuum` 비트마스크 (ERROR\|WARNING\|VACUUM_DATA\|JOBS) |
| `WORK` | 임시 디렉터리 | 산출물 디렉터리. 지정하면 그 경로를 쓴다 |

---

## 4. 4단계 시나리오

### 1단계 — OOS 적재 행 만들기

5000바이트 `BIT VARYING` 페이로드로 `ROWS` 개 INSERT. 문자열 압축을 끈 `BIT VARYING` 이라 디스크 크기가 정확히 예측되고, 5000B > 트리거 문턱이므로 전부 OOS 로 빠진다.

### 2단계 — 옛 체인을 undo image 에만 남기고, 그 슬롯을 산 행에 넘긴다

**단일 트랜잭션으로** 전체 UPDATE 한다. 이유가 두 개다.

- **DELETE 가 아니라 UPDATE 여야 한다.** DELETE 는 heap sysop 안에서 OOS 를 회수하고 MVCC 체크로 멱등해서 이 버그 경로가 아니다 (본문 Q5). UPDATE 는 매번 새 OID 를 발급하므로 옛 체인을 가리키는 살아있는 heap 레코드가 없고 **undo image 에만** 남는다 — forward-walk 만이 그것을 본다.
- **단일 트랜잭션이어야 한다.** 커밋 전에는 MVCCID 가 활성이라 vacuum 이 손댈 수 없고, 커밋 순간 `ROWS` 개가 **한꺼번에** 회수 대상이 된다. 배치 커밋으로 쪼개면 vacuum 회수율과 클라이언트 생산율이 비슷해서 backlog 가 자라지 않는다.

커밋 직후 `R3_WRITERS` 개 세션이 **같은 크기** 페이로드로 INSERT 를 시작한다. `oos_delete_chain` 이 슬롯을 비우고 곧바로 bestspace 에 페이지를 재등록하므로, 이 INSERT 들이 방금 해제된 슬롯을 그대로 집는다.

### 3단계 — 블록을 중간에 버리게 한다

vacuum 이 `STOP_AT_PCT`% 를 회수한 순간 `cubrid server stop`. 종료 신호가 worker 에 닿으면 worker 는 다음 로그 엔트리에서 블록을 포기하고(`vacuum.c:3493` 의 `thread_p->shutdown`), `start_lsa` 는 그대로 남는다.

### 4단계 — 재기동, 그리고 검증

vacuum 이 그 블록을 `start_lsa` 부터 재주행한다. 같은 undo image 에서 같은 head OOS OID 를 뽑고, probe 는 "차 있음"만 확인하고, `oos_delete` 가 **살아있는 행의 청크** 를 지운다. 그 뒤 id 범위를 나눠 무결성을 검사한다 — 한 문장으로 전체를 훑으면 첫 판독 실패가 statement 를 중단시켜 뒤의 행이 모두 가려지기 때문이다.

---

## 5. 실행 결과 (2026-08-05, 소요 170초)

```
=== phase 0 — recreate oos26950 with a 16K page size
    work dir : .../run17

=== phase 1 — insert R1, OOS-backed
    R1: 20000 rows, payload 5000 B each

=== phase 2 — UPDATE, let live inserts take the freed slots, then stop mid-block
    R1 updated to 'BB' — 20000 'AA' chains now live only in the undo image
    6 R3 writers inserting; stopping once vacuum has freed 6000 chains
    pass 1 freed 8215 of 20000 chains, leaving 11785 unreclaimed
    R3 rows committed before the stop: 1838
    vacuum blocks abandoned mid-walk: 1

=== phase 3 — restart, and let vacuum re-walk the abandoned block
    waiting for vacuum to go quiet...
    the retry deleted 240 chunks

=== phase 4 — verdict
    committed gen-3 rows                   : 1838
    OOS OIDs deleted in both vacuum passes : 240
    gen-1 control (chains predate any free): 0 unreadable ranges, 0 rows wrong
    gen-3 victims                          : 6 unreadable ranges, 0 rows wrong

=== CORROBORATING — 240 OOS OIDs were deleted by both vacuum passes
    vol|page|slot  0|7350|0
    vol|page|slot  0|7350|1
    vol|page|slot  0|7350|2
    ... and 234 more, in .../run17/double_deleted.txt

=== REPRODUCED — committed gen-3 rows lost their OOS values
    240 gen-3 rows are unreadable, for example ids: 20273 20274 20275 20276 ...
    the server reports, for one of them:
    ERROR: Internal error: slot 2 on page 8079 of volume ".../oos26950" is not allocated.
```

종료 코드는 재현 시 `0`, 미재현 시 `1`, 환경 오류 시 `2` 다.

### 5-1. 출력 읽는 법

| 출력 줄 | 의미 | 정상 범위 |
|---|---|---|
| `pass 1 freed N of ROWS chains` | 1차 pass 가 회수한 체인 수. **`ROWS` 보다 작아야 한다** — 같으면 backlog 를 다 비운 것이고 재주행 대상이 없다 | 0 < N < `ROWS` |
| `R3 rows committed before the stop` | 슬롯을 재사용한 살아있는 행 수. 이 행들이 피해 후보다 | 수백~수천 |
| `vacuum blocks abandoned mid-walk` | 서버 로그의 `is interrupted!` 건수 | **0 이어도 정상** (5-2 참조) |
| `the retry deleted N chunks` | 2차 pass 가 지운 청크 수 | > 0 |
| `OOS OIDs deleted in both vacuum passes` | 두 pass 모두에서 삭제된 OID 수 = **재사용된 슬롯 수** | > 0 이면 재현 |
| `gen-1 control` | 대조군. UPDATE 후 체인이 어떤 삭제보다 먼저 할당되어 재사용 슬롯에 있을 수 없는 행들 | **반드시 `0 unreadable, 0 wrong`** |
| `gen-3 victims` | 해제 이후 INSERT·커밋되고 그 뒤 무수정인 행들 | 재현 시 `unreadable > 0` |

`STOP_AT_PCT=30` 이라 목표는 6000인데 실제로는 8215가 회수됐다. `cubrid server stop` 이 worker 에 닿기까지 약 1.5초가 걸리고 그동안 vacuum 이 계속 돌기 때문이며, 정상이다. 기본값이 이 초과분을 감안해 넉넉하게 잡혀 있다.

### 5-2. `abandoned mid-walk: 0` 이어도 재현되는 이유

`Processing log block N is interrupted!` 경고는 master 가 종료 전에 finished-job 큐를 처리한 경우에만 남는다. 그러지 못하면 블록은 vacuum data 페이지에 **IN_PROGRESS 로 남고**, 다음 부팅의 `vacuum_data_load_and_recover` 가 `set_interrupted()` 로 바꾼다(`vacuum.c:4398-4403`). **재주행은 어느 쪽이든 일어난다.** 실제로 이 경고가 0건인 실행에서도 재현됐으므로, **서버 로그에 경고가 없다는 것은 안전의 근거가 아니다.**

---

## 6. 결과 해석 — 두 갈래 증거

### 6-1. 결정적 증거: 살아있는 행의 데이터 소실

피해 행은 **슬롯이 해제된 뒤에 INSERT·커밋되고 그 후 한 번도 수정되지 않은** 행이다. 이 행을 건드린 것은 vacuum 의 2차 pass 뿐이다. 실행 후 실제 csql 세션:

```sql
-- 행은 heap 에 그대로 있다
SELECT id, gen FROM t WHERE id = 20273;
           id          gen
===========================
        20273            3
1 row selected.

-- 그런데 payload 를 읽으면 실패한다
SELECT DISK_SIZE(payload) FROM t WHERE id = 20273;
ERROR: Internal error: slot 2 on page 8079 of volume ".../oos26950" is not allocated.

-- 대조군은 정상
SELECT DISK_SIZE(payload) FROM t WHERE id = 1;
   disk_size(payload)
=====================
                 5008
1 row selected.

-- COUNT 는 성공한다 — heap 은 무손상, OOS 값만 사라졌다
SELECT gen, COUNT(*) FROM t GROUP BY gen;
          gen              count(*)
====================================
            1                 20000
            3                  1838
2 rows selected.
```

**손상 범위가 "재사용된 슬롯"에 정확히 국한** 된다는 것이 핵심이다. 대조군 20000행은 3회 실행 모두 무손상이었다.

> 실제 운영에서는 이보다 더 나쁠 수 있다. 여기서는 슬롯이 비어 있어 에러가 났지만, 그 슬롯이 **또 다른 행에 재할당된 뒤** 읽으면 에러 없이 남의 데이터가 반환될 수 있다 — 티켓이 말하는 무증상 손실이다. 스크립트는 그 경우도 "rows wrong" 으로 잡도록 페이로드에 id 를 새겨 두었다.

### 6-2. 보강 증거: 같은 OID 의 두 번 삭제

`oos.log` 에서 같은 OID 가 두 pass 에서 각각 삭제된 기록. 아래는 위 실행의 원시 로그로, 11초 간격(= 서버 재기동 간격)으로 같은 슬롯이 두 번 지워졌다.

```
[13:41:22] OOS [DEBUG](oos_delete_chain:2212): deleted chunk at oid={vol=0,page=7350,slot=0}, next={vol=-1,page=-1,slot=-1}
[13:41:33] OOS [DEBUG](oos_delete_chain:2212): deleted chunk at oid={vol=0,page=7350,slot=0}, next={vol=-1,page=-1,slot=-1}
```

청크는 슬롯이 차 있을 때만 삭제되므로, 이 슬롯들은 두 삭제 **사이에 누군가에게 넘어갔다.**

단, 이 목록은 **재삭제된 슬롯 수** 로 읽어야 하고 행 단위 피해 목록으로 읽으면 안 된다. 종료 중 abort 된 sysop 이 청크를 복원했다면 두 번째 삭제가 정당할 수 있고, 그것도 같은 목록에 들어온다. 그래서 6-1 이 결정적 증거고 이것이 보강 증거다. (참고로 3회 실행 모두 두 수치가 정확히 일치했다.)

---

## 7. 산출물

`WORK` 디렉터리에 남는다. 재현 실패 원인 추적에 쓴다.

| 파일 | 내용 |
|---|---|
| `damaged_ids.txt` | **판독 불가해진 행 id 전체 목록** |
| `double_deleted.txt` | 두 pass 모두에서 삭제된 OOS OID (`vol\|page\|slot`) |
| `deleted_A.txt` / `deleted_C.txt` | 1차 / 2차 pass 가 삭제한 OID 집합 |
| `verify_gen3.log` / `verify_gen1.log` | 검증 실패 범위와 서버 에러 원문 (대조군 파일은 비어 있어야 정상) |
| `cubrid.conf` | 그 실행이 실제로 쓴 설정 |
| `insert_r1.sql`, `insert_r3_*.sql`, `*.out` | 투입한 SQL 과 csql 출력 |

이와 별도로 `$CUBRID/log/oos.log` (청크 삭제 원시 로그)와 `$CUBRID/log/server/<DB>_latest.err` (vacuum 블록 상태 전이)를 본다.

---

## 8. 재현되지 않을 때

스크립트가 어느 레버를 올릴지 안내하지만, 판단 기준은 이렇다.

| 증상 | 원인 | 조치 |
|---|---|---|
| `pass 1 freed` = `ROWS` | vacuum 이 backlog 를 다 비웠다 — 재주행할 블록이 없다 | `ROWS` 를 올리거나 `STOP_AT_PCT` 를 낮춘다 |
| backlog 는 남았는데 `deleted in both passes: 0` | 재사용이 최근 해제된 슬롯까지 못 따라갔다. 중단된 블록의 이미 처리된 구간은 **가장 최근에 해제된** 슬롯이다 | `R3_WRITERS` 를 올린다 |
| `vacuum freed nothing` 으로 즉시 종료 | 블록이 발행되지 않았거나 vacuum 이 안 돌았다 | 서버 로그의 `Add block` 유무 확인, `ROWS` 상향 |
| `oos.log` 가 아예 안 생김 | release 빌드다 | debug 빌드로 전환 |

회수 속도가 버퍼 온도에 따라 초당 1000~13000개까지 요동치기 때문에, 고정 sleep 대신 진행률 기반 정지를 쓴다. 그래도 실패하면 그냥 한 번 더 돌리는 것이 가장 빠르다.

---

## 9. 재현 이력

최종 기본값(`ROWS=20000`, `R3_WRITERS=6`, `STOP_AT_PCT=30`) 기준 **3회 연속 재현**.

| 실행 | 회수(1차 pass) | 재삭제 OID | 판독 불가 행 | 대조군 | 소요 |
|---|---|---|---|---|---|
| 1회차 | 미기록 | 293 | 293 | 무손상 | ~4분 |
| 2회차 | 미기록 | 163 | 163 | 무손상 | ~4분 |
| 3회차 | 8215 / 20000 | 240 | 240 | 무손상 | 170초 |

매회 **재삭제 OID 수 = 판독 불가 행 수** 로 정확히 일치했다.

---

## 10. 주의사항

- **다른 DB 에는 영향이 없다.** 전용 DB 와 전용 conf 를 쓴다. 다만 `$CUBRID/log/oos.log` 는 설치본 공용이라 append 된다. 스크립트는 파일을 자르지 않고 시작 오프셋만 기억해 그 이후만 읽으므로, 다른 세션의 기록은 보존된다.
- **DB 를 켜둔 채로 끝난다.** 사후 조사용이다. 정리는 다음과 같이 한다.

  ```bash
  CUBRID_CONF_FILE=<WORK>/cubrid.conf cubrid server stop oos26950
  CUBRID_CONF_FILE=<WORK>/cubrid.conf cubrid deletedb oos26950
  ```

- **부수 발견 1 — 종료 중 인터럽트가 debug 빌드에서 서버를 abort 시킬 수 있다.** 종료로 클라이언트의 OOS INSERT 가 인터럽트되어 `pgbuf_fix` 가 `ER_INTERRUPTED`(-4) 로 실패하면 `file_alloc` 이 정상적으로 에러를 반환하는데, `oos_file_alloc_new` 가 무조건 `assert (false)` 를 건다(`oos_file.cpp:1892`). 실행 중 코어가 생기면 이것일 수 있고, CBRD-26950 과는 별개 이슈다. 스택은 분석 문서 §8-5 에 있다.
- **부수 발견 2 — `oos_insert_many` 에 디버그 로그가 없다.** 실제 INSERT 경로인 배치 API(CBRD-27006)에 `oos_debug` 가 없어서 `oos.log` 에 **삭제만 남고 삽입은 남지 않는다**. 그래서 슬롯 재사용을 로그만으로 직접 증명할 수 없고, 이 스크립트는 "두 pass 의 삭제 집합 교집합" 이라는 우회로를 쓴다. 재현 초기에 OOS 가 트리거되지 않는다고 오판한 원인도 이것이었다.
- **수정 검증에 쓸 때**: `oos_record_header` 에 신원 필드(generation 우세, 분석 문서 §5-1)가 들어가면 2차 pass 의 probe 가 불일치를 보고 no-op 해야 한다. 즉 **`deleted in both passes` 와 `gen-3 unreadable` 이 모두 0** 이 되고 스크립트는 종료 코드 1(미재현)을 반환해야 한다. 회귀 게이트로 쓸 때는 이 반전된 기대값을 쓴다.
