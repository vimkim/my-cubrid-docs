# OOS 성장 비용 전후 측정 (ADR-0010 결정 6)

2026-11-06, Asia/Seoul. Work839. [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872), [CBRD-27925](https://jira.cubrid.org/browse/CBRD-27925).

독자는 ADR-0010을 accepted로 바꿀지 정할 사용자와, 후보 집합 구현(Work840)을 리뷰하고 통합할 사람이다.

## 질문과 결론

ADR-0010 결정 6은 채택 조건을 두 가지로 둔다. 하나는 UPDATE·DELETE churn 뒤 큰 OOS 파일에 하는 INSERT의 시간이 나빠지지 않는 것이다. 다른 하나는 churn 뒤 파일 크기가 커지지 않는 것이다. 이 측정은 빈 페이지 후보 집합 구현(after)과 그 직전 엔진(before)을 같은 장비와 같은 부하에서 비교했다.

> **적용 범위 (2026-11-09 갱신).** 계획이 2026-11-09에 바뀌었다. 1단계는 빈 페이지를 집합에 두고 파일 관리자에 반환하는 구현이다(`076c3e4c6`과 보강 `e8e714dae`). 2단계는 C안(재사용 우선)이고 이 측정 뒤에 한다. C안은 빈 페이지를 반환하지 않고 집합에서 꺼내 바로 다시 쓰며, fast path와 반환 sysop을 없앤다. 그래서 이 보고서의 처음 판정(2026-11-06)은 `076c3e4c6`에 대한 것이고, 아래 "2026-11-09 재측정"은 `e8e714dae`에 대한 것이다. 둘 다 1단계를 판정한다. 2단계는 검증하지 않는다. C안 구현이 나오면 같은 harness로 다시 잰다. 그때 파일 크기 판정은 삭제 뒤 페이지 수가 아니라 sector 수와 cycle 사이 peak 증가 여부로 본다. 페이지를 반환하지 않으면 삭제 뒤 페이지 수가 줄지 않기 때문이다. 이 보고서의 before 수치와 harness는 그 측정의 기준선으로 쓴다.

**결론: `076c3e4c6`에서는 두 조건 모두 충족했다.**

1. **삭제 뒤 INSERT가 파일 전체 lap을 하지 않는다.** OOS 페이지 약 2만 개 파일에서 다음 결과가 나왔다.
   - 한 행을 지우고 vacuum이 끝난 뒤 새 페이지가 필요한 INSERT의 중앙값은 before 28.1 ms, after 3.4 ms였다. 데이터 페이지 fetch는 20,120회에서 42회로 줄었다.
   - 페이지를 비우지 않는 삭제 뒤에는 82.6 ms가 3.5 ms가 됐다. fetch는 20,088회에서 42회로, 디스크 읽기는 20,041회에서 1회로 줄었다.
   - 삭제가 없는 INSERT는 2.2~3.2 ms다. after의 삭제 뒤 INSERT는 이 범위 안에 들어왔다.
2. **같은 파일에 동시에 성장하는 INSERT가 lap을 기다리지 않는다.** 8개 세션이 한꺼번에 INSERT할 때 가장 느린 세션의 중앙값은 before 33.8 ms, after 7.0 ms였다. before에서는 한 세션이 파일 전체를 훑고 나머지 7개가 그 lap을 기다렸다.
3. **파일 크기는 같다.** churn 6 cycle을 4회 반복한 뒤 OOS 파일의 sector 수는 두 빌드에서 같았다(churn 테이블 32, 큰 테이블 318과 315). drain 뒤 페이지 수도 cycle마다 1~2 페이지 안에서 일치했다. 전체 측정이 끝난 두 DB의 최종 상태도 행 수, OOS 레코드 수, 페이지 수, sector 수까지 같았다.
4. **재시작 직후 첫 INSERT는 그대로다.** 두 빌드 모두 약 220 ms이고 파일 전체(약 20,100 페이지)를 읽는다. ADR-0010 결정 4가 재시작 뒤 한 바퀴 lap을 유지하므로 예상한 결과다. R3 리뷰 보고값 0.23~0.25초와 같은 크기다.
5. **삭제가 없는 일반 INSERT는 측정 잡음 안에서 같다.** 중앙값은 before 2.26 ms, after 2.48 ms였다. 그러나 서버 실행마다 중앙값이 1.9~4.2 ms로 흔들렸다. round별 중앙값을 짝지은 차이의 중앙값은 +0.07 ms였다. 코드상 after가 이 경로에서 더하는 일은 mutex 한 번과 set erase 한 번이다(아래 "일반 INSERT" 절).

판정은 공용 80코어 서버에서 했고, 측정 동안 load average가 6~67이었다. 아래 수치는 그 조건의 값이다. 결정을 좌우한 차이(10배 이상, fetch 수 500배)는 이 잡음보다 훨씬 크다.

## 비교 대상

| 이름 | 소스 | 빌드 |
| --- | --- | --- |
| before | `CBRD-27781-postpone-commit` `6a8d16da7`(ADR-0008 구현, `pending_deletes` 무장). 측정용 detached worktree `/home/vimkim/gh/cb/CBRD-27872-before` | `release_gcc`(RelWithDebInfo, `-O2 -DNDEBUG`), `/usr/bin/g++` 11.5.0, 설치 `~/.cub/install/CBRD-27872-before/release_gcc` |
| after | `CBRD-27925-emptied-set` `076c3e4c6`(ADR-0010 후보 집합, Work840). 측정용 detached worktree `/home/vimkim/gh/cb/CBRD-27872-after` | 같은 preset과 컴파일러, 설치 `~/.cub/install/CBRD-27872-after/release_gcc` |

두 worktree에는 로컬 수정이 없다. before의 성장 게이트 코드는 `src/storage/oos_file.cpp` 1763-1934 (`oos_reclaim_sweep_step`, `6a8d16da7`)다. after는 그 자리에 집합 단계를 두고, 집합이 비었고 파일이 known이면 페이지를 하나도 고정하지 않는다(`076c3e4c6` `oos_file.cpp` 1838).

장비는 Intel Xeon Gold 5218R 80코어(2 NUMA), 커널 5.14.0-570.30.1.el9_6, governor `performance`, DB는 NVMe 위 XFS(`/mnt/nvme/data-5`)다. 다른 사용자의 작업이 함께 돌았다.

## 방법

harness는 [bench/growth_cost.py](bench/growth_cost.py), 요약은 [bench/summarize.py](bench/summarize.py)다. 원자료는 [bench/results-076c3e4c6-vs-6a8d16da7.csv](bench/results-076c3e4c6-vs-6a8d16da7.csv)다(`label,sha,round,item,iter,metric,value`).

### DB와 부하

빌드마다 DB 하나를 만들어 끝까지 쓴다. server mode이고 설정은 두 빌드가 같다(`data_buffer_size=256M`, `log_buffer_size=64M`, 볼륨 2G, 로그 1G). 버퍼 256MB는 R3 리뷰와 같은 값이다.

| 테이블 | 내용 | OOS 파일 |
| --- | --- | --- |
| `t(id INT PK, v BIT VARYING)` | 10,000바이트 값 20,000행 | 20,001 페이지. 페이지마다 chunk 하나라서 새 10KB 값은 항상 새 페이지가 필요하다 |
| `u` | 7,000바이트 값 40,000행 | 20,001 페이지. 페이지마다 chunk 둘. 하나를 지워도 페이지는 비지 않는다 |
| `p` | 10KB 값 1행 | vacuum 완료 확인용 probe |
| `c` | 7,000바이트 값 2,000행 | churn 측정용, 약 1,000 페이지 |

측정용 INSERT의 값은 SQL 안에서 만든다(`CAST(REPEAT(LPAD(HEX(k),8,'0'),2500) AS BIT VARYING)`). 큰 리터럴을 파싱하는 비용을 빼려는 선택이다. OOS 페이지는 압축하지 않으므로 값의 압축성은 결과에 영향이 없다.

### 시간과 검사량

- **시간.** csql 한 세션 안에서 csql 자체 타이머가 찍는 문장 시간이다(`1 row affected. (0.003426 sec)`). commit 시간은 따로 찍히며 여기에 넣지 않았다. 접속 비용도 빠진다.
- **검사량.** 각 INSERT 바로 뒤의 `SHOW EXEC STATISTICS`가 그 문장의 `data_page_fetches`, `data_page_ioreads`를 준다. lap이 돌면 fetch가 파일 페이지 수만큼 늘어난다. 그래서 이 값이 "lap을 했는가"를 직접 보여 준다.
- **vacuum 완료.** `SHOW HEAP OOS`는 파일의 모든 페이지를 고정하므로 측정 루프 안에서 쓰지 않았다. 대신 삭제 트랜잭션에서 `p`의 값도 갱신한다. 그 뒤 OOS가 없는 filler 테이블에 행을 넣어 로그 block을 닫고, `p`의 OOS 레코드가 1개로 돌아올 때까지 기다린다. 다른 vacuum worker를 위해 0.5초를 더 기다린다.

### 항목

| 항목 | 절차 | 반복 |
| --- | --- | --- |
| 1. 재시작 첫 INSERT (`restart`) | 서버 재시작, `SELECT id FROM t WHERE id=1`로 세션을 데운 뒤 `t`에 INSERT 두 번 | round마다 1회, 빌드당 18회 |
| 2. 페이지를 비우는 삭제 뒤 (`delete_empties`) | `t`의 한 행 DELETE와 commit, vacuum 대기, 새 세션에서 INSERT(after_delete), 이어서 INSERT(no_delete) | 빌드당 40회 |
| 3. 페이지를 비우지 않는 삭제 뒤 (`delete_keeps`) | `u`의 홀수 id 한 행 DELETE, 나머지는 2와 같다. INSERT 값은 10KB라서 반쯤 빈 페이지에 들어가지 않는다 | 빌드당 40회 |
| 4. churn 뒤 파일 크기 (`churn`) | `c`를 새로 만들고 6 cycle을 돈다. cycle마다 전체 UPDATE, drain, 30% DELETE, drain, 재INSERT를 하고 각 단계 뒤 페이지 수를 잰다. 끝나면 서버를 내리고 `cubrid diagdb -d 1`로 OOS 파일별 `sector: total`을 읽는다 | 빌드당 4회 |
| 5. 동시 INSERT (`concurrent`) | `t`의 한 행을 지우고 vacuum을 기다린다. 한 세션이 행 잠금을 3초 쥐고, 8개 세션이 그 잠금 뒤에서 기다리다 풀리면 각자 `t`에 INSERT한다 | 빌드당 16회 × 8 세션 |
| 일반 INSERT (`plain`) | 재시작 lap 뒤 삭제 없이 `t`에 INSERT 30번 | 빌드당 10 round × 30 |

before와 after는 round마다 번갈아 돌았다(B A A B B A ...). 한 번에 서버 하나만 떴다. 명령은 다음과 같다.

```sh
python3 -I -B cbrd-27872/bench/growth_cost.py --out /mnt/nvme/data-5/tmp/w839/ab \
  --build before=$HOME/.cub/install/CBRD-27872-before/release_gcc=6a8d16da7 \
  --build after=$HOME/.cub/install/CBRD-27872-after/release_gcc=076c3e4c6 \
  --create --rounds 8 --iters 5 --conc-iters 2 --churn-reps 4 --churn-cycles 6
# 같은 DB에 이어서
python3 -I -B cbrd-27872/bench/growth_cost.py --out /mnt/nvme/data-5/tmp/w839/ab \
  --build before=... --build after=... --rounds 10 --iters 0 --plain 30
python3 -I -B cbrd-27872/bench/summarize.py <out>/results.csv
```

## 결과

중앙값, p95, 범위다. 시간 단위는 ms다.

### 1. 재시작 직후 첫 INSERT

| 지표 | before | after |
| --- | --- | --- |
| 첫 INSERT ms (n=18) | 224.9 (p95 321.8, 200.1–335.8) | 222.8 (p95 326.7, 193.4–333.3) |
| 첫 INSERT fetch / 디스크 읽기 | 20,161 / 20,092 | 20,161 / 20,092 |
| 둘째 INSERT ms | 2.24 (1.93–77.4) | 3.02 (1.93–47.2) |
| 둘째 INSERT fetch | 32 | 32 |

두 빌드가 같은 일을 한다. 파일 전체를 디스크(대부분 OS page cache)에서 읽는 lap이다. after는 재시작 뒤 파일을 unknown으로 두고 한 번 lap을 돌기 때문이다(ADR-0010 결정 4). 이 비용을 없애려면 별도 설계가 필요하다. CBRD-27872의 첫 번째 경우는 이번 변경으로 해결되지 않았다.

### 2. 페이지를 비우는 삭제와 vacuum 뒤 INSERT

| 지표 (n=40) | before | after |
| --- | --- | --- |
| 삭제 뒤 INSERT ms | **28.1** (p95 32.4, 25.9–42.3) | **3.43** (p95 4.26, 2.21–4.42) |
| 삭제 뒤 INSERT fetch | 20,121 (20,045–20,196) | 42 (42–42) |
| 삭제 뒤 INSERT 디스크 읽기 | 3,926 | 0 |
| 이어진 INSERT ms (삭제 없음) | 2.17 (1.85–5.22) | 3.17 (1.75–3.80) |
| 이어진 INSERT fetch | 32 | 32 |

before의 fetch 20,121은 파일 20,0xx 페이지를 한 바퀴 돈 값이다. vacuum fast path가 비운 페이지를 이미 반환했으므로 lap은 아무것도 회수하지 못한다. after는 fast path가 집합에서 그 페이지를 뺐으므로 성장이 페이지를 하나도 검사하지 않는다. 남은 fetch 42는 삭제 없는 INSERT의 32보다 10 많다. 반환된 페이지를 `file_alloc`이 다시 할당하는 비용으로 보이지만, 확인하지 않은 추정이다.

R3 리뷰는 이 경우를 약 12 ms로 보고했다. 여기서는 before가 28 ms다. 버퍼 256MB에 OOS 파일 두 개(약 650MB)가 있어 lap 페이지의 약 20%를 디스크에서 다시 읽었기 때문이다(디스크 읽기 3,926회).

### 3. 페이지를 비우지 않는 삭제 뒤 INSERT

| 지표 (n=40) | before | after |
| --- | --- | --- |
| 삭제 뒤 INSERT ms | **82.6** (p95 104.0, 77.6–108.2) | **3.53** (p95 6.68, 2.26–7.55) |
| 삭제 뒤 INSERT fetch | 20,088 | 42 (42–44) |
| 삭제 뒤 INSERT 디스크 읽기 | 20,041 | 1 |

인계 문서의 기준은 "after에서 검사 0회"다. after의 fetch 42는 항목 2의 after와 같고, 삭제 없는 INSERT(32)와 10 차이다. lap이라면 2만 회가 된다. 따라서 성장 단계의 검사는 0회로 판단한다. 다만 fetch 카운터는 성장 단계 검사만 따로 세지 않는다. 그래서 "0회"는 fetch 수 차이에서 끌어낸 추론이다. 단위 테스트(`076c3e4c6` `test_oos_growth_sweep.cpp`)는 이를 직접 단언한다고 커밋 메시지가 밝힌다. 이 측정에서는 그 테스트를 실행하지 않았다.

before가 항목 2보다 느린 이유는 `u`의 페이지가 버퍼에 거의 없어서다(lap 페이지의 99.8%를 디스크에서 읽음).

### 4. churn 뒤 파일 크기

`c` 2,000행(약 1,000 페이지), 6 cycle, 빌드당 4회다.

| 지표 | before | after |
| --- | --- | --- |
| 초기 페이지 | 1,001 | 1,001 |
| UPDATE drain 뒤 페이지 (cycle 24개) | 1,001 (모두) | 1,001 (모두) |
| DELETE drain 뒤 페이지, cycle 1–6 | 801, 757–778, 709–729, 702–718, 707–719, 707–720 | 801, 773–776, 724–728, 716–717, 716–718, 719 |
| 재INSERT 뒤 페이지 | 1,001 (모두) | 1,001 (모두) |
| 최종 OOS sector: `c` / `t` / `u` / `p` | 32 / 318 / 315 / 1 | 32 / 318 / 315 / 1 |

두 빌드의 크기는 같다. sector는 64 페이지 단위로 예약되므로, sector 수가 디스크상 파일 크기다. DELETE drain 뒤 페이지 수가 700대에 머무는 것은 30% 삭제가 페이지 두 chunk 중 하나만 지운 경우가 남기 때문이다. 두 빌드가 같다.

`pages_peak_update`(UPDATE commit 직후 snapshot)는 판정에 쓰지 않았다. 별도 csql로 찍는 사이에 vacuum이 이미 회수를 시작하므로 진짜 peak가 아니다. 값은 before 1,672–1,999, after 1,057–2,001이고, 두 빌드 모두 2,001을 넘지 않았다.

전체 측정이 끝난 두 DB도 같았다. `t` 20,488행과 OOS 레코드 20,488개, 페이지 20,489, sector 321이다. `u` 40,058행과 레코드 40,058개, 페이지 20,099, sector 315다. 모든 삭제가 vacuum됐고 모든 INSERT가 성공했다는 확인이기도 하다.

### 5. 동시 INSERT

| 지표 | before | after |
| --- | --- | --- |
| 세션 INSERT ms (16회 × 8 세션) | 33.0 (p95 36.7, 26.1–36.9) | 4.73 (p95 9.16, 2.30–13.1) |
| 회당 가장 느린 세션 ms (n=16) | 33.8 (29.4–36.9) | 7.03 (4.48–13.1) |
| 세션 fetch | 59, 회마다 한 세션만 약 20,150 | 59–61 |

before에서는 회마다 정확히 한 세션이 파일 전체를 fetch했고, 나머지 일곱 세션은 fetch 59회로 끝났지만 같은 시간 동안 기다렸다. 성장 single-flight 대기다(`6a8d16da7` `oos_file.cpp` 1788-1805). after는 lap이 없으므로 기다릴 대상도 없다. after에 남는 4~13 ms는 8개 세션이 같은 파일의 페이지 할당과 로그를 나눠 쓰는 비용으로 보인다. 측정하지는 않았다.

### 일반 INSERT

삭제 없이 새 페이지가 필요한 INSERT는 결정 6의 판정 대상이 아니다. 그래도 회귀 여부는 확인했다.

| 지표 | before | after |
| --- | --- | --- |
| `plain` ms (10 round × 30) | 2.26 (p95 8.01) | 2.48 (p95 7.45) |
| 서버 실행별 중앙값 범위 | 2.02–2.98 | 1.88–4.21 |
| 짝지은 round 중앙값 차이(after − before) | 중앙값 +0.07 ms, 10개 중 7개 양수 | |
| fetch | 32 | 32 |

풀링한 300 대 300 표본에 rank-sum을 쓰면 p=0.009로 after가 느리게 나온다. 하지만 한 서버 실행 안의 표본은 서로 독립이 아니다. 서버 실행마다 중앙값이 약 2.1 ms와 약 3.2 ms 둘 중 하나에 몰리는 현상이 두 빌드에서 모두 보였고, 원인은 확인하지 못했다. 그래서 독립 단위는 서버 실행이다. 이 단위로 본 차이(+0.07 ms)는 실행 간 변동(1.9–4.2 ms)보다 훨씬 작다.

코드도 같은 결론을 가리킨다. after가 이 경로에서 더하는 일은 빈 페이지에 넣을 때 `oos_reclaim_drop_emptied`(`076c3e4c6` `oos_file.cpp` 1443-1454)가 bestspace mutex 아래에서 하는 map 조회와 set erase 한 번이다. 대신 before가 하던 `pending_deletes` 확인은 사라졌다. 이 비용은 µs 미만으로 추정하며, 측정한 값은 아니다. 두 빌드 모두 30번에 한 번꼴로 약 80 ms짜리 INSERT가 있었고, 원인은 조사하지 않았다.

**판정: 측정 가능한 악화 없음.** 같다고 증명한 것은 아니다. 조용한 장비에서 서버 실행 수를 늘리면 0.1 ms 수준까지 가를 수 있다.

## 한계

- 공용 서버에서 load average 6~67 아래 측정했다. 판정을 가른 차이는 크지만, 1 ms 이하의 차이는 이 장비에서 가릴 수 없다.
- 단일 OOS 크기(10KB, 7KB)와 파일 크기 약 2만 페이지만 쟀다. 다중 chunk 값, 더 큰 파일, 오래 열린 쓰기 트랜잭션이 있는 경우는 재지 않았다.
- 항목 4는 단일 세션 churn이다. 동시 쓰기와 rollback이 섞인 churn, 집합 상한(4096) 초과는 측정하지 않았다. 이 경우들의 크기 상한은 Work821의 TLA+ 모델과 Work840의 단위 테스트가 다룬다.
- 재시작 직후 첫 INSERT의 lap은 두 빌드가 같다. CBRD-27872의 재시작 경우는 이번 변경 범위 밖으로 남는다.
- after의 fetch 42 중 삭제 없는 INSERT보다 많은 10회의 출처는 추정이다.

## ADR-0010 결정 6 판정

| 조건 | 판정 | 근거 |
| --- | --- | --- |
| UPDATE·DELETE churn 뒤 큰 OOS 파일의 INSERT 시간이 나빠지지 않는다 | 충족 | 삭제 뒤 INSERT 28.1 → 3.4 ms, 비우지 않는 삭제 뒤 82.6 → 3.5 ms, 동시 8 세션 최대 33.8 → 7.0 ms. 일반 INSERT와 재시작 첫 INSERT는 측정 잡음 안에서 같다 |
| churn 뒤 파일 크기가 커지지 않는다 | 충족 | sector 수 동일(32/318/315/1), drain 뒤 페이지 수 cycle별 일치, 최종 DB 상태 동일 |

ADR-0010의 accepted 전환, 후보 집합 commit의 Work742 통합, JIRA 게시는 이 보고서가 하지 않았다. 사용자 결정이다.

## 2026-11-09 재측정: 성장 lock을 넣은 `e8e714dae`

Work839 후속. 1단계 구현을 판정한다.

### 왜 다시 쟀나

`076c3e4c6` 위에 `e8e714dae`가 두 가지를 더했다. 하나는 파일별 growth lock이다. reclaim 단계부터 `file_alloc`이 끝날 때까지 쥔다. 그래서 한 파일의 새 페이지 할당은 한 번에 하나씩 일어난다. 다른 하나는 lap이 끝난 뒤 빈 페이지 집합을 다시 보는 것이다. 동시 INSERT 항목이 가장 바뀔 수 있어서 같은 harness로 세 빌드를 다시 쟀다.

### 빌드와 실행

| 이름 | 소스 | 설치 |
| --- | --- | --- |
| before | `6a8d16da7` | `~/.cub/install/CBRD-27872-before/release_gcc` (11-06과 같은 빌드) |
| after | `076c3e4c6` | `~/.cub/install/CBRD-27872-after/release_gcc` (11-06과 같은 빌드) |
| after2 | `e8e714dae`, detached worktree `/home/vimkim/gh/cb/CBRD-27872-after2` | `~/.cub/install/CBRD-27872-after2/release_gcc` |

after2는 같은 `release_gcc` preset과 `g++` 11.5.0으로 빌드했다. 처음 빌드는 github 3rdparty 다운로드가 HTTP 504로 실패했다. 3rdparty는 `076c3e4c6`과 `e8e714dae` 사이에 바뀌지 않았다(측정함: `git diff --stat`가 비어 있음). 그래서 after 빌드 디렉터리의 같은 tarball을 복사해 빌드했다.

세 빌드를 round마다 번갈아 돌렸고(A B C, C B A), 서버는 한 번에 하나만 띄웠다. 출력은 `/mnt/nvme/data-5/tmp/w839/abc`다. 원자료는 [bench/results-e8e714dae-076c3e4c6-6a8d16da7.csv](bench/results-e8e714dae-076c3e4c6-6a8d16da7.csv)다.

실행 순서와 중단은 다음과 같다.
1. DB 생성 뒤 첫 실행은 `--rounds 8 --iters 5 --conc-iters 2 --churn-reps 4`로 시작했다. round 3의 after에서 `cub_master`가 포트 35110을 bind하지 못해(`Address already in use`) 멈췄다. 공용 서버의 다른 프로세스가 포트를 쓴 것으로 보이며, 원인은 확인하지 않았다. 이때 round 0-2는 세 빌드 모두 끝났고, after2는 round 3도 끝났다.
2. 이어서 plain 통과(`--rounds 10 --iters 0 --plain 30`)를 돌렸다. 정상 종료했다.
3. 같은 DB에 `--rounds 5 --iters 5 --conc-iters 2 --churn-reps 4 --churn-cycles 6`을 이어서 돌렸다. 정상 종료했다.

결과적으로 삭제 항목 반복 수는 before 40, after 40, after2 45다. 동시 INSERT는 before와 after가 16회, after2가 18회다(회마다 8 세션). 11-06 실행(40, 16)과 같은 규모다. 세 빌드를 번갈아 돌렸는데도 전체 시간은 약 42분이었다. 2.5시간 한도 안이라 round를 줄이지 않았다. 다만 포트 충돌로 round가 끊겨서 빌드별 round 수가 같지 않다.

load average(1분)는 `/proc/loadavg`를 30초마다 기록한 84개 값에서 최소 67.8, 중앙값 86.6, 최대 132.0이었다. 11-06 실행(6~67)보다 부하가 높다. 그래서 before의 절대값이 11-06보다 크게 나왔다(예: 동시 INSERT 33.8에서 68.6 ms). 세 빌드는 같은 시간대에 번갈아 돌았으므로 빌드 사이 비교는 유효하다. 절대값 비교는 유효하지 않다.

### 결과 (측정함)

중앙값, 괄호는 p95다. 시간은 ms다. 세 빌드는 `before / after(076c3e4c6) / after2(e8e714dae)` 순서다.

#### 5. 동시 INSERT (먼저 본다)

8 세션이 같은 파일에 INSERT한다.

| 지표 | before | after | after2 |
| --- | --- | --- | --- |
| 회당 가장 느린 세션 (n=16/16/18) | 68.6 (152.7) | 6.3 (24.5) | **5.9** (9.9) |
| 회당 가장 빠른 세션 | 66.5 | 3.7 | 3.5 |
| 세션 INSERT 중앙값 (n=128/128/144) | 67.6 (195.9) | 5.75 (21.8) | 5.55 (9.8) |
| 세션 fetch | 59, 회마다 한 세션 약 2만 | 59-61 | 59-61 |

after2는 after보다 느려지지 않았다. 가장 느린 세션의 중앙값은 6.3에서 5.9로, p95는 24.5에서 9.9로 내려갔다. after의 p95가 컸던 것은 한두 번의 느린 round 탓으로 보인다. 그 원인은 조사하지 않았다. 샘플 16-18개로는 5.9와 6.3의 차이를 구분할 수 없다. 측정한 결론은 "나빠지지 않았다"까지다.

before는 11-06처럼 회마다 한 세션이 파일 전체를 fetch했고 나머지는 그 lap을 기다렸다. 부하가 높아서 68.6 ms까지 올랐다.

**growth lock이 무엇을 제한하나 (추정).** lock은 `file_alloc`까지 한 파일의 새 페이지 할당을 직렬화한다. 이 직렬화의 크기는 측정한 값으로 상한을 잡을 수 있다. 8 세션이 모두 같은 구간을 순서대로 지나간다면, 가장 빠른 세션과 가장 느린 세션의 차이는 (8-1) × 구간 길이다. after2는 이 차이의 중앙값이 5.9 - 3.5 = 2.4 ms다. 그러면 직렬 구간은 한 번에 약 0.35 ms 이하다. after도 같은 계산에서 (6.3 - 3.7) / 7 = 0.37 ms다. 전체 INSERT를 직렬화했다면 한 문장이 3.7 ms(아래 일반 INSERT)이므로 가장 느린 세션이 약 26 ms가 됐을 것이다. 실제는 5.9 ms다. 따라서 lock 구간은 문장 시간 3.7 ms 중 작은 일부다. 이 숫자는 시간 차이에서 뺀 추정이다. lock 대기 시간을 직접 잰 것이 아니다. 대기 시간을 직접 보려면 lock 앞뒤에 계측이 필요하고, 이번에는 넣지 않았다.

#### 2. 페이지를 비우는 삭제와 vacuum 뒤 INSERT

| 지표 (n=40/40/45) | before | after | after2 |
| --- | --- | --- | --- |
| 삭제 뒤 INSERT ms | 51.0 (75.9) | 3.36 (5.30) | 4.55 (5.86) |
| 이어진 INSERT ms (삭제 없음) | 3.65 (5.88) | 2.80 (5.07) | 4.01 (6.37) |
| 삭제 뒤 INSERT fetch | 20,440 | 42 | 42 |
| 삭제 뒤 INSERT 디스크 읽기 | 4,250 | 0 | 0 |
| 이어진 INSERT fetch | 32 | 32 | 32 |

after2의 삭제 뒤 INSERT가 after보다 1.2 ms 느리게 보인다. 같은 서버 실행에서 바로 이어 잰 "삭제 없는 INSERT"도 같은 폭으로 올랐다(2.80에서 4.01). 삭제 뒤 값에서 이어진 값을 뺀 차이는 after 0.56 ms, after2 0.54 ms로 같다. 그래서 이 차이는 서버 실행 사이 변동으로 본다(추정). fetch 42는 둘이 같으므로 lap은 일어나지 않았다(측정함).

#### 3. 페이지를 비우지 않는 삭제 뒤 INSERT

| 지표 (n=40/40/45) | before | after | after2 |
| --- | --- | --- | --- |
| 삭제 뒤 INSERT ms | 147.2 (253.9) | 3.77 (11.5) | 4.33 (9.4) |
| 이어진 INSERT ms | 4.10 (6.50) | 3.05 (11.5) | 3.38 (5.5) |
| 삭제 뒤 INSERT fetch | 20,098 | 42 | 42 |
| 삭제 뒤 INSERT 디스크 읽기 | 20,052 | 1 | 1 |

before가 11-06의 82.6 ms보다 느린 것은 부하 때문이다. 이 항목은 `u`의 페이지가 거의 모두 디스크에서 읽힌다(디스크 읽기 20,052회). 두 after는 fetch 42로 lap이 없다. after2는 after와 같다.

#### 4. churn 뒤 파일 크기

6 cycle × 4회, 빌드당 24 cycle이다.

| 지표 | before | after | after2 |
| --- | --- | --- | --- |
| UPDATE drain 뒤 페이지 | 1,001 (모두) | 1,001 (모두) | 1,001 (모두) |
| DELETE drain 뒤 페이지 중앙값 (범위) | 720 (702-801) | 717 (702-801) | 720 (716-801) |
| 재INSERT 뒤 페이지 | 1,001 (모두) | 1,001 (모두) | 1,001 (모두) |
| 최종 OOS sector `c` / `t` / `u` / `p` | 32 / 321 / 315 / 1 | 32 / 321 / 315 / 1 | 32 / 321 / 315 / 1 |

세 빌드가 같다. `t`의 sector가 11-06의 318 대신 321인 것은 이번 DB에 INSERT가 더 쌓였기 때문이다. 세 빌드에서 같다.

#### 1. 재시작 직후 첫 INSERT

| 지표 | before | after | after2 |
| --- | --- | --- | --- |
| 첫 INSERT ms (n=18/18/19) | 347.4 (502.0) | 361.2 (469.7) | 349.6 (456.9) |
| 첫 INSERT fetch | 20,326 | 20,326 | 20,331 |
| 둘째 INSERT ms | 3.66 (6.79) | 3.48 (4.78) | 3.89 (36.3) |
| 둘째 INSERT fetch | 32 | 32 | 32 |

세 빌드가 같다. 결정 4가 재시작 뒤 한 바퀴 lap을 유지하기 때문이다. 부하가 높아서 11-06의 약 220 ms보다 크다. `e8e714dae`의 "lap 뒤 집합 재확인"은 이 항목에서 눈에 띄는 비용을 더하지 않았다. 둘째 INSERT의 after2 p95 36.3 ms는 한 번의 이상치(최대 41.0)가 만들었다. 중앙값은 같다.

#### 일반 INSERT

| 지표 | before | after | after2 |
| --- | --- | --- | --- |
| `plain` ms (10 실행 × 30) | 3.87 (9.76) | 3.74 (10.0) | 3.68 (7.32) |
| 서버 실행별 중앙값 범위 | 3.09-4.41 | 2.62-5.24 | 2.90-4.97 |
| fetch | 32 | 32 | 32 |

세 빌드가 잡음 안에서 같다. growth lock은 새 페이지가 필요한 모든 INSERT가 한 번 쥐는 lock이다. 이 경로의 비용이 보이지 않는 것은 단일 세션이라 대기가 없기 때문이다.

### ADR-0010 결정 7 판정 (`e8e714dae`)

위 처음 보고서는 같은 두 조건을 "결정 6"이라고 불렀다. 요청서의 번호는 7이다. 조건 내용은 같다.

| 조건 | 판정 | 근거 |
| --- | --- | --- |
| UPDATE·DELETE churn 뒤 큰 OOS 파일의 INSERT 시간이 나빠지지 않는다 | 충족 | 삭제 뒤 INSERT 51.0 → 4.55 ms, 비우지 않는 삭제 뒤 147.2 → 4.33 ms, 동시 8 세션 최대 68.6 → 5.9 ms. `076c3e4c6`과 비교해 나빠진 항목이 없다. 일반 INSERT와 재시작 첫 INSERT는 잡음 안에서 같다 |
| churn 뒤 파일 크기가 커지지 않는다 | 충족 | sector 수 동일(32/321/315/1), drain 뒤 페이지 수 범위 일치 |

### 한계

- 부하가 11-06보다 높았다(load 68-132). 1 ms 이하의 차이는 가릴 수 없다. after와 after2의 0.5 ms 안팎 차이는 해석하지 않았다.
- 동시 INSERT는 빌드당 16-18회다. 8 세션 한 종류의 부하만 쟀다. 세션 수를 늘렸을 때 lock이 병목이 되는지는 재지 않았다.
- lock 구간 길이(약 0.35 ms 이하)는 시간 차이에서 뺀 추정이다. 직접 계측하지 않았다.
- 포트 충돌로 첫 실행이 round 3에서 끊겼다. 이어 돌렸으므로 round 번호가 CSV에서 연속이 아니고 빌드별 round 수가 다르다(before 8, after 8, after2 9, 삭제 항목 기준).
- 최종 DB 상태(행 수, OOS 레코드 수) 비교와 단위 테스트 실행은 이번에 하지 않았다.
- 이 측정은 1단계를 판정한다. C안(2단계)은 구현 뒤 다시 잰다.
