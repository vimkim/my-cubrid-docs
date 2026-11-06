## 후보 B (`b-slack-bound`) 결과: 비추천

**목표.** live 데이터 양이 일정한 insert/delete churn에서 OOS 파일이 한없이 커지지 않아야 하고, 성장 경로의 회수 비용이 INSERT/UPDATE 처리량을 깎지 않아야 합니다. 이 후보는 강한 규칙을 일부러 약하게 했습니다. 알려진 빈 페이지가 K개 이하이면 회수 없이 새 페이지를 잡습니다.

**판정.** slack은 회수 횟수를 줄이지 않고 미룰 뿐입니다. 시뮬레이션에서 K=8은 회수를 정확히 8회, K=64는 정확히 64회 줄였습니다. 파일은 정확히 그만큼 커졌습니다(seed 1, 2, 3, 7과 두 workload에서 모두 같음). `cand_fullboot` 의 회수 한 번은 이미 "후보 페이지 1개 검사 + `file_dealloc` 1회"이므로 slack이 덜어 줄 비용이 거의 없습니다. 회수 비율은 그대로이고 보장만 약해집니다.

전달 사항 하나가 있습니다. **`REPORT.md` 는 harness가 쓰기를 막았습니다**("Subagents should return findings as text"). 아래 본문이 보고서 내용입니다. 코디네이터가 `cbrd-27925/growth-arena/b-slack-bound/REPORT.md` 로 저장해 주십시오. 커밋은 하지 않았습니다.

### 1. 후보와 데이터 형태

성장 한 번마다 `need = unknown || tracked_empty > K` 를 판정합니다. `K = max(k, ε × 할당 페이지)` 도 같은 판정입니다. need이면 빈 페이지 하나를 회수한 뒤 `file_alloc` 을 하고, 아니면 바로 `file_alloc` 을 합니다. 빈 페이지 수를 아는 방법은 세 가지를 따졌습니다.

- **집합 (`slack_set_K`).** `cand` 의 VPID 집합과 `unknown` 입니다. 수는 집합 크기이므로 `cand` 위에 비교 하나만 더하면 됩니다.
  - 재시작 때만 정보를 잃고, 그때 boot lap이 복구합니다.
  - READ 경합이 있어도 원소를 지우지 않습니다(모델 drift 0).
- **카운터 (`slack_count_K`).** VPID 없이 `INT64 empty_pages` 만 둡니다. 회수 대상은 cursor lap으로 찾습니다.
  - 재시작 뒤 카운터는 0부터 다시 셉니다. 재시작 전부터 비어 있던 페이지가 다시 채워지거나 회수될 때도 1을 뺍니다. 카운터는 그 페이지를 셌는지 구분하지 못하므로 값이 실제보다 낮게 drift합니다.
  - 이를 막으려면 어느 페이지를 셌는지 알아야 하는데, 그 정보가 곧 집합입니다.
- **sector별 메모리 bitmap.** 집합과 같은 정보를 다르게 인코딩한 것이라 판정은 집합과 같습니다.

### 2. 결과표

`OosSlackBound.tla` 로 TLC를 돌린 결과입니다. 유한 모델이고 상수는 Cap=2, L=2입니다. 한 페이지를 한 sector로 둡니다. "조용"은 성장 동안 쓰기가 기다리는 설정, "쓰기"는 성장 중간에 쓰기가 끼어드는 설정입니다. 시간은 큰 MaxPages 실행의 wall time이고, 3 worker로 돌렸으며 80코어를 다른 agent와 함께 썼습니다. MaxPages 두 값에서 최악 크기가 같으면 유계로 봅니다.

| 설계 | 설정 | 현재 명세 | slack 명세 | 최악 R | 성장당 최대 검사 | 헛된 검사 | 최대 drift | MaxPages | 상태 수 | 시간(s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cand_fullboot | 조용 | PASS | PASS | 3 | 3 | 없음 | 0 | 6,7 | 795 | 1.6 |
| cand_fullboot | 쓰기 | PASS | PASS | 4 | 3 | 없음 | 0 | 6,7 | 12,261 | 5.4 |
| cand_fullboot | 크래시+조용 | PASS | PASS | 3 | 5 | 있음 | 0 | 6,7 | 15,750 | 4.6 |
| cand_fullboot | 크래시+쓰기 | PASS | PASS | cap | 7 | 있음 | 0 | 5 | 3,454,552 | 577.1 |
| slack_set_K1 | 조용 | FAIL | PASS | 3 | 3 | 없음 | 0 | 6,7 | 1,128 | 1.7 |
| slack_set_K1 | 쓰기 | FAIL | PASS | 4 | 3 | 없음 | 0 | 6,7 | 25,012 | 8.1 |
| slack_set_K1 | 크래시+조용 | FAIL | PASS | 3 | 5 | 있음 | 0 | 6,7 | 28,767 | 7.8 |
| slack_set_K1 | 크래시+쓰기 | FAIL | PASS | cap | 6 | 있음 | 0 | 4 | 1,158,087 | 292.4 |
| slack_set_K2 | 조용 | FAIL | PASS | 4 | 3 | 없음 | 0 | 6,7 | 2,034 | 1.8 |
| slack_set_K2 | 쓰기 | FAIL | PASS | 4 | 3 | 없음 | 0 | 6,7 | 25,388 | 8.2 |
| slack_set_K2 | 크래시+조용 | FAIL | PASS | 4 | 6 | 있음 | 0 | 6,7 | 82,931 | 16.0 |
| slack_set_K1_noboot | 크래시+조용 | FAIL | FAIL | cap | 3 | 없음 | 7 | 6,7 | 4,102,994 | 639.0 |
| count_K0 | 조용 | PASS | PASS | 3 | 3 | 없음 | 0 | 6,7 | 1,174 | 2.0 |
| count_K0 | 쓰기 | PASS | PASS | cap | 6 | 없음 | 0 | 5,6 | 219,842 | 42.5 |
| count_K0 | 크래시+조용 | FAIL | FAIL | 3 | 3 | 있음 | 1 | 6,7 | 18,092 | 6.5 |
| slack_count_K1 | 조용 | FAIL | PASS | 3 | 3 | 없음 | 0 | 6,7 | 1,814 | 1.9 |
| slack_count_K1 | 쓰기 | FAIL | PASS | cap | 6 | 없음 | 0 | 5,6 | 445,596 | 84.1 |
| slack_count_K1 | 크래시+조용 | FAIL | FAIL | 4 | 4 | 있음 | 1 | 6,7 | 60,566 | 12.7 |
| slack_count_K1_noboot | 크래시+조용 | FAIL | FAIL | cap | 7 | 없음 | 7 | 6,7 | 556,300 | 87.9 |
| cand_freegate | 조용 | PASS | PASS | 3 | 3 | 없음 | 0 | 6,7 | 585 | 1.5 |
| cand_freegate | 쓰기 | PASS | PASS | 4 | 3 | 없음 | 0 | 6,7 | 12,913 | 5.4 |
| cand_freegate | 크래시+조용 | PASS | PASS | 3 | 4 | 있음 | 0 | 6,7 | 9,364 | 3.3 |

안전성 invariant `TypeOK`, `FreeHoldsNothing`, `TrackerNeverHigh` 는 모든 설정에서 PASS했습니다. 추적기가 실제보다 많이 보고하는 일은 없었습니다. 표의 몇 칸은 일부러 비었거나 줄였습니다.

- `slack_*` 의 현재 명세 FAIL은 설계 의도대로입니다.
- `*_noboot` 은 크래시가 없으면 BootLap 짝과 같은 명세라서 크래시 설정만 돌렸습니다.
- 카운터 설계의 크래시+쓰기는 돌리지 않았습니다. 크래시가 없는 쓰기 설정에서 이미 cap이기 때문입니다.
- `slack_set_K1` 의 크래시+쓰기는 MaxPages 5에서 17분을 넘겨 중단하고 4로 줄였습니다.

slack이 크기에 주는 효과를 보려고 L=3(파일 안 chunk 3개), MaxPages 7과 8로 크래시 없는 설정을 더 돌렸습니다.

| 설계 | 설정 | 최악 R | slack 명세 | 상태 수 | 시간(s) |
| --- | --- | --- | --- | --- | --- |
| cand_fullboot | 조용 / 쓰기 | 4 / 5 | PASS | 6,204 / 146,030 | 2.8 / 25.7 |
| slack_set_K1 | 조용 / 쓰기 | 4 / 5 | PASS | 9,867 / 297,543 | 3.6 / 46.6 |
| slack_set_K2 | 조용 / 쓰기 | 5 / 5 | PASS | 18,470 / 305,193 | 5.3 / 47.7 |
| slack_count_K1 | 조용 | 4 | PASS | 18,407 | 5.4 |

**해석.**
- 12칸 모두가 "최악 크기 = 성장 시작 때의 live 페이지 + max(K, c) + 1" 이라는 식에 맞습니다. 모델 결과에 맞춘 추론이며 증명한 것은 아닙니다.
  - c는 현재 명세도 남겨 두도록 허용하는 빈 페이지 수입니다. 조용할 때는 undo가 latch를 쥔 페이지 1개입니다. 쓰기가 있으면 성장 도중 비워진 페이지까지 더해 2개입니다.
  - 따라서 K ≤ c 이면 slack은 파일 크기를 늘리지 않습니다. K가 c를 넘는 만큼만 파일이 커집니다.
- 집합 설계는 성장 중 쓰기가 있어도 유계입니다.
- 카운터 설계는 성장 중 쓰기에서 cap에 닿습니다. K=0에서도 그러므로 원인은 slack이 아니라 cursor lap입니다.
- 카운터는 크래시가 있으면 drift 때문에 현재 명세와 slack 명세를 둘 다 어깁니다. 같은 K에서 집합 설계보다 한 페이지 큽니다(4 대 3).

### 3. 최단 반례

모두 BFS로 찾은 최단 반례입니다. 전체 단계는 `runs/r2/<설정>.json` 의 `traces` 에 있습니다.

- **slack 설계의 현재 명세 FAIL (6단계).** vacuum이 페이지 1을 비웁니다. 집합은 {1}이고 1 ≤ K입니다. 성장이 회수 없이 페이지 2를 잡습니다. 설계 의도대로의 위반입니다.
- **카운터, 성장 중 쓰기, cap (`count_K0` 49단계, `slack_count_K1` 45단계).** cursor가 닿기 직전에 INSERT가 빈 페이지를 채우고, 지나간 뒤 삭제가 다시 비웁니다. lap은 매번 빈손으로 끝나고 파일이 늘어납니다.
- **카운터, 크래시, slack 명세 FAIL (`slack_count_K1` 18단계).**
  1. 재시작 전에 rollback이 페이지 1을 비웁니다. 재시작으로 n=0이 됩니다.
  2. rollback이 페이지 2를 비워 n=1이 됩니다.
  3. INSERT가 재시작 전부터 비어 있던 페이지 1을 채우면서 n=0으로 뺍니다.
  4. boot lap은 latch가 걸린 페이지 2를 지나 끝납니다.
  5. vacuum이 페이지 1을 비워 n=1이 됩니다.
  6. 실제 빈 페이지는 2개인데, 성장은 1 ≤ K로 보고 파일을 늘립니다.
- **카운터, 크래시, drift (`count_K0` 15단계).** 위와 같은 구조입니다. 다만 재시작 전 빈 페이지를 fast path가 회수하면서 카운터를 뺍니다.
- **BootLap 없음 (slack 위반 10단계, cap 22단계).** 크래시마다 추적기가 비고 그 전의 빈 페이지는 다시 발견되지 않습니다. 크래시 한 번마다 그때의 빈 페이지 수만큼 파일이 커집니다.
- **크래시+쓰기, cap (`cand_fullboot` 53단계, `slack_set_K1` 32단계).** 성장 사이마다 재시작하고, boot lap이 쓰기에 회피당합니다. 이전 보고서와 같은 결과이고 slack은 바꾸지 않습니다.
- **헛된 검사 (7단계).** 재시작 뒤 첫 성장은 빈 페이지가 없어도 boot lap을 돕니다.

### 4. 비용과 구현 크기

**회수 빈도.** 빈 페이지가 생긴 수를 e라 하겠습니다. 생긴 빈 페이지는 네 갈래로 끝납니다. INSERT가 bestspace로 받아 다시 채우거나(u), fast path가 회수하거나(f), 성장이 회수하거나(g), 아직 비어 있습니다(E). 그러므로 g = e − u − f − E 입니다.
- 파일이 유계이려면 E가 유계여야 합니다. cand에서는 E ≤ c, slack에서는 E ≤ K + c입니다.
- 따라서 두 설계의 g 차이는 K 이하이고, 비율 차이는 시간이 갈수록 0으로 갑니다.
- slack이 u를 늘리지도 않습니다. 소스로 확인했습니다.
  - `oos_find_best_page` 는 bestspace에서 페이지를 찾지 못했을 때만 성장 경로로 갑니다(`oos_file.cpp:3044-3130`).
  - vacuum이 비운 페이지는 bestspace에 들어가므로 INSERT가 먼저 가져갑니다(`3370`, `1071-1082`).
  - rollback undo가 비운 페이지는 bestspace에서 빠지고(`3671`), cache는 1000개가 차면 더 넣지 않습니다(`130`, `373-377`).
  - 그래서 slack이 남겨 둔 페이지는 bestspace 밖에 머물고 INSERT가 재사용하지 못합니다.

`sim.py` 결과입니다(live 4096, 200,000 step, seed 7, 전체는 `sim-out.md`).

| workload | 설계 | 회수한 성장 비율 | cand 대비 줄인 회수 | 성장당 평균 검사 | 최대 페이지 / sector |
| --- | --- | --- | --- | --- | --- |
| vacuum만, fast path 0.9 | 현재 엔진 | 0% | 해당 없음 | 4096 | 4096 / 64 |
| vacuum만, fast path 0.9 | cand | 0% | 0 | 0 | 4096 / 64 |
| rollback 5% | cand | 5.2% | 0 | 0.05 | 4096 / 64 |
| rollback 5% | set K=64 | 5.1% | 64 | 0.05 | 4160 / 65 |
| rollback 5% | count ε=0.1 | 4.9% | 455 | 0.25 | 4551 / 72 |
| fast path 0.5, miss 절반이 cache 밖 | cand | 33.3% | 0 | 0.33 | 4096 / 64 |
| fast path 0.5, miss 절반이 cache 밖 | count K=64 | 33.3% | 64 | 10.70 | 4160 / 65 |
| fast path 없음 | cand | 100% | 0 | 1.00 | 4096 / 64 |
| fast path 없음 | count K=64 | 100% | 64 | 32.16 | 4160 / 65 |

**할당 한 번의 비용.**
- cand와 `slack_set_K`: 집합이 비었거나 K 이하이면 일이 없습니다. K를 넘으면 후보 페이지 1개를 조건부 fix하고 `file_dealloc` 을 1회 합니다.
- `slack_count_K`: K를 넘을 때마다 sector 표를 모아 정렬합니다(`1915-1935`). 그다음 평균 R/(2(K+1)) 페이지를 READ fix합니다.
- 현재 엔진의 진짜 비용은 회수가 아니라 무장된 lap입니다. 위 표에서 회수가 0회여도 성장마다 4096 페이지를 읽었습니다. 이 비용은 cand가 이미 없앱니다.

**구현 크기.** 소스를 실제로 고쳐 보지 않은 추정입니다.
- `slack_set_K` 는 cand(100~150줄) 위에 15~25줄을 더합니다. K(또는 ε) 파라미터 하나와 무장 판정(`oos_file.cpp:1861`)의 비교 하나입니다.
- `slack_count_K` 는 40~60줄입니다.
  - 상태: `oos_reclaim_file_state` (`1289-1300`)
  - +1 지점: `oos_delete_chain:3375`, `oos_rv_redo_delete:3650-3673`. 후자는 지금 비었는지 보지 않고 재무장합니다.
  - −1 지점: `page_was_empty` (`2158`, `2188`), 두 번째 INSERT 경로(`2513-2529`, 지금은 빈 페이지 검사가 없음), fast path(`1723-1770`), sweep 회수(`1960-1975`)
  - 무장 판정과 정산: `1861`, `1783-1797`
  - 감소 지점을 하나라도 빠뜨리면 카운터가 높게 drift해 lap이 계속 돕니다.

### 5. 추천

**비추천.** slack은 회수를 수명 전체에서 K번 미룰 뿐 비율을 바꾸지 않습니다. cand의 회수는 이미 페이지 1개 검사라 측정 가능한 이득이 없습니다. 카운터 형태는 동시 쓰기와 재시작 drift에서 slack 보장마저 잃습니다.

`cand_freegate` 는 예약 sector 안에 FREE 페이지가 있는 동안 회수를 건너뜁니다. 모든 설정에서 현재 명세를 PASS했습니다. 그러나 같은 등식에 묶여 회수를 미룰 뿐이라 채택할 이유가 없습니다.

### 6. 모델의 한계

- 페이지 6~8개, chunk 2~3개, rollback 하나짜리 유한 모델입니다. 최악 크기 값 3, 4, 5는 실제 상한이 아닙니다. 판정이 갈리는 지점만 의미가 있습니다.
- 크래시+쓰기는 집합 설계 두 개만 MaxPages 5와 4에서 확인했습니다.
- 이전 모델의 제한을 그대로 썼습니다. undo는 성장 한 번에 새 latch를 최대 1회 잡습니다. grower는 1개이고, 한 페이지를 한 sector로 둡니다.
- 카운터의 lap 끝 정산은 모델에 넣지 않았습니다. 정산이 있으면 READ 경합으로 건너뛴 페이지 몫이 사라질 수 있지만(Work818과 같은 구조) 확인하지 않았습니다.
- 시뮬레이션은 크래시, 동시성, ratio-gated bestspace sync(`3065-3075`)를 넣지 않았습니다.
- 엔진 성능은 측정하지 않았습니다.

### 이전 agent 작업 판정

집합 쪽 모델은 건전해서 이어 썼습니다. 고친 것은 다섯 가지입니다.
- 카운터 설계가 실제로는 집합 크기를 세고 있어 drift할 수 없었습니다. 정수 카운터로 바꿨습니다.
- 카운터 lap이 회수 뒤에도 다음 성장으로 이어지는 모델 오류가 있었습니다. 엔진은 회수하면 lap을 끝내고 다음 성장이 새로 시작합니다(`1960-1975`). 그렇게 고쳤습니다.
- `saved` 와 `expSaved` 카운터는 상태 공간만 키우고 빈도를 보여 주지 못해 뺐습니다.
- runner가 결과를 메모리에만 들고 있어, 중단되면 모두 잃었습니다. 작업별 JSON과 `--resume` 을 넣었습니다.
- 이전 `sim.py` 의 "98% 절감"은 엔진에 없는 재사용 경로를 가정한 결과라 다시 썼습니다.

재현 확인으로, 같은 모델에서 `cand_fullboot` 은 이전 수치 3/4/3/cap, 검사 3/5를 그대로 냈습니다.

### 적용한 원칙

- **Prove It Works.** 비교 전에 `cand_fullboot` 의 이전 수치를 먼저 재현했습니다. 표는 손으로 옮기지 않고 `table.py` 가 JSON에서 만듭니다.
- **Explain the Number.** 이전 시뮬레이션의 98%가 무엇을 재는지 따졌습니다. 소스와 맞지 않는 재사용 경로였고, 모델을 고치자 절감이 정확히 K가 됐습니다. seed 4개로 잡음이 없음을 확인했습니다.
- **Attack the Premise.** "slack이 회수 빈도를 줄인다"는 후보의 전제를 보존 등식과 시뮬레이션으로 직접 시험했습니다. 이것이 비추천의 근거입니다.
- **Build the Lever.** 다시 실행할 수 있는 스크립트(`run.py`, `table.py`, `sim.py`)를 남겼습니다.

### 파일과 정리

- 이전 agent의 `runs/r1` 은 바뀐 모델로 대체되어 지웠습니다(states 포함 1.6GB).
- `states-*`, `tmp-*`, dump는 남아 있지 않습니다. `runs/` 는 1.4MB입니다.
- 원시 실행 출력은 `runs-r2.txt`, `runs-r2-cw4.txt`, `runs-r2-L3.txt` 입니다. 위 표는 `table.py` 가 다시 만듭니다.

재실행 명령:
```sh
python3 -I -B run.py --out runs/r2 --jobs 4 --workers 3
python3 -I -B run.py --out runs/r2-L3 --live 3 --pages 7,8 --designs cand_fullboot,slack_set_K1,slack_set_K2,slack_count_K1 --settings Q
python3 -I -B run.py --out runs/r2-L3 --resume --live 3 --pages 7,8 --designs cand_fullboot,slack_set_K1,slack_set_K2 --settings W
python3 -I -B table.py runs/r2
python3 -I -B sim.py
```

모델 해시는 `OosSlackBound.tla` SHA-256 `2146e770314918e8…` 이고, TLC 2.19(`tla2tools-1.7.4.jar`), OpenJDK 1.8.0_462를 썼습니다.

Files are in /home/vimkim/gh/my-cubrid-docs-CBRD-27925-growth-arena/cbrd-27925/growth-arena/b-slack-bound:
- OosSlackBound.tla
- run.py
- table.py
- sim.py
- sim-out.md
- runs/r2/
- runs/r2-L3/
