# Tab B: PR #7990 성능 머지 기준 1·2와 UPDATE 비용

작성일: 2026-11-11, Asia/Seoul. 읽기 전용 조사. 빌드·벤치마크·코멘트 게시 없음.

- 엔진 기준: `feature/oos-merge` = PR #7990 head = `67220b7e230ff1587ba5940001d72e10477a1fc4`.
  2026-11-11에 `gh pr view`로 확인함. PR #8299는 2026-11-11T10:31:35Z에 병합됐고, 그 merge commit이 이 SHA다.
- develop 비교 기준: 현재 merge-base는 `2dd94e32ab86`이다(`git merge-base 67220b7 origin/develop`). 리뷰어가 쓴 기준은 `4781495f`였다.
  merge-base 이후 `origin/develop`(`2d1513a8a`)에 12 commit이 더 있다.
- 범위: 대화 탭 코멘트 [6434778190](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6434778190)과 [6461744209](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6461744209)의 성능 지적. 기준 3(CBRD-27788 보고)과 trace 요청(6625292994)은 다른 slice 범위라서 여기서는 언급만 한다.
- 근거 표기: **[코드]** 코드 확인, **[측정]** 문서에 남은 측정, **[추론]** 추론.

---

## 항목 1. 원인 지적이 67220b7에서도 맞는가 (읽기 경로)

### 1. 리뷰어 요구

6461744209 "원인으로 보이는 부분": OOS 값 하나를 읽을 때 페이지 고정 3번과 복사 2번이 든다. 고정 3번은 `pgbuf_fix_if_not_deallocated`가 볼륨 헤더와 섹터 테이블을 먼저 고정하고, 그 뒤에 OOS 페이지를 고정하기 때문이다. 복사 2번은 임시 버퍼에 한 번, 결과 값에 한 번이다. develop은 heap 페이지를 한 번 고정하고 값을 그 자리에서 읽는다.

### 2. 67220b7 기준 현재 상태

**지적은 지금도 그대로 맞다. #8299는 이 경로를 바꾸지 않았다.** [코드]

| 단계 | 위치 (67220b7) | 내용 |
|---|---|---|
| 단일 값 읽기 진입 | `src/storage/heap_file.c:12079-12081` → `heap_attrvalue_read_oos` `:11967` | OOS 표시가 있는 가변 컬럼은 이 함수로 간다 |
| 고정 ① 볼륨 헤더 | `oos_file.cpp:2793` `oos_fix_page_if_oos` → `:2555` `pgbuf_fix_if_not_deallocated` → `page_buffer.c:16172` `disk_is_page_sector_reserved` → `disk_manager.c:4271` `disk_get_volheader` | 값마다 볼륨 헤더 페이지를 READ로 고정한다 |
| 고정 ② 섹터 테이블 | `disk_manager.c:4291` → `:4320` `disk_stab_cursor_fix` | 섹터 테이블 페이지를 READ로 고정한다 |
| 고정 ③ OOS 페이지 | `page_buffer.c:16187` `pgbuf_fix_release (… OLD_PAGE_MAYBE_DEALLOCATED …)` | 실제 OOS 페이지를 고정한다 |
| 복사 ① | `oos_file.cpp:2649` `writer.append` | OOS 페이지에서 16KB 스택 scratch(`heap_file.c:11973`)로, 또는 그보다 크면 `recdes_allocate_data_area`(`:11605`)로 복사한다 |
| 복사 ② | `heap_file.c:11984` → `:11758` `data_readval (…, copy_raw=true, …)` | scratch에서 DB_VALUE로 다시 할당하고 복사한다. 주석 `:11985` "TODO: revisit when dbvalue supports zero-copy" |
| develop 비교 | `origin/develop:src/storage/heap_file.c` `data_readval (…, false, …)` | develop은 PEEK(복사 없음)다 |

추가로 확인한 것:

- 고정 3번이 값 하나당 든다는 점은 함수 주석에도 적혀 있다(`oos_file.cpp:2546-2548`, "that probe costs two extra fixes of cached volume pages per call, on the read path too"). [코드]
- 한 레코드에서 OOS 컬럼을 두 개 이상 읽을 때만 grouped 읽기(`heap_oos.cpp:747-764` → `oos_read_many` `oos_file.cpp:2843`)를 쓴다. 이때 sector 검사는 레코드 안의 서로 다른 head 페이지마다 한 번으로 줄어든다(`oos_file.cpp:2840-2841`). 리뷰어의 `w` 표는 OOS 컬럼이 하나뿐이라 항상 단일 경로를 탄다. grouped 경로도 값마다 `recdes_allocate_data_area`(`heap_oos.cpp:791`)와 복사 2번이 든다. [코드]
- 16KB를 넘는 값의 연속 chunk는 일반 `pgbuf_fix`로 읽는다(`oos_file.cpp:2670`). 연속 chunk에는 sector 검사가 없다. [코드]
- #8299가 바꾼 것은 다음 두 가지다. 이 읽기 비용과는 무관하다. [코드, 문서]
  - OOS가 없는 행의 공통 reader. layout을 한 번만 계산하고, `heap_attrvalue_read_oos`를 noinline으로 떼어 16KB 스택 버퍼를 OOS 경로로만 옮겼다(`heap_file.c:11963-11964`).
  - 4-record 분리 기준.
- **새로 생긴 비용(리뷰 시점에는 없었다).** develop에서 들어온 page batch(CBRD-27361, #8196)는 OOS가 있는 레코드를 만나면 그 chunk를 row 경로로 넘긴다(`src/query/expr_batch.c:4220-4224`, commit `dcf38cb0aa`). [코드]
  따라서 develop에서 batch로 처리되는 6KB heap 행 스캔이 PR에서는 row 경로로 처리될 수 있다. 이 영향은 측정되지 않았다. 리뷰어가 측정한 좁은 컬럼 스캔의 이득(-23%)도 현재 develop 기준으로는 줄거나 반대가 될 수 있다. [추론]

### 3. 판정

**미충족.** 지적한 원인이 67220b7에 그대로 남아 있다.

### 4. 남은 일, 크기와 위험

| 개선 후보 | 크기 | 위험 |
|---|---|---|
| (a) sector 검사 생략. 호출자가 home page latch나 instance lock을 쥐고 있어 head 페이지가 해제될 수 없을 때 일반 fix로 바꾼다. `page_buffer.c:16168-16170` 주석도 "lock이 있으면 생략할 수 있다"고 적고 있다 | 작다(수십 줄) | 크다. CBRD-26950 stale reference 방어와 CBRD-27981 조사(home page latch, instance lock이 실제 보호)의 전제를 다시 증명해야 한다. 그 보호가 없는 reader(예: `db_ha_apply_info` cached scan)는 sector 검사를 유지해야 한다 |
| (b) 복사 1번 제거. DB_VALUE용 버퍼를 먼저 할당하고 `oos_read`가 바로 그 버퍼에 쓴다. TODO `:11985`가 이 작업이다 | 중간 | 중간. 모든 문자열·비트 타입의 `data_readval` 경계(압축 값, 문자셋 헤더)를 확인해야 한다 |
| (c) 두 개를 다 해도 develop과 같아지지 않는다. 6KB 행은 develop에서 페이지 하나에 약 2개가 들어가지만, PR은 값마다 OOS 페이지를 하나 더 고정한다 | - | 기준 2를 코드 최적화만으로 맞추기는 어렵다고 본다. 리뷰어 수치로는 행당 약 3,750 instructions가 늘었다(75.6M ÷ 20,000). [추론] |

### 5. 답글 초안

> 67220b7 기준으로 다시 확인했습니다. 말씀하신 원인이 그대로 남아 있습니다. OOS 값 하나를 읽을 때 `pgbuf_fix_if_not_deallocated`의 sector 검사로 볼륨 헤더와 섹터 테이블을 고정하고, OOS 페이지를 고정합니다(`oos_file.cpp:2555`, `disk_manager.c:4271`, `:4320`). 복사도 scratch에 한 번, DB_VALUE에 한 번 합니다(`oos_file.cpp:2649`, `heap_file.c:11758`). #8299는 OOS가 없는 행의 reader만 줄였고, 이 경로는 바꾸지 않았습니다.
> 추가로, develop에서 들어온 page batch가 OOS 레코드를 row 경로로 넘기는 것도 확인했습니다(`expr_batch.c:4221`). 그래서 OOS 표의 스캔은 현재 develop 기준으로 다시 재야 합니다.
> sector 검사 생략과 복사 1회 제거는 검토하겠습니다. 다만 그것만으로 4~16KB 구간이 develop과 같아지기는 어렵다고 봅니다. 기준 2는 기본 저장 정책 문제로 따로 답드리겠습니다.

---

## 항목 2. UPDATE가 바뀌지 않은 OOS 값을 새로 쓰는가

### 1. 리뷰어 요구

6434778190 2번과 6461744209: 작은 컬럼 UPDATE가 바뀌지 않은 OOS 값까지 OOS에 새로 쓰고, 옛 값은 vacuum이 지운다. 그 결과 instructions가 +73.7% 늘었다. CBRD-27230을 머지 범위에 넣을 수 있는지 의견을 물었다.

### 2. 67220b7 기준 현재 상태

**값을 재사용하지 않는다. 지적이 맞다.** [코드]

1. `update w set a=a+1`은 `heap_attrinfo_transform_to_disk_internal`에서 시작한다(`heap_file.c:14877`).
2. `heap_attrinfo_set_uninitialized`(`:14901`)가 SET 절에 없는 컬럼을 옛 레코드에서 읽는다(`:13636-13641`). OOS 컬럼은 항목 1의 경로로 실제로 읽는다. 고정 3번과 복사 2번이 든다.
3. `heap_attrinfo_determine_disk_layout`(`:13780`)이 값의 크기만 보고 OOS 대상을 다시 고른다(`:13841-13887`). 옛 OOS 참조를 이어받는 분기가 없다.
4. 고른 값은 다시 직렬화하고(`:14963` 또는 `:14180`) `oos_insert_many`로 새 chain에 쓴다(`heap_oos.cpp:889`).
5. 옛 chain은 vacuum이 `RVHF_UPDATE_NOTIFY_VACUUM`에서 지운다(`src/query/vacuum.c:3739-3748`).
6. 67220b7 소스에는 CBRD-27230이나 값 재사용 코드가 없다(`git grep "27230\|reuse.*oos"`).

실행 근거도 있다. CBRD-27981 조사에서 applylogdb의 counter UPDATE가 바뀌지 않은 `copied_log_path`를 새 chain에 쓰는 것을 실행으로 확인했다(`my-cubrid-docs/cbrd-27781/null-snapshot-reader-investigation.md` 결론 (c)). [측정]

비용 측정은 리뷰 시점 코드에만 있다. [측정]

| 출처 | revision | 작은 컬럼 UPDATE(명령어 수, develop 대비) |
|---|---|---|
| 리뷰어 | `4408135c` 대 `4781495f` | +73.7% |
| 작성자 재현, UTF-8 | 같음, 같은 표에 20회 누적 | +176.3% |
| 작성자 재현, ISO-8859-1 | 같음 | +175.8% |

작성자 재현은 `cbrd-27785/CBRD-27785-reviewer-reproduction_4408135c_20261031_codex.md`에 있다. 누적 조건이 원문과 달라 수치가 다르다.

#8299 이후, 그리고 67220b7에서 OOS 행 UPDATE를 잰 기록은 없다.

미병합 PR #8434(CBRD-27781)는 회수 로그를 값 하나당 약 6.1KB에서 0.71KB로 줄였다(`cbrd-27781/perf.md`). 다만 재기록 자체는 없애지 않는다. 같은 PR에서 행 하나 UPDATE+COMMIT 지연이 늘어난 것도 관찰됐다(`CBRD-27788/final-perf-handoff.md` 1절). [측정]

### 3. 판정

**미충족. 머지 범위는 팀 결정 필요.** 리뷰어는 이 항목을 머지 기준 1~3에 넣지 않았다. 대신 "이번 머지 범위에 넣을 수 있는지" 의견을 물었다. 작성자는 CBRD-27230을 후속 최적화로 분류했다(6441306406).

### 4. 남은 일, 크기와 위험

- CBRD-27230의 값 재사용은 다음 작업이다.
  - UPDATE가 assign하지 않은 OOS 컬럼의 stub(OID, 길이, identity stamp)을 새 레코드에 그대로 복사한다.
  - 옛 버전의 vacuum은 새 버전이 같은 chain을 가리키면 지우지 않는다.
- 크기: 크다.
- 위험: 높다. 같은 chain을 두 버전이 공유하면 CBRD-27237(rollback 뒤 vacuum이 살아 있는 값을 지움)과 같은 종류의 소유권 문제가 바로 생긴다. 참조 계수나 "마지막 소유 버전" 판정이 필요하다. CBRD-27237, CBRD-27781, #8434의 회수 설계가 정해진 다음에 해야 안전하다. [추론]
- 리뷰어 지적에는 "재기록 + 재읽기"가 함께 들어 있다. 항목 1의 읽기 비용을 줄이면 UPDATE의 읽기 부분도 같이 준다. [추론]

### 5. 답글 초안

> 67220b7에서도 작은 컬럼만 바꾸는 UPDATE가 바뀌지 않은 OOS 값을 다시 읽고(`heap_file.c:14901`) 새 chain에 씁니다(`heap_oos.cpp:889`). 옛 chain은 vacuum이 지웁니다(`vacuum.c:3748`). 지적하신 그대로입니다.
> 값 재사용(CBRD-27230)은 두 버전이 같은 chain을 공유하게 만듭니다. 그래서 rollback·vacuum의 소유권 문제(CBRD-27237, CBRD-27781)를 먼저 정리한 뒤에 넣는 것이 안전하다고 봅니다. 이번 머지에 넣을지는 팀에서 정하도록 올리겠습니다. 그 전까지 작은 컬럼 UPDATE의 현재 비용은 최종 head에서 다시 재서 숫자로 공유하겠습니다.

---

## 항목 3. 기준 1: OOS 값이 없는 테이블이 develop보다 느려지지 않을 것

### 1. 리뷰어 요구

6461744209 기준 1: OOS 값이 없는 테이블에서 develop보다 느려지지 않을 것(측정 노이즈 제외). #8299가 먼저 반영되어야 한다.

### 2. 67220b7 기준 현재 상태

- **선행 조건은 충족됐다.** #8299는 67220b7로 병합됐다. 측정 도구 `contrib/benchmarks/oos-performance/{bench.py,ordinary.py}`도 67220b7에 들어 있다(`git ls-tree`). [코드]
- **67220b7을 develop과 비교한 측정은 없다.** 문서 저장소에서 `67220b7`을 언급하는 측정 문서는 없다. `CBRD-27788/final-perf-handoff.md`(2026-11-11)도 #8299 미병합을 이유로 "지금은 잴 수 없다"고 적었다. [문서]
- 지금 있는 가장 가까운 측정은 다음과 같다. [측정]

| 측정 | revision | 조건 | 결과(명령어 수, 좋아지면 +) | 기준 1과의 관계 |
|---|---|---|---|---|
| PR #8299 본문 | `4c3c8d791` 대 develop `4781495f`, 2026-11-03 | release, `data_buffer_size=4G`, `instructions:u`, `ordinary.py`(리뷰어 질의), locale `en_US.utf8`, 테이블 문자셋 미기록 | 스캔 +0.79%, 조건 스캔 −0.83%, UPDATE −1.34% | 리뷰어와 같은 조건이다. 단 develop 기준이 옛 `4781495f`다 |
| CBRD-27816 1단계 | 같은 표 연속 UPDATE, 2026-11-04 | 유지 표본 36개 | −1.33%, 최악 −2.94% | 같다 |
| `pr8299-newbase-perf.md` | `855f220d5` 대 `50619ce53`(feature 끝), 2026-11-10 | 같은 conf, `en_US.utf8` | narrow +5.44%, wide +9.64%, scan +0.05%, predicate +7.26%, update +3.84% | **develop 대비가 아니다.** #8299가 feature보다 나아졌다는 것만 보여 준다 |

출처: `cbrd-27785/pr8299-sign-rule-pr-body.md`, `CBRD-27816-ordinary-update-phase1.md`, `pr8299-newbase-perf.md`.

- 리뷰어 조건(release, 4G, `instructions:u`)은 위 측정과 같다. 다른 점은 셋이다. [문서]
  - 리뷰어의 locale이 알려지지 않았다. 작성자 재현에서는 ISO-8859-1이 원문 수치에 더 가까웠다.
  - develop 기준이 `4781495f`에서 `2dd94e32`로 바뀌었다.
  - 반복 방식은 리뷰어가 4라운드×5회, `ordinary.py`가 매번 새 복제본에서 5 sample이다.
- 새 develop에는 page batch가 있다. 그래서 OOS 없는 표의 SELECT는 양쪽 다 batch 경로를 탈 가능성이 크다. 그렇다면 #8299 이전 비교보다 차이가 더 작아질 수 있다. UPDATE는 row 경로라서 이 영향이 없다. [추론, 미측정]

### 3. 판정

**부분 충족. 측정이 필요하다.**

- 선행 조건(#8299 병합)은 충족했다.
- 옛 develop 기준 측정에서는 SELECT 두 건이 ±1% 안이다.
- UPDATE는 −1.34%(최악 −2.94%)다. 작성자의 잠정 기준 2% 안이지만, 리뷰어 기준인 "노이즈 제외 동등"에 들어가는지는 리뷰어가 판단할 일이다.
- 최종 head와 현재 develop의 비교는 없다.

### 4. 남은 일, 크기와 위험

- 67220b7(또는 고정한 최종 head `F`)을 merge-base `2dd94e32`와 비교해 잰다. 연속 기준으로 `4781495f`도 함께 잰다. 아래 "측정 계획" P-1이다.
- 크기: 장비만 조용하면 반나절~하루다.
- 위험:
  - 이 서버의 load가 42~67이라 실행 시간은 판정에 쓸 수 없다(`final-perf-handoff.md` R6). 명령어 수만으로 판정해야 한다.
  - UPDATE의 1~3%가 리뷰어에게 노이즈로 받아들여질지는 불확실하다.

### 5. 답글 초안

> 기준 1의 선행 조건인 #8299는 2026-11-11에 feature/oos-merge에 병합됐습니다(67220b7). 병합 전 측정(4c3c8d791 대 develop 4781495f, release, data_buffer_size=4G, instructions:u, 말씀하신 질의)에서는 일반 테이블 스캔 −0.8%, 조건 스캔 +0.8%, UPDATE 20만 행 +1.3%였습니다(명령어 수 증가를 +로 표기).
> 다만 PR의 develop 기준이 2dd94e32로 바뀌었고 그 사이 page batch가 들어왔습니다. 그래서 67220b7과 현재 merge-base로 리뷰어님 재현 절차를 그대로 다시 돌려 결과를 공유드리겠습니다. 일반 테이블 UPDATE의 1%대 차이를 노이즈로 볼 수 있을지도 그 결과로 판단 부탁드립니다.

부호 주의: 리뷰어 표기(명령어 증가 = +)로 바꿔 적었다. 문서 저장소 표기(좋아지면 +)와 반대다.

---

## 항목 4. 기준 2: 기본 설정에서 4~16KB 행의 전체 읽기가 develop보다 느려지지 않을 것

### 1. 리뷰어 요구

6461744209 기준 2. 근거는 다음과 같다.

- 6KB 값 표의 큰 컬럼 스캔: length +40.6%, substr +38.7%(4408135c 기준).
- 4~16KB 행은 develop에서 heap에 있던 크기다. 기본 동작이 이 구간을 OOS로 보내서, 사용자가 요청하지 않은 손해가 생긴다.

### 2. 67220b7 기준 현재 상태

**OOS 임계값** [코드]

| 구분 | 위치 | 값 |
|---|---|---|
| 리뷰 시점 | - | `DB_PAGESIZE/4`(16KB 페이지에서 판정값 4,086B) |
| 67220b7 | `heap_oos_inline_target_size()` `heap_file.c:13746-13762`, `HEAP_OOS_MIN_RECS_PER_PAGE 4` `:13737`. #8299의 `4c3c8d791`에서 CBRD-27057 기준을 가져옴 | 4-record 목표 4,060B. TC 경계는 4,011B inline, 4,012B OOS |
| develop | - | 레코드가 `heap_Maxslotted_reclength`(16KB 페이지에서 16,236B)를 넘을 때만 REC_BIGONE overflow. 그 아래는 heap |

**기준 2의 구간과 같다.** 약 4,060B부터 16,236B까지는 develop에서 heap에 있고, PR에서 OOS로 간다(heap→OOS).

**OOS를 끄는 방법** [코드]

- 이 정책을 바꿀 system parameter가 없다(`system_parameter.c`에 OOS 관련 파라미터 없음).
- STORAGE 옵션은 `DEFAULT`, `PREFER_INLINE`, `FORCE_OUTLINE` 셋이다(`object_representation_sr.h:95-97`).
- `PREFER_INLINE`도 4,060B를 넘으면 마지막에 OOS로 보낸다(`heap_file.c:13865-13867`).
- `FORCE_INLINE`은 PR #8416(CBRD-27259)에 있고, OPEN 상태이며 미병합이다.

**#8299 이후 측정** [문서]

- 4~16KB OOS 행의 전체 읽기를 잰 기록은 없다. #8299 측정(`bench.py`, `ordinary.py`)은 80B 행만 다룬다(`pr8299-newbase-perf.md` 한계 절: "OOS 크기 행 … 범위가 아니다").
- 가장 최근 측정은 리뷰 시점 코드다. [측정]
  - 작성자 재현(`4408135c` 대 `4781495f`): LENGTH −28.3%(UTF-8), −44.2%(ISO-8859-1). SUBSTR −15.8%, −39.6%.
  - CBRD-27788(`dcbf09e`): 일반 heap 입력 Q4가 실행 시간 −25.9%(restart), −17.8%(warm). Q5가 −21.3%, −16.4%.
- 작성자 측은 기준 2를 "이번 수락에서 제외, 후속 이연"으로 정했다(`cbrd-27785/CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md` AC-P2). **리뷰어에게 이 결정을 알렸거나 리뷰어가 동의했다는 기록은 찾지 못했다.**

### 3. 판정

**미충족. 팀 결정 필요.**

- 현재 기본값에서는 구조적으로 heap→OOS 전환이 일어난다. 항목 1의 읽기 비용이 행마다 붙으므로, 측정 없이도 develop보다 느릴 것이 거의 확실하다. [추론]
- 작성자 측의 "후속 이연"은 리뷰어 기준과 충돌한다. 리뷰어는 이 기준을 머지 조건으로 걸었다.

### 4. 기본값 조정으로 기준 2를 맞출 수 있는가, 그 대가

| 안 | 기준 2 충족 | 대가와 위험 | 크기 |
|---|---|---|---|
| **A. 임계값을 페이지 크기로 올린다.** `heap_oos_inline_target_size()`가 `heap_Maxslotted_reclength` 근처를 돌려준다. 행이 페이지에 안 들어갈 때만 OOS로 보낸다(develop의 BIGONE 경계와 같게) | **충족 가능.** 4~16KB 행이 develop처럼 heap에 남는다. 남는 차이는 OOS 없는 행 reader의 차이(항목 3)뿐이다. 측정으로 확인해야 한다 [추론] | ① 4~16KB 구간에서 좁은 컬럼 조회 이득이 사라진다. 리뷰어 측정 −23%, CBRD-27788 Q1 heap 입력 실행 시간 +48.6%. OOS 이득은 16KB 넘는 행(overflow→OOS, Q1 +72.1%)에만 남는다. ② OOS 명세의 4-record 목표(CBRD-27057)를 버린다. 설계 문서와 리뷰 답변을 고쳐야 한다. ③ 많은 OOS TC가 기본 임계값(약 4~6KB 값)으로 OOS 행을 만든다. 이들이 OOS를 타지 않게 되어 커버리지가 조용히 빠진다. 4,011/4,012B 경계 TC도 바뀐다. `FORCE_OUTLINE`으로 바꾸거나 answer를 바꾸는 큰 작업이 필요하다 [추론, TC 전수 미확인] | 엔진은 작다. TC는 크다 |
| **B. 임계값을 system parameter로 만들고, 기본값을 A로 둔다** | A와 같다 | A의 대가에 파라미터 추가(이름, 범위, 재시작 여부, HA 일관성)가 더해진다. 리뷰어 6434778190 4번 요청("시스템 파라미터나 임계값 설정 검토")도 함께 충족한다. 작성자 수락 기준서의 AC-P2 후속 방향과 같은 방향이다 | 중간 |
| **C. `FORCE_INLINE`(#8416)을 기본 저장 정책으로** | 아마 충족한다. #8416에서 FORCE_INLINE이고 16KB를 넘는 행이 REC_BIGONE으로 가는지 확인해야 한다. ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE로 거부되면 develop보다 나빠진다 [추론, 미확인] | OOS가 사실상 opt-in이 되어 기본 설정의 이득이 0이다. A와 같은 TC 문제가 있다. #8416은 리뷰도 받지 않았다 | 중간 |
| **D. 기본값 유지 + 읽기 비용 최적화(항목 1의 a, b)** | **어려움.** 값마다 OOS 페이지 고정이 남는다 [추론] | 이득은 유지된다. 기준 2는 리뷰어 동의를 얻어 완화해야 한다 | 중간~크다 |

참고:

- 임계값은 저장 시 정책이고 디스크 형식이 아니다. 읽기 경로는 heap 행과 OOS 행을 모두 읽는다(`heap_file.c:12060-12083`). 그래서 A나 B로 출시한 뒤 기본값을 낮추는 것은 형식 변경 없이 할 수 있다. 반대로 지금 기본값으로 출시하면 이미 OOS로 간 4~16KB 행은 UPDATE하기 전까지 OOS에 남는다. [코드, 추론]
- 이 점은 리뷰어의 "11.5로 나가면 디스크 형식이 굳는다"는 우려에 대한 답의 근거가 된다. 보수적인 기본값(A/B)으로 출시하고 나중에 낮추는 경로다.

### 5. 답글 초안

> 기준 2는 현재 기본값으로는 충족하지 못합니다. 67220b7의 분리 기준은 4-record 목표(16KB 페이지에서 4,060B, `heap_file.c:13746`)입니다. develop에서 heap에 있던 약 4~16KB 행이 그대로 OOS로 갑니다. 그 행을 읽을 때마다 항목 1의 고정·복사 비용이 붙습니다. #8299 이후 이 구간을 잰 결과는 아직 없습니다.
> 맞추는 방법으로는 OOS로 보내는 기준을 develop의 overflow 경계(행이 한 페이지에 안 들어갈 때)로 올리고, 그 값을 시스템 파라미터로 조정할 수 있게 하는 안을 검토하고 있습니다. 이 기준은 저장 시 정책이라 디스크 형식이 아닙니다. 그래서 나중에 낮춰도 형식 변경이 필요 없습니다. 대신 4~16KB 행의 좁은 컬럼 조회 이득은 사라지고, OOS 이득은 16KB 넘는 행에만 남습니다.
> 이 방향으로 갈지는 팀 결정을 받은 뒤, 같은 재현 절차로 기본값과 조정값 양쪽 결과를 공유드리겠습니다.

---

## 측정 계획 제안 (실행하지 않음)

`CBRD-27788/final-perf-handoff.md`의 준비 조건과 시나리오를 그대로 쓴다. 바뀐 점은 R1이 참이 된 것이다(#8299 병합, 도구가 67220b7에 있음). 리뷰어 재현 스크립트를 그대로 쓰는 부분만 정리한다.

### 공통 조건

- **대상.**
  - `F` = 고정한 최종 head. 지금은 67220b7이다. #8434, #8348, #8492, #8416의 포함 여부를 정한 뒤 고정한다(`final-perf-handoff` R2, R3).
  - `B` = `git merge-base F origin/develop`. 지금은 `2dd94e32ab86`이다.
  - 연속 기준 `4781495f`는 별도 표로 둔다.
- **빌드와 설정.**
  - 양쪽 모두 release(CMake `RelWithDebInfo`, `-O2 -DNDEBUG`)로 빌드한다. `CUBRID_UNIT_TEST_ENABLED`는 없어야 한다.
  - 리뷰어 conf를 그대로 쓴다: `data_buffer_size=4G`, `log_buffer_size=256M`, `sort_buffer_size=16M`, `max_clients=50`, `db_volume_size=2G`, `log_volume_size=1G`, `log_max_archives=0`. port만 다르게 한다.
- **지표.** 질의마다 `perf stat -e instructions:u -p <cub_server pid>`로 잰 명령어 수가 판정 지표다. 실행 시간과 cycles는 참고로 남긴다.
- **반복.** 4라운드 ABBA(B→F, F→B, B→F, F→B), 라운드마다 5회, 첫 회는 버린다. 질의마다 유지 표본이 16개다.
- **문자셋.** `en_US.utf8`과 `en_US.iso88591`을 각각 새 DB로 만들어 따로 집계한다. 원문 locale을 모르므로 섞지 않는다.

### 시나리오

| ID | 대상 기준 | 실행기 | 질의 |
|---|---|---|---|
| P-1 | 기준 1 | 리뷰어 원문 실행기 `cbrd-27785/reviewer-exact-20261031/reproduce.py`, `locale_campaign.py`. `REVISIONS`(22~23행)만 `B`·`F`로 바꾼 사본을 쓰고 그 diff를 결과와 함께 남긴다(handoff M4). 보조로 `ordinary.py measure`(새 복제본 UPDATE)를 같은 서버에서 잰다 | `select count(*), sum(a) from n;`, `select count(*) from n where substr(s,30,1)='a';`, `update n set a=a+1;` |
| P-2 | 기준 2(기본값) | 같은 실행기, 같은 fixture(`w` 6,016자 값 2만 행) | `select sum(length(big)) from w;`, `select count(*) from w where substr(big,5000,1)='a';`, 그리고 이득 쪽 `select count(*), sum(a) from w;` |
| P-2b | 기준 2(구간 전체) | fixture의 SHA2 연결 개수만 바꾼 사본: 4.5KB(36개), 8KB(63개), 12KB(94개), 16KB 직전(126개). 큰 값 표 `w`의 `varchar(20000)`은 그대로다 | P-2와 같다. 값 크기마다 `SHOW HEAP CAPACITY`와 `SHOW HEAP OOS`로 B=heap, F=OOS인지 먼저 확인한다 |
| P-2c | 기준 2(조정안 진단) | `heap_oos_inline_target_size()`만 `heap_Maxslotted_reclength` 근처를 돌려주도록 바꾼 진단용 빌드 `F'`. 브랜치를 따로 만들고 PR에는 넣지 않는다 | P-2b와 같다. F'에서 4~16KB 행이 heap에 남는지 확인한 뒤 B 대비를 잰다. 안 A/B의 효과를 수치로 보여 주는 용도다 |
| P-3 | 항목 2(UPDATE) | 같은 실행기. UPDATE는 원문대로 같은 표에 연속 실행하는 방식과, 매번 새 복제본에서 하는 방식을 따로 잰다 | `update w set a=a+1;`, `update w set big=concat(substr(big,2),substr(big,1,1)) where id<=5000;`. vacuum이 계수 구간에 들어왔는지 기록한다 |
| P-4 | 항목 1 진단 | P-2와 같은 서버에서 `perf record -g`를 한 번 | 행당 `pgbuf_fix` 호출 수와 `disk_is_page_sector_reserved`·`memcpy`·`malloc`의 비중을 본다. 개선안 (a)(b)의 기대 효과를 추정하는 용도다. page batch fallback 여부는 B·F의 trace나 `expr_batch` fallback 이유로 확인한다 |

### 판정 규칙(측정 전에 고정)

- 기준 1·2는 질의별 유지 표본 중앙값으로 `(F − B) / B`를 낸다(리뷰어 부호).
- 라운드 사이 spread보다 차이가 작으면 "노이즈 안"으로 본다.
- 작성자 쪽 잠정 2%는 따로 적는다. 리뷰어가 승인한 허용치로 쓰지 않는다.
- heap→OOS 결과(P-2, P-2b)는 기본값 결과다. 조정 빌드 결과(P-2c)와 표를 나눈다.

### 장비

- 이 공유 서버는 load 42~67이라 실행 시간 판정에는 쓸 수 없다. 명령어 수만 판정하거나 조용한 장비를 쓴다(handoff R6, M9).
- 다른 세션(w2ED:p4 latency/flush, w2ED:p5 reader)의 측정과 시간이 겹치지 않게 한다(R7).

---

## 가장 중요한 결론 3줄

1. 리뷰어가 지적한 읽기 원인(값마다 고정 3번: 볼륨 헤더 `disk_manager.c:4271`, 섹터 테이블 `:4320`, OOS 페이지 / 복사 2번: `oos_file.cpp:2649`, `heap_file.c:11758`)과 UPDATE의 재기록(`heap_file.c:14901` → `heap_oos.cpp:889`, vacuum `vacuum.c:3748`)은 67220b7에도 그대로다. #8299는 OOS 없는 행만 고쳤다.
2. 기준 1은 선행 조건(#8299 병합)만 충족했다. 67220b7을 현재 develop(`2dd94e32`, page batch 포함)과 비교한 측정은 없다. 마지막 측정(4c3c8d791 대 옛 develop)은 SELECT ±0.8%, UPDATE +1.3%다.
3. 기준 2는 기본 임계값(4,060B)이 정확히 그 구간을 OOS로 보내므로 코드 최적화만으로는 맞추기 어렵다. 임계값을 페이지 크기로 올리고 파라미터로 두면 충족할 수 있다. 대신 4~16KB 이득 포기, 4-record 설계 철회, OOS TC 커버리지 재작업이 필요하다. 작성자 측의 "기준 2 후속 이연"은 리뷰어와 합의되지 않았으니 팀 결정이 먼저다.
