# Pedagogy Research Packet

## Metadata

- **Role:** Pedagogy Architect
- **Topic:** CBRD-27157을 이해하기 위한 server-side loaddb locking, transaction MVCCID self-lock, `BU_LOCK` 입문서 설계
- **Scope digest:** `f07826ef64e37143f055cdf4814be26d965d9bc531421f21439871475722fa5b`
- **Timestamp:** `2026-08-11T15:56:42+09:00`
- **Audience:** C/C++, 자료구조, 운영체제의 기본적인 mutex, SQL `COMMIT`/`ROLLBACK`은 배웠지만 DBMS 내부 잠금은 처음인 컴퓨터공학 2학년
- **Read-only inputs:** frozen `research/scope.md`, `cbrd-27157/loaddb-locking-study/` 전체 학습자료, Korean HTML Book Contract, Quiz/Live Grill contract, OOS normative context

## Findings

### 1. 기존 자료에서 반드시 살릴 것

기존 자료의 가장 좋은 교육적 결정은 문제를 단순히 “lock을 잡느냐”로 보지 않고 다음 네 축으로 나눈 점이다.

1. **Resource:** 무엇을 식별하는 key를 잠그는가?
2. **Owner:** 어느 transaction이 보유하는가?
3. **Observer/Waiter:** 누가 그 상태를 발견하고 기다리는가?
4. **Invariant:** 어떤 관계가 항상 참이어야 하는가?

특히 다음 설명은 새 책의 결론부까지 유지할 가치가 있다.

- `BU_LOCK`과 MVCCID self-lock은 같은 resource가 아니다.
- session transaction과 worker batch transaction은 같은 transaction이 아니다.
- OOS는 새 잠금 정책의 원인이 아니라, 기존에는 드러나지 않던 MVCCID 발급 경로를 연 trigger다.
- source fact, inference, historical intent, design preference를 구분해야 한다.
- `BU_LOCK`은 “모든 다른 transaction을 막는 완전 배타 잠금”이 아니다. 적어도 `BU_LOCK` 및 `SCH_S_LOCK`과의 호환성을 별도로 말해야 한다.

기존 quick reference는 한 번 이해한 독자의 회상 자료로는 유용하다. 다만 첫 학습 자료로는 너무 압축되어 있다. 새 책에서는 마지막 요약표로 재사용하는 편이 맞다.

### 2. 현재 자료가 초급자에게 어려운 근본 이유

현재 lesson은 약 12분 안에 아래 개념을 거의 동시에 요구한다.

- session, connection, thread, worker, batch transaction
- object lock, transaction lock, class OID, MVCCID
- `S_LOCK`, `X_LOCK`, `IS_LOCK`, `IX_LOCK`, `SIX_LOCK`, `SCH_S_LOCK`, `BU_LOCK`
- MVCC, row version, INSID, unique/FK waiter
- observer, rendezvous, invariant, module seam
- OOS lazy creation, file identifier reuse, vacuum
- debug assert, early return, uniform policy

이는 “어려운 내용을 쉽게 설명하지 못한” 문제가 아니다. 선행 개념 여섯 층을 한 lesson에 압축한 **순서 문제**다. 독자는 표의 각 칸은 읽을 수 있어도, 왜 그런 칸이 필요한지는 이해하지 못한다.

가장 큰 점프는 다음 네 곳이다.

1. mutex를 안다고 가정한 직후 곧바로 transaction lock의 resource/owner 모델로 이동한다.
2. `S/X` 호환성도 설명하기 전에 `IS/IX/SIX/BU/SCH_S` 행렬을 보여 준다.
3. transaction의 정체성을 고정하기 전에 `tran_index`, transaction ID, MVCCID, INSID를 사용한다.
4. MVCC version과 unique/FK 충돌 검사를 설명하기 전에 self-lock rendezvous의 결론을 먼저 제시한다.

새 책은 이 네 점프 사이에 각각 한 장씩 다리를 놓아야 한다.

### 3. 기존 자료가 암묵적으로 전제한 배경지식

다음 질문에 답할 수 없는 독자는 현재 lesson의 핵심 문장을 외우게 된다.

- “같은 lock”이라는 말은 같은 함수, 같은 mode, 같은 hash table, 같은 resource key 중 무엇을 뜻하는가?
- mutex의 owner인 thread와 transaction lock의 owner인 transaction은 왜 다른가?
- page latch를 transaction 종료까지 잡아 두면 왜 안 되는가?
- `S`와 `X`가 왜 충돌하며, 기다린 뒤에는 왜 조건을 다시 검사해야 하는가?
- class lock과 instance lock을 함께 두는 이유는 무엇인가?
- intention lock은 실제 row 접근 권한인가, 상위 계층에 하위 잠금 의도를 알리는 표식인가?
- `tran_index`가 같다는 것, MVCCID가 같다는 것, 같은 client에서 실행된다는 것은 각각 무엇이 다른가?
- MVCC가 일반 `SELECT`의 block을 줄이는 것과 unique/FK 검사가 unfinished inserter를 기다리는 것은 왜 모순이 아닌가?
- self-lock의 “self”는 자기 자신을 막는다는 뜻인가?
- `assert`가 사라지면 release build의 의미도 바뀌는가?

이 질문들은 부록으로 미루면 안 된다. CBRD-27157의 인과를 이해하기 위한 본문이다.

### 4. 첫 등장 전에 정의해야 할 용어

아래 표의 “쉬운 첫 정의”는 설명의 출발점이다. 정확한 source-level 세부는 각 전문 장에서 추가한다.

| 용어 | 쉬운 첫 정의 | 주의할 혼동 |
|---|---|---|
| race condition | 실행 순서에 따라 결과가 달라지는 동시성 오류 | 단순히 “두 thread가 동시에 실행됨”과 같지 않다. |
| critical section | 한 번에 제한된 실행자만 들어가야 하는 코드 구간 | transaction 전체와 같지 않다. |
| mutex | 주로 thread 사이에서 짧은 in-memory critical section을 보호하는 동기화 도구 | SQL transaction의 의미나 commit까지의 lifetime이 없다. |
| latch | buffer/page 같은 DBMS 내부 물리 구조를 짧게 안정화하는 내부 동기화 도구 | logical row/class 보호와 다르다. CUBRID의 구체 mode는 source 근거 뒤 소개한다. |
| transaction lock | logical resource에 대한 충돌을 transaction 단위로 조정하는 잠금 | mutex나 page latch와 owner/lifetime이 다르다. |
| resource key | lock manager가 “무엇에 대한 잠금인가”를 구별하는 식별값 | mode가 같아도 key가 다르면 다른 resource다. |
| mode | 그 resource를 어떤 방식으로 사용하려는지 나타내는 값 | `X_LOCK`이라는 이름만으로 resource 종류를 알 수 없다. |
| owner | 잠금을 보유하고 release 책임을 지는 transaction | 호출 thread나 client와 항상 같지 않다. |
| holder / waiter | 이미 grant받은 transaction / 충돌 해소를 기다리는 transaction | waiter는 깨어난 뒤 업무 조건을 다시 검사해야 한다. |
| compatibility | 두 mode를 동시에 grant할 수 있는지 정한 규칙 | “읽기/쓰기”라는 직감만으로 `BU_LOCK`을 판단하면 안 된다. |
| conversion | 같은 owner가 기존 mode를 더 강하거나 다른 mode로 바꾸는 요청 | 최초 획득과 대기 조건이 다를 수 있다. 정확한 경계는 source claim에 묶는다. |
| wait / wakeup / recheck | 충돌 때문에 잠들고, 상태 변화 뒤 깨어나, 업무 조건을 다시 확인하는 과정 | wakeup은 원래 조건이 참임을 보장하지 않는다. |
| deadlock / timeout / starvation | 순환 대기 / 제한 시간 초과 / 장기간 grant받지 못함 | 세 현상을 하나의 “오래 기다림”으로 합치지 않는다. |
| class / instance | table 수준 logical object / 한 row 수준 logical object | C++ class/object 의미와 혼동하지 않는다. |
| OID | CUBRID object를 식별하는 값 | MVCCID와 역할도 key namespace도 다르다. |
| intention lock | 하위 object에 lock을 잡거나 잡으려 함을 상위 object에 알리는 mode | 하위 row lock을 자동으로 대신하지 않는다. |
| `S_LOCK` / `X_LOCK` | 함께 읽을 수 있는 mode / 충돌하는 변경을 배타적으로 조정하는 mode라는 첫 모델 | 실제 compatibility는 resource 종류와 표를 기준으로 확인한다. |
| `IS_LOCK` / `IX_LOCK` / `SIX_LOCK` | instance 수준 작업 의도를 class 수준에 표시하는 mode | 각 약어를 정의한 뒤에만 행렬을 제시한다. |
| `BU_LOCK` | bulk load 동안 class의 일반 data access mode와 충돌시키는 CUBRID object-lock mode | 모든 access를 막는 global lock도, MVCCID lock도 아니다. 약어의 expansion은 근거 없이 만들지 않는다. |
| `SCH_S_LOCK` / `SCH_M_LOCK` | schema 안정성/변경과 관련된 lock mode | 자세한 schema locking은 범위 밖이며 `BU_LOCK` compatibility를 정확히 읽을 만큼만 설명한다. |
| session / connection / thread | 사용자의 연결 맥락 / 통신 연결 / CPU가 실행하는 흐름 | 어느 것도 transaction과 동의어가 아니다. |
| worker / batch transaction | load 일부를 처리하는 실행자 / 그 batch가 commit 또는 abort되는 소유 단위 | worker가 session transaction의 child transaction이라는 뜻이 아니다. |
| `tran_index` | runtime transaction table에서 현재 transaction state를 찾는 index | persistent transaction ID나 MVCCID와 같지 않다. |
| transaction ID | transaction을 식별하는 CUBRID 내부 ID | 정확한 필드/lifetime은 source claim에서 고정한다. MVCCID와 섞지 않는다. |
| MVCC / row version | 여러 시점의 row 상태를 두고 transaction마다 보이는 version을 결정하는 방식 | “잠금이 전혀 필요 없다”는 뜻이 아니다. |
| MVCCID | row-version 동시성 판단에서 writer를 표시하는 식별자 | `tran_index`, transaction ID, OID와 다르다. |
| INSID | record version에 기록되는 inserter의 MVCCID | MVCCID가 발급되었다고 반드시 모든 record에 INSID가 쓰이는 것은 아니다. |
| self-lock | inserter가 자기 MVCCID resource에 잡는 `X_LOCK`으로 종료 전임을 알리는 rendezvous | 자기 자신을 정지시키는 lock이 아니다. |
| rendezvous | 서로 다른 transaction이 같은 MVCCID resource에서 “writer 종료”를 만나 확인하는 약속 | 일반 snapshot reader 전체를 뜻하지 않는다. |
| observer | protocol이 남긴 표식을 실제로 읽고 행동하는 경로 | 잠재적인 모든 thread를 뜻하지 않는다. |
| invariant | 허용되는 모든 실행에서 항상 유지해야 하는 관계 | 현재 관측된 사실, 미래 설계 선호와 구분한다. |
| server-side loaddb | 서버 내부 worker들이 batch로 load를 수행하는 경로 | client-side load 일반과 동일하다고 가정하지 않는다. |
| OOS-backed attribute | heap record에는 inline stub이 있고 실제 큰 값은 OOS value chain에 저장된 attribute 값 | schema column 전체가 항상 OOS라는 뜻이 아니다. |
| lazy file creation | 첫 필요 시점까지 OOS file 생성을 미루는 정책 | OOS가 매 row마다 file을 만든다는 뜻이 아니다. |
| vacuum / file identifier reuse | 더 이상 필요 없는 상태를 정리하고 식별자를 안전하게 재사용하는 주변 메커니즘 | vacuum 전체 알고리즘은 범위 밖이다. 이번에는 `file_create`가 current MVCCID를 요구하는 이유만 다룬다. |
| debug assert | 개발 빌드에서 예상 밖 상태를 즉시 드러내는 검사 | release 동작을 대신하는 오류 처리 분기가 아니다. |
| seam / choke point | 정책을 바꾸거나 공통 규칙을 적용하기 좋은 module 경계 / 여러 호출이 모이는 지점 | 단순히 줄 수가 가장 적은 수정 지점이라는 뜻이 아니다. |

### 5. 빠진 인과 연결

새 책은 다음 연결을 문장과 그림으로 모두 보여 주어야 한다.

1. **동시 실행 → 보호할 상태 → primitive 선택**  
   먼저 “무엇이 깨지는가”를 보여 준다. 그다음 보호 대상의 물리성/논리성 및 필요한 lifetime에 따라 mutex, latch, transaction lock을 고른다.

2. **Lock 이름 → 5-tuple 사고법**  
   모든 lock 요청을 `(resource key, mode, owner, waiter, lifetime)`로 다시 쓴다. `BU_LOCK`과 MVCCID `X_LOCK`의 차이는 이 형식으로 비교해야 한다.

3. **Instance lock → class intention lock → `BU_LOCK` compatibility**  
   먼저 `S/X` 두 mode로 작은 compatibility 표를 읽힌다. 그 뒤 class/instance hierarchy와 intention mode를 소개한다. 마지막에만 `BU_LOCK` 행을 제시한다.

4. **실행 주체 → transaction 정체성 → lock owner**  
   session, worker thread, batch transaction을 한 그림에 놓는다. client identity 복사와 lock ownership 공유를 분리한다.

5. **MVCC version → INSID 표식 → 특수 검사자 → wait/recheck**  
   일반 reader가 MVCC로 old version을 읽는 장면과, unique/FK 검사자가 unfinished inserter 때문에 기다리는 장면을 나란히 보여 준다. 그래야 “MVCC인데 왜 lock을 기다리지?”라는 의문이 풀린다.

6. **MVCCID 발급 → self-lock side effect → transaction 종료 release**  
   lazy allocation만 말하지 말고, acquire/ensure, grant, waiter, commit/abort, `lock_unlock_all`, recheck까지 완결된 state machine으로 설명한다.

7. **Bulk mode의 두 조건을 분리**  
   `BU_LOCK`이 일반 data-access 진입을 제한하는 조건과 bulk record가 INSID를 생략하는 조건은 서로 다른 사실이다. 둘을 합쳐 “현재 특정 waiter 경로가 없다”는 제한된 결론을 만든다.

8. **큰 값 → OOS demotion → 첫 OOS file 필요 → `file_create` → current MVCCID**  
   OOS 상세 저장 형식은 설명하지 않는다. 큰 값이 숨은 file-creation path를 여는 데 필요한 최소한만 사용한다.

9. **current MVCCID → CBRD-26942 uniform self-lock → 오래된 loaddb assert**  
   CBRD-23375, CBRD-26942, CBRD-27157/PR #7588을 날짜/commit이 있는 세 칸 timeline으로 분리한다. 현재 code와 역사적 의도를 한 시제로 쓰지 않는다.

10. **Assert 수정 → 허용 범위 → 여전히 금지되는 것**  
    uniform self-lock 수정이 transaction MVCCID resource에 대한 규칙을 어떻게 다루는지 보여 준다. 이것이 loaddb worker의 일반 class/instance object locking을 되살리는 것으로 읽히지 않게 해야 한다.

### 6. 오해를 부르는 표현과 교정안

| 기존 또는 예상 표현 | 문제 | 권장 표현 |
|---|---|---|
| “BU가 observer를 막는다.” | observer 종류와 lock mode가 생략되어 너무 넓다. | “`BU_LOCK`은 호환표상 일반 row data access에 필요한 특정 object-lock mode와 충돌한다. 별도로 bulk record는 INSID를 생략한다. 현재 분석된 unique/FK wait path는 두 조건 때문에 worker MVCCID를 관측하지 못한다.” |
| “self-lock이 불필요하다/의미가 사라진다.” | 현재 path와 미래 invariant를 섞는다. | “현재 분석된 bulk-row observer path만 보면 기다릴 주체가 확인되지 않았다. uniform self-lock은 미래 producer까지 같은 불변식을 적용하는 별도의 설계 선택이다.” |
| “MVCC에서는 reader가 writer MVCCID에 기다린다.” | 일반 snapshot reader와 unique/FK 검사자를 섞는다. | “일반 visibility read와 unique/FK conflict check를 분리한다. 이 책의 `S_LOCK` waiter는 source로 확인된 특수 검사 경로를 가리킨다.” |
| “session이 BU를 잡고 worker가 그 아래서 일한다.” | parent-child transaction 또는 lock 상속처럼 들린다. | “session transaction은 class `BU_LOCK` owner다. worker는 별도의 batch transaction으로 commit/abort하며 MVCCID self-lock도 그 batch가 소유한다. object-lock lookup의 redirect는 별도 규칙이다.” |
| “fresh MVCCID의 self-lock은 기다리지 않는다.” | 왜 기다리지 않는지와 예외가 없다. | “그 MVCCID resource에 충돌 holder가 없다는 전제에서 inserter의 최초 `X_LOCK`은 즉시 grant된다. 다른 resource의 wait 가능성까지 부정하지 않는다.” |
| “OOS 때문에 lock bug가 났다.” | OOS를 잠금 원인으로 오해하게 한다. | “큰 값이 OOS lazy file creation path를 열었다. `file_create`의 current-MVCCID 요구와 MVCCID self-lock side effect가 기존 loaddb assert를 드러냈다.” |
| “crash stack” | debug assertion failure와 crash recovery를 혼동한다. | “debug assertion failure call path”라고 쓰고, crash recovery는 durability 절에서만 사용한다. |
| “assert 완화가 fix다.” | assert가 runtime semantics 전부인 것처럼 들린다. | debug/release 동작, 실제 lock 획득, release, 허용 resource 범위를 각각 따로 쓴다. |
| “같은 hash table이지만 alias되지 않는다.” | 초급자에게 구현 자료구조가 핵심처럼 보인다. | 먼저 “resource type과 value가 함께 key를 이룬다”고 설명한다. hash/compare 구현은 source note로 뒤에 둔다. |
| “현재 결정: 미합의” | frozen PR head의 현재 상태와 과거 토론이 섞일 수 있다. | 각 안을 역사적 proposal로 표시하고, frozen revision이 실제로 구현한 동작은 source-confirmed current behavior로 별도 기록한다. |

기존 quiz의 4번 문항은 early-return seam을 사실상 정답으로 제시하면서 본문에서는 “둘 중 하나가 유일하게 옳다고 증명되지 않는다”고 말한다. 이는 design preference를 factual recall 문제로 바꾼 것이다. 새 quiz에서는 두 안의 precondition과 failure mode를 비교하게 하고, 선택의 평가는 rubric으로 채점해야 한다.

기존 quiz의 2번 정답 문구인 “대기 관측자가 없어서 의미가 사라진다”도 지나치게 절대적이다. “현재 분석한 observer path에서 필요성을 뒷받침할 waiter가 없다” 정도로 좁혀야 한다.

## Gaps

### 1. 본문 작성 전에 Evidence 역할이 고정해야 할 사실

Pedagogy 역할은 아래 항목의 설명 순서를 제안하지만, 정확한 결론을 만들 수는 없다. Book writer는 source Claims와 일치시켜야 한다.

- transaction ID, `tran_index`, MVCCID의 정확한 allocation/lifetime 관계
- self-lock을 최초 획득하는 함수와 이미 획득한 경우의 ensure/no-op 동작
- unique/FK waiter가 INSID 또는 index 상태에서 MVCCID를 얻는 정확한 call path
- wait 뒤 재검사하는 업무 조건과 error/timeout/deadlock 전달 경로
- commit과 abort에서 self-lock 및 object lock이 풀리는 정확한 공통 경로
- `TT_LOADDB` object-lock lookup redirect가 적용되는 정확한 Interface와 예외
- `BU_LOCK` 전체 compatibility 표 및 conversion semantics
- bulk operation에서 INSID를 생략하는 정확한 조건과 해당 조건의 범위
- `file_create(FILE_OOS)`가 current MVCCID를 요구하는 정확한 이유와 file identifier/vacuum seam
- PR #7588 frozen head의 uniform fix가 허용하는 resource 종류와 남겨 둔 assert
- debug assertion failure와 release build의 관찰 결과 차이
- PostgreSQL/MySQL analogue의 정확한 owner, resource, wait/recheck 의미

### 2. 범위상 의도적으로 짧게 다루되 숨기면 안 되는 항목

- page latch 구현 전체는 범위 밖이다. 그러나 latch와 transaction lock을 구분하는 한 장은 필수다.
- MVCC snapshot 알고리즘 전체는 범위 밖이다. 그러나 old-version visibility와 unique/FK wait의 차이는 필수다.
- wait-for graph와 victim policy 전체는 범위 밖이다. 그러나 deadlock이 가능한 이유, transaction이 받는 결과, cleanup 경계는 설명해야 한다.
- WAL/ARIES 전체는 범위 밖이다. 이 issue의 lock state가 process restart 뒤 복원되는 persistent state인지, transaction 종료 때 사라지는 volatile coordination state인지 명시해야 한다.
- OOS binary layout/CRUD는 범위 밖이다. 첫 OOS-backed value가 lazy file create를 일으킨다는 최소 causal seam은 필수다.
- PostgreSQL/MySQL runtime 실험은 금지된다. comparison은 pinned source와 공통 시나리오로만 가르친다.

### 3. 관찰 가능성의 교육적 공백

초급자는 “lock이 있었다”를 SQL 결과만으로 직접 볼 수 있다고 생각하기 쉽다. 각 실험은 다음을 분리해야 한다.

- SQL 결과로 직접 관찰한 것
- 대기 시간 또는 blocking으로 간접 관찰한 것
- debug assert/log/stack에서 관찰한 것
- source를 근거로 해석한 것
- 실험이 증명하지 못한 것

특히 release build에서 OOS placement나 internal self-lock entry가 직접 보이지 않을 수 있다. 관찰 도구가 없으면 “없다”고 결론내리지 말고 `Unknown` 또는 inference로 표시해야 한다.

## Proposal

### 1. 책 전체의 교수 원칙

1. **구체 장면을 먼저 준다.** 각 장 첫 문단은 두 transaction이나 한 load batch가 있는 작은 상황으로 시작한다.
2. **한 장에서 새 핵심 용어는 최대 3~5개로 제한한다.** 나머지는 이전 장 glossary seed에 연결한다.
3. **직관 뒤에 곧바로 경계를 말한다.** 비유를 제시한 같은 절에서 “여기부터는 실제와 다르다”를 둔다.
4. **모든 lock을 같은 질문으로 읽는다.** resource key, mode, owner, waiter, lifetime 다섯 칸을 반복한다.
5. **일반 모델과 CUBRID 구현을 층으로 나눈다.** 먼저 언어 독립 모델, 다음 CUBRID identifier/function, 마지막 Claim/source link 순서다.
6. **일반 reader와 constraint waiter를 계속 구분한다.** “MVCC인데 왜 기다리는가?”를 책의 반복 질문으로 삼는다.
7. **현재·역사·제안 시제를 분리한다.** `Source-confirmed current`, `Historical`, `Inferred`, `Design alternative`, `Unknown` 라벨을 텍스트로도 표시한다.
8. **문장 하나에 주장 하나만 둔다.** 괄호 안에 새 개념을 넣지 않는다. canonical English term은 한국어 설명 다음에 붙인다.
9. **장 끝은 암기 요약이 아니라 인과 회상으로 끝낸다.** “A 때문에 B, 그래서 C”를 독자가 완성하게 한다.
10. **central explanation은 접지 않는다.** `<details>`는 부가 source excerpt에만 쓸 수 있다.

### 2. 사용할 비유와 반드시 붙일 중단점

| 개념 | 권장 비유 | 비유가 도움이 되는 지점 | 여기서 비유를 중단한다 |
|---|---|---|---|
| mutex | 공용 화이트보드 옆에 펜이 하나뿐인 상황 | 한 thread가 짧은 critical section을 수정하는 동안 다른 thread가 기다린다. | 실제 mutex는 펜이 아니며 transaction 의미가 없다. spin/sleep, memory ordering, process-shared 여부도 비유가 설명하지 못한다. |
| latch | 서랍 속 카드 배열을 바꾸는 동안 서랍을 잠깐 고정하는 걸쇠 | buffer page 같은 물리 구조를 읽거나 바꾸는 짧은 시간만 보호한다. | latch가 logical row 접근 권한을 주지 않는다. commit까지 보유한다는 뜻도 아니다. |
| transaction lock | 대출 처리의 최종 승인/취소가 날 때까지 자료에 붙이는 예약표 | logical resource를 transaction lifetime 동안 조정하고 commit/abort 때 정리한다. | isolation level과 조기 해제 규칙은 DBMS마다 다르다. 모든 transaction lock이 무조건 commit까지라는 일반 법칙으로 확장하지 않는다. |
| lock request 5-tuple | 택배 접수표의 주소, 서비스 종류, 보낸 사람, 대기자, 유효기간 | 이름에 `LOCK`이 붙어도 주소(resource key)가 다르면 다른 요청임을 보여 준다. | lock manager는 택배 시스템이 아니다. conversion, deadlock, queue fairness는 별도 상태 머신으로 설명한다. |
| intention lock | 건물 입구 게시판에 “3층 방을 사용할 예정”이라고 표시하기 | 상위 class에서 하위 instance lock 존재/의도를 빠르게 충돌 검사하는 이유를 보여 준다. | 게시판 표시는 실제 방 열쇠를 대신하지 않는다. 계층은 물리 공간이 아니라 logical object 관계다. |
| `BU_LOCK` | 이삿날 건물을 예약해 일반 입주자의 출입 작업은 막지만 승인된 여러 이사팀은 함께 일할 수 있는 규칙 | `BU`-`BU` 호환과 일반 data mode 충돌을 직관화한다. | 접근 제어나 사용자 권한이 아니다. `SCH_S_LOCK`은 호환된다. 정확한 허용 여부는 반드시 compatibility matrix가 결정한다. |
| session/worker transaction | 현장 책임자가 건물 사용 허가를 들고 있고, 각 작업팀은 자기 batch 작업서를 별도로 정산하는 상황 | session의 `BU_LOCK` owner와 worker batch의 commit/abort owner를 분리한다. | batch가 nested/child transaction이라는 뜻이 아니다. 전체 load의 atomicity도 이 비유만으로 결론내리지 않는다. |
| MVCC row version | 문서 사본마다 작성자 번호와 유효 시점 표식이 붙는 상황 | 한 logical row에 여러 version이 있고 reader가 자기 시점에 맞는 version을 고른다는 직관을 준다. | 디스크에 완전한 문서 사본이 단순 배열된다는 뜻이 아니다. CUBRID undo/version reconstruction은 source 설명을 따른다. |
| MVCCID self-lock | 작업자 번호판 아래 “작업 중” 표지를 작업자 자신이 걸고, 검사자가 같은 번호판에서 종료를 기다리는 상황 | self-lock이 자기 자신을 막는 것이 아니라 다른 waiter를 위한 rendezvous임을 보여 준다. | 실제 grant는 `X/S` compatibility와 transaction owner 규칙으로 처리된다. 일반 snapshot reader가 모두 이 표지 앞에서 기다리는 것도 아니다. |
| OOS lazy creation | 큰 짐이 처음 들어온 순간 별도 창고를 처음 여는 상황 | 작은 row에서는 보이지 않던 file-creation path가 큰 값에서만 열린 이유를 보여 준다. | OOS는 lock manager가 아니며 self-lock은 OOS contents를 보호하는 잠금이 아니다. OOS page latch 문제와도 구분한다. |
| debug assert | 개발 중 잘못된 길에 들어오면 울리는 tripwire | 예상하지 않은 `TT_LOADDB` 경로를 즉시 드러낸다. | tripwire가 production error handling이나 correctness protocol 자체는 아니다. assert 제거만으로 실제 동작이 안전하다고 증명되지 않는다. |

비유는 제목이나 장식으로만 사용하지 않는다. 각 비유 다음에 실제 CUBRID 표 또는 sequence를 놓고, 두 표현을 한 줄씩 대응시킨다.

### 3. `index.html` 읽기 지도

`index.html`은 요약 보고서가 아니라 학습 경로 선택 페이지로 만든다.

- **처음 배우는 경로:** 01 → 11 전체. 03, 06, 09 뒤에 checkpoint를 둔다.
- **기존 lesson을 이미 읽은 경로:** 03 → 05 → 06 → 08 → 09 → 11.
- **assert call path만 복습하는 경로:** 01의 전체 그림 → 08 → 09. 단, 03~06 용어를 링크로 즉시 복원할 수 있게 한다.
- **비교/설계 리뷰 경로:** 03 → 04 → 06 → 09 → 10 → 11.

첫 화면에는 다음을 명시한다.

- 이 책은 OOS 전체를 가르치는 책이 아니다.
- 이 책에서 “lock”은 적어도 mutex, latch, transaction lock 세 종류로 나뉜다.
- 최종 질문은 “lock을 잡나?”가 아니라 “어떤 resource를 어느 transaction이 왜 언제까지 잡나?”이다.
- 모든 source revision과 dirty provenance는 고정되어 있다.

### 4. 구체적인 11장 설계

#### 01. 큰 행 하나가 debug assert에 닿기까지 — 방향 잡기

- **학습 질문:** 왜 작은 row load는 지나가는데 큰 값이 있는 load가 잠금 assert를 드러내는가?
- **내용:** 공통 시나리오, Declared Scope, 제외 범위, 세 central behavior, provenance, evidence label, 전체 결론의 teaser. 용어는 아직 풀지 않고 “모르는 말 목록”으로 표시한다.
- **시각화:** `large value → OOS lazy create → current MVCCID → self-lock → debug assert` 한 줄 지도. 아래쪽에 별도 lane으로 `session BU_LOCK`을 그려 “같은 lock 아님”을 미리 보인다.
- **보이는 한국어 대체 설명:** “큰 값은 첫 OOS file 생성을 요구한다. file 생성은 worker의 current MVCCID를 요구한다. MVCCID 발급은 self-lock 획득을 부른다. 이 transaction resource 요청이 오래된 loaddb object-lock assert와 만난다. session의 `BU_LOCK`은 별도 resource다.”
- **요약:** “OOS는 원인이 아니라 숨은 경로를 연 trigger다.”
- **다음 장 연결:** “하지만 왜 내부 걸쇠와 transaction lock을 같은 ‘lock’으로 부르면 안 되는지 먼저 배워야 한다.”

#### 02. mutex, latch, transaction lock — 같은 단어, 다른 수명

- **학습 질문:** 두 thread가 같은 page를 만지는 문제와 두 transaction이 같은 row를 바꾸는 문제는 왜 다른 도구가 필요한가?
- **내용:** race condition, critical section, 물리 상태와 logical 상태, thread owner와 transaction owner, 짧은 latch lifetime과 transaction decision lifetime, primitive를 잘못 바꿨을 때의 실패.
- **시각화:** 세 lane timeline. mutex/latch는 짧은 코드 구간에서 끝나고, transaction lock은 SQL 작업과 `COMMIT`/`ROLLBACK` 경계까지 이어지는 대비를 그린다.
- **보이는 한국어 대체 설명:** “mutex와 latch는 내부 메모리 구조를 사용하는 짧은 동안 유지된다. transaction lock은 logical resource 충돌을 transaction의 결정 시점까지 조정한다. 서로 대체할 수 없다.”
- **요약:** “무엇을 보호하는지와 언제까지 보호하는지가 primitive를 고른다.”
- **다음 장 연결:** “이제 transaction lock 요청 하나를 다섯 칸으로 분해한다.”

#### 03. 잠금 요청을 읽는 다섯 칸 — resource, mode, owner, waiter, lifetime

- **학습 질문:** 둘 다 `X_LOCK`인데 왜 다른 lock일 수 있는가?
- **내용:** lock resource entry, holder/waiter, 최소 `S/X` compatibility, grant/wait/wakeup/recheck, 같은 owner 재요청과 conversion의 개념, commit/abort release. 실제 CUBRID 세부는 Claims가 증명한 범위만 쓴다.
- **시각화:** lock request card 두 장과 `S/X` 2×2 matrix. 두 transaction timeline에서 wait와 wakeup 뒤 recheck를 표시한다.
- **보이는 한국어 대체 설명:** “요청 A와 B가 같은 resource key를 가리키고 mode가 충돌할 때만 waiter가 생긴다. owner 종료로 holder가 사라지면 waiter가 깨어난다. waiter는 업무 조건을 다시 검사한다.”
- **Checkpoint A:** 이름만 보고 mutex/latch/transaction lock을 분류하고 5-tuple을 채울 수 있어야 다음으로 간다.
- **요약:** “mode 이름은 lock identity의 일부일 뿐이다. resource key와 owner가 빠지면 설명이 완성되지 않는다.”
- **다음 장 연결:** “row가 수백만 개인 table에서는 class와 instance 잠금을 함께 조정해야 한다.”

#### 04. class와 instance의 계층 — intention mode에서 `BU_LOCK`까지

- **학습 질문:** row 하나를 바꾸려는 transaction이 왜 table 수준에도 표식을 남기는가?
- **내용:** class/instance OID, hierarchy, `IS/IX/SIX`의 목적, 상위/하위 obligation, `BU_LOCK`의 정확한 compatibility, `BU`-`BU` 및 `BU`-`SCH_S`, 일반 data mode와 충돌. `BU_LOCK`을 전체 DB exclusive lock처럼 말하지 않는다.
- **시각화:** class node 아래 instance node 세 개가 있는 tree와 `BU_LOCK` 한 행을 강조한 full compatibility matrix.
- **보이는 한국어 대체 설명:** “instance lock을 쓰는 transaction은 class에 intention mode를 둔다. `BU_LOCK`은 class resource에 걸린다. 소스의 compatibility 표에서 다른 `BU_LOCK` 및 `SCH_S_LOCK`과는 함께 grant될 수 있지만 일반 data access mode와는 충돌한다.”
- **요약:** “`BU_LOCK`은 class object lock이다. MVCCID transaction resource를 대신하지 않는다.”
- **다음 장 연결:** “그렇다면 server-side loaddb에서 이 class lock의 owner는 누구인가?”

#### 05. 한 load, 여러 transaction — session과 worker batch의 소유권

- **학습 질문:** 한 client가 시작한 load인데 왜 lock owner가 둘 이상인가?
- **내용:** session, connection, thread, worker, transaction을 분리한다. session transaction의 class `BU_LOCK`, worker별 batch `tran_index`, commit/abort, object-lock lookup redirect, client identity와 ownership의 차이. `tran_index`, transaction ID, MVCCID 비교표를 둔다.
- **시각화:** session transaction S와 worker batch B1/B2의 ownership tree가 아니라 **관계 graph**. object lookup redirect는 점선, actual ownership은 실선으로 표시한다.
- **보이는 한국어 대체 설명:** “session transaction S가 class T의 `BU_LOCK`을 소유한다. worker W1과 W2는 각각 batch transaction B1과 B2로 행을 넣고 따로 종료한다. object-lock 조회는 session 쪽을 볼 수 있지만 MVCCID self-lock은 현재 worker batch가 소유한다.”
- **요약:** “같은 load 요청에 속한다는 사실은 같은 transaction이라는 뜻이 아니다.”
- **다음 장 연결:** “worker가 자기 MVCCID resource에 lock을 잡는 이유를 알려면 MVCC version과 constraint waiter를 봐야 한다.”

#### 06. MVCCID self-lock — 자기 자신을 막는 lock이 아니다

- **학습 질문:** MVCC가 reader blocking을 줄이는데, 왜 다른 transaction은 inserter의 종료를 기다리는가?
- **내용:** row version, INSID, 일반 snapshot visibility와 unique/FK conflict check의 차이, inserter의 MVCCID `X_LOCK`, waiter의 같은 key `S_LOCK`, commit/abort release, recheck, `observable INSID ⇒ matching X self-lock` 불변식, lazy MVCCID allocation/ensure.
- **시각화:** T1 inserter와 T2 unique/FK checker의 sequence diagram. 옆에 일반 snapshot reader lane을 두되 self-lock waiter lane과 다른 색 및 텍스트 라벨을 쓴다.
- **보이는 한국어 대체 설명:** “T1은 MVCCID 42를 record에 INSID로 남기기 전에 같은 MVCCID resource에 `X_LOCK`을 보유한다. T2의 constraint 검사 경로가 42를 발견하면 `S_LOCK`을 요청해 T1 종료까지 기다린다. 깨어난 T2는 key 상태를 다시 검사한다. 일반 snapshot reader는 같은 경로라고 가정하지 않는다.”
- **Checkpoint B:** 독자가 inserter/waiter sequence와 invariant를 빈 종이에 그린다.
- **요약:** “self-lock은 transaction 완료 여부를 다른 검사자에게 전달하는 rendezvous다.”
- **다음 장 연결:** “이 rendezvous가 정상 종료, abort, timeout, 잘못된 interleaving에서 어떻게 끝나는지 시간축으로 확인한다.”

#### 07. 시간축으로 검증하기 — wait, commit, abort, deadlock, cleanup

- **학습 질문:** waiter가 기다리는 동안 owner가 commit하거나 abort하면 각각 무엇을 다시 확인해야 하는가?
- **내용:** self-lock과 object lock의 lifecycle/state machine, transaction 종료의 `lock_unlock_all`, legal/illegal transitions, wait/recheck, timeout/deadlock/cancellation/shutdown 경계, volatile lock state와 durable row/log state 구분, crash/restart의 `Not applicable` 범위를 정확히 설명한다. 성능은 per-row rendezvous와 transaction-keyed self-lock의 cost model을 직관적으로 소개한다.
- **시각화:** `UNALLOCATED → MVCCID_ALLOCATED → X_HELD → COMMIT/ABORT → RELEASED` state diagram과 commit/abort interleaving 표.
- **보이는 한국어 대체 설명:** “MVCCID가 생기고 self-lock이 grant되면 transaction 종료까지 보유된다. commit 또는 abort 뒤 lock release가 waiter를 깨운다. waiter는 종료 결과와 key 상태를 다시 검사한다. process restart는 volatile lock entry를 그대로 복원하는 문제가 아니다.”
- **요약:** “wakeup은 정답이 아니라 재검사를 시작할 기회다.”
- **다음 장 연결:** “이제 이 정상 state machine에 server-side loaddb와 OOS가 어떻게 들어왔는지 재구성한다.”

#### 08. CBRD-27157 재구성 — 큰 값에서만 열린 숨은 경로

- **학습 질문:** OOS 저장이 왜 transaction lock manager의 debug assert까지 도달하는가?
- **내용:** server-side loaddb fast path와 큰 값 slow path, OOS demotion의 최소 설명, first OOS-backed attribute, lazy `FILE_OOS` creation, file identifier/vacuum seam, `logtb_get_current_mvccid`, CBRD-26942 self-lock side effect, `lock_transaction_mvccid`, assertion failure. OOS page latch와 이번 transaction self-lock을 명시적으로 구분한다.
- **시각화:** small-row와 OOS-row의 갈라지는 call-flow. 각 단계에 “state before/after, owner, lock, I/O, possible failure, Claim ID” 표를 붙인다.
- **보이는 한국어 대체 설명:** “작은 row는 이미 있는 heap 경로로 들어가 OOS file 생성을 요구하지 않는다. 큰 variable value가 OOS-backed가 되면 첫 OOS file 생성이 필요하다. file 생성은 worker의 current MVCCID를 요구한다. MVCCID 발급은 transaction self-lock 획득을 호출하고, 그 요청이 `TT_LOADDB` debug assert에 닿는다.”
- **요약:** “데이터 크기는 잠금 mode를 바꾼 것이 아니라 다른 dependency path를 선택했다.”
- **다음 장 연결:** “실패 지점을 찾았다고 수정 계약이 자동으로 정해지지는 않는다.”

#### 09. 수정의 경계 — 역사적 no-object-lock과 uniform self-lock

- **학습 질문:** early skip과 uniform acquire는 각각 어떤 불변식을 선택하는가?
- **내용:** CBRD-23375 object-lock bypass, CBRD-26942 transaction-keyed self-lock, CBRD-27157/PR #7588의 chronology. historical alternative인 early return과 frozen head의 uniform behavior를 같은 지위로 쓰지 않는다. 각 안의 precondition, permitted/forbidden calls, debug/release behavior, cleanup, future INSID producer 위험, module seam을 비교한다. 현재 수정의 total pseudocode와 conformance oracle을 제시한다.
- **시각화:** 세 commit/ticket timeline, 두 안의 decision table, `TT_LOADDB × resource type` 허용/금지 matrix.
- **보이는 한국어 대체 설명:** “과거 loaddb 규칙은 class/instance object-lock 경로를 우회했다. 이후 MVCCID 발급은 transaction self-lock을 일관되게 획득하는 규칙을 얻었다. OOS lazy creation이 두 계약을 같은 call path에 놓았다. 수정은 어떤 transaction resource 요청을 허용하는지 좁게 설명해야 하며 일반 object-lock 우회를 되돌렸다고 해석하면 안 된다.”
- **Checkpoint C:** 독자가 “무엇이 바뀌고 무엇은 그대로 금지되는가”를 source identifier를 사용해 설명한다.
- **요약:** “좋은 fix 설명은 assert 한 줄이 아니라 허용 resource와 유지 invariant를 말한다.”
- **다음 장 연결:** “이 설계가 보편적인가를 판단하려면 같은 문제의 책임을 PostgreSQL과 MySQL/InnoDB가 어디에 두는지 비교해야 한다.”

#### 10. 같은 문제, 다른 경계 — PostgreSQL/MySQL 비교와 CUBRID 실험

- **학습 질문:** 세 DBMS가 bulk load 조정과 unfinished inserter wait를 같은 resource에 구현하는가?
- **내용:** frozen source가 확인한 nearest mechanism만 사용한다. PostgreSQL relation heavyweight lock 및 virtual/transaction ID wait, MySQL/InnoDB metadata/table intention/record-index/transaction wait를 공통 시나리오에 배치한다. 모든 대응을 `Equivalent`, `Partial analogy`, `No equivalent`로 표시한다. 이어서 central behavior별 CUBRID runtime experiment를 `Question → Hypothesis → Setup → Action → Observation → Interpretation → Alternative → Cleanup` 형식으로 설명한다. PostgreSQL/MySQL runtime은 요구하지 않는다.
- **시각화:** 세 DBMS swimlane과 responsibility matrix. 실험마다 prediction/observation 카드를 둔다.
- **보이는 한국어 대체 설명:** “세 시스템 모두 bulk load와 unfinished writer 충돌을 조정하지만 resource identity, owner, lifetime, wait/recheck 경계가 다르다. CUBRID의 `BU_LOCK`이나 MVCCID self-lock과 이름 또는 일부 역할이 비슷하다는 이유만으로 동일 구현이라고 부르지 않는다.”
- **요약:** “비교의 목적은 같은 이름을 찾는 것이 아니라 같은 책임이 어디에 배치됐는지 찾는 것이다.”
- **다음 장 연결:** “마지막으로 이 지식을 독립 구현 가능한 Interface와 시험 목록으로 압축한다.”

#### 11. 다시 만들 수 있을 만큼 설명하기 — blueprint, glossary, unknowns, mastery

- **학습 질문:** source를 다시 열지 않고 최소 동작을 재구현하려면 무엇이 더 필요한가?
- **내용:** Interface contract, abstract resource model, ownership/lifetime, total state transitions, compatibility and wait algorithm, transaction cleanup, error propagation, dependency seams, implementation order, conformance tests. glossary, Claim/evidence index, known unknowns, compatibility limits, readiness declaration을 포함한다. 마지막에는 central behavior→chapter→Quiz→Live Grill map을 둔다.
- **시각화:** implementation dependency DAG와 conformance matrix.
- **보이는 한국어 대체 설명:** “먼저 resource key와 owner model을 만든다. 다음 compatibility/grant/wait/recheck를 구현한다. 그 뒤 transaction 종료 cleanup, object hierarchy, MVCCID rendezvous, loaddb integration, OOS-trigger regression 순으로 붙인다. 각 단계는 별도 conformance test로 확인한다.”
- **요약:** “CBRD-27157은 두 lock을 구분하는 문제에서 시작하지만, 최종적으로는 resource·owner·observer·lifetime·invariant를 끝까지 연결하는 문제다.”
- **마지막 teach-back:** learner가 small row와 OOS row를 비교하고 session/worker owner, `BU_LOCK`, MVCCID self-lock, wait/recheck, assert, fix boundary, 세 DBMS 차이를 한 흐름으로 설명한다.

### 5. Mandatory Coverage Obligation 배치

| Obligation | 주 장 | 보조 장 |
|---|---:|---:|
| orientation | 01 | 11 |
| mental-model | 02, 03 | 01 |
| scope-interface-seams | 03, 05, 09 | 11 |
| data-ownership-lifetime | 03, 05, 06 | 07 |
| lifecycle-state-machines | 06, 07 | 05, 09 |
| core-workflows | 06, 08 | 09 |
| concurrency | 03, 04, 06, 07 | 09 |
| storage-durability-recovery | 07 | 08, 11 |
| policies-algorithms | 03, 04, 06, 09 | 11 |
| errors-resource-pressure | 07, 08, 09 | 11 |
| performance-observability | 07, 10 | 08 |
| experimental-validation | 10 | 08, 09 |
| postgresql-analysis | 10 | 01 |
| mysql-analysis | 10 | 01 |
| cross-database-comparison | 10 | 11 |
| reimplementation-blueprint | 11 | 03, 06, 09 |
| glossary-evidence-unknowns | 11 | 모든 장의 first-use 정의 |
| teaching-map | 01, 11 | 각 장 recap |

### 6. 시각화 공통 규칙

- 모든 그림 뒤에 화면에 보이는 `<p>` 형태의 한국어 text alternative를 둔다. `aria-label` 한 줄만으로 대체하지 않는다.
- sequence diagram은 행위자, 요청, wait, wakeup, recheck, commit/abort를 시간순 문장으로 다시 쓴다.
- state diagram은 state와 transition 목록을 별도 표로 반복한다. 그림과 표의 state 이름을 일치시킨다.
- compatibility matrix는 색뿐 아니라 각 칸에 `호환` 또는 `충돌` 텍스트를 쓴다.
- ownership graph는 실선=`owns`, 점선=`lookup redirect`, 화살표=`calls`라는 범례를 텍스트로도 제공한다.
- historical/current/proposed는 색 외에 라벨을 반드시 적는다.
- inline SVG가 복잡해지면 그림을 줄인다. central causal explanation은 prose와 표만 읽어도 완전해야 한다.
- Book contract상 JavaScript가 금지되므로 기존 `quiz.js` 방식은 최종 Book에 옮기지 않는다. static Quiz는 `quiz/quiz-N/quiz.md`와 분리된 `answer.md`, 실행 artifact로 제공한다.

### 7. 장별 recap과 transition 작성 틀

각 장 마지막은 아래 네 문장으로 고정하면 초급자가 길을 잃지 않는다.

1. **이번 장의 한 문장:** 새로 배운 인과 한 줄.
2. **이제 구분할 수 있는 것:** 이전에 섞었던 두 개념의 대비.
3. **CBRD-27157에 쓰는 법:** 이번 개념이 잘못된 결론 하나를 어떻게 막는지.
4. **다음 질문:** 다음 장이 답할 구체 질문.

예를 들어 04장의 recap은 다음처럼 쓸 수 있다.

> `BU_LOCK`은 class OID를 key로 한 object lock이다. MVCCID resource의 `X_LOCK`과 직접 대체되지 않는다. 이 구분 덕분에 “session이 BU를 잡았으니 worker도 self-lock을 이미 잡았다”는 결론을 피할 수 있다. 다음 장에서는 실제 owner인 session transaction과 worker batch transaction을 분리한다.

### 8. Static Quiz 설계와 central behavior 매핑

Quiz는 용어 선택 문제가 아니라 예측→실행→관찰→인과 설명 순서로 만든다. 실행 artifact와 oracle은 검증된 CUBRID Experiment에서 가져오며, Pedagogy 단계에서 결과를 꾸며 내지 않는다.

| Quiz | 핵심 과제 | 연결 장 | Central Behavior | Mastery 영역 |
|---|---|---|---|---|
| Quiz 1: “어떤 lock인가?” | 여러 요청에서 resource key, mode, owner, waiter, lifetime을 채우고 `COMMIT` 전후 결과를 예측한다. | 02, 03 | `lock-resource-owner-lifecycle` | 1, 2, 3 |
| Quiz 2: “`BU_LOCK`은 누구와 함께 갈 수 있나?” | full compatibility row를 읽고 session/worker owner graph를 완성한다. “모두 차단”과 “self-lock 대체”가 왜 틀렸는지 설명한다. | 04, 05 | `lock-resource-owner-lifecycle` | 1, 2, 4, 6 |
| Quiz 3: “INSID 42를 발견한 T2” | T1 commit 변형과 abort 변형에서 wait/wakeup/recheck를 예측한다. 일반 snapshot reader와 constraint waiter를 구분한다. | 06, 07 | `mvccid-self-lock-rendezvous` | 2, 3, 4, 5 |
| Quiz 4: “작은 row와 큰 row의 갈림길” | 같은 loaddb에서 value size만 바꾸어 어떤 call path/evidence가 달라지는지 예측한다. OOS가 lock 원인이 아니라 trigger인 이유를 teach-back한다. | 08, 09 | `loaddb-oos-regression` | 3, 5, 7 |
| Quiz 5: “Fix contract와 세 DBMS 지도” | early skip/uniform acquire의 precondition과 failure mode를 비교하고, frozen fix의 허용/금지 matrix 및 PostgreSQL/MySQL의 nearest mechanism을 분류한다. | 09, 10, 11 | 세 behavior 통합 | 1, 4, 6, 8 |

각 `answer.md`는 반드시 다음 오답 모델을 다룬다.

- lock mode 이름만 보고 같은 resource라고 판단함
- thread/session/transaction을 같은 owner로 봄
- MVCC가 있으므로 어떤 wait도 없다고 생각함
- self-lock을 self-deadlock으로 해석함
- `BU_LOCK`을 global exclusive lock으로 해석함
- OOS가 MVCCID lock을 직접 잡는다고 생각함
- assert 제거와 runtime correctness를 같은 것으로 봄
- 다른 DBMS에서 이름이 비슷하면 equivalent라고 판단함

### 9. Live Grill mastery mapping

| Mastery 영역 | 주 학습 장 | 좁혀 물을 질문의 방향 |
|---|---|---|
| 1. responsibility, scope, Interface, seams | 01, 03, 04, 09 | “이 함수가 보호하는 resource를 key로 말해 보라.” |
| 2. data ownership and lifetime | 03, 05, 06 | “session S와 worker B1이 각각 무엇을 언제까지 소유하는가?” |
| 3. lifecycle and transitions | 05, 06, 07, 08 | “MVCCID 미발급부터 commit/abort release까지 state를 순서대로 말해 보라.” |
| 4. concurrency invariants | 03, 04, 06, 07, 09 | “어떤 interleaving이 `observable INSID ⇒ X self-lock`을 깨는가?” |
| 5. durability, recovery, failure | 07, 08, 09 | “assert, abort, process restart에서 각각 어떤 state가 남는가?” |
| 6. policy and performance trade-offs | 04, 07, 09 | “early skip과 uniform acquire가 비용을 어디에 내고 어떤 미래 위험을 받는가?” |
| 7. experiment interpretation | 08, 10 | “관찰한 사실과 source에서 추론한 사실을 분리해 보라.” |
| 8. PostgreSQL/MySQL non-equivalence | 10, 11 | “같은 공통 시나리오에서 resource owner와 wait protocol이 어디서 달라지는가?” |

Grill은 용어 정의부터 시작하지 않는다. 먼저 장면을 주고 learner의 현재 모델을 그리게 한다. 약한 답변은 `resource → owner → lifetime → observer → invariant` 순서로 한 단계씩 좁힌다. 최종 capstone은 다음 하나의 질문으로 충분하다.

> “server-side loaddb에서 큰 OOS-backed row 하나가 들어올 때, session과 worker의 transaction ownership부터 debug assert와 frozen fix의 경계까지를 시간순으로 설명하고, PostgreSQL/MySQL에서는 같은 책임이 어디에 놓이는지 비교해 보세요.”

### 10. Book writer를 위한 최종 품질 체크

- 03장 전에는 `IS/IX/SIX/BU` full matrix를 보여 주지 않았는가?
- `tran_index`, transaction ID, MVCCID, INSID가 각각 첫 등장에 정의되었는가?
- 모든 lock 설명에 resource key, mode, owner, waiter, lifetime이 있는가?
- 일반 snapshot reader와 unique/FK waiter를 한 문장에 합치지 않았는가?
- `BU_LOCK`의 `BU`/`SCH_S` 호환성을 숨기지 않았는가?
- session→worker 관계를 nested transaction처럼 그리지 않았는가?
- OOS를 root cause가 아니라 path trigger로 설명했는가?
- OOS page latch와 MVCCID transaction lock을 구분했는가?
- “crash”를 debug assert와 crash recovery 두 뜻으로 혼용하지 않았는가?
- historical early-return proposal을 frozen current behavior처럼 쓰지 않았는가?
- debug/release, acquire/release, commit/abort를 각각 설명했는가?
- 비유마다 실제와 달라지는 breakpoint가 같은 절에 있는가?
- 모든 diagram에 보이는 한국어 text alternative가 있는가?
- 각 장에 학습 목표, scenario, exact mechanics+Claim IDs, failures, recap, transition이 있는가?
- static Quiz가 답을 노출하지 않고 실제 CUBRID artifact를 포함하는가?
- comparison cell마다 `Equivalent`, `Partial analogy`, `No equivalent`가 근거와 함께 있는가?
- 마지막 장이 “source를 다시 읽으라”는 말 없이 Interface와 conformance oracle을 제공하는가?

