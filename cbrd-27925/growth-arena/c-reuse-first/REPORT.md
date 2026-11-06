## c-reuse-first: 빈 페이지를 반환하지 않고 바로 재사용하는 후보

이 답이 `REPORT.md` 본문입니다. 하네스가 서브에이전트의 보고서 파일 작성을 막아서 파일을 만들지 못했습니다. 아래 내용을 `cbrd-27925/growth-arena/c-reuse-first/REPORT.md` 로 저장해 주세요. 커밋은 하지 않았습니다. 엔진 소스는 `feature/oos-merge` `d52b1889e` 이고 읽기만 했습니다.

**목표.** live 데이터가 일정한 churn에서 OOS 파일이 끝없이 커지면 안 됩니다. 사용자는 강한 규칙이 INSERT·UPDATE 처리량을 깎을까 걱정합니다. 이 후보는 dealloc sysop과 그동안 잡는 헤더 WRITE latch를 INSERT 경로에서 빼면서도 같은 보장을 지키는지 봅니다.

**결론.** 조건부 추천입니다. 모델의 모든 설정에서 `cand` 와 같은 보장을 지키고, 빈 페이지를 다시 쓸 때 sysop이 없습니다. 조건은 다섯 가지입니다.
- ADR-0008이 먼저 들어가야 합니다.
- INSERT rollback이 파일 ID를 알도록 로그를 바꿔야 합니다.
- 다시 채워진 페이지는 그 자리에서 바로 집합에서 빼야 합니다.
- 재시작 뒤 lap이 끝나면 집합을 한 번 더 읽어야 합니다.
- 처리량 개선은 아직 소스 판독 추정이라 측정이 필요합니다.

### 1. 후보와 데이터 형태

빈 페이지를 `file_dealloc` 으로 돌려주지 않습니다. 페이지가 비는 두 지점에서 그 VPID를 파일별 정확한 집합 `emptied` 에 넣습니다. bestspace가 페이지를 찾지 못한 INSERT는 `file_alloc` 전에 이 집합에서 하나를 꺼냅니다. 그 페이지를 조건부 WRITE fix 아래에서 다시 확인하고 바로 씁니다.

```text
oos_reclaim_file_state (VFID별, bestspace_mutex 아래)
  emptied    : VPID 집합, 상한 K. 넘으면 unknown = true
  unknown    : bool. boot, OOM, K 초과 뒤 lap이 끝날 때까지
  lap_cursor : VPID
RVOOS_INSERT undo 데이터: VFID 8B (추가)
삭제: pending_deletes, swept_this_boot, oos_try_reclaim_page_internal, vacuum fast path
```

규칙은 다섯 개입니다.

1. **넣기.** 넣는 곳은 두 곳입니다.
   - `oos_delete_chain` 이 페이지를 비운 곳(`oos_file.cpp:3375`).
   - INSERT rollback undo가 페이지를 비운 곳(`oos_rv_redo_delete`, 3655 뒤).

   둘 다 페이지 WRITE latch를 쥔 채 넣습니다.
2. **즉시 빼기.** 집합에서 꺼낼 때 뺍니다. bestspace Phase C가 빈 페이지를 내줄 때도 그 latch 아래에서 뺍니다(2158의 `page_was_empty` 와 같은 판정).
3. **재검증.** 조건부 WRITE fix(`OLD_PAGE_MAYBE_DEALLOCATED`) 아래에서 다섯 가지를 봅니다. `PAGE_OOS` 인지, 이 파일 소유인지, 레코드가 0개인지, 공간이 충분한지 봅니다. Phase C(665-760)와 같은 검사라서 helper 하나를 같이 씁니다. latch를 못 잡으면 집합에 남겨 둡니다.
4. **공간이 모자라면 재초기화.** 짧은 sysop 안에서 `oos_vpid_init_new` 를 부릅니다.
5. **순서.** bestspace → `emptied` → ratio sync → (unknown이면) lap → `emptied` 재확인 → `file_alloc`.

### 2. 소스에서 다시 확인한 사실

- **rollback 지점은 VFID를 모릅니다.**
  - `RVOOS_INSERT` 의 undo는 `oos_rv_redo_delete` 입니다(`recovery.c:881-886`).
  - `LOG_RCV` 에는 VFID가 없습니다(`recovery.h:226-234`).
  - INSERT 로그에는 undo 데이터가 없습니다(`oos_file.cpp:3180`).
  - 그래서 undo 데이터에 VFID를 넣어야 합니다. ADR-0008 결정 6에 따라 병합 전 형식 변경으로 허용됩니다.
  - 이전 `cand_fullboot` 권고도 같은 구멍이 있습니다.
  - 헤더 레코드 INSERT(1210)도 같은 레코드를 씁니다. 그래서 undo 함수는 VFID가 없는 레코드를 건너뛰어야 합니다.
- **빈 ANCHORED 페이지는 죽은 slot을 남깁니다.** 원인은 `slotted_page.c:2093-2096` 입니다.
  - 16KB 페이지에서 최대 chunk 레코드는 16344B입니다.
  - 죽은 slot N개인 빈 페이지에 들어가는 최대 크기는 `ALIGN_BELOW(16352-4N, 8)` 입니다.
  - 그래서 N≥3이면 최대 chunk가 들어가지 않습니다(841-844, 948-985에서 계산).
- **재초기화는 sysop 안에서 해야 합니다.** `RVPGBUF_NEW_PAGE` undo는 page type을 `PAGE_UNKNOWN` 으로 되돌립니다(`page_buffer.c:15272-15277`).
- **헤더 latch 비용.** 모든 OOS INSERT는 헤더 페이지를 무조건 WRITE latch합니다(3023). 회수 phase 2와 vacuum fast path는 같은 latch를 잡은 채 dealloc sysop을 commit합니다(1609-1677, `vacuum.c:1983`).
- **안전 근거는 ADR-0008입니다.** chunk 삭제에 undo가 없으면 빈 페이지에는 앞으로 올 undo가 없습니다. undo할 INSERT가 남은 페이지는 그 chunk를 갖고 있으니 비어 있지 않습니다. ADR-0008 이전의 슬롯 덮어쓰기(CBRD-27781)는 bestspace 재사용에도 똑같이 있는 위험입니다.

### 3. 모델

`OosReuseFirst.tla` 입니다.
- 페이지 하나가 sector 하나입니다. 예약 페이지 수 `R` 은 줄지 않습니다.
- 행위자는 bestspace INSERT, vacuum 삭제, fast path, undo latch, 힌트 손실, 재시작, 성장자 하나입니다.
- 상수는 Cap=2, L=2, MaxPages 4와 5입니다.
- **유계인 설계는 P4와 P5에서 distinct state 수가 정확히 같습니다.** 5번째 페이지에 닿는 상태가 없다는 직접 증거입니다.
- 측정 실행 한 번이 최악 크기, 성장당 검사 수, sysop 수, 성질별 첫 위반을 기록합니다. 위반된 성질마다 1-worker BFS로 최단 반례를 다시 구합니다.

검사한 성질은 다섯 개입니다.
- `Safe`: dealloc된 페이지에 쓰지 않습니다. latch된 페이지는 조건부 fix가 구성상 막습니다.
- `SetComplete`: 비어 있는 모든 페이지가 집합에 있습니다.
- `StrictRule`: 손대지 않은 빈 페이지가 남아 있으면 성장하지 않습니다. 재사용한 경우도 규칙을 지킨 것으로 칩니다.
- `NoOverflow`: 파일이 MaxPages를 넘지 않습니다.
- `NoFutileWork`: 빈 페이지가 없었던 성장은 아무 페이지도 검사하지 않습니다.

### 4. 결과

**후보 `reuse`** (fast path 끔, 재확인 1회, 즉시 빼기, P4):

| 설정 | Safe | SetComplete | StrictRule | NoOverflow | NoFutileWork | 최악 크기 | 성장당 최대 검사 | 성장당 최대 sysop | states (P4=P5) | TLC 시간 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 크래시 없음, 성장 중 쓰기 없음 | PASS | PASS | PASS | PASS | PASS | 3 | 3 | 1 | 1,465 | 2s |
| 크래시 없음, 쓰기 있음 | PASS | PASS | PASS | PASS | PASS | 4 | 3 | 1 | 8,150 | 3s |
| 크래시 있음, 쓰기 없음 | PASS | PASS | PASS | PASS | - | 3 | 4 | 1 | 13,214 | 3s |
| 크래시 있음, 쓰기 있음 | PASS | PASS | PASS | PASS | - | 4 | 7 | 1 | 122,221 | 13s (P5 11s) |

- sysop 1은 집합이 비었을 때의 `file_alloc` 입니다. 재사용 자체는 0입니다.
- 공간 부족(MayNotFit)을 넣어도 네 설정이 모두 PASS입니다(states 2,540 / 14,263 / 22,998 / 212,671). 재초기화는 1 sysop입니다.

**비교** (P4. 최악 크기는 무사고·쓰기·크래시·크래시+쓰기 순서):

| 설계 | 최악 크기 | 실패 | 최대 sysop | 크래시+쓰기 states / 시간 |
| --- | --- | --- | --- | --- |
| `cand_fullboot` (이전 권고) | 3·4·3·**cap** | NoOverflow (크래시+쓰기) | 2 | 1,030,415 / 112s |
| `cand_recheck` | 3·4·3·4 | 없음 | 2 | 675,015 / 77s, P5 같음 |
| **`reuse`** | 3·4·3·4 | 없음 | 1 | 122,221 / 13s, P5 같음 |
| `reuse_fast` (fast path 유지) | 3·4·3·4 | 없음 | 1 | 476,943 / 62s |
| `reuse_norecheck` | 3·4·3·**cap** | NoOverflow (크래시+쓰기) | 1 | 184,230 / 19s |
| `reuse_lazy`, `cand_lazy` (늦게 빼기) | 3·**cap**·3·미실행 | NoOverflow (쓰기), NoFutileWork | 1, 2 | - |
| `reuse_nocheck` (재검증 없음) | - | Safe (모든 설정) | 1 | - |
| `reuse_noreinit` (MayNotFit) | 모두 cap | StrictRule, NoOverflow | 1 | 1,757,234 / 143s |
| `hybrid` | 3·4·3·4 | 없음 | 1 | 588,122 / 74s |
| `hybrid_cand` (브리프의 hybrid) | 3·4·3·4 | 없음 | 2 | 1,847,979 / 196s, P5 같음 |
| `hybrid_leaky` | cap·cap·cap | SetComplete, StrictRule, NoOverflow | 1 | - |

이전 모델의 제한(undo는 성장 한 번에 새 latch를 한 번만 잡음)을 풀면 결과가 갈립니다.
- 성장 중 쓰기가 없는 두 설정에서는 `cand_recheck`, `reuse`, `hybrid_cand` 가 모두 PASS입니다.
- 크래시 없이 쓰기가 있는 설정에서는 세 설계 모두 cap에 닿습니다. 반례는 34 states(P5에서 51)입니다.

### 5. 최단 반례

길이는 TLC state 수이고 초기 상태를 포함합니다.

- **`cand_fullboot`, 크래시+쓰기, NoOverflow (36).** `reuse_norecheck` 도 같은 반례를 냅니다.
  - 크래시가 집합을 지웁니다.
  - boot lap 동안 writer가 cursor 바로 앞 페이지를 채우고, 지나간 페이지를 비웁니다.
  - lap이 끝날 때 `E={1,2,4}`, `stale={}` 인데, 집합을 다시 읽지 않고 할당합니다.
  - 강한 규칙은 통과합니다. 그래서 **강한 규칙만으로는 유계 성장이 보장되지 않습니다.** 이전 보고의 열린 지점("크래시+쓰기에서 모든 설계가 cap")의 원인이 이 재확인 누락입니다.
- **`reuse_lazy` 와 `cand_lazy`, 쓰기, NoOverflow (35).**
  - 다시 채워진 페이지가 집합에 남습니다.
  - 성장자는 그 페이지를 보고 버린 뒤 지나갑니다. 그다음 vacuum이 그 페이지를 다시 비웁니다. 이것이 성장마다 반복됩니다.
  - 한 성장에서 같은 페이지를 다시 보게 하면 반례 대신 livelock이 됩니다(`examined` 무한).
  - 이전 보고의 "늦게 빼도 검사가 한 번 늘 뿐"이라는 말은 틀렸습니다.
- **`reuse_nocheck`, Safe (8).** vacuum이 p1을 비우고 fast path가 dealloc합니다. 집합에 남은 p1에 성장자가 씁니다.
- **`hybrid_leaky`.**
  - SetComplete (6): vacuum이 비운 p1의 힌트가 손실되고, 어느 집합에도 없습니다.
  - StrictRule (9): 다음 성장이 새 페이지를 잡습니다.
  - NoOverflow (22): 이것을 세 번 반복합니다.
- **`reuse_noreinit`, StrictRule (9).** 빈 p1에 chunk가 들어가지 않아 건너뛰고 할당합니다. NoOverflow (25)는 이것의 반복입니다.
- **제한을 푼 undo + 쓰기, NoOverflow (34).**
  - 성장자가 busy 페이지를 건너뛸 때마다 undo가 latch를 풀고, 성장자가 다음에 볼 페이지를 latch합니다.
  - 그 사이 INSERT가 손대지 않은 빈 페이지를 채웁니다.
  - `Alloc` 시점에 3·4번 페이지는 비어 있고 latch도 없지만 이미 건너뛴 상태입니다.

### 6. 할당당 비용과 구현 크기

비용은 소스를 읽고 센 추정입니다. 측정하지 않았습니다.

| 단계 | `cand_fullboot` | `reuse` |
| --- | --- | --- |
| 후보 찾기 | 집합 연산 1 | 같음 |
| 후보 검사 | READ fix, 헤더 WRITE latch(무조건), 조건부 WRITE fix | 조건부 WRITE fix, 소유 검사(파일 헤더 READ fix) |
| 반환 | dealloc sysop 1. 파일 헤더 WRITE fix 2, 로그 약 4개, 헤더 latch를 commit까지 유지 | 없음 |
| 다시 얻기 | `file_alloc` sysop. 파일 헤더 WRITE fix, NEW_PAGE, 로그 약 4개 | 없음. 죽은 slot이 많을 때만 sysop 1 |
| vacuum fast path | 페이지가 빌 때마다 반환 1회, 그리고 나중에 다시 얻기 1회 | 없음. 힌트가 살아 있어 bestspace가 바로 씀 |

- 성능을 묶는 지점은 모든 INSERT가 잡는 OOS 헤더 WRITE latch(3023)입니다. `cand` 는 이 latch를 dealloc sysop 동안 쥡니다.
- 판단을 정할 측정은 ADR-0009 결정 4의 5-cycle churn에서 잽니다.
  - `cand` 와 `reuse` 의 INSERT/UPDATE 지연.
  - 헤더 latch 대기.
  - 1000 INSERT당 sysop 수.

구현 크기도 추정입니다. 소스를 고쳐 보지는 않았습니다.

- `reuse` 는 약 200줄을 추가하고 약 450줄을 지웁니다(주석 포함).
- 추가:
  - 상태 구조체(1289).
  - 넣기 helper.
  - 3375 hook.
  - VFID undo(3170-3181, 3650-3673, `recovery.c:881-886`).
  - Phase C 검증 helper 추출과 즉시 빼기(665-760).
  - 3006-3141의 집합 단계와 재초기화.
  - lap 재작성(1816-2000).
- 삭제:
  - `oos_try_reclaim_page_internal` (1524-1701).
  - `oos_reclaim_empty_pages` (1704-1781).
  - lap 정산과 무장(1325-1395, 1783-1813).
  - `vacuum_oos.cpp` 172-245와 445-480, `vacuum.c` fast path, `oos_delete` 의 `emptied_vpids` 인자.
- `cand_fullboot` 는 약 100~150줄을 추가하고, VFID undo 때문에 약 40줄이 더 듭니다. dealloc 경로와 fast path는 남습니다.

### 7. 권고

- **`reuse`: 조건부 추천.** 모든 설정에서 `cand_recheck` 와 같은 보장을 sysop 없이 지키고, 코드는 오히려 줄어듭니다.
  - ADR-0009 결정 3(fast path 유지)을 고쳐야 합니다. `reuse_fast` 가 PASS이므로 전환기에 fast path를 남겨도 안전합니다. 다만 비용은 남습니다.
- **`hybrid`, `hybrid_cand`: 비추천.** 보장은 같습니다. 대신 손실 가능한 bestspace 캐시의 4~5개 지점에 hook을 달아야 합니다(용량 초과, Phase A 퇴출, Phase C 공간 부족, 3655). hook 하나를 빠뜨린 `hybrid_leaky` 는 cap입니다. 아끼는 것은 vacuum이 비운 페이지마다 집합 연산 1회뿐입니다.
- **어느 안을 고르든 lap 뒤 재확인은 넣어야 합니다.** 재확인이 없는 `cand_fullboot` 는 크래시+쓰기에서 cap입니다.

### 8. 모델의 한계

- 유한 모델입니다. 페이지 4~5개, chunk 2개, 페이지당 2개, rollback 행위자 하나, 성장자 하나입니다. 크기 3·4는 실제 상한이 아닙니다.
- 성장자 하나라는 가정의 근거는 두 가지입니다. 집합 단계는 헤더 latch 아래에서 직렬화되고, lap은 single-flight입니다. 서로 다른 `file_alloc` 은 각자 페이지가 정말 필요합니다.
- 꺼내기·검증·쓰기를 원자 단계로 두었습니다. 같은 WRITE latch 아래에서 일어나기 때문입니다. 집합을 읽은 뒤 fix하기까지의 틈은 `LazyRemove` 실행이 덮습니다.
- MayNotFit은 꺼낼 때마다 비결정입니다. 실제로는 빈 페이지의 죽은 slot 수가 고정이라, 과대 근사입니다.
- undo latch를 성장 한 번에 한 번으로 묶는 제한은 쓰기 설정에서만 필요합니다(4절). 완화안은 검증하지 않았습니다. 모든 후보가 busy이면 헤더 latch를 놓고 busy 페이지 하나를 기다리는 방식입니다.
- 다중 파일, VFID 경로, 로그 형식은 소스 판독에만 근거합니다.
- 1~5단계 spec(`b4cf6825…`)과 현재 spec(`8fc8cee2…`)은 한 곳만 다릅니다. `MayNotFit ∧ hybrid_cand` 일 때만 쓰는 분기입니다. 처음 모델은 한 성장 안에서 페이지가 H와 C 사이를 오가는 livelock을 냈습니다. 엔진은 힌트를 호출당 한 번만 읽으므로 같은 호출에서 dealloc하도록 고쳤습니다.

### 9. 적용한 원칙

- **Foundational Thinking.** fast path, rollback, 다른 INSERT, 성장자가 같은 페이지를 건드릴 때를 먼저 따졌습니다. 그래서 페이지 WRITE latch를 유일한 중재자로 두고, 집합은 그 latch 아래에서 재검증하는 힌트로 정했습니다. 데이터 형태를 먼저 그리다가 rollback 지점의 VFID 공백을 찾았습니다.
- **Attack the Premise.** "늦게 빼도 된다", "크래시+쓰기는 모든 설계가 cap"이라는 이전 전제를 `cand_lazy`, `cand_recheck` 로 직접 시험했습니다. 앞의 것은 거짓이었고, 뒤의 것의 원인은 재확인 누락이었습니다.
- **Subtract Before You Add.** hook을 더하는 hybrid 대신 dealloc 경로·fast path·무장 카운터를 지우는 `reuse` 를 골랐습니다.
- **Build the Lever.** `run.py` (측정, 최단 반례, `--collect`)와 `run_all.sh` 가 모든 표를 다시 만듭니다.
- **Explain the Number.** 비용은 측정이 아니라 소스에서 센 것이라고 표시했습니다. 제한 지점(3023)과 판단을 바꿀 측정을 적었습니다.
- **Prove It Works.** 유계 판정은 P4=P5 state 수 일치로 확인했습니다. 모델을 고친 뒤에는 다시 돌렸습니다.

### 10. 재현과 파일

- `bash run_all.sh <새 디렉터리>` 를 실행합니다. 동시 TLC worker는 최대 12개이고, 약 40분 걸립니다.
- 결과는 `runs/v4/<단계>/results.json` 에 있고, 반례 전체는 `*-ce-*.log` 에 있습니다. `states/` 디렉터리는 모두 지웠습니다.

파일:
- /home/vimkim/gh/my-cubrid-docs-CBRD-27925-growth-arena/cbrd-27925/growth-arena/c-reuse-first/OosReuseFirst.tla
- /home/vimkim/gh/my-cubrid-docs-CBRD-27925-growth-arena/cbrd-27925/growth-arena/c-reuse-first/run.py
- /home/vimkim/gh/my-cubrid-docs-CBRD-27925-growth-arena/cbrd-27925/growth-arena/c-reuse-first/run_all.sh
- /home/vimkim/gh/my-cubrid-docs-CBRD-27925-growth-arena/cbrd-27925/growth-arena/c-reuse-first/runs/v4/
