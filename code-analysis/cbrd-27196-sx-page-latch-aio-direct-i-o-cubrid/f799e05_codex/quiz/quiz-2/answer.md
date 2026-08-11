# Quiz 2 — 해설

네 lifetime의 답은 다음과 같다.

1. synchronous buffered + live frame: blocking call 반환까지.
2. synchronous `O_DIRECT` + live frame: 역시 blocking call 반환까지. direct는 page-cache 우회 축이지
   async라는 뜻이 아니다.
3. AIO + copy: terminal completion까지 copy가 살아 있어야 하며 live frame은 submit 뒤 바뀌어도 된다.
4. AIO + live frame: terminal completion까지 frame의 content와 identity가 모두 안정해야 한다.

따라서 copy AIO의 최소 계약은 request-owned immutable copy다. sync live-frame write는 strict `READ`가
모든 writer와 충돌한다는 source 계약과 retained fix/pin, single-flusher state를 함께 만족하면 generic
SX 없이도 가능하다. frame AIO는 completion까지 writer·두 번째 flusher·victim을 막고 다른 thread가
terminal transition을 끝낼 수 있는 request-owned 상태가 필요하다. 이 범위만 보면 dedicated
`IO_WRITE_FREEZE` + in-flight reference가 가장 좁은 Interface 후보다. 이는 현재 구현 사실이 아니라
근거가 있는 설계 권고이며 실제 fairness/성능은 미측정이다.

`READ` latch만으로 부족할 수 있는 이유는 content exclusion과 request lifetime이 다르기 때문이다.
현재 holder/fix가 submitter thread에 묶여 있다면 다른 completion thread가 release와 dirty/error/wakeup을
안전하게 끝낼 owner token이 없다. latch가 writer를 막더라도 frame reuse를 별도 reference가 막지 않으면
같은 주소가 다른 VPID를 담은 뒤 옛 completion이 새 page 상태를 건드릴 수 있다.

PostgreSQL은 SHARE_EXCLUSIVE 외에 buffer pin과 I/O state가 있고, InnoDB는 SX 외에 `io_fix`와
doublewrite/completion protocol이 있다. 이름 하나만 옮기면 lifetime과 single-completion 책임이 빠진다.
관련 비교 Claim은 `PG-C001`, `MYSQL-C001`, `CMP-C002`다.

흔한 오답은 “direct라서 completion까지”, “AIO라서 live frame freeze”, “SX라서 WAL까지 해결”이다.
세 문장 모두 서로 다른 축이나 책임을 섞는다. 이 Quiz의 SQL은 dirty page를 만들 뿐 실제 direct I/O,
AIO, zero-copy 또는 대안 성능을 관찰하지 않는다.

## actor matrix 정답

| case | reader | writer | 두 번째 flusher | victim/reuse | completion owner |
|---|---|---|---|---|---|
| sync live frame + READ/fix | 허용 | call return까지 대기 | FLUSHING에서 대기/skip | fix 때문에 금지 | submitter call stack |
| sync live frame + WRITE | 대기 | 대기 | 대기/skip | fix 때문에 금지 | submitter call stack |
| copy AIO | 허용 | 허용, 새 DIRTY | active request에서 대기/skip | live frame은 정책상 가능하나 BCB generation 검증 필요 | request/callback |
| frame AIO + freeze/ref | 허용 | terminal까지 대기 | active request에서 대기/skip | io_ref 때문에 금지 | request terminal CAS 승자 |

content stability, single flusher와 identity stability를 한 칸에 합치면 안 된다. copy AIO도 old completion이
새 BCB state를 건드리지 않도록 VPID/generation 확인은 필요하다.

## failure/concurrency 정답

1. publish 전 allocation/TDE 실패는 BCB state를 바꾸지 않고 반환한다.
2. queue full은 freeze 전에 확인하고 configured copy/sync fallback으로 간다.
3. submit failure는 동기 terminal branch가 DIRTY/LSA, FLUSHING, freeze/ref, waiter를 정확히 한 번 정리한다.
4. callback error도 success처럼 terminal owner 하나만 cleanup하지만 clean으로 publish하지 않는다.
5. cancel 요청은 terminal event가 아니다. kernel이 buffer를 더 읽지 않는다는 확인 전 reuse하면 안 된다.
6. callback 두 번 중 terminal CAS 승자만 cleanup하고 loser는 no-op이어야 한다.
7. shutdown은 submit gate를 닫고 in-flight=0을 기다린 뒤 page/request pool을 파기한다.

모든 scheduler order에서 유지할 invariant는 reader의 일관된 bytes, completion 전 writer/reuse 금지,
동일 generation single flusher, WAL-before-data, exactly-once cleanup, publish-before-wakeup이다.

## policy·비교·재구현 정답

copy AIO memory 상한은 대략 `N × (IO_PAGESIZE + request metadata)`다. frame AIO는 page-size copy 대신
최대 `N` frame을 replacement 불가로 만든다. TDE-heavy workload는 어차피 output allocation이 필요해
plain zero-copy 이득이 줄 수 있다. 작은 pool/hot writer에서는 frame pin과 writer p99가 악화될 수 있다.
반증 metric은 copy bytes/time, in-flight bytes/frames, writer p95/p99, victim miss, throughput이다.

PostgreSQL current ordinary write와 InnoDB AIO wiring은 `no equivalent`다. PostgreSQL의 SX+pin과
InnoDB SX+io_fix 책임은 `partial analogy`다. InnoDB compressed/temp 예외를 normal path와
`equivalent`로 분류하면 안 된다. CUBRID/PG/InnoDB terminal error도 rollback/BM_IO_ERROR/fatal policy가
달라 `no equivalent`다. 관련 Claim은 `CMP-C001`~`CMP-C005`다.

허용 가능한 pseudocode는 11장의 total state table과 같아야 한다. 핵심은 queue slot을 먼저 확보하고,
BCB 아래 PREPARING state를 publish하고, WAL 뒤 submit하며, submit failure도 `complete`와 같은 terminal
cleanup을 쓰는 것이다. success/error/cancel은 atomic terminal owner 하나만 `COMPLETING→IDLE`을 수행한다.

최소 conformance set은 다음에서 여섯 개 이상이다: reader 진행, writer/victim/second-flusher 차단,
success+re-dirty 보존, allocation/TDE/WAL/submit failure rollback, callback error, cancel terminal 확인,
double callback exactly-once, queue-full memory bound, TDE/DWB output lifetime, shutdown drain, WAL/DWB/home
각 crash point restart. 실제 대안 code가 없으므로 model output은 설계 consistency만 보며 engine correctness나
성능을 증명하지 않는다.

## B-tree overflow OID checkpoint 해설

AS-IS는 leaf WRITE를 유지한 채 H1을 WRITE fix하고, full이면 다음 VPID를 지역 변수에 복사한 다음 H1을
unfix한다. H2도 같은 순서로 놓은 뒤 H3를 WRITE fix한다. 따라서 helper가 동시에 보유하는 overflow latch는
최대 한 장이고 overflow-page crabbing은 아니다. 그러나 leaf WRITE는 전체 순회 동안 남아 있다.

H3에서 공간을 찾으면 WRITE를 놓지 않은 채 caller로 반환하고, caller가 같은 latch 아래 OID를 삽입한 뒤
unfix한다. 그러므로 H2를 놓고 H3을 잡는 구간은 있어도, 이미 잡아 반환한 H3 공간을 다른 writer가 먼저
채우는 race나 재검증은 없다.

런타임에서 새 overflow page는 leaf 바로 뒤의 head로 들어가고 새 OID 하나를 담는다. 이후 INSERT는 새
head가 찰 때까지 보통 첫 page에서 끝난다. O(K)는 head를 포함해 앞 page가 모두 찬 증설 시점, bulk-load가
만든 chain 끝의 partial page를 찾는 구간, 또는 delete hole이 깊은 page에만 있는 fragmented 상태에서
나타날 수 있다. 따라서 정확한 표현은 “한 호출의 worst case O(K), 일반 append는 head에서 O(1)에 가깝고
주기적 tail-latency spike 가능”이다.

TO-BE에서는 H1과 H2를 SX로 읽을 때 그 overflow page의 READ reader는 공존할 수 있다. 두 번째 inserter는
SX/SX가 충돌하므로 첫 번째 inserter가 지나간 page에서 기다릴 수 있다. H3에서 첫 inserter는 SX를 유지한
채 WRITE를 요청하고, 기존 reader가 빠진 뒤 삽입한다. “항상 성공”은 즉시 성공이 아니라, page당 SX owner가
하나이고 승격 대기 중 신규 reader admission을 닫으며 기존 reader가 결국 빠지고 latch-order cycle이 없을
때 경쟁 promoter 때문에 실패·재시작하지 않는 eventual 획득이라는 뜻이다.

overflow-only SX가 줄일 후보는 지나가는 overflow page에서 이미 진행 중인 READ와의 짧은 충돌이다. 남는
비용은 O(K) 주소 탐색, page별 fix/unfix, SX/SX에 따른 inserter 충돌, 그리고 upstream leaf WRITE gate다.
표준 range scan도 leaf READ를 보유한 채 overflow를 읽으므로 leaf 충돌이 SX 효과를 가릴 수 있다. 이
reasoning은 `CUBRID-C016`~`CUBRID-C021`에 연결되며, 기존 Quiz runtime은 성능을 검증하지 않는다.
