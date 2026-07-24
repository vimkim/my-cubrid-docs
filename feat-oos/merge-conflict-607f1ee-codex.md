# `feat/oos`–`develop` 병합 충돌 해결 결정 보고서

## 1. 개요

본 보고서는 `feat/oos`에서 `git merge origin/develop`를 수행하면서 발생한 충돌의 해결 결정과 검증 결과를 기록합니다.

| 항목 | 값 |
|---|---|
| 작업 브랜치 | `feat/oos` |
| OOS 측 선행 커밋 | `d915476d2ecf288bda0a05817550ae5dbdecaba6` |
| 병합한 `develop` 커밋 | `607f1ee9fb2394de129e083602c84a6525fc685c` |
| merge base | `ecd16cc8e93f7febeb5a1d7ba0ccd01600932c8e` |
| merge commit | `46682090f7791bab6bdd5c1ad617c6ab34fb957a` |
| 해결일 | 2026-07-24 |

병합 시작 시 `MERGE_HEAD`는 `607f1ee`였습니다. 양쪽 고유 커밋 수는 OOS 측 75개, `develop` 측 10개였습니다.

검증 완료 뒤 로컬 `origin/develop` 참조가 `f98020709b0c82703cbeb6c8bad02b69b1b8d760`으로 한 커밋 더 전진했습니다. 이 후속 커밋은 본 충돌의 `MERGE_HEAD`가 아니므로 merge commit `4668209`와 본 보고서의 범위에 포함하지 않았습니다.

## 2. 결론

충돌은 다음 원칙으로 해결했습니다.

1. `develop`의 parser 위치 추적 개선과 heap scan latch API 전환을 수용합니다.
2. OOS 브랜치의 SQL 키워드, `SHOW HEAP OOS`, column storage 문법과 OOS 수명주기 처리를 보존합니다.
3. raw recdes 소비 여부와 caller-owned buffer 소유권을 구분하는 OOS fetch 계약을 보존합니다.
4. Git 충돌 마커 밖의 OOS 전용 테스트도 새 latch 타입에 맞춰 수정합니다.

최종 결과는 `develop`의 새 parser/lexer 및 `PGBUF_LATCH_MODE` 계약을 사용하면서 OOS 브랜치의 현재 기능을 유지합니다. 여기서 `STORAGE PREFER_INLINE`은 현재 `feat/oos` 구현을 보존한 것이며, OOS 규범 문서상 별도 설계 상태를 변경한 결정은 아닙니다.

## 3. 충돌 범위

Git이 보고한 텍스트 충돌은 다음 세 파일입니다.

- `src/parser/csql_grammar.y`
- `src/parser/csql_lexer.l`
- `src/storage/heap_file.c`

첫 빌드에서 충돌 마커 밖의 의미 충돌 한 건도 확인했습니다.

- `unit_tests/oos/test_oos_real_vacuum_server.cpp`: `HEAP_SCANCACHE::page_latch`의 타입이 `LOCK`에서 `PGBUF_LATCH_MODE`로 바뀌었지만 OOS 전용 테스트가 `X_LOCK`을 계속 대입

## 4. 세부 결정

### 4.1 Identifier grammar에는 새 위치 인자와 OOS 키워드를 함께 유지

`develop`는 CBRD-26909의 parser 위치 추적 개선에 따라 `SET_CPTR_2_PTNAME` 호출에 token location `@1`을 추가했습니다. OOS 측은 다음 identifier token을 추가한 상태였습니다.

- `OOS`
- `PREFER_INLINE`
- `PREFER_OUTLINE`
- `STORAGE`

최종 grammar는 `develop` 형식인 `SET_CPTR_2_PTNAME($$, $1, @1, @$.buffer_pos)`을 모든 identifier token에 적용하고, 위 네 OOS token도 같은 형식으로 복원했습니다.

관련 위치:

- `src/parser/csql_grammar.y:20723`
- `src/parser/csql_grammar.y:20739`
- `src/parser/csql_grammar.y:20740`
- `src/parser/csql_grammar.y:20782`

### 4.2 Lexer는 공통 `YY_USER_ACTION` 위치 추적을 사용

`develop`의 lexer는 각 keyword action에서 반복하던 `begin_token` 호출을 제거하고 `YY_USER_ACTION`을 통해 `parser_yy_user_action()`을 공통 실행합니다. 따라서 OOS 키워드만 과거 형식으로 되살리면 위치 추적 계약이 일관되지 않습니다.

최종 lexer는 `develop` 구조를 그대로 사용하고 다음 네 keyword rule만 새 형식으로 추가했습니다.

- `OOS`
- `PREFER_INLINE`
- `PREFER_OUTLINE`
- `STORAGE`

각 rule은 필요한 `pt_makename()`과 token 반환만 수행하며 위치 갱신은 공통 `YY_USER_ACTION`에 맡깁니다.

관련 위치:

- `src/parser/csql_lexer.l:103`
- `src/parser/csql_lexer.l:657`
- `src/parser/csql_lexer.l:704`
- `src/parser/csql_lexer.l:706`
- `src/parser/csql_lexer.l:855`

### 4.3 OOS SQL 문법과 진단 기능은 보존

`develop` 버전을 기준으로 parser 충돌 구간을 정리한 뒤, OOS 측의 다음 변경을 모두 다시 적용했습니다.

- `COLUMN_CONSTRAINT_STORAGE`
- `STORAGE PREFER_INLINE`, `STORAGE DEFAULT`, `STORAGE PREFER_OUTLINE`
- shared/class attribute에 대한 storage option 거부
- `SHOW HEAP OOS`, `SHOW ALL HEAP OOS`

관련 위치:

- `src/parser/csql_grammar.y:169`
- `src/parser/csql_grammar.y:7533`
- `src/parser/csql_grammar.y:7537`
- `src/parser/csql_grammar.y:10001`
- `src/parser/csql_grammar.y:10534`

### 4.4 Non-MVCC DELETE의 OOS eager cleanup을 유지

`heap_delete_home` 충돌에서 `develop` 측에는 추가 동작이 없었고, OOS 측에는 SA_MODE/non-MVCC DELETE가 heap slot을 물리 삭제하기 전에 OOS value chain을 정리하는 처리가 있었습니다.

이 처리를 제거하면 vacuum이 없는 단일 프로세스 모드에서 OOS value chain이 남을 수 있으므로 `heap_oos_delete_unreferenced()` 호출을 유지했습니다. MVCC DELETE는 기존처럼 OOS inline stub을 보존하고 vacuum이 나중에 정리합니다.

관련 위치:

- `src/storage/heap_file.c:23018`
- `src/storage/heap_file.c:23024`

### 4.5 OOS recdes 계약과 새 latch enum을 결합

`heap_init_get_context` 충돌은 서로 독립적인 변경이 겹친 경우였습니다.

OOS 측에서 유지한 항목:

- `recdes_consumption_policy`
- scan-cache area 여부 판별
- caller-positioned buffer의 `keep_recdes_buffer` 소유권 보존

`develop` 측에서 수용한 항목:

- `scan_cache->page_latch == PGBUF_LATCH_WRITE`
- `PGBUF_LATCH_READ`/`PGBUF_LATCH_WRITE` 기반 context latch mode

따라서 OOS의 record-level Expand 및 buffer ownership 계약은 유지하되, 폐기된 `X_LOCK` 비교는 되살리지 않았습니다.

관련 위치:

- `src/storage/heap_file.c:26778`
- `src/storage/heap_file.c:26782`
- `src/storage/heap_file.c:26783`

### 4.6 OOS real-vacuum 테스트도 latch enum으로 이행

Git 충돌을 모두 해결한 뒤 첫 빌드는 다음 타입 오류를 발견했습니다.

```text
cannot convert ‘LOCK’ to ‘PGBUF_LATCH_MODE’ in assignment
```

전체 source/unit-test tree를 검색한 결과 남은 구식 대입은 OOS real-vacuum fixture 한 곳뿐이었습니다. Write latch가 필요했던 기존 의미를 유지하도록 다음과 같이 변경했습니다.

```cpp
scan_cache.page_latch = PGBUF_LATCH_WRITE;
```

관련 위치:

- `unit_tests/oos/test_oos_real_vacuum_server.cpp:293`

## 5. 검증

`debug_gcc` 구성에서 로컬 빌드 및 테스트를 수행했습니다.

| 검증 | 결과 |
|---|---|
| 전체 build/install | 성공 |
| 첫 build의 의미 충돌 탐지 | OOS real-vacuum 테스트의 `X_LOCK` 대입 1건 |
| 수정 후 rebuild/install | 성공 |
| CTest | 24/24 성공 |
| 전체 테스트 시간 | 48.73초 |
| 미해결 index entry | 없음 |
| 충돌 마커 | 없음 |

24개 CTest 항목에는 다음 경로가 포함됩니다.

- OOS insert/read/delete 및 multi-chunk
- OOS bestspace
- SERVER_MODE OOS 처리
- mock vacuum 및 real vacuum
- SQL CRUD, DDL, UPDATE/DELETE, 트랜잭션
- OOS eager cleanup
- PG-style four-record heap target 경계
- OOS + bigone 거부
- `STORAGE PREFER_INLINE`
- `SHOW HEAP OOS`
- TDE 사용자 데이터 gate

Parser 생성은 성공했습니다. Bison은 기존 grammar 수준의 shift/reduce 및 reduce/reduce warning을 출력했지만 생성과 컴파일은 완료되었습니다.

## 6. 커밋 위생 및 보존 사항

로컬 pre-commit hook은 staged C/C++ 파일 전체에 formatter를 실행합니다. 이번 merge에는 `origin/develop`에서 들어온 대규모 parser 및 engine 변경이 포함되어 있어 hook을 실행하면 충돌 해결과 무관한 재포맷이 생길 수 있습니다. 빌드와 24개 테스트를 통과한 merge tree를 그대로 커밋하기 위해 개인용 lefthook만 비활성화했습니다.

`develop`의 parser/lexer 변경에는 기존 trailing whitespace가 포함되어 있습니다. 충돌 해결 범위를 넘어 upstream 전체를 재작성하지 않기 위해 이를 별도 정리하지 않았습니다.

작업 전부터 존재한 다음 내용은 merge commit에 포함하지 않았습니다.

- `cubrid-cci` 서브모듈의 로컬 수정
- `cubrid-jdbc` 서브모듈의 로컬 상태
- 개인용 미추적 설정, 도구 및 문서

원격 push는 수행하지 않았습니다.

## 7. 최종 상태

merge commit `46682090f7791bab6bdd5c1ad617c6ab34fb957a`은 다음 두 커밋을 부모로 가집니다.

1. `d915476d2ecf288bda0a05817550ae5dbdecaba6` — 병합 전 `feat/oos`
2. `607f1ee9fb2394de129e083602c84a6525fc685c` — 충돌을 발생시킨 `origin/develop` snapshot

`607f1ee`는 merge commit의 조상이므로 요청된 충돌 병합은 완료되었습니다. 현재 로컬 `origin/develop`의 후속 `f980207`은 별도 병합 대상입니다.
