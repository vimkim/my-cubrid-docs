# Quiz 2 — 어떤 I/O에 어떤 계약이 필요한가

## 학습 목표와 준비

dirty page를 만든 뒤 I/O 방식의 세 직교 축(cache 경로, completion 방식, 제출 memory)을 분리하고,
copy·`READ`+fix·`SX`+pin·`IO_WRITE_FREEZE`·`WRITE` 중 최소 충분 계약을 고른다. `cubrid`, `csql`이
PATH에 있고 quiz-owned DB `sxq2codex`가 없어야 한다. 예상 시간은 25분이다.

관련 장/Claim: `chapters/02-mental-model.html#four-io-modes`,
`chapters/06-policy.html#stable-frame-io-contract`, `CUBRID-C007`, `CMP-C002`.

## 먼저 예측하기

다음 네 case마다 I/O가 읽는 memory object와 그 object를 놓아도 되는 마지막 event를 적는다.

1. synchronous buffered write + live frame
2. synchronous `O_DIRECT` + live frame
3. AIO + immutable snapshot copy
4. AIO + live frame

아직 latch 이름은 고르지 말고 `call return` 또는 `terminal completion` 중 하나로 lifetime 끝을 표시한다.

## 실행 절차

```bash
bash run.sh
python3 simulate_contract.py
```

실행은 작은 update workload로 “논의 대상이 실제 dirty buffer page”임을 확인할 뿐, 미래 AIO 구현을
구현하지 않는다. 두 번째 command는 engine evidence가 아닌 deterministic state-model이다. 예측을 먼저
쓴 뒤 model의 terminal state가 불변식을 만족하는지 대조한다. DB 스크립트는 자신이 만든
`sxq2codex`만 정리한다.

## 설계 표 채우기

각 case에 대해 다음 다섯 actor를 표로 채운다: reader, writer, 두 번째 flusher, victim/reuse,
completion thread. `허용`, `대기`, `해당 없음` 중 하나를 쓰고 이유를 한 줄씩 적는다.

그 다음 아래 선택지에서 최소 충분 조합을 고른다.

- immutable copy + request-owned lifetime
- strict `READ` + retained fix
- generic `SX` + in-flight pin
- dedicated `IO_WRITE_FREEZE` + in-flight reference
- retained `WRITE`

## 분석과 teach-back

1. synchronous `O_DIRECT`와 AIO의 buffer 안정 구간이 다른 이유는 무엇인가?
2. copy-based AIO에서 live frame writer를 막지 않아도 되는 이유는 무엇인가?
3. CUBRID `READ`가 content stability에는 충분할 수 있지만 AIO request Interface로는 모자랄 수 있는
   이유를 owner와 completion thread로 설명하라.
4. frame-based AIO에서 writer만 막고 victim/reuse를 허용하면 어떤 identity bug가 생기는가?
5. PostgreSQL SHARE_EXCLUSIVE와 InnoDB SX를 CUBRID generic SX와 “같다”고 단정할 수 없는 companion
   state는 무엇인가?

## edge/failure/concurrency 변형

각 사건에서 reader, writer, 두 번째 flusher, victim, completion의 상태와 cleanup owner를 적는다.

1. request allocation 또는 TDE output 생성이 publish 전에 실패한다.
2. queue가 full이다.
3. frame을 freeze한 뒤 AIO submit이 실패한다.
4. I/O callback이 error를 반환한다.
5. cancel을 요청했지만 OS terminal completion은 아직 오지 않았다.
6. 같은 request callback이 두 번 전달된다.
7. in-flight request가 있는 동안 shutdown이 시작된다.

허용 scheduler order는 여러 개일 수 있다. 답은 순서 하나가 아니라 “절대 깨지면 안 되는 invariant”로 쓴다.

## policy·비교·작은 재구현 과제

1. copy AIO와 frame AIO의 peak memory/replacement 비용을 `N`과 `IO_PAGESIZE`로 식으로 적는다.
2. TDE-heavy, 작은 buffer pool, hot-page writer workload에서 어떤 policy가 불리할지 가설과 반증 metric을 적는다.
3. PostgreSQL current write-AIO, InnoDB compressed/temp path, 세 엔진 terminal error policy를 각각
   `equivalent`, `partial analogy`, `no equivalent` 중 하나로 분류한다.
4. 다음 signature를 기준으로 `PREPARING`, `SUBMITTED`, `COMPLETING`, `IDLE` 모든 terminal branch를
   포함한 20줄 이내 pseudocode를 작성한다.

```text
prepare(page, policy) -> request | error
submit(request) -> submitted | synchronous_failure
complete(request, success | io_error | cancelled)
```

5. 이 구현의 conformance test를 최소 6개 설계한다. 반드시 writer/victim/second flusher, re-dirty,
   submit error, cancel/double callback, shutdown/crash 중 네 범주 이상을 포함한다.

## B-tree overflow OID reasoning checkpoint

`status='ACTIVE'`인 행이 매우 많고, index 생성 뒤 같은 key를 다시 INSERT한다고 하자. leaf record는
`H1 → H2 → H3` overflow chain의 head를 가리킨다. `H1`, `H2`는 full이고 `H3`에만 공간이 있다.
먼저 `chapters/06-policy.html#btree-overflow-oid-case`를 읽지 않고 답을 적은 뒤 소스 설명과 대조한다.

1. AS-IS 탐색 순서를 `fix → 확인 → next 복사 → unfix`로 그리고, helper가 동시에 보유하는 overflow
   latch의 최대 수와 별도로 계속 보유하는 latch를 적어라.
2. H3는 어떤 latch 상태로 caller에 반환되는가? 다른 writer가 그 공간을 먼저 채워서 caller가 다시
   검사해야 하는가?
3. 새 overflow page가 chain head에 들어간다면 왜 “chain이 K장이므로 모든 INSERT가 O(K)”가 아닌가?
   O(K)가 되는 두 상황을 적어라.
4. SX가 READ와 호환되고 SX/SX·SX/WRITE는 충돌한다고 하자. H1~H3를 TO-BE로 다시 그리고, reader와
   두 번째 inserter가 각각 어디서 진행하거나 기다리는지 적어라.
5. SX→WRITE를 “즉시 성공”이라고 부를 수 없는 이유와, 경쟁 promoter에 의한 실패·재시작 없이 eventual
   획득하려면 필요한 조건 두 가지를 적어라.
6. overflow-only SX가 없애는 비용과 남기는 비용을 구분하라. 반드시 O(K), fix/unfix, leaf WRITE,
   same-leaf writer 중 세 항목 이상을 사용한다.

이 checkpoint는 source reasoning 과제다. 기존 `run.sh`와 `simulate_contract.py`는 overflow chain이나 SX
성능을 실행하지 않는다.

## 안전한 정리

`run.sh`는 등록된 동일 이름이 있으면 중단한다. 자신이 생성한 경우에만 EXIT trap에서 삭제한다.
`simulate_contract.py`는 stdout만 쓰고 file/process/database를 만들지 않는다.
