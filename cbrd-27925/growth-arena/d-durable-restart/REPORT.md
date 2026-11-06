## 후보 D 결과: 체크포인트 스냅샷과 복구 스캔으로 재시작 lap을 없앤다

**목표.** 같은 양의 live 데이터로 insert/delete를 반복해도 OOS 파일이 끝없이 커지면 안 된다. 제 몫은 재시작이 끼는 두 빈틈이었다. 하나는 크래시와 성장 중 쓰기가 겹치면 `cand_fullboot` 를 포함한 이전 설계가 모두 cap에 닿는다는 점이다. 다른 하나는 재시작 뒤 첫 성장이 할당 경로에서 파일 전체를 한 바퀴 돈다는 점이다.

**결론.** `ckpt_redo` 를 조건부 추천합니다. 실행 중에는 `cand_fullboot` 의 메모리 후보 집합을 그대로 쓰고, 체크포인트마다 그 집합을 로그에 남깁니다. 복구 때는 그 스냅샷에 체크포인트 이후의 빈 페이지 이벤트를 더해 집합을 다시 만듭니다. 그래서 재시작 뒤 lap이 없습니다. 크래시와 쓰기가 겹쳐도 파일은 4페이지를 넘지 않았습니다(MaxPages 5에서 확인). 같은 조건에서 `cand_fullboot` 은 cap에 닿습니다.

하네스가 서브에이전트의 REPORT.md 쓰기를 막아서 파일은 만들지 못했습니다. 아래 본문이 보고서 전체이니 저장해 주세요. 커밋은 하지 않았습니다.

---

### 엔진이 재시작 때 실제로 하는 일 (`d52b1889e`, 소스로 다시 확인)

- `oos_rv_redo_delete` 는 `RVOOS_DELETE` 의 redo이면서 `RVOOS_INSERT` 의 undo다(`recovery.c:881-892`).
- 복구 redo는 레코드 LSA가 페이지 LSA보다 클 때만 redo 함수를 부른다(`log_recovery.c:532`). 페이지가 비워진 뒤 flush됐다면 그 페이지의 redo 함수는 불리지 않는다.
- 지금 엔진은 복구 중에 아무 메모도 남기지 않는다. bestspace 항목이 없어서 `oos_reclaim_note_recovery_delete_locked(NULL, …)` 로 가는데, 이 함수가 도는 `oos_Reclaim_states` 가 재시작 직후 비어 있다(`oos_file.cpp:423-447`, `1362-1382`, `3650-3672`). 재시작 뒤의 보장은 boot lap 하나뿐이다.
- 복구 순서는 analysis(`hdr.chkpt_lsa` 부터, `log_recovery.c:796`), redo(체크포인트 `redo_lsa` 부터, `881`), undo(`894`), 체크포인트(`938`)다.
- 체크포인트는 `LOG_START_CHKPT` LSA를 잡고, `oldest_unflush_lsa` 가 그 LSA 이하인 dirty 페이지를 모두 동기로 flush한다(`log_page_buffer.c:7413-7455`). WRITE latch가 걸린 페이지는 holder가 unfix할 때 flush하고, 체크포인트는 그것을 기다린다(`page_buffer.c:8858`).
- 지금 vacuum은 페이지를 unfix한 뒤에야 메모한다(`oos_file.cpp:3512-3516`). 페이지가 비었음을 latch 안에서 아는 곳은 `3379` 다.
- `RVOOS_DELETE` 와 `RVOOS_INSERT` 레코드에는 VFID가 없다(`oos_file.cpp:3170-3200`).
- ADR-0008의 reclaimer는 재시작 때 다시 돌지만 첫 빈 slot에서 멈춘다. 그래서 크래시 전에 이미 비운 페이지는 다시 메모되지 않는다.
- 메모 상태는 복구 전에 초기화된다(`boot_sr.c:2299` 가 `2435` 보다 먼저).
- redo reader 루프에는 이미 rcvindex 하나를 따로 처리하는 곳이 있다(`RVVAC_COMPLETE`, `log_recovery.c:3707`).

여기서 두 가지가 나온다.
1. redo 함수만으로는 집합을 다시 채울 수 없다. flush된 페이지에서는 redo 함수가 불리지 않는다.
2. 로그 스캔으로도 체크포인트 시작보다 앞에서 비워진 페이지는 볼 수 없다. 그 부분은 다른 곳에 적어 둬야 하고, 후보는 체크포인트 레코드(`ckpt_redo`)나 OOS 헤더 페이지(`hdr_list`)다.

### 1. 후보와 데이터 모양

**`ckpt_redo`.**
- **실행 중.** 파일별 메모리 집합 `{VPID ≤ K, unknown 비트}` 를 쓴다. 페이지를 비운 스레드가 그 페이지 latch를 쥔 채로 집합에 넣는다.
- **체크포인트.** `pgbuf_flush_checkpoint` 가 돌아온 뒤 파일마다 페이지 없는 redo 레코드 `(VFID, unknown, VPID 목록)` 하나를 남긴다. 그리고 "모든 파일을 담았다"는 표시를 함께 남긴다.
- **복구.** redo reader 루프가 `RVOOS_DELETE` 와 `RVOOS_INSERT` 의 CLR을 만나면, 페이지 LSA와 상관없이 그 VPID를 집합에 넣는다. VFID를 알기 위해 두 레코드에 8 B를 더한다.

**`hdr_list` (비교안).** 같은 모양의 목록을 OOS 헤더 페이지에 두고 로그한다. 비우기 전에 넣고, 다시 채우면 뺀다.

**모델.** 이전 에이전트의 부분 모델을 읽고 건전하다고 판단한 뒤 이어서 고쳤다. 바꾼 점은 다섯 가지다.
- rollback undo의 메모를 두 단계로 나눴다. latch를 쥐고 로그하는 단계와, 메모하고 unfix하는 단계다.
- 체크포인트를 시작과 끝으로 나눴다. 복구 스캔은 체크포인트 시작 뒤만 본다고 두었다. 실제 redo 범위보다 좁으니 보수적이다.
- 이전 모델의 "아무 때나 집합을 잃음"을 실제 용량 K로 바꿨다.
- 대조군 `ckpt_early`(flush 전에 스냅샷)와 `hdr_late`(삭제 뒤에 목록 기록)를 넣었다. 순서가 틀리면 실패해야 하는 설계다.
- `hdr_lazy`(다시 채워도 목록에서 빼지 않음)를 넣었다.

### 2. 결과표

유한 모델이고 상수는 Cap=2, L=2, Slack=1, K=MaxPages(넘침 없음)다. 하드웨어는 TLC 3 jobs × 4 workers다. 사이에 "/"가 있는 칸은 crash 없음 / crash 있음 순서다. 시간은 그 행의 모든 TLC 실행을 더한 값이다. 대조군의 "쓰기 있음" 행은 돌리지 않았다. 쓰기 없이도 이미 실패하기 때문이다.

| 설계 | crash | 성장 중 쓰기 | strict | 창 밖 strict | 집합 완전 | 최악 크기 | 최악 검사/성장 | 헛일 없음 | states | 시간 |
|---|---|---|---|---|---|---|---|---|---|---|
| 모든 설계 | 없음 | 없음/있음 | PASS | PASS | PASS | 3 (`hdr_list` 쓰기 4, `hdr_lazy` 쓰기 cap) | 1 (`hdr_*` 3) | PASS (`hdr_lazy` FAIL) | 546–49,540 | ≤26 s |
| `cand_fullboot` | 있음 | 없음/있음 | PASS/PASS | PASS | PASS | 3 / **cap** | 3 / 4 | FAIL | 9,419 / 214,929 | 10 / 24 s |
| `hdr_count` | 있음 | 없음/있음 | PASS | PASS | PASS | 3 / **cap** | 3 / 4 | FAIL | 9,415 / 218,171 | 11 / 25 s |
| `redofn_only` | 있음 | 없음/있음 | FAIL | FAIL | FAIL | cap / cap | 5 / 5 | FAIL | 878,619 / 6,438,390 | 55 / 353 s |
| `redo_bg_slack` | 있음 | 없음/있음 | FAIL(창) | PASS | PASS | cap / cap | 5 / 5 | FAIL | 3,431,419 / 18,255,777 | 115 / 626 s |
| **`ckpt_redo`** | 있음 | 없음/있음 | **PASS** | **PASS** | **PASS** | **3 / 4** | 4 / 5 | FAIL | 33,641 / 1,174,524 | 46 / 124 s |
| `ckpt_early` | 있음 | 없음 | FAIL | FAIL | FAIL | cap | 5 | FAIL | 5,195,535 | 187 s |
| **`hdr_list`** | 있음 | 없음/있음 | **PASS** | **PASS** | **PASS** | **3 / 4** | 3 / 3 | PASS | 850 / 12,240 | 11 / 13 s |
| `hdr_late` | 있음 | 없음 | FAIL | FAIL | FAIL | cap | 1 | PASS | 9,532 | 38 s |
| `hdr_lazy` | 있음 | 없음/있음 | PASS | PASS | PASS | 3 / cap | 3 / 4 | FAIL | 1,372 / 49,540 | 10 / 17 s |

- **MaxPages 5 확인.** `ckpt_redo` 와 `hdr_list` 의 crash+쓰기 행은 최악 크기가 그대로 4였다. state 수도 P4와 똑같다(1,174,524 / 12,240). 5번째 페이지를 쓸 수 있는데도 한 번도 예약하지 않았다는 뜻이다. crash+조용 행도 P5에서 3을 유지했다(`cand_fullboot` 9,419, `ckpt_redo` 33,641, `hdr_list` 850).
- **넘침 행 (K=1, P4).** `cand_fullboot`, `ckpt_redo`, `hdr_list` 모두 결과가 같다. 조용하면 크기 3, 검사 6–7이고 strict PASS다. 쓰기가 있으면 crash와 상관없이 cap이다. `ckpt_redo` 의 crash+쓰기 행은 r12에서 cap을 찾았다. 남은 불변식을 다 도는 마지막 실행은 600 s 제한에 걸렸지만, 그 전까지 찾은 위반은 없다.
- 모든 행이 runner의 EXPECTED 표와 맞았다(exit 0).

### 3. 반례 (가장 짧은 것)

- **`cand_fullboot` / `hdr_count`, crash+쓰기, 39 step.** 재시작이 집합을 지운다. 재시작 lap 동안 writer가 cursor 앞의 페이지를 다시 채우고, 지나간 뒤에 비운다. rollback 하나는 페이지를 latch로 쥐고 있다. 그래서 lap이 아무것도 찾지 못하고 파일이 자란다. 다음 크래시가 그사이 메모를 또 지운다. 반복되면 cap이다.
- **`redofn_only`, 7 step.** vacuum이 page 1을 비우고, page 1이 flush된 뒤 크래시가 난다. redo 함수가 그 레코드를 건너뛰므로 집합은 비어 있는데 완전하다고 주장한다.
- **`redo_bg_slack`, 10 step.** undo가 page 1을 비운 뒤 크래시가 난다. 복구 스캔이 page 1을 적지만, 복구 끝의 체크포인트가 스캔 범위를 옮긴다. 백그라운드 lap이 돌기 전에 두 번째 크래시가 나면 page 1이 사라진다. Slack 창 안의 성장이 page 1을 지나친다. 크래시마다 창이 새로 열리므로 cap이다.
- **`ckpt_early`, 9 step.** undo가 page 1을 비우고 로그한다(latch 유지). 체크포인트가 시작하며 page 1이 없는 집합을 찍는다. 그 뒤 undo가 page 1을 메모하고 unfix한다. 체크포인트가 끝나고 크래시가 나면 page 1은 스냅샷에도 스캔 범위에도 없다.
- **`hdr_late`, 6 step.** undo가 page 1의 삭제를 로그한 뒤, 목록에 적기 전에 크래시가 난다.
- **`hdr_lazy`, 크래시 없음, 쓰기, 38 step.** writer가 목록의 페이지를 성장자가 보기 직전에 채우고, 본 직후에 비운다. 성장자는 그 페이지를 목록에서 떨어뜨리고 파일을 키운다.
- **K=1 넘침 + 쓰기, 50 step.** 첫 lap은 메모가 떨어져 다시 돌고, 다시 돈 lap도 같은 앞채움·뒤비움에 회피당한다. 결국 cap이다.

이 과정에서 넘침 fallback의 버그도 하나 찾았다. `cand_fullboot` 계열 전부에 해당한다. lap 도중 메모가 떨어지면 lap이 끝나도 집합은 완전하지 않다. 그런데 처음 모델은 그 상태로 성장해서 strict 규칙을 깼다. 규칙은 "메모가 떨어진 뒤 끝난 lap은 같은 성장 안에서 한 번 더 돈다"로 고쳤고, 고친 뒤 strict는 PASS다.

### 4. 비용과 구현 크기

**`ckpt_redo` (실행 경로 비용은 `cand_fullboot` 과 같음).**
- **INSERT.** 빈 페이지를 다시 채울 때만 해시 하나를 지운다. `oos_stats_update` 가 이미 잡는 bestspace mutex 아래에서 한다.
- **페이지를 비우는 삭제.** 해시 하나를 넣는다. 로그는 더하지 않는다.
- **성장.** 집합 항목을 빈 페이지가 나올 때까지 검사한다. 모델의 최악은 5회다. 재시작 뒤 full lap은 없다. 크래시 뒤 스냅샷의 낡은 항목은 항목마다 한 번씩만 검사한다. 이 때문에 "헛일 없음"이 FAIL이지만, 비용 상한은 파일 크기가 아니라 스냅샷 크기다.
- **체크포인트.** 집합이 비어 있지 않은 파일마다 레코드 하나를 남긴다(VPID 6 B × K, K=1024면 약 6 KB, 추정).
- **복구.** 해당 레코드 하나마다 해시를 하나 넣는다.
- **구현 크기 (추정, 코드는 쓰지 않음).** `cand_fullboot` 본체가 100–150줄이고 여기에 150–200줄이 더해진다. 5개 파일을 건드린다.
  - `oos_file.cpp`: 메모를 `3512` 에서 latch 안의 `3379` 와 `3650-3672` 로 옮긴다. `3170-3200` 에 VFID를 더한다. 스냅샷 쓰기·redo·dump, 표시 레코드, 복원 후보 검증, 파일 생성·삭제 초기화(`1398-1425`)를 넣는다.
  - `log_page_buffer.c`: `7436-7441` 에 호출 하나.
  - `log_recovery.c`: hook을 `3701-3715`(`RVVAC_COMPLETE` 옆), `3768-3777`(CLR), ADR-0008 전까지는 `3662` 에도 넣는다.
  - `recovery.h` / `recovery.c`: rcvindex 하나를 추가한다.

**`hdr_list`.**
- 페이지를 비울 때와 빈 페이지를 다시 채울 때마다 헤더 페이지 WRITE latch와 로그 레코드가 하나씩 든다. 지금 헤더는 zero-wait로만 잡는데(`oos_file.cpp:1087-1113`), 그런 사건이 모두 그 latch에서 줄을 선다.
- undo 함수 안에서 로그해야 한다. 단, redo 문맥에서는 하면 안 된다.
- 비우기 전에 적어야 하므로 rollback이 쥔 페이지가 목록에 먼저 올라간다. 그래서 성장 한 번에 검사가 2회 헛되고, 크래시 없는 쓰기 설정에서 페이지가 하나 더 든다(최악 4 대 3).
- 구현 크기는 250–350줄로 추정한다.

### 5. 추천

| 설계 | 판정 | 이유 |
|---|---|---|
| **`ckpt_redo`** | **조건부 추천** | 크래시와 쓰기가 겹쳐도 유계이고, 재시작 lap이 없고, 실행 경로 비용은 `cand_fullboot` 과 같다. |
| `hdr_list` | 비추천 | 모델은 통과하지만 hot path 헤더 로그, undo 안 로그, 헤더 latch 경합의 비용을 `ckpt_redo` 대비 이점 없이 치른다. |
| `cand_fullboot`, `hdr_count` | 비추천(이 빈틈 기준) | 크래시+쓰기에서 cap. |
| `redofn_only`, `redo_bg_slack`, `hdr_lazy` | 비추천 | 반례가 있다. |

`ckpt_redo` 의 조건은 다음과 같습니다.
1. 메모는 페이지 unfix 전에 한다. `ckpt_early` 반례가 이유다.
2. 스냅샷은 flush가 끝난 뒤 찍는다.
3. VFID를 레코드에서 얻는다.
4. "모든 파일을 담음" 표시가 없으면 복구 결과를 unknown으로 둔다. 복원된 후보는 페이지 타입과 소유 파일을 확인한다.
5. K를 넉넉히 잡는다. 넘침 fallback은 오늘의 lap처럼 쓰기에 회피당하기 때문이다.

창 밖 strict 규칙은 따로 볼 필요가 없습니다. `ckpt_redo` 에는 재시작 창 자체가 없고, strict 규칙이 모든 성장에서 PASS입니다.

### 6. 모델의 한계

- 모델 범위
  - 파일 하나, 성장자 하나다.
  - rollback latch는 성장 한 번에 새로 하나만 잡는다고 제한했다.
  - in-memory 설계에서는 다시 채운 페이지를 집합에서 바로 뺀다.
- 표현하지 않은 것
  - 복구는 한 단계로 묶었다. 복구 undo와 postpone 재실행이 비우는 페이지는 따로 표현하지 않았다. 같은 코드가 끝의 체크포인트 전에 메모한다고만 가정했다.
  - VFID 부여, 파일 삭제 뒤 VFID 재사용, 스냅샷 크기 제한, "모든 파일" 표시는 모델에 없다.
- 가정과 미확인
  - CUBRID의 체크포인트·WAL 보장은 소스를 읽고 가정했을 뿐 검증하지 않았다. 레코드 LSA가 `redo_lsa` 보다 작으면 페이지가 그 전에 flush됐다는 보장이다.
  - liveness는 보지 않았다.
  - 모델은 코드가 이 설계를 따르는지 보이지 않는다.

### 적용한 원칙

- **Attack the Premise.** 이전 재시작 설계들은 모두 "재시작하면 집합을 잃으니 다시 찾아야 한다"는 전제를 공유했다. 복구가 실제로 보는 범위를 확인해 보니, 빠지는 것은 체크포인트 시작 앞의 사건뿐이었다. 그래서 lap을 싸게 만드는 대신(`redo_bg_slack`) lap을 없애는 쪽을 골랐다.
- **Make Operations Idempotent.** 어느 지점에서 크래시가 나도 집합이 줄지 않고 늘기만 하도록 메모 순서를 정했다. 대조군 두 개로 그 순서가 필요함을 보였다.
- **Model the Domain.** 스냅샷과 스캔 이벤트를 "복구가 다시 만들 집합" 하나로 합쳤다. state가 13.7M에서 1.17M으로 줄었다.
- **Explain the Number.** P4에서 최악 크기 4가 MaxPages와 같았다. 이것만으로는 유계라고 할 수 없어서 P5를 돌렸다. 그 과정에서 runner가 state 수로 진행 줄을 읽던 버그도 찾아 고쳤다.
- **Prove It Works.** runner가 모든 행을 EXPECTED와 비교하고, `--retable` 로 로그에서 표를 다시 만든다.
- **Laziness Protocol.** 새 백그라운드 작업 없이 기존 장치를 다시 썼다. 동기 flush 대기, `RVVAC_COMPLETE` 옆 hook, 페이지 없는 redo 레코드다.

---

`runs/` 아래의 states 디렉터리와 대체된 이전 실행은 지웠습니다. 남은 파일의 spec sha256은 모두 `f005a1f4…` 입니다.

Files are in `/home/vimkim/gh/my-cubrid-docs-CBRD-27925-growth-arena/cbrd-27925/growth-arena/d-durable-restart/`:
- `OosRestartGrowth.tla`
- `run.py`
- `trace.py`
- `runs/p4.table.txt`
- `runs/p5-r4.table.txt`
- `runs/p5-quiet.table.txt`
- `runs/{p4,p5-r4,p5-quiet}/` (cfg, log, `results.json`)
