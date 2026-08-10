# quiz-2 답안

## Q1 — 상태와 영속

상태는 블록 엔트리(VACUUM_DATA_ENTRY)의 `blockid` 상위 3비트에 인코딩되어 vacuum data
페이지(영속, WAL 보호)에 저장된다: `VACUUMED`(0x8000…), `IN_PROGRESS`(0x4000…),
`AVAILABLE`(리터럴 0). `INTERRUPTED`(0x2000…)는 셋과 직교하는 **플래그**다 —
`set_interrupted()` 는 상태를 AVAILABLE 로 되돌리면서 플래그를 켠다(vacuum.c:8358-8363).
"재배포 가능(AVAILABLE)"과 "이전에 중단됨(INTERRUPTED)"이 동시에 참일 수 있어야 하기
때문이다. 엔트리에는 blockid/start_lsa/두 MVCCID 외에 **블록 내 위치 필드가 없다**
(`CUBRID-C010`, ch05).

## Q2 — 정상 셧다운과 재처리

(1) worker 루프가 매 레코드마다 `thread_p->shutdown` 을 검사하고 참이면 블록을 버린다
(vacuum.c:3493-3498). (2) 미완 블록의 `start_lsa` 는 전진하지 않는다 — 소스의 TODO
(vacuum.c:3766-3767)가 "같은 로그 데이터를 다시 처리하게 됨"을 자인한다. 결과: 블록은
AVAILABLE+INTERRUPTED 로 되돌아가 다음 디스패치 때 처음부터 재주행된다(`CUBRID-C011`).

## Q3 — 아니다 (경고 부재 ≠ 안전)

`is interrupted!` 경고는 master 가 종료 전에 finished-job 큐를 소비한 경우에만 남는다.
소비하지 못하면 블록은 vacuum data 에 IN_PROGRESS 로 남고, 다음 부팅의
`vacuum_data_load_and_recover` 가 조용히 INTERRUPTED 로 바꾼다(vacuum.c:4400-4403).
재주행은 어느 쪽이든 일어난다. 실증: 이번 experiment-2 는 경고 0건에서 12,432건을
재삭제했다(`CUBRID-C012`). states.sh 의 출력이 이 비대칭을 보여준다.

## Q4 — 블록 단일 sysop 이 안 되는 세 가지

1. VACUUMED 표기는 여전히 master 가 비동기로 기록한다 — sysop 커밋과 표기 영속화 사이의
   중단에서 같은 재주행이 남는다(창이 좁아질 뿐).
2. `oos_delete_chain` 은 커밋 전에 페이지를 unfix 하고 bestspace 에 재등록한다 — 커밋 전
   빈 슬롯 노출 창이 레코드 단위에선 마이크로초, 블록 단위에선 블록 처리 시간 전체가 되고,
   abort 시 undo 의 원-슬롯 복원이 남의 슬롯과 충돌할 창도 같이 커진다(ch08).
3. 로그 수십 페이지 분량의 무한계 sysop 은 vacuum 의 짧은-시스템-트랜잭션 설계와 충돌한다.

## teach-back 모범 답안 (요지)

heap 슬롯은 MVCC 헤더를, btree 엔트리는 키+MVCC info 를 **자기 몸에** 지닌다. 재시도가
같은 주소에 도착해도 판정을 점유자의 자기 증언에서 다시 유도하므로, 재사용된 슬롯의 새
점유자는 "살아 있음"을 스스로 증언해 보호된다. vacuum 이 지연 삭제하는 대상 중 OOS 청크만
그런 데이터가 없어서, 같은 재시도 조건이 손상이 된다(ch09, `CUBRID-C041`).

## 이 퀴즈가 증명하지 않는 것

로그 카운트는 재처리의 **간접** 증거다(직접 증거는 experiment-2 의 재삭제 집합).
또한 states.sh 는 최신 로그 파일 하나만 보므로, 실험을 여러 번 반복했다면 이전 부팅
주기의 기록은 포함하지 않는다.
