# develop·OOS·Sidecar·Inner Table workload별 성능 비교

- 이슈: [CBRD-28077](https://jira.cubrid.org/browse/CBRD-28077) (상위 CBRD-26978)
- 관련: CBRD-26357(OOS), CBRD-28053(Sidecar POC), CBRD-28054(Inner Table POC), CBRD-27230, CBRD-27872, CBRD-27788
- 측정일: 2026-11-12 22:07 ~ 2026-11-13 00:34 (Asia/Seoul)
- 원시 결과: 로컬 `/home/vimkim/temp/oos-pocs-benchmark/runs/run-20261112-220750/` (git에 넣지 않음). 집계 표 전체는 [results-tables.md](results-tables.md)에 있다.

> **정정 (2026-11-13).** S7과 S8b는 의도한 크기의 값을 쓰지 않았다. develop에서 같은 형태의 UPDATE가 재사용된 plan으로 실행되면 `REPEAT(X'..', N)`이 N/4 크기의 텍스트를 저장한다. 그래서 S7·S8b는 첫 실행만 의도한 크기였다. S8s, S9와 io 조건의 변경도 그 상태 위에서 측정되었다. 반복 측정과 결과·값 길이 검사를 더한 3차 실행이 이 항목들을 대체한다: [run3-report.md](run3-report.md) (원인은 6.4절). S1·S2·S3·S5의 방향과 OOS 재적재 확인은 3차 실행에서도 재현되었다.

## 질문과 결론

큰 컬럼 값을 행 밖에 두는 세 설계(OOS, Sidecar, Inner Table)는 develop과 비교해 어떤 workload에서 이득을 보고 어떤 workload에서 손해를 보는가? 대상 독자는 OOS 이후 저장 구조를 결정하는 엔진 개발자와 리뷰어다.

결론은 다음과 같다. 수치는 모두 develop 대비 서버 명령어 수 비율(작을수록 좋음)이며, 큰 값이 실제로 행 밖으로 나가는 8 KB와 64 KB 값에서 측정했다.

1. **작은 컬럼만 읽는 scan(S1)은 세 설계 모두 크게 이긴다.** IO가 있을 때 명령어 0.01~0.07배, OS 읽기 바이트 0.00~0.02배다. 세 설계 사이의 차이는 작다.
2. **작은 컬럼만 바꾸는 UPDATE(S5)에서 결과가 가장 크게 갈린다.** Sidecar 0.07~0.41배, Inner Table 0.42~0.86배인데, OOS는 1.8~16배로 develop보다 훨씬 나쁘다. OOS가 바꾸지 않은 큰 값도 매번 다시 읽고 새로 적재하기 때문이다. 이 동작은 이미 CBRD-27230으로 등록되어 있고, 이번 측정이 그 비용을 처음으로 정량화한다(아래 "OOS의 UPDATE 재적재").
3. **큰 값을 다시 쓰는 UPDATE(S6)는 세 설계 모두 develop보다 비싸다.** Sidecar 1.2~1.35배, Inner Table 약 2.0~3.0배, OOS 3.3~5.6배다.
4. **큰 값을 모두 읽는 scan(S2)은 Inner Table이 가장 비싸다.** OOS·Sidecar는 0.7~1.8배인데 Inner Table은 2.3~11배다. 값 하나를 chunk 행 여러 개로 나눠 index로 다시 모으기 때문이다.
5. **PK로 한 행을 읽을 때 Inner Table은 큰 컬럼을 고르지 않아도 chunk를 읽는다(S3n).** 64 KB에서 OS 읽기가 develop 1,004 MiB, OOS 4 MiB, Sidecar 11 MiB, Inner Table 1,828 MiB였다. scan 경로(S1)에서는 chunk를 읽지 않으므로, 단건 fetch 경로에서만 참조를 펼치는 것으로 보인다(코드 미확인 추정).
6. **기능을 쓰지 않는 경우(값 100 B, 2 KB)는 네 빌드가 거의 같은 일을 한다.** 적재(S4)를 빼면 page fetch 비율은 모두 0.98~1.03이고, 명령어 비율은 반복 측정한 읽기에서 0.93~1.02다(Inner Table의 wide scan만 1.08~1.21). 한 번만 측정한 쓰기에서는 0.89~1.16까지 흔들린다. 다만 세 POC의 develop 기준 커밋이 서로 달라서 이 값으로 "미사용 비용 5% 이내" 같은 판정을 내리지는 않는다.

종합하면, 이번 workload에서 develop보다 나빠지는 정도가 가장 작은 설계는 Sidecar이고, OOS는 UPDATE 계열에서, Inner Table은 큰 값 읽기와 PK 단건 조회에서 비용이 크다. OOS의 UPDATE 비용 대부분은 CBRD-27230이 해결되면 줄어들 것으로 예상하지만, 이번에 측정하지는 않았다.

## 비교 대상

모두 2026-11-12의 브랜치 HEAD를 그대로 빌드했다. 기준 develop 커밋을 서로 맞추지 않았다.

| 대상 | 브랜치 | 커밋 | 기준 develop | 행 밖으로 옮기는 조건 |
| --- | --- | --- | --- | --- |
| develop | `develop` | `a7f220d5d7` | - | 없음(한 페이지를 넘는 행은 overflow) |
| OOS | `feature/oos-merge` | `c02f897268` | `a7f220d5d7` | 행이 inline 목표(16 KB 페이지의 1/4, 약 4,060 B)를 넘으면 큰 값부터 OOS 파일로 |
| Sidecar | `sidecar` | `7c5028d5bd` | `e64a04a79a` | 기본값 그대로: 행이 `sidecar_inline_target`=4060을 넘으면 256 B 이상 값을 store heap으로 |
| Inner Table | `inner-table` | `fbb4f25057` | `81fa5696cd` | `inner_table_threshold`=4060으로 설정, `t__inner` companion 생성 |

- 빌드: `release_gcc` preset(GCC 11.5, RelWithDebInfo, `-O2`). 커밋마다 별도 worktree(`b28077-*`, detached)와 별도 설치 경로를 썼다.
- 빌드 플래그 차이: 최신 develop(`a7f220d5d7`)과 OOS는 `src/optimizer/query_planner.c`의 `-Werror=return-local-addr` 경고 때문에 release 빌드가 실패한다. develop·OOS·Sidecar 빌드에는 `-Wno-error=return-local-addr`을 더했다. Inner Table은 더하지 않고도 빌드되었다. 이 플래그는 경고를 오류로 바꿀지만 정하고 생성 코드는 바꾸지 않는다.
- 공통 설정: 이 설치에서는 Java PL 서버가 뜨지 않아 네 DB 모두 `stored_procedure=no`로 측정했다.
- 저장 확인: 8 KB 적재 직후 `SHOW HEAP OOS`, `SHOW HEAP SIDECAR`, `t__inner`의 행 수로 세 설계 모두 값을 행 밖으로 옮긴 것을 확인했다. 예를 들어 8 KB·12,000행에서 heap 페이지는 57~65개였고, OOS 레코드 12,000개, Sidecar store 레코드 12,000개, Inner Table chunk 행 24,000개가 있었다.

## 측정 방법

### 테이블과 값 크기

`t (id INT PRIMARY KEY, k INT NOT NULL, s VARCHAR(50), big BIT VARYING)`를 `INSERT ... SELECT`로 채운다. `big`은 `REPEAT(X'AB', SIZE)`다. BIT VARYING은 압축되지 않으므로 모든 빌드가 SIZE 바이트를 그대로 저장한다.

| 값 크기 | 행 수 | 의미 |
| --- | ---: | --- |
| 100 B | 1,000,000 | 모든 빌드에서 inline. 기능 미사용(S10) |
| 2 KB | 400,000 | 행이 4,060 B보다 작아 어느 설계도 옮기지 않는다. 대조군 |
| 8 KB | 120,000 | develop은 inline(페이지당 1행), 세 설계는 모두 옮긴다 |
| 64 KB | 16,000 | develop은 overflow, 세 설계는 모두 옮긴다 |

### IO 조건

- **io**: `data_buffer_size=128M`. 측정할 문장마다 서버를 재시작하고, 서버를 멈춘 상태에서 DB 파일의 OS page cache를 `posix_fadvise(DONTNEED)`로 비운다(root 권한 불필요).
- **warm**: `data_buffer_size=4G`. 읽기는 한 번 실행해 데우고 나서 측정한다.

### 시나리오

변경 시나리오는 테이블 상태를 바꾸므로 아래 순서로 한 DB에서 실행한다. 크기와 빌드 조합마다 새 DB를 만든다.

| # | 내용 | 반복 |
| --- | --- | --- |
| S4 | 적재 `INSERT ... SELECT` N행 | warm 1회 |
| S1 | `SELECT SUM(k) FROM t` | 모드별 3회 |
| S2 | `SELECT COUNT(*) FROM t WHERE big > X'00'` | 모드별 3회 |
| S3n | PK 단건 조회 5,000회, `SELECT k ... WHERE id = ?` | 모드별 3회 |
| S3w | PK 단건 조회 5,000회, `SELECT COUNT(*) ... WHERE id = ? AND big > X'00'` | 모드별 3회 |
| S5 | `UPDATE t SET k = k + 1` 전체 행, 한 트랜잭션 | 모드별 1회 |
| S6 | 행의 1/4에 `UPDATE t SET big = <새 값>` | 모드별 1회 |
| S7 | 3,000회 반복: 한 행의 `big` UPDATE + 한 행 INSERT + COMMIT | 모드별 1회 |
| S8b | 3,000회 반복: 100개 hot 행 중 하나의 `big` UPDATE + COMMIT | 모드별 1회 |
| S8s | 3,000회 반복: 100개 hot 행 중 하나의 `k` UPDATE + COMMIT | 모드별 1회 |
| S9 | 행의 1/4 DELETE, 한 트랜잭션 | 모드별 1회 |

각 측정은 서버가 idle(0.25초 간격 8회 연속 CPU 1% 이하, vacuum 종료)이 된 뒤 시작한다. 변경 시나리오는 문장이 끝난 뒤 서버가 다시 idle이 될 때까지의 일(vacuum, flush)도 "drain"으로 따로 잰다. 표의 명령어·쓰기 바이트·log 쓰기는 drain을 포함한다.

### 지표

| 지표 | 수집 방법 |
| --- | --- |
| 서버 명령어 수 | `perf stat -e instructions,cycles,task-clock -p <cub_server>` |
| data page fetch, IO read/write | `cubrid statdump -c`의 전후 차이. 서버는 watcher가 있을 때만 통계를 모으므로 서버마다 `cubrid statdump -i 3600`을 띄워 두었다 |
| OS 읽기·쓰기 바이트 | `/proc/<cub_server>/io`의 `read_bytes`, `write_bytes` 전후 차이 |
| 경과 시간 | csql 실행의 wall time |

### 한계

- **경과 시간은 신뢰하기 어렵다.** 측정 서버는 공용 서버이며 시작 시 load average가 17~30이었다. 앞선 시험 실행 때는 다른 사용자의 벤치마크로 78(80 core)까지 올랐다. 같은 읽기의 반복 사이 wall time이 최대 4.6배 차이 났다. 반면 명령어 수의 반복 간 차이는 상위 15개 목록에 들지 못할 만큼 작았다. 그래서 결론은 명령어 수와 page·IO 횟수로 내리고, wall time은 참고로만 둔다.
- **변경 시나리오는 1회 측정이다.** 반복 측정한 읽기보다 흔들림이 크다(100 B에서 0.89~1.16).
- **기준 develop 커밋이 다르다.** 기능 미사용 비용을 판정하려면 같은 develop 위에 다시 올려 측정해야 한다.
- **warm 단계의 변경이 io 단계의 변경보다 먼저 실행된다.** io 단계의 S5~S9는 warm 단계가 남긴 상태(늘어난 파일, 이미 바뀐 값) 위에서 측정된다. 네 빌드가 같은 순서를 따르므로 비교는 공정하지만, 같은 빌드의 warm과 io 수치를 직접 비교할 때는 주의해야 한다.
- **DB 크기는 볼륨 파일 크기다.** 볼륨이 큰 단위로 늘어나므로 정밀하지 않다.
- 동시 접속 workload(예: CBRD-27827의 OOS 헤더 경합)는 범위 밖이다.

## 결과

### 8 KB 값, io 조건

명령어 수(drain 포함)의 절대값이다.

| 시나리오 | develop | OOS | Sidecar | Inner Table |
| --- | ---: | ---: | ---: | ---: |
| S1 narrow scan | 3.03 G | 216 M | 109 M | 96 M |
| S2 wide scan | 2.96 G | 4.00 G | 3.23 G | 6.67 G |
| S3n PK 조회, 작은 컬럼 | 2.67 G | 2.63 G | 2.49 G | 3.28 G |
| S3w PK 조회, 큰 컬럼 | 2.83 G | 3.40 G | 2.79 G | 3.18 G |
| S5 작은 컬럼 UPDATE | 25.4 G | **325 G** | 4.64 G | 10.7 G |
| S6 큰 컬럼 UPDATE | 11.4 G | 56.4 G | 15.3 G | 23.0 G |
| S7 UPDATE+INSERT 반복 | 7.36 G | 16.1 G | 9.31 G | 8.52 G |
| S8b 큰 컬럼 UPDATE 반복 | 3.79 G | 6.62 G | 3.47 G | 4.35 G |
| S8s 작은 컬럼 UPDATE 반복 | 2.73 G | 4.71 G | 2.05 G | 2.46 G |
| S9 DELETE 1/4 | 15.6 G | 6.45 G | 8.09 G | 15.3 G |

### 64 KB 값, io 조건

| 시나리오 | develop | OOS | Sidecar | Inner Table |
| --- | ---: | ---: | ---: | ---: |
| S1 narrow scan | 1.72 G | 38 M | 24 M | 21 M |
| S2 wide scan | 1.74 G | 1.83 G | 1.83 G | 6.61 G |
| S3n PK 조회, 작은 컬럼 | 3.93 G | 2.41 G | 2.51 G | 6.38 G |
| S3w PK 조회, 큰 컬럼 | 3.90 G | 3.66 G | 3.86 G | 6.44 G |
| S5 작은 컬럼 UPDATE | 11.7 G | **189 G** | 0.77 G | 7.71 G |
| S6 큰 컬럼 UPDATE | 8.74 G | 29.5 G | 10.8 G | 26.4 G |
| S7 UPDATE+INSERT 반복 | 27.8 G | 51.8 G | 29.7 G | 42.8 G |
| S8b 큰 컬럼 UPDATE 반복 | 12.7 G | 16.7 G | 11.5 G | 17.8 G |
| S8s 작은 컬럼 UPDATE 반복 | 2.95 G | 6.17 G | 2.14 G | 3.65 G |
| S9 DELETE 1/4 | 5.91 G | 4.07 G | 4.56 G | 18.2 G |

OS 읽기 바이트(io 조건, 64 KB)에서 develop의 PK 조회가 크다. develop은 64 KB 행을 overflow로 저장하므로, 작은 컬럼만 고르는 PK 조회(S3n)도 overflow 페이지를 읽는다.

| 시나리오 | develop | OOS | Sidecar | Inner Table |
| --- | ---: | ---: | ---: | ---: |
| S1 narrow scan | 1,260 MiB | 5 MiB | 6 MiB | 5 MiB |
| S2 wide scan | 1,260 MiB | 1,261 MiB | 1,261 MiB | 2,013 MiB |
| S3n PK 조회, 작은 컬럼 | 1,004 MiB | 4 MiB | 11 MiB | 1,828 MiB |
| S3w PK 조회, 큰 컬럼 | 1,030 MiB | 400 MiB | 1,033 MiB | 1,817 MiB |

### develop 대비 비율 요약

명령어 수(drain 포함) 비율이며, 순서는 OOS / Sidecar / Inner Table이다. 1보다 작으면 develop보다 일을 적게 한다.

| 시나리오 | io 8 KB | io 64 KB | warm 8 KB | warm 64 KB |
| --- | --- | --- | --- | --- |
| S1 narrow scan | 0.07 / 0.04 / 0.03 | 0.02 / 0.01 / 0.01 | 0.30 / 0.12 / 0.08 | 0.17 / 0.08 / 0.07 |
| S2 wide scan | 1.35 / 1.09 / 2.25 | 1.05 / 1.05 / 3.80 | 1.77 / 1.10 / 9.53 | 0.68 / 0.76 / 11.25 |
| S3n PK 조회, 작은 컬럼 | 0.98 / 0.93 / 1.23 | 0.61 / 0.64 / 1.62 | 0.98 / 0.98 / 1.06 | 0.94 / 0.93 / 1.68 |
| S3w PK 조회, 큰 컬럼 | 1.20 / 0.99 / 1.12 | 0.94 / 0.99 / 1.65 | 1.01 / 0.99 / 1.08 | 1.12 / 0.97 / 1.64 |
| S5 작은 컬럼 UPDATE | 12.81 / 0.18 / 0.42 | 16.26 / 0.07 / 0.66 | 1.82 / 0.41 / 0.76 | 2.05 / 0.13 / 0.86 |
| S6 큰 컬럼 UPDATE | 4.96 / 1.35 / 2.02 | 3.37 / 1.23 / 3.02 | 5.59 / 1.32 / 1.98 | 3.28 / 1.20 / 2.05 |
| S7 UPDATE+INSERT 반복 | 2.19 / 1.26 / 1.16 | 1.86 / 1.07 / 1.54 | 1.82 / 1.31 / 1.23 | 1.59 / 0.98 / 1.24 |
| S8b 큰 컬럼 UPDATE 반복 | 1.75 / 0.92 / 1.15 | 1.32 / 0.91 / 1.41 | 1.63 / 1.00 / 1.25 | 1.17 / 0.96 / 1.41 |
| S8s 작은 컬럼 UPDATE 반복 | 1.73 / 0.75 / 0.90 | 2.09 / 0.73 / 1.24 | 1.59 / 0.85 / 0.92 | 1.62 / 0.74 / 1.11 |
| S9 DELETE 1/4 | 0.41 / 0.52 / 0.98 | 0.69 / 0.77 / 3.09 | 0.52 / 0.68 / 1.59 | 0.23 / 0.44 / 2.13 |
| S4 적재 | - | - | 0.94 / 1.02 / 1.16 | 1.02 / 1.02 / 1.35 |

### 기능을 쓰지 않을 때 (100 B, 2 KB)

값이 inline으로 남는 두 크기에서는 적재(S4)를 빼면 page fetch 비율이 모든 시나리오에서 0.98~1.03이다. 네 빌드가 같은 페이지를 거의 같은 횟수만큼 읽고 쓴다. 적재의 page fetch 비율은 0.92~1.02였다. 명령어 비율은 3회 반복한 읽기 시나리오(S1~S3)에서 0.93~1.02, 1회 측정한 변경 시나리오에서 0.89~1.16이다. 예외는 Inner Table의 wide scan(S2)으로, 값이 inline인데도 1.08~1.21배였다. `big`을 비교할 때마다 참조인지 확인하는 비용으로 보이며, 코드로 확인하지는 않았다.

### DB 크기 (볼륨 파일 합계)

| 크기 | 시점 | develop | OOS | Sidecar | Inner Table |
| --- | --- | ---: | ---: | ---: | ---: |
| 8 KB | 적재 직후 | 2,401 MiB | 2,305 MiB | 2,401 MiB | 2,433 MiB |
| 8 KB | 마지막 | 2,593 MiB | **4,705 MiB** | 3,041 MiB | 3,233 MiB |
| 64 KB | 적재 직후 | 1,633 MiB | 1,633 MiB | 1,633 MiB | 2,529 MiB |
| 64 KB | 마지막 | 2,049 MiB | 3,201 MiB | 2,017 MiB | 3,649 MiB |

## OOS의 UPDATE 재적재

S5에서 OOS의 비용이 develop의 12~16배(io)로 나와 따로 확인했다.

**재현.** OOS 빌드에서 8 KB 값 30,000행을 적재하고, io 조건(128 MB buffer, 재시작, cache 비움)에서 `UPDATE t SET k = k + 1`을 실행했다. 앞뒤로 `SHOW HEAP OOS OF t`를 보았다. 실행 스크립트는 [tools/oos_s5_probe.py](tools/oos_s5_probe.py)다.

| 시점 | `Oos_num_user_pages` | `Oos_num_recs` | `Oos_recs_sumlen` |
| --- | ---: | ---: | ---: |
| UPDATE 전 | 30,001 | 30,000 | 246,720,000 |
| UPDATE·vacuum 후 | 60,001 | 30,000 | 246,720,000 |

`big`을 바꾸지 않았는데 OOS 레코드 30,000개가 새로 쓰였다. vacuum이 옛 레코드를 지워 레코드 수는 그대로지만 OOS 파일 페이지는 두 배가 되었고, 빈 페이지는 다시 쓰이지 않았다.

**프로파일.** 같은 UPDATE를 `perf record -g -F 499`로 기록했다. 누적(children) 비율이 큰 함수는 다음과 같다.

| 함수 | 누적 비율 | 하는 일 |
| --- | ---: | --- |
| `heap_oos_insert_serialized_values` → `oos_insert_many` | 19% | 바꾸지 않은 값을 OOS에 새로 적재 |
| `oos_find_best_page` → `oos_alloc_page_with_reclaim` | 16% / 15% | 적재할 페이지 찾기, 빈 페이지 회수 검사 |
| `heap_attrvalue_read_oos` → `oos_read` | 9% | 옛 값을 다시 읽기 |
| `pgbuf_get_victim*`, `pgbuf_flush_victim_candidates` | 약 7% | 작은 buffer에서 쫓아낼 페이지 찾기 |

이 동작은 CBRD-27230("변경 없는 OOS 값 중복 적재 방지", Open)에 정리된 AS-IS와 같다. UPDATE는 할당하지 않은 OOS 컬럼도 다시 읽고(`oos_read`) 새 chain으로 적재한다(`oos_insert`). 빈 페이지 회수 검사 비용은 CBRD-27872가 다룬다. 이번 측정이 보탠 것은 크기다. 작은 컬럼만 바꾸는 UPDATE가 OOS에서 develop보다 io 조건 명령어 12~16배, warm 조건 1.8~2.0배를 쓰고, 8 KB 시나리오가 끝났을 때 DB가 develop의 1.8배(4,705 MiB 대 2,593 MiB)였다.

시험 실행(8 KB, 12,000행)에서 warm S6가 page fetch 5,000만 회를 기록한 적이 있다. 전체 실행에서는 재현되지 않았다(80만 회). 이번에는 원인을 조사하지 않았다.

## 후속으로 볼 것

- CBRD-27230이 반영된 OOS로 S5·S7·S8s를 다시 측정하면 OOS의 UPDATE 손해가 얼마나 줄어드는지 알 수 있다.
- Inner Table의 PK 단건 조회(S3n)가 큰 컬럼을 고르지 않아도 chunk를 읽는 원인을 코드에서 확인한다.
- 기능 미사용 비용을 판정하려면 세 POC를 같은 develop 커밋 위에 올리고, 한가한 서버에서 반복 수를 늘려 다시 측정한다.
- 동시 접속 workload는 이번 범위 밖이다.

## 재현 방법

1. 빌드할 커밋마다 worktree를 만들고 `release_gcc` preset으로 빌드·설치한다. GCC 11에서는 develop `a7f220d5d7` 이후 커밋에 `-Wno-error=return-local-addr`이 필요하다.

   ```sh
   git worktree add --detach ../b28077-develop a7f220d5d7   # oos c02f897268, sidecar 7c5028d5bd, inner fbb4f25057
   cmake --preset release_gcc
   cmake -B build_preset_release_gcc \
     -DCMAKE_CXX_FLAGS_RELWITHDEBINFO="-O2 -ggdb3 -DNDEBUG -finline-functions -Wno-error=stringop-truncation -Wno-error=maybe-uninitialized -Wno-error=format-overflow -Wno-error=format-truncation -Wno-error=return-local-addr"
   cmake --build --preset release_gcc && cmake --install build_preset_release_gcc
   ```

2. 설치마다 독립된 CUBRID 환경(설치 경로, `cubrid.conf`, `databases.txt`, master 포트)을 준비한다. 드라이버는 worktree에서 `direnv exec`로 이 환경을 읽는다. 다른 방식으로 환경을 준비했다면 [tools/oosbench.py](tools/oosbench.py)의 `load_env`, `create`, `drop`을 그 방식에 맞춘다.
3. 측정과 집계:

   ```sh
   OOSBENCH_WORKTREES=/path/to/parent python3 tools/oosbench.py --root runs
   python3 tools/analyze.py runs/run-<timestamp> --out summary.md
   ```

   `--quick`은 행 수를 1/10로 줄인 점검용이고, `--sizes`, `--variants`, `--only-scenarios`로 범위를 줄일 수 있다.
