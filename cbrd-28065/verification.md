# CBRD-28065 검증 기록: 커밋 응답 뒤 서버가 죽으면 커밋이 롤백되는 결함

## Purpose

- 클라이언트가 COMMIT 성공을 받은 트랜잭션은 그 직후 서버가 어떻게 죽어도 재시작 뒤 커밋된 상태로 남아야 한다.
- AS-IS: `logpb_flush_pages()` 는 `nxio_lsa < flush_lsa` 동안만 기다린다. `nxio_lsa` 는 아직 디스크에 쓰지 않은 가장 낮은 LSA이고, `flush_lsa` 는 커밋 레코드가 시작하는 LSA다. 직전 flush가 `nxio_lsa` 를 커밋 레코드의 시작과 같게 만들어 두면, 커밋 레코드가 메모리에만 있는데도 대기가 바로 끝난다.
- TO-BE: 커밋은 자기 커밋 레코드가 디스크에 쓰인 뒤에만 응답한다.

이 문서는 PR 본문에 다 넣지 못한 근거를 모은다. 호출자 점검, 대기가 멈추지 않는 이유, 재현 방법과 수치, 지연 측정이다.

## Implementation

### 원인

`nxio_lsa` 는 "디스크에 없는 가장 낮은 LSA"다. 그래서 LSA `L` 에서 시작하는 레코드는 `L < nxio_lsa` 일 때만 디스크에 있다. 엔진의 다른 곳은 모두 이 기준을 쓴다. 대표가 `logpb_need_wal()` 로, `nxio_lsa <= lsa` 이면 "아직 디스크에 없음"으로 본다. 커밋 대기만 `nxio_lsa == flush_lsa` 를 "디스크에 있음"으로 보았다.

이 상태는 흔하게 생긴다. 트랜잭션 A가 UPDATE를 하고 아직 커밋하지 않았을 때, 다른 트랜잭션 B의 커밋이 로그를 flush하면 A의 UPDATE 레코드까지 디스크에 쓰인다. flush가 끝나면 `nxio_lsa` 는 B의 커밋 레코드 바로 뒤, 곧 다음 레코드가 들어올 자리다. 그 뒤 A가 커밋하면 A의 커밋 레코드는 정확히 그 자리에서 시작한다. 수정 전 코드는 기다리지 않고 응답했다.

### 수정

`logpb_flush_pages()` 의 대기 조건 두 곳(루프 조건과 `gc_mutex` 안에서 다시 보는 조건)을 `logpb_need_wal (flush_lsa)` 로 바꿨다. WAL 검사와 커밋 대기가 같은 함수로 같은 경계를 판정하므로, 두 판정이 다시 어긋날 수 없다. 쓰지 않게 된 지역 변수 `nxio_lsa` 와 그 대입 세 곳을 지웠다. 바뀐 동작은 `nxio_lsa == flush_lsa` 인 경우 하나다. 예전에는 바로 돌아갔고, 이제는 flush 한 번을 기다린다.

같은 변경을 release/11.4, release/11.3, release/10.2 에 그대로 적용했다. 세 라인의 해당 코드와 호출자는 develop과 같다(`test/audit_flush_callers.py` 로 확인).

### 호출자 점검

새 조건에서는 호출자가 넘기는 LSA를 어떤 flush가 반드시 지나가야 한다. 그렇지 않으면 대기가 끝나지 않는다. `test/audit_flush_callers.py` 는 각 `logpb_flush_pages` 호출에서 넘기는 LSA가 어디서 왔는지 출력한다. develop 기준 결과는 다음과 같다.

| 호출 위치 | 기다리는 레코드 | 넘기는 LSA |
| --- | --- | --- |
| `log_change_tran_as_completed` (커밋) | `LOG_COMMIT` | `log_append_commit_log` 또는 `log_append_repl_info_and_commit_log` 가 돌려준 `prior_lsa_next_record` 반환값 |
| `log_change_tran_as_completed` (체크포인트 중 abort) | `LOG_ABORT` | `log_append_abort_log` 가 돌려준 `prior_lsa_next_record` 반환값 |
| `log_append_ha_server_state` | `LOG_DUMMY_HA_SERVER_STATE` | `prior_lsa_next_record` 반환값 |
| `log_append_commit_postpone_obsolete` | `LOG_COMMIT_WITH_POSTPONE_OBSOLETE` | `prior_lsa_next_record` 반환값 |
| `log_complete_for_2pc` (2곳) | `LOG_2PC_COMMIT_INFORM_PARTICPS`, `LOG_2PC_ABORT_INFORM_PARTICPS` | `prior_lsa_next_record` 반환값 |
| `log_2pc_prepare_global_tran` | `LOG_2PC_PREPARE` | `prior_lsa_next_record` 반환값 |
| `log_2pc_append_start` | `LOG_2PC_START` | `prior_lsa_next_record` 반환값 |
| `log_2pc_append_decision` | `LOG_2PC_COMMIT_DECISION` | `prior_lsa_next_record` 반환값 |
| `log_append_commit_postpone` (release 라인만) | `LOG_COMMIT_WITH_POSTPONE` | `prior_lsa_next_record` 반환값. develop은 CBRD-28046 에서 이 대기를 없앴다 |

모든 호출자가 방금 prior list에 넣은 레코드의 시작 LSA를 넘긴다. `log_append_donetime_internal` 이 노드 할당에 실패하면 LSA를 NULL로 둔다. 이 값은 `logpb_flush_pages()` 앞부분의 `LSA_ISNULL` 분기에서 직접 flush 하므로 대기 조건에 닿지 않는다.

`nxio_lsa` 를 목표 LSA와 비교하는 다른 곳도 확인했다. `logpb_need_wal()` 과 이를 쓰는 `logpb_flush_log_for_wal()` (페이지 버퍼, double write buffer, CBRD-28046 의 `log_execute_run_postpone`), CDC의 `cdc_loginfo_producer_execute`, `cdc_find_user`, `cdc_validate_lsa`, HA 로그 전송의 `logwr_pack_log_pages` 는 모두 `lsa < nxio_lsa` 를 "디스크에 있음"으로 본다. `log_prior_has_worker_log_records` 의 `nxio_lsa == prior_lsa` 비교는 prior list가 비었는지를 보는 것이라 내구성 판정이 아니다. 비동기 커밋(`async_commit=yes`)은 설계상 기다리지 않으므로 바뀌지 않는다. 그룹 커밋은 같은 대기 루프를 쓰므로 함께 고쳐진다.

### 대기가 멈추지 않는 이유

다른 스레드가 flush 하지 않아도 대기는 끝난다.

1. 호출자는 `prior_lsa_next_record` 로 레코드를 prior list에 연결한 뒤 `logpb_flush_pages()` 를 부른다.
2. 일반 커밋은 첫 반복부터, 그룹 커밋은 두 번째 반복(최대 1초 뒤)부터 `need_wakeup_LFT` 가 참이다. 반복마다 `gc_mutex` 를 쥐고 조건을 다시 본 뒤 `log_wakeup_log_flush_daemon()` 으로 `log_Flush_has_been_requested` 를 세우고 log flush 데몬을 깨운다. 요청이 서 있으면 데몬 주기는 0이다.
3. 데몬의 `log_flush_execute()` 는 `logpb_flush_pages_direct()` 로 prior list를 모두 로그 버퍼에 붙이고 flush 한다. 이때 모든 레코드가 완성되어 있으므로 `nxio_lsa` 는 `append_lsa`, 곧 대기 레코드의 끝 뒤로 간다. 그다음 `gc_mutex` 안에서 `gc_cond` 를 broadcast 한다.
4. 대기자는 조건 확인부터 `pthread_cond_timedwait` 진입까지 `gc_mutex` 를 쥐므로 broadcast를 놓치지 않는다. 대기 레코드가 prior list에 들어오기 전에 시작한 flush가 요청 플래그를 지워도, 다음 반복(최대 1초 뒤)이 다시 요청한다.
5. 서버 기동 전이거나 데몬이 없으면 처음부터 `logpb_flush_pages_direct()` 로 직접 flush 하고 기다리지 않는다.

같은 이유로, flush 도중에 큰 레코드를 쓰다 만 상태(`nxio_lsa = prev_lsa`)에서 그 레코드가 대기 레코드였던 경우도 이제 기다린다. 수정 전에는 이 경우에도 바로 응답했다. 이 경우는 코드를 읽고 추론했으며 따로 재현하지 않았다.

## Remarks

### Test Plan

모든 재현은 `cub_server` 에 SIGKILL을 보낸 뒤 서버를 다시 띄우고, 응답받은 커밋이 남아 있는지 본다. 스크립트는 CUBRID 환경 변수(`CUBRID`, `PATH`, `CUBRID_DATABASES`)와 실행 중인 DB만 있으면 돈다.

| 스크립트 | 무엇을 하는가 |
| --- | --- |
| [`test/commit_after_flush_repro.py`](test/commit_after_flush_repro.py) | 결정적 재현. 세션 A가 1번 행을 UPDATE만 하고, 세션 B가 2번 행을 UPDATE 후 COMMIT 해서 A의 UPDATE까지 flush 한다. 이어서 A가 COMMIT 하고, 응답을 받자마자 서버를 죽인다. 인덱스가 없는 표를 써서 A의 커밋 레코드가 flush 직후 첫 레코드가 되게 한다 |
| [`test/commit_durability_repro.py`](test/commit_durability_repro.py) | 무작위 재현. 8개 세션이 자기 행에 UPDATE와 COMMIT을 반복하고, 3~12초 뒤 서버를 죽인다 |
| [`test/twopc_attach_repro.py`](test/twopc_attach_repro.py), [`test/twopc.c`](test/twopc.c) | JIRA 댓글(2026-11-18)의 2PC 시나리오. C API로 2PC 트랜잭션을 준비하고 서버를 죽인 뒤, 다른 클라이언트가 붙어 커밋하고 다시 서버를 죽인다. 그 트랜잭션이 준비 상태로 다시 나타나면 손실이다 |
| [`test/latency.py`](test/latency.py), [`test/commit_lat.c`](test/commit_lat.c) | C API로 INSERT 한 건과 `db_commit_transaction` 을 반복하며 커밋 호출 시간을 잰다. 서버의 `Num_file_iosynches` 와 `Num_tran_commits` 차이로 커밋당 fsync 횟수도 낸다 |

### 재현 결과

각 라인은 같은 빌드 옵션의 수정 전(base)과 수정 후(fix) 빌드를 같은 DB와 같은 매개변수로 돌렸다. 숫자는 "응답받은 커밋을 잃은 횟수 / 서버를 죽인 횟수"다.

| 라인 | 빌드 | 결정적 재현 base | 결정적 재현 fix | 무작위 재현 base | 무작위 재현 fix | 2PC base | 2PC fix |
| --- | --- | --- | --- | --- | --- | --- | --- |
| develop `86b3c49c10` | debug | 20 / 20 | 0 / 20 | 1 / 20 | 0 / 20 | 5 / 5 | 0 / 5 |
| develop `86b3c49c10` | release | 20 / 20 | 0 / 20 | - | - | - | - |
| release/11.4 `28b98c3496` | debug | 20 / 20 | 0 / 20 | - | - | - | - |
| release/11.3 `15360995b5` | debug | 20 / 20 | 0 / 20 | - | - | - | - |
| release/10.2 `45e25f1d35` | debug | 16 / 20 | 0 / 20 | - | - | - | - |

무작위 재현은 develop debug에서 수정 전 20번 중 1번 손실을 보였다(세션 하나가 16565를 응답받았는데 재시작 뒤 16564). 결정적 재현은 같은 결함을 매번 일으키므로 백포트 라인은 결정적 재현으로 확인했다.

### 지연 측정

release 빌드 두 개(base, fix)를 같은 DB에 번갈아 띄우고 6라운드를 쟀다. 라운드마다 순서를 바꿨고(base-fix, fix-base, ...), 각 빌드에서 1세션 × 3000커밋과 8세션 × 1000커밋을 돌렸다. 서버를 띄울 때마다 8세션 × 500커밋을 예열로 돌리고 버렸다. 커밋 시간은 클라이언트가 `db_commit_transaction` 호출 앞뒤로 잰 값이고, 세션마다 처음 50건은 뺐다. DB는 `/home` 보다 fsync 시간이 고른 NVMe 볼륨에 두었다(4 KiB 동기 쓰기 300번이 `/home` 은 0.2~3.5초, NVMe는 1.5~1.8초). 표의 값은 6라운드의 중앙값이고 괄호 안은 최소와 최대다.

| 세션 수 | 빌드 | 라운드 | 커밋 p50 (µs) | 커밋 평균 (µs) | 커밋 p99 (µs) | 커밋/초 | 커밋당 fsync |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | base | 6 | 2060.5 (1216-3432) | 2044.85 (1662.1-3999.1) | 6303 (3793-10826) | 344.8 (201.5-433.6) | 0.999 (0.999-0.999) |
| 1 | fix | 6 | 1319 (1211-4162) | 1984.2 (1501-4770.2) | 7061 (3056-13922) | 396 (175.9-452.1) | 0.999 (0.999-0.999) |
| 8 | base | 6 | 3427.5 (2290-7434) | 3494.5 (2153-7691.5) | 9639 (4521-18403) | 1943.15 (867.6-2625.3) | 0.2575 (0.252-0.291) |
| 8 | fix | 6 | 3649 (2288-5057) | 4063.85 (2104.9-6591.8) | 11181 (3717-18202) | 1653.75 (1016.9-2751.6) | 0.255 (0.251-0.272) |

- 같은 빌드의 라운드 간 차이가 빌드 간 차이보다 크다. 8세션 처리량은 base가 868~2625, fix가 1017~2752커밋/초였다. 같은 라운드의 두 빌드를 비교하면 fix가 6번 중 4번 앞섰다. 측정 동안 호스트의 1분 load average는 다른 사용자 작업 때문에 35~143 사이를 오갔다. 이 측정으로는 두 빌드의 차이를 구분할 수 없다.
- 커밋당 fsync 횟수는 두 빌드가 같다(1세션 0.999, 8세션 약 0.255). 수정은 flush 횟수를 늘리지 않는다.
- 수정으로 동작이 바뀌는 커밋을 직접 셌다. base 코드에서 대기가 끝난 시점에 `nxio_lsa == flush_lsa` 이면 세는 임시 계측을 넣은 release 빌드다(커밋하지 않음). 1세션 3000커밋은 두 번 모두 0건, 8세션 8000커밋은 184건(2.3%)과 228건(2.9%)이었다. 이 커밋들만 수정 뒤 flush 한 번을 더 기다린다. 그래서 8세션 평균 커밋 지연의 증가는 1~3% 정도로 추정한다(추론). 이 값은 위 측정의 잡음보다 작다. 1세션에는 영향이 없다(측정).
- 같은 숫자는 결함의 빈도이기도 하다. 수정 전 8세션 부하에서는 응답한 커밋의 2~3%가 응답 시점에 커밋 레코드가 디스크에 없었다.

### 제한 사항

- 11.2에도 같은 코드가 있지만 대상 버전이 아니어서 고치지 않았다.
- HA 복제(applylogdb)에 주는 영향은 따로 시험하지 않았다.
- 백포트 라인에서는 2PC 시나리오와 무작위 재현을 돌리지 않았다. 결정적 재현만 돌렸다.
