# 후보 E: 할당 경로 밖 회수 (off-path sweep)

CBRD-27925 growth arena, id `e-offpath-sweep`. 엔진 기준은 `feature/oos-merge` `d52b1889e`이고, 모델은 ADR-0008 이후 목표(LSA gate 없음, chunk 삭제는 undo 없음)를 따른다.

## 목표

같은 양의 live 데이터로 insert/delete를 반복해도 OOS 파일이 끝없이 커지지 않아야 한다. 지금의 강한 규칙("회수할 수 있는 빈 페이지가 있으면 새 sector를 잡지 않는다")은 바꿀 수 있다. 이 후보는 회수 일을 INSERT/UPDATE 할당 경로 밖으로 옮긴다. 그때 유계성, 강한 규칙, 안전성이 어떻게 되는지를 TLC로 확인했다.

## 결론

- **할당 경로 쪽 보완 없이는 유계가 아니다. 공정성(fairness)을 주어도 마찬가지다.** 파일 크기 상한은 safety 성질이다. 공정성은 무한 실행만 제약하고 유한 접두는 하나도 지우지 않는다. 모델에서 `pure_bg`는 공정성이 없을 때와 weak fairness일 때 모두 cap에 닿았다. 공정성은 liveness 하나만 준다. 빈 페이지는 결국 회수되거나 다시 쓰인다. 이것도 FIFO 순서일 때만 성립한다.
- **할당 경로 fallback(밀린 양 > S이면 동기 회수)을 두면 worker 공정성과 무관하게 유계다.** 상한은 기준선 + S 페이지다. 강한 규칙은 정확히 S 페이지만큼 깨진다. S = 0이면 강한 규칙이 crash와 동시 쓰기에서도 지켜진다.
- **재시작 뒤 lap은 할당 경로 밖으로 옮길 수 없다.** 성장이 lap을 무시하는 `bg`는 재시작 1번으로 cap에 닿는다. S번만 무시하는 `bg_slack`은 재시작 k번에 S·k 페이지씩 더 커진다. 그래서 재시작이 반복되면 상한이 없다.
- **최악 비용은 줄지 않는다.** 줄어드는 것은 worker가 따라올 때의 흔한 경우뿐이다. 그런데 vacuum fast path가 이미 그 흔한 경우를 할당 경로 밖에서 처리한다(ADR-0008 결정 5, 결과 7). 따라서 이 후보가 추가로 옮기는 일은 fast path가 놓친 나머지뿐이다. INSERT rollback, eager cleanup, latch 때문에 미뤄진 페이지가 그 나머지다.

## 후보와 데이터 모양

파일별로 빈 페이지 VPID 집합 E(밀린 회수 목록)와 `unknown` 플래그를 둔다. `unknown`은 재시작 뒤 lap이 파일 전체를 아직 덮지 않았다는 뜻이다. 페이지를 비우는 두 지점이 E에 넣는다. 하나는 `oos_delete_chain`(`oos_file.cpp:3372-3376`), 다른 하나는 `oos_rv_redo_delete`(3650-3675)다. 빈 페이지에 INSERT가 다시 쓰면 E에서 뺀다(`page_was_empty`, 2158). worker(vacuum fast path, 그리고 vacuum hook이나 daemon의 drain)가 E에서 꺼내 기존 두 단계 primitive `oos_try_reclaim_page_internal`(1565-1700)로 회수한다. 할당 경로는 |E| ≤ S이면 카운터만 읽고 지나간다. |E| > S이면 E에서 하나를 동기로 회수한다. 재시작 뒤 처리는 `Boot`가 정한다. `sync`는 첫 성장이 lap을 돈다. `bg`는 worker의 lap만 기다린다. `bg_slack`은 S번의 성장까지 lap을 건너뛴다.

## 모델

`OffPathSweep.tla`(sha256 `239ab785…ec151`), `run.py`, 결과는 `runs/run2/`와 `runs-run2.txt`에 있다. 유한 모델이며 상수는 다음과 같다.

- `Cap = 2`(페이지당 chunk 수), `L = 2`(live chunk 상한), `MaxPages = 5`. 상한 판정에는 6과 7도 썼다. `NoOverflow`가 통과하는 첫 `MaxPages`에서 잰 최대 R을 상한으로 적었다. R이 cap보다 작은 동안의 동작은 `MaxPages`와 무관하다. 7까지도 통과하지 않으면 "cap"이다.
- 한 페이지 = 한 sector다. R이 파일 크기이고 줄지 않는다.
- 행위자: INSERT, vacuum chunk 삭제, INSERT rollback undo(페이지 WRITE latch를 잡고 chunk를 지운다. 성장 한 번에 새 latch는 최대 1개), crash(메모리 힌트 소실), worker(READ 확인 → 이후 WRITE 재확인 + dealloc. 두 단계 사이에 다른 행위자가 끼어든다), grower(파일당 single-flight).
- 측정: TLC register에 최대값을 기록했다. 최대 R, 성장 한 번에 grower가 fix한 페이지 수, 새 sector를 잡는 순간 성장 시작부터 비어 있었고 손대지 않은 채 남겨진 빈 페이지 수(gap)다. 강한 규칙 = gap 0.
- 성질: `TypeOK`, `Safe`(dealloc으로 chunk를 잃지 않는다, latch 잡힌 페이지는 할당 상태, E ⊆ 예약 페이지), `DebtExact`(`unknown`이 아니면 모든 빈 페이지가 E에 있다), `NoOverflow`, `Strict`(action property), `EmptyEventuallyGone`(liveness).

설계 이름:

| 이름 | Worker | Fallback | S | Boot | 뜻 |
| --- | --- | --- | --- | --- | --- |
| `cand_base` | 없음 | 있음 | 0 | sync | `cand_fullboot`, fast path 없음 |
| `off_S0` | 있음 | 있음 | 0 | sync | `cand_fullboot` + fast path/drain |
| `off_S1`, `off_S2` | 있음 | 있음 | 1, 2 | sync | 이 후보 |
| `pure_bg` | 있음 | 없음 | - | bg | 할당 경로는 아무것도 안 함 |
| `off_S1_bg` | 있음 | 있음 | 1 | bg | 재시작 lap도 경로 밖 |
| `off_S1_bgslack` | 있음 | 있음 | 1 | bg_slack | 재시작 뒤 S번은 lap 생략 |

## 결과

안전성은 `TypeOK ∧ Safe ∧ DebtExact`이다. 비용은 grower가 성장 한 번에 fix한 페이지 수의 최대값이다. states는 main run의 distinct state 수다. 초는 그 행의 모든 TLC run(main, cost, overflow)을 더한 값이며, run마다 worker 2~6개를 썼다.

| 설계 | crash | 성장 중 쓰기 | 안전성 | 최대 R | 최대 gap | 비용/성장 | states | 초 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cand_base | 끔 | 끔 | PASS | 3 | 0 | 3 | 421 | 6 |
| cand_base | 끔 | 켬 | PASS | 4 | 0 | 3 | 4,417 | 7 |
| cand_base | 켬 | 끔 | PASS | 3 | 0 | 6 | 1,947 | 6 |
| cand_base | 켬 | 켬 | PASS | 4 | 0 | 7 | 17,499 | 8 |
| off_S0 | 끔 | 끔 | PASS | 3 | 0 | 4 | 4,460 | 7 |
| off_S0 | 끔 | 켬 | PASS | 4 | 0 | 4 | 55,232 | 15 |
| off_S0 | 켬 | 끔 | PASS | 3 | 0 | 7 | 24,384 | 12 |
| off_S0 | 켬 | 켬 | PASS | 4 | 0 | 8 | 272,233 | 36 |
| off_S1 | 끔 | 끔 | PASS | 4 | 1 | 4 | 23,234 | 11 |
| off_S1 | 끔 | 켬 | PASS | 5 | 1 | 4 | 355,123 | 55 |
| off_S1 | 켬 | 끔 | PASS | 4 | 1 | 8 | 174,904 | 25 |
| off_S1 | 켬 | 켬 | PASS | 5 | 1 | 9 | 2,175,023 | 91 |
| off_S2 | 끔 | 끔 | PASS | 5 | 2 | 4 | 94,348 | 25 |
| off_S2 | 끔 | 켬 | PASS | 6 | 2 | 4 | 633,581 | 120 |
| off_S2 | 켬 | 끔 | PASS | 5 | 2 | 9 | 894,122 | 56 |
| off_S2 | 켬 | 켬 | PASS | 6 | 2 | 9 | 3,979,715 | 270 |
| pure_bg | 끔 | 끔 | PASS | cap | 4 | 0 | 47,964 | 23 |
| pure_bg | 끔 | 켬 | PASS | cap | 4 | 0 | 95,352 | 26 |
| pure_bg | 켬 | 끔 | PASS | cap | 4 | 0 | 742,530 | 107 |
| pure_bg | 켬 | 켬 | PASS | cap | 4 | 0 | 1,318,122 | 44 |
| off_S1_bg | 끔 | 끔 | PASS | 4 | 1 | 4 | 23,234 | 16 |
| off_S1_bg | 끔 | 켬 | PASS | 5 | 1 | 4 | 355,123 | 75 |
| off_S1_bg | 켬 | 끔 | PASS | cap | 4 | 4 | 2,628,121 | 73 |
| off_S1_bg | 켬 | 켬 | PASS | cap | 4 | 4 | 8,641,383 | 206 |
| off_S1_bgslack | 끔 | 끔 | PASS | 4 | 1 | 4 | 23,234 | 14 |
| off_S1_bgslack | 끔 | 켬 | PASS | 5 | 1 | 4 | 355,123 | 71 |
| off_S1_bgslack | 켬 | 끔 | PASS | cap | 4 | 9 | 4,085,737 | 172 |
| off_S1_bgslack | 켬 | 켬 | PASS | cap | 4 | 9 | 11,656,484 | 506 |

"cap" 행의 gap 4는 cap에 닿는 실행에서 잰 값이다. 상한이 아니다.

재시작 횟수 k를 제한했을 때의 최대 R:

| 설계 | k = 1, 조용 | k = 1, 쓰기 | k = 2, 조용 | k = 2, 쓰기 |
| --- | --- | --- | --- | --- |
| off_S1 (sync) | 4 | 5 | 4 | 5 |
| off_S1_bgslack | 5 | 6 | 6 | 7 |
| off_S1_bg | cap | cap | cap | cap |

`bg_slack`은 재시작마다 S 페이지씩 더 커진다(4 + 1·k, 5 + 1·k). `sync`는 k와 무관하다.

공정성과 liveness(`MaxPages = 4`, crash 없음, 쓰기 켬):

| 설계 | spec | worker 순서 | EmptyEventuallyGone | states | 초 |
| --- | --- | --- | --- | --- | --- |
| pure_bg | 공정성 없음 | fifo | FAIL | 16,738 | 7 |
| pure_bg | WF | 아무거나 | FAIL | 3,100 | 6 |
| pure_bg | WF | fifo | PASS | 40,672 | 38 |
| off_S1 | 공정성 없음 | fifo | FAIL | 16,020 | 6 |
| off_S1 | WF | 아무거나 | FAIL | 3,565 | 6 |
| off_S1 | WF | fifo | PASS | 121,205 | 108 |
| cand_base | WF | - | FAIL | 3,133 | 6 |
| pure_bg, `NoOverflow` | WF | fifo | **FAIL** | 2,189 | 4 |

마지막 행이 핵심이다. weak fairness를 준 spec에서도 같은 overflow에 닿는다. `cand_base`의 FAIL은 ADR-0009 결정 1과 맞는다. 쉬는 파일의 빈 페이지는 회수하지 않아도 된다.

## 반례 (가장 짧은 것)

- **강한 규칙, `off_S1`(8 상태).** 성장으로 페이지 1을 만든다. vacuum 삭제가 페이지 1을 비워 E = {1}이 된다. 다음 성장은 밀린 양 1 ≤ S라서 회수하지 않고 페이지 2를 예약한다. gap은 1이다. S = 2이면 gap은 2다.
- **안전성, worker가 WRITE 재확인을 하지 않을 때(`Recheck = FALSE`, 8 상태).** 페이지 1이 비어 E에 들어간다. worker가 READ fix로 "비었음"을 본다. INSERT가 페이지 1에 chunk를 쓴다. worker가 이전 판정만 믿고 dealloc한다. chunk 하나가 사라져 `Safe`가 깨진다. 지금 primitive의 phase 2 재확인(헤더 WRITE latch 아래 WRITE fix 재검사, `oos_file.cpp:1607-1640`)이 바로 이 경합을 막는다. vacuum과 inserter가 같은 페이지를 두고 경합할 때도 안전하려면, worker가 이 primitive를 그대로 써야 한다.
- **유계성, `pure_bg`(23 상태, crash 없음, 조용).** 삭제가 페이지를 비우고 성장이 새 페이지를 잡는 일이 네 번 반복된다. worker는 한 번도 돌지 않는다. E = {1,2,3,4}인 채로 R = 5에서 overflow가 난다. WF 판(21 상태)도 같은 모양이다. worker가 돌기 전에 접두가 이미 cap에 닿는다.
- **유계성, `off_S1_bgslack` + 반복 재시작(26 상태).** 재시작 → 성장(grace로 lap 생략, 새 페이지) → 그 페이지를 비움 → 재시작이 반복된다. 재시작마다 grace가 S로 돌아오고 E는 비어 있다.

## "백그라운드 작업은 스케줄되지 않을 수 있다"는 주장

이전 보고서의 결론(경로 밖 sweep만으로는 부족하다)은 맞다. 근거는 틀렸다. 스케줄을 보장해도, 즉 worker에 weak fairness를 주어도 크기 상한은 생기지 않는다. 공정성은 "언젠가는 돈다"만 보장한다. 그 전에 몇 번 성장할지는 제한하지 않는다. 상한을 주는 것은 할당 경로의 fallback뿐이다. fallback이 있으면 worker가 전혀 돌지 않아도(`Spec`) 상한 기준선 + S가 지켜진다. worker 공정성이 주는 것은 마지막 S 페이지의 liveness뿐이다. 그 페이지들은 ADR-0009 결정 1에 따라 원래 회수할 의무가 없다.

## 이전 보고서와 다른 점

이전 보고서는 crash + 동시 쓰기에서 `cand_fullboot`도 cap에 닿는다고 했다. 이 모델의 `cand_base`와 `off_S0`은 같은 조건에서 R ≤ 4, gap 0이다(`Strict` PASS, 272,233 상태). 차이는 lap이 끝난 뒤의 전이다. 이전 모델의 lap은 끝나면 바로 `alloc`으로 간다(`OosGrowthBound.tla:232-238`). 그래서 lap 뒤쪽에서 동시 삭제가 비운 페이지는 집합에 기록만 되고 확인되지 않는다. 그 성장은 그대로 예약한다. 다음 성장 전에 재시작하면 그 기록도 잃는다. 이 모델의 lap은 끝나면 집합 단계로 돌아간다(`OffPathSweep.tla:228`). 이전 모델의 cap이 이 전이 때문이라는 것은 두 명세를 읽고 한 추론이다. 이전 모델로 다시 돌려 보지는 않았다. 그래도 `cand_fullboot` 구현에 옮겨 붙일 만하다. 재시작 lap이 끝나면 예약하기 전에 집합을 한 번 더 확인하면 된다.

## 할당 경로 비용과 구현 크기 (`cand_fullboot` 대비)

성장 한 번의 비용은 엔진 소스에서 읽은 것이다.

| | 집합이 비었거나 \|E\| ≤ S | 동기 회수가 필요할 때 | 재시작 뒤 첫 성장 |
| --- | --- | --- | --- |
| 회수 없음(기준) | `oos_file_alloc_new` 하나: sysop 1개(`file_alloc` + 페이지 초기화, 2976-3004) | - | - |
| `cand_fullboot` | 기준 + 집합 확인(mutex 1회) | + READ fix, 헤더 WRITE latch, WRITE fix, dealloc sysop, bestspace 정리(1565-1700). 모델 최악 3 fix | 파일 전체 READ fix lap. 모델 최악 6~7 |
| 이 후보(S ≥ 1, sync) | 기준 + 카운터 읽기 | `cand_fullboot`과 같다. 모델 최악 4 fix(+1) | 같다. 모델 최악 8~9(파일이 S만큼 더 커서 lap이 길다) |

- +1의 원인은 worker다. WRITE fix가 막혀 DEFERRED가 된 페이지를 worker가 E에 다시 넣는다. 그 사이 INSERT가 그 페이지를 다시 채웠으면 grower가 비어 있지 않은 항목을 하나 더 fix한다.
- 이 후보가 아끼는 것은 "worker가 따라오는 동안" 동기 회수를 건너뛰는 몫이다. worker가 돌지 않으면 S는 따라잡기 한 번에 동기 회수 최대 S번만 아낀다. 그 뒤로는 성장마다 `cand_fullboot`과 똑같이 회수한다.
- vacuum fast path는 ADR-0008 뒤에도 남는다(결정 5). fast path는 reclaimer에서 공급받는다(결과 7). 그래서 vacuum이 비운 페이지는 이미 할당 경로 밖에서 회수된다. E에 남는 것은 INSERT rollback이 비운 페이지, eager cleanup이 비운 페이지(`heap_oos.cpp:946-948`, 거기서 바로 회수할 수 없다), WRITE fix가 막혀 미뤄진 페이지, 중단된 경우뿐이다. 이 몫이 얼마나 되는지는 재지 않았다. 일반 OLTP에서는 작을 것이라고 추측한다.
- 경로 밖 회수도 phase 2에서 헤더 WRITE latch를 잡는다. 그동안 다른 INSERT의 `oos_find_best_page`(3022-3023)가 기다린다. 이 후보는 지연을 한 INSERT 스레드에서 다른 스레드로 옮길 뿐이고, 헤더 latch 경합은 줄이지 않는다.
- S ≥ 1의 실제 디스크 비용은 추론이다. 실제 sector는 64페이지다(`storage_common.h:109`). 그래서 S < 64이면 파일당 많아야 sector 하나 정도가 더 쓰인다. 모델에서는 한 페이지 = 한 sector로 두었다.

구현 크기는 추정이다. 소스를 고쳐 보지 않았다.

- `cand_fullboot` 자체: 100~150줄(이전 보고서 추정). 거의 `oos_file.cpp` 안이다.
- slack 확인: `oos_alloc_page_with_reclaim`(2011-2027) 근처에 5~10줄. 시스템 파라미터로 만들면 15~25줄이 더 든다.
- drain 함수 `oos_reclaim_drain (vfid, k)`: `oos_file.cpp`에 40~60줄, `oos_file.hpp`에 3~5줄.
- drain 호출, vacuum hook 방식: `vacuum.c:1978-1987`의 fast path 호출 뒤에 5~10줄. vacuum은 이미 파일이 drop됐는지 확인한다(`vacuum.c:4332`).
- drain 호출, 전용 daemon 방식: 100~150줄. daemon 등록 방식은 `vacuum.c:793`, `948`, `1407`과 같다. 여기에 `oos_remove_file`(1248-1256)과의 장벽이 더 필요하다. daemon이 꺼낸 VPID를 파일 destroy 뒤에 dealloc하면 안 된다.
- 재시작 lap의 백그라운드 선행: 30~50줄. 동기 lap 코드는 없앨 수 없다. 상한을 지키려면 남아야 한다.
- 합계: vacuum hook 방식은 `cand_fullboot` + 50~90줄, daemon 방식은 `cand_fullboot` + 200~300줄이다.

## 권고: 조건부 추천

유계성과 강한 규칙을 지키는 것은 할당 경로의 backstop이다. 그 backstop이 곧 `cand_fullboot`이다. 경로 밖 부분은 그 위에 얹는 선택적 최적화다. 조건은 다음과 같다.

1. S = 0으로 둔다. 그러면 강한 규칙이 그대로 지켜진다(`off_S0`, crash + 쓰기에서도 gap 0). ADR-0009 결정 2를 고칠 필요가 없다. S ≥ 1은 아끼는 것이 따라잡기 한 번에 S번의 동기 회수뿐이다. 그런데 결정 2를 고쳐야 하므로 비추천한다.
2. drain은 새 daemon이 아니라 vacuum의 fast path 호출 뒤에 붙인다. 새 행위자, 파일 수명 장벽, 스레드 생명주기가 생기지 않는다.
3. 재시작 lap은 할당 경로에 남긴다(`sync`). `bg`와 `bg_slack`은 반복 재시작에서 상한이 없다.
4. 먼저 `cand_fullboot`을 넣고 CBRD-27872 측정에서 성장 시 동기 회수가 실제 비용으로 보일 때만 drain을 더한다. 측정 없이 넣을 이유는 모델에서 나오지 않는다.

## 모델의 한계

- 유한 모델이다(`Cap = 2`, `L = 2`, `MaxPages ≤ 7`, liveness는 4). 상한 값은 이 상수에서의 값이다. 일반식(기준선 + S, bg_slack은 + S·k)은 S = 0, 1, 2와 k = 1, 2에서 본 규칙성이다. 증명이 아니다.
- 한 페이지 = 한 sector다. 실제 sector는 64페이지이고, 같은 sector의 free bit를 먼저 쓰는 `file_alloc` 동작은 "FREE 페이지 먼저"로만 반영했다.
- INSERT의 페이지 선택과 쓰기는 한 단계다. 근거는 엔진이 헤더 WRITE latch 아래에서 페이지를 고르고 WRITE latch를 잡은 채 넘긴다는 점이다(`oos_file.cpp:3117-3125`). 그 latch 규약을 깨는 구현은 이 모델이 덮지 않는다.
- undo는 성장 한 번에 새 latch를 최대 1개만 잡는다(이전 모델과 같은 제한).
- INSERT가 다시 채운 페이지는 E에서 바로 뺀다. worker가 DEFERRED로 다시 넣은 항목만 stale로 남는다.
- E의 메모리 부족(overflow), 여러 파일, 파일 drop, 여러 grower, 실제 비용(시간)은 모델에 없다. 비용 열은 fix한 페이지 수다. 시간이 아니다.
- liveness는 worker 전체에 WF를 준 것과 FIFO 순서로만 확인했다. vacuum hook 방식의 실제 "공정성"은 그 파일에 vacuum 일이 다시 생기는가에 달려 있다. 이것은 보장되지 않는다. 그래도 상한은 이것에 기대지 않는다.

## 적용한 원칙

- **Attack the Premise.** 이전 보고서의 전제("스케줄되지 않을 수 있다")를 공정성 유무로 직접 시험했다. 그 결과 근거를 "공정성으로도 safety는 생기지 않는다"로 바꿨다. 후보 자체의 전제("회수 일이 INSERT 경로에 있다")도 소스로 확인했다. vacuum fast path가 대부분을 이미 경로 밖에서 하므로, 권고를 S = 0과 측정 뒤 도입으로 좁혔다.
- **Build the Lever.** 이전 실행은 binary search로 TLC를 431번 돌렸고 28분 안에 끝나지 않았다. TLC register로 최대값을 한 번에 재는 `run.py`로 바꿨다. 전체를 23분에 다시 돌릴 수 있고, 예상과 다르면 종료 코드가 1이다.
- **Explain the Number.** 실행 전에 판정을 바꿀 결과를 `EXPECTED`에 적었다. 상한 숫자는 `NoOverflow`가 통과하는 `MaxPages`에서만 읽었다. cap에 눌린 숫자를 상한으로 읽지 않기 위해서다.
- **Sequence Work into Verifiable Units.** 전체 실행 전에 설정 3개로 명세, 측정, 파서를 따로 확인했다. action property를 매개변수 연산자로 쓴 것을 TLC가 거부했는데, 이때 잡혔다.
- **Prove It Works.** `Recheck = FALSE`에서 `Safe`가 깨지는 것을 보였다. 따라서 안전성 PASS는 빈 검사가 아니다. 반례 trace는 직접 읽었다.
- **Separate Before Serializing Shared State.** 전용 daemon은 E와 페이지에 쓰는 행위자를 하나 더 늘리고 파일 drop과의 경합을 만든다. 그래서 이미 있는 행위자(vacuum)에 붙이는 쪽을 권했다.
- **Laziness Protocol.** 권고안은 `cand_fullboot` + vacuum hook 5~10줄 + drain 함수다. slack 파라미터, daemon, 백그라운드 lap은 뺐다.

## 재현

```
cd cbrd-27925/growth-arena/e-offpath-sweep
python3 -I -B run.py --out runs/run3 --tokens 12   # 약 23분, TLC worker 최대 12개
```

`runs-run2.txt`가 이 보고서의 숫자를 낸 출력이다. `runs/run2/`에는 run마다 `.cfg`와 `.log`가 있다. 측정값은 log의 `<<"HI", i, v>>` 줄에 있다(1 = R, 2 = 비용, 3 = gap).

---

Files are in `/home/vimkim/gh/my-cubrid-docs-CBRD-27925-growth-arena/cbrd-27925/growth-arena/e-offpath-sweep/`:
- `OffPathSweep.tla`
- `run.py`
- `runs-run2.txt`
- `runs/run2/`
- `REPORT.md` is not there yet. Its content is the Korean report above.
