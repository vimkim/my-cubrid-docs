# Handoff: ADR-0008 decision 7 — INSERT·UPDATE 지연 재측정

2026-11-06, Work742 (2026-11-09 base 갱신). 다른(조용한) 장비에서 사람이 이어서 할 측정이다. 결과로 ADR-0008 decision 7의 마지막 조건, "INSERT와 UPDATE 지연이 나빠지지 않을 것"을 판정한다.

## 지금까지

- 로그 바이트와 OOS 파일 크기는 이미 측정했다: [perf.md](perf.md). 결과는 UPDATE churn 로그 −42%, 버린 값 하나당 회수 로그 약 6.1 → 0.71 KB, churn 뒤 OOS 페이지 3539 → 1502였다.
- 지연은 판단하지 못했다. 측정 서버는 80코어 공용 장비였고 load average가 57–60이었다. 반복이 3회뿐이라 base와 new의 범위가 겹쳤다(INSERT 5.75 s vs 6.39 s 중앙값, UPDATE 회차별로 엇갈림).
- PR #8434가 merge되기 전에 이 조건을 판정해야 한다(ADR-0008 decision 7, 사용자 결정 2026-11-05).

## 비교 대상

| 이름 | 커밋 | 얻는 곳 |
|---|---|---|
| base | `95ff126a8` (`feature/oos-merge`, PR #8434의 base. 2026-11-09 rebase 후) | `https://github.com/CUBRID/cubrid` |
| new | PR #8434의 현재 head. `0034bc2fb` 이후 커밋이어야 한다 | `https://github.com/vimkim/cubrid` 브랜치 `CBRD-27781-postpone-commit` |

new의 커밋은 측정 시점에 `git ls-remote https://github.com/vimkim/cubrid CBRD-27781-postpone-commit`로 확인하고 결과에 적는다. PR 리뷰로 head가 더 움직였으면 최신 head를 잰다.

## 장비 조건

- 측정 동안 다른 CUBRID 서버, 빌드, 테스트가 돌지 않는다. 시작 전과 끝난 뒤 `uptime`의 load average가 1 미만이어야 한다. 아니면 그 표본을 버린다.
- base와 new는 같은 장비, 같은 디스크에서 잰다. 장비 사양(CPU, 코어 수, 메모리, 디스크 종류)과 커널을 적는다.
- 가능하면 CPU frequency governor를 `performance`로 고정한다. 바꿀 권한이 없으면 현재 값을 적는다.

## 빌드 (release)

두 커밋을 각각 따로 checkout하고 따로 설치한다. CUBRID 저장소의 `CMakePresets.json`에는 `release`(RelWithDebInfo) preset이 있고, 설치 위치는 `$CUBRID`다.

```bash
# base
git clone https://github.com/CUBRID/cubrid cubrid-base && cd cubrid-base && git checkout 95ff126a8
export CUBRID=$HOME/cub-install/base
cmake --preset release && cmake --build build_preset_release && cmake --install build_preset_release
cd ..

# new
git clone https://github.com/vimkim/cubrid cubrid-new && cd cubrid-new && git checkout CBRD-27781-postpone-commit
git log -1 --format=%H   # 결과에 적는다
export CUBRID=$HOME/cub-install/new
cmake --preset release && cmake --build build_preset_release && cmake --install build_preset_release
```

이 장비에 사용자의 `just` worktree 도구가 있으면 `release_gcc` preset으로 같은 일을 해도 된다. 지난 측정도 `release_gcc`였다. 두 쪽은 같은 preset과 같은 컴파일러로 빌드한다.

## 실행

스크립트는 이 디렉터리의 [bench/oos_update_churn.sh](bench/oos_update_churn.sh)와 [bench/run_all.sh](bench/run_all.sh)다. 표본마다 새 DB(1G 볼륨, 512M 로그, data_buffer 512M)를 만들고 별도 포트로 server mode를 띄운다. base와 new를 번갈아 돈다.

```bash
cd my-cubrid-docs/cbrd-27781/bench
BASE=$HOME/cub-install/base NEW=$HOME/cub-install/new \
OUT=$HOME/oos-latency-$(date +%Y%m%d) REPEATS=10 \
  bash run_all.sh
```

- 기본 부하는 3000행이다. 값은 6000바이트이고, 서로 다른 MD5를 이어 붙여 로그 압축이 거의 듣지 않는다. 순서는 INSERT → UPDATE 3회(회마다 commit) → vacuum drain → DELETE → drain → 재삽입이다. `ROWS`, `ROUNDS`, `BYTES` 환경 변수로 바꿀 수 있다.
- **반복은 10회 이상**으로 한다. 지난번 3회는 판정에 부족했다.
- 지난 측정에서 표본 하나는 1–2분이었다. 10회 × 2쪽이면 대략 30분–1시간을 잡는다.
- 각 표본의 로그는 `$OUT/<label>-<rep>.log`, 수치는 `$OUT/results.csv`(`label,rep,metric,value`)에 쌓인다.

### 지연 지표

| metric | 뜻 |
|---|---|
| `insert_sec` | 3000행 INSERT + COMMIT, `csql -C` 클라이언트 벽시계 |
| `update1_sec`, `update2_sec`, `update3_sec` | 3000행 UPDATE + COMMIT 각 회차. new에서는 commit의 postpone(행마다 drop postpone 실행과 알림 기록)이 여기에 들어간다 |
| `delete_sec` | DELETE + COMMIT |

알려진 한계가 있다. INSERT와 UPDATE 시간에는 값을 만드는 MD5 `GROUP_CONCAT` 계산이 들어 있다. 두 쪽에 똑같이 들어가는 비용이지만 잡음이 커진다. 차이가 애매하면 다음 보조 측정을 권한다.

- **보조 A (값 계산 제외)**: 값을 미리 별도 테이블에 만들어 두고, `INSERT INTO t SELECT id, v FROM staging`과 `UPDATE t SET v = (SELECT v FROM staging_r WHERE staging_r.id = t.id)`로 잰다. 스크립트를 고치면 그 변경도 결과와 함께 남긴다.
- **보조 B (작은 트랜잭션)**: 행 하나를 UPDATE하고 commit하는 트랜잭션을 한 세션에서 3000번 돌린다. new는 commit마다 run-postpone sysop과 알림 기록이 붙으므로, 행당 오버헤드는 여기서 가장 잘 보인다. 한 csql 세션에서 SQL 파일로 돌려 접속 비용을 뺀다.

## 판정

1. 지표마다 base와 new의 중앙값, 최솟값–최댓값, 사분위 범위를 표로 만든다.
2. 반복 r마다 쌍 차이 `new − base`를 구한다. 번갈아 돌렸으므로 같은 r끼리 짝이다. 그 중앙값과 부호를 본다.
3. 판정 기준은 사람이 정한다. 권하는 기준은 다음과 같다. new 중앙값이 base 중앙값의 +5% 이내이고, 쌍 차이의 중앙값이 base의 사분위 범위 안이면 "나빠지지 않음"으로 본다. 그보다 나쁘면 어느 지표가 얼마나 나빠졌는지 적고, 보조 B로 행당 비용을 확인한다.
4. load average 조건을 어긴 표본은 버리고, 버린 수를 적는다.

## 결과를 남길 곳

- [perf.md](perf.md)에 "재측정 (지연)" 절을 추가한다. 장비 사양, 두 커밋, 반복 수, 표, 판정을 적는다. 원자료 CSV는 `bench/results-<new>-vs-95ff126a8-latency.csv`로 넣는다.
- 판정이 나면 함께 갱신할 곳:
  - ADR-0008 decision 7 문장(`cubrid-oos-context`의 `docs/adr/0008-reclaim-oos-chains-after-the-delete-is-final.md`): 지연이 "판단 못함"으로 남아 있다.
  - PR #8434 본문의 성능 항목. 원본은 [pr-body.md](pr-body.md)이다.
- 결과를 이 세션 쪽에 넘길 때는 `results.csv`, 표본 로그 디렉터리, 장비 사양을 함께 준다.
