# PR #8434 지연 재측정: #8495가 `feature/oos-merge`에 들어온 뒤

2026-11-17 (Asia/Seoul). 리뷰어가 승인 조건으로 요청한 재측정이다([리뷰](https://github.com/CUBRID/cubrid/pull/8434#pullrequestreview-5921146350)). 지난 측정([latency-8495](../latency-8495/README.md), 2026-11-12)은 #8495(CBRD-28046)를 PR head에 로컬로 cherry-pick해서 쟀다. 이번에는 #8495가 develop을 거쳐 `feature/oos-merge`에 병합된 실제 base와, 그 위로 rebase한 PR head를 비교한다.

## 결론

- 커밋 한 번에 로그 동기화(`fdatasync`)는 1번이다. 3000 커밋에 base 3011, PR head 3006이다. 지난 측정의 PR head 단독 6006은 더 이상 나오지 않는다.
- 행 단위 UPDATE+COMMIT 3000번의 중앙값은 base 7.71 s, PR head 4.45 s다. 12번 모두 PR head가 빨랐다(짝 차이 중앙값 −2.34 s). 장비 부하 때문에 범위가 넓어(2.7–24.3 s) 크기보다는 "느려지지 않았다"는 판정에 쓴다.
- UPDATE churn의 시간 지표는 모두 base와 같거나 PR head가 빠르다. 로그 양과 OOS 페이지 수는 지난 측정과 같은 경향이다(두 번째 UPDATE부터 로그 −41%, UPDATE drain 뒤 페이지 3513 → 1502, DELETE drain 뒤 3513 → 1).
- 따라서 ADR-0008 decision 7의 지연 조건은 실제 병합된 base에서 충족된다.

## 측정 대상

| 이름 | 커밋 | 내용 |
|---|---|---|
| base | `3e541fcf67` | `feature/oos-merge`. develop `8b9e7fd01f`까지 병합, #8495 `9d23fc6a32` 포함 |
| new | `ca1c1176fc` | PR #8434 head. `3e541fcf67` 위로 rebase하고 fail-stop 경로의 로그 flush를 추가한 커밋 |

- 두 빌드 모두 release_gcc로 빌드하고 설치했다(`~/.cub/install/CBRD-27781-lat2-{base,new}/release_gcc`).
- 장비는 Intel Xeon Gold 5218R, 80 CPU이고, 여러 사람이 함께 쓰는 서버다. 측정 중 1분 load는 행 단위 커밋에서 9.1–14.5, churn에서 8.6–149.7이었다. 조용한 장비 조건은 맞추지 못했다.
- 반복마다 두 빌드의 순서를 번갈아 바꿨다(`run2.sh`). 측정마다 DB를 새로 만들고 서버를 새로 띄웠다. 측정 스크립트는 지난 측정과 같다(`../latency-8495/oos_small_txn.sh`, `../latency-8495/oos_flush_count.sh`, `../bench/oos_update_churn.sh`).

## 결과

### 로그 동기화 횟수

행 하나의 OOS 값을 UPDATE하고 COMMIT하기를 3000번 하는 동안 `cub_server`의 `fdatasync` 횟수를 `strace -f -c`로 셌다. 빌드마다 2번 측정했다.

| 빌드 | fdatasync | UPDATE된 행 |
|---|---|---|
| base | 3011, 3011 | 3000, 3000 |
| new | 3006, 3006 | 3000, 3000 |

### 행 단위 커밋

작업은 위와 같고 strace는 없다. 빌드마다 12번 측정했고, 실패는 0건이다. 모든 측정에서 3000행이 갱신되었다.

| 빌드 | 중앙값 | 범위 | IQR |
|---|---|---|---|
| base | 7.71 s | 3.03–24.25 | 6.80–13.02 |
| new | 4.45 s | 2.68–22.83 | 3.04–6.49 |

짝 차이(new − base) 중앙값은 −2.34 s이고, 12번 모두 new가 빨랐다.

### UPDATE churn

빌드마다 12번 측정했고, 실패는 0건이다. 모든 측정에서 vacuum drain이 완료되었다.

| 지표 | base | new | new−base 짝 차이 중앙값 (빠름/느림) |
|---|---|---|---|
| insert_sec | 3.60 | 3.53 | −0.06 (9/3) |
| update1_sec | 3.67 | 3.60 | −0.01 (6/6) |
| update2_sec | 4.14 | 3.54 | −0.54 (11/1) |
| update3_sec | 3.83 | 3.53 | −0.29 (10/2) |
| delete_sec | 0.07 | 0.06 | −0.00 (6/6) |
| drain_sec_after_updates | 0.62 | 0.29 | −0.29 (12/0) |
| delete_drain_sec | 0.46 | 0.34 | −0.09 (11/1) |
| update1_log_bytes | 20.03 MB | 21.25 MB | +1.23 MB (0/12) |
| update2_log_bytes | 38.10 MB | 22.36 MB | −15.74 MB (12/0) |
| update3_log_bytes | 38.29 MB | 22.15 MB | −16.15 MB (12/0) |
| pages_after_update_drain | 3513 | 1502 | −2011 |
| pages_after_delete_drain | 3513 | 1 | −3512 |

- 시간 지표는 모두 중앙값이다.
- 첫 UPDATE의 로그는 new가 +6% 많고, 두 번째 UPDATE부터는 new가 41–42% 적다. 지난 측정의 base·fix 비교와 같은 방향이며, 원인은 이번 측정에서 따로 확인하지 않았다.

## 한계

- 공용 서버라 부하가 측정마다 달랐다. 판정은 반복마다 짝지은 차이로 했다.
- 행 단위 커밋에서 new가 빠른 이유는 이번 측정으로 확정하지 않았다. 판정에는 "base보다 느리지 않음"만 쓴다.

## 재현

```bash
# 두 worktree를 release_gcc로 빌드하고 설치한 뒤
OUT=$PWD/flush REPEATS=2  MODE=flush ./run2.sh
OUT=$PWD/small REPEATS=12 MODE=small ./run2.sh
OUT=$PWD/churn REPEATS=12 MODE=churn ./run2.sh
python3 analyze2.py small/results.csv small_update_sec,small_update_rows
python3 analyze2.py churn/results.csv insert_sec,update1_sec,update2_sec,update3_sec,delete_sec,drain_sec_after_updates,delete_drain_sec,pages_after_update_drain,pages_after_delete_drain,update1_log_bytes,update2_log_bytes,update3_log_bytes
```

원시 결과는 `flush-results.csv`, `small-results.csv`, `churn-results.csv`에 있다. `fdatasync` 횟수는 각 측정의 `strace.out`에서 읽었고, 그 원본은 Git에 넣지 않았다.
