# CBRD-26399 slotted page 정렬 회계 재검증

- 분석일은 2026-11-05 (Asia/Seoul)이다. 작업 추적은 Work 805이다.
- 대상 이슈는 [CBRD-26399](http://jira.cubrid.org/browse/CBRD-26399)이다. 분석을 시작할 때 JIRA 요약은 `fix align bug in spage_max_record_size()`이고 상태는 Open이었다. 설명은 2025-11-24 작성본이고 코멘트는 2026-07-29 보고자 코멘트와 2026-10-01 반박 코멘트 두 개였다.
- 2026-11-05에 이 보고서로 이슈 본문을 바꾸고, OOS 확인 코멘트를 남긴 뒤 resolution `Not a bug` 로 종료했다. [CBRD-27781](http://jira.cubrid.org/browse/CBRD-27781) 과는 `Relates` 로 연결했다.
- 소스 기준은 `CUBRID/cubrid` develop의 `e64a04a79a5842827a124b3f8313516d0da2594c` 이다. 2026-11-05에 받은 `origin/develop` `2362424f25bcebd1bd9733bddd59a993e2852ac5` 와 비교하면 `slotted_page.c`, `slotted_page.h`, `memory_alloc.h`, `storage_common.c`, `heap_file.c`, `system_catalog.c` 는 같다. `external_sort.c` 와 `list_file.c` 의 차이는 `put_fn` 오류 처리와 정렬 목록 helper뿐이라 이 결론에 영향이 없다.
- OOS 브랜치 `feature/oos-merge` 의 `d52b1889e907abcf84190ec504dde3bc93de260d` 도 확인했다. 이 브랜치의 `slotted_page.c` 는 develop과 비교해 `spage_boot()` 반환형과 `PAGE_OOS` 페이지 종류 처리만 다르다. OOS가 이 결론에 주는 영향은 [OOS 브랜치](#oos-브랜치) 절에 적는다.
- 엔진 소스는 수정하지 않았다. 실험은 `debug_gcc` 빌드(Debug, `-O0`)의 SA 모드 `slotted_page.c` 객체에 별도 하네스를 링크해 실행했다. 하네스와 결과는 [evidence/](evidence/) 에 있다.
- 이 문서는 소스 추적, 계산, 이전 보고 인용, 이번 실행 결과를 구분해 적는다. 각 항목에 어느 종류인지 표시한다.

## 질문과 결론

이슈 설명은 두 가지를 주장한다. 첫째, `spage_initialize()` 가 `total_free` 를 `DB_ALIGN` 으로 올림해 실제 가용량보다 크게 보고할 수 있다. 둘째, `spage_max_record_size()` 가 정렬을 무시하므로 그 길이의 레코드가 들어가면 레코드 정렬 낭비가 slot 배열과 겹친다. 설명은 이를 근거로 두 함수의 식 변경과 assertion 추가를 제안했다. 2026-10-01 코멘트는 debug 빌드 실측으로 이 주장을 반박하고 Close를 요청했다.

결론은 다음과 같다.

- **현재 develop에는 이슈가 말하는 결함이 없다.** 레코드가 slot 배열을 침범하거나 `total_free` 가 실제 가용량보다 커지는 경로를 소스에서 찾지 못했다. 이번 실험의 72만 회 무작위 연산에서도 한 번도 나오지 않았다.
- `spage_max_record_size()` 는 정렬 8 페이지에서 실제 최대 길이보다 4바이트 크다. 이것은 사전 거절 기준이 느슨한 것일 뿐이다. 실제 판정 함수가 정렬 낭비와 slot 크기를 더해 다시 검사하므로 그 길이는 `SP_DOESNT_FIT` 으로 거절된다.
- `spage_initialize()` 의 `DB_ALIGN` 올림은 지원하는 모든 페이지 크기와 정렬에서 값을 바꾸지 않는다. `sizeof (SPAGE_HEADER)` 32와 `DB_PAGESIZE` 4056/8152/16344가 모두 8의 배수이기 때문이다.
- 2026-10-01 반박 코멘트의 실측 수치와 네 가지 지적은 모두 이번 실험과 소스 추적으로 재확인되었다.
- **권고는 코드 수정 없이 결함 아님으로 종료하는 것이다.** 옛 제안의 옵션 1은 도달 가능한 실패를 고치지 않으면서 heap 최대 slotted 레코드 길이를 4바이트 줄인다. 제안한 정렬 assertion은 정상 페이지에서 실패한다.

## 주장별 판정

| # | 주장과 출처 | 판정 | 근거 |
| --- | --- | --- | --- |
| 1 | `spage_initialize()` 의 `DB_ALIGN` 올림이 `total_free` 를 부풀린다 (설명 Analysis 1) | 현재 소스에서 반증. 헤더 크기가 바뀌는 가정에서만 성립 | 계산과 실행. 세 페이지 크기, 네 정렬 모두 `total_free == DB_PAGESIZE - 32` 로 정확한 값과 같다 ([계산](#계산), [실행 결과](#빈-페이지-경계)) |
| 2 | 초기화 직후와 compact 직후의 `total_free` 가 달라 회계가 어긋난다 (Analysis 2) | 반증 | 두 식은 같은 값을 낸다. 매 연산 뒤 `total_free == P - 32 - 4·num_slots - Σ DB_ALIGN(len)` 이 유지되었다 ([작업 부하](#무작위-작업-부하)) |
| 3 | `spage_max_record_size()` 길이의 레코드가 slot 영역과 겹친다 (Analysis 3) | 반증 | 설명의 예시는 페이지 크기를 16384로 두었지만 실제는 `DB_PAGESIZE` 16344다. 그 가정에서도 slot 4바이트를 더하면 거절된다. 실행에서도 정렬 8의 그 길이는 `SP_DOESNT_FIT` 이었다 |
| 4 | catalog, extendible hash 호출자가 과대 보고를 믿고 공간을 잘못 잡는다 (Analysis 4) | 반증 | 이들은 정렬을 반영하는 `spage_max_space_for_new_record()` 를 쓰고, 이 값은 실행에서 항상 실제로 들어갔다 ([호출자](#호출자-영향)) |
| 5 | `total_free` 가 항상 정렬 배수라는 assertion을 추가한다 (변경 4) | 성립하지 않음 | 정렬 8 페이지에서 slot이 4바이트씩 늘고 줄어 `total_free` 가 8의 배수가 아닌 상태가 75,162회 관측되었다 |
| 6 | `offset_to_free_area + cont_free + num_slots * 4 <= P` assertion을 추가한다 (변경 4) | 이미 있음 | `spage_check()` 가 같은 조건을 검사한다 ([slotted_page.c:4413][sp-check]) |
| 7 | 16K에서는 없고 8K, 4K에서 의심된다 (2026-07-29 코멘트) | 반증 | 세 페이지 크기의 산술과 실행 결과가 같은 패턴이다 |
| 8 | 4K/8K/16K 실측 값과 Close 요청 (2026-10-01 코멘트) | 재현됨 | 아래 [빈 페이지 경계](#빈-페이지-경계) 표가 코멘트의 수치와 일치한다 |

## slotted page 회계 계약

slotted page는 앞쪽에 `SPAGE_HEADER` 를, 뒤쪽 끝에서 앞으로 자라는 `SPAGE_SLOT` 배열을 둔다. 레코드는 헤더 뒤에 정렬된 offset으로 쌓인다.

```text
0          32                         offset_to_free_area          P - 4*num_slots        P
| header   | record | pad | record | pad | contiguous free (cont_free) | slot[n-1] ... slot[0] |
```

- `P` 는 `SPAGE_DB_PAGESIZE`, 즉 `DB_PAGESIZE` 다 ([slotted_page.c:70][sp-pagesize]). IO 페이지에서 예약 영역 40바이트를 뺀 값이다 ([storage_common.c:43-48][sc-reserved], [:74][sc-set]). 지원하는 IO 페이지는 4K, 8K, 16K다 ([storage_common.h:91-93][sch-sizes]).
- `SPAGE_HEADER` 는 32바이트이고 `SPAGE_SLOT` 은 4바이트다 ([slotted_page.h:64-91][sph-struct]). 헤더 주석은 "SPAGE_HEADER should be 8 bytes aligned"라고 요구한다 ([slotted_page.h:79][sph-comment]). 크기는 이번 실행에서 `sizeof` 로 확인했다.
- `alignment` 는 페이지마다 고정이다. heap, B+tree, extendible hash, hash scan 페이지는 4, catalog 페이지는 8 (`MAX_ALIGNMENT`)이다 ([호출자 영향](#호출자-영향)).

함수의 역할은 다음과 같다.

- `spage_max_record_size()` 는 정렬을 모른다. `P - 32 - 4` 를 돌려준다 ([slotted_page.c:842-845][sp-maxrec]). 이 값은 "이보다 길면 어떤 페이지에도 들어가지 않는다"는 사전 거절 기준으로 쓰인다. 삽입 전 검사 ([:1718][sp-checkins]), 갱신 전 검사 ([:2211][sp-checkupd]), `spage_put_helper` 의 검사가 이 값보다 긴 길이를 즉시 거절한다.
- 실제로 들어가는지는 다른 함수가 판정한다. `spage_find_empty_slot()` 은 `length + DB_WASTED_ALIGN (length, alignment)` 를 계산하고 ([:1389][sp-findwaste]), 새 slot이 필요하면 4바이트를 더한 뒤 ([:1417][sp-findslot]) `total_free` 및 `cont_free` 와 비교한다. `spage_check_updatable()` 도 새 길이의 정렬 낭비를 더해 비교한다 ([:2228][sp-updwaste]). 지정 slot 삽입 경로 (`spage_find_empty_slot_at`) 와 `spage_put_helper` 도 같은 방식이다.
- `spage_max_space_for_new_record()` 는 정렬을 반영한 여유 공간이다. 새 slot이 필요하면 4바이트를 빼고 ([:971][sp-maxnew-slot]) 정렬 단위로 내림한다 ([:978][sp-maxnew-align]). 외부 호출자는 주로 이 값을 쓴다.
- `spage_check()` 는 `used + total_free <= P` 와 `cont_free + offset_to_free_area + 4 * num_slots <= P` 를 검사한다 ([:4397][sp-check-used], [:4413][sp-check]). `SPAGE_DEBUG` 를 정의한 빌드가 아니면 heap과 B+tree의 점검 경로에서만 호출된다.

따라서 `spage_max_record_size()` 가 정렬 8 페이지에서 조금 크다는 사실은 "어떤 길이를 바로 거절할지"에만 영향을 준다. 페이지 배치를 정하는 계산에는 들어가지 않는다.

## 계산

이 절은 소스 식에서 직접 계산한 값이다. 실행 결과는 다음 절에 있다.

| IO 페이지 | `DB_PAGESIZE` (P) | 빈 페이지 `total_free` | `spage_max_record_size()` | 실제 최대 길이 (정렬 1/2/4) | 실제 최대 길이 (정렬 8) |
| --- | --- | --- | --- | --- | --- |
| 4K | 4056 | 4024 | 4020 | 4020 | 4016 |
| 8K | 8152 | 8120 | 8116 | 8116 | 8112 |
| 16K | 16344 | 16312 | 16308 | 16308 | 16304 |

- **초기화 식.** `spage_initialize()` 는 `total_free = DB_ALIGN (P - 32, a)`, `offset_to_free_area = DB_ALIGN (32, a)` 로 둔다 ([slotted_page.c:1085-1088][sp-init]). P와 32가 모두 8의 배수이므로 `a <= 8` 에서 두 식은 `P - 32` 와 `32` 이고 정확한 가용량과 같다.
- **compact 식.** `spage_compact()` 는 `P - DB_ALIGN (to_offset, a) - 4 * num_slots` 로 다시 계산한다 ([:1244][sp-compact]). 빈 페이지에서 이 값도 `P - 32` 다. 설명이 말한 "초기화 직후와 compact 직후의 차이"는 생기지 않는다.
- **정렬 8의 최대 길이.** 새 slot이 필요한 삽입은 `DB_ALIGN (L, 8) + 4 <= P - 32` 를 만족해야 한다. `P - 36` 은 8로 나눈 나머지가 4이므로 `DB_ALIGN (L, 8) <= P - 40` 이 되고 최대 L은 `P - 40` 이다. 정렬 4 이하에서는 `P - 36` 이 정렬 배수이므로 `spage_max_record_size()` 와 같다.
- **설명의 시나리오.** 설명은 P를 16384로 놓고 길이 16348을 넣으면 slot이 겹친다고 계산했다. 그 계산은 `spage_find_empty_slot()` 이 slot 4바이트를 더한다는 점을 빠뜨렸다. 16348 + 낭비 4 + slot 4 = 16356 > `total_free` 16352이므로 그 가정에서도 `SP_DOESNT_FIT` 이다.
- **헤더 크기가 바뀌는 가정.** 헤더가 36바이트가 되면 정렬 8의 16K 페이지에서 `total_free = DB_ALIGN (16308, 8) = 16312`, 실제 가용량은 `16344 - 40 = 16304` 다. 8바이트 과대 보고가 생기고 길이 16304 레코드가 받아들여져 slot[0]과 겹친다. 이 위험은 실제다. 그러나 `SPAGE_HEADER` 는 모든 slotted page에 기록되는 디스크 포맷이다. 크기를 바꾸려면 기존 볼륨 변환이 필요하므로 이 식만 따로 고칠 상황은 아니다. 그 변경을 막고 싶다면 `sizeof (SPAGE_HEADER) % MAX_ALIGNMENT == 0` 같은 컴파일 시점 검사가 더 직접적이다. 이것은 결함 수정이 아니라 선택적 하드닝이다.

## 실행

### 방법

- 대상은 수정하지 않은 `src/storage/slotted_page.c` 를 `debug_gcc` 프리셋의 SA 모드 컴파일 옵션 그대로 빌드한 객체다. `slotted_page.c` 의 sha256은 `0ff7f217cde5348dad7b67d8e38e275d3c44b535d0c82da093c86fe92eca33d4` 이고 `2362424f2` 의 파일과 같다. 컴파일러는 GCC 11.5.0이다.
- 하네스 [spage_boundary_probe.cpp](evidence/spage_boundary_probe.cpp) 는 공개 API `spage_initialize`, `spage_insert`, `spage_update`, `spage_delete`, `spage_vacuum_slot`, `spage_max_record_size`, `spage_max_space_for_new_record`, `spage_check` 를 메모리 페이지에 직접 호출한다. page buffer, 로그, 오류 관리자 함수는 최소 stub으로 바꾸었다. 실행 중 `er_set` 호출은 0회였다.
- `DB_PAGESIZE` 는 IO 페이지 4096, 8192, 16384에서 `sizeof (FILEIO_PAGE_RESERVED) + sizeof (FILEIO_PAGE_WATERMARK)` 를 뺀 값으로 설정했다. 정렬은 1, 2, 4, 8을 모두 시험했다.
- 저장 공간 예약 (`is_saving`) 은 껐다. 예약은 여유 공간을 줄이기만 하므로 과대 보고 여부를 판정하는 데 영향이 없다.
- 실행 명령은 다음과 같다. 소스 worktree에서 실행한다.

```bash
cmake --preset debug_gcc
ninja -C build_preset_debug_gcc sa/CMakeFiles/cubridsa.dir/__/src/storage/slotted_page.c.o
cbrd-26399/evidence/run-probe.sh build_preset_debug_gcc <output-dir> 20000
```

`run-probe.sh` 는 `compile_commands.json` 에서 그 객체의 컴파일 옵션을 꺼내 하네스를 같은 옵션으로 컴파일하고, 객체와 링크해 실행한다. 원본 결과는 [results.jsonl](evidence/results.jsonl), 실행 정보는 [identity.txt](evidence/identity.txt) 에 있다. 같은 seed로 두 번 실행해 결과가 같음을 확인했다.

### 빈 페이지 경계

각 조합에서 빈 페이지에 길이 `max - 24` 부터 `max + 8` 까지 삽입하고, 길이 1 레코드를 같은 길이로 갱신했다. 성공할 때마다 아래 [기하 검사](#무작위-작업-부하)를 실행했다.

| IO 페이지 | 정렬 | 초기 `total_free` | 초기 offset | `spage_max_record_size()` | 그 길이 삽입/갱신 | 최대 성공 길이 (삽입/갱신) | `spage_max_space_for_new_record()` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4K | 1, 2, 4 | 4024 | 32 | 4020 | `SP_SUCCESS` | 4020 / 4020 | 4020 |
| 4K | 8 | 4024 | 32 | 4020 | `SP_DOESNT_FIT` | 4016 / 4016 | 4016 |
| 8K | 1, 2, 4 | 8120 | 32 | 8116 | `SP_SUCCESS` | 8116 / 8116 | 8116 |
| 8K | 8 | 8120 | 32 | 8116 | `SP_DOESNT_FIT` | 8112 / 8112 | 8112 |
| 16K | 1, 2, 4 | 16312 | 32 | 16308 | `SP_SUCCESS` | 16308 / 16308 | 16308 |
| 16K | 8 | 16312 | 32 | 16308 | `SP_DOESNT_FIT` | 16304 / 16304 | 16304 |

모든 성공 사례에서 기하 검사가 통과했다. 이 표는 2026-10-01 코멘트의 실측 값과 같다.

### 무작위 작업 부하

페이지 크기 3 × 정렬 4 × anchor 종류 3 (`ANCHORED`, `ANCHORED_DONT_REUSE_SLOTS`, `UNANCHORED_KEEP_SEQUENCE`) 의 36개 조합에서 각 20,000회, 총 720,000회 연산을 실행했다. 연산은 삽입 50%, 삭제 25%, 갱신 25%이고 `ANCHORED` 의 삭제 중 4분의 1은 `spage_vacuum_slot()` 이다. 길이는 대부분 200바이트 이하이고 10%는 페이지 최대 길이까지 고르게 뽑았다. 390,739회가 성공했고 329,261회는 `SP_DOESNT_FIT` 이었다.

매 연산 뒤 하네스는 다음을 독립적으로 검사했다.

- 모든 레코드가 정렬된 offset에서 시작하고 `offset_to_free_area` 와 slot 배열 시작점보다 앞에서 끝난다.
- 레코드끼리 겹치지 않는다. `DB_PAGESIZE` 뒤의 guard 바이트가 바뀌지 않았다.
- `offset_to_free_area + cont_free <= P - 4 * num_slots` 이다.
- `total_free == P - 32 - 4 * num_slots - Σ DB_ALIGN (record_length, alignment)` 이다.
- `spage_check()` 가 `NO_ERROR` 를 돌려준다.

| 관측 | 결과 |
| --- | --- |
| 기하 검사 실패 | 0회 |
| `spage_max_space_for_new_record()` 길이를 복사 페이지에 삽입 | 584,888회 시도. `ANCHORED_DONT_REUSE_SLOTS` 와 `UNANCHORED_KEEP_SEQUENCE` 는 실패 0회. `ANCHORED` 는 37,126회 실패했고 모두 [범위 밖 관찰 3](#범위-밖-관찰)의 조건이었다 |
| `total_free` 가 정렬 배수가 아닌 상태 | 정렬 8에서 75,162회, 정렬 1/2/4에서 0회 |

### 한계

- 단일 스레드에서 공개 API만 호출했다. 저장 공간 예약, 복구 경로 (`spage_insert_for_recovery`), `spage_split`, `spage_merge`, `spage_take_out` 은 실행하지 않았다. 이 경로의 정렬 처리는 소스로만 확인했다.
- 실제 DB, heap, catalog를 통한 SQL 재현은 하지 않았다. 호출자 판단은 소스 추적이다.
- release 빌드는 실행하지 않았다. 판정 산술은 debug와 release에서 같은 소스 식이다.

## 호출자 영향

이 절은 소스 추적이다. 별도 에이전트가 호출자를 조사했고, 아래 항목은 본문 작성자가 다시 열어 확인했다.

| 호출자 | 페이지 정렬 | 사용하는 값 | 판단 |
| --- | --- | --- | --- |
| heap `heap_Maxslotted_reclength` ([heap_file.c:3752-3754][hf-maxslotted]) | 4 | `spage_max_record_size()` 에서 chain 레코드와 slot 8개 여유를 뺀 값 | 정렬 4에서는 `spage_max_record_size()` 가 정확하다. 영향 없음 |
| heap bestspace 페이지 용량 ([heap_file.c:3951-3952][hf-bestspace]) | 4 | `spage_max_record_size()` - chain - slot | 정렬 4에서 정확하다. 영향 없음 |
| `heap_nonheader_page_capacity()` ([heap_file.c:27854][hf-capacity]) | 4 | `spage_max_record_size()` - chain | 문턱값으로만 쓰인다. 영향 없음 |
| catalog `catalog_Max_record_size` ([system_catalog.c:274][cat-max], [:2608][cat-max-set]) | 8 | `spage_max_record_size()` 기반 | 대입만 있고 읽는 곳이 없다 |
| catalog 레코드 공간 계산 | 8 | `spage_max_space_for_new_record()` - 12 | 정렬을 반영한 값이다. 실행에서 `ANCHORED_DONT_REUSE_SLOTS`, 정렬 8의 실패는 0회였다 |
| extendible hash ([extendible_hash.c:1019-1033][eh-align]) | 항상 4 | split과 merge 문턱값 | 영향 없음 |
| B+tree, hash scan | 4 | `spage_max_space_for_new_record()`, 자체 상수 | 영향 없음 |

heap 페이지의 anchor 종류는 항상 `ANCHORED_DONT_REUSE_SLOTS` 다 ([heap_file.c:1085][hf-spagetype]). 2026-10-01 코멘트가 지적한 대로, 옵션 1 (`spage_max_record_size()` 를 `MAX_ALIGNMENT` 기준으로 내림) 을 적용하면 정렬 4 heap 페이지의 위 상수들이 4바이트 줄어든다. 도달 가능한 실패를 고치지 않으므로 얻는 것이 없다.

## 범위 밖 관찰

조사 중 정렬과 slot 회계에 관련된 세 가지를 더 확인했다. develop에서는 셋 다 결함 조건에 도달할 수 없어서 CBRD-26399의 결론을 바꾸지 않는다. 1번과 2번은 코드가 실제로 실행되지만, 결함을 드러내는 입력이나 페이지 상태를 지금 호출자가 만들지 않는다. 3번은 develop에 해당 페이지 조합이 없다.

1. **`external_sort.c` 의 `SORT_MAXREC_LENGTH`.** 질의 정렬은 `slotted_page.c` 가 아닌 자체 slotted page 구현을 쓴다. 헤더는 16바이트, slot은 6바이트, 정렬은 8이다 ([external_sort.c:212-230][es-struct], [:2345][es-init]). 최대 길이는 `DB_PAGESIZE - 16 - 6` 인데 ([:91-92][es-max]), 빈 페이지가 실제로 받는 최대 길이는 `DB_PAGESIZE - 24` 다. 따라서 `DB_PAGESIZE - 23` 과 `DB_PAGESIZE - 22` 길이는 사전 검사를 통과한 뒤 빈 페이지 삽입에서 실패하고, 정렬은 `ER_FATAL_ERROR_SEVERITY` 로 `ER_GENERIC_ERROR` 를 낸다 ([:2389-2395][es-fail]). 그러나 정렬 입력 레코드는 네 호출 경로 모두 `qfile_make_sort_key()` 가 만들고, 그 길이는 항상 4의 배수다 ([list_file.c:268-270][lf-aslot], [qfile_tuple_layout.h:617][qt-align]). 두 길이는 4의 배수가 아니므로 현재 도달할 수 없다. 정렬 버퍼의 첫 레코드는 `malloc` 결과에서 8바이트 뒤에 놓이고 ([external_sort.c:1921][es-buf]), 다음 레코드는 `DB_ALIGN (len, 8) + 8` 만큼 뒤에 놓인다 ([:2177][es-advance]). 그래서 정렬 레코드의 시작 주소는 항상 8의 배수이고, 데이터 앞 헤더 부분의 길이도 8의 배수가 된다. 조건이 깨지더라도 결과는 질의 하나의 실패다. fatal 심각도는 로그와 call stack 덤프만 남기고 서버를 내리지 않는다 ([error_manager.c:1549][em-dump]). 예외는 `er_stop_on_error` 를 그 오류 번호로 설정한 경우다 ([:1579-1582][em-stop]). B+tree 정렬의 복사본은 이미 정렬 낭비를 반영한 `BTSORT_MAXREC_LENGTH` 를 쓴다 ([btree_sort.c:104-109][bs-max], CBRD-27235).
2. **정렬 1에서 `spage_check()` 의 오탐.** `spage_check()` 는 `cont_free <= -(alignment - 1)` 이면 오류로 본다 ([slotted_page.c:4432][sp-check-cfree]). 정렬 1에서는 꽉 찬 정상 페이지 (`cont_free == 0`) 도 오류가 된다. 첫 실행이 이 assert로 멈췄다. `cont_free` 는 `SPAGE_VERIFY_HEADER` 가 0 이상으로 assert하므로 ([slotted_page.c:77][sp-verify]) 잘못 판정하는 경우는 정렬 1이면서 `cont_free == 0` 일 때뿐이다. `spage_check()` 호출자는 heap 점검 ([heap_file.c:15542][hf-check]) 과 B+tree 점검 ([btree.c:8824][bt-check]) 이고, 운영 코드에서 정렬 1 페이지를 만드는 곳은 없다.
3. **`ANCHORED` 페이지의 재사용 불가 slot.** `spage_max_space_for_new_record()` 는 `ANCHORED` 페이지에서 `num_slots > num_records` 이면 재사용할 slot이 있다고 보고 slot 4바이트를 빼지 않는다. `spage_vacuum_slot (..., reusable = false)` 가 남긴 `REC_MARKDELETED` slot만 있으면 이 가정이 틀려 4바이트 크게 보고한다 ([slotted_page.c:4859][sp-vacuum]). 실행에서 본 37,126회 실패가 모두 이 경우였다. develop에서는 `ANCHORED` 값이 enum 정의 ([slotted_page.h:38][sph-anchored]) 와 이름 출력 ([slotted_page.c:4114][sp-anchored-name]) 에만 나오고, `spage_initialize()` 에 넘기는 곳이 없다. `heap_get_spage_type()` 은 git 이력이 시작된 2014-04부터 항상 `ANCHORED_DONT_REUSE_SLOTS` 를 반환했다. `spage_vacuum_slot()` 은 heap 페이지에만 쓰인다. OOS 브랜치는 `ANCHORED` 페이지를 쓰므로 [OOS 브랜치](#oos-브랜치) 절에서 따로 다룬다.

## OOS 브랜치

OOS (Out-of-row Overflow Storage) 는 develop에 아직 없고 `feature/oos-merge` 에 있다. 기준은 `d52b1889e907abcf84190ec504dde3bc93de260d` 이다 (소스). 결론은 바뀌지 않는다. 다만 범위 밖 관찰 3은 앞으로의 OOS 변경에 조건이 붙는다.

- **페이지 형태.** OOS 페이지는 `ANCHORED`, 정렬 8, `is_saving=false` 로 초기화된다 ([oos_file.cpp:128][oos-align], [:3152][oos-init]).
- **정렬 4바이트 차이는 이미 보정되어 있다.** OOS는 정렬 8 페이지에서 `spage_max_record_size()` 를 쓰지만 `DB_ALIGN_BELOW (spage_max_record_size (), OOS_ALIGNMENT)` 로 내려서 쓴다 ([:2226][oos-cap], [:2511][oos-assert], [:3626][oos-limit]). 이 값은 `DB_PAGESIZE - 40` 이고 정렬 8 빈 페이지에 실제로 들어가는 최대 길이와 같다 (계산).
- **범위 밖 관찰 3의 조건은 아직 생기지 않는다.** OOS에서 slot을 비우는 함수는 `spage_delete()` 뿐이다 (삭제 [:3359][oos-del], redo [:3655][oos-rv-del]). 이 함수는 `ANCHORED` 페이지에서 slot을 `REC_DELETED_WILL_REUSE` 로 남긴다 ([slotted_page.c:2093-2095][oos-sp-delete]). undo의 `spage_insert_for_recovery()` 는 빈 slot을 채울 뿐 재사용 불가 slot을 만들지 않는다. `REC_MARKDELETED` 를 만드는 `spage_vacuum_slot()` 호출은 모두 heap vacuum이다 (소스).
- **조건이 생기면 결과는 삽입 실패다.** OOS는 `spage_max_space_for_new_record()` ([slotted_page.c:960-967][oos-sp-maxnew]) 가 돌려준 값으로 삽입할 페이지를 고른다 ([oos_file.cpp:725][oos-pick]). 그 뒤 `spage_insert()` 가 실패하면 `ER_GENERIC_ERROR` 를 반환한다 ([:2479-2484][oos-fail]). `spage_insert()` 가 다시 판정하므로 페이지 손상은 없다 (소스 근거 추론, 실행하지 않음).
- **CBRD-27781 수정의 조건.** [CBRD-27781](http://jira.cubrid.org/browse/CBRD-27781) 은 OOS 삭제를 취소할 때 복원할 slot을 다른 트랜잭션이 먼저 쓰는 결함이다. 그 수정이 삭제된 OOS slot을 비운 채 재사용 불가로 남기면 관찰 3이 실제로 발생한다. 그 경우 같은 변경에서 `spage_max_space_for_new_record()` 의 `ANCHORED` 분기가 재사용 가능한 slot을 확인하게 하거나, OOS 페이지를 `ANCHORED_DONT_REUSE_SLOTS` 로 바꿔야 한다. slot을 재사용 가능으로 둔 채 페이지를 잠시 삽입 후보에서 빼는 방식이면 해당하지 않는다. 이 조건은 CBRD-27781 코멘트에도 남겼다.

## 결함과 해석 차이를 가르는 질문

| 질문 | 답 | 근거 종류 |
| --- | --- | --- |
| 지원하는 페이지 크기와 헤더 크기에서 초기화의 올림이 값을 바꾸는가? | 아니다 | 계산, 실행 |
| `spage_max_record_size()` 를 통과한 길이를 정렬 낭비나 slot 없이 받아들이는 삽입·갱신 경로가 있는가? | 없다. 모든 경로가 낭비와 slot을 더해 다시 검사한다 | 소스, 실행 |
| 정렬 8 페이지의 외부 호출자 중 `spage_max_record_size()` 를 "들어간다는 보장"으로 쓰는 곳이 있는가? | develop에는 없다. catalog의 유일한 사용은 읽히지 않는다. OOS 브랜치는 정렬 8로 내린 값을 쓴다 | 소스 |
| 연산이 이어져도 `total_free` 가 실제 배치와 맞는가? | 맞다. 72만 회 동안 항등식이 유지되었다 | 실행 |
| 제안한 assertion이 정상 페이지에서 성립하는가? | 정렬 assertion은 성립하지 않는다. 침범 검사는 이미 `spage_check()` 에 있다 | 소스, 실행 |

## 권고

- CBRD-26399는 코드 수정 없이 결함 아님으로 종료한다. 이슈 본문은 이 검증 결과로 바꾸어 기록을 남긴다. 2026-11-05에 이대로 처리했다.
- OOS 삭제 slot의 재사용 방식을 바꾸는 CBRD-27781 수정은 범위 밖 관찰 3을 함께 고친다. 조건은 [OOS 브랜치](#oos-브랜치) 절에 있다.
- 선택적 하드닝은 별도 판단이다. `SPAGE_HEADER` 크기의 정렬 요구를 컴파일 시점 검사로 바꾸거나, `spage_max_record_size()` 주석에 "정렬 무관 사전 상한"임을 적을 수 있다. 둘 다 동작을 바꾸지 않는다.
- 범위 밖 관찰 1의 `SORT_MAXREC_LENGTH` 는 `BTSORT_MAXREC_LENGTH` 와 같은 식으로 맞출 수 있다. 현재 도달할 수 없으므로 우선순위는 낮다. 정렬 레코드 길이 규칙이 바뀌는 변경이 있을 때 함께 보는 것이 적절하다.

[sp-pagesize]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L70-L71
[sp-maxrec]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L842-L845
[sp-maxnew-slot]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L971
[sp-maxnew-align]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L978
[sp-init]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L1085-L1088
[sp-compact]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L1244
[sp-findwaste]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L1389-L1396
[sp-findslot]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L1414-L1423
[sp-checkins]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L1718
[sp-checkupd]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L2211
[sp-updwaste]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L2227-L2234
[sp-check-used]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L4397
[sp-check]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L4413-L4414
[sp-check-cfree]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L4432
[sp-vacuum]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L4853-L4860
[sph-struct]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.h#L64-L91
[sph-comment]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.h#L79
[sc-reserved]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/storage_common.c#L43-L48
[sc-set]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/storage_common.c#L74
[sch-sizes]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/storage_common.h#L91-L93
[hf-maxslotted]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/heap_file.c#L3752-L3754
[hf-bestspace]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/heap_file.c#L3951-L3952
[hf-capacity]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/heap_file.c#L27854-L27857
[hf-spagetype]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/heap_file.c#L1085-L1088
[cat-max]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/system_catalog.c#L274
[cat-max-set]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/system_catalog.c#L2608-L2609
[eh-align]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/extendible_hash.c#L1019-L1033
[es-max]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/external_sort.c#L91-L92
[es-struct]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/external_sort.c#L212-L230
[es-init]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/external_sort.c#L2345
[es-fail]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/external_sort.c#L2389-L2395
[lf-aslot]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/query/list_file.c#L268-L270
[qt-align]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/query/qfile_tuple_layout.h#L617
[bs-max]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/btree_sort.c#L104-L109
[es-buf]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/external_sort.c#L1921
[es-advance]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/external_sort.c#L2177
[em-dump]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/base/error_manager.c#L1549
[em-stop]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/base/error_manager.c#L1579-L1582
[sp-verify]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L77
[hf-check]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/heap_file.c#L15542
[bt-check]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/btree.c#L8824
[sph-anchored]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.h#L38
[sp-anchored-name]: https://github.com/CUBRID/cubrid/blob/e64a04a79a5842827a124b3f8313516d0da2594c/src/storage/slotted_page.c#L4114
[oos-align]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L128
[oos-init]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L3152
[oos-pick]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L725
[oos-cap]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L2226
[oos-fail]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L2479-L2484
[oos-assert]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L2511
[oos-limit]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L3626
[oos-del]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L3359
[oos-rv-del]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L3655
[oos-sp-maxnew]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/slotted_page.c#L960-L967
[oos-sp-delete]: https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/slotted_page.c#L2093-L2095
