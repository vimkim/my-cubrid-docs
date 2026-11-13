# CBRD-27230 재측정: 미할당 OOS chain 재사용

- 측정일 2026-11-13. 도구는 CBRD-28077의 `oosbench2.py` 이다. 변종 두 개를 추가했고, 하위 클래스 `oosbench_reuse.py` 가 OOS 페이지 수와 내용 검사를 더한다.
- 빌드는 모두 `release_gcc` 이고 동시에 실행했다.
  - `develop`
  - `reuse-base`: `b049fa155c`, PR #8434 head, 재사용 없음
  - `reuse`: `f0d6b03a56`
- 수치는 `perf stat -p cub_server` 로 잰 서버 instruction 수다. 시나리오별 3회 반복의 중앙값이고, vacuum drain을 포함한다.
- 상세 표, 페이지 수 시계열, profile은 [`results/tables-main.md`](results/tables-main.md) 에 있다. raw 디렉터리는 `/mnt/nvme/data-5/tmp/cbrd-27230-reuse/` 다.

## 결과

| 시나리오 | 크기 | io: dev / base / reuse | reuse/base | reuse/dev | warm: dev / base / reuse | reuse/base | reuse/dev |
|---|---|---|---|---|---|---|---|
| S5 | 4 KB | 10.41 / 15.46 / 4.21 G | x0.27 | x0.40 | 6.60 / 10.32 / 3.87 G | x0.38 | x0.59 |
| S5 | 8 KB | 10.25 / 14.54 / 2.22 G | x0.15 | x0.22 | 4.66 / 7.62 / 2.13 G | x0.28 | x0.46 |
| S5 | 64 KB | 6.42 / 12.30 / 0.52 G | x0.04 | x0.08 | 2.56 / 4.80 / 0.39 G | x0.08 | x0.15 |
| S8s | 8 KB | 0.52 / 1.78 / 0.49 G | x0.28 | x0.95 | 0.51 / 0.60 / 0.48 G | x0.79 | x0.93 |
| S8s | 64 KB | 0.70 / 2.21 / 0.49 G | x0.22 | x0.71 | 0.64 / 0.87 / 0.49 G | x0.56 | x0.76 |

S8s 4 KB는 reuse/dev가 x1.00 (io) 와 x0.99 (warm) 다.

**OOS 페이지 (8 KB, 40,000행, S5 UPDATE 후 vacuum 완료).**

| 빌드 | 페이지 수 |
|---|---|
| `c02f897268` (run3/run4 OOS 빌드, 대조군) | 40,001 → 80,001 |
| `reuse-base` | 40,001 → 40,001 |
| `reuse` | 40,001 → 40,001 |

30,000행 probe에서 `reuse-base` 는 commit 시점에 60,001페이지까지 갔다가 0.7초 안에 30,001로 돌아온다. 하지만 DB volume은 1,249 MiB에서 1,729 MiB로 커진 채 남는다. `reuse` 는 30,001페이지, 1,249 MiB 그대로다.

**정확성.** statement digest 180개, table checksum 30개, 내용 검사 15개가 세 빌드에서 모두 일치했다. 길이가 틀린 행과 실패는 0건이다.

**나머지 시나리오.** reuse/base 비율:
- 변화 없음: 읽기 x0.97-1.10, load x1.00-1.04, S7 x0.95-1.03, S8b x0.91-1.01, S11/S12 x1.00-1.06, 100 B(OOS 없음) x0.97-1.04.
- S6과 S9는 반복 간 편차(최대 2.46) 안에 있어 판단하지 않는다.

## 수치를 제한하는 것

- **`reuse-base`.** 다시 읽고, 다시 넣고, 회수한다. `oos_insert_many` 13.3%, `vacuum_oos_reclaim_notified_chains` 18.6%, `oos_find_best_page` 7.8%, `oos_alloc_page_with_reclaim` 7.2%, `oos_read` 4.1%. 누적 비율이라 합산할 수 없다.
- **`reuse`.** 위 함수들이 profile에서 사라졌다. 남은 것은 일반 행 UPDATE 경로다 (`locator_update_force` 23.9%).
- **하한.** OOS가 없는 100 B S5가 행당 약 40k instruction이다. `reuse` 는 4-64 KB에서 행당 48k-65k다. S8s는 100 B에서 0.46 G, `reuse` 에서 0.47-0.49 G다. 더 줄일 여지가 작다.
- **S5에서 `reuse` 가 develop보다 싼 이유.** develop은 8 KB 행 전체를 log한다 (`log_diff` 17%, `memmove` 15%, LZ4 5%).

## 주의

- **대조 기준.** `reuse-base` 는 CBRD-28077의 OOS 기준(`c02f897268`)에 CBRD-27781/27925 commit 14개를 더한 것이다. `c02f897268` 을 다시 돌리면 S5 8 KB가 develop의 x10.41(warm)과 x7.23(io)으로, run3/run4를 재현한다. `reuse-base` 는 이미 develop의 x1.4-1.9다. `c02f897268` 대비 `reuse` 는 x0.045(warm), x0.030(io)이다. 14개 중 어느 commit이 차이를 냈는지는 분리하지 않았다.
- **`reuse-base` 의 첫 S5 반복.** 파일 성장을 포함해 10.07 G가 나왔다 (다른 반복은 7.09 G). 중앙값이 두 상태를 섞는다.
- **60,001페이지 표본.** sampler가 table lock을 기다리므로 statement 도중이 아니라 commit 시점 값이다.
- **호스트.** 80코어 공유 호스트다. 다른 사용자의 `cub_server` 가 내내 약 700% CPU를 썼다. 1분 load average는 최소 5.6, 중앙값 13.5, 최대 80.3이다. 시간이 아니라 instruction 수로 판단했다.
- **측정하지 않음.** partition 테이블, OOS 컬럼을 할당하는 UPDATE, HA (`ha_mode=off`).
