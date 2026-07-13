# CBRD-27014 OOS SELECT 성능 시험 상세 보고서

> 대상 발표 자료: [`ppt-oos-simplified.html`](ppt-oos-simplified.html)의 3~5번 슬라이드<br>
> 측정일: 2026-07-10 (KST)<br>
> 목적: 발표에 사용한 수치가 **어떤 데이터와 SQL로**, **어떤 절차를 거쳐** 나왔는지 쉽게 설명하고, 원본 증거 확인과 재현이 가능하도록 한다.

## 1. 먼저 읽는 결론

이번 시험에서 확인한 결론은 “OOS를 켜면 모든 SELECT가 빨라진다”가 아니다. 정확한 결론은 다음과 같다.

1. **큰 컬럼을 읽지 않는 조회(Q1~Q3)**에서는 OOS가 heap record를 약 4KB로 줄여 page I/O를 크게 줄였다.
   - 기존 레코드가 14.5KB ordinary heap인 경우, full scan wall time이 **31~53% 감소**했다.
   - 기존 레코드가 22KB `REC_BIGONE`인 경우, full scan wall time이 **60~82% 감소**했다.
2. **OOS로 분리된 큰 컬럼을 실제로 읽는 조회(Q4~Q5)**에서는 결과가 달라졌다.
   - 14.5KB ordinary heap에서 큰 컬럼 하나를 읽으면 OOS가 추가 page read를 해야 하므로 **8~14% 느려졌다**.
   - 22KB `REC_BIGONE`에서 큰 컬럼 하나만 읽으면 전체 overflow chain 대신 필요한 값만 읽어 **24~27% 빨랐다**.
   - 모든 logical column을 읽으면 양쪽 모두 결국 큰 데이터를 읽어야 하므로 **거의 동률**이었다.
3. 따라서 OOS의 효과는 다음 두 질문으로 판단해야 한다.
   - workload가 큰 컬럼을 읽지 않는 비율은 얼마나 높은가?
   - OOS 도입 전 레코드는 ordinary heap인가, whole-record overflow인가?

이 보고서에서 “best case”는 주로 **작은 컬럼만 읽고 기존 레코드가 overflow인 경우**, “worst case”는 주로 **ordinary heap에 있던 큰 컬럼을 OOS에서 다시 읽는 경우**를 뜻한다. 일반적인 모든 workload의 절대 최선·최악을 뜻하지 않는다.

## 2. 시험이 답하려는 질문

OOS는 큰 variable column을 별도의 OOS file에 두고 heap record에는 16B OOS OID를 남긴다. 작은 컬럼만 읽을 때는 compact heap만 읽고, 큰 값이 필요한 때에만 OOS page를 읽는다.

따라서 성능 시험은 서로 반대되는 두 질문으로 나눴다.

| 구분 | 질문 | 대상 query |
|---|---|---|
| 이득 측정 | 큰 컬럼을 읽지 않으면 heap/overflow page 접근이 얼마나 줄어드는가? | Q1, Q2, Q3 |
| 비용 경계 측정 | 분리된 큰 컬럼을 읽기 시작하면 추가 OOS read 비용이 얼마나 생기는가? | Q4, Q5 |

단순히 작은 테이블 하나를 반복 조회하면 buffer cache 효과만 측정할 수 있다. 그래서 100,000행과 512MiB data buffer를 사용하고, OOS 도입 전 저장 형태가 다른 두 layout을 만들었다.

## 3. 비교 대상과 시험 환경

### 3.1 비교한 코드

| 역할 | branch / commit |
|---|---|
| 기준 구현 | `develop` / `e3b1bf014ac37fcf3b72b9816a245ff23d9a5e1f` |
| OOS 구현 | `CBRD-27006-oos-recdes-locality` / `3173d3bd5a9c615a17fb9425c2e1c2fee1095474` |

두 branch는 GCC `RelWithDebInfo` release 설치본을 사용했다. debug와 release를 섞지 않았으며, runner는 source/build 관련 tracked 변경이 남아 있으면 시작을 거부한다.

runner의 사전 검사 원문은 다음과 같다.

```bash
for branch in develop oos; do
  [[ -x "${PREFIX[$branch]}/bin/csql" ]] || exit 1
  [[ -x "${PREFIX[$branch]}/bin/cubrid" ]] || exit 1
  git -C "${WORKTREE[$branch]}" diff --quiet -- src CMakeLists.txt CMakePresets.json || {
    echo "$branch has tracked source/build changes; refusing benchmark" >&2
    exit 1
  }
done
```

근거: [`run_oos_select_v2.sh`](performance-results/run_oos_select_v2.sh#L124-L139)

### 3.2 환경

| 항목 | 실제 값 |
|---|---|
| CUBRID / csql | 11.5.0 |
| CPU | Intel Xeon Gold 5218R, 2 sockets × 20 cores, 80 logical CPUs |
| Memory | 125GiB |
| Filesystem | XFS, `/dev/mapper/rl-home` |
| DB page / log page | 16KiB |
| data buffer | 512MiB, 양쪽 동일 |
| 초기 permanent volume | branch별 8GiB |
| DB | develop=`perf27014d`, OOS=`perf27014o` |
| 측정 행 수 | layout별 100,000행 |
| 반복 | cache state·layout·query별 5회 |
| host 상태 | shared host; 다른 CUBRID server 2개가 계속 실행 중 |

Core(Q1~Q3) 측정 시간은 2026-07-10 20:54~21:11 KST이고 당시 load average는 약 1.8~2.7이었다. 따라서 결과는 격리된 전용 성능 장비의 공식 수치가 아니라, 동일 host에서 조건을 통제한 branch 간 비교 결과다.

환경 원본은 다음 위치에 보존되어 있다.

- Core run: [`performance-results/select-v2/20260710-205439-27006-n100000-r5/environment/`](performance-results/select-v2/20260710-205439-27006-n100000-r5/environment/)
- Payload-read run: [`performance-results/select-worstcase/20260710-215418-27006-n100000-r5/environment/`](performance-results/select-worstcase/20260710-215418-27006-n100000-r5/environment/)

## 4. 시험 데이터를 어떻게 만들었는가

### 4.1 왜 `BIT VARYING`을 사용했는가

`VARCHAR`는 type serialization 과정에서 압축될 수 있어 동일한 글자 수가 동일한 disk size를 보장하지 않는다. 이 시험은 record 크기를 의도적으로 만들기 위해 압축되지 않는 `BIT VARYING`과 반복 byte pattern을 사용했다.

예를 들어 다음 식은 `AA` byte를 5,300번 반복해 정확히 5,300B의 값을 만든다.

```sql
REPEAT (X'AA', 5300)
```

### 4.2 Layout A: develop에서는 ordinary heap, OOS에서는 약 4KB

Layout A의 table과 load SQL 핵심 부분은 다음과 같다.

```sql
CREATE TABLE perf_heap_14500 (
  id          BIGINT NOT NULL,
  lookup_key  INT NOT NULL,
  hot_col     INT NOT NULL,
  inline_1    BIT VARYING,
  inline_2    BIT VARYING,
  inline_3    BIT VARYING,
  cold_1      BIT VARYING,
  cold_2      BIT VARYING
);

CREATE INDEX ix_heap_14500_lookup ON perf_heap_14500 (lookup_key);

INSERT INTO perf_heap_14500
SELECT LEVEL,
       MOD (CAST (LEVEL - 1 AS BIGINT) * 48271, 100000) + 1,
       MOD (LEVEL, 1000),
       REPEAT (X'11', 1300),
       REPEAT (X'22', 1300),
       REPEAT (X'33', 1300),
       REPEAT (X'AA', 5300),
       REPEAT (X'BB', 5200)
  FROM db_root
CONNECT BY LEVEL <= 100000;
```

근거: [`oos-select-performance-workload.sql`](oos-select-performance-workload.sql#L10-L39)

payload 합계는 `1,300 × 3 + 5,300 + 5,200 = 14,400B`다. record header 등 metadata를 더한 실제 평균 record 길이는 develop에서 14,480B였다. OOS branch는 largest-first 정책에 따라 5,300B와 5,200B 컬럼을 분리하고 1,300B 컬럼 세 개는 inline으로 남겼다.

### 4.3 Layout B: develop에서는 whole-record overflow, OOS에서는 약 4KB

```sql
CREATE TABLE perf_overflow_22000 (
  id          BIGINT NOT NULL,
  lookup_key  INT NOT NULL,
  hot_col     INT NOT NULL,
  inline_1    BIT VARYING,
  inline_2    BIT VARYING,
  inline_3    BIT VARYING,
  cold_1      BIT VARYING,
  cold_2      BIT VARYING,
  cold_3      BIT VARYING
);

CREATE INDEX ix_overflow_22000_lookup
    ON perf_overflow_22000 (lookup_key);

INSERT INTO perf_overflow_22000
SELECT LEVEL,
       MOD (CAST (LEVEL - 1 AS BIGINT) * 48271, 100000) + 1,
       MOD (LEVEL, 1000),
       REPEAT (X'11', 1300),
       REPEAT (X'22', 1300),
       REPEAT (X'33', 1300),
       REPEAT (X'AA', 7000),
       REPEAT (X'BB', 6000),
       REPEAT (X'CC', 5000)
  FROM db_root
CONNECT BY LEVEL <= 100000;
```

근거: [`oos-select-performance-workload.sql`](oos-select-performance-workload.sql#L45-L75)

payload 합계는 `1,300 × 3 + 7,000 + 6,000 + 5,000 = 21,900B`다. develop에서는 평균 22,016B가 되어 모든 행이 `REC_BIGONE`으로 저장됐다. OOS branch에서는 7,000B, 6,000B, 5,000B 컬럼 세 개가 분리되어 heap record가 평균 4,016B가 됐다.

### 4.4 `lookup_key`를 일부러 섞은 이유

다음 식은 1~100,000을 중복 없이 섞는다.

```sql
MOD (CAST (LEVEL - 1 AS BIGINT) * 48271, 100000) + 1
```

`48271`과 `100000`은 서로소이므로 모든 key가 한 번씩 나온다. insertion order와 lookup order가 달라져 Q3가 index에서 연속 key를 찾더라도 heap에서는 흩어진 행을 방문한다.

또한 `id`에는 의도적으로 index를 만들지 않았다. Q1/Q2가 covering index만 읽어 heap record 크기 차이를 회피하는 것을 막기 위해서다. Q3는 `lookup_key` index를 사용하지만 결과 컬럼 `hot_col`은 index에 없으므로 반드시 heap lookup을 수행한다.

## 5. 측정 전 저장 구조 검증

시간 측정 전에 같은 SQL로 행 수, key 중복, 합계, 각 payload의 `DISK_SIZE()`를 확인했다. 이후 `SHOW HEAP CAPACITY`, `spacedb`, OOS branch의 `;oos_stats`로 실제 저장 형태를 확인했다.

runner 원문은 다음과 같다.

```bash
csql_cmd "$branch" -t -N -c 'SHOW HEAP CAPACITY OF perf_heap_14500;'
csql_cmd "$branch" -t -N -c 'SHOW HEAP CAPACITY OF perf_overflow_22000;'
cubrid_cmd "$branch" spacedb -C --size-unit=M "${DBNAME[$branch]}"

if [[ "$branch" == oos ]]; then
  printf ';oos_stats perf_heap_14500\n' | csql_cmd "$branch"
  printf ';oos_stats perf_overflow_22000\n' | csql_cmd "$branch"
fi
```

근거: [`run_oos_select_v2.sh`](performance-results/run_oos_select_v2.sh#L308-L336)

검증된 결과는 다음과 같다.

| branch | layout | 실제 평균 heap record | heap pages | overflow records | live OOS records | 해석 |
|---|---|---:|---:|---:|---:|---|
| develop | A | 14,480B | 100,000 | 0 | 0 | ordinary heap, page당 약 1행 |
| OOS | A | 3,996B | 33,334 | 0 | 200,000 | 큰 컬럼 2개 OOS, page당 약 3행 |
| develop | B | 22,016B | `SHOW` 보고 200,083 | 100,000 | 0 | 모든 행이 `REC_BIGONE` |
| OOS | B | 4,016B | 33,334 | 0 | 300,000 | 큰 컬럼 3개 OOS, overflow 제거 |

원시 출력:

- [`develop/prepare/heap-14500-capacity.out`](performance-results/select-v2/20260710-205439-27006-n100000-r5/develop/prepare/heap-14500-capacity.out)
- [`develop/prepare/overflow-22000-capacity.out`](performance-results/select-v2/20260710-205439-27006-n100000-r5/develop/prepare/overflow-22000-capacity.out)
- [`oos/prepare/heap-14500-capacity.out`](performance-results/select-v2/20260710-205439-27006-n100000-r5/oos/prepare/heap-14500-capacity.out)
- [`oos/prepare/overflow-22000-capacity.out`](performance-results/select-v2/20260710-205439-27006-n100000-r5/oos/prepare/overflow-22000-capacity.out)

> **증거 정합성 주의:** 원시 `SHOW HEAP CAPACITY`, 두 run의 `analysis.json`, machine summary, 발표 슬라이드는 모두 Layout B OOS 평균 길이를 **4,016B**로 기록한다. [`oos-select-performance-results.md`](oos-select-performance-results.md)의 한 표에만 4,020B로 적혀 있으며 이는 오기다. 이 보고서와 발표의 4,016B를 사용한다.

또한 당시 `;oos_stats`의 `Logical data size`는 알려진 payload 합계와 일치하지 않았다. 따라서 그 필드는 성능 결론의 근거에서 제외하고, `Live OOS records`와 `Physical pages`만 보조 증거로 사용했다.

## 6. 실제로 측정한 SQL

모든 query에는 다음 hint를 동일하게 사용했다.

```sql
/*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
```

- `RECOMPILE`: 해당 query의 plan을 다시 만든다.
- `PARALLEL(0)`과 `NO_PARALLEL_HEAP_SCAN`: 병렬 실행 차이가 저장 구조 차이로 오인되지 않도록 serial scan을 강제한다.
- Core 결과의 Q1/Q2는 table scan, Q3는 지정한 non-covering index scan + heap lookup이었는지 machine gate로 검사했다.

각 SQL 앞뒤에는 JSON trace를 켜고 결과를 저장했다.

```sql
SET TRACE ON OUTPUT JSON;
-- measured SELECT
SHOW TRACE;
SET TRACE OFF;
```

### 6.1 Q1: 작은 컬럼만 읽는 server-side full scan

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
       SUM (id)
  FROM perf_heap_14500;
```

Layout B에서는 table만 `perf_overflow_22000`으로 바꿨다.

Q1은 100,000개의 `id`를 client로 보내지 않고 server 안에서 합계 하나만 만든다. 따라서 storage scan 비용을 가장 깨끗하게 비교한다. 정답은 `5,000,050,000`이다.

### 6.2 Q2: 작은 컬럼 100,000건을 client로 반환

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
       id
  FROM perf_heap_14500;
```

Q2는 Q1과 같은 narrow scan이지만 100,000개 결과를 `csql`로 serialize하고 전달하는 비용도 포함한다. 그래서 storage engine 개선폭과 end-to-end wall time 개선폭이 다를 수 있다. 양 branch에서 row count와 checksum이 같은지 별도로 검증했다.

### 6.3 Q3: random non-covering range lookup

한 query의 형태는 다음과 같다.

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
       hot_col
  FROM perf_heap_14500
 WHERE lookup_key BETWEEN 1 AND 100;
```

실제 측정은 100-key 범위 1,000개를 한 `csql` session에서 실행했다. 범위가 겹치지 않으므로 전체 100,000행을 정확히 한 번씩 읽지만, 순서는 고정 permutation으로 섞었다.

runner의 범위 생성 원문은 다음과 같다.

```bash
for ((i = 0; i < range_count; i++)); do
  range_index=$(((i * 271) % range_count))
  start=$((range_index * 100 + 1))
  end=$((start + 99))
  printf '%s\n' \
    "SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ hot_col FROM $table WHERE lookup_key BETWEEN $start AND $end;" \
    'SHOW TRACE;' >> "$out"
done
```

근거: [`run_oos_select_v2.sh`](performance-results/run_oos_select_v2.sh#L220-L245)

Q3가 보여 주는 것은 “page당 row가 많아지면 모든 random lookup도 같은 비율로 빨라지는가?”이다. 정답은 아니다. index에서 heap으로 내려간 뒤 행마다 한 번의 scattered heap lookup이 남으면 page fetch 횟수가 줄지 않을 수 있다.

### 6.4 Q4: OOS로 분리된 큰 컬럼 하나를 실제로 읽기

Layout A:

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
       COUNT (*)
  FROM perf_heap_14500
 WHERE cold_1 = CAST (REPEAT (X'AA', 5300) AS BIT VARYING);
```

Layout B:

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
       COUNT (*)
  FROM perf_overflow_22000
 WHERE cold_1 = CAST (REPEAT (X'AA', 7000) AS BIT VARYING);
```

`DISK_SIZE(cold_1)` 같은 size-only 식은 OOS OID에 저장된 full length만으로 답할 가능성이 있다. 그래서 실제 payload byte를 읽었다는 것을 보장하려고 원본 값과 **내용 전체를 비교**했다. 정답은 두 query 모두 100,000이다.

### 6.5 Q5: 모든 logical column을 읽되 큰 결과 전송은 피하기

Layout A의 SQL은 다음과 같다.

```sql
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
       SUM (id + lookup_key + hot_col
            + CASE WHEN inline_1 = CAST (REPEAT (X'11', 1300) AS BIT VARYING)
                         AND inline_2 = CAST (REPEAT (X'22', 1300) AS BIT VARYING)
                         AND inline_3 = CAST (REPEAT (X'33', 1300) AS BIT VARYING)
                         AND cold_1 = CAST (REPEAT (X'AA', 5300) AS BIT VARYING)
                         AND cold_2 = CAST (REPEAT (X'BB', 5200) AS BIT VARYING)
                    THEN 1 ELSE 0 END)
  FROM perf_heap_14500;
```

Layout B는 `cold_1/2/3`을 각각 7,000B, 6,000B, 5,000B 원본과 비교한다. 전체 SQL은 [`oos-select-performance-workload.sql`](oos-select-performance-workload.sql#L145-L167)에 있다.

실제로 `SELECT *`를 하면 측정 1회마다 약 1.4~2.2GB를 client로 보내 client 출력 비용이 결과를 지배한다. Q5는 모든 scalar/payload 값을 실제로 읽고 비교하면서 checksum 하나만 반환한다. 따라서 “모든 logical column을 읽는 server-side storage 비용”을 비교할 수 있다. 정답은 `10,050,150,000`이다.

Q5는 raw `recdes` 전체를 강제로 Expand하는 내부 API 시험이 아니다. SQL attribute layer가 각 logical column을 읽는 실제 SQL workload다.

## 7. 시험 실행 절차

### 7.1 database 생성과 setup

runner는 branch마다 별도 database를 만들고 16KiB page를 명시했다.

```bash
cubrid_cmd "$branch" createdb \
  --db-volume-size="$DB_VOLUME_SIZE" \
  --log-volume-size="$LOG_VOLUME_SIZE" \
  --db-page-size=16K \
  --replace -F "${DATABASES[$branch]}/$db_name" \
  "$db_name" en_US.utf8
```

그 뒤 동일한 generated `setup.sql`을 양쪽 `csql`에 입력했다.

```bash
/usr/bin/time -f 'elapsed_s=%e\nuser_cpu_s=%U\nsys_cpu_s=%S\nmax_rss_kb=%M' \
  -o "$RUN_ROOT/$branch/prepare/time.txt" \
  "${PREFIX[$branch]}/bin/csql" -C -u dba -p '' "${DBNAME[$branch]}" \
  -i "$GENERATED/setup.sql" \
  -o "$RUN_ROOT/$branch/prepare/setup.out"
```

근거: [`run_oos_select_v2.sh`](performance-results/run_oos_select_v2.sh#L286-L336)

### 7.2 한 번의 측정에서 저장한 것

```bash
capture_stats "$branch" "$dir/stat-before.txt"
/usr/bin/time -f 'elapsed_s=%e\nuser_cpu_s=%U\nsys_cpu_s=%S\nmax_rss_kb=%M' \
  -o "$dir/time.txt" \
  "${PREFIX[$branch]}/bin/csql" -C -u dba -p '' "${DBNAME[$branch]}" \
  -t -N -i "$sql_file" -o "$dir/csql.out" \
  2> "$dir/csql.err"
capture_stats "$branch" "$dir/stat-after.txt"
```

근거: [`run_oos_select_v2.sh`](performance-results/run_oos_select_v2.sh#L348-L365)

각 run directory에는 다음이 남는다.

| 파일 | 의미 |
|---|---|
| `time.txt` | `csql` 시작부터 종료까지 wall time, user/sys CPU, max RSS |
| `csql.out` | query 결과와 JSON trace |
| `csql.err` | SQL/client 오류 확인 |
| `stat-before.txt`, `stat-after.txt` | 누적 server counter의 전후 snapshot; 보조 자료 |

발표의 시간 수치는 `time.txt`의 end-to-end wall time 중앙값이다. `csql.out`의 JSON query trace 시간과 page fetch/ioread는 원인 설명 및 acceptance gate에 사용했다. 이전 시험에서 SELECT의 `statdump` delta가 0으로 관찰된 적이 있으므로 `statdump`만으로 I/O 결론을 내리지 않았다.

### 7.3 warm과 restart-only

| 상태 | 실제 절차 | 의미 |
|---|---|---|
| restart-only | 매 반복 직전 해당 DB server stop/start | CUBRID buffer pool은 초기화되지만 OS page cache는 그대로 |
| warm | 동일 query를 1회 미측정 warm-up 후 server restart 없이 5회 측정 | 반복 접근 steady state; 전체 dataset이 memory에 들어갔다는 뜻은 아님 |

restart-only 원문:

```bash
if [[ "$cache_state" == restart-only ]]; then
  restart_branch "$branch"
fi
run_sql_file "$branch" "$case_name" "$cache_state" "$run" "$sql_file"
```

warm 원문:

```bash
if [[ "$cache_state" == warm ]]; then
  warmup_case develop "$case_name" "$sql_file"
  warmup_case oos "$case_name" "$sql_file"
fi
```

근거: [`run_oos_select_v2.sh`](performance-results/run_oos_select_v2.sh#L367-L402)

OS cache를 비우는 권한과 격리 절차가 없었으므로 이 보고서는 restart-only를 **cold**라고 부르지 않는다.

### 7.4 paired run과 실행 순서 교대

각 조건은 develop 5회, OOS 5회를 측정했다. host 상태가 시간에 따라 변하는 편향을 줄이기 위해 홀수 반복은 develop→OOS, 짝수 반복은 OOS→develop 순서로 실행했다.

```bash
if (( run % 2 == 1 )); then
  first=develop
  second=oos
else
  first=oos
  second=develop
fi
```

전체 측정 수는 다음과 같다.

- Core: `2 branches × 2 cache states × 2 layouts × 3 queries × 5 = 120 branch-runs`
- Payload-read: `2 branches × 2 cache states × 2 layouts × 2 queries × 5 = 80 branch-runs`

### 7.5 자동 acceptance gate

runner 종료 시 analyzer가 원본 결과를 읽어 다음을 검사했다.

- setup/측정 오류 파일이 비어 있는가
- Q1 합계, Q2 행 수/checksum, Q3 전체 행 수/checksum이 양 branch에서 같은가
- Q4가 100,000, Q5가 10,050,150,000을 반환하는가
- Q1/Q2/Q4/Q5가 serial table scan인가
- Q3가 지정 index를 이용한 non-covering lookup인가
- restart-only develop에서 query trace physical read가 실제로 발생했는가
- 예상한 heap/overflow/OOS 저장 layout인가

두 suite 모두 **Acceptance: PASS**였다.

## 8. Q1~Q3 결과: 큰 컬럼을 읽지 않는 경우

Delta는 `(OOS / develop - 1) × 100`으로 계산했다. 음수는 OOS가 더 빠르다는 뜻이다. 아래 값은 각 조건 5회의 wall time 중앙값이다.

### 8.1 Restart-only

| baseline layout | query | develop → OOS | wall delta | fetch develop → OOS | ioread develop → OOS |
|---|---|---:|---:|---:|---:|
| 14.5KB heap | Q1 `SUM(id)` | 0.93s → 0.61s | **-34.4%** | 100,005 → 33,339 | 100,001 → 33,335 |
| 14.5KB heap | Q2 all IDs | 1.10s → 0.76s | **-30.9%** | 100,305 → 33,639 | 100,007 → 33,335 |
| 14.5KB heap | Q3 random ranges | 7.61s → 5.63s | **-26.0%** | 103,256 → 103,256 | 100,274 → 37,979 |
| 22KB BIGONE | Q1 `SUM(id)` | 1.69s → 0.57s | **-66.3%** | 300,088 → 33,339 | 200,084 → 33,335 |
| 22KB BIGONE | Q2 all IDs | 1.81s → 0.73s | **-59.7%** | 300,388 → 33,639 | 200,093 → 33,335 |
| 22KB BIGONE | Q3 random ranges | 9.10s → 5.93s | **-34.8%** | 403,256 → 103,256 | 200,903 → 37,979 |

### 8.2 Warm steady state

| baseline layout | query | develop → OOS | wall delta | fetch develop → OOS | ioread develop → OOS |
|---|---|---:|---:|---:|---:|
| 14.5KB heap | Q1 `SUM(id)` | 0.57s → 0.27s | **-52.6%** | 100,001 → 33,335 | 99,992 → 33,326 |
| 14.5KB heap | Q2 all IDs | 0.72s → 0.39s | **-45.8%** | 100,289 → 33,623 | 99,983 → 33,317 |
| 14.5KB heap | Q3 random ranges | 6.30s → 5.91s | **-6.2%** | 103,252 → 103,252 | 101,225 → 101,173 |
| 22KB BIGONE | Q1 `SUM(id)` | 0.91s → 0.16s | **-82.4%** | 300,084 → 33,335 | 167,598 → 931 |
| 22KB BIGONE | Q2 all IDs | 0.91s → 0.35s | **-61.5%** | 300,372 → 33,623 | 167,589 → 925 |
| 22KB BIGONE | Q3 random ranges | 7.59s → 5.38s | **-29.1%** | 403,252 → 103,252 | 168,159 → 2,917 |

전체 5회 범위, trace time, CPU/RSS는 [`oos-select-performance-results.md`](oos-select-performance-results.md#primary-results)와 machine summary [`analysis.md`](performance-results/select-v2/20260710-205439-27006-n100000-r5/analysis.md)에 있다.

### 8.3 왜 Q1/Q2가 빨라졌는가

Layout A에서 develop은 평균 14,480B라 heap page당 약 1행이 들어갔다. OOS는 평균 3,996B라 약 3행이 들어갔다. Q1 fetch가 약 100K에서 33K로 줄어든 것은 이 page density 변화와 일치한다.

Layout B에서 develop은 heap의 overflow pointer뿐 아니라 `REC_BIGONE` chain도 따라가야 했다. Q1/Q2 fetch가 약 300K였다. OOS는 작은 heap record만 읽으면 되므로 약 33K로 줄었다. 그래서 Layout A보다 개선폭이 더 컸다.

Q2는 storage read가 줄어도 양쪽 모두 100,000개의 `id`를 client로 보내야 한다. 그래서 일반적으로 query trace 개선폭보다 end-to-end wall time 개선폭이 작다.

### 8.4 왜 Q3의 이득은 조건부인가

Q3는 index에서 찾은 100,000개 결과마다 heap lookup을 수행한다. Layout A의 query trace fetch는 develop과 OOS가 모두 약 103K로 같았다. compact heap의 page density가 높더라도 흩어진 row를 한 번씩 찾아가면 logical fetch 횟수 자체가 줄지 않을 수 있다.

restart-only에서는 OOS ioread가 100,274→37,979로 줄어 26% 빨랐지만, warm에서는 양쪽 ioread가 약 101K로 비슷해져 이득이 6%까지 축소됐다. 반면 Layout B에서는 OOS가 overflow chain 자체를 제거하므로 Q3도 fetch가 403K→103K로 줄고 warm에서 29% 빨랐다.

## 9. Q4~Q5 결과: 큰 컬럼을 읽는 경우

### 9.1 측정 결과

| baseline layout | query | cache | develop → OOS | wall delta | fetch develop → OOS |
|---|---|---|---:|---:|---:|
| 14.5KB heap | Q4 큰 컬럼 1개 | restart-only | 1.40s → 1.59s | **+13.6%** | 100,005 → 133,339 |
| 14.5KB heap | Q4 큰 컬럼 1개 | warm | 0.91s → 0.98s | **+7.7%** | 100,001 → 133,335 |
| 14.5KB heap | Q5 모든 컬럼 | restart-only | 2.24s → 2.41s | **+7.6%** | 100,005 → 133,339 |
| 14.5KB heap | Q5 모든 컬럼 | warm | 1.76s → 1.75s | **-0.6%, 동률** | 100,001 → 133,335 |
| 22KB BIGONE | Q4 큰 컬럼 1개 | restart-only | 2.28s → 1.67s | **-26.8%** | 300,088 → 133,339 |
| 22KB BIGONE | Q4 큰 컬럼 1개 | warm | 1.59s → 1.21s | **-23.9%** | 300,084 → 133,335 |
| 22KB BIGONE | Q5 모든 컬럼 | restart-only | 3.56s → 3.53s | **-0.8%, 동률** | 300,088 → 233,339 |
| 22KB BIGONE | Q5 모든 컬럼 | warm | 2.95s → 2.77s | **-6.1%** | 300,084 → 233,335 |

전체 trace/ioread 값과 5회 범위는 [`oos-select-worstcase-results.md`](oos-select-worstcase-results.md)와 machine summary [`analysis.md`](performance-results/select-worstcase/20260710-215418-27006-n100000-r5/analysis.md)에 있다.

### 9.2 ordinary heap에서 Q4가 느려진 이유

develop에서는 5,300B `cold_1`이 이미 heap record 안에 있다. heap page를 읽은 뒤 같은 record에서 값을 비교할 수 있다.

OOS에서는 먼저 compact heap을 읽고 OOS OID를 얻은 다음, 별도 OOS page에서 `cold_1`을 resolve해야 한다. fetch가 약 100K에서 133K로 늘었고 wall time도 8~14% 늘었다. 이것이 이번 시험에서 관찰한 OOS의 명확한 비용 경계다.

### 9.3 overflow에서 Q4가 여전히 빨라진 이유

develop의 22KB 행은 `REC_BIGONE`이므로 작은 값 하나를 읽어도 whole-record overflow chain을 가져오는 경로를 거친다. OOS는 compact heap + 필요한 `cold_1`만 읽는다. fetch가 약 300K에서 133K로 줄어 wall time이 24~27% 감소했다.

즉, “OOS column을 읽으면 무조건 손해”도 아니다. 기존 방식이 whole-record overflow라면 필요한 column만 읽는 OOS가 더 적은 page를 읽을 수 있다.

### 9.4 Q5가 거의 동률인 이유

모든 payload를 읽으면 OOS도 분리된 값들을 모두 resolve해야 한다. develop도 큰 heap/overflow record 전체를 읽는다. 결과적으로 양쪽 모두 거의 같은 logical data 양을 처리하며, OOS의 narrow-read 장점이 사라진다.

Layout A OOS에서 Q4와 Q5의 fetch가 같은 것은 Q5가 컬럼을 읽지 않았다는 뜻이 아니다. 여러 OOS record가 같은 page/access path에서 처리될 수 있어 “컬럼 하나당 counter 1 증가”가 보장되지 않는다. Q5의 모든 content comparison과 정답 checksum이 모든 값을 읽고 검증했다는 근거다.

## 10. 공간 비용

두 table의 permanent data 사용량은 다음과 같았다.

| develop | OOS | 차이 |
|---:|---:|---:|
| 4,806MiB | 5,847MiB | +1,041MiB, **+21.7%** |

OOS는 compact heap과 별도 slotted OOS pages를 함께 유지하며 page/slot metadata가 추가된다. 따라서 이 시험은 read locality 개선을 입증하지만, 저장 공간 절감까지 입증하지는 않는다.

초기 두 table load는 develop 110.29초, OOS 104.90초였지만 shared host에서 순차로 한 번씩만 수행했다. paired 반복을 하지 않았으므로 INSERT 성능 결과로 해석하지 않는다.

## 11. 재현 방법

### 11.1 준비 조건

재현자는 다음을 준비해야 한다.

1. 비교할 develop과 OOS source commit을 checkout한다.
2. 양쪽을 동일 compiler·optimization의 release-equivalent 설정으로 build/install한다.
3. runner 상단의 worktree/install 경로가 실제 환경과 맞는지 확인한다.
4. 양쪽 `cubrid.conf`를 보존하고, 최소 8GiB × 2 database volume과 4GiB log volume을 만들 disk 공간을 확보한다.
5. Node.js를 준비한다. runner 종료 후 analyzer가 결과와 acceptance gate를 검사한다.

runner는 실행 중 `data_buffer_size=512M`으로 바꾸고 종료 trap에서 원래 config를 복원한다. 전용 host가 아니라면 동시에 실행 중인 server와 load average를 반드시 기록해야 한다.

### 11.2 Core Q1~Q3 실행

저장소 root에서 다음을 실행한다.

```bash
bash performance-results/run_oos_select_v2.sh 27006 100000 5
```

인수는 순서대로 OOS target, 행 수, 반복 횟수다. 출력은 `performance-results/select-v2/<run-id>/`에 생성된다.

### 11.3 Payload-read Q4~Q5 실행

```bash
SELECT_V2_SUITE=worst \
  bash performance-results/run_oos_select_v2.sh 27006 100000 5
```

출력은 `performance-results/select-worstcase/<run-id>/`에 생성된다.

### 11.4 재현 결과 확인 순서

1. 최상위 `completed.txt`가 생성되었는지 확인한다.
2. `analysis.md`의 `Acceptance: PASS`를 확인한다.
3. `environment/{develop,oos}/git-commit.txt`가 의도한 commit인지 확인한다.
4. `prepare/*capacity.out`에서 Layout A/B가 의도한 ordinary/overflow/OOS 형태인지 확인한다.
5. `generated-sql/sha256.txt`로 실제 실행 SQL을 고정한다.
6. 각 `csql.err`가 비어 있는지 확인한다.
7. 각 `time.txt`와 `csql.out`의 trace를 확인한다.
8. median뿐 아니라 5회 원시 범위와 branch 실행 순서를 함께 검토한다.

다른 commit, host, storage, buffer 크기에서 재현한 값은 이번 숫자와 정확히 같을 필요는 없다. 다만 올바른 비교라면 storage layout, query plan, correctness gate가 먼저 같아야 하며, 그 후 fetch/ioread 변화와 wall time 방향을 해석해야 한다.

## 12. 한계와 발표 후 질문에 대한 안전한 답변

### “이것은 cold benchmark인가?”

아니다. server restart로 CUBRID buffer pool은 비웠지만 OS page cache는 비우지 않았다. 정확한 명칭은 `restart-only`다.

### “왜 warm인데 physical ioread가 많나?”

warm은 1회 warm-up 후 반복했다는 뜻이다. dataset과 index/OOS working set 전체가 512MiB CUBRID buffer에 들어간다는 뜻이 아니며, shared host의 OS cache 상태도 계속 변할 수 있다.

### “OOS read가 0이라는 counter를 측정했나?”

Q1~Q3에는 demoted `cold_*` column을 참조하지 않았다. lazy attribute read 설계와 accepted plan상 payload를 resolve하지 않는다. 다만 이 환경에는 직접적인 per-query `oos_read()` 횟수 counter가 없으므로 “측정된 0”이라고 주장하지 않는다.

### “Q5는 `SELECT *`와 완전히 같은가?”

storage 접근 관점에서 모든 logical value를 읽고 비교하지만, 1.4~2.2GB의 client 전송은 하지 않는다. 따라서 server-side all-column access 비용을 비교하는 query이며, client로 `SELECT *` 결과를 소비하는 end-to-end workload와는 다르다.

### “공간도 줄었나?”

아니다. 이 dataset에서는 permanent data가 21.7% 늘었다. read locality 개선과 storage 절감을 혼동하면 안 된다.

### “INSERT도 빨라졌나?”

이 시험으로는 결론을 낼 수 없다. load는 반복 paired benchmark가 아니므로 추적 정보일 뿐이다.

### “항상 82% 빨라진다고 말할 수 있나?”

말할 수 없다. 82%는 22KB `REC_BIGONE`, warm steady-state, `SUM(id)`라는 의도적으로 유리한 조건의 중앙값이다. ordinary heap의 warm random lookup은 6% 개선에 그쳤고, ordinary heap에서 OOS column 하나를 읽을 때는 8~14% 느려졌다.

## 13. 원본 증거 색인

| 자료 | 용도 |
|---|---|
| [`oos-performance-test-plan.md`](oos-performance-test-plan.md) | 비교 계약, query별 의도, acceptance 조건 |
| [`oos-select-performance-workload.sql`](oos-select-performance-workload.sql) | DDL, load, validation, Q1~Q5 SQL 원본 |
| [`run_oos_select_v2.sh`](performance-results/run_oos_select_v2.sh) | 환경 수집, DB 생성, 반복·교대·warm/restart 실행 원본 |
| [`oos-select-performance-results.md`](oos-select-performance-results.md) | Q1~Q3 서술형 결과와 해석 |
| [`Core analysis.md`](performance-results/select-v2/20260710-205439-27006-n100000-r5/analysis.md) | Q1~Q3 machine-generated summary |
| [`Core analysis.json`](performance-results/select-v2/20260710-205439-27006-n100000-r5/analysis.json) | Q1~Q3 구조화 원시 집계 |
| [`oos-select-worstcase-results.md`](oos-select-worstcase-results.md) | Q4~Q5 서술형 결과와 해석 |
| [`Payload analysis.md`](performance-results/select-worstcase/20260710-215418-27006-n100000-r5/analysis.md) | Q4~Q5 machine-generated summary |
| [`Payload analysis.json`](performance-results/select-worstcase/20260710-215418-27006-n100000-r5/analysis.json) | Q4~Q5 구조화 원시 집계 |

## 14. 발표 슬라이드와의 대응

| 슬라이드 | 보고서 근거 |
|---|---|
| 3. Performance Test Plan | 2~7장: 두 layout, Q1~Q5, 환경, 반복 및 cache 조건 |
| 4. Measured Result | 8장: Q1~Q3 중앙값, fetch/ioread, random lookup 경계, 공간 비용 |
| 5. Payload Read Boundary | 9장: Q4/Q5 SQL, 결과, ordinary heap과 overflow에서 결과가 다른 이유 |

발표에서 한 문장으로 요약하면 다음과 같다.

> OOS는 큰 값을 읽지 않는 workload에서는 compact heap으로 page I/O를 크게 줄이지만, 큰 값을 읽으면 별도 OOS read 비용이 생긴다. 기존 whole-record overflow를 필요한 column read로 바꾸는 경우에는 큰 값을 읽어도 이득이 남을 수 있다.
