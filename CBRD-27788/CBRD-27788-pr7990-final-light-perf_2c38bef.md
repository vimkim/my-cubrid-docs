# PR #7990 최종 가벼운 성능 확인 (2c38bef)

2026-11-19 (Asia/Seoul). PR CUBRID/cubrid#7990 본문에 넣을 성능 메모를 위한 before/after 비교다. 사용자가 전체 수락 측정이 아니라 가벼운 확인을 요청했으므로, [인계 문서](final-perf-handoff.md) 4·5절의 시나리오 중 P1-a, P1-b, P3-d만 돌렸다. 수락 기준의 통과·실패는 판정하지 않고, 차이와 5%를 넘는 변화만 적는다.

## PR 본문용 결론 (세 줄)

- 일반 테이블 scan(P1-a)과 리뷰어 일반 테이블 질의(P1-b)에서 서버 사용자 명령어 수 차이는 −2.0%~+1.2%이다. 5%를 넘는 변화는 없고, `bench.py compare --max-overhead-percent 2`는 세 라운드 모두 `within_budget`이다.
- 행 하나 UPDATE+COMMIT 3000회(P3-d)에서 `fdatasync`는 develop 3011회, PR head 3006회이다. #8434 단독 측정 때(6006회, 18.83 s → 31.09 s)의 커밋당 추가 동기 flush는 더 이상 없다.
- P3-d 실행 시간 중앙값은 develop 4.66 s, PR head 3.99 s(−14.4%)이다. 공유 장비라서 두 빌드의 사분위 범위가 겹친다. 이 차이는 속도 향상이 아니라 "느려지지 않음"의 근거로만 쓴다.

## 조건

| 항목 | 값 |
| --- | --- |
| `B` (base) | develop `2e67e1d9482714f077b554dec5b17a64d167393f` |
| `F` (final) | PR head `2c38bef05b2a248f232800e4b9d0ff7c8b5fc041` (CI run 44296776118 green) |
| SHA 재확인 | 측정 전(02:31)과 후(03:04)에 `git rev-parse origin/develop`, `gh pr view 7990 --json headRefOid`로 확인했다. 둘 다 바뀌지 않았다. |
| 빌드 | 두 빌드 모두 `release_gcc` preset이다. RelWithDebInfo, `-O2 -ggdb3 -DNDEBUG -finline-functions`, GCC 11.5.0 20240719, `UNIT_TESTS=OFF`. worktree는 `/home/vimkim/gh/cb/perf-7990-base-2e67e1d`, `/home/vimkim/gh/cb/perf-7990-final-2c38bef`(detached)이다. |
| B 빌드 수정 | develop `2e67e1d`는 release_gcc에서 `src/broker/cas_cgw_odbc.c`가 `toupper`/`tolower` 선언 누락으로 컴파일되지 않는다. F의 develop merge(`3e541fc`)에 들어간 `#include <ctype.h>` 두 줄을 B worktree에만 로컬로 적용했다(`base-build-fix.patch`). broker CAS gateway 파일이므로 `cub_server`와 `csql`에는 영향이 없다. |
| 설치 | `~/.cub/install/perf-7990-{base-2e67e1d,final-2c38bef}/release_gcc`. 설치마다 registry(`CUBRID_DATABASES`), TMP, `cubrid_port_id`(B 47101, F 47102)를 따로 두었다. 서버는 한 번에 하나만 띄웠다. |
| P1 설정 | `data_buffer_size=4G`, `max_query_cache_entries=0`, `query_cache_size_in_pages=0`. DB는 `cubrid createdb -F <dir> --db-volume-size=2G --log-volume-size=512M <db> en_US.utf8`(16 KiB page 기본값). P1-a는 `p1a`, P1-b는 `p1b` DB를 썼다. |
| P3-d 설정 | 기존 `oos_small_txn.sh`·`oos_flush_count.sh`의 설정을 그대로 썼다(측정마다 새 DB, `data_buffer_size=512M`, `log_buffer_size=64M`, 임의 포트 36000~37999). |
| 장비 | Intel Xeon Gold 5218R, 80 CPU, NUMA 2, 251 GiB, kernel 5.14.0-570.30.1.el9_6, governor `performance`, boot ID `65134914-8ca7-473a-8891-a5852e59f984`. 여러 사람이 함께 쓰는 서버다. 측정 중 다른 사용자의 debug `cub_server`가 하나 떠 있었다. |
| 부하 | 시작 02:40:12 load 19.69 / 38.89 / 28.43. P1·P3-d 3라운드 끝 02:56:23 load 19.14 / 15.16 / 18.46. P3-d 추가 라운드 끝 03:03:49 load 24.65 / 21.62 / 20.06. |
| 순서 | B, F, B, F, B, F 순으로 교대했다. 한 라운드는 P1-a, P1-b, P3-d flush 계수, P3-d 시간 측정 순이다. 그 뒤 P3-d 시간 측정만 B, F를 6라운드 더 교대했다(`order.log`). |

## P1-a 일반 테이블 scan (`bench.py`)

200,000행, 80바이트 일반 행. `bench.py` 기본값(라운드 2개 × run 5개, run 0 버림, run마다 scan 20회)을 한 번 호출로 하고, B/F를 3번씩 교대 호출했다. 빌드·case마다 유지 표본은 24개다. 명령어 수는 `perf stat -p <cub_server>`의 `instructions:u`이다.

| case | B 명령어 중앙값 | F 명령어 중앙값 | 차이 | 표본 spread (B / F) | 호출 간 spread (B / F) | B 시간 ms | F 시간 ms | 시간 차이 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| narrow | 6,785,273,863 | 6,689,446,788 | −1.41% | 0.01% / 0.02% | 0.00% / 0.00% | 316.0 | 316.1 | +0.03% |
| wide | 12,260,864,928 | 12,017,235,174 | −1.99% | 0.02% / 0.02% | 0.02% / 0.00% | 716.6 | 717.2 | +0.08% |

- spread는 `(최댓값 − 최솟값) / 중앙값`이다. "호출 간"은 호출 3번의 중앙값끼리 비교한 값이다.
- `bench.py compare --max-overhead-percent 2`를 라운드 짝(B-rN, F-rN)마다 돌렸다. 세 번 모두 exit 0, 두 case 모두 `within_budget`이다.
- 시간 표본의 spread는 32~64%다. 값이 약 50 ms 단위로 몰려 있어서, 시간은 CPU 비용의 지표로 쓰지 않는다.

## P1-b 리뷰어 일반 테이블 질의 (`ordinary.py`)

`id INT PRIMARY KEY, a INT, s VARCHAR(100)` 200,000행. 호출 한 번이 질의마다 5회(첫 회 warmup)이고, 라운드마다 새 prefix(`r1_`~`r3_`)로 fixture를 만들었다. UPDATE는 매번 새 복제본에서 시작한다. 빌드·질의마다 유지 표본은 12개다.

| 질의 | B 명령어 중앙값 | F 명령어 중앙값 | 차이 | 표본 spread (B / F) | 호출 간 spread (B / F) | B 시간 ms | F 시간 ms | 시간 차이 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `COUNT(*), SUM(a)` | 65,796,369 | 66,205,236 | +0.62% | 4.94% / 4.51% | 0.06% / 0.04% | 65.3 | 65.4 | +0.14% |
| `SUBSTR(s,30,1)='a'` | 505,827,816 | 505,645,376 | −0.04% | 0.04% / 0.06% | 0.01% / 0.00% | 65.4 | 65.3 | −0.07% |
| `UPDATE ... SET a=a+1; COMMIT` | 6,366,747,065 | 6,444,151,617 | +1.22% | 1.94% / 1.08% | 0.23% / 0.12% | 1744.1 | 1769.2 | +1.43% |

- 저장 상태: F의 scan 복제본은 `SHOW HEAP CAPACITY`에서 Num_recs 200000, relocated 0, overflowed 0이다. `SHOW HEAP OOS`에서 Has_oos_file 0이다. 즉 일반 heap 레코드만 있다. B는 `SHOW HEAP OOS`가 없어서 capacity만 수집했다.
- 차이는 손으로 계산한 `(F − B) / B`이다. `ordinary.py` 결과는 `bench.py compare`가 받지 않는다.

## P3-d 행 단위 UPDATE+COMMIT 지연

한 csql 세션에서 행 하나의 `BIT VARYING` 값(약 6000 B)을 UPDATE하고 COMMIT하기를 3000번 했다(`cbrd-27781/latency-8495/oos_small_txn.sh`). `fdatasync` 횟수는 같은 작업을 `strace -f -c -p <cub_server>`를 붙여 따로 돌려 셌다(`oos_flush_count.sh`). strace를 붙인 동안의 시간은 쓰지 않는다. 모든 측정에서 3000행이 갱신되었다.

| 지표 | B | F | 차이 |
| --- | --- | --- | --- |
| `fdatasync` (3번씩) | 3011, 3011, 3011 | 3006, 3006, 3006 | −5 |
| 실행 시간 중앙값 (9번씩) | 4.656 s | 3.986 s | −14.4% |
| 범위 | 2.41–8.84 s | 2.42–8.08 s | |
| 사분위 범위 | 3.21–5.73 s | 3.62–5.51 s | |
| 라운드 짝 차이 F − B | | | 중앙값 −0.41 s, F가 빠름 6 / 느림 3 |

- 5%를 넘는 변화로 표시한다: 시간 중앙값 −14.4%(F가 빠름). 다만 두 빌드의 사분위 범위가 겹치고 범위가 3배 이상 벌어진다. 공유 장비의 부하가 원인으로 보인다(추정). 이 값을 속도 향상으로 쓰지 않는다.
- 처음 3라운드만으로는 중앙값이 B 2.51 s, F 3.99 s(+59%)였다. 표본 3개로는 부하 변동을 가릴 수 없어서 B/F를 6라운드 더 교대했다. 위 표는 9라운드 전체 값이다.
- #8434 비용: #8434 단독 측정(Work841)에서는 커밋마다 동기 로그 flush가 하나 더 붙었다(`fdatasync` 6006회, 18.83 s → 31.09 s). F의 `fdatasync`는 3006회로 B(3011회)와 같은 수준이다. 그 비용은 더 이상 남아 있지 않다. #8495(CBRD-28046)가 develop을 거쳐 들어온 결과와 일치한다.
- 저장 경로가 다르다. B(develop)에는 OOS가 없어서 6000 B 값이 heap 레코드에 들어가고, F에서는 OOS로 간다(같은 SQL, 다른 저장 경로). 그래서 이 행은 같은 저장 정책끼리의 비교가 아니라 사용자가 보는 커밋 지연의 관측값이다.

## 건너뛴 시나리오

P1-c(연속 UPDATE·vacuum 비용), P3-a(OOS SELECT Q1~Q5), P3-b(리뷰어 큰 값 `w` 표), P3-c(INSERT·UPDATE churn 로그·페이지), P2(threshold 4~16KB)는 돌리지 않았다. 이유: 사용자 요청에 따른 가벼운 확인이다(light check per user). P2는 원래 후속으로 미룬 항목이며, 통과로 표시하지 않는다.

## 한계

- 공유 장비이고 load는 15~39였다. 명령어 수는 부하에 거의 흔들리지 않았지만(호출 간 spread 0.23% 이하), 시간은 크게 흔들렸다.
- 반복 수가 인계 문서의 기준보다 적다. P1-a는 B→F 교대 호출 3번이고 F→B 역순 호출은 따로 하지 않았다. P1-b는 4라운드 ABBA가 아니라 3라운드 교대다. 사용자가 1~2시간의 가벼운 확인을 요청했기 때문이다.
- 인계 문서 5절의 "측정마다 남길 것" 중 `fincore`, CPU affinity 고정, 로드된 DSO 전체의 해시는 따로 남기지 않았다. `bench.py`가 수집하는 서버·client 정체, affinity, locale, 서버 파라미터만 있다.
- B는 broker 파일 한 개를 로컬로 고쳐서 빌드했다(위 조건 표).
- 수락 기준(AC-P1 2%, AC-P3)의 통과·실패는 판정하지 않았다.

## 원시 산출물 경로

Git 밖에 둔다.

- 측정 루트: `/home/vimkim/tk/perf-7990/`
  - `runs/P1a/{B,F}-r{1,2,3}/`, `runs/P1a/compare-r{1,2,3}.txt`
  - `runs/P1b/{B,F}-r{1,2,3}/`
  - `runs/P3d/{B,F}-{1..9}/`, `runs/P3d/results.csv`
  - `runs/P3d-flush/{B,F}-{1,2,3}/strace.out`, `runs/P3d-flush/results.csv`
  - `order.log`(순서와 load), `summary.json`(집계), `build-evidence.txt`(compiler·flag·SHA-256·장비), `base-build-fix.patch`
  - 실행 스크립트: `env.sh`, `setup-install.sh`, `round.sh`, `drive.sh`, `drive-p3d.sh`, `agg.py`
- 빌드 로그: `/home/vimkim/tk/perf-7990/build-{base,base2,final}.log`
