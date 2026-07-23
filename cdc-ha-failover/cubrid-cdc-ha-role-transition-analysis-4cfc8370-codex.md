# CUBRID CDC의 HA 역할 전환 장애 분석과 개선 제안

- 작성일: 2026-07-22
- 작성자: Codex
- 분석 대상: CUBRID `develop-2`
- 기준 커밋: `4cfc8370edc030fb69433702428916f1c90dc780`
- 분석 범위: CDC client API, CDC server session/producer, connection worker, HA log applier, supplemental log
- 분석 성격: 소스 코드와 관련 JIRA 이력을 바탕으로 한 정적 분석

> 이 문서는 다음 장애를 쉽게 설명하고, 단기 복구책과 근본 해결 방향을 제안하기 위해 작성했다.
>
> **ACTIVE였던 서버 A가 장애로 내려간 뒤 STANDBY로 복귀하고, 나중에 다시 ACTIVE가 되었을 때
> CDC가 더 이상 정상적으로 동작하지 않는 문제**

## 한 문장 결론

현재 CUBRID CDC는 **한 서버의 물리 WAL을 그 서버의 LSA로 읽는 단일 노드 기능**에 가깝지만,
HA는 장애와 역할 전환 과정에서 연결 서버와 WAL의 출처를 바꾼다. 그런데 CDC에는
**HA 노드, promotion 세대, 원본 트랜잭션을 식별하는 정보와 자동 복구 절차가 없기 때문에**
연결 단절, 재접속 실패, LSA 오류, 무한 대기, 데이터 누락 또는 중복이 발생할 수 있다.

즉, 이 문제는 재접속 코드 한 군데만 고쳐서 끝나는 버그가 아니다. CDC의 물리 노드 중심 설계와
HA의 논리 서비스 중심 동작이 충돌하는 구조적인 문제다.

---

## 1. 문제 상황을 먼저 쉽게 이해하기

두 개의 HA 서버가 있다고 하자.

- A: 최초 ACTIVE 서버
- B: 최초 STANDBY 서버
- CDC consumer: WAL을 읽어 외부 시스템으로 변경 데이터를 전달하는 프로그램

문제 시나리오는 다음과 같다.

```text
1. A ACTIVE, B STANDBY
   CDC는 A에 연결되어 A의 LSA를 저장한다.

2. A 장애
   B가 ACTIVE로 승격된다.
   CDC의 A 연결은 끊어진다.

3. B에서 새 트랜잭션 발생
   B는 자기 WAL과 자기 LSA를 사용한다.

4. A 재기동
   A는 STANDBY가 되어 B의 변경을 받아 자기 DB에 다시 적용한다.

5. failback
   A가 다시 ACTIVE가 된다.
   CDC는 A에 다시 연결하거나, B에서 쓰던 위치를 A에 제출하려고 한다.

6. 장애
   재접속이 거절되거나, LSA가 유효하지 않거나, 데이터가 나오지 않거나,
   일부 변경이 누락·중복될 수 있다.
```

핵심은 A와 B의 LSA가 같은 좌표계가 아니라는 점이다.

```text
A의 LSA 1000  !=  B의 LSA 1000
```

숫자가 같더라도 서로 다른 WAL의 서로 다른 record를 뜻할 수 있다. 그런데 현재 공개 CDC API는
이 둘을 구분할 추가 정보를 갖고 있지 않다.

---

## 2. 먼저 알아야 할 용어

### CDC

CDC(Change Data Capture)는 DB에서 발생한 INSERT, UPDATE, DELETE 같은 변경을 읽어 외부 시스템으로
전달하는 기능이다. CUBRID CDC는 WAL과 supplemental log를 해석해 변경 정보를 만든다.

### WAL

WAL(Write-Ahead Log)은 DB page를 실제로 바꾸기 전에 변경 내역을 먼저 기록하는 로그다. 장애 복구와
HA 복제에 사용된다.

### LSA

LSA(Log Sequence Address)는 WAL 안의 위치다. CUBRID의 실질적인 LSA는 `pageid`와 `offset`으로
구성된다. CDC API는 이를 `uint64_t` 값으로 포장해 resume 위치로 사용한다.

LSA는 전 세계적으로 유일한 event ID가 아니다. **한 데이터베이스 인스턴스의 물리 로그 안에서만
의미 있는 주소**다.

### ACTIVE와 STANDBY

- ACTIVE: 사용자 트랜잭션을 처리하는 현재 주 서버
- STANDBY: ACTIVE의 replication log를 받아 변경을 적용하는 대기 서버
- `TO_BE_STANDBY`: ACTIVE에서 STANDBY로 내려가기 위한 중간 상태

### supplemental log

일반 복구 WAL만으로는 CDC가 테이블명, 사용자, 변경 종류 같은 논리 정보를 충분히 만들기 어렵다.
이를 보완하기 위해 CDC용 추가 정보를 WAL에 기록한 것이 supplemental log다.

---

## 3. 현재 CDC 구조

### 3.1 서버에는 사실상 CDC session 하나가 있다

서버의 CDC 전역 상태 `cdc_Gl`에는 다음이 들어 있다.

- CDC client connection 하나
- producer 하나
- consumer 하나
- producer가 채우고 consumer가 읽는 queue 하나
- 다음 추출 위치인 `next_extraction_lsa`

근거:

- `src/transaction/log_manager.c:186`
- `src/transaction/log_impl.h:787-884`

따라서 현재 구조는 여러 HA node를 하나의 논리 CDC cluster로 묶는 구조가 아니다. 각각의 서버가
자기 WAL을 읽는 독립적인 CDC server이며, 각 서버 안에서도 singleton session 성격이 강하다.

### 3.2 client는 특정 host와 port에 직접 연결한다

공개 API는 다음과 같다.

```c
int cubrid_log_connect_server (char *host, int port, char *dbname,
                               char *id, char *password);
int cubrid_log_extract (uint64_t *lsa, CUBRID_LOG_ITEM **items, int *size);
```

근거:

- `src/api/cubrid_log.h:143-151`
- `src/connection/connection_cl.cpp:929-934`

이 API에는 다음 기능이 없다.

- 현재 ACTIVE 서버 탐색
- 서버가 ACTIVE인지 확인하는 handshake
- role 변경 notification
- 다른 node로 redirect
- failover epoch 확인
- cursor가 어느 node에서 발급됐는지 확인

### 3.3 CDC cursor는 `uint64_t LSA`뿐이다

CDC가 재시작할 때 저장하는 위치에는 다음 정보가 없다.

| 필요한 식별 정보 | 현재 cursor에 존재하는가 |
|---|---:|
| WAL page/offset | 예 |
| database UUID | 아니오 |
| 원본 HA node | 아니오 |
| promotion/failover 세대 | 아니오 |
| WAL timeline | 아니오 |
| 원본 transaction ID | 아니오 |
| 안정적인 logical event ID | 아니오 |

이 제약 때문에 같은 노드의 같은 WAL에서는 resume할 수 있어도, HA node를 넘나드는 resume은 안전하게
정의할 수 없다.

---

## 4. 장애 원인 1: 역할 하강 과정에서 CDC 연결이 끊어진다

HA 서버가 `HA_SERVER_STATE_TO_BE_STANDBY`에 들어가면 connection worker는 안전하게 닫을 수 있는
connection context를 찾아 종료한다.

근거:

- `src/connection/connection_worker.cpp:624-645`
- 실제 socket 정리 경로: `src/connection/connection_worker.cpp:560-565`

CDC raw-log connection은 일반적인 사용자 transaction을 수행하는 연결이 아니다. 따라서 worker가
사용 중이지 않은 시점에는 종료 조건을 만족하기 쉽다. 진행 중인 요청이 있으면 즉시가 아니라 안전한
시점까지 늦어질 수 있지만, 역할 하강 과정에서 기존 CDC 연결의 생존을 보장하는 설계는 아니다.

이 사실은 다음 두 상황을 모두 설명한다.

1. A가 장애로 죽을 때 CDC 연결이 끊긴다.
2. B 또는 복귀한 A가 ACTIVE에서 STANDBY로 내려갈 때 CDC 연결이 다시 끊긴다.

문제는 연결이 끊기는 것 자체보다 **그다음 자동 복구 계약이 없다는 점**이다.

---

## 5. 장애 원인 2: client API가 자동 재접속 상태 머신을 제공하지 않는다

CDC client library는 전역 stage를 사용한다.

```text
configuration -> connection/preparation -> extraction -> finalize
```

근거:

- 전역 상태: `src/api/cubrid_log.c:86-127`
- 연결: `src/api/cubrid_log.c:928-997`
- 내부 extraction: `src/api/cubrid_log.c:1162-1202`
- 공개 extraction: `src/api/cubrid_log.c:1809-1868`
- 전역 초기화: `src/api/cubrid_log.c:2035-2075`
- finalize: `src/api/cubrid_log.c:2084-2119`

추출 중 socket이 끊기면 `CUBRID_LOG_FAILED_CONNECT`가 반환된다. 그러나 library가 자동으로 다음 작업을
하지는 않는다.

1. 죽은 connection 폐기
2. stage를 재연결 가능한 상태로 변경
3. 새 ACTIVE 검색
4. 설정을 유지한 채 재접속
5. 저장한 cursor의 출처 검증
6. extraction 재개

호출자가 extraction 실패 직후 `cubrid_log_connect_server()`를 다시 부르면 기존 stage가 남아 있어
`CUBRID_LOG_INVALID_FUNC_CALL_STAGE`가 발생할 수 있다.

정상적으로 초기화하려면 `cubrid_log_finalize()`를 호출해야 한다. 하지만 finalize 과정은 timeout,
filter, 다음 LSA를 포함한 전역 설정도 초기화한다. 결국 application이 설정 저장과 복구 절차를 모두
직접 구현해야 한다.

현재 CTP의 `cdc_test_helper`도 서버에 한 번 연결한 뒤 extraction loop를 수행하고, extraction 오류가
나면 종료한다. failover 후 active discovery와 재접속을 검증하는 기본 흐름은 없다.

---

## 6. 장애 원인 3: 다른 HA node의 LSA를 안전하게 이어 읽을 수 없다

서버는 client가 전달한 LSA를 `cdc_validate_lsa()`로 검사한다.

근거:

- 호출 지점: `src/communication/network_interface_sr.cpp:11606-11625`
- 검증 구현: `src/transaction/log_manager.c:14494-14553`

검증 내용은 대략 다음과 같다.

1. 이 서버가 현재 보유한 log 범위 안인가?
2. 해당 page를 읽을 수 있는가?
3. page 안에 정확한 offset의 record가 있는가?

하지만 다음은 검사하지 못한다.

- 이 LSA를 발급한 node가 현재 node와 같은가?
- DB 생성 세대가 같은가?
- failover 전후 같은 WAL timeline인가?
- 같은 논리 transaction history인가?

따라서 B에서 받은 LSA를 A에 전달하면 다음 결과가 가능하다.

### 경우 A: 명확한 오류

B의 cursor가 A의 현재 log 범위를 벗어나면 `CUBRID_LOG_INVALID_LSA`가 발생한다.

### 경우 B: 계속 기다림

CDC producer는 `next_extraction_lsa >= nxio_lsa`이면 아직 새 로그가 오지 않았다고 보고 잠시 기다린다.

근거: `src/transaction/log_manager.c:11130-11143`

다른 node의 cursor가 A의 현재 WAL보다 앞서 있으면 잘못된 cursor를 “미래에 생성될 정상 위치”로
오인할 수 있다. 이 경우 extraction timeout만 반복되며 CDC가 멈춘 것처럼 보인다.

### 경우 C: 숫자상 우연히 유효함

가장 위험한 경우다. B의 pageid/offset이 A에도 존재하면 검증을 통과할 수 있지만, 실제로는 다른
record를 가리킬 수 있다. 명시적인 오류 없이 중복, 누락 또는 잘못된 시작 위치가 만들어질 수 있다.

그래서 단순히 LSA 범위 검사만 완화하거나 “일단 존재하면 받자”는 수정은 안전하지 않다.

---

## 7. 장애 원인 4: HA 적용 과정에서 원본 CDC 의미가 보존되지 않는다

이 부분이 장기적으로 가장 중요한 문제다.

### 7.1 HA는 원본 supplemental record를 CDC stream으로 그대로 복제하지 않는다

log applier는 원본 WAL에서 주로 다음 replication record를 읽는다.

- `LOG_REPLICATION_DATA`
- `LOG_REPLICATION_STATEMENT`

근거:

- `src/transaction/log_applier.c:6081`
- `src/transaction/log_applier.c:6174-6200`

원본 서버에 기록된 `LOG_SUPPLEMENTAL_INFO`를 그대로 standby CDC record로 전달하는 case는 없다.
대신 log applier가 변경 내용을 해석해 standby DB에서 INSERT/UPDATE/DELETE를 다시 수행한다.

### 7.2 standby에서는 새로운 로컬 transaction과 WAL이 만들어진다

applylogdb는 target server에 `DB_CLIENT_TYPE_LOG_APPLIER`로 접속하며 DB 사용자는 `DBA`다.

근거:

- `src/executables/util_cs.c:3437-3443`
- `src/executables/util_cs.c:3498-3507`

standby에서 heap 변경이 실행되면 일반 변경 경로가 target의 새 supplemental log를 기록한다.

근거:

- `src/storage/heap_file.c:2773-2787`
- `src/storage/heap_file.c:23055-23067`
- transaction user 기록: `src/transaction/log_manager.c:4647-4663`, `4779-4790`

그 결과 B에서 발생한 변경이 A에 적용되었을 때 CDC 관점은 다음처럼 달라진다.

| CDC 속성 | B의 원본 | A STANDBY에 적용된 결과 |
|---|---|---|
| WAL 위치 | B의 LSA | A의 새 로컬 LSA |
| transaction ID | B의 trid | A의 새 trid |
| DB 사용자 | 실제 application user | `DBA` |
| commit 시각 | 원본 commit 시각 | target 적용 transaction 시각 |
| 원본 node/timeline | B | 보존 정보 없음 |

### 7.3 사용자 filter로 조용히 누락될 수 있다

CDC가 특정 application user만 추출하도록 설정되어 있다고 하자.

```text
원본 B: app_user가 UPDATE 수행
HA 적용 A: DBA가 UPDATE를 재수행한 것으로 기록
CDC filter: app_user만 허용
결과: A에서 재생성된 변경이 filter에 걸려 사라질 수 있음
```

이 경우 에러 메시지가 아니라 데이터 누락으로 보일 수 있어 더 위험하다.

### 7.4 exactly-once를 판단할 event identity가 없다

동일한 논리 변경이 B의 원본 WAL과 A의 재적용 WAL 양쪽에 존재할 수 있지만 둘을 같은 event로
연결하는 안정적인 ID가 없다. CDC가 ACTIVE node를 따라 이동하면 같은 변경을 두 번 내보냈는지,
아예 빠뜨렸는지 판단하기 어렵다.

---

## 8. 추가로 장애를 악화시키는 취약 지점

### 8.1 STANDBY에서 producer를 깨우는 전제가 약하다

CDC producer는 log 끝에 도달하면 `nxio_lsa`가 앞으로 이동하기를 기다린다. 코드 주석은 HA dummy
log가 약 1초마다 생겨 producer를 깨우는 흐름을 전제로 한다.

그러나 HA delay timer log는 다음 상태에서만 기록된다.

- `HA_SERVER_STATE_ACTIVE`
- `HA_SERVER_STATE_TO_BE_STANDBY`

순수 STANDBY에서는 기록되지 않는다.

근거: `src/transaction/log_manager.c:10295-10325`

STANDBY가 실제 replication DML을 적용하고 있으면 WAL이 진행하므로 producer가 다시 움직일 수 있다.
반대로 적용할 변경이 없다면 timeout을 반복할 수 있다. 이것만으로 재승격 후의 영구 장애를 모두
설명하지는 못하지만, 잘못된 cross-node cursor와 결합하면 “연결은 살아 있는데 데이터가 영원히
안 나오는” 현상을 만들 수 있다.

### 8.2 timestamp 기반 재시작도 정확한 cross-node 복구점이 아니다

LSA가 무효라면 마지막 처리 시각으로 `cubrid_log_find_lsa()`를 다시 호출하는 방법을 생각할 수 있다.
하지만 `cdc_find_lsa()`가 시간 이정표로 인정하는 record는 다음 두 종류다.

- `LOG_COMMIT` 또는 `LOG_ABORT`의 완료 시각
- `LOG_DUMMY_HA_SERVER_STATE`의 기록 시각

근거:

- 시간→LSA 탐색: `src/transaction/log_manager.c:14210-14315`
- 실제 시간 record 판별: `src/transaction/log_manager.c:14821-14903`

STANDBY에서는 주기적인 HA dummy record가 없고, replication으로 생긴 transaction의 commit 시각은
원본 B의 commit 시각이 아니라 A에서 적용된 시각이다. 따라서 같은 timestamp를 A와 B에 주더라도
동일한 논리 변경 경계가 나온다고 보장할 수 없다.

변경이 전혀 없는 시간 공백이라면 다음 commit을 고르는 것 자체는 문제가 아닐 수 있다. 하지만
failover 전후의 원본 순서, apply 지연, 초 단위로 겹치는 transaction을 고려하면 timestamp는 정확한
checkpoint 변환 수단이 아니다. `ER_CDC_ADJUSTED_LSA` 또는 `ER_CDC_LSA_NOT_FOUND`도 발생할 수 있다.

따라서 timestamp fallback을 제공하더라도 반드시 다음 조건이 붙어야 한다.

- 요청 시각보다 앞선 overlap 구간부터 다시 읽기
- 중복 가능성을 API에 명시
- downstream stable event ID 기반 deduplication

### 8.3 CDC의 archive 보존 위치는 session 메모리에 의존한다

CDC가 아직 읽지 않은 archive를 지우지 않도록 하는 기준은
`cdc_Gl.consumer.start_lsa.pageid`다.

근거:

- CDC 보존 page 반환: `src/transaction/log_manager.c:14070-14074`
- archive 삭제 제한에 반영: `src/transaction/log_page_buffer.c:6112-6135`, `6316-6324`

이 위치는 CDC session의 runtime 상태다. 서버가 죽거나 session이 사라지면 외부 consumer가 저장한
checkpoint를 서버가 계속 보호해 주지 못한다. A가 오랫동안 장애 또는 STANDBY 상태에 있고 archive
rotation이 진행되면, A가 다시 ACTIVE가 되었을 때 필요한 옛 LSA가 이미 보존 범위 밖일 수 있다.

이 경우 `cdc_validate_lsa()`는 정상적으로 invalid LSA를 반환하지만, application 관점에서는
“이전에 정상 저장한 checkpoint가 failback 후 더 이상 동작하지 않는다”가 된다.

따라서 HA CDC를 지원하려면 다음 중 하나가 필요하다.

- acknowledged cursor와 retention lease를 서버에 영속화
- 외부 CDC coordinator가 각 node에 필요한 최소 WAL 위치를 등록
- 보존 기한을 넘긴 cursor에는 별도의 `CURSOR_EXPIRED` 오류와 snapshot 재동기화 절차 제공

단순히 `log_max_archives`를 크게 잡는 방법은 단기 완화일 뿐 correctness 보장은 아니다.

### 8.4 transaction user 탐색이 긴 scan 또는 debug assert로 이어질 가능성

CDC가 현재 위치 앞쪽에서 `LOG_SUPPLEMENT_TRAN_USER`를 찾지 못하면 `cdc_find_user()`가 해당 trid의
사용자 record를 찾기 위해 현재 `nxio_lsa`까지 앞으로 scan한다.

근거: `src/transaction/log_manager.c:13583-13653`

함수 주석도 abort되었거나 아직 active인 transaction에는 찾을 user record가 없을 수 있다고 설명한다.
그런데 commit을 만났는데 user record가 없으면 `assert`가 있고, 끝까지 못 찾으면 `ER_FAILED`를
반환한다. 크래시 경계나 잘린 과거 log에서 이런 조건이 만들어지면 긴 scan, 반복 실패 또는 debug
build assert로 증상이 나타날 가능성이 있다.

이 경로가 보고된 장애의 직접 원인이라고 정적 분석만으로 확정할 수는 없다. 그러나 failback 재현에서
CPU 사용량 증가나 extraction 지연이 보이면 반드시 추적해야 할 2차 위험이다. 못 찾은 trid를 반복
scan하지 않도록 negative cache에 넣고, 정상적으로 가능한 불완전 transaction을 assert 대신 명시적인
ignore/error 정책으로 처리하는 방안을 검토할 필요가 있다.

---

## 9. 증상별 원인 지도

| 관찰되는 증상 | 가능성이 높은 원인 | 확인할 정보 |
|---|---|---|
| `CUBRID_LOG_FAILED_CONNECT` | 장애 또는 역할 하강으로 socket 종료 | HA state 변경 시각, server error log |
| 재연결 시 `CUBRID_LOG_INVALID_FUNC_CALL_STAGE` | extraction 실패 뒤 client stage 미초기화 | finalize 호출 여부 |
| `ER_CDC_NOT_AVAILABLE` | stale singleton session 또는 supplemental log 비활성 | 서버 버전, CBRD-26911 포함 여부 |
| `CUBRID_LOG_INVALID_LSA` | 다른 node/timeline의 LSA 제출 | cursor 발급 node와 현재 접속 node |
| 오래 중단한 뒤 `CUBRID_LOG_INVALID_LSA` | CDC session 부재 중 필요한 archive 삭제 | archive 범위와 마지막 checkpoint page |
| `CUBRID_LOG_EXTRACTION_TIMEOUT` 반복 | cursor가 local log tail보다 앞섬, STANDBY wake-up 부족 | cursor와 `nxio_lsa` 비교 |
| 시간 기반 재시작 위치가 예상과 다름 | STANDBY dummy log 부재, source/apply commit 시각 차이 | 요청 시각과 반환 시각, `ADJUSTED_LSA` |
| failover 구간의 일부 사용자 데이터만 누락 | applylogdb의 `DBA` identity와 user filter 충돌 | CDC user filter, 추출 event user |
| 재승격 후 CPU 증가 또는 긴 scan | user가 없는 trid에 대한 `cdc_find_user()` 전방 scan | CDC debug trace, 해당 trid와 commit/abort |
| 재접속 후 일부 record 누락 | 구버전 producer `process_lsa` reset 결함 | CBRD-26994 포함 여부 |
| 중복과 누락이 함께 나타남 | 노드 간 stable logical event ID 부재 | A/B 양쪽 cursor와 downstream checkpoint |

---

## 10. 최근 수정된 관련 문제

관련 JIRA와 커밋 이력을 현재 HEAD와 대조했다.

### 10.1 CBRD-26911: 비정상 client 종료 후 재접속 문제

기존에는 CDC client가 `END_SESSION` 없이 비정상 종료하면 `cdc_Gl.conn.fd`가 남아 새 client를
`ER_CDC_NOT_AVAILABLE`로 거절할 수 있었다.

현재 코드는 새 `START_SESSION`이 들어오면 이전 connection과 client ID를 확인하고 최신 연결이
takeover하도록 보완되어 있다.

근거: `src/communication/network_interface_sr.cpp:11371-11435`

- 수정 커밋: `a25a6b6d4`
- 현재 기준 커밋 포함 여부: 포함됨

### 10.2 CBRD-26994: resume 후 record 누락 문제

queue를 비운 뒤 consumer가 저장한 LSA로 돌아가도 producer의 로컬 `process_lsa`가 이전의 더 앞선
위치를 유지할 수 있었다. 그러면 queue에 있었지만 아직 consumer가 받지 못한 record를 건너뛸 수 있다.

현재는 queue 초기화 때 `is_reset_process_lsa`를 설정하고 producer가 새
`next_extraction_lsa`를 채택하도록 보완되어 있다.

근거:

- `src/transaction/log_impl.h:823-824`
- `src/transaction/log_manager.c:11150-11169`
- queue reset 지점: `src/transaction/log_manager.c:14626`, `15093`, `15132`

- 수정 커밋: `af389ac21`
- 현재 기준 커밋 포함 여부: 포함됨

### 10.3 두 수정으로 해결되지 않는 것

두 수정은 같은 물리 서버에서의 session takeover와 resume 정확도를 높이는 중요한 수정이다. 그러나
다음 문제는 그대로 남아 있다.

- 현재 ACTIVE node 탐색
- HA role handshake와 fencing
- node/timeline이 포함된 cursor
- cross-node checkpoint 변환
- 원본 user, trid, commit metadata 보존
- stable logical event ID
- 자동 reconnect 상태 머신

따라서 구버전이라면 두 수정을 우선 backport해야 하지만, 이를 “HA CDC 지원 완료”로 판단하면 안 된다.

---

## 11. 근본 원인 트리

```text
HA 역할 전환 후 CDC 중단/오동작
|
+-- 전송 계층
|   +-- role 하강 과정에서 기존 socket 종료
|   +-- client가 active discovery와 자동 reconnect를 하지 않음
|
+-- session 계층
|   +-- 서버에 singleton 성격의 CDC session
|   +-- connection close와 CDC owner 정리가 완전히 결합되지 않음
|   +-- 구버전에서는 stale owner가 새 연결을 거부
|
+-- cursor 계층
|   +-- cursor가 uint64_t LSA뿐임
|   +-- database/node/timeline/promotion epoch가 없음
|   +-- 다른 node의 LSA를 안전하게 reject 또는 변환할 수 없음
|
+-- 데이터 의미 계층
|   +-- source supplemental metadata를 그대로 복제하지 않음
|   +-- standby가 local LSA/trid/user로 변경을 재기록
|   +-- 원본 user가 DBA로 바뀔 수 있음
|   +-- 동일 논리 event를 식별할 ID가 없음
|
+-- 검증 계층
    +-- 실제 HA failover/failback CDC test 부족
    +-- server restart test도 reconnect/resume 연속성을 충분히 검증하지 않음
```

---

## 12. 해결 방향

해결은 운영 완화, 단기 코드 보강, 근본 구조 개선의 세 단계로 나누는 것이 현실적이다.

### 12.1 P0: 즉시 가능한 운영 완화와 진단

### 운영 버전 확인

먼저 운영 바이너리에 다음 수정이 포함되어 있는지 확인한다.

- CBRD-26911 / `a25a6b6d4`
- CBRD-26994 / `af389ac21`

포함되어 있지 않다면 같은 노드 재접속도 실패하거나 resume 시 실제 누락이 생길 수 있으므로 우선
backport해야 한다.

### 기존 API의 지원 범위를 제한한다

현재 `uint64_t LSA` 기반 API는 다음 조건에서만 resume을 허용하는 편이 안전하다.

> 같은 database generation, 같은 물리 node, 같은 WAL timeline으로 다시 연결하는 경우

다른 ACTIVE node를 따라가면서 기존 LSA를 그대로 제출하는 것은 금지해야 한다.

### 안전한 임시 운영 방식

CDC를 특정 물리 node에 고정하고, 그 node가 다시 ACTIVE가 된 뒤 다음 순서로 재시작한다.

```text
extract 오류 감지
  -> cubrid_log_finalize()
  -> 대상 node가 ACTIVE인지 확인
  -> timeout/filter 등 모든 설정 재적용
  -> 같은 node에서 저장한 LSA로 reconnect/resume
```

이 방식은 cross-node LSA 혼용을 피하지만 다음 한계가 있다.

- 해당 node가 복귀할 때까지 CDC가 중단됨
- STANDBY catch-up에서 원본 user/trid가 보존되지 않음
- 장애 직전 checkpoint 경계에서 중복 가능

### ACTIVE를 따라가야 한다면

현재 API로는 정확한 cross-node resume이 불가능하다. 부득이하게 ACTIVE를 따라가야 한다면:

- timestamp보다 조금 앞선 구간부터 다시 읽기
- downstream에서 PK와 event 내용으로 멱등 처리
- 중복을 허용하는 at-least-once 운영

을 사용해야 한다. timestamp는 초 단위 충돌과 clock/commit ordering 문제가 있으므로 정확한 cursor가
아니며, 이는 임시 우회책일 뿐이다.

### 장애 시 수집할 정보

`cdc_logging_debug=y`를 제한적으로 활성화하고 다음을 같은 시간축으로 수집한다.

- HA state 변화: ACTIVE, TO_BE_STANDBY, STANDBY
- CDC client 반환 코드
- CDC server error log
- 저장된 LSA의 pageid/offset
- LSA를 발급한 node
- 재접속한 node
- 각 node의 `db_creation`, `ha_promotion_time`, `nxio_lsa`
- CDC user/table filter

민감한 데이터와 로그 증가량을 고려해 재현 구간에만 debug logging을 사용하는 것이 좋다.

---

### 12.2 P1: 낮은 위험으로 가능한 코드 보강

### A. connection 종료와 CDC session 정리를 결합한다

connection worker가 socket을 닫을 때 CDC에 다음과 같은 명시적인 hook을 호출한다.

```cpp
cdc_session_on_connection_closed (fd, client_id, generation);
```

중요한 점은 `fd`만 비교하면 안 된다는 것이다. OS가 fd 번호를 재사용할 수 있기 때문이다.
`client_id` 또는 증가하는 connection generation까지 함께 비교해 이전 connection의 늦은 teardown이
새 connection owner를 지우지 못하게 해야 한다.

### B. role 변경을 일반 network error와 구분한다

서버가 ACTIVE에서 내려갈 때 CDC session을 fencing하고 다음과 같은 명시적 오류를 반환한다.

```text
ER_CDC_HA_ROLE_CHANGED
  role = TO_BE_STANDBY
  node_id = A
  timeline_epoch = 17
```

그러면 client는 일반적인 일시적 socket 오류와 role 전환을 구분할 수 있다.

### C. STANDBY 접속을 기본적으로 거부한다

현재 `scdc_start_session()`은 `supplemental_log` 활성 여부는 확인하지만 HA role을 명확히 제한하지 않는다.

근거: `src/communication/network_interface_sr.cpp:11371-11435`

초기 단계에서는 CDC session을 ACTIVE에서만 허용하는 것이 안전하다. STANDBY 읽기가 필요하다면
`local catch-up diagnostic mode`처럼 별도 옵션으로 분리하고 HA 연속성 보장 대상이 아님을 명시해야 한다.

### D. client에 강제 reset/reconnect API를 제공한다

서버와 통신할 수 없어도 로컬 connection과 stage만 정리할 수 있어야 한다.

예시:

```c
int cubrid_log_abort_connection (void);
int cubrid_log_reconnect_server (const CUBRID_LOG_ENDPOINTS *endpoints,
                                 const CUBRID_LOG_CURSOR *cursor);
```

reconnect 동안 다음 설정은 유지해야 한다.

- table/user filter
- extraction timeout
- max log item
- last acknowledged cursor

기존 `finalize()`처럼 모든 설정을 지우는 API만 있으면 HA client 구현이 불필요하게 복잡해진다.

### E. producer가 잘못된 미래 cursor를 무한 대기하지 않게 한다

현재 node/timeline과 맞지 않거나 정상 upper bound를 벗어난 cursor는 extraction timeout으로 처리하지 말고
명시적인 cursor mismatch 오류로 반환해야 한다.

```text
ER_CDC_CURSOR_SOURCE_MISMATCH
ER_CDC_CURSOR_TIMELINE_MISMATCH
ER_CDC_CURSOR_AHEAD_OF_VALID_LOG
```

---

### 12.3 P2: HA-aware cursor 도입

기존 `uint64_t`만으로는 HA correctness를 만들 수 없다. versioned cursor가 필요하다.

개념 예시는 다음과 같다.

```cpp
struct CDC_CURSOR_V2
{
  uint32_t version;
  DB_UUID database_uuid;
  NODE_ID origin_node;
  uint64_t timeline_epoch;
  LOG_LSA local_lsa;
};
```

CDC session handshake에서 서버는 최소한 다음 정보를 반환해야 한다.

- protocol version
- database UUID 또는 안정적인 DB generation ID
- node ID
- 현재 HA role
- promotion/timeline epoch
- 사용 가능한 WAL lower bound와 upper bound

### cursor 검증 규칙

| 조건 | 처리 |
|---|---|
| DB UUID 다름 | 즉시 거절 |
| node와 timeline 동일 | local LSA resume 허용 |
| node 동일, timeline 다름 | 명시적 rebase 필요 오류 |
| node 다름 | mapping 없이는 거절 |
| LSA가 archive 보존 범위보다 과거 | expired cursor 오류 |
| LSA가 현재 valid upper bound보다 미래 | timeout이 아니라 mismatch 오류 |

구 API는 호환성을 위해 유지할 수 있지만 “single-node cursor”라고 명시해야 한다. V2 API를 별도로 만들어
기존 application이 조용히 의미가 바뀌지 않게 하는 편이 안전하다.

---

### 12.4 P3: 진정한 HA CDC를 위한 원본 event identity 보존

권장하는 근본 방향은 **HA apply 과정에 원본 CDC metadata를 전달하고 target WAL에 원자적으로 남기는 것**이다.

### 전달해야 할 정보

- origin database UUID
- origin node와 timeline epoch
- source replication 또는 commit LSA
- source transaction ID
- 원본 DB user
- 원본 commit timestamp
- transaction 안에서의 event sequence

### target에서의 기록 방법

standby가 replication DML을 적용할 때 같은 target transaction 안에 다음과 같은 별도 supplemental record를
기록한다.

```text
LOG_SUPPLEMENTAL_CDC_ORIGIN
  origin_db_uuid
  origin_timeline
  origin_commit_lsa
  origin_trid
  origin_user
  origin_commit_time
  event_sequence
```

이 metadata는 실제 row 변경과 같은 transaction으로 commit되어야 한다. 변경 적용 전에 밖으로 보이거나,
변경은 abort됐는데 origin record만 남아서는 안 된다.

### CDC event가 반환할 두 종류의 위치

```text
origin_event_id
  -> HA cluster 전체에서 중복 제거에 사용

local_resume_cursor
  -> 현재 연결된 node의 WAL을 다시 읽는 데 사용
```

예를 들면 stable event ID는 다음 조합을 기반으로 만들 수 있다.

```text
(origin_db_uuid, origin_timeline, origin_commit_lsa,
 origin_trid, event_sequence)
```

hash만 반환하더라도 원본 필드는 내부적으로 보존해야 충돌과 장애 분석이 가능하다.

### 왜 이것이 필요한가

이 정보가 있으면 B에서 발생한 event를 A가 재적용하더라도 다음을 판단할 수 있다.

- A에서 본 event가 B의 어떤 원본 event인가?
- 이미 downstream에 전달한 event인가?
- 원래 변경 사용자는 누구인가?
- transaction boundary는 어디인가?
- failback 후 어디부터 다시 읽어야 하는가?

---

## 13. 대안 설계와 trade-off

### 대안 A: target WAL에 origin metadata 기록

앞 절에서 제안한 방식이다.

장점:

- 승격된 어느 node에서도 자기 로컬 WAL을 읽을 수 있음
- 기존 CDC producer 구조를 점진적으로 확장 가능
- source event와 target apply event를 연결 가능

단점:

- replication payload와 apply protocol 변경 필요
- WAL 크기 증가
- transaction atomicity와 version compatibility 설계 필요

### 대안 B: CDC service가 원본 HA log를 직접 이어 붙여 읽음

CDC를 각 DB server 내부 기능이 아니라 HA log archive를 읽는 별도 cluster service로 만든다.

장점:

- 원본 WAL identity를 그대로 유지할 수 있음
- target 재적용 과정의 DBA/user 왜곡을 피함

단점:

- archive 보존, node별 timeline, 장애 중 접근성 관리가 복잡함
- 별도 서비스 운영과 leader/fencing 필요
- 현재 API와 구조에서 변화 폭이 큼

### 권장 판단

점진적인 CUBRID 코드 개선에는 대안 A가 현실적이다. 다만 장기적으로 다양한 sink와 대규모 CDC를
지원하려면 대안 B 성격의 독립 CDC service도 검토할 가치가 있다.

---

## 14. 하면 안 되는 단순 수정

### 다른 node에서도 숫자상 존재하는 LSA를 허용

같은 pageid/offset이 존재한다고 같은 logical event가 아니다. 조용한 데이터 corruption을 만들 수 있다.

### socket이 끊기면 같은 LSA로 아무 ACTIVE에 자동 재접속

빠르게 복구되는 것처럼 보이지만 cross-node LSA 문제를 숨긴다.

### user filter에서 DBA를 원래 사용자로 추정

여러 원본 사용자가 모두 DBA로 합쳐졌다면 역으로 복원할 수 없다. 원본 metadata를 replication payload에
실어야 한다.

### timeout이면 무조건 최신 LSA로 이동

서비스는 살아나지만 확인하지 못한 event를 버릴 수 있다. cursor를 임의로 앞으로 이동하면 안 된다.

### exactly-once라고 먼저 선언

stable event ID와 downstream checkpoint atomicity 없이 exactly-once를 선언할 수 없다.

---

## 15. 권장 delivery contract

첫 번째 현실적인 목표는 다음이다.

> HA role 전환 중에도 event loss가 없고, 재전송된 event는 stable origin event ID로 제거할 수 있는
> at-least-once CDC

CDC server가 event를 전달한 직후 죽으면 consumer가 event를 처리했는지 서버는 알 수 없다. 따라서
중복 가능성은 본질적으로 존재한다. exactly-once가 필요하면 다음 중 하나가 필요하다.

- downstream write와 checkpoint를 같은 transaction으로 commit
- sink가 `origin_event_id`를 unique key로 사용해 멱등 처리

서버 내부 수정만으로 모든 외부 sink에 exactly-once를 보장하기는 어렵다.

---

## 16. 반드시 추가해야 할 HA 회귀 테스트

### 16.1 기본 failover/failback 시나리오

```text
초기 상태
  A ACTIVE
  B STANDBY
  supplemental_log = 1

1. CDC를 A에 연결
2. app_user_1로 batch S0 입력
3. 일부 event를 소비하고 cursor 저장
4. extraction 중 A를 강제 종료
5. B가 ACTIVE가 될 때까지 대기
6. app_user_2로 batch S1 입력
7. A를 STANDBY로 재기동
8. A가 B를 완전히 따라잡을 때까지 대기
9. B를 내리고 A를 다시 ACTIVE로 승격
10. CDC reconnect/resume
11. app_user_1로 batch S2 입력
12. 모든 event와 metadata 검증
```

### 16.2 필수 검증 항목

- S0, S1, S2의 모든 PK가 존재하는가?
- 누락이 없는가?
- 중복이 있다면 stable event ID로 제거 가능한가?
- transaction boundary가 유지되는가?
- 원본 사용자가 `app_user_1`, `app_user_2`로 보존되는가?
- B의 cursor를 A가 조용히 받아들이지 않는가?
- role 변경 시 명확한 오류가 반환되는가?
- reconnect가 무한 timeout에 빠지지 않는가?
- cursor가 archive 범위를 벗어나면 명확한 expired 오류가 나는가?

### 16.3 통신 단절 지점별 테스트

다음 각 지점에서 socket을 끊어야 한다.

1. extraction 요청 전송 직후
2. metadata 응답 전
3. metadata 수신 후 payload 수신 전
4. payload 수신 후 application checkpoint 저장 전
5. 새 connection이 takeover한 직후 이전 connection teardown

마지막 경우에는 fd 재사용까지 유도해 `(fd, client_id, generation)` 검증이 올바른지 확인해야 한다.

### 16.4 cursor 경계 테스트

- 같은 node, 같은 timeline, 정상 LSA
- 같은 node, 다른 promotion epoch
- 다른 node, 같은 숫자의 LSA
- local `nxio_lsa`보다 앞선 LSA
- archive가 삭제된 오래된 LSA
- crash로 tail 일부가 잘린 LSA
- page는 존재하지만 offset이 다른 LSA

### 16.5 filter와 metadata 테스트

- user filter 없음
- `app_user_1`만 허용
- `app_user_2`만 허용
- DBA 제외
- table filter 변경 전후
- statement replication과 data replication 각각

### 16.6 부하와 보존 테스트

- producer queue full
- prefetch 중 role 변경
- 장시간 consumer 지연
- archive log rotation
- STANDBY에 적용할 DML이 없는 시간대
- failover와 failback 반복
- split-brain 방지/fencing이 작동하는 전환

---

## 17. 구현 순서 제안

### 1차: 현재 장애를 명확하게 실패시키기

1. 운영/지원 branch에 CBRD-26911, CBRD-26994 반영
2. HA end-to-end 재현 test 추가
3. CDC handshake에 HA role 반환
4. STANDBY CDC session 기본 거부
5. role 변경 전용 오류 추가
6. connection close 시 owner/session 정리

이 단계의 목표는 잘못된 LSA로 조용히 동작하는 대신 명확한 오류와 안전한 재시작 경로를 제공하는 것이다.

### 2차: 같은 node 재접속을 완성하기

1. client abort/reset API
2. 설정을 보존하는 reconnect API
3. connection generation 기반 stale teardown 방지
4. queue와 producer cursor reset의 원자성 강화
5. archive 범위와 cursor 만료 오류 구분

### 3차: HA cursor V2

1. DB UUID, node, timeline을 포함한 token 정의
2. protocol version negotiation
3. cursor source validation
4. 기존 `uint64_t` API를 single-node compatibility API로 유지

### 4차: 원본 event identity 보존

1. replication payload 확장
2. log applier의 origin metadata 전달
3. target WAL supplemental record 추가
4. CDC output에 `origin_event_id` 추가
5. sink deduplication contract와 transaction boundary 정의

---

## 18. 완료 기준

다음 조건을 모두 만족해야 “HA에서 CDC가 동작한다”고 말할 수 있다.

- role 변경 중 연결이 끊겨도 client가 원인을 식별할 수 있다.
- 다른 node/timeline의 cursor를 조용히 받아들이지 않는다.
- 같은 node의 재접속에서는 확인하지 않은 event가 누락되지 않는다.
- failover 구간의 변경이 새 ACTIVE에서 추출 가능하다.
- 원본 user와 transaction boundary가 보존된다.
- 중복 event를 안정적으로 식별할 수 있다.
- failover/failback 자동화 test가 반복 실행되어도 결과가 같다.
- archive rotation과 장시간 consumer lag에서도 cursor 만료를 명확히 보고한다.
- delivery guarantee가 API 문서에 명시되어 있다.

---

## 19. 최종 판단

현재 기준 소스에는 같은 서버에서의 CDC 재접속과 resume을 개선한 최근 수정이 들어 있다. 따라서 운영
버전이 오래됐다면 이 두 수정만으로도 일부 “CDC가 다시 안 붙는” 증상은 해소될 수 있다.

하지만 질문의 HA 시나리오 전체를 보면 핵심 문제는 여전히 남아 있다.

1. HA 역할 하강은 기존 CDC connection을 종료할 수 있다.
2. client는 자동 reconnect와 active discovery를 제공하지 않는다.
3. cursor는 node-local 물리 LSA일 뿐이다.
4. HA apply는 원본 CDC metadata를 보존하지 않는다.
5. 원본 event identity가 없어 정확한 deduplication과 cross-node resume이 불가능하다.

따라서 권장 결론은 다음과 같다.

> 단기에는 기존 API를 “같은 물리 node에서만 resume 가능한 CDC”로 안전하게 제한하고 명시적
> role/cursor 오류와 reconnect API를 제공해야 한다. 장기에는 node·timeline이 포함된 cursor와
> HA apply 과정의 원본 event identity 보존을 구현해야 한다.

이 구조가 갖춰지기 전까지 ACTIVE node를 자유롭게 따라가는 CDC에 exactly-once 의미를 부여해서는
안 된다.

---

## 부록 A. 주요 소스 위치

| 주제 | 소스 위치 |
|---|---|
| CDC 공개 API | `src/api/cubrid_log.h:143-151` |
| CDC client 전역 상태 | `src/api/cubrid_log.c:86-127` |
| CDC connect | `src/api/cubrid_log.c:928-997` |
| CDC extract | `src/api/cubrid_log.c:1809-1868` |
| CDC finalize/reset | `src/api/cubrid_log.c:2035-2119` |
| raw log server 연결 | `src/connection/connection_cl.cpp:929-934` |
| HA role 하강 연결 종료 | `src/connection/connection_worker.cpp:624-645` |
| CDC global/session 구조 | `src/transaction/log_impl.h:787-884` |
| CDC session 시작 | `src/communication/network_interface_sr.cpp:11371-11435` |
| restart 후 LSA 검증 호출 | `src/communication/network_interface_sr.cpp:11606-11625` |
| producer log-tail 대기 | `src/transaction/log_manager.c:11130-11143` |
| producer LSA reset 보완 | `src/transaction/log_manager.c:11150-11169` |
| LSA 유효성 검사 | `src/transaction/log_manager.c:14494-14553` |
| HA dummy log 조건 | `src/transaction/log_manager.c:10295-10325` |
| 시간→LSA 탐색 | `src/transaction/log_manager.c:14210-14315`, `14821-14903` |
| transaction user 전방 탐색 | `src/transaction/log_manager.c:13583-13653` |
| CDC archive 보존 기준 | `src/transaction/log_manager.c:14070-14074` |
| archive 삭제 제한 적용 | `src/transaction/log_page_buffer.c:6112-6135`, `6316-6324` |
| HA replication record 처리 | `src/transaction/log_applier.c:6081`, `6174-6200` |
| applylogdb client/user | `src/executables/util_cs.c:3437-3507` |
| heap supplemental log | `src/storage/heap_file.c:2773-2787`, `23055-23067` |

## 부록 B. 분석의 한계

이 보고서는 기준 커밋의 소스 코드, 관련 JIRA와 commit 이력, 기존 CDC test 구조를 분석한 결과다.
실제 장애 환경의 server error log와 CDC 반환 코드를 사용한 동적 재현 결과는 포함하지 않았다.

따라서 “HA에서 CDC가 동작하지 않는다”는 단일 증상이 현장에서 정확히 어느 오류 경로로 나타났는지는
다음 정보가 있으면 더 좁힐 수 있다.

- 최초 CDC 오류 코드
- 장애 전후 연결 node
- 마지막 정상 cursor와 발급 node
- HA state transition 시각
- 운영 바이너리 commit/version
- user/table filter 설정
- `cdc_logging_debug` trace

다만 이러한 실행 정보가 없어도, 현재 API와 WAL/apply 구조만으로 **cross-node HA CDC 연속성을 안전하게
보장할 수 없다는 구조적 결론**은 달라지지 않는다.
