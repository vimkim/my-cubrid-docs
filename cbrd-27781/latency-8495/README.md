# PR #8434 지연 재측정: #8495(CBRD-28046) 적용 시

2026-11-12. ADR-0008 decision 7의 지연 조건을 다시 판정하려고, PR #8434 head에 PR #8495를 얹어 측정했다. 지난 측정(2026-11-11, `94ed2ea46`)에서 행 단위 커밋이 base보다 +65% 느렸고, 원인은 `log_append_commit_postpone`의 추가 로그 flush였다.

## 결론

- #8495를 얹으면 커밋 한 번에 로그 동기화(`fdatasync`)가 다시 1번이 된다. 횟수는 base 3011, PR head 6006, #8495 적용 3006이었다.
- 행 단위 커밋 3000번의 중앙값은 base 12.28 s, PR head 16.22 s(+32%), #8495 적용 11.13 s(−9.4%)였다. #8495 적용과 base의 짝 차이 중앙값은 −1.43 s이고, 이 값은 base 사분위 범위 폭 안이다. handoff 기준으로 "나빠지지 않음"이다.
- UPDATE churn은 세 빌드 모두 handoff 기준 안이다. #8495는 churn을 나쁘게 만들지 않았다.
- 따라서 decision 7의 지연 조건은 #8495가 함께 들어가는 경우에만 충족된다. #8434만으로는 충족되지 않는다(+32%, 12번 중 10번 PR head가 더 느림).

## 측정 대상

| 이름 | 커밋 | 내용 |
|---|---|---|
| base | `50619ce53` | #8434의 base(`feature/oos-merge`) |
| new | `0d9732a63` | #8434 head |
| fix | `75dba5b98` | `0d9732a63` + #8495 `6a7ca6b4a` cherry-pick(로컬 전용) |

- 세 빌드 모두 release_gcc(`just preset release_gcc`)로 빌드했다.
- 장비는 Intel Xeon Gold 5218R, 80 CPU이고, 여러 사람이 함께 쓰는 서버다. 측정 중 1분 load는 18~232였다. 조용한 장비 조건은 맞추지 못했다.
- 노이즈를 줄이려고 반복마다 세 빌드의 실행 순서를 바꿨다. 6번에 한 바퀴로 여섯 가지 순서가 모두 나온다(`run3.sh`). 측정마다 DB를 새로 만들고 서버를 새로 띄웠다.

## 결과

### 로그 동기화 횟수

`oos_flush_count.sh`로 측정했다. 행 하나의 OOS 값을 UPDATE하고 COMMIT하기를 3000번 하는 동안, `cub_server`에 `strace -f -c`를 붙여 `fdatasync` 횟수를 셌다. 빌드마다 2번 측정했다.

| 빌드 | fdatasync | UPDATE된 행 |
|---|---|---|
| base | 3011, 3011 | 3000, 3000 |
| new | 6006, 6006 | 3000, 3000 |
| fix | 3006, 3006 | 3000, 3000 |

strace를 붙인 동안의 시간은 판정에 쓰지 않는다.

### 행 단위 커밋(보조 B)

`oos_small_txn.sh`로 측정했다. 작업은 위와 같고 strace는 없다. 빌드마다 12번 측정했고, 실패는 0건이었다. 모든 측정에서 3000행이 갱신되었다.

| 빌드 | 중앙값 | 범위 | IQR |
|---|---|---|---|
| base | 12.28 s | 7.23–26.09 | 8.67–21.12 |
| new | 16.22 s | 11.26–33.20 | 14.37–20.02 |
| fix | 11.13 s | 6.64–26.85 | 8.86–13.71 |

| 비교 | 짝 차이 중앙값 | 앞쪽이 빠름 / 느림 |
|---|---|---|
| fix − base | −1.43 s | 8 / 4 |
| fix − new | −6.71 s | 10 / 2 (부호 검정 양측 p ≈ 0.039) |

- 이 측정의 한계 요인은 커밋마다 기다리는 로그 동기화다. new와 base의 차이(커밋당 약 1.3 ms, 노이즈 포함)는 커밋당 1번 늘어난 `fdatasync`로 설명되고, fix에서 동기화가 1번으로 줄면 그 차이도 사라진다.
- 서버 부하 때문에 범위가 넓다(7~33 s). 판정은 반복마다 짝지은 차이로 했다.

### UPDATE churn

`../bench/oos_update_churn.sh`로 측정했다. 빌드마다 12번 측정했고, 실패는 0건이었다. 모든 측정에서 vacuum drain이 완료되었다.

| 지표 | base | new | fix | fix−base 짝 차이 중앙값 (빠름/느림) |
|---|---|---|---|---|
| insert_sec | 3.69 | 4.01 | 3.59 | +0.04 (5/7) |
| update1_sec | 3.65 | 3.96 | 3.65 | +0.07 (5/7) |
| update2_sec | 3.98 | 3.90 | 3.65 | −0.37 (11/1) |
| update3_sec | 3.75 | 3.78 | 3.64 | −0.12 (9/3) |
| delete_sec | 0.06 | 0.07 | 0.06 | −0.00 (7/5) |
| drain_sec_after_updates | 0.36 | 0.29 | 0.29 | −0.06 (10/2) |
| delete_drain_sec | 0.38 | 0.34 | 0.33 | −0.04 (10/2) |
| pages_after_update_drain | 3539 | 1503 | 1503 | −2036 |

- 시간 지표는 모두 중앙값이다. fix와 base의 짝 차이는 모두 base 사분위 범위 폭 안이거나 fix 쪽이 빠르다.
- churn은 행을 묶어 한 트랜잭션으로 커밋하므로 커밋당 flush 비용이 거의 드러나지 않는다. 그래서 #8495의 영향도 작다.

## 재현

```bash
# 세 worktree를 release_gcc로 빌드하고 설치한 뒤
OUT=$PWD/flush REPEATS=2  MODE=flush ./run3.sh
OUT=$PWD/small REPEATS=12 MODE=small ./run3.sh
OUT=$PWD/churn REPEATS=12 MODE=churn ./run3.sh
python3 analyze3.py small/results.csv small_update_sec,small_update_rows
```

`run3.sh`는 설치 경로 `~/.cub/install/CBRD-27781-lat2-{base,new,fix}/release_gcc`를 쓴다. 원시 결과는 `flush-results.csv`, `small-results.csv`, `churn-results.csv`에 있다.
