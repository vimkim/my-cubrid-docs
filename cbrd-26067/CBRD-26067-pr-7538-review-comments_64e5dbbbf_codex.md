# CBRD-26067 PR #7538 리뷰 댓글 검토 보고서

- PR: [CUBRID/cubrid#7538](https://github.com/CUBRID/cubrid/pull/7538)
- 제목: `[CBRD-26067] Add STORAGE FORCE_OUTLINE column option`
- 조사 일자: 2026-07-28
- PR 원격 HEAD: `dfe30e5b09abf8411ade72f914d01d71b325d900`
- 조사 시작 시 로컬 HEAD: `64e5dbbbf699c1b69ec5ddff436eca1dddc54069`
- 기준 문서: CBRD-26067 JIRA, OOS 규범 문서(2026-07-13), 현재 소스

## 결론

의미 있는 인라인 리뷰 댓글은 4건이다. 이 중 3건은 유효하여 로컬 코드에 반영했고, 1건은 다섯 개의
enum 이름을 다섯 개의 서로 다른 값으로 해석한 오해이므로 코드 수정 대상에서 제외했다.

| 구분 | 건수 |
|---|---:|
| 유효, 수정 완료 | 3 |
| 무효, 수정 없음 | 1 |
| 승인 리뷰 | 4 |
| PR 대화 댓글 | 1 |

2026-07-28 조사 시점에 네 인라인 스레드는 모두 GitHub UI에서 `unresolved`, `not outdated` 상태다.
수정은 아직 커밋하거나 push하지 않았으므로 GitHub 스레드 상태와 PR 원격 HEAD는 바뀌지 않았다.

## 수집 범위

GitHub REST API의 세 채널을 모두 조회했다.

1. 인라인 리뷰 댓글: 4건
2. 리뷰 요약: 8건
   - 승인 4건
   - 본문이 빈 `COMMENTED` wrapper 4건은 인라인 댓글과 중복되어 별도 댓글로 세지 않음
3. PR 대화 댓글: 1건

GraphQL `reviewThreads`도 조회하여 인라인 스레드의 해결 여부와 outdated 여부를 대조했다.

## 인라인 댓글 추적

### 1. 파서 저장 상태의 2비트 표현

- 댓글: [discussion_r3654603385](https://github.com/CUBRID/cubrid/pull/7538#discussion_r3654603385)
- 작성자: `lht1199`
- 위치: `src/parser/parse_tree.h:1963`
- 원문: “2비트인데 5개 상태를 갖네요.”
- 판정: **무효 — 실제로는 서로 다른 상태가 4개임**
- 처리: 코드 수정 없음

`PT_ATTR_STORAGE_SETTING`에는 이름이 다섯 개 보이지만 `PT_ATTR_STORAGE_PREFER_OUTLINE`은
`PT_ATTR_STORAGE_DEFAULT`의 alias다. 실제 값은 다음 네 개뿐이다.

| 값 | 상태 |
|---:|---|
| 0 | `UNSET` |
| 1 | `DEFAULT`, `PREFER_OUTLINE` |
| 2 | `PREFER_INLINE` |
| 3 | `FORCE_OUTLINE` |

따라서 2비트 필드로 네 값을 모두 표현할 수 있다. 이 alias는 JIRA의 정책 정의와도 일치한다.
`PREFER_OUTLINE`은 현재 `DEFAULT`와 같은 일반 OOS demotion 정책이다.

### 2. 가변 타입에서 고정 타입으로 변경한 뒤 FORCE_OUTLINE 잔존

- 댓글: [discussion_r3654693131](https://github.com/CUBRID/cubrid/pull/7538#discussion_r3654693131)
- 작성자: `lht1199`
- 위치: `src/query/execute_schema.c:12308`
- 판정: **유효 — 기능 오류**
- 처리: **수정 완료**

`ALTER TABLE ... MODIFY`에서 `STORAGE` 절을 생략하면 기존 storage 속성을 보존한다. 기존 코드는 새 타입이
고정 타입이어도 `SM_ATTFLAG_OOS_FORCE_OUTLINE`을 그대로 보존했다. 그 결과 `INTEGER STORAGE FORCE_OUTLINE`처럼
생성 시에는 허용되지 않는 스키마 상태가 ALTER 경로에서 만들어졌다.

수정 내용:

- 새 domain이 가변 타입이 아니고 `STORAGE` 절이 생략되었으면 기존 `FORCE_OUTLINE` 속성을 `LOST`로 처리한다.
- 리뷰어가 제시한 `VARCHAR(4) FORCE_OUTLINE → INT` 시나리오를 회귀 테스트로 추가했다.
- ALTER 이후 `SHOW CREATE TABLE`에 `STORAGE FORCE_OUTLINE`이 없고, 변환된 값 `1234`가 정상 조회되는지 확인한다.

관련 로컬 코드:

- `src/query/execute_schema.c:12569`
- `unit_tests/oos/sql/test_oos_sql_storage.cpp:426`

### 3. PREFER_INLINE/FORCE_OUTLINE을 별도 boolean으로 보관

- 댓글: [discussion_r3656348304](https://github.com/CUBRID/cubrid/pull/7538#discussion_r3656348304)
- 작성자: `hgryoo`
- 위치: `src/base/object_representation_sr.h:120`
- 원문 요지: 두 속성이 동시에 set될 수 있는 표현보다 하나의 필드로 합치는 것이 좋음
- 판정: **유효 — 불가능한 상태를 타입 표현에서 제거하는 설계 개선**
- 처리: **수정 완료**

영속 스키마의 `SM_ATTRIBUTE.flags`는 기존 디스크 호환성 때문에 비트 플래그를 유지해야 한다. 그러나 서버의
일시적 `OR_ATTRIBUTE` 표현까지 두 boolean을 유지할 필요는 없다. 두 boolean은 둘 다 true인 상태를 표현할 수
있고, heap 배치 코드가 그 상태의 우선순위를 암묵적으로 결정하게 만든다.

수정 내용:

- `is_oos_prefer_inline`과 `is_oos_force_outline`을 단일 2비트 enum 필드 `oos_storage`로 통합했다.
- enum 상태는 `DEFAULT`, `PREFER_INLINE`, `FORCE_OUTLINE` 세 개다.
- 디스크 flags를 읽을 때 두 영속 비트가 동시에 설정되지 않았음을 assert하고 단일 상태로 변환한다.
- heap layout은 단일 상태만 검사한다.

관련 로컬 코드:

- `src/base/object_representation_sr.h:92`
- `src/base/object_representation_sr.c:2520`
- `src/storage/heap_file.c:12119`

### 4. db_attribute_is_oos_force_outline 단순화

- 댓글: [discussion_r3662847340](https://github.com/CUBRID/cubrid/pull/7538#discussion_r3662847340)
- 작성자: `youngjun9072`
- 위치: `src/compat/db_info.c:1401`
- 판정: **유효 — NIT 수준의 가독성 개선**
- 처리: **수정 완료**

임시 `status` 변수와 조건문을 제거하고 null 검사와 flag 검사를 직접 반환하도록 변경했다.

관련 로컬 코드: `src/compat/db_info.c:1392`

## 그 밖의 PR 댓글과 리뷰

| 시각(UTC) | 종류 | 작성자 | 내용/상태 | 처리 |
|---|---|---|---|---|
| 2026-07-24 09:12:09 | PR 대화 | `vimkim` | `/run all` | 정보성 기록 |
| 2026-07-24 09:27:03 | 리뷰 | `hornetmj` | `APPROVED` | 수정 요구 없음 |
| 2026-07-27 08:21:27 | 리뷰 | `YeunjunLee` | `APPROVED` | 수정 요구 없음 |
| 2026-07-27 10:36:51 | 리뷰 | `hgryoo` | `APPROVED` | 인라인 댓글은 별도 추적 |
| 2026-07-28 08:38:29 | 리뷰 | `youngjun9072` | `APPROVED` | 인라인 NIT는 별도 추적 |

본문이 빈 `COMMENTED` 리뷰 4건은 각각 인라인 댓글 제출을 감싸는 wrapper다. 새로운 의견이 없으므로 위 인라인
댓글과 중복 기록하지 않았다.

## 로컬 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `src/base/object_representation_sr.h` | OOS storage 상태를 단일 enum 필드로 통합 |
| `src/base/object_representation_sr.c` | 영속 flags를 단일 서버 상태로 변환하고 상호 배타성 검증 |
| `src/storage/heap_file.c` | 단일 OOS storage 상태 사용 |
| `src/query/execute_schema.c` | 고정 타입 변경 시 잔존 `FORCE_OUTLINE` 해제 |
| `src/compat/db_info.c` | 조회 함수 단순화 |
| `unit_tests/oos/sql/test_oos_sql_storage.cpp` | 리뷰어 재현 시나리오 회귀 테스트 추가 |

기존 로컬 변경인 `cubrid-cci` submodule dirty 상태, 환경 파일, `64e5dbbbf` 코드 스타일 커밋은 건드리지 않았다.

## 검증 결과

- `debug_gcc` 빌드 및 설치: 성공
- 구성된 전체 CTest: **24/24 통과**, 실패 0, 총 49.06초
- 최종 리팩터링 후 재빌드: 성공
- 최종 `test_oos_sql_storage` fixture 실행: **3/3 통과**
  - `oos_setup_db`
  - `test_oos_sql_storage` 내부 15개 테스트
  - `oos_cleanup_db`
- 포맷 dry-run: 변경 제안 없음
- `git diff --check`: 통과

## 남은 작업

- 로컬 수정 내용을 커밋하고 PR 브랜치에 push해야 한다.
- push 후 네 인라인 스레드에 판정과 수정 근거를 답변해야 한다.
- 유효한 세 스레드는 원격 diff 반영을 확인한 뒤 resolve할 수 있다.
- 2비트 댓글은 alias 관계를 설명한 뒤 reviewer 판단에 따라 resolve한다.
