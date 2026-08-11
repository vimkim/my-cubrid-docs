# Pedagogy Architect Research Packet

- **Role:** Pedagogy Architect
- **Topic:** CUBRID flush와 AIO에서 SX latch가 정말 필요한가 — frame 안정성, `READ` latch, 사본, 전용 I/O freeze 비교
- **Declared Scope digest:** `research/scope.md`의 frozen SHA-256 `db5ba3f0288fbb966ca5a4a832b420e7b5c582b461dc266ceda80a816c410885`. 현행 snapshot-copy flush를 재구성하고, synchronous buffered write, synchronous `O_DIRECT`, copy-based AIO, frame-based zero-copy AIO를 분리한 뒤 사본·`READ`·범용 `SX`·전용 `IO_WRITE_FREEZE`·`WRITE`를 동일한 소유권/수명/동시성/durability 축으로 비교한다.
- **Pinned revisions:** CUBRID `f799e05d77d5300c6ea5753b4a6cc7caee6d8912`; PostgreSQL `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc`; MySQL/InnoDB `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`
- **작성 시각:** `2026-08-11T04:42:34Z` (`2026-08-11T13:42:34+09:00`)
- **권한/산출물:** source, Book, Quiz, report metadata를 수정하지 않았다. 이 문서는 최종 저자를 위한 한국어 교육 설계 패킷이다. 아래 anchor와 Claim ID는 제안이며, 최종 저자가 확정된 evidence ledger에 맞춰 연결해야 한다.

## 1. 교육 결론: 첫 화면에서 바로 고칠 문장

독자가 가장 먼저 보아야 할 답은 다음 세 문장이다.

1. **AIO가 요구하는 것은 `SX`라는 이름의 latch가 아니라, I/O가 실제로 읽는 메모리의 주소와 바이트가 completion까지 유효하고 불변이라는 계약이다.**
2. **synchronous `O_DIRECT`는 direct이지만 asynchronous가 아니다.** blocking 호출이라면 사용자 buffer 안정 구간은 호출 시작부터 반환까지이며, submit 이후 completion까지로 늘어나는 것은 AIO다.
3. **CUBRID flush만을 위한 미래 write AIO라면 범용 public `SX`보다 request-owned `IO_WRITE_FREEZE`가 더 좁고 설명 가능한 경계일 수 있다.** copy-based AIO는 frame freeze 없이도 가능하고, 현행 동기 snapshot-copy flush에는 새 latch mode가 정확성 요구사항이 아니다.

이 세 문장을 orientation, 마지막 권고, capstone grill에서 같은 의미로 반복한다. “AIO라서 SX가 필수” 또는 “direct I/O라서 completion까지 buffer를 잡아야 한다”는 축약은 사용하지 않는다.

## 2. 독자가 따라갈 하나의 추론식

책 전체를 다음 질문 순서로 조직한다.

```text
디스크가 읽는 메모리는 무엇인가?
  -> 그 메모리의 owner는 누구인가?
  -> 언제부터 언제까지 살아 있어야 하는가?
  -> 그 구간에 누가 바이트를 바꿀 수 있는가?
  -> 같은 frame을 다른 page에 재사용할 수 있는가?
  -> 제출·성공·재더티·실패를 누가 마무리하는가?
  -> 이 계약을 만족하는 가장 좁은 동기화 수단은 무엇인가?
```

모든 장과 표는 위 질문 중 어느 것에 답하는지 첫 문단에서 밝힌다. latch mode 이름부터 시작하지 않는다. 먼저 memory object와 lifetime을 고르면, 필요한 동기화가 결과로 나오게 한다.

### 핵심 불변식의 층

- **I1 — content stability:** I/O consumer가 읽는 byte range는 소비 구간 동안 바뀌지 않는다.
- **I2 — identity/lifetime stability:** 그 주소가 가리키는 allocation은 소비 구간 동안 해제되거나 다른 page 용도로 재사용되지 않는다.
- **I3 — writeback ownership:** 같은 page의 두 번째 flusher가 중복 상태 전이를 하지 않고, 정확히 하나의 completion 경로가 성공·실패·wakeup을 마무리한다.
- **I4 — durability ordering:** data page image의 page LSA에 필요한 WAL이 data write보다 먼저 durable하다.
- **I5 — later-update preservation:** image를 정한 뒤 live frame에 생긴 수정은 현재 I/O 성공으로 소거되지 않고 다음 flush 대상으로 남는다.

I1과 I2가 “stable frame”의 본체다. I3은 single-flusher 및 completion ownership, I4와 I5는 persistence protocol이다. `SX` 하나가 다섯 불변식을 자동으로 보장한다고 쓰지 않는다.

## 3. 2학년 독자용 mental model

### 권장 concrete object: “빌려 준 배열”

도서관/복사기 비유보다 `char page[IO_PAGESIZE]`와 pointer를 직접 사용한다.

```text
frame F의 주소 p ──> I/O 함수에 전달

질문 A: I/O는 p를 언제까지 역참조하는가?
질문 B: 그동안 다른 thread가 p[0..n)을 바꿀 수 있는가?
질문 C: buffer pool이 F를 page Q의 frame으로 재사용할 수 있는가?
```

이 모델은 “byte가 변하면 안 됨”과 “주소가 다른 객체가 되면 안 됨”을 분리한다. `latch`는 주로 A를 만족시키는 content 접근 규칙이고, `fix`/pin/in-flight reference는 주로 C를 막는 lifetime 규칙이다. 실제 설계에서는 둘을 함께 묶어야 한다.

### 비유를 쓴다면 지켜야 할 제한

“사진을 찍는다”는 snapshot 순간만 설명할 때만 쓴다. 사진 비유만으로는 다음을 설명할 수 없으므로 곧바로 배열/주소 모델로 돌아온다.

- 사진 파일의 owner와 해제 시점
- DMA 또는 kernel의 buffer 소비 종료 시점
- frame 재사용 금지
- completion thread가 다른 thread일 수 있음
- WAL과 dirty state의 성공/실패 처리

“책을 스캔하는 동안 편집 금지” 비유는 `SX`를 자연스러운 유일 해법처럼 보이게 하므로 주 비유로 사용하지 않는다. 사본을 스캔할 수도 있고, 동기 호출 동안 `READ`를 유지할 수도 있으며, 전용 freeze token을 I/O request가 소유할 수도 있기 때문이다.

## 4. 먼저 분리할 세 개의 직교 축과 네 I/O mode

독자에게 `direct`, `async`, `zero-copy`가 서로 다른 축임을 먼저 가르친다.

| 축 | 선택지 | 이 축이 답하는 질문 |
|---|---|---|
| cache 경로 | buffered / direct | OS page cache를 거치는가 |
| 완료 방식 | synchronous / asynchronous | 호출 반환과 I/O 완료가 같은 사건인가 |
| 제출 memory | snapshot/output copy / live frame | I/O request가 어느 allocation을 읽는가 |

`O_DIRECT`는 첫째 축, AIO는 둘째 축, frame-based zero-copy는 셋째 축의 선택이다. 이름이 한 문장에 같이 등장해도 같은 개념이 아니다.

### 네 mode 비교

| mode | I/O가 읽는 memory | 안정 구간 | 반환 뒤 live frame 수정 | 필요한 소유권 계약 | 핵심 교정 |
|---|---|---|---|---|---|
| synchronous buffered write | 전달한 frame 또는 output copy | 호출 진입부터 `write` 반환까지 | 가능 | 호출 thread가 반환까지 buffer를 보유 | page cache 사용은 “비동기”의 동의어가 아니다 |
| synchronous `O_DIRECT` | 전달한 aligned frame 또는 output copy | blocking 호출 진입부터 반환까지 | 가능 | 호출 thread가 반환까지 buffer를 보유 | direct는 cache 우회 축이다. 반환 뒤까지 잡는다고 일반화하지 않는다 |
| copy-based AIO | request 전용 snapshot/TDE/DWB output image | submit 전 image 확정부터 completion까지 | 가능 | I/O request가 copy를 completion까지 소유 | AIO여도 live frame freeze는 필요하지 않다 |
| frame-based zero-copy AIO | live buffer-pool frame | submit 전 freeze부터 completion까지 | 불가 | request가 frame pin + content freeze + completion 권한을 소유 | 이 mode에서만 completion까지 live frame 안정성이 직접 필요하다 |

“zero-copy”는 이 보고서에서 **page buffer가 별도 snapshot image를 만들지 않는다**는 좁은 뜻으로 정의한다. kernel, driver, device, TDE, DWB 어디에서도 byte copy가 전혀 없다는 약속이 아니다.

### 각 mode의 짧은 causal explanation

- **동기 buffered:** 호출자가 `write`에서 돌아오기 전까지 input buffer를 바꾸지 않는다. 반환이 곧 호출자의 소비 구간 끝이므로 그 뒤 lifetime을 I/O request에 넘길 필요가 없다.
- **동기 direct:** OS page cache 우회 여부만 달라진다. blocking 호출이 반환하기 전까지 안정해야 한다는 lifetime 모양은 동기 buffered와 같다.
- **copy AIO:** live frame에서 immutable image를 만든 순간 둘의 lifetime이 갈라진다. request가 copy를 잡고 있으므로 live frame writer는 진행할 수 있다.
- **frame AIO:** request가 live frame 자체를 계속 읽는다. 따라서 completion 전 writer와 victim/reuse를 함께 막아야 한다.

## 5. memory owner/lifetime ledger

소유권 장에서는 자료구조 이름 나열 대신 다음 표를 중심에 둔다.

| object | identity | owner 후보 | 만들어지는 때 | 최소 lifetime 끝 | 바뀔 수 있는가 | 해제/전이 담당 |
|---|---|---|---|---|---|---|
| live frame | `VPID`가 올라온 buffer frame | buffer pool/BCB | page fix/load | 마지막 fix 및 in-flight reference 종료, 재사용 protocol 완료 | ordinary writer가 수정 | buffer manager/victimizer |
| BCB | frame의 제어 객체 | buffer pool | pool 초기화 | frame identity가 바뀌어도 객체 자체는 pool lifetime | mutex/atomic/latch protocol로 변경 | buffer manager |
| plain snapshot | 특정 시점 page image | 현행 sync flusher 또는 미래 AIO request | BCB 보호 아래 `memcpy` | sync 반환 또는 AIO completion | 생성 후 불변 | submitter 또는 completion handler |
| TDE output image | 암호화된 write image | TDE/flush request | encryption 완료 | 실제 consumer completion | 생성 후 불변 | 해당 output-buffer owner |
| DWB slot/image | doublewrite 단계의 image | DWB subsystem | slot reservation/copy | DWB protocol이 slot 재사용을 허용할 때 | DWB 계약에 따름 | DWB completion/slot manager |
| page LSA snapshot | write image가 나타내는 log frontier | flush request | image 결정 시 | WAL ordering 판정과 completion bookkeeping 종료 | 값 자체는 불변 | request/completion |
| I/O request | buffer pointer, length, page identity, result, references | sync call stack 또는 async queue | prepare/submit | terminal completion/cancel 처리 종료 | state machine으로만 전이 | completion handler |

최종 소스 근거를 붙일 때는 “누가 free하는가”, “어느 lock 아래 pointer가 request에 들어가는가”, “completion이 어떤 reference를 줄이는가”까지 보여 준다. allocation 함수만 인용해서 lifetime을 증명하지 않는다.

## 6. 현행 CUBRID flush를 가르치는 순서

현행 흐름은 함수 호출보다 **image를 정하는 경계**와 **state를 정리하는 경계**를 먼저 보여 준다.

### 6.1 정상 흐름의 여섯 단계

1. flusher가 BCB를 보호하고 현재 dirty page와 page LSA를 확인한다.
2. `FLUSHING_TO_DISK`를 세우고 현행 re-dirty protocol에 맞게 dirty/`oldest_unflush_lsa` 상태를 준비한다.
3. plain page는 snapshot copy를 만들고, TDE page는 별도 encrypted output image를 만든다. 이 순간 이번 write의 image가 고정된다.
4. BCB 보호를 놓는다. 이후 live frame writer가 수정해도 제출 image는 변하지 않으며, 새 수정은 dirty를 다시 세워야 한다.
5. image가 나타내는 page LSA까지 WAL을 먼저 flush한 뒤 DWB/datafile의 동기 write 경로가 output image를 소비한다.
6. BCB를 다시 보호해 성공, re-dirty, I/O 실패 중 하나로 정리하고 `FLUSHING_TO_DISK` 대기자를 깨운다.

각 단계 옆에는 반드시 다음 네 칸을 둔다: `현재 image owner / live frame writer 가능 여부 / dirty·oldest LSA / 다음 실패 분기`.

### 6.2 세 종료 분기

| 종료 | disk로 시도한 image | live frame 상태 | dirty 결과 | 설명해야 할 원인 |
|---|---|---|---|---|
| 성공, 추가 수정 없음 | snapshot 시점 image | snapshot과 같은 논리 시점 | clean 가능 | 현재 disk image가 이번 dirty frontier를 포함 |
| 성공, flush 중 re-dirty | 더 오래된 snapshot image | 더 최신 | dirty 유지 | 현재 I/O 성공이 나중 수정을 지우면 안 됨 |
| write 실패 | snapshot image 기록 실패/불확실 | 현재 frame 유지 | dirty 및 필요한 oldest LSA 복원 | 다음 retry와 checkpoint 추적이 살아 있어야 함 |

“writer는 자유”라는 표현은 **snapshot이 완성되고 BCB 보호가 풀린 뒤, ordinary page latch 규칙이 허용하는 범위에서**라고 한정한다. snapshot 생성 중에도 무조건 writer가 자유롭다는 뜻으로 쓰지 않는다.

### 6.3 runtime evidence의 역할 제한

SQL workload와 statdump는 dirty/physical write 활동이 생겼다는 사실을 보강할 수 있다. 다음은 runtime 숫자만으로 증명하지 못한다.

- `memcpy`가 정확히 어느 lock 구간에 실행되는지
- live frame writer와 실제 I/O가 겹칠 수 있는지
- TDE/DWB image owner의 정확한 lifetime
- 미래 AIO 또는 `IO_WRITE_FREEZE`의 성능/공정성

이 네 항목은 pinned source 또는 아직 구현되지 않았다는 `Unknown`으로 표시한다.

## 7. 동시성 matrix: 행위자별로 묻기

먼저 “reader 허용 + writer 금지”만으로는 부족하다고 밝힌다. 두 번째 flusher, victimizer, async completion owner를 표에 넣어야 한다.

| 대안 | reader | writer | 두 번째 flusher | victim/frame reuse | 다른 thread의 completion | 별도 상태 필요 |
|---|---|---|---|---|---|---|
| 현행 sync snapshot copy | snapshot 뒤 허용 | snapshot 뒤 허용, re-dirty | `FLUSHING_TO_DISK`로 금지 | 현행 flushing/BCB identity 계약에 따라 금지 | 해당 없음 | dirty, flushing, oldest LSA |
| copy-based AIO | 허용 | 허용, re-dirty | in-flight request 상태로 금지 | completion bookkeeping이 BCB를 참조하면 금지; 완전 분리 설계만 별도 검토 | 자연스러움: request가 copy 소유 | in-flight request, queue/backpressure |
| strict `READ` + retained fix, sync zero-copy | 허용 | 반환까지 금지 | `READ` 자체로는 해결 못함 | retained fix/pin이 금지 | 해당 없음 | `FLUSHING_TO_DISK` 및 fix owner |
| 범용 `SX` + pin/reference | 허용 | completion까지 금지 | 모든 flusher가 `SX`를 요청하면 충돌 | pin/reference가 금지; latch만으로 단정 금지 | thread-owned holder라면 부자연스러워 token화 필요 | dirty, I/O owner, completion protocol |
| 전용 `IO_WRITE_FREEZE` + in-flight ref | 허용 | completion까지 금지 | 상태 전이 자체가 금지 | freeze/ref가 명시적으로 금지 | 자연스러움: request가 owner | 하나의 전용 state machine에 통합 |
| `WRITE` + retained fix | 금지 | 금지 | 충돌 | fix가 금지 | holder 이전 문제 존재 | 지나치게 강한 reader 차단 |

이 표의 CUBRID 현행 셀은 source tracer의 확정 Claim으로 교체해야 한다. 제안 대안 셀은 `Inferred`로 표시하고, premise와 falsifier를 적는다.

### `READ` latch를 공정하게 설명하는 법

CUBRID의 strict `READ`가 모든 content writer와 충돌한다면, **동기 frame-based write의 I1**은 이미 제공할 수 있다. retained fix가 I2를, 기존 `FLUSHING_TO_DISK`가 I3을 제공한다면 sync zero-copy의 정확성에 public `SX`는 논리적으로 필수가 아니다.

그러나 `READ` latch 하나만으로 미래 AIO가 끝나지는 않는다.

- latch holder가 submitter thread/fix lifetime에 묶여 있으면 completion thread가 안전하게 release할 수 없다.
- latch와 별도로 frame pin/reference를 completion까지 유지해야 한다.
- 두 번째 flusher와 dirty/error/wakeup은 `FLUSHING_TO_DISK`/request state가 계속 책임져야 한다.
- 장시간 `READ` 보유가 writer fairness와 shutdown drain에 미치는 영향은 측정/설계가 필요하다.

따라서 결론은 “`READ`가 AIO에 충분하다/불충분하다”가 아니라, **content exclusion에는 충분할 수 있지만 request-owned lifetime과 completion protocol까지 담는 Interface는 아니다**이다.

## 8. durability는 memory stability와 별도 장으로 분리

독자가 “불변 image를 쓰면 durable하다”라고 오해하지 않게 두 화살표를 분리한다.

```text
memory correctness: image 확정 -> image 불변/생존 -> write consumer 종료
persistence order:  page LSA L 확정 -> WAL through L durable -> data write 제출
```

둘 다 필요하지만 서로를 대신하지 않는다.

### crash/failure reasoning 카드

| 사건 | 안전성을 설명할 질문 |
|---|---|
| WAL flush 전 data write 시도 | 왜 금지되어야 하는가? recovery가 page가 참조한 update를 재현할 log를 갖는가? |
| WAL durable 후 data write 전 crash | data page가 옛 image여도 redo 가능한가? |
| snapshot 뒤 live frame re-dirty | 성공 completion이 새 dirty를 지우지 않는가? |
| DWB write 성공, datafile write 중 torn write | DWB가 어느 failure class를 다루며 WAL과 무엇이 다른가? |
| async submit 성공 후 completion error | 누가 dirty/oldest LSA/freeze/ref/wakeup을 복구하는가? |
| shutdown/cancel | 모든 request가 terminal state에 도달하거나 안전하게 drain되는가? |

TDE output copy는 암호화 transformation boundary, DWB copy는 torn-write protection boundary, snapshot copy는 writer-overlap boundary다. 모두 “사본”이지만 목적과 lifetime이 다르므로 한 단어로 합치지 않는다.

## 9. 대안 비교와 권고

### 9.1 동일 축 비교

| 대안 | I1 content | I2 lifetime | reader | writer | async completion 소유권 | memory/copy 비용 | Interface 폭 |
|---|---|---|---|---|---|---|---|
| 현행/copy 유지 | immutable copy | request가 copy 소유 | 허용 | 허용 | copy request로 자연스러움 | page마다 output buffer | 좁음 |
| strict `READ` + fix | `READ`가 writer 차단 | fix/pin | 허용 | 차단 | thread/fix holder 이전 필요 | plain snapshot 제거 가능 | 기존 public mode 재사용, I/O 의미는 별도 |
| 범용 `SX` + pin | SX가 writer 차단 | pin/ref | 허용 | 차단 | request token화 필요 | plain snapshot 제거 가능 | 모든 `pgbuf_fix` caller/행렬/대기/재귀에 영향 |
| 전용 `IO_WRITE_FREEZE` | writer grant가 freeze 확인 | in-flight ref가 reuse 금지 | 허용 | 차단 | request가 직접 소유 | plain snapshot 제거 가능 | flush/writeback 내부에 한정 |
| `WRITE` + fix | 모두 차단 | fix/pin | 차단 | 차단 | holder 이전 필요 | plain snapshot 제거 가능 | 의미는 단순하나 동시성이 과도함 |

### 9.2 권고 문장

1. **현행 synchronous snapshot-copy flush:** 정확성을 위해 새 `SX`는 필요하지 않다. copy CPU가 실제 병목인지와 writer wait trade-off를 측정하기 전에는 현행 사본을 baseline으로 유지한다.
2. **synchronous zero-copy 실험:** strict `READ` + retained fix + 기존 `FLUSHING_TO_DISK` 조합이 I1~I3을 만족하는지 먼저 검증한다. 이는 “SX가 유일한 답이 아님”을 가장 작은 prototype으로 검사하는 경로다.
3. **copy-based AIO:** request-owned copy pool과 backpressure를 설계한다. live frame writer를 막지 않으므로 public `SX` 도입의 근거가 되지 않는다.
4. **frame-based zero-copy AIO:** flush 전용 `IO_WRITE_FREEZE` + in-flight reference + completion-owned state transition을 우선안으로 검토한다. 이 상태는 reader 허용, writer/두 번째 flusher/victim 금지를 이름 자체로 드러낸다.
5. **범용 public `SX`:** B-tree 등 다른 Module도 동일 semantics를 실제로 필요로 하고, recursion/promotion/wakeup/fairness 비용을 독립적으로 정당화할 때 별도 결정한다. flush/AIO만으로 넓은 Interface 변경을 정당화하지 않는다.

### 9.3 전용 freeze blueprint

제안 상태 이름은 구현 확정이 아니라 교육용 Interface sketch다.

```text
DIRTY
  --prepare under BCB protection / capture image LSA, acquire in-flight ref-->
IO_WRITE_FREEZE + WAL_PENDING
  --WAL through image LSA durable-->
IO_WRITE_FREEZE + SUBMITTED
  --completion(success, no later dirty)--> CLEAN + release ref + wake
  --completion(success, re-dirty)-------> DIRTY + release ref + wake
  --completion(error/cancel)------------> DIRTY/oldest-LSA restored + release ref + wake
```

Interface가 명시해야 할 항목:

- acquire는 BCB 보호 아래 conditional transition이며 두 번째 flusher를 거절한다.
- reader grant는 허용하지만 모든 writer grant path는 freeze를 확인한다.
- victim/invalidation/reassignment는 in-flight ref가 0이 될 때까지 금지한다.
- request는 `VPID`, BCB/frame identity, image LSA, dirty-generation 또는 현행 re-dirty 판별 state, buffer pointer, result를 소유한다.
- WAL success 전 data submit을 금지한다.
- completion은 성공/재더티/실패/cancel의 total function이어야 한다.
- terminal path는 정확히 한 번 freeze와 ref를 release하고 필요한 waiter를 깨운다.
- shutdown은 drain, cancel, timeout 중 하나를 명시하며 “completion이 언젠가 온다”에 의존하지 않는다.
- queue-full/copy-pool exhaustion은 block, fallback-to-sync/copy, retry 중 정책을 명시한다.

`dirty_generation` 신규 도입은 자동 권고하지 않는다. 현행 dirty/`oldest_unflush_lsa` protocol로 동일 판별을 유지할 수 있는지 source tracer의 상태 전이를 먼저 사용한다.

## 10. PostgreSQL/MySQL 비교에서 지켜야 할 semantic gap

### PostgreSQL

- PostgreSQL의 `SHARE_EXCLUSIVE`는 **동일 책임의 한 구현에 대한 partial analogy**다. 이름이 CUBRID public `SX` 도입을 명령하지 않는다.
- 과거 PostgreSQL `SHARE` 아래에서는 hint-bit writer가 허용되어 content가 변할 수 있었다. CUBRID의 strict `READ`가 모든 page content writer를 막는다면 출발점이 다르다. “PG가 새 mode를 만들었으므로 CUBRID도 만들어야 한다”는 추론을 금지한다.
- `FlushBuffer`가 어떤 content lock과 I/O state/pin을 함께 유지하는지 나누어 설명한다. content lock만 떼어 CUBRID의 frame lifetime과 등가라고 하지 않는다.
- PostgreSQL의 AIO 준비 동기와 현재 실제 write submission/completion 경로는 별도 Claim으로 둔다. 미래 방향 또는 commit rationale을 현재 CUBRID 동작으로 확장하지 않는다.
- `SHARE_EXCLUSIVE`라는 이름은 SQL/table lock의 shared-exclusive와 혼동될 수 있으므로 “buffer content lock mode”라고 매번 첫 사용에 한정한다.

### MySQL/InnoDB

- 실제 주어는 MySQL 서버 전체가 아니라 InnoDB buffer pool이다.
- InnoDB 비교의 단위는 `SX` latch 하나가 아니라 **page latch + `io_fix`/in-flight state + completion release + doublewrite lifetime**의 묶음이다.
- `SX`는 reader 허용/writer 금지 축에서는 전용 freeze와 비슷하지만, public B-tree/latch use와 I/O ownership까지 포함하면 CUBRID 전용 상태와 `equivalent`가 아니다.
- `io_fix`가 second flusher/eviction/I/O lifetime을 책임지는 부분을 빼면 “SX가 모든 것을 보장한다”는 잘못된 전이가 생긴다.
- doublewrite가 켜진 경로에는 별도 page image/slot lifetime이 남는다. “InnoDB SX = 완전 zero-copy”라고 쓰지 않는다.

### 비교표의 권장 행

DBMS별 mode 이름을 열로 나열하지 말고 다음 책임을 행으로 둔다.

1. content writer exclusion
2. reader admission
3. single-flusher ownership
4. frame eviction/reuse prohibition
5. submitter와 completion owner
6. dirty/re-dirty/error bookkeeping
7. WAL/redo-before-data ordering
8. TDE/checksum/doublewrite output image

각 셀에는 `equivalent`, `partial analogy`, `no equivalent`를 붙이고, 왜 다른지를 한 문장으로 설명한다.

## 11. 이전 `f799e05_claude` 보고서의 오해 유발 표현 교정

### 반드시 폐기할 서술

| 이전 서술/구조 | 문제 | 새 서술 |
|---|---|---|
| 제목부터 “AIO/direct I/O 필수성”으로 묶음 | cache 경로와 completion 방식 혼합 | direct, async, copy/frame을 직교 축으로 소개 |
| “direct I/O/AIO는 syscall 반환 후에도 사용자 buffer를 읽는다” | synchronous `O_DIRECT`까지 AIO lifetime으로 늘림 | sync direct는 blocking 반환까지, AIO는 completion까지 |
| “AIO/direct I/O write ⇒ SX 등가 latch 또는 사본 필수” | `READ`+pin, 전용 freeze, request ownership을 가림 | 안정 memory 계약이 필수이며 구현 수단은 여러 개 |
| “AIO 도입 시 SX는 성능 옵션이 아니라 선행 조건” | copy-based AIO를 배제하고 broad public mode를 필수화 | frame-based zero-copy AIO에 content freeze+pin이 필요; copy AIO는 별도 가능 |
| “CUBRID는 AIO/direct write 준비가 안 됨(frame 불안정)” | 현행 sync 구현과 가능한 copy-AIO 설계를 혼합 | 현행은 AIO 미구현; snapshot lifetime을 completion까지 늘리면 copy-AIO 설계 가능 |
| “InnoDB/PG가 SX로 수렴했으므로 산업 검증” | 책임 bundle과 semantic gap을 이름 하나로 축소 | 각 엔진의 content lock + I/O state + buffer lifetime을 묶어 partial analogy로 비교 |
| “InnoDB가 정확히 이 방식” | `io_fix`, completion release, doublewrite copy 누락 | SX는 content exclusion 일부이며 I/O state/lifetime이 함께 필요 |
| “SX 직접 flush면 plain page 사본 제거”를 일반 결론화 | TDE/DWB/checksum/output transform 경계에 copy가 남을 수 있음 | 어느 copy가 어떤 목적인지 각각 계산 |
| B-tree promote가 insert당 약 4.4회인 hot path | summary 산식 오류를 실제 event count로 사용 | 이 보고서에서는 B-tree 성능 근거를 재사용하지 않고 관측 교정 사례로만 설명 |

### promote summary 오류의 정확한 교육 처리

이 사례는 본 주제의 성능 근거가 아니라 **관측값 검증 훈련**으로만 한 단락 사용한다.

- 이전 runtime stdout의 summary는 `Data_page_total_promote_success = 89,587 / 88,779 / 88,779`였다.
- 같은 출력의 detailed `Num_data_page_promote_ext`는 `887 / 879 / 879`였다.
- 두 값은 각 run에서 정확히 `summary = detail × 101` 관계다.
- pinned `perf_monitor.c`의 summary 계산은 computed slot에 detailed counter를 더한 뒤 `×100` scaling을 하고, 출력은 `/100` 한다. 이미 계산된 summary가 diff input에 남은 채 다시 계산되는 경로에서는 이전 scaled 값과 detailed 값이 합쳐져 `detail × 101`처럼 보인다.
- 그러므로 이전 보고서의 “20,000 insert에서 약 88,000회, insert당 4.4회”는 폐기한다. detailed 기준은 약 879회, 단순 비율은 약 0.044회/insert지만, 새 scope에서는 이 수치조차 B-tree 성능 주장에 사용하지 않는다.

교훈 문장: **computed summary를 성능 근거로 쓰기 전에 raw/detailed counter의 합, 계산 함수의 초기화·scale, 출력 formatting을 함께 검증한다.**

## 12. 최소 시각 자료와 한국어 text alternative

책 전체에서 관계를 실제로 단순화하는 시각 자료는 다섯 개면 충분하다.

### D1. “세 memory object와 lifetime” 그림

- 구성: live frame, snapshot/TDE/DWB output image, I/O request 세 상자. `owner`, `created`, `release`를 상자 안에 표시.
- 목적: frame과 output image가 같은 “page”가 아님을 보여 줌.
- text alternative 예시: “live frame은 buffer pool이 소유하고 writer가 수정할 수 있다. snapshot을 만든 뒤 request가 snapshot을 completion까지 소유하면 frame 수정과 I/O가 겹쳐도 제출 image는 변하지 않는다. frame 자체를 제출하면 request가 completion까지 frame의 수정과 재사용을 모두 금지해야 한다.”

### D2. “direct/async/copy의 직교 축” 2×2+overlay

- 구성: 가로 buffered/direct, 세로 sync/async, 각 칸에 copy/frame badge를 별도로 붙임.
- 목적: direct=AIO, AIO=zero-copy 오해 방지.
- text alternative 예시: “buffered/direct는 page cache 경로, sync/async는 완료 시점, copy/frame은 제출 memory 선택이다. 한 축의 선택은 다른 축을 자동 결정하지 않는다.”

### D3. 현행 CUBRID snapshot flush sequence

- participants: writer, flusher/BCB, WAL, DWB/datafile.
- edge: image 결정, BCB release, later write/re-dirty, WAL durable, data write, success/error completion.
- text alternative에는 성공과 re-dirty와 실패 세 분기를 모두 문장으로 쓴다. 정상 화살표만 설명하지 않는다.

### D4. 현행 copy state와 제안 freeze state의 나란한 state machine

- 현행: dirty → copy/flushing → clean 또는 re-dirty 또는 error restore.
- 제안: dirty → freeze/WAL pending → submitted → terminal branch.
- text alternative에는 각 guard, actor, release action을 적는다.

### D5. 대안 decision table

- table로 충분하며 radar chart는 사용하지 않는다.
- 행: copy, `READ`+fix, `SX`+pin, `IO_WRITE_FREEZE`, `WRITE`+fix.
- 열: reader/writer/second flusher/victim/completion ownership/TDE-DWB copy/복잡도.
- 모든 substantive cell에 Claim 또는 `Inferred`/`Unknown` 표시.

시각 자료마다 Korean caption과 별도의 완결된 text alternative를 둔다. “위 그림은 흐름을 보여 준다” 같은 무의미한 대체문은 금지한다.

## 13. source link가 닫혀도 이해되는 causal explanation 블록

각 핵심 장에는 다음 형식의 4문장 블록을 둔다.

```text
전제: 어떤 memory를 누가 소유한다.
사건: 다른 actor가 언제 무엇을 하려 한다.
위험: 어떤 byte/identity/state가 어떻게 깨진다.
해법: 어떤 state/latch/reference/order가 어느 구간을 막거나 보존한다.
```

반드시 독립 설명할 여덟 항목:

1. snapshot copy가 writer overlap을 안전하게 만드는 이유
2. synchronous `O_DIRECT`가 AIO lifetime을 뜻하지 않는 이유
3. strict `READ`가 sync zero-copy content 안정성을 줄 수 있는 이유
4. `READ` latch만으로 async completion ownership이 끝나지 않는 이유
5. `IO_WRITE_FREEZE`가 latch mode보다 single-flusher/victim 의미를 더 직접 표현하는 이유
6. WAL-before-data가 image 안정성과 별개인 이유
7. TDE와 DWB 사본이 snapshot-copy 제거 후에도 남을 수 있는 이유
8. completion이 단순 notification이 아니라 dirty/error/ref/wakeup의 commit point인 이유

소스 인용은 이 설명 뒤에 붙인다. 함수명/라인을 문장의 주어로 삼지 않는다.

## 14. 용어집 seed와 첫 사용 규칙

| 용어 | 2학년 독자용 정의 | 혼동 방지 문장 |
|---|---|---|
| page | disk에 저장되는 고정 크기 논리 block | memory 주소가 아니다 |
| frame | page 한 장을 담는 buffer-pool memory slot | 같은 frame이 나중에 다른 page를 담을 수 있다 |
| page image | 특정 시점 page bytes | live frame, snapshot, encrypted image가 서로 다른 allocation일 수 있다 |
| BCB | frame identity와 fix/latch/dirty/I/O state를 관리하는 control block | page bytes 자체가 아니다 |
| latch | memory structure의 짧은 동시 접근 규칙 | transaction lock과 목적·수명이 다르다 |
| fix / pin | frame을 사용 중으로 붙잡아 재사용을 막는 reference | content를 자동으로 immutable하게 만들지는 않는다 |
| owner | object를 release하거나 state를 끝낼 책임이 있는 주체 | pointer를 잠깐 가진 thread와 같지 않을 수 있다 |
| lifetime | allocation/identity가 유효해야 하는 시간 구간 | latch hold time과 항상 같지 않다 |
| synchronous | 호출 반환이 해당 I/O 소비 종료 경계인 방식 | buffered의 동의어가 아니다 |
| AIO | submit과 terminal completion이 분리된 방식 | direct 또는 zero-copy의 동의어가 아니다 |
| buffered I/O | OS page cache를 거치는 경로 | write-back device durability 시점과 syscall 반환은 다르다 |
| direct I/O | OS page cache를 우회하도록 요청하는 경로 | 그 자체로 async가 아니다 |
| completion | request가 성공/실패/cancel의 terminal result를 얻는 사건 | submit 반환과 다르다 |
| snapshot copy | 특정 순간의 page bytes를 별도 allocation에 고정한 image | DWB/TDE copy와 목적을 구별한다 |
| zero-copy | 이 책에서는 flush snapshot copy를 만들지 않는다는 좁은 뜻 | end-to-end copy 0을 약속하지 않는다 |
| dirty / re-dirty | memory image가 disk보다 새로움 / flush image 확정 뒤 다시 수정됨 | I/O 성공이 re-dirty까지 지우면 안 된다 |
| `FLUSHING_TO_DISK` | 현재 CUBRID의 writeback 진행을 나타내는 BCB state | content latch와 동일하지 않다 |
| `IO_WRITE_FREEZE` | 제안된 request-owned writeback 전용 state | 현재 구현된 CUBRID API가 아니다 |
| WAL / page LSA | data보다 먼저 보존할 log 규칙 / page image의 log frontier | stable memory와 durable storage는 별개다 |
| DWB | torn page 대응을 위한 double-write 단계 | WAL이나 content freeze를 대체하지 않는다 |
| TDE | disk image를 암호화하는 transformation | live frame과 output image가 달라질 수 있다 |
| victim/eviction/reuse | frame의 기존 page identity를 버리고 다른 page에 배정 | writer 차단과 별도로 금지해야 한다 |
| backpressure | in-flight request/copy slot이 찼을 때 제출 속도를 제한하는 정책 | correctness가 아니라 resource policy도 포함한다 |

약어는 첫 사용에 Korean 설명과 English 원문을 함께 쓴다. 이후 glossary link를 붙이되 central 설명을 glossary에 숨기지 않는다.

## 15. 예상 오개념과 교정 질문

| 오개념 | 왜 생기는가 | 교정할 좁은 질문 |
|---|---|---|
| direct I/O는 곧 AIO다 | 둘을 한 구절로 반복 | “blocking `O_DIRECT`가 반환했을 때 아직 누가 input buffer를 소비 중인가?” |
| AIO는 곧 zero-copy다 | submit/completion만 보고 memory source를 생략 | “AIO request가 snapshot pointer를 가지면 live frame을 왜 freeze해야 하는가?” |
| `SX`가 durability를 지킨다 | 안정 image와 WAL을 한 흐름으로 봄 | “page LSA의 log가 durable하지 않으면 immutable page를 잘 써도 무엇이 깨지는가?” |
| `READ`는 읽기 전용이므로 flusher가 가질 수 없다 | holder 이름을 actor 권한으로 해석 | “flusher가 bytes를 수정하지 않고 읽어 write한다면 content exclusion에 어떤 mode가 필요한가?” |
| latch가 있으면 frame은 재사용되지 않는다 | content와 lifetime 혼합 | “latch release 없이도 BCB/page identity를 completion까지 누가 pin하는가?” |
| copy면 victim이 즉시 frame을 재사용해도 된다 | output bytes만 생각하고 completion bookkeeping을 잊음 | “completion이 BCB dirty/flushing state를 갱신한다면 identity reuse 뒤 어느 page를 갱신하게 되는가?” |
| `FLUSHING_TO_DISK`가 있으면 bytes도 immutable하다 | state flag와 writer grant rule 혼합 | “ordinary writer acquisition path가 이 flag를 검사해 block한다는 근거가 있는가?” |
| TDE/DWB copy가 있으니 snapshot copy 논의는 무의미하다 | copy 목적을 하나로 취급 | “각 copy가 writer overlap, encryption, torn write 중 무엇을 책임지는가?” |
| I/O success면 page를 clean으로 만들면 된다 | re-dirty generation 누락 | “snapshot 뒤 writer가 바꾼 bytes가 성공한 old image에 포함되어 있는가?” |
| PG/InnoDB도 SX이므로 CUBRID에 그대로 복사 가능하다 | 이름 기반 analogy | “그 엔진에서 eviction과 completion을 SX 외의 어떤 state가 맡는가?” |
| summary counter는 상세 counter의 합이다 | 계산/scale을 검증하지 않음 | “같은 출력의 88,779와 879가 왜 101배 차이인가?” |

## 16. 권장 chapter progression과 anchor

파일 수는 최종 저자가 조정할 수 있으나, 학습 순서는 바꾸지 않는 편이 좋다.

| 순서 | 권장 장/anchor | 독자가 답해야 할 질문 | coverage obligations |
|---|---|---|---|
| 1 | `01-orientation.html#short-answer` | SX가 정말 필요한가? 가장 중요한 정정은 무엇인가? | orientation |
| 2 | `02-mental-model.html#borrowed-buffer` | page, frame, image, owner, lifetime은 어떻게 다른가? | mental-model |
| 2 | `02-mental-model.html#orthogonal-io-axes` | direct/async/copy는 어떤 독립 축인가? | mental-model |
| 2 | `02-mental-model.html#four-io-modes` | 각 mode의 안정 구간은 어디까지인가? | mental-model |
| 3 | `03-interface-ownership.html#module-seams` | caller→pgbuf→WAL→TDE/DWB→file I/O 의무는 무엇인가? | scope-interface-seams |
| 3 | `03-interface-ownership.html#owner-lifetime-ledger` | 각 allocation을 누가 언제 release하는가? | data-ownership-lifetime |
| 4 | `04-current-flush.html#snapshot-boundary` | 현행 CUBRID가 언제 write image를 확정하는가? | core-workflows |
| 4 | `04-current-flush.html#success-redirty-error` | 세 completion 분기가 dirty/LSA를 어떻게 처리하는가? | lifecycle-state-machines, core-workflows |
| 5 | `05-stable-frame-contract.html#five-invariants` | stable frame의 최소 계약은 무엇인가? | concurrency |
| 5 | `05-stable-frame-contract.html#read-is-not-a-request` | `READ`가 무엇을 제공하고 무엇을 제공하지 않는가? | concurrency |
| 6 | `06-concurrency-states.html#actor-matrix` | reader/writer/flusher/victim은 대안마다 통과하는가? | concurrency |
| 6 | `06-concurrency-states.html#freeze-state-machine` | request-owned freeze는 어떻게 종료되는가? | lifecycle-state-machines |
| 7 | `07-durability.html#wal-before-data` | memory correctness와 durability order는 어떻게 결합되는가? | storage-durability-recovery |
| 7 | `07-durability.html#tde-dwb-boundaries` | TDE/DWB copy의 별도 목적은 무엇인가? | storage-durability-recovery |
| 8 | `08-alternatives.html#decision-table` | copy/READ/SX/freeze/WRITE의 비용과 Interface 폭은? | policies-algorithms |
| 9 | `09-errors-pressure.html#terminal-completion` | error/cancel/shutdown/queue-full에서 누가 cleanup하는가? | errors-resource-pressure |
| 10 | `10-performance-experiment.html#measure-before-mode` | copy bytes, writer wait, in-flight 수를 어떻게 재는가? | performance-observability, experimental-validation |
| 10 | `10-performance-experiment.html#promote-summary-correction` | 이전 숫자를 왜 성능 근거로 재사용하지 않는가? | performance-observability |
| 11 | `11-postgresql.html#share-exclusive-gap` | PG의 content lock 출발점이 CUBRID와 왜 다른가? | postgresql-analysis |
| 12 | `12-mysql.html#sx-io-fix-bundle` | InnoDB의 SX 외에 lifetime을 누가 맡는가? | mysql-analysis |
| 13 | `13-comparison.html#responsibility-map` | 같은 이름이 아니라 같은 책임을 비교했는가? | cross-database-comparison |
| 14 | `14-blueprint.html#io-write-freeze-interface` | 독립 구현자가 acquire부터 terminal completion까지 재구현할 수 있는가? | reimplementation-blueprint |
| 14 | `14-blueprint.html#conformance-matrix` | 어떤 race/error test가 계약을 반증하는가? | reimplementation-blueprint |
| 15 | `15-glossary-evidence.html#terms` | 모든 용어와 Unknown이 닫혀 있는가? | glossary-evidence-unknowns |
| 16 | `16-teaching-map.html#central-behaviors` | Claim/Experiment/Quiz/Grill 연결이 완전한가? | teaching-map |

각 장은 `구체적 질문 → 직관 → exact mechanics → invariant/failure → 비교/선택 → 짧은 recap → 다음 장 질문` 순서를 따른다.

## 17. static Quiz concept

정답을 문제 문장이나 script comment에 노출하지 않는다. PostgreSQL/MySQL 서버는 요구하지 않는다.

### Quiz 1 — “이 pointer는 언제 놓아도 되는가?”

- **연결 behavior:** `stable-frame-io-contract`
- **예측:** 네 mode의 `t_call`, `t_return`, `t_complete`, `t_frame_reuse` event card를 주고 각 buffer 안정 구간을 표시하게 한다.
- **실행물:** CUBRID 의존성이 없는 deterministic state-check script 또는 책에 포함된 작은 request timeline checker. 외부 DBMS는 요구하지 않는다.
- **분석:** content stability와 allocation lifetime을 각각 위반하는 schedule을 하나씩 찾게 한다.
- **teach-back:** `O_DIRECT`와 AIO를 한 문장으로 구별하게 한다.
- **한계:** kernel/device 구현이나 실제 CUBRID AIO를 관측하는 실험이 아님을 answer에 명시한다.

### Quiz 2 — “현행 snapshot 뒤 writer가 수정하면?”

- **연결 behavior:** `snapshot-copy-flush`
- **예측:** dirty page workload와 강제 flush/checkpoint 전후 statdump 관측을 예측한다.
- **실행물:** report experiment의 안전한 CUBRID SQL workload를 재사용하되 quiz-owned object와 cleanup을 사용한다.
- **분석:** `snapshot`, `WAL`, `write`, `re-dirty`, `completion(error)` 카드를 올바른 causal order로 놓고 각 dirty/LSA 상태를 적게 한다.
- **핵심 한계:** runtime 카운터는 `memcpy` 위치나 writer/I/O overlap을 직접 증명하지 않는다고 답하게 한다.

### Quiz 3 — “가장 좁은 Interface를 선택하라”

- **연결 behavior:** `stable-frame-io-contract`
- **입력:** (a) sync buffered zero-copy, (b) sync direct zero-copy, (c) copy AIO, (d) frame AIO 네 요구사항.
- **과제:** copy, `READ`+fix, `SX`+pin, `IO_WRITE_FREEZE`, `WRITE`+fix 중 최소 충분 조합을 선택하고 reader/writer/flusher/victim matrix를 채운다.
- **adversarial variation:** completion이 submitter와 다른 thread, queue-full, cancel, re-dirty를 하나씩 추가해 선택이 바뀌는지 설명하게 한다.
- **비교:** 제공된 PG/InnoDB evidence만으로 어떤 항목이 partial analogy인지 분류한다.

### Quiz 4 — “88,779를 믿을 것인가?”

- **목적:** perf metric 검증 습관. B-tree/SX 성능 입증이 목적이 아니다.
- **입력:** 이전 stdout의 summary `88,779`, detailed `879`, 관련 계산/formatting의 짧은 발췌.
- **과제:** scale과 재계산 경로를 따라 101배 관계를 설명하고, 어떤 결론을 폐기해야 하는지 적는다.
- **answer의 마지막 문장:** 이 교정은 현재 flush/AIO 대안의 성능 우열을 증명하지 않는다.

## 18. Live Grill concept와 remediation ladder

질문은 매 user turn에 정확히 하나만 한다. 아래는 concept별 첫 질문 seed이며, 질문 속에 정답을 넣지 않는다.

| mastery concept | 첫 질문 seed | partial/misconception 때 좁힐 축 | 복습 anchor |
|---|---|---|---|
| responsibility/scope/seams | “flusher가 I/O 함수에 pointer를 넘길 때 caller와 page buffer의 의무를 각각 설명해 보세요.” | input buffer와 dirty state를 분리 | `#module-seams` |
| ownership/lifetime | “frame-based AIO에서 frame, BCB, request의 owner와 해제 시점을 각각 말해 보세요.” | content와 identity 중 하나만 질문 | `#owner-lifetime-ledger` |
| lifecycle/state | “dirty page 하나가 제안 freeze를 얻은 뒤 성공, re-dirty, error로 끝나는 세 경로를 설명해 보세요.” | 한 terminal branch만 질문 | `#freeze-state-machine` |
| concurrency | “I/O 중 reader는 통과시키고 writer와 victim은 막으려면 서로 다른 어떤 계약이 필요합니까?” | writer exclusion 또는 pin만 질문 | `#actor-matrix` |
| durability/failure | “immutable image를 만들었는데도 WAL-before-data가 별도로 필요한 이유는 무엇입니까?” | crash 시점 하나 제시 | `#wal-before-data` |
| policy/performance | “copy AIO와 frame AIO 중 하나를 고를 때 최소 세 가지 비용을 어떻게 측정하겠습니까?” | copy bytes, writer wait, memory pressure 중 하나 | `#measure-before-mode` |
| experiment limits | “SQL/statdump 실험이 현행 flush에 대해 증명하는 것과 증명하지 못하는 것을 구분해 보세요.” | 관측 하나의 alternative explanation | `#promote-summary-correction` 또는 experiment anchor |
| PG/MySQL gaps | “InnoDB의 SX 한 개만 CUBRID에 옮기면 부족한 이유를 I/O lifetime 관점에서 설명해 보세요.” | `io_fix` 또는 doublewrite 한 축 | `#sx-io-fix-bundle` |
| capstone | “네 I/O mode를 모두 지원하는 CUBRID writeback Interface를 owner, lifetime, state, ordering, error, test 순서로 설계해 가르쳐 보세요.” | capstone은 모든 concept mastered 뒤 한 번 | blueprint 전체 |

평가 기준:

- mode 이름이 아니라 memory object와 종료 event부터 말하면 좋은 출발이다.
- I1만 말하고 I2/I3를 빠뜨리면 `PARTIAL`이다.
- direct=AIO, SX=durability, latch=pin 중 하나가 나오면 `MISCONCEPTION`이다.
- 같은 concept 세 번째 실패는 `RETEACH`로 기록하고 해당 Quiz 하나를 지정한다.
- learner가 source/experiment 모순을 발견하면 `EVIDENCE_GAP`으로 전환하고 Book을 재검증한다.

## 19. Claim/근거 배치 권고

Pedagogy packet 자체가 implementation Claim을 확정하지 않는다. 최종 저자는 다음 단위를 별도 Claim으로 유지해야 한다.

- CUBRID 현행 snapshot image 생성과 BCB 보호 해제 순서
- `FLUSHING_TO_DISK`, dirty, `oldest_unflush_lsa`의 성공/re-dirty/error 전이
- WAL flush와 data write의 exact ordering
- file I/O가 synchronous이며 input buffer를 언제까지 소비하는지
- TDE output image와 DWB slot의 owner/lifetime
- strict CUBRID `READ`와 writer compatibility, fix/victim interaction
- PostgreSQL `SHARE_EXCLUSIVE`의 content semantics와 I/O-state/lifetime companion
- InnoDB S/SX/X와 `io_fix`/completion/doublewrite의 responsibility split
- 네 I/O mode의 OS-level buffer lifetime 전제
- copy/READ/SX/freeze/WRITE 대안의 inference와 falsifier
- promote summary/detail 101배 교정 사실

Diagram edge, state transition, 비교표 cell마다 이 Claim을 가까이 붙인다. 미래 `IO_WRITE_FREEZE`의 fairness/성능은 `Inferred` 또는 `Unknown`이며 source-confirmed처럼 색칠하지 않는다.

## 20. examined material, contradiction, unknowns, handoff

### 완독/검토 자료

- frozen scope: `f799e05_codex/research/scope.md`
- 이전 Book 핵심 장: `f799e05_claude/index.html`, `chapters/01-orientation.html`, `02-mental-model.html`, `06-flush-frame-stability.html`, `09-policies-algorithms.html`, `11-performance-observability.html`, `13-postgresql.html`, `14-mysql.html`, `15-comparison.html`, `16-blueprint.html`, `17-glossary-evidence.html`
- 이전 Quiz/Experiment의 promote/flush 설명과 raw output
- pinned CUBRID `src/base/perf_monitor.c`, `perf_monitor.h`의 promote summary 계산 및 출력 formatting; 이전 raw output의 `Data_page_total_promote_success`와 `Num_data_page_promote_ext`
- 스킬의 research/evidence, Book, experiment, Quiz/Grill, agent-role, artifact-schema 계약

### 확인된 contradiction

1. 이전 Book은 synchronous `O_DIRECT`와 AIO의 buffer lifetime을 합쳤다. frozen scope는 둘을 명시적으로 분리한다.
2. 이전 Book은 broad `SX`를 AIO의 선행 조건처럼 서술했다. frozen scope는 copy AIO, existing `READ`, dedicated freeze를 동등 후보로 요구한다.
3. 이전 Book은 InnoDB/PG의 named mode를 CUBRID public `SX`와 과도하게 등치했다. 새 비교는 companion I/O state와 lifetime까지 responsibility bundle로 보아야 한다.
4. 이전 Book의 promote 성능 서사는 summary 산식 오류로 약 101배 부풀려진 수치를 사용했다. 새 보고서에서 재사용하면 안 된다.

### source packet에서 최종 확인할 unknown/search gap

- 현행 CUBRID flusher가 snapshot 생성 중 content 안정성을 정확히 어떤 mutex/latch/fix invariant로 얻는가
- `FLUSHING_TO_DISK`가 victim/invalidation/reassignment를 막는 정확한 call path
- sync file write가 DWB on/off 및 TDE 각 경로에서 어느 output buffer를 마지막으로 소비하는가
- DWB slot이 copy를 보관하는지 pointer/frame reference를 보관하는지, slot release event는 무엇인지
- failure 시 dirty/`oldest_unflush_lsa`가 재더티와 겹칠 때 정확히 합쳐지는 규칙
- PostgreSQL의 content lock 외 pin/I/O-in-progress state가 write lifetime을 어떻게 닫는가
- InnoDB `io_fix`와 SX release가 normal/error/cancel/shutdown에서 어떤 completion owner로 끝나는가
- public `SX`와 전용 freeze의 실제 fairness/cache-line/wakeup 비용은 구현·측정 전 Unknown

### 최종 저자 handoff checklist

- orientation에서 “SX 필요?”에 3문장으로 답했는가
- direct/async/copy 축을 먼저 분리했는가
- 네 mode마다 memory object, owner, lifetime 끝 event를 적었는가
- content stability와 frame reuse 금지를 다른 문장으로 설명했는가
- second flusher와 completion owner를 concurrency 표에 포함했는가
- WAL/DWB/TDE를 각각 다른 책임으로 설명했는가
- `READ`의 가능성과 한계를 공정하게 다뤘는가
- dedicated freeze 권고가 public `SX`보다 좁은 이유를 Interface 영향으로 설명했는가
- PG/MySQL을 named latch가 아니라 responsibility bundle로 비교했는가
- promote 88k/4.4회 서술을 모두 제거하고 교정 사례로만 남겼는가
- runtime evidence가 증명하지 못하는 것을 명시했는가
- 모든 그림에 독립적인 한국어 text alternative가 있는가
- Quiz와 Live Grill이 정답 암기가 아니라 owner/lifetime에서 해법을 도출하게 하는가

## 2026-08-11 addendum — overflow OID 설명 순서

쉬운 설명은 다음 순서를 지킨다.

1. `ACTIVE` 하나에 OID가 몰리면 leaf가 head VPID와 `0x2000` flag로 singly-linked overflow chain을 가리킨다.
2. literal CREATE INDEX bulk load와 이후 DML을 먼저 분리한다.
3. AS-IS를 H1 full → H2 full → H3 free의 `WRITE fix/check/next/unfix` 그림으로 보인다. helper max one
   overflow latch, leaf W 유지, found page W-held/no race를 함께 적는다.
4. 새 runtime page가 head에 들어가므로 “모든 insert O(K)”가 아니라 common O(1), periodic/pathological O(K)로
   정정한다.
5. TO-BE는 overflow SX→WRITE로 reader 충돌을 줄이는 후보로만 소개한다. leaf W gate와 O(K)는 남는다.
6. “always succeeds”를 immediate success가 아닌 single SX/new-reader gate/reader drain 조건의 eventual
   no-promoter-failure로 다시 쓴다.
7. 주차장 비유에서는 leaf W를 입구 차단기, overflow latch를 층 문으로 설명해 local SX 이득이 upstream
   gate에 가릴 수 있음을 보여 주고, 비유가 WAL/O(K)/fairness를 설명하지 않는다고 닫는다.

반드시 제거할 오해: unique overflow 불가, page 간 crabbing, caller 공간 재검증, tracker가 병목 자백,
PostgreSQL/InnoDB가 같은 overflow algorithm을 사용한다는 주장.
