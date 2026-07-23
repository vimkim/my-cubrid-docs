# CUBRID CDC × HA Failover 문제 분석 보고서

- **주제**: HA 환경에서 master가 죽었다가 standby를 거쳐 다시 master가 되면 CDC가 동작하지 않는 문제의 원인 분석
- **분석 대상 소스**: cubrid `develop` 브랜치, commit `4cfc8370e`
- **작성**: Claude (Fable 5), 2026-07-22
- **성격**: 소스코드 정적 분석 보고서 (재현 로그 미확보 상태의 원인 후보 분석 포함)

---

## 1. 문제 요약

QA에서 다음 시나리오가 보고되었다.

```
노드 A (master, CDC 연결됨)
   │ ① A 죽음 (crash) ──────► 노드 B가 master로 failover
   │ ② A 재기동 ────────────► A는 standby로 합류 (applylogdb가 B의 변경분을 적용)
   │ ③ B 죽음 or 스위치오버 ──► A가 다시 master로 승격
   ▼
이후 A에 대해 CDC가 동작하지 않음
```

**한 줄 결론: CDC 서브시스템에는 HA 역할 전이(active↔standby)를 인지하는 코드가 단 한 줄도 없다.**

`git log --all -S "standby" -- src/api/cubrid_log.c` 와
`git log --all -S "standby" -- src/transaction/log_manager.c` (CDC 함수 기준)가
빈 결과를 반환할 정도로, CDC는 "이 서버는 영원히 단일 active 서버"라는 암묵적
전제 위에 설계되어 있다. master→standby→master 사이클은 이 전제를 세 곳에서
깨뜨리며, 그 결과가 "CDC 동작 안 함"으로 관측된다.

---

## 2. 배경 지식: CDC가 동작하는 방식

원인을 이해하려면 CDC의 네 가지 축을 알아야 한다.

### 2.1 Supplemental Log — CDC의 원재료

`supplemental_log` 파라미터를 켜면, 서버는 DML을 수행할 때마다 일반 WAL 레코드
외에 **CDC 전용 보조 레코드**를 트랜잭션 로그에 추가로 남긴다.

| 레코드 | 내용 | 기록 위치 |
|---|---|---|
| `LOG_SUPPLEMENT_TRAN_USER` | 트랜잭션을 수행한 **DB 유저 이름** | 트랜잭션의 첫 supplemental DML 직전 + 커밋 직전 (`log_manager.c:4649`) |
| `LOG_SUPPLEMENT_INSERT/UPDATE/DELETE` | 클래스 OID + undo/redo LSA | 각 DML마다 (`heap_file.c` → `log_append_supplemental_lsa`, `log_manager.c:4892`) |
| `LOG_SUPPLEMENT_UNDO_RECORD` 등 | 변경 전 이미지 | 필요 시 |

핵심: **유저 이름은 "그 서버에 접속해 DML을 실행한 세션의 계정"** 이 기록된다
(`tdes->client.get_db_user()`). 이 사실이 뒤에서 문제가 된다.

### 2.2 시간 → LSA 탐색 (`cdc_find_lsa`)

CDC 클라이언트는 "몇 시부터의 변경분을 달라"고 시간으로 요청하고, 서버는 이를
로그 위치(LSA)로 변환한다 (`log_manager.c:14210`). 이때 서버는 로그를 앞으로
스캔하면서 **시간 정보를 가진 레코드만**을 이정표로 사용한다:

- `LOG_COMMIT` / `LOG_ABORT` — 커밋/어보트 시각 (donetime)
- `LOG_DUMMY_HA_SERVER_STATE` — **1초마다 주기적으로 기록되는 더미 레코드** (at_time)

두 번째 레코드가 CDC의 사실상 "심장 박동"이다. producer 데몬의 주석
(`log_manager.c:11132`)이 이를 명시한다:

```
/* LOG_HA_DUMMY_SERVER_STATUS is appended every 1 seconds and flushed.
 * So it is expected to be woken up by looper within period of looper */
```

그런데 이 더미 레코드를 기록하는 데몬 `log_check_ha_delay_info_execute`
(`log_manager.c:10294`)의 조건을 보면:

```c
if (server_state == HA_SERVER_STATE_ACTIVE || server_state == HA_SERVER_STATE_TO_BE_STANDBY)
  {
    ...
    log_append_ha_server_state (&thread_ref, server_state);   /* ← ACTIVE 계열에서만 */
  }
else
  {
    /* standby: 복제 지연 계산만 하고 아무것도 append하지 않음 */
  }
```

**서버가 standby인 동안에는 이 이정표가 로그에 전혀 기록되지 않는다.**
standby 서버의 로그에는 applylogdb가 적용한 트랜잭션의 커밋 레코드만 있고,
복제 트래픽이 없으면 시간 이정표가 하나도 없는 공백 구간이 된다.

### 2.3 진행 위치(북마크) = 노드-로컬 물리 LSA

CDC의 "어디까지 읽었는가"는 순수하게 **그 노드 로그 파일의 물리 위치(LSA =
pageid + offset)** 다.

- 클라이언트: `g_next_lsa` (`cubrid_log.c`)
- 서버: `cdc_Gl.consumer.next_lsa`, `cdc_Gl.producer.next_extraction_lsa`

HA에서는 같은 논리적 변경이 노드마다 **완전히 다른 LSA**에 기록된다. 즉 이
북마크는 A 노드에서만 의미가 있고, failover를 가로질러 이동할 수 없다.
(MySQL이 binlog file/position 복제의 같은 문제를 GTID로 해결한 것과 정확히
같은 종류의 문제다.)

### 2.4 재접속 시 북마크 검증 (`cdc_validate_lsa`)

서버가 재기동된 후 클라이언트가 저장해둔 LSA로 추출을 재개하면, 서버는
`cdc_validate_lsa` (`log_manager.c:14494`)로 검증한다:

1. `cdc_check_lsa_range` — 보존된 로그(가장 오래된 아카이브 ~ 현재 append 지점)
   범위 안인가? (`log_manager.c:14395`)
2. 해당 로그 페이지를 읽어, 페이지 첫 레코드부터 `forw_lsa` 체인을 따라가며
   **정확히 그 offset에서 시작하는 레코드가 실제로 있는가?** (`log_manager.c:14539`)

둘 중 하나라도 실패하면 `ER_CDC_INVALID_LOG_LSA`로 추출이 거부된다.

---

## 3. 타임라인별 고장 메커니즘

이제 보고된 시나리오를 시간 순으로 따라가며, 각 단계에서 무엇이 어긋나는지 본다.

```
 A의 트랜잭션 로그 (시간 →)

 [ ① master 구간 ]   [ 크래시 경계 ]  [ ② standby 구간 ]        [ ③ 재승격 후 ]
 ─────────────────── ✂ ─────────────────────────────────────────────────────►
  커밋 + 1초 더미      꼬리 유실 +      applylogdb 적용 트랜잭션만    커밋 + 1초 더미
  (시간 이정표 촘촘)    recovery 레코드   · 시간 이정표 공백/희박       (정상 복귀)
                                       · TRAN_USER = applier 계정
                                       · 크래시로 끊긴 트랜잭션 잔재
        ▲
        └ CDC 클라이언트의 마지막 북마크는 크래시 직전 로그 꼬리
```

### 3.1 ① → 크래시: LSA 북마크 오염

CDC는 실시간으로 로그 꼬리를 쫓아가므로, 크래시 직전 클라이언트의 `next_lsa`는
A 로그의 최말단이다. 크래시로 미플러시 꼬리가 유실되고, 재기동 후 recovery와
standby 기간의 새 레코드가 **같은 pageid/offset 영역에 다시 쓰인다.** 이후
클라이언트가 저장한 LSA로 재개를 시도하면 두 가지 경우가 생긴다.

| 경우 | 결과 |
|---|---|
| 그 offset에서 시작하는 레코드가 없음 | `cdc_validate_lsa` 실패 → **`ER_CDC_INVALID_LOG_LSA` 영구 반환.** 클라이언트 라이브러리에는 자동 폴백(시간 기반 재탐색)이 없어서, 애플리케이션이 스스로 `cubrid_log_finalize()` 후 처음부터 다시 시작하지 않는 한 CDC는 계속 실패한다 |
| 우연히 새 레코드가 정확히 그 offset에서 시작 | 검증은 통과하지만 **원래 의미와 다른 위치**에서 재개 → 이벤트 중복/유실 (조용한 오동작) |

참고로 `cubrid_log_finalize()`는 `g_next_lsa`를 지워버리므로
(`cubrid_log.c:2067`), 재시작 후에는 애플리케이션이 LSA를 외부에 따로 보관해
두지 않았다면 시간 기반으로만 재개할 수 있다 — 그리고 그 시간 기반 재개가
다음 절의 문제에 부딪힌다.

### 3.2 ② standby 구간: 시간 이정표 공백 + 로그 소유권 변질

**(1) 시간 이정표 공백.**
2.2에서 본 대로 standby 동안 `LOG_DUMMY_HA_SERVER_STATE`는 기록되지 않는다.
이 구간에 존재하는 시간 정보는 applylogdb가 적용한 트랜잭션의 커밋 시각뿐인데,
이는 **원본(B에서의) 커밋 시각이 아니라 A에서의 적용 시각**이다. 복제 트래픽이
없었다면 이 구간에는 시간 정보가 아예 없다.

그 결과, failover 전후 구간을 향한 `cubrid_log_find_lsa(time)`은:

- 이정표를 못 찾고 다음 구간(재승격 후 첫 더미 레코드)까지 밀리거나
  → `ER_CDC_ADJUSTED_LSA` (`log_manager.c:14273-14286`)
- 아예 못 찾아 `ER_CDC_LSA_NOT_FOUND`

가 되어, **그 사이의 이벤트가 조용히 건너뛰어진다.**

**(2) 유저 정보 변질 — user 필터가 이벤트를 전멸시킴.**
standby 구간의 로그는 applylogdb가 적용한 트랜잭션이다. supplemental log 자체는
standby에서도 정상 생성되지만(생성 경로 `heap_file.c:2773
check_supplemental_log`는 HA 상태를 보지 않음), `LOG_SUPPLEMENT_TRAN_USER`에는
원본 유저가 아니라 **applylogdb의 접속 계정(보통 dba)** 이 기록된다.

따라서 `cubrid_log_set_extraction_user()`로 특정 유저 필터를 걸어둔 CDC
클라이언트는, failover 동안 B에서 발생했던 변경분을 A의 로그에서 **한 건도
받지 못한다.** `cdc_log_extract`의 유저 필터 (`log_manager.c:10740`
`cdc_is_filtered_user`)에서 전부 걸러지기 때문이다.

**(3) standby에도 CDC 세션이 그냥 붙는다.**
`scdc_start_session` (`network_interface_sr.cpp:11371`)은 `supplemental_log`
파라미터만 검사하고 HA 상태를 보지 않는다. standby 서버는 일반 클라이언트
등록도 허용하므로 (`server_support.c:1754` — `TO_BE_STANDBY`만 거부), CDC
클라이언트는 standby 서버에 정상적으로 세션을 열고 추출을 시작할 수 있다.

그런데 유휴 standby에서는 producer가 로그 끝(`LOG_END_OF_LOG`)에 도달하면
`ER_CDC_NULL_EXTRACTION_LSA` (`log_manager.c:10695-10701`)로 같은 LSA를
무한 재시도한다. active 서버에서는 1초마다 더미 레코드가 이 상태를 풀어주지만,
standby에는 그 하트비트가 없다. 클라이언트 입장에서는 **"연결은 되는데 매번
timeout에 0건"** 인 상태가 된다 — "CDC가 동작 안 한다"의 전형적인 관측 형태다.

### 3.3 ③ 재승격: 아무도 CDC를 복구해주지 않는다

HA 상태 전이의 중심 함수 `css_change_ha_server_state`
(`server_support.c:1860`)와 승격/강등 경로 전체에 `cdc_*` 호출이 **하나도
없다.** 승격 시:

- CDC 큐 재초기화 없음, producer/consumer 위치 리셋 없음, 세션 무효화 없음
- ①에서 오염된 북마크와 ②에서 밀린 탐색 결과가 그대로 정상 구간까지 이어짐

추가로 두 가지 지뢰가 재승격 후 추출 경로에 남는다.

**(a) 크래시 경계의 미완료 트랜잭션 잔재 → `cdc_find_user` 풀스캔.**
크래시로 커밋/어보트 없이 끊긴 트랜잭션의 supplemental 레코드를 추출기가
만나면, `cdc_find_user` (`log_manager.c:13583`)는 그 trid의 TRAN_USER를 찾아
**현재 nxio_lsa까지 로그 전체를 앞으로 스캔**한 뒤에야 포기한다. 이 실패는
캐시되지 않아서 그런 레코드를 만날 때마다 반복된다(standby 구간 + 재승격 구간
전체 재스캔). 최악의 경우 debug 빌드에서는 `log_manager.c:13636`의
`assert (!(LOG_COMMIT && trid))`에 걸린다.

**(b) 아카이브 보존 보호의 증발.**
CDC가 아직 안 읽은 아카이브를 지우지 않게 하는 보호 장치
`cdc_min_log_pageid_to_keep` (`log_manager.c:14071`)은
`cdc_Gl.consumer.start_lsa`라는 **런타임 메모리 상태**에 의존한다. 서버가 죽는
순간 이 보호는 사라지고, A가 죽어 있거나 standby인 동안 아카이브가 삭제되면
클라이언트의 옛 LSA는 `cdc_check_lsa_range` 범위 검사에서 탈락해 역시
`ER_CDC_INVALID_LOG_LSA`가 된다.

---

## 4. 왜 "단순 재시작"은 되는데 이 시나리오만 문제인가

active → 재기동 → active 의 단순 재시작은:

- 시간 이정표 공백이 서버 다운 시간만큼으로 짧고,
- 로그 내용의 "소유권"(누가 쓴 트랜잭션인가)이 변하지 않으며,
- 크래시 경계가 하나뿐이고 그 직후 바로 1초 더미 레코드가 재개된다.

반면 master→standby→master 사이클은 다음 세 가지를 **동시에** 만든다:

1. **긴 시간-이정표 공백 구간** (standby 기간 전체)
2. **applier 소유 로그 구간** (유저 필터 무력화, 시각 왜곡)
3. **크래시 경계** (북마크 오염, 미완료 트랜잭션 잔재)

이 조합이 CDC의 세 축 — 시간 탐색, LSA 재개, 유저 필터 — 을 모두 건드린다.

---

## 5. 관측될 수 있는 증상 정리 (진단 가이드)

QA가 본 "동작 안 함"이 정확히 어떤 것인지는 재현 로그로 확정해야 한다.
가능성이 높은 순서:

| # | 증상 | 원인 메커니즘 | 확인 방법 |
|---|---|---|---|
| 1 | `cubrid_log_extract`가 `CUBRID_LOG_INVALID_LSA` 계열 에러 반복 | 3.1 북마크 오염 또는 3.3(b) 아카이브 삭제 | 클라이언트 반환 코드, 서버 `ER_CDC_INVALID_LOG_LSA` notification |
| 2 | 연결은 되는데 timeout마다 0건 (무한 무소식) | 3.2(3) producer 스톨, 또는 3.3(a) 풀스캔 지연 | `cdc_logging_debug=yes` 후 producer 로그에서 같은 LSA 반복/`ER_CDC_NULL_EXTRACTION_LSA` 확인 |
| 3 | `find_lsa`가 `ADJUSTED`/`NOT_FOUND` 반환, failover 구간 이벤트 유실 | 3.2(1) 시간 이정표 공백 | 반환 timestamp가 요청보다 크게 밀렸는지 확인 |
| 4 | 이벤트는 나오는데 failover 구간 것만 없음/유저가 dba로 나옴 | 3.2(2) applier 유저 기록 | user 필터 제거 후 재시도 비교 |

**재현 시 켜야 할 것**: 클라이언트 `cubrid_log_set_tracelog()`, 서버
`supplemental_log` 유지 + CDC 디버그 로깅 파라미터, 서버 에러 로그의
`ER_CDC_*` 시퀀스.

---

## 6. 해결 방안 제안

### 6.1 단기 — 현 구조 유지, 결함 봉합

1. **HA 전이 훅에 CDC 라이프사이클 연결.**
   `css_change_ha_server_state`의 승격/강등 경로에서 `cdc_pause_producer()` →
   `cdc_reinitialize_queue()` → consumer 위치 무효화를 수행하고, 붙어 있던
   클라이언트에는 전용 에러코드(예: `ER_CDC_ROLE_CHANGED`)로 재동기화 필요를
   알린다. 최소한 "조용히 이상해지는" 것은 막는다.

2. **standby에서의 CDC 정책을 명시적으로 결정.**
   - 지원 안 함: `scdc_start_session`에서 `ha_Server_state != ACTIVE`이면
     `ER_CDC_NOT_AVAILABLE` 반환 (현재 supplemental_log 검사 옆 한 줄).
   - 지원함: 아래 3번이 선행 조건.

3. **시간 이정표를 standby에서도 유지.**
   `log_check_ha_delay_info_execute`가 standby 상태에서도
   `LOG_DUMMY_HA_SERVER_STATE`를 append하도록 확장. 더미 레코드는 복제 대상이
   아니므로 이론상 안전하지만, standby의 로그 append가 copylogdb/applylogdb와
   로그 볼륨 수명에 미치는 영향 검증 필요. **이 한 가지로 시간 탐색 공백과
   standby producer 스톨이 동시에 해소된다.**

4. **클라이언트 라이브러리에 복구 프로토콜 내장.**
   `CUBRID_LOG_INVALID_LSA`/`LSA_NOT_FOUND` 수신 시 "마지막 성공 이벤트의
   timestamp로 `find_lsa` 폴백 + at-least-once 재개"를 라이브러리가 제공하고,
   재개 시맨틱(중복 가능성 포함)을 매뉴얼에 문서화. 현재는 이 판단이 전부
   애플리케이션 몫이다.

5. **`cdc_find_user` 방어.**
   TRAN_USER를 못 찾은 trid를 `tran_ignore`에 등록해 풀스캔을 1회로 제한하고,
   `log_manager.c:13636`의 assert를 에러 처리로 전환. (크래시 경계 미완료
   트랜잭션은 정상 상황임을 코드가 인정해야 한다.)

6. **아카이브 보존의 영속화.**
   CDC 소비 위치를 로그 헤더/별도 메타에 영속화해 재기동 후에도
   `cdc_min_log_pageid_to_keep`이 유효하게 하거나, 최소한 "CDC 운영 시
   `log_max_archives` 여유 확보"를 운영 가이드에 명시.

### 6.2 중기 — 데이터 정합성

7. **applier 트랜잭션의 원본 유저 보존.**
   복제 로그에 원본 TRAN_USER를 실어 applylogdb 적용 시 supplemental
   TRAN_USER를 원본 유저로 기록하거나, CDC 이벤트에 "replicated" 플래그를 달아
   소비자가 구분하게 한다. 이것 없이는 user 필터를 쓰는 CDC가 failover 구간을
   항상 잃는다.

### 6.3 장기 — 아키텍처

8. **진행 위치의 논리화.**
   - 1단계: 북마크를 `(node-id, LSA)` 튜플로 확장해 다른 노드/다른 수명의
     LSA 오용을 즉시 감지.
   - 최종: 원본 커밋 기준의 논리적 위치(GTID 유사 식별자, 또는 원본 LSA ↔
     적용 LSA 매핑)를 도입해 **failover를 가로질러 이어받을 수 있는 CDC 위치**를
     정의. 이것이 없는 한 "HA에서 CDC가 끊김 없이 동작"은 어떤 봉합으로도
     달성되지 않는다.

---

## 7. 부록: 관련 코드 위치 총람

| 항목 | 위치 |
|---|---|
| CDC 세션 시작 (HA 검사 없음) | `src/communication/network_interface_sr.cpp:11371` `scdc_start_session` |
| 시간→LSA 탐색 | `src/transaction/log_manager.c:14210` `cdc_find_lsa` |
| 시간 이정표 스캔 (COMMIT/ABORT/HA더미만 인식) | `log_manager.c:14645` `cdc_get_start_point_from_file`, `:14821` `cdc_get_lsa_with_start_point` |
| 1초 더미 레코드 append 조건 (ACTIVE 계열만) | `log_manager.c:10294` `log_check_ha_delay_info_execute` |
| producer 데몬 본체 + END_OF_LOG 재시도 | `log_manager.c:11069` `cdc_loginfo_producer_execute`, `:10695` |
| 북마크 검증 | `log_manager.c:14494` `cdc_validate_lsa`, `:14395` `cdc_check_lsa_range` |
| TRAN_USER 탐색 (풀스캔/assert 지뢰) | `log_manager.c:13583` `cdc_find_user`, `:13636` assert |
| 유저 필터 | `log_manager.c:10740` `cdc_is_filtered_user` 호출부 |
| 아카이브 보존 보호 (휘발성) | `log_manager.c:14071` `cdc_min_log_pageid_to_keep` |
| HA 상태 전이 (cdc 호출 전무) | `src/connection/server_support.c:1860` `css_change_ha_server_state` |
| standby 클라이언트 허용 정책 | `server_support.c:1744` `css_check_ha_server_state_for_client` |
| supplemental log 생성 게이트 (HA 무관) | `src/storage/heap_file.c:2773` `check_supplemental_log` |
| 클라이언트 API 상태머신/북마크 | `src/api/cubrid_log.c` (`g_next_lsa`, `cubrid_log_finalize:2067`) |
| CDC 데몬 부팅 시 1회 초기화 | `src/transaction/boot_sr.c:2440` `cdc_daemons_init` |

---

## 8. 요약 다이어그램

```
                    CDC가 기대하는 세계                 HA가 만드는 실제 세계
              ┌──────────────────────────┐      ┌─────────────────────────────────┐
 시간 탐색     │ 1초마다 시간 이정표 존재      │  ✗  │ standby 구간엔 이정표 없음          │
 LSA 북마크   │ 로그는 연속·불변             │  ✗  │ 크래시로 꼬리 유실·재사용            │
 유저 필터    │ TRAN_USER = 실제 사용자     │  ✗  │ failover 구간은 applier 계정        │
 상태 관리    │ 서버는 항상 active          │  ✗  │ active↔standby 전이 발생,          │
              │                          │     │ 전이 시 CDC 리셋 훅 없음             │
              └──────────────────────────┘      └─────────────────────────────────┘
```

**근본 원인**: CDC의 진행 위치·시간 탐색·유저 귀속이 모두 "단일 active 노드의
로컬 로그"에 결박되어 있고, HA 역할 전이 시 이를 복구하거나 거부하는 로직이
서버·클라이언트 어디에도 없다.
