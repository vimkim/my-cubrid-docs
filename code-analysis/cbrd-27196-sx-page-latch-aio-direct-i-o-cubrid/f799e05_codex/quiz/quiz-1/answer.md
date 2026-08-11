# Quiz 1 — 해설

`quiz_rows`는 2,000이고 `Num_data_page_dirties`는 0보다 커야 한다. 이는 SQL mutation이 buffer page를
dirty로 만든 runtime 사실을 보여 준다. 값의 정확한 크기는 내부 page 접근 횟수까지 세므로 row 수와
같을 필요가 없다. 관련 Claim은 `CUBRID-C006`이다.

이 출력만으로 snapshot `memcpy`를 증명할 수는 없다. SQL/histogram은 함수 안의 instruction이나 BCB
mutex 해제 시점을 관찰하지 않는다. `pgbuf_bcb_flush_with_wal`의 plain-page `memcpy`, 그 뒤 BCB unlock,
WAL flush, DWB/datafile write 순서는 pinned source Claim `CUBRID-C002`와 `CUBRID-C004`가 증명한다.

`Num_data_page_iowrites`도 unique page 수가 아니다. DWB는 같은 logical page image를 doublewrite volume과
home volume에 기록하는 단계가 있고 여러 write 지점이 같은 counter를 증가시킨다. 따라서 실험 oracle은
`after > before`라는 활동 여부까지이며, 증가량을 “정확히 N pages flushed”로 번역하면 안 된다.

현행 방식의 핵심은 두 memory object의 분리다. snapshot image A를 BCB 보호 아래 확정하면 sync write가
A를 읽는 동안 live frame B는 나중 writer가 수정할 수 있다. B의 새 수정은 re-dirty로 남고, A의 성공이
B의 새 상태를 clean으로 지워서는 안 된다. “copy이므로 무조건 안전”이 아니라 image lifetime과 dirty
state machine이 함께 안전하게 만든다.

흔한 오답은 `Num_data_page_dirties > 0`을 “disk write 완료”로 해석하는 것이다. dirty는 memory image가
disk보다 새롭다는 뜻이지 durability 완료가 아니다. 이 Quiz는 AIO, writer overlap의 실제 schedule,
사본 비용, `READ`/`SX`/freeze 대안의 성능을 증명하지 않는다.

## failure와 crash 해설

snapshot 뒤 WAL 전 crash에서는 새 image가 datafile에 제출되지 않아야 한다. restart는 이전 disk page와
WAL recovery를 사용한다. WAL 뒤 data 전 crash에서는 redo log가 새 변경의 복원 근거다. DWB가 durable하고
home write가 torn이면 `dwb_load_and_recover_pages`가 유효 DWB image로 home page를 다시 쓰고 volume을
sync할 수 있다. home write 뒤 BCB cleanup 전 crash에서는 volatile `FLUSHING`은 사라지며 disk page LSA와
WAL이 판정 근거다. 이 때문에 BCB flag를 persistent truth처럼 복원하는 답은 틀리다. 관련 Claim은
`CUBRID-C004`, `CUBRID-C015`다.

TDE 조기 실패가 common rollback을 우회하면 이미 set된 `FLUSHING`과 clear된 이전 `DIRTY`, flush waiter
wakeup이 정상 종료되지 않을 수 있다. 이는 source-confirmed defect candidate `CUBRID-C010`이며 실제
발생률이나 fault-injection reproduction은 이 Quiz가 증명하지 않는다.
