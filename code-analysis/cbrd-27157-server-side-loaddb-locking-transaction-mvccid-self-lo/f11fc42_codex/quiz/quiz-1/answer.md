# Quiz 1 모범 답안과 해설

resource는 `dba.bu_target` class OID다. server-side loader의 session transaction이 `BU_LOCK` holder이고, 별도 csql transaction이 `SCH_M_LOCK` waiter다. owner는 잠깐 실행한 worker thread가 아니라 transaction이다. FIFO EOF로 loaddb session이 끝나 BU lock을 놓으면 ALTER가 다시 진행한다.

unrelated `bu_control` UPDATE가 성공하는 것은 DB 전체가 멈춘 것이 아니라는 negative control이다. 같은 dump에 class 이름, BU holder, SCH_M waiter가 함께 있고 종료 뒤 attribute가 생겨야 positive control이 완성된다. 시간만으로 resource나 mode를 확정하면 안 된다.

이 한 번의 실행은 선택한 BU/SCH_M 조합만 확인한다. 전체 compatibility table이나 모든 scheduler interleaving을 증명하지 않는다. session transaction ownership의 내부 연결은 lockdb의 `loaddb` transaction 표시와 고정 소스를 함께 읽어야 한다.

흔한 오답은 `BU_LOCK`을 “모든 DB 작업을 막는 bulk 모드”로 보는 것이다. 실제 판단에는 resource, mode, owner, waiter, lifetime 다섯 가지가 모두 필요하다.
